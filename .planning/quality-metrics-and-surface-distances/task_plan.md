# 质量评估指标扩展 + 表面距离计算加速 任务规划

**范围：** 把 quality 评估报告补齐到 Dice、IoU、Pixel Accuracy、Hausdorff Distance（含 HD95、ASD）等 6 类医学影像主流指标；同步收紧 6 EDT/label 的性能瓶颈，把每个 label 的 `distance_transform_edt` 调用从 6 次合并到 2 次。

**当前状态：** 8 个修复点全部完成；9 份核心文档同步；4 份 planning 文档落地；自动验证通过。下一轮候选：GPU EDT 加速、距离阈值按器官动态化、离线/在线报告一致性测试。

---

## 本轮已完成（2026-06-03）

1. `server/main.py` 新增 `surface_distances(prediction_mask, reference_mask, spacing_tuple)`：1 crop + 2 EDT/label
2. 保留 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 为 legacy 供回归测试对照
3. `compute_label_metrics()` 单 label 改用 `surface_distances()`；foreground metrics 也走 `surface_distances()`
4. `validation_summary.json` 增补 12 个新字段：pixel_accuracy / mean_pixel_accuracy / min_pixel_accuracy / foreground_pixel_accuracy、mean_asd / max_asd / foreground_asd、mean_hd / max_hd / foreground_hd、mean_hd95 / max_hd95 / foreground_hd95、surface_distance_unit="mm"、spacing=[sx, sy, sz]
5. `src/inference/inferenceClient.ts` 的 `ValidationSummary` / `LabelMetric` 增补上述字段；`normalizeValidation()` 加入白名单；`parseInferenceEvent()` 在 complete 事件里透传
6. `src/report/exportReport.ts` 新增 3 个 metric group（区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD，共 19 张卡片）和 4 个逐标签列（像素准确率、ASD (mm)、HD95 (mm)、HD (mm)）
7. `tools/segmentation_metrics_summary.py` 复用 `surface_distances()`，离线/在线口径完全一致
8. `tests/backendState.test.py` 新增 3 个测试（1e-9 精度对照、EDT 调用计数恒为 2、wall-time 加速比 ≥30% 断言）；`tests/imagingLogic.test.ts` 新增全部新字段的 source-grep 约束和 `parseInferenceEvent()` complete 事件解析值测试
9. 9 份核心文档同步质量评估指标扩展 + 表面距离计算加速描述
10. 4 份 planning 文档落地（`explanation.md` / `findings.md` / `progress.md` / `task_plan.md`）

---

## 推荐下一轮任务

### 1. GPU EDT 加速

**优先级：** 中

**前置文档：** 本目录 `findings.md` 待验证假设 1

**目标：** 把 `scipy.ndimage.distance_transform_edt` 替换为 GPU 端实现（`cupyx.scipy.ndimage.distance_transform_edt` 或 numba JIT），把 validation 阶段从 16.78s 进一步压到 1-3s。

**关键步骤：**

1. 评估 RTX 4060 Laptop 上 `cupyx.scipy.ndimage.distance_transform_edt` 的性能与显存占用（768×768×103 volume）。
2. 写 `tests/backendState.test.py` 覆盖 GPU EDT 路径与 CPU EDT 路径的 1e-9 精度对照。
3. 通过 `SEGMENTATION_DEVICE=cuda` / `cupy` 检测自动切换 CPU / GPU 路径，避免在无 GPU 环境崩溃。
4. 更新 `src/report/exportReport.ts` 的 `phase_timings` 字段，记录 GPU EDT 阶段耗时。

**风险：** GPU EDT 在 surface mask 较小的 label 上数据传输可能比 CPU 慢；需要按 mask 体积动态切 CPU / GPU。

---

### 2. 距离阈值按器官动态化

**优先级：** 中

**前置文档：** 本目录 `findings.md` 待验证假设 2

