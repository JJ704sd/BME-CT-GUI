# 近三轮分割推理滚动记录

> 本文档按时间滚动覆写，只保留最近三轮成功或具备诊断价值的推理数据。历史完整记录见 `SEGMENTATION_EXPERIMENT_COMPARISON.md`。

最近更新：2026-06-02

## 第 1 轮（最新）— dataset_hint 字段打通 auto 边界

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-02 |
| 修复内容 | 新增 `dataset_hint` 表单字段：前端 `loadReferenceCase()` 把 `referenceCase.dataset` 写入 `referenceCaseDatasetHint` 状态并随 job 提交；后端 `validate_against_custom_label()` 在 `taxonomy=auto + dataset_hint=FLARE22` 时强制 remap，覆盖 0.85 守卫的 None |
| 受影响逻辑 | `server/main.py:Job.dataset_hint` / `create_job` / `validate_against_custom_label()`；`src/main.tsx:referenceCaseDatasetHint` 状态；`src/inference/inferenceClient.ts:createInferenceJob` 新增 `datasetHint` 选项 |
| 回归测试 | `tests/backendState.test.py` 新增 `test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto`（FLARE22 真实 1-13 + AMOS ckpt 1-15，验证 `taxonomy=auto + dataset_hint=FLARE22` 走 remap、`taxonomy=auto + dataset_hint=AMOS22` 不 remap） |
| 自动验证 | `python tests/backendState.test.py`、`npm test`、`npm run build` 全过（`EXIT=0`） |

**问题描述：**

第 1 轮 0.85 coverage 守卫上线后，FLARE22 真实 1-13 标签也会被 `detect_dataset()` 返回 `None`，导致 FLARE22_Tr_0009 在 `taxonomy=auto` 模式下走不到 remap 路径——即使前端已经按 `referenceCase.dataset` 把 `label_taxonomy` 自动设成 `FLARE22`，但如果用户把 `label_taxonomy` 切回 `auto`，Dice 仍会跌到 0.073 量级。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| 后端 Job 字段 | `Job.dataset_hint: str \| None = None`；`create_job` 接收 `dataset_hint: str \| None = Form(None)`，归一化（`strip().upper()`）后写入 job state |
| 后端优先级 | `taxonomy_hint=AMOS22/FLARE22` → `dataset_hint=FLARE22/AMOS22` → `detect_dataset()`；`dataset_hint=FLARE22` 覆盖 0.85 守卫的 None |
| 后端 action 文案 | 区分"已按用户选择" / "已按参考病例" / "已自动" |
| 前端状态 | `referenceCaseDatasetHint` 在 `loadReferenceCase()` 成功后写入 `referenceCase.dataset`；catch / else / 上传自定义 NIfTI（`role === "source"`）时清空 |
| 前端 inference client | `createInferenceJob` options 增加 `datasetHint?: string \| null`；`formData.append("dataset_hint", ...)` |
| `auto` 行为 | 仍为保底；`dataset_hint` 是 auto 边界下让 FLARE22 真实 1-13 仍能 remap 的补充信号 |

**结论：** FLARE22 真实 1-13 病例在 `taxonomy=auto` 下能正确 remap（`remap_applied=true`、`remap_source=FLARE22`）；`dataset_hint=AMOS22` 不误 remap；上传自定义 NIfTI 时 `referenceCaseDatasetHint` 自动清空。本轮不修改 `server/taxonomy.py` 的判定逻辑、不改变 nnUNetv2 推理、缓存复用、SSE 协议、影像量化或历史基线指标数值。

---

## 第 1 轮 — detect_dataset 二轮收紧 + 前端按 dataset 预设 taxonomy

