# 进度记录

## 2026-05-26

- 用户提出：点击在线推理按钮后，希望底部结合前后端实现实时推理进度条展示；本轮先按项目实际写规划文档，后续再操作。
- 已检查当前 Git 状态：工作树起始为干净状态，分支 `codex/plan-non-amos-acceptance`。
- 已确认本规划实施起点提交：`c4cabfb fix: keep orthogonal drag views live`；当前主分支已推进到 2026-05-29 的 validation/cache 修复基线。
- 已梳理前端：
  - `startSegmentation()` 已使用 `EventSource` 监听后端 job events。
  - 现有 `progress`、`inferenceStatus`、`logs` 可作为底部进度条的数据来源。
  - 底部 console 当前没有结构化进度条，仅显示切片缩略图和 4 条日志。
- 已梳理后端：
  - `/api/segment/jobs/{job_id}/events` 已通过 SSE 推送 `job.events`。
  - `push_event()` 已维护 `job.progress` 和 `job.stage`。
  - 真实推理主阶段可能长时间停留在 `20%`，因此后续应优先使用“阶段进度 + 已耗时 + 心跳”表达，不应伪造连续百分比。
- 已创建规划文件：
  - `.planning/realtime-inference-progress/task_plan.md`
  - `.planning/realtime-inference-progress/findings.md`
  - `.planning/realtime-inference-progress/progress.md`

## 下一步候选

等待用户确认规划后再进入实现。推荐第一轮只做前端底部进度条和结构化 timeline；第二轮按演示效果决定是否增加后端 heartbeat。

## 2026-05-26 实施记录

- 已按方案 A 完成第一阶段前端实现，未修改后端推理语义。
- `src/main.tsx` 新增：
  - `inferenceTimeline`：结构化阶段日志。
  - `inferenceStartedAt`：用于底部已耗时展示。
  - `inferenceProgressCopy`：集中生成底部 progress rail 文案。
  - `appendInferenceTimelineEntry()`：把 job 创建、SSE progress/complete/error、结果回填、取消和失败写入 timeline。
- 底部 `bottom-console` 在切片缩略图上方新增 `inference-progress-rail`，显示阶段、百分比、job id、推理模式、已耗时和最近阶段日志。
- `src/styles.css` 新增桌面/移动端 rail 样式；调试时发现初版 rail 让 sagittal/coronal canvas 高度从可读阈值以下压到 `130px`，已通过压缩 rail 垂直密度修复。
- diff 审查时发现初始 `progress=100` 会让等待态误显示 `100%`；已改为无 timeline 时等待态显示 `0%`。
- 测试按 TDD 执行：
  - `node tests/imagingLogic.test.ts` 先因缺少 `inferenceTimeline` 失败，后通过。
  - `node tests/browserLayout.test.ts` 先因缺少 rail 样式失败，后通过；期间发现并修复桌面 canvas 被压缩问题。
- 已更新 `README.md`、`CODE_MODULE_GUIDE.md`、`ACCEPTANCE.md`、`REVIEW.md`，记录底部实时推理进度功能、边界和验证结果。
- 已通过验证：
  - `node tests/imagingLogic.test.ts`
  - `node tests/browserLayout.test.ts`
  - `npm test`
  - `npm run build`

## 后续候选

- 若真实演示仍觉得 nnUNetv2 主体阶段 `20%` 停留太久，再进入第二阶段：后端增加 heartbeat 型 progress 事件，百分比保持阶段值，只补充已耗时、阶段 key 和可选资源快照。
