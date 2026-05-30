# 近三轮分割推理滚动记录

> 本文档按时间滚动覆写，只保留最近三轮成功或具备诊断价值的推理数据。历史完整记录见 `SEGMENTATION_EXPERIMENT_COMPARISON.md`。

最近更新：2026-05-31

## 第 1 轮（最新）— 服务器 AMOS 0117 validation 异常

| 项目 | 值 |
|---|---|
| job_id | `5d8f5eee7b75` |
| 日期 | 2026-05-30 |
| 病例 | AMOS 0117 |
| 运行位置 | Ubuntu 服务器，5GPU / 5-fold soft ensemble |
| 前端接入 | Windows GUI 通过校园网 API endpoint |
| 模式 | `real-nnunetv2` |
| 缓存 | 否 |
| 推理配置 | quality / tile_step=0.5 / TTA on |
| 总耗时 | `586.453s`（约 9分46秒） |
| 主要阶段 | `server_fold_predict=449.5s`, `server_ensemble=131.116s`, `validation=5.51s` |
| 结果大小 | `141986 bytes` |
| remap_applied | `true` |
| remap_source | `FLARE22` |

**验证结果：**

| 指标 | 值 | 状态 |
|---|---:|---|
| 平均 Dice | `0.076015` | 未通过 |
| 最低 Dice | `0.000000` | 未通过 |
| 前景 Dice | `0.979808` | 前景总体高度重合 |
| validation status | `review` | 建议人工复核 |

**结论：** 服务器推理、soft ensemble、下载和 GUI 回填链路已跑通。该轮 Dice 异常不应直接解读为模型完全失败，因为 foreground Dice 很高，但报告显示 AMOS 标签被自动当作 FLARE22 执行 remap。下一步需用显式 `label_taxonomy=AMOS22` 复跑，并确认 `remap_applied=false`。

---

## 第 2 轮 — 服务器 FLARE22 + 自动 remap 在线验证

| 项目 | 值 |
|---|---|
| 日期 | 2026-05-30 |
| 病例 | FLARE22 |
| 运行位置 | Ubuntu 服务器，5GPU / 5-fold soft ensemble |
| 前端接入 | Windows GUI 通过校园网 API endpoint |
| 模式 | `real-nnunetv2` |
| 缓存 | 否 |
| 推理配置 | quality / tile_step=0.5 / TTA on |
| 总耗时 | 约 `3分48秒` |
| 瓶颈阶段 | 服务器 5-fold 推理约 `2分55.3秒` |
| 结果大小 | 约 `117.2 KB` |
| remap | FLARE22 → 当前 AMOS 模型 |

**验证结果（自动重映射后）：**

| 指标 | 值 | 状态 |
|---|---:|---|
| 平均 Dice | 约 `0.891` | 可用，仍需复核最低标签 |
| 最低 Dice | 约 `0.657` | 低于 0.70，建议人工复核 |
| 前景 Dice | 约 `0.951` | 前景重合良好 |

**结论：** FLARE 服务器轮次说明服务器模式下 5-fold 推理、soft ensemble、自动 taxonomy remap、validation 和前端回填均可工作。该结果是服务器链路跑通证据，但仍应与 AMOS 原生标签质量基线分开解释。

---

## 第 3 轮 — FLARE22 + 自动 Taxonomy Remap 在线验证（本地/既有基线）

| 项目 | 值 |
|---|---|
| job_id | `a717dacf42d3` |
| 日期 | 2026-05-28 |
| 病例 | FLARE22 Tr 0009 |
| 标签文件 | 已上传（自动 taxonomy remap） |
| 模式 | real-nnunetv2 |
| 缓存 | 否 |
| 推理配置 | quality / tile_step=0.5 / TTA on |
| remap_applied | True |
| remap_source | FLARE22 |

**验证结果（自动重映射后）：**

| 指标 | 值 | 阈值 | 状态 |
|---|---:|---:|---|
| 平均 Dice | `0.926` | ≥ 0.85 | 通过 |
| 验证状态 | passed | — | 自动验证通过 |

**结论：** 自动 taxonomy remap 上线后，FLARE22 标签在线验证从 mean_dice=0.073 提升到 0.926。后端自动检测 FLARE22 数据集并按器官名重映射标签 ID，无需手动干预。跨数据集在线验证链路正式打通。

---

## 近三轮趋势

| 维度 | 第 1 轮（服务器 AMOS 异常） | 第 2 轮（服务器 FLARE） | 第 3 轮（FLARE 自动 remap 基线） |
|---|---|---|---|
| 耗时 | 586s | 约 228s | 约 220s |
| 结果大小 | 138.7 KB | 117.2 KB | 约 118 KB |
| 验证状态 | review | review / 可用 | passed |
| mean_dice | 0.076 | 约 0.891 | 0.926 |
| foreground_dice | 0.980 | 约 0.951 | 未记录 |
| 核心问题 | AMOS 可能被误判为 FLARE22 并错误 remap | 最低标签仍需人工复核 | 已解决 FLARE taxonomy 错位 |

---

## 待解决问题

### 问题 1：AMOS 原生标签可能被误判为 FLARE22

**现状：** 服务器 AMOS 轮次出现 `foreground_dice=0.979808` 但 `mean_dice=0.076015`，同时报告记录 `remap_applied=true`、`remap_source=FLARE22`。这更像 label taxonomy 误判，而不是模型完全失败。

**行动：**

- 增加显式 `label_taxonomy=auto|AMOS22|FLARE22`。
- AMOS22：禁止 FLARE remap，直接按当前 AMOS checkpoint label ID 验证。
- FLARE22：强制 FLARE22 → AMOS22 remap。
- auto：保留当前检测逻辑，但 message 必须明确检测来源和 remap 状态。

### 问题 2：server 模式 gating 仍需收口

**现状：** `/api/models` 默认仍可能显示 `runtime_target=local` 并报告本地 Windows nnUNet 文件缺失；服务器云端推理创建 job 时不应依赖本地 `dataset.json/plans/checkpoint/python.exe`。

**行动：**

- `runtime_target=server` 只检查 server runtime 必需路径。
- `runtime_target=local` 才检查本地 nnUNet 文件。
- 保留 `/api/models` 和 job summary 中的最终 runtime target，避免误读当前运行位置。

### 问题 3：标签文件传输和缓存 validation 语义已收口

**现状：** 标签上传入口、FormData `label_file`、后端保存路径和在线 validation 已有回归覆盖；缓存命中只复用预测 NIfTI，不复用旧 validation。

**行动：** 后续观察改为检查 job summary、`label_path`、`validation_summary.json` 和 validation 结果，不再依赖控制台文件名日志。
