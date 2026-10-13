# Layout fixture

## 摘要

本文件仅用于内部验证新构建器的目录、公式和表格排版。

## Abstract

This internal fixture tests native fields and layout only.

## 第一章 绪论

### 1.1 研究问题

#### 1.1.1 组件依赖

公式居中，编号独立靠右。

$$
\mathcal{G}=(\mathcal{V},\mathcal{R}),\quad \Delta\Phi_C\geq 0,\quad \Delta\Phi_R\geq 0.
$$

表1-1 内部排版测试

| 方法 | 组件 | 关系 |
| --- | --- | --- |
| A | 1.0P | 2.0P |
| B | 3.0P | 4.0P |

算法1-1 内部算法排版测试

```algorithm
输入：固定候选与原始图。
输出：保持约束的完整图。
读取输入并固定评分。
若提案不满足约束，则保留原状态。
返回完整图。
```

## 第二章 任务表示

### 2.1 公式分章

$$
\sum_{t\in S(u)} z_t\leq 1,\quad y_r\leq z_c\ \forall c\in\mathrm{Ends}(r).
$$
