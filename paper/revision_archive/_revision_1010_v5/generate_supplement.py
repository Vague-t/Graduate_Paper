"""Explicit synthetic authoring scenarios. Does not invoke a model, annotator or solver."""
from pathlib import Path
from collections import defaultdict
import csv,hashlib,json,math,statistics,random,re
import numpy as np
W=Path(__file__).resolve().parent
SEEDS=[17,29,43];DS=['AAEC','CDCP'];IDENTITY='SIM-1010-V4'
def rng(*x):return random.Random(int(hashlib.sha256('|'.join(map(str,x)).encode()).hexdigest()[:16],16))
def dump(name,obj): (W/name).write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n')
def csvout(name,rows):
 with (W/name).open('w',newline='') as f:
  writer=csv.DictWriter(f,fieldnames=list(rows[0]));writer.writeheader();writer.writerows(rows)
def f1(c):
 t,p,n=c;return 200*t/(2*t+p+n) if 2*t+p+n else 0
def lev(a,b):
 prev=list(range(len(b)+1))
 for i,x in enumerate(a,1):
  cur=[i]
  for j,y in enumerate(b,1):cur.append(min(cur[-1]+1,prev[j]+1,prev[j-1]+(x!=y)))
  prev=cur
 return prev[-1]
def tokens(s):return re.findall(r"[A-Za-z]+|\d+|[^\w\s]",s)
old={}
with (W/'document_counts.csv').open() as f:
 for z in csv.DictReader(f):old[z['dataset'],int(z['seed']),z['method'],z['object'],z['document']]=[int(z[k]) for k in ['tp','fp','fn']]
res=json.loads((W/'scenario_results.json').read_text());docs={ds:sorted({k[4] for k in old if k[0]==ds}) for ds in DS}
summary={'identity':IDENTITY,'evidence_type':'SYNTHETIC_AUTHORING_SCENARIOS','real_model_runs':0,'real_human_judgements':0,'real_solver_runs':0,'seeds':SEEDS,'provenance':'Probabilities, memberships, resource costs and external placeholders are assigned by this public generator, not estimated from real corpus/model output.'}
# A shared, templated pool separates variation from screening. Methods share every attempt.
variants=[];screen=[]
for ds in DS:
 for di in range(40):
  group='low' if di<20 else 'high';nf=4 if group=='low' else 12
  source_id=f'SYN-{ds}-AUG-{di+1:03d}'
  original=f'The public service unit {di+1} cannot meet the current demand in the local community.'
  phrases=[original,
   f'The present capacity of public service unit {di+1} is insufficient for local residents.',
   f'In the local community, public service unit {di+1} still lacks the capacity to meet demand.',
   f'Public service unit {di+1} needs more capacity because the demand of local residents remains unmet.']
  taken={m:0 for m in ['plain','qos','full']}
  for attempt in range(4):
   rr=rng(IDENTITY,'augmentation',ds,di,attempt)
   choice=rr.choices(range(4),[.10,.32,.30,.28])[0];variant=phrases[choice]
   drift=[]
   for j in range(nf):
    # These are synthetic factor truth labels, not human semantic decisions.
    drift.append(choice!=0 and rr.random()<(0.038 if group=='low' else 0.060))
   if any(drift):variant=variant.replace('insufficient','sufficient').replace('cannot','can').replace('still lacks','already has').replace('remains unmet','is met')
   ta,tb=tokens(original),tokens(variant);dist=lev(ta,tb)/max(len(ta),len(tb))
   record={'identity':IDENTITY,'dataset':ds,'source':source_id,'attempt':attempt+1,'group':group,'source_text':f'The unit should receive public funding. {original} Demand rose last year.','original_slot':original,'variant_slot':variant,'factor_count':nf,'synthetic_factor_drift':drift,'noncopy':original!=variant,'edit_distance':dist,'evidence_type':'RULE_GENERATED_TEXT_AND_ASSIGNED_FACTOR_LABELS'}
   variants.append(record)
   for method,detect,false_alarm in [('plain',.18,.005),('qos',.55,.012),('full',.90,.023)]:
    mr=rng(IDENTITY,'screen',ds,di,attempt,method)
    flags=[(mr.random()<detect if bad else mr.random()<false_alarm) for bad in drift]
    passed=not any(flags);accepted=passed and taken[method]<2
    if accepted:taken[method]+=1
    screen.append({'identity':IDENTITY,'dataset':ds,'source':source_id,'attempt':attempt+1,'method':method,'group':group,'factors':nf,'noncopy':int(record['noncopy']),'edit_distance':dist,'drift_factors':sum(drift),'drift_variant':int(any(drift)),'accepted':int(accepted),'rejected_screen':int(not passed),'quota_only':int(passed and not accepted),'evidence_type':'SIMULATED_SCREENING'})
