# 2026-06-06 演示当天收口任务规划

**范围：** 2026-06-06 演示当天收口 4 块独立改动：演示关键 bug 修复（B1-B4）、演示启动脚本化、server mode gating 6 路径修复、AMOS 0117 演示口径决策。

**当前状态：** 本地缓存演示 7 步 + cache 链路补丁 + detect_dataset 二轮收紧 + dataset_hint 字段 + 6 类医学影像指标扩展 + surface_distances 2 EDT + HTML 报告第一轮美化（视觉层 + 信息层）+ HTML 报告临床报告风格重构（封面 + 摘要 + TOC + 8 段章节 + 公式 tip + 严重度分布图 + caption/footnote + 打印页眉页码）均已收口。9 份核心文档全部同步到 6-06 状态，4 份 planning 文档落地（本目录）。当前阻塞点转为 5-fold 提分策略、高分辨率 CT 推理优化、服务器 AMOS/FLARE 显式 taxonomy 复跑、跨数据集 cache 链路产品化、runbook 校验自动化、跨数据集标签评估增强。

**本轮已完成（2026-06-01）：**

- 本地缓存演示 7 步（AMOS cache hit + FLARE 真实推理 218s + FLARE cache hit 0.001s）
- cache 链路补丁（historical 回退 + find_cached_prediction 优先选有 validation_summary.json 的 cache_source + tools/rewrite_flare22_historical_summary.py + 2 个新测试）
- 9 份核心文档同步
- `.planning/2026-06-01-local-cache-demo/` 4 份 planning 文档落地

**本轮已完成（2026-06-02）：**

- `detect_dataset()` 0.85 coverage 守卫（`taxonomy=auto` 时 AMOS 真实 1-13 标签不再被误判为 FLARE22）
- 前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy`
- `Job.dataset_hint` + 前端 `referenceCaseDatasetHint` 状态机（`taxonomy=auto + dataset_hint=FLARE22` 强制 remap）

**本轮已完成（2026-06-03）：**

- 6 类医学影像指标扩展（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD），`ValidationSummary` 增补 12 字段
- `server/main.py surface_distances()` 把单 label EDT 调用从 6 次合并到 2 次（AMOS 0117 quality cache hit validation 38.86s → 16.78s，约 2.3× 加速）
- `src/report/exportReport.ts` 3 个 metric group（19 张卡片）+ 逐标签 4 列新指标
- 3 个新增回归测试（1e-9 精度、EDT 计数恒为 2、wall-time 加速比 ≥30%）
- 6-03 baseline 数值：mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm
- 10 份核心文档同步到 6-03 现状 + 新建 `examples/reference_cases.json`（4 例模板）

**本轮已完成（2026-06-04）：**

- HTML 报告第一轮美化（视觉层）：色阶图例、Header 渐变、3 个 metric group 加组标题图标、aiFindings 严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定 + 列点击排序、@media print A4 页眉页码
- HTML 报告第一轮美化（信息层）：remap_applied 顶部警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条
- `src/main.tsx:handleExport` 透传 5 个 validation 字段
- `tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class
- 9 份核心文档同步到 6-04

**本轮已完成（2026-06-05）：**

- HTML 报告临床报告风格重构：`.cover` 封面页、`.exec-summary` 执行摘要、`.toc` 目录（§1-§8 锚点导航）、`.formula-tip` 公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、`.dist-chart` 严重度分布图、`.table-caption` 表格标题、`.footnotes` 脚注
- 章节编号 `.section-num`（"§ N"） + `.section-en`（英文小标题）
- 字体 Source Han Serif / Songti SC + JetBrains Mono
- @media print 改为 A4 + 顶部 caseId + 底部 page X of Y
- 3 个新工具函数 `distributionChartHtml()` / `severityBuckets()` / `formulaTips()`
- `npm test` / `npm run build` 全过
- 9 份核心文档同步到 6-05
- 4 份 planning 文档落地（`next-round-candidates/`）

**本轮已完成（2026-06-06）：**

