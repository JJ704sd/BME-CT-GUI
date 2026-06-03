# 质量评估指标扩展 + 表面距离计算加速 进度

## 2026-06-03：质量评估指标扩展 + 表面距离计算加速 完成

**状态：** 全部完成。把 quality 评估报告补齐到 6 类医学影像主流指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD），同时把单 label 表面距离计算从 6 次 `distance_transform_edt` 合并到 2 次，validation 阶段实测 38.86s → 16.78s（约 2.3× 加速）。

**背景：** 验收指南要求 6 类医学影像主流指标同时出现；2026-05-25 baseline 的 HTML 报告只有 Dice / IoU 卡片，逐标签表也只有 Dice / IoU / HD 三列，前端 `inferenceClient.ts` 的白名单不全。同时，缓存命中路径下的实测发现 validation 阶段耗时 38.86s，比一次 quality 推理（1360.398s）的 1/35 还慢 10 倍以上，逐器官遍历 + 6 EDT/label 是主要瓶颈。

## 本轮已完成

### 1. 后端新函数 [完成]

- [x] `server/main.py` 新增 `surface_distances(prediction_mask, reference_mask, spacing_tuple)`：1 crop + 2 surface mask + 2 EDT（forward / backward），再用 value 数组派生 `asd` / `hd` / `hd95` / `forward_*` / `backward_*`
- [x] 保留 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 为 legacy
- [x] `compute_label_metrics()` 单 label 改用 `surface_distances()`
- [x] foreground metrics 也走 `surface_distances()`（非全 volume union mask）

### 2. validation 字段扩展 [完成]

- [x] `validation_summary.json` 增补 12 个新字段：pixel_accuracy / mean_pixel_accuracy / min_pixel_accuracy / foreground_pixel_accuracy、mean_asd / max_asd / foreground_asd、mean_hd / max_hd / foreground_hd、mean_hd95 / max_hd95 / foreground_hd95、surface_distance_unit="mm"、spacing=[sx, sy, sz]
- [x] per-label 增补 pixel_accuracy / asd / hd / hd95
- [x] spacing 字段按 NIfTI header 的 `pixdim[1:4]` 写入（单位 mm）

### 3. 前端白名单 [完成]

- [x] `src/inference/inferenceClient.ts` 的 `ValidationSummary` / `LabelMetric` 类型增补上述字段
- [x] `normalizeValidation()` 加入白名单
- [x] `parseInferenceEvent()` 在 complete 事件里透传新字段
- [x] `surface_distance_unit` / `spacing` 解析为 string / number[]

### 4. HTML 报告 [完成]

- [x] `src/report/exportReport.ts` 新增 3 个 metric group：区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD（共 19 张卡片）
- [x] HD/HD95/ASD 卡片使用 mm 单位 + ≤1mm 绿 / ≤3mm 黄 / >3mm 红色阶
- [x] 逐标签表新增 4 列：像素准确率、ASD (mm)、HD95 (mm)、HD (mm)
- [x] 新增 `distLevel()` / `distBarPercent()` helpers
- [x] `metricBarHtml` 扩展 `kind: "dice" | "iou" | "pix" | "dist"`
- [x] `metricCard` 扩展 `kind: "vox" | "dist"`
- [x] 报告元信息 chips 显示 `spacing=[sx, sy, sz] mm` 与 `surface_distance_unit=mm`

### 5. 离线口径 [完成]

- [x] `tools/segmentation_metrics_summary.py` 复用 `surface_distances()` 合并函数
- [x] 离线脚本生成的 Dice / IoU / Pixel Accuracy / HD / HD95 / ASD 与后端在线 validation 完全一致

### 6. 回归测试 [完成]

- [x] `tests/backendState.test.py` 新增 `test_surface_distances_matches_legacy_individual_functions`（4 shape × 8 场景 1e-9 精度对照）
- [x] `tests/backendState.test.py` 新增 `test_surface_distances_uses_fewer_distance_transforms_than_legacy`（patch `scipy.ndimage.distance_transform_edt` 计数恒为 2）
- [x] `tests/backendState.test.py` 新增 `test_compute_label_metrics_with_surface_distances_faster_than_legacy`（wall-time 加速比 ≥30% 断言）
- [x] `tests/imagingLogic.test.ts` 新增全部 12 个新字段的 source-grep 约束
- [x] `tests/imagingLogic.test.ts` 新增 `parseInferenceEvent()` complete 事件解析值测试

