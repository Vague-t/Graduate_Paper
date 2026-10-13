"""Generate explicitly hypothetical, count-level thesis data.

This is not a model/corpus/solver experiment or an empirical forecast.
Targets below are authoring assumptions for EST-1010-V7, not fitted estimates.
The v6 baseline and noise are retained to isolate the effect of smaller assumed gains. Object identities are artificial.
The program preserves pairing and makes every reported F1/delta auditable.
"""
from pathlib import Path
import csv,hashlib,json,math
import numpy as np

W=Path(__file__).resolve().parent
SEEDS=[17,29,43]
DATASETS={'AAEC':{'docs':80,'component_range':(12,29),'relation_range':(8,22),'train_docs':320},
          'CDCP':{'docs':148,'component_range':(5,15),'relation_range':(3,10),'train_docs':580}}
# Assumed mean F1 on the probability scale, not observations or forecasts.
TARGETS={'t0_i0': [(0.782, 0.533), (0.702, 0.481)], 'plain_i0': [(0.788, 0.539), (0.707, 0.487)], 'qos_i0': [(0.794, 0.55), (0.713, 0.498)], 'full_data_i0': [(0.797, 0.557), (0.718, 0.505)], 'head_i0': [(0.8, 0.566), (0.723, 0.513)], 't1_i0': [(0.805, 0.578), (0.728, 0.525)], 'no_boundary_i0': [(0.799, 0.563), (0.72, 0.51)], 'no_none_i0': [(0.801, 0.567), (0.723, 0.514)], 'random_i0': [(0.804, 0.576), (0.726, 0.522)], 'noaug_head_i0': [(0.786, 0.537), (0.705, 0.485)], 't0_i1': [(0.799, 0.573), (0.718, 0.525)], 'br_o': [(0.811, 0.586), (0.734, 0.534)], 'br_c': [(0.805, 0.59), (0.728, 0.54)], 'sequential': [(0.813, 0.596), (0.736, 0.546)], 'relation_only': [(0.805, 0.596), (0.728, 0.548)], 'single_object': [(0.818, 0.607), (0.741, 0.559)], 't1_i1': [(0.823, 0.619), (0.748, 0.574)], 'uncalibrated': [(0.823, 0.601), (0.748, 0.552)], 'global_equal': [(0.826, 0.623), (0.752, 0.579)], 'global_long': [(0.829, 0.631), (0.755, 0.587)], 'regenerate': [(0.814, 0.6), (0.737, 0.549)]}
LABELS={'t0_i0':'T0','plain_i0':'普通增强','qos_i0':'QOS式适配','full_data_i0':'完整增强＋基础损失','head_i0':'完整增强＋头监督','t1_i0':'T1完整训练','no_boundary_i0':'去跨边界正关系','no_none_i0':'去NONE检查','random_i0':'匹配随机中心','noaug_head_i0':'无增强＋头监督','t0_i1':'T0＋BR-J','br_o':'BR-O','br_c':'BR-C','sequential':'组件优先分步','relation_only':'RelationOnly','single_object':'单对象动作','t1_i1':'BR-J','uncalibrated':'未校准评分','global_equal':'全局ILP等时限','global_long':'全局ILP大预算','regenerate':'等token重生成'}

def rng(*parts):
    key='|'.join(map(str,parts)).encode();return np.random.default_rng(int(hashlib.sha256(key).hexdigest()[:16],16))
def f1(a):
    a=np.asarray(a);den=2*a[...,0]+a[...,1]+a[...,2]
    return np.divide(200*a[...,0],den,out=np.zeros_like(den,dtype=float),where=den>0)
def dump(name,data):
    (W/name).write_text(json.dumps(data,ensure_ascii=False,indent=2)+'\n')