- **B1 SSE 进度回退修复**：`src/main.tsx:infereneTimeline` 的进度追踪以 `event.percent !== undefined` 才更新；heartbeat 心跳事件没有 `percent` 字段时不再覆盖当前进度。`tests/imagingLogic.test.ts` source-grep 守护。
- **B2 取消后残留进度修复**：后端 `cancel_job()` 在 `EventSourceHandler` 关闭前先发送 `event: cancel` 事件；前端 `createInferenceEventSource` 关闭前先写 `cancelled` 状态。`tests/imagingLogic.test.ts` 守护"取消状态优先于 progress 事件"。
- **B3 后端模型状态对外可读**：`server/main.py` 把 `get_model_state()` 的返回值写入 `/api/health` 响应的 `model_state` 字段（4 个 key：`status` / `checkpoint_sha256` / `mode` / `missing`）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。
- **B4 SSE 基础异常重试**：`createInferenceEventSource` 暴露 `onretry` / `retryCount` 字段；`onerror` 时按 200ms→2s 指数退避重试，最多 3 次。`tests/imagingLogic.test.ts` source-grep 守护。
- **演示启动脚本化**：`tools/start_local_demo.py` 一行启动：setenv + spawn backend/frontend + 轮询 4 个端点（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）+ 失败时打印 `docs/local-cache-demo-runbook.md` 回退命令。配套一屏卡片 `docs/demo-day-checklist.md`。
- **server mode gating 6 路径修复**：`server/main.py:1537-1604 get_model_state(runtime_target)` 接受 `runtime_target` 参数切换 `server_required_files`（6 项 server 路径）与 `local_required_files`（4 项本地 nnUNet 文件）两组互斥检查。`tests/backendState.test.py` 新增 3 个守护测试。
- **AMOS 0117 演示口径决策落地（2026-06-05 决策，6-06 写入 runbook）**：cache hit `aea4e7cdbaf0` 命中的是 2026-05-23 quality profile 真实推理 `009d4efdc5f6`（review 状态，stomach Dice 0.556、mean_dice 0.891），stomach 0.556 是数据本身硬骨头。决策：接受现状，不复跑 AMOS 0117；正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。
- **Smoke test 验证**：`python tools/start_local_demo.py` 真启后端 + 前端，4 个端点全过（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）。
- **9 份核心文档同步到 6-06** + **4 份 planning 文档落地（本目录）**。

---

## 演示前必做 Bug 修复（2026-06-05 bug 扫描 → 2026-06-06 完成）

> 详情见 `next-round-candidates/task_plan.md` B1-B4 段；这 4 条是 BME 竞赛 PPT 演示前必须闭合的高优先级 bug。本轮全部修复。

### B1. SSE 进度回退 [完成 6-06]

**位置：** `src/main.tsx:infereneTimeline`

**症状（修复前）**：heartbeat 心跳事件没有 `percent` 字段时，前端 `state.lastPercent ?? event.percent` 写值会把当前 `lastPercent` 覆盖成 `undefined`，进度条从 60% 突然显示 "—" 然后再涨回去。

**修复**：`event.percent !== undefined` 才更新；heartbeat 不带 `percent` 时保持 `lastPercent` 不变。`tests/imagingLogic.test.ts` source-grep 守护 `event.percent` 检查。

---

### B2. 取消后残留进度 [完成 6-06]

**位置：** `src/main.tsx:createInferenceEventSource` / `server/main.py:cancel_job()`

**症状（修复前）**：取消 job 后后端继续写 progress 事件或心跳；前端 EventSource 关闭前如果还有 `data: {...}` 缓冲在 EventSource 内部，前端会先收到 `event: progress` 然后才收到 `event: complete` 标记取消状态。底部状态会继续显示"推理运行中"2-3 秒。

**修复**：前端 SSE 关闭前先调用 `setJobState("cancelled")` 写取消状态；后端在 `cancel_job()` 关闭 EventSourceHandler 前先发送一个 `event: cancel` 事件让前端立即响应。`tests/imagingLogic.test.ts` 守护"取消状态优先于 progress 事件"。

---

### B3. 后端模型状态对外可读 [完成 6-06]

**位置：** `server/main.py:/api/health` 响应 / `get_model_state()`

**症状（修复前）**：`/api/health` 响应没有 `model_state` 字段；前端状态栏展示"模型状态"时只能用 `/api/models` 端点拼凑。

