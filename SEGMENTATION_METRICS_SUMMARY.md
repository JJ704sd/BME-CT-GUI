# 分割指标汇总

本文档用于登记训练权重对应的分割指标。每次更换或训练出新权重后，使用同一套输入、参考标签和命令生成 JSON 与 Markdown，便于横向比较。

## 当前运行状态

2026-06-06 已完成：
- **演示当天收口 + B1-B4 演示关键 bug 修复**：
  - **B1 SSE 进度回退**：`src/main.tsx` 的 `inferenceTimeline` 进度追踪以 `event.percent` 存在为强信号；心跳事件没有 `percent` 字段时不再覆盖当前进度。**2026-06-06 `76bb1ff` 补完**：6-06 `23e0c4d` 虚标；同日 `76bb1ff` 真正实现 `parsed.heartbeat && parsed.progress === 0` 守护。
  - **B2 取消后残留进度**：后端 `cancel_job()` 在 `EventSourceHandler` 关闭后写取消状态；前端不把 cancel 后的心跳误显示为"还在跑"。**2026-06-06 `76bb1ff` 补完**：6-06 `23e0c4d` 虚标；同日 `76bb1ff` 真正实现 `inferenceStatusRef` 镜像 + SSE onmessage 入口 cancelled 早退。
  - **B3 后端模型状态对外可读**：`/api/health` 的 `model_state` 字段从内部变量提升为可被 GUI 状态栏读取的稳定 JSON 字段（`status` / `checkpoint_sha256` / `mode` / `missing`）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。**2026-06-06 真实完成**。
  - **B4 SSE 基础异常重试**：`createInferenceEventSource` 暴露 `onretry` / `retryCount` 字段；单次断连后自动退避重连（200ms→2s 指数退避，最多 3 次）。**2026-06-06 `76bb1ff` 补完**：6-06 `23e0c4d` 虚标；同日 `76bb1ff` 真正抽出 `src/inference/createInferenceEventSource.ts` 工具并接入。
  - **演示启动脚本化**：`tools/start_local_demo.py` 一行启动：setenv + spawn backend/frontend + 启动后采样 `/api/samples`（最多 15s）校验 4 例参考病例（AMOS 0117 / FLARE22 Tr 0009 / WORD / AbdomenCT-1K）已就绪 + 失败时打印 runbook 回退命令。配套卡片见 `docs/demo-day-checklist.md`。
  - **server mode gating 6 路径修复**：`runtime_target=server` 创建 job 时只检查 6 个 `SEGMENTATION_SERVER_*` 路径（`server_evaluate_full.py` / `server_dataset.json` / `server_nnunet_raw` / `server_nnunet_preprocessed` / `server_nnunet_results` / `server_output_root`），不被本地 Windows nnUNet 文件缺失阻断；`runtime_target=local` 才检查本地 4 文件。`tests/backendState.test.py` 新增 3 个守护测试。
  - **AMOS 0117 演示口径（2026-06-05 决策，6-06 落地）**：cache hit `aea4e7cdbaf0` 命中的是 2026-05-23 quality profile 真实推理 `009d4efdc5f6`（review 状态，stomach Dice 0.556、mean_dice 0.891）；stomach 0.556 是数据本身硬骨头。决策：接受现状，不复跑 AMOS 0117。本文件所有 AMOS 基线数值（`b3c528cc9e20` mean Dice 0.924780、`27216eb73220` mean Dice 0.924791、6 类指标 in `2d477d8bbd7d` cache hit 等）保持不变。
- **本轮不修改**：`surface_distances()` 2 EDT 实现、6 类指标计算路径或历史 baseline 数值；AMOS quality / FLARE22 自动 remap / FLARE22 离线 remap 三套历史基线不变。

