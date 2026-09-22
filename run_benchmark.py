#!/usr/bin/env python3
"""JEV Multi-Channel Benchmark Runner.

Executes the JEV Deterministic Decision Benchmark across three providers:
  1. TypeSafe Direct (https://api.typesafe.ai/v1/systemone)
  2. Experiential Labs (https://api.experientiallabs.ai/v1/systemone)
  3. OpenRouter (https://openrouter.ai/api/alpha/decisions)

Distributes questions evenly across the active channels (round-robin by default),
extracts selected choices, 5-option probabilities, reported confidence scores,
measures latency, and formats output into both CSV (matching results_schema.csv)
and structured JSON.

Safety:
  By default, runs in DRY-RUN mode (validates config, prepares requests, spends 0 credits).
  Pass --execute to actually run live inference against the providers.

Usage:
  # Dry-run (validate plan, requests, and credentials without spending credits):
  python3 run_benchmark.py --plan smoke --limit 5

  # 5-question live pilot:
  python3 run_benchmark.py --plan smoke --limit 5 --execute --out runs/pilot_5

  # 100-question live smoke run:
  python3 run_benchmark.py --plan smoke --execute --out runs/smoke_100 --run-analysis

  # 2,780-question live evaluation run:
  python3 run_benchmark.py --plan evaluation --execute --out runs/evaluation_01 --run-analysis
"""

from __future__ import annotations

import argparse
import concurrent.futures
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import ssl
import sys
import threading
import time
from typing import Any, Mapping
import urllib.error
import urllib.request
import zipfile

# SSL context with certifi fallback
def get_ssl_context() -> ssl.SSLContext:
    ctx = ssl.create_default_context()
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        fallback_bundles = (
            "/etc/ssl/cert.pem",
            "/usr/local/etc/ca-certificates/cert.pem",
            "/etc/pki/tls/certs/ca-bundle.crt",
        )
        for bundle in fallback_bundles:
            if os.path.isfile(bundle):
                try:
                    return ssl.create_default_context(cafile=bundle)
                except Exception:
                    pass
        return ctx

SSL_CONTEXT = get_ssl_context()

CSV_HEADERS = [
    "run_id",
    "item_id",
    "repeat_index",
    "selected_option",
    "probability_1",
    "probability_2",
    "probability_3",
    "probability_4",
    "probability_5",
    "reported_confidence",
    "status",
    "provider",
    "model_requested",
    "model_returned",
    "prompt_mode",
    "settings_json",
    "timestamp_utc",
    "latency_ms",
    "input_tokens",
    "output_tokens",
    "http_status",
    "attempt_count",
    "api_request_id",
    "prompt_sha256",
    "request_payload_sha256",
    "error_message",
    "raw_response_json",
]

CHANNELS_CONFIG = {
    "typesafe": {
        "name": "TypeSafe Direct",
        "base_url": "https://api.typesafe.ai/v1/systemone",
        "model": "jev-latest",
        "env_keys": ["TYPESAFE_API_KEY"],
    },
    "experiential": {
        "name": "Experiential Labs",
        "base_url": "https://api.experientiallabs.ai/v1/systemone",
        "model": "jev-latest",
        "env_keys": [
            "EXPERIENTIAL_LAB_JEV_API_KEY",
            "EXPERIENTIAL_LABS_API_KEY",
            "EXPERIENTIAL_API_KEY",
            "EXPLABS_API_KEY",
        ],
    },
    "openrouter": {
        "name": "OpenRouter",
        "base_url": "https://openrouter.ai/api/alpha/decisions",
        "model": "jev-latest",
        "env_keys": ["OPENROUTER_API_KEY"],
    },
}


