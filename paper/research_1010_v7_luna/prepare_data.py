#!/usr/bin/env python3
"""Freeze real texts for a small, gold-blind Luna prediction experiment."""
from pathlib import Path
import sys, importlib.util, hashlib, json, zipfile
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent
WORK = ROOT.parent
OLD = WORK / 'research_0920'
sys.path.insert(0, str(OLD / 'vendor'))
spec = importlib.util.spec_from_file_location('legacy_data_reader', OLD / 'run_feasibility.py')
legacy = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = legacy
spec.loader.exec_module(legacy)

def digest(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()

def write(p, obj):
    p.parent.mkdir(parents=True, exist_ok=True)
    if p.exists():
        raise FileExistsError(p)
    p.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n')

def main():
    if (ROOT/'protocol.json').exists():
        raise RuntimeError('Frozen preparation already exists; do not overwrite it.')
    now = datetime.now(timezone.utc).isoformat()
    for sub in ('blind_inputs','raw_predictions','evaluation','logs','scripts','scores','results'):
        (ROOT/sub).mkdir(parents=True,exist_ok=True)
    source_files=['data/aaec_brat.zip','data/aaec_split.csv','data/cdcp_acl17.zip']
    sources=[]
    for f in source_files:
        p=OLD/f
        if p.suffix=='.zip':
            with zipfile.ZipFile(p) as z:
                if z.testzip() is not None: raise ValueError('corrupt archive '+str(p))
        sources.append({'path':str(p),'sha256':digest(p),'bytes':p.stat().st_size})
    selected=[]
    for corpus in ('aaec','cdcp'):
        docs, provenance=legacy.load_data(corpus)
        previous=json.loads((OLD/f'results/{corpus}_data_manifest.json').read_text())
        assert provenance['archive_sha256']==previous['archive_sha256']
        # Same official-training-only audit partition as the earlier CPU pilot.
        # Fixed text-hash grouping prevents duplicate text crossing partitions.
        _,_,audit=legacy.split_docs(docs)
        unique={hashlib.sha256(d.text.encode()).hexdigest():d for d in audit}
        ordered=sorted(unique.values(),key=lambda d:(len(d.tokens),d.ident))
        strata=[ordered[len(ordered)*i//4:len(ordered)*(i+1)//4] for i in range(4)]
        chosen=[]
        for si,part in enumerate(strata):
            rank=sorted(part,key=lambda d:hashlib.sha256(('LUNA-V7-1010|'+corpus+'|'+d.text).encode()).hexdigest())
            chosen.extend((d,si) for d in rank[:2])
        chosen.sort(key=lambda x:x[0].ident)
        blind=[]; gold=[]
        for d,stratum in chosen:
            tid=corpus+'_'+d.ident
            h=hashlib.sha256(d.text.encode()).hexdigest()
            blind.append({'id':tid,'corpus':corpus,'text':d.text})
            comps=[]
            for s,e,t in d.gold:
                if s>=0:
                    cs,ce=d.offsets[s][0],d.offsets[e-1][1]
                else: cs=ce=None
                comps.append({'token_start':s,'token_end':e,'char_start':cs,'char_end':ce,'type':t})
            gold.append({'id':tid,'corpus':corpus,'source_doc_id':d.ident,'text':d.text,
                         'text_sha256':h,'tokens':d.tokens,'offsets':d.offsets,
                         'components':comps,'relations':[{'sources':list(s),'target':t,'type':l} for s,t,l in d.edges],
                         'issues':d.issues})
            selected.append({'id':tid,'source_doc_id':d.ident,'corpus':corpus,'text_sha256':h,
                             'length_stratum':stratum,'tokens':len(d.tokens),'chars':len(d.text)})
        write(ROOT/'blind_inputs'/f'{corpus}.json',{'documents':blind})
        write(ROOT/'evaluation'/f'{corpus}_gold.json',{'documents':gold})
        write(ROOT/'evaluation'/f'{corpus}_provenance.json',provenance)
    write(ROOT/'sample_manifest.json',{'selection':'2 per token-length quartile, stable SHA256 rank; official train audit partition; no selection by prediction or correction outcome',
          'selection_seed_label':'LUNA-V7-1010','previous_partition_seed':920,'selected':selected})
    write(ROOT/'protocol.json',{
        'experiment_id':'AM-LUNA-20261010-001','created_at_utc':now,
        'purpose':'Real-text qualitative pilot of dependency-closed graph correction; not a full thesis replication or benchmark claim',
        'manuscript':{'path':str(WORK/'report_1010_v7_full.md'),'sha256':digest(WORK/'report_1010_v7_full.md')},
        'model_requested':'gpt-5.6-luna','reasoning_effort':'low','model_snapshot':'not exposed by agent tool',
        'model_sampling_seed':'not exposed by agent tool','temperature':'not exposed by agent tool',
        'generation':{'documents_per_corpus':8,'candidate_graphs_per_document':2,'candidate_independence':'same response; not independent draws'},
        'gold_blinding':'prediction and scoring agents receive only declared blind inputs; gold used only by local evaluator after scores and outputs freeze',
        'data_sources':sources,
        'source_urls':{
            'aaec_original_metadata':'https://tudatalib.ulb.tu-darmstadt.de/handle/tudatalib/2422',
            'aaec_archive_mirror':'https://github.com/ArneBinder/pie-datasets/raw/83fb46f904b13f335b6da3cce2fc7004d802ce4e/data/datasets/ArgumentAnnotatedEssays-2.0/brat-project-final.zip',
            'aaec_split_mirror':'https://raw.githubusercontent.com/ArneBinder/pie-datasets/83fb46f904b13f335b6da3cce2fc7004d802ce4e/data/datasets/ArgumentAnnotatedEssays-2.0/train-test-split.csv',
            'cdcp_author_archive':'https://facultystaff.richmond.edu/~jpark/data/cdcp_acl17.zip'},
        'source_refresh':'Original metadata returned 403; web reader recognized CDCP zip but cannot read zip; shell DNS blocked and escalated GitHub API returned HTTP403. Existing archives match saved provenance hashes; original AAEC versus mirror byte equality remains unverified.',
        'official_test_used':False,'no_gold_perturbation':True,
        'evaluation':'exact original character-span and type components; complete typed source-set, target and label relations; all 16 selected documents remain in denominator',
        'candidate_protocol':'finite union of 2 Luna graph outputs; supplemental labels/slots specified and frozen before scoring; deviations from exhaustive thesis universe will be enumerated',
        'scoring_protocol':'separate gold-blind Luna scoring call; fixed per-object confidence as a heuristic proxy, not calibrated probability and not the trained MLP scorer from thesis',
        'repair_core':{'solver':'scipy.optimize.milp / bundled HiGHS','kappa_C':1.0,'kappa_R':1.0,'w_C':1.0,'w_R':1.0,'delta':0.01,
                       'component_edits_per_transaction':3,'component_edits_total':24,'relation_edits_total':96,
                       'attempts_per_round':32,'accepts_per_round':3,'rounds':4,'batch':6,
                       'preserve_untouched_relations':True,'allow_empty_graph':True,'acyclic_constraint':False},
        'report_all_outcomes':True,'case_selection':'fixed rule after full evaluation: first doc ID of improvement, harm, unchanged; enumerate unavailable categories',
        'not_executed_in_this_pilot':['training-side augmentation','paired loss training','trained independent neural object scorer','full same-budget global comparison','four-cell trained-model comparison','formal test-set benchmark']})
    write(ROOT/'preparation_audit.json',{'status':'PASS','created_at_utc':now,'data_archives_hash_match_previous':True,
         'zip_crc_pass':True,'documents':len(selected),'code_sha256':digest(Path(__file__)),
         'blind_input_sha256':{p.name:digest(p) for p in sorted((ROOT/'blind_inputs').glob('*.json'))},
         'gold_sha256':{p.name:digest(p) for p in sorted((ROOT/'evaluation').glob('*gold.json'))}})
    print(json.dumps({'status':'PREPARED','documents':selected},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
