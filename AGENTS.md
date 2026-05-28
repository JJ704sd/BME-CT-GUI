# 仓库协作指南

## 项目现状（2026-05-28）

- 本仓库是腹部 CT 器官分割 GUI 原型，前端为 React + TypeScript + Vite，后端为 FastAPI + 本机 nnUNetv2 推理桥接。
- 当前 checkpoint 为 `nnunetv2_files/checkpoint_best.pth`，对应 AMOS22 / `Dataset001_AMOS22`，前景标签共 15 个。
- 当前主要参考病例为 AMOS 0117 和 FLARE22 Tr 0009；真实 CT、NIfTI、checkpoint、推理输出只保留在本机，不提交仓库。
- 后端模式包括 `real-nnunetv2`、`cached-real-nnunetv2`、`unavailable`，历史调试路径可能出现 `debug-label-fallback`。
- 已实现标签文件上传、在线 Dice 验证、FLARE22 自动 taxonomy remap。FLARE22 在线验证 mean_dice 已从 taxonomy 错位时的 0.073 提升到自动 remap 后的 0.926（job `a717dacf42d3`）。
- `quality` 是正式报告和验收基线；`fast` 只作为快速预览或演示候选，必须标注“需人工复核”。
- 主要证据文档：`README.md`、`ACCEPTANCE.md`、`REVIEW.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_RECENT_ROUNDS.md`、`CODE_MODULE_GUIDE.md`。

## 项目结构与模块组织

- `src/main.tsx`：前端主容器，编排病例选择、NIfTI 导入、三视图状态、推理提交、SSE 进度、标签上传、报告导出和结果回填。
- `src/components/OrthogonalViewer.tsx`：Axial / Sagittal / Coronal 三正交视图，包含十字线、点击/拖动坐标映射、overlay / split / side / difference 对比和拖动期轻量渲染。
- `src/imaging/`：NIfTI 体素映射、切片坐标换算、canvas 切片渲染与缓存。底层成像逻辑应优先放在这里，而不是继续塞进组件。
- `src/inference/inferenceClient.ts`：前端推理通信封装，负责创建 job、解析 SSE progress / complete / error / heartbeat、取消任务和下载结果。
- `src/report/exportReport.ts`：报告导出，支持 HTML / JSON / PDF。PDF 通过同一 HTML 模板和浏览器原生打印实现，不引入第三方 PDF 库。
- `src/data/organDetails.ts`、`src/organLayerLogic.ts`、`src/referenceCases.ts`、`src/viewerLogic.ts`：器官 label、评估层、参考病例归一化和可测试 UI 逻辑。
- `server/main.py`：FastAPI 主文件，管理模型状态、参考病例 registry、job 生命周期、输入规范化、nnUNetv2 调度、缓存、validation、取消和 SSE heartbeat。
- `server/taxonomy.py`：跨数据集标签 taxonomy 检测与自动重映射，当前覆盖 FLARE22 到 AMOS22 的器官名映射。
- `server/persistent_nnunet_worker.py`：实验性常驻 worker 路径。历史结果缓存是已验证的重复演示加速路径；persistent worker 不应被写成已验证首轮推理加速方案。
- `tests/`：Node、Python 和 Playwright 盒模型/布局测试。
- `tools/`：离线指标和性能对照脚本，例如 `segmentation_metrics_summary.py`、`perf_no_cache_persistent.py`。
- `.planning/`：任务规划和阶段性发现；`nnunetv2_files/`、`.test-output/`、`server/work/`、`dist/`、`node_modules/` 是本地数据、输出或构建目录，不进入提交。

## 构建、测试与本地运行

```powershell
npm install
npm run dev -- --port 5173

$env:SEGMENTATION_DEVICE='cuda'
$env:SEGMENTATION_INFERENCE_PROFILE='quality'
$env:SEGMENTATION_PREPROCESS_WORKERS='2'
$env:SEGMENTATION_EXPORT_WORKERS='2'
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000

npm test
npm run build
```

- 前端入口：`http://127.0.0.1:5173`。
- 后端健康检查：`http://127.0.0.1:8000/api/health`。
- 后端 Web 依赖见 `server/requirements.txt`；真实推理还依赖本机可用的 Python、torch、nnUNetv2、CUDA/CPU 环境和模型文件。
- 单独运行测试示例：`node tests/viewerLogic.test.ts`、`node tests/imagingLogic.test.ts`、`python tests/backendState.test.py`、`python tests/segmentationMetrics.test.py`。
- 浏览器布局测试命令：`npm run test:browser`。若本机缺 Playwright 浏览器，需要先按 Playwright 提示安装。

