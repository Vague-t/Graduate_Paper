"""Post-freeze evaluation and independent trace/archive audit. Never edits outputs."""
from pathlib import Path
import json, hashlib, itertools, zipfile, csv, io
from datetime import datetime, timezone
from collections import Counter,defaultdict
ROOT=Path(__file__).resolve().parent
RUN=ROOT/'results/run_001'
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def write(p,o):
    if p.exists():raise FileExistsError(p)
    p.write_text(json.dumps(o,ensure_ascii=False,indent=2)+'\n')
def ckey(c):return (c['start'],c['end'],c['type'])
def rkey(r,cs):return (tuple(sorted(ckey(cs[c]) for c in r['sources'])),ckey(cs[r['target']]),r['type'])
def object_sets(d,st):return ({ckey(d['components'][c]) for c in st['C']},{rkey(d['relations'][r],d['components']) for r in st['R']})
def stats(pred,gold):
    tp=len(pred&gold);fp=len(pred-gold);fn=len(gold-pred)
    return from_counts(tp,fp,fn)
def from_counts(tp,fp,fn):
    return {'TP':tp,'FP':fp,'FN':fn,'precision':tp/(tp+fp) if tp+fp else 0.,'recall':tp/(tp+fn) if tp+fn else 0.,'F1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.}
def gold_keys(g):
    cs=[(c['char_start'],c['char_end'],c['type']) for c in g['components']]
    assert all(c[0] is not None for c in cs),g['id']
    return set(cs),{(tuple(sorted(cs[i] for i in r['sources'])),cs[r['target']],r['type']) for r in g['relations']}
def changes(old,new,gold):
    return {'TP_recovered':len((new-old)&gold),'TP_lost':len((old-new)&gold),'FP_removed':len((old-new)-gold),
            'FP_added':len((new-old)-gold),'initial_TP':len(old&gold),'initial_TP_retained':len(old&new&gold)}
def overlap(a,b):return max(a['start'],b['start'])<min(a['end'],b['end'])
def slot(r):return (tuple(r['sources']),r['target'])
def rellegal(d,r,C):
    ends=set(r['sources'])|{r['target']}
    if not ends<=C or r['target'] in r['sources'] or not r['sources']:return False
    if d['corpus']=='cdcp':
        order=sorted(C,key=lambda c:ckey(d['components'][c]));pos=sorted(order.index(c) for c in r['sources'])
        if pos!=list(range(pos[0],pos[-1]+1)):return False
    return True
def valid(d,C,R):
    assert not any(overlap(d['components'][a],d['components'][b]) for a,b in itertools.combinations(C,2))
    assert all(rellegal(d,d['relations'][r],C) for r in R)
    assert len({slot(d['relations'][r]) for r in R})==len(R)
def audit_trace(d,res,q):
    cs=d['components'];rs=d['relations'];ec=er=0;commits=[]
    def u(X,t):return sum(2*q[t][x]-1 for x in X)
    cur=res['initial'];groups=[]
    for attempt in res['attempts']:
        if not groups or groups[-1][0]['before']!=attempt['before']:groups.append([])
        groups[-1].append(attempt)
    for group in groups:
        assert group[0]['before']==cur
        winners=[a for a in group if a['committed']];assert len(winners)<=1
        for a in group:
            C=set(a['before']['C']);R=set(a['before']['R']);p=a['proposal'];D=set(p['D']);B=set(p['B']);Cp=(C-D)|B
            assert sorted(Cp)==a['candidate_C']
            assert D<=C and not B&C and len(D)+len(B)<=3
            assert {c for c in C if any(overlap(cs[c],cs[b]) for b in B)}<=D
            if a['accepted_candidate']:
                Rn=set(a['after']['R']);assert set(a['after']['C'])==Cp
                P={r for r,v in rs.items() if (set(v['sources'])|{v['target']})&(D|B)}|set(p['S_R'])
                exp={slot(rs[r]) for r in R-P if not rellegal(d,rs[r],Cp)}
                P|={r for r,v in rs.items() if slot(v) in exp}
                assert set(a['transaction_relations'])==P and Rn-P==R-P
                valid(d,Cp,Rn);dc=u(Cp,'C')-u(C,'C');dr=u(Rn,'R')-u(R,'R')
                assert dc>=-1e-8 and dr>=-1e-8 and dc+dr>.01+1e-8
                assert abs(a['delta_phi']-dc-dr)<1e-7
                assert a['component_edits']==len(C^Cp) and a['relation_edits']==len(R^Rn)
                assert ec+len(C^Cp)<=24 and er+len(R^Rn)<=96
        if winners:
            a=winners[0];cur=a['after'];ec+=a['component_edits'];er+=a['relation_edits'];commits.append(a['attempt'])
    assert cur==res['final'] and commits==res['accepted_attempts']
    assert ec==res['component_edits_total'] and er==res['relation_edits_total']
    assert len(res['attempts'])<=128 and len(commits)<=12
    assert all(r['attempts']<=32 and r['accepts']<=3 for r in res['rounds'])
    if res['mode']=='RelationOnly':assert res['initial']['C']==res['final']['C']
    valid(d,set(cur['C']),set(cur['R']))
    return {'id':d['id'],'mode':res['mode'],'attempts':len(res['attempts']),'eligible':sum(a['accepted_candidate'] for a in res['attempts']),
            'commits':len(commits),'component_edits':ec,'relation_edits':er,'status':'PASS'}

def audit_archive(g):
    # Independent native read, not the preparation loader.
    old=ROOT.parent/'research_0920/data';ident=g['source_doc_id'];C=[];R=[]
    if g['corpus']=='aaec':
        split={x['ID']:x['SET'] for x in csv.DictReader(io.StringIO((old/'aaec_split.csv').read_text()),delimiter=';')}
        assert split[ident]=='TRAIN'
        with zipfile.ZipFile(old/'aaec_brat.zip') as z:
            text=z.read('brat-project-final/'+ident+'.txt').decode();ann=z.read('brat-project-final/'+ident+'.ann').decode()
        ids={};rels=[]
        for line in ann.splitlines():
            f=line.split('\t')
            if f[0].startswith('T'):
                t,s,e=f[1].split();s=int(s);e=int(e);assert text[s:e]==f[2];ids[f[0]]=len(C);C.append((s,e,t))
            if f[0].startswith('R'):
                t,a,b=f[1].split();rels.append((a.split(':')[1],b.split(':')[1],t))
        R=[((ids[a],),ids[b],t) for a,b,t in rels]
    else:
        with zipfile.ZipFile(old/'cdcp_acl17.zip') as z:
            stem='cdcp/train/'+ident;text=z.read(stem+'.txt').decode();a=json.loads(z.read(stem+'.ann.json'))
        C=[(s,e,t) for (s,e),t in zip(a['prop_offsets'],a['prop_labels'])]
        R=[(tuple(range(s,e+1)),t,lab) for field,lab in [('reasons','reason'),('evidences','evidence')] for (s,e),t in a[field]]
    assert text==g['text'];norm=[]
    for s,e,t in C:
        while text[s:e] and text[s].isspace():s+=1
        while text[s:e] and text[e-1].isspace():e-=1
        norm.append((s,e,t))
    exactC=set(norm);exactR={(tuple(sorted(norm[i] for i in ss)),norm[t],lab) for ss,t,lab in R}
    assert (exactC,exactR)==gold_keys(g)
    return {'id':g['id'],'components':len(exactC),'relations':len(exactR),'multisource_relations':sum(len(r[0])>1 for r in exactR),'status':'PASS'}

def main():
    out=ROOT/'results/evaluation_001';out.mkdir(exist_ok=False)
    first=datetime.now(timezone.utc).isoformat()
    frozen=read(RUN/'input_freeze.json');outfreeze=read(RUN/'output_freeze.json')
    for p,h in frozen['hashes'].items():assert sha(ROOT/p)==h,p
    for p,h in outfreeze['hashes'].items():assert sha(RUN/p)==h,p
    docs=read(ROOT/'candidate_pools.json')['documents'];gm={}
    for corpus in sorted({d['corpus'] for d in docs}):
        for g in read(ROOT/'evaluation'/f'{corpus}_gold.json')['documents']:gm[g['id']]=g
    rows=[];traceaudit=[];archiveaudit=[];object_changes=[]
    for d in docs:
        gold=gm[d['id']];archiveaudit.append(audit_archive(gold));GC,GR=gold_keys(gold)
        qs=read(ROOT/'scores'/f"{d['id']}.json");q={'C':qs['component_scores'],'R':{r:qs['relation_score_overrides'].get(r,.05) for r in d['relations']}}
        br=read(RUN/f"{d['id']}__BRJ-lite.json");ro=read(RUN/f"{d['id']}__RelationOnly.json")
        run_status={m:r['status'] for m,r in [('BRJ-lite',br),('RelationOnly',ro)]}
        assert br['ranks']==ro['ranks']
        rank=min(br['ranks'],key=lambda r:(-r['rank'],r['slot'])) if br['ranks'] else None
        selected=d['graphs'][rank['slot']] if rank else None
        base={'C':selected['components'],'R':selected['relations']} if selected else {'C':[],'R':[]}
        init=object_sets(d,base);methods={'MCR-only':init}
        for m,res in [('BRJ-lite',br),('RelationOnly',ro)]:
            if res['status']=='completed':
                assert res['initial']==base
                traceaudit.append(audit_trace(d,res,q));methods[m]=object_sets(d,res['final'])
            else:
                assert res['status']=='initial_failure'
                assert selected is None or not selected['structurally_valid']
                traceaudit.append({'id':d['id'],'mode':m,'status':'PASS_EXPECTED_INITIAL_FAILURE','trace_available':False})
                # Evaluation convention only; no fallback graph is claimed as a returned output.
                methods[m]=(set(),set())
        for g in d['graphs']:methods[g['candidate_id']]=object_sets(d,{'C':g['components'],'R':g['relations']})
        row={'id':d['id'],'corpus':d['corpus'],'initial_candidate':selected['candidate_id'] if selected else None,'gold_C':len(GC),'gold_R':len(GR),
             'run_status':run_status,'initial_structurally_valid':bool(selected and selected['structurally_valid']),
             'failed_output_evaluation_convention':'No returned prediction is counted as empty; all gold remains FN; no repaired graph or semantic deletion is claimed',
             'metrics':{m:{'C':stats(p[0],GC),'R':stats(p[1],GR)} for m,p in methods.items()},
             'changes':{m:{'C':changes(init[0],p[0],GC),'R':changes(init[1],p[1],GR)} for m,p in methods.items() if m in ('BRJ-lite','RelationOnly')}}
        allC={ckey(v) for v in d['components'].values()};allR={rkey(v,d['components']) for v in d['relations'].values()}
        row['coverage']={'C_hits':len(allC&GC),'C_gold':len(GC),'R_hits':len(allR&GR),'R_gold':len(GR),
                         'R_all_endpoints_present':sum(set(r[0])|{r[1]}<=allC for r in GR),
                         'R_multisource_gold':sum(len(r[0])>1 for r in GR),'R_multisource_in_pool':sum(len(r[0])>1 for r in allR&GR),
                         'C_candidates':len(allC),'R_candidates':len(allR)}
        row['relation_F1_delta']=row['metrics']['BRJ-lite']['R']['F1']-row['metrics']['MCR-only']['R']['F1']
        row['component_F1_delta']=row['metrics']['BRJ-lite']['C']['F1']-row['metrics']['MCR-only']['C']['F1']
        row['relation_outcome']=('failure' if br['status']!='completed' else ('improvement' if row['relation_F1_delta']>1e-10 else ('harm' if row['relation_F1_delta']<-1e-10 else 'unchanged')))
        rows.append(row)
        diffs={'id':d['id']}
        for m,p in methods.items():
            if m not in ('BRJ-lite','RelationOnly'):continue
            diffs[m]={}
            for k,base,final,gg in [('C',init[0],p[0],GC),('R',init[1],p[1],GR)]:
                diffs[m][k]={lab:sorted(s) for lab,s in {'TP_recovered':(final-base)&gg,'TP_lost':(base-final)&gg,'FP_removed':(base-final)-gg,'FP_added':(final-base)-gg}.items()}
        object_changes.append(diffs)
    aggregate={};case_selection={}
    for corpus in sorted({d['corpus'] for d in docs}):
        rr=[r for r in rows if r['corpus']==corpus];agg={'documents':len(rr),'metrics':{},'changes':{},'coverage':{}}
        for m in ['g0','g1','MCR-only','RelationOnly','BRJ-lite']:
            agg['metrics'][m]={k:from_counts(*(sum(r['metrics'][m][k][n] for r in rr) for n in ['TP','FP','FN'])) for k in ['C','R']}
        for m in ['RelationOnly','BRJ-lite']:
            agg['changes'][m]={k:{n:sum(r['changes'][m][k][n] for r in rr) for n in rr[0]['changes'][m][k]} for k in ['C','R']}
        agg['coverage']={k:sum(r['coverage'][k] for r in rr) for k in rr[0]['coverage']}
        agg['document_relation_outcomes']=dict(Counter(r['relation_outcome'] for r in rr))
        aggregate[corpus]=agg
        case_selection[corpus]={k:next((r['id'] for r in sorted(rr,key=lambda x:x['id']) if r['relation_outcome']==k),None) for k in ['improvement','harm','unchanged']}
    costs={};statuses=Counter();ties=Counter();reasons=Counter();shapes=Counter()
    for p in RUN.glob('*__*.json'):
        r=read(p);k=r.get('corpus',r['id'].split('_')[0])+'__'+r['mode'];v=costs.setdefault(k,{'documents':0,'completed_documents':0,'failed_documents':0,'wall_seconds':0,'solver_seconds':0,'attempts':0,'accepts':0,'calls':0,'component_edits':0,'relation_edits':0,'timing_scope':'completed repair-stage runs only; initial failure durations not recorded'})
        v['documents']+=1
        if r['status']!='completed':v['failed_documents']+=1;continue
        v['completed_documents']+=1;v['wall_seconds']+=r['wall_seconds'];v['solver_seconds']+=r['solver_seconds'];v['attempts']+=len(r['attempts']);v['accepts']+=len(r['accepted_attempts']);v['calls']+=len(r['solver_calls']);v['component_edits']+=r['component_edits_total'];v['relation_edits']+=r['relation_edits_total']
        statuses.update(str(c['status']) for c in r['solver_calls'])
        ties.update(a.get('tie_status','not_reached') for a in r['attempts'] if a['committed'])
        reasons.update(a['reason'] for a in r['attempts']);shapes.update(r['mode']+':'+a['proposal']['kind'] for a in r['attempts'] if a['committed'])
    result={'experiment_id':'AM-LUNA-20261011-EXPAND-007','evaluation_started_at_utc':first,'output_freeze_at_utc':outfreeze['frozen_at_utc'],
            'evaluation_code_sha256':sha(__file__),'zero_division':'F1=0 when TP=FP=FN=0; report FP changes separately',
            'aggregate':aggregate,'documents':rows,'case_selection':case_selection,'costs':costs,
            'solver_status_counts':dict(statuses),'committed_tie_status_counts':dict(ties),'attempt_reason_counts':dict(reasons),'committed_shape_counts':dict(shapes)}
    write(out/'metrics.json',result);write(out/'object_changes.json',object_changes)
    write(out/'audit.json',{'status':'PASS','frozen_input_hashes_unchanged':True,'frozen_output_hashes_unchanged':True,'native_archive_checks':archiveaudit,'trace_checks':traceaudit})
    print(json.dumps({'aggregate':aggregate,'case_selection':case_selection,'costs':costs,'solver_status_counts':dict(statuses),'committed_shape_counts':dict(shapes)},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
