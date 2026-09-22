#!/usr/bin/env python3
"""Rebuild the CSV/JSONL benchmark. No external dependencies; does not call JEV."""
from __future__ import annotations
import argparse,copy,csv,hashlib,itertools as it,json,random,re,time
from collections import Counter
from pathlib import Path
from benchmark_engine import *

INPUT_FIELDS=['item_id','instructions','context','question']+[f'option_{i}' for i in range(1,6)]+['prompt_text','prompt_sha256']
RESULT_FIELDS=['run_id','item_id','repeat_index','selected_option']+[f'probability_{i}' for i in range(1,6)]+[
    'reported_confidence','status','provider','model_requested','model_returned','prompt_mode','settings_json',
    'timestamp_utc','latency_ms','input_tokens','output_tokens','http_status','attempt_count','api_request_id',
    'prompt_sha256','request_payload_sha256','error_message','raw_response_json']
RENAME_PEOPLE=['Arin','Bela','Cleo','Dara','Emil','Freya','Galen','Hugo','Ines','Jules','Kira','Leon','Mara','Nico','Orla','Petra','Remy','Sami','Tara','Vito','Willa','Zora']
RENAME_PLACES=['Alder','Aspen','Basil','Coral','Delta','Flint','Haven','Linden','Moss','Opal','Pearl','Quartz','Sage','Slate','Vale','Yew','Bramble','Clover','Wattle','Thyme']
NOISE_SHORT=('Unrelated background note: The nearby community centre recently repainted its entrance. '
             'A notice on the wall describes a pottery exhibition, and a visitor has left a folded umbrella by the door. '
             'These details do not add or change any fact or rule in the problem.')
NOISE_LONG=('Unrelated background material follows. It describes a different building and does not add or change any rule, event, relationship, observation, or record in the problem.\n\n'
    'The community centre has a broad entrance with a woven mat and a display of drawings from a local workshop. '
    'The drawings show gardens, bicycles, clouds, and ordinary household objects. A volunteer has arranged them at different heights so visitors can see them comfortably. '
    'Near the entrance, a small cabinet contains paper, spare pencils, tape, and a collection of postcards. The postcards were donated after an exhibition and are kept for future craft activities.\n\n'
    'A notice describes a reading group that discusses short stories. Participants bring their own notebooks, share observations about the writing, and sometimes read a favourite passage aloud. '
    'The description emphasizes attentive listening and an open conversation about different interpretations. It also explains that visitors may simply listen during their first meeting. '
    'The reading group has no connection to the people, objects, or rules in the decision problem.\n\n'
    'The rear corridor leads to a courtyard with benches and large planters. The plants include herbs and climbing vines. A caretaker stores a watering can nearby and checks the soil before watering. '
    'The courtyard is used for informal conversations when the weather is pleasant. A mural on the outer wall depicts an imaginary landscape with winding paths and a distant shoreline. '
    'Its shapes were chosen by the artists for visual balance.\n\n'
    'Another display describes how a fabric banner was made. Several pieces were cut, arranged, stitched, and attached to a backing. '
    'The makers experimented with textures and kept small samples of the materials. The display includes photographs of the unfinished banner and a paragraph about the workshop atmosphere. '
    'These photographs and descriptions are background documentation, not additional clues about the decision problem.\n\n'
    'A shelf beside the common room holds magazines, folded leaflets, and a guest book. Some visitors leave a few sentences about their experience. '
    'Other visitors draw a tiny picture or simply sign their name. The guest book belongs to this separate community-centre description. '
    'Nothing in it changes the authorized sources, priority rules, movement steps, assignments, or observations stated for the problem. '
    'End of unrelated background material.')


def csvwrite(path,rows,fields=None):
    rows=list(rows)
    if fields is None: fields=list(rows[0]) if rows else []
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields,extrasaction='raise'); w.writeheader(); w.writerows(rows)


def sha(obj):
    return hashlib.sha256(json.dumps(obj,ensure_ascii=False,sort_keys=True,separators=(',',':')).encode()).hexdigest()


def replace_all(text,mapping):
    if not mapping: return text
    pattern=r'\b(?:'+'|'.join(re.escape(x) for x in sorted(mapping,key=len,reverse=True))+r')\b'
    return re.sub(pattern,lambda m:mapping[m.group(0)],text)