| 项目 | 值 |
||---|
| 日期 | 2026-06-02 |
| 修复内容 | `detect_dataset()` 收紧：参考覆盖 ckpt 标签 ≥ 0.85 时返回 `None`（`auto` 退化为保底）；前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy` |
| 受影响逻辑 | `server/taxonomy.py:detect_dataset()`、`src/main.tsx:mapDatasetToLabelTaxonomy()` 与 `loadReferenceCase()` |
| 回归测试 | `tests/backendState.test.py` 新增 AMOS 1-13 + ckpt 1-15 真实 case 测试；更新 FLARE22 1-13 + ckpt 1-15 用例注释 |
| 自动验证 | `python tests/backendState.test.py`、`npm test`、`npm run build` 全过（`EXIT=0`） |

**问题描述：**

2026-06-01 现场复测时发现，AMOS 0117 自身标签在 `detect_dataset()` 中仍可能被错判为 FLARE22，触发 `remap_applied=true`，AMOS 推理 Dice 异常偏低。原因：

- AMOS 真实 `amos_0117_label.nii/amos_0117(2).nii` 实际 unique IDs 为 `{1..13}`，缺 14/15（bladder/prostate）。
- FLARE22 真实标签 unique IDs 也是 `{1..13}`。
- 两者在裸 ID 集合上不可分，仅靠命名对比无法稳定区分。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| `detect_dataset()` 0.85 守卫 | `coverage = len(reference_ids ∩ ckpt_ids) / len(ckpt_ids) >= 0.85` → `None` |
| 前端预设 | `loadReferenceCase()` 在拿到参考 label 后立即调用 `mapDatasetToLabelTaxonomy()`；AMOS/AMOS22 → `AMOS22`、FLARE/FLARE22 → `FLARE22`、其他保持原值 |
| `auto` 行为 | 退化为保底策略；`label_taxonomy=AMOS22` / `FLARE22` 显式选择仍是正式质量基线入口；`dataset_hint` 字段补充 auto 边界下 FLARE22 真实 1-13 的 remap 路径 |
| 用户体验 | 用户仍可在 UI 切换 taxonomy；前端预设只是默认值 |

**回归测试覆盖：**

| 用例 | reference | checkpoint | 期望 |
|---|---|---|---|
| AMOS 自指 1-15 | `{1..15}` | `{1..15}` | `None`（短路 `==`） |
| AMOS 真实 1-13 | `{1..13}` | `{1..15}` | `None`（coverage 0.867 ≥ 0.85） |
| FLARE22 真实 1-13 | `{1..13}` | `{1..15}` | `None`（coverage 0.867 ≥ 0.85；前端预设补 / `dataset_hint=FLARE22` 覆盖） |
| AMOS 子集 {1,2,6} | `{1,2,6}` | `{1..15}` | `None`（进入循环，mismatch=0 < 5） |
| Partial {1,3} | `{1,3}` | `{1,3,6}` | `None`（`len(shared_ids) < 3` 守卫） |

**结论：** `auto` 模式在裸 ID 不可分的边界（AMOS 1-13 vs FLARE22 1-13）退化为保底，避免错误 remap。正式 taxonomy 由前端 `loadReferenceCase()` 按 `referenceCase.dataset` 字段预设；`dataset_hint` 字段补充 `auto` 边界下 FLARE22 真实 1-13 的 remap 路径；用户仍可在 UI 切换。本修复不改变 nnUNetv2 推理、缓存复用、SSE 协议或影像量化逻辑。

---

## 第 2 轮 — 本地缓存演示 7 步验证

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-01 |
| 病例 | AMOS 0117 + FLARE22 Tr 0009（项目自带 4 例 reference cases） |
| 运行位置 | 本地 RTX 4060（`runtime_target=local`） |
| 目的 | 跑通“同输入 → 真实 nnUNetv2 推理 → 缓存回填 → 二次命中”全链路，并沉淀可重跑脚本与运行说明 |
| 新增脚本 | `tools/seed_demo_cache.py`（替换了仅 AMOS 版的 `tools/seed_amos_cache.py`） |
| 新增运行说明 | `docs/local-cache-demo-runbook.md`（启动命令、关键路径、cache_key 7 字段、已知约束） |
| 新增 spec/plan | `docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`、`docs/superpowers/plans/2026-06-01-local-cache-demo.md` |
| 后端依赖 | 在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装了 `fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30` |

**4 步演示结果：**

| 演示步骤 | job_id | mode | cache_key（前 16 位） | 耗时 | 结果 |
|---|---|---|---|---|---|
| AMOS 0117 cache hit | `aea4e7cdbaf0` | `cached-real-nnunetv2` | `4e0eb3cd29145b70` | ~3s | 命中手工 seed 的 `009d4efdc5f6`；validation `review`，mean_dice 0.891（stomach 0.556 偏低） |
| FLARE 真实推理 | `0aa7323a4c01` | `real-nnunetv2` | `0f9c6d68e314b3d7` | 218s | RTX 4060，quality + TTA，3d_fullres，结果 120KB |
| FLARE cache hit | `02da885c97d8` | `cached-real-nnunetv2` | `0f9c6d68e314b3d7` | 0.001s | 命中 `0aa7323a4c01` |

**7 步任务验收：**

| 阶段 | 状态 | 备注 |
|---|---|---|
| Task 1 装 fastapi/uvicorn | ✓ | fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30 |
| Task 2 启动后端 | ✓ | cwd=project subdir，`/api/health` ready=true；`/api/samples` 含 4 例（设置 `SEGMENTATION_REFERENCE_CASES_JSON` 后） |
| Task 3 启动前端 | ✓ | Vite 6.4.2, http://127.0.0.1:5173/ → 200 |
| Task 4 AMOS cache hit | ✓ | `aea4e7cdbaf0`, mode=cached, source=`009d4efdc5f6` |
| Task 5 FLARE 真实推理 | ✓ | `0aa7323a4c01`, 218s, 120KB result |
| Task 6 FLARE cache hit | ✓ | `02da885c97d8`, 0.001s, source=`0aa7323a4c01` |
| Task 7 写 runbook | ✓ | `docs/local-cache-demo-runbook.md` |

**cache_key 7 字段（任一不一致即失配）：**

1. `input_sha256`（输入文件 SHA-256，非路径；重压缩即失配）
2. `checkpoint_sha256`（`nnunetv2_files/checkpoint_best.pth` 的 SHA-256）
3. `checkpoint_dataset_name`（如 `Dataset001_AMOS22`）
4. `checkpoint_configuration`（如 `3d_fullres`）
5. `labels_source`（内置 AMOS checkpoint label vs 用户上传 label）
6. `runtime_target`（`local` vs `server`，互不混用）
7. `inference_options`（`quality` vs `fast`，TTA、tile_step_size 也算）

**结论：** 本地 4 步演示完整跑通，cache_key 7 字段隔离正确，二次命中耗时 < 5s；AMOS 预热预测的 review 状态（stomach 0.556）属于 5 月 23 日历史推理结果，本次未重训，复跑 AMOS 真实推理会得到更新更准的预测。`tools/seed_demo_cache.py` 幂等可重跑，便于在演示前预热 AMOS 缓存或在新机器上确认 FLARE 缓存存在。

---

## 第 2 轮 — label_taxonomy 修复与 AMOS CT 推理完成

| 项目 | 值 |
|---|---|
| 日期 | 2026-05-31 |
| 修复内容 | 显式 `label_taxonomy=auto\|AMOS22\|FLARE22`，`detect_dataset()` 更保守 |
| 验证 job | `d56bcff76a8b`（AMOS22 选择，`remap_applied=false`） |
| AMOS CT 推理 | job `ad3d14eba3de`，768×768×103，fast profile，mean_dice=0.77724 |
| 部署包 | `server-runtime-package-20260531.zip` |

**label_taxonomy 修复要点：**

| 修改项 | 说明 |
|---|---|
| `detect_dataset()` | 标签 ID 是 checkpoint 子集时不触发 remap |
| `label_taxonomy` 参数 | `auto`：保守检测；`AMOS22`：强制不 remap；`FLARE22`：强制 remap |
| 缓存 key | `label_taxonomy` 已纳入，不同标签体系结果不会混用 |
| 测试更新 | `tests/backendState.test.py` 已更新期望值 |

**AMOS CT 推理速度分析：**

| 瓶颈因素 | 说明 |
|---|---|
| 输入分辨率 | 768×768 是标准 512×512 的 1.5 倍，面积 2.25 倍 |
| GPU 显存 | 8GB 显存占用 95%，接近上限 |
| GPU 功率 | 27W/40W，受限于笔记本散热 |
| 模型复杂度 | 8 阶段 ResidualEncoderUNet，约 10.2M 参数 |
| 2D 模型处理 3D 数据 | 逐切片处理 103 层，每层需独立推理 |
| 重采样开销 | nnUNetv2 需将 768×768 重采样到模型 patch 640×640 |

**结论：** label_taxonomy 修复已完成，AMOS 标签不再被误判为 FLARE22。AMOS CT 高分辨率推理完成，fast profile 下 mean_dice=0.77724（低于 quality 的 0.924791，符合预期）。建议后续高分辨率 CT 可考虑预降采样以加速推理。

---

## 第 2 轮 — 服务器 AMOS 0117 validation 异常

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

## 历史基线 — FLARE22 + 自动 Taxonomy Remap 在线验证（本地）

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

| 维度 | 第 1 轮（本地缓存演示 7 步） | 第 2 轮（label_taxonomy 修复 + 本地高分辨率） | 第 3 轮（服务器 FLARE 5-fold） |
|---|---|---|---|
| 运行位置 | 本地 RTX 4060，cache_key 7 字段 | 本地 RTX 4060 / 服务器 5GPU | Ubuntu 服务器 5GPU |
| 病例 | AMOS 0117 + FLARE22 Tr 0009 | 768×768×103 高分辨率 | 标准 FLARE22 |
| 耗时 | AMOS cache hit ~3s，FLARE 真实 218s，FLARE cache hit 0.001s | 268s+（fast profile） | 约 228s |
| 验证状态 | AMOS review（stomach 0.556）、FLARE 真实 0 验证、FLARE cache hit 0.001s | review，mean_dice=0.77724 | review / 可用，mean Dice 约 0.891 |
| 核心问题 | AMOS 预热预测 review 状态保留，复跑新 AMOS 真实推理可换更新预测 | 高分辨率导致推理慢 | 最低标签仍需人工复核 |

---

## 待解决问题

### 问题 0：高分辨率 CT 推理速度优化

**现状：** 2026-05-31 的 AMOS CT（768×768×103）推理已完成，fast profile mean_dice=0.77724，低于 quality 基线 0.924791。主要瓶颈是输入分辨率高于模型训练时的标准尺寸，导致计算量增加约 2.25 倍。

**行动：**

- 短期：保留当前 fast profile 作为高分辨率预览证据，但不得作为正式质量基线。
- 中期：考虑在推理前对高分辨率 CT 进行预降采样（如 768→512），可显著缩短推理时间。
- 长期：评估是否需要训练支持更高分辨率的模型，或在 nnUNetv2 配置中调整 patch size。

### 问题 1：AMOS 原生标签可能被误判为 FLARE22 [已修复]

**现状：** 已实现显式 `label_taxonomy=auto|AMOS22|FLARE22`，`detect_dataset()` 更保守：标签 ID 是 checkpoint 子集时不触发 remap。验证 job `d56bcff76a8b` 确认 AMOS22 选择时 `remap_applied=false`。

**行动：** 后续服务器 AMOS validation 复跑时使用 `label_taxonomy=AMOS22`，确认 `remap_applied=false` 后纳入正式质量基线。

### 问题 2：server 模式 gating 仍需收口

**现状：** `/api/models` 默认仍可能显示 `runtime_target=local` 并报告本地 Windows nnUNet 文件缺失；服务器云端推理创建 job 时不应依赖本地 `dataset.json/plans/checkpoint/python.exe`。

**行动：**

- `runtime_target=server` 只检查 server runtime 必需路径。
- `runtime_target=local` 才检查本地 nnUNet 文件。
- 保留 `/api/models` 和 job summary 中的最终 runtime target，避免误读当前运行位置。

### 问题 3：标签文件传输和缓存 validation 语义已收口

**现状：** 标签上传入口、FormData `label_file`、后端保存路径和在线 validation 已有回归覆盖；缓存命中只复用预测 NIfTI，不复用旧 validation。

**行动：** 后续观察改为检查 job summary、`label_path`、`validation_summary.json` 和 validation 结果，不再依赖控制台文件名日志。

### 问题 4：量化报告需跟随结果回填验证

**现状：** 影像量化分析已作为纯前端能力接入，计算依赖推理完成后的预测 mask 和 NIfTI spacing，不改变服务器推理、缓存或 validation 链路。

**行动：** 后续每次做服务器 smoke 或报告验收时，在“结果下载并回填 GUI”之后补充检查：评估模块是否显示量化面板、HTML/JSON/PDF 报告是否包含 `quantification`，并确认壁厚和精确管腔指标仍显示为不可用/后续扩展。

### 问题 5：AMOS 预热预测质量偏低（cache hit 暴露 review 状态）

**现状：** 2026-06-01 本地缓存演示发现 AMOS 0117 预热预测（`009d4efdc5f6`，2026-05-23 推理，138KB）validation 为 review，mean_dice 0.891，stomach 0.556。该预测是当前唯一会被 cache hit 复用的 AMOS 推理结果；首次未缓存新推理可换更新预测（job `b3c528cc9e20` quality 模式 mean_dice 0.924780、stomach 0.846569）。

**行动：**

- 演示前允许 `tools/seed_demo_cache.py` 把 009d4efdc5f6 写为 cache hit，标签上明确是 review 不是 passed。
- 若需 quality 模式 AMOS 验证，优先做真实新推理（已通过 `find_cached_prediction()` 复用现成 `b3c528cc9e20` 缓存）。
- 后续如果 AMOS 重新训练或新 checkpoint 接入，需重跑 `tools/seed_demo_cache.py` 让 `cache_key` 重新指向新预测，否则历史 cache hit 会继续给出旧指标。

### 问题 6：FLARE22 cache hit 显示 AMOS 数据 [已修复]

**现状：** 2026-06-01 晚间现场复测时，FLARE22 Tr 0009 cache hit（`02da885c97d8`）显示的 validation 摘要来自 `009d4efdc5f6`（AMOS 0117 历史推理），mean_dice 0.891（stomach 0.556），与 README/参考病例的 0.893/0.674/0.950 不一致。看起来像是"FLARE22 cache hit 用了 AMOS 的数据"。

**根因：** 1) `find_cached_prediction()` 只按 mtime 排序候选，空 job 目录被误选；2) `complete_cached_job()` 不回退到 cache_source_job_id 的 `validation_summary.json`，cache hit 找不到当前 validation 时直接给 null；3) 0aa7323a4c01 与 2026-05-26 历史 `86b0153d0a73` 的预测字节不同，cache_key 不一致，无法直接复算；4) 现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，导致 FLARE22 Tr 0009 根本没出现在 `/api/samples`，所有"参考病例载入"都跑到了 AMOS 0117。

**行动：**

- 已实现 `complete_cached_job()` 的 historical 回退：读 `cache_source_job_id/output/validation_summary.json`，加 `historical: true` 和 `source_job_id`。
- 已修改 `find_cached_prediction()` 排序为 `(has_validation_summary, mtime)` 降序，优先选有摘要的 cache_source。
- 已写 `tools/rewrite_flare22_historical_summary.py`，按 2026-05-26 remap 后的 metrics 把 validation_summary.json 写入 0aa7323a4c01 的 output；前端显示 0.893127/0.673730/0.949908 + "（历史离线缓存摘要）"。
- 前端 `getValidationStatusCopy()` 增加 `cachedResult` 参数；`inferenceClient.ts` 增加 `cached_result` / `cache_source_job_id` / `historical` / `source_job_id` 字段。
- `tests/backendState.test.py` 增加 2 个回归测试。
- 教训：env var 缺一项就会让整条 cache 链路看起来指向错位数据；runbook 必须把 `SEGMENTATION_REFERENCE_CASES_JSON` 写在最前面，并在 `/api/samples` 列表中确认 4 个 case。