**目标：** 把 1mm / 3mm 全局色阶改为按器官 + 体素间距动态化。例如食管、肾上腺等边界本身细的小器官，阈值放宽到 2mm / 5mm；肝脏、脾脏等大器官保持 1mm / 3mm。

**关键步骤：**

1. 在 `src/data/organDetails.ts` 增加 `distance_thresholds?: { good: number; warn: number }` 字段，按器官写经验阈值。
2. 修改 `src/report/exportReport.ts` 的 `distLevel()` / `distBarPercent()` 接受器官 ID 参数，按器官查表。
3. 修改 HTML 报告 metric group，让色阶 caption 显示当前器官的阈值（"≤2mm 绿 / ≤5mm 黄 / >5mm 红"）。
4. 补 `tests/imagingLogic.test.ts` 覆盖按器官阈值的色阶判定。

**风险：** 经验阈值需要从历史数据反推；如果设得过宽会失去色阶的判读价值。

---

### 3. class-balanced accuracy / frequency-weighted IoU

**优先级：** 低

**前置文档：** 本目录 `findings.md` 待验证假设 3

**目标：** 补齐 class-balanced accuracy / frequency-weighted IoU 等小器官更敏感的指标。`pixel_accuracy` 在大器官上接近 1.0，无法区分小器官差异。

**关键步骤：**

1. 在 `server/main.py` 的 `compute_label_metrics()` 增加 class-balanced accuracy / frequency-weighted IoU 计算。
2. 在 `src/inference/inferenceClient.ts` 的 `ValidationSummary` 增补 `class_balanced_accuracy` / `frequency_weighted_iou` 字段。
3. 在 `src/report/exportReport.ts` 的"像素准确率" metric group 增加 2 张卡片。
4. 补 `tests/backendState.test.py` 覆盖新指标计算。

**风险：** 这些指标在竞赛评审中权重不高；ROI 较低。

---

### 4. 离线/在线报告一致性测试

**优先级：** 中

**前置文档：** 本目录 `findings.md` 待验证假设 3

**目标：** 写 `tests/reportMetricsConsistency.test.py` 自动对比 `tools/segmentation_metrics_summary.py` 离线报告与 `src/report/exportReport.ts` 在线 HTML 报告的 Dice / IoU / HD / HD95 / ASD 是否一致。

**关键步骤：**

1. 准备一组 AMOS 0117 真实预测 + 参考 NIfTI，分别跑 `tools/segmentation_metrics_summary.py` 和 `server/main.py` 拿到两份 metrics。
2. 用 unittest 断言两份 metrics 在 1e-4 精度内一致。
3. 在 `npm test` / `python tests/backendState.test.py` 链路中自动跑。

**风险：** `tools/segmentation_metrics_summary.py` 与 `server/main.py` 的 NIfTI loading 路径不同（一个走 nibabel，一个走 nnUNetv2 internal），可能存在 spacing 提取差异。

---

### 5. 独立 planning 入口（按需推进）

**优先级：** 各自独立

| 任务 | 入口 |
|---|---|
| server mode gating 修复 | `.planning/label-taxonomy-server-validation/` |
| AMOS/FLARE 服务器轮次显式 taxonomy 复跑 | `.planning/label-taxonomy-server-validation/` |
| 高分辨率推理优化 | `.planning/high-resolution-inference-optimization/` |
| 跨数据集 cache 链路产品化 | `.planning/next-round-candidates/` |
| 演示启动脚本化 | `.planning/next-round-candidates/` |

---

## 推荐执行顺序

1. **离线/在线报告一致性测试**（防止后续重构引入口径差异）。
2. **距离阈值按器官动态化**（提升小器官 HD/HD95/ASD 的判读价值）。
3. **GPU EDT 加速**（进一步压缩 16.78s validation 时延）。
4. **class-balanced accuracy / frequency-weighted IoU**（持续）。
5. **独立 planning 入口**（按需推进）。

---

*更新日期：2026-06-03*
