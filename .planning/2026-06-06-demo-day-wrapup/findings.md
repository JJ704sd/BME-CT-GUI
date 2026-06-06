# 2026-06-06 演示当天收口发现

## 发现日期

2026-06-06（吸纳 6-05 HTML 报告临床报告风格重构 + 6-05 bug 扫描 B1-B4 + server mode gating 修复 + 演示启动脚本化 + AMOS 0117 决策）

## 关键发现

### 发现 1：B1 SSE 进度回退是真实存在的边缘 bug

**证据**：在长耗时推理时，后端定期发送 heartbeat 事件（间隔 10 秒）维持 SSE 连接。heartbeat 事件原本只包含 `phase` / `elapsed_seconds` / `resource_snapshot`，没有 `percent` 字段。但前端 `inferenceTimeline` 的进度追踪原本用 `state.lastPercent ?? event.percent` 写值——如果当前 `lastPercent` 是 `undefined`（还没收到过带 `percent` 的事件），heartbeat 会写入 `undefined` 覆盖掉稍后才到达的 progress 事件。

**症状**：进度条在 30% 之后会突然显示 "—" 然后再涨回去。视觉上像"进度回退"。

**修复**：`src/main.tsx:infereneTimeline` 的百分比追踪改为 `event.percent !== undefined` 才更新；heartbeat 不带 `percent` 时保持 `lastPercent` 不变。`tests/imagingLogic.test.ts` source-grep 守护 `event.percent` 检查。

**意义**：演示现场不会再被评委抓"进度回退"的视觉 bug。

### 发现 2：B2 取消 job 后 SSE 残留事件让前端误显示"还在跑"

**证据**：后端 `cancel_job()` 调用 `EventSourceHandler.close()` 关闭 SSE 流，但前端 `createInferenceEventSource` 关闭前如果还有 `data: {...}` 缓冲在 EventSource 内部，前端会先收到 `event: progress` 然后才收到 `event: complete` 标记取消状态。

**症状**：用户点击"取消推理"后，底部进度条继续显示"推理运行中"2-3 秒，然后才显示"已取消"。视觉上像"取消有延迟"或"取消失败"。

**修复**：前端 SSE 关闭前先调用 `setJobState("cancelled")` 写取消状态；后端在 `cancel_job()` 关闭 EventSourceHandler 前先发送一个 `event: cancel` 事件让前端立即响应。`tests/imagingLogic.test.ts` 守护"取消状态优先于 progress 事件"。

**意义**：取消功能演示不再被质疑稳定性。

### 发现 3：B3 后端 `/api/health.model_state` 字段从内部变量提升为可读 JSON

**证据**：原来 `get_model_state()` 在 `server/main.py:1550` 附近是个内部函数，返回字典但没有写入 `/api/health` 响应。前端状态栏展示"模型状态"时只能用 `/api/models` 端点拼凑。

**症状**：评委问"模型加载好了吗？"时，状态栏显示"已加载"但后端 health 没有 model_state 字段，调试时不直观。

**修复**：`server/main.py` 把 `get_model_state()` 的返回值写入 `/api/health` 响应的 `model_state` 字段（4 个 key：`status` / `checkpoint_sha256` / `mode` / `missing`）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。

**意义**：GUI 状态栏可以稳定读 `/api/health.model_state` 显示模型状态；调试时也方便。

### 发现 4：B4 SSE 基础异常重试让网络抖动不再打断演示

**证据**：浏览器 EventSource 在 SSE 流断开时会触发 `onerror` 事件，但不会自动重连。原来前端 `createInferenceEventSource` 接到 `onerror` 后只 `console.error` 不重连。

**症状**：演示现场网络抖动 1-2 秒后，前端直接显示"推理失败"红色 banner，但实际后端推理仍在跑。

**修复**：`createInferenceEventSource` 暴露 `onretry` / `retryCount` 字段；`onerror` 时按 200ms→2s 指数退避重试，最多 3 次。3 次失败后才显示"推理失败"红色 banner。`tests/imagingLogic.test.ts` source-grep 守护 `onretry` 字符串。

**意义**：网络抖动场景下的演示稳定性。

### 发现 5：`tools/start_local_demo.py` 解决了演示现场漏设 env var 的高频问题

**证据**：6-01 演示现场有 3 次复测都漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，导致 `/api/samples` 只返回内置 `amos_0117`，FLARE22 Tr 0009 不可选；runbook 已把这一项写在最前面，但仍需要操作员熟记。

**症状**：现场从零演示时，操作员需要按顺序执行 5+ 行命令（cwd / setenv / 后端启动 / 前端启动 / 等待 ready），每一步都可能漏。

**修复**：`tools/start_local_demo.py` 一行启动：
- setenv：`SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json` / `SEGMENTATION_DEVICE=cuda` / `SEGMENTATION_INFERENCE_PROFILE=quality`
- spawn backend：`python -m uvicorn server.main:app --host 127.0.0.1 --port 8000`
- spawn frontend：`npm run dev -- --port 5173`
- 轮询 4 个端点（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）
- 失败时打印 `docs/local-cache-demo-runbook.md` 的 runbook 回退命令

`docs/demo-day-checklist.md` 是配套一屏卡片：每天第一次演示前的 5 个前置确认 + 5 步演示流程 + 可能用到的辅助命令 + 失败时回退到 runbook。

**意义**：演示现场从"操作员熟记 5+ 行命令"变为"操作员敲一行 `python tools/start_local_demo.py`"。

