# 代码模块说明书

本说明书面向后续代码讲解、交接和答辩演示。它不替代 `README.md`、`ACCEPTANCE.md` 或 `REVIEW.md`，重点解释各模块在系统里的职责、入口和讲解顺序。

## 1. 推荐讲解路线

1. 从 `src/main.tsx` 讲产品主流程：病例选择、NIfTI 导入、三视图显示、在线推理、结果回填。
2. 到 `src/components/OrthogonalViewer.tsx` 讲三正交视图如何联动，以及本轮 `requestAnimationFrame` 合并渲染如何缓解快速鼠标移动卡帧。
3. 到 `src/imaging/voxelMapping.ts` 和 `src/imaging/sliceRenderer.ts` 讲体素坐标、切片坐标、方向映射和 canvas 切片渲染缓存。
4. 到 `src/inference/inferenceClient.ts` 讲前端如何创建 job、监听 SSE、下载结果。
5. 到 `src/report/exportReport.ts` 讲报告导出：HTML/JSON/PDF 三种格式、自包含 HTML 模板和数据收集。
6. 到 `server/main.py`、`server/server_inference.py` 和 `server/persistent_nnunet_worker.py` 讲 FastAPI 后端如何桥接 nnUNetv2、管理任务、缓存、validation，以及如何按 `runtime_target` 选择本地保底路径或服务器 5-fold soft ensemble 路径。
7. 到 `server/taxonomy.py` 讲跨数据集标签 taxonomy 检测与自动重映射：FLARE22 标签定义、器官名别名映射、`detect_dataset()` 自动识别数据集来源、`build_remap_mapping()` 按器官名建立 ID 映射、`apply_remap()` 用查找表重排参考标签数组。
8. 到 `tools/segmentation_metrics_summary.py` 讲 Dice、IoU、Voxel Accuracy 和 Hausdorff Distance 指标如何离线复算。
9. 最后用 `tests/` 和文档说明验收边界：AMOS 原生 validation 与 FLARE22 自动 taxonomy-remap validation 的区别。

## 2. 前端入口：`src/main.tsx`

`src/main.tsx` 是 GUI 的主容器，承担产品流程编排，不建议把底层成像逻辑继续塞进这个文件。

主要职责：

- 维护全局 UI 状态：当前模块、病例、体素坐标、切片、窗宽窗位、窗预设激活态、器官高亮集合、对比模式、推理状态、器官列表、报告状态。
- 解析本地 `.nii` / `.nii.gz`：`parseNiftiVolume()` 读取 NIfTI header 和 image buffer，生成前端可用的 volume 对象。
- 管理参考病例：通过 `/api/samples` 拉取本地 registry，把 `AMOS_0117`、`FLARE22_Tr_0009` 等真实病例显示到顶部病例选择器。
- 管理标签文件：`labelFile` 状态存储用户上传的标签 NIfTI，通过"标签 CT 导入"按钮或拖拽区域选择。`processVisualizationFile()` 中 `role === "label"` 分支处理标签文件。推理前若 `labelFile` 为 null 会 toast 提醒。
- 管理在线推理：`startSegmentation()` 调用 inference client 创建 job，监听进度，下载结果并回填到 GUI。标签文件通过 FormData 的 `label_file` 字段传给后端。
- 管理运行位置：`selectedRuntimeTarget` 控制 `服务器云端推理` / `本地在线推理`，提交 job 时写入 `runtime_target=server|local`；运行中会锁定选项，避免同一 job 的运行位置被误改。
- 管理底部实时进度：`inferenceTimeline` 记录结构化阶段日志，`inferenceStartedAt` 驱动已耗时展示，`inferenceProgressCopy` 集中生成底部 progress rail 文案。
- 管理 axial 预览：右侧文件卡片和底部切片时间轴使用 `renderCachedAxialNiftiSliceToDataUrl()`，复用 `src/imaging/sliceRenderer.ts` 的切片缓存，避免重复 canvas toDataURL。
- 管理窗预设联动：`applyWindowPreset()` 切换窗宽窗位时同步设置 `activePresetId` 和 `highlightedOrganIds`；`presetOrganMap` 映射预设到关联器官 ID 列表；`highlightTimerRef` / `presetToastTimerRef` 防止快速点击堆叠定时器。
- 管理模型信息展示：`modelOptions` 显示当前可用模型（AMOS22 腹部器官分割），下方 `.organ-category-grid` 按系统分类展示覆盖的 15 个器官。
- 管理报告导出：`handleExport()` 收集当前病例、模型、推理、验证、器官、测量、时间线等状态组装 `ReportData`，调用 `exportReport()` 生成 HTML/JSON/PDF 报告。`selectedExportFormat` 控制导出格式。

