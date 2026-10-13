"""Exact native whole-object metrics; inference never imports this module."""
from collections import Counter,defaultdict
from .schema import Graph,graph_errors,digest

def counts(pred,gold):
    p,g=set(pred),set(gold);return {'tp':len(p&g),'fp':len(p-g),'fn':len(g-p)}
def metrics(c):
    t,p,n=(c[k] for k in ('tp','fp','fn'))
    return {**c,'n_pred':t+p,'n_gold':t+n,'precision':100*t/(t+p) if t+p else 0.,'recall':100*t/(t+n) if t+n else 0.,'f1':200*t/(2*t+p+n) if 2*t+p+n else 0.}
def evaluate(documents,predictions,method,seed,require_input_hash=False):
    if not documents:raise ValueError('empty evaluation set')
    if method=='Regenerate':
        from .regeneration import verify_matched_predictions
        verify_matched_predictions(predictions)
    ids=[d.doc_id for d in documents];pids=[p['doc_id'] for p in predictions]
    if len(set(ids))!=len(ids) or len(set(pids))!=len(pids) or set(ids)!=set(pids):raise ValueError('prediction ids must match exactly; failures need explicit rows')
    pred={p['doc_id']:p for p in predictions};rows=[];failures=Counter()
    for d in documents:
        p=pred[d.doc_id];status=p.get('status','ok')
        if require_input_hash and not p.get('input_sha256'):raise ValueError('formal evaluation requires prediction input identity')
        if p.get('input_sha256') and p['input_sha256']!=digest(d.input.to_dict()):raise ValueError('prediction input identity differs')
        if status not in ('ok','optimal','feasible','no_change','policy_no_repair'):
            graph=Graph();failures[status]+=1
        else:
            try:
                graph=Graph.from_dict(p['graph'])
                if graph_errors(d.input,graph):raise ValueError('invalid native graph')
            except (ValueError,KeyError,TypeError):
                graph=Graph();status='invalid_graph';failures[status]+=1
        for family,pc,gc in [('component',graph.components,d.gold.components),('relation',graph.relations,d.gold.relations)]:
            rows.append({'corpus':d.corpus,'doc_id':d.doc_id,'source_group':d.source_group,'seed':seed,'method':method,'family':family,'status':status,
                         **({'matched_budget_verified':True} if method=='Regenerate' else {}),**metrics(counts(pc,gc))})
    summaries={}
    for corpus in sorted({d.corpus for d in documents}):
        summaries[corpus]={}
        for family in ('component','relation'):
            subset=[r for r in rows if r['corpus']==corpus and r['family']==family]
            summaries[corpus][family]=metrics({k:sum(r[k] for r in subset) for k in ('tp','fp','fn')})
    return {'method':method,'seed':seed,'documents':len(documents),'failures':dict(failures),'protocol':'native_char_complete_source_set_strict_micro; canonical_dedup_all_methods; zero_denominator=0','metrics':summaries},rows

def paired_bootstrap(rows,comparisons,repetitions=2000,seed=20261012):
    """Shared seed/group draws across every predeclared contrast; centered p + Holm."""
    import numpy as np
    if type(repetitions) is not int or repetitions<2:raise ValueError('at least 2 integer replicates')
    if not rows or not comparisons:raise ValueError('nonempty counts and comparisons required')
    if type(seed) is not int:raise ValueError('integer bootstrap seed required')
    contrast_keys=[(c['a'],c['b']) for c in comparisons]
    if len(set(contrast_keys))!=len(contrast_keys) or any(a==b for a,b in contrast_keys):raise ValueError('duplicate or self comparison')
    if any(c.get('role','exploratory') not in ('primary','exploratory') for c in comparisons):raise ValueError('unknown comparison role')
    for r in rows:
        if any(type(r.get(k)) is not int or r[k]<0 for k in ('tp','fp','fn')):raise ValueError('counts must be nonnegative integers')
        if type(r.get('seed')) is not int:raise ValueError('integer experiment seed required')
        if ('n_pred' in r and r['n_pred']!=r['tp']+r['fp']) or ('n_gold' in r and r['n_gold']!=r['tp']+r['fn']):raise ValueError('count denominator mismatch')
    if any(r['method']=='Regenerate' and r.get('matched_budget_verified') is not True for r in rows):raise ValueError('Regenerate counts lack verified matching budget')
    rng=np.random.default_rng(seed);outputs=[];draws={}
    for corpus in sorted({x['corpus'] for x in rows}):
        rr=[x for x in rows if x['corpus']==corpus and x['family']=='relation']
        seeds=sorted({r['seed'] for r in rr});groups=sorted({r['source_group'] or r['doc_id'] for r in rr})
        methods=sorted({r['method'] for r in rr});idx={};membership={}
        for r in rr:
            key=(r['method'],r['seed'],r['doc_id'])
            if key in idx:raise ValueError('duplicate count key')
            idx[key]=r
        reference=None
        for m in methods:
            for s in seeds:
                current={r['doc_id']:(r['source_group'],r['tp']+r['fn']) for r in rr if r['method']==m and r['seed']==s}
                if reference is None:reference=current
                if current!=reference:raise ValueError('unpaired documents/groups/gold denominators')
        tensor=np.zeros((len(methods),len(seeds),len(groups),3),dtype=np.int64)
        for r in rr:tensor[methods.index(r['method']),seeds.index(r['seed']),groups.index(r['source_group'] or r['doc_id'])]+= [r['tp'],r['fp'],r['fn']]
        def f1(a):
            den=2*a[...,0]+a[...,1]+a[...,2]
            return np.divide(200*a[...,0],den,out=np.zeros_like(den,dtype=float),where=den>0)
        observed=f1(tensor.sum(axis=2));sd=rng.integers(len(seeds),size=(repetitions,len(seeds)));gd=rng.integers(len(groups),size=(repetitions,len(groups)))
        boot=np.stack([f1(tensor[:,ss][:,:,gg].sum(axis=2)).mean(axis=1) for ss,gg in zip(sd,gd)])
        fixed=np.stack([f1(tensor[:,:,gg].sum(axis=2)).mean(axis=1) for gg in gd])
        draws[corpus]={'seeds':seeds,'groups':groups,'seed_indices':sd.tolist(),'group_indices':gd.tolist()}
        for contrast in comparisons:
            a,b=contrast['a'],contrast['b']
            if a not in methods or b not in methods:raise ValueError(f'missing preregistered contrast {a}-{b}')
            ai,bi=methods.index(a),methods.index(b);obs=float((observed[ai]-observed[bi]).mean());delta=boot[:,ai]-boot[:,bi]
            p=float((1+np.sum(np.abs(delta-obs)>=abs(obs)))/(repetitions+1))
            outputs.append({'corpus':corpus,'a':a,'b':b,'role':contrast.get('role','exploratory'),'difference_pp':obs,'per_seed_pp':(observed[ai]-observed[bi]).tolist(),'ci95':np.quantile(delta,[.025,.975]).tolist(),'fixed_seed_ci95':np.quantile(fixed[:,ai]-fixed[:,bi],[.025,.975]).tolist(),'p':p})
    family=[i for i,r in enumerate(outputs) if r['role']=='primary'];order=sorted(family,key=lambda i:outputs[i]['p']);last=0.
    for rank,i in enumerate(order):
        last=max(last,min(1.,(len(order)-rank)*outputs[i]['p']));outputs[i]['holm_p']=last
    return {'seed':seed,'repetitions':repetitions,'primary_family_size':len(family),'contrasts':outputs,'draws':draws}
