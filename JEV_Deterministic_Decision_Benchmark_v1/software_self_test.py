#!/usr/bin/env python3
"""Test the analyzer with synthetic responses, never with JEV or an API.
All temporary synthetic result files are automatically deleted.
"""
from __future__ import annotations
import contextlib
import csv
import io
import json
import tempfile
from pathlib import Path
from analyze_results import analyze, readcsv


def main() -> None:
    bank = Path(__file__).resolve().parent
    keys = {r['item_id']: r for r in readcsv(bank / 'answer_key_PRIVATE.csv')}
    template = readcsv(bank / 'results_template.csv')
    fields = list(template[0])
    with tempfile.TemporaryDirectory(prefix='jev_software_self_test_') as work:
        test = Path(work)

        def run(name: str, rows: list[dict], split: str = 'evaluation') -> dict:
            path = test / (name + '.csv')
            with path.open('w', encoding='utf-8-sig', newline='') as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows(rows)
            with contextlib.redirect_stdout(io.StringIO()):
                return analyze(path, bank, test / name, run_id=name, split=split)

        oracle = []
        for row in template:
            r = row.copy()
            gold = int(keys[r['item_id']]['gold_option'])
            r.update(run_id='oracle', selected_option=gold, reported_confidence=1,
                     status='ok', repeat_index=1, provider='SOFTWARE_SELF_TEST_NOT_JEV',
                     model_returned='synthetic-oracle')
            for i in range(1, 6):
                r[f'probability_{i}'] = int(i == gold)
            oracle.append(r)
        result = run('oracle', oracle)
        assert result['primary_core']['valid'] == 1600
        assert result['primary_core']['accuracy_valid'] == 1
        assert result['probability_ece_10bins'] == 0
        assert result['primary_core']['brier_multiclass_sum'] == 0
        assert result['complete_rotation_panels'] == 100
        assert result['rotation_all_five_correct_rate'] == 1
        assert result['contrast_both_correct_rate'] == 1
        assert result['contrast_pair_count'] == 100
        components = readcsv(test / 'oracle' / 'component_check_profile.csv')
        assert len(components) == 16
        assert all(r['all_five_candidate_checks_correct'] == 'True' for r in components)

        constant = []
        for row in oracle:
            r = row.copy()
            r.update(run_id='constant', selected_option=1, reported_confidence=0,
                     model_returned='synthetic-constant')
            for i in range(1, 6):
                r[f'probability_{i}'] = 0.2
            constant.append(r)
        result = run('constant', constant)
        assert abs(result['primary_core']['accuracy_valid'] - 0.2) < 1e-12
        assert abs(result['primary_core']['brier_multiclass_sum'] - 0.8) < 1e-10
        assert result['rotation_all_five_correct_rate'] == 0
        assert result['rotation_meaning_consistency_rate'] == 0
        assert abs(result['probability_ece_10bins']) < 1e-12

        partial = [r.copy() for r in oracle if keys[r['item_id']]['role'] == 'core'][:5]
        for r in partial:
            r['run_id'] = 'partial'
        partial[0].update(status='timeout', selected_option='', error_message='synthetic timeout')
        partial[1].update(selected_option=6)
        for i in range(1, 6):
            partial[2][f'probability_{i}'] = 0.9
        partial[3].update(reported_confidence=100)
        result = run('partial', partial, split='all')
        assert result['primary_core']['attempted'] == 5
        assert result['primary_core']['valid'] == 3
        assert result['primary_core']['correct'] == 3
        assert result['validation_warning_rows'] >= 3

        repeats = []
        for repeat in (1, 2, 3):
            r = oracle[0].copy()
            r.update(run_id='repeats', repeat_index=repeat)
            repeats.append(r)
        run('repeats', repeats)
        report = readcsv(test / 'repeats' / 'repeatability.csv')
        assert len(report) == 1 and report[0]['repeats'] == '3'
        assert report[0]['same_meaning_all_repeats'] == 'True'

        rejected = []
        cases = [
            ('duplicate', [oracle[0].copy(), oracle[0].copy()]),
            ('hash_mismatch', [{**oracle[0], 'prompt_sha256': 'wrong'}]),
            ('unknown_item', [{**oracle[0], 'item_id': 'NO_SUCH_ITEM'}]),
            ('mixed_models', [oracle[0].copy(), {**oracle[1], 'model_returned': 'different'}]),
        ]
        for name, rows in cases:
            for r in rows:
                r['run_id'] = name
            try:
                run(name, rows)
            except ValueError:
                rejected.append(name)
        assert len(rejected) == len(cases)

    report = {
        'software_self_tests_only': True,
        'actual_jev_calls': 0,
        'tests': ['perfect synthetic oracle', 'uniform probabilities with constant choice',
                  'invalid and failed responses', 'identical-input repeats',
                  'duplicate rejection', 'prompt hash rejection', 'unknown item rejection',
                  'mixed-model rejection'],
        'passed': True,
    }
    (bank / 'analyzer_self_test_report.json').write_text(
        json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
