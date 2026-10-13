"""Materialize the next preregistered CDCP search wave; no outcome-driven sampling."""
from pathlib import Path
from datetime import datetime,timezone
import json,sys,hashlib,shutil
import prepare

BASE=Path(__file__).resolve().parent;WORK=BASE.parent
read=lambda p:json.loads(p.read_text())
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
write=prepare.write

def main(wave):
    assert 2<=wave<=8
    target=WORK/f'research_1011_luna_expanded_w{wave:02d}';target.mkdir(exist_ok=False)
    for sub in ['blind_inputs','raw_predictions','evaluation','scores','scoring_inputs','prompts','results','logs']:(target/sub).mkdir()
    manifest=read(BASE/'sample_manifest.json');plan=manifest['full_preordered_extension_plan']['cdcp']
    lo=8+4*(wave-2);hi=lo+4
    ids={ident for part in plan for ident in part[lo:hi]};assert ids
    docs,prov=prepare.legacy.load_data('cdcp');dm={'cdcp_'+d.ident:d for d in docs}
    rows=[];blind=[];gold=[]
    for ident in sorted(ids):
        d=dm[ident];si=next(i for i,part in enumerate(plan) if ident in part);rank=plan[si].index(ident)+1
        assert lo<rank<=hi
        blind.append({'id':ident,'corpus':'cdcp','text':d.text});gold.append(prepare.raw_gold(d,'cdcp'))
        rows.append({'id':ident,'source_doc_id':d.ident,'corpus':'cdcp','text_sha256':hashlib.sha256(d.text.encode()).hexdigest(),'length_stratum':si,'within_stratum_hash_rank':rank,'tokens':len(d.tokens),'chars':len(d.text),'wave':wave})
    batches=[]
    for k,start in enumerate(range(0,len(blind),8),1):
        name=f'cdcp_{k:02d}';part=blind[start:start+8]
        write(target/'blind_inputs'/f'{name}.json',{'documents':part})
        batches.append({'task':f'expand_w{wave:02d}_predict_{name}','corpus':'cdcp','input':f'blind_inputs/{name}.json','output':f'raw_predictions/{name}.json','documents':[d['id'] for d in part]})
    write(target/'blind_inputs/cdcp.json',{'documents':blind})
    write(target/'evaluation/cdcp_gold.json',{'documents':gold});write(target/'evaluation/cdcp_provenance.json',prov)
    previous=[WORK/'research_1010_v7_luna',BASE]+[WORK/f'research_1011_luna_expanded_w{i:02d}' for i in range(2,wave)]
    evidence=[]
    for root in previous:
        m=read(root/'results/evaluation_001/metrics.json')
        rr=[d for d in m['documents'] if d['corpus']=='cdcp']
        assert not any(d['relation_outcome']=='improvement' for d in rr),'CDCP already improved; extension forbidden by stop rule'
        evidence.append({'root':root.name,'evaluated_cdcp':len(rr),'metrics_sha256':sha(root/'results/evaluation_001/metrics.json'),'improvement_documents':[]})
    priorids={d['id'] for root in previous for d in read(root/'sample_manifest.json')['selected'] if d['corpus']=='cdcp'}
    assert not ids&priorids
    total=len(priorids|ids)
    write(target/'extension_decision.json',{'decided_at_utc':datetime.now(timezone.utc).isoformat(),'rule':read(BASE/'protocol.json')['continuation'],'prior_waves':evidence,'new_ids':sorted(ids),'cumulative_cdcp':total,'aaec_stops_at':32,'adaptation':'Outcome determines whether to run next frozen block, never which documents or scores enter it'})
    for name in ['graph_core.py','repair.py','test_repair.py','replay.py','evaluate.py','pipeline.py']:
        shutil.copyfile(BASE/name,target/name)
    p=target/'test_repair.py';p.write_text(p.read_text().replace('self.assertEqual(len(docs),48)',f'self.assertEqual(len(docs),{len(rows)})'))
    p=target/'evaluate.py';s=p.read_text().replace("['aaec','cdcp']","sorted({d['corpus'] for d in docs})").replace('AM-LUNA-20261011-EXPAND-001',f'AM-LUNA-20261011-EXPAND-{wave:03d}');p.write_text(s)
    p=target/'pipeline.py';s=p.read_text().replace('len(raws)==len(blind)==8','len(raws)==len(blind) and 1<=len(blind)<=8').replace("assert len(docs)==48 and len({d['id'] for d in docs})==48","assert len(docs)==len(manifest['selected']) and len({d['id'] for d in docs})==len(docs)").replace("for corpus in ['aaec','cdcp']:","for corpus in sorted({d['corpus'] for d in docs}):");p.write_text(s)
    for name in ['prediction_cdcp.txt','scoring_instructions.md']:
        shutil.copyfile(BASE/'prompts'/name,target/'prompts'/name)
    write(target/'scoring_protocol.json',read(BASE/'scoring_protocol.json'))
    write(target/'sample_manifest.json',{'selection':manifest['selection'],'selection_seed_label':manifest['selection_seed_label'],'selected':rows,'full_preordered_extension_plan':manifest['full_preordered_extension_plan'],'prediction_batches':batches,'wave':wave})
    protocol=read(BASE/'protocol.json');protocol.update(experiment_id=f'AM-LUNA-20261011-EXPAND-{wave:03d}',created_at_utc=datetime.now(timezone.utc).isoformat(),generation={**protocol['generation'],'new_documents_per_corpus':{'cdcp':len(rows)},'cumulative_documents_per_corpus':{'aaec':32,'cdcp':total}},wave=wave)
    write(target/'protocol.json',protocol)
    write(target/'source_freeze.json',{'created_at_utc':protocol['created_at_utc'],'old_files':{str(p.relative_to(WORK)):sha(p) for root in previous for p in root.rglob('*') if p.is_file() and '__pycache__' not in p.parts},'core_code_identical':{name:sha(target/name)==sha(BASE/name) for name in ['graph_core.py','repair.py']},'new_blind_hashes':{p.name:sha(p) for p in (target/'blind_inputs').glob('*.json')},'gold_hashes':{p.name:sha(p) for p in (target/'evaluation').glob('*gold.json')}})
    print(json.dumps({'root':str(target),'new_cdcp':len(rows),'cumulative_cdcp':total,'batches':batches},ensure_ascii=False,indent=2))

if __name__=='__main__':main(int(sys.argv[1]))
