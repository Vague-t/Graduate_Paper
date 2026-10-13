from pathlib import Path
import json, math, statistics

W = Path(__file__).resolve().parent
blocks = {b['id']: b for b in json.loads((W/'source_blocks.json').read_text())}
rows = lambda key: blocks[key]['rows'][1:]
results = []

def check(name, condition, details):
    results.append({'check': name, 'status': 'passed' if condition else 'needs_attention', 'details': details})

def f1(tp, fp, fn):
    return 200*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0

def wilson(k,n):
    z=1.959963984540054;p=k/n;den=1+z*z/n
    mid=(p+z*z/(2*n))/den
    half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/den
    return [100*(mid-half),100*(mid+half)]

by_method={}
for row in rows('B1034'):
    corpus,method,seed,*values=row
    tp,fp,fn=map(int,values[:3]);reported=float(values[3]);actual=f1(tp,fp,fn)
    check(f'H-5 {corpus} {method} {seed}',abs(actual-reported)<=.0051, {'counts':[tp,fp,fn],'F1':actual,'reported':reported})
    by_method.setdefault((corpus,method),[]).append({'seed':int(seed),'tp':tp,'fp':fp,'fn':fn,'f1':actual})

means={k:statistics.mean(x['f1'] for x in v) for k,v in by_method.items()}
sds={k:statistics.stdev(x['f1'] for x in v) for k,v in by_method.items()}
for row in rows('B0693'):
    for corpus,col in [('AAEC',2),('CDCP',4)]:
        mean,sd=map(float,row[col].split('±'))
        key=(corpus,row[0])
        check(f'5-2 {corpus} {row[0]} mean SD',abs(means[key]-mean)<=.0051 and abs(sds[key]-sd)<=.0051, {'mean':means[key],'SD':sds[key]})

derived={}
for corpus in ['AAEC','CDCP']:
    m={k[1]:v for k,v in means.items() if k[0]==corpus}
    derived[corpus]={'training':m['T1I0']-m['T0I0'],'inference_on_T1':m['T1I1']-m['T1I0'],
                     'inference_on_T0':m['T0I1']-m['T0I0'],'combined':m['T1I1']-m['T0I0'],
                     'interaction':m['T1I1']-m['T1I0']-m['T0I1']+m['T0I0']}
    total={name:sum(x[name] for x in by_method[(corpus,'T1I1')]) for name in ['tp','fp','fn']}
    r=next(r for r in rows('B0703') if r[0]==corpus)
    v=list(map(int,r[1:]));reconciled=sum(v[:5])-v[5]-v[6]
    check(f'5-4 {corpus} member identity',reconciled==v[-1]==total['tp'],{'sum':reconciled,'total':total})
    for r in [r for r in rows('B0706') if r[0]==corpus]:
        vals=list(map(int,r[2:]));check(f'5-5a {corpus} {r[1]}',sum(vals[1:])==vals[0],vals)
    r=next(r for r in rows('B0708') if r[0]==corpus);v=list(map(int,r[1:]));check(f'5-5b {corpus}',sum(v[1:])==v[0],v)
    r=next(r for r in rows('B0620') if r[0]==corpus and r[1]=='T1I1')
    initial,recovered,lost,del_fp,add_fp=map(int,r[2:7])
    init=by_method[(corpus,'T1I0')]
    check(f'4-6 {corpus} object transitions',initial+recovered-lost==total['tp'] and sum(x['fp'] for x in init)-del_fp+add_fp==total['fp'],{'initial_tp':initial,'recover':recovered,'lost':lost,'final':total})

for row in rows('B0613'):
    corpus,*v=row;v=list(map(int,v))
    check(f'4-5 {corpus} supply chain',v[0]>=v[1] and all(a>=b for a,b in zip(v[2:],v[3:])),v)

