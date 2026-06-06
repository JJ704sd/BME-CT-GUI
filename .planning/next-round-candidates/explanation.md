# 下一轮候选任务解释

## 为什么需要这个说明

2026-06-06 项目已连续完成八项里程碑：本地缓存演示 7 步（AMOS cache hit → FLARE 真实推理 → FLARE cache hit）、晚间的 cache 链路补丁、detect_dataset 二轮收紧 + dataset_hint 字段、质量评估指标扩展 + surface_distances 2 EDT、HTML 报告第一轮美化（视觉层 + 信息层）、HTML 报告临床报告风格重构（第二轮美化）、演示当天收口（B1-B4 演示关键 bug 修复 + 演示启动脚本化 + server mode gating 6 路径修复 + AMOS 0117 演示口径决策）。本文档解释下一轮任务的背景和优先级依据。

完整 6-06 收口 4 块改动的 planning 记录见 `.planning/2026-06-06-demo-day-wrapup/`（explanation / findings / progress / task_plan 4 文档）。

## 当前项目状态

### 已完成

1. **本地缓存演示 7 步**：AMOS 0117 cache hit（`aea4e7cdbaf0`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）。
2. **cache 链路补丁**：`_load_cached_validation_summary()` + `complete_cached_job()` 增加 historical 回退；`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序；`tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的 `validation_summary.json`；前端 `getValidationStatusCopy()` 增加 cachedResult 参数；`tests/backendState.test.py` 新增 2 个回归测试。
3. **env var 强制**：`SEGMENTATION_REFERENCE_CASES_JSON` 必须指向 `examples/reference_cases.json`（或 `nnunetv2_files/reference_cases.local.json`）才能让 `/api/samples` 暴露 4 个 reference case；runbook 已把这一项写在最前面。
4. **2026-06-02 detect_dataset 二轮收紧 + dataset_hint 字段**：0.85 coverage 守卫让 AMOS 真实 1-13 标签不再被误判为 FLARE22；`Job.dataset_hint` + 前端 `referenceCaseDatasetHint` 状态机让 `taxonomy=auto + dataset_hint=FLARE22` 仍能强制 remap，覆盖 0.85 守卫的 None。
5. **2026-06-03 质量评估指标扩展 + surface_distances 2 EDT**：`ValidationSummary` 增补 12 字段（Pixel Accuracy 4 项 + HD/HD95/ASD 9 项 + `surface_distance_unit` + `spacing`）；`server/main.py surface_distances()` 把单 label EDT 调用从 6 次合并到 2 次（AMOS 0117 quality cache hit validation 38.86s → 16.78s，约 2.3× 加速）；`src/report/exportReport.ts` 3 个 metric group（19 张卡片）+ 逐标签 4 列新指标。6-03 baseline 数值：mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm。
6. **2026-06-04 HTML 报告第一轮美化（视觉层 + 信息层）**：`src/report/exportReport.ts` 从"工程 dump"提升为"卡片式仪表板"。视觉层：色阶图例、Header 渐变、3 个 metric group 加组标题图标、aiFindings 严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定 + 列点击排序、@media print A4 页眉页码。信息层：remap_applied 顶部警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条。`src/main.tsx:handleExport` 透传 5 个 validation 字段；`tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class。
7. **2026-06-05 HTML 报告临床报告风格重构（第二轮美化）**：`src/report/exportReport.ts` 从"卡片式仪表板"重塑为"临床评估报告"。新增 7 个 CSS 块：`.cover` 封面页、`.exec-summary` 执行摘要、`.toc` 目录、`.formula-tip` 公式小贴士、`.dist-chart` 严重度分布图、`.table-caption` 表格标题、`.footnotes` 脚注；新增 3 个工具函数 `distributionChartHtml()` / `severityBuckets()` / `formulaTips()`；正文模板按 §1 报告概览 / §2 摘要 / §3 数据集 / §4 器官 / §5 体素 / §6 距离 / §7 关键发现 / §8 附录 8 段章节编号排版；字体改为 Source Han Serif / Songti SC + JetBrains Mono；@media print 改为 A4 + 顶部 caseId + 底部 page X of Y。本轮不动 6 类指标、`surface_distances()` 2 EDT 或 `ValidationSummary` / `LabelMetric` 白名单；与 6-04 第一轮美化兼容并叠加。
8. **2026-06-06 演示当天收口**（**说明**：B1 / B2 / B4 当时只写了 commit message 与文档，源码实际未做；真实实现见 2026-06-07 补完段）：
   - **B1 SSE 进度回退修复**：6-06 虚标；6-07 真正实现 `parsed.heartbeat && parsed.progress === 0` 守护，`tests/imagingLogic.test.ts` source-grep 守护。
   - **B2 取消后残留进度修复**：6-06 虚标；6-07 真正实现 `inferenceStatusRef` 镜像 React state + SSE onmessage 入口 cancelled 早退。
   - **B3 后端模型状态对外可读**：`/api/health` 的 `model_state` 字段从内部变量提升为可被 GUI 状态栏读取的稳定 JSON 字段（`status` / `checkpoint_sha256` / `mode` / `missing`）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。（2026-06-06 真实完成）
   - **B4 SSE 基础异常重试**：6-06 虚标；6-07 真正抽出 `src/inference/createInferenceEventSource.ts` 工具并接入。
   - **演示启动脚本化**：`tools/start_local_demo.py` 一行启动：setenv + spawn backend/frontend + 轮询 4 个端点 + 失败时打印 runbook 回退命令。`docs/demo-day-checklist.md` 是配套一屏卡片。
   - **server mode gating 6 路径修复**：`server/main.py:1537-1604 get_model_state(runtime_target)` 接受 `runtime_target` 参数切换 `server_required_files`（6 项 server 路径）与 `local_required_files`（4 项本地 nnUNet 文件）两组互斥检查；`tests/backendState.test.py` 新增 3 个守护测试。
   - **AMOS 0117 演示口径决策（2026-06-05 决策，6-06 落地）**：cache hit 命中的是 2026-05-23 quality profile 真实推理（review，stomach Dice 0.556、mean_dice 0.891），stomach 0.556 是数据本身硬骨头。决策：接受现状，不复跑 AMOS 0117；正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。已写入 `docs/local-cache-demo-runbook.md` 的 AMOS 0117 演示口径段落。

9. **2026-06-07 B1 / B2 / B4 真实补完**（`feat(sse): B1 heartbeat percent guard + B2 cancel priority + B4 EventSource retry`）：
   - **B1 真实实现**：`src/main.tsx` SSE onmessage 在 `parsed.type === "progress" && parsed.heartbeat && parsed.progress === 0` 时只更新 stage 不更新进度。
   - **B2 真实实现**：新增 `inferenceStatusRef` 镜像 React state；SSE onmessage 入口先判 `inferenceStatusRef.current.status === "cancelled"` 早退，`handle.close()` 阻止重试。
   - **B4 真实实现**：抽出 `src/inference/createInferenceEventSource.ts` 工具，含 `onretry` / `retryCount` / `onfatal` 字段、200ms→2s 指数退避、默认 3 次上限。`src/main.tsx` SSE 流接入，3 次失败后 `onfatal` → reject Promise。
   - **测试守护**：`tests/imagingLogic.test.ts` 新增 11 条 source-grep 断言保护 4 个核心改动。

### 待完成

1. **高分辨率推理优化**：768×768 输入面积是标准 512×512 的 2.25 倍，推理时间显著延长。
2. **5-fold 提分策略**：当前服务器只跑 fold 0 单次，5-fold ensemble 预计 +2-3% Dice。
3. **服务器 AMOS/FLARE 显式 taxonomy 复跑**：用显式 `label_taxonomy=AMOS22` 复跑服务器 AMOS，确认 `remap_applied=false` 后纳入正式质量基线。
4. **跨数据集 cache 链路产品化**：当前 cache 链路补丁只针对 FLARE22 Tr 0009 + 0aa7323a4c01 这一对 cache_source；其他 cache_source 命中时若没有 `validation_summary.json`，仍然会显示"无历史验证摘要"。
5. **runbook 自动校验**：写 `tests/cacheDemoRunbook.test.py` 自动确认 runbook 中 4 个已知约束仍在代码里成立。

## 优先级依据

### 中高优先级：高分辨率推理优化

**原因**：768×768 输入导致推理时间显著延长（fast profile 约 6.4 分钟，quality 预计约 23 分钟）。预降采样（768→512）可缩短推理时间约 50%。

**影响范围**：前端推理选项、后端降采样逻辑、结果上采样。

### 中高优先级：5-fold 提分策略

**原因**：当前服务器只跑 fold 0 单次。nnUNetv2 标准 5-fold ensemble（`nnUNetv2_ensemble -np 5` 拿全部 5 个 fold 的 softmax 概率图后取 mean 再 argmax）预计 +2-3% Dice。本地 quality 复跑 `b3c528cc9e20`（mean Dice 0.924780）已是单 fold 上限，要进一步提分必须走 5-fold。

**影响范围**：服务器后端 `server_inference.py` 的 5-fold 编排入口；cache_key 7 字段加入 `ensemble_folds` 区分单 fold / 5 fold。

### 中优先级：服务器 AMOS/FLARE 显式 taxonomy 复跑

**原因**：2026-05-31 的服务器 AMOS 轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808`，且 `remap_source=FLARE22`，疑似 taxonomy 误判。需要用显式 `label_taxonomy=AMOS22` 复跑确认（server gating 6 路径修复已完成，6-06）。

