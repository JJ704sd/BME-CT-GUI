# 三大目标验收包

本文档用于把当前 GUI 的三个目标从”功能接近完成”推进到”可复现验收”。当前证据包含 AMOS 0117 原生标签验证，以及 FLARE22 Tr 0009 的非 AMOS 在线推理和 taxonomy-remap 指标。2026-05-28 实现自动 taxonomy remap 后，FLARE22 在线验证已能自动重映射标签 ID 并得到有意义的跨数据集指标（job `a717dacf42d3`，mean_dice=0.926，验证通过）。2026-05-29 已收口缓存 validation、persistent worker reader、上传文件名调试日志和部分 FLARE22 标签 remap 的历史风险。2026-05-30 已增加 `本地在线推理` / `服务器云端推理` 运行位置选择、局域网访问配置化和服务器 5-fold soft ensemble 编排入口；2026-05-31 已通过校园网完成 Windows 前端调用 Ubuntu 服务器后端的 5-fold + soft ensemble + 前端回填 smoke，但 AMOS 标签 validation 暴露自动 taxonomy 误判风险，完整验收仍需补显式标签体系选择和 server gating 修复。

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
| 底部实时进度 | 是否显示 SSE 阶段进度条、当前阶段、job id、推理模式、已耗时和最近阶段日志 |

通过标准：

- 模型配置完整时，后端可创建真实 nnUNetv2 job。
- 模型配置不完整时返回明确错误，不创建假成功流程。
- 上传 `.nii` 或 `.nii.gz` 原图时，后端输入目录中的文件名必须符合当前模型 `dataset.json.file_ending`，避免 nnUNetv2 报 `There are 0 cases in the source folder`。
- `cached-real-nnunetv2` 只能表示历史预测结果缓存回填，不能代替未缓存真实推理性能；validation 必须按本次请求的标签文件或内置参考标签重新计算，无当前标签时不得复用缓存来源 job 的旧 Dice。
- SSE 文本进度和 NIfTI 二进制结果保持分离。
- GUI 底部进度条必须来自 SSE 阶段事件，不得把前端估算动画写成真实 nnUNetv2 内部进度。
- 长时间推理期间后端应定期发送心跳事件（`heartbeat: true`），前端更新已耗时和资源快照，避免界面显示停滞。
- 点击”取消推理”应请求 `/api/segment/jobs/{job_id}/cancel`，后端应终止运行中的 nnUNetv2 子进程并写入取消状态。
- GUI 可下载结果并回填到 overlay / split / side / difference 对比流程。

## 执行步骤

1. 准备或确认参考病例配置：

```powershell
$env:SEGMENTATION_REFERENCE_CASES_JSON = "D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\reference_cases.example.json"
```

2. 启动后端：

