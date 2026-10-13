# 单卡 24GB 服务器运行手册

以下命令在本项目根目录执行。正式运行前固定代码、模型 revision、数据摘要和计划；本手册提供可执行步骤，不声明服务器训练、24GB 峰值显存或方法增益已经通过实测。

## 1. 环境与文件

建议 Linux、Python 3.11/3.12、支持 bf16 的 NVIDIA GPU，并预留模型、三折检查点和候选快照所需空间。单卡 24GB 不意味着任何 8192-token 双视图都一定可运行，先做一篇短样本及最长样本预检。

```bash
python3.11 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[test,cuda]'
python - <<'PY'
import torch, transformers, scipy, bitsandbytes
print('torch', torch.__version__, 'transformers', transformers.__version__)
print('scipy', scipy.__version__, 'bitsandbytes', bitsandbytes.__version__)
assert torch.cuda.is_available(), 'CUDA unavailable'
print(torch.cuda.get_device_name(0))
print('VRAM GiB', torch.cuda.get_device_properties(0).total_memory/2**30)
assert torch.cuda.is_bf16_supported(), 'This profile requires bf16 support'
PY
OMP_NUM_THREADS=2 python -m pytest -q
```

若 CUDA PyTorch 不可用，应按该服务器驱动匹配的官方 PyTorch 发行包安装后重做检查；不要把 CPU 测试通过当成 CUDA 环境通过。项目依赖版本写在 `pyproject.toml`。首次启动同时保存 `python -m pip freeze` 与 `nvidia-smi` 到本次实验目录。

## 2. 模型下载与版本固定

本地小模型固定版本为 `Qwen/Qwen2.5-0.5B-Instruct@7ae557604adf67be50417f59c2c2f167def9a775`。服务器默认使用 7B，下载脚本会先将请求 revision 解析成精确提交，再记录每个本地文件的 SHA-256：

```bash
python scripts/download_model.py \
  --model Qwen/Qwen2.5-7B-Instruct \
  --revision main --output models/Qwen2.5-7B-Instruct
python - <<'PY'
import json
from pathlib import Path
cfg=json.loads(Path('configs/server_24gb.json').read_text())
manifest=json.loads(Path('models/Qwen2.5-7B-Instruct/download_manifest.json').read_text())
revision=manifest['revision']
cfg['model']['revision']=revision
cfg['chat']['revision']=revision
cfg['encoder']['revision']=revision
cfg['profile']['pinned_revision']=revision
Path('configs/server_24gb_locked.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
print('Locked model revision:',revision)
PY
```

`model`、`chat`、`encoder` 都引用本地模型路径，但职责和参数更新不同。生成器使用训练 adapter；审核/源组调用保持冻结；对象评分头另行训练。不要用某一阶段的新 checkpoint 随意替换另一阶段的基础模型。四比特开启 NF4、double quant 和 bf16 计算。没有 CUDA/bitsandbytes 时明确失败。

## 3. 准备原始语料

本机已有文件的完整历史路径为：

- `/Users/channtang/Downloads/paper/research_0920/data/aaec_brat.zip`
- `/Users/channtang/Downloads/paper/research_0920/data/aaec_split.csv`
- `/Users/channtang/Downloads/paper/research_0920/data/cdcp_acl17.zip`

服务器上将你有权使用的三份原始文件放到一个目录，或为这些文件创建符号链接。不要通过本代码压缩包重新分发语料。

```bash
RAW_CORPUS_DIR=/path/to/authorized_corpora
python -m argrepair prepare \
  --raw "$RAW_CORPUS_DIR" --out data/native_server_001 --seed 17
```

检查 `data_audit.json` 与 `split_manifest.json`：