本轮性能相关改动：

- `handleVoxelCoordChange()` 不再在每个 `pointermove` 上直接提交 `setVoxelCoord`，而是进入 `scheduleVoxelCoordChange()`。
- `scheduleVoxelCoordChange()` 使用 `requestAnimationFrame` 合并高频体素坐标更新，每帧最多提交一次 `voxelCoord`；由拖动派生的 `selectedSlice` 辅助预览改为空闲后同步。
- `scheduleSelectedSlice()` 保留给非拖动路径的按帧 z 切片同步；主切片滑块和底部切片点击仍可正常驱动 z 坐标。

讲解重点：

- `voxelCoord` 是三视图联动的核心状态。
- `selectedSlice` 主要服务 axial 预览、滑条和底部时间轴。
- 在线推理的结果不是图片，而是 NIfTI mask volume；GUI 回填后仍走同一套三视图渲染。
- 底部 progress rail 只展示后端 SSE 阶段百分比，不伪造 nnUNetv2 内部细粒度进度。
- 窗预设联动：`presetOrganMap` 定义预设→器官映射；软组织映射全部 15 个器官，肺窗/骨窗为空（当前模型无相关标签）。高亮使用 CSS `organ-highlight-pulse` 动画，2.2 秒后自动淡出。
- 预设 Toast：`.preset-toast` 渲染在 `.preset-strip` 正下方，`flex-basis: 100%` 独占一行，2.8 秒后自动消失。
- 模型卡片：从虚构多模型改为单一真实 AMOS22 模型 + 4 个器官分类卡片（消化/泌尿/血管/其他）。

## 3. 三正交视图：`src/components/OrthogonalViewer.tsx`

`OrthogonalViewer` 负责 Axial、Sagittal、Coronal 三个方向的可视化和交互。

主要职责：

- 三个 panel 共用同一个 `coord`，不同方向只固定不同轴。
- 鼠标点击或拖动时，把屏幕点位转换成 slice point，再转换回 volume voxel coordinate。
- 用 `getCrosshairPercent()` 计算十字线位置，让十字线即时跟随最新 `coord`。
- 用 `renderNiftiSliceToDataUrl()` 渲染原图切片和 mask overlay。
- 点击非背景 label 时，通过 `onOrganPick()` 通知主页面打开器官说明。

本轮性能相关改动：

- 新增 `useRafCoalescedCoord()`：把高频 `coord` 变化合并到每帧一次的 `renderCoord`。
- 十字线仍使用即时 `props.coord`，所以视觉反馈优先。
- 切片图像使用 `renderCoord`，减少快速拖动时三张大图反复同步 rasterize。
- 拖动期间三张视图仍实时变化，但切片渲染使用 `interactive` 轻量质量；释放后自动恢复 `full` 完整质量。
- 点击拾取 label 不依赖坐标是否变化，即使点击当前十字线位置也仍能拾取器官。

讲解重点：

- `props.coord` 和 `renderCoord` 的区别：前者用于即时交互，后者用于较重的图像重绘。
- `requestAnimationFrame` 不是降低最终准确性，而是把中间无意义帧合并掉。
- `interactiveRenderMode` 不冻结视图，只降低拖动中的切片采样密度，保证三视图仍能连续观察。

## 4. 成像映射：`src/imaging/voxelMapping.ts`

该模块只做几何和坐标计算，不接触 DOM，也不创建 canvas，适合单元测试。

关键函数：

