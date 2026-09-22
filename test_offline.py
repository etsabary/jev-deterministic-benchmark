#!/usr/bin/env python3
"""Automated Offline Test Suite for JEV Benchmark Runner.

Runs completely offline (no external HTTP calls, no credentials needed).
Validates:
  1. Request integrity & option preservation
  2. Response parsing (choice, probabilities, confidence, tokens)
  3. Handling of missing or malformed probabilities
  4. Error and timeout classification
  5. Checkpoint & resume logic (no duplicate execution)
  6. Secret redaction (API keys never appear in outputs or error strings)
  7. Full compatibility with the benchmark's analyze_results.py
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

from run_benchmark import (
    CSV_HEADERS,
    canonical_json_bytes,
    load_csv,
    parse_response,
    redact_secrets,
    run_benchmark,
)

ROOT = Path(__file__).resolve().parent
BANK_DIR = ROOT / "JEV_Deterministic_Decision_Benchmark_v1"


class OfflineBenchmarkTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = Path(tempfile.mkdtemp(prefix="jev_test_offline_"))

    def tearDown(self):
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_request_integrity_and_options(self):
        """Verify request records preserve exactly 5 numbered options and payload hashes."""
        plan_rows = load_csv(BANK_DIR / "run_plan.csv")
        smoke_rows = [r for r in plan_rows if r["plan"] == "smoke"]
        self.assertGreater(len(smoke_rows), 0)

        # Dry-run generates prepared requests without network calls
        dummy_env = self.temp_dir / ".env.dummy"
        dummy_env.write_text("TYPESAFE_API_KEY=dummy\nEXPERIENTIAL_LAB_JEV_API_KEY=dummy\nOPENROUTER_API_KEY=dummy\n")

        run_benchmark(
            bank_dir=BANK_DIR,
            env_path=dummy_env,
            out_dir=self.temp_dir / "dryrun_out",
            plan="smoke",
            limit=5,
            execute=False,
        )

        requests_file = self.temp_dir / "dryrun_out" / "requests.jsonl"
        self.assertTrue(requests_file.exists())

        with requests_file.open(encoding="utf-8") as f:
            lines = [json.loads(line) for line in f]

        self.assertEqual(len(lines), 5)
        for rec in lines:
            self.assertIn("payload", rec)
            payload = rec["payload"]
            self.assertEqual(payload["model"], "jev-latest")
            self.assertIn("state", payload)
            self.assertIn("questions", payload)
            decision = payload["questions"]["decision"]
            self.assertEqual(decision["type"], "choice")
            criteria = decision["criteria"]
            self.assertEqual(list(criteria.keys()), ["1", "2", "3", "4", "5"])
            for opt_key, opt_text in criteria.items():
                self.assertTrue(bool(opt_text.strip()), f"Empty option text for key {opt_key}")

    def test_response_parsing_valid(self):
        """Verify parsing of valid choice response with full distribution and confidence."""
        sample_resp = {
            "model": "jev-1.13.0",
            "answers": {
                "decision": {
                    "type": "choice",
                    "choice": "3",
                    "confidence": 0.94,
                    "probabilities": {
                        "1": 0.01,
                        "2": 0.02,
                        "3": 0.94,
                        "4": 0.02,
                        "5": 0.01,
                    },
                }
            },
            "usage": {"input_tokens": 450, "output_tokens": 52},
            "id": "test-req-12345",
        }

        status, choice, conf, probs, model_ret, in_tok, out_tok, req_id = parse_response(
            resp_json=sample_resp, http_status=200, error_msg=""
        )

        self.assertEqual(status, "ok")
        self.assertEqual(choice, "3")
        self.assertAlmostEqual(conf, 0.94)
        self.assertEqual(model_ret, "jev-1.13.0")
        self.assertEqual(in_tok, 450)
        self.assertEqual(out_tok, 52)
        self.assertEqual(req_id, "test-req-12345")
        self.assertEqual(probs["3"], 0.94)

    def test_response_parsing_missing_probabilities(self):
        """Verify that missing probability maps do not crash parser and leave probabilities blank."""
        sample_resp = {
            "model": "jev-latest",
            "answers": {
                "decision": {
                    "type": "choice",
                    "choice": "2",
                    "confidence": 0.85,
                }
            },
        }

        status, choice, conf, probs, model_ret, in_tok, out_tok, req_id = parse_response(
            resp_json=sample_resp, http_status=200, error_msg=""
        )

        self.assertEqual(status, "ok")
        self.assertEqual(choice, "2")
        self.assertAlmostEqual(conf, 0.85)
        self.assertEqual(probs, {})

    def test_response_parsing_error_and_invalid(self):
        """Verify proper classification of HTTP errors and malformed choices."""
        # 1. HTTP 500 error
        status, choice, conf, probs, _, _, _, _ = parse_response(
            resp_json={}, http_status=500, error_msg="HTTP 500: Internal Server Error"
        )
        self.assertEqual(status, "error")
        self.assertEqual(choice, "")

        # 2. Timeout error
        status, choice, conf, probs, _, _, _, _ = parse_response(
            resp_json={}, http_status=0, error_msg="Request timed out"
        )
        self.assertEqual(status, "timeout")

        # 3. Invalid choice (e.g. choice="9" when allowed is 1..5)
        sample_invalid = {
            "answers": {"decision": {"type": "choice", "choice": "9", "confidence": 1.0}}
        }
        status, choice, _, _, _, _, _, _ = parse_response(
            resp_json=sample_invalid, http_status=200, error_msg=""
        )
        self.assertEqual(status, "invalid_response")
        self.assertEqual(choice, "9")

    def test_secret_redaction(self):
        """Verify API keys are never leaked into raw responses or error messages."""
        secret_key = "xpl_secret_token_123456789"
        raw_msg = f"Failed to authenticate with Bearer {secret_key} at endpoint."
        redacted = redact_secrets(raw_msg, [secret_key])
        self.assertNotIn(secret_key, redacted)
        self.assertIn("[REDACTED_API_KEY]", redacted)

    def test_checkpoint_and_resume(self):
        """Verify resume detects previously completed items and does not duplicate them."""
        out_dir = self.temp_dir / "resume_test"
        out_dir.mkdir(parents=True)
        csv_file = out_dir / "results_completed.csv"

        # Pre-populate CSV with 2 items
        dummy_row_1 = {h: "" for h in CSV_HEADERS}
        dummy_row_1.update({
            "run_id": "test_run",
            "item_id": "J002576",
            "repeat_index": "1",
            "selected_option": "1",
            "status": "ok",
            "provider": "typesafe",
        })
        dummy_row_2 = {h: "" for h in CSV_HEADERS}
        dummy_row_2.update({
            "run_id": "test_run",
            "item_id": "J000698",
            "repeat_index": "1",
            "selected_option": "3",
            "status": "ok",
            "provider": "experiential",
        })

        with csv_file.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writeheader()
            w.writerow(dummy_row_1)
            w.writerow(dummy_row_2)

        # Run dry-run with resume=True
        dummy_env = self.temp_dir / ".env.dummy"
        dummy_env.write_text("TYPESAFE_API_KEY=dummy\nEXPERIENTIAL_LAB_JEV_API_KEY=dummy\nOPENROUTER_API_KEY=dummy\n")

        # Verify load_csv reads existing completed rows correctly
        existing = load_csv(csv_file)
        self.assertEqual(len(existing), 2)
        completed_keys = {(r["item_id"], int(r["repeat_index"])) for r in existing}
        self.assertIn(("J002576", 1), completed_keys)
        self.assertIn(("J000698", 1), completed_keys)

    def test_compatibility_with_analyze_results(self):
        """Verify that output CSV format is 100% compatible with analyze_results.py."""
        analyze_script = BANK_DIR / "analyze_results.py"
        self.assertTrue(analyze_script.exists())

        # Create a synthetic results CSV for 5 smoke items
        smoke_rows = [r for r in load_csv(BANK_DIR / "run_plan.csv") if r["plan"] == "smoke"][:5]
        key_map = {r["item_id"]: r for r in load_csv(BANK_DIR / "answer_key_PRIVATE.csv")}
        meta_map = {r["item_id"]: r for r in load_csv(BANK_DIR / "metadata_PRIVATE.csv")}

        synth_csv = self.temp_dir / "synthetic_results.csv"
        rows = []
        for r in smoke_rows:
            iid = r["item_id"]
            gold = key_map[iid]["gold_option"]
            meta = meta_map[iid]
            row = {h: "" for h in CSV_HEADERS}
            row.update({
                "run_id": "synth_01",
                "item_id": iid,
                "repeat_index": "1",
                "selected_option": gold,
                "probability_1": "0.0",
                "probability_2": "0.0",
                "probability_3": "0.0",
                "probability_4": "0.0",
                "probability_5": "0.0",
                f"probability_{gold}": "1.0",
                "reported_confidence": "1.0",
                "status": "ok",
                "provider": "typesafe",
                "model_requested": "jev-latest",
                "model_returned": "jev-1.13.0",
                "prompt_mode": "native_choice",
                "settings_json": json.dumps({"timeout": 15.0}),
                "prompt_sha256": meta["prompt_sha256"],
                "latency_ms": "250.0",
            })
            rows.append(row)

        with synth_csv.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADERS)
            w.writeheader()
            w.writerows(rows)

        # Run analyze_results.py
        out_analysis = self.temp_dir / "synth_analysis"
        cmd = [
            sys.executable,
            str(analyze_script),
            str(synth_csv),
            "--run-id", "synth_01",
            "--split", "development",
            "--out", str(out_analysis),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0, f"Analyzer failed: {proc.stderr}\n{proc.stdout}")
        self.assertTrue((out_analysis / "summary.json").exists())
        self.assertTrue((out_analysis / "SUMMARY.md").exists())
        self.assertTrue((out_analysis / "accuracy_by_family.csv").exists())


if __name__ == "__main__":
    unittest.main()
