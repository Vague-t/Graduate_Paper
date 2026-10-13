"""Collect already executed evidence; never launch or invent benchmark results."""
from pathlib import Path
import json,shutil,sys,xml.etree.ElementTree as ET
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from argrepair.io import read_json,write_json,file_hash
from argrepair.schema import digest,Graph

root=Path(__file__).resolve().parents[1];out=root/'validation';out.mkdir(exist_ok=True)
tree=ET.parse(out/'pytest.xml');suites=list(tree.getroot().iter('testsuite'))
tests=sum(int(x.attrib['tests']) for x in suites);failures=sum(int(x.attrib['failures'])+int(x.attrib['errors']) for x in suites)
assert tests>0 and failures==0,'No successful complete pytest evidence'
pretrained=root/'runs/pretrained_qwen05b_overfit64_20261012';tiny=root/'runs/tiny_e2e_20261012_final'
report=read_json(pretrained/'report.json');generation=read_json(pretrained/'generation.json')
assert read_json(pretrained/'manifest.json')['status']=='completed'
assert read_json(tiny/'manifest.json')['status']=='completed'
assert generation['status']=='ok' and report['training_steps']==64
assert report['reloaded_loss']==report['teacher_forced_generation_loss_after']
audit=read_json(root/'data/native_v2/data_audit.json');preflight=read_json(root/'runs/context_preflight_final.json')
assert preflight['status']=='passed'
plan=read_json(root/'runs/server_plan_24gb_reviewable/plan.json')
sources={str(p.relative_to(root)):file_hash(p) for pattern in ('argrepair/*.py','scripts/*.py','tests/*.py','configs/*.json') for p in sorted(root.glob(pattern))}
write_json(out/'source_snapshot.json',{'files':sources,'digest':digest(sources)})
for name,src in {
    'data_audit.json':root/'data/native_v2/data_audit.json',
    'context_preflight.json':root/'runs/context_preflight_final.json',
    'pretrained_report.json':pretrained/'report.json',
    'pretrained_generation.json':pretrained/'generation.json',
    'pretrained_run_manifest.json':pretrained/'manifest.json',
    'pretrained_training_log.jsonl':pretrained/'training/training_log.jsonl',
    'tiny_run_manifest.json':tiny/'manifest.json',
    'model_download_manifest.json':root/'models/Qwen2.5-0.5B-Instruct/download_manifest.json',
}.items():shutil.copyfile(src,out/name)
history=[]
for p in sorted((root/'runs').glob('pretrained*')):
    if (p/'manifest.json').is_file():
        m=read_json(p/'manifest.json');g=read_json(p/'generation.json') if (p/'generation.json').exists() else {}
        history.append({'directory':p.name,'execution_status':m['status'],'error':m.get('error'),
                        'generation_status':g.get('status'),'output_tokens':g.get('usage',{}).get('output_tokens'),
                        'training_steps':read_json(p/'training/run_manifest.json').get('steps_completed') if (p/'training/run_manifest.json').exists() else None})
write_json(out/'diagnostic_history.json',history)
summary={'validation_date':'2026-10-13','source_digest':digest(sources),'pytest_tests':tests,'pytest_failures':failures,
         'real_corpus_documents_preflighted':preflight['documents_checked'],'data_statistics':audit['statistics'],
         'pretrained_steps_on_one_train_document':64,'pretrained_generation_status':generation['status'],
         'server_plan_jobs':len(plan['jobs']),'server_training_executed':False,'cuda_24gb_validated':False,
         'heldout_model_benchmark_executed':False,'regenerate_budget_match_executed':False}
write_json(out/'summary.json',summary)
text=f'''# 本地验证报告（2026-10-13）

本报告对应当前实验代码，论文正文没有修改。代码快照摘要：`{digest(sources)}`；逐文件摘要见 `validation/source_snapshot.json`。

## 已执行结果

| 验证 | 实际结果 | 证据 |
|---|---|---|
| 完整测试 | {tests} passed，0 failures/errors | `validation/pytest.txt`、`pytest.xml` |
| 两种语料随机 tiny 端到端 | 真实优化器更新、构造双视图、评分/校准优化、跨度提案、六条修复路径、账本回放通过 | `runs/tiny_e2e_20261012_final` |
| 原始语料读取 | AAEC 319/80，CDCP 580/150 篇；CDCP 完整多源关系、词内字符边界及 AAEC Stance 属性保留 | `validation/data_audit.json` |
| 全文长度/因素预检 | 1,129 篇；最大输入 763、训练输出 862、总长 1,524 token，最大因素数 2,438，无溢出 | `validation/context_preflight.json` |
| 真实预训练模型 | Qwen2.5-0.5B，CPU float32；1 篇官方训练文档，64 次参数更新 | `validation/pretrained_report.json`、`pretrained_training_log.jsonl` |
| 自由生成与重载 | 输出 2 个组件、1 个关系，56 token、EOS 正常结束，结构校验通过；重载损失一致 | `validation/pretrained_generation.json` |
| 依赖与编译 | pip check 无破损依赖；Python 源码编译通过 | `requirements-lock-local.txt`；实际命令日志 |
| 服务器计划 | 双语料、3 个 seed，生成 {len(plan['jobs'])} 个有序阶段（含内部准备）；未启动服务器计算 | `runs/server_plan_24gb_reviewable/plan.json` |

本机使用 0.5B 的实际分词器做预检，服务器仍应对下载后的 7B 分词器重新运行。上述 token 数不是显存测量。

## 小模型诊断的解释

使用官方训练文档 `cdcp_00785`，生成损失由 {report['teacher_forced_generation_loss_before']:.8f} 降至 {report['teacher_forced_generation_loss_after']:.8f}；保存重载后为 {report['reloaded_loss']:.8f}。该样例已被训练，合法输出不能作为泛化能力、测试集 F1 或方法增益证据。

最初 1 步、8 步诊断的自由生成未通过解析，原始记录保留于 `validation/diagnostic_history.json` 及对应 runs 目录。后续 64 步过拟合诊断才通过完整图输出校验。早期冻结评分 metadata 序列化缺陷也保留在失败记录中，修复后已有专门回归测试。

此真实模型调试没有接受的增强视图，成对项为零。完整成对项、掩码、双侧梯度和原文/变体归一化通过独立构造双视图和随机 mini Qwen2 HF 测试验证。评分/跨度的真实模型接口使用训练标签构造候选进行调试，未进行自然候选校准质量评估。

## 尚需服务器实际完成

单卡 24GB 配置已经提供，但 CUDA、bitsandbytes、峰值显存尚未在本机验证。需要按 `SERVER_RUNBOOK.md` 运行短样本和最长样本/双视图负载检查，再执行完整 OOF 与最终训练。正式主表、置信区间、审核接受率、风险与成本均须由这次服务器运行生成。

默认计划每语料 6 项主要比较。Regenerate 实现了预算计费和验证入口，但在真实 I1 逐调用资源凭证齐备前关闭；启用并通过匹配后才扩为每语料 7 项（共 14 项）。外部论文系统和历史检查点不因本代码测试通过而视为已复现。

代码包不包含虚拟环境、模型权重、原始/全文语料或服务器训练结果。工作目录保留本机调试 checkpoint，压缩包通过下载/prepare 命令恢复相应依赖。
'''
(root/'LOCAL_VALIDATION.md').write_text(text)
print(json.dumps(summary,ensure_ascii=False,indent=2))
