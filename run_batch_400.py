#!/usr/bin/env python3
"""
Run the next 400 questions of the JEV Deterministic Decision Benchmark.
- Accumulates results into runs/combined_400/results_completed.csv (reaching 1,000 items).
- Automatically retries any channel failures (especially Experiential Labs 429) via TypeSafe Direct.
- Saves the 400 new results separately in runs/combined_400/additional_400_eval.csv and runs/combined_400/batch_3_new_400.csv.
"""
import concurrent.futures
import csv
import hashlib
import json
import os
import sys
import threading
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from run_benchmark import (
    CHANNELS_CONFIG,
    CSV_HEADERS,
    SSL_CONTEXT,
    canonical_json_bytes,
    execute_single_request,
    get_api_key,
    load_csv,
    load_env,
    parse_response,
    redact_secrets,
)

BASE_DIR = Path("/Users/etsabary/Documents/repos/benchmarks/jev")
BANK_DIR = BASE_DIR / "JEV_Deterministic_Decision_Benchmark_v1"
COMBINED_DIR = BASE_DIR / "runs" / "combined_400"
ENV_FILE = BASE_DIR / ".env"

def main():
    print("=" * 65)
    print("          JEV BENCHMARK - BATCH 3 (400 QUESTIONS)")
    print("=" * 65)

    # 1. Load credentials
    env_vars = load_env(ENV_FILE)
    api_keys = {
        "typesafe": get_api_key("typesafe", env_vars),
        "experiential": get_api_key("experiential", env_vars),
        "openrouter": get_api_key("openrouter", env_vars),
    }
    all_secrets = [k for k in api_keys.values() if k]
    active_channels = [ch for ch, k in api_keys.items() if k]
    print(f"Active channels: {active_channels}")

    # 2. Load packets, answer keys, and templates
    packets_path = BANK_DIR / "jev_requests.jsonl"
    packets = {}
    with packets_path.open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                packets[item["item_id"]] = item["payload"]

    answer_keys = {}
    ak_path = BANK_DIR / "answer_key_PRIVATE.csv"
    if ak_path.exists():
        for row in load_csv(ak_path):
            answer_keys[row["item_id"]] = row

    templates = {}
    tmpl_path = BANK_DIR / "results_template.csv"
    if tmpl_path.exists():
        for row in load_csv(tmpl_path):
            templates[row["item_id"]] = row

    # 3. Check already completed items
    master_csv_path = COMBINED_DIR / "results_completed.csv"
    completed_items = set()
    master_rows = []
    if master_csv_path.exists():
        master_rows = load_csv(master_csv_path)
        for r in master_rows:
            if r.get("status") == "ok" and r.get("selected_option"):
                completed_items.add(r["item_id"])

    print(f"Already completed in master dataset: {len(completed_items)} items")

    # 4. Extract next 400 uncompleted items from evaluation plan
    plan_rows = load_csv(BANK_DIR / "run_plan.csv")
    eval_plan = [r for r in plan_rows if r["plan"] == "evaluation"]
    uncompleted = [r for r in eval_plan if r["item_id"] not in completed_items]
    print(f"Total uncompleted in evaluation plan: {len(uncompleted)}")

    target_batch = uncompleted[:400]
    print(f"Selected batch: {len(target_batch)} questions (from {target_batch[0]['item_id']} to {target_batch[-1]['item_id']})")

    # 5. Distribute across channels round-robin
    jobs = []
    for idx, item in enumerate(target_batch):
        assigned_ch = active_channels[idx % len(active_channels)]
        jobs.append({
            "index": idx + 1,
            "item_id": item["item_id"],
            "repeat_index": int(item.get("repeat_index", 1)),
            "channel": assigned_ch,
            "payload_data": packets[item["item_id"]],
            "template_row": templates.get(item["item_id"], {}),
        })

    # 6. Execute with worker pool and automatic TypeSafe failover
    new_results = []
    lock = threading.Lock()
    completed_count = 0
    failover_count = 0

    def worker(job: dict[str, Any]) -> dict[str, Any]:
        nonlocal completed_count, failover_count
        ch = job["channel"]
        item_id = job["item_id"]
        rep = job["repeat_index"]
        payload = {"model": "jev-latest", **job["payload_data"]}
        payload_bytes = canonical_json_bytes(payload)
        payload_sha256 = hashlib.sha256(payload_bytes).hexdigest()
        prompt_sha256 = job["template_row"].get("prompt_sha256", "")

        timestamp = datetime.now(timezone.utc).isoformat()
        
        # Primary attempt on assigned channel
        resp_json, http_status, latency_ms, attempts, error_msg = execute_single_request(
            channel=ch,
            payload=payload,
            api_key=api_keys[ch],
            timeout=15.0,
            max_retries=2,
            all_secret_keys=all_secrets,
        )
        status, choice, reported_conf, probs, model_ret, in_tok, out_tok, req_id = parse_response(
            resp_json, http_status, error_msg
        )

        used_channel = ch
        # Auto-failover to TypeSafe Direct if primary failed or rate-limited
        if status != "ok" or not choice:
            if ch != "typesafe":
                with lock:
                    failover_count += 1
                # print(f"  [FAILOVER] {item_id} on {ch} failed ({error_msg or http_status}). Retrying with typesafe...")
                t_resp_json, t_http_status, t_latency_ms, t_attempts, t_error_msg = execute_single_request(
                    channel="typesafe",
                    payload=payload,
                    api_key=api_keys["typesafe"],
                    timeout=15.0,
                    max_retries=3,
                    all_secret_keys=all_secrets,
                )
                t_status, t_choice, t_reported_conf, t_probs, t_model_ret, t_in_tok, t_out_tok, t_req_id = parse_response(
                    t_resp_json, t_http_status, t_error_msg
                )
                if t_status == "ok" and t_choice:
                    resp_json = t_resp_json
                    http_status = t_http_status
                    latency_ms = t_latency_ms
                    attempts += t_attempts
                    error_msg = ""
                    status = t_status
                    choice = t_choice
                    reported_conf = t_reported_conf
                    probs = t_probs
                    model_ret = t_model_ret
                    in_tok = t_in_tok
                    out_tok = t_out_tok
                    req_id = t_req_id
                    used_channel = "typesafe"

        raw_json_str = json.dumps(resp_json, ensure_ascii=False) if resp_json else ""
        raw_json_str = redact_secrets(raw_json_str, all_secrets)

        row = {
            "run_id": "evaluation_step_400",
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
            "provider": used_channel,
            "model_requested": "jev-latest",
            "model_returned": model_ret or "jev-latest",
            "prompt_mode": "native_choice",
            "settings_json": json.dumps({"timeout": 15.0, "max_retries": 3}),
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

        gold = answer_keys.get(item_id, {}).get("gold_option") or answer_keys.get(item_id, {}).get("correct_option", "")
        is_corr = (choice == gold) if gold else False
        corr_str = "✓" if is_corr else f"✗ (gold={gold})"

        with lock:
            completed_count += 1
            new_results.append((row, is_corr, gold))
            if completed_count % 50 == 0 or completed_count == len(target_batch):
                print(f"Progress: [{completed_count}/{len(target_batch)}] completed | failovers to typesafe: {failover_count}")

        return row

    print(f"\nStarting thread pool with 6 workers (2 per channel)...")
    t0 = time.perf_counter()
    with concurrent.futures.ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(worker, job) for job in jobs]
        concurrent.futures.wait(futures)
    elapsed_total = time.perf_counter() - t0
    print(f"Completed 400 requests in {elapsed_total:.1f}s ({elapsed_total/400*1000:.1f}ms avg/item)")

    # 7. Sort new results back into original order
    item_order = {job["item_id"]: i for i, job in enumerate(jobs)}
    new_results.sort(key=lambda x: item_order[x[0]["item_id"]])

    # 8. Check statistics of new batch
    batch_rows = [r[0] for r in new_results]
    batch_valid = [r for r in batch_rows if r["status"] == "ok" and r["selected_option"]]
    batch_correct = sum(1 for r in new_results if r[1])
    batch_acc = (batch_correct / len(new_results)) * 100.0 if new_results else 0.0

    print("\n" + "=" * 65)
    print("             BATCH 3 RESULTS (400 ITEMS)")
    print("=" * 65)
    print(f"Batch Items: {len(new_results)} | Valid: {len(batch_valid)} | Errors: {len(new_results) - len(batch_valid)}")
    print(f"Batch Accuracy: {batch_acc:.1f}% ({batch_correct}/{len(new_results)})")
    print(f"Failovers to TypeSafe: {failover_count}")
    print("=" * 65)

    # 9. Save standalone batch files
    # A. Evaluation CSV (schema matching results_schema.csv)
    batch_eval_path = COMBINED_DIR / "additional_400_eval.csv"
    with batch_eval_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "run_id", "item_id", "repeat_index", "selected_option",
            "probability_1", "probability_2", "probability_3", "probability_4", "probability_5",
            "reported_confidence", "status", "provider", "model_requested", "model_returned",
            "latency_ms", "http_status"
        ])
        writer.writeheader()
        for r, _, _ in new_results:
            writer.writerow({k: r[k] for k in writer.fieldnames})
    print(f"Saved standalone batch CSV: {batch_eval_path}")

    # B. Full CSV
    batch_full_path = COMBINED_DIR / "additional_400_full.csv"
    with batch_full_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        for r, _, _ in new_results:
            writer.writerow(r)
    print(f"Saved standalone full CSV: {batch_full_path}")

    # C. Compact Batch CSV
    batch_compact_path = COMBINED_DIR / "batch_3_new_400.csv"
    with batch_compact_path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["item_id", "provider", "choice", "gold", "correct", "confidence", "prob_1", "prob_2", "prob_3", "prob_4", "prob_5", "status"])
        for r, is_corr, gold in new_results:
            writer.writerow([
                r["item_id"], r["provider"], r["selected_option"], gold, is_corr,
                r["reported_confidence"], r["probability_1"], r["probability_2"],
                r["probability_3"], r["probability_4"], r["probability_5"], r["status"]
            ])
    print(f"Saved compact batch CSV: {batch_compact_path}")

    # 10. Accumulate into master files (600 + 400 = 1,000 items)
    all_combined_rows = master_rows + batch_rows
    # Ensure no duplicates
    seen = set()
    deduped_rows = []
    for r in all_combined_rows:
        if r["item_id"] not in seen:
            seen.add(r["item_id"])
            deduped_rows.append(r)

    print(f"\nAccumulating master dataset to {len(deduped_rows)} items...")
    with master_csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        writer.writeheader()
        writer.writerows(deduped_rows)
    print(f"Updated master CSV: {master_csv_path}")

    master_json_path = COMBINED_DIR / "results_completed.json"
    with master_json_path.open("w", encoding="utf-8") as f:
        json.dump(deduped_rows, f, indent=2, ensure_ascii=False)
    print(f"Updated master JSON: {master_json_path}")

    # Calculate cumulative accuracy
    cum_correct = 0
    cum_total = 0
    for r in deduped_rows:
        iid = r["item_id"]
        if iid in answer_keys:
            gold = answer_keys[iid].get("gold_option") or answer_keys[iid].get("correct_option")
            if gold:
                cum_total += 1
                if r["selected_option"] == gold:
                    cum_correct += 1

    cum_acc = (cum_correct / cum_total) * 100.0 if cum_total else 0.0
    print("\n" + "=" * 65)
    print("             CUMULATIVE DATASET (1,000 ITEMS)")
    print("=" * 65)
    print(f"Total Unique Items: {len(deduped_rows)}")
    print(f"Cumulative Accuracy: {cum_acc:.1f}% ({cum_correct}/{cum_total})")
    print("=" * 65)

    # 11. Create updated package zip
    zip_path = COMBINED_DIR / "results_1000_package.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(master_csv_path, arcname="results_completed.csv")
        zf.write(master_json_path, arcname="results_completed.json")
        zf.write(batch_eval_path, arcname="additional_400_eval.csv")
        zf.write(batch_compact_path, arcname="batch_3_new_400.csv")
    print(f"Created clean 1,000-decision ZIP package: {zip_path}\n")

if __name__ == "__main__":
    main()
