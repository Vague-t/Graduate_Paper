"""Regenerate two code-native mechanism figures; preserve all old assets."""
import importlib.util,sys,json,inspect
from pathlib import Path
sys.dont_write_bytecode=True
W=Path(__file__).resolve().parent
spec=importlib.util.spec_from_file_location('native_figures',W.parent/'_revision_1007_v2/figures/generate_figures.py')
m=importlib.util.module_from_spec(spec);sys.modules[spec.name]=m;spec.loader.exec_module(m)
m.ROOT=W/'figures';m.ROOT.mkdir(exist_ok=True)
m.pdfmetrics.registerFont(m.TTFont(m.FONT,str(m.FONT_PATH)))
src=inspect.getsource(m.repair)
src=src.replace('如产生外部依赖冲突：扩大事务或拒绝','失效已选槽位最小扩域并计费；仍失败则拒绝')
src=src.replace('无法维持则扩大事务或拒绝','失效已选槽位最小扩域、重新计费，仍失败则拒绝')
exec(src,m.__dict__);m.repair(300)

def flow(dpi):
    d=m.Diagram('bounded_execution',382,'固定候选与评分下，六类队列分批评估并整批择优；空批保留no-op并继续余批。',[
      '每次搜索前冻结候选及评分；纯关系、插入、删除、替换、拆分、合并六类轮转。',
      '单提议评估执行冲突闭合、失效已选外部槽位最小扩域、完整计费和全图复核。',
      '空批继续余批；队列检查完或资源用尽停止；非空合格批择优原子提交。'])
    d.box(15,8,414,30,'原文 → K 个候选 → MCR 与共用合法化 → 初始合法图',size=9.3)
    d.arrow([(222,38),(222,49)])
    d.box(15,49,414,34,'冻结候选宇宙、完整对象分、效用及资源配置\n训练辅助头不参与推理；no-op独立保留当前图',size=9.2,fill=.95)
    d.arrow([(222,83),(222,95)])
    d.box(34,95,380,34,'按当前状态枚举六类提议并轮转；批长6\n每轮外层尝试32／接受3；失败计算也计费',size=9.2,fill=.93)
    d.arrow([(222,129),(222,141)])
    d.box(34,141,380,34,'算法4-2：冲突闭合与端点依赖域\n失效已选外部槽位最小扩域；全部删增重新计费',size=9.2,fill=.93)
    d.arrow([(222,175),(222,187)])
    d.box(34,187,380,34,'局部ILP；可行incumbent复核且保留非最优身份\n整图合法、分项非降、严格总增益、剩余预算',size=9.2,fill=.93)
    d.arrow([(130,221),(130,236)])
    d.arrow([(330,221),(330,236)],dash=(3,2))
    d.box(34,236,192,42,'有合格项：整批择优\n总效用 → 少编辑 → 语义键\n原子提交；失败完整回退',size=9.1,fill=.92,leading=11.5)
    d.box(245,236,169,42,'本批无合格：保留no-op\n仍有余批且额度允许：继续\n队列或资源耗尽：停止',size=9.0,leading=11.5)
    d.arrow([(34,258),(20,258),(20,112),(34,112)],dash=(3,2))
    d.text(17,302,'同状态跨轮续游标；未见状态建队列；评分冻结',size=9.2,align='left')
    d.box(120,313,230,26,'返回最后完整合法图及停止原因',size=9.2)
    d.arrow([(330,278),(330,313)],dash=(3,2))
    d.legend(361)
    d.save(dpi)
flow(300)
(m.ROOT/'semantic_manifest.json').write_text(json.dumps({'status':'constructed_mechanism_not_measurement','figures':m.RECORDS},ensure_ascii=False,indent=2)+'\n')