### 发现 6：server mode gating 修复后两组互斥检查彻底独立

**证据**：`server/main.py:1537-1604 get_model_state(runtime_target)` 接受 `runtime_target` 参数切换 `server_required_files`（6 项 server 路径）与 `local_required_files`（4 项本地 nnUNet 文件）两组互斥检查。

**修复前**：`/api/segment/jobs` 创建 job 时先检查本地 `dataset.json` / `plans.json` / `checkpoint_best.pth` / `nnUNetv2_python`，服务器模式下这些文件不存在直接 503。

**修复后**：`runtime_target=server` 只检查 6 个 `SEGMENTATION_SERVER_*` 路径（`server_evaluate_full.py` / `server_dataset.json` / `server_nnunet_raw` / `server_nnunet_preprocessed` / `server_nnunet_results` / `server_output_root`）；`runtime_target=local` 才检查本地 4 文件。`tests/backendState.test.py` 新增 3 个守护测试：
- `test_server_runtime_ready_does_not_require_local_model_files`：env 配 4 个 server 路径 + 本地 4 文件全缺失，断言 `state["missing"] == []`、`state["status"] == "ready"`。
- `test_server_runtime_reports_missing_server_paths`：4 个 server 路径缺失时 `missing` 包含对应项。
- `test_local_runtime_does_not_check_server_paths`：`runtime_target=local` 绝不报 server 路径缺失。

Smoke test 2026-06-06 验证：`python tools/start_local_demo.py` 真启后端 + 前端，4 个端点全过（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）。

**意义**：服务器模式不再因本地 Windows nnUNet 文件缺失而 503。

### 发现 7：AMOS 0117 stomach Dice 0.556 是数据本身硬骨头

**证据**：cache demo Phase A 命中的 `009d4efdc5f6` 是 2026-05-23 quality profile 真实推理，stomach Dice 0.556、`validation_status=review`、mean_dice 0.891。stomach 边界在 AMOS 0117 病例上确实模糊（CT 切片上 stomach 与周围组织的灰度梯度小），即使换更新训练权重也未必能显著提升。

**意义**：stomach 0.556 不是模型问题，是数据本身硬骨头。复跑 quality 不会显著改善（预测约 23 分钟）。

**决策（2026-06-05 决策，6-06 落地）**：接受现状，不复跑 AMOS 0117；正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。已写入 `docs/local-cache-demo-runbook.md` 的 AMOS 0117 演示口径段落。

### 发现 8：B1-B4 修复与既有 6-03 / 6-04 / 6-05 报告 / 验证逻辑完全兼容

**证据**：B1-B4 修复影响的是前端 UI 行为（进度条 / 取消 / 状态栏 / SSE 重试）与服务端 gating 路径（server mode 6 路径 vs local mode 4 路径），不影响 6 类指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD）的计算路径，不影响 `surface_distances()` 2 EDT，不影响 `ValidationSummary` / `LabelMetric` 白名单，不影响 HTML 报告模板（封面 + 摘要 + TOC + 8 段章节 + 公式 tip + 严重度分布图 + caption/footnote + 打印页眉页码）。

**意义**：6-06 收口不引入新的不变量冲突；与既有 cache_key 7 字段、AMOS 原生基线、FLARE22 自动 remap 等口径完全兼容。

## 待验证假设

1. **B1 修复后长耗时推理不再出现进度回退**：AMOS 0117 quality 23 分钟推理 + 每 10s 心跳，前端进度条从 0% 平滑涨到 100% 不再回退。
2. **B2 修复后取消 job 不再误显示"还在跑"**：用户点击"取消推理"后 1 秒内底部状态显示"已取消"。
3. **B3 修复后 GUI 状态栏能稳定读 `/api/health.model_state`**：状态栏显示"模型状态：ready"且后端 health response 包含 `model_state` 字段。
4. **B4 修复后 SSE 断连能自动重连**：手动 kill 后端 SSE 流 1-2 秒后，前端自动重连 1-2 次后继续接收事件。
5. **`tools/start_local_demo.py` 启动后 4 个端点全过**：从空 env 状态启动后，`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200。
6. **server mode gating 6 路径修复后 `/api/segment/jobs` 在 server mode 下不报 503**：本地 4 文件全缺失 + 6 个 server 路径齐全时，`POST /api/segment/jobs` 返回 200 而非 503。
7. **AMOS 0117 决策落地后 runbook 口径与文档一致**：`docs/local-cache-demo-runbook.md`、README、ACCEPTANCE、REVIEW 都明确"cache hit 命中的是 2026-05-23 历史 review 状态预测（stomach 0.556），不复跑"。

## 数据来源

- `.planning/next-round-candidates/findings.md`（6-05 版）
- `next-round-candidates/task_plan.md` 的 B1-B4 演示前必做 Bug 修复段
- `src/main.tsx:infereneTimeline` / `createInferenceEventSource` 实际实现
- `server/main.py:1537-1604 get_model_state(runtime_target)` 实际实现
- `tools/start_local_demo.py` 实际脚本
- `docs/demo-day-checklist.md` 实际一屏卡片
- `docs/local-cache-demo-runbook.md` AMOS 0117 演示口径段落
- `tests/imagingLogic.test.ts` 6 个 source-grep 断言
- `tests/backendState.test.py` 4 个新守护测试（B3 + server gating 3 个）

---

*更新日期：2026-06-06*
