# Run protocol
## JEV-DD-1.0

## 1. What the benchmark is intended to establish

The primary question is: **Which classes of deterministic decisions does this exact JEV model and request format handle reliably, and under what changes does its performance deteriorate?**

Our earlier explanation of a possible constraint-integration or working-state limitation is a hypothesis. A chosen wrong option alone cannot establish the model's internal process. This bank tests observable alternatives: failure to evaluate individual conditions, failure to combine conditions, dependence on wording or option position, stale-state errors, sensitivity to irrelevant material, and poorly calibrated certainty.

The main outcome is a profile across families and controlled comparisons. Do not reduce it to one intelligence number.

## 2. Select the run

`run_plan.csv` contains a reproducibly shuffled order for each plan. Select one plan; do not concatenate all rows of that file as though they were different questions.

| Plan | Requests | Use |
|---|---:|---|
| `smoke` | 100 | Check request mapping, response parsing, and approximate task coverage. Development only. |
| `development` | 400 | Settle the prompt format and runner configuration. Includes the smoke items. |
| `evaluation` | 2,780 | Frozen test: 1,600 core cases, 1,000 variants, 100 contrasts, 80 probes. |
| `full` | 3,180 | The complete bank. The analyzer still separates development and evaluation. |
| `repeatability` | 200 | Two additional identical-input runs per evaluation anchor; repeat indices 2 and 3. |

Start with smoke, repair integration problems, and use development if prompt tuning is needed. Freeze the model configuration and request construction before evaluation. Running smoke and then development does not create 500 distinct development cases: 100 are repeated. Retain only one designated first response per item and condition for the headline score; use higher repeat indices for extra presentations.

The full plan is an alternative convenience, not an additional independent test after the other plans. The default analyzer scores the 1,600 evaluation core cases and reports the diagnostic panels separately.

Prepare a plan without making API calls:

```bash
python3 prepare_run.py --plan smoke --model YOUR_JEV_MODEL_ID --run-id smoke_01 --out run_smoke
python3 prepare_run.py --plan evaluation --model YOUR_JEV_MODEL_ID --run-id evaluation_01 --out run_evaluation
```

For repeatability, use the same model, settings, prompt format, and run ID as evaluation:

```bash
python3 prepare_run.py --plan repeatability --model YOUR_JEV_MODEL_ID --run-id evaluation_01 --out run_repeats
```

Merge the completed evaluation and repeat CSV rows before analysis, keeping a single header. Item IDs may repeat only with a different `repeat_index`. Log provider-level retries in `attempt_count`, not as duplicate successful first responses.

## 3. What the model receives

Use an allowlist. For each question, the only semantic inputs are the shared instructions, context, question, and five options. Do not include answer keys, explanations, family names, levels, base IDs, split labels, diagnostic notes, or formal specifications.

The native Choice mapping follows TypeSafe's documentation [S1]:

```json
{
  "model": "YOUR_JEV_MODEL_ID",
  "state": "The context field from the dataset",
  "questions": {
    "decision": {
      "type": "choice",
      "instructions": "The instructions field, a blank line, then the question field",
      "criteria": {
        "1": "The option_1 field",
        "2": "The option_2 field",
        "3": "The option_3 field",
        "4": "The option_4 field",
        "5": "The option_5 field"
      }
    }
  }
}
```

`jev_requests.jsonl` already contains this mapping without the model field. `prepare_run.py` adds your model identifier and wraps each request with local logging identifiers. **Submit only the inner `payload`.** The outer fields are for your runner.

TypeSafe's documented endpoint is `https://api.typesafe.ai/v1/systemone`. Option keys and descriptions both reach the model. The request question ID is a response-mapping key. The returned choice is under `answers.decision.choice`; the probability map and confidence are alongside it [S1]. For another provider, adapt the transport to its actual documented contract while preserving this content and logging the provider and model version.

Use one independent problem state per request, or a batching facility that genuinely preserves independent request states. Do not put all benchmark problems into one shared context. Keep prior responses and answer feedback out of every request. Run the supplied benchmark as a single-shot choice test: no added external solver, generated chain of thought, search tool, or helper model. Assisted approaches can be tested as separate conditions later.

Preserve option order, including the deliberate rotations. Do not sort criteria alphabetically by their descriptions. The numbered labels must remain strings `1` through `5`. The dataset's `prompt_text` is useful for inspection or a separate text-based adapter; do not duplicate it inside the native request alongside the same context and criteria.

