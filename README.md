# BME CT 分割 GUI 原型

本项目是面向腹部 CT 分割验证流程的本地 GUI 原型。前端使用 React + Vite，后端使用 FastAPI 桥接本机 nnUNetv2 环境，目标是完成 CT 浏览、三正交联动、器官 label 说明、真实模型推理回填、结果下载和验收记录。

截至 2026-06-03，项目已经作为独立 GUI 仓库维护；真实 CT、NIfTI、checkpoint 权重和推理输出仍只保留在本机，不提交到 GitHub。当前已完成本地在线推理、标签上传、自动 taxonomy remap、报告导出（HTML / JSON / PDF 三种格式，2026-06-03 已补齐到 6 类医学影像主流指标：Dice / IoU / Pixel Accuracy / HD / HD95 / ASD）、服务器 runtime 部署准备、校园网内 Windows 前端直连 Ubuntu 服务器 FastAPI 后端的 5GPU / 5-fold soft ensemble 在线推理回填，以及本地缓存演示 7 步验证（AMOS cache hit → FLARE 真实推理 → FLARE cache hit）。最新服务器运行显示：FLARE22 标签经自动 remap 后 Dice 较高，AMOS 原生标签曾被误判为 FLARE22 后 mean Dice 异常偏低；2026-05-31 已实现显式 `label_taxonomy=auto|AMOS22|FLARE22`，2026-06-02 发现 AMOS 真实标签只有 1-13（缺 14/15）与 FLARE22 在裸 ID 集合上无法仅靠 auto 区分，进一步收紧 `detect_dataset()` 在参考覆盖 ckpt ≥ 0.85 时返回 `None`，并由前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动预设 `label_taxonomy`（AMOS → AMOS22、FLARE22 → FLARE22），用户仍可在 UI 切换。2026-06-03 进一步把单 label 表面距离计算从 6 次 `distance_transform_edt` 合并到 2 次，validation 阶段约 2.3× 加速。

## 当前运行状态

2026-06-03 已完成：
- **质量评估指标扩展**：把 quality 评估报告补齐到 6 类医学影像主流指标（Dice、IoU、Pixel Accuracy、Hausdorff Distance、HD95、ASD）。`src/report/exportReport.ts` 报告模板新增 3 个 metric group：区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD（共 19 张卡片，HD/HD95/ASD 卡片用 mm 单位 + 越低越好的色阶：≤1mm 绿、≤3mm 黄、>3mm 红）。逐标签表新增 4 列：像素准确率、ASD (mm)、HD95 (mm)、HD (mm)；额外显示 NIfTI spacing 和 surface_distance_unit 标签。`src/inference/inferenceClient.ts` 的 `ValidationSummary` / `LabelMetric` 增补 12 个新字段：pixel_accuracy / mean_pixel_accuracy / min_pixel_accuracy / foreground_pixel_accuracy、mean_asd / max_asd / foreground_asd、mean_hd / max_hd / foreground_hd、mean_hd95 / max_hd95 / foreground_hd95、surface_distance_unit="mm"、spacing=[sx, sy, sz]。
- **表面距离计算加速**：`server/main.py` 新增 `surface_distances()`，把单 label 的 `distance_transform_edt` 调用从 6 次合并到 2 次（预测→参考、参考→预测各一次），通过 value 数组派生 `asd` / `hd` / `hd95`。`compute_label_metrics()` 与 foreground metrics 都改用新函数；旧 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 保留为 legacy 供回归测试对照。AMOS 0117 quality 缓存命中实测：validation 阶段从 `38.86s` 降到 `16.78s`，约 2.3× 加速。
- **回归测试**：`tests/backendState.test.py` 新增 `test_surface_distances_matches_legacy_individual_functions`（4 shape × 8 场景 1e-9 精度对照）、`test_surface_distances_uses_fewer_distance_transforms_than_legacy`（patch `scipy.ndimage.distance_transform_edt` 计数恒为 2）、`test_compute_label_metrics_with_surface_distances_faster_than_legacy`（wall-time 加速比 ≥30% 断言）；`tests/imagingLogic.test.ts` 新增全部新 metric 字段的 source-grep 约束和 `parseInferenceEvent()` complete 事件解析值测试。
- **基线数值不变**：本轮不修改 AMOS `quality` profile `b3c528cc9e20`（mean Dice 0.924780）、FLARE22 自动 remap `a717dacf42d3`（mean Dice 0.926）、FLARE22 离线 remap `86b0153d0a73`（mean Dice 0.893127）三套历史基线；新指标在 AMOS quality 缓存命中（如 `2d477d8bbd7d`）上的具体数值为 mean Pixel Accuracy `0.999855`、mean HD `9.59281mm`、mean HD95 `3.596449mm`、mean ASD `0.660724mm`。