2026-06-05 已完成：
- **HTML 报告临床报告风格重构（第二轮美化）**：`src/report/exportReport.ts` 从"卡片式仪表板"重塑为"临床评估报告"。新增 7 个 CSS 块：`.cover` 封面页（题图条 + 报告编号 + 主副标题 + 数据集/病例/生成时间三列）、`.exec-summary` 执行摘要（通过 / 关注点 / 建议三栏）、`.toc` 目录（§1-§8 锚点导航）、`.formula-tip` 公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、`.dist-chart` 严重度分布图（高/中/低 bar chart）、`.table-caption` 表格标题、`.footnotes` 脚注；新增 3 个工具函数 `distributionChartHtml()` / `severityBuckets()` / `formulaTips()`；正文模板按 §1 报告概览 / §2 摘要 / §3 数据集 / §4 器官 / §5 体素 / §6 距离 / §7 关键发现 / §8 附录 8 段章节编号排版；字体改为 Source Han Serif / Songti SC + JetBrains Mono；@media print 改为 A4 + 顶部 caseId + 底部 page X of Y。本轮不动 `surface_distances()`、AMOS quality / FLARE22 自动 remap / FLARE22 离线 remap 三套历史基线或 6 类指标计算路径。
- **不变量回归保护**：本轮不动 `src/inference/inferenceClient.ts` 的 `ValidationSummary` / `LabelMetric` 白名单；与 2026-06-04 第一轮美化的所有功能（remap 警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条、aiFindings 严重度排序、器官列表折叠、列固定/排序）兼容并叠加。

2026-06-04 已完成：
- **HTML 报告第一轮美化（视觉层 + 信息层）**：`src/report/exportReport.ts` 从"工程 dump"提升为"卡片式仪表板"。视觉层：色阶图例、Header 渐变、3 个 metric group 加组标题图标、aiFindings 严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定 + 列点击排序、@media print A4 页眉页码。信息层：remap_applied 顶部警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条。`src/main.tsx:handleExport` 透传 `validation.remap_applied` / `taxonomy_match` / `dataset_hint` / `historical` / `label_taxonomy`。`tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class。
- **本轮不修改 `surface_distances()` 2 EDT 实现、6 类指标计算路径或历史 baseline 数值**；6 类指标在 AMOS quality 缓存命中（`2d477d8bbd7d` / `9fd0fdc39960` / `096e5b8349df`）上的具体数值仍为 mean Dice 0.891327、mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm。

2026-06-03 已完成：
- **质量评估指标扩展**：把 quality 评估报告补齐到 6 类医学影像主流指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD）。`server/main.py` 新增 `surface_distances()`（1 crop + 2 EDT/label），把单 label 的 `distance_transform_edt` 调用从 6 次合并到 2 次；`validation_summary.json` 增补 12 个新字段（pixel_accuracy 4 项 + HD/HD95/ASD 9 项 + surface_distance_unit + spacing）；`src/inference/inferenceClient.ts` 在 `ValidationSummary` / `LabelMetric` 增补对应字段并加入 `normalizeValidation()` 白名单；`src/report/exportReport.ts` 报告模板新增 3 个 metric group（区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD）和 4 个逐标签列（像素准确率、ASD (mm)、HD95 (mm)、HD (mm)）。AMOS 0117 quality 缓存命中实测：validation 阶段从 38.86s 降到 16.78s（约 2.3× 加速）。
- **回归测试**：`tests/backendState.test.py` 新增 `test_surface_distances_matches_legacy_individual_functions`（4 shape × 8 场景 1e-9 精度对照）、`test_surface_distances_uses_fewer_distance_transforms_than_legacy`（patch `scipy.ndimage.distance_transform_edt` 计数恒为 2）、`test_compute_label_metrics_with_surface_distances_faster_than_legacy`（wall-time 加速比 ≥30% 断言）；`tests/imagingLogic.test.ts` 新增全部新 metric 字段的 source-grep 约束和 `parseInferenceEvent()` complete 事件解析值测试。
- **基线数值不变**：本轮不修改 AMOS `quality` profile `b3c528cc9e20`（mean Dice 0.924780）、FLARE22 自动 remap `a717dacf42d3`（mean Dice 0.926）、FLARE22 离线 remap `86b0153d0a73`（mean Dice 0.893127）三套历史基线；新指标在 AMOS quality 缓存命中（如 `2d477d8bbd7d` / `9fd0fdc39960` / `096e5b8349df`）上的具体数值为 mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm。

2026-06-02 已完成：
- `detect_dataset()` 二轮收紧：参考覆盖 ckpt 标签 ≥ 0.85 时直接返回 `None`，避免 AMOS 1-13 真实数据被错判为 FLARE22。
- 前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy`：AMOS → `AMOS22`、FLARE22 → `FLARE22`、其他保持原值。`auto` 退化为保底策略。
- `dataset_hint` 字段打通 auto 边界：0.85 守卫下 FLARE22 真实 1-13 也会被返回 `None`，因此新增 `dataset_hint` 表单字段——前端在 `loadReferenceCase()` 成功后把 `referenceCase.dataset` 写入 `referenceCaseDatasetHint` 状态并随 job 提交，后端 `validate_against_custom_label()` 在 `taxonomy=auto + dataset_hint=FLARE22` 时强制 remap，覆盖 0.85 守卫的 None；上传自定义 NIfTI 时前端清空 `referenceCaseDatasetHint` 避免错误继承。
- `tests/backendState.test.py` 新增 AMOS 1-13 + ckpt 1-15 真实 case 测试、`test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto`，更新 FLARE22 1-13 + ckpt 1-15 用例注释。
- 本文档既有 AMOS quality 基线 `b3c528cc9e20`（mean_dice 0.924780）和新权重首跑 `27216eb73220`（mean_dice 0.924791）保持不变；2026-06-02 修复仅影响 `auto` 模式下的 taxonomy 判定逻辑与 `auto` 边界下 FLARE22 的 remap 路径，不改变已记录的任何指标数值。

