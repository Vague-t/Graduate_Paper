"""Pre-outcome expansion of the frozen training-audit Luna pilot."""
from pathlib import Path
from datetime import datetime, timezone
import sys, importlib.util, hashlib, json, zipfile, shutil

ROOT=Path(__file__).resolve().parent
WORK=ROOT.parent
OLD=WORK/'research_1010_v7_luna'
DATA=WORK/'research_0920'
sys.path.insert(0,str(DATA/'vendor'))
spec=importlib.util.spec_from_file_location('legacy',DATA/'run_feasibility.py')
legacy=importlib.util.module_from_spec(spec);sys.modules[spec.name]=legacy;spec.loader.exec_module(legacy)
sha=lambda p:hashlib.sha256(Path(p).read_bytes()).hexdigest()
read=lambda p:json.loads(Path(p).read_text())
def write(p,o):
    p.parent.mkdir(parents=True,exist_ok=True)
    with p.open('x') as f:json.dump(o,f,ensure_ascii=False,indent=2);f.write('\n')
def raw_gold(d,corpus):
    if corpus=='aaec':
        with zipfile.ZipFile(DATA/'data/aaec_brat.zip') as z:
            ann=z.read('brat-project-final/'+d.ident+'.ann').decode()
        spans=[];ids={};relations=[]
        for line in ann.splitlines():
            f=line.split('\t')
            if f[0].startswith('T'):
                t,s,e=f[1].split();ids[f[0]]=len(spans);spans.append((int(s),int(e),t))
            elif f[0].startswith('R'):
                t,a,b=f[1].split();relations.append((a.split(':')[1],b.split(':')[1],t))
        rel=[{'sources':[ids[a]],'target':ids[b],'type':t} for a,b,t in relations]
    else:
        with zipfile.ZipFile(DATA/'data/cdcp_acl17.zip') as z:a=json.loads(z.read('cdcp/train/'+d.ident+'.ann.json'))
        spans=[(s,e,t) for (s,e),t in zip(a['prop_offsets'],a['prop_labels'])]
        rel=[{'sources':list(range(s,e+1)),'target':t,'type':lab} for field,lab in [('reasons','reason'),('evidences','evidence')] for (s,e),t in a[field]]
    cs=[]
    for i,(s,e,t) in enumerate(spans):
        while s<e and d.text[s].isspace():s+=1
        while e>s and d.text[e-1].isspace():e-=1
        ts,te,_=d.gold[i]
        cs.append({'token_start':ts,'token_end':te,'char_start':s,'char_end':e,'type':t})
    return {'id':corpus+'_'+d.ident,'source_doc_id':d.ident,'corpus':corpus,'text':d.text,'text_sha256':hashlib.sha256(d.text.encode()).hexdigest(),'tokens':d.tokens,'offsets':d.offsets,'components':cs,'relations':rel,'issues':d.issues}