- 官方测试保留 AAEC 80、CDCP 150 篇；失败也不得减小评价分母。
- 全文哈希定义源组；重复训练源保留一个规范代表，跨训练/测试重复则保留测试、排除相应训练副本。
- 字符跨度只规范化标注首尾空白并保存变更；词内边界保留，CDCP 多源超边不拆平。`native_v2` 保留 AAEC Stance 属性，增强输运同步属性绑定的字符键，当前不把它扩展为新预测任务。
- 三折 OOF 在官方训练源组中建立；每个 OOF 提取器和跨度头排除该源及其所有增强视图。
- 官方训练源组另固定为约 80% scorer-fit、10% calibration、10% policy，三者的标签用途分离；测试只用于最后计数。

本机已准备快照的原始摘要为：

| 文件 | SHA-256 |
|---|---|
| aaec_brat.zip | `9f49a6d388896d0f390445592ccc9dbfc87325553e3fe3f988eb252de7cdc4b5` |
| aaec_split.csv | `903176797ea73c45e3848019bc390882a2bdab520e5feb4b28fd75d95ec44285` |
| cdcp_acl17.zip | `acec61f72e5f9dfcb200ff620a529fad7d1f69928e42498eedc66d98eb1fe2a0` |

摘要不同不自动代表错误，但必须记录来源及差异，不能沿用旧版样本统计。

## 4. 先做短样本和显存预检

在 GPU 训练之前，对全部输入进行不加载权重的预检：

```bash
python scripts/preflight.py --data data/native_server_001 \
  --config configs/server_24gb_locked.json \
  --out runs/preflight_server_001.json
```

程序读取训练标注以核查金标图、答案长度和因素资源；测试仅读取 `*_test_inputs.jsonl`，不访问测试标注。输出 `weights_loaded=false` 与 `gpu_memory_validated=false`。若失败，先处理并登记协议/长度问题，不能忽略失败后偷偷剔除文档；修改配置则另存新版本重做预检。

先运行本地构造 smoke；再从 **训练集** 选择一篇较短真实文档，保存一个单独输入文件，执行 7B 一步训练。这样得到的是新模型的调试记录，不是论文结果。

```bash
python - <<'PY'
import json
from pathlib import Path
rows=[json.loads(x) for x in Path('data/native_server_001/aaec_train.jsonl').read_text().splitlines() if x.strip()]
short=min(rows,key=lambda x:len(x['text']))
Path('data/aaec_probe_train.jsonl').write_text(json.dumps(short,ensure_ascii=False)+'\n')
cfg=json.loads(Path('configs/server_24gb_locked.json').read_text())
cfg['training'].update(epochs=1,max_steps=1,accumulation=1)
Path('configs/server_24gb_probe.json').write_text(json.dumps(cfg,ensure_ascii=False,indent=2)+'\n')
PY
python -m argrepair train --data data/aaec_probe_train.jsonl \
  --config configs/server_24gb_probe.json --variant T0 --seed 17 \
  --out runs/gpu_probe_001
```

核对 `runs/gpu_probe_001/adapter/run_manifest.json`、`training_log.jsonl` 中的真实 step、loss、梯度范数和 `peak_cuda_allocated_bytes`。然后用训练侧长样本和真实接受视图检查 T1 最大负载；不要把单篇短样本峰值当成全文上限。

默认 `max_input_tokens=4096`、`max_output_tokens=2048`、`max_context=8192`；连续提示也占上下文。输入上限包括聊天模板；编码器上限针对其文本 token。超长或 OOM 时保留失败记录，再以新命名配置调整输入预算或模型规模；不要对同一实验身份静默截断。初调的 2048 上下文配置与 8192 正式配置分开报告。

## 5. 推荐：生成并运行完整计划

```bash
python -m argrepair plan --data data/native_server_001 \
  --config configs/server_24gb_locked.json \
  --out runs/paper_server_001 --corpus both --seeds 17 29 43
python -m argrepair run-plan --plan runs/paper_server_001/plan.json
```

计划会依次执行：

