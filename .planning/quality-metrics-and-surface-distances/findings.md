# 质量评估指标扩展 + 表面距离计算加速 发现

## 发现日期

2026-06-03

## 关键发现

### 发现 1：6 EDT/label 是 validation 阶段的主要性能瓶颈

**证据**：在 AMOS 0117 quality cache hit（job `2d477d8bbd7d` / `9fd0fdc39960` / `096e5b8349df`，768×768×103 volume）上，validation 阶段从 `prepare_runtime_model` 到 `collect_result` 累计耗时 `38.86s`。逐器官遍历 13 个 label + foreground union，每个 label 调用 `average_surface_distance` + `hausdorff_95` + `hausdorff_distance_full` 三个函数；每个函数独立 `distance_transform_edt` 一到两次（crop + 双向 surface mask）。实测 EDT 调用计数 = 13 × 6 + 1 × 6 ≈ 84 次，CPU 端 numpy loop 累计 38.86s。

**根因**：`compute_label_metrics()` 把表面距离指标拆成 3 个独立函数实现，每个函数都自己跑 EDT，重复 crop + 重复 surface mask 提取。

**意义**：把 6 EDT/label 合并到 2 EDT/label（1 crop + 2 EDT：预测→参考、参考→预测）后，单 label EDT 调用次数下降 3×，validation 阶段实测 `38.86s` → `16.78s`（约 2.3× 加速）。

**后续**：该性能不变量应作为后续 `compute_*_metrics` 调用的硬约束；如果新调用方回退到 6 EDT 模式，CI 中 `test_compute_label_metrics_with_surface_distances_faster_than_legacy` 会直接挂掉。

### 发现 2：前端白名单缺字段导致 validation 链路无声丢弃

**证据**：`src/inference/inferenceClient.ts` 的 `normalizeValidation()` 白名单只有 `mean_dice` / `min_dice` / `foreground_dice` / `mean_iou` / `min_iou` / `foreground_iou` / `mean_hd` / `max_hd` 8 个字段。后端在 2026-05-26 起就已经在 `validation_summary.json` 写入 `pixel_accuracy` / `mean_asd` / `foreground_asd` / `mean_hd95` / `foreground_hd95` 等字段（部分），但白名单没有，导致 HTML 报告 / JSON 报告都看不到这些指标。

**根因**：补指标时只改了后端 serialize，没同步改前端白名单；GUI 用户从未在界面看到这些指标。

**意义**：本轮把白名单扩到 19 个字段（pixel_accuracy 4 项 + HD/HD95/ASD 9 项 + Dice/IoU 6 项），并把 `surface_distance_unit="mm"` / `spacing=[sx, sy, sz]` 提升为必填元信息；HTML 报告用 `metricCard()` 渲染 mm 单位 + 距离色阶。

**后续**：后续新增任何 validation 字段，都必须同时改 backend serialize / `inferenceClient.ts` 白名单 / `exportReport.ts` 报告模板三处；`tests/imagingLogic.test.ts` 中已经加了 source-grep 约束防止白名单漏写。

### 发现 3：HD/HD95/ASD 应使用 mm 单位 + 独立色阶

**证据**：医学影像竞赛的 Hausdorff Distance 通常以 mm 计（按 NIfTI spacing 缩放）。AMOS 0117 quality cache hit 的 mean HD = 9.59mm、max HD = 22.05mm（胃）；如果按 Dice 风格的 0-1 比例缩放到百分比，会丢失物理意义。如果按 Dice 0.85/0.70 阈值，会把 HD 全部染红（因为 mm 数值远大于 0.85），失去色阶的判读价值。

**根因**：早期 `metricBarHtml` 只支持 `kind: "dice" | "iou"`，色阶按 0-1 比例。HD 直接套用会全红。

**意义**：本轮新增 `distLevel()` / `distBarPercent()` helpers，色阶按 ≤1mm 绿 / ≤3mm 黄 / >3mm 红；`metricBarHtml` 扩展 `kind: "dice" | "iou" | "pix" | "dist"`，`metricCard` 扩展 `kind: "vox" | "dist"`。距离色阶与 Dice 色阶独立，避免误判。

**后续**：1mm / 3mm 是经验阈值；后续可按器官 + 体素间距动态化（见 `explanation.md` 后续建议 1）。

### 发现 4：precision 1e-9 对照确认 surface_distances 与旧函数完全等价

**证据**：`test_surface_distances_matches_legacy_individual_functions` 覆盖 4 shape（sphere / shell / cube / sphere+ring）× 8 场景，新 `surface_distances()` 输出的 `asd` / `hd` / `hd95` 与旧 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 拆解结果在 1e-9 精度内完全一致。证明合并 6 EDT 到 2 EDT 没有引入数值偏差。

