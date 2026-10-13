"""Count actual model judgments, distinguishing drift from anchor disagreement."""
from pathlib import Path
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json,hashlib,statistics,re
from prepare import R,W,read,write,sha
def distance(a,b):
 a=re.findall(r'\w+|[^\w\s]',a);b=re.findall(r'\w+|[^\w\s]',b);prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  cur=[i]
  for j,y in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+int(x!=y)))
  prev=cur
 return prev[-1],max(len(a),len(b))
def validate(group,raw):
 assert raw['model_requested']=='gpt-5.6-luna'
 ds=raw['documents'];assert len(ds)==len(group)
 out={x['id']:x for x in ds};assert set(out)=={g['id'] for g in group}
 for g in group:
  vs=out[g['id']]['variants'];assert len(vs)==2 and {v['variant_id'] for v in vs}=={'concise','fluent'}
  for v in vs:
   assert set(v['components'])==set(g['editable_ids'])
   assert set(v['factors'])=={f['id'] for f in g['factors']}
   for c in v['components'].values():
    assert c['meaning'] in ['preserved','changed','uncertain'] and c['original_type_valid'] in [True,False,None] and c['rewritten_type_valid'] in [True,False,None]
   for f in v['factors'].values():assert f['original_label_valid'] in [True,False,None] and f['rewritten_label_valid'] in [True,False,None]
 return {(d['id'],v['variant_id']):v for d in ds for v in d['variants']}
def state(v):
 changed=[('component',i) for i,c in v['components'].items() if c['meaning']=='changed' or (c['original_type_valid'] is True and c['rewritten_type_valid'] is False)]
 changed += [('factor',i) for i,f in v['factors'].items() if f['original_label_valid'] is True and f['rewritten_label_valid'] is False]
 unknown=[('component',i) for i,c in v['components'].items() if c['meaning']=='uncertain' or c['original_type_valid'] is not True or c['rewritten_type_valid'] is None]
 unknown += [('factor',i) for i,f in v['factors'].items() if f['original_label_valid'] is not True or f['rewritten_label_valid'] is None]
 return ('drift' if changed else ('unresolved_or_anchor_disagreement' if unknown else 'no_detected_drift')),changed,unknown
def accepts(v,fs,method):
 if method=='format_only':return True
 if not all(c['meaning']=='preserved' and c['original_type_valid'] is True and c['rewritten_type_valid'] is True for c in v['components'].values()):return False
 factors=[f for f in fs if method=='full_affected' or f['category']=='internal_positive']
 return all(v['factors'][f['id']]['original_label_valid'] is True and v['factors'][f['id']]['rewritten_label_valid'] is True for f in factors)