def question_data(spec,variant,order,variant_seed):
    d=render(spec); r=random.Random(variant_seed); mapping={}; facts=d['facts'].copy()
    question=d['question']; opts=d['options'].copy()
    if variant=='fact_order':
        # Explicit step/time/priority labels retain their original meaning.
        r.shuffle(facts)
        if facts==d['facts'] and len(facts)>1: facts=facts[1:]+facts[:1]
    if variant=='question_rewording': question=d['question_alt']
    if variant=='expanded_options': opts=[f'The final answer is: {x}' for x in opts]
    if variant in ['noise_short','noise_long']:
        at=len(facts)//2; facts.insert(at,NOISE_SHORT if variant=='noise_short' else NOISE_LONG)
    context=d['intro']+'\n\n'+'\n'.join(facts)
    if variant=='entity_rename':
        alltext=context+' '+question+' '+' '.join(opts)
        oldp=[x for x in PEOPLE if re.search(r'\b'+re.escape(x)+r'\b',alltext)]
        oldl=[x for x in PLACES if re.search(r'\b'+re.escape(x)+r'\b',alltext)]
        mapping.update(zip(oldp,r.sample(RENAME_PEOPLE,len(oldp))))
        mapping.update(zip(oldl,r.sample(RENAME_PLACES,len(oldl))))
        assert mapping
        context=replace_all(context,mapping); question=replace_all(question,mapping); opts=[replace_all(x,mapping) for x in opts]
    displayed=[opts[i] for i in order]
    payload={'instructions':INSTRUCTIONS,'context':context,'question':question,'options':displayed}
    prompt=INSTRUCTIONS+'\n\n'+context+'\n\n'+question+'\n\n'+'\n'.join(f'{j+1}. {x}' for j,x in enumerate(displayed))
    return payload,prompt,mapping


def parameters(s):
    f=s['family']; p={'facts':len(render(s)['facts'])}
    if s.get('probe'): return {'probe_candidate_evaluation':True,'parent_family':s['parent_spec']['family']}
    if f=='F01': p['required_filter_fields']=len(s['query_values'])
    if f in ['F02','F03']: p.update(chain_length=s['chain_length'],boolean_variables=s['nvars'])
    if f=='F04': p['condition_form_level']=s['level']
    if f=='F05': p.update(quantifier_premises=len(s['premises']),finite_objects=3,properties=3)
    if f=='F06': p['max_comparison_depth']=s['level']
    if f in ['F07','F08','F11']: p.update(clues=len(s['clues']),entities=3 if f=='F11' else 5)
    if f=='F09': p.update(inscriptions=len(s['subsets']),required_true=s['required'])
    if f=='F10': p['speakers']=len(s['names'])
    if f in ['F12','F13','F15']: p['operations']=len(s['ops'])
    if f=='F14': p['temporal_markers']=s['level']-1
    if f=='F16': p['binding_depth']=len(s['roles'])
    if f=='F17': p.update(events=len(s['events']),belief_order=len(s['path']),belief_differs_from_reality=get_gold(s)!=s['events'][-1][0])
    if f=='F18': p.update(intermediate_gates=s['level'],total_gates=len(s['gates']))
    if f=='F19': p['priority_rules']=len(s['rules'])
    if f=='F20': p.update(shortest_plan=plans(s)[0],initially_allowed_actions=sum(applicable(s['initial'],a) for a in s['actions']))
    if f=='F21': p['intended_path_length']=s['level']
    if f=='F22': p['ordered_criteria']=s['ncriteria']
    if f=='F23': p['rules']=len(s['rules'])
    if f=='F24': p['records']=len(s['records'])
    if f=='F25': p['probes']=len(s['observed'])
    return p


def make_probe(parent,candidate,r):
    f=parent['family']; n=len(parent['subsets']) if f=='F09' else len(parent['statements']) if f=='F10' else len(parent['clues'])
    if f=='F09': value=sum(candidate in sub for sub in parent['subsets'])
    elif f in ['F07','F08']: value=sum(not perm_pred(candidate,c) for c in parent['clues'])
    else: value=sum(bool(candidate[i])!=expr_eval(e,candidate) for i,e in enumerate(parent['statements']))
    available=list(range(max(4,n)+1)); rest=[v for v in available if v!=value]
    # Include the correct count and four nearby count distractors. At low-clue
    # levels some deliberately exceed the possible maximum; probes are auxiliary.
    rest.sort(key=lambda x:(abs(x-value),r.random()))
    opts=sorted([value]+rest[:4])
    return {'family':f,'level':parent['level'],'instance':parent['instance'],'probe':True,'parent_spec':copy.deepcopy(parent),'candidate':copy.deepcopy(candidate),'count_options':opts,'names':parent['names']}


