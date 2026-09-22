#!/usr/bin/env python3
"""Verify the complete bank without contacting any AI provider."""
from __future__ import annotations
import argparse,csv,hashlib,itertools as it,json,random,sys,time
from collections import Counter,defaultdict,deque
from pathlib import Path
from benchmark_engine import *
from build_benchmark import INPUT_FIELDS,question_data,sha


def readcsv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def forward_plan_distance(s):
    """Independent forward search, unlike the engine's reverse-state search."""
    start=s['initial']; q=deque([(start,0,None)]); seen={(start,None)}; found=[]; best=None
    while q:
        st,depth,first=q.popleft()
        if best is not None and depth>best: break
        if all(((st>>i)&1)==v for i,v in s['goal']): best=depth; found.append(first); continue
        for a,act in enumerate(s['actions']):
            if not applicable(st,act): continue
            nxt=apply_action(st,act); fi=a if first is None else first; pair=(nxt,fi)
            if pair not in seen: seen.add(pair); q.append((nxt,depth+1,fi))
    return best,{x for x in found if x is not None}


def validate(folder):
    folder=Path(folder); start=time.time(); problems=readcsv(folder/'questions.csv'); keys=readcsv(folder/'answer_key_PRIVATE.csv'); metas=readcsv(folder/'metadata_PRIVATE.csv')
    inputs={x['item_id']:x for x in problems}; key={x['item_id']:x for x in keys}; meta={x['item_id']:x for x in metas}
    specs=[json.loads(x) for x in (folder/'specifications_PRIVATE.jsonl').read_text().splitlines()]; smap={x['item_id']:x for x in specs}
    assert len(inputs)==len(problems)==len(key)==len(meta)==len(specs)
    assert set(inputs)==set(key)==set(meta)==set(smap)
    assert set(problems[0])==set(INPUT_FIELDS), 'Unexpected potentially private input field'
    hashes=[]; groups=defaultdict(list); aux=Counter(); changed_components=[]
    for record in specs:
        item=record['item_id']; s=record['spec']; k=key[item]; order=record['option_order']; variant=record['variant']
        assert sorted(order)==list(range(5))
        gold=get_gold(s); pos=order.index(gold)+1
        assert int(k['gold_option'])==pos and k['gold_canonical']==f'c{gold+1}'
        payload,prompt,mapping=question_data(s,variant,order,record['variant_seed'])
        assert len(set(payload['options']))==5
        actual=inputs[item]
        assert actual['prompt_text']==prompt and actual['prompt_sha256']==sha(payload)
        assert actual['context']==payload['context'] and actual['question']==payload['question']
        assert [actual[f'option_{i}'] for i in range(1,6)]==payload['options']
        assert k['gold_text']==payload['options'][pos-1]
        hashes.append(actual['prompt_sha256']); groups[record['base_id']].append(record)
        if k['role'] in ['core','contrast']:
            # Cross-check selected families using a second algorithm.
            if s['family']=='F18' and k['role']=='core':
                natural=circuit(clone(s,forced_node=-1))
                assert s['forced_value']!=natural[s['forced_node']]
                assert circuit(s)[-3:]!=natural[-3:]
                assert natural[-3:] in s['candidate_worlds']
                aux['causal_override_changes_output_and_includes_no_override_foil']+=1
            elif s['family']=='F20':
                distance,first=forward_plan_distance(s); reverse_distance,reverse_first,_=plans(s)
                assert distance==reverse_distance and first==set(reverse_first)=={gold}
                aux['planning_forward_vs_reverse']+=1
            elif s['family']=='F12':
                # Invert every swap to check which original box fed each final box.
                finalbox=gold
                for a,b in reversed(s['ops']):
                    if finalbox==a: finalbox=b
                    elif finalbox==b: finalbox=a
                assert s['initial'][finalbox]==s['query_object']; aux['swap_forward_vs_inverse']+=1
            elif s['family'] in ['F02','F03']:
                facts=dict(s['known']); again=True
                while again:
                    old=facts.copy()
                    for a,b in s['rules']:
                        if facts.get(a)==1: facts[b]=1
                        if facts.get(b)==0: facts[a]=0
                    again=facts!=old
                target=1 if s['family']=='F02' else 0
                assert [i for i in range(5) if facts.get(i)==target]==[gold]
                aux['boolean_enumeration_vs_propagation']+=1
            elif s['family']=='F14':
                # Enumerate interleavings of four endpoints and marker events.
                # Only the explicitly stated strict temporal chain survives.
                rank={event:j for j,event in enumerate(s['order'])}
                a,b=(2,0) if s['reverse_query'] else (0,2)
                before=rank[a+1]<rank[b]; after=rank[b+1]<rank[a]
                inside=rank[b]<rank[a] and rank[a+1]<rank[b+1]
                contains=rank[a]<rank[b] and rank[b+1]<rank[a+1]
                vals=[before,after,not any([before,after,inside,contains]),inside,contains]
                assert sum(vals)==1 and vals[gold]; aux['interval_relation_partition']+=1
        if variant=='contrast':
            base=smap[record['base_id']]['spec']
            assert get_gold(base)!=gold
            # A controlled edit changes exactly one top-level task component;
            # edits of one clue, record field, command, or observation are checked below.
            changed=[f for f in base if base[f]!=s[f]]
            assert len(changed)==1,(item,changed)
            field=changed[0]; old,new=base[field],s[field]
            if isinstance(old,list):
                assert len(old)==len(new)
                assert sum(a!=b for a,b in zip(old,new))==1,(item,field)
            elif field=='initial' and s['family']=='F20':
                assert (old^new).bit_count()==1
            changed_components.append({'item_id':item,'base_id':record['base_id'],'changed_component':field})
    assert len(hashes)==len(set(hashes)), 'Duplicate complete model-visible item'
    for base,rs in groups.items():
        b=smap[base]; expected=key[base]['gold_canonical']
        rotations=[r for r in rs if r['variant']=='base' or r['variant'].startswith('option_rotation_')]
        if len(rotations)>1:
            assert len(rotations)==5
            assert {int(key[r['item_id']]['gold_option']) for r in rotations}==set(range(1,6))
        for record in rs:
            role=key[record['item_id']]['role']
            if role=='robustness':
                assert record['spec']==b['spec']
                assert key[record['item_id']]['gold_canonical']==expected
    core=[x for x in keys if x['role']=='core']; strata=defaultdict(Counter)
    for x in core: strata[(x['family_id'],x['level'])][int(x['gold_option'])]+=1
    for counts in strata.values(): assert len(counts)==5 and len(set(counts.values()))==1
    # Each split is also balanced as closely as its size permits. Sixteen
    # evaluation instances give three or four correct answers per position.
    for split in ['development','evaluation']:
        split_groups=defaultdict(Counter)
        for x in core:
            if x['split']==split: split_groups[(x['family_id'],x['level'])][int(x['gold_option'])]+=1
        for counts in split_groups.values():
            values=[counts[i] for i in range(1,6)]
            assert max(values)-min(values)<=1
    report={'benchmark_version':VERSION,'total_items_verified':len(specs),'core_items_verified':len(core),'unique_prompts':len(set(hashes)),
            'exactly_five_distinct_options_each':True,'gold_keys_recomputed':True,'payload_hashes_verified':True,
            'all_100_contrasts_changed_one_task_component':len(changed_components)==100,'all_contrast_answers_change':True,
            'core_keys_balanced_within_each_family_and_level':True,'each_split_position_balanced_as_closely_as_possible_within_family_and_level':True,'all_five_answer_positions_covered_per_rotation_anchor':True,
            'auxiliary_cross_checks':dict(aux),'runtime_seconds':round(time.time()-start,2),
            'limitations':['Natural-language renderers and primary solvers share the same specification; this is not an independent human audit of every sentence.',
                           'Engineered levels are not empirically calibrated difficulty scores.','No JEV inference has been run by this validation.']}
    (folder/'validation_report.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    with (folder/'contrast_edits_PRIVATE.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['item_id','base_id','changed_component']); w.writeheader(); w.writerows(changed_components)
    print(json.dumps(report,indent=2)); return report

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('folder',nargs='?',default=str(Path(__file__).parent)); args=p.parse_args(); validate(args.folder)
