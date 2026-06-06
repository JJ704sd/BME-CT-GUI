# 2026-06-06 演示当天收口解释

## 为什么需要这个说明

2026-06-06 是 BME 竞赛答辩演示日的前一天。答辩现场需要把"本地缓存演示 7 步"在 5 分钟内跑完（AMOS 0117 cache hit → FLARE 真实推理 → FLARE cache hit），并配合 5-fold 提分 / 报告导出 / 三正交联动等核心功能展示。

上一轮 2026-06-05 收口于 HTML 报告临床报告风格重构（第二轮美化），但演示现场仍存在 4 个高风险 bug 容易被现场评委抓个正着；同时 6-05 bug 扫描发现 4 个"BME 竞赛 PPT 演示前必须闭合的高优先级 bug"（B1-B4，详见 `next-round-candidates/task_plan.md`）。本文档解释演示当天收口 4 块改动的背景、优先级依据和验收口径。

## 当前项目状态

### 已完成（6-06 之前）

1. **本地缓存演示 7 步**：AMOS 0117 cache hit（`aea4e7cdbaf0`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）。
2. **cache 链路补丁**：`_load_cached_validation_summary()` + `complete_cached_job()` 增加 historical 回退；`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序；`tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的 `validation_summary.json`。
3. **2026-06-02 detect_dataset 二轮收紧 + dataset_hint 字段**：0.85 coverage 守卫让 AMOS 真实 1-13 标签不再被误判为 FLARE22；`Job.dataset_hint` + 前端 `referenceCaseDatasetHint` 状态机让 `taxonomy=auto + dataset_hint=FLARE22` 仍能强制 remap。
4. **2026-06-03 质量评估指标扩展 + surface_distances 2 EDT**：`ValidationSummary` 增补 12 字段；`server/main.py surface_distances()` 把单 label EDT 调用从 6 次合并到 2 次（AMOS 0117 quality cache hit validation 38.86s → 16.78s，约 2.3× 加速）。
5. **2026-06-04 HTML 报告第一轮美化（视觉层 + 信息层）**：`src/report/exportReport.ts` 从"工程 dump"提升为"卡片式仪表板"。
6. **2026-06-05 HTML 报告临床报告风格重构（第二轮美化）**：从"卡片式仪表板"重塑为"临床评估报告"（封面 + 摘要 + TOC + 8 段章节 + 公式 tip + 严重度分布图 + caption/footnote + 打印页眉页码）。

### 6-06 本轮收口（本目录 task_plan.md 详述）

1. **B1 SSE 进度回退修复**：heartbeat 心跳事件没有 `percent` 字段时不再覆盖当前进度。
2. **B2 取消后残留进度修复**：取消 job 后后端不会继续写 progress 事件；前端不把 cancel 后的心跳误显示为"还在跑"。
3. **B3 后端模型状态对外可读**：`/api/health` 的 `model_state` 字段从内部变量提升为可被 GUI 状态栏读取的稳定 JSON 字段（`status` / `checkpoint_sha256` / `mode` / `missing`）。
4. **B4 SSE 基础异常重试**：`createInferenceEventSource` 暴露 `onretry` / `retryCount` 字段；单次断连后自动退避重连（200ms→2s 指数退避，最多 3 次）。
5. **演示启动脚本化**：`tools/start_local_demo.py` 一行启动演示：setenv + spawn backend/frontend + 轮询 4 个端点 + 失败时打印 runbook 回退命令。`docs/demo-day-checklist.md` 是配套一屏卡片。
6. **server mode gating 6 路径修复**：`runtime_target=server` 创建 job 时只检查 6 个 `SEGMENTATION_SERVER_*` 路径（`server_evaluate_full.py` / `server_dataset.json` / `server_nnunet_raw` / `server_nnunet_preprocessed` / `server_nnunet_results` / `server_output_root`），不被本地 Windows nnUNet 文件缺失阻断；`runtime_target=local` 才检查本地 4 文件，两组互斥。
7. **AMOS 0117 演示口径决策（2026-06-05 决策，6-06 落地）**：cache hit `aea4e7cdbaf0` 命中的是 2026-05-23 quality profile 真实推理 `009d4efdc5f6`（review 状态，stomach Dice 0.556、mean_dice 0.891），stomach 0.556 是数据本身硬骨头（边界模糊），复跑 quality 不会显著改善。决策：接受现状，不复跑 AMOS 0117；正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。已写入 `docs/local-cache-demo-runbook.md`。

### 6-06 之后待完成（转入下一轮）