2026-06-01 已完成：
- 本地缓存演示 7 步：AMOS 0117 cache hit、FLARE22 Tr 0009 真实推理、FLARE22 cache hit
- 新增 `tools/seed_demo_cache.py`（幂等可重跑）和 `docs/local-cache-demo-runbook.md`
- 新增 spec/plan：`docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`、`docs/superpowers/plans/2026-06-01-local-cache-demo.md`
- 在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装了 `fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30`

2026-05-31 已完成：
- 显式 `label_taxonomy=auto|AMOS22|FLARE22` 功能，修复了 AMOS 标签被误判为 FLARE22 的问题
- AMOS CT 高分辨率在线推理（768×768×103，fast profile，mean_dice=0.77724）
- 新部署包 `server-runtime-package-20260531.zip` 已创建

当前进行中：
- 高分辨率 CT 推理优化评估（预降采样方案）
- 服务器 AMOS/FLARE 显式 taxonomy 复跑验证 `remap_applied` 状态（AMOS 0117 演示口径决策后已不再复跑 AMOS 0117，但仍需在新服务器窗口上复跑确认 `remap_applied=false` 后纳入正式基线）

2026-06-11 增量：

- **启动操作手册独立化**：把 `tools/start_local_demo.py` 的"线下实时启动"操作抽成独立文档 [`docs/quickstart-launch-guide.md`](./docs/quickstart-launch-guide.md)，与 `docs/demo-day-checklist.md`（演示当天）和 `docs/local-cache-demo-runbook.md`（cache demo 7 步复跑）形成三档文档分工。任何时候要把 GUI 起来看 → 走 quickstart；演示当天 → 走 checklist；cache demo → 走 runbook。
- **文档巡检同步**：9 份核心文档全部补一行 quickstart 索引；中文主体仍合格。
- **新 planning 主题**：`.planning/2026-06-11-launch-guide-and-doc-sync/` 4 份文档落地。
- 本轮不动 `surface_distances()` 2 EDT 实现、6 类指标计算路径或任何历史 baseline 数值；AMOS quality / FLARE22 自动 remap / FLARE22 离线 remap 三套历史基线（`b3c528cc9e20` mean Dice 0.924780、`a717dacf42d3` mean Dice 0.926、`86b0153d0a73` mean Dice 0.893127）保持不变。

2026-06-13 增量 — 文档一致性巡检 + 提交包打包：

- **9 份 md "4 端点 → 1 端点"措辞统一**：`tools/start_local_demo.py` 实际只采样 `/api/samples`（最多 15s）校验 4 例参考病例（AMOS 0117 / FLARE22 Tr 0009 / WORD / AbdomenCT-1K）已就绪；6-06 起的"4 端点 smoke test"措辞漂移 7 天没人发现。lesson：事实声明必须靠 source-grep 守护。
- **评审在任意电脑极简运行手册**：新增 [`RUN_ON_OTHER_PC.md`](./RUN_ON_OTHER_PC.md)（4 章 + 6 个 FAQ），面向压缩包评审场景；主仓库 5 个本地 nnUNet 路径加 env var override（`SEGMENTATION_NNUNET_RAW` / `_PREPROCESSED` / `_RESULTS` / `_PYTHON` / `_FILES`），不再硬编码 `D:\BME2026\BME_CT_Seg\` 父目录布局。
- **`server/server_inference.py` 6 个 server 路径默认值脱敏**：原 `/mnt/data0/LUO_Zheng/...` 改为 `<需设置 SEGMENTATION_SERVER_* 环境变量>`；`tests/backendState.test.py` 31 处 fixture 同步替换 `LUO_Zheng` → `user_eval` 并去 PowerShell `Set-Content -Encoding utf8` 引入的 UTF-8 BOM。
- 新 planning 主题：`.planning/2026-06-13-doc-consistency-pass/` 4 份文档落地（explanation / findings / progress / task_plan）。
- 不修改 `surface_distances()` 2 EDT / 6 类指标实现路径或任何历史 baseline 数值；本文件覆盖的 `b3c528cc9e20` mean Dice 0.924780 / `a717dacf42d3` mean Dice 0.926 / `86b0153d0a73` mean Dice 0.893127 三套基线保持不变。

## 可复用命令

```powershell
python tools\segmentation_metrics_summary.py `
  --prediction <prediction.nii.gz> `
  --reference <reference-label.nii.gz> `
  --checkpoint <checkpoint_best.pth> `
  --labels-json <validation_summary.json> `
  --sample-id <sample-id> `
  --output-dir .test-output\<metrics-run-id> `
  --stem <run-name>-segmentation-metrics
```