- `clampVoxelCoord()`：保证坐标不越界。
- `getOrientationDimensions()`：返回某个方向下显示切片的宽高。
- `getSliceIndexForOrientation()`：决定 axial/sagittal/coronal 分别固定哪个轴。
- `clientPointToSlicePoint()`：把浏览器坐标映射到切片像素坐标，处理 object-fit contain 产生的留白。
- `slicePointToVoxelCoord()`：把二维切片点还原成三维体素坐标。
- `getCrosshairPercent()`：输出十字线 CSS 百分比位置。
- `getSliceRenderKey()` / `getSliceImageCacheKey()`：为切片缓存提供稳定 key。

讲解重点：

- sagittal 和 coronal 的 y/z 方向会做翻转，目的是让显示方向符合医学阅片直觉。
- 映射逻辑被拆出来后，浏览器布局、NIfTI 渲染和坐标数学可以分别测试。

## 5. 切片渲染：`src/imaging/sliceRenderer.ts`

该模块把 NIfTI volume 的某个方向切片渲染成 data URL。

主要职责：

- `getVoxelValue()` / `getLabelAtVoxel()`：按 NIfTI datatype 从 ArrayBuffer 读取体素值。
- `renderNiftiSliceToDataUrl()`：根据 orientation、coord 和 mode 生成 intensity 或 mask 图片。
- `NiftiRenderQuality`：`interactive` 用于拖动实时预览，`full` 用于静止后的完整质量查看。
- 对 intensity 做当前切片 min/max 灰度归一化。
- 对 mask 使用固定调色板，并根据 `visibleLabels` 控制透明度。
- 使用 WeakMap 做 volume 级缓存，最多保存 `MAX_CACHED_SLICES_PER_VOLUME` 个切片。

讲解重点：

- 这是三视图里最重的同步逻辑，包含像素遍历、ImageData 写入和 `canvas.toDataURL()`。
- 本轮卡帧缓解不是改变算法结果，而是在 pointer move 路径上使用轻量实时预览，并让右侧/底部 axial 预览复用缓存。

## 6. 前端推理客户端：`src/inference/inferenceClient.ts`

该模块封装浏览器到 FastAPI 的所有推理通信。

主要职责：

- `createInferenceJob()`：提交源图、模型、运行位置、profile、后处理配置。可选附带 `label_file` 用于在线 Dice 验证。
- `parseInferenceEvent()`：解析 SSE 进度、完成、失败事件。
- `downloadInferenceResult()`：下载后端生成的 NIfTI mask。
- `fetchModelLabels()`：获取 checkpoint label 定义，保证前端器官列表和模型一致。
- `getInferenceStatusCopy()` / `getInferenceResultMeta()`：生成 UI 展示文案。

讲解重点：

- `quality` 是默认正式推理路径。
- `fast` 只作为快速预览，界面和结果元信息都需要标记“需人工复核”。
- `runtime_target` 会进入 job state、SSE complete event 和缓存 key，避免本地 fold0、服务器 5-fold ensemble、fast/quality 混用缓存。
- 失败事件中的 `log_tail` 会被前端保留到结构化 timeline，便于从底部状态追溯后端错误摘要。

## 7. 器官与病例数据

相关文件：

- `src/data/organDetails.ts`：默认器官 label、颜色、中文名称和器官说明。
- `src/organLayerLogic.ts`：把 label 列表转换成 UI 器官层，合并 validation 分数和人工质量状态。
- `src/referenceCases.ts`：归一化 `/api/samples` 返回值，提供参考病例 URL。
- `src/viewerLogic.ts`：主页面可测试的 UI 计算逻辑，例如病例 ID、切片窗口、配准状态、坐标去重。

讲解重点：

- `AMOS_0117` 是有原生 label 的自动 validation 病例。
- `FLARE22_Tr_0009` 在 `/api/samples` 中 `validation_available=false`，因为内置 registry 不把 FLARE22 标签直接当作 AMOS 原生标签使用。标签文件可通过"标签 CT 导入"上传；2026-05-28 自动 taxonomy remap 上线后，后端会检测 FLARE22 并按器官名重映射，job `a717dacf42d3` 在线 validation mean Dice 为 `0.926`。2026-05-29 起，至少两个明确错位 label 的 FLARE22 部分标签也可自动 remap；单 label 文件仍保持保守处理。历史 job `bf20f0ec4456` 的 `0.073` 是 remap 前的 taxonomy 错位示例。
- `shouldUpdateVoxelCoord()` 是本轮性能优化的基础小工具，用于阻止重复坐标更新。
- `getVoxelCoordDragCommit()` 用于三视图拖动时的坐标裁剪、去重和 axial selected slice 推导，避免把该逻辑写死在 React 事件处理里。