2026-06-01 已完成：
- **本地缓存演示 7 步**：AMOS 0117 cache hit（`aea4e7cdbaf0`，命中 2026-05-23 历史推理 `009d4efdc5f6`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）
- **新增 `tools/seed_demo_cache.py`**：幂等可重跑的预热脚本，7 字段 cache_key 计算后写 `job_summary.json` 让 `009d4efdc5f6` 接入 `find_cached_prediction()`
- **新增 `docs/local-cache-demo-runbook.md`**：本地缓存演示复跑手册（启动命令、关键路径、cache_key 7 字段、4 个已知约束）
- **新增 spec/plan**：`docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`、`docs/superpowers/plans/2026-06-01-local-cache-demo.md`
- **后端依赖补充**：在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装了 `fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30`
- **2026-06-01 晚间 cache 链路补丁**：FLARE22 cache hit 现在能正确显示历史 validation 摘要（0.893/0.674/0.950），不再显示 AMOS 数据错位或"待验证"。修复点：
  - `server/main.py` 新增 `_load_cached_validation_summary()`；`complete_cached_job()` 在无当前 validation 时回退到 cache_source_job_id 的 `validation_summary.json`，并加 `historical: true`、`source_job_id` 标记。
  - `find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序，优先选带 `validation_summary.json` 的 cache_source，避免命中空 job 目录。
  - `tools/rewrite_flare22_historical_summary.py` 新增：因新预测 `0aa7323a4c01` 与历史 `86b0153d0a73` 字节不同（cache_key 也不一致），按 2026-05-26 remap 后的 metrics 把 validation_summary.json 写入 0aa7323a4c01 的 output。
  - 前端 `getValidationStatusCopy()` 增加 `cachedResult` 参数，区分"无历史验证摘要"和"（历史离线缓存摘要）"；`inferenceClient.ts` 增加 `cached_result` / `cache_source_job_id` / `historical` / `source_job_id` 字段。
  - `tests/backendState.test.py` 增加 `test_cached_prediction_falls_back_to_source_validation_summary` 和 `test_cached_prediction_without_historical_validation_summary`。
  - **关键发现**：`SEGMENTATION_REFERENCE_CASES_JSON` 必须指向 `examples/reference_cases.json`（或 `nnunetv2_files/reference_cases.local.json`），否则 `/api/samples` 只会返回内置 `amos_0117`，FLARE22 Tr 0009 不会出现在参考病例列表中。这条 runbook 写明但现场容易漏。

2026-05-31 已完成：
- 显式 `label_taxonomy=auto|AMOS22|FLARE22` 功能，AMOS 原生标签不再被自动误判为 FLARE22
- AMOS CT 高分辨率在线推理（768×768×103，2D nnUNet，fast profile，mean_dice=0.77724）
- 校园网 Windows 前端直连 Ubuntu FastAPI 后端的 5GPU / 5-fold soft ensemble smoke
- 服务器 runtime 更新包 `server-runtime-package-20260531.zip`，zip 内已按 `server/...` 项目结构组织，可在项目根目录解压覆盖

当前后续重点：
- 服务器 AMOS/FLARE validation 复跑：显式选择 `AMOS22` / `FLARE22` 后分别确认 `remap_applied` 状态
- server mode gating 继续收口：`runtime_target=server` 只依赖服务器 runtime 配置，不被本地 Windows nnUNet 文件缺失阻断
- 高分辨率 CT 推理优化评估：预降采样与 3D 模型可行性
- AMOS 预热预测的 review 状态（stomach 0.556）：复跑 quality 真实推理或新训练权重接入后可换更新预测
- 质量评估新指标推广：把 `surface_distances` 2 EDT 模式应用到后续 3D 模型评估和跨数据集验证

## 当前状态

- 前端入口：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 后端模式：模型资源齐备时为 `real-nnunetv2`，缺失时为 `unavailable`
- 当前主要参考病例：AMOS 0117、FLARE22 Tr 0009
- 当前新权重：`nnunetv2_files/checkpoint_best.pth`
- 自动 taxonomy remap：已实现，FLARE22 在线验证 mean_dice 从 0.073 提升到 0.926；服务器最新 FLARE 轮次约 `mean Dice=0.891`、`foreground Dice=0.951`。显式 `label_taxonomy=auto|AMOS22|FLARE22` 已接入，AMOS22 选择下不会执行 FLARE remap，`auto` 模式也更保守。
- 主要进展和实验记录：见 [REVIEW.md](./REVIEW.md)、[ACCEPTANCE.md](./ACCEPTANCE.md) 与 [SEGMENTATION_EXPERIMENT_COMPARISON.md](./SEGMENTATION_EXPERIMENT_COMPARISON.md)
- 代码讲解材料：见 [CODE_MODULE_GUIDE.md](./CODE_MODULE_GUIDE.md)
- 服务器 runtime 部署包：`deployment-packages/server-runtime-package-20260531.zip`，配套最短操作清单见 `deployment-packages/server-runtime-quickstart-20260531.md`。该包只包含后端运行代码和 `server/requirements.txt`，不包含真实 CT/NIfTI、checkpoint、`.env`、日志或推理输出；zip 内已包含 `server/` 前缀，应在项目根目录解压覆盖。
- 当前推荐部署顺序：校园网 API 直连和 Ubuntu 22.04 真实 5GPU smoke test 已初步跑通；后续先用 20260531 runtime 包更新服务器并复跑 AMOS/FLARE 显式 taxonomy validation，再继续收口 server 模式 gating，最后再考虑 Tailscale / WireGuard 或公网 HTTPS、鉴权、大文件上传和 SSE 反代。

## 主要功能

- 读取并浏览 `.nii` / `.nii.gz` CT 体数据。
- 支持 Axial、Sagittal、Coronal 三正交视图联动。
- 支持窗宽窗位、切片切换、缩放、overlay / split / side / difference 对比。
- `split` 分屏模式表示原图与分割 mask 的滑动对比，不是 Axial / Sagittal / Coronal 布局切换。
- 点击非背景 label 后展示对应器官说明。
- 通过本地 FastAPI 创建 nnUNetv2 推理任务，并通过 SSE 获取进度。
- 底部“切片与流程日志”区域展示 SSE 阶段进度条、当前阶段、job id、推理模式、已耗时和最近阶段日志。
- 推理完成后下载 NIfTI 分割结果并回填 GUI。
- 前端基于回填后的分割 mask 和 NIfTI spacing 执行纯 CPU 影像量化分析，自动计算器官体积、体素数、最大轴向截面积、包围盒尺寸、头足向长度估算和三维最长径估算；壁厚、精确管腔面积和中心线长度只作为需专用标签/后续算法的说明，不伪造临床数值。
- 后端会按当前模型 `dataset.json.file_ending` 规范化输入文件名；当前模型要求 `.nii.gz`，所以 `.nii` 上传会转为 nnUNet 可识别的 `_0000.nii.gz` 输入。
- 推理运行中可点击”取消推理”，后端会请求终止当前 nnUNetv2 子进程并通过 SSE 回写取消状态。
- 长时间推理期间后端会定期发送心跳事件（间隔 10 秒），前端底部进度 rail 更新已耗时和资源快照，避免界面显示停滞。
- 支持通过"标签 CT 导入"按钮或拖拽上传标签 NIfTI 文件，推理完成后自动执行在线 Dice 验证。前端会提交 `label_taxonomy=auto|AMOS22|FLARE22` 和 `dataset_hint`（由参考病例 `dataset` 字段在 `loadReferenceCase()` 阶段自动设置，AMOS22 / FLARE22 / 其他）：`AMOS22` 强制不执行 FLARE remap，`FLARE22` 强制执行 FLARE22 → AMOS22 remap，`auto` + `dataset_hint=FLARE22` 触发参考病例驱动的 remap（解决 FLARE22 真实 1-13 标签与 AMOS 真实 1-13 标签在裸 ID 集合上不可分的问题），`auto` 无 hint 时退化为保守自动检测；validation 结果中的 `remap_applied`、`remap_source`、`label_taxonomy` 和 `dataset_hint` 是解释 Dice 的关键字段。
- 持久化 job summary、阶段耗时、结果大小、资源快照和 nnUNetv2 日志尾部。
- 支持同输入、同 checkpoint、同推理配置的历史预测结果缓存回填：`cached-real-nnunetv2`。缓存只复用 NIfTI 预测结果；validation 会按本次请求的标签文件或内置参考标签重新计算，无当前标签时不复用旧 validation。
- 支持导出分割报告（HTML / JSON / PDF 三种格式），报告包含概览、6 类医学影像主流验证指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD，按 NIfTI spacing 计算 mm）、逐标签指标、影像量化分析、器官列表、关键发现、测量点和推理时间线。JSON 报告当前使用 `schema_version: "1.1"` 并包含 `quantification` 字段；PDF 导出使用浏览器原生打印，不引入第三方 PDF 库。距离指标（HD / HD95 / ASD）在 HTML 报告内使用 ≤1mm 绿 / ≤3mm 黄 / >3mm 红的色阶显示；与 Dice / IoU 的 0.85/0.70 阈值互不影响。

## 在线推理速度策略

当前已验证有效的加速路径是历史结果缓存：同一输入、同一 checkpoint、同一模型配置和同一推理参数重复提交时，后端会返回 `cached-real-nnunetv2`，可把重复演示和复核等待时间降到秒级。该缓存语义只覆盖预测结果；Dice/validation 仍绑定当前请求上下文，不再从缓存来源 job 继承旧指标。

未缓存首次推理仍主要受 3D full-res sliding-window 计算影响。AMOS 0117 同脚本单次对照中，`quality` 耗时 `1360.398s` 且验证通过；`fast` 耗时 `384.345s`，但 mean Dice 降到 `0.777243`，并对 label 14/15 产生小体积假阳性。因此默认/正式报告应使用 `quality`，`fast` 只能作为快速预览或演示候选。persistent worker 未证明能加速；当前只作为实验路径保留。

前端“分割控制”面板现在提供两个运行位置：`服务器运行` 和 `本地运行`。默认推荐 `服务器运行`，后端会按 Linux 服务器 5 张 GPU 并行跑 5 个 fold、保存 softmax 概率图，并通过 `nnUNetv2_ensemble` 软投票生成正式结果；`本地运行` 保留当前单机 nnUNetv2 路径，作为开发调试和服务器不可用时的保底方案。

前端“分割控制”面板同时提供 `质量推理` 和 `快速预览` 两个推理模式。默认选择 `质量推理`；选择 `快速预览` 时界面会显示“需人工复核”提示，成功结果元信息也会标注为快速预览结果，避免误认为正式报告依据。

后端仍支持环境变量作为默认配置；前端每次提交 job 时会把所选 `runtime_target` 和 `inference_profile` 显式传给 `/api/segment/jobs`。最终生效的 `runtime_target` 与 `inference_options` 会写入创建响应、job state、SSE complete 事件和 `job_summary.json`，并纳入 cache key，避免本地 fold0 结果、服务器 5-fold ensemble 结果和不同质量/速度参数误用同一缓存：

```powershell
$env:SEGMENTATION_RUNTIME_TARGET='server'  # 可选 local|server
$env:SEGMENTATION_INFERENCE_PROFILE='fast'
$env:SEGMENTATION_DISABLE_TTA='1'
$env:SEGMENTATION_TILE_STEP_SIZE='1.0'
```

含义：

- `SEGMENTATION_RUNTIME_TARGET=server|local`：默认运行位置；前端提交 job 时会显式传入 `runtime_target`，`server` 使用 5-GPU 5-fold soft ensemble，`local` 使用当前本地 nnUNetv2 保底路径。
- `SEGMENTATION_SERVER_GPUS=0,1,2,3,4` 与 `SEGMENTATION_SERVER_FOLDS=0,1,2,3,4`：服务器运行时的 GPU/fold 映射，不足的 GPU 会复用最后一个配置值。
- `SEGMENTATION_SERVER_NNUNET_RAW`、`SEGMENTATION_SERVER_NNUNET_PREPROCESSED`、`SEGMENTATION_SERVER_NNUNET_RESULTS`：服务器 nnUNet 数据目录，默认分别指向 `/mnt/data0/LUO_Zheng/nnUNet_raw`、`/mnt/data0/LUO_Zheng/nnUNet_preprocessed`、`/mnt/data0/LUO_Zheng/nnUNet_results`。
- `SEGMENTATION_SERVER_OUTPUT_ROOT`：服务器 5-fold 中间结果和 ensemble 输出根目录，默认 `/mnt/data0/LUO_Zheng/result/gui_jobs`。
- `SEGMENTATION_SERVER_EVALUATE_SCRIPT`、`SEGMENTATION_SERVER_LABELS_DIR`、`SEGMENTATION_SERVER_DATASET_JSON`：服务器评估脚本、默认标签目录和 dataset.json；上传标签时 GUI 仍会优先按本次标签计算在线 validation。
- `SEGMENTATION_DEVICE`：推理设备，可选 `cuda`、`cpu`、`mps`，默认 `cuda`。
- `SEGMENTATION_INFERENCE_PROFILE=quality`：默认质量模式，nnUNetv2 默认 `tile_step_size=0.5`，保留 TTA/mirroring；用于正式结果和报告依据。
- `SEGMENTATION_INFERENCE_PROFILE=fast`：在线快速模式，默认 `SEGMENTATION_DISABLE_TTA=1`，`SEGMENTATION_TILE_STEP_SIZE=1.0`。速度更快，但本地 AMOS 0117 对照已显示质量明显下降，只能作为快速预览并需人工复核。
- `SEGMENTATION_DISABLE_TTA`：显式控制是否关闭 mirroring/TTA。
- `SEGMENTATION_TILE_STEP_SIZE`：控制 sliding-window 步长，允许 `0.1` 到 `1.0`；越大通常越快但重叠更少。
- `SEGMENTATION_NOT_ON_DEVICE=1`：关闭 `perform_everything_on_device`，主要用于降低显存压力，不保证更快。
- `SEGMENTATION_PERSISTENT_WORKER=1`：实验开关，仅建议用于性能对照；2026-05-29 已修复复用 worker 时 stdout reader 竞争消费事件的问题，并通过轻量 shutdown smoke，但当前仍没有真实长耗时推理加速证据。

## 本地运行

安装依赖：

```powershell
npm install
```

启动前端：

```powershell
npm run dev -- --port 5173
```

启动后端。默认推理设备为 `cuda`，默认推理模式为 `质量推理`：

```powershell
$env:SEGMENTATION_DEVICE='cuda'   # 可选，默认已是 cuda
$env:SEGMENTATION_INFERENCE_PROFILE='quality'
$env:SEGMENTATION_PREPROCESS_WORKERS='2'
$env:SEGMENTATION_EXPORT_WORKERS='2'
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

