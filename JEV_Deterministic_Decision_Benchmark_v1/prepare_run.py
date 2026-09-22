#!/usr/bin/env python3
"""Prepare model-only native Choice requests and a matching results template.
This utility makes no network calls and spends no inference credits.
Example:
  python3 prepare_run.py --plan smoke --model YOUR_SNAPSHOT --run-id smoke_01 --out run_smoke
Send only each record's payload to the API, never the outer logging fields.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def load_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def prepare(bank: Path, out: Path, plan: str, model: str, run_id: str, provider: str) -> int:
    if not model.strip() or not run_id.strip():
        raise ValueError('A nonempty model identifier and run_id are required.')
    jobs = [r for r in load_csv(bank / 'run_plan.csv') if r['plan'] == plan]
    jobs.sort(key=lambda r: int(r['order']))
    if not jobs:
        raise ValueError(f'Unknown or empty plan: {plan}')
    rows = load_csv(bank / 'results_template.csv')
    headers = list(rows[0])
    templates = {r['item_id']: r for r in rows}
    packets = {}
    with (bank / 'jev_requests.jsonl').open(encoding='utf-8') as f:
        for line in f:
            record = json.loads(line)
            packets[record['item_id']] = record['payload']
    manifest = json.loads((bank / 'manifest.json').read_text(encoding='utf-8'))
    out.mkdir(parents=True, exist_ok=True)
    names = ['requests.jsonl', 'results_template.csv', 'run_manifest.json']
    if any((out / name).exists() for name in names):
        raise FileExistsError('Output already contains run files. Use a new output directory.')
    result_rows = []
    with (out / 'requests.jsonl').open('w', encoding='utf-8') as f:
        for job in jobs:
            item = job['item_id']
            payload = {'model': model, **packets[item]}
            canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True,
                                   separators=(',', ':')).encode('utf-8')
            row = templates[item].copy()
            row.update(run_id=run_id, repeat_index=job['repeat_index'], provider=provider,
                       model_requested=model, prompt_mode='native_choice')
            result_rows.append(row)
            wrapper = {'run_id': run_id, 'item_id': item,
                       'repeat_index': int(job['repeat_index']),
                       'prompt_sha256': row['prompt_sha256'],
                       'prepared_payload_sha256': hashlib.sha256(canonical).hexdigest(),
                       'payload': payload}
            f.write(json.dumps(wrapper, ensure_ascii=False) + '\n')
    with (out / 'results_template.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(result_rows)
    record = {'benchmark_version': manifest['benchmark_version'], 'plan': plan,
              'run_id': run_id, 'model_requested': model, 'provider': provider,
              'prompt_mode': 'native_choice', 'requests_prepared': len(jobs),
              'actual_api_calls': 0,
              'prepared_at_utc': datetime.now(timezone.utc).isoformat(),
              'instructions': 'Send only payload. Preserve option IDs and all returned probabilities. Log the actual transmitted payload hash if the runner changes this prepared payload.'}
    (out / 'run_manifest.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(record, indent=2))
    return len(jobs)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--bank', type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--plan', choices=['smoke', 'development', 'evaluation', 'full', 'repeatability'], required=True)
    parser.add_argument('--model', required=True)
    parser.add_argument('--run-id', required=True)
    parser.add_argument('--provider', default='')
    args = parser.parse_args()
    try:
        prepare(args.bank, args.out, args.plan, args.model, args.run_id, args.provider)
    except (ValueError, KeyError, OSError) as exc:
        parser.exit(2, str(exc) + '\n')
