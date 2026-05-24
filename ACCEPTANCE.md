# 三大目标验收包

本文档用于把当前 GUI 的三个目标从“功能接近完成”推进到“可复现验收”。当前本地可见真实 NIfTI 资源仍以 AMOS 0117 为主，未发现可直接登记的非 AMOS CT 文件；因此非 AMOS 病例先通过 `reference_cases.example.json` 给出注册方式，不能把占位配置当成模型泛化验证结论。

## 目标 1：CT 可浏览、三正交可联动

验收对象：

- 任意 `.nii` / `.nii.gz` CT 原图。
- 内置参考病例 AMOS 0117。
- 通过 `SEGMENTATION_REFERENCE_CASES_JSON` 登记的外部参考病例。

人工验收记录应包含：

| 项目 | 记录内容 |
|---|---|
| 病例 id | 例如 `amos_0117` 或外部病例 id |
| 数据集 | 例如 `AMOS22`、`FLARE`、`Local` |
| 体数据尺寸 | columns / rows / slices |
| spacing | x / y / z |
| Axial | 可读 / 变形 / 溢出 / 异常说明 |
| Sagittal | 可读 / 变形 / 溢出 / 异常说明 |
| Coronal | 可读 / 变形 / 溢出 / 异常说明 |
| 交互 | 点击、拖动、滚轮、十字线是否稳定 |
| 截图 | 桌面和移动端至少各一张 |

通过标准：

- 三个方向同时可读，不被压成不可用窄条。
- 图像使用 contain 方式显示，不为填满面板而拉伸变形。
- 点击和拖动只移动体素坐标，不触发页面横移或原生图片拖拽。
- 移动端允许纵向滚动，但不应出现横向溢出。

## 目标 2：器官 label 可点击并展示说明

验收对象：

- `/api/models` 返回的真实 label 表。
- 前端 fallback label 表。
- 带标准答案或预测结果的 mask NIfTI。

人工验收记录应包含：

| 项目 | 记录内容 |
|---|---|
| label 来源 | `/api/models` 或 fallback |
| label 数量 | 实际返回数量 |
| label id/name | 每个 label 的 id、中文名、颜色 |
| 点击结果 | 命中 mask 后是否打开正确器官说明 |
| 背景行为 | label 0 或空白处是否不会误弹说明 |
| 质控结果 | 有标准答案时记录 per-label Dice |

通过标准：

- `validation_available=true` 的参考病例可显示标准答案验证结果。
- `validation_available=false` 的病例不得伪装成可自动 Dice 验证。
- 每个非背景 label 都能映射到稳定的器官说明。
- 未出现的器官保持可复核状态，不应被描述为模型错误。

## 目标 3：连接本地 nnUNetv2 后端并回填结果

验收对象：

- `GET /api/health`
- `GET /api/models`
- `POST /api/segment/jobs`
- `GET /api/segment/jobs/{job_id}`
- `GET /api/segment/jobs/{job_id}/events`
- `GET /api/segment/jobs/{job_id}/result`

人工验收记录应包含：

| 项目 | 记录内容 |
|---|---|
| 输入病例 | 文件名、大小、hash 或病例 id |
| job id | 后端返回的 job id |
| mode | `real-nnunetv2`、`cached-real-nnunetv2` 或 `unavailable` |
| 未缓存真实推理 | 是否清空/避开历史缓存后执行 |
| 总耗时 | duration_seconds |
| 阶段耗时 | `phase_timings` 中的预处理、推理、导出等 |
| 资源快照 | device、GPU 显存、磁盘空间 |
| 结果文件 | 下载状态、字节数、能否回填 GUI |
| 验证结果 | 有标准答案时记录 mean/min/foreground Dice |

通过标准：

- 模型配置完整时，后端可创建真实 nnUNetv2 job。
- 模型配置不完整时返回明确错误，不创建假成功流程。
- `cached-real-nnunetv2` 只能表示历史缓存回填，不能代替未缓存真实推理性能。
- SSE 文本进度和 NIfTI 二进制结果保持分离。
- GUI 可下载结果并回填到 overlay / split / side / difference 对比流程。