## 局域网运行

局域网联调时，前端通过 `VITE_API_ENDPOINT` 指向后端机器，后端通过 `SEGMENTATION_ALLOWED_ORIGINS` 放行前端来源。

前端机器：

```powershell
$env:VITE_API_ENDPOINT='http://<后端机器IP>:8000'
npm run dev:lan
```

后端机器：

```powershell
$env:SEGMENTATION_ALLOWED_ORIGINS='http://<前端机器IP>:5173'
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

验收时至少检查：

- 局域网设备可打开 `http://<前端机器IP>:5173`。
- 局域网设备可访问 `http://<后端机器IP>:8000/api/health`。
- 浏览器控制台无 CORS 报错。
- 上传 CT、SSE 进度、取消任务、下载结果和标签 validation 均可用。

快速预览示例：

```powershell
$env:SEGMENTATION_RUNTIME_TARGET='server'  # 可选 local|server
$env:SEGMENTATION_INFERENCE_PROFILE='fast'
$env:SEGMENTATION_DISABLE_TTA='1'
$env:SEGMENTATION_TILE_STEP_SIZE='1.0'
```

后端 Python 依赖见：

```text
server/requirements.txt
```

## 模型和参考病例文件

真实数据和权重不进入仓库。当前 `.gitignore` 排除：

