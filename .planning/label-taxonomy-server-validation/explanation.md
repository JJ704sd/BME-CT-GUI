# 标签体系与服务器验证解释

## 为什么需要这个说明

服务器在线推理已经能跑通 5-fold + soft ensemble + GUI 回填，但 validation 指标是否可信，取决于**预测 mask 和参考 label 是否使用同一套标签体系**。如果 AMOS22 原生标签被误判成 FLARE22 并自动 remap，就会出现 `foreground_dice` 很高但 `mean_dice` 很低的异常现象。

2026-05-31 已完成显式 `label_taxonomy=auto|AMOS22|FLARE22` 和更保守的 `detect_dataset()`。当前说明的重点不再是“是否要实现 taxonomy hint”，而是服务器更新后如何复跑并解释 AMOS/FLARE validation。

## 核心概念

### 1. label taxonomy

label taxonomy 指 label ID 与器官语义之间的对应关系。

例如当前 AMOS22 模型中：

```text
6 -> 肝脏
8 -> 主动脉
9 -> 下腔静脉
```

如果另一个数据集的 label ID 定义不同，即使 mask 看起来都是腹部器官，也不能直接按同一个 ID 计算 Dice。

### 2. remap

remap 是把外部数据集的 label ID 转换到当前模型的 label ID。

```text
FLARE22 label IDs -> AMOS22/current model label IDs
```

只有在确认参考 label 来自 FLARE22 时，才应该执行 FLARE22 到当前模型标签体系的 remap。

### 3. validation

validation 是把预测结果和参考 label 对齐后计算 Dice、foreground Dice、per-label metric 等。

validation 的前提是：

```text
prediction label ID 语义 == reference label ID 语义
```

如果这个前提不成立，Dice 数字没有质量解释意义。

## 显式 taxonomy hint 当前语义

请求字段：

```text
label_taxonomy=auto|AMOS22|FLARE22
```

当前行为：

- `AMOS22`：参考标签已经是 AMOS/current model 体系，不执行 FLARE remap。
- `FLARE22`：参考标签来自 FLARE22，强制执行 FLARE22 → 当前模型 remap。
- `auto`：保留自动检测，但策略更保守；如果参考标签 ID 是 checkpoint 标签 ID 的子集，不会自动触发 remap。

`label_taxonomy` 已纳入 cache key，避免不同标签体系的 validation 或预测语义混用。

## Dice 异常怎么理解

如果出现：

```text
foreground_dice 很高
mean_dice 很低
大量 per-label Dice 接近 0
remap_applied=true
```

常见解释是：

1. 前景整体位置可能大致对齐。
2. 单个器官 label ID 语义错位。
3. validation 对每个 label 的解释不可信。
4. 需要先检查 taxonomy/remap，而不是直接判断模型质量差。

## server gating 是什么

server gating 指创建推理 job 前，后端检查所需运行环境是否完整。

当前项目有两条运行路径：

```text
runtime_target=local
runtime_target=server
```

二者需要检查的文件不同。

### local 模式

本机推理需要检查本地 nnUNetv2 相关文件，例如：

```text
nnunetv2_files/checkpoint_best.pth
本地 dataset.json
本地 plans.json
本地 python / nnUNetv2 环境
```

### server 模式

服务器推理应检查 server runtime 配置，例如：

```text
SEGMENTATION_SERVER_EVALUATE_SCRIPT
SEGMENTATION_SERVER_DATASET_JSON
SEGMENTATION_SERVER_NNUNET_RAW
SEGMENTATION_SERVER_NNUNET_PREPROCESSED
SEGMENTATION_SERVER_NNUNET_RESULTS
SEGMENTATION_SERVER_OUTPUT_ROOT
```

server 模式不应因为 Windows 本地缺少 `dataset.json/plans/checkpoint/python.exe` 而拒绝创建 job。当前下一轮仍需重点验证和收口这一点。

## 服务器更新后的排查顺序

1. 用 `deployment-packages/server-runtime-package-20260531.zip` 覆盖服务器后端代码，并重启 FastAPI。
2. 确认 `/api/health` 和 `/api/models` 可访问。
3. 上传 AMOS 原图 + AMOS label，选择 `label_taxonomy=AMOS22`。
4. 上传 FLARE 原图 + FLARE label，选择 `label_taxonomy=FLARE22`。
5. 检查 CT、reference label、prediction 的 shape 是否一致。
6. 检查 spacing / affine 是否明显不一致。
7. 检查 reference label 和 prediction label 的 unique IDs。
8. 检查 `label_taxonomy`、`remap_applied`、`remap_source` 是否符合预期。
9. 再判断 Dice 是否代表真实模型质量。

## 验证口径

### AMOS label

选择：

```text
label_taxonomy=AMOS22
```

预期：

```text
remap_applied=false
Label 6=肝脏
Label 9=下腔静脉
per-label Dice 不应因 ID 错位大面积为 0
```

### FLARE label

选择：

```text
label_taxonomy=FLARE22
```

预期：

```text
remap_applied=true
remap_source=FLARE22
validation 按当前模型标签体系解释
```

### auto 模式

适合作为保底和演示默认值；正式质量基线建议使用显式 taxonomy。

## 与量化功能的关系

影像量化分析直接读取前端已加载的预测 mask，根据当前 `modelLabels` 解释 label ID。它不改变 validation/remap 流程。

但如果预测 mask 或 label taxonomy 本身解释错位，量化结果的器官名称也会跟着错。因此正式报告展示最好建立在明确的 taxonomy 和可靠分割结果之上。
