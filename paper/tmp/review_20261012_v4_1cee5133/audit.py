from pathlib import Path
from collections import defaultdict
import json, statistics, math, re

base=Path(__file__).parent
tables={x['block']:x['rows'] for x in json.loads((base/'tables.json').read_text())}
four=defaultdict(list); counts={}; individual=[]
for row in tables[1117][1:]:
    ds,method,seed,tp,fp,fn,reported=row
    tp,fp,fn=map(int,(tp,fp,fn)); score=200*tp/(2*tp+fp+fn)
    individual.append({'dataset':ds,'method':method,'seed':seed,'recomputed':score,'reported':reported,'consistent':abs(score-float(reported))<=0.005001})
    four[(ds,method)].append(score); counts[(ds,method,int(seed))]=(tp,fp,fn)
stats={f'{d}/{m}':{'mean':statistics.mean(v),'sample_sd':statistics.stdev(v),'values':v} for (d,m),v in four.items()}
diffs={d:{'training':statistics.mean(four[(d,'T1I0')])-statistics.mean(four[(d,'T0I0')]),'inference':statistics.mean(four[(d,'T1I1')])-statistics.mean(four[(d,'T1I0')]),'total':statistics.mean(four[(d,'T1I1')])-statistics.mean(four[(d,'T0I0')]),'interaction':statistics.mean(four[(d,'T1I1')])-statistics.mean(four[(d,'T1I0')])-statistics.mean(four[(d,'T0I1')])+statistics.mean(four[(d,'T0I0')])} for d in ['AAEC','CDCP']}
cardinality=[{'dataset':d,'method':m,'seed':s,'predicted':t+p,'gold':t+n,'equal':p==n} for (d,m,s),(t,p,n) in counts.items() if m.endswith('I0')]
members=[]
for r in tables[786][1:]:
    v=list(map(int,r[1:])); implied=v[0]+sum(v[1:5])-v[5]-v[6]
    members.append({'dataset':r[0],'recomputed':implied,'reported':v[7],'consistent':implied==v[7]})
audit={}
for ds in ['AAEC','CDCP']:
    rows=[r for r in tables[497][1:] if r[0].startswith(ds)]
    weighted_num=sum(int(r[5])*int(r[1])/int(r[2]) for r in rows)
    weighted_den=sum(int(r[4])*int(r[1])/int(r[2]) for r in rows)
    audit[ds]={'weighted_unsafe_percent':100*weighted_num/weighted_den,'sample_n':sum(int(r[2]) for r in rows),'sample_accepted':sum(int(r[4]) for r in rows),'sample_unsafe':sum(int(r[5]) for r in rows)}
wilson=[]
for r in tables[497][1:]:
    n=int(r[4]); k=int(r[5]); p=k/n; z=1.959963984540054; a=1+z*z/n
    center=(p+z*z/(2*n))/a; half=z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/a
    wilson.append({'group':r[0],'computed':[100*(center-half),100*(center+half)],'reported':r[7]})
result={'scope':'Manuscript-only arithmetic, not reproduction of experiments or document-level bootstrap p/CI','individual_F1':individual,'four_grid_summary':stats,'differences':diffs,'I0_cardinality':cardinality,'member_identity':members,'weighted_audit':audit,'Wilson_independence_approximation':wilson}
(base/'arithmetic_audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2))
print(json.dumps({'F1_rows':len(individual),'F1_mismatches':[x for x in individual if not x['consistent']],'summary':stats,'differences':diffs,'I0_equal_cardinality_rows':sum(x['equal'] for x in cardinality),'I0_total_rows':len(cardinality),'members':members,'weighted_audit':audit,'Wilson':wilson},ensure_ascii=False,indent=2))