def main():
    if (ROOT/'protocol.json').exists():raise FileExistsError('Existing frozen expansion')
    for sub in ['blind_inputs','raw_predictions','evaluation','scores','scoring_inputs','prompts','results','logs']:(ROOT/sub).mkdir(exist_ok=True)
    oldmanifest=read(OLD/'sample_manifest.json');oldby={x['id']:x for x in oldmanifest['selected']}
    frozen={str(p.relative_to(WORK)):sha(p) for p in OLD.rglob('*') if p.is_file() and '__pycache__' not in p.parts}
    for name in ['report_1011_v9_full.md','report_1011_v9_full.docx']:
        frozen[name]=sha(WORK/name)
    rows=[];plans={};batch_manifest=[];provenance={}
    for corpus in ['aaec','cdcp']:
        docs,prov=legacy.load_data(corpus);provenance[corpus]=prov
        assert prov['archive_sha256']==read(OLD/'evaluation'/f'{corpus}_provenance.json')['archive_sha256']
        _,_,audit=legacy.split_docs(docs)
        unique={hashlib.sha256(d.text.encode()).hexdigest():d for d in audit}
        ordered=sorted(unique.values(),key=lambda d:(len(d.tokens),d.ident))
        ranked=[]
        for si in range(4):
            part=ordered[len(ordered)*si//4:len(ordered)*(si+1)//4]
            ranked.append(sorted(part,key=lambda d:hashlib.sha256(('LUNA-V7-1010|'+corpus+'|'+d.text).encode()).hexdigest()))
        prior={corpus+'_'+d.ident for part in ranked for d in part[:2]}
        assert prior=={x for x in oldby if x.startswith(corpus+'_')}
        plans[corpus]=[[corpus+'_'+d.ident for d in part] for part in ranked]
        chosen=sorted([(d,si,rank+1) for si,part in enumerate(ranked) for rank,d in enumerate(part) if 2<=rank<8],key=lambda x:x[0].ident)
        assert len(chosen)==24
        blind=[];gold=[]
        for d,si,rank in chosen:
            tid=corpus+'_'+d.ident;h=hashlib.sha256(d.text.encode()).hexdigest()
            blind.append({'id':tid,'corpus':corpus,'text':d.text});gold.append(raw_gold(d,corpus))
            rows.append({'id':tid,'source_doc_id':d.ident,'corpus':corpus,'text_sha256':h,'length_stratum':si,'within_stratum_hash_rank':rank,'tokens':len(d.tokens),'chars':len(d.text),'wave':1})
        write(ROOT/'blind_inputs'/f'{corpus}.json',{'documents':blind})
        write(ROOT/'evaluation'/f'{corpus}_gold.json',{'documents':gold})
        write(ROOT/'evaluation'/f'{corpus}_provenance.json',prov)
        for k in range(3):
            name=f'{corpus}_{k+1:02d}';part=blind[8*k:8*k+8]
            write(ROOT/'blind_inputs'/f'{name}.json',{'documents':part})
            batch_manifest.append({'task':f'expand_predict_{name}','corpus':corpus,'input':f'blind_inputs/{name}.json','output':f'raw_predictions/{name}.json','documents':[d['id'] for d in part]})
    for name in ['graph_core.py','repair.py','test_repair.py','replay.py']:
        shutil.copyfile(OLD/name,ROOT/name)
    s=(ROOT/'test_repair.py').read_text().replace('self.assertEqual(len(docs),16)','self.assertEqual(len(docs),48)')
    (ROOT/'test_repair.py').write_text(s)
    s=(OLD/'evaluate.py').read_text().replace("'AM-LUNA-20261010-001'","'AM-LUNA-20261011-EXPAND-001'")
    (ROOT/'evaluate.py').write_text(s)
    scoring=read(OLD/'scoring_protocol.json');scoring['status']='FROZEN_BEFORE_NEW_PREDICTIONS';write(ROOT/'scoring_protocol.json',scoring)
    inst=(OLD/'prompts/scoring_instructions.md').read_text().replace('AM-LUNA-20261010-001','AM-LUNA-20261011-EXPAND-001')
    (ROOT/'prompts/scoring_instructions.md').write_text(inst)
    for corpus in ['aaec','cdcp']:
        s=(OLD/'prompts'/f'predict_{corpus}.txt').read_text()
        # Preserve task definitions. File dispatch supplies the exact batch paths.
        s=s.replace(str(OLD/'blind_inputs'/f'{corpus}.json'),'the one blind input JSON named in your task message')
        s=s.replace(str(OLD/'raw_predictions'/f'{corpus}_luna.json'),'the one output JSON path named in your task message')
        s=s.replace('Only read the one blind input JSON named in your task message.','Only read this instruction and the one blind input JSON named in your task message.')
        (ROOT/'prompts'/f'prediction_{corpus}.txt').write_text(s)
    write(ROOT/'sample_manifest.json',{'selection':'Continuation of original length-quartile SHA256 ranking; ranks 3 through 8 per stratum, plus frozen original ranks 1 and 2; selected before new outputs','selection_seed_label':'LUNA-V7-1010','old_documents':oldmanifest['selected'],'selected':rows,'full_preordered_extension_plan':plans,'prediction_batches':batch_manifest})
    protocol=read(OLD/'protocol.json')
    protocol.update(experiment_id='AM-LUNA-20261011-EXPAND-001',created_at_utc=datetime.now(timezone.utc).isoformat(),purpose='Expanded exploratory real-case search with all outcomes retained; not confirmatory efficacy estimation',manuscript={'path':str(WORK/'report_1011_v9_full.md'),'sha256':sha(WORK/'report_1011_v9_full.md')},generation={**protocol['generation'],'new_documents_per_corpus':24,'cumulative_documents_per_corpus':32,'prediction_task_batch_size':8},evaluation='Exact original character boundaries/types and complete typed native relations; same evaluator as initial 16; all selected documents including failures stay in denominators',gold_blinding='Fresh no-history prediction and score agents; instructional file whitelist, shared filesystem not OS isolation; preparation reads annotations solely for later evaluation, outputs evaluated only after freeze',continuation={'initial_target_per_corpus':32,'positive_primary':'strict complete relation F1 > MCR-only; separately identify recovered-TP cases and improvement beyond RelationOnly','selection_of_cases':'lexicographic first per outcome, plus lexicographic first TP-recovery and BRJ-over-RelationOnly cases; list all positive IDs','extension_trigger':'After completing all first-wave documents, if a corpus has no strict relation F1 improvement, expand only that corpus by the next 4 ranks per length stratum (up to 16 documents per complete wave), preserving all prior outcomes','stop':'Stop once both corpora contain an improvement after a completed wave, or each lacking-positive corpus exhausts its preordered unique audit-text pool; never tune scores or redraw candidates using gold','remaining_population':{k:sum(map(len,v)) for k,v in plans.items()},'inference_limit':'Outcome-adaptive expansion is case discovery; no significance testing, generalization, or independent-test claim'},previous_pilot={'path':str(OLD),'reuse':'Existing 16 predictions, scores and results reused byte-for-byte; new 48 run separately; combined totals clearly split by wave'},scope_changes=['Only sample size and task grouping change; candidate constructor, default 0.05, repair functions, budgets and prompt task definitions unchanged'],no_gold_tuning=True)
    write(ROOT/'protocol.json',protocol)
    write(ROOT/'source_freeze.json',{'created_at_utc':protocol['created_at_utc'],'old_files':frozen,'core_code_identical':{name:sha(ROOT/name)==sha(OLD/name) for name in ['graph_core.py','repair.py']},'new_blind_hashes':{p.name:sha(p) for p in (ROOT/'blind_inputs').glob('*.json')},'gold_hashes':{p.name:sha(p) for p in (ROOT/'evaluation').glob('*gold.json')}})
    print(json.dumps({'new_documents':len(rows),'cumulative_documents':len(rows)+16,'available_unique_texts':protocol['continuation']['remaining_population'],'batches':batch_manifest},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