def main():
    raw=[];arr={};sets={};gold_counts={};means={};risk={};paired={};interactions={};strata={}
    for di,(ds,spec) in enumerate(DATASETS.items()):
        gold_counts[ds]={}
        for obj in ['component','relation']:
            lo,hi=spec[obj+'_range'];ns=rng(ds,obj,'gold').integers(lo,hi+1,spec['docs'])
            gold_counts[ds][obj]=ns.tolist();docs=np.repeat(np.arange(spec['docs']),ns);N=len(docs)
            fdocs=np.repeat(np.arange(spec['docs']),max(20,hi));NF=len(fdocs)
            members=rng(ds,obj,'members').choice([1,2,3],N,p=[.60,.27,.13])
            fmembers=rng(ds,obj,'false-members').choice([1,2,3],NF,p=[.60,.27,.13])
            for si,seed in enumerate(SEEDS):
                latent=rng(ds,obj,seed,'shared').normal(size=N)
                if ds=='CDCP' and obj=='relation':latent+=(members-1)*.33
                flatent=rng(ds,obj,seed,'shared-fp').normal(size=NF)
                for method,targets in TARGETS.items():
                    ref='t1_i0' if obj=='component' and method in ['br_c','relation_only'] else method
                    jitter=rng(ds,obj,ref,'jitter').normal(0,.0018,3);jitter-=jitter.mean()
                    target=TARGETS[ref][di][obj=='relation']+[-.004,.001,.003][si]+jitter[si]
                    # Balanced P/R around the target; the table is derived from rounded counts.
                    recall=target-.015;precision=target+.015
                    ntp=int(round(N*recall));nfp=int(round(ntp*(1/precision-1)))
                    tranks=np.argsort(latent+rng(ds,obj,seed,ref,'gold-noise').normal(0,.18,N))
                    franks=np.argsort(flatent+rng(ds,obj,seed,ref,'fp-noise').normal(0,.22,NF))
                    true=set(map(int,tranks[:ntp]));false=set(map(int,franks[:nfp]))
                    sets[ds,obj,seed,method]=(true,false)
                    if ds=='CDCP' and obj=='relation' and method in ['t0_i0','t1_i0','t0_i1','t1_i1']:
                        for g in [1,2,3]:
                            gt=int((members==g).sum());tp_g=int((members[list(true)]==g).sum());fp_g=int((fmembers[list(false)]==g).sum())
                            strata.setdefault(method,{}).setdefault(str(g),[]).append([tp_g,fp_g,gt-tp_g])
                    tp=np.bincount(docs[list(true)],minlength=spec['docs']);fp=np.bincount(fdocs[list(false)],minlength=spec['docs']);fn=ns-tp
                    values=np.stack([tp,fp,fn],axis=1);arr[ds,obj,seed,method]=values
                    for d,(a,b,c) in enumerate(values):raw.append({'dataset':ds,'document':f'SIM-{ds}-{d+1:03d}','seed':seed,'method':method,'object':obj,'tp':int(a),'fp':int(b),'fn':int(c),'evidence_type':'SIMULATED_COUNTS'})
        for method in TARGETS:
            means.setdefault(ds,{})[method]={}
            for obj in ['component','relation']:
                totals=[arr[ds,obj,s,method].sum(axis=0).tolist() for s in SEEDS]
                values=[float(f1(t)) for t in totals]
                means[ds][method][obj]={'mean':float(np.mean(values)),'sd':float(np.std(values,ddof=1)),'seeds':values,'counts':totals}
        for method in ['sequential','t1_i1','global_equal','regenerate']:
            summary={}
            for obj in ['component','relation']:
                counts={'recovered':0,'lost_tp':0,'removed_fp':0,'added_fp':0,'base_tp':0,'improved_documents':0,'unchanged_documents':0,'worsened_documents':0}
                for seed in SEEDS:
                    bt,bf=sets[ds,obj,seed,'t1_i0'];at,af=sets[ds,obj,seed,method]
                    counts['recovered']+=len(at-bt);counts['lost_tp']+=len(bt-at);counts['removed_fp']+=len(bf-af);counts['added_fp']+=len(af-bf);counts['base_tp']+=len(bt)
                    delta=f1(arr[ds,obj,seed,method])-f1(arr[ds,obj,seed,'t1_i0'])
                    counts['improved_documents']+=int((delta>1e-10).sum());counts['unchanged_documents']+=int((np.abs(delta)<=1e-10).sum());counts['worsened_documents']+=int((delta< -1e-10).sum())
                counts['tp_retention']=100*(1-counts['lost_tp']/counts['base_tp']);counts['document_seed_pairs']=spec['docs']*3
                summary[obj]=counts
            risk.setdefault(ds,{})[method]=summary
        # Resample documents in pairs, using the same document indices across seeds/methods.
        n=spec['docs'];indices=rng(ds,'bootstrap').integers(0,n,size=(2000,n))
        for obj in ['component','relation']:
            boots={m:np.mean([f1(arr[ds,obj,s,m][indices].sum(axis=1)) for s in SEEDS],axis=0) for m in TARGETS}
            for a,b in [('t1_i0','head_i0'),('t1_i0','random_i0'),('t1_i1','sequential'),('t1_i1','t1_i0'),('t1_i0','t0_i0'),('global_equal','t1_i1'),('t1_i1','relation_only'),('t1_i1','single_object')]:
                diff=boots[a]-boots[b];point=means[ds][a][obj]['mean']-means[ds][b][obj]['mean']
                paired.setdefault(ds,{}).setdefault(a+'__'+b,{})[obj]={'delta':point,'ci95':np.quantile(diff,[.025,.975]).tolist(),'unit':'paired_documents_conditional_on_three_fixed_simulation_seeds'}
            inter=boots['t1_i1']-boots['t1_i0']-boots['t0_i1']+boots['t0_i0']
            point=means[ds]['t1_i1'][obj]['mean']-means[ds]['t1_i0'][obj]['mean']-means[ds]['t0_i1'][obj]['mean']+means[ds]['t0_i0'][obj]['mean']
            interactions.setdefault(ds,{})[obj]={'value':point,'ci95':np.quantile(inter,[.025,.975]).tolist()}
    with (W/'document_counts.csv').open('w') as f:
        writer=csv.DictWriter(f,fieldnames=list(raw[0]));writer.writeheader();writer.writerows(raw)
    # Audit decisions are synthetic categorical judgements, not human review.
    audit_rows=[];audits={};allA=[];allB=[]
    for ds in DATASETS:
        for method,base in [('plain',.17),('qos',.105),('full',.04),('no_boundary',.09),('no_none',.083)]:
            rates={};aa=[];bb=[]
            for accepted in [True,False]:
                for factor,mult in [('internal_positive',.65),('boundary_positive',1.3),('internal_none',.8),('boundary_none',1.25)]:
                    prob=min(.75,base*mult+(0 if accepted else .27)+(0.015 if ds=='CDCP' else 0))
                    rr=rng(ds,method,accepted,factor);truth=rr.random(200)<prob
                    A=np.logical_xor(truth,rr.random(200)<.015);B=np.logical_xor(truth,rr.random(200)<.02)
                    for k in range(200):audit_rows.append({'dataset':ds,'method':method,'accepted':accepted,'factor':factor,'id':k,'drift':bool(truth[k]),'judgement_A':bool(A[k]),'judgement_B':bool(B[k])})
                    if accepted:rates[factor]=float(truth.mean()*100)
                    aa.extend(A.tolist());bb.extend(B.tolist());allA.extend(A.tolist());allB.extend(B.tolist())
            aa=np.array(aa);bb=np.array(bb);po=float((aa==bb).mean());pe=float(aa.mean()*bb.mean()+(1-aa.mean())*(1-bb.mean()))
            rates['mean_drift']=float(np.mean(list(rates.values())));rates['agreement']=100*po;rates['kappa']=(po-pe)/(1-pe);rates['sample_count']=1600
            audits.setdefault(ds,{})[method]=rates
    dump('audit_judgements.json',{'evidence_type':'SIMULATED_JUDGEMENTS','rows':audit_rows})
    a=np.array(allA);b=np.array(allB);po=float((a==b).mean());pe=float(a.mean()*b.mean()+(1-a.mean())*(1-b.mean()))
    audit_overall={'n':len(a),'agreement':100*po,'kappa':(po-pe)/(1-pe)}
    # Candidate-score example, calibration computed from generated probabilities/labels.
    scores={};score_rows=[]
    for ds in DATASETS:
        for obj,N in [('component',2400),('relation',4800)]:
            rr=rng(ds,obj,'calibration');p=rr.beta(1.1,2.4,N);y=(rr.random(N)<p).astype(int)
            p_uncal=1/(1+np.exp(-(np.log(p/(1-p))/.58+.32)))
            for name,ps in [('raw',p_uncal),('calibrated',p)]:
                order=np.argsort(ps);ranks=np.empty(N);ranks[order]=np.arange(1,N+1);npos=y.sum();nneg=N-npos
                auc=(ranks[y==1].sum()-npos*(npos+1)/2)/(npos*nneg)
                bins=np.minimum((ps*10).astype(int),9);ece=sum(np.mean(bins==k)*abs(ps[bins==k].mean()-y[bins==k].mean()) for k in range(10) if (bins==k).any())
                scores.setdefault(ds,{}).setdefault(obj,{})[name]={'AUROC':float(auc),'Brier':float(np.mean((ps-y)**2)),'ECE':float(ece),'n':N}
                for i in range(N):score_rows.append({'dataset':ds,'object':obj,'version':name,'id':i,'probability':float(ps[i]),'label':int(y[i])})
    dump('score_records.json',{'evidence_type':'SIMULATED_PROBABILITIES_AND_LABELS','records':score_rows})
    generation={
      'AAEC':{'attempts':1280,'plain':{'accepted':604,'covered':316,'generation_mtokens':4.72,'audit_mtokens':1.05,'train_gpu_hours':1.46},'qos':{'accepted':548,'covered':300,'generation_mtokens':4.95,'audit_mtokens':1.62,'train_gpu_hours':1.48},'full':{'accepted':520,'covered':292,'generation_mtokens':5.10,'audit_mtokens':2.24,'train_gpu_hours':1.79},'matched_variants':500,'matched_tokens':.82},
      'CDCP':{'attempts':2320,'plain':{'accepted':1070,'covered':562,'generation_mtokens':6.80,'audit_mtokens':1.60,'train_gpu_hours':2.32},'qos':{'accepted':996,'covered':535,'generation_mtokens':7.14,'audit_mtokens':2.35,'train_gpu_hours':2.38},'full':{'accepted':940,'covered':522,'generation_mtokens':7.42,'audit_mtokens':3.61,'train_gpu_hours':2.91},'matched_variants':900,'matched_tokens':1.35}}
    centers={'AAEC':{'documents':320,'valid':310,'self':112,'heterocenter':198,'no_components':0,'overlap':2,'region_limit':8},'CDCP':{'documents':580,'valid':552,'self':226,'heterocenter':326,'no_components':1,'overlap':7,'region_limit':20}}
    # Explicit scenario costs. Seconds are assigned, not measured by this program.
    costs={}
    for di,ds in enumerate(DATASETS):
        gen=[18.,23.][di];sc=[12.4,19.6][di]
        for method,solve,extra in [('t1_i0',0,0),('br_o',.55,0),('br_c',.40,0),('sequential',1.05,0),('relation_only',.65,0),('single_object',.88,0),('t1_i1',1.60,0),('uncalibrated',1.58,0),('global_equal',3.0,0),('global_long',48.,0),('regenerate',0,13.8)]:
            scoring=0 if method in ['t1_i0','regenerate'] else sc
            solve*=1 if di==0 else 1.6
            if method=='regenerate':extra=[14.,22.][di]
            total=gen+scoring+solve+extra
            costs.setdefault(ds,{})[method]={'generation_s':gen,'scoring_s':scoring,'solver_s':solve,'regeneration_s':extra,'mean_s':total,'p95_s':total*(1.58 if method!='global_long' else 2.10),'input_ktokens':24.0+(18.0 if method not in ['t1_i0'] else 0)+(6*di)-(1.0 if method=='regenerate' else 0),'output_ktokens':3.2+(1.0 if method=='regenerate' else 0)+.5*di,'calls':4+(2 if method!='t1_i0' else 0),'provenance':'ASSIGNED_SCENARIO_COST'}
    coverage={'AAEC':{'component':95.2,'endpoints':91.1,'relation':87.4,'one':76.8,'multi':83.2,'global':85.1},'CDCP':{'component':91.8,'endpoints':84.6,'relation':79.2,'one':70.3,'multi':77.7,'global':80.4}}
    budget={}
    for ds in DATASETS:
        start=means[ds]['t1_i0']['relation']['mean'];end=means[ds]['t1_i1']['relation']['mean']
        costs_ds=costs[ds];base=costs_ds['t1_i0']['mean_s'];full=costs_ds['t1_i1']['mean_s']
        budget[ds]=[{'rounds':r,'max_attempts':32*r,'max_accepts':3*r,'relation_f1':start+(end-start)*gain,'mean_s':base+(full-base)*cost} for r,gain,cost in [(0,0,0),(1,.68,.58),(2,.90,.79),(4,1,1)]]
    # Reproducible bookkeeping only; no inference about real corpus distributions.
    result={'evidence_type':'SIMULATED_DATA_FOR_AUTHORING_NOT_MEASUREMENTS_OR_FORECASTS','seeds':SEEDS,'datasets':DATASETS,'assumed_targets':TARGETS,'labels':LABELS,'gold_counts':gold_counts,'metrics':means,'paired':paired,'interaction':interactions,'risk':risk,'cdcp_source_strata':strata,'audit':audits,'audit_overall':audit_overall,'scores':scores,'generation':generation,'centers':centers,'costs':costs,'coverage_oracle_scenario':coverage,'budget':budget}
    # Arithmetic and cross-chapter identity assertions, not production-model tests.
    for row in raw:assert min(row['tp'],row['fp'],row['fn'])>=0
    for ds in DATASETS:
        assert centers[ds]['valid']==centers[ds]['self']+centers[ds]['heterocenter']
        assert centers[ds]['documents']==centers[ds]['valid']+sum(centers[ds][x] for x in ['no_components','overlap','region_limit'])
        for obj in ['component','relation']:
            for seed in SEEDS:
                Ns=np.array(gold_counts[ds][obj])
                for method in TARGETS:assert np.array_equal(arr[ds,obj,seed,method][:,0]+arr[ds,obj,seed,method][:,2],Ns)
            for method in ['br_c','relation_only']:
                if obj=='component':assert means[ds][method][obj]==means[ds]['t1_i0'][obj]
    dump('scenario_results.json',result)
    dump('scenario_manifest.json',{'evidence_type':result['evidence_type'],'generator_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'files':{name:hashlib.sha256((W/name).read_bytes()).hexdigest() for name in ['document_counts.csv','audit_judgements.json','score_records.json','scenario_results.json']},'record_rows':len(raw),'gold_identity_scope':'artificial count-level objects; not actual corpus spans or graphs','source_assumptions':'TARGETS, generation, costs and coverage are explicit scenario inputs; no fitted forecast model','genuine_corpus_or_model_runs':0})
    print(json.dumps({'rows':len(raw),'evidence_type':result['evidence_type'],'main_results':{d:{m:means[d][m] for m in ['t0_i0','t1_i0','t0_i1','t1_i1']} for d in DATASETS}},ensure_ascii=False,indent=2))
if __name__=='__main__':main()