```powershell
$env:SEGMENTATION_DEVICE = "cuda"   # 可选，默认已是 cuda
$env:SEGMENTATION_PREPROCESS_WORKERS = "2"
$env:SEGMENTATION_EXPORT_WORKERS = "2"
$env:SEGMENTATION_PERSISTENT_WORKER = "1"  # 可选实验路径；正式速度结论仍以未缓存实测为准
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
- `deployment-packages/server-runtime-package-20260530.zip` 只是服务器后端运行包，需在 Ubuntu 22.04 服务器具备 nnUNetv2、CUDA/PyTorch、模型目录和真实 `SEGMENTATION_SERVER_*` 路径后按 `deployment-packages/server-runtime-quickstart-20260530.md` 启动。
- 当前本地可直接验收的真实 NIfTI 主要是 AMOS 0117。
- 新增 FLARE 或其他数据集病例后，应先登记到 `reference_cases.example.json` 的同结构配置，再补充本文件中的人工验收记录。
- 真实服务器模式已完成校园网端到端 smoke：可提交服务器 job、进入 5-fold 推理、完成 soft ensemble、下载并回填 GUI。后续仍需单独记录取消、失败恢复、server/local gating、AMOS/FLARE 显式 taxonomy、更多病例 validation 和长期稳定性。
- 没有标准答案的病例只能验收浏览、推理回填和人工复核流程，不能记录自动 Dice 通过。

## 2026-05-31 服务器在线推理 smoke 与 validation 风险

| 项目 | FLARE22 服务器轮次 | AMOS 服务器轮次 |
|---|---|---|
| 运行方式 | Windows 前端 → Ubuntu FastAPI → 5GPU/5-fold soft ensemble | Windows 前端 → Ubuntu FastAPI → 5GPU/5-fold soft ensemble |
| 推理状态 | 结果已回填 GUI | 结果已回填 GUI |
| validation | mean Dice 约 `0.891`，foreground Dice 约 `0.951` | mean Dice `0.076015`，foreground Dice `0.979808` |
| remap | FLARE22 → AMOS22，符合预期 | 报告显示 FLARE22 → AMOS22，但输入疑似 AMOS 原生标签 |
| 结论 | 服务器推理链路和 FLARE remap 可用 | 高前景 Dice + 低逐器官 Dice 更像标签体系误判，不应判定为模型完全失败 |

验收口径：服务器端到端链路已可作为阶段性进展记录；质量验收仍必须先确认上传 label 的 unique ID、spacing/affine 与 prediction 是否一致，并提供显式 `label_taxonomy=AMOS22|FLARE22|auto` 避免 AMOS 原生标签被错误 remap。

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

## 2026-05-26 FLARE22 Tr 0009 在线推理记录

本轮新增本地 FLARE22 Tr 0009 病例，并通过私有 registry 暴露给 `/api/samples`。该 registry 位于被忽略的 `nnunetv2_files/reference_cases.local.json`，不提交真实 NIfTI 数据。

病例元信息：

| 项目 | 结果 |
|---|---|
| case id | `flare22_tr_0009` |
| dataset | `FLARE22` |
| original | `FLARE22_Tr_0009_0000.nii.gz` |
| label | `FLARE22_Tr_0009.nii.gz`，仅离线使用 |
| dimensions | `512 / 512 / 87` |
| spacing | `0.806641 / 0.806641 / 2.5 mm` |
| original dtype | `float32` |
| label values | `0..13` |
| `/api/samples` | `has_original=true`, `has_label=false`, `validation_available=false` |

标签边界：

- FLARE22 label 定义为 `1=liver`, `2=right_kidney`, `3=spleen`, `4=pancreas`, `5=aorta`, `6=inferior_vena_cava`, `7=right_adrenal_gland`, `8=left_adrenal_gland`, `9=gallbladder`, `10=esophagus`, `11=stomach`, `12=duodenum`, `13=left_kidney`。
- 当前 checkpoint 是 `Dataset001_AMOS22`，label ID 顺序不同且包含 `14=bladder`, `15=prostate_or_uterus`。
- 该参考病例在 `/api/samples` 中仍保持 `validation_available=false`，因为内置 registry 不把 FLARE22 标签直接当作 AMOS 原生标签使用；如用户另行上传 FLARE22 标签文件，2026-05-28 之后后端会通过自动 taxonomy remap 执行在线 validation。

未缓存 `quality` 在线推理记录：

| 项目 | 结果 |
|---|---|
| job id | `86b0153d0a73` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| device | `cuda` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |
| duration_seconds | `237.323` |
| phase_timings | `prepare_runtime_model=0.003`, `persistent_worker=237.119`, `collect_result=0.001` |
| result_status | `200` |
| result_bytes | `120761` |
| resource_latest | RTX 4060 Laptop GPU, `1804 / 8188 MiB`, `18%`, disk free `105865117696 bytes` |
| output | `.test-output\flare22-tr-0009-quality-20260526\86b0153d0a73.nii.gz` |

离线 FLARE→AMOS taxonomy-remapped 指标：

| 指标 | 值 |
|---|---:|
| mean Dice | `0.893127` |
| min Dice | `0.673730` |
| foreground Dice | `0.949908` |
| mean IoU | `0.815941` |
| min IoU | `0.507989` |
| foreground IoU | `0.904594` |
| Pixel/Voxel Accuracy | `0.991879` |
| mean Hausdorff Distance | `12.595149 mm` |
| max Hausdorff Distance | `38.043429 mm` |
| weakest label | `duodenum`, Dice `0.673730` |

## 2026-05-26 GUI 交互性能与代码交接

范围：

- 缓解三正交 CT 视图中快速移动光标时的可见卡帧和图像滞后。
- 新增 `CODE_MODULE_GUIDE.md`，作为后续代码讲解和交接的模块级说明书。

验收证据：

| 检查项 | 结果 |
|---|---|
| 三视图指针烟测 | Edge/Playwright 成功加载 `.orthogonal-viewer`，识别到 `3` 个视图面板，并完成快速拖动，无控制台错误。 |
| 图像渲染烟测 | 拖动后所有 `.ortho-canvas img` 都有非空 `src`，且 natural dimensions 不为 0。 |
| 回归验证 | 本轮已通过 `node tests/imagingLogic.test.ts`、`node tests/acceptanceDocs.test.ts`、`npm test` 和 `npm run build`。 |

行为边界：

- 十字线移动优先保持即时反馈。
- 较重的切片栅格化通过 `requestAnimationFrame` 合并调度，快速拖动时中间帧可能被跳过，但最终会渲染最新坐标。
- 三正交视图中的 `分屏` 仅在存在 mask 结果时显示分割线；滑杆控制左侧分割结果叠加区域的比例。
- 本改动不改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 指标或 label taxonomy 处理。

结论：

- FLARE22 Tr 0009 的后端在线推理链路通过，结果可下载，且未命中历史缓存。
- 该病例不是 AMOS 原生标签验收；在未上传标签文件的这次运行中，自动 Dice 验证被正确关闭。
- Remapped 指标显示总体可用，但 duodenum 低于 `0.70`，pancreas/esophagus 约 `0.81`，正式报告仍需人工复核三正交视图和局部边界。

## 2026-05-26 矢状/冠状拖动回跳修复记录

范围：

- 修复矢状面或冠状面快速拖动时，旧 `selectedSlice` 延迟回写导致 `voxelCoord.z` 被拉回的问题。
- 保持三视图拖动和主切片滑块两种交互路径可用。

验收证据：

| 检查项 | 结果 |
|---|---|
| 根因 | `voxelCoord.z` 与 `selectedSlice` 双向同步发生延迟回写，不是 nnUNetv2 推理或 NIfTI 标签体系问题。 |
| 回归测试 | `tests/imagingLogic.test.ts` 覆盖 voxel 驱动同步不得回退 z 坐标、slice 驱动同步仍可更新 z 坐标。 |
| 自动验证 | `node tests/imagingLogic.test.ts`、`npm test`、`npm run build` 均通过。 |

行为边界：

- 三视图拖动时，十字线和体素坐标以最新 `voxelCoord` 为准。
- 右侧 axial 预览和底部缩略图仍按帧同步，但不再反向覆盖正在拖动的矢状/冠状坐标。
- 本改动不改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 指标或 FLARE22 taxonomy remap。

## 2026-05-26 三视图拖动卡顿二次修复记录

范围：

- 修复上一轮回跳修复后，快速拖动三视图仍会按每个 `pointermove` 同步刷新父组件导致的卡顿。
- 保持十字线、体素坐标、主切片滑块和底部切片入口之间的联动语义不变。

验收证据：

| 检查项 | 结果 |
|---|---|
| 根因 | `handleVoxelCoordChange()` 每个指针事件立即提交 `voxelCoord`，带动父组件、右侧 axial 预览和底部状态高频重渲染。 |
| 回归测试 | `tests/imagingLogic.test.ts` 覆盖 `getVoxelCoordDragCommit()`、rAF 坐标合并入口和禁止同步提交旧 `clampedCoord`。 |
| 自动验证 | `node tests/imagingLogic.test.ts`、`npm test`、`npm run build`、`git diff --check` 均通过。 |

行为边界：

- 三视图拖动坐标每帧最多提交一次 React 状态，快速拖动时只保留最新待提交坐标。
- 如果下一帧前回到原坐标，待提交中间坐标会被清空，不会再触发过时切片渲染。
- 本改动只影响前端渲染调度，不改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 指标或 FLARE22 taxonomy remap。

## 2026-05-26 矢状/冠状拖动卡顿三次修复记录

范围：

- 修复矢状面、冠状面拖动时仍比横断面更容易卡顿的问题。
- 保持三视图实时变化和十字线即时联动，同时降低拖动期间的图像重绘压力。

验收证据：

| 检查项 | 结果 |
|---|---|
| 根因 | 横断面拖动多为 `x/y` 变化，固定 `z` 切片不变；矢状/冠状拖动会连续改变 `z`，带动 Axial 面板和辅助预览刷新。 |
| 交互修复 | `OrthogonalViewer` 拖动期间启用 `interactive` 轻量渲染，三张视图仍实时更新；释放后自动回到 `full` 完整质量。 |
| 回归测试 | `tests/imagingLogic.test.ts` 覆盖 `activePointerOrientation`、`interactiveRenderMode`、`latestSliceKeyRef` 和空闲同步入口。 |

行为边界：

- 拖动过程中十字线和体素坐标仍以最新位置为准。
- 三张视图在拖动过程中仍会实时变化；快速拖动时使用轻量预览图像，释放后恢复完整质量。
- 本改动不改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 指标或 FLARE22 taxonomy remap。

## 2026-05-26 底部实时推理进度记录

范围：

- 在底部“切片与流程日志”区域新增实时推理进度 rail。
- 复用现有 `/api/segment/jobs/{job_id}/events` SSE 阶段事件，不修改后端推理语义。

验收证据：

| 检查项 | 结果 |
|---|---|
| 进度来源 | `progress/complete/error` 事件写入结构化 `inferenceTimeline`，进度条百分比使用后端 SSE 阶段值。 |
| 底部信息 | 显示当前阶段、百分比、job id、`quality/fast` 模式、已耗时和最近阶段日志。 |
| 失败路径 | SSE `error.log_tail` 保留到 timeline 摘要，不伪装成成功。 |
| 布局回归 | `tests/browserLayout.test.ts` 覆盖桌面和移动端 progress rail，避免遮挡或压缩三视图。 |
| 自动验证 | `node tests/imagingLogic.test.ts`、`node tests/browserLayout.test.ts`、`npm test`、`npm run build` 均通过。 |

行为边界：

- 长时间 nnUNetv2 主体推理仍可能停留在 `20%` 阶段；界面用”推理运行中”和已耗时表达活跃状态，不伪造连续百分比。
- 后端已实现心跳机制（`push_heartbeat()`，间隔 10 秒），推理期间会定期通过 SSE 推送已耗时和资源快照，前端底部进度 rail 会更新活跃状态。
- 本改动不改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 指标或 FLARE22 taxonomy remap。

## 2026-05-26 在线推理启动与取消链路修复记录

范围：

- 修复 `.nii` 原图上传后 nnUNetv2 报 `There are 0 cases in the source folder` 的问题。
- 复核在线推理取消链路，确认前端已有“取消推理”入口，后端已有子进程终止逻辑。

验收证据：

| 检查项 | 结果 |
|---|---|
| 根因 | 当前模型 `dataset.json.file_ending` 为 `.nii.gz`，失败 job 的输入保存为 `<job>_0000.nii`，nnUNetv2 因后缀不匹配识别到 `0` 个病例。 |
| 修复 | 后端按模型 `file_ending` 规范化输入；`.nii` 上传会 gzip 成 `<job>_0000.nii.gz`。 |
| 取消链路 | `tests/backendState.test.py` 已覆盖运行中 job 取消、`cancel_requested`、子进程 `terminate()` 和 SSE 取消阶段事件。 |
| 自动验证 | `python tests/backendState.test.py` 通过。 |

行为边界：

- 该修复只解决 nnUNetv2 输入识别问题，不改变模型权重、推理参数或指标计算。
- 浏览器不能自动启动 Python 后端；在线推理前仍需 FastAPI 服务在 `127.0.0.1:8000` 运行。

## 2026-05-27 标签文件传输修复与在线验证链路

范围：

- 修复标签文件上传后后端 `label_path` 为 `null` 的问题。
- 打通从 GUI 标签文件上传到后端在线 Dice 验证的完整链路。
- 记录 FLARE22 与 AMOS22 taxonomy 错位的根因发现。

验收证据：

| 检查项 | 结果 |
|---|---|
| 根因 | `UploadRole` 类型不包含 `"label"`，拖拽不支持标签文件；当时还通过临时上传文件名日志确认后端服务是否加载了新代码。 |
| 前端修复 | `UploadRole` 扩展为 `"source" | "result" | "label"`；`processVisualizationFile()` 增加 label 分支；数据操作面板新增"标签 CT 导入"拖放区域。 |
| 后端排查 | 曾临时在 `create_job()` 打印接收文件信息，重启后标签文件正常传输；该类上传文件名调试日志已在 2026-05-29 移除，不再作为当前运行要求。 |
| 在线验证 | job `bf20f0ec4456`：`label_path` 非空，validation 执行成功，标签文件 131 KB 正确保存。 |
| taxonomy 错位 | FLARE22 label ID 与 AMOS22 checkpoint 语义完全不同，仅 label 2（右肾）一致 Dice=0.945，其余错位 Dice≈0。 |
| 离线 remap | 器官名重映射后 mean_dice=0.893, min_dice=0.674, fg_dice=0.950。 |
| 自动验证 | `npm test`、`npm run build` 均通过。 |

行为边界：

- 标签文件传输 bug 的根因可能是后端服务未重启导致代码变更未生效。
- 该历史运行中的 `taxonomy_match: True` 只检查了 ID 集合交集，未做语义级匹配；这个问题已在 2026-05-28 的自动 taxonomy remap 中修正。
- 在线验证 mean_dice=0.073 是 taxonomy 错位导致，非模型质量问题；离线 remap 后真实值为 0.893。
- 2026-05-28 已实现自动 taxonomy remap（见下一节），跨数据集在线验证现在可以按器官名重映射后解释。

## 2026-05-28 自动 Taxonomy Remap 在线验证记录

范围：

- 将 FLARE22 等已知数据集的标签 ID 按器官名自动重映射到当前 AMOS22 checkpoint 的标签 ID。
- 让用户上传标签文件后的在线 Dice validation 可以得到有意义的跨数据集指标。
- 在 validation 结果和评估面板中明确显示 `remap_applied`、`remap_source` 和重映射说明。

验收证据：

| 检查项 | 结果 |
|---|---|
| 代码路径 | `server/taxonomy.py` 负责 FLARE22 标签表、器官别名、数据集检测、映射构建和参考标签数组重排。 |
| 在线运行 | job `a717dacf42d3`，病例 FLARE22 Tr 0009，`quality` profile，未命中缓存。 |
| 重映射状态 | `remap_applied=true`，`remap_source=FLARE22`。 |
| validation | `status=passed`，`mean_dice=0.926`，相对 taxonomy 错位运行的 `0.073` 明显恢复。 |
| 前端展示 | 评估面板显示“已自动重映射标签 ID（FLARE22 → 当前模型）”，避免误认为 AMOS 原生标签。 |
| 文档记录 | `README.md`、`REVIEW.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_RECENT_ROUNDS.md` 已记录该轮结果。 |

行为边界：

- 自动 remap 解决的是标签 ID 语义错位，不改变 nnUNetv2 模型输出本身。
- FLARE22 自动 remap 是跨数据集在线验证证据，仍不能和 AMOS 0117 原生标签指标无条件混算。
- 当前已知 remap 来源以 FLARE22 为主；新增数据集前应先补充标签表、别名映射、测试和验收记录。

## 2026-05-29 历史 bug 收口验收记录

范围：

- 修复缓存命中时可能复用旧 `validation` 的风险。
- 修复 `SEGMENTATION_PERSISTENT_WORKER=1` 路径中 stdout reader 线程可能竞争消费事件的问题。
- 移除前后端上传文件名调试日志，避免病例文件名进入浏览器控制台或后端 stdout。
- 扩展 FLARE22 自动 taxonomy remap：部分标签在至少两个明确错位 ID 时也可自动识别；单 label 文件仍保持人工判断边界。

验收证据：

| 检查项 | 结果 |
|---|---|
| 缓存 validation | 缓存命中只复用预测 NIfTI；当前请求带 `label_file` 时重新 validation，无当前标签且非内置参考病例时 `validation=null`。 |
| persistent worker reader | 后端为每个 worker 进程维护共享 stdout reader 和 `queue.Queue`，连续读取事件不再新建多个 reader 线程。 |
| 调试日志 | `src/main.tsx`、`src/inference/inferenceClient.ts`、`server/main.py` 中上传文件名日志已移除。 |
| 部分标签 remap | FLARE22 `{1, 3}` 这类至少两个明确错位 label 可触发 remap；单个 label ID 不自动推断来源。 |
| 自动验证 | `node tests/imagingLogic.test.ts`、`python tests/backendState.test.py`、`npm test`、`npm run build` 已在代码修复轮通过。 |
| worker smoke | 轻量启动 `server/persistent_nnunet_worker.py` 并发送 shutdown，收到 `bye` 且进程退出码为 `0`。 |

行为边界：

- 本轮没有运行真实长耗时 persistent worker 推理；当前只能说明协议和 reader 复用路径稳定性改善，不能写成已验证加速。
- 预测缓存仍按输入 CT、checkpoint 和推理配置复用；标签文件不进入预测 cache key，但 validation 不再随预测缓存复用。
- 部分标签 remap 的目标是避免明显 FLARE22 子集被误判为 AMOS 原生标签；未知数据集和单 label 文件仍需要显式数据集 hint 或人工复核。
