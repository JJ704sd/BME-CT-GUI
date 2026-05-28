# BME CT 分割 GUI 原型

本项目是面向腹部 CT 分割验证流程的本地 GUI 原型。前端使用 React + Vite，后端使用 FastAPI 桥接本机 nnUNetv2 环境，目标是完成 CT 浏览、三正交联动、器官 label 说明、真实模型推理回填、结果下载和验收记录。

截至 2026-05-26，项目已经作为独立 GUI 仓库维护；真实 CT、NIfTI、checkpoint 权重和推理输出仍只保留在本机，不提交到 GitHub。

## 当前状态

- 前端入口：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 后端模式：模型资源齐备时为 `real-nnunetv2`，缺失时为 `unavailable`
- 当前主要参考病例：AMOS 0117、FLARE22 Tr 0009
- 当前新权重：`nnunetv2_files/checkpoint_best.pth`
- 主要进展和实验记录：见 [REVIEW.md](./REVIEW.md)、[ACCEPTANCE.md](./ACCEPTANCE.md) 与 [SEGMENTATION_EXPERIMENT_COMPARISON.md](./SEGMENTATION_EXPERIMENT_COMPARISON.md)
- 代码讲解材料：见 [CODE_MODULE_GUIDE.md](./CODE_MODULE_GUIDE.md)

## 主要功能

- 读取并浏览 `.nii` / `.nii.gz` CT 体数据。
- 支持 Axial、Sagittal、Coronal 三正交视图联动。
- 支持窗宽窗位、切片切换、缩放、overlay / split / side / difference 对比。
- `split` 分屏模式表示原图与分割 mask 的滑动对比，不是 Axial / Sagittal / Coronal 布局切换。
- 点击非背景 label 后展示对应器官说明。
- 通过本地 FastAPI 创建 nnUNetv2 推理任务，并通过 SSE 获取进度。
- 底部“切片与流程日志”区域展示 SSE 阶段进度条、当前阶段、job id、推理模式、已耗时和最近阶段日志。
- 推理完成后下载 NIfTI 分割结果并回填 GUI。
- 后端会按当前模型 `dataset.json.file_ending` 规范化输入文件名；当前模型要求 `.nii.gz`，所以 `.nii` 上传会转为 nnUNet 可识别的 `_0000.nii.gz` 输入。
- 推理运行中可点击”取消推理”，后端会请求终止当前 nnUNetv2 子进程并通过 SSE 回写取消状态。
- 长时间推理期间后端会定期发送心跳事件（间隔 10 秒），前端底部进度 rail 更新已耗时和资源快照，避免界面显示停滞。
- 支持通过"标签 CT 导入"按钮或拖拽上传标签 NIfTI 文件，推理完成后自动执行在线 Dice 验证。当标签 ID 与当前 checkpoint 不一致时（如 FLARE22 vs AMOS22），后端自动检测数据集来源并按器官名重映射标签 ID，validation 结果中 `remap_applied: true` 表示已自动重映射。
- 持久化 job summary、阶段耗时、结果大小、资源快照和 nnUNetv2 日志尾部。
- 支持同输入、同 checkpoint、同推理配置的历史结果缓存回填：`cached-real-nnunetv2`。

## 在线推理速度策略

当前已验证有效的加速路径是历史结果缓存：同一输入、同一 checkpoint、同一模型配置和同一推理参数重复提交时，后端会返回 `cached-real-nnunetv2`，可把重复演示和复核等待时间降到秒级。

未缓存首次推理仍主要受 3D full-res sliding-window 计算影响。AMOS 0117 同脚本单次对照中，`quality` 耗时 `1360.398s` 且验证通过；`fast` 耗时 `384.345s`，但 mean Dice 降到 `0.777243`，并对 label 14/15 产生小体积假阳性。因此默认/正式报告应使用 `quality`，`fast` 只能作为快速预览或演示候选。persistent worker 未证明能加速；当前只作为实验路径保留。

前端“分割控制”面板现在提供 `质量推理` 和 `快速预览` 两个推理模式。默认选择 `质量推理`；选择 `快速预览` 时界面会显示“需人工复核”提示，成功结果元信息也会标注为快速预览结果，避免误认为正式报告依据。

后端仍支持环境变量作为默认配置；前端每次提交 job 时会把所选 `inference_profile` 显式传给 `/api/segment/jobs`。最终生效的 `inference_options` 会写入创建响应、job state、SSE complete 事件和 `job_summary.json`，并纳入 cache key，避免不同质量/速度参数误用同一缓存：

```powershell
$env:SEGMENTATION_INFERENCE_PROFILE='fast'
$env:SEGMENTATION_DISABLE_TTA='1'
$env:SEGMENTATION_TILE_STEP_SIZE='1.0'
```

含义：

- `SEGMENTATION_DEVICE`：推理设备，可选 `cuda`、`cpu`、`mps`，默认 `cuda`。
- `SEGMENTATION_INFERENCE_PROFILE=quality`：默认质量模式，nnUNetv2 默认 `tile_step_size=0.5`，保留 TTA/mirroring；用于正式结果和报告依据。
- `SEGMENTATION_INFERENCE_PROFILE=fast`：在线快速模式，默认 `SEGMENTATION_DISABLE_TTA=1`，`SEGMENTATION_TILE_STEP_SIZE=1.0`。速度更快，但本地 AMOS 0117 对照已显示质量明显下降，只能作为快速预览并需人工复核。
- `SEGMENTATION_DISABLE_TTA`：显式控制是否关闭 mirroring/TTA。
- `SEGMENTATION_TILE_STEP_SIZE`：控制 sliding-window 步长，允许 `0.1` 到 `1.0`；越大通常越快但重叠更少。
- `SEGMENTATION_NOT_ON_DEVICE=1`：关闭 `perform_everything_on_device`，主要用于降低显存压力，不保证更快。
- `SEGMENTATION_PERSISTENT_WORKER=1`：实验开关，仅建议用于性能对照；当前无缓存实验未证明能加速。

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

快速预览示例：

```powershell
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
| 后端自动验证 | 关闭，`validation_available=false` |
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

该记录验证了标签文件在线传输和 validation 链路可用；但 taxonomy 错位问题需自动 remap 才能得到有意义的在线指标。

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
- `POST /api/segment/jobs`：创建 nnUNetv2 推理任务；表单字段 `inference_profile=quality|fast` 可按任务选择质量/速度配置。
- `GET /api/segment/jobs/{job_id}`：查询任务状态、耗时、资源、验证摘要和最终 `inference_options`。
- `GET /api/segment/jobs/{job_id}/events`：SSE 推理进度；推理期间每 10 秒发送心跳事件（含已耗时和资源快照）；complete 事件包含最终 `inference_options`。
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
- 浏览器本身不能启动 Python/FastAPI 后端进程；在线推理前需要本地后端已在 `127.0.0.1:8000` 运行。
- 当前已有 AMOS 0117 原生标签验收和 FLARE22 Tr 0009 非 AMOS 推理补充（含标签上传在线验证）；新增病例后仍应分别记录三正交显示、label 点击、推理耗时、资源快照和标准答案状态。
