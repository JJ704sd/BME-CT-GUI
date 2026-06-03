# 质量评估指标扩展 + 表面距离计算加速 解释

## 为什么需要这一轮工作

中国生物医学工程竞赛「呼吸-消化系统疾病」赛道的验收指南要求质量评估报告至少包含 Dice、IoU、像素准确率（Pixel Accuracy）、Hausdorff Distance（含 HD95）四类医学影像主流指标；本轮再把 ASD（Average Surface Distance）补齐以覆盖更完整的距离维度。本项目在 2026-05-25 baseline 下 HTML 报告只有 Dice / IoU 卡片，逐标签表也只有 Dice / IoU / HD 三列；`src/inference/inferenceClient.ts` 的 `ValidationSummary` 白名单也只透传这三类指标，其他字段被无声丢弃。

同时，缓存命中路径下的实测发现 validation 阶段耗时 `38.86s`（`2d477d8bbd7d` / `9fd0fdc39960` / `096e5b8349df` 这几次 AMOS quality cache hit），比一次 quality 推理（`1360.398s`）的 1/35 还慢 10 倍以上——逐器官遍历 + 6 EDT/label 是主要瓶颈。这种"validation 比推理还慢"的现象不只影响验收节奏，也影响高分辨率 CT 推理场景的端到端时延。

## 为什么不能简单忽略

1. **验收口径风险**：竞赛 PPT 与验收文档要求 6 类医学影像主流指标同时出现；如果只展示 Dice/IoU，验收会被质疑"指标不全"。
2. **逐器官表面距离盲区**：现有 HD 单值无法区分"边界大幅偏移"与"边界轻微毛刺"；补 HD95 + ASD 后可以分别评估"最坏情况"和"平均情况"。
3. **性能 vs 精度权衡**：当前 validation 阶段比推理本身慢 10×，意味着把全部 6 类指标补齐后，validation 阶段会进一步变慢（新增 3 类指标会再触发 EDT）。必须在补指标的同时压缩 EDT 调用次数，避免 validation 阶段成为新的瓶颈。
4. **离线/在线口径一致性**：`tools/segmentation_metrics_summary.py` 在 offline 端已经能输出全部 6 类指标，但前端 `inferenceClient.ts` 的白名单不全。补齐前端白名单才能让 GUI 报告与离线 `tools/` 报告口径完全一致。

## 本轮范围

| 项目 | 范围 |
|---|---|
| 后端新函数 | `server/main.py` 新增 `surface_distances(prediction_mask, reference_mask, spacing_tuple)`：1 crop + 2 surface mask + 2 EDT（forward / backward），再用 value 数组派生 `asd` / `hd` / `hd95` / `forward_*` / `backward_*` |
| 后端旧函数 | 保留 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 为 legacy，仅供回归测试 1e-9 精度对照 |
| compute_label_metrics | 单个 label 改用 `surface_distances()`；foreground metrics 也走 `surface_distances()`（非全 volume union mask） |
| 字段扩展 | `validation_summary.json` 增补 12 个新字段：pixel_accuracy / mean_pixel_accuracy / min_pixel_accuracy / foreground_pixel_accuracy、mean_asd / max_asd / foreground_asd、mean_hd / max_hd / foreground_hd、mean_hd95 / max_hd95 / foreground_hd95、surface_distance_unit="mm"、spacing=[sx, sy, sz]；per-label 增补 pixel_accuracy / asd / hd / hd95 |
| 前端白名单 | `src/inference/inferenceClient.ts` 的 `ValidationSummary` / `LabelMetric` 增补上述字段；`normalizeValidation()` 加入白名单；`parseInferenceEvent()` 在 complete 事件里透传 |
| HTML 报告 | 3 个 metric group（区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD，共 19 张卡片），HD/HD95/ASD 卡片使用 mm 单位 + ≤1mm 绿 / ≤3mm 黄 / >3mm 红色阶；逐标签表新增 4 列：像素准确率、ASD (mm)、HD95 (mm)、HD (mm) |
| 距离色阶 | 独立于 Dice / IoU 阈值；不会因为 distance 数值小而把 Dice 误染绿 |
| 报告元信息 chips | 逐标签表上方显示 `spacing=[sx, sy, sz] mm` 与 `surface_distance_unit=mm` 两个 info tag |
| 离线口径 | `tools/segmentation_metrics_summary.py` 复用 `surface_distances()` 合并函数，保证离线口径与后端在线 validation 完全一致 |
| 回归测试 | `tests/backendState.test.py` 3 个测试（1e-9 精度对照、EDT 调用计数恒为 2、wall-time 加速比 ≥30%）；`tests/imagingLogic.test.ts` 全部新字段的 source-grep + `parseInferenceEvent()` complete 事件解析值测试 |
| 文档同步 | 9 份核心文档统一加"2026-06-03 质量评估指标扩展 + 表面距离计算加速"或同等描述 |