1. **高分辨率 CT 推理优化**（预降采样 768→512）。
2. **5-fold 提分策略**：用 `nnUNetv2_ensemble -np 5` 拿全部 5 个 fold 的 softmax 概率图后取 mean 再 argmax；当前服务器只跑 fold 0 单次，5-fold ensemble 预计 +2-3% Dice。
3. **服务器 AMOS/FLARE 显式 taxonomy 复跑**：确认 `remap_applied=false` 后纳入正式质量基线。
4. **跨数据集 cache 链路产品化**：把 `tools/rewrite_flare22_historical_summary.py` 重构为通用 `tools/rewrite_cached_validation_summary.py`。
5. **runbook 自动校验**：写 `tests/cacheDemoRunbook.test.py` 自动确认 runbook 中 4 个已知约束。

## 优先级依据

### 高优先级：B1-B4 演示关键 bug 修复

**原因**：6-05 bug 扫描发现的 4 个 bug 都是 BME 竞赛 PPT 演示现场容易被评委抓个正着的边缘场景：

- **B1 SSE 进度回退**：在长耗时推理时，heartbeat 心跳事件被前端误当成"进度"事件，会让进度条从 60% 突然回退到 30% 然后再涨回去，破坏演示视觉。
- **B2 取消后残留进度**：取消 job 后后端继续写 progress 事件或心跳，前端会显示"推理还在跑"或"取消失败"，让评委怀疑系统稳定性。
- **B3 后端模型状态不外露**：GUI 状态栏没法直接读 `/api/health.model_state`，需要在前端硬编码 fallback；评委问"模型加载好了吗"时无法即时回答。
- **B4 SSE 断连无重试**：网络抖动导致 EventSource 断开后，前端直接报错"推理失败"，但实际后端推理仍在跑；需要自动退避重连。

**影响范围**：`src/main.tsx` 的 `inferenceTimeline` / `createInferenceEventSource`、`server/main.py` 的 `cancel_job()` 与 `model_state` 字段。

### 高优先级：演示启动脚本化

**原因**：演示现场容易漏设 `SEGMENTATION_REFERENCE_CASES_JSON`、`SEGMENTATION_PERSISTENT_WORKER`、`SEGMENTATION_DEVICE` 等环境变量。`tools/start_local_demo.py` 自动 setenv + spawn backend/frontend，能避免现场翻车。

**影响范围**：`tools/start_local_demo.py`、`docs/demo-day-checklist.md`、`docs/local-cache-demo-runbook.md` 的卡片化展示。

### 高优先级：server mode gating 修复

**原因**：上一轮收口于 taxonomy fix，但服务器模式下创建 job 仍可能因本地 Windows `dataset.json/plans/checkpoint/python.exe` 缺失而 503。这会阻塞服务器模式的正常使用，演示现场切换 runtime_target=server 时会直接 503。

**影响范围**：`server/main.py` 中 `/api/segment/jobs` 与 `get_model_state()` 的路径检查逻辑。

### 高优先级：AMOS 0117 演示口径决策

**原因**：cache demo Phase A 命中的 `009d4efdc5f6` 是 2026-05-23 历史 review 状态预测（stomach Dice 0.556、mean_dice 0.891），但 stomach 0.556 是数据本身硬骨头（边界模糊），复跑 quality 不会显著改善。决策：接受现状，不复跑 AMOS 0117。正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。

**影响范围**：`docs/local-cache-demo-runbook.md` 的 AMOS 0117 演示口径段落、PPT 演示口径。

## 与其他 planning 文档的关系

- `.planning/2026-06-01-local-cache-demo/`：本地缓存演示已完成。
- `.planning/label-taxonomy-server-validation/`：taxonomy fix + server gating 已完成（6-06），validation 复跑是下一轮。
- `.planning/high-resolution-inference-optimization/`：推理已完成，优化方案是下一轮。
- `.planning/next-round-candidates/`：本目录是对 `next-round-candidates/` 6-05 版本的更新版，加入 6-06 收口后的新优先级与"AMOS 0117 决策：接受现状"。

## 执行顺序建议

1. **B1 SSE 进度回退修复**：影响演示视觉，第一优先。
2. **B2 取消后残留进度修复**：影响取消功能演示，第二优先。
3. **B3 后端模型状态对外可读**：影响状态栏展示，第三优先。
4. **B4 SSE 基础异常重试**：影响网络抖动场景，第四优先。
5. **演示启动脚本化**：把所有"演示现场手动设 env"前置，第五优先。
6. **server mode gating 6 路径修复**：让服务器模式不再因本地文件缺失而 503，第六优先。
7. **AMOS 0117 演示口径决策**：更新 runbook + 文档口径，第七优先。
8. **文档与验收口径再同步**：确保 9 份核心文档全部反映 6-06 现状。
9. **GitHub 推送 + 启动 GUI 验证**：`python tools/start_local_demo.py` 真启后端 + 前端，确认 4 端点全过。

---

*更新日期：2026-06-06*
