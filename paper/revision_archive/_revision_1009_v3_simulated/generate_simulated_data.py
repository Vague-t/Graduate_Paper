"""Generate explicitly synthetic manuscript data, never real experiment logs.

Targets are scenario assumptions. All scores, intervals, deltas and plots are
calculated from generated counts. No model, corpus, human annotator or ILP is run.
"""
from pathlib import Path
import csv
import hashlib
import json
import math
import numpy as np

W = Path(__file__).resolve().parent
SEEDS = [17, 29, 43]
TYPE = 'SYNTHETIC_ILLUSTRATIVE_NOT_MEASURED'
TARGETS = {
 'T0I0': [81.70,58.90,69.50,39.50],
 'T1I0': [83.40,62.00,71.70,43.00],
 'T0I1': [83.00,61.90,71.20,42.60],
 'T1I1': [84.40,64.60,73.10,45.40],
 'ordinary_fixed': [82.20,59.80,70.10,40.60],
 'ordinary_matched': [82.30,60.00,70.20,40.90],
 'qos_matched': [82.70,60.70,70.60,41.70],
 'full_base': [82.80,61.10,70.90,42.00],
 'full_heads': [83.20,61.50,71.30,42.50],
 'no_boundary': [82.90,61.00,71.10,41.80],
 'no_none': [82.80,60.80,70.90,41.30],
 'internal_only': [82.40,60.20,70.50,40.70],
 'random_center': [83.30,61.85,71.60,42.88],
 'BR_O': [83.85,63.00,72.15,43.75],
 'BR_C': [83.40,62.70,71.70,43.65],
 'relation_only': [83.40,63.20,71.70,44.05],
 'delete_only': [83.40,62.30,71.70,43.35],
 'sequential': [84.15,63.50,72.75,44.20],
 'single_object': [84.05,63.80,72.55,44.55],
 'old_score': [83.70,63.15,72.05,43.80],
 'global_equal': [84.20,64.40,72.95,45.20],
 'global_sufficient': [84.60,64.70,73.35,45.20],
 'regenerate_equal': [83.85,63.35,72.10,43.90],
}
PANELS = {'AAEC': {'documents':80,'components_range':[10,31],'relation_ratio':.65},
          'CDCP': {'documents':150,'components_range':[5,24],'relation_ratio':.52}}
ALIASES = {'MCR_only':'T1I0','BR_J':'T1I1','full_alignment':'T1I0'}

def rng(*parts):
    digest = hashlib.sha256('|'.join(map(str, parts)).encode()).digest()
    return np.random.default_rng(int.from_bytes(digest[:8], 'big'))

def f1(a):
    a = np.asarray(a, dtype=float)
    return np.divide(200*a[...,0], 2*a[...,0]+a[...,1]+a[...,2],
                     out=np.zeros(a.shape[:-1]), where=(2*a[...,0]+a[...,1]+a[...,2]) != 0)

def summarize(a):
    values=f1(a.sum(axis=1))
    return {'mean':float(values.mean()),'sd':float(values.std(ddof=1)),
            'by_seed':dict(zip(map(str,SEEDS),map(float,values))),
            'counts_by_seed':dict(zip(map(str,SEEDS),a.sum(axis=1).tolist()))}

def bootstrap_delta(a,b,idx):
    # The same document resample is applied to every seed. Repeated documents
    # across seeds are not treated as additional independent observations.
    diff=[]
    for sample in idx:
        diff.append(float((f1(a[:,sample].sum(axis=1))-f1(b[:,sample].sum(axis=1))).mean()))
    return [float(x) for x in np.percentile(diff,[2.5,97.5])]