输出文件：

- `<run-name>-segmentation-metrics.json`：结构化指标，适合脚本读取和后续对比。
- `<run-name>-segmentation-metrics.md`：人工阅读版指标摘要。

记录字段：

- Dice：逐标签、平均值、最低值、前景值。
- IoU：逐标签、平均值、最低值、前景值。
- Voxel Accuracy / Pixel Accuracy：3D NIfTI 中两者均为体素逐点 exact-match accuracy。
- Hausdorff Distance：按 NIfTI spacing 计算的对称 surface Hausdorff Distance，单位为 mm。
- Checkpoint 元数据：路径、文件大小、修改时间和 SHA256。

标签源要求：

- 优先使用本次推理生成的 `validation_summary.json`，因为它来自 checkpoint 内嵌的 `dataset_json`，能保留当前权重的完整标签定义。
- 不要混用旧的外部 `dataset.json`；如果标签集合不同，会导致 label 名称错位或漏记空标签。
- 本轮 checkpoint 定义 15 个前景标签。AMOS 0117 的参考标签实际只出现 label `1..13`；如果预测也没有 label `14/15`，它们记录为 N/A。如果预测出现 label `14/15` 假阳性，则 Dice/IoU 为 `0` 并应纳入 fast/quality 对照判断。
- 2026-05-26 后端新增输入后缀规范化，确保 `.nii` 上传会按当前模型 `file_ending=.nii.gz` 进入 nnUNetv2；该工程修复不改变本文件既有指标数值。
- 2026-05-27 标签文件传输修复后，后端在线 custom label validation 已可用。当上传的标签 ID 与 checkpoint 不一致时，`server/taxonomy.py` 会自动检测数据集来源（如 FLARE22）并按器官名重映射 ID，validation 结果中 `remap_applied: true` 表示已自动重映射。
- 2026-05-29 缓存命中时不再复用缓存来源 job 的 `validation`；预测 NIfTI 可复用，但 Dice/IoU/Hausdorff 必须来自本次请求的标签文件或内置参考标签。
- 2026-05-29 自动 remap 支持部分 FLARE22 标签：当至少两个共享 ID 明确语义错位且没有原生匹配时可识别为 FLARE22；单 label 文件仍不自动推断数据集来源。
- 2026-05-30 新增 `runtime_target=local|server` 和局域网访问配置后，本文件中的历史 AMOS/FLARE 指标不变；本地 fold0、服务器 5-fold ensemble 和不同 profile 的指标必须分开记录，不能混算。
- 2026-05-31 校园网服务器 5GPU/5-fold smoke 已跑通并回填 GUI；FLARE 轮次 remap 后指标合理，AMOS 轮次出现 `mean Dice=0.076015`、`foreground Dice=0.979808` 且 `remap_source=FLARE22` 的异常。该 AMOS 数值暂列为 taxonomy 误判证据，不作为模型质量基线。
- 2026-05-31 显式 `label_taxonomy=auto|AMOS22|FLARE22` 已实现，`detect_dataset()` 更保守：标签 ID 是 checkpoint 子集时不触发 remap。AMOS CT 高分辨率推理完成（fast profile，mean_dice=0.77724）。
- 2026-05-31 新增的影像量化分析来自前端已回填的预测 mask 与 NIfTI spacing，输出体积、截面积和长度估算；它不改变本文件中的 Dice、IoU、Voxel Accuracy 或 Hausdorff Distance 口径。
- 2026-06-01 本地缓存演示：AMOS 0117 cache hit（`aea4e7cdbaf0`，命中 `009d4efdc5f6`，review，mean_dice 0.891，stomach 0.556）；FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，quality 模式，218s，结果 120KB）；FLARE22 cache hit（`02da885c97d8`，0.001s，命中 `0aa7323a4c01`）。该演示不修改本文件既有 AMOS 基线 `b3c528cc9e20`（mean_dice 0.924780）和新权重首跑 `27216eb73220`（mean_dice 0.924791）。`tools/seed_demo_cache.py` 是该演示的预热脚本，幂等可重跑；cache_key 7 字段隔离已实测正确。
- 2026-06-01 晚间 cache 链路补丁：FLARE22 cache hit 现在能正确显示历史 validation 摘要（0.893127/0.67373/0.949908，"（历史离线缓存摘要）"）；`tools/rewrite_flare22_historical_summary.py` 把 2026-05-26 remap 后的 metrics 写入 0aa7323a4c01 的 output。`server/main.py` 的 `complete_cached_job()` 增加 historical 回退，`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序。该补丁不修改本文件任何基线指标数值，仅修正 cache hit 时的 validation 显示口径；AMOS 原生基线 `b3c528cc9e20`（mean_dice 0.924780）仍是 quality profile 的正式 AMOS 验证。

## 当前 AMOS 基线运行

本轮新权重：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\checkpoint_best.pth
```

