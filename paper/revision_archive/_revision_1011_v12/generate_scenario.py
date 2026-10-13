"""Explicit positive authoring scenarios; no model, corpus graph or solver inference.

Two artificial metric universes are independent. ICIC-compatible numbers target
the old report scale; strict native numbers require a new baseline. They are
not conversion/projection of one graph and not an empirical superiority claim.
"""
from pathlib import Path
import csv,json,hashlib,sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'research_0920/vendor'))
import numpy as np
W=Path(__file__).resolve().parent;OUT=W/'simulation';OUT.mkdir(exist_ok=True)
SEEDS=[17,29,43];SPECS={'AAEC':(80,(12,29),(8,22)),'CDCP':(148,(5,15),(3,10))}
# Entries: AAEC C/R, CDCP C/R, percentages. Chosen authoring inputs only.
STRICT={
 't0_i0':[83.70,64.40,76.45,36.90],
 'original_heads_i0':[83.90,64.90,76.60,37.25],
 'plain_i0':[83.85,64.85,76.60,37.20],
 'qos_i0':[84.00,65.20,76.80,37.55],
 'simple_data_i0':[84.10,65.45,76.90,37.75],
 'head_i0':[84.25,65.95,77.15,38.05],
 't1_i0':[84.50,66.60,77.50,38.50],
 'full_filter_i0':[84.49,66.57,77.48,38.48],
 'random_i0':[84.48,66.52,77.48,38.44],
 't0_i1':[84.35,65.95,77.10,38.30],
 'mcr_t1':[84.10,64.85,77.10,36.80],
 'br_c':[84.10,65.65,77.10,37.55],
 'relation_only':[84.10,66.20,77.10,38.00],
 'sequential':[84.70,66.95,77.70,38.95],
 'single_object':[84.98,67.58,78.10,39.62],
 'brj_local':[85.10,67.72,78.23,39.82],
 't1_i1':[85.20,67.80,78.30,39.90],
 'uncalibrated':[85.12,66.45,78.21,38.65],
 'missing_as_low':[84.83,66.55,78.02,38.75],
 'no_risk_guard':[85.25,68.00,78.35,40.06],
 'global_equal':[85.28,67.95,78.35,40.05],
 'global_long':[85.40,68.10,78.40,40.20],
 'regenerate':[84.75,66.80,77.85,39.00],
 'external_encoder':[83.50,64.20,76.50,38.20],
 'external_generator':[84.80,67.10,77.90,40.00]}
COMPAT={m:[*v] for m,v in STRICT.items() if m in ['t0_i0','t1_i0','t0_i1','t1_i1']}
COMPAT.update(t0_i0=[83.71,64.83,76.45,38.17],t1_i0=[84.50,66.95,77.50,39.90],t0_i1=[84.35,66.35,77.10,40.05],t1_i1=[85.20,68.20,78.30,41.50])
LABELS={'t0_i0':'ICIC继承配置 T0/I0','original_heads_i0':'仅原文辅助头','plain_i0':'普通增强＋同一辅助监督','qos_i0':'QOS式适配＋同一辅助监督','simple_data_i0':'可靠对应＋辅助监督，无成对项','head_i0':'同数据＋组件成对项','t1_i0':'T1/I0：组件及关系成对学习','full_filter_i0':'完整筛选替代因素掩码','random_i0':'匹配随机中心','t0_i1':'T0/I1：仅新修正','mcr_t1':'T1的MCR初始图','br_c':'BR-C','relation_only':'RelationOnly','sequential':'组件优先分步','single_object':'单对象闭合','brj_local':'集合局部BR-J','t1_i1':'T1/I1：完整框架','uncalibrated':'取消概率校准','missing_as_low':'缺失分数当低分','no_risk_guard':'取消风险阈值','global_equal':'全局ILP等预算','global_long':'全局ILP大预算','regenerate':'等token重生成'}
LABELS.update(external_encoder='匿名编码式对照',external_generator='匿名生成式对照')
def rng(*p):return np.random.default_rng(int(hashlib.sha256('|'.join(map(str,p)).encode()).hexdigest()[:16],16))
def f1(a):
 a=np.asarray(a);den=2*a[...,0]+a[...,1]+a[...,2];return np.divide(200*a[...,0],den,out=np.zeros_like(den,dtype=float),where=den>0)