- `nnunetv2_files/`
- `server/work/`
- `.test-output/`
- `*.nii`
- `*.nii.gz`
- `*.pth`
- `*.pt`

本地真实推理至少需要：

```text
nnunetv2_files/checkpoint_best.pth
nnunetv2_files/amos_0117(3).nii.gz
nnunetv2_files/amos_0117(2).nii.gz
```

可通过 `SEGMENTATION_REFERENCE_CASES_JSON` 登记更多参考病例，格式见 [reference_cases.example.json](./reference_cases.example.json)。

## 当前验收记录

新权重 AMOS 0117 未缓存真实推理：

| 项目 | 结果 |
|---|---|
| job id | `27216eb73220` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| device | `cuda` |
| duration_seconds | `1124.327` |
| phase_timings | `persistent_worker=1121.592`, `validation=2.527` |
| result_size_bytes | `141569` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |
| validation status | `passed` |
| mean_dice | `0.924791` |
| foreground_dice | `0.980316` |
| min_dice | `0.846551` |

新权重同输入缓存回填：

| 项目 | 结果 |
|---|---|
| job id | `f200f16f47be` |
| mode | `cached-real-nnunetv2` |
| cached_result | `true` |
| cache_source_job_id | `27216eb73220` |
| elapsed_seconds | `3.532` |
| result_status | `200` |
| result_bytes | `141569` |