def build(out,instances=20):
    out=Path(out); out.mkdir(parents=True,exist_ok=True); allrows=[]; keys=[]; metadata=[]; specs=[]; serial=0
    coreids=[]; screenids=[]; anchorids=[]; start=time.time()
    def add(spec,base_id,variant,order,parent=None):
        nonlocal serial
        serial+=1; item_id=f'J{serial:06d}'; base_id=base_id or item_id
        variant_seed=SEED+serial*17
        payload,prompt,mapping=question_data(spec,variant,order,variant_seed)
        g=get_gold(spec); answer=order.index(g)+1; digest=sha(payload)
        inp={'item_id':item_id,**{k:payload[k] for k in ['instructions','context','question']},**{f'option_{i+1}':x for i,x in enumerate(payload['options'])},'prompt_text':prompt,'prompt_sha256':digest}
        details,diagnostic=explain(spec)
        details=replace_all(details,mapping); diagnostic=[replace_all(x,mapping) for x in diagnostic]
        split='development' if spec['instance']%5==4 else 'evaluation'
        role='core' if variant=='base' else 'contrast' if variant=='contrast' else 'probe' if variant=='candidate_probe' else 'robustness'
        key={'item_id':item_id,'base_id':base_id,'role':role,'family_id':spec['family'],'family':FD[spec['family']][1],'level':spec['level'],
             'variant':variant,'split':split,'gold_option':answer,'gold_canonical':f'c{g+1}','gold_text':payload['options'][answer-1],
             **{f'option_{i+1}_canonical':f'c{x+1}' for i,x in enumerate(order)},'explanation':details,
             **{f'option_{i+1}_diagnostic':diagnostic[x] for i,x in enumerate(order)}}
        meta={'item_id':item_id,'base_id':base_id,'family_id':spec['family'],'family':FD[spec['family']][1],'level':spec['level'],
              'instance':spec['instance'],'role':role,'variant':variant,'split':split,
              'intended_relation':'same_answer' if role=='robustness' else 'different_answer' if role=='contrast' else 'component_check' if role=='probe' else 'standalone',
              'word_count':len(prompt.split()),'option_word_count':sum(len(x.split()) for x in payload['options']),
              'parameters_json':json.dumps(parameters(spec),ensure_ascii=False),'prompt_sha256':digest}
        allrows.append(inp); keys.append(key); metadata.append(meta)
        specs.append({'item_id':item_id,'base_id':base_id,'variant':variant,'option_order':order,'variant_seed':variant_seed,'spec':spec,'entity_rename_map':mapping})
        return item_id
    for family_index,(f,title,*_) in enumerate(FAMILIES):
        for level in range(1,5):
            for inst in range(instances):
                s,alt=generate(f,level,inst); g=get_gold(s)
                r=random.Random(SEED+family_index*1000+level*100+inst)
                correct_position=(family_index+level+inst+inst//5)%5
                remaining=[i for i in range(5) if i!=g]; r.shuffle(remaining)
                order=remaining[:correct_position]+[g]+remaining[correct_position:]
                base=add(s,None,'base',order); coreids.append(base)
                if inst==4: screenids.append(base)
                if inst!=0: continue
                anchorids.append(base)
                # Four cyclic rotations plus the original cover every answer position.
                for k in range(1,5): add(s,base,f'option_rotation_{k}',order[k:]+order[:k])
                for v in ['entity_rename','fact_order','noise_short','noise_long','expanded_options','question_rewording']: add(s,base,v,order)
                add(alt,base,'contrast',order)
                if f in ['F07','F08','F09','F10']:
                    if f=='F09': candidates=list(range(5))
                    elif f=='F10': candidates=s['candidate_worlds']
                    else:
                        candidates=[]
                        for value in range(5):
                            ws=[p for p in it.permutations(range(5)) if p[s['query_person']]==value]
                            candidates.append(list(min(ws,key=lambda p:sum(not perm_pred(p,c) for c in s['clues']))))
                    for candidate in candidates:
                        ps=make_probe(s,candidate,r); pg=get_gold(ps); po=list(range(5)); r.shuffle(po)
                        add(ps,base,'candidate_probe',po)
        print(f'{f} {title}: generated',flush=True)
    byid={row['item_id']:row for row in allrows}; metabyid={row['item_id']:row for row in metadata}
    r=random.Random(SEED+99); r.shuffle(allrows)
    csvwrite(out/'questions.csv',allrows,INPUT_FIELDS)
    csvwrite(out/'smoke_test_100.csv',[byid[i] for i in screenids],INPUT_FIELDS)
    csvwrite(out/'answer_key_PRIVATE.csv',keys)
    csvwrite(out/'metadata_PRIVATE.csv',metadata)
    csvwrite(out/'families.csv',[dict(zip(['family_id','family','target_ability','level_definition'],f)) for f in FAMILIES])
    with (out/'questions.jsonl').open('w',encoding='utf-8') as fh:
        for row in allrows: fh.write(json.dumps(row,ensure_ascii=False)+'\n')
    with (out/'jev_requests.jsonl').open('w',encoding='utf-8') as fh:
        for row in allrows:
            packet={'state':row['context'],'questions':{'decision':{'type':'choice','instructions':row['instructions']+'\n\n'+row['question'],
                    'criteria':{str(i):row[f'option_{i}'] for i in range(1,6)}}}}
            fh.write(json.dumps({'item_id':row['item_id'],'payload':packet},ensure_ascii=False)+'\n')
    with (out/'specifications_PRIVATE.jsonl').open('w',encoding='utf-8') as fh:
        for row in specs: fh.write(json.dumps(row,ensure_ascii=False)+'\n')
    template=[]
    for row in allrows:
        rec={f:'' for f in RESULT_FIELDS}; rec.update(item_id=row['item_id'],repeat_index=1,prompt_sha256=row['prompt_sha256']); template.append(rec)
    csvwrite(out/'results_template.csv',template,RESULT_FIELDS)
    plans=[]
    for name,ids in [('smoke',[i for i in screenids]),('development',[x['item_id'] for x in metadata if x['split']=='development' and x['role']=='core']),
                     ('evaluation',[x['item_id'] for x in metadata if x['split']=='evaluation']),('full',list(byid))]:
        rr=random.Random(SEED+len(name)); rr.shuffle(ids)
        plans += [{'plan':name,'order':j+1,'item_id':i,'repeat_index':1} for j,i in enumerate(ids)]
    # Repeat precisely the same anchor requests; do not feed previous answers back.
    repeat=[(i,j) for i in anchorids for j in [2,3]]; r.shuffle(repeat)
    plans += [{'plan':'repeatability','order':j+1,'item_id':i,'repeat_index':rep} for j,(i,rep) in enumerate(repeat)]
    csvwrite(out/'run_plan.csv',plans)
    counts=Counter(m['role'] for m in metadata)
    summary={'benchmark_version':VERSION,'seed':SEED,'created_date':'2026-09-22','instances_per_family_level':instances,'total_items':len(allrows),
             'counts_by_role':dict(counts),'families':len(FAMILIES),'levels_per_family':4,'anchor_base_cases':len(anchorids),
             'core_answer_positions':dict(Counter(k['gold_option'] for k in keys if k['role']=='core')),
             'development_core':sum(k['role']=='core' and k['split']=='development' for k in keys),
             'evaluation_core':sum(k['role']=='core' and k['split']=='evaluation' for k in keys),
             'min_words':min(m['word_count'] for m in metadata),'max_words':max(m['word_count'] for m in metadata),
             'runtime_seconds':round(time.time()-start,2),'actual_model_runs':0}
    (out/'manifest.json').write_text(json.dumps(summary,indent=2),encoding='utf-8')
    print(json.dumps(summary,indent=2)); return allrows,keys,metadata,specs

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--out',default=str(Path(__file__).parent)); ap.add_argument('--instances',type=int,default=20)
    args=ap.parse_args(); build(args.out,args.instances)
