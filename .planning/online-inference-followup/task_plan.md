# 在线推理后续规划

**范围：** 记录 2026-05-25 fast / quality 对照之后的在线推理产品化工作。

**当前分支：** `main`

**当前基线：** commit `dafe400 fix: close segmentation validation regressions`

**核心规则：** `quality` 仍是默认和正式报告路径；`fast` 只是快速预览路径，必须明确标注“需人工复核”。

## 状态

- [x] 在 `REVIEW.md` 记录 fast vs quality 无缓存基线。
- [x] 在 `SEGMENTATION_METRICS_SUMMARY.md` 记录基准指标。
- [x] 将基线文档推送到 `origin/codex/update-ct-gui-prototype`。
- [x] 增加用户可见的推理模式选择。
- [x] 将所选推理 profile 贯穿 API、job state 和结果 summary。
- [x] 对 fast preview 结果显示清晰的“需人工复核”提示。
- [x] 在 UI 和后端 profile 串联后重新运行聚焦验证。
- [x] 实现后更新 `README.md`、`REVIEW.md` 和 `SEGMENTATION_METRICS_SUMMARY.md`。
- [x] 将可选推理 profile 后续改动合并并推送到 `origin/main`。

## Phase 1：产品化推理模式选择

目标：把 `quality` / `fast` 区别显式放进产品界面，而不是只依赖环境变量。

任务：

- [x] 检查当前 job 创建 UI 和后端请求 schema。
- [x] 增加两个模式选择：`quality` 和 `fast`。
- [x] 默认使用 `quality`。
- [x] 将 `fast` 标注为快速预览且需要复核。
- [x] 将所选 profile 写入 job state 和 `job_summary.json`。
- [x] 确保缓存 key 仍包含最终生效的 `inference_options`。

验收：

- [x] 默认提交使用 `quality`。
- [x] fast preview 提交使用 `fast`、`tile_step_size=1.0`，并在未被后端显式覆盖时关闭 TTA。
- [x] UI 和 job summary 中 fast 结果不会被误认为正式质量结果。

## Phase 2：基准记录纪律

目标：后续速度声明必须绑定可复现的测量记录。

任务：

- [x] 基准运行输出保留在 `.test-output/`。
- [x] 每个基准记录输入、checkpoint、profile、tile step、TTA 状态、缓存状态、job id、总耗时、阶段耗时、结果大小、资源快照和 validation 状态。
- [x] 有标签的参考病例记录 Dice、IoU、Hausdorff 以及 label 14/15 预测体素数量。
- [x] 区分原始模型指标和任何后处理指标。

验收：

- [x] `REVIEW.md` 包含决策级结论。
- [x] `SEGMENTATION_METRICS_SUMMARY.md` 包含数值对比。
- [x] `README.md` 只保留当前面向用户的用法，不承载完整实验日志。

## Phase 3：后处理实验门禁

目标：只把 label 14/15 假阳性作为显式后处理实验研究，不覆盖原始模型质量指标。

任务：

- [ ] 设计一个面向缺失或极小标签的小体积连通域过滤实验。
- [ ] 用现有 fast 输出中的 label 14/15 假阳性做离线试验。
- [ ] 同时报告原始指标和后处理指标。
- [ ] 不用过滤后的指标替换原始模型质量指标。

验收：

- [ ] 后处理输出有单独标识。
- [ ] 原始 fast 指标仍在文档中可见。
- [ ] 未在超过一个病例验证前，不修改产品默认行为。

## Phase 4：主分支基线验证

任务：

- [x] 从项目根目录运行 `npm test`。
- [x] 从项目根目录运行 `npm run build`。
- [x] 检查 `git status --short`。
- [x] 将已验证的 `main` 基线记录到 `progress.md`。

## 2026-05-28 现状补记

- 推理 profile 产品化已完成，当前仍沿用 `quality` 正式、`fast` 预览的口径。
- 后续在线推理重点转为远程 Linux GPU 部署、长耗时病例性能策略和报告/评估细节打磨。

## 2026-05-29 现状补记

- 缓存命中只复用预测结果，不再复用缓存来源 job 的 validation；在线推理文档中必须继续区分预测缓存耗时和当前标签验证结果。
- persistent worker reader 竞争问题已修复并通过轻量 shutdown smoke；真实连续无缓存推理速度仍需单独任务验证。
- 上传文件名调试日志已移除，后续线上排查应使用 job id、结构化状态和 `server/work` 输出。
