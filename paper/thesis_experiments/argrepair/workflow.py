"""Generate and execute a sequential 24 GB server experiment dependency plan."""
from pathlib import Path
import subprocess,sys,shlex,json
from .schema import digest

_INPUT_FLAGS={'data','inputs','adapter','views','ranked','groups','scorer','span','scores','policy','gold','predictions','comparisons','config','pools','counts','reference_budget','generations'}

def _code_hashes():
    return {p.name:file_hash(p) for p in sorted(Path(__file__).parent.glob('*.py'))}

def _snapshot(paths):
    files={}
    for value in paths:
        path=Path(value).resolve()
        if not path.exists():raise FileNotFoundError(f'Required stage input missing: {path}')
        found=sorted(p for p in path.rglob('*') if p.is_file()) if path.is_dir() else [path]
        if not found and path.is_dir():raise ValueError(f'Empty checkpoint/input directory: {path}')
        for p in found:files[str(p)]=file_hash(p)
        for parent in (path if path.is_dir() else path.parent,path.parent,path.parent.parent):
            sidecar=parent/'training_identity.json'
            if sidecar.is_file():files[str(sidecar)]=file_hash(sidecar)
    return files

from .io import read_json,write_json,read_jsonl,write_jsonl,file_hash

def make_plan(data,configuration,output,corpus='both',seeds=(17,29,43)):
    data=Path(data).resolve();configuration=Path(configuration).resolve();out=Path(output).resolve()
    if out.exists() and any(out.iterdir()):raise FileExistsError(f'Plan output must be a new empty directory: {out}')
    if corpus not in {'both','aaec','cdcp'}:raise ValueError('unknown corpus')
    if not seeds or len(set(seeds))!=len(seeds) or any(type(seed) is not int for seed in seeds):raise ValueError('seeds must be distinct integers')
    configuration_data=read_json(configuration)
    regeneration=configuration_data.get('regeneration',{})
    if regeneration.get('enabled') and not regeneration.get('reference_budget_manifest'):
        raise ValueError('enabled Regenerate requires reference_budget_manifest with actual per-document I1 receipts')
    out.mkdir(parents=True,exist_ok=True);jobs=[];corpora=['aaec','cdcp'] if corpus=='both' else [corpus]
    def add(name,command,**kwargs):
        target=out/name;argv=['-m','argrepair',command,'--config',str(configuration),'--out',str(target)]
        for key,value in kwargs.items():
            if value is None or value is False:continue
            argv+=['--'+key.replace('_','-')]
            if value is True:continue
            argv+=list(map(str,value)) if isinstance(value,(list,tuple)) else [str(value)]
        source_paths=[str(configuration)]
        for key,value in kwargs.items():
            if key in _INPUT_FLAGS and value is not None:
                source_paths.extend(map(str,value)) if isinstance(value,(list,tuple)) else source_paths.append(str(value))
        jobs.append({'id':name,'argv':argv,'output':str(target),'inputs':source_paths});return target
    counts=[]
    for c in corpora:
        augmented=add(f'{c}/augmentation','augment',data=data/f'{c}_train.jsonl')
        for seed in seeds:
            prefix=f'{c}/seed{seed}';oof_pools=[];t1_policy_pools=[]
            # Every fold excludes the source document and all accepted views.
            for fold in range(3):
                fold_data=data/f'{c}_fold{fold}_train.jsonl';fold_inputs=data/f'{c}_fold{fold}_inputs.jsonl'
                span=add(f'{prefix}/fold{fold}/span','span-train',data=fold_data,corpus=c,seed=seed)
                for variant in ('T0','T1'):
                    dest=out/f'{prefix}/fold{fold}/{variant}/filtered_views.jsonl'
                    jobs.append({'id':str(dest.relative_to(out)),'internal':'filter_views','data':str(fold_data),'views':str(augmented/'views.jsonl'),'inputs':[str(fold_data),str(augmented/'views.jsonl')],'output_file':str(dest)})
                    tr=add(f'{prefix}/fold{fold}/{variant}/train','train',data=fold_data,views=dest,variant=variant,seed=seed)
                    gen=add(f'{prefix}/fold{fold}/{variant}/generate','generate',inputs=fold_inputs,adapter=tr/'adapter/checkpoint')
                    rank=add(f'{prefix}/fold{fold}/{variant}/rank','rank',inputs=fold_inputs,generations=gen/'generations.jsonl')
                    groups=add(f'{prefix}/fold{fold}/{variant}/groups','groups',inputs=fold_inputs,ranked=rank/'ranked.jsonl',span=span/'span')
                    pools=add(f'{prefix}/fold{fold}/{variant}/pools','build-pools',inputs=fold_inputs,ranked=rank/'ranked.jsonl',groups=groups/'groups.jsonl',span=span/'span',oof=True)
                    oof_pools.append(pools/'pools.jsonl')
                    if variant=='T1':t1_policy_pools.append(pools/'pools.jsonl')
            fitted=add(f'{prefix}/scorer-fit','scorer-train',data=data/f'{c}_fit.jsonl',pools=oof_pools,corpus=c,seed=seed)
            calibrated=add(f'{prefix}/calibrate','calibrate',data=data/f'{c}_calibration.jsonl',pools=oof_pools,scorer=fitted/'scorer')
            policy_pools=out/f'{prefix}/policy_pools.jsonl'
            jobs.append({'id':f'{prefix}/policy_T1_pools','internal':'select_policy_pools','policy_generator':'T1','data':str(data/f'{c}_policy.jsonl'),'pools':list(map(str,t1_policy_pools)),'inputs':[str(data/f'{c}_policy.jsonl'),*map(str,t1_policy_pools)],'output_file':str(policy_pools)})
            scored=add(f'{prefix}/policy-score','score',pools=[policy_pools],scorer=calibrated/'scorer')
            policy=add(f'{prefix}/policy','select-policy',data=data/f'{c}_policy.jsonl',scores=scored/'scored.jsonl')
            span=add(f'{prefix}/final-span','span-train',data=data/f'{c}_train.jsonl',corpus=c,seed=seed)
            for variant in ('T0','Heads','NoPair','CompPair','T1'):
                tr=add(f'{prefix}/{variant}/train','train',data=data/f'{c}_train.jsonl',views=augmented/'views.jsonl',variant=variant,seed=seed)
                gen=add(f'{prefix}/{variant}/generate','generate',inputs=data/f'{c}_test_inputs.jsonl',adapter=tr/'adapter/checkpoint')
                rank=add(f'{prefix}/{variant}/rank','rank',inputs=data/f'{c}_test_inputs.jsonl',generations=gen/'generations.jsonl',with_i0=True)
                ev=add(f'{prefix}/{variant}/I0-eval','evaluate',gold=data/f'{c}_test.jsonl',predictions=rank/'i0_predictions.jsonl',method=variant+'I0',seed=seed);counts.append(ev/'counts.jsonl')
                if variant not in ('T0','T1'):continue
                groups=add(f'{prefix}/{variant}/groups','groups',inputs=data/f'{c}_test_inputs.jsonl',ranked=rank/'ranked.jsonl',span=span/'span')
                pools=add(f'{prefix}/{variant}/pools','build-pools',inputs=data/f'{c}_test_inputs.jsonl',ranked=rank/'ranked.jsonl',groups=groups/'groups.jsonl',span=span/'span',scorer=calibrated/'scorer')
                scored=add(f'{prefix}/{variant}/score','score',pools=[pools/'pools.jsonl'],scorer=calibrated/'scorer')
                for method in (('I1',) if variant=='T0' else ('I1','RelationOnly','Sequential','Single','SetLocal','Global','NoRisk')):
                    repaired=add(f'{prefix}/{variant}/{method}','repair',scores=scored/'scored.jsonl',policy=policy/'policy.json',method=method)
                    name=variant+'I1' if method=='I1' else method
                    ev=add(f'{prefix}/{variant}/{method}-eval','evaluate',gold=data/f'{c}_test.jsonl',predictions=repaired/'predictions.jsonl',method=name,seed=seed);counts.append(ev/'counts.jsonl')
                    analysis=out/f'{prefix}/{variant}/{method}-analysis'
                    analysis_inputs=[str(data/f'{c}_test.jsonl'),str(scored/'scored.jsonl'),str(repaired/'predictions.jsonl')]
                    jobs.append({'id':f'{prefix}/{variant}/{method}-analysis','argv':['-m','argrepair.analysis',
                                 '--gold',analysis_inputs[0],'--scores',analysis_inputs[1],'--predictions',analysis_inputs[2],
                                 '--method',name,'--seed',str(seed),'--out',str(analysis)],'output':str(analysis),'inputs':analysis_inputs})
                if variant=='T1' and regeneration.get('enabled'):
                    reference=Path(str(regeneration['reference_budget_manifest']).format(corpus=c,seed=seed,output=str(out)))
                    if not reference.is_absolute():reference=configuration.parent/reference
                    target=out/f'{prefix}/T1/Regenerate'
                    source_paths=[str(configuration),str(data/f'{c}_test_inputs.jsonl'),str(rank/'ranked.jsonl'),str(tr/'adapter/checkpoint'),str(reference)]
                    argv=['-m','argrepair.regeneration','--config',str(configuration),'--out',str(target),
                          '--inputs',source_paths[1],'--ranked',source_paths[2],'--adapter',source_paths[3],'--reference-budget',str(reference),'--seed',str(seed)]
                    jobs.append({'id':f'{prefix}/T1/Regenerate','argv':argv,'output':str(target),'inputs':source_paths})
                    verified=out/f'{prefix}/T1/Regenerate-verified/predictions.jsonl'
                    jobs.append({'id':f'{prefix}/T1/verify-regeneration','internal':'verify_regeneration',
                                 'predictions':str(target/'predictions.jsonl'),'inputs':[str(target/'predictions.jsonl')],'output_file':str(verified)})
                    ev=add(f'{prefix}/T1/Regenerate-eval','evaluate',gold=data/f'{c}_test.jsonl',predictions=verified,method='Regenerate',seed=seed)
                    counts.append(ev/'counts.jsonl')
    comparisons=[{'a':'T1I0','b':'T0I0','role':'primary'},{'a':'T1I0','b':'NoPairI0','role':'primary'},{'a':'T1I1','b':'T1I0','role':'primary'},
                 {'a':'T1I1','b':'RelationOnly','role':'primary'},{'a':'Single','b':'Sequential','role':'primary'},{'a':'T1I1','b':'NoRisk','role':'primary'},
                 {'a':'T0I1','b':'T0I0','role':'exploratory'},{'a':'SetLocal','b':'Single','role':'exploratory'}]
    if regeneration.get('enabled'):comparisons.append({'a':'T1I1','b':'Regenerate','role':'primary'})
    write_json(out/'comparisons.json',comparisons)
    add('statistics','bootstrap',counts=counts,comparisons=out/'comparisons.json')
    plan={'version':2,'configuration_path':str(configuration),'configuration_sha256':file_hash(configuration),'data_split_path':str(data/'split_manifest.json'),'data_split_sha256':file_hash(data/'split_manifest.json'),'data_hashes':_snapshot(sorted(data.glob('*.jsonl'))),'code':_code_hashes(),'jobs':jobs,
          'policy_protocol':'One T1 OOF pool per held-out policy source; freeze once and share the selected policy across T0 and T1. Fitting/calibration may use declared T0/T1 families separately.','primary_comparisons_per_corpus':7 if regeneration.get('enabled') else 6,'regeneration_enabled':bool(regeneration.get('enabled')),'note':'New executable protocol. NoRisk is included. Optional Regenerate has a mandatory verified matching-budget gate before evaluation and statistics; historical simulated counts are never reused.'}
    write_json(out/'plan.json',plan)
    (out/'commands.sh').write_text('#!/usr/bin/env bash\nset -euo pipefail\n# Prefer python -m argrepair run-plan --plan plan.json for internal preparation steps.\n'+ '\n'.join('# '+j['id']+'\n'+shlex.join(['python',*j['argv']]) if 'argv' in j else '# internal: '+j['id'] for j in jobs)+'\n')
    return str(out/'plan.json')

