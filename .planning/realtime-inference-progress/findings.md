# 调研记录

## 前端现状

- `src/main.tsx` 已维护 `progress`、`logs`、`inferenceStatus`。
- `startSegmentation()` 已创建后端 job，并通过 `EventSource` 监听 `/api/segment/jobs/{job_id}/events`。
- 每个 progress 事件会调用 `setProgress(parsed.progress)`、`setInferenceStatus(...)` 和 `setLogs(...)`。
- 当前右侧“分割控制”只用 `detail-chip` 展示百分比；底部 console 只有文本日志和切片缩略图，没有可视化进度条。
- `src/inference/inferenceClient.ts` 已有 `InferenceEvent`、`parseInferenceEvent()`、`getInferenceStatusCopy()`，后续可以在这里扩展可选字段。

## 后端现状

- `server/main.py` 的 `Job` 保存 `progress`、`stage`、`events`、`phase_timings`、`resource_snapshots`、`log_tail`。
- `push_event()` 会把 progress/complete 事件同步写回 job 当前进度和阶段。
- `job_events()` 使用 `StreamingResponse` 输出 SSE，轮询间隔为 `0.2s`。
- 真实推理阶段事件主要是：
  - `8`：任务已提交到本地 nnUNetv2
  - `14`：已准备项目指定训练权重
  - `20`：nnUNetv2 命令运行中或常驻 worker 推理中
  - `90`：整理 nnUNetv2 输出
  - `96`：使用 AMOS 标准答案验证推理结果
  - `100`：真实 nnUNetv2 推理结果已生成
- 当前 `build_predict_command()` 使用 `--disable_progress_bar`，因此不能直接读取 nnUNetv2 的控制台进度条当作真实细粒度百分比。

## 设计约束

- 用户希望进度展示位于底部，并和前后端真实推理链路结合。
- 项目已有真实推理耗时记录，未缓存 `quality` 可能达到数分钟到十几分钟；底部 UI 必须处理长时间停留在同一阶段的情况。
- `fast` profile 已被文档定义为快速预览且需人工复核；进度 UI 不能弱化这个边界。
- 当前仓库不提交真实 NIfTI、checkpoint、`server/work` 或 `.test-output` 输出。

## 推荐判断

先做前端可视化进度条，复用已有 SSE；如果演示时仍感觉“20% 停太久”，再加后端 heartbeat。这样可以最快提供可见改进，同时保持进度含义真实。

## 实施后发现

- 第一阶段前端方案足以把已有 SSE 阶段事件转为底部可视化进度体验，不需要修改 `/api/segment/jobs/{job_id}/events`。
- 底部进度 rail 的垂直占用会直接压缩桌面三视图高度；桌面 1366x768 下需要保持 rail 紧凑，否则 sagittal/coronal canvas 会低于既有 `140px` 可读阈值。
- 失败事件应保留 `log_tail` 摘要到 timeline；否则底部状态只能看到泛化错误，无法和后端日志快速对应。