## 关键环境变量与推理配置

| 变量 | 默认值 | 说明 |
|---|---|---|
| `SEGMENTATION_DEVICE` | `cuda` | 推理设备：`cuda` / `cpu` / `mps` |
| `SEGMENTATION_INFERENCE_PROFILE` | `quality` | 默认推理 profile；前端提交 job 时也会显式传入 `inference_profile` |
| `SEGMENTATION_DISABLE_TTA` | `fast` 时默认 `1` | 是否关闭 mirroring / TTA |
| `SEGMENTATION_TILE_STEP_SIZE` | `quality=0.5`, `fast=1.0` | sliding-window 步长，越大通常越快但重叠更少 |
| `SEGMENTATION_NOT_ON_DEVICE` | `0` | 启用 nnUNetv2 `--not_on_device`，主要用于降低显存压力 |
| `SEGMENTATION_PREPROCESS_WORKERS` | `2` | nnUNetv2 预处理 worker 数 |
| `SEGMENTATION_EXPORT_WORKERS` | `2` | nnUNetv2 导出 worker 数 |
| `SEGMENTATION_PERSISTENT_WORKER` | 关闭 | 实验性常驻 worker 开关 |
| `SEGMENTATION_REFERENCE_CASES_JSON` | `reference_cases.json` | 私有参考病例 registry 路径 |
| `CUDA_VISIBLE_DEVICES` | 未设置 | 多 GPU 机器选择可见 GPU |

### 推理 profile 口径

- `quality`：默认正式路径，TTA/mirroring 开启，`tile_step_size=0.5`，用于报告、验收和基准对比。
- `fast`：关闭 TTA，默认 `tile_step_size=1.0`，速度更快但质量下降；AMOS 0117 对照中 mean Dice 明显降低，并出现 label 14/15 小体积假阳性，只能作预览。
- 缓存 key 包含输入 SHA256、checkpoint SHA256 和最终 `inference_options`，禁止 fast / quality 误用同一缓存。

## 关键 API 端点

| 端点 | 用途 |
|---|---|
| `GET /api/health` | 后端状态、模型就绪、worker、设备与推理配置 |
| `GET /api/models` | 当前模型和 label 表 |
| `GET /api/samples` | 本地参考病例列表 |
| `GET /api/samples/{sample_id}/original` | 下载参考病例原图 |
| `GET /api/samples/{sample_id}/label` | 下载参考病例标准答案 |
| `POST /api/segment/jobs` | 创建推理任务；表单字段包含 `file`、`inference_profile`，可选 `label_file` |
| `GET /api/segment/jobs/{job_id}` | 查询任务状态、耗时、资源、validation、缓存和最终推理配置 |
| `GET /api/segment/jobs/{job_id}/events` | SSE 进度流，事件包含 progress / complete / error / heartbeat |
| `POST /api/segment/jobs/{job_id}/cancel` | 请求取消运行中的 nnUNetv2 子进程 |
| `GET /api/segment/jobs/{job_id}/result` | 下载结果 NIfTI |

## 推理数据流与状态约定

1. 前端 `createInferenceJob()` 将源图、profile 和可选 `label_file` 提交到 `POST /api/segment/jobs`。
2. 后端创建 job，按当前模型 `dataset.json.file_ending` 规范化输入；当前模型要求 `.nii.gz`，`.nii` 上传会被转为 `_0000.nii.gz`。
3. 后端后台线程执行 nnUNetv2，期间写入 job state、phase timings、resource snapshots、日志尾部和 job summary。
4. 前端用 `EventSource` 监听 SSE。heartbeat 事件用于刷新已耗时和资源，不应污染阶段 timeline。
5. 推理完成后前端下载结果 NIfTI，解析为 mask volume 并回填三正交视图。
6. 若上传标签文件或参考病例有 compatible label，后端执行 validation；FLARE22 等非 AMOS 标签会通过 `server/taxonomy.py` 自动按器官名重映射，`remap_applied: true` 表示已生效。

## 编码风格与实现约束