dump('augmentation_text_pairs.json',variants);csvout('augmentation_screening.csv',screen)
summary['augmentation']=[]
for ds in DS:
 for method in ['plain','qos','full']:
  rows=[x for x in screen if x['dataset']==ds and x['method']==method];acc=[x for x in rows if x['accepted']]
  summary['augmentation'].append({'dataset':ds,'method':method,'attempts':len(rows),'accepted':len(acc),'noncopy':sum(x['noncopy'] for x in acc),'noncopy_pct':100*statistics.mean(x['noncopy'] for x in acc),'edit_median':float(np.median([x['edit_distance'] for x in acc])),'edit_q1':float(np.quantile([x['edit_distance'] for x in acc],.25)),'edit_q3':float(np.quantile([x['edit_distance'] for x in acc],.75)),'drift_variants':sum(x['drift_variant'] for x in acc),'drift_pct':100*statistics.mean(x['drift_variant'] for x in acc),'source_coverage':len({x['source'] for x in acc}),'low_covered':len({x['source'] for x in acc if x['group']=='low'}),'high_covered':len({x['source'] for x in acc if x['group']=='high'}),'stratum_denominator':20,'factor_drift':sum(x['drift_factors'] for x in acc),'factor_denominator':sum(x['factors'] for x in acc)})
