# Tasks: JEV Benchmark Integration & Multi-Channel Runner

- [x] **Phase 1: Environment & Credentials Research**
  - [x] Inspect `.env` for JEV endpoints and API keys.
  - [x] Identify three channels: TypeSafe Direct, Experiential Labs, OpenRouter.
  - [x] Probe all three channels live to verify endpoint reachability, request format, and model ID (`jev-latest`).

- [x] **Phase 2: Benchmark Package Analysis**
  - [x] Unzip and inspect `JEV_Deterministic_Decision_Benchmark_v1.zip`.
  - [x] Verify package integrity using `validate_benchmark.py` and `software_self_test.py`.
  - [x] Understand `prepare_run.py`, `run_plan.csv`, `results_schema.csv`, and `analyze_results.py`.

- [x] **Phase 3: Implementation of Multi-Channel Runner (`run_benchmark.py`)**
  - [x] Implement round-robin question distribution across TypeSafe, Experiential Labs, and OpenRouter.
  - [x] Implement request preparation matching TypeSafe native Choice contract (submitting only inner `payload`).
  - [x] Implement response parsing for `choice`, 5-option probabilities, reported confidence, tokens, and latency.
  - [x] Add safety dry-run mode (default; requires `--execute` for live inference).
  - [x] Add hard cap on total HTTP attempts (`--max-http-attempts`).
  - [x] Add secret redaction to prevent API keys from leaking into logs or raw responses.
  - [x] Add durable checkpoints and resume support without duplicate queries.
  - [x] Add multi-format output: `results_completed.csv`, `results_completed.json`, `results_completed.jsonl`, and per-provider CSVs.
  - [x] Add automated post-run analysis via `analyze_results.py` (`--run-analysis`).
  - [x] Add export packaging (`--export-package`).

- [x] **Phase 4: Automated Offline Testing (`test_offline.py`)**
  - [x] Test request integrity & option preservation (1..5 criteria).
  - [x] Test response parsing for valid, partial, and malformed responses.
  - [x] Test secret redaction.
  - [x] Test checkpointing and resume.
  - [x] Test full compatibility with `analyze_results.py`.

- [x] **Phase 5: Live Stepped Evaluation**
  - [x] Run 100-question smoke test (`--plan smoke --execute`): 100/100 valid (88.0%).
  - [x] Run Batch 1 (300 questions, items 101–400): 259 valid, 41 retried via TypeSafe Direct (100% completed, 80.5% overall).
  - [x] Run Batch 2 (200 questions, items 401–600): 200/200 valid (80.5% batch accuracy).
  - [x] Run Batch 3 (400 questions, items 601–1,000): 400/400 valid (83.5% batch accuracy, 28 TypeSafe failovers).
  - [x] Accumulate master dataset to 1,000 items (`runs/combined_400/results_completed.csv`, 81.7% accuracy).
  - [x] Establish and maintain cumulative diagnostic log ([`DIAGNOSTIC_ANALYSIS.md`](file:///Users/etsabary/Documents/repos/benchmarks/jev/DIAGNOSTIC_ANALYSIS.md)).
  - [x] Generate updated vector graphics and interactive dashboard ([`jev_benchmark_visualizations.html`](file:///Users/etsabary/.gemini/antigravity/brain/de3bf14b-f9bd-47ac-b919-eac2ca8003b7/jev_benchmark_visualizations.html)).
  - [ ] Run remaining evaluation batches (1,780 items remaining out of 2,780).
  - [ ] Export final package upon completion.