## 与其他 planning 文档的关系

- `.planning/label-taxonomy-server-validation/`：独立工程入口，本轮未触及。`label_taxonomy` 字段已在 `validation_summary.json` 出现，本轮不动。
- `.planning/high-resolution-inference-optimization/`：高分辨率 CT 推理优化（预降采样、3D 模型评估）。本轮 `surface_distances()` 2 EDT 优化是高分辨率 CT 端到端时延的"validation 侧"优化，与该目录互补。
- `.planning/2026-06-01-cache-link-patch/`：cache 链路补丁，让 cache hit 显示历史 validation 摘要。本轮补齐的 12 个新字段在 cache hit 时会透传到 `validation_summary.json`，与 cache 链路补丁形成"显示的字段更全"协同。
- `.planning/next-round-candidates/`：跨数据集 cache 链路产品化、runbook 自动校验、演示启动脚本化是下一轮候选任务。

## 优先级依据

| 优先级 | 工作 | 理由 |
|---|---|---|
| 高 | 补齐 6 类医学影像主流指标 | 验收硬约束；不补齐会被质疑"指标不全" |
| 高 | `surface_distances()` 2 EDT 性能不变量 | 验证阶段比推理慢 10× 已影响演示节奏 |
| 高 | 前端白名单 + HTML 报告 3 metric group + 4 列 | 让用户能在 GUI 直接看到新指标 |
| 中 | 回归测试覆盖精度 / EDT 计数 / 加速比 | 防止后续重构破坏 2 EDT 不变量 |
| 中 | 9 份核心文档同步 | 防止下次复现困惑 |
| 中 | 离线 `tools/` 复用 `surface_distances()` | 离线/在线口径一致 |

## 行为边界

- "surface_distances 2 EDT"是单 label 性能不变量：每个 label 在 1 次 crop + 2 次 `distance_transform_edt`（预测→参考、参考→预测）后用 value 数组派生 `asd` / `hd` / `hd95`。新写 `compute_*_metrics` 时不应回退到 6 EDT 模式；旧 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 仅保留供回归测试对照，不再走主路径。
- HD / HD95 / ASD 报告单位固定为 mm（按 NIfTI spacing 缩放），与 Pixel/Voxel Accuracy 的 0-1 比例独立；色阶阈值 1mm / 3mm 不与 Dice 阈值 0.85 / 0.70 混用。
- 本轮不修改 nnUNetv2 推理、缓存复用、SSE 协议、影像量化或历史 AMOS `quality` profile `b3c528cc9e20`（mean Dice 0.924780）、FLARE22 自动 remap `a717dacf42d3`（mean Dice 0.926）、FLARE22 离线 remap `86b0153d0a73`（mean Dice 0.893127）三套历史基线数值。
- "validation 比推理慢 10×"已被 2 EDT 优化收口到约 2.3× 加速；剩余 wall-time 仍由 `numpy` 单线程 EDT 实现主导，进一步加速需要切到 `cupy` / `numba` JIT，这是下一轮候选任务。

## 后续建议

1. **距离阈值按器官动态化**：当前 1mm / 3mm 色阶是全局固定值；后续可按器官 + 体素间距动态化（如食管边界本身细，阈值应放宽到 2mm / 5mm）。
2. **GPU EDT 加速**：768×768×103 volume 上 EDT CPU 端 numpy 实现仍占 validation 主要耗时；可考虑 `cupyx.scipy.ndimage.distance_transform_edt` 或 numba JIT 把 16.78s 进一步压到秒级。
3. **3D Dice / IoU 体素精度细分**：当前 `pixel_accuracy` 是 0-1 比例，体积较大器官接近 1.0；可加 "class-balanced accuracy" / "frequency-weighted IoU" 进一步区分小器官与大器官。
4. **离线报告 + 在线报告双向通道**：`tools/segmentation_metrics_summary.py` 目前复用 `surface_distances()`，但前端 HTML 报告是另一个渲染路径；可以写一个 `tests/reportMetricsConsistency.test.py` 自动对比两边的 Dice / IoU / HD 是否一致。

---

*更新日期：2026-06-03*
