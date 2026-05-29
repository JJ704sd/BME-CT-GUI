# 实时推理进度展示规划

**日期：** 2026-05-26  
**当前分支：** `codex/plan-non-amos-acceptance`  
**实施起点基线：** `c4cabfb fix: keep orthogonal drag views live`；当前主分支已推进到 2026-05-29 的 validation/cache 修复基线。
**范围：** 点击“运行分割/在线推理”后，在底部“切片与流程日志”区域展示实时推理进度条、当前阶段和阶段日志。  
**原则：** 不伪造模型内部精确百分比；进度条基于后端 SSE 阶段事件，长时间 nnUNetv2 推理阶段用“运行中/耗时/心跳”表达。
**实施状态：** 已完成前端底部 progress rail、结构化 `inferenceTimeline`、SSE 阶段日志写入、后端 heartbeat 和文档收尾。后续只保留更细粒度进度展示作为候选增强，不伪造 nnUNetv2 内部 patch 级进度。

## 背景与现状

当前前后端已经具备在线推理进度基础：

- 前端 `src/main.tsx` 在 `startSegmentation()` 中创建 job，并通过 `EventSource(/api/segment/jobs/{job_id}/events)` 监听 SSE。
- 前端已有 `progress`、`inferenceStatus`、`logs` 状态；右侧“分割控制”面板显示运行百分比，底部只显示最多 4 条文本日志。
- `src/inference/inferenceClient.ts` 已定义 `InferenceEvent`，可解析 `progress`、`complete`、`error`。
- 后端 `server/main.py` 的 `push_event()` 会把事件写入 `job.events`，`job_events()` 每 `0.2s` 输出 SSE。
- 后端真实推理目前主要阶段为 `8/14/20/90/96/100`；其中 `20% -> 90%` 对应 nnUNetv2 主体推理，可能持续数分钟到十几分钟。

因此下一步不需要重建通信链路，主要是把已有进度信号变成底部可视化进度体验，并补足长耗时阶段的“仍在运行”反馈。

## 方案选型

### 方案 A：前端优先，复用现有 SSE

在底部 console 增加进度条、当前阶段、job id、推理模式和阶段日志。只使用现有 `progress/stage/complete/error` 事件。

优点：改动小，风险低，能快速完成演示。  
缺点：真实推理阶段会长时间停在 `20%`，只能靠动效和耗时提示说明任务仍在运行。

### 方案 B：增加后端心跳事件

保留现有阶段百分比，同时后端在长耗时推理阶段定期发出 heartbeat 型 progress 事件，包含相同百分比、已耗时、阶段名和可选资源快照。

优点：底部进度条能持续显示“后端仍活跃”，更适合真实病例演示。  
缺点：需要调整后端运行过程或监控线程，并扩展前端事件类型。

### 方案 C：纯演示平滑百分比

前端在 `20% -> 90%` 之间用定时器平滑推进。

优点：视觉上最流畅。  
缺点：容易误导使用者，以为这是 nnUNetv2 真实内部进度。除非明确标为“演示估算”，否则不采用。

**当前结论：** 方案 A 和方案 B 均已落地；前端使用阶段进度和已耗时表达活跃状态，后端 heartbeat 每 10 秒发送已耗时和资源快照。暂不采用方案 C。

## 目标体验

点击在线推理按钮后，底部区域从“在线演示模式”切换为“推理运行中”，显示：

- 一条横向进度条：使用后端 SSE `progress` 百分比。
- 当前阶段：例如“nnUNetv2 命令运行中”或“常驻 nnUNetv2 worker 推理中”。
- job id：便于和后端 `server/work`、`.test-output`、文档记录对应。
- 推理模式：`quality` 或 `fast`，其中 `fast` 保持“需人工复核”提示。
- 已耗时：前端从提交成功开始计时；收到 heartbeat 时优先使用后端 `elapsed_seconds`。
- 阶段日志：保留最近若干条进度、验证、资源和失败信息。

缓存命中时进度条可以快速到 `100%`，并显示“命中历史缓存”。失败或取消时，进度条停止并展示错误摘要，不自动伪装成功。

## 前端实施计划

1. 新增或整理前端状态：
   - `inferenceTimeline`：结构化阶段日志，替代仅靠字符串 `logs` 判断。
   - `inferenceStartedAt`：用于显示当前 job 已耗时。
   - `inferenceProgressCopy`：集中生成底部进度条所需文案。
2. 在 `startSegmentation()` 中：
   - job 创建成功后初始化 timeline。
   - 每个 SSE progress/complete/error 事件写入 timeline。
   - complete 后保留最终进度、耗时、资源和验证摘要。
   - error/cancel 后保留失败状态和 `log_tail` 摘要。
3. 在底部 `bottom-console` 中：
   - 在 `console-head` 与 `footer-slices` 之间新增 `inference-progress-rail`。
   - 运行中显示 progress bar、阶段、耗时和 job id。
   - 未运行时显示最近一次结果或“等待在线推理”。
4. 样式要求：
   - 不遮挡三视图，不压缩右侧控制面板。
   - 保持当前深色医学工作站风格。
   - 移动端降级为垂直堆叠。

## 后端实施计划

后端心跳已经实现，当前行为如下：

1. progress event 字段：
   - `elapsed_seconds`
   - `phase_key`
   - `resource_latest`
   - `heartbeat: true`
2. 在真实推理长阶段中发送心跳：
   - `persistent_worker` 或 `nnunet_process` 运行期间每 10 秒发送一次事件。
   - 百分比保持当前阶段值，不伪造内部完成度。
   - 可附带 GPU/内存快照，复用已有 `record_job_resource_snapshot()` 机制。
3. 保证取消、失败、complete 事件仍为终态事件，前端可停止计时和动效。

## 测试与验收

前端测试：

- `tests/imagingLogic.test.ts` 增加源码约束：底部存在结构化进度条、SSE progress 写入 timeline、失败事件保留日志。
- `tests/browserLayout.test.ts` 增加底部进度条布局 smoke，确保桌面和移动端不遮挡主要视图。

后端测试：

- `tests/backendState.test.py` 保留现有 SSE 行为测试。
- 心跳测试覆盖长任务会推送 heartbeat progress，取消/失败/complete 仍结束 stream。

手工验收：

- 点击“运行分割流程”后底部立即出现进度条。
- 真实 nnUNetv2 阶段长时间运行时，界面仍显示“运行中”和已耗时。
- 完成后进度为 `100%`，结果下载并回填三视图。
- 缓存命中、失败、取消三种路径都有明确底部状态。

## 文档收尾

实现后需要更新：

- `README.md`：说明底部实时进度条基于 SSE 阶段事件。
- `CODE_MODULE_GUIDE.md`：补充前端 timeline 和后端 SSE/heartbeat 代码讲解。
- `ACCEPTANCE.md`：补充在线推理进度条验收记录。
- `REVIEW.md`：记录该功能的范围、限制和验证结果。

## 非目标

- 不解析 nnUNetv2 内部 patch 级进度。
- 不修改模型、权重、Dice/IoU/Hausdorff 指标计算。
- 不把估算动画写成真实推理百分比。
- 不提交真实 CT、NIfTI、checkpoint 或推理输出。