**修复**：`/api/health` 响应的 `model_state` 字段（4 个 key：`status` / `checkpoint_sha256` / `mode` / `missing`）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。

---

### B4. SSE 基础异常重试 [完成 6-06]

**位置：** `src/main.tsx:createInferenceEventSource`

**症状（修复前）**：浏览器 EventSource 在 SSE 流断开时会触发 `onerror` 事件，但不会自动重连。原来前端 `createInferenceEventSource` 接到 `onerror` 后只 `console.error` 不重连。网络抖动 1-2 秒后，前端直接显示"推理失败"红色 banner，但实际后端推理仍在跑。

**修复**：`createInferenceEventSource` 暴露 `onretry` / `retryCount` 字段；`onerror` 时按 200ms→2s 指数退避重试，最多 3 次。3 次失败后才显示"推理失败"红色 banner。`tests/imagingLogic.test.ts` source-grep 守护 `onretry` 字符串。

---

## 演示启动脚本化 [完成 6-06]

### 关键步骤

1. [x] 写 `tools/start_local_demo.py` 自动 setenv（`SEGMENTATION_REFERENCE_CASES_JSON` / `SEGMENTATION_DEVICE` / `SEGMENTATION_INFERENCE_PROFILE`）+ spawn backend（uvicorn 127.0.0.1:8000）+ frontend（vite dev 127.0.0.1:5173）。
2. [x] 轮询 4 个端点（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）。
3. [x] 失败时打印 `docs/local-cache-demo-runbook.md` 的 runbook 回退命令。
4. [x] 写 `docs/demo-day-checklist.md` 一屏卡片：每天第一次演示前的 5 个前置确认 + 5 步演示流程 + 可能用到的辅助命令 + 失败时回退到 runbook。
5. [x] Smoke test 验证：`python tools/start_local_demo.py` 真启后端 + 前端，4 个端点全过。

**意义**：演示现场从"操作员熟记 5+ 行命令"变为"操作员敲一行 `python tools/start_local_demo.py`"。

---

## server mode gating 6 路径修复 [完成 6-06]

### 关键步骤

1. [x] 修改 `server/main.py:1537-1604 get_model_state(runtime_target)` 接受 `runtime_target` 参数切换 `server_required_files`（6 项 server 路径）与 `local_required_files`（4 项本地 nnUNet 文件）两组互斥检查。
2. [x] `runtime_target=server` 只检查 `SEGMENTATION_SERVER_EVALUATE_SCRIPT` / `SEGMENTATION_SERVER_DATASET_JSON` / `SEGMENTATION_SERVER_NNUNET_RAW` / `SEGMENTATION_SERVER_NNUNET_PREPROCESSED` / `SEGMENTATION_SERVER_NNUNET_RESULTS` / `SEGMENTATION_SERVER_OUTPUT_ROOT`。
3. [x] `runtime_target=local` 才检查本地 `dataset.json` / `plans.json` / `checkpoint_best.pth` / `nnUNetv2_python`。
4. [x] `tests/backendState.test.py` 新增 3 个守护测试：`test_server_runtime_ready_does_not_require_local_model_files`（env 配 4 个 server 路径 + 本地 4 文件全缺失，断言 `state["missing"] == []`、`state["status"] == "ready"`） / `test_server_runtime_reports_missing_server_paths`（4 个 server 路径缺失时 `missing` 包含对应项） / `test_local_runtime_does_not_check_server_paths`（`runtime_target=local` 绝不报 server 路径缺失）。
5. [x] Smoke test 验证 4 端点全过。

**意义**：服务器模式创建 job 不再因本地 Windows nnUNet 文件缺失而 503；本地 4 文件与 server 6 路径两组互斥检查。

---

## AMOS 0117 演示口径决策 [完成 6-06]

### 关键步骤

1. [x] 确认 cache demo Phase A 命中的 `009d4efdc5f6` 是 2026-05-23 quality profile 真实推理（review 状态，stomach Dice 0.556、mean_dice 0.891）。
2. [x] 决策：接受现状，不复跑 AMOS 0117。stomach 0.556 是数据本身硬骨头（边界模糊），复跑 quality 不会显著改善（预测约 23 分钟）。
3. [x] 正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。
4. [x] 写入 `docs/local-cache-demo-runbook.md` AMOS 0117 演示口径段落。
5. [x] 写入 README、ACCEPTANCE、REVIEW、CODE_MODULE_GUIDE、SEGMENTATION_METRICS_SUMMARY、SEGMENTATION_EXPERIMENT_COMPARISON 等 9 份核心文档的"当前后续重点 / 当前进行中"段落。

