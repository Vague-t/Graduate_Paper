"""Paired document/seed bootstrap. No manuscript result data are embedded.

Example:
  python recompute_statistics.py --counts counts.jsonl --comparisons family.json \
    --output recomputed --resamples 2000 --seed 20261012
The seed default is a NEW reproducibility setting, not an asserted historical seed.
"""
from pathlib import Path
import argparse,hashlib,json
import numpy as np

FIELDS=('dataset','document_id','source_group','seed','method','object_family','tp','fp','fn','status')
def validate(rows):
    seen={};groups={};gold={}
    for r in rows:
        if set(FIELDS)-r.keys():raise ValueError('Missing fields')
        if any(isinstance(r[k],bool) or not isinstance(r[k],int) or r[k]<0 for k in ('tp','fp','fn')):raise ValueError('Counts must be nonnegative integers')
        key=tuple(r[k] for k in ('dataset','document_id','seed','method','object_family'))
        if key in seen:raise ValueError('Duplicate paired key')
        seen[key]=r
        dk=(r['dataset'],r['document_id'],r['object_family'])
        if dk in gold and gold[dk]!=r['tp']+r['fn']:raise ValueError('Gold supply differs')
        gold[dk]=r['tp']+r['fn']
        if dk in groups and groups[dk]!=r['source_group']:raise ValueError('Inconsistent source group')
        groups[dk]=r['source_group']
        if r['status'] not in ('ok','failed'):raise ValueError('Unsupported status')
        if r['status']=='failed' and (r['tp'] or r['fp']):raise ValueError('Failure must be an empty prediction')
    return seen

def f1(counts):
    a=np.asarray(counts,dtype=float);den=2*a[...,0]+a[...,1]+a[...,2]
    return np.divide(200*a[...,0],den,out=np.zeros_like(den),where=den!=0)

def holm(pvalues):
    p=np.asarray(pvalues);order=np.argsort(p,kind='stable');m=len(p)
    adjusted=np.minimum(1,np.maximum.accumulate(p[order]*(m-np.arange(m))))
    out=np.empty(m);out[order]=adjusted;return out.tolist()

def run(rows,family,B,seed):
    validate(rows)
    if B<1 or not family:raise ValueError('Empty resampling or family')
    rng=np.random.Generator(np.random.PCG64(seed));reports=[];indices={}
    for dataset in sorted({c['dataset'] for c in family}):
        specs=[c for c in family if c['dataset']==dataset]
        families={c.get('object_family','relation') for c in specs}
        if len(families)!=1:raise ValueError('Use one object family per dataset per run')
        of=next(iter(families));rr=[r for r in rows if r['dataset']==dataset and r['object_family']==of]
        methods=sorted({c[k] for c in specs for k in ('a','b')})
        seeds=sorted({r['seed'] for r in rr});docs=sorted({r['document_id'] for r in rr})
        if len(seeds)!=3 or not docs:raise ValueError('This protocol requires three seeds and nonempty documents')
        keyed={(r['method'],r['seed'],r['document_id']):r for r in rr}
        groups=sorted({r['source_group'] for r in rr});gi={v:i for i,v in enumerate(groups)}
        arr=np.zeros((len(methods),len(seeds),len(groups),3),dtype=np.int64)
        for mi,method in enumerate(methods):
            for si,s in enumerate(seeds):
                for d in docs:
                    if (method,s,d) not in keyed:raise ValueError('Missing paired document/seed/method record')
                    r=keyed[method,s,d];arr[mi,si,gi[r['source_group']]]+=[r[k] for k in ('tp','fp','fn')]
        observed_seed=f1(arr.sum(axis=2));observed=observed_seed.mean(axis=1)
        seed_idx=rng.integers(0,len(seeds),(B,len(seeds)))
        group_idx=rng.integers(0,len(groups),(B,len(groups)))
        boot=np.empty((B,len(methods)));doc_boot=np.empty_like(boot)
        for j in range(B):
            # One shared group draw for every method and selected seed.
            counts=arr[:,:,group_idx[j],:].sum(axis=2)
            seed_scores=f1(counts)
            boot[j]=seed_scores[:,seed_idx[j]].mean(axis=1)
            doc_boot[j]=seed_scores.mean(axis=1)
        indices[dataset]={'seed_values':seeds,'source_groups':groups,'seed_indices':seed_idx.tolist(),'group_indices':group_idx.tolist()}
        for c in specs:
            ai,bi=methods.index(c['a']),methods.index(c['b']);delta=float(observed[ai]-observed[bi]);samples=boot[:,ai]-boot[:,bi]
            p=(1+np.count_nonzero(np.abs(samples-delta)>=abs(delta)-1e-12))/(B+1)
            reports.append({'dataset':dataset,'a':c['a'],'b':c['b'],'difference_pp':delta,'a_seed_f1':observed_seed[ai].tolist(),'b_seed_f1':observed_seed[bi].tolist(),'paired_seed_differences_pp':(observed_seed[ai]-observed_seed[bi]).tolist(),'joint_ci95_pp':np.quantile(samples,[.025,.975],method='linear').tolist(),'document_only_ci95_pp':np.quantile(doc_boot[:,ai]-doc_boot[:,bi],[.025,.975],method='linear').tolist(),'p_raw':float(p),'bootstrap_differences_pp':samples.tolist()})
    adjusted=holm([r['p_raw'] for r in reports])
    for r,p in zip(reports,adjusted):r['p_holm']=p
    return {'resamples':B,'rng':'numpy.random.PCG64','seed':seed,'quantile_method':'linear','family_size':len(reports),'results':reports},indices