def load_env(env_path: Path) -> dict[str, str]:
    vals = {}
    if env_path.exists():
        with env_path.open("r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip("'\"")
                vals[k] = v
    for k, v in os.environ.items():
        vals[k] = v
    return vals


def get_api_key(channel: str, env_vars: dict[str, str]) -> str:
    cfg = CHANNELS_CONFIG.get(channel)
    if not cfg:
        return ""
    for key_name in cfg["env_keys"]:
        val = env_vars.get(key_name)
        if val:
            return val
    return ""


def redact_secrets(text: str, secret_keys: list[str]) -> str:
    if not text:
        return ""
    redacted = text
    for key in secret_keys:
        if key and len(key) >= 6:
            redacted = redacted.replace(key, "[REDACTED_API_KEY]")
    return redacted


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def canonical_json_bytes(obj: Any) -> bytes:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def execute_single_request(
    channel: str,
    payload: dict[str, Any],
    api_key: str,
    timeout: float = 15.0,
    max_retries: int = 3,
    all_secret_keys: list[str] | None = None,
) -> tuple[dict[str, Any], int, float, int, str]:
    """Sends one decision request to the specified channel with retry backoff.
    
    Returns: (parsed_json, http_status, latency_ms, attempt_count, error_message)
    """
    cfg = CHANNELS_CONFIG[channel]
    url = cfg["base_url"]
    data = json.dumps(payload).encode("utf-8")

    attempts = 0
    backoff = 1.0
    secrets = all_secret_keys or ([api_key] if api_key else [])

    while attempts < max_retries:
        attempts += 1
        req = urllib.request.Request(
            url,
            data=data,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
                "User-Agent": "JEV-Benchmark-Runner/1.0",
            },
            method="POST",
        )
        t0 = time.perf_counter()
        try:
            with urllib.request.urlopen(req, timeout=timeout, context=SSL_CONTEXT) as resp:
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                body = resp.read().decode("utf-8", errors="replace")
                try:
                    parsed = json.loads(body)
                except Exception as e:
                    return {}, resp.status, elapsed_ms, attempts, redact_secrets(f"Invalid JSON response: {e}", secrets)
                return parsed, resp.status, elapsed_ms, attempts, ""
        except urllib.error.HTTPError as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            body = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            status = exc.code
            if status in (429, 500, 502, 503, 504, 529) and attempts < max_retries:
                retry_after = exc.headers.get("Retry-After") if exc.headers else None
                sleep_time = float(retry_after) if retry_after and retry_after.isdigit() else backoff
                time.sleep(min(sleep_time, 10.0))
                backoff *= 2.0
                continue
            err_msg = redact_secrets(f"HTTP {status}: {body[:300]}", secrets)
            return {}, status, elapsed_ms, attempts, err_msg
        except urllib.error.URLError as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            if attempts < max_retries:
                time.sleep(backoff)
                backoff *= 2.0
                continue
            return {}, 0, elapsed_ms, attempts, redact_secrets(f"Transport error: {exc.reason}", secrets)
        except TimeoutError:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            if attempts < max_retries:
                time.sleep(backoff)
                backoff *= 2.0
                continue
            return {}, 0, elapsed_ms, attempts, "Request timed out"
        except Exception as exc:
            elapsed_ms = (time.perf_counter() - t0) * 1000.0
            return {}, 0, elapsed_ms, attempts, redact_secrets(f"Unexpected error: {exc}", secrets)

    return {}, 0, 0.0, attempts, "Exceeded max retries"


def parse_response(
    resp_json: dict[str, Any],
    http_status: int,
    error_msg: str,
) -> tuple[str, str, float | None, dict[str, float], str, int | None, int | None, str]:
    """Extracts benchmark metrics from JEV response.
    
    Returns:
      (status, selected_choice, reported_confidence, probabilities_dict, model_returned, input_tokens, output_tokens, api_request_id)
    """
    if error_msg or http_status != 200 or not resp_json:
        status = "timeout" if "timed out" in error_msg.lower() else "error"
        return status, "", None, {}, "", None, None, ""

    answers = resp_json.get("answers", {})
    decision = answers.get("decision", {})
    choice = str(decision.get("choice", "")).strip()
    conf = decision.get("confidence")
    reported_conf = float(conf) if conf is not None and isinstance(conf, (int, float)) and math.isfinite(conf) else None

    raw_probs = decision.get("probabilities", {})
    probs: dict[str, float] = {}
    if isinstance(raw_probs, dict):
        for k, v in raw_probs.items():
            if isinstance(v, (int, float)) and math.isfinite(v):
                probs[str(k)] = float(v)

    model_returned = str(resp_json.get("model", "")).strip()
    usage = resp_json.get("usage", {})
    in_tok = usage.get("input_tokens")
    out_tok = usage.get("output_tokens")
    input_tokens = int(in_tok) if isinstance(in_tok, (int, float)) else None
    output_tokens = int(out_tok) if isinstance(out_tok, (int, float)) else None
    api_request_id = str(resp_json.get("id", "")).strip()

    status = "ok" if choice in ("1", "2", "3", "4", "5") else "invalid_response"
    return status, choice, reported_conf, probs, model_returned, input_tokens, output_tokens, api_request_id


