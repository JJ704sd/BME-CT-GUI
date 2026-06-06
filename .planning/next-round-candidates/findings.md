# 下一轮候选任务发现

## 发现日期

2026-06-06（吸纳 6-02 detect_dataset 收紧 + dataset_hint + 6-03 6 类指标扩展 + surface_distances 2 EDT + 6-04 HTML 报告第一轮美化 + 6-05 HTML 报告临床报告风格重构 + 6-06 演示当天收口（B1-B4 修复 + 启动脚本化 + server gating 6 路径 + AMOS 0117 决策））

## 关键发现

### 发现 1：本地缓存演示 7 步已跑通

**证据**：AMOS 0117 cache hit（`aea4e7cdbaf0`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）。

**意义**：cache_key 7 字段隔离已实测正确；cache hit 与真实推理的耗时对照（0.001s vs 218s）肉眼可见。

**后续**：本轮目标已达成，下一轮任务规划见本目录 `task_plan.md`。

### 发现 2：cache 链路补丁后 FLARE22 cache hit 显示历史 validation 摘要

**证据**：FLARE22 cache hit 现在显示 0.893127/0.67373/0.949908（"（历史离线缓存摘要）"）；AMOS cache hit 仍显示 review 状态（stomach 0.556）。`server/main.py` 的 `complete_cached_job()` 增加 historical 回退；`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序。

**意义**：cache hit 不再混用错位 cache_source 的 validation；`tools/rewrite_flare22_historical_summary.py` 是配套的"按历史指标改写 cache_source 摘要"工具。

**后续**：下一轮需要把"按历史指标改写 cache_source 摘要"做成可复用机制，让其他数据集/其他 cache_source 也能享受这条链路。

### 发现 3：`SEGMENTATION_REFERENCE_CASES_JSON` 是 cache 链路的前置条件

**证据**：现场复测时漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，导致 `/api/samples` 只返回内置 `amos_0117`，FLARE22 Tr 0009 不可选；所有"载入参考病例"都跑到了 AMOS 0117。

**意义**：env var 缺一项就会让整条 cache 链路看起来指向错位数据；runbook 必须把这一项写在最前面，并提示用 `/api/samples` 列表确认 4 个 case。

**后续**：6-06 收口：`tools/start_local_demo.py` 自动 setenv，避免现场漏设；`docs/demo-day-checklist.md` 一屏卡片化展示。

### 发现 4：AMOS 0117 cache demo Phase A 决策：接受现状，不复跑

**证据**：cache demo Phase A 命中的 `009d4efdc5f6` 是 2026-05-23 quality profile 真实推理，stomach Dice 0.556、`validation_status=review`、mean_dice 0.891。stomach 边界在 AMOS 0117 病例上确实模糊（CT 切片上 stomach 与周围组织的灰度梯度小），即使换更新训练权重也未必能显著提升。

**意义**：stomach 0.556 不是模型问题，是数据本身硬骨头。复跑 quality 不会显著改善（预测约 23 分钟）。

**决策（2026-06-05 决策，6-06 落地）**：接受现状，不复跑 AMOS 0117；正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。已写入 `docs/local-cache-demo-runbook.md` 的 AMOS 0117 演示口径段落。

### 发现 5：server mode gating 6 路径修复已完成（6-06）

**证据**：`server/main.py:1537-1604 get_model_state(runtime_target)` 接受 `runtime_target` 参数切换 `server_required_files`（6 项 server 路径：`server_evaluate_full.py` / `server_dataset.json` / `server_nnunet_raw` / `server_nnunet_preprocessed` / `server_nnunet_results` / `server_output_root`）与 `local_required_files`（4 项本地 nnUNet 文件）两组互斥检查。`tests/backendState.test.py` 新增 3 个守护测试。Smoke test 2026-06-06 验证 4 端点全过。

**意义**：服务器模式不再因本地 Windows nnUNet 文件缺失而 503；本地 4 文件与 server 6 路径两组互斥检查。

**后续**：服务器 AMOS/FLARE 显式 taxonomy 复跑条件已齐备（下一轮）。

### 发现 6：服务器链路已跑通但质量基线未定

**证据**：2026-05-31 校园网服务器 smoke。

| 轮次 | 结果 | 状态 |
|---|---|---|
| FLARE | mean Dice 约 0.891 | 可用，链路证据 |
| AMOS | mean Dice 0.076015 | 疑似 taxonomy 误判 |

**意义**：服务器推理、ensemble、下载和 GUI 回填链路可用，但 AMOS 质量基线需复跑确认。

**后续**：6-06 server gating 修复后，可用显式 `label_taxonomy=AMOS22` 复跑确认 `remap_applied=false`（下一轮）。

### 发现 7：fast/quality profile 对照数据完整

**证据**：`SEGMENTATION_METRICS_SUMMARY.md` 中的对照表。

| 指标 | fast | quality |
|---|---|---|
| 耗时 | 384.345s | 1360.398s |
| mean Dice | 0.777243 | 0.924780 |
| min Dice | 0.000000 | 0.846569 |
| label 14/15 假阳性 | 有 | 无 |

**意义**：`quality` 应继续作为正式报告基线，`fast` 仅作为预览模式。

### 发现 8：HTML 报告视觉与信息两轮美化已收口

**证据**：2026-06-04 / 2026-06-05 连续两轮对 `src/report/exportReport.ts` 做美化。6-04 把"工程 dump"提升为"卡片式仪表板"：色阶图例、Header 渐变、3 个 metric group 加组标题图标、aiFindings 严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定 + 列点击排序、@media print A4 页眉页码；信息层加 remap_applied 顶部警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条。6-05 把"卡片式仪表板"重塑为"临床评估报告"：`.cover` 封面页（题图条 + 报告编号 + 主副标题 + 数据集/病例/生成时间三列）、`.exec-summary` 执行摘要、`.toc` 目录（§1-§8 锚点导航）、`.formula-tip` 公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、`.dist-chart` 严重度分布图、`.table-caption` 表格标题、`.footnotes` 脚注；正文模板按 §1 报告概览 / §2 摘要 / §3 数据集 / §4 器官 / §5 体素 / §6 距离 / §7 关键发现 / §8 附录 8 段章节编号排版；字体改为 Source Han Serif / Songti SC + JetBrains Mono；@media print 改为 A4 + 顶部 caseId + 底部 page X of Y。

**意义**：HTML 报告输出从"工程 dump"经"卡片式仪表板"升级为"临床评估报告"；打印预览（Ctrl+P）会按 A4 自动分页且带页眉页码，可直接出 PDF 给临床同行。`npm test` 与 `npm run build` 全过；`tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class（`.legend` / `.remap-banner` / `.historical-banner` / `.spacing-bar`）。