## 执行步骤

1. 准备或确认参考病例配置：

```powershell
$env:SEGMENTATION_REFERENCE_CASES_JSON = "D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\reference_cases.example.json"
```

2. 启动后端：

```powershell
$env:SEGMENTATION_DEVICE = "cuda"
$env:SEGMENTATION_PREPROCESS_WORKERS = "2"
$env:SEGMENTATION_EXPORT_WORKERS = "2"
$env:SEGMENTATION_PERSISTENT_WORKER = "1"
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

3. 启动前端：

```powershell
npm run dev -- --port 5173
```

4. 浏览器中完成三项人工验收记录：

- 载入参考病例，检查三正交视图。
- 载入或运行分割结果，逐项点击非背景 label。
- 对同一病例分别记录未缓存真实推理和 `cached-real-nnunetv2` 回填表现。

5. 提交前运行自动验证：

```powershell
npm test
npm run build
```

## 当前边界

- 本仓库不提交真实 CT、NIfTI、checkpoint 权重或推理输出。
- 当前本地可直接验收的真实 NIfTI 主要是 AMOS 0117。
- 新增 FLARE 或其他数据集病例后，应先登记到 `reference_cases.example.json` 的同结构配置，再补充本文件中的人工验收记录。
- 没有标准答案的病例只能验收浏览、推理回填和人工复核流程，不能记录自动 Dice 通过。

## 2026-05-24 运行态记录

本轮在隔离工作目录中执行了一次 AMOS 0117 未缓存真实推理，并随后执行同输入缓存回填验证。隔离目录为：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\acceptance-real-20260524-194750
```

未缓存真实推理记录：

| 项目 | 结果 |
|---|---|
| job id | `32dfe3117b40` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| device | `cuda` |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB |
| duration_seconds | `359.425` |
| phase_timings | `nnunet_process=356.767`, `validation=2.481` |
| result_status | `200` |
| result_bytes | `141470` |
| validation status | `review` |
| mean_dice | `0.891305` |
| foreground_dice | `0.97122` |
| min_dice | `0.55591` |
| 结论 | 推理链路和结果下载通过；胃 label Dice 低于 `0.70`，仍建议人工复核。 |

同输入缓存回填记录：

| 项目 | 结果 |
|---|---|
| job id | `c8cecb040657` |
| mode | `cached-real-nnunetv2` |
| cached_result | `true` |
| cache_source_job_id | `32dfe3117b40` |
| elapsed_seconds | `2.674` |
| result_status | `200` |
| result_bytes | `141470` |

注意：本节记录的是 AMOS 0117 的运行态验收，不代表新增 FLARE 或其他非 AMOS 病例已经完成模型效果验证。

## 2026-05-24 新权重运行态记录

