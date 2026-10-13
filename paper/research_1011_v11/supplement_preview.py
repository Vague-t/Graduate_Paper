"""Explicit synthetic completion and cost assumptions; never invokes a model."""
from pathlib import Path
import csv,hashlib,importlib.util,json,math,sys
import numpy as np
R=Path(__file__).resolve().parent;W=R.parent;OUT=R/'simulation'
OUT.mkdir(exist_ok=True)
def read(p):return json.loads(Path(p).read_text())
def dump(name,x): (OUT/name).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n')
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
spec=importlib.util.spec_from_file_location('legacy_sim',W/'_revision_1010_v7/generate_scenario.py');old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
base=read(W/'_revision_1010_v7/scenario_results.json')
source_rows=list(csv.DictReader((W/'_revision_1010_v7/document_counts.csv').open()))
counts={(r['dataset'],r['object'],int(r['seed']),r['method'],r['document']):(int(r['tp']),int(r['fp']),int(r['fn'])) for r in source_rows}
membership=[];overlap=[];paired=[];stress=[]
methods=['t0_i0','t1_i0','t0_i1','t1_i1']
for di,(ds,spec) in enumerate(old.DATASETS.items()):
 for obj in ['component','relation']:
  lo,hi=spec[obj+'_range'];ns=old.rng(ds,obj,'gold').integers(lo,hi+1,spec['docs']);docs=np.repeat(np.arange(spec['docs']),ns);N=len(docs)
  fd=np.repeat(np.arange(spec['docs']),max(20,hi));NF=len(fd);members=old.rng(ds,obj,'members').choice([1,2,3],N,p=[.60,.27,.13])
  for si,seed in enumerate(old.SEEDS):
   latent=old.rng(ds,obj,seed,'shared').normal(size=N)
   if ds=='CDCP' and obj=='relation':latent+=(members-1)*.33
   flatent=old.rng(ds,obj,seed,'shared-fp').normal(size=NF);sets={}
   for method in methods:
    jitter=old.rng(ds,obj,method,'jitter').normal(0,.0018,3);jitter-=jitter.mean();target=old.TARGETS[method][di][obj=='relation']+[-.004,.001,.003][si]+jitter[si]
    ntp=int(round(N*(target-.015)));nfp=int(round(ntp*(1/(target+.015)-1)))
    t=set(map(int,np.argsort(latent+old.rng(ds,obj,seed,method,'gold-noise').normal(0,.18,N))[:ntp]));f=set(map(int,np.argsort(flatent+old.rng(ds,obj,seed,method,'fp-noise').normal(0,.22,NF))[:nfp]));sets[method]=(t,f)
    for d in range(spec['docs']):
     a=sum(docs[i]==d for i in t);b=sum(fd[i]==d for i in f);key=(ds,obj,seed,method,f'SIM-{ds}-{d+1:03d}')
     assert counts[key]==(a,b,int(ns[d])-a)
   for isgold,pool,docids in [(True,range(N),docs),(False,range(NF),fd)]:
    for i in pool:
     flags=[i in sets[m][0 if isgold else 1] for m in methods]
     membership.append({'dataset':ds,'object':obj,'seed':seed,'document':f'SIM-{ds}-{int(docids[i])+1:03d}','object_id':('G' if isgold else 'F')+str(i),'gold':isgold,**dict(zip(methods,flags))})
   p00,p10,p01,p11=[sets[m][0] for m in methods];rt=p10-p00;ri=p01-p00
   overlap.append({'dataset':ds,'object':obj,'seed':seed,'training_only':len(rt-ri),'inference_only':len(ri-rt),'shared':len(rt&ri),'combination_new':len(p11-p00-p10-p01),'remaining_FN':N-len(p11),'lost_vs_T0':len(p00-p11),'lost_vs_T1':len(p10-p11)})
  # New comparisons from exactly the preserved v7 document counts.
  indices=old.rng(ds,'bootstrap').integers(0,spec['docs'],size=(2000,spec['docs']))
  for a,b in [('full_data_i0','qos_i0'),('head_i0','full_data_i0'),('t1_i0','head_i0')]:
   arrays={m:[np.array([counts[ds,obj,s,m,f'SIM-{ds}-{d+1:03d}'] for d in range(spec['docs'])]) for s in old.SEEDS] for m in [a,b]}
   boot={m:np.mean([old.f1(v[indices].sum(axis=1)) for v in arrays[m]],axis=0) for m in [a,b]}
   paired.append({'dataset':ds,'object':obj,'comparison':a+' - '+b,'delta':base['metrics'][ds][a][obj]['mean']-base['metrics'][ds][b][obj]['mean'],'ci95':np.quantile(boot[a]-boot[b],[.025,.975]).tolist(),'basis':'preserved_v7_synthetic_counts'})
 # Stress relation counts: generate explicit per-document counts for effects incl zero/negative.
 for mechanism,bm,shifts in [('paired','head_i0',[-.5,0,1.2]),('component_change','relation_only',[-.5,0,2.3]),('local_vs_global','global_equal',[-1.5,-.5,.5])]:
  for shift in shifts:
   values=[]
   for seed in old.SEEDS:
    rows=[counts[ds,'relation',seed,bm,f'SIM-{ds}-{d+1:03d}'] for d in range(spec['docs'])];tot=np.array(rows).sum(axis=0);G=int(tot[0]+tot[2]);target=float(old.f1(tot))/100+shift/100
    tp=int(round(G*max(.001,target-.015)));fp=int(round(tp*(1/max(.001,target+.015)-1)));gold=np.array([a+c for a,b,c in rows]);rr=old.rng(ds,mechanism,shift,seed)
    gold_doc=np.repeat(np.arange(len(gold)),gold);rr.shuffle(gold_doc);t=np.bincount(gold_doc[:tp],minlength=len(gold));f=np.bincount(rr.integers(0,len(gold),fp),minlength=len(gold));a=np.stack([t,f,gold-t],axis=1)
    for d,row in enumerate(a):stress.append({'dataset':ds,'mechanism':mechanism,'assumed_shift_pp':shift,'seed':seed,'document':f'SIM-{ds}-{d+1:03d}','tp':int(row[0]),'fp':int(row[1]),'fn':int(row[2])})
    values.append(float(old.f1(a.sum(axis=0)))-float(old.f1(tot)))
   paired.append({'dataset':ds,'object':'relation','comparison':mechanism,'assumed_shift_pp':shift,'actual_integer_delta':float(np.mean(values)),'basis':'new_synthetic_stress_counts'})