这些记录只代表 AMOS 0117 的本地验收，不代表更多外部病例已经完成泛化验证。

FLARE22 Tr 0009 非 AMOS 在线推理补充：

| 项目 | 结果 |
|---|---|
| job id | `86b0153d0a73` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| duration_seconds | `237.323` |
| result_size_bytes | `120761` |
| 后端自动验证 | 该参考病例 registry 中关闭，`validation_available=false`；用户上传标签文件时可走自动 taxonomy remap 在线验证 |
| 离线 remap mean Dice | `0.893127` |
| 离线 remap min Dice | `0.673730`，最低标签为十二指肠 |

该记录只能作为非 AMOS、按器官名重映射后的对照证据；FLARE22 label ID 与当前 AMOS22 checkpoint 不一致，不能写成 AMOS 原生自动验证。

FLARE22 Tr 0009 + 标签上传在线验证：

| 项目 | 结果 |
|---|---|
| job id | `bf20f0ec4456` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| duration_seconds | `222.6` |
| 标签文件 | 已上传（131 KB），`label_path` 非空 |
| validation status | `review` |
| mean_dice | `0.073`（taxonomy 错位） |
| 前景 Dice | `0.950` |
| label 2（右肾）Dice | `0.945` |
| 结论 | 标签传输链路修复成功；Dice 极低是 FLARE22 与 AMOS22 标签 ID 语义错位导致，非模型质量问题。离线 remap 后 mean_dice=0.893。 |