本轮确认更新后的权重文件为：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\checkpoint_best.pth
```

权重元信息：

| 项目 | 结果 |
|---|---|
| 文件大小 | `1136119762 bytes` |
| 修改时间 | `2026-05-24 18:04:22` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |

本次采用的在线推理加速方式：

- `SEGMENTATION_PERSISTENT_WORKER=1`：尝试使用常驻 nnUNet predictor worker，避免每个在线 job 重复启动 Python 解释器和重新初始化 predictor。
- checkpoint hash 已纳入 `cache_key`：权重更新后不会命中旧权重缓存；同一新权重、同一输入、同一配置的后续请求可走 `cached-real-nnunetv2` 快速回填。

新权重未缓存真实推理记录：

| 项目 | 结果 |
|---|---|
| 隔离目录 | `.test-output\acceptance-new-weight-20260524-201714` |
| job id | `27216eb73220` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| device | `cuda` |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB |
| duration_seconds | `1124.327` |
| phase_timings | `persistent_worker=1121.592`, `validation=2.527` |
| result_status | `200` |
| result_bytes | `141569` |
| validation status | `passed` |
| mean_dice | `0.924791` |
| foreground_dice | `0.980316` |
| min_dice | `0.846551` |
| 结论 | 新权重在 AMOS 0117 标准答案验证上通过阈值；首次未缓存耗时仍较长。 |

新权重同输入缓存回填记录：

| 项目 | 结果 |
|---|---|
| job id | `f200f16f47be` |
| mode | `cached-real-nnunetv2` |
| cached_result | `true` |
| cache_source_job_id | `27216eb73220` |
| elapsed_seconds | `3.532` |
| result_status | `200` |
| result_bytes | `141569` |

新权重分割指标 summary：

| 项目 | 结果 |
|---|---|
| summary 文档 | `SEGMENTATION_METRICS_SUMMARY.md` |
| 指标 JSON | `.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.json` |
| 指标 Markdown | `.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.md` |
| Dice | `mean=0.924791`, `min=0.846551`, `foreground=0.980316` |
| IoU | `mean=0.865105`, `min=0.733930`, `foreground=0.961392` |
| Pixel/Voxel Accuracy | `0.998578` |
| Hausdorff Distance | `mean=7.716048 mm`, `max=16.562684 mm` |
| 标签数 | checkpoint 定义 `15` 个前景标签；AMOS 0117 本例实际出现 `1..13`，label `14/15` 为 `N/A` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |

无缓存 persistent worker 对照：

| 项目 | 结果 |
|---|---|
| 实验目录 | `.test-output\perf-no-cache-persistent-20260524-212332` |
| summary | `.test-output\perf-no-cache-persistent-20260524-212332\perf_no_cache_persistent_summary.json` |
| 缓存策略 | `disabled via patch(server.find_cached_prediction, return_value=None)` |
| cold job | `c7ef1da0195e`, `succeeded`, `cached_result=false` |
| cold duration | `1528.792s`, `persistent_worker=1525.923s` |
| warm job | `685426290aa4`, `warm_persistent_no_cache` |
| warm summary status | `timeout` at `1800.785s`, progress remained `20` |
| warm actual output | `.test-output\perf-no-cache-persistent-20260524-212332\work\685426290aa4\output\685426290aa4.nii.gz` |
| warm output wall time | input write `2026-05-24 21:49:08` to NIfTI write `2026-05-24 22:57:33`, about `4104.567s` / `68.409min` |
| warm metrics JSON | `.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.json` |
| cold/warm output SHA256 | both `5473EAFB22FA21B896F8511BE9E02FFD49D678DEE4B82E63681FDD99DA57D9C0` |
| 结论 | 当前常驻 worker 未证明无缓存加速；warm 反而明显慢于 cold，并触发 timeout。 |

推理过久的排查结论：

- 这不是训练耗时，而是 nnUNetv2 在线推理耗时。
- cold/warm 使用同一输入、同一 checkpoint、同一 worker 参数，输出 hash 完全一致，说明质量结果可复现，但性能没有改善。
- warm 在日志中长时间停在 `Predicting 685426290aa4` 和 `perform_everything_on_device: True`，直到约 `22:55:50` 才进入 `sending off prediction to background worker for resampling and export`；主要耗时发生在 nnUNet sliding-window 预测阶段，而非导出或 Dice 验证阶段。
- GPU 监控显示预测阶段长期接近 `100%` 利用率，显存约 `7.5-7.9 GiB / 8.0 GiB`，接近 RTX 4060 Laptop GPU 显存上限，可能存在 3D full-res 推理、mirroring/TTA、PyTorch 显存碎片或第二次复用 predictor 状态导致的长尾。
- perf 工具本身还有收尾缺陷：timeout 后 summary 需要等待 `persistent_worker_lock`，而后台推理线程也持有该锁等待 worker complete，因此 summary 只能在 worker 返回后落盘；warm 的 `job_summary.json` 和 `validation_summary.json` 没有被后端完整写出，需要用已落盘 NIfTI 单独补 metrics。

注意：新权重质量指标明显改善，但本次冷启动常驻 worker 的首次推理耗时不应被写成加速成功。当前已经验证的在线加速收益是缓存回填；常驻 worker 是否能改善连续未缓存病例，需要在同一后端进程内执行第二个不同输入或禁用缓存的 warm-worker 对照测试。