## 8. 报告导出：`src/report/exportReport.ts`

该模块负责将分割结果、验证指标、器官列表等信息导出为可分享的报告文件。

主要职责：

- `exportReport(data, format)`：根据格式分发到对应导出函数。
- `exportHtmlReport(data, printMode)`：生成自包含 HTML 文件（内联 CSS，`@media print` 友好）或打开新窗口触发 `window.print()`。
- `exportJsonReport(data)`：生成结构化 JSON，加 `schema_version` 和 `report_type` 字段。
- HTML 报告包含：概览（模型、推理模式、耗时、结果大小）、验证指标（mean/min/foreground Dice、逐标签表）、器官列表（颜色圆点 + 质控分数 + 解剖位置）、关键发现、测量点、推理时间线。
- `ReportData` 类型聚合前端已有状态：病例、模型、图像、验证、推理、器官、测量、时间线和 AI 发现。

讲解重点：

- PDF 导出不引入第三方库，复用同一 HTML 模板 + 浏览器原生打印。
- 报告不嵌入 CT 切片截图，避免文件体积膨胀和跨浏览器渲染问题。
- `downloadFile()` 使用 `Blob` + `URL.createObjectURL` 实现浏览器端文件下载。

## 9. 后端桥接：`server/main.py`

`server/main.py` 是 FastAPI 后端主文件，负责把前端请求转换成本地 nnUNetv2 推理任务。

主要职责：

- 暴露 API：`/api/health`、`/api/models`、`/api/samples`、`/api/segment/jobs`、job events、cancel、result。
- 读取本地参考病例 registry：默认 `reference_cases.json`，也支持 `SEGMENTATION_REFERENCE_CASES_JSON` 指向私有 registry。
- 管理 job state：进度、阶段、错误、结果路径、validation、缓存信息、资源快照、日志尾部。
- 准备 runtime model，把项目 checkpoint 接入 nnUNetv2 modelfolder 推理。
- 根据 `inference_profile` 生成 effective options，例如 `quality` / `fast`、TTA、tile step、device。
- 按当前模型 `dataset.json.file_ending` 规范化上传输入；当前权重要求 `.nii.gz`，因此 `.nii` 原图会被 gzip 成 nnUNetv2 可识别的 `_0000.nii.gz`。
- 对有 compatible label 的病例执行自动 validation；用户上传 `label_file` 时，validation 使用本次请求的标签文件。
- 对相同输入、相同 checkpoint、相同 options 的任务返回 `cached-real-nnunetv2`，但只复用预测 NIfTI；缓存命中后的 validation 按当前请求重新计算或为空，不继承缓存来源 job 的旧指标。
- 取消运行中任务时，`request_job_cancel()` 会标记 `cancel_requested` 并终止当前子进程；前端通过”取消推理”调用 `/api/segment/jobs/{job_id}/cancel`。
- 长时间推理期间会定期发送心跳事件：`push_heartbeat()` 每 10 秒通过 SSE 推送当前进度、已耗时和资源快照，避免前端在推理主阶段（如 `20%`）停留时显示停滞。常驻 worker 路径使用 `_read_worker_event_with_heartbeat()` 通过 `queue.Queue` 超时实现非阻塞心跳。
- 默认推理设备为 `cuda`（`get_predict_device()`），可通过 `SEGMENTATION_DEVICE` 环境变量覆盖。

讲解重点：

