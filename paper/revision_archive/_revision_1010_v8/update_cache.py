"""Update only TOC result text from the most recent verified PDF locations."""
from pathlib import Path
import json,zipfile
from lxml import etree
W=Path(__file__).resolve().parent;R=W.parent
NS={'w':'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
path=R/'report_1010_v8_full.docx';mapping=json.loads((W/'page_map.json').read_text())
build=json.loads((W/'docx_build.json').read_text());labels=[x[1] for x in build['headings']]+[x for prefix in ['图','表'] for x in build['captions'] if x.startswith(prefix)]
with zipfile.ZipFile(path) as z:infos=z.infolist();parts={n:z.read(n) for n in z.namelist()}
root=etree.fromstring(parts['word/document.xml'])
ps=root.xpath('//w:p[w:pPr/w:pStyle[@w:val="TOC1" or @w:val="TOC2" or @w:val="TOC3" or @w:val="FigureList" or @w:val="TableList"]]',namespaces=NS)
assert len(ps)==len(labels)
changed=0
for p,label in zip(ps,labels):
 nodes=p.xpath('.//w:t',namespaces=NS)
 assert ''.join(n.text or '' for n in nodes).startswith(label.replace('`','').replace('$','')) or label.startswith(('图','表')),(label,''.join(n.text or '' for n in nodes))
 changed+=nodes[-1].text!=mapping[label];nodes[-1].text=mapping[label]
parts['word/document.xml']=etree.tostring(root,encoding='UTF-8',xml_declaration=True,standalone=True)
with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
 for info in infos:z.writestr(info,parts[info.filename])
print('Cached page numbers updated:',changed,'/',len(labels))