def dump(name,v):(OUT/name).write_text(json.dumps(v,ensure_ascii=False,indent=2)+'\n')
def main():
 arr={};sets={};raw=[];object_rows=[];metrics={};risk={};paired={};interactions={};member_counts=[];strata=[];gold={}
 for protocol,targets in [('strict_native',STRICT),('icic_compatible_target',COMPAT)]:
  for di,(ds,(nd,cr,rr)) in enumerate(SPECS.items()):
   for oi,obj in enumerate(['component','relation']):
    # Same synthetic sizes across protocols, independent objects and predictions.
    lo,hi=[cr,rr][oi];ns=rng('V12',ds,obj,'gold').integers(lo,hi+1,nd);gid=np.repeat(np.arange(nd),ns);N=len(gid);fid=np.repeat(np.arange(nd),max(20,hi));NF=len(fid)
    gold[ds,obj]=ns;arity=rng('V12',protocol,ds,obj,'arity').choice([1,2,3],N,p=[.60,.27,.13]);farity=rng('V12',protocol,ds,obj,'farity').choice([1,2,3],NF,p=[.6,.27,.13])
    for si,seed in enumerate(SEEDS):
     latent=rng('V12',protocol,ds,obj,seed,'true').normal(size=N);fl=rng('V12',protocol,ds,obj,seed,'false').normal(size=NF)
     if ds=='CDCP' and obj=='relation':latent+=(arity-1)*.30
     for method,vals in targets.items():
      ref='mcr_t1' if protocol=='strict_native' and obj=='component' and method in ['br_c','relation_only'] else method
      jitter=rng('V12',protocol,ds,obj,ref,'jitter').normal(0,.0011,3);jitter-=jitter.mean();target=targets[ref][di*2+oi]/100+[-.003,.0005,.0025][si]+jitter[si]
      recall=target-.012;precision=target+.012;ntp=int(round(N*recall));nfp=int(round(ntp*(1/precision-1)))
      noise=.28 if method=='no_risk_guard' else .085 if method in ['single_object','brj_local','t1_i1','global_equal','global_long'] else .11
      tr=set(map(int,np.argsort(latent+rng('V12',protocol,ds,obj,seed,ref,'tn').normal(0,noise,N))[:ntp]));fr=set(map(int,np.argsort(fl+rng('V12',protocol,ds,obj,seed,ref,'fn').normal(0,noise,NF))[:nfp]))
      sets[protocol,ds,obj,seed,method]=(tr,fr);tp=np.bincount(gid[list(tr)],minlength=nd);fp=np.bincount(fid[list(fr)],minlength=nd);a=np.stack([tp,fp,ns-tp],axis=1);arr[protocol,ds,obj,seed,method]=a
      for doc,(t,p,n) in enumerate(a):raw.append({'protocol':protocol,'dataset':ds,'document':f'SIM12-{ds}-{doc+1:03d}','seed':seed,'method':method,'object':obj,'tp':int(t),'fp':int(p),'fn':int(n),'evidence_type':'SIMULATED_COUNT_OBJECTS'})
      object_rows.append({'protocol':protocol,'dataset':ds,'object':obj,'seed':seed,'method':method,'gold_n':N,'gold_document':gid.tolist(),'false_document':fid.tolist(),'true_ids':sorted(tr),'false_ids':sorted(fr)})
      if protocol=='strict_native' and ds=='CDCP' and obj=='relation' and method in ['t0_i0','t1_i0','t0_i1','t1_i1']:
       for k in [1,2,3]:
        t=sum(arity[x]==k for x in tr);p=sum(farity[x]==k for x in fr);n=int((arity==k).sum())-t;strata.append({'method':method,'seed':seed,'arity':k,'tp':int(t),'fp':int(p),'fn':int(n)})
   for m in targets:
    metrics.setdefault(protocol,{}).setdefault(ds,{})[m]={}
    for obj in ['component','relation']:
     totals=[arr[protocol,ds,obj,s,m].sum(axis=0).tolist() for s in SEEDS];v=[float(f1(a)) for a in totals];metrics[protocol][ds][m][obj]={'mean':float(np.mean(v)),'sd':float(np.std(v,ddof=1)),'seeds':v,'counts':totals}
   indices=rng('V12',protocol,ds,'boot').integers(0,nd,size=(2000,nd))
   for obj in ['component','relation']:
    b={m:np.mean([f1(arr[protocol,ds,obj,s,m][indices].sum(axis=1)) for s in SEEDS],axis=0) for m in targets}
    comparisons=[('t1_i1','t0_i0'),('t1_i0','t0_i0'),('t0_i1','t0_i0'),('t1_i1','t1_i0'),('t1_i1','t0_i1')]
    if protocol=='strict_native':comparisons += [('simple_data_i0','qos_i0'),('head_i0','simple_data_i0'),('t1_i0','head_i0'),('full_filter_i0','t1_i0'),('random_i0','t1_i0'),('t1_i1','single_object'),('brj_local','single_object'),('t1_i1','relation_only'),('global_equal','brj_local'),('t1_i1','missing_as_low'),('t1_i1','uncalibrated')]
    for a,c in comparisons:
     dd=b[a]-b[c];point=metrics[protocol][ds][a][obj]['mean']-metrics[protocol][ds][c][obj]['mean'];paired.setdefault(protocol,{}).setdefault(ds,{})[a+'__'+c+'__'+obj]={'delta':point,'ci95':np.quantile(dd,[.025,.975]).tolist()}
    dd=b['t1_i1']-b['t1_i0']-b['t0_i1']+b['t0_i0'];point=metrics[protocol][ds]['t1_i1'][obj]['mean']-metrics[protocol][ds]['t1_i0'][obj]['mean']-metrics[protocol][ds]['t0_i1'][obj]['mean']+metrics[protocol][ds]['t0_i0'][obj]['mean'];interactions.setdefault(protocol,{}).setdefault(ds,{})[obj]={'value':point,'ci95':np.quantile(dd,[.025,.975]).tolist()}
    for seed in SEEDS:
     a=sets[protocol,ds,obj,seed,'t0_i0'][0];b1=sets[protocol,ds,obj,seed,'t1_i0'][0];c=sets[protocol,ds,obj,seed,'t0_i1'][0];d=sets[protocol,ds,obj,seed,'t1_i1'][0];N=sum(gold[ds,obj]);v={'baseline':len(a),'both_only':len((b1-a)&(c-a)),'training_only':len((b1-a)-(c-a)),'repair_only':len((c-a)-(b1-a)),'neither_single_but_combined':len(d-(a|b1|c)),'single_recovery_lost_in_combined':len(((b1|c)-a)-d),'baseline_lost_combined':len(a-d)}
     member_counts.append({'protocol':protocol,'dataset':ds,'object':obj,'seed':seed,**v})
   if protocol=='strict_native':
    for m in ['sequential','single_object','brj_local','t1_i1','global_equal','no_risk_guard']:
     v={'recovered':0,'lost_tp':0,'removed_fp':0,'added_fp':0,'base_tp':0,'worse_documents':0,'document_seed_pairs':nd*3}
     for s in SEEDS:
      bt,bf=sets[protocol,ds,'relation',s,'mcr_t1'];at,af=sets[protocol,ds,'relation',s,m]
      for k,n in [('recovered',len(at-bt)),('lost_tp',len(bt-at)),('removed_fp',len(bf-af)),('added_fp',len(af-bf)),('base_tp',len(bt))]:v[k]+=n
      v['worse_documents']+=int((f1(arr[protocol,ds,'relation',s,m])-f1(arr[protocol,ds,'relation',s,'mcr_t1'])< -1e-9).sum())
     v['tp_retention']=100*(1-v['lost_tp']/v['base_tp']);risk.setdefault(ds,{})[m]=v
 with (OUT/'document_counts.csv').open('w') as f:
  wr=csv.DictWriter(f,fieldnames=list(raw[0]));wr.writeheader();wr.writerows(raw)
 with (OUT/'object_membership.jsonl').open('w') as f:
  for row in object_rows:f.write(json.dumps(row,separators=(',',':'))+'\n')
 result={'evidence_type':'SIMULATED_POSITIVE_AUTHORING_SCENARIO_NOT_MODEL_RESULTS_OR_FORECAST','protocols':{'strict_native':'new assumed re-evaluation including complete native CDCP hyperedges','icic_compatible_target':'assumed old-protocol compatibility scale, NOT a verified implementation or projection from strict graphs'},'assumed_targets':{'strict_native':STRICT,'icic_compatible_target':COMPAT},'labels':LABELS,'metrics':metrics,'paired':paired,'interactions':interactions,'risk':risk,'members':member_counts,'cdcp_strata':strata,'seeds':SEEDS,'limitations':['artificial identities, no actual spans or endpoint-linked graphs','CI conditional on chosen count model and three simulation seeds','not a simulation of actual training/solver execution','cannot infer calibrated Qwen effect sizes from Luna'],'genuine_model_or_solver_runs':0}
 dump('results.json',result)
 dump('manifest.json',{'evidence_type':result['evidence_type'],'rows':len(raw),'identity_records':len(object_rows),'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file() and p.name!='manifest.json'},'new_real_model_runs':0})
 print(json.dumps({'rows':len(raw),'strict':{d:metrics['strict_native'][d]['t1_i1'] for d in SPECS},'compat':{d:metrics['icic_compatible_target'][d]['t1_i1'] for d in SPECS}},indent=2))
if __name__=='__main__':main()
