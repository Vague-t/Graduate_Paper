"""Post-freeze strict metrics, native-source reconciliation, and transaction audit."""
from pathlib import Path
from datetime import datetime, timezone
from collections import Counter, defaultdict
import ast, csv, hashlib, importlib.util, json, re, sys, unicodedata

BASE=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('audit_primitives',BASE.parent/'research_1010_v7_luna/evaluate.py')
old=importlib.util.module_from_spec(spec);spec.loader.exec_module(old)
read=old.read;sha=old.sha;write=old.write;gold_keys=old.gold_keys
object_sets=old.object_sets;stats=old.stats;from_counts=old.from_counts;changes=old.changes

def independent_native(g):
    """A second implementation reads release files; never calls the converter."""
    if g['corpus']=='cdcp':return old.audit_archive(g)
    raw=BASE/'datasets/raw';C=[];edges=[]
    if g['corpus']=='argunsc':
        rows=[r for r in csv.DictReader((raw/'argunsc_base.csv').open()) if r['Speech']==g['source_doc_id']]
        sentences=sorted({(int(r['Sentence_ID']),r['Full_Sentence']) for r in rows})
        text=' '.join(s for _,s in sentences);bounds={};at=0
        for sid,s in sentences:bounds[sid]=(at,at+len(s));at+=len(s)+1
        ids={}
        for row in rows:
            if row['Component_Type']=='non-arg':continue
            ident,quote=ast.literal_eval(row['Component']);quote=quote.strip()
            lo,hi=bounds[int(row['Sentence_ID'])]
            positions=[];start=lo
            while True:
                pos=text.find(quote,start)
                if pos<0 or pos>=hi:break
                positions.append(pos);start=pos+1
            assert len(positions)==1 and ident not in ids
            ids[ident]=(positions[0],positions[0]+len(quote),row['Component_Type'])
        C=set(ids.values())
        # Relation labels come from the separately distributed positive-pair CSV.
        for row in csv.DictReader((raw/'argunsc_component_relations_local.csv').open()):
            if row['relation type']=='no relation':continue
            a,b=ast.literal_eval(row['ids of components'])
            if a in ids or b in ids:
                assert a in ids and b in ids
                edges.append(((ids[a],),ids[b],row['relation type']))
        R=set(edges)
    else:
        row=next(r for r in read(raw/f"casimedicos_en_{g['split']}_en_ordered.json") if r['id']==g['source_doc_id'])
        text='\n'.join(' '.join(toks) for toks in row['text']);at=0
        for toks,labs in zip(row['text'],row['labels']):
            offsets=[]
            for tok in toks:offsets.append((at,at+len(tok)));at+=len(tok)+1
            i=0
            while i<len(labs):
                if labs[i] not in ('B-Claim','B-Premise'):i+=1;continue
                typ=labs[i][2:];j=i+1
                while j<len(labs) and labs[j]=='I-'+typ:j+=1
                C.append((offsets[i][0],offsets[j-1][1],typ));i=j
        def key(s):return re.sub(r'\s+',' ',unicodedata.normalize('NFKC',s)).strip().rstrip(' .,:;!?')
        mapping=defaultdict(list)
        for c in C:mapping[key(text[c[0]:c[1]])].append(c)
        native=[];found=False
        for line in (raw/f"casimedicos_relations_{g['split']}_relations.jsonl").read_text().splitlines():
            rec=json.loads(line)
            if isinstance(rec,list):rec=rec[0]
            if g['source_doc_id'] in rec:
                assert not found;native=rec[g['source_doc_id']];found=True
        assert found
        for a,b,lab in native:
            aa=mapping[key(a)];bb=mapping[key(b)]
            assert len(aa)==len(bb)==1 and aa!=bb
            edges.append(((aa[0],),bb[0],lab))
        C=set(C);R=set(edges)
    assert text==g['text'],g['id']
    assert (C,R)==gold_keys(g),g['id']
    return {'id':g['id'],'components':len(C),'relations':len(R),'multisource_relations':sum(len(x[0])>1 for x in R),'status':'PASS','source':'independent release-file reconstruction; ArgUNSC pair CSV relation authority'}

def qload(root,d,condition):
    if condition=='sparse':
        q=read(root/'scores'/f"{d['id']}.json")
        return {'C':q['component_scores'],'R':{r:q['relation_score_overrides'].get(r,.05) for r in d['relations']}},{'C':[],'R':[]}
    q=read(root/'scores_dense'/f"{d['id']}.json")
    unknown={axis:[k for k,v in q[field].items() if v is None] for axis,field in [('C','component_scores'),('R','relation_scores')]}
    return {axis:{k:.5 if v is None else v for k,v in q[field].items()} for axis,field in [('C','component_scores'),('R','relation_scores')]},unknown