- `nnunetv2_files/`、`.test-output/`、`server/work/` 都是本地私有或临时输出，不进入 Git。
- 自动 validation 的前提是 label taxonomy 与 checkpoint 原生一致，或后端能通过 `server/taxonomy.py` 识别并自动 remap。FLARE22 已支持在线自动 remap；部分标签需至少两个明确错位 ID，单 label 文件仍需人工判断或后续显式数据集 hint。
- 心跳事件的 `heartbeat: true` 字段可用于前端区分心跳和真正的阶段进度；心跳失败不会中断推理。

## 10. 服务器推理编排：`server/server_inference.py`

`server/server_inference.py` 集中生成 Linux 服务器 5-GPU / 5-fold soft ensemble 所需的命令和环境变量，避免把服务器脚本细节散落在 FastAPI 路由中。

主要职责：

- 从环境变量读取服务器 nnUNet 数据目录、输出目录、dataset id、configuration、plans、fold 列表、GPU 列表和命令名。
- `build_server_fold_commands()` 为每个 fold 生成一条 `nnUNetv2_predict` 命令，并设置对应 `CUDA_VISIBLE_DEVICES`。
- `build_server_ensemble_command()` 生成 `nnUNetv2_ensemble` 命令，把 5 个 fold 的 softmax 概率输出集成为最终结果。
- `build_server_evaluate_command()` 在有评估脚本和标签目录时生成服务器侧评估命令；GUI 上传标签时仍以本次请求标签 validation 为准。

讲解重点：

- 服务器模式是正式推理候选路径，目标是 5 张 GPU 并行跑 5 个 fold 后做 soft ensemble；本地模式仍作为开发调试和服务器不可用时的保底。
- 服务器路径只负责命令构造和进程编排，job 生命周期、SSE、取消、结果下载、cache key 和 validation 仍由 `server/main.py` 统一管理。
- 真实 Linux 服务器端到端推理尚需单独 smoke test；在完成前，文档不能把服务器模式写成已完成质量验收。

## 11. 常驻推理 worker：`server/persistent_nnunet_worker.py`

该脚本承接后端启动的 persistent worker 路径，用于减少部分模型加载开销。

讲解重点：

- 目前已有实验证明历史结果缓存能显著加速重复演示。
- persistent worker 对未缓存首轮推理不应被宣传为已验证加速路径；相关限制在 `REVIEW.md` 和 `ACCEPTANCE.md` 中有记录。
- 常驻 worker 读取响应时使用进程级共享 `_persistent_worker_reader_thread()` + `queue.Queue` 实现非阻塞读取，超时后自动发送心跳，不阻塞主线程。2026-05-29 修复前，复用 worker 时每次读事件都会新建 stdout reader 线程，存在旧线程抢读后续事件的风险；当前 reader 状态会随 worker 进程创建和关闭统一维护。
- 目前只通过轻量 shutdown smoke 验证 worker 协议和 reader 清理，未重新完成真实长耗时无缓存推理加速验收。

## 12. 指标与性能工具

相关文件：

- `tools/segmentation_metrics_summary.py`：离线计算 Dice、IoU、Pixel/Voxel Accuracy、Hausdorff Distance，并生成 JSON/Markdown。
- `tools/perf_no_cache_persistent.py`：执行无缓存推理性能对照，记录 job、资源和输出。

讲解重点：

- 指标脚本可以用于 AMOS 原生 label，也可以用于 FLARE22 remapped reference，但文档必须明确区分解释边界。
- 对外报告时，应优先引用 `SEGMENTATION_METRICS_SUMMARY.md` 中已经整理过的指标，而不是直接引用临时输出。

## 13. 测试结构：`tests/`

主要测试：

