"""Validate human-facing artifacts, derived claims, and preserved real outputs."""
from pathlib import Path
from collections import Counter
import json,re,hashlib
ROOT=Path(__file__).resolve().parent;WORK=ROOT.parent
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    docs=read(ROOT/'candidate_pools.json')['documents'];changes={d['id']:d for d in read(ROOT/'results/evaluation_001/object_changes.json')}
    freeze=read(ROOT/'results/run_001/input_freeze.json');out=read(ROOT/'results/run_001/output_freeze.json')
    for p,h in freeze['hashes'].items():assert sha(ROOT/p)==h,p
    for p,h in out['hashes'].items():assert sha(ROOT/'results/run_001'/p)==h,p
    assert sha(WORK/'report_1010_v7_full.md')=='cab53d7b66a4ce2ef6e8d5ebecfb5152034ae98824cbb23d2ea1de7862485869'
    assert sha(WORK/'report_1010_v7_full.docx')=='168531e234421afcf7f09f2f4c07a1e5cba0ee042435f43d643e142a8fc7cb99'
    origins=Counter();scored=0;nc=nr=0;selected=[];shapes=Counter();calls=Counter();ties=Counter()
    for d in docs:
        score=read(ROOT/'scores'/f"{d['id']}.json");nc+=len(d['components']);nr+=len(d['relations']);scored+=len(score['relation_score_overrides'])
        recovered={tuple(c) for c in changes[d['id']]['BRJ-lite']['C']['TP_recovered']}
        for c in d['components'].values():
            if (c['start'],c['end'],c['type']) in recovered:origins[d['corpus']+':'+c['origin']]+=1
        br=read(ROOT/'results/run_001'/f"{d['id']}__BRJ-lite.json");selected.append(br['initial_candidate'])
        shapes.update(a['proposal']['kind'] for a in br['attempts'] if a['committed'])
        for mode in ['BRJ-lite','RelationOnly']:
            r=read(ROOT/'results/run_001'/f"{d['id']}__{mode}.json")
            calls.update((a['stage'],a['status']) for a in r['solver_calls']);ties.update(a.get('tie_status') for a in r['attempts'] if a['committed'])
    assert nc==210 and nr==5404 and scored==149
    assert origins=={'aaec:terminal_punctuation_boundary_variant':28,'aaec:generated':2}
    assert selected==['g0']*16 and shapes['split']==1 and shapes['merge']==0
    assert ties=={'unique_optimum_and_min_edits':139}
    assert calls[('maximize_phi',2)]==858 and calls[('test_uniqueness',2)]==258
    score=read(ROOT/'scores/cdcp_01057.json');assert 'r0063' not in score['relation_score_overrides'] and score['default_relation_score']==.05
    negative=read(ROOT/'results/run_001/cdcp_01057__BRJ-lite.json')['attempts'][0]
    assert negative['committed'] and negative['delta_phi_C']==0 and abs(negative['delta_phi_R']-.9)<1e-8
    mainreport=WORK/'1011_v7_Luna真实预测与联合修正尝试记录.md';casebook=WORK/'1011_v7_Luna逐例标注与修正轨迹.md'
    assert re.findall(r'^## ((?:aaec|cdcp)_\w+)$',casebook.read_text(),re.M)==[d['id'] for d in docs]
    links=[]
    for p in [mainreport,casebook]:
        t=p.read_text();assert '\ufffd' not in t
        for target in re.findall(r'\]\((/[^)]+)\)',t):
            assert Path(target).exists(),target;links.append(target)
        expected=None
        for line in t.splitlines():
            if line.startswith('|') and line.endswith('|'):
                count=len(re.split(r'(?<!\\)\|',line))-2
                if expected is None:expected=count
                assert count==expected,(p,line)
            else:expected=None
    result={'status':'PASS','all_original_inputs_outputs_preserved':True,'paper_v7_unchanged':True,'all_16_cases_present':True,
            'local_links_verified':len(links),'candidate_components':nc,'candidate_relations':nr,'scored_relation_overrides':scored,
            'recovered_component_origin_counts':dict(origins),'brj_committed_shapes':dict(shapes),'committed_tie_proof_counts':dict(ties),
            'solver_status_by_stage':[{ 'stage':k[0],'status':k[1],'count':v} for k,v in sorted(calls.items())],
            'human_report_sha256':sha(mainreport),'casebook_sha256':sha(casebook)}
    dest=ROOT/'delivery_audit.json';assert not dest.exists();dest.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n');print(json.dumps(result,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