def export_package(out_dir: Path, export_zip: Path) -> Path:
    """Exports results, manifest, raw responses, and reports into a clean zip package excluding secrets."""
    export_zip.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(export_zip, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in out_dir.rglob("*"):
            if file_path.is_file():
                # Avoid archiving secrets, git files, or the destination zip itself
                if file_path.resolve() == export_zip.resolve() or file_path.name in (".env", ".DS_Store") or file_path.name.endswith(".tmp"):
                    continue
                rel_path = file_path.relative_to(out_dir)
                zf.write(file_path, arcname=str(rel_path))
    print(f"Export package created: {export_zip} ({export_zip.stat().st_size} bytes)")
    return export_zip


def run_benchmark(
    bank_dir: Path,
    env_path: Path,
    out_dir: Path,
    plan: str = "smoke",
    model: str = "jev-latest",
    run_id: str | None = None,
    limit: int | None = None,
    channels: list[str] | None = None,
    concurrency_per_channel: int = 2,
    timeout: float = 15.0,
    max_retries: int = 3,
    max_http_attempts: int | None = None,
    batch_size: int | None = None,
    execute: bool = False,
    resume: bool = True,
    run_analysis: bool = False,
    export_zip_path: Path | None = None,
) -> dict[str, Any]:
    bank_dir = bank_dir.resolve()
    out_dir = out_dir.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Credentials
    env_vars = load_env(env_path)
    active_channels = channels or ["typesafe", "experiential", "openrouter"]
    api_keys = {}
    for ch in active_channels:
        key = get_api_key(ch, env_vars)
        if not key and execute:
            raise ValueError(f"No API key found for channel '{ch}'. Please check {env_path}.")
        api_keys[ch] = key

    all_secrets = [k for k in api_keys.values() if k]

    print(f"Active channels ({len(active_channels)}): {', '.join(active_channels)}")

    # 2. Plan jobs & requests
    plan_rows = [r for r in load_csv(bank_dir / "run_plan.csv") if r["plan"] == plan]
    plan_rows.sort(key=lambda r: int(r["order"]))
    if not plan_rows:
        raise ValueError(f"Unknown or empty plan: {plan}")

    if limit is not None and limit > 0:
        plan_rows = plan_rows[:limit]

    total_jobs = len(plan_rows)
    print(f"Selected plan '{plan}': {total_jobs} questions.")

    # Templates & Request Packets
    res_template = {r["item_id"]: r for r in load_csv(bank_dir / "results_template.csv")}
    packets = {}
    with (bank_dir / "jev_requests.jsonl").open(encoding="utf-8") as f:
        for line in f:
            rec = json.loads(line)
            packets[rec["item_id"]] = rec["payload"]

    # Optional Answer Key for live accuracy evaluation
    answer_keys = {}
    key_path = bank_dir / "answer_key_PRIVATE.csv"
    if key_path.exists():
        answer_keys = {r["item_id"]: r for r in load_csv(key_path)}

    manifest = json.loads((bank_dir / "manifest.json").read_text(encoding="utf-8"))
    actual_run_id = run_id or f"{plan}_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    # 3. Always prepare requests.jsonl, results_template.csv, and run_manifest.json (reuses prepare_run.py contract)
    prepared_requests_path = out_dir / "requests.jsonl"
    prepared_template_path = out_dir / "results_template.csv"
    run_manifest_path = out_dir / "run_manifest.json"

    template_headers = list(res_template[plan_rows[0]["item_id"]].keys())
    template_rows = []
    with prepared_requests_path.open("w", encoding="utf-8") as f_req:
        for idx, job in enumerate(plan_rows):
            item = job["item_id"]
            rep = int(job["repeat_index"])
            ch = active_channels[idx % len(active_channels)]
            payload = {"model": model, **packets[item]}
            canonical = canonical_json_bytes(payload)
            row = res_template[item].copy()
            row.update(run_id=actual_run_id, repeat_index=str(rep), provider=ch,
                       model_requested=model, prompt_mode="native_choice")
            template_rows.append(row)
            wrapper = {
                "run_id": actual_run_id,
                "item_id": item,
                "repeat_index": rep,
                "channel": ch,
                "prompt_sha256": row["prompt_sha256"],
                "prepared_payload_sha256": hashlib.sha256(canonical).hexdigest(),
                "payload": payload,
            }
            f_req.write(json.dumps(wrapper, ensure_ascii=False) + "\n")

    if not prepared_template_path.exists():
        with prepared_template_path.open("w", encoding="utf-8-sig", newline="") as f_tmpl:
            w = csv.DictWriter(f_tmpl, fieldnames=template_headers)
            w.writeheader()
            w.writerows(template_rows)

    manifest_record = {
        "benchmark_version": manifest["benchmark_version"],
        "plan": plan,
        "run_id": actual_run_id,
        "model_requested": model,
        "active_channels": active_channels,
        "prompt_mode": "native_choice",
        "requests_prepared": total_jobs,
        "execute": execute,
        "prepared_at_utc": datetime.now(timezone.utc).isoformat(),
        "instructions": "Send only the payload object from requests.jsonl. Preserve option IDs and all returned probabilities.",
    }
    run_manifest_path.write_text(json.dumps(manifest_record, indent=2) + "\n", encoding="utf-8")

    # 4. DRY-RUN MODE CHECK
    if not execute:
        print("\n" + "=" * 65)
        print("               DRY-RUN MODE (No API calls made)")
        print("=" * 65)
        print(f"Plan: {plan} | Run ID: {actual_run_id}")
        print(f"Prepared {total_jobs} requests in: {prepared_requests_path}")
        print(f"Prepared results template in: {prepared_template_path}")
        print(f"Run manifest saved to: {run_manifest_path}")
        print("-" * 65)
        print("Channel Distribution:")
        counts = {ch: 0 for ch in active_channels}
        for idx in range(total_jobs):
            counts[active_channels[idx % len(active_channels)]] += 1
        for ch, cnt in counts.items():
            has_key = bool(get_api_key(ch, env_vars))
            status_str = "Configured ✓" if has_key else "Missing key in .env ✗"
            print(f"  - {ch:<16}: {cnt:>4} questions | {status_str}")
        print("=" * 65)
        print("To execute live inference and spend credits, add the --execute flag:")
        print(f"  python3 run_benchmark.py --plan {plan}" + (f" --limit {limit}" if limit else "") + " --execute\n")
        return manifest_record

    # 5. LIVE EXECUTION MODE
    print(f"\n[EXECUTION MODE] Starting live inference across {len(active_channels)} channels...")

    # Check existing results for resume
    completed_rows: dict[tuple[str, int], dict[str, Any]] = {}
    main_csv_path = out_dir / "results_completed.csv"
    if resume and main_csv_path.exists():
        try:
            for row in load_csv(main_csv_path):
                iid = row.get("item_id", "")
                rid = int(row.get("repeat_index", 1))
                if row.get("status") in ("ok", "error", "timeout", "invalid_response") and (
                    row.get("selected_option") or row.get("error_message")
                ):
                    completed_rows[(iid, rid)] = row
            print(f"Resuming: found {len(completed_rows)} already completed items in {main_csv_path.name}")
        except Exception as e:
            print(f"Warning reading existing CSV for resume: {e}")

    remaining_jobs = []
    for idx, job in enumerate(plan_rows):
        item_id = job["item_id"]
        rep = int(job["repeat_index"])
        assigned_channel = active_channels[idx % len(active_channels)]
        if (item_id, rep) in completed_rows:
            continue
        remaining_jobs.append({
            "index": idx + 1,
            "item_id": item_id,
            "repeat_index": rep,
            "channel": assigned_channel,
            "payload_data": packets[item_id],
            "template_row": res_template[item_id],
        })

    print(f"Jobs remaining to execute: {len(remaining_jobs)} of {total_jobs}")
    if batch_size is not None and batch_size > 0:
        remaining_jobs = remaining_jobs[:batch_size]
        print(f"Batch limit applied: executing next {len(remaining_jobs)} questions in this step.")

    # Execution controls
    lock = threading.Lock()
    all_results: list[dict[str, Any]] = list(completed_rows.values())
    total_http_attempts = 0
    stop_event = threading.Event()

    # Write headers if main CSV does not exist
    if not main_csv_path.exists():
        with main_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writeheader()

    def worker(job: dict[str, Any]) -> dict[str, Any] | None:
        nonlocal total_http_attempts
        if stop_event.is_set():
            return None

        ch = job["channel"]
        item_id = job["item_id"]
        rep = job["repeat_index"]
        payload = {"model": model, **job["payload_data"]}
        payload_bytes = canonical_json_bytes(payload)
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        prompt_sha256 = job["template_row"]["prompt_sha256"]

        timestamp = datetime.now(timezone.utc).isoformat()
        resp_json, http_status, latency_ms, attempts, error_msg = execute_single_request(
            channel=ch,
            payload=payload,
            api_key=api_keys[ch],
            timeout=timeout,
            max_retries=max_retries,
            all_secret_keys=all_secrets,
        )

        with lock:
            total_http_attempts += attempts
            if max_http_attempts and total_http_attempts >= max_http_attempts:
                print(f"\n[WARNING] Hard HTTP attempts cap reached ({total_http_attempts} >= {max_http_attempts}). Stopping further requests.")
                stop_event.set()

        status, choice, reported_conf, probs, model_ret, in_tok, out_tok, req_id = parse_response(
            resp_json, http_status, error_msg
        )

        # Redact any secrets from raw response JSON string
        raw_json_str = json.dumps(resp_json, ensure_ascii=False) if resp_json else ""
        raw_json_str = redact_secrets(raw_json_str, all_secrets)

        row = {
            "run_id": actual_run_id,
            "item_id": item_id,
            "repeat_index": rep,
            "selected_option": choice,
            "probability_1": f"{probs.get('1', ''):.15g}" if "1" in probs else "",
            "probability_2": f"{probs.get('2', ''):.15g}" if "2" in probs else "",
            "probability_3": f"{probs.get('3', ''):.15g}" if "3" in probs else "",
            "probability_4": f"{probs.get('4', ''):.15g}" if "4" in probs else "",
            "probability_5": f"{probs.get('5', ''):.15g}" if "5" in probs else "",
            "reported_confidence": f"{reported_conf:.15g}" if reported_conf is not None else "",
            "status": status,
            "provider": ch,
            "model_requested": model,
            "model_returned": model_ret or model,
            "prompt_mode": "native_choice",
            "settings_json": json.dumps({"timeout": timeout, "max_retries": max_retries}),
            "timestamp_utc": timestamp,
            "latency_ms": f"{latency_ms:.2f}",
            "input_tokens": in_tok if in_tok is not None else "",
            "output_tokens": out_tok if out_tok is not None else "",
            "http_status": http_status if http_status else "",
            "attempt_count": attempts,
            "api_request_id": req_id,
            "prompt_sha256": prompt_sha256,
            "request_payload_sha256": payload_sha256,
            "error_message": redact_secrets(error_msg, all_secrets),
            "raw_response_json": raw_json_str,
        }

        correct_symbol = ""
        if item_id in answer_keys:
            gold = answer_keys[item_id].get("gold_option") or answer_keys[item_id].get("correct_option")
            is_correct = (choice == gold)
            correct_symbol = " ✓" if is_correct else f" ✗ (gold={gold})"

        with lock:
            all_results.append(row)
            with main_csv_path.open("a", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
                w.writerow(row)

            conf_str = f"conf={reported_conf:.2f}" if reported_conf is not None else "conf=N/A"
            print(
                f"[{len(all_results)}/{total_jobs}] {job['item_id']} via {ch:<12} | "
                f"choice={choice or '-'}{correct_symbol:<14} | {conf_str} | "
                f"{latency_ms:6.1f}ms | status={status}"
            )

        return row

    max_workers = max(1, len(active_channels) * concurrency_per_channel)
    if remaining_jobs:
        print(f"Starting execution pool with {max_workers} concurrent workers...")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = [executor.submit(worker, job) for job in remaining_jobs]
            for f in concurrent.futures.as_completed(futures):
                try:
                    f.result()
                except Exception as exc:
                    print(f"Error in worker thread: {exc}")

    # 6. Write outputs: JSON, JSONL, and Per-Provider CSVs
    print("\nFinalizing output files...")

    json_path = out_dir / "results_completed.json"
    jsonl_path = out_dir / "results_completed.jsonl"
    with json_path.open("w", encoding="utf-8") as f:
        json.dump(all_results, f, indent=2, ensure_ascii=False)
    with jsonl_path.open("w", encoding="utf-8") as f:
        for r in all_results:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")

    for ch in active_channels:
        ch_rows = [r for r in all_results if r.get("provider") == ch]
        ch_csv_path = out_dir / f"results_{ch}.csv"
        with ch_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writeheader()
            w.writerows(ch_rows)

    # 7. Generate Summary Report
    valid_results = [r for r in all_results if r.get("status") == "ok" and r.get("selected_option")]
    by_channel: dict[str, dict[str, Any]] = {}
    for ch in active_channels:
        ch_items = [r for r in all_results if r.get("provider") == ch]
        ch_valid = [r for r in ch_items if r.get("status") == "ok" and r.get("selected_option")]
        latencies = [float(r["latency_ms"]) for r in ch_items if r.get("latency_ms")]
        correct_count = 0
        gold_available = 0
        for r in ch_valid:
            iid = r["item_id"]
            if iid in answer_keys:
                gold_available += 1
                gold = answer_keys[iid].get("gold_option") or answer_keys[iid].get("correct_option")
                if r["selected_option"] == gold:
                    correct_count += 1

        by_channel[ch] = {
            "total_items": len(ch_items),
            "valid_items": len(ch_valid),
            "errors": len(ch_items) - len(ch_valid),
            "mean_latency_ms": round(sum(latencies) / len(latencies), 2) if latencies else None,
            "accuracy": round(correct_count / gold_available, 4) if gold_available else None,
            "gold_items_evaluated": gold_available,
        }

    total_correct = 0
    total_gold = 0
    for r in valid_results:
        iid = r["item_id"]
        if iid in answer_keys:
            total_gold += 1
            gold = answer_keys[iid].get("gold_option") or answer_keys[iid].get("correct_option")
            if r["selected_option"] == gold:
                total_correct += 1

    all_latencies = [float(r["latency_ms"]) for r in all_results if r.get("latency_ms")]
    confidences = [
        float(r["reported_confidence"])
        for r in valid_results
        if r.get("reported_confidence") and r["reported_confidence"] != ""
    ]

    summary = {
        "benchmark_version": manifest["benchmark_version"],
        "plan": plan,
        "run_id": actual_run_id,
        "model_requested": model,
        "total_requests": len(all_results),
        "valid_decisions": len(valid_results),
        "failed_requests": len(all_results) - len(valid_results),
        "total_http_attempts": total_http_attempts,
        "mean_latency_ms": round(sum(all_latencies) / len(all_latencies), 2) if all_latencies else None,
        "mean_reported_confidence": round(sum(confidences) / len(confidences), 4) if confidences else None,
        "overall_accuracy": round(total_correct / total_gold, 4) if total_gold else None,
        "gold_items_evaluated": total_gold,
        "channels": by_channel,
        "completed_at_utc": datetime.now(timezone.utc).isoformat(),
        "files_generated": [
            str(main_csv_path.name),
            str(json_path.name),
            str(jsonl_path.name),
            *[f"results_{ch}.csv" for ch in active_channels],
        ],
    }

    summary_path = out_dir / "summary_report.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    # 8. Print Console Summary
    print("\n" + "=" * 65)
    print("           JEV BENCHMARK RUN SUMMARY")
    print("=" * 65)
    print(f"Plan: {plan} | Run ID: {actual_run_id}")
    print(f"Total Questions: {len(all_results)} | Valid: {len(valid_results)} | Errors: {len(all_results) - len(valid_results)}")
    if total_gold:
        print(f"Overall Accuracy: {summary['overall_accuracy'] * 100:.1f}% ({total_correct}/{total_gold})")
    if confidences:
        print(f"Mean Reported Confidence: {summary['mean_reported_confidence'] * 100:.1f}%")
    if all_latencies:
        print(f"Mean Latency: {summary['mean_latency_ms']:.1f}ms")
    print("-" * 65)
    print(f"{'Channel':<16} {'Items':<8} {'Valid':<8} {'Errors':<8} {'Avg Latency':<14} {'Accuracy':<10}")
    for ch, stats in by_channel.items():
        acc_str = f"{stats['accuracy'] * 100:.1f}%" if stats['accuracy'] is not None else "N/A"
        lat_str = f"{stats['mean_latency_ms']}ms" if stats['mean_latency_ms'] is not None else "N/A"
        print(f"{ch:<16} {stats['total_items']:<8} {stats['valid_items']:<8} {stats['errors']:<8} {lat_str:<14} {acc_str:<10}")
    print("=" * 65)
    print(f"Outputs written to: {out_dir}\n")

    # 9. Optional Run Package Analyzer
    if run_analysis:
        analyze_script = bank_dir / "analyze_results.py"
        if analyze_script.exists():
            print("Running official package analyzer per provider...")
            import subprocess

            for ch in active_channels:
                ch_csv = out_dir / f"results_{ch}.csv"
                ch_analysis_dir = out_dir / f"analysis_{ch}"
                cmd = [
                    sys.executable,
                    str(analyze_script),
                    str(ch_csv),
                    "--run-id", actual_run_id,
                    "--out", str(ch_analysis_dir),
                ]
                if plan in ("smoke", "development"):
                    cmd.extend(["--split", "development"])
                print(f"  > Analyzing {ch}...")
                res = subprocess.run(cmd, capture_output=True, text=True)
                if res.returncode != 0:
                    print(f"    Analyzer warning for {ch}: {res.stderr.strip() or res.stdout.strip()}")
                else:
                    print(f"    Analysis for {ch} saved to {ch_analysis_dir}")

    # 10. Optional Export Package
    if export_zip_path:
        export_package(out_dir, export_zip_path)

    return summary


def main():
    parser = argparse.ArgumentParser(description="Run JEV Benchmark across multiple channels")
    parser.add_argument("--plan", choices=["smoke", "development", "evaluation", "full", "repeatability"], default="smoke")
    parser.add_argument("--model", default="jev-latest", help="JEV model identifier (default: jev-latest)")
    parser.add_argument("--run-id", default=None, help="Custom run identifier")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of questions (e.g. for pilot/testing)")
    parser.add_argument("--channels", default="typesafe,experiential,openrouter", help="Comma-separated channels to use")
    parser.add_argument("--concurrency-per-channel", type=int, default=2, help="Concurrency per channel (default: 2)")
    parser.add_argument("--timeout", type=float, default=15.0, help="HTTP request timeout in seconds (default: 15)")
    parser.add_argument("--max-retries", type=int, default=3, help="Max retry attempts per request (default: 3)")
    parser.add_argument("--max-http-attempts", type=int, default=None, help="Hard cap on total HTTP attempts (including retries)")
    parser.add_argument("--batch-size", type=int, default=None, help="Number of uncompleted questions to run in this batch")
    parser.add_argument("--bank", type=Path, default=Path(__file__).resolve().parent / "JEV_Deterministic_Decision_Benchmark_v1")
    parser.add_argument("--env-file", type=Path, default=Path(__file__).resolve().parent / ".env")
    parser.add_argument("--out", type=Path, default=None, help="Output directory")
    parser.add_argument("--execute", action="store_true", help="Explicitly authorize live API calls (otherwise runs dry-run)")
    parser.add_argument("--no-resume", dest="resume", action="store_false", help="Do not resume existing run")
    parser.add_argument("--run-analysis", action="store_true", help="Run analyze_results.py after benchmark completion")
    parser.add_argument("--export-package", type=Path, default=None, help="Export final results package as a clean zip file")

    args = parser.parse_args()
    channel_list = [c.strip() for c in args.channels.split(",") if c.strip()]

    out_dir = args.out
    if out_dir is None:
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        prefix = "dryrun" if not args.execute else "run"
        out_dir = Path(__file__).resolve().parent / "runs" / f"{prefix}_{args.plan}_{ts}"

    run_benchmark(
        bank_dir=args.bank,
        env_path=args.env_file,
        out_dir=out_dir,
        plan=args.plan,
        model=args.model,
        run_id=args.run_id,
        limit=args.limit,
        channels=channel_list,
        concurrency_per_channel=args.concurrency_per_channel,
        timeout=args.timeout,
        max_retries=args.max_retries,
        max_http_attempts=args.max_http_attempts,
        batch_size=args.batch_size,
        execute=args.execute,
        resume=args.resume,
        run_analysis=args.run_analysis,
        export_zip_path=args.export_package,
    )


if __name__ == "__main__":
    main()