dump('four_cell_membership.json',{'status':'SIMULATED_ARTIFICIAL_IDENTITIES_NOT_NATIVE_TEXT_GRAPHS','methods':methods,'rows':membership})
dump('four_cell_overlap.json',{'status':'SIMULATED_COMPATIBLE_WITH_V7_COUNTS','rows':overlap})
dump('additional_paired_and_stress.json',paired);dump('stress_document_counts.json',stress)
# OOF error-chain simulation: these are invented document records, not Luna extrapolation.
oof=[]
for ds,n in [('AAEC',320),('CDCP',580)]:
 for i in range(n):
  rr=old.rng('v11-OOF',ds,i);g=int(rr.integers(6,24));hits=int(rr.binomial(g,.54 if ds=='AAEC' else .47));missing=g-hits
  parts=rr.multinomial(missing,[.38,.21,.13,.17,.11]);oof.append({'id':f'SIM-OOF-{ds}-{i+1:03d}','dataset':ds,'fold':i%3,'gold_R':g,'initial_TP':hits,**dict(zip(['missing_endpoint_span','wrong_endpoint_type','complete_slot_absent','score_or_label_error','budget_or_search'],map(int,parts)))})
dump('oof_error_records.json',{'status':'SIMULATED_NOT_OOF_MODEL_RUNS','rows':oof})
# Unnamed comparator scenarios are never assigned to a published system.
external=[];external_summary=[]
for di,(ds,spec) in enumerate(old.DATASETS.items()):
 for method,targets in [('SIM_encoder',[(.797,.566),(.716,.510)]),('SIM_generator',[(.817,.613),(.744,.579)])]:
  summary={'dataset':ds,'method':method,'status':'UNNAMED_SYNTHETIC_COMPARATOR_NOT_PUBLISHED_PERFORMANCE'}
  for oi,obj in enumerate(['component','relation']):
   means=[]
   for si,seed in enumerate(old.SEEDS):
    gold=np.array(base['gold_counts'][ds][obj]);N=int(gold.sum());target=targets[di][oi]+[-.004,.001,.003][si];tp=int(round(N*(target-.015)));fp=int(round(tp*(1/(target+.015)-1)));rr=old.rng(ds,method,obj,seed)
    docids=np.repeat(np.arange(len(gold)),gold);rr.shuffle(docids);t=np.bincount(docids[:tp],minlength=len(gold));f=np.bincount(rr.integers(0,len(gold),fp),minlength=len(gold));a=np.stack([t,f,gold-t],axis=1);means.append(float(old.f1(a.sum(axis=0))))
    for d,row in enumerate(a):external.append({'dataset':ds,'method':method,'object':obj,'seed':seed,'document':f'SIM-{ds}-{d+1:03d}','tp':int(row[0]),'fp':int(row[1]),'fn':int(row[2])})
   summary[obj]={'mean':float(np.mean(means)),'sd':float(np.std(means,ddof=1))}
  external_summary.append(summary)
