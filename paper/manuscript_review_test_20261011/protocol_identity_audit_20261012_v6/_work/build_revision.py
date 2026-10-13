from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
from lxml import etree as E
import json, hashlib, shutil

O = Path(__file__).resolve().parents[1]
SM = json.loads((O/'_source/manifest.json').read_text())
S = Path(SM['source'])
D = O/'论文规范排版稿_v6.docx'
sha = lambda p: hashlib.sha256(p.read_bytes()).hexdigest()
assert sha(S) == SM['sha256']
with ZipFile(S) as z:
    data = {n: z.read(n) for n in z.namelist()}
root = E.fromstring(data['word/document.xml'])
NS = {'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main', 'm':'http://schemas.openxmlformats.org/officeDocument/2006/math'}
body = root.find('{'+NS['w']+'}body')
T = lambda p: ''.join(p.xpath('.//w:t/text()|.//m:t/text()', namespaces=NS))
edits=[]
def replace(bid, old, new, reason):
    p=body[int(bid[1:])]
    before=T(p)
    assert before.count(old)==1, (bid,before,old)
    nodes=p.xpath('.//w:t',namespaces=NS)
    # Replace only textual runs. Native mathematical objects remain untouched.
    joined=''.join(n.text or '' for n in nodes)
    assert joined.count(old)==1, (bid,joined)
    start=joined.index(old);end=start+len(old);pos=0
    for n in nodes:
        s=n.text or '';a=pos;b=pos+len(s);pos=b
        if b<=start or a>=end:continue
        left=s[:max(0,start-a)]
        right=s[max(0,end-a):] if end<b else ''
        n.text=left+(new if a<=start<b else '')+right
    after=T(p)
    assert after==before.replace(old,new), (bid,after)
    edits.append({'block_id':bid,'op':'replace_text','before':before,'after':after,'reason':reason})

replace('B0300','继承配置T0/I0在共同协议下重新评价，其增量作为后续主要比较的基准。',
        'T0保留MCR-BR的结论专项适配、线索提示及句子监督，I0保留其多候选重排序与有界修正BR-O；T0/I0构成完整继承配置。I0的最终输出包含BR-O修正，不能用仅经初始重排序和共同合法化得到的G0代替。后续主要比较以共同协议下的T0/I0为基准。',
        '恢复被简化掉的继承配置定义，明确I0包含旧BR-O，区别I0终态与G0。')
replace('B0488','T0/I0为继承配置；','T0/I0为包含BR-O推理的完整继承配置；',
        '明确训练对照统一沿用的I0包含继承修正。')
replace('B0527','I1表示依赖闭合决策及固定路由的完整配置，BR-J专指集合局部子程序；',
        'I0沿用继承的BR-O；I1保留初始候选生成与重排序接口，以依赖闭合决策及固定路由替代BR-O，BR-J专指其中的集合局部子程序；',
        '明确新推理与继承推理的替代关系，不把I1写成在I0终态上追加修正。')
replace('B0553','并补充预测分段中相邻2／3成员的源组，每文档补充源组上限256',
        '再加入预测分段中相邻2／3成员的规则补充，模型提案与规则补充合计每文档最多256个完整源组与目标',
        '64约束模型提案，256约束模型提案与规则补充的合计，受保护关系另计。')
replace('B0557','CDCP完整源组与目标提案最多256',
        'CDCP模型提案最多64，连同规则补充共不超过256个完整源组与目标',
        '统一候选资源段与候选构建段的数量口径。')
replace('B0782','以T0/I0作为继承配置，并在相同测试文档和三个种子上比较四种组合。其中，T1/I0仅引入第三章的训练配置，T0/I1仅引入第四章的推理配置，T1/I1同时采用两阶段方法。',
        '以含BR-O推理的T0/I0作为完整继承配置，并在相同测试文档和三个种子上比较四种组合。其中，T1/I0引入第三章的训练配置并保留BR-O；T0/I1保留继承训练，以第四章的I1替代I0；T1/I1同时采用两阶段方法。',
        '在综合章再次明确四格配置，避免将I0误当作无修正基线。')
replace('B0783','固定T1时的推理比较考察既定模型输出上的修正增量',
        '固定T1时的推理比较考察I1替代继承I0后的条件增量',
        '主比较是新旧推理配置之差，并非相对未经BR-O修正的初始图。')
# The table has one changed explanatory cell; all result tables remain intact.
table=body[785]
cells=table.xpath('.//w:tc',namespaces=NS)
target=next(c for c in cells if T(c)=='I1是否改善初始图')
before=T(target)
ns=target.xpath('.//w:t',namespaces=NS)
ns[0].text='完整I1是否优于继承I0'
for n in ns[1:]:n.text=''
edits.append({'block_id':'B0785','op':'replace_cell','before':before,'after':T(target),'reason':'表5-1与实际I1−I0比较对象一致。'})
replace('B0799','在T1基础上启用I1后，进一步增加4.48 pp和8.37 pp。',
        '固定T1并以I1替代I0后，分别增加4.48 pp和8.37 pp。',
        '避免将I1误读为在含BR-O的I0结果上继续叠加修正。')
data['word/document.xml']=E.tostring(root,xml_declaration=True,encoding='UTF-8',standalone=True)
with ZipFile(D,'w',ZIP_DEFLATED) as z:
    for n,b in data.items():z.writestr(n,b)
prior=json.loads((S.parent/'_work/revision_manifest.json').read_text())
M={'source':str(S),'output':str(D),'source_sha256':sha(S),'output_sha256':sha(D),
   'scope':'Confirmed I0 and CDCP proposal-cap definitions only. Three independent audit proposals are not applied.',
   'edits':edits,'headings':prior['headings']}
(O/'_work/revision_manifest.json').write_text(json.dumps(M,ensure_ascii=False,indent=2))
shutil.copyfile(S.parent/'_work/sync_toc.py',O/'_work/sync_toc.py')
print(json.dumps({'output':str(D),'edits':len(edits),'source_preserved':sha(S)==SM['sha256']},ensure_ascii=False))
