#!/usr/bin/env python3
"""Analyze returned JEV choices. Python standard library only; no inference calls.
Usage: python3 analyze_results.py results.csv --out analysis --run-id my_run
Do not send this script, private metadata, or the answer key to the model.
"""
from __future__ import annotations
import argparse,csv,json,math,random,statistics,sys
from collections import Counter,defaultdict
from pathlib import Path

EPS=1e-15
VALID_STATUSES={'ok','error','timeout','invalid_response'}


def readcsv(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f))


def writecsv(path,rows,fields=None):
    rows=list(rows)
    if fields is None:
        fields=[]
        for r in rows:
            for k in r:
                if k not in fields: fields.append(k)
    with Path(path).open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields or ['no_rows']); w.writeheader()
        for row in rows: w.writerow({k:('' if row.get(k) is None else row.get(k,'')) for k in fields})


def mean(xs):
    xs=[x for x in xs if x is not None]
    return sum(xs)/len(xs) if xs else None


def wilson(k,n):
    if not n: return None,None
    z=1.959963984540054; p=k/n; d=1+z*z/n
    centre=(p+z*z/(2*n))/d; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return max(0,centre-half),min(1,centre+half)


def number(value,lo=None,hi=None):
    if value in ['',None]: return None
    x=float(value)
    if not math.isfinite(x) or (lo is not None and x<lo) or (hi is not None and x>hi): raise ValueError(f'Out-of-range number: {value}')
    return x


def summarize(rows,expected=None):
    valid=[r for r in rows if r['valid_choice']]; correct=sum(r['correct'] for r in valid)
    n=len(valid); lo,hi=wilson(correct,n)
    return {'expected':expected,'attempted':len(rows),'valid':n,'invalid_or_failed':len(rows)-n,'correct':correct,
            'accuracy_valid':correct/n if n else None,'accuracy_attempted':correct/len(rows) if rows else None,
            'coverage':n/expected if expected else None,'correct_over_expected':correct/expected if expected else None,
            'wilson95_low_descriptive':lo,'wilson95_high_descriptive':hi,
            'mean_selected_probability':mean(r['selected_probability'] for r in valid),
            'mean_reported_confidence':mean(r['reported_confidence_numeric'] for r in valid),
            'brier_multiclass_sum':mean(r['brier'] for r in valid),'log_loss_clipped':mean(r['log_loss'] for r in valid),
            'probability_rows':sum(r['distribution_valid'] for r in valid),
            'zero_probability_for_gold':sum(r['zero_probability_gold'] for r in valid),
            'mean_latency_ms':mean(r['latency_numeric'] for r in rows)}


def group_report(rows,fields,expected_keys):
    groups=defaultdict(list)
    for row in rows: groups[tuple(row.get(f,'') for f in fields)].append(row)
    expected=Counter(tuple(k.get(f,'') for f in fields) for k in expected_keys)
    out=[]
    for group in sorted(set(groups)|set(expected),key=str):
        out.append({**dict(zip(fields,group)),**summarize(groups[group],expected.get(group))})
    return out


def reliability(rows,field):
    bins=defaultdict(list)
    for row in rows:
        p=row.get(field)
        if row['valid_choice'] and p is not None: bins[min(9,int(p*10))].append(row)
    output=[]
    for i in range(10):
        rs=bins[i]; n=len(rs); acc=mean(r['correct'] for r in rs); pred=mean(r[field] for r in rs)
        output.append({'bin_lower_inclusive':i/10,'bin_upper':(i+1)/10,'upper_inclusive':i==9,'n':n,
                       'mean_value':pred,'accuracy':acc,'absolute_gap':abs(pred-acc) if n else None})
    return output


def percentile(a,p):
    a=sorted(a)
    if not a: return None
    x=(len(a)-1)*p; lo=int(x); hi=min(lo+1,len(a)-1)
    return a[lo]+(a[hi]-a[lo])*(x-lo)


def clustered_delta(pairs,seed=20260922,draws=1000):
    """Resample whole families, retaining all matched base/variant pairs in them."""
    clusters=defaultdict(list)
    for a,b in pairs: clusters[a['family_id']].append(b['correct']-a['correct'])
    if len(clusters)<2: return None,None
    buckets=list(clusters.values()); r=random.Random(seed); estimates=[]
    for _ in range(draws):
        sampled=[r.choice(buckets) for _ in buckets]
        estimates.append(sum(sum(x) for x in sampled)/sum(map(len,sampled)))
    return percentile(estimates,.025),percentile(estimates,.975)