dump('external_comparator_counts.json',{'rows':external,'summary':external_summary,'status':'SIMULATED_UNNAMED_ONLY'})
# Measured slot-building observations, followed by explicit throughput/memory assumptions.
cov=read(R/'candidate/evaluation/coverage.json');cost=[]
for ds in ['argunsc','casimedicos','cdcp']:
 for layer in ['A_original','B_parse_components','C_separate_extraction','D_boundary_and_joint']:
  rows=[r for r in cov['by_document'] if r['corpus']==ds and r['layer']==layer];slots=np.array([r['cost']['slots_before_cap'] for r in rows]);C=np.array([r['cost']['component_candidates'] for r in rows]);O=C+slots*2
  cost.append({'corpus':ds,'layer':layer,'n':len(rows),'pre_slots_mean':float(slots.mean()),'pre_slots_P95':float(np.quantile(slots,.95)),'post_slots_mean':float(np.mean([r['cost']['slots_after_cap'] for r in rows])),'enumeration_ms_mean_measured':float(np.mean([r['cost']['slot_construction_seconds_with_tracemalloc'] for r in rows])*1000),'allocation_MiB_P95_measured':float(np.quantile([r['cost']['python_allocation_peak_bytes'] for r in rows],.95)/2**20),'score_seconds_mean_estimated_at_500_2000_10000':[float(O.mean()/q) for q in [500,2000,10000]],'score_seconds_P95_estimated_at_2000':float(np.quantile(O,.95)/2000),'object_storage_MiB_estimated_512B':float(O.max()*512/2**20)})
dump('candidate_cost_estimates.json',{'status':'MEASURED_COUNTS_PLUS_UNCALIBRATED_ASSUMED_THROUGHPUT','assumptions':{'positive_labels':2,'score_objects_per_second':[500,2000,10000],'bytes_per_object':512,'includes':'scoring numeric throughput illustration only; no model load/generation/encoding/API cost'},'rows':cost})
# Exact relaxed combinatorial bounds for the formal all-types pool.
bounds=[]
for m in [16,32,64]:
 for ds,q in [('AAEC',3),('CDCP',5)]:
  slots=m*(m-1)*q*q if ds=='AAEC' else sum(math.comb(m,k)*(m-k)*q**(k+1) for k in [1,2,3]);bounds.append({'dataset':ds,'spans':m,'types':q,'loose_slot_bound':slots,'label_objects':2*slots,'preflight_exceeds_5M':slots>5000000,'score_hours_at_2000':2*slots/2000/3600,'object_GiB_at_512B':2*slots*512/2**30})
