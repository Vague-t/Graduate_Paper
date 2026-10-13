"""Independent read-only v12 audit. All output stays beside this script."""
from pathlib import Path
import csv
import hashlib
import json
import statistics
from collections import Counter, defaultdict

ROOT = Path('/Users/channtang/Downloads/paper')
OUT = Path(__file__).resolve().parent

def read(p):
    return json.loads(p.read_text())

def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def f1(v):
    t, p, n = v
    return 200*t/(2*t+p+n) if 2*t+p+n else 0.

def add(a, b):
    return [x+y for x,y in zip(a,b)]

def counts(a,b):
    return [len(a&b),len(a-b),len(b-a)]

def ckey(c):
    return (c['start'],c['end'],c['type'])

def predkeys(d,s):
    return ({ckey(d['components'][c]) for c in s['C']},
            {(tuple(sorted(ckey(d['components'][c]) for c in d['relations'][r]['sources'])),
              ckey(d['components'][d['relations'][r]['target']]),d['relations'][r]['type']) for r in s['R']})

def main():
    manifest=read(ROOT/'1011_v12内容与数据清单.json')
    checked=0
    for name,digest in manifest['files'].items():
        assert sha(ROOT/name)==digest, name
        checked+=1
    refs=[]
    cache=ROOT/'tmp/pdfs/comparison_1009'
    attachments=Path('/Users/channtang/Library/Containers/com.tencent.xinWeChat/Data/Documents/xwechat_files/wxid_cqn98y9b01mm12_58e7/msg/file/2026-10')
    for slug in ['contrastive','style_transfer','transformer','temporal_kg']:
        m=read(cache/f'{slug}_metadata.json');p=Path(m['source'])
        if not p.exists():p=attachments/p.name
        pre=read(cache/f'{slug}_preflight.json')
        assert sha(p)==m['sha256']==pre['sha256'] and pre['verdict']=='PASS'
        refs.append({'slug':slug,'path':str(p),'sha256':sha(p),'preflight':pre['verdict'],'page_count':m['page_count']})
    sim=ROOT/'_revision_1011_v12/simulation'
    result=read(sim/'results.json')
    rows=list(csv.DictReader((sim/'document_counts.csv').open()))
    totals=defaultdict(lambda:[0,0,0]);raw={}
    for r in rows:
        key=(r['protocol'],r['dataset'],r['object'],int(r['seed']),r['method'])
        v=[int(r[k]) for k in ['tp','fp','fn']]
        assert min(v)>=0 and r['evidence_type']=='SIMULATED_COUNT_OBJECTS'
        totals[key]=add(totals[key],v)
        dk=key+(int(r['document'].rsplit('-',1)[1])-1,)
        assert dk not in raw
        raw[dk]=v
    members={}
    for line in (sim/'object_membership.jsonl').open():
        r=json.loads(line);key=tuple(r[k] for k in ['protocol','dataset','object','seed','method'])
        tp=set(r['true_ids']);fp=set(r['false_ids']);gd=r['gold_document'];fd=r['false_document']
        assert len(tp)==len(r['true_ids']) and len(fp)==len(r['false_ids'])
        assert min(tp)>=0 and max(tp)<len(gd) and min(fp)>=0 and max(fp)<len(fd)
        assert totals[key]==[len(tp),len(fp),r['gold_n']-len(tp)]
        t=Counter(gd[i] for i in tp);p=Counter(fd[i] for i in fp);g=Counter(gd)
        for doc in g:assert raw[key+(doc,)]==[t[doc],p[doc],g[doc]-t[doc]]
        members[key]=(tp,fp)
    scalar_checks=0
    for protocol,datasets in result['metrics'].items():
        for ds,methods in datasets.items():
            for method,axes in methods.items():
                for axis,m in axes.items():
                    arr=[totals[protocol,ds,axis,s,method] for s in result['seeds']]
                    vals=[f1(v) for v in arr]
                    assert arr==m['counts']
                    for a,b in zip(vals,m['seeds']):assert abs(a-b)<1e-10
                    assert abs(statistics.mean(vals)-m['mean'])<1e-10
                    assert abs(statistics.stdev(vals)-m['sd'])<1e-10
                    scalar_checks+=2
    for row in result['members']:
        key=tuple(row[k] for k in ['protocol','dataset','object','seed'])
        a,b,c,d=[members[key+(m,)][0] for m in ['t0_i0','t1_i0','t0_i1','t1_i1']]
        expected={'baseline':len(a),'both_only':len((b-a)&(c-a)),
                  'training_only':len((b-a)-(c-a)),'repair_only':len((c-a)-(b-a)),
                  'neither_single_but_combined':len(d-(a|b|c)),
                  'single_recovery_lost_in_combined':len(((b|c)-a)-d),'baseline_lost_combined':len(a-d)}
        assert all(row[k]==v for k,v in expected.items())
    for ds,methods in result['risk'].items():
        for method,row in methods.items():
            vals=Counter()
            for seed in result['seeds']:
                bt,bf=members['strict_native',ds,'relation',seed,'mcr_t1'];at,af=members['strict_native',ds,'relation',seed,method]
                vals.update(recovered=len(at-bt),lost_tp=len(bt-at),removed_fp=len(bf-af),added_fp=len(af-bf),base_tp=len(bt))
            assert all(row[k]==v for k,v in vals.items())
            assert abs(row['tp_retention']-100*(1-vals['lost_tp']/vals['base_tp']))<1e-10
    casi=ROOT/'research_1011_v12/casimedicos'
    docs={d['id']:d for d in read(casi/'candidate_pools.json')['documents']}
    gold={d['id']:d for d in read(ROOT/'research_1011_v11/candidate/evaluation/source_gold.json')['documents'] if d['id'] in docs}
    goldkeys={}
    for ident,d in gold.items():
        cs=[(c['char_start'],c['char_end'],c['type']) for c in d['components']]
        rs={(tuple(sorted(cs[i] for i in r['sources'])),cs[r['target']],r['type']) for r in d['relations']}
        goldkeys[ident]=(set(cs),rs)
    agg=defaultdict(lambda:{'C':[0,0,0],'R':[0,0,0],'n':0,'changed_docs':0})
    metrics=read(casi/'evaluation/metrics.json')
    existing={(r['id'],r['mode'],r['threshold']):r for r in metrics['rows']}
    summaries=read(casi/'results/summary.json')
    for item in summaries:
        z=read(casi/'results'/item['file']);ident=z['id'];ck,rk=predkeys(docs[ident],z['final']);gc,gr=goldkeys[ident]
        row=existing[ident,item['mode'],item['threshold']]
        key=(item['mode'],item['threshold'])
        for ax,p,g in [('C',ck,gc),('R',rk,gr)]:
            v=counts(p,g);assert v==row[ax];agg[key][ax]=add(agg[key][ax],v)
        agg[key]['n']+=1
        agg[key]['changed_docs']+=int(z['final']!=z['initial'])
    for row in metrics['summary']:
        if row['threshold'] is None:continue
        computed=agg[row['mode'],row['threshold']]
        for axis in ['C','R']:
            assert computed[axis]==[row[axis][k] for k in ['tp','fp','fn']]
            assert abs(f1(computed[axis])-row[axis]['f1'])<1e-10
    scores=read(casi/'validated_scores.json');scorecheck=[]
    for axis in ['C','R']:
        pairs=[]
        for ident,d in docs.items():
            for obj,p in scores[ident][axis].items():
                st={'C':[obj] if axis=='C' else [],'R':[obj] if axis=='R' else []}
                k=next(iter(predkeys(d,st)[axis=='R']))
                pairs.append((p,int(k in goldkeys[ident][axis=='R'])))
        pos=[p for p,y in pairs if y];neg=[p for p,y in pairs if not y]
        auc=sum((p>n)+.5*(p==n) for p in pos for n in neg)/(len(pos)*len(neg))
        brier=statistics.mean((p-y)**2 for p,y in pairs)
        old=next(r for r in metrics['score_audit'] if r['object']==axis)
        assert abs(auc-old['AUROC'])<1e-12 and abs(brier-old['Brier'])<1e-12
        rate=len(pos)/len(pairs)
        scorecheck.append({'axis':axis,'n':len(pairs),'positive':len(pos),'AUROC':auc,'Brier':brier,
                           'positive_rate':rate,'constant_prevalence_Brier':rate*(1-rate),
                           'constant_zero_Brier':rate,'positives_gt_05':sum(p>.5 for p in pos),'negatives_gt_05':sum(p>.5 for p in neg)})
    evidence={'manuscript_sha256':sha(ROOT/'report_1011_v12_content.md'),
              'package_manifest_files_hash_verified':checked,'references':refs,
              'simulation':{'count_rows':len(rows),'object_records':len(members),'mean_sd_scalar_checks':scalar_checks,
                            'all_document_count_membership_matches':True,'risk_and_four_grid_members_recomputed':True,
                            'bootstrap_CIs_rerun':False,'model_training_or_solver_execution':False},
              'real_outputs_recounted':len(summaries),'real_unique_documents':len(docs),
              'real_summary':[{'mode':k[0],'threshold':k[1],**v,'C_f1':f1(v['C']),'R_f1':f1(v['R'])} for k,v in agg.items()],
              'scores_recomputed':scorecheck,
              'limits':['stored scores and outputs only; no new LLM calls or solver rerun',
                        'score payloads and frozen files do not independently attest hidden tool metadata',
                        'no PDF of v12, no layout acceptance claim']}
    target=OUT/'independent_audit.json'
    with target.open('x') as stream:json.dump(evidence,stream,ensure_ascii=False,indent=2)
    print(json.dumps(evidence,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