def demo_rows():
    rows=[]
    for s in (17,29,43):
        for method in ('A','B'):
            for d,counts in [('demo_1',(10,0,0)),('demo_2',(0,0,1))]:
                rows.append(dict(dataset='DEMO',document_id=d,source_group=d,seed=s,method=method,object_family='relation',tp=counts[0],fp=counts[1],fn=counts[2],status='ok'))
    return rows

def self_test():
    assert abs(f1([10,0,1])-100*20/21)<1e-10
    assert f1([0,0,0])==0
    assert f1([10,0,1])!=np.mean([f1([10,0,0]),f1([0,0,1])])
    assert np.allclose(holm([.01,.04,.03]),[.03,.06,.06])
    rows=demo_rows();family=[{'dataset':'DEMO','a':'A','b':'B'}]
    result,idx=run(rows,family,2000,20261012);r=result['results'][0]
    assert r['difference_pp']==0 and r['joint_ci95_pp']==[0,0] and r['p_raw']==1 and r['p_holm']==1
    assert (result,idx)==run(rows,family,2000,20261012)
    for bad in [rows+rows[:1],rows[:-1],[dict(rows[0],tp=9)]+rows[1:],[dict(rows[0],status='failed')]+rows[1:]]:
        try:run(bad,family,10,0)
        except ValueError:pass
        else:raise AssertionError('Invalid data were accepted')
    return {'micro_aggregation':True,'zero_denominator':True,'paired_identity':True,'holm_known_case':True,'deterministic_indices':True,'duplicate_rejected':True,'missing_pair_rejected':True,'gold_mismatch_rejected':True,'failure_semantics_checked':True,'scope':'synthetic interface tests only; no thesis result reproduction'}

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--counts');ap.add_argument('--comparisons');ap.add_argument('--output');ap.add_argument('--resamples',type=int,default=2000);ap.add_argument('--seed',type=int,default=20261012);ap.add_argument('--self-test',action='store_true');a=ap.parse_args()
    if a.self_test:print(json.dumps(self_test(),ensure_ascii=False,indent=2))
    else:
        if not all([a.counts,a.comparisons,a.output]):ap.error('counts, comparisons and output are required')
        cp=Path(a.counts);fp=Path(a.comparisons);rows=[json.loads(line) for line in cp.read_text().splitlines() if line.strip()];family=json.loads(fp.read_text())
        result,idx=run(rows,family,a.resamples,a.seed);out=Path(a.output);out.mkdir(parents=True,exist_ok=True)
        result['counts_sha256']=hashlib.sha256(cp.read_bytes()).hexdigest();result['family_sha256']=hashlib.sha256(fp.read_bytes()).hexdigest();result['script_sha256']=hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        (out/'results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2));(out/'paired_indices.json').write_text(json.dumps(idx,ensure_ascii=False));print(json.dumps({'output':str(out),'family_size':result['family_size']},ensure_ascii=False))
