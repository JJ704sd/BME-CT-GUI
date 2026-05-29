# 2026-05-29 文档同步发现记录

## 已确认事实

- `origin/main` 已包含提交 `dafe400 fix: close segmentation validation regressions`。
- 本轮需要反映的代码现状：
  - 预测缓存只复用 NIfTI 结果，validation 按当前请求上下文重新计算或为空。
  - persistent worker stdout reader 已改为进程级共享队列。
  - 前后端不再输出上传文件名调试日志。
  - FLARE22 部分标签在至少两个明确错位 label 时可触发自动 remap。

## 审阅结论

- `README.md` 原先只写历史结果缓存，已补充“预测缓存”和“当前 validation”分离。
- `ACCEPTANCE.md` 的 2026-05-27 标签传输段落仍把临时日志写成后端修复，已改为历史排查手段并新增 2026-05-29 收口验收记录。
- `CODE_MODULE_GUIDE.md` 原先把 FLARE22 remap 写成离线指标、不是后端自动 validation，已改为后端自动 remap 现状和部分标签边界。
- `SEGMENTATION_RECENT_ROUNDS.md` 原先要求保留 `console.log`，已改为检查 job summary、`label_path` 和 validation 结果。
- `SEGMENTATION_METRICS_SUMMARY.md` 和 `SEGMENTATION_EXPERIMENT_COMPARISON.md` 已补充 2026-05-29 修复不改变历史指标，但改变后续解释口径。
- `REVIEW.md` 已保留历史排查事实，同时说明上传文件名日志已在第 47 节移除，并新增第 48 节记录本轮文档同步。

## 下一轮规划结论

- `.planning/next-round-candidates/` 已更新到 2026-05-29 项目现状。
- `.planning/label-scoring-optimization/` 已删除“保留 console.log 两周”的待办，改为 job state / validation summary 观察，并新增单 label 数据集 hint。
- `.planning/online-inference-followup/` 已记录 `dafe400` 基线、缓存 validation 语义和 persistent worker 真实速度待验证。
- `.planning/non-amos-acceptance-expansion/` 已补充部分标签 remap、单 label 边界和缓存 validation 口径。
