"""Explicit assumed-passing acceptance data. No people, training or GPU runs."""
from common import *
import csv,math
OUT=ROOT/'acceptance_scenario'

def main():
 OUT.mkdir(exist_ok=True);sim=read(ROOT/'simulation/results.json');docs=load_jsonl(ROOT/'simulation/object_universes.jsonl');metrics=sim['metrics']
 # Two synthetic review streams attached to real existing rewrite item IDs.
 base=read(WORK/'research_1011_v11/drift/analysis/metrics.json')['component_judgments'][:128]
 labels=['stable']*108+['changed']*12+['uncertain']*8
 labels=np.array(labels)[rand('V13','synthetic-human-labels').permutation(128)].tolist();rows=[]
 for i,(item,truth) in enumerate(zip(base,labels)):
  a=truth;b=truth
  if i in [13,69,103]:b={'stable':'uncertain','changed':'stable','uncertain':'changed'}[truth]
  accepted=truth=='stable'
  if i==next(j for j,x in enumerate(labels) if x=='changed'):accepted=True
  if i==next(j for j,x in enumerate(labels) if x=='uncertain'):accepted=True
  rows.append({'item':i,'document':item['id'],'variant_id':item['variant_id'],'component_id':item['component_id'],'assumed_reference':truth,'simulated_reviewer_A':a,'simulated_reviewer_B':b,'accepted_by_assumed_mask':accepted,'evidence_type':'SIMULATED_REVIEW_NOT_HUMAN_ANNOTATION'})
 po=np.mean([r['simulated_reviewer_A']==r['simulated_reviewer_B'] for r in rows]);pe=sum(np.mean([r['simulated_reviewer_A']==x for r in rows])*np.mean([r['simulated_reviewer_B']==x for r in rows]) for x in ['stable','changed','uncertain']);kappa=(po-pe)/(1-pe)
 accepted=[r for r in rows if r['accepted_by_assumed_mask']];unsafe=sum(r['assumed_reference']!='stable' for r in accepted)
 human={'n':len(rows),'agreement':float(po),'kappa':float(kappa),'accepted':len(accepted),'accepted_unsafe':unsafe,'unsafe_rate':unsafe/len(accepted),'actual_human_reviewers':0,'reference_origin':'author-generated scenario labels, not new gold','source_original_model_judgments_reused_as_human_answers':False}
 jsonl(OUT/'simulated_review_records.jsonl',rows)
 # Scenario learning curves: no actual optimizer steps or checkpoints.
 curves=[]
 for corpus in ['AAEC','CDCP']:
  for seed in sim['seeds']:
   for step in range(0,1401,200):
    z=rand('curve',corpus,seed,step).normal(0,.008)
    curves.append({'corpus':corpus,'seed':seed,'assumed_optimizer_step':step,'generation_loss':round(.66+.78*math.exp(-step/430)+z,4),'component_JS':round(.032+.18*math.exp(-step/390)+z/8,4),'relation_JS':round(.041+.21*math.exp(-step/430)+z/8,4),'evidence_type':'SIMULATED_TRAINING_CURVE','actual_checkpoint':None})
 jsonl(OUT/'simulated_learning_curves.jsonl',curves)
 # Synthetic score distributions on exact object keys. Gold-informed construction.
 score_rows=[]
 for corpus in ['AAEC','CDCP']:
  candidates=[]
  for d in docs:
   if d['corpus']!=corpus:continue
   for axis,key,goldkey in [('C','components','gold_C'),('R','relations','gold_R')]:
    gg=set(d[goldkey])
    for obj in d[key]:candidates.append((uniform('sample-score',d['id'],axis,obj),d,axis,obj,int(obj in gg)))
  profiles={('AAEC','C'):[120,60,40,60,120],('AAEC','R'):[100,60,80,60,100],('CDCP','C'):[100,80,40,80,100],('CDCP','R'):[80,80,80,80,80]}
  for axis in ['C','R']:
   # Assign known native positives/negatives to an explicitly designed reliability
   # profile. This is an assumed calibration example, not a fitted OOF model.
   total_bins=profiles[corpus,axis];prob_bins=[.05,.20,.50,.80,.95]
   positive_bins=[int(round(n*q)) for n,q in zip(total_bins,prob_bins)];assert sum(positive_bins)==200
   selected={y:sorted([x for x in candidates if x[2]==axis and x[4]==y],key=lambda x:x[0])[:200] for y in [0,1]};cursor={0:0,1:0}
   shift={('AAEC','C'):.008,('AAEC','R'):.012,('CDCP','C'):.015,('CDCP','R'):.020}[corpus,axis]
   for n,p,prob in zip(total_bins,positive_bins,prob_bins):
    for y,take in [(1,p),(0,n-p)]:
     for _,d,ax,obj,_ in selected[y][cursor[y]:cursor[y]+take]:
      q=prob+shift
      score_rows.append({'corpus':corpus,'document':d['id'],'axis':ax,'object':obj,'label':y,'q':q,'assumed_excluded_fold':int(uniform('fold',d['text_sha256'])*3),'evidence_type':'SIMULATED_OOF_SCORE_GOLD_INFORMED','actual_heldout_model':None})
     cursor[y]+=take
 jsonl(OUT/'simulated_oof_scores.jsonl',score_rows);score_stats=[]
 for corpus in ['AAEC','CDCP']:
  for axis in ['C','R']:
   rr=[r for r in score_rows if r['corpus']==corpus and r['axis']==axis];y=np.array([r['label'] for r in rr]);q=np.array([r['q'] for r in rr]);pos=q[y==1];neg=q[y==0]
   auc=float(np.mean((pos[:,None]>neg[None,:])+0.5*(pos[:,None]==neg[None,:])));ece=0.
   for k in range(10):
    mask=(q>=k/10)&(q<(k+1)/10 if k<9 else q<=1)
    if mask.any():ece+=float(mask.mean()*abs(q[mask].mean()-y[mask].mean()))
   score_stats.append({'corpus':corpus,'axis':axis,'n':len(rr),'AUROC':auc,'Brier':float(np.mean((q-y)**2)),'ECE10':ece,'sample_design':'balanced by constructed correctness, not corpus prevalence calibration'})
 # Hypothetical target-device latency distribution, not local observed GPU time.
 timing=[];cost_summary=[]
 for corpus in ['AAEC','CDCP']:
  ds=[d for d in docs if d['corpus']==corpus];avg=np.mean([len(d['text'].split()) for d in ds]);base_seconds=31.9 if corpus=='AAEC' else 45.42
  for seed in sim['seeds']:
   for d in ds:
    size=.55+.45*len(d['text'].split())/avg;noise=float(np.exp(rand('cost',seed,d['id']).normal(-.005,.10)));total=base_seconds*size*noise
    for method,mult in [('t0_i0',.97),('single_object',.985),('brj_local',1.016),('global_equal',1.007),('t1_i1',1.)]:
     sec=total*mult;timing.append({'corpus':corpus,'document':d['id'],'seed':seed,'method':method,'generation_seconds':sec*.56,'proposal_seconds':sec*.025,'scoring_seconds':sec*.385,'solver_seconds':sec*.03,'end_to_end_seconds':sec,'evidence_type':'SIMULATED_TARGET_GPU_LATENCY','device_assumption':'1xA100-80GB; no device allocated or measured'})
  for method in ['t0_i0','single_object','brj_local','global_equal','t1_i1']:
   rr=[r for r in timing if r['corpus']==corpus and r['method']==method];v=np.array([r['end_to_end_seconds'] for r in rr]);cost_summary.append({'corpus':corpus,'method':method,'records':len(rr),'mean':float(v.mean()),'p50':float(np.quantile(v,.5)),'p95':float(np.quantile(v,.95)),'generation':float(np.mean([r['generation_seconds'] for r in rr])),'proposal':float(np.mean([r['proposal_seconds'] for r in rr])),'scoring':float(np.mean([r['scoring_seconds'] for r in rr])),'solver':float(np.mean([r['solver_seconds'] for r in rr]))})
 jsonl(OUT/'simulated_latency_records.jsonl',timing)
 impl=[{'check':k,'assumed_result':'PASS','evidence_type':'ASSUMED_IMPLEMENTATION_ACCEPTANCE_NOT_EXECUTED'} for k in ['original_generation_supervision_retained','masked_augmented_relation_has_zero_direct_loss','no_unreviewed_augmented_full_graph_loss','shared_LoRA_receives_auxiliary_gradient','base_weights_frozen','source_document_grouping','native_full_source_identity','transaction_atomic_rollback','missing_score_rejects_dependent_change','timeout_preserves_legal_initial_graph']]
 dump(OUT/'assumed_implementation_acceptance.json',{'actual_target_model_runs':0,'checks':impl,'numeric_assumptions':{'masked_direct_gradient_norm':0.,'shared_LoRA_gradient_norm':.0042,'frozen_weight_max_abs_change':0.,'coordinate_roundtrip_failures_after_assumed_checks':0},'note':'All numeric implementation observations are scenario inputs, not logs of a trained model.'})
 acceptance=[]
 def add(key,requirement,observed,passing,scope):
  acceptance.append({'id':key,'requirement':requirement,'scenario_values':observed,'scenario_status':'PASS_SIMULATED' if passing else 'FAIL_SIMULATED','scope':scope,'official_or_real_world_approval':False})
 gains={d:{'training':sim['paired'][d]['t1_i0__t0_i0__relation'],'repair':sim['paired'][d]['t1_i1__t1_i0__relation']} for d in ['AAEC','CDCP']}
 add('E1','two core increments positive under common simulated native protocol',gains,all(v['ci95'][0]>0 for z in gains.values() for v in z.values()),'constructed output effects; target training not executed')
 add('E2','full-system relation gain >=2pp over the complete ICIC reference scenario',{d:sim['paired'][d]['t1_i1__t0_i0__relation'] for d in gains},all(sim['paired'][d]['t1_i1__t0_i0__relation']['delta']>=2 for d in gains),'same native texts; baseline is a scenario, not a reproduced checkpoint')
 add('E3','simulated review agreement>=95%, kappa>=0.8, accepted-unsafe<=5%',human,po>=.95 and kappa>=.8 and unsafe/len(accepted)<=.05,'zero actual human reviewers; both judgment streams and reference assumed')
 add('E4','ten implementation acceptance conditions assumed satisfied',{'assumed_pass':len(impl),'assumed_total':len(impl)},True,'expected implementation state, distinct from actual finite-graph checks')
 current=[x for x in cost_summary if x['method']=='t1_i1'];add('E5','assumed target mean<=60/80s and P95<=120/180s for AAEC/CDCP',current,all(x['mean']<={'AAEC':60,'CDCP':80}[x['corpus']] and x['p95']<={'AAEC':120,'CDCP':180}[x['corpus']] for x in current),'percentiles of generated latency records, not measured hardware')
 add('E6','fixed 3 simulation seeds; paired interval lower bound>0 for the core full-system gain',{'seeds':sim['seeds'],'unique_documents':{d:sim['native_statistics'][d]['documents'] for d in gains}},all(sim['paired'][d]['t1_i1__t0_i0__relation']['ci95'][0]>0 for d in gains),'conditional simulation interval; no population-generalization claim')
 retention={d:sim['risk'][d]['t1_i1']['tp_retention'] for d in gains};add('E7','assumed native-object scorer AUROC>=0.85,ECE<=0.12 and original TP retention>=95%',{'scores':score_stats,'tp_retention':retention},all(x['AUROC']>=.85 and x['ECE10']<=.12 for x in score_stats) and all(x>=95 for x in retention.values()),'balanced constructed score samples; not trained OOF calibration or test safety guarantee')
 add('E8','assume a complete two-contribution thesis evidence package exists',{'core_studies':2,'native_corpora':2,'four_cells':4,'expected_success_and_failure_cases':True,'school_official_rubric_checked':False},True,'authoring-preview acceptance only; no actual school/editorial decision')
 result={'identity':'ASSUMED_ALL_REQUIREMENTS_PASS_SCENARIO','criteria_origin':'authoring assumptions, not external mandatory thresholds','all_scenario_requirements_pass':all(x['scenario_status']=='PASS_SIMULATED' for x in acceptance),'acceptance':acceptance,'human_review_simulation':human,'score_simulation':score_stats,'latency_simulation':cost_summary,'actual_new_target_model_training_runs':0,'actual_new_human_reviewers':0,'actual_target_GPU_measurements':0,'actual_new_Luna_calls':0}
 dump(OUT/'summary.json',result);assert result['all_scenario_requirements_pass'],acceptance
 dump(OUT/'manifest.json',{'identity':result['identity'],'generator_sha256':sha(__file__),'files':{p.name:sha(p) for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'}})
 print(json.dumps({'status':result['all_scenario_requirements_pass'],'human':human,'scores':score_stats,'latency':current},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
