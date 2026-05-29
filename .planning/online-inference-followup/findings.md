# 在线推理后续发现

## 已确认的证据

- 最新已推送 main 提交：`dafe400 fix: close segmentation validation regressions`。
- 可选推理 profile 工作已从 `codex/update-ct-gui-prototype` 合并到 `main`，旧分支不再作为当前规划基线。
- fast 无缓存运行：
  - 运行目录：`.test-output\perf-fast-profile-20260525-1305`
  - job id：`6802e01f1a73`
  - 总耗时：`384.345s`
  - 主阶段：`persistent_worker=381.448s`
  - validation：`review`
  - mean Dice：`0.777243`
  - min Dice：`0.0`
  - mean IoU：`0.713592`
  - mean Hausdorff：`10.282058 mm`
  - label 14/15 预测体素：`664 / 670`
- quality 无缓存运行：
  - 运行目录：`.test-output\perf-quality-profile-20260525-1330`
  - job id：`b3c528cc9e20`
  - 总耗时：`1360.398s`
  - 主阶段：`persistent_worker=1357.677s`
  - validation：`passed`
  - mean Dice：`0.924780`
  - min Dice：`0.846569`
  - mean IoU：`0.865088`
  - mean Hausdorff：`7.716048 mm`
  - label 14/15 预测体素：`0 / 0`

## 决策

- `quality` 是默认和正式结果路径。
- `fast` 只允许作为快速预览或演示路径。
- fast preview 必须明显标注“需人工复核”。
- 前端 job 提交现在按任务发送 `inference_profile`；后端环境变量仍作为 fallback 默认值。
- 最终生效的 `inference_options` 会写入创建响应、job state、SSE complete 事件、`job_summary.json` 和 cache key 输入。
- 当前 AMOS 0117 对照中，label 14/15 小体积假阳性是 fast profile 的已知风险。
- 任何 label 14/15 过滤都必须标注为 `postprocess`，不能替代原始模型输出。
- 任何速度提升声明都必须绑定同输入、同 checkpoint、同脚本和同缓存状态的基准运行。

## 约束

- 真实 CT、NIfTI、checkpoint 和推理输出只保留在本地，并被 Git 忽略。
- `.test-output`、`nnunetv2_files` 和 `server/work` 不得提交。
- Cache key 必须包含 checkpoint 身份和最终生效的推理参数。
- 旧 AMOS 缓存只有在 `job_summary.json` 中存在匹配 `cache_key` 时才可复用。
- 缓存命中后的 Dice/validation 必须按当前请求标签重新计算；不能沿用缓存来源 job 的旧指标。

## 待确认问题

- label 14/15 后处理过滤至少需要多少病例验证，才能进入默认产品路径？
- 是否需要把 warm-cache 的 quality / fast 耗时单独列为演示对照，还是首轮体验仍只看 no-cache？
- 下一批用于扩展验收的非 AMOS 本地 CT 病例应选哪些？

## 2026-05-28 补记

- 自动 taxonomy remap 已让 FLARE22 标签上传后的在线验证可解释，job `a717dacf42d3` mean Dice 为 `0.926`。
- 后续在线推理规划应同时关注性能、远程部署和跨数据集评估解释，不再重复实现 profile 选择。

## 2026-05-29 补记

- 预测缓存和 validation 语义已拆开：缓存命中仍能快速回填 NIfTI，但当前标签的 Dice 需要重新计算。
- persistent worker 的 stdout reader 改为共享队列；后续仍需真实无缓存连续推理对照来评估速度。
- 上传文件名调试日志已移除，后续标签链路排查依赖 job state、`label_path` 和 validation summary。