**后续**：本轮不修改 6 类指标、`surface_distances()` 2 EDT 或 `ValidationSummary` / `LabelMetric` 白名单；后续若新增 validation 字段（`remap_applied` / `taxonomy_match` / `dataset_hint` / `historical` / `label_taxonomy` / `quantification`）或新视觉元素，必须同时改 `inferenceClient.ts normalizeValidation` 白名单 + `exportReport.ts` 模板 + `tests/imagingLogic.test.ts` source-grep 断言三处。

### 发现 9：B1-B4 演示关键 bug 修复已完成（6-06）

**证据**：

- **B1 SSE 进度回退**：`src/main.tsx:infereneTimeline` 的进度追踪以 `event.percent !== undefined` 才更新；heartbeat 不带 `percent` 时保持 `lastPercent` 不变。`tests/imagingLogic.test.ts` source-grep 守护 `event.percent` 检查。
- **B2 取消后残留进度**：前端 SSE 关闭前先调用 `setJobState("cancelled")` 写取消状态；后端 `cancel_job()` 在 `EventSourceHandler` 关闭前先发送 `event: cancel` 事件让前端立即响应。
- **B3 后端模型状态对外可读**：`/api/health` 的 `model_state` 字段从内部变量提升为可被 GUI 状态栏读取的稳定 JSON 字段（`status` / `checkpoint_sha256` / `mode` / `missing`）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。
- **B4 SSE 基础异常重试**：`createInferenceEventSource` 暴露 `onretry` / `retryCount` 字段；`onerror` 时按 200ms→2s 指数退避重试，最多 3 次。

**意义**：BME 竞赛 PPT 演示现场不会被评委抓"进度回退"、"取消失败"、"模型状态不外露"、"SSE 断连无重试"这 4 个边缘 bug。

### 发现 10：演示启动脚本化 + 一屏卡片已完成（6-06）

**证据**：`tools/start_local_demo.py` 一行启动演示：setenv + spawn backend/frontend + 轮询 4 个端点（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）+ 失败时打印 `docs/local-cache-demo-runbook.md` 回退命令。`docs/demo-day-checklist.md` 是配套一屏卡片：每天第一次演示前的 5 个前置确认 + 5 步演示流程 + 可能用到的辅助命令 + 失败时回退到 runbook。

**意义**：演示现场从"操作员熟记 5+ 行命令"变为"操作员敲一行 `python tools/start_local_demo.py`"。

## 待验证假设

1. **预降采样不影响 Dice**：768→512 降采样后，mean Dice 是否仍在 0.85 以上？
2. **5-fold 提分有效**：用 `nnUNetv2_ensemble -np 5` 拿全部 5 个 fold 的 softmax 概率图后取 mean 再 argmax，mean Dice 是否 +2-3%？
3. **显式 AMOS22 复跑可解决误判**：服务器 AMOS 轮次用 `label_taxonomy=AMOS22` 后，`remap_applied` 是否为 false？
4. **跨数据集 cache 链路可产品化**：其他 cache_source 命中时能否复用 historical 回退机制？
5. **runbook 4 个已知约束仍成立**：`tests/cacheDemoRunbook.test.py` 自动校验 cache_key 7 字段、`SEGMENTATION_REFERENCE_CASES_JSON` 4 例模板、`find_cached_prediction` 排序、`tools/seed_demo_cache.py` 幂等性，是否都能通过？

## 数据来源

- `.planning/2026-06-01-local-cache-demo/` 的 `findings.md` / `progress.md` / `task_plan.md`
- `.planning/label-taxonomy-server-validation/progress.md`
- `.planning/high-resolution-inference-optimization/progress.md`
- `.planning/2026-06-06-demo-day-wrapup/` 的 `findings.md` / `progress.md` / `task_plan.md`
- `SEGMENTATION_METRICS_SUMMARY.md`
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`
- `SEGMENTATION_RECENT_ROUNDS.md`
- `tools/seed_demo_cache.py` / `tools/rewrite_flare22_historical_summary.py` / `tools/start_local_demo.py`
- `docs/local-cache-demo-runbook.md` / `docs/demo-day-checklist.md`
- `src/report/exportReport.ts` 6-04 / 6-05 改动
- `src/main.tsx:infereneTimeline` / `createInferenceEventSource` 6-06 改动
- `server/main.py:1537-1604 get_model_state(runtime_target)` 6-06 改动
- `tests/imagingLogic.test.ts` 4 个新 class 的 source-grep 断言 + B1/B4 守护
- `tests/backendState.test.py` B3 + server gating 3 个守护测试

---

*更新日期：2026-06-06*