def _policy_rows(job):
    """Select exactly one T1 OOF pool per policy document; never family-union it."""
    from dataclasses import replace
    from .io import load_documents,load_pool,save_pool
    if job.get('policy_generator')!='T1':raise ValueError('policy generator must be preregistered T1')
    docs={d.doc_id:d for d in load_documents(job['data'])}
    if any(d.split!='policy' for d in docs.values()):raise ValueError('policy split required')
    selected={}
    for file in job['pools']:
        for row in read_jsonl(file):
            ident=row['doc_id']
            if ident not in docs:continue
            if ident in selected:raise ValueError('multiple policy pools for one source; T0/T1 union forbidden')
            d=docs[ident]
            provenance=(load_pool(row['pool']).metadata if row['status']=='ok' else row.get('metadata',{})).get('oof',{})
            if (provenance.get('held_out_source_group')!=d.source_group or not provenance.get('trained_source_groups')
                or d.source_group in provenance['trained_source_groups']):raise ValueError('invalid policy OOF isolation')
            output=dict(row)
            if row['status']=='ok':
                pool=load_pool(row['pool'])
                if pool.doc!=d.input:raise ValueError('policy source identity differs')
                pool=replace(pool,metadata={**pool.metadata,'policy_generator':'T1','policy_scope':'single_T1_oof_pool_no_family_union','policy_source_file':str(file)})
                output['pool']=save_pool(pool)
            selected[ident]=output
    if set(selected)!=set(docs):raise ValueError('policy inputs incomplete; retain failed documents explicitly')
    return [selected[k] for k in sorted(selected)]