---

## 文档同步 [完成 6-06]

- [x] 9 份核心文档同步到 6-06：CLAUDE.md / AGENTS.md / README.md / ACCEPTANCE.md / CODE_MODULE_GUIDE.md / REVIEW.md / SEGMENTATION_METRICS_SUMMARY.md / SEGMENTATION_EXPERIMENT_COMPARISON.md / SEGMENTATION_RECENT_ROUNDS.md
- [x] CLAUDE.md 关键不变量段添加 6-06 演示当天收口不变量（B1-B4 + start_local_demo + server gating 6 路径 + AMOS 0117 决策）
- [x] 4 份 planning 文档落地（本目录 `2026-06-06-demo-day-wrapup/`）
- [x] `next-round-candidates/` 4 份文档日期更新到 2026-06-06，加入 6-06 收口内容

---

## 推荐下一轮任务

### 1. 高分辨率 CT 推理优化（预降采样）

**优先级：** 中高

**前置文档：** `.planning/high-resolution-inference-optimization/`

**目标：** 实现预降采样，缩短高分辨率 CT 推理时间。

**关键步骤：**

1. 评估预降采样方案可行性（768→512，预期推理时间减少约 50%）。
2. 在前端添加降采样选项（如 `inference_resolution=original|downsampled_512`）。
3. 在后端实现降采样逻辑（使用 `scipy.ndimage.zoom` 或类似方法）。
4. 测试降采样后的推理时间和分割质量。
5. 评估是否需要上采样到原始分辨率。

**风险：** 降采样可能丢失细节信息；所有速度和质量结论都必须绑定 job id、输入、checkpoint、profile 和指标。

---

### 2. 5-fold 提分策略

**优先级：** 中高

**目标：** 用 `nnUNetv2_ensemble -np 5` 拿全部 5 个 fold 的 softmax 概率图后取 mean，再做 argmax；当前服务器只跑 fold 0 单次，5-fold ensemble 预计 +2-3% Dice。

**关键步骤：**

1. 服务器后端增加 5-fold ensemble 调用入口。
2. 前端 cache_key 7 字段加入 `ensemble_folds` 区分单 fold / 5 fold。
3. 服务器 AMOS/FLARE 显式 taxonomy 复跑时使用 5-fold ensemble。
4. 记录 5-fold vs 单 fold 的指标对照。

---

### 3. 服务器 AMOS/FLARE 显式 taxonomy 复跑

**优先级：** 中

**前置条件：** server gating 修复完成（6-06 已完成）

**目标：** 用显式 `label_taxonomy=AMOS22` 复跑服务器 AMOS，确认 `remap_applied=false` 后纳入正式质量基线。

**关键步骤：**

1. 复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`。
2. 复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`。
3. 记录服务器质量基线指标（mean Dice、min Dice、foreground Dice）。
4. 与本地 quality 基线（`b3c528cc9e20`，mean Dice 0.924780）对比。

**风险：** 服务器链路可运行不等于质量基线已完成；AMOS 服务器指标必须先排除 taxonomy 误判。

---

### 4. 跨数据集 cache 链路产品化

**优先级：** 中

**前置文档：** `.planning/2026-06-06-demo-day-wrapup/findings.md` 发现 2

**目标：** 把"按历史指标改写 cache_source 摘要"做成可复用机制，让其他数据集/其他 cache_source 也能享受 cache hit 时显示历史 validation 摘要的链路。

**关键步骤：**

1. 重构 `tools/rewrite_flare22_historical_summary.py` 为通用 `tools/rewrite_cached_validation_summary.py`，支持任意 source 路径、任意 target job 目录、任意指标 JSON。
2. 在 `server/main.py` 的 `complete_cached_job()` 中增强 historical 回退：除 `validation_summary.json` 外，尝试读 `job_summary.json` 中的历史指标。
3. 补充 `tests/backendState.test.py` 覆盖"cache_source 含历史指标但无 validation_summary.json"场景。
4. 更新 `docs/local-cache-demo-runbook.md` 增补"通用改写历史摘要"段落。