1. 每个语料进行训练侧增强与审核，固定视图/掩码。
2. 每个种子、每个 OOF 折训练跨度头，以及 T0/T1 提取器；折外全文生成、重排序、完整源组提案和候选构造。
3. 用折外候选拟合独立对象评分头；校准划分按各生成器部署候选分布校准；预先只用 T1 的独立 OOF policy 池选择是否修正及参数，冻结后共用于 T0/T1。
4. 在全部官方训练源上训练最终跨度头，以及 T0/Heads/NoPair/CompPair/T1 提取器；共同测试集执行 I0，T0/T1 再执行 I1，T1 再进行相应推理消融。
5. 完整对象计数与配对统计，输出各方法、语料、文档、种子的原始计数。

正式运行前阅读生成的 `comparisons.json`。当前可执行计划声明自己的主要比较族与探索比较，不宣称已经实现历史模拟表中的全部比较族；历史 14 项与新计划的差异不能靠改名称掩盖。新增对照须在测试评价之前冻结协议。

`commands.sh` 用于查看外部命令；内部视图过滤、候选并集等步骤由 `run-plan` 完成，不能仅执行带注释的 shell 文件后声称完整计划已运行。各阶段为独立进程，在单卡上串行加载模型。

## 6. 需要逐步排查时的命令

下面给出一个 AAEC/seed17/fold0 的具体路径示例；完整三折由 plan 自动展开。

```bash
python -m argrepair augment --data data/native_server_001/aaec_train.jsonl \
  --mode factor --config configs/server_24gb_locked.json --out runs/manual/augment
python -m argrepair span-train --data data/native_server_001/aaec_fold0_train.jsonl \
  --corpus aaec --config configs/server_24gb_locked.json --out runs/manual/fold0-span
```

过滤增强视图到本折训练源，防止把折外视图传入训练：

```bash
python - <<'PY'
from argrepair.io import read_jsonl,write_jsonl
ids={x['doc_id'] for x in read_jsonl('data/native_server_001/aaec_fold0_train.jsonl')}
write_jsonl('runs/manual/fold0-views.jsonl',[v for v in read_jsonl('runs/manual/augment/views.jsonl') if v['source_doc_id'] in ids])
PY
python -m argrepair train --data data/native_server_001/aaec_fold0_train.jsonl \
  --views runs/manual/fold0-views.jsonl --variant T1 --seed 17 \
  --config configs/server_24gb_locked.json --out runs/manual/fold0-T1
python -m argrepair generate --inputs data/native_server_001/aaec_fold0_inputs.jsonl \
  --adapter runs/manual/fold0-T1/adapter/checkpoint \
  --config configs/server_24gb_locked.json --out runs/manual/fold0-generate
python -m argrepair rank --inputs data/native_server_001/aaec_fold0_inputs.jsonl \
  --generations runs/manual/fold0-generate/generations.jsonl \
  --config configs/server_24gb_locked.json --out runs/manual/fold0-rank
python -m argrepair groups --inputs data/native_server_001/aaec_fold0_inputs.jsonl \
  --ranked runs/manual/fold0-rank/ranked.jsonl \
  --span runs/manual/fold0-span/span \
  --config configs/server_24gb_locked.json --out runs/manual/fold0-groups
python -m argrepair build-pools --inputs data/native_server_001/aaec_fold0_inputs.jsonl \
  --ranked runs/manual/fold0-rank/ranked.jsonl --groups runs/manual/fold0-groups/groups.jsonl \
  --span runs/manual/fold0-span/span --oof \
  --config configs/server_24gb_locked.json --out runs/manual/fold0-pools
```

AAEC 不需要源组模型，groups 会生成对应空提案记录；CDCP 先读取跨度头补充完整组件目录，再调用模型产生完整源集合。跨度编码器在聊天模型加载前释放。

准备 **三折、T0/T1 六份** OOF 池后：