def main():
    counts={}; predictions={}; panels={}; rows=[]; summary={}; contrasts={}; changes={}
    for di,(dataset,profile) in enumerate(PANELS.items()):
        n=profile['documents']
        C=rng(dataset,'gold').integers(*profile['components_range'],size=n)
        R=np.maximum(2,np.floor(C*profile['relation_ratio']).astype(int))
        panels[dataset]={'documents':n,'gold_components':int(C.sum()),'gold_relations':int(R.sum()),
                         'document_ids':[f'SIM-{dataset}-{i:03d}' for i in range(1,n+1)],
                         'evidence_type':TYPE}
        counts[dataset]={};predictions[dataset]={};summary[dataset]={};contrasts[dataset]={};changes[dataset]={}
        for method,targets in TARGETS.items():
            counts[dataset][method]={}; predictions[dataset][method]={};summary[dataset][method]={}
            for ki,(kind,ngold) in enumerate([('C',C),('R',R)]):
                refmethod='T1I0' if kind=='C' and method in {'BR_C','relation_only','delete_only'} else method
                if refmethod!=method:
                    counts[dataset][method][kind]=counts[dataset][refmethod][kind].copy()
                    predictions[dataset][method][kind]=predictions[dataset][refmethod][kind]
                else:
                    G=int(ngold.sum()); true_doc=np.repeat(np.arange(n),ngold)
                    false_doc=np.repeat(np.arange(n),ngold*2)
                    multi=[];sets=[]
                    for seed_index,seed in enumerate(SEEDS):
                        offset=[-.28,.03,.25][seed_index]*(1.25 if kind=='R' else .8)
                        offset+=float(rng(dataset,method,kind,'offset',seed).normal(0,.045))
                        target=(targets[2*di+ki]+offset)/100
                        recall=min(.97,target+.008)
                        ntp=int(round(G*recall)); nfp=max(0,int(round(2*ntp/target-ntp-G)))
                        difficulty=rng(dataset,kind,'true',seed).uniform(size=G)
                        false_difficulty=rng(dataset,kind,'false',seed).uniform(size=2*G)
                        noise=.013 if method in {'T0I0','T1I0','T0I1','T1I1'} else .016
                        selected=set(np.argsort(difficulty+rng(dataset,method,kind,'tp',seed).normal(0,noise,G))[:ntp].tolist())
                        false_selected=set(np.argsort(false_difficulty+rng(dataset,method,kind,'fp',seed).normal(0,noise,2*G))[:nfp].tolist())
                        tp=np.bincount(true_doc[list(selected)],minlength=n)
                        fp=np.bincount(false_doc[list(false_selected)],minlength=n)
                        multi.append(np.stack([tp,fp,ngold-tp],axis=1))
                        sets.append((selected,false_selected,true_doc,false_doc))
                    counts[dataset][method][kind]=np.array(multi)
                    predictions[dataset][method][kind]=sets
                arr=counts[dataset][method][kind]
                summary[dataset][method][kind]=summarize(arr)
                for si,seed in enumerate(SEEDS):
                    for i,(tp,fp,fn) in enumerate(arr[si]):
                        rows.append({'evidence_type':TYPE,'dataset_profile':dataset,'document_id':panels[dataset]['document_ids'][i],
                                     'scenario_id':method,'seed':seed,'object_kind':kind,'tp':int(tp),'fp':int(fp),'fn':int(fn)})
        resamples=rng(dataset,'bootstrap').integers(0,n,size=(1500,n))
        for contrast,a,b in [('training','T1I0','T0I0'),('repair_T1','T1I1','T1I0'),('repair_T0','T0I1','T0I0'),
                             ('alignment','T1I0','full_heads'),('heads','full_heads','full_base'),
                             ('joint_vs_sequential','T1I1','sequential'),('center','T1I0','random_center'),
                             ('combined','T1I1','T0I0')]:
            contrasts[dataset][contrast]={}
            for kind in ['C','R']:
                aa=counts[dataset][a][kind];bb=counts[dataset][b][kind]
                contrasts[dataset][contrast][kind]={'mean_delta':summary[dataset][a][kind]['mean']-summary[dataset][b][kind]['mean'],
                    'document_ci95':bootstrap_delta(aa,bb,resamples),'a':a,'b':b}
        contrasts[dataset]['interaction']={}
        for kind in ['C','R']:
            matrices=[counts[dataset][m][kind] for m in ['T1I1','T1I0','T0I1','T0I0']]
            coeff=np.array([1,-1,-1,1])
            vals=np.array([f1(a.sum(axis=1)) for a in matrices])
            per_seed=coeff@vals
            bs=[]
            for idx in resamples:
                bs.append(float(sum(c*f1(a[:,idx].sum(axis=1)).mean() for c,a in zip(coeff,matrices))))
            contrasts[dataset]['interaction'][kind]={'mean_delta':float(per_seed.mean()),'sd':float(per_seed.std(ddof=1)),
                                                    'document_ci95':list(map(float,np.percentile(bs,[2.5,97.5])))}
        # Object identities support gains/losses and common-unit document risks.
        for method in ['T0I1','T1I1','sequential','global_equal','regenerate_equal']:
            before='T0I0' if method=='T0I1' else 'T1I0'
            changes[dataset][method]={}
            for kind in ['C','R']:
                record=[]
                for si,seed in enumerate(SEEDS):
                    p,q,_,_=predictions[dataset][before][kind][si]
                    x,y,_,_=predictions[dataset][method][kind][si]
                    a=counts[dataset][before][kind][si];b=counts[dataset][method][kind][si]
                    df=f1(b)-f1(a)
                    rec={'seed':seed,'restored_tp':len(x-p),'lost_tp':len(p-x),'removed_fp':len(q-y),'added_fp':len(y-q),
                         'before_tp':len(p),'retention_percent':100*len(p&x)/len(p),
                         'documents_beneficial':int(np.sum(df>1e-9)),'documents_neutral':int(np.sum(np.abs(df)<=1e-9)),
                         'documents_harmful':int(np.sum(df< -1e-9))}
                    assert rec['restored_tp']-rec['lost_tp']==int(b[:,0].sum()-a[:,0].sum())
                    assert rec['added_fp']-rec['removed_fp']==int(b[:,1].sum()-a[:,1].sum())
                    record.append(rec)
                changes[dataset][method][kind]=record
    audit=[]
    drift={'ordinary':[15,25,23,34], 'qos':[10,18,16,26], 'full':[4,7,6,9], 'no_none':[5,8,23,34]}
    for di,ds in enumerate(PANELS):
        for method,base in drift.items():
            nums=[x+di*2 for x in base];readonly=4+di*2 if method=='full' else 8+di*3
            attempts=[1116,2040][di]
            accepted={'ordinary':[514,960],'qos':[474,842],'full':[436,784],'no_none':[487,887]}[method][di]
            audit.append({'dataset_profile':ds,'method':method,'attempts':attempts,'accepted':accepted,
                          'acceptance_percent':100*accepted/attempts,'per_stratum_n':160,
                          'drift_counts':nums,'all_drift_percent':100*sum(nums)/640,
                          'readonly_n':160,'readonly_drift':readonly,'rejected_audit_n':160,
                          'rejected_but_preserved':{'ordinary':18,'qos':27,'full':35,'no_none':22}[method]+di*4})
    center={'AAEC':{'all_documents':286,'valid_reference':279,'self_match':112,'heterocenter':167,'empty':2,'region_failure':1,'resource_failure':4},
            'CDCP':{'all_documents':523,'valid_reference':510,'self_match':233,'heterocenter':277,'empty':3,'region_failure':4,'resource_failure':6}}
    calibration=[];prob_rows=[]
    for ds in PANELS:
        for kind in ['C','R']:
            g=rng(ds,kind,'calibration');n=2400
            latent=g.beta(2.1,2.0,size=n);y=g.binomial(1,latent)
            raw=1/(1+np.exp(-(np.log(latent/(1-latent))*1.55+.45)))
            calibrated=1/(1+np.exp(-((np.log(raw/(1-raw))-.45)/1.55)))
            def metrics(p):
                ece=0
                for lo in np.linspace(0,.9,10):
                    ix=(p>=lo)&(p<(lo+.1) if lo<.9 else p<=1)
                    if ix.any():ece+=ix.mean()*abs(p[ix].mean()-y[ix].mean())
                order=np.argsort(p);ranks=np.empty(n);ranks[order]=np.arange(1,n+1)
                pos=y.sum();neg=n-pos
                auc=(ranks[y==1].sum()-pos*(pos+1)/2)/(pos*neg)
                return {'ece':float(ece),'brier':float(np.mean((p-y)**2)),'auroc':float(auc)}
            calibration.append({'dataset_profile':ds,'object_kind':kind,'n':n,'positive':int(y.sum()),'raw':metrics(raw),'calibrated':metrics(calibrated)})
            prob_rows.extend({'evidence_type':TYPE,'dataset_profile':ds,'object_kind':kind,'id':i,'label':int(y[i]),'raw':float(raw[i]),'calibrated':float(calibrated[i])} for i in range(n))
    cost={};cost_rows=[]
    solver_centers={'T1I0':(0,0),'T1I1':(.45,.90),'sequential':(.40,.82),
                    'global_equal':(2.6,3.3),'global_sufficient':(9,22),'regenerate_equal':(0,0)}
    for di,(ds,profile) in enumerate(PANELS.items()):
        cost[ds]={}
        n=profile['documents'];g=rng(ds,'common_cost')
        common_generation=g.lognormal(math.log((4.0,7.0)[di])-.08,.4,size=n)
        common_scoring=g.lognormal(math.log((1.7,3.2)[di])-.045,.3,size=n)
        for method,centers in solver_centers.items():
            g=rng(ds,method,'cost');generation=common_generation.copy()
            scoring=common_scoring.copy();overhead=np.full(n,(.2,.4)[di])
            solver=np.zeros(n)
            if method=='T1I0':scoring=common_scoring*.3
            elif method=='regenerate_equal':
                generation+=g.lognormal(math.log((2.2,4.2)[di])-.08,.4,size=n)
                scoring=common_scoring*.65
            else:
                solver=np.minimum(g.lognormal(math.log(centers[di])-.125,.5,size=n),60 if method=='global_sufficient' else 4)
            other=solver+overhead;values=generation+scoring+other
            cost[ds][method]={'mean_seconds':float(values.mean()),'p95_seconds':float(np.percentile(values,95)),
                              'generation_mean':float(generation.mean()),'scoring_mean':float(scoring.mean()),
                              'solver_mean':float(solver.mean()),'remaining_mean':float(other.mean())}
            cost_rows.extend({'evidence_type':TYPE,'dataset_profile':ds,'scenario_id':method,'document_id':panels[ds]['document_ids'][i],
                              'total_seconds':float(values[i]),'generation_seconds':float(generation[i]),'scoring_seconds':float(scoring[i]),
                              'solver_seconds':float(solver[i]),'other_seconds':float(other[i])} for i in range(n))
    once={'AAEC':{'generation_gpu_hours':1.4,'audit_gpu_hours':.7,'training_T0_hours':2.1,'training_T1_hours':3.4,'oof_hours':14.8,'peak_memory_gib':31.6,'generated_tokens':812400},
          'CDCP':{'generation_gpu_hours':2.8,'audit_gpu_hours':1.5,'training_T0_hours':3.6,'training_T1_hours':5.7,'oof_hours':28.0,'peak_memory_gib':38.2,'generated_tokens':1586400}}
    coverage={'AAEC':{'component_percent':94.8,'all_endpoints_percent':91.1,'complete_relation_percent':88.2,
                     'one_step_feasible':70.3,'multi_step_feasible':78.8,'net_feasible':82.6,'net_bound':85.2},
              'CDCP':{'component_percent':92.7,'all_endpoints_percent':86.2,'complete_relation_percent':80.4,
                     'one_step_feasible':50.4,'multi_step_feasible':62.5,'net_feasible':67.1,'net_bound':70.8}}
    profile={'evidence_type':TYPE,'simulation_id':'SIM-1009-v3-counts-01','seed_list':SEEDS,'panels':panels,
             'target_assumptions':TARGETS,'aliases':ALIASES,'bootstrap_replicates':1500,
             'bootstrap_unit':'same_document_indices_across_seeds_then_mean_metric','model_scenario':'Qwen2.5-7B-Instruct',
             'training_scenario':{'lora_rank':16,'alpha':32,'dropout':.05,'optimizer':'AdamW','learning_rate':.0002,
                                  'epochs':3,'effective_batch_documents':16,'max_context_tokens':4096,'rho':1,'lambda_head':.1,'lambda_align':.2},
             'generation_scenario':{'complete_candidates':3,'temperature':.7,'max_new_tokens':2048},
             'resource_scenario':{'gpu_memory_gib':80,'solver_threads':4,'solver_total_seconds':4,'solver_single_seconds':1,'sufficient_solver_seconds':60},
             'scope':'Generated counts, audit labels, probabilities and resource samples; no corpus text, model checkpoint, actual solver status or human review.'}
    report={'evidence_type':TYPE,'profile':profile,'metrics':summary,'contrasts':contrasts,'changes':changes,'audit':audit,
            'centers':center,'calibration':calibration,'cost':cost,'once_cost':once,'coverage':coverage}
    (W/'simulation_profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n')
    (W/'simulation_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
    (W/'simulated_counts.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in rows))
    (W/'simulated_probabilities.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prob_rows))
    (W/'simulated_costs.jsonl').write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in cost_rows))
    for ds in PANELS:
        for name,rec in center.items():assert rec['valid_reference']==rec['self_match']+rec['heterocenter']
        print(ds, 'four cell R', {m:round(summary[ds][m]['R']['mean'],2) for m in ['T0I0','T1I0','T0I1','T1I1']}, 'interaction',contrasts[ds]['interaction']['R'])
    print('Generated explicitly synthetic rows',len(rows),'probabilities',len(prob_rows),'costs',len(cost_rows))

if __name__=='__main__':main()