dump('formal_prepruning_bounds.json',{'status':'COMBINATORIAL_UPPER_BOUND_COST_NOT_MEASUREMENT','rows':bounds})
config={'status':'COMPLETE_PREVIEW_PARAMETERS_NOT_DEPLOYED_OR_TRAINED','config_id':'AM-V11-PREVIEW-20261011','models':{'generator':'Qwen/Qwen2.5-7B-Instruct','augmenter':'Qwen/Qwen2.5-7B-Instruct','semantic_verifier':'Qwen/Qwen2.5-7B-Instruct','encoder':'Qwen/Qwen2.5-7B-Instruct','span_head':'linear_start_end_bce_on_frozen_Qwen_hidden','score_head':'MLP_2layers_1024_hidden_dropout0.1_sigmoid','tokenizer':'Qwen/Qwen2.5-7B-Instruct','artifact_revisions':'resolve and hash at real-run startup; no checkpoint was fabricated'},'training':{'lora_rank':16,'lora_alpha':32,'lora_dropout':.05,'optimizer':'AdamW','lr':.0002,'weight_decay':.01,'betas':[.9,.999],'eps':1e-8,'epochs':5,'warmup_ratio':.03,'gradient_clip':1,'microbatch_sources':4,'accumulation':8,'precision':'bfloat16','max_input_tokens':4096,'max_output_tokens':2048,'context':8192,'seeds':[17,29,43],'rho':1.0,'lambda_sup':1.0,'lambda_C':.5,'lambda_R':.5,'coefficient_selection':'fixed preview assumptions; train-side alternative grid 0.25/0.5/1.0, selected once before held-out evaluation','span_head_lr':.001,'score_head_lr':.001,'score_head_epochs':10},'generation':{'temperature':.7,'top_p':.9,'max_variants':2,'attempts':4,'seed':17,'eval_temperature':0,'eval_graphs':2},'calibration':{'method':'Platt logistic by object family','fit_train_fraction':.8,'calibration_fraction':.1,'policy_fraction':.1,'crossfit_folds':3},'hardware_assumption':{'GPU':'one NVIDIA A100 80GB','CPU_threads':4,'RAM_GiB':64,'actual_allocated':False},'solver':{'library':'SciPy 1.13.1 HiGHS milp','presolve':True,'mip_rel_gap':0,'aaec_seconds':3,'cdcp_seconds':5,'large_seconds':[60,90],'component_cumulative_edits':24,'relation_cumulative_edits':96,'attempts':128,'accepts':12,'delta':.01,'numeric_tol':1e-9,'component_and_relation_kappa':1,'global_edits':'net, not cumulative'},'candidates':{'supplement_spans':64,'max_tokens':64,'max_new_sources':3,'supplement_slots':4096,'preflight_slot_limit':5000000,'score_object_batch':4096,'estimated_object_bytes':512,'protected_overflow':'fail document with explicit status; retain denominator'},'ICIC_provenance':'Qwen backbone, LoRA and AdamW writing convention; additional concrete settings are preview assumptions, not claims about ICIC hardware or exact training setup','real_luna_protocol':'separate protocol.json, gpt-5.6-luna low; decoding temperature, snapshot and token usage unavailable'}
dump('preview_config.json',config)
config['training']['paired_auxiliary_heads']={'layers':2,'hidden':1024,'activation':'GELU','dropout':.1,'lr':.0002,'component_classes':'native 3 or 5','relation_classes':'native 2 plus NONE','input':'shared input-side hidden states; no gold answer tokens','stop_gradient':False,'updated_parameters':'shared LoRA and both auxiliary heads; base weights frozen; type-gated branch trained by generation loss'}
config['training']['lora_target_modules']=['q_proj','k_proj','v_proj','o_proj']
config['generation']['evaluation_prompt_variants']=2
dump('preview_config.json',config)
assert config['training']['microbatch_sources']*config['training']['accumulation']==32
assert config['training']['max_input_tokens']+config['training']['max_output_tokens']<=config['training']['context']
assert config['candidates']['supplement_slots']<config['candidates']['preflight_slot_limit']
dump('config_validation.json',{'status':'PASS_STATIC_ONLY','checks':['source_batch32','context_budget','positive_budgets','explicit_hardware_assumption','real_and_preview_model_identities_separate'],'training_run':False})
dump('manifest.json',{'status':'SIMULATED_PREVIEW_AND_EXPLICIT_COST_ESTIMATES','new_real_training_runs':0,'base_generator_sha256':sha(W/'_revision_1010_v7/generate_scenario.py'),'base_counts_sha256':sha(W/'_revision_1010_v7/document_counts.csv'),'new_generator_sha256':sha(__file__),'membership_rows':len(membership),'all_four_cell_document_counts_exactly_match_v7':True,'oof_documents':len(oof),'stress_rows':len(stress),'files':{p.name:sha(p) for p in OUT.glob('*.json') if p.name!='manifest.json'}})
print(json.dumps({'membership':len(membership),'oof':len(oof),'stress':len(stress),'four_cell_counts':'exactly match preserved v7','status':'SIMULATED_ONLY'}))