该记录验证了标签文件在线传输和 validation 链路可用；taxonomy 错位问题已通过自动 remap 解决。

FLARE22 Tr 0009 + 自动 taxonomy remap 在线验证：

| 项目 | 结果 |
|---|---|
| job id | `a717dacf42d3` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| remap_applied | `true` |
| remap_source | `FLARE22` |
| mean_dice | `0.926` |
| 验证状态 | `passed` |

自动 taxonomy remap 上线后，FLARE22 标签在线验证从 mean_dice=0.073 提升到 0.926。后端 `server/taxonomy.py` 自动检测 FLARE22 数据集并按器官名重映射标签 ID，无需手动干预。跨数据集在线验证链路正式打通。

## 2026-06-01 本地缓存演示补充

为竞赛 PPT 演示准备的"本地缓存演示 7 步"已经在 Windows 单机 RTX 4060 Laptop 跑通，演示 cache hit → 真实推理 → cache hit 的完整链路：

| Phase | job id | mode | 耗时 | 备注 |
|---|---|---|---|---|
| A：AMOS 0117 cache hit | `aea4e7cdbaf0` | `cached-real-nnunetv2` | 命中 | 命中 2026-05-23 历史推理 `009d4efdc5f6`（review 状态，stomach 0.556），不是新一轮 AMOS 基线 |
| B：FLARE22 Tr 0009 真实推理 | `0aa7323a4c01` | `real-nnunetv2` | `218s` | `remap_applied=true`，`remap_source=FLARE22`；本地单机 fold0，仅作 cache demo Phase B 链路证据 |
| C：FLARE22 Tr 0009 cache hit | `02da885c97d8` | `cached-real-nnunetv2` | `0.001s` | 命中 Phase B `0aa7323a4c01` |