**影响范围**：服务器质量基线的可信度。

### 中优先级：跨数据集 cache 链路产品化

**原因**：当前 cache 链路补丁只针对 FLARE22 Tr 0009 这一具体 cache_source（`0aa7323a4c01`）。其他 cache_source 命中时如果 cache_source 的 output 没有 `validation_summary.json`，UI 仍会显示"无历史验证摘要"。需要把"按历史指标改写 cache_source 摘要"做成可复用工具。

**影响范围**：`tools/`、`server/main.py` 的 `complete_cached_job()` 回退路径、未来新增数据集的接入流程。

### 中优先级：runbook 自动校验

**原因**：cache demo 7 步里有 4 个容易现场忽略的约束（cwd 必须落在 `segmentation-gui-prototype/`、cache_key 7 字段、`SEGMENTATION_REFERENCE_CASES_JSON` 4 例模板、find_cached_prediction 排序）。`tests/cacheDemoRunbook.test.py` 把这些约束变成自动化回归测试，防止后续重构破坏 runbook 假设。

**影响范围**：`tests/cacheDemoRunbook.test.py`。

### 中优先级：跨数据集标签评估增强

**原因**：自动 remap 已可用，但对未知数据集和异常指标的解释能力仍需增强。

**影响范围**：前端 UI 警告、报告导出。