def analyze(results,bank,out,run_id=None,split='evaluation'):
    bank=Path(bank); out=Path(out); out.mkdir(parents=True,exist_ok=True)
    keys=readcsv(bank/'answer_key_PRIVATE.csv'); key={k['item_id']:k for k in keys}
    metadata={k['item_id']:k for k in readcsv(bank/'metadata_PRIVATE.csv')}
    raw=readcsv(results)
    if not raw or 'item_id' not in raw[0] or 'selected_option' not in raw[0]: raise ValueError('Need item_id and selected_option columns.')
    attempted=[]
    for row in raw:
        # Pre-filled blank template rows are not model attempts.
        has_attempt=any(row.get(f,'').strip() for f in ['selected_option','status','error_message','raw_response_json']+[f'probability_{i}' for i in range(1,6)])
        if not has_attempt: continue
        row['run_id']=row.get('run_id','').strip() or 'unspecified_run'
        attempted.append(row)
    available=sorted({r['run_id'] for r in attempted})
    if run_id is None:
        if len(available)>1: raise ValueError('Multiple run_id values found. Select one with --run-id: '+', '.join(available))
        if not available: raise ValueError('No attempted responses found. The supplied file appears to be an unfilled template.')
        run_id=available[0]
    raw=[r for r in attempted if r['run_id']==run_id]
    if not raw: raise ValueError(f'No attempted rows for run_id {run_id!r}.')
    # Detect mixed conditions before pooling their scores.
    for field in ['provider','model_requested','model_returned','prompt_mode','settings_json']:
        values={r.get(field,'').strip() for r in raw if r.get(field,'').strip()}
        if len(values)>1: raise ValueError(f'Mixed {field} values within a run. Give each condition a separate run_id: {values}')
    scored=[]; seen=set(); warnings=[]
    for row in raw:
        item=row['item_id'].strip()
        if item not in key: raise ValueError(f'Unknown item_id {item!r}.')
        k=key[item]; m=metadata[item]
        repeat_value=number(row.get('repeat_index') or 1,1)
        if not repeat_value.is_integer(): raise ValueError(f'Invalid repeat_index for {item}')
        repeat=int(repeat_value); identity=(item,repeat)
        if identity in seen: raise ValueError(f'Duplicate row for {item}, repeat {repeat}. Preserve one final response per item/repeat; log retries in raw_response_json.')
        seen.add(identity)
        supplied_hash=row.get('prompt_sha256','').strip()
        if supplied_hash and supplied_hash!=m['prompt_sha256']: raise ValueError(f'Prompt hash mismatch for {item}: changed prompts must not be scored as original items.')
        messages=[]; status=row.get('status','').strip().lower() or 'ok'
        if status not in VALID_STATUSES: messages.append('unrecognized_status'); status='invalid_response'
        choice=None
        try:
            cv=number(row.get('selected_option'),1,5)
            if cv is not None and cv.is_integer(): choice=int(cv)
            else: messages.append('missing_or_noninteger_choice')
        except (ValueError,TypeError): messages.append('invalid_choice')
        valid=status=='ok' and choice is not None
        if status=='ok' and not valid: status='invalid_response'
        probabilities=None; pfields=[row.get(f'probability_{i}','') for i in range(1,6)]
        if any(v not in ['',None] for v in pfields):
            try:
                pp=[number(v,0,1) for v in pfields]
                if any(v is None for v in pp): raise ValueError('partial_distribution')
                if abs(sum(pp)-1)>1e-5: raise ValueError('probabilities_do_not_sum_to_one')
                probabilities=pp
            except (ValueError,TypeError) as e: messages.append('invalid_distribution:'+str(e))
        conf=None
        try: conf=number(row.get('reported_confidence'),0,1)
        except (ValueError,TypeError): messages.append('invalid_reported_confidence')
        latency=None
        try: latency=number(row.get('latency_ms'),0)
        except (ValueError,TypeError): messages.append('invalid_latency')
        gold=int(k['gold_option']); correct=int(valid and choice==gold)
        psel=pgold=brier=logloss=None; zero=False
        if probabilities is not None and valid:
            psel=probabilities[choice-1]; pgold=probabilities[gold-1]
            brier=sum((p-int(i==gold-1))**2 for i,p in enumerate(probabilities))
            logloss=-math.log(max(EPS,pgold)); zero=pgold==0
            if psel < max(probabilities)-1e-8: messages.append('selected_choice_is_not_a_maximum_probability_option')
        record={**row,**{f:m[f] for f in ['base_id','family_id','family','level','instance','role','variant','split','word_count','option_word_count','parameters_json']},
                'repeat_index':repeat,'status':status,'valid_choice':valid,'selected_option_numeric':choice,'gold_option':gold,'correct':correct,
                'chosen_canonical':k.get(f'option_{choice}_canonical','') if valid else '', 'gold_canonical':k['gold_canonical'],
                'distribution_valid':probabilities is not None,'selected_probability':psel,'gold_probability':pgold,
                'reported_confidence_numeric':conf,'brier':brier,'log_loss':logloss,'zero_probability_gold':int(zero),
                'latency_numeric':latency,'validation_notes':'; '.join(messages),
                'diagnostic':k.get(f'option_{choice}_diagnostic','') if valid and not correct else '',
                'gold_explanation':k['explanation']}
        for i in range(1,6): record[f'p{i}']=probabilities[i-1] if probabilities is not None else None
        scored.append(record)
        if messages: warnings.append({'item_id':item,'repeat_index':repeat,'notes':'; '.join(messages)})
    included=lambda r: split=='all' or r['split']==split
    first={r['item_id']:r for r in scored if r['repeat_index']==1 and included(r)}
    core=[r for r in first.values() if r['role']=='core']
    expected_core=[k for k in keys if k['role']=='core' and included(k)]
    summary={'run_id':run_id,'split':split,'primary_core':summarize(core,len(expected_core)),
             'notes':['Core accuracy uses repeat_index 1 only. Robustness variants, contrasts, probes, and repeated requests are not extra independent core items.',
                      'Wilson intervals are descriptive and assume independent cases; template reuse limits population-level interpretation.',
                      'Reported confidence is a distribution-concentration score, not automatically a probability of correctness.',
                      'The benchmark characterizes observed decisions, not hidden model architecture or a literal working-memory capacity.'],
             'attempted_total_rows_in_run':len(scored),'validation_warning_rows':len(warnings)}
    writecsv(out/'scored_results.csv',scored)
    writecsv(out/'data_warnings.csv',warnings,['item_id','repeat_index','notes'])
    writecsv(out/'accuracy_by_family.csv',group_report(core,['family_id','family'],expected_core))
    writecsv(out/'accuracy_by_level.csv',group_report(core,['level'],expected_core))
    writecsv(out/'accuracy_by_family_level.csv',group_report(core,['family_id','family','level'],expected_core))
    validcore=[r for r in core if r['valid_choice']]
    pos=[]
    for i in range(1,6):
        expected=[k for k in expected_core if int(k['gold_option'])==i]
        rs=[r for r in core if r['gold_option']==i]
        pos.append({'gold_position':i,**summarize(rs,len(expected)),
                    'times_chosen_over_all_core':sum(r['selected_option_numeric']==i for r in validcore),
                    'chosen_share_over_all_valid_core':sum(r['selected_option_numeric']==i for r in validcore)/len(validcore) if validcore else None})
    writecsv(out/'answer_position_profile.csv',pos)
    calib=reliability(core,'selected_probability'); confbins=reliability(core,'reported_confidence_numeric')
    # A gap for provider confidence is deliberately not labeled calibration error.
    for row in confbins: row.pop('absolute_gap',None)
    writecsv(out/'probability_reliability.csv',calib)
    writecsv(out/'reported_confidence_vs_accuracy.csv',confbins)
    nc=sum(b['n'] for b in calib)
    summary['probability_ece_10bins']=sum(b['n']*b['absolute_gap'] for b in calib if b['n'])/nc if nc else None
    summary['probability_ece_n']=nc
    risk=[]
    for field in ['selected_probability','reported_confidence_numeric']:
        available_rows=[r for r in validcore if r[field] is not None]
        for threshold in [.5,.6,.7,.8,.9,.95,.99,1.0]:
            accepted=[r for r in available_rows if r[field]>=threshold]
            errors=sum(not r['correct'] for r in accepted)
            low,high=wilson(errors,len(accepted))
            risk.append({'measure':field,'threshold':threshold,'accepted':len(accepted),'errors':errors,
                         'coverage_among_available_scores':len(accepted)/len(available_rows) if available_rows else None,
                         'error_rate':errors/len(accepted) if accepted else None,'error_wilson95_low':low,'error_wilson95_high':high})
    writecsv(out/'risk_coverage.csv',risk)
    # Paired robustness: compare meanings using private canonical-option mappings.
    paired=defaultdict(list); detail=[]
    for r in first.values():
        if r['role']!='robustness' or not r['valid_choice']: continue
        b=first.get(r['base_id'])
        if not b or not b['valid_choice']: continue
        paired[r['variant']].append((b,r))
        tv=None
        if b['distribution_valid'] and r['distribution_valid']:
            bp={key[b['item_id']][f'option_{j}_canonical']:b[f'p{j}'] for j in range(1,6)}
            rp={key[r['item_id']][f'option_{j}_canonical']:r[f'p{j}'] for j in range(1,6)}
            tv=.5*sum(abs(bp[c]-rp[c]) for c in bp)
        detail.append({'base_id':b['item_id'],'item_id':r['item_id'],'family_id':r['family_id'],'variant':r['variant'],
                       'base_correct':b['correct'],'variant_correct':r['correct'],
                       'same_meaning_chosen':b['chosen_canonical']==r['chosen_canonical'],'probability_total_variation':tv})
    pr=[]
    for v,pairs in sorted(paired.items()):
        n=len(pairs); low,high=clustered_delta(pairs)
        pr.append({'variant':v,'complete_pairs':n,'base_accuracy':mean(a['correct'] for a,b in pairs),
                   'variant_accuracy':mean(b['correct'] for a,b in pairs),
                   'paired_accuracy_delta':mean(b['correct']-a['correct'] for a,b in pairs),
                   'family_cluster_bootstrap95_low':low,'family_cluster_bootstrap95_high':high,
                   'same_meaning_rate':mean(a['chosen_canonical']==b['chosen_canonical'] for a,b in pairs),
                   'base_right_variant_wrong':sum(a['correct'] and not b['correct'] for a,b in pairs),
                   'base_wrong_variant_right':sum(not a['correct'] and b['correct'] for a,b in pairs),
                   'both_correct':sum(a['correct'] and b['correct'] for a,b in pairs)})
    writecsv(out/'paired_robustness.csv',pr); writecsv(out/'paired_details.csv',detail)
    # Full five-position cyclic rotation panels, not all 120 permutations.
    rotgroups=defaultdict(list)
    for r in first.values():
        if r['variant']=='base' or r['variant'].startswith('option_rotation_'): rotgroups[r['base_id']].append(r)
    rots=[]
    for base,rs in rotgroups.items():
        if len(rs)!=5 or not all(r['valid_choice'] for r in rs): continue
        rots.append({'base_id':base,'family_id':rs[0]['family_id'],'all_five_correct':all(r['correct'] for r in rs),
                     'any_of_five_correct':any(r['correct'] for r in rs),'mean_rotation_accuracy':mean(r['correct'] for r in rs),
                     'same_meaning_all_five':len({r['chosen_canonical'] for r in rs})==1,
                     'distinct_chosen_meanings':len({r['chosen_canonical'] for r in rs})})
    writecsv(out/'rotation_panels.csv',rots)
    summary['complete_rotation_panels']=len(rots)
    summary['rotation_all_five_correct_rate']=mean(r['all_five_correct'] for r in rots)
    summary['rotation_meaning_consistency_rate']=mean(r['same_meaning_all_five'] for r in rots)
    # Contrast: merely switching is not enough; both answers must be correct.
    contrasts=[]
    for r in first.values():
        if r['role']!='contrast' or not r['valid_choice']: continue
        b=first.get(r['base_id'])
        if not b or not b['valid_choice']: continue
        contrasts.append({'base_id':b['item_id'],'item_id':r['item_id'],'family_id':r['family_id'],
                          'base_correct':b['correct'],'contrast_correct':r['correct'],
                          'both_correct':bool(b['correct'] and r['correct']),
                          'answer_changed':b['chosen_canonical']!=r['chosen_canonical']})
    writecsv(out/'contrast_pairs.csv',contrasts)
    summary['contrast_pair_count']=len(contrasts)
    summary['contrast_both_correct_rate']=mean(r['both_correct'] for r in contrasts)
    eligible=[r for r in contrasts if r['base_correct']]
    summary['contrast_accuracy_given_base_correct']=mean(r['contrast_correct'] for r in eligible)
    # Candidate evaluation probes diagnose local checking versus final integration.
    pg=defaultdict(list)
    for r in first.values():
        if r['role']=='probe': pg[r['base_id']].append(r)
    components=[]
    for base,rs in pg.items():
        b=first.get(base)
        if not b or not b['valid_choice'] or len(rs)!=5 or not all(r['valid_choice'] for r in rs): continue
        allok=all(r['correct'] for r in rs)
        components.append({'base_id':base,'family_id':b['family_id'],'family':b['family'],'level':b['level'],
                           'parent_correct':b['correct'],'correct_candidate_checks':sum(r['correct'] for r in rs),
                           'all_five_candidate_checks_correct':allok,'parent_wrong_checks_all_correct':not b['correct'] and allok})
    writecsv(out/'component_check_profile.csv',components)
    # Identical-input repeatability is separate from option-order invariance.
    repeats=defaultdict(list)
    for r in scored:
        if included(r) and r['valid_choice']: repeats[r['item_id']].append(r)
    repeat_report=[]
    for item,rs in repeats.items():
        if len(rs)<2: continue
        counts=Counter(r['chosen_canonical'] for r in rs)
        repeat_report.append({'item_id':item,'role':rs[0]['role'],'repeats':len(rs),'same_meaning_all_repeats':len(counts)==1,
                              'modal_choice_share':max(counts.values())/len(rs),'accuracy_across_repeats':mean(r['correct'] for r in rs),
                              'selected_probability_range':max(r['selected_probability'] for r in rs if r['selected_probability'] is not None)-min(r['selected_probability'] for r in rs if r['selected_probability'] is not None) if all(r['selected_probability'] is not None for r in rs) else None})
    writecsv(out/'repeatability.csv',repeat_report)
    errors=[r for r in first.values() if r['valid_choice'] and not r['correct']]
    errors.sort(key=lambda r:(-(r['selected_probability'] if r['selected_probability'] is not None else -1),r['item_id']))
    writecsv(out/'errors_for_review.csv',errors)
    with (out/'summary.json').open('w',encoding='utf-8') as f: json.dump(summary,f,indent=2)
    text='# Benchmark analysis\n\nRun: '+run_id+'\n\nSplit: '+split+'\n\n'
    primary=summary['primary_core']; text+=f"Core questions attempted: {primary['attempted']} of {primary['expected']}. Valid answers: {primary['valid']}. Correct answers: {primary['correct']}.\n\n"
    if primary['accuracy_valid'] is not None: text+=f"Accuracy among valid core answers: {primary['accuracy_valid']:.2%}. Accuracy among all attempted core questions: {primary['accuracy_attempted']:.2%}.\n\n"
    text+='See accuracy_by_family.csv for the ability profile, paired_robustness.csv for controlled perturbations, contrast_pairs.csv for sensitivity to changed evidence, and component_check_profile.csv for candidate checking versus final integration.\n\n'
    text+='Reported confidence is analyzed separately from selected-option probability. A concentrated distribution is not itself proof that the chosen answer is correct.\n\n'
    text+='The results describe this model snapshot, request format, question bank, and run. They do not establish a hidden reasoning algorithm, a human grade level, or a fixed number of working-memory slots.\n'
    (out/'SUMMARY.md').write_text(text,encoding='utf-8')
    print(json.dumps(summary,indent=2)); return summary

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('results'); p.add_argument('--bank',default=str(Path(__file__).parent)); p.add_argument('--out',default='analysis')
    p.add_argument('--run-id'); p.add_argument('--split',choices=['evaluation','development','all'],default='evaluation')
    a=p.parse_args()
    try: analyze(a.results,a.bank,a.out,a.run_id,a.split)
    except (ValueError,KeyError,FileNotFoundError) as e: p.exit(2,str(e)+'\n')