该轮新增工具与文档：

- `tools/seed_demo_cache.py`：幂等预热脚本，重算 7 字段 cache_key 后写 `job_summary.json` 让 `009d4efdc5f6` 进入缓存索引。
- `docs/local-cache-demo-runbook.md`：本地缓存演示复跑手册，覆盖启动命令、关键路径、cache_key 7 字段和 4 个已知约束。
- `docs/superpowers/specs/2026-06-01-local-cache-demo-design.md` 与 `docs/superpowers/plans/2026-06-01-local-cache-demo.md`。

该记录是工程链路演示证据，**不替代** AMOS / FLARE22 正式质量基线：AMOS 基线仍是本地 quality `b3c528cc9e20`（mean_dice 0.924780），跨数据集在线基线仍是服务器 5-fold ensemble `a717dacf42d3`（mean_dice 0.926）。

## 2026-05-31 服务器在线推理补充

校园网链路已经从“部署准备”推进到“可运行 smoke”：Windows 前端通过 `VITE_API_ENDPOINT=http://10.102.1.202:8000` 调用 Ubuntu FastAPI 后端，服务器执行 5-fold 并行推理、soft ensemble，并把 NIfTI 结果下载回 GUI 三视图。

| 轮次 | 结果 | 解读 |
|---|---|---|
| FLARE22 + 标签 | mean Dice 约 `0.891`，foreground Dice 约 `0.951`，约 `3分48秒` | 自动 FLARE22 → AMOS22 remap 后指标合理，可作为服务器链路跑通证据。 |
| AMOS 0117 + AMOS 标签 | mean Dice `0.076015`，foreground Dice `0.979808`，约 `9分46秒` | 前景 Dice 很高但逐器官 Dice 大面积为 0，且报告显示 `remap_source=FLARE22`，更像 AMOS 标签被误 remap，不应解读为模型完全失败。 |

下一轮计划已记录在 `.planning/label-taxonomy-server-validation/` 和 `.planning/high-resolution-inference-optimization/`：显式 `label_taxonomy=auto|AMOS22|FLARE22` 已实现，后续重点是用 20260531 runtime 包更新服务器后复跑 AMOS/FLARE validation，并继续收口 `runtime_target=server` 的环境 gating。

## 三视图拖动体验

- 横断面拖动通常只改变 `x/y` 坐标，固定 `z` 切片不变，因此主要表现为十字线移动。
- 矢状面和冠状面拖动会连续改变 `z` 坐标，Axial 面板和辅助预览需要切换切片，渲染压力更高。
- 当前版本会记录是否正在拖动三视图；拖动期间三张视图仍实时变化，但使用 `interactive` 轻量切片预览降低每帧渲染成本。
- 松开鼠标后，当前坐标会自动恢复 `full` 完整质量切片渲染，最终查看质量不下降。
- 右侧 axial 预览和底部缩略图只在拖动空闲后同步，避免快速拖动时抢占主线程。

## 底部实时推理进度