## 与其他 planning 文档的关系

- `.planning/2026-06-01-local-cache-demo/`：本地缓存演示 + cache 链路补丁已完成。
- `.planning/label-taxonomy-server-validation/`：taxonomy fix + server gating 修复已完成（6-06），validation 复跑是下一轮。
- `.planning/high-resolution-inference-optimization/`：推理已完成，优化方案评估是下一轮。
- `.planning/2026-06-06-demo-day-wrapup/`：6-06 演示当天收口（B1-B4 修复 + 启动脚本化 + server gating 6 路径 + AMOS 0117 决策）已完成。
- `.planning/campus-network-and-public-access/`：校园网 smoke 已跑通，稳定性补验是下一步。

## 执行顺序建议

1. **高分辨率推理优化**：实现预降采样，缩短推理时间。
2. **5-fold 提分策略**：服务器 5-fold ensemble，预计 +2-3% Dice。
3. **服务器 AMOS/FLARE 显式 taxonomy 复跑**：确认服务器质量基线。
4. **跨数据集 cache 链路产品化**：把 cache 链路补丁做成通用机制。
5. **runbook 自动校验**：防止下次复现同样的困惑。
6. **跨数据集标签评估增强**：补单 label hint、remap 覆盖率提示。
7. **文档与验收口径再同步**：确保文档持续跟随代码变化。

---

*更新日期：2026-06-06*