预测结果：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\acceptance-new-weight-20260524-201714\work\27216eb73220\output\27216eb73220.nii.gz
```

参考标签：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\amos_0117(2).nii.gz
```

详细输出：

- JSON: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.json`
- Markdown: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.md`

无缓存 warm timeout 后补充输出：

- Prediction: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\perf-no-cache-persistent-20260524-212332\work\685426290aa4\output\685426290aa4.nii.gz`
- JSON: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.json`
- Markdown: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.md`
- 结果 SHA256：`5473EAFB22FA21B896F8511BE9E02FFD49D678DEE4B82E63681FDD99DA57D9C0`

2026-05-25 fast/quality no-cache profile 对照输出：

- 快速预览 prediction：`.test-output\perf-fast-profile-20260525-1305\work\6802e01f1a73\output\6802e01f1a73.nii.gz`
- 快速预览 JSON：`.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.json`
- 快速预览 Markdown：`.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.md`
- 质量推理 prediction：`.test-output\perf-quality-profile-20260525-1330\work\b3c528cc9e20\output\b3c528cc9e20.nii.gz`
- 质量推理 JSON：`.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.json`
- 质量推理 Markdown：`.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.md`

## 当前 AMOS 基线聚合指标

| 指标 | 数值 |
|---|---:|
| mean Dice | `0.924791` |
| min Dice | `0.846551` |
| foreground Dice | `0.980316` |
| mean IoU | `0.865105` |
| min IoU | `0.733930` |
| foreground IoU | `0.961392` |
| Voxel Accuracy | `0.998578` |
| Pixel Accuracy | `0.998578` |
| mean Pixel Accuracy（label 平均，2026-06-03 增补） | `0.999855` |
| min Pixel Accuracy（2026-06-03 增补） | `0.999493` |
| foreground Pixel Accuracy（2026-06-03 增补） | `0.998252` |
| mean Hausdorff Distance | `7.716048 mm` |
| max Hausdorff Distance | `16.562684 mm` |
| mean HD95（2026-06-03 增补） | `3.596449 mm` |
| max HD95（2026-06-03 增补） | `16.540683 mm` |
| mean ASD（2026-06-03 增补） | `0.660724 mm` |
| max ASD（2026-06-03 增补） | `3.58299 mm` |
| surface_distance_unit | `mm` |
| spacing | `[0.5078125, 0.5078125, 5.0] mm` |

## 快速预览与质量推理无缓存对照

同一 AMOS 0117 输入、同一 checkpoint、同一性能脚本，均禁用历史缓存：

| 指标 | 快速预览 profile | 质量推理 profile |
|---|---:|---:|
| job id | `6802e01f1a73` | `b3c528cc9e20` |
| duration_seconds | `384.345` | `1360.398` |
| persistent_worker | `381.448` | `1357.677` |
| result_bytes | `142578` | `141568` |
| validation status | `review` | `passed` |
| mean Dice | `0.777243` | `0.924780` |
| min Dice | `0.000000` | `0.846569` |
| foreground Dice | `0.972898` | `0.980317` |
| mean IoU | `0.713592` | `0.865088` |
| min IoU | `0.000000` | `0.733957` |
| foreground IoU | `0.947226` | `0.961394` |
| Voxel Accuracy | `0.998068` | `0.998578` |
| Pixel Accuracy | `0.998068` | `0.998578` |
| mean Hausdorff Distance | `10.282058 mm` | `7.716048 mm` |
| max Hausdorff Distance | `24.616009 mm` | `16.562684 mm` |
| label 14 prediction_voxels | `664` | `0` |
| label 15 prediction_voxels | `670` | `0` |

结论：

- `quality` 应作为默认/正式报告依据。
- `fast` 可作为快速预览或演示模式，但必须标注“需复核”。
- label `14/15` 的小体积假阳性只在本轮 `fast` profile 中出现；如要过滤，应作为独立 `postprocess` 实验记录，不能混同模型原始输出。
- 2026-05-25 后续实现已把 `quality/fast` 做成每次 job 的显式产品选择。`inference_options` 会随创建响应、job state、SSE complete 事件和 `job_summary.json` 保存；本节指标仍只代表上表两次原始模型输出，没有新增后处理分数。

## FLARE22 Tr 0009 标签体系重映射对照

2026-05-26 新增 FLARE22 Tr 0009 后执行一次 `quality` 在线推理。该病例的原始 FLARE22 label ID 顺序与当前 AMOS22 checkpoint 不一致；当时的下表指标来自离线 remap：先按器官名把 FLARE22 label 映射到 AMOS22 checkpoint label ID，再运行指标脚本，仅作为非 AMOS 对照证据。

2026-05-28 已将同一类映射能力产品化到后端 `server/taxonomy.py`：用户上传 FLARE22 标签文件时，后端会自动检测来源数据集并按器官名重映射后计算在线 Dice。最新在线验证记录见本节后面的“自动 taxonomy remap 在线验证”。

运行输出：

- Job summary：`.test-output\flare22-tr-0009-quality-20260526\job_summary.json`
- Prediction：`.test-output\flare22-tr-0009-quality-20260526\86b0153d0a73.nii.gz`
- Remapped reference：`.test-output\flare22-tr-0009-quality-20260526\FLARE22_Tr_0009_label_remapped_to_amos_ids.nii.gz`
- Remap metadata：`.test-output\flare22-tr-0009-quality-20260526\flare_to_amos_label_remap.json`
- Metrics JSON：`.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.json`
- Metrics Markdown：`.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.md`

推理记录：

| 指标 | 数值 |
|---|---:|
| job id | `86b0153d0a73` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| duration_seconds | `237.323` |
| phase_timings | `prepare_runtime_model=0.003`, `persistent_worker=237.119`, `collect_result=0.001` |
| result_size_bytes | `120761` |
| GPU at completion | `NVIDIA GeForce RTX 4060 Laptop GPU`, `1804 / 8188 MiB`, `18%` |

重映射后的聚合指标：

| 指标 | 数值 |
|---|---:|
| mean Dice | `0.893127` |
| min Dice | `0.673730` |
| foreground Dice | `0.949908` |
| mean IoU | `0.815941` |
| min IoU | `0.507989` |
| foreground IoU | `0.904594` |
| Voxel Accuracy | `0.991879` |
| Pixel Accuracy | `0.991879` |
| mean Hausdorff Distance | `12.595149 mm` |
| max Hausdorff Distance | `38.043429 mm` |
| label 14 prediction_voxels | `0` |
| label 15 prediction_voxels | `0` |

本次重映射对照中，逐标签最低值为 `duodenum` Dice `0.673730`、`pancreas` Dice `0.806389` 和 `esophagus` Dice `0.808989`；最高 Dice 为 `liver=0.968961`、`spleen=0.965952` 和 `gall_bladder=0.949364`。

解释边界：

- 这是 2026-05-26 的离线 remap 对照，不是当时的后端自动验证；不能与 AMOS 0117 原生标签指标混算。
- 该 remap 只适合作为 FLARE22 与 AMOS22 checkpoint 共有 13 个器官的器官名对齐检查。
- FLARE22 本例没有膀胱或前列腺/子宫标签；label `14/15` 仍为空，并且本次 `quality` 运行中对应预测体素为 `0`。

### 自动 taxonomy remap 在线验证

2026-05-28 自动 taxonomy remap 上线后，FLARE22 Tr 0009 上传标签文件即可在后端在线 validation 中自动重映射：

| 指标 | 数值 |
|---|---:|
| job id | `a717dacf42d3` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| remap_applied | `true` |
| remap_source | `FLARE22` |
| mean Dice | `0.926` |
| validation status | `passed` |

解释边界：

- 该记录证明跨数据集在线 validation 链路已打通，但仍是 FLARE22 标签按器官名重映射后的指标，不是 AMOS 原生标签验证。
- `remap_applied: true` 是解释指标的关键字段；缺少该字段时，不应把 FLARE22 原始 label ID 直接当作 AMOS22 label ID 解读。
- 当前部分标签自动 remap 只覆盖至少两个明确错位 ID 的情况；只有单个 label ID 的文件仍应记录为人工判断或等待显式数据集 hint。

Checkpoint 元数据：

| 字段 | 数值 |
|---|---|
| size_bytes | `1136119762` |
| modified_time | `2026-05-24T10:04:22+00:00` |
| sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |

## 服务器 5-fold soft ensemble 运行补充

2026-05-31 已完成校园网服务器在线推理 smoke。该部分指标与本地 AMOS quality 基线分开记录：

| 服务器轮次 | 指标 | 当前解释 |
|---|---|---|
| FLARE22 + 标签 | mean Dice 约 `0.891`，foreground Dice 约 `0.951`，总耗时约 `3分48秒` | FLARE22 → AMOS22 remap 后结果合理，可证明服务器推理、ensemble、下载和前端回填链路可用。 |
| AMOS 0117 + AMOS 标签 | mean Dice `0.076015`，foreground Dice `0.979808`，总耗时约 `9分46秒` | 报告显示 `remap_applied=true`、`remap_source=FLARE22`，更像 AMOS 原生标签被错误 remap；暂不作为模型失败证据。 |

后续只有在显式 `label_taxonomy=AMOS22` 下复跑并确认 `remap_applied=false` 后，才能把 AMOS 服务器轮次纳入正式质量指标表。

## 当前 AMOS 基线逐标签指标

> 数值来自 2026-06-03 之后的 AMOS quality cache hit（如 `2d477d8bbd7d`），使用 `surface_distances()` 2 EDT 实现。HD/HD95/ASD 单位为 mm，Pixel Accuracy 为 0-1 比例。

| 标签 | 名称 | Dice | IoU | 像素准确率 | HD (mm) | HD95 (mm) | ASD (mm) |
|---:|---|---:|---:|---:|---:|---:|---:|
| 1 | 脾脏 | `0.979085` | `0.959027` | `0.999861` | `6.09375` | `1.015625` | `0.157572` |
| 2 | 右肾 | `0.978704` | `0.958296` | `0.999925` | `6.621065` | `1.015625` | `0.15945` |
| 3 | 左肾 | `0.985648` | `0.971702` | `0.999947` | `5.0` | `0.507812` | `0.087983` |
| 4 | 胆囊 | `0.950342` | `0.905383` | `0.999952` | `4.094115` | `1.135503` | `0.159064` |
| 5 | 食管 | `0.793725` | `0.657997` | `0.999782` | `15.24724` | `11.041705` | `1.704524` |
| 6 | 肝脏 | `0.984249` | `0.968987` | `0.999493` | `10.0` | `1.436311` | `0.225846` |
| 7 | 胃 | `0.555985` | `0.385027` | `0.999525` | `22.047485` | `16.540683` | `3.58299` |
| 8 | 主动脉 | `0.977631` | `0.956241` | `0.999862` | `10.0` | `1.523438` | `0.271276` |
| 9 | 下腔静脉 | `0.923908` | `0.858578` | `0.999865` | `10.025754` | `2.539062` | `0.538958` |
| 10 | 胰腺 | `0.899086` | `0.816672` | `0.999803` | `16.547107` | `3.251587` | `0.528217` |
| 11 | 右肾上腺 | `0.851822` | `0.74189` | `0.999991` | `5.0` | `1.605844` | `0.271422` |
| 12 | 左肾上腺 | `0.815983` | `0.689165` | `0.999986` | `6.114872` | `2.093765` | `0.331275` |
| 13 | 十二指肠 | `0.891079` | `0.803555` | `0.999828` | `7.915146` | `3.046875` | `0.57083` |
| 14 | 膀胱 | `N/A` | `N/A` | `1.0` | `N/A` | `N/A` | `N/A` |
| 15 | 前列腺/子宫 | `N/A` | `N/A` | `1.0` | `N/A` | `N/A` | `N/A` |

## 备注

### 2026-05-26 GUI 运行时渲染说明

本轮 GUI 交互性能优化不改变本指标汇总中的任何数值。代码改动只影响前端渲染节奏：

- `src/components/OrthogonalViewer.tsx` 使用 `requestAnimationFrame` 合并高频切片图像更新。
- `src/main.tsx` 按动画帧调度 axial 预览切片更新，并让右侧预览和底部缩略图复用共享切片缓存渲染器。
- 十字线反馈仍保持即时；较重的 `canvas.toDataURL()` 切片栅格化在快速移动光标时减少同步触发。
- 矢状/冠状拖动回跳修复只改变前端 `voxelCoord` 与 `selectedSlice` 的同步方向，不改变任何分割结果或指标计算。
- 三视图拖动卡顿二次修复进一步把 `voxelCoord` 本身的 React 状态提交合并到每帧一次，并与拖动派生的 `selectedSlice` 同帧提交；该改动仍只影响前端渲染节奏。
- 矢状/冠状拖动卡顿三次修复增加拖动状态识别，拖动期间三视图使用 `interactive` 轻量切片实时预览，释放后恢复完整质量；这是 GUI 交互优化，不影响 NIfTI 输出或指标脚本。
- 本轮没有改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 计算，也没有改变 FLARE22 taxonomy-remap 指标。

- 本文档记录的是 AMOS 0117 参考病例上的指标，不代表所有外部 CT 都具备同等效果。
- 2026-05-27 标签文件传输修复后，后端在线 custom label validation 链路已打通。job `bf20f0ec4456`（FLARE22 + 标签上传）验证了 `label_path` 非空、validation 正常执行。2026-05-28 实现自动 taxonomy remap 后，job `a717dacf42d3` 在线验证 mean_dice=0.926，验证通过。
- 2026-05-29 修复缓存 validation 语义后，缓存命中的指标不得解释为缓存来源 job 的旧标签结果；同一 CT 换标签文件时，validation 会重新计算。
- 2026-05-29 移除上传文件名调试日志后，标签链路排查应依赖 job state、`label_path`、validation summary 和测试覆盖，而不是控制台文件名输出。
- 2026-05-30 的运行位置选择、局域网配置和服务器 5-fold soft ensemble 编排入口已在 2026-05-31 完成服务器 smoke；当前 FLARE 服务器轮次可作为链路跑通证据，AMOS 服务器轮次因疑似 taxonomy 误判暂不替换当前 AMOS `quality` 基线。
- 没有标准标签的病例不能计算 Dice、IoU 或 Hausdorff Distance，只能记录推理耗时、资源快照和人工复核结论。
- 后续训练权重应保留每次的 JSON 原始输出，并把关键聚合指标追加到本文档。
- 2026-06-01 本地缓存演示的 AMOS 0117 cache hit 命中 `009d4efdc5f6`（2026-05-23 历史推理，138KB，validation review，mean_dice 0.891，stomach 0.556）；当前 AMOS 基线指标与该 cache hit 复用的预测均已记录。如需 quality 模式 AMOS 验证，应使用 job `b3c528cc9e20`（mean_dice 0.924780）作为正式基线，不要把 cache hit 命中的 0.891 解读为正式 AMOS 质量基线。
- 2026-06-01 cache 链路补丁后，FLARE22 cache hit（`02da885c97d8`）显示的是 0aa7323a4c01 的历史 validation_summary.json（0.893127/0.67373/0.949908，"（历史离线缓存摘要）"），而不是 009d4efdc5f6 的 AMOS 摘要；该指标源自 2026-05-26 remap 后的真实数据，与 AMOS 原生基线 `b3c528cc9e20`（0.924780）属不同口径。
- 2026-06-03 质量评估指标扩展后，本文档的"当前 AMOS 基线聚合指标"和"当前 AMOS 基线逐标签指标"已补充 6 类医学影像主流指标完整字段。新指标值取自 AMOS quality cache hit（`2d477d8bbd7d` / `9fd0fdc39960` / `096e5b8349df`），validation 阶段实测 16.78s（旧实现 38.86s）。`surface_distances()` 1 crop + 2 EDT/label 是新的性能不变量；`tools/segmentation_metrics_summary.py` 离线脚本复用同一份实现，保证离线口径与后端在线 validation 完全一致。HD/HD95/ASD 报告单位固定为 mm，色阶 ≤1mm 绿 / ≤3mm 黄 / >3mm 红；与 Dice 0.85/0.70 阈值互不影响。
