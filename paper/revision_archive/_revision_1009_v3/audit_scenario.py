"""Independently recompute the artificial authoring data, never model accuracy."""
from pathlib import Path
from collections import defaultdict
import csv, hashlib, json
import numpy as np

W=Path(__file__).resolve().parent
def read(name): return json.loads((W/name).read_text())
def f1(v):
    v=np.asarray(v); d=2*v[...,0]+v[...,1]+v[...,2]
    return np.divide(200*v[...,0],d,out=np.zeros_like(d,dtype=float),where=d>0)
def close(a,b): assert np.allclose(a,b,rtol=0,atol=1e-10),(a,b)
def rng(*parts):
    return np.random.default_rng(int(hashlib.sha256('|'.join(map(str,parts)).encode()).hexdigest()[:16],16))

def main():
    r=read('scenario_results.json'); m=read('scenario_manifest.json')
    assert m['genuine_corpus_or_model_runs']==0
    for name,digest in m['files'].items(): assert hashlib.sha256((W/name).read_bytes()).hexdigest()==digest
    assert hashlib.sha256((W/'generate_scenario.py').read_bytes()).hexdigest()==m['generator_sha256']
    arr=defaultdict(list); n=0
    with (W/'document_counts.csv').open() as f:
        for row in csv.DictReader(f):
            assert row['evidence_type']=='SIMULATED_COUNTS'
            counts=[int(row[k]) for k in ['tp','fp','fn']]
            assert min(counts)>=0
            arr[row['dataset'],row['object'],int(row['seed']),row['method']].append((row['document'],counts)); n+=1
    assert n==m['record_rows']==28728
    arr={k:np.array([v for _,v in sorted(a)]) for k,a in arr.items()}
    metrics=0; intervals=0
    for ds,spec in r['datasets'].items():
        for obj in ['component','relation']:
            for method,byobj in r['metrics'][ds].items():
                counts=[arr[ds,obj,s,method].sum(axis=0) for s in r['seeds']]
                values=f1(counts); expected=byobj[obj]
                close(counts,expected['counts']); close(values,expected['seeds'])
                close(values.mean(),expected['mean']); close(values.std(ddof=1),expected['sd'])
                for seed in r['seeds']:
                    a=arr[ds,obj,seed,method]
                    assert len(a)==spec['docs'];close(a[:,0]+a[:,2],r['gold_counts'][ds][obj])
                metrics+=1
            idx=rng(ds,'bootstrap').integers(0,spec['docs'],size=(2000,spec['docs']))
            boots={method:np.mean([f1(arr[ds,obj,s,method][idx].sum(axis=1)) for s in r['seeds']],axis=0) for method in r['metrics'][ds]}
            for pair,byobj in r['paired'][ds].items():
                a,b=pair.split('__'); expected=byobj[obj]
                close(r['metrics'][ds][a][obj]['mean']-r['metrics'][ds][b][obj]['mean'],expected['delta'])
                close(np.quantile(boots[a]-boots[b],[.025,.975]),expected['ci95']);intervals+=1
            inter=boots['t1_i1']-boots['t1_i0']-boots['t0_i1']+boots['t0_i0']
            close(np.quantile(inter,[.025,.975]),r['interaction'][ds][obj]['ci95']);intervals+=1
        c=r['centers'][ds]
        assert c['valid']==c['self']+c['heterocenter']
        assert c['documents']==c['valid']+c['no_components']+c['overlap']+c['region_limit']
        for method,byobj in r['risk'][ds].items():
            for obj,k in byobj.items():
                base=sum(r['metrics'][ds]['t1_i0'][obj]['counts'][i][0] for i in range(3))
                after=sum(r['metrics'][ds][method][obj]['counts'][i][0] for i in range(3))
                assert base==k['base_tp'] and after-base==k['recovered']-k['lost_tp']
                before_fp=sum(r['metrics'][ds]['t1_i0'][obj]['counts'][i][1] for i in range(3))
                after_fp=sum(r['metrics'][ds][method][obj]['counts'][i][1] for i in range(3))
                assert after_fp-before_fp==k['added_fp']-k['removed_fp']
                assert sum(k[x] for x in ['improved_documents','unchanged_documents','worsened_documents'])==3*spec['docs']
        for cost in r['costs'][ds].values():
            assert cost['provenance']=='ASSIGNED_SCENARIO_COST'
            close(sum(cost[x] for x in ['generation_s','scoring_s','solver_s','regeneration_s']),cost['mean_s'])
    sr=read('score_records.json'); groups=defaultdict(list)
    assert sr['evidence_type']=='SIMULATED_PROBABILITIES_AND_LABELS'
    for row in sr['records']:groups[row['dataset'],row['object'],row['version']].append(row)
    for (ds,obj,version),rows in groups.items():
        p=np.array([x['probability'] for x in rows]);y=np.array([x['label'] for x in rows]);expected=r['scores'][ds][obj][version]
        ranks=np.empty(len(p));ranks[np.argsort(p)]=np.arange(1,len(p)+1)
        np_=y.sum(); nn=len(p)-np_
        close((ranks[y==1].sum()-np_*(np_+1)/2)/(np_*nn),expected['AUROC'])
        close(((p-y)**2).mean(),expected['Brier'])
        bins=np.minimum((10*p).astype(int),9)
        close(sum((bins==k).mean()*abs(p[bins==k].mean()-y[bins==k].mean()) for k in range(10) if (bins==k).any()),expected['ECE'])
    ar=read('audit_judgements.json');assert ar['evidence_type']=='SIMULATED_JUDGEMENTS'
    a=np.array([x['judgement_A'] for x in ar['rows']]);b=np.array([x['judgement_B'] for x in ar['rows']]);po=(a==b).mean();pe=a.mean()*b.mean()+(1-a.mean())*(1-b.mean())
    close(100*po,r['audit_overall']['agreement']);close((po-pe)/(1-pe),r['audit_overall']['kappa'])
    dt=read('derived_tables.json')
    for ds,entries in dt['oracle_counts'].items():
        for entry in entries.values():close(f1([entry['tp'],entry['fp'],entry['fn']]),entry['f1'])
    source=(W.parent/'report_1009_v3_full.md').read_text()
    old=(W.parent/'report_1009_v2_full.md').read_text()
    import re
    assert re.findall(r'\$\$(.*?)\$\$',source,re.S)==re.findall(r'\$\$(.*?)\$\$',old,re.S)
    def appendix_e(s):return s[s.index('# 附录E'):s.index('# 附录F')]
    assert appendix_e(source)==appendix_e(old)
    assert '@@' not in source and '稿件说明：本稿为模拟数据演示稿。' in source
    result={'passed':True,'scope':'ARITHMETIC_AND_DOCUMENT_IDENTITY_ONLY','genuine_corpus_or_model_runs':0,'count_rows':n,'metric_cells':metrics,'paired_and_interaction_intervals':intervals,'probability_rows':len(sr['records']),'judgement_rows':len(ar['rows']),'unchanged_display_equations':32,'appendix_E_unchanged':True,'source_sha256':hashlib.sha256(source.encode()).hexdigest()}
    (W/'numerical_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False))
if __name__=='__main__':main()