### 7. 文档同步 [完成]

- [x] `README.md`：当前运行状态加 2026-06-03 节；主要功能描述更新到 6 类医学影像指标
- [x] `CLAUDE.md`：关键不变量加 6 类指标和 `surface_distances` 2 EDT 不变量；文档协作清单加 6 类指标相关条目
- [x] `AGENTS.md`：当前运行状态加 2026-06-03 节；进行中加"质量评估指标新口径推广"
- [x] `REVIEW.md`：新增"五十六、2026-06-03 质量评估指标扩展 + 表面距离计算加速"节
- [x] `ACCEPTANCE.md`：新增"2026-06-03 质量评估指标扩展 + 表面距离计算加速验收记录"节
- [x] `CODE_MODULE_GUIDE.md`：当前运行状态加 2026-06-03 节；报告导出节更新到 6 类指标
- [x] `SEGMENTATION_RECENT_ROUNDS.md`：第 1 轮替换为"质量评估指标扩展 + 表面距离计算加速"；近三轮趋势表更新
- [x] `SEGMENTATION_EXPERIMENT_COMPARISON.md`：数据来源列表加 2026-06-03 描述；实验名称说明加新行
- [x] `SEGMENTATION_METRICS_SUMMARY.md`：当前运行状态加 2026-06-03 节；当前 AMOS 基线聚合指标加 6 类新指标；逐标签指标加 4 列；备注加新口径说明

### 8. planning 4 文档 [完成]

- [x] `.planning/quality-metrics-and-surface-distances/explanation.md`
- [x] `.planning/quality-metrics-and-surface-distances/findings.md`
- [x] `.planning/quality-metrics-and-surface-distances/progress.md`（本文档）
- [x] `.planning/quality-metrics-and-surface-distances/task_plan.md`

## 当前未完成

### 本轮范围内但未做

- [x] 8 个修复点全部完成
- [x] 9 份核心文档同步
- [x] 4 份 planning 文档落地
- [x] 自动验证：`python tests/backendState.test.py` / `npm test` / `npm run build` 通过

### 本轮范围外的后续工作

- [ ] GPU EDT 加速（`cupyx.scipy.ndimage.distance_transform_edt` 或 numba JIT），把 16.78s 进一步压到 1-3s
- [ ] 距离阈值按器官动态化（食管、肾上腺等小器官阈值放宽到 2mm / 5mm）
- [ ] class-balanced accuracy / frequency-weighted IoU 进一步区分小器官与大器官
- [ ] 离线/在线报告一致性测试（`tests/reportMetricsConsistency.test.py`）

## 收尾步骤

- [x] 9 份核心文档同步
- [x] 4 份 planning 文档落地
- [ ] git status 全审 + commit
- [ ] git push 到 `https://github.com/JJ704sd/BME-CT-GUI`

## 当前结论

2026-06-03 质量评估指标扩展 + 表面距离计算加速已落地 8 个修复点，质量评估报告已补齐到 6 类医学影像主流指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD），HTML 报告新增 3 个 metric group 共 19 张卡片、逐标签表现新增 4 列；`surface_distances()` 2 EDT 实现让 validation 阶段实测 38.86s → 16.78s（约 2.3× 加速）；3 个新增回归测试覆盖 1e-9 精度、EDT 调用计数恒为 2、wall-time 加速比 ≥30% 三个硬约束；本轮不修改 nnUNetv2 推理、缓存复用、SSE 协议、影像量化或历史 AMOS `quality` profile `b3c528cc9e20`（mean Dice 0.924780）、FLARE22 自动 remap `a717dacf42d3`（mean Dice 0.926）、FLARE22 离线 remap `86b0153d0a73`（mean Dice 0.893127）三套历史基线数值。下一步进入 git 提交收尾。

---

*更新日期：2026-06-03*