- `tests/viewerLogic.test.ts`：纯 UI 逻辑。
- `tests/imagingLogic.test.ts`：坐标映射、切片 key、器官 label、推理事件解析，以及本轮性能优化的源码约束。
- `tests/imagingLogic.test.ts` 同时约束底部实时进度 rail、结构化 `inferenceTimeline` 和失败 `log_tail` 保留。
- `tests/acceptanceDocs.test.ts`：验收文档、指标文档、代码说明书的存在性和关键内容。
- `tests/backendState.test.py`：后端 job state、cache key、registry、validation 等行为。
- `tests/backendState.test.py` 覆盖 `.nii` 上传规范化为模型需要的 `.nii.gz`、运行中 job 取消、子进程 terminate 和取消事件记录。
- `tests/backendState.test.py` 还包含端到端推理流程测试（`test_e2e_inference_flow_create_events_result`），验证创建 job → 执行推理 → 事件序列 → 结果下载的完整链路。
- `tests/backendState.test.py` 覆盖缓存命中时 validation 不复用旧 job、带当前标签时重新 validation、persistent worker reader 连续读事件、部分 FLARE22 标签 remap 和后端上传文件名日志移除。
- `tests/imagingLogic.test.ts` 覆盖前端主流程和 inference client 不再包含上传标签文件名调试日志。
- `tests/segmentationMetrics.test.py`：指标脚本输出。
- `tests/browserLayout.test.ts` / `tests/layoutRegression.test.ts`：三视图布局和响应式约束。
- `tests/browserLayout.test.ts` 覆盖底部实时进度 rail 的桌面/移动布局，避免压缩三视图或产生横向溢出。
- `tests/perfTool.test.ts`：性能工具 dry-run 基础行为。

常用验证命令：

```powershell
npm test
npm run build
```

## 14. 本轮性能优化的讲解口径

分屏模式说明：

- `分屏` 用来对比原图和分割结果，不是切换三视图布局。
- 有 `maskVolume` 时，滑杆数值表示左侧多少比例显示分割 mask 叠加，右侧保留原始 CT。
- 没有分割结果时，分屏没有可对比对象，因此三视图不会显示分割线。
- 本轮修复后，三正交视图中的 `.ortho-mask` 会在 `.compare-split.has-mask` 下按 `--compare-position` 裁剪，并显示一条分割线。

问题现象：

- 快速点击或拖动三视图十字线时，三张切片图像会有轻微延迟和卡帧。

根因：

- 鼠标移动会触发体素坐标变化。
- 三视图切片、右侧 axial 预览、底部切片缩略图都可能同步生成 data URL。
- `canvas.toDataURL()` 和像素遍历会占用主线程，高频触发时会影响交互流畅度。

处理方式：

- 十字线位置继续绑定即时 `coord`，保持快速反馈。
- 三视图图像重绘改用 `requestAnimationFrame` 合并坐标变化，只渲染最新一帧。
- 拖动期间三视图仍实时变化，并使用 `interactive` 轻量切片；释放后使用 `full` 完整质量重新渲染当前坐标。
- 主页面 `voxelCoord` 与拖动派生的 `selectedSlice` 也按帧合并，避免右侧/底部预览在每个 pointer event 同步重绘。
- `selectedSliceSyncSourceRef` 区分 voxel 驱动和 slice 驱动同步，防止旧 selected slice 反向覆盖矢状/冠状拖动中的最新 z 坐标。
- axial 预览改用 `src/imaging/sliceRenderer.ts` 的缓存渲染函数，避免重复渲染已生成切片。

验证结果：

- `node tests/imagingLogic.test.ts` 覆盖了 rAF 合并渲染和坐标去重约束。
- `npm test` 通过。
- `npm run build` 通过。
- 浏览器烟测在 `http://127.0.0.1:5173/` 快速拖动三视图后无控制台错误，三视图图片非空白。

## 15. 数据与文档边界

- 真实 NIfTI、checkpoint、推理输出和私有 registry 不提交。
- 局域网运行时，前端 API 地址由 `VITE_API_ENDPOINT` 配置，Vite 通过 `npm run dev:lan` 监听局域网地址，后端通过 `SEGMENTATION_ALLOWED_ORIGINS` 放行实际浏览器来源；不应长期使用无限制公网来源。
- `AMOS_0117` 是当前自动 validation 的主要原生标签案例。
- `FLARE22_Tr_0009` 已完成真实 `quality` 在线推理、标签上传在线 validation 和自动 taxonomy remap 验证。remap 前 job `bf20f0ec4456` 的 Dice 低是 taxonomy 错位历史证据；remap 后 job `a717dacf42d3` mean Dice 为 `0.926`。
- 任何后续新增病例都应先判断 label taxonomy，再决定是否允许后端自动 validation；未知数据集和单 label 文件不能自动声明模型质量通过。