def _outputs(job):
    if 'internal' in job:return _snapshot([job['output_file']])
    root=Path(job['output'])
    return {str(p.resolve()):file_hash(p) for p in sorted(root.rglob('*')) if p.is_file()}


def run_plan(path,resume=False,timeout=172800):
    """Resume only matching completed checkpoints; never overwrite failed work."""
    path=Path(path).resolve();plan=read_json(path);completed=[]
    if plan.get('version')!=2:raise ValueError('legacy plan lacks resume provenance; generate a fresh plan')
    if file_hash(plan['configuration_path'])!=plan['configuration_sha256']:raise ValueError('plan configuration drift')
    if file_hash(plan['data_split_path'])!=plan['data_split_sha256']:raise ValueError('plan split drift')
    for file,sha in plan['data_hashes'].items():
        if file_hash(file)!=sha:raise ValueError('plan source data drift: '+file)
    if _code_hashes()!=plan['code']:raise ValueError('plan code drift; create a new versioned plan')
    plan_sha=file_hash(path);state_dir=path.parent/'.job_state';state_dir.mkdir(exist_ok=True)
    for job in plan['jobs']:
        state_path=state_dir/(digest(job['id'])+'.json')
        inputs=_snapshot(job['inputs']);signature={'plan_sha256':plan_sha,'job':job,'inputs':inputs,'code':_code_hashes(),
                                                  'configuration_sha256':file_hash(plan['configuration_path'])}
        if state_path.exists():
            state=read_json(state_path)
            if not resume:raise FileExistsError('Stage already exists; use --resume only for verified completion: '+job['id'])
            if state.get('status')!='completed':raise FileExistsError('Failed or interrupted stage is preserved; choose a new plan directory: '+job['id'])
            if state.get('signature')!=signature:raise ValueError('completed stage inputs/config/code/plan drift: '+job['id'])
            if state.get('outputs')!=_outputs(job):raise ValueError('completed stage output drift: '+job['id'])
            completed.append(job['id']);continue
        target=Path(job['output_file'] if 'internal' in job else job['output'])
        if target.exists():raise FileExistsError('Unverified or failed stage output will not be overwritten: '+str(target))
        write_json(state_path,{'status':'running','signature':signature})
        try:
            if 'internal' in job:
                if job['internal']=='filter_views':
                    ids={d['doc_id'] for d in read_jsonl(job['data'])}
                    rows=[v for v in read_jsonl(job['views']) if v['source_doc_id'] in ids]
                elif job['internal']=='select_policy_pools':rows=_policy_rows(job)
                elif job['internal']=='verify_regeneration':
                    from .regeneration import verify_matched_predictions
                    rows=read_jsonl(job['predictions']);verify_matched_predictions(rows)
                else:raise ValueError('unknown internal stage')
                write_jsonl(target,rows)
            else:
                print('RUN',job['id'],flush=True)
                subprocess.run([sys.executable,*job['argv']],check=True,timeout=timeout)
                manifest=target/'manifest.json'
                if not manifest.exists() or read_json(manifest).get('status')!='completed':
                    raise ValueError('command returned without a completed manifest: '+job['id'])
                saved=read_json(manifest)
                for name,sha in saved.get('outputs',{}).items():
                    if file_hash(target/name)!=sha:raise ValueError('command output manifest mismatch')
            write_json(state_path,{'status':'completed','signature':signature,'outputs':_outputs(job)})
        except BaseException as exc:
            write_json(state_path,{'status':'failed','signature':signature,'error':type(exc).__name__+': '+str(exc)})
            raise
        completed.append(job['id'])
        write_json(path.with_name('progress.json'),{'completed':completed,'total':len(plan['jobs']),'plan_sha256':plan_sha})
    return completed