- TypeScript 使用 2 空格缩进；React 组件使用 PascalCase；函数、变量和 hook 使用 camelCase。
- Python 后端沿用本项目现有 2 空格缩进风格，避免在同文件混入 4 空格缩进。
- 文档主体说明使用中文；医学术语、API、文件名、命令、profile、job id、Dice / IoU / HD 等技术字段可保留英文原名。
- 新增成像、坐标、切片或推理事件逻辑时，优先放入 `src/imaging/`、`src/inference/`、`src/viewerLogic.ts` 等可测试模块，减少 `src/main.tsx` 膨胀。
- UI 图标优先使用现有 `lucide-react`；不要用不可追踪的内联图标体系替代现有风格。
- `split` 是原图与分割 mask 的滑动对比模式，不是 Axial / Sagittal / Coronal 布局切换。
- `confidenceThreshold` 仍是质控提示，不会真实作用于多标签概率图；不要在文档或 UI 中写成真实阈值分割能力。

## 测试规范

- 新增或修改纯前端逻辑时补充/更新 `tests/*.test.ts`，优先覆盖可测试函数而不是只测 React 外壳。
- 修改三视图坐标、切片渲染、对比模式或响应式布局时，至少关注 `tests/imagingLogic.test.ts`、`tests/layoutRegression.test.ts` 和 `npm run test:browser`。
- 修改推理通信、SSE 事件、heartbeat、取消、缓存或 result meta 时，更新 `tests/imagingLogic.test.ts` 与 `tests/backendState.test.py`。
- 修改后端 job state、registry、validation、taxonomy remap 或缓存 key 时，更新 `tests/backendState.test.py`。
- 修改指标脚本时，更新 `tests/segmentationMetrics.test.py`。
- 修改验收、指标或讲解文档时，确认 `tests/acceptanceDocs.test.ts` 仍覆盖关键内容。
- 完成代码或文档口径变更前，能运行时优先执行 `npm test` 和 `npm run build`；无法运行必须在交付说明中写明原因。

## 文档与验收口径

- 涉及推理质量、性能、缓存、taxonomy、报告导出或验收证据的变更，应同步评估是否更新 `README.md`、`ACCEPTANCE.md`、`REVIEW.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_RECENT_ROUNDS.md` 和 `CODE_MODULE_GUIDE.md`。
- AMOS 0117 原生标签验证、FLARE22 自动 remap 在线验证、FLARE22 离线 remap 对照、fast preview 和 cached result 必须分开表述，不能混成同一类证据。
- `cached-real-nnunetv2` 只能证明同输入、同 checkpoint、同配置的历史结果可快速回填，不能替代未缓存真实推理耗时。
- 新增病例时，应记录病例来源、原图/标签状态、是否可自动 validation、三视图显示、label 点击、推理耗时、资源快照、result size、job id 和指标解释边界。
- 对外报告优先引用整理后的指标文档，而不是直接引用 `.test-output/` 临时文件。

## 提交与 Pull Request 规范

- 提交信息沿用现有格式：`feat: ...`、`fix: ...`、`docs: ...`、`merge ...`。
- PR 说明应包含变更范围、验证命令、是否影响推理指标、是否涉及真实数据、是否需要截图或观察路径。
- UI、三正交视图、报告导出或布局变更建议附截图或说明复现路径。
- 不要在未运行或未核对输出时宣称测试、构建、推理或指标“通过”。

## 安全与配置边界

- 不提交真实 CT、NIfTI、checkpoint、推理输出、私有 registry、`.env` 或日志；参见 `.gitignore`。
- 本地真实数据目录包括 `nnunetv2_files/`、`server/work/`、`.test-output/`，这些目录可读写但不应进入 Git。
- 私有参考病例通过 `SEGMENTATION_REFERENCE_CASES_JSON` 指向被忽略的 JSON，示例结构见 `reference_cases.example.json`。
- 浏览器不能启动 Python/FastAPI 后端；在线推理前必须确保后端已在 `127.0.0.1:8000` 运行。
- `server/taxonomy.py` 的 remap 只表示标签 ID 已按器官名对齐，不代表跨数据集验证可以和 AMOS 原生验证无条件合并。

## Linux 部署注意

- `server/main.py` 中当前 Windows 虚拟环境路径使用 `nnunet_env/Scripts/*.exe`；Linux 需改为 `nnunet_env/bin/*`，或实现按 `sys.platform` 选择 `Scripts` / `bin` 的跨平台 helper。
- Linux 上需确保 `nnunet_env/bin/nnUNetv2_predict_from_modelfolder` 和相关 Python 可执行文件有执行权限。
- 多卡部署用 `CUDA_VISIBLE_DEVICES` 选择 GPU；如启动多个后端实例，需要分别规划端口、工作目录和缓存边界。