def main(root):
    run=root/'results/run_001';freeze=read(run/'output_freeze.json')
    for p,h in read(run/'input_freeze.json')['hashes'].items():assert sha(root/p)==h,p
    for p,h in freeze['hashes'].items():assert sha(run/p)==h,p
    for p,h in read(root/'pre_prediction_freeze.json')['hashes'].items():assert sha(root/p)==h,p
    top=read(BASE/'pre_experiment_manifest.json')
    for p,h in top['raw_sources'].items():assert sha(BASE/p)==h,p
    out=root/'results/evaluation_001';out.mkdir(exist_ok=False)
    first=datetime.now(timezone.utc).isoformat()
    docs=read(root/'candidate_pools.json')['documents'];gold={}
    for path in (root/'evaluation').glob('*_gold.json'):
        gold.update({g['id']:g for g in read(path)['documents']})
    assert set(gold)=={d['id'] for d in docs}
    native=[];traces=[];rows=[];objects=[];costs={};reason_counts=Counter();solver_counts=Counter();shapes=Counter()
    conditions=['sparse','dense_native'] if root.name=='cdcp_scoring' else ['sparse']
    common=read(run/'common_initial_states.json')
    for d in docs:
        g=gold[d['id']];native.append(independent_native(g));GC,GR=gold_keys(g)
        chosen=common[d['id']]['graph'];init={'C':[],'R':[]}
        if chosen is not None and chosen['structurally_valid']:init={'C':chosen['components'],'R':chosen['relations']}
        base=object_sets(d,init);methods={'MCR-only':base};run_meta={}
        for ident in ['g0','g1']:
            graph=next((x for x in d['graphs'] if x['candidate_id']==ident),None)
            methods[ident]=object_sets(d,{'C':graph['components'],'R':graph['relations']}) if graph and graph['structurally_valid'] else (set(),set())
        for cond in conditions:
            q,unknown=qload(root,d,cond)
            for mode in ['BRJ-lite','RelationOnly']:
                result=read(run/f"{d['id']}__{cond}__{mode}.json");label=cond+'__'+mode
                if result['status']=='completed':
                    assert result['initial']=={'C':sorted(init['C']),'R':sorted(init['R'])}
                    audit=old.audit_trace(d,result,q);audit['condition']=cond;traces.append(audit)
                    for a in result['attempts']:
                        if a['accepted_candidate']:
                            assert not (set(a['proposal']['D'])|set(a['proposal']['B']))&set(unknown['C'])
                            assert not set(a['transaction_relations'])&set(unknown['R'])
                    methods[label]=object_sets(d,result['final'])
                else:
                    assert result['status'] in ('initial_failure','construction_failure') and not init['C'] and not init['R']
                    methods[label]=(set(),set());traces.append({'id':d['id'],'mode':mode,'condition':cond,'status':'PASS_FAILURE_RETAINED'})
                run_meta[label]={k:result.get(k) for k in ['status','stop_reason','solver_seconds','total_run_wall_seconds']}
                k=d['corpus']+'__'+label;c=costs.setdefault(k,{'documents':0,'completed':0,'failures':0,'wall_seconds':0.,'solver_seconds':0.,'attempts':0,'commits':0,'solver_calls':0,'component_edits':0,'relation_edits':0,'unknown_C':0,'unknown_R':0})
                c['documents']+=1;c['completed']+=int(result['status']=='completed');c['failures']+=int(result['status']!='completed')
                c['wall_seconds']+=result['total_run_wall_seconds'];c['solver_seconds']+=result.get('solver_seconds',0.)
                c['attempts']+=len(result.get('attempts',[]));c['commits']+=len(result.get('accepted_attempts',[]));c['solver_calls']+=len(result.get('solver_calls',[]))
                c['component_edits']+=result.get('component_edits_total',0);c['relation_edits']+=result.get('relation_edits_total',0)
                c['unknown_C']+=len(unknown['C']);c['unknown_R']+=len(unknown['R'])
                reason_counts.update(cond+'__'+a['reason'] for a in result.get('attempts',[]))
                solver_counts.update(str(a['status']) for a in result.get('solver_calls',[]))
                shapes.update(cond+'__'+mode+'__'+a['proposal']['kind'] for a in result.get('attempts',[]) if a['committed'])
        metrics={m:{'C':stats(p[0],GC),'R':stats(p[1],GR)} for m,p in methods.items()}
        diff={m:{'C':changes(base[0],p[0],GC),'R':changes(base[1],p[1],GR)} for m,p in methods.items() if '__' in m}
        allC={old.ckey(c) for c in d['components'].values()};allR={old.rkey(r,d['components']) for r in d['relations'].values()}
        coverage={'C_hits':len(allC&GC),'C_gold':len(GC),'R_hits':len(allR&GR),'R_gold':len(GR),'C_candidates':len(allC),'R_candidates':len(allR),'R_all_endpoints_present':sum((set(r[0])|{r[1]})<=allC for r in GR),'R_multisource_gold':sum(len(r[0])>1 for r in GR),'R_multisource_in_pool':sum(len(r[0])>1 for r in allR&GR)}
        sq,_=qload(root,d,'sparse');over=read(root/'scores'/f"{d['id']}.json")['relation_score_overrides']
        score_diag={'sparse_default_R':len(d['relations'])-len(over),'sparse_default_gold_R':sum(old.rkey(v,d['components']) in GR and r not in over for r,v in d['relations'].items()),'sparse_positive_gold_R':sum(old.rkey(v,d['components']) in GR and sq['R'][r]>=.5 for r,v in d['relations'].items())}
        if len(conditions)>1:
            dq,unk=qload(root,d,'dense_native');score_diag.update(dense_unknown_C=len(unk['C']),dense_unknown_R=len(unk['R']),dense_positive_gold_R=sum(old.rkey(v,d['components']) in GR and dq['R'][r]>=.5 and r not in unk['R'] for r,v in d['relations'].items()))
        outcomes={m:('improvement' if metrics[m]['R']['F1']>metrics['MCR-only']['R']['F1']+1e-10 else 'harm' if metrics[m]['R']['F1']<metrics['MCR-only']['R']['F1']-1e-10 else 'unchanged') for m in diff}
        rows.append({'id':d['id'],'corpus':d['corpus'],'metrics':metrics,'changes':diff,'coverage':coverage,'score_diagnostics':score_diag,'initial_candidate':None if chosen is None else chosen['candidate_id'],'parse_errors':d['parse_errors'],'parsed_graphs':len(d['graphs']),'valid_graphs':sum(x['structurally_valid'] for x in d['graphs']),'initial_failure':not(chosen and chosen['structurally_valid']),'run_meta':run_meta,'relation_outcomes':outcomes})
        objects.append({'id':d['id'],'changes':{m:{axis:{name:sorted(value) for name,value in {'TP_recovered':(p[i]-base[i])&gg,'TP_lost':(base[i]-p[i])&gg,'FP_removed':(base[i]-p[i])-gg,'FP_added':(p[i]-base[i])-gg}.items()} for i,axis,gg in [(0,'C',GC),(1,'R',GR)]} for m,p in methods.items() if '__' in m}})
    aggregate={}
    for corpus in sorted({d['corpus'] for d in docs}):
        rr=[r for r in rows if r['corpus']==corpus];methods=list(rr[0]['metrics']);repaired=list(rr[0]['changes'])
        aggregate[corpus]={'documents':len(rr),'gold_C':sum(r['coverage']['C_gold'] for r in rr),'gold_R':sum(r['coverage']['R_gold'] for r in rr),'initial_failures':sum(r['initial_failure'] for r in rr),'parsed_graphs':sum(r['parsed_graphs'] for r in rr),'valid_graphs':sum(r['valid_graphs'] for r in rr),'metrics':{m:{axis:from_counts(*(sum(r['metrics'][m][axis][n] for r in rr) for n in ['TP','FP','FN'])) for axis in ['C','R']} for m in methods},'changes':{m:{axis:{n:sum(r['changes'][m][axis][n] for r in rr) for n in rr[0]['changes'][m][axis]} for axis in ['C','R']} for m in repaired},'coverage':{k:sum(r['coverage'][k] for r in rr) for k in rr[0]['coverage']},'score_diagnostics':{k:sum(r['score_diagnostics'][k] for r in rr) for k in rr[0]['score_diagnostics']},'relation_outcomes':{m:dict(Counter(r['relation_outcomes'][m] for r in rr)) for m in repaired},'case_selection':{m:{outcome:next((r['id'] for r in sorted(rr,key=lambda x:x['id']) if r['relation_outcomes'][m]==outcome),None) for outcome in ['improvement','harm','unchanged']} for m in repaired}}
    result={'experiment_id':read(root/'protocol.json')['experiment_id'],'evaluation_started_at_utc':first,'output_freeze_at_utc':freeze['frozen_at_utc'],'evaluation_code_sha256':sha(__file__),'aggregate':aggregate,'documents':rows,'costs':costs,'solver_status_counts':dict(solver_counts),'attempt_reason_counts':dict(reason_counts),'committed_shape_counts':dict(shapes),'zero_division':'F1=0 for zero denominator; failures count as empty predicted graph with every gold object retained','raw_graph_policy':'g0/g1 evaluated only when parsed and structurally valid; otherwise empty; no failed graph repaired with gold'}
    write(out/'metrics.json',result);write(out/'object_changes.json',objects)
    write(out/'audit.json',{'status':'PASS','frozen_input_hashes_unchanged':True,'frozen_output_hashes_unchanged':True,'upstream_source_hashes_unchanged':True,'native_archive_checks':native,'trace_checks':traces})
    print(json.dumps({'aggregate':aggregate,'costs':costs},ensure_ascii=False,indent=2))

if __name__=='__main__':main(Path(sys.argv[1]).resolve())