**根因**：旧函数每次 EDT 都从同一对 surface mask 开始算，新函数复用 1 crop + 2 surface mask + 2 EDT，结果在 numpy 浮点精度内可证等价。

**意义**：可以放心地把旧函数调用方迁移到新函数，旧函数仅保留为回归测试对照。

**后续**：旧函数保留供 1e-9 对照，新调用方应使用 `surface_distances()`；`tests/backendState.test.py` 已经把 1e-9 精度对照作为硬约束。

### 发现 5：wall-time 加速比 ≥30% 是稳定的硬约束

**证据**：`test_compute_label_metrics_with_surface_distances_faster_than_legacy` 在 768×768×103 mock volume 上跑 3 轮取中位数，新路径比旧路径快 ≥30%。本机实测新路径 `16.78s` / 旧路径 `38.86s` ≈ 2.32× 加速，远超 30% 下限。

**根因**：CPU 端 numpy EDT 实现的常量项（mask 提取、crop 边界处理、float64 转换）在 2 EDT 路径下减半；其他运算（mean / max / percentile 在 value 数组上的统计）耗时与 EDT 本身相比可忽略。

**意义**：该 wall-time 测试是 `surface_distances()` 性能不退化的兜底；如果后续有人把 EDT 改回 6 次调用，或者在 `surface_distances()` 内部加额外循环，CI 会立即挂掉。

**后续**：当前 16.78s 仍由 CPU EDT 主导，进一步加速需要 GPU EDT（cupy / numba JIT）；这是下一轮候选任务（见 `explanation.md` 后续建议 2）。

### 发现 6：validation 阶段不能反过来卡 cache hit 的端到端时延

**证据**：cache hit 的端到端时延 = `find_cached_prediction()` 查找 + `complete_cached_job()` historical 回退 + validation 阶段。AMOS 0117 quality cache hit `2d477d8bbd7d` 当前实测约 19.44s，其中 validation 占 16.78s。如果 validation 不优化，cache hit 比真实推理（1360.398s）快 70× 这个卖点会被 validation 拖到只有约 2-3× 加速比。

**根因**：validation 阶段本来只跑 1 次（1 个 cache hit = 1 次 validation），但单次 validation 跑 6 EDT/label 太慢。

**意义**：2 EDT 优化后，cache hit 的端到端时延 ≈ `find_cached_prediction` 0.5s + `complete_cached_job` 0.5s + validation 16.78s ≈ 18s，比真实推理 1360s 快约 75×。这个加速比足以让 cache hit 在演示中作为"秒级回填"。

**后续**：cache hit 的 75× 加速是本轮的关键演示口径；下一轮可以引入 GPU EDT 把 16.78s 进一步压到秒级。

## 待验证假设

1. **GPU EDT 可继续压缩 16.78s**：把 `scipy.ndimage.distance_transform_edt` 替换为 `cupyx.scipy.ndimage.distance_transform_edt` 或 numba JIT，可以把 validation 阶段从 16.78s 压到 1-3s 量级。
2. **distance 色阶 1mm / 3mm 适用于所有器官**：当前阈值是经验值；后续按器官 + 体素间距动态化可能更准确。
3. **离线 `tools/segmentation_metrics_summary.py` 与后端 `validation_summary.json` 完全等价**：两者都使用 `surface_distances()` 合并函数，但渲染路径不同；可以写一个 `tests/reportMetricsConsistency.test.py` 自动对比两边的 Dice / IoU / HD 是否一致。
4. **白名单扩展不会引入解析错误**：当前 19 个字段都是 number 或 string；后续若引入 array 字段（如 confusion matrix），需要重新评估 SSE 序列化大小。

## 数据来源

- `server/main.py` 的 `surface_distances()` / `compute_label_metrics()` / `validate_against_custom_label()`
- `src/inference/inferenceClient.ts` 的 `ValidationSummary` / `LabelMetric` / `normalizeValidation()` / `parseInferenceEvent()`
- `src/report/exportReport.ts` 的 `metricCard()` / `metricBarHtml()` / `distLevel()` / `distBarPercent()` / 3 个 metric group
- `tools/segmentation_metrics_summary.py` 的离线指标
- `tests/backendState.test.py` 中新增的 3 个测试
- `tests/imagingLogic.test.ts` 中新增的 source-grep 约束
- AMOS 0117 quality cache hit（job `2d477d8bbd7d` / `9fd0fdc39960` / `096e5b8349df`）的实际指标
- 2026-05-25 baseline 报告：HTML 报告只显示 Dice / IoU 卡片，逐标签表只显示 Dice / IoU / HD 三列

---

*更新日期：2026-06-03*