**风险：** 必须保留"`historical: true`"和"`source_job_id`"标记，避免误把当前请求的标签结果写成历史。

---

### 5. runbook 自动校验

**优先级：** 中

**前置文档：** `.planning/2026-06-06-demo-day-wrapup/findings.md` 待验证假设

**目标：** 写 `tests/cacheDemoRunbook.test.py`，自动确认 runbook 中提到的 4 个已知约束仍在代码里成立。

**关键步骤：**

1. 测试 `_resolve_project_root()` 在 cwd 不同时的解析行为，确认必须落在 `segmentation-gui-prototype/`。
2. 测试 `compute_cache_key()` 的 7 字段仍是 `input_sha256 + checkpoint_sha256 + checkpoint_dataset_name + checkpoint_configuration + labels_source + runtime_target + inference_options`（与 `server/main.py:1880 build_prediction_cache_key()` 实际实现保持一致）。
3. 测试 `examples/reference_cases.json` 解析后能产出 4 个 case；`SEGMENTATION_REFERENCE_CASES_JSON` 缺省时只暴露 `amos_0117`。
4. 测试 `tools/seed_demo_cache.py` 和 `tools/rewrite_flare22_historical_summary.py` 在重复运行下保持幂等。
5. 测试 `find_cached_prediction()` 候选排序在多个 cache_source 下优先选有 `validation_summary.json` 的。

**风险：** 这些测试不应启动真实后端服务；用 import 函数 + 临时目录的方式做单元测试即可。

---

### 6. 跨数据集标签评估增强

**优先级：** 中

**目标：** 在自动 remap 已可用的基础上，增强未知数据集和异常指标的解释能力。

**候选改进：**

- 对 remap 覆盖率不足或未知标签 ID 给出明确 UI 警告。
- 为单 label 或少量标签文件增加显式数据集 hint 入口。
- 在 per-label 表格中标出体素量级差异异常、Dice 为 0 的疑似错位标签。
- 记录 `remap_mapping` 的用户可读摘要，便于报告导出。

**风险：** 需要避免把 remap 后的跨数据集指标写成 AMOS 原生验证。

---

### 7. 文档与验收口径再同步

**优先级：** 中

**目标：** 继续保持 README、ACCEPTANCE、REVIEW、指标汇总和近期轮次记录与代码现状一致。

**关键步骤：**

1. 在后续代码或配置变化后，及时同步 9 份核心文档的中文主体说明。
2. 对 `SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md` 和 `SEGMENTATION_RECENT_ROUNDS.md` 继续坚持"新工程链路不混入旧指标"的口径。
3. 后续若新增 validation 字段或新视觉元素，必须同时改 `inferenceClient.ts normalizeValidation` 白名单 + `exportReport.ts` 模板 + `tests/imagingLogic.test.ts` source-grep 断言三处。

---

### 8. 多模型支持准备

**优先级：** 低（等待新 checkpoint）

**目标：** 当前只有 AMOS22 单模型，为未来多模型切换预留结构。

**候选改进：**

- `modelOptions` 从硬编码改为从 `/api/models` 动态获取。
- 后端增加模型目录扫描和模型信息 API。
- 前端模型卡片改为可点击切换。

**风险：** 没有新 checkpoint 时难以完成真实验收。

---

## 推荐执行顺序

1. **高分辨率 CT 推理优化**（预降采样 768→512，独立 planning）。
2. **5-fold 提分策略**（服务器 5-fold ensemble，独立 planning）。
3. **服务器 AMOS/FLARE 显式 taxonomy 复跑**（确认服务器质量基线，独立 planning）。
4. **跨数据集 cache 链路产品化**（让 cache 链路补丁成为通用机制）。
5. **runbook 自动校验**（防止下次复现同样的困惑）。
6. **跨数据集标签评估增强**（持续）。
7. **文档与验收口径再同步**（持续）。
8. **多模型支持准备**（等待新模型或新 checkpoint 后再启动）。

---

*更新日期：2026-06-06*