# End-to-end resource envelope. Cost functions are scenario assumptions.
resources=[];budgetrows=[]
for ds in DS:
 ranks=sorted(docs[ds],key=lambda d:(sum(old[ds,17,'t1_i0','component',d][::2]),d))
 for di,doc in enumerate(ranks):
  gcomp=sum(old[ds,17,'t1_i0','component',doc][::2]);m=gcomp+8
  upper=m*(m-1)*4 if ds=='AAEC' else sum(math.comb(m,k)*(m-k)*2**(k+1) for k in [1,2,3])
  # Treat 60% as a declared synthetic legal-candidate ratio, not measured pruning.
  slots=int(.6*upper);score_objects=2*slots;group=['small','medium','large'][min(2,3*di//len(ranks))]
  limit=9000 if ds=='AAEC' else 330000;failed=slots>limit
  factor=1 if ds=='AAEC' else 1.35
  generation=factor*(9+.09*gcomp);enumeration=slots*(.0003 if ds=='AAEC' else .000003)
  scoring=score_objects*(.00048 if ds=='AAEC' else .000018)
  preparation=generation+enumeration+scoring;memory=.8+score_objects*.000008
  obj={'identity':IDENTITY,'dataset':ds,'document':doc,'group':group,'candidate_spans':m,'typed_components':2*m,'preprune_slots':slots,'scored_label_objects':score_objects,'postprune_slots':min(slots,4096),'precheck_limit':limit,'gold_relations':sum(old[ds,17,'t1_i0','relation',doc][::2]),'precheck_failed':int(failed),'generation_s':generation,'enumeration_s':enumeration,'scoring_s':scoring,'preparation_s':preparation,'assigned_peak_gib':memory,'evidence_type':'ASSIGNED_RESOURCE_FUNCTION'}
  resources.append(obj)
  for seed in SEEDS:
   for method in ['local','global']:
    target='t1_i1' if method=='local' else 'global_equal'
    fullsolve=(1.8+.00032*slots) if method=='local' else (1.1+.0009*slots)
    if ds=='CDCP':fullsolve=(3.0+.000018*slots) if method=='local' else (1.8+.00007*slots)
    fullsolve*=rng(IDENTITY,'solve',ds,doc,seed,method).uniform(.88,1.12)
    for mult in [.5,1,2]:
     limit_s=(24 if ds=='AAEC' else 36)*mult
     remaining=max(0,limit_s-preparation);fraction=min(1,remaining/fullsolve)
     if failed:status='PRECHECK_FAIL';fraction=0;elapsed=min(limit_s,generation+enumeration)
     elif remaining==0:status='PREPARATION_TIMEOUT';fraction=0;elapsed=limit_s
     elif fraction<.20:status='NO_INCUMBENT_TIMEOUT';fraction=0;elapsed=limit_s
     elif fraction<1:status='FEASIBLE_TIMEOUT';elapsed=limit_s
     else:status='COMPLETE_SCENARIO';elapsed=preparation+fullsolve
     for ob in ['component','relation']:
      base=old[ds,seed,'t1_i0',ob,doc];end=old[ds,seed,target,ob,doc];gold=base[0]+base[2]
      tp=round(base[0]+fraction*(end[0]-base[0]));fp=round(base[1]+fraction*(end[1]-base[1]))
      budgetrows.append({'identity':IDENTITY,'dataset':ds,'document':doc,'seed':seed,'method':method,'group':group,'budget_multiplier':mult,'deadline_s':limit_s,'object':ob,'tp':tp,'fp':fp,'fn':gold-tp,'status':status,'elapsed_s':elapsed,'preparation_s':preparation,'assigned_solver_s':min(remaining,fullsolve) if not failed else 0,'incumbent_fraction':fraction,'fallback':int(fraction==0),'returned_baseline_or_simulated_complete_counts':1,'solver_certificate':'NOT_EXECUTED','global_gap':None,'evidence_type':'SIMULATED_BUDGET_OUTCOME'})
csvout('resource_envelope.csv',resources);csvout('budget_outcomes.csv',budgetrows)
summary['resources']=[];summary['budget']=[]
for ds in DS:
 for group in ['all','small','medium','large']:
  rr=[x for x in resources if x['dataset']==ds and (group=='all' or x['group']==group)]
  summary['resources'].append({'dataset':ds,'group':group,'docs':len(rr),'slots_median':float(np.median([x['preprune_slots'] for x in rr])),'slots_max':max(x['preprune_slots'] for x in rr),'preparation_p95':float(np.quantile([x['preparation_s'] for x in rr],.95)),'precheck_fail':sum(x['precheck_failed'] for x in rr),'precheck_gold_relations':sum(x['gold_relations'] for x in rr if x['precheck_failed']), 'gold_relations':sum(x['gold_relations'] for x in rr)})
  for mult in [.5,1,2]:
   for method in ['local','global']:
    rr=[x for x in budgetrows if x['dataset']==ds and x['object']=='relation' and x['method']==method and x['budget_multiplier']==mult and (group=='all' or x['group']==group)]
    vals=[f1([sum(x[k] for x in rr if x['seed']==seed) for k in ['tp','fp','fn']]) for seed in SEEDS]
    summary['budget'].append({'dataset':ds,'group':group,'multiplier':mult,'method':method,'doc_seed_rows':len(rr),'mean_f1':statistics.mean(vals),'sd_f1':statistics.stdev(vals),'mean_s':statistics.mean(x['elapsed_s'] for x in rr),'p95_s':float(np.quantile([x['elapsed_s'] for x in rr],.95)),'timeout_pct':100*sum('TIMEOUT' in x['status'] for x in rr)/len(rr),'fallback_pct':100*sum(x['fallback'] for x in rr)/len(rr),'precheck_pct':100*sum(x['status']=='PRECHECK_FAIL' for x in rr)/len(rr),'complete_pct':100*sum(x['status']=='COMPLETE_SCENARIO' for x in rr)/len(rr)})
# Document-paired bootstrap within the assigned scenarios; uncertainty is conditional on assumptions.
summary['budget_pairs']=[]
for ds in DS:
 for group in ['all','small','medium','large']:
  groupdocs=[x['document'] for x in resources if x['dataset']==ds and (group=='all' or x['group']==group)]
  for mult in [.5,1,2]:
   bmap={(x['method'],x['seed'],x['document']):[x[k] for k in ['tp','fp','fn']] for x in budgetrows if x['dataset']==ds and x['object']=='relation' and x['budget_multiplier']==mult}
   ix=np.random.default_rng(int(hashlib.sha256(f'{IDENTITY}|{ds}|{group}|{mult}'.encode()).hexdigest()[:16],16)).integers(0,len(groupdocs),size=(2000,len(groupdocs)))
   boots={}
   for method in ['local','global']:
    samples=[]
    for seed in SEEDS:
     a=np.array([bmap[method,seed,d] for d in groupdocs]);z=a[ix].sum(axis=1);samples.append(200*z[:,0]/(2*z[:,0]+z[:,1]+z[:,2]))
    boots[method]=np.mean(samples,axis=0)
   ci=np.quantile(boots['local']-boots['global'],[.025,.975]).tolist()
   mean=lambda method:next(x['mean_f1'] for x in summary['budget'] if x['dataset']==ds and x['group']==group and x['multiplier']==mult and x['method']==method)
   summary['budget_pairs'].append({'dataset':ds,'group':group,'multiplier':mult,'local_minus_global':mean('local')-mean('global'),'ci95':ci,'unit':'synthetic document paired; average across three seeds'})
# External systems are visibly named placeholders. Each has raw per-document counts.
ext=[]
params={'Kawarada_proxy':{'AAEC':(.67,.40),'CDCP':(.63,.44)},'UniASA_proxy':{'AAEC':(.72,.37),'CDCP':(.69,.41)}}
for ds in DS:
 for method in params:
  for seed in SEEDS:
   for doc in docs[ds]:
    for ob in ['component','relation']:
     gold=sum(old[ds,seed,'t1_i0',ob,doc][::2]);rr=rng(IDENTITY,'external',ds,method,seed,doc,ob)
     recall,fpr=params[method][ds]
     if ob=='component':recall+=.13;fpr-=.20
     # Binomial draws are synthetic; no author's output/checkpoint is used.
     tp=sum(rr.random()<recall for _ in range(gold));fp=sum(rr.random()<fpr for _ in range(gold))
     ext.append({'identity':IDENTITY,'dataset':ds,'document':doc,'seed':seed,'method':method,'object':ob,'tp':tp,'fp':fp,'fn':gold-tp,'evidence_type':'EXTERNAL_METHOD_PLACEHOLDER_SIMULATION','not_author_reported':True})
csvout('external_placeholders.csv',ext);summary['external']=[]
for ds in DS:
 for method in params:
  ent={'dataset':ds,'method':method}
  for ob in ['component','relation']:
   rr=[x for x in ext if x['dataset']==ds and x['method']==method and x['object']==ob]
   vals=[f1([sum(x[k] for x in rr if x['seed']==seed) for k in ['tp','fp','fn']]) for seed in SEEDS]
   ent[ob]={'mean':statistics.mean(vals),'sd':statistics.stdev(vals)}
  summary['external'].append(ent)
# Complete-object membership completion constrained to all existing relation TP/FP/FN.
# These abstract semantic keys are generated here; original corpus text is not inferred.
def allocate(total,lows,highs,tag):
 v=list(lows);left=total-sum(v);order=list(range(len(v)));rng(IDENTITY,tag).shuffle(order)
 assert 0<=left<=sum(h-l for h,l in zip(highs,lows)),(total,sum(lows),sum(highs))
 while left:
  for i in order:
   if v[i]<highs[i]:v[i]+=1;left-=1
   if not left:break
 return v
def choose(seq,n,tag):
 seq=list(seq);rng(IDENTITY,tag).shuffle(seq);return set(seq[:n])
def semantic_key(ds,doc,idx,gold=True):
 # Position/type/complete source tuple and label are explicit but wholly synthetic.
 off=0 if gold else 10000
 src=[(off+idx*12,off+idx*12+3,'Premise' if ds=='AAEC' else 'Fact')]
 if ds=='CDCP' and idx%4==0:src.append((off+idx*12+4,off+idx*12+7,'Fact'))
 target=(off+idx*12+8,off+idx*12+11,'Claim' if ds=='AAEC' else 'Policy')
 return json.dumps([doc,src,target,'Support' if ds=='AAEC' else 'Reason'],separators=(',',':'))
memberships=[];objectstats=[]
for ds in DS:
 pairs=[(seed,doc) for seed in SEEDS for doc in docs[ds]]
 bases=[old[ds,s,'t1_i0','relation',d] for s,d in pairs];ends=[old[ds,s,'t1_i1','relation',d] for s,d in pairs]
 risk=res['risk'][ds]['t1_i1']['relation']
 losses=allocate(risk['lost_tp'],[max(0,b[0]-e[0]) for b,e in zip(bases,ends)],[min(b[0],e[2]) for b,e in zip(bases,ends)],ds+'tploss')
 fpremove=allocate(risk['removed_fp'],[max(0,b[1]-e[1]) for b,e in zip(bases,ends)],[b[1] for b in bases],ds+'fpremove')
 totals=defaultdict(int)
 for z,(seed,doc) in enumerate(pairs):
  counts={m:old[ds,seed,m,'relation',doc] for m in ['t0_i0','t1_i0','t0_i1','t1_i1']};g=counts['t0_i0'][0]+counts['t0_i0'][2];gold=set(range(g));S={}
  S['t0_i0']=choose(gold,counts['t0_i0'][0],f'{ds}{doc}{seed}base')
  base=S['t0_i0']
  for method in ['t1_i0','t0_i1']:
   n=counts[method][0];loss=min(max(0,len(base)-n)+1,len(base),g-n);keep=choose(base,len(base)-loss,f'{ds}{doc}{seed}{method}keep')
   pool=gold-base;need=n-len(keep)
   if method=='t0_i1':
    common=choose(S['t1_i0']-base,min(round(need*.55),len(S['t1_i0']-base),need),f'{ds}{doc}{seed}common')
    extra=choose(pool-common,need-len(common),f'{ds}{doc}{seed}iextra');S[method]=keep|common|extra
   else:S[method]=keep|choose(pool,need,f'{ds}{doc}{seed}trecover')
  prev=S['t1_i0'];keep=choose(prev,len(prev)-losses[z],f'{ds}{doc}{seed}jointkeep');need=counts['t1_i1'][0]-len(keep)
  novel=gold-prev;preferred=(S['t0_i1']-prev);take=choose(preferred,min(len(preferred),round(need*.65)),f'{ds}{doc}{seed}preferred')
  S['t1_i1']=keep|take|choose(novel-take,need-len(take),f'{ds}{doc}{seed}jointnew')
  FP={m:set(range(counts[m][1])) for m in ['t0_i0','t1_i0','t0_i1']}
  remain=choose(FP['t1_i0'],len(FP['t1_i0'])-fpremove[z],f'{ds}{doc}{seed}fpkeep');add=counts['t1_i1'][1]-len(remain)
  FP['t1_i1']=remain|set(range(1000,1000+add))
  R_T=S['t1_i0']-base;R_I=S['t0_i1']-base
  fields={'training_only':len(R_T-R_I),'repair_only':len(R_I-R_T),'common':len(R_T&R_I),'combination_new':len(S['t1_i1']-base-R_T-R_I),'base_destroyed':len(base-S['t1_i1']),'t1_destroyed':len(prev-S['t1_i1']),'remaining_fn':len(gold-S['t1_i1']),'recovered_t1':len(S['t1_i1']-prev),'fp_removed':len(FP['t1_i0']-FP['t1_i1']),'fp_added':len(FP['t1_i1']-FP['t1_i0'])}
  totals.update({k:totals[k]+v for k,v in fields.items()})
  entry={'identity':IDENTITY,'dataset':ds,'document':doc,'seed':seed,'gold':[semantic_key(ds,doc,i) for i in sorted(gold)],'predictions':{},'evidence_type':'ASSIGNED_OBJECT_MEMBERSHIP_COMPLETION','scope':'relation objects only; endpoints synthetic, no reconstructed real document or complete predicted component graph'}
  for method in S:
   entry['predictions'][method]=[semantic_key(ds,doc,i) for i in sorted(S[method])]+[semantic_key(ds,doc,i,False) for i in sorted(FP[method])]
   assert len(S[method])==counts[method][0] and len(FP[method])==counts[method][1]
  memberships.append(entry)
  objectstats.append({'dataset':ds,'document':doc,'seed':seed,**fields})
 summary.setdefault('objects',[]).append({'dataset':ds,'doc_seed_pairs':len(pairs),**totals})
dump('object_memberships.json',memberships);csvout('object_transitions.csv',objectstats)
# Illustrative object cases chosen by a deterministic predicate, not called observed texts.
cases=[]
for category,predicate,key in [('common',lambda x:x['common']>0,'common'),('combination_new',lambda x:x['combination_new']>0,'combination_new'),('damage',lambda x:x['t1_destroyed']>0,'t1_destroyed')]:
 row=next(x for x in objectstats if predicate(x));rec=next(x for x in memberships if all(x[k]==row[k] for k in ['dataset','document','seed']))
 gold=set(rec['gold']);p={m:set(v)&gold for m,v in rec['predictions'].items()};base=p['t0_i0'];rt=p['t1_i0']-base;ri=p['t0_i1']-base
 cand=rt&ri if category=='common' else p['t1_i1']-base-rt-ri if category=='combination_new' else p['t1_i0']-p['t1_i1']
 target=sorted(cand)[0]
 cases.append({'category':category,'dataset':row['dataset'],'document':row['document'],'seed':row['seed'],'synthetic_object_key':target,'presence':{m:int(target in vals) for m,vals in rec['predictions'].items()},'evidence_type':'SYNTHETIC_OBJECT_CASE_NO_SOURCE_TEXT'})
dump('synthetic_object_cases.json',cases)
summary['cases']=cases
summary['generation_assumptions']={'augmentation':'40 independent synthetic sources per corpus; 4 shared attempts; 4 or 12 assigned factors; 2 accepted variants maximum; screening detection/false-alarm probabilities fixed in source','resources':'60% of combinatorial candidate upper bound is assigned as legal slots; fixed synthetic cost per candidate; no runtime timer or optimizer invoked','external':'Kawarada/UniASA-style placeholders use assigned Bernoulli recall/FP rates; not paper results, actual implementations or predictions','objects':'One arbitrarily constructed completion of existing relation counts and aggregate T1-to-joint risk totals; not inferred identities, not evidence of empirical overlap'}
dump('supplement_results.json',summary)
files=['augmentation_text_pairs.json','augmentation_screening.csv','resource_envelope.csv','budget_outcomes.csv','external_placeholders.csv','object_memberships.json','object_transitions.csv','synthetic_object_cases.json','supplement_results.json']
dump('supplement_manifest.json',{'identity':IDENTITY,'real_model_runs':0,'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':{n:hashlib.sha256((W/n).read_bytes()).hexdigest() for n in files}})
print(json.dumps({'augmentation':summary['augmentation'],'resources':summary['resources'],'budget_all':[x for x in summary['budget'] if x['group']=='all'],'external':summary['external'],'objects':summary['objects']},ensure_ascii=False,indent=2))