```bash
python -m argrepair scorer-train --data data/native_server_001/aaec_fit.jsonl \
  --pools PATH_TO_FOLD0_T0_POOLS PATH_TO_FOLD0_T1_POOLS \
          PATH_TO_FOLD1_T0_POOLS PATH_TO_FOLD1_T1_POOLS \
          PATH_TO_FOLD2_T0_POOLS PATH_TO_FOLD2_T1_POOLS \
  --corpus aaec --config configs/server_24gb_locked.json --out runs/manual/scorer-fit
python -m argrepair calibrate --data data/native_server_001/aaec_calibration.jsonl \
  --pools PATH_TO_FOLD0_T0_POOLS PATH_TO_FOLD0_T1_POOLS \
          PATH_TO_FOLD1_T0_POOLS PATH_TO_FOLD1_T1_POOLS \
          PATH_TO_FOLD2_T0_POOLS PATH_TO_FOLD2_T1_POOLS \
  --scorer runs/manual/scorer-fit/scorer \
  --config configs/server_24gb_locked.json --out runs/manual/calibrated
```

此处 `PATH_TO_...` 必须替换为实际六份 `pools.jsonl`，不是合成数据。评分拟合可以按原生身份取候选并集；校准必须保留各生成器实际候选频率，先执行部署裁剪，再拟合分族正斜率 Platt。空集、单类别或缺失 OOF 来源不会伪装校准成功。

policy 和测试阶段建议继续用完整计划，其会进行候选范围一致性、来源和摘要检查。单独运行 I1 必须提供训练侧 `policy.json`；`Global` 是可直接调用的诊断接口，不因此成为已冻结的正式 I1。

## 7. NoRisk 与 Regenerate 对照

NoRisk 已纳入默认主要比较：保持同一评分、κ、依赖闭合、合法性、分项门和编辑预算，只将 `delta` 改为 `10 × numeric_tol`，并绕过开发集 `enabled=false` 的禁修开关。它不等于关闭所有安全条件或重新拟合评分器。默认计划每语料声明六项主要比较。

Regenerate 是独立入口，`configs/*.json` 中 `regeneration.enabled=false`。其正式比较需要逐文档真实 I1 资源凭证，绑定文档/检查点/调用与输入输出 token 上限、完整实际使用记录和源运行文件摘要。不能使用历史模拟中的数字填成“已匹配”。具备凭证后以新配置启用，并提供可含 `{corpus}`、`{seed}` 占位的 `reference_budget_manifest` 路径；计划验证匹配后才允许评价并新增第七项主要比较。

```bash
python -m argrepair.regeneration --help
```

请按该入口的实际凭证契约准备文件。无资源记录或调用失败后的真实消耗不明时，保留诊断输出但不能声称通过等预算验收。相同资源上限不要求两种方法恰好消耗相同 token；还须分别报告实际成本与 MILP CPU 时间。

## 8. 输出、失败与续跑

- 每个阶段使用新输出目录；已有 `manifest.json` 不覆盖。
- `run-plan --resume` 核验计划、配置、代码、输入及检查点/输出摘要后跳过已完成阶段；它不等价于从 optimizer 的任意中间 step 精确续训。修改代码、模型或配置后应生成新版本计划，不能绕过旧计划绑定。
- 单个训练阶段保存结束检查点与 optimizer 状态。失败阶段连同计划状态保留，使用新的计划目录重跑；仅移动失败输出目录不能绕过 `.job_state` 的失败保护。不要删除成功阶段来掩盖失败。
- 超长、解析失败、候选构造失败、缺分、预算耗尽、数学不可行、求解超时分别报告。候选构造失败保留可用 G0；初始化失败保留空输出并继续计入官方分母。
- `generation_failed`、`candidate_failed` 与 `policy_no_repair` 不是同一种结论。增强零接受也不代表成对机制已完成验证。
- 全局主目标最优、二级最少编辑、三级破同分是否完成分别记录。局部按累计编辑计费；全局按相对 G0 的净编辑计费，不能直接把预算差异解释为搜索算法优势。

最终论文结果应从本次真实 `counts.jsonl` 与统计输出生成，同时报告运行配置、失败覆盖、增益与负收益个例、完整多源恢复、成本和不确定性。不要将教学图、故障注入、随机模型调试或历史模拟表写成服务器真实实验。
