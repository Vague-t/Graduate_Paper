from pathlib import Path
import json
O=Path(__file__).resolve().parents[1];P=[]
def a(b,old,new,why,**kw):P.append(dict(block_id=f'B{b:04d}',old_text=old,new_text=new,reason=why,category='统一终审',**kw))
for b,old in [(500,'差值/百分点'),(798,'差值/pp'),(836,'差值/pp'),(1033,'差值/pp')]:a(b,old,'差值（百分点）','统一统计表格的F1差值单位。')
for b in [500,798,836,1033]:a(b,'95% CI','单项95% CI','明确区间未作家族同时校正；与第2章及表4-6一致。')
a(1072,'原稿已发表值','MCR-BR已发表值','明确转录结果的来源主体。')
a(1072,'均值差/pp','均值差（百分点）','统一差值单位。')
a(319,'文件位置及内容概述见附录J S2.5。','复算材料说明见附录J的S2.5。','避免将文件摘要误读为内容摘要。')
a(532,'AAEC essay098的CPU模型的实际预测','CPU模型对AAEC essay098的实际预测','删除重复的属格，明确预测对象。')
a(1097,'OOF训练；Platt冻结','OOF训练；Platt校准参数冻结','冻结的是校准参数而非校准方法。')
(O/'_work/editorial_additions.json').write_text(json.dumps(P,ensure_ascii=False,indent=2));print(len(P))