for row in rows('B0367'):
    group,nh,n,pi,accepted,unsafe,pct,ci,agreement,kappa=row
    nh,n,accepted,unsafe=map(int,[nh,n,accepted,unsafe])
    check(f'3-6 {group} rate',abs(100*unsafe/accepted-float(pct.rstrip('%')))<=.0051,{'unsafe_rate':100*unsafe/accepted,'Wilson':wilson(unsafe,accepted)})
    check(f'3-6 {group} sampling probability',abs(n/nh-float(pi))<=.000051,{'pi':n/nh})
    rejection=next(r for r in rows('B1020') if r[0]==group)
    check(f'3-6 and H-2 {group}',accepted+sum(map(int,rejection[1:]))==n,{'accepted':accepted,'rejected':rejection[1:],'n':n})

for corpus in ['AAEC','CDCP']:
    groups=[r for r in rows('B0367') if r[0].startswith(corpus)]
    accepted=sum(int(r[4]) for r in groups);unsafe=sum(int(r[5]) for r in groups)
    wa=sum(int(r[4])*int(r[1])/int(r[2]) for r in groups)
    wu=sum(int(r[5])*int(r[1])/int(r[2]) for r in groups)
    declared=next(r for r in rows('B0378') if r[0]==corpus)
    check(f'3-8 {corpus} unsafe aggregation',abs(100*unsafe/accepted-float(declared[2].rstrip('%')))<=.0051 and abs(100*wu/wa-float(declared[3].rstrip('%')))<=.0051,{'unweighted':100*unsafe/accepted,'weighted':100*wu/wa,'accepted':accepted,'unsafe':unsafe})

for method in ['T0I0','T1I0','T0I1','T1I1']:
    rr=[r for r in rows('B0714') if r[1]==method]
    summed=[sum(int(r[c]) for r in rr) for c in [2,3,4]]
    target=[sum(x[k] for x in by_method[('CDCP',method)]) for k in ['tp','fp','fn']]
    check(f'5-6 {method} arity groups',summed==target,{'groups_sum':summed,'H5_sum':target})

for row in rows('B0641'):
    seed,before,after,bf,af,removed,lost=row
    b=list(map(int,before.split('/')));a=list(map(int,after.split('/')))
    check(f'4-10 CPU case seed {seed}',abs(f1(*b)-float(bf))<=.0051 and abs(f1(*a)-float(af))<=.0051,{'before':f1(*b),'after':f1(*a)})

for row in rows('B0634'):
    actual=sum(float(x) for x in row[2:6]);reported=float(row[7])
    check(f'4-9 cost {row[0]} {row[1]}',abs(actual-reported)<=.0201,{'component_sum':actual,'reported_total':reported})

components=sum(int(r[4]) for r in rows('B0176'))
check('2-3 and A-1 component total',components==10986,{'sum':components})
check('I-1 CasiMedicos retained and excluded',381+55+117+69==622,{'retained':381+55+117,'excluded':69,'original':622})

out={'source_scope':'Only supplied DOCX tables; no underlying model, reviewer or solver runs verified',
     'checks':results,'pass_count':sum(r['status']=='passed' for r in results),'check_count':len(results),
     'derived_effects':derived,
     'formal_example_issue':{'source':'B.6 and 4.4.4; Table 2-5 / A-2', 'old_utility':.8,'new_utility':1.,'gain_decimal':'.20','default_delta':'.20','condition':'gain > delta','passes_default_gate':False,
                             'scope':'Positive gain exists, but the stated numerical example does not pass the default strict margin. Fix example or declare a smaller demonstration margin.'},
     'not_recomputable_from_DOCX':['bootstrap confidence intervals and p-values','AUROC AP Brier ECE from score arrays','actual training gradients and runtime','source file hash strings without files','case raw outputs and exact text slices without source texts']}
(W/'numeric_audit.json').write_text(json.dumps(out,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:v for k,v in out.items() if k!='checks'},ensure_ascii=False,indent=2))
for r in results:
    if r['status']!='passed':print(json.dumps(r,ensure_ascii=False))