## 4. Freeze and record the condition

Use a versioned model snapshot when your provider makes one available. Record both `model_requested` and the actual `model_returned`. Keep provider, model snapshot, prompt mode, and explicitly supplied settings constant within a `run_id`. Give a different configuration a different run ID. Avoid silent failover to a different model.

Keep raw responses, the actual request-body hash, timestamps, and failure details. Record caching information in `settings_json` when available. Identical results may reflect deterministic inference or caching; identical-input repeatability alone cannot distinguish those explanations. API defaults or undocumented provider processing may remain unknown: record that limitation.

The supplied text uses normal Unicode punctuation and multiline fields. Read CSV with a real CSV parser and `utf-8-sig`; do not split records by physical line. JSONL is an alternative when convenient. In a spreadsheet, preserve newlines and treat IDs as text. Editing prompts in a spreadsheet changes the tested item: make a separately versioned dataset and regenerate its hashes before scoring it as a new condition.

## 5. Response fields

At minimum, complete `run_id`, `item_id`, `repeat_index`, `selected_option`, and `status`. For the full diagnostic analysis, also preserve all five option probabilities, reported confidence, provider/model identifiers, prompt mode, and timing. `results_schema.csv` documents every field.

| Field | Convention |
|---|---|
| `selected_option` | Integer 1–5. Use the returned option key, not zero-based array indexing or A–E. |
| `probability_1` through `probability_5` | Returned values in 0–1 units. Preserve precision; the full distribution should sum to one. |
| `reported_confidence` | The provider's returned 0–1 score, separately recorded. |
| `status` | `ok`, `error`, `timeout`, or `invalid_response`. |
| `latency_ms` | Observed request latency in milliseconds. Define consistently whether it includes retries. |
| `prompt_sha256` | Preserve the dataset's supplied content hash. |
| `request_payload_sha256` | Hash of the actual transmitted request body under a documented canonicalization. |
| `raw_response_json` | Original response, with no API credentials or authorization headers. |

Leave unavailable fields blank. A missing confidence or probability is not zero. Record API failure as failure, not as an arbitrary guessed option. A valid choice can still be scored when the provider omits probability data; probability analyses then have lower coverage.

The benchmark content hash uses SHA-256 over UTF-8 JSON containing `instructions`, `context`, `question`, and the five-option array, with sorted keys, no ASCII escaping, and comma/colon separators without extra spaces. It is not a hash of the HTTP request or authorization headers. The preparation tool also supplies a hash of its prepared payload; recompute the actual transmitted hash if the runner changes that payload.

## 6. Confidence and probability are separate measurements

TypeSafe describes `confidence` as a statistic derived from how concentrated the option distribution is, not as an independently measured success rate [S2]. Preserve both it and the complete probability map. The analyzer evaluates calibration using the probability assigned to the selected option and examines reported confidence separately as an error-ranking signal.

A result displayed as 100 percent confidence is an observation to test against correctness. It is not, by itself, evidence of a guaranteed answer or a particular reasoning process.

## 7. Analysis commands

```bash
# Frozen evaluation: the default split.
python3 analyze_results.py results_completed.csv --run-id evaluation_01 --out analysis

# Smoke or development only. Expect incomplete development coverage for smoke.
python3 analyze_results.py smoke_completed.csv --run-id smoke_01 --split development --out smoke_analysis

# Exploratory report using both core splits, with that choice explicitly labeled.
python3 analyze_results.py all_completed.csv --run-id full_01 --split all --out all_analysis
```

The analyzer rejects unknown item IDs, duplicate item/repeat combinations, mixed conditions, and mismatched supplied content hashes. Invalid probability distributions generate warnings and are excluded from probability metrics; a separately valid choice remains eligible for accuracy. Review `data_warnings.csv` before interpreting scores.

Return the completed result CSV together with the run manifest. Raw responses and probability precision will make the interpretation substantially more informative than a list of chosen numbers alone.

## 8. References

[S1] TypeSafe AI. *Choice*. Official documentation, checked 22 September 2026. `https://docs.typesafe.ai/primitives/choice`

[S2] TypeSafe AI. *Confidence*. Official documentation, checked 22 September 2026. `https://docs.typesafe.ai/confidence`

Additional methodological references and their role are in `sources.csv` and `ANALYSIS_GUIDE.md`.