def main():
 inputs=sorted((R/'drift/judge_inputs').glob('*.json'));assert len(inputs)==8
 files=inputs+list((R/'drift/filter_outputs').glob('*.json'))+list((R/'drift/audit_outputs').glob('*.json'))
 assert len(files)==24
 out=R/'drift/analysis';out.mkdir(exist_ok=False)
 write(out/'input_freeze.json',{'at_utc':datetime.now(timezone.utc).isoformat(),'code_sha256':sha(__file__),'hashes':{str(p.relative_to(R)):sha(p) for p in files}})
 rows=[];factor_rows=[];component_rows=[];source_rows=[]
 for p in inputs:
  group=read(p)['documents'];filt=validate(group,read(R/'drift/filter_outputs'/p.name));audit=validate(group,read(R/'drift/audit_outputs'/p.name))
  for g in group:
   originals={c['id']:c['quote'] for c in g['original_components']}
   for variant in g['variants']:
    ident=(g['id'],variant['variant_id']);f=filt[ident];a=audit[ident];label,changes,unknown=state(a);flabel,_,_=state(f)
    distances=[distance(originals[i],t) for i,t in variant['replacements'].items()];dist=sum(x[0] for x in distances);den=sum(x[1] for x in distances)
    row={'id':g['id'],'corpus':g['corpus'],'variant_id':variant['variant_id'],'audit_state':label,'filter_state':flabel,'state_agreement':label==flabel,'audit_changes':changes,'audit_unresolved':unknown,'noncopy':any(originals[i]!=t for i,t in variant['replacements'].items()),'normalized_edit_distance':dist/den if den else 0.,'accepted':{m:accepts(f,g['factors'],m) for m in ['format_only','internal_positive','full_affected']}}
    rows.append(row)
    for factor in g['factors']:
     aa=a['factors'][factor['id']];ff=f['factors'][factor['id']]
     factor_rows.append({'id':g['id'],'corpus':g['corpus'],'variant_id':variant['variant_id'],**factor,'audit':aa,'filter':ff,'anchor_agreed':aa['original_label_valid'] is True,'drift':aa['original_label_valid'] is True and aa['rewritten_label_valid'] is False,'unresolved_new':aa['original_label_valid'] is True and aa['rewritten_label_valid'] is None,'agreement':(aa['original_label_valid'],aa['rewritten_label_valid'])==(ff['original_label_valid'],ff['rewritten_label_valid'])})
    for ident,c in a['components'].items():component_rows.append({'id':g['id'],'corpus':g['corpus'],'variant_id':variant['variant_id'],'component_id':ident,'audit':c,'filter':f['components'][ident]})
   source_rows.append({'id':g['id'],'corpus':g['corpus'],'original_text':g['original_text'],'original_components':g['original_components'],'editable_ids':g['editable_ids'],'variants':g['variants'],'factors':g['factors']})
 totals=[];filters=[];factors=[]
 for corpus in ['aaec','cdcp']:
  rr=[x for x in rows if x['corpus']==corpus];count=Counter(x['audit_state'] for x in rr)
  totals.append({'corpus':corpus,'documents':len({x['id'] for x in rr}),'variants':len(rr),'states':dict(count),'noncopy':sum(x['noncopy'] for x in rr),'edit_distance_median':statistics.median(x['normalized_edit_distance'] for x in rr),'variant_state_agreement':sum(x['state_agreement'] for x in rr)})
  for method in ['format_only','internal_positive','full_affected']:
   accepted=[x for x in rr if x['accepted'][method]];rejected=[x for x in rr if not x['accepted'][method]];states=Counter(x['audit_state'] for x in accepted);rejectstates=Counter(x['audit_state'] for x in rejected)
   filters.append({'corpus':corpus,'filter':method,'all_variants':len(rr),'accepted':len(accepted),'source_coverage':len({x['id'] for x in accepted}),'accepted_states':dict(states),'rejected_states':dict(rejectstates),'accepted_noncopy':sum(x['noncopy'] for x in accepted),'accepted_edit_distance_median':statistics.median(x['normalized_edit_distance'] for x in accepted) if accepted else None,'drift_among_all_accepted':states['drift']/len(accepted) if accepted else None,'drift_among_resolved_accepted':states['drift']/(states['drift']+states['no_detected_drift']) if states['drift']+states['no_detected_drift'] else None})
  for category in ['internal_positive','crossing_positive','internal_NONE','crossing_NONE']:
   fr=[x for x in factor_rows if x['corpus']==corpus and x['category']==category]
   factors.append({'corpus':corpus,'category':category,'factor_variants':len(fr),'original_label_agreed':sum(x['anchor_agreed'] for x in fr),'original_disagreed':sum(x['audit']['original_label_valid'] is False for x in fr),'original_uncertain':sum(x['audit']['original_label_valid'] is None for x in fr),'drift':sum(x['drift'] for x in fr),'new_uncertain_when_anchor_agreed':sum(x['unresolved_new'] for x in fr),'two_assessor_agreement':sum(x['agreement'] for x in fr)})
 write(out/'metrics.json',{'source':'ACTUAL_LUNA_OUTPUTS_MODEL_ASSESSED','human_adjudication':False,'totals':totals,'filters':filters,'factor_breakdown':factors,'by_variant':rows,'factor_judgments':factor_rows,'component_judgments':component_rows,'limitations':['same model family generation/filter/audit, independent contexts only','all selected source-centered rewrites retained; no general prevalence claim','NONE probes are sampled binary slots and exclude singleton pieces of known joint sources','original label disagreement not counted as induced drift','no real downstream training or human semantic audit']})
 write(out/'source_pairs.json',{'documents':source_rows})
 print(json.dumps({'totals':totals,'filters':filters,'factors':factors},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
