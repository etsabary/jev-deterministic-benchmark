# JEV Deterministic Decision Benchmark
## JEV-DD-1.0 · 22 September 2026

A 3,180-item, five-choice English benchmark prepared for Eldad's evaluation of JEV. It measures a broad profile of observable decision performance: logical inference, constraint integration, state updates, rule application, planning, information sufficiency, and sensitivity to changes in presentation and evidence.

Every model-facing question is plain text, has exactly five numbered outcomes, and is answerable from its stated facts and rules. The answer options do not supply worked solutions. All inference results in the supplied results template are blank. **No JEV inference was performed in creating this package.**

## Start here

Read **RUN_PROTOCOL.md** before running the model. The shortest operational path is:

```bash
python3 validate_benchmark.py
python3 software_self_test.py
python3 prepare_run.py --plan smoke --model YOUR_JEV_MODEL_ID --run-id smoke_01 --out run_smoke
```

The preparation utility creates 100 model-only request payloads and a matching results template. It does not make network calls. Your runner submits **only the `payload` object** from each JSONL record. Log the chosen option, all five probabilities, reported confidence, model identifier, and failures in the prepared results template.

After checking the integration, freeze the request format and use the evaluation plan:

```bash
python3 prepare_run.py --plan evaluation --model YOUR_JEV_MODEL_ID --run-id evaluation_01 --out run_evaluation
```

Once your runner has saved responses:

```bash
python3 analyze_results.py run_evaluation/results_completed.csv --run-id evaluation_01 --out analysis
```

Python 3.10 or newer is required. The utilities use the Python standard library; there are no package installations, embedded credentials, inference calls, or external services in the supplied code.

## Contents

| File | Purpose |
|---|---|
| `questions.csv` | All 3,180 model-input records; no answer keys or diagnostic labels. |
| `questions.jsonl` | The same input records, one JSON object per line. |
| `jev_requests.jsonl` | Native Choice request bodies, with external item IDs; add your actual model identifier. |
| `smoke_test_100.csv` | One development item per family and load level. |
| `SAMPLE_QUESTIONS.md` | Twelve development examples for human inspection, with a separate private answer section. |
| `results_template.csv` | Blank response log covering the complete bank. |
| `results_schema.csv` | Definitions, required fields, units, and response mappings. |
| `run_plan.csv` | Reproducibly shuffled plans for smoke, development, evaluation, full, and repeatability runs. |
| `families.csv` | The 25 families and the intended meaning of their four levels. |
| `answer_key_PRIVATE.csv` | Correct outcomes, canonical option mappings, explanations, and per-option checks. Keep out of inference requests. |
| `metadata_PRIVATE.csv` | Family, level, split, variant relationship, task parameters, and content hash. Keep out of inference requests. |
| `specifications_PRIVATE.jsonl` | The formal problem instances used by the solvers and renderers. |
| `contrast_edits_PRIVATE.csv` | The single changed component for each controlled contrast. |
| `RUN_PROTOCOL.md` | Integration, run order, controls, and response logging. |
| `ANALYSIS_GUIDE.md` | Metrics, diagnostic comparisons, and interpretation limits. |
| `prepare_run.py` | Selects a run plan and builds request and response files; no API calls. |
| `analyze_results.py` | Scores returned results and produces diagnostic CSV reports. |
| `benchmark_engine.py`, `build_benchmark.py` | Reproducible generation and exact answer computation. |
| `validate_benchmark.py` | Recomputes and checks every key and structural invariant. |
| `software_self_test.py` | Checks the analyzer against explicitly synthetic responses in a temporary directory. |
| `manifest.json`, `validation_report.json`, `analyzer_self_test_report.json` | Version, counts, and checks performed. |
| `sources.csv` | Primary API and methodological references; these are not source question banks. |
| `SHA256SUMS.txt` | File integrity checks for the delivered package. |

## Bank structure

| Part | Items | Role |
|---|---:|---|
| Core cases | 2,000 | 25 families, four engineered load levels, 20 instances per family and level. |
| Meaning-preserving variants | 1,000 | Ten variants of each of 100 core anchors. |
| Changed-evidence contrasts | 100 | One controlled task edit per anchor, with a different correct outcome. |
| Candidate-evaluation probes | 80 | Five local checks for each of 16 parent puzzles. |
| **Total** | **3,180** | The parts support different analyses and should not be pooled as independent core cases. |

The core bank contains 400 development items and 1,600 held-out evaluation items. The 100-question smoke test is a subset of development. All anchors and their variants, contrasts, and probes belong to evaluation. An optional repeatability plan adds 200 calls, giving three identical presentations of each of the 100 anchors when combined with the initial evaluation run.

Correct positions are exactly balanced across the complete core bank: 400 at each position, including four at every position within each 20-item family-level group. The 16-item held-out groups have three or four at each position. Positions are also balanced overall in each split.

## Scope and caution

This is a first-version diagnostic bank, not an established standardized test or an exhaustive inventory of all possible decision-making. The four levels describe intended task load, not human school grades or empirically validated difficulty. It contains generated finite problems, not real deployment traffic, open-ended intelligence tests, or mathematical examination questions.

Formal answer keys have been checked for all items. The primary solvers and English renderers share a specification; that is not an independent human audit of every sentence. Distinct instances still share templates. Read the interpretation limits in ANALYSIS_GUIDE.md before drawing conclusions about general intelligence, human equivalence, or hidden model mechanisms.

Checksums describe the package as delivered. Rebuilding the bank or rerunning validation may update timing fields in the reports, so check original integrity before running those utilities.