- 点击“运行分割流程”后，底部 console 会立即显示结构化推理进度 rail。
- 进度百分比来自 `/api/segment/jobs/{job_id}/events` 的 SSE `progress/complete/error` 事件，不估算 nnUNetv2 内部 patch 级进度。
- 长时间停留在 `20%` 的真实 nnUNetv2 阶段会通过“推理运行中”、已耗时和阶段日志表达任务仍在运行。
- `fast` profile 在底部元信息中继续标注“快速预览 · 需人工复核”。
- 失败、取消和缓存命中路径都会保留底部状态和最近阶段日志，便于和后端 job id、`server/work` 输出及日志尾部对应。

## API 概览

- `GET /api/health`：后端和模型状态，含 worker、设备、推理参数。
- `GET /api/models`：模型与 label 表。
- `GET /api/samples`：本地参考病例列表。
- `GET /api/samples/{sample_id}/original`：下载参考病例原图。
- `GET /api/samples/{sample_id}/label`：下载参考病例标准答案。
- `POST /api/segment/jobs`：创建 nnUNetv2 推理任务；表单字段 `runtime_target=local|server` 可选择本地保底路径或服务器 5-GPU 5-fold soft ensemble，`inference_profile=quality|fast` 可按任务选择质量/速度配置，`label_taxonomy=auto|AMOS22|FLARE22` 控制标签体系解释，`label_file` 可选上传本次 validation 使用的标签 NIfTI。
- `GET /api/segment/jobs/{job_id}`：查询任务状态、耗时、资源、验证摘要和最终 `inference_options`。
- `GET /api/segment/jobs/{job_id}/events`：SSE 推理进度；推理期间每 10 秒发送心跳事件（含已耗时和资源快照）；complete 事件包含最终 `runtime_target` 和 `inference_options`。
- `POST /api/segment/jobs/{job_id}/cancel`：请求取消运行中任务。
- `GET /api/segment/jobs/{job_id}/result`：下载结果 NIfTI。

## 验证命令

```powershell
npm test
npm run build
```

后端测试会在 `.test-output/` 下生成临时模型和 job 文件，不需要提交真实 CT、checkpoint 或推理输出。

性能对照脚本：

```powershell
python tools/perf_no_cache_persistent.py --dry-run
python tools/perf_no_cache_persistent.py --inference-profile fast --disable-tta --tile-step-size 1.0
```

## 当前限制

- `confidenceThreshold` 仍是质控提示，不会真实作用于多标签概率图。
- `fast` profile 会牺牲一部分 nnUNetv2 默认质量设置。AMOS 0117 对照中 fast 明显更快，但 validation 为 `review`，不能作为正式报告结果。
- 单个新病例的首次未缓存推理仍可能达到分钟级到十几分钟级。
- 历史缓存只证明预测结果复用；不同标签文件下的 validation 必须以本次请求重新计算，不能把缓存来源 job 的 Dice 当作当前标签结果。
- persistent worker 的 reader 复用问题已修复并通过轻量 smoke，但真实连续无缓存推理是否更快仍未验证。
- FLARE22 部分标签自动 remap 需要至少两个明确错位 label；单 label 文件暂不自动推断数据集来源。
- 浏览器本身不能启动 Python/FastAPI 后端进程；在线推理前需要本地后端已在 `127.0.0.1:8000` 运行。
- 当前已有 AMOS 0117 原生标签验收和 FLARE22 Tr 0009 非 AMOS 推理补充（含标签上传在线验证和自动 taxonomy remap）；新增病例后仍应分别记录三正交显示、label 点击、推理耗时、资源快照和标准答案状态。
- AMOS cache demo Phase A 命中 `009d4efdc5f6` 是 2026-05-23 历史 review 状态预测（stomach Dice 0.556、mean_dice 0.891），不能作为新一轮 AMOS 质量基线；`SEGMENTATION_REFERENCE_CASES_JSON` 必须指向 `examples/reference_cases.json`（4 例模板），否则 `/api/samples` 退回只含 `amos_0117` 的 1 例状态。
- FLARE22 cache hit `02da885c97d8` 的 validation 摘要来自历史离线 remap（`86b0153d0a73` mean_dice=0.893127 / min_dice=0.67373 / fg=0.949908），不是本次请求重新推理；新计算仍未复跑时用 historical 回退。
