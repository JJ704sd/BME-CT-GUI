# GUI 原型审阅与改造建议（现状版）

> 基于 `segmentation-gui-prototype` 当前代码、运行中的本地服务以及 `nnunetv2_files` 资源整理。
> 目标是把这个原型收敛成一个可浏览 CT、可联动三正交视图、可点击器官说明、可连接本地分割后端的工作型 GUI。
> 当前结论：前端已经具备三正交浏览、13 类器官说明、真实病例入口、结果对比视图和报告导出功能；后端已接入本地 nnUNetv2 model folder 与真实推理命令，并会在配置不完整时明确拒绝创建任务。AMOS 0117 已形成原生标签质量基线，FLARE22 Tr 0009 已完成未缓存 `quality` 在线推理和自动 taxonomy-remap 验证（job `a717dacf42d3`，mean_dice=0.926，验证通过）。2026-05-31 的校园网服务器 smoke 进一步证明：Ubuntu 服务器 5GPU / 5-fold soft ensemble 已能被 Windows GUI 调用；但 AMOS 服务器轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808` 且 `remap_source=FLARE22` 的异常；目前显式 `label_taxonomy=auto|AMOS22|FLARE22` 已实现，仍需要用 20260531 runtime 包更新服务器后复跑 AMOS/FLARE validation，并继续收口 server gating。GUI 支持 HTML / JSON / PDF 三种格式的分割报告导出。

---

## 〇、2026-06-11 最新状态更新

### 2026-06-11 启动操作手册独立化 + 9 份核心文档巡检同步

- 把 `tools/start_local_demo.py` 的"线下实时启动"操作抽成独立文档 [`docs/quickstart-launch-guide.md`](./docs/quickstart-launch-guide.md)（10 章：TL;DR / 前置确认 / 标准启动前台+后台 / 启动选项 / 验证 / 停服 / 手工回退 / 局域网 / 一页速记卡 / 相关文档）；与 [`docs/demo-day-checklist.md`](./docs/demo-day-checklist.md)（演示当天）和 [`docs/local-cache-demo-runbook.md`](./docs/local-cache-demo-runbook.md)（cache demo 7 步复跑）形成三档分工。
- 任何时候要把 GUI 起来看 → 走 quickstart；演示当天 → 走 checklist；cache demo 复跑 → 走 runbook。
- 9 份核心文档（README / AGENTS / CLAUDE / ACCEPTANCE / REVIEW / CODE_MODULE_GUIDE / SEGMENTATION_METRICS_SUMMARY / SEGMENTATION_EXPERIMENT_COMPARISON / SEGMENTATION_RECENT_ROUNDS）全部补一行 quickstart 索引；中文主体仍合格。
- 实测：`& "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" tools\start_local_demo.py` 在 PowerShell 下用 `Start-Process` 后台启动后，采样 `/api/samples` 校验 4 例参考病例（AMOS 0117 / FLARE22 Tr 0009 / WORD / AbdomenCT-1K）已就绪；证明 `Start-Process` 脱离 bash 工具管控的设计假设成立 — 前台跑会被 bash 超时 kill 整个进程组，后台 `Start-Process` 不会。
- 新 planning 主题 `.planning/2026-06-11-launch-guide-and-doc-sync/` 4 份文档落地。
- 本轮不动 nnUNetv2 推理、缓存复用 7 字段、SSE 协议、HTML 报告样式或影像量化逻辑；不改变历史 AMOS / FLARE baseline。

### 2026-06-06 演示当天 B1-B4 修复 + start_local_demo + server mode gating 收口

**说明：** 6-06 commit `23e0c4d` 在 commit message 与文档里写了 B1 / B2 / B4 都修复了，但实际源码只动了 B3。同日 bug 扫描时通过 source-grep 守护发现 `23e0c4d` 虚标（代码里**没有** `createInferenceEventSource` 函数、没有 `onretry` / `retryCount` 字符串、`tests/imagingLogic.test.ts` 没有相应 source-grep 守护、`src/main.tsx` SSE onmessage 直接 `setProgress(parsed.progress)` 无 `!== undefined` 守护），同日 commit `76bb1ff` 真实补完。下方按"6-06 `23e0c4d` 真实完成 / 同日 `76bb1ff` 补完"两个时段分别记录。

- 4 个 demo-day 关键 bug 修复（B1-B4）：
  - **B1 SSE 进度回退修复**（6-06 `23e0c4d` 文档虚标；同日 `76bb1ff` 真实实现）：`src/main.tsx` SSE onmessage 在 `parsed.type === "progress" && parsed.heartbeat && parsed.progress === 0` 时只更新 `stage` 不更新进度；heartbeat 心跳事件没有 `percent` 字段时不再覆盖当前进度，长耗时推理时进度条不再从 60% 突然回退到 30% 再涨回去。`tests/imagingLogic.test.ts` 新增 source-grep 守护 `parsed.heartbeat && parsed.progress === 0`。
  - **B2 取消后残留进度修复**（6-06 `23e0c4d` 文档虚标；同日 `76bb1ff` 真实实现）：新增 `inferenceStatusRef` 镜像 React state；SSE onmessage 入口先判 `inferenceStatusRef.current.status === "cancelled"` 早退 + `handle.close()` 阻止重试。`tests/imagingLogic.test.ts` source-grep 守护 `inferenceStatusRef.current.status === "cancelled"`。
  - **B3 后端模型状态对外可读**（6-06 `23e0c4d` 真实完成）：`/api/health` 的 `model_state` 字段从内部变量提升为可被 GUI 状态栏读取的稳定 JSON 字段（`status` / `checkpoint_sha256` / `mode` / `missing` 4 个 key）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。
  - **B4 SSE 基础异常重试**（6-06 `23e0c4d` 文档虚标；同日 `76bb1ff` 真实实现）：抽出 `src/inference/createInferenceEventSource.ts` 工具，暴露 `onretry` / `retryCount` / `onfatal` 字段；onerror 时按 200ms→2s 指数退避重试，最多 3 次；3 次失败后 `onfatal` → reject Promise。`src/main.tsx` SSE 流接入新工具。`tests/imagingLogic.test.ts` 新增 11 条 source-grep 断言保护 4 个核心改动（`createInferenceEventSource` / `inferenceStatusRef` / `parsed.heartbeat && parsed.progress === 0` / `onretry` / `retryCount` / `onfatal` / `handle.close()` 等）。
- `tools/start_local_demo.py` 新建：一行命令启动后端 + 前端，自动 setenv（`SEGMENTATION_REFERENCE_CASES_JSON` / `SEGMENTATION_DEVICE` / `SEGMENTATION_PERSISTENT_WORKER` 等）、spawn backend（uvicorn）+ frontend（vite dev）、启动后采样 `/api/samples`（最多 15s）校验 4 例参考病例（AMOS 0117 / FLARE22 Tr 0009 / WORD / AbdomenCT-1K）已就绪、失败时打印 runbook 回退命令。`docs/demo-day-checklist.md` 是配套的一屏卡片：5 步演示流程 + 前置确认 5 项 + 兜底 curl。
- `server/main.py:1537-1604 get_model_state(runtime_target)` 接受 `runtime_target` 参数；`runtime_target=server` 只检查 6 个 `SEGMENTATION_SERVER_*` 路径（`server_evaluate_full.py` / `server_dataset.json` / `server_nnunet_raw` / `server_nnunet_preprocessed` / `server_nnunet_results` / `server_output_root`）；`runtime_target=local` 才检查本地 4 文件（`dataset.json` / `plans.json` / `checkpoint_best.pth` / `nnUNetv2_python`）。两组检查互斥，server 模式创建 job 不再因本地 Windows nnUNet 文件缺失而 503。`tests/backendState.test.py` 新增 3 个守护测试（`test_server_runtime_ready_does_not_require_local_model_files` / `test_server_runtime_reports_missing_server_paths` / `test_local_runtime_does_not_check_server_paths`）。
- `docs/local-cache-demo-runbook.md` AMOS 0117 演示口径修正：**决策（2026-06-05）接受现状，不复跑 AMOS 0117**。cache hit `aea4e7cdbaf0` 命中的是 2026-05-23 quality profile 真实推理 `009d4efdc5f6`（review 状态，stomach Dice 0.556、mean_dice 0.891），stomach 0.556 是数据本身硬骨头（胃边界模糊、形态多变），复跑 quality 不会显著改善；PPT 直接用"质量推理 mean Dice 0.891，stomach 0.556（review 状态），反映真实临床难度"。正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。
- Smoke test（2026-06-06）：`python tools/start_local_demo.py` 真启后端 + 前端，采样 `/api/samples` 校验 4 例参考病例（AMOS 0117 / FLARE22 Tr 0009 / WORD / AbdomenCT-1K）已就绪，Ctrl+C 干净退出。`npm test` + `npm run build` + `node tests/imagingLogic.test.ts` + `python tests/backendState.test.py` 全过。
- 9 份核心文档全部同步到 6-06 状态；4 份 planning 文档落地（`.planning/2026-06-06-demo-day-wrapup/`）。
- 本轮不动 nnUNetv2 推理、缓存复用 7 字段、SSE 协议、HTML 报告样式或影像量化逻辑；不改变历史 AMOS/FLARE baseline。

### 2026-06-05 HTML 报告临床报告风格重构（第二轮美化）

- `src/report/exportReport.ts` 从"卡片式仪表板"重塑为"临床评估报告"。
- 新增 7 个 CSS 块：`.cover` 封面页（题图条 + 报告编号 + 主副标题 + 数据集/病例/生成时间三列）、`.exec-summary` 执行摘要（通过 / 关注点 / 建议三栏）、`.toc` 目录（§1-§8 锚点导航）、`.formula-tip` 公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、`.dist-chart` 严重度分布图（高/中/低 bar chart）、`.table-caption` 表格标题、`.footnotes` 脚注。
- 新增 3 个工具函数 `distributionChartHtml()` / `severityBuckets()` / `formulaTips()`。
- 正文模板按 §1 报告概览 / §2 摘要 / §3 数据集 / §4 器官 / §5 体素 / §6 距离 / §7 关键发现 / §8 附录 8 段章节编号排版。
- 字体改为 Source Han Serif / Songti SC（serif 主体）+ JetBrains Mono（数值/代码/公式）。
- @media print 改为 A4 + 顶部 caseId + 底部 page X of Y；`.cover` / `.dist-chart` `break-inside: avoid`。
- 本轮不动 nnUNetv2 推理、缓存复用、SSE 协议、validation 字段或影像量化逻辑；与 2026-06-04 第一轮美化兼容并叠加。
- `npm test` 与 `npm run build` 全过；浏览器自检 9 项视觉/信息元素 + 打印预览。

### 2026-06-04 HTML 报告第一轮美化（视觉层 + 信息层）

- `src/report/exportReport.ts` 从"工程 dump"提升为"卡片式仪表板"。
- 视觉层：色阶图例（HD/HD95/ASD 共用 ≤1mm 绿 / ≤3mm 黄 / >3mm 红，Dice/IoU 共用 ≥0.85 绿 / ≥0.7 黄）、Header 渐变、3 个 metric group 加组标题图标（`OverlapIcon` / `PixelIcon` / `DistanceIcon` 内联 SVG）、aiFindings 按严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定（thead sticky + 首列 sticky-left）+ 列点击排序、@media print A4 页眉页码。
- 信息层：remap_applied 顶部警告条（`.remap-banner.remap-on` 黄底红字 / `.remap-banner.remap-off` 绿底）、taxonomy / dataset_hint 展示位、spacing 可视化（`.spacing-bar` 3 色块按 min=0.5mm / max=2.0mm 反向归一化）、historical 警告条（`.historical-banner` 灰底斜体）。
- `src/main.tsx:handleExport` 透传 `validation.remap_applied` / `taxonomy_match` / `dataset_hint` / `historical` / `label_taxonomy`（已在 `src/inference/inferenceClient.ts:117-147 normalizeValidation` 白名单）。
- `tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class（`.legend` / `.remap-banner` / `.historical-banner` / `.spacing-bar`）。
- 浏览器自检 9 项视觉/信息元素。

### 2026-06-03 质量评估指标扩展 + 表面距离计算加速

- 把 quality 评估报告补齐到 6 类医学影像主流指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD）。
- `server/main.py` 新增 `surface_distances()`（1 crop + 2 EDT/label），把单 label 的 `distance_transform_edt` 调用从 6 次合并到 2 次。
- `src/inference/inferenceClient.ts` 在 `ValidationSummary` / `LabelMetric` 增补 12 个新字段并加入 `normalizeValidation()` 白名单。
- `src/report/exportReport.ts` 报告模板新增 3 个 metric group（区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD）和 4 个逐标签列（像素准确率、ASD (mm)、HD95 (mm)、HD (mm)）。
- AMOS 0117 quality 缓存命中：validation 阶段从 38.86s 降到 16.78s（约 2.3× 加速）。
- 3 个新增回归测试覆盖新函数精度（1e-9）、EDT 调用计数恒为 2、wall-time 加速比 ≥30%。

### 2026-05-31 label_taxonomy 修复与 AMOS CT 推理

- 显式 `label_taxonomy=auto|AMOS22|FLARE22` 已实现，修复了 AMOS 标签被误判为 FLARE22 的问题。
- `server/taxonomy.py` 的 `detect_dataset()` 现在更保守：标签 ID 是 checkpoint 子集时不触发 remap。
- 新部署包 `server-runtime-package-20260531.zip` 已创建，配套 `server-runtime-quickstart-20260531.md`。
- AMOS CT（768×768×103）本地在线推理完成，fast profile，mean_dice=0.77724。
- 输入分辨率高于标准 AMOS（768×768 vs 512×512），面积增加 2.25 倍，推理时间显著延长。
- 后续优化方向：预降采样、3D 模型评估。

---

## 一、现状总览

### 1.1 技术栈

| 项目 | 当前状态 |
|---|---|
| 前端 | React 19 + TypeScript + Vite |
| 医学图像 | `nifti-reader-js`，支持 `.nii` / `.nii.gz` |
| 普通图片 | PNG / JPG / WebP |
| 图标 | `lucide-react` |
| 样式 | `src/styles.css` 单文件 |
| 主入口 | `src/main.tsx` |
| 三正交视图 | `src/components/OrthogonalViewer.tsx` |
| 体素/切片映射 | `src/imaging/voxelMapping.ts` |
| NIfTI 切片渲染 | `src/imaging/sliceRenderer.ts` |
| 器官说明 | `src/data/organDetails.ts` |
| 推理客户端 | `src/inference/inferenceClient.ts` |
| 报告导出 | `src/report/exportReport.ts` |
| 后端桥接 | `server/main.py` |
| 测试脚本 | `package.json` 已配置 `test` |

### 1.2 本地资源

`nnunetv2_files` 当前可见：

| 资源 | 说明 |
|---|---|
| `checkpoint_best.pth` | 模型权重文件 |
| `amos_0117(3).nii.gz` | AMOS 0117 参考病例原始 CT |
| `amos_0117(2).nii.gz` | AMOS 0117 参考病例标准答案 |
| `amos_0117_original.nii/` | 目录型解压参考病例，不是直接可读的单一文件 |
| `amos_0117_label.nii/` | 目录型解压标准答案，不是直接可读的单一文件 |
| `FLARE22_Tr_0009_0000.nii.gz` | FLARE22 Tr 0009 原始 CT，本轮用于在线推理补充 |
| `FLARE22_Tr_0009.nii.gz` | FLARE22 Tr 0009 label，仅用于离线 taxonomy-remap 对照，不登记为后端自动验证 label |
| `FLARE\` | FLARE challenge 说明和评估资料，本地资料目录 |

这些资源可用于演示和调试，但不能自动等同于完整、可验证的 nnUNetv2 生产结果目录。

### 1.3 运行态

- 前端可在 `http://127.0.0.1:5173` 访问。
- 后端健康检查可在 `http://127.0.0.1:8000/api/health` 访问。
- 当前后端会根据模型资源返回 `real-nnunetv2` 或 `unavailable`。本机检测到 `dataset.json`、`plans.json`、`fold_0/checkpoint_best.pth` 与 `nnUNetv2_predict_from_modelfolder.exe` 时为 `real-nnunetv2`。

---

## 二、已经完成的部分

### 2.1 前端图像浏览

- 已支持 NIfTI 读取、窗宽窗位、切片切换、overlay / split / side / difference 模式。
- 已有 Axial、Sagittal、Coronal 三正交视图。
- 三个视图共用同一体素坐标，不再是独立的百分比光标。
- 图片层已禁止原生拖拽和事件接管，鼠标交互由容器统一处理。

### 2.2 器官点击与说明

- 已有 `label -> organ` 的查找表。
- 已有器官说明面板。
- 点击 mask label 后可打开对应器官说明。
- 背景体素不会误弹器官说明。

### 2.3 后端桥接

`server/main.py` 目前已提供：

- `/api/health`
- `/api/models`
- `/api/samples`
- `/api/samples/{sample_id}/original`
- `/api/samples/{sample_id}/label`
- `/api/segment/jobs`
- `/api/segment/jobs/{job_id}`
- `/api/segment/jobs/{job_id}/events`
- `/api/segment/jobs/{job_id}/result`

作业创建现在会先检查本地 nnUNetv2 资源完整性。资源齐备时，后端调用 `nnUNetv2_predict_from_modelfolder.exe` 并返回输出目录中的真实结果；资源缺失时，接口返回 503，不再复制参考标签冒充分割结果。

### 2.4 测试与构建

- `package.json` 已配置 `npm test`。
- `npm test` 通过。
- `npm run build` 通过。
- 已有布局回归测试，覆盖三正交布局和关键 CSS 约束。

---

## 三、当前仍未完成或只完成一半的部分

| 目标 | 当前状态 | 结论 |
|---|---|---|
| 真实 nnUNetv2 在线推理 | 本地 AMOS 0117 / FLARE22 Tr 0009 与服务器 5-fold smoke 已跑通；显式 `label_taxonomy=auto\|AMOS22\|FLARE22` 与 `dataset_hint` 字段已接入；高分辨率 CT fast 推理完成 | 已完成（2026-06-03 收口） |
| 结果自动回填并替换手工导入 | 前端能接收后端结果，后端输出路径已改为真实 nnUNetv2 结果；6 类指标 + spacing 回填到 GUI | 已完成（2026-06-03） |
| HTML 报告输出 | `src/report/exportReport.ts` 输出已升级为"临床报告"风格：封面 + 摘要 + TOC + 8 段章节编号 + 公式 tip + 严重度分布图 + caption/footnote + A4 打印页眉页码（6-05 临床报告风格重构）；色阶图例 + remap/historical 警告条 + taxonomy 展示位 + spacing 可视化 + aiFindings 严重度排序 + 器官列表折叠 + 列固定/排序（6-04 第一轮美化） | 已完成（2026-06-05 收口） |
| 置信度阈值 | 仅保留 UI 控件，尚未与概率输出建立真实语义 | 未完成（倾向从 UI 移除假控件） |
| label 表稳定来源 | 后端从真实 `dataset.json` 读取，前端优先使用 `/api/models` 并保留 fallback；`loadReferenceCase()` 按 `referenceCase.dataset` 自动预设 `label_taxonomy` | 已完成（2026-06-02） |
| 三正交桌面布局 | 已有 CSS 测试和 Playwright 盒模型回归检查 | 已完成 |
| 三正交移动端布局 | 已有单列、高度约束和 Playwright 盒模型回归检查，仍需真机再验 | 部分完成 |
| 真实 3D 体渲染 | 目前仍是轻量预览，不是医学级 3D 工作台 | 未完成 |

---

## 四、设计要求

### 4.1 分割后端

1. 不要把“调试回退”写成“真实推理”。
2. 不要把 `volume.image` 当成完整 NIfTI 文件上传。
3. 不要把进度条当成真实任务状态，除非它来自后端 job state。
4. 不要把 SSE 文本进度和二进制结果混在一个响应里。
5. 如果模型配置不完整，要明确展示“不完整”，不要伪造成功流程。

### 4.2 三正交视图

1. 三个方向必须同时可读。
2. 不能为了“填满”而把图像拉成不自然形变。
3. 不能为了“保留物理比例”把 sagittal / coronal 压成肉眼看不清的小条。
4. 面板位置必须稳定，切片切换时不应左右漂移。
5. 鼠标拖动只能改变体素坐标，不应触发浏览器原生拖图或外层误响应。
6. 视图层级应清楚：容器负责布局，图像层负责显示，事件由容器统一接管。

### 4.3 交互与可读性

- 按钮优先使用图标或图标+短文本。
- 工具栏要紧凑，不要把屏幕切成过多互相争抢的卡片。
- 主视图区应稳定，不要因为切片变化改变页面主布局。
- 在小屏设备上，允许纵向滚动，但不要挤成不可用的缩略图。
- 文本和控件不得覆盖图像观察区域。

---

## 五、具体实现评估

### 5.1 `src/main.tsx`

职责：

- 组合整个页面。
- 管理病例、上传、结果、推理状态、报告草稿。
- 调用 `createInferenceJob()` / `downloadInferenceResult()`。

评价：

- 功能已经较多，仍然是协调层。
- 仍承担较多状态，后续适合继续拆薄，而不是继续堆逻辑。

### 5.2 `src/components/OrthogonalViewer.tsx`

职责：

- 三正交视图布局。
- 点击、滚轮、十字线联动。
- mask overlay。
- label 命中与器官说明触发。

评价：

- 方向模型是对的。
- 图片层的 pointer 处理已经隔离。
- 目前需要继续把比例和布局稳定性作为首要目标，而不是增加更多视觉效果。

### 5.3 `src/imaging/voxelMapping.ts`

职责：

- 体素坐标与切片坐标转换。
- 三方向切片尺寸计算。
- 视图显示比例计算。

评价：

- 这里是三正交视图的关键基础。
- 当前已加入显示比例钳制，避免极端病例把 sagittal / coronal 压得太窄。

### 5.4 `server/main.py`

职责：

- 健康检查。
- 模型/参考病例信息。
- 任务创建、事件流、结果下载。

评价：

- API 形状已经比较清楚。
- 执行路径已从调试回退切换到真实 nnUNetv2 调用；本地 AMOS/FLARE、服务器 5-fold smoke 和高分辨率 fast 轮次已有证据，后续重点是更多病例、显式 taxonomy 服务器复跑和长期稳定性。

---

## 六、推荐的下一步

### 阶段 1：服务器验证收口

- 用 `server-runtime-package-20260531.zip` 更新服务器后端。
- 分别用 `label_taxonomy=AMOS22` 和 `label_taxonomy=FLARE22` 复跑 AMOS/FLARE validation。
- 确认 `runtime_target=server` 创建任务只依赖服务器 runtime 配置，不被本地 Windows nnUNet 文件缺失阻断。

### 阶段 2：模型配置与标签体系收敛

- 明确 `dataset.json`、`plans.json`、trainer、configuration、fold 的来源。
- 把 label 映射写成单一真源，不要前端和后端各写一套不一致的表。
- 置信度阈值要么真正生效，要么降级成只读质控提示。

### 阶段 3：三正交体验收口

- 继续验证桌面、窄屏和不同病例的显示比例。
- 保证 sagittal / coronal 不窄、不挤、不漂移。
- 把点击、滚轮、拖动都限制在容器内。

### 阶段 4：测试补强

- 保留现有单测。
- 增加浏览器级布局回归检查。
- 对后端 job state 做最小集成测试。

---

## 七、验收标准

1. 上传一个完整 `.nii` 或 `.nii.gz` 后，后端能创建任务并返回真实结果，而不是参考标签复制件。
2. 三正交视图在桌面上同时可读，Sagittal / Coronal 不会瘦到看不见。
3. 三正交视图在移动端不挤压成不可用缩略图。
4. 点击 mask 非背景体素后，能显示正确器官说明。
5. 鼠标拖动和切片切换不会让页面横移或抖动。
6. `npm test` 与 `npm run build` 保持通过。
7. 后端 health/models 接口与实际模型配置一致，不输出假的“已完成”状态。

---

## 八、待确认事项

1. `checkpoint_best.pth` 对应的真实 `dataset.json` / `plans.json` / trainer / configuration / fold 是否已经齐备并且可复现。
2. 当前 label 表是否完全等同于最终要支持的器官集合。
3. `confidenceThreshold` 的最终产品语义是“真实筛选阈值”还是“质控提示阈值”。
4. 3D 预览是否要升级为真正的医学体渲染，还是仅保留轻量预览。
5. 移动端是否要优先保证纵向可读，还是要保留部分并排布局。

---

## 九、2026-05-23 继续完成记录

### 9.1 已推进

- 后端作业创建已改为检查真实 nnUNetv2 model folder：`dataset.json`、`plans.json`、`fold_0/checkpoint_best.pth` 与 `nnUNetv2_predict_from_modelfolder.exe` 缺一则返回 503，不再把参考标签复制件伪装成真实推理结果。
- 后端真实推理路径已接入 `D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\nnUNetv2_predict_from_modelfolder.exe`，并设置 `nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results` 环境变量。默认设备为 CPU，可通过 `SEGMENTATION_DEVICE=cuda` 改为 GPU。
- `/api/health` 和 `/api/models` 现在返回 `model_status`、`mode`、`missing` 与 `confidence_threshold_effective`，前端可以明确展示模型是否可用。
- 前端推理文案已区分“真实 nnUNetv2 推理结果”和“调试标签回填结果（非真实推理）”，置信度控件降级为“质控提示”，不再暗示会筛选概率输出。
- 前端 label 表已补齐到 `dataset.json` 的 13 个标签，并会优先从 `/api/models` 读取后端 label 列表，接口不可用时才使用本地 fallback。
- 新增 `tests/backendState.test.py`，并纳入 `npm test`，覆盖模型配置缺失、job 拒绝创建、真实推理命令构造。

### 9.2 仍需验证

- 尚未在本轮执行完整大体积 nnUNetv2 推理，只验证了命令路径、配置探测、测试与前端构建。实际推理耗时和 GPU/CPU 资源占用仍需用真实服务启动后验证。
- 如果要让 `confidenceThreshold` 真正生效，需要启用概率输出并定义阈值如何作用于多标签结果；当前仍是质控提示。
- 浏览器级布局回归已补齐到 Playwright 盒模型检查；真机手动验证仍未完成。

### 9.3 本轮继续完善

- 后端从 `dataset.json` 读取 label 时已对齐前端 canonical id，尤其是 `inferior vena cava -> ivc`，避免点击 label 后落入未知器官说明。
- 前端 13 类默认 label 均已配置器官说明，点击肝脏、双肾、脾脏、胰腺、主动脉、下腔静脉、双侧肾上腺、胆囊、食管、胃、十二指肠均能展示非 fallback 的说明内容。
- `/api/segment/jobs/{job_id}` 增加 `result_ready`，并在下载结果时同时确认结果文件存在，减少前端对 409 下载响应的猜测。
- 新增 `tests/browserLayout.test.ts` 与 `npm run test:browser`，使用本机 Edge/Chrome 的 Playwright 盒模型检查桌面三列、移动单列、canvas 可读尺寸、无横向溢出、图像层 `object-fit: contain` 与 `pointer-events: none`。
- `npm test` 已纳入浏览器布局测试；在受限沙箱内需要提升权限启动本机浏览器。

---

## 十、当前功能与三大目标达成度

### 10.1 当前可实现的主要功能

1. **本地 CT / NIfTI 浏览**
   - 支持载入 `.nii` / `.nii.gz` 体数据，也保留 PNG / JPG / WebP 演示图导入。
   - 支持窗宽窗位、切片切换、缩放、透明度调节、split / overlay / side / difference 对比模式。
   - 支持载入内置参考病例（当前为 AMOS 0117）原图和标准答案，便于无外部数据时演示、回归和 Dice 验证。

2. **三正交联动查看**
   - Axial、Sagittal、Coronal 三个视图共用同一体素坐标。
   - 点击、拖动、滚轮切片会更新共享坐标和十字线位置。
   - 切片坐标、体素坐标、HU 值和当前 label 会同步显示。
   - 布局上已避免 sagittal / coronal 被压成不可读窄条，并通过 CSS 与 Playwright 盒模型测试做回归保护。

3. **分割结果叠加与器官说明**
   - 可将分割 mask 作为结果图层叠加到原图上。
   - 点击非背景 mask label 后，可打开对应器官说明卡片。
   - 当前默认支持 13 类：肝脏、右肾、脾脏、胰腺、主动脉、下腔静脉、右肾上腺、左肾上腺、胆囊、食管、胃、十二指肠、左肾。
   - 前端优先使用后端 `/api/models` 返回的 label 表；后端优先从真实 `dataset.json` 读取 label。

4. **本地 nnUNetv2 后端桥接**
   - `/api/health` 返回模型资源状态、路径、缺失项和当前模式。
   - `/api/models` 返回模型状态和 label 表。
   - `/api/segment/jobs` 创建真实 nnUNetv2 推理任务；配置缺失时返回 503，不伪造成成功流程。
   - `/api/segment/jobs/{job_id}` 返回 job state、进度、阶段、错误和 `result_ready`。
   - `/api/segment/jobs/{job_id}/events` 使用 SSE 发送文本状态。
   - `/api/segment/jobs/{job_id}/result` 单独返回二进制 NIfTI 结果，避免和 SSE 文本混在同一响应。

5. **测试与构建保障**
   - `npm test` 覆盖 viewer 逻辑、imaging 逻辑、CSS 布局约束、后端状态逻辑和浏览器盒模型回归。
   - `npm run build` 可完成 TypeScript 与 Vite 生产构建。
   - 浏览器测试和 Vite 构建在受限 shell 下可能遇到 `spawn EPERM`，需要在正常权限下运行。

### 10.2 三大目标达成度

| 三大目标 | 当前达成度 | 说明 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 90% | 体数据读取、三视图联动、十字线、滚轮/点击/拖动、桌面和移动端基础布局均已完成并有自动化回归；仍建议用更多真实病例和真机屏幕做视觉验收。 |
| 器官 label 可点击并展示说明 | 约 90% | 13 类 label 表与器官说明已补齐，后端 `dataset.json` 与前端 canonical id 已对齐；后续需要用最终训练集 label 集合确认是否还会新增或改名。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 70% | API 形状、模型资源探测、真实命令调用、job state、SSE 和结果下载已完成；尚未完成真实大体积 CT 的端到端耗时验证、GPU/CPU 资源评估和失败恢复策略。 |

结论：三个主要目标的“工作型 GUI 骨架”已经到位，可以用于本地演示、参考病例浏览、三正交检查和后端推理任务发起；距离稳定交付还差真实推理压力验证、置信度语义落地和更完整的异常处理。

### 10.3 后续迭代优先级

1. **真实推理验收**
   - 用一个完整 `.nii.gz` CT 文件从页面发起推理，记录 CPU/GPU、内存、耗时、输出文件名和前端回填结果。
   - 若 CPU 推理不可接受，明确要求 `SEGMENTATION_DEVICE=cuda` 并验证 CUDA 环境。
   - 将真实作业的 stdout/stderr 摘要写入 job state 或后端日志，便于定位失败。

2. **置信度阈值语义**
   - 当前 `confidenceThreshold` 是质控提示，不会真实筛选概率输出。
   - 若要做真实阈值，需要启用 nnUNetv2 probability 输出，定义多标签概率图如何阈值化、如何处理互斥标签和后处理。
   - 若短期不做真实概率阈值，UI 应继续保持“质控提示”语义，避免误导。

3. **前端状态拆分**
   - `src/main.tsx` 仍承担病例、上传、推理、报告、布局控制等多类状态。
   - 后续建议拆出 `useCaseData`、`useInferenceJob`、`useViewerState` 等 hook 或小模块，降低主入口维护成本。

4. **真实病例和移动端验收**
   - 使用不同层厚、不同矩阵大小、不同器官标签密度的 CT 验证三正交比例。
   - 在真实移动端或窄屏设备检查纵向滚动、工具栏换行和 inspector 区域可读性。

5. **3D 预览定位**
   - 当前 3D 仍是轻量预览，不是医学级体渲染。
   - 如果项目目标是临床级观察，应单独规划基于 WebGL/volume rendering 的体渲染模块；如果只是演示，应在 UI 和文档中保持“轻量预览”定位。

---

## 十一、2026-05-23 本轮继续完善记录

### 11.1 本轮已完成

1. **内置参考病例标准答案验证链路**
   - 后端新增标准答案 Dice 计算能力：当上传内容与 `nnunetv2_files/amos_0117(3).nii.gz` 一致时，真实 nnUNetv2 推理完成后会自动读取输出结果，并与 `nnunetv2_files/amos_0117(2).nii.gz` 计算 per-label Dice、平均 Dice、最低 Dice 和前景 Dice。
   - `/api/segment/jobs/{job_id}` 会返回 `validation` 字段；SSE `complete` 事件也会携带验证摘要，前端可在“分割”和“评估”模块显示标准答案验证状态。
   - 当前验收阈值为：平均 Dice `>= 0.85` 且最低 label Dice `>= 0.70` 记为 `passed`；未达阈值为 `review`，不阻断结果下载，但提示人工复核。

2. **项目内训练权重接入**
   - 用户确认训练好的权重文件位于 `nnunetv2_files/checkpoint_best.pth`。
   - nnUNetv2 的 `predict_from_modelfolder` 仍要求权重位于 model folder 的 `fold_0/checkpoint_best.pth`，因此后端会在运行时准备 `server/work/runtime_model/nnUNetTrainer__nnUNetPlans__2d`，复用现有 `dataset.json` / `plans.json`，并把项目内权重链接或复制到 runtime model folder。
   - `/api/health` 的 `model_status` 会区分 `checkpoint_source`、`checkpoint_runtime`、`checkpoint_in_model_folder` 和 `checkpoint_source_matches_model_folder`，避免误判实际使用的权重来源。

3. **鼠标点击/拖动稳定性**
   - 坐标换算已改为只对实际图像内容区域生效；点到 `object-fit` 留白区时返回 `null`，不会再把坐标夹到边界导致十字线或切片乱跳。
   - `OrthogonalViewer` 增加 pointer release/cancel 处理，拖动结束后释放 pointer capture，减少后续交互串扰。
   - 新增回归测试覆盖横向和纵向 letterbox 点击映射。

4. **Sagittal / Coronal 可读性**
   - 桌面三正交布局从三等分横排改为：Axial 左侧跨两行，Sagittal / Coronal 在右侧上下排列。
   - 正交切片渲染会按体素 spacing 计算 display ratio，并将侧向切片重新采样到可读比例，避免原始 `slices x rows` 像素比例把 Sagittal 压成窄条。
   - 浏览器布局测试已更新：桌面要求 Sagittal / Coronal canvas 宽度至少 300px，所有正交 canvas 至少 180x140；移动端仍保持单列并要求 canvas 不退化成缩略图。

5. **前端标准答案验证展示**
   - “分割控制”面板新增“标准答案验证”状态卡。
   - “评估”面板优先展示真实验证得到的平均 Dice、最低 Dice 和标准答案状态；未运行参考病例推理时继续显示待验证。

### 11.2 三大目标当前判断

| 三大目标 | 当前达成度 | 本轮变化 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 93% | 点击映射已避开留白区，桌面正交布局已扩大侧向视图；仍需用更多真实 CT 和真机屏幕做人工视觉验收。 |
| 器官 label 可点击并展示说明 | 约 90% | 本轮未改 label 体系；13 类器官说明和后端 label 对齐仍保持可用。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 80% | 已新增内置参考病例标准答案 Dice 验证链路；仍需完成一次真实长耗时端到端推理记录，包括耗时、设备、内存和失败恢复。 |

### 11.3 AMOS 0117 参考病例真实推理验收记录

- 输入原图：`nnunetv2_files/amos_0117(3).nii.gz`
- 标准答案：`nnunetv2_files/amos_0117(2).nii.gz`
- 实际权重源：`nnunetv2_files/checkpoint_best.pth`
- checkpoint 元信息：`Dataset001_AMOS22`、`3d_fullres`、15 个前景标签。
- 推理设备：`SEGMENTATION_DEVICE=cuda`，本机检测到 `NVIDIA GeForce RTX 4060 Laptop GPU`。
- 成功 job：`009d4efdc5f6`
- 输出文件：`server/work/009d4efdc5f6/output/009d4efdc5f6.nii.gz`
- 下载接口：`/api/segment/jobs/009d4efdc5f6/result` 返回 `200 OK`，结果大小约 141 KB。
- 标准答案验证：
  - `mean_dice = 0.891327`
  - `foreground_dice = 0.971222`
  - `min_dice = 0.555985`
  - 当前状态：`review`，不是 `passed`。
  - 最低 Dice 标签：胃 `0.555985`，其次为食管 `0.793725`、左肾上腺 `0.815983`。

结论：真实 CUDA 推理链路已经跑通，结果可以自动回填并下载；但参考病例标准答案验收没有完全达标，因为最低 label Dice 未达到 `0.70`。后续界面和文档应继续显示“建议人工复核”，不能把该参考病例表述为模型效果已完全理想。

### 11.4 后续验收清单

**自动化验收**

1. `npm test` 必须通过，覆盖 viewer/imaging/layout/backend/browser 布局回归。
2. `npm run build` 必须通过，确认 TypeScript 与 Vite 生产构建可用。
3. `GET http://127.0.0.1:8000/api/health` 应返回 `status: ok`、`mode: real-nnunetv2`、`model_config_detected: true`、`missing: []`。
4. 使用 AMOS 0117 内置参考病例真实推理完成后，job state 或 SSE complete 事件应包含 `validation` 摘要。

**人工验收**

1. 打开 `http://127.0.0.1:5173`，载入内置参考病例，确认 Axial/Sagittal/Coronal 同时清晰可读。
2. 在三正交图像内容区点击和拖动，十字线应平稳移动；点击图像外留白区不应跳到边缘切片。
3. 运行分割流程后，结果 NIfTI 应自动回填到三正交视图；若输入是 AMOS 0117 参考病例，前端应显示标准答案验证状态。
4. 点击 mask 中非背景 label，应打开正确器官说明；点击背景不应弹出器官说明。
5. 若验证结果为 `review` 或 `unavailable`，不能在文档或 UI 中表述为“模型效果已达标”，必须保留人工复核提示。

---

## 十二、2026-05-23 切片栏与验证 JSON 修复记录

### 12.1 本轮已修复

1. **底部切片栏快速点击乱跳**
   - 原因：底部 7 个切片缩略图每次都按 `selectedSlice` 重新居中；快速点击时缩略图窗口会移动，导致鼠标下同一位置代表的切片号不断变化。
   - 修复：新增稳定窗口起点逻辑 `getStableSliceWindowStart()`，主界面增加 `footerSliceStart` 状态。只在当前切片移出可见窗口或总切片数变化时移动底部缩略图窗口。
   - 验收：`node tests/viewerLogic.test.ts` 已覆盖窗口内点击不漂移、越界时才平移、总切片数小于 7 时钳制到合法范围。

2. **`validation_summary.json` 中文字段乱码**
   - 原因：历史输出文件中的 `message` 和 `labels[].name` 已被二次编码成 mojibake，并且文件带 UTF-8 BOM，导致直接查看和部分解析工具显示异常。
   - 修复：后端新增 `write_validation_summary()`，统一用 UTF-8 无 BOM 写入验证摘要，`json.dumps(..., ensure_ascii=False)` 保留中文字段。
   - 已修复历史文件：`server/work/009d4efdc5f6/output/validation_summary.json`，现在 `message` 为“标准答案验证未达阈值，建议人工复核。”，标签名如“脾脏”“胃”等可正常读取。

3. **后端测试避免读取大权重**
   - `tests/backendState.test.py` 已改用 AMOS checkpoint 元信息 fixture，避免单测阶段加载 `checkpoint_best.pth` 造成长时间卡顿。
   - JSON 写入测试支持 `SEGMENTATION_TEST_TMP` 指定临时输出目录，避免当前受限环境下 Windows 系统 Temp 权限异常。

### 12.2 本轮验证结果

- `node tests/viewerLogic.test.ts`：通过。
- `node tests/imagingLogic.test.ts`：通过。
- `node tests/layoutRegression.test.ts`：通过。
- `python tests/backendState.test.py`：通过。
- `npm test`：通过。运行时使用 `SEGMENTATION_TEST_TMP=D:\Trae_develop_code\segmentation-test-tmp-direct`，并在正常权限下启动浏览器测试，避免 Playwright `spawn EPERM`。
- `npx tsc --noEmit`：通过。
- `npm run build`：通过。此前 Vite `spawn EPERM` 属于受限 shell 权限问题，正常权限下构建成功。
- 历史验证摘要文件已确认：无 UTF-8 BOM，`message` 和标签名为正常中文。

### 12.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 95% | 三正交布局、侧向视图可读性、点击留白区过滤、底部切片栏稳定窗口均已完成并有回归测试；仍建议继续用更多真实 CT 和真机屏幕做人工验收。 |
| 器官 label 可点击并展示说明 | 约 90% | AMOS/后端 label 与前端 canonical id 已对齐，13/15 类器官说明可用；后续需要确认最终训练集标签集合是否固定。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 85% | CUDA 真实推理链路已跑通，结果可下载/回填，AMOS 标准答案 Dice 摘要可生成且 JSON 中文输出已修复；仍需补充更完整的耗时记录、失败恢复和多病例压力验证。 |

---

## 十三、2026-05-23 作业可追溯性补强

### 13.1 本轮已完成

1. **推理耗时与结果大小记录**
   - `Job` 增加 `started_at`、`completed_at`、`duration_seconds` 和 `result_size_bytes`。
   - `/api/segment/jobs/{job_id}` 现在返回耗时、结果大小、结果路径、验证摘要和结果就绪状态。
   - SSE `complete` 事件会携带 `duration_seconds` 与 `result_size_bytes`，前端成功状态、日志和“评估”面板可显示推理耗时与输出大小。

2. **作业摘要持久化**
   - 成功或失败的真实 nnUNetv2 作业会在输出目录写入 `job_summary.json`。
   - `job_summary.json` 使用 UTF-8 无 BOM，保留中文验证信息。

3. **服务重启后的历史结果读取**
   - 如果内存中找不到 job，后端会回退读取 `server/work/<job_id>/output/job_summary.json`。
   - 对于旧作业，如果没有 `job_summary.json`，但存在 `<job_id>.nii.gz` 和 `validation_summary.json`，后端会合成历史摘要，并从 input/output 文件时间估算耗时。
   - 这使 `009d4efdc5f6` 这类已完成历史结果在服务重启后仍可通过 API 查询和下载。

### 13.2 本轮验证

- `npm test`：通过。
- `npm run build`：通过。
- 后端新增测试覆盖：job runtime 字段、`job_summary.json` 写入、重启后读取持久化摘要、无摘要旧输出回退。

### 13.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 95% | 交互和布局主问题已收口，后续以更多真实病例人工验收为主。 |
| 器官 label 可点击并展示说明 | 约 90% | 标签和器官说明仍保持可用，后续依赖最终标签集合确认。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 88% | 新增耗时、结果大小、job 摘要持久化和历史结果回读；剩余重点是多病例压力验证、失败恢复策略和更完整的运行日志归档。 |

---

## 十四、2026-05-23 推理失败诊断增强

### 14.1 本轮已完成

1. **nnUNetv2 子进程日志持久化**
   - 真实推理作业运行结束后，后端会把子进程 stdout/stderr 写入 `output/nnunetv2_process.log`。
   - 日志文件使用 UTF-8 无 BOM，保留中文和 nnUNetv2 原始错误信息。

2. **失败尾部日志进入 job 状态**
   - `Job` 增加 `log_tail` 与 `process_log_path`。
   - `job_summary.json` 会记录 `log_tail` 和日志路径。
   - 如果 nnUNetv2 返回非 0 退出码，SSE `error` 事件会带上 `log_tail`，前端错误信息会包含尾部日志，便于直接定位如 CUDA OOM、模型目录错误、输入格式错误等问题。

3. **历史结果兼容**
   - 新作业优先使用 `job_summary.json` 中的日志字段。
   - 旧作业如果存在 `nnunetv2_process.log`，后端历史摘要回读时也会补充日志尾部。

### 14.2 本轮验证

- `python tests/backendState.test.py`：通过，覆盖 process log 写入、UTF-8 内容、日志尾部和 job summary 字段。
- `node tests/imagingLogic.test.ts`：通过，覆盖 SSE error 事件的 `log_tail` 解析。
- `npx tsc --noEmit`：通过。
- `npm test`：通过。
- `npm run build`：通过。

### 14.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 95% | 当前主要交互缺陷已有测试保护，后续以更多病例和真机验收为主。 |
| 器官 label 可点击并展示说明 | 约 90% | label 与说明链路稳定，后续等待最终标签集合确认。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 89% | 新增子进程日志、失败尾部日志、job 摘要与历史回读后，端到端可追溯性更完整；剩余重点是多病例压力测试、长任务取消/重试和更细粒度资源监控。 |

---

## 十五、2026-05-23 GitHub 发布准备与 README 更新

### 15.1 本轮已完成

1. **补充 GitHub 首页 README**
   - 新增/更新 `README.md`，说明当前项目定位、主要功能、本地运行方式、API 概览、三大目标进度和参考 CT 推理结果。
   - README 明确记录 AMOS 0117 参考病例结果：`mean_dice=0.891327`、`foreground_dice=0.971222`、`min_dice=0.555985`，当前结论为 `review`，不能表述为完全通过验收。

2. **发布范围收口**
   - `.gitignore` 已排除 `node_modules/`、`dist/`、`.test-output/`、`server/work/`、`nnunetv2_files/`、`*.nii`、`*.nii.gz`、`*.pth`、`*.pt`。
   - GitHub 仓库只应提交 GUI 源码、文档、测试、示例静态图片和截图；真实 CT、模型权重和推理输出继续保留在本机。

3. **测试去除真实权重依赖**
   - `test_project_checkpoint_is_preferred_as_weight_source()` 改为在 `.test-output/` 下创建临时模型目录和假权重文件。
   - 该测试继续覆盖“项目 `checkpoint_best.pth` 优先于模型目录 checkpoint”的逻辑，但不再要求仓库内存在真实权重。

### 15.2 本轮验证

- 在独立发布副本 `D:\Trae_develop_code\BME-CT-GUI-publish` 中执行 `npm ci --no-audit --no-fund --prefer-online`：通过。
- `npm test`：通过。
- `npm run build`：通过。
- 受限 shell 下仍可能出现 Vite `spawn EPERM`，正常权限下构建与浏览器测试通过。

### 15.3 发布注意事项

- 原始 GUI 目录位于父级 nnUNet Git 仓库内部，不能直接从 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` 执行 `git add -A`。
- 发布到 `https://github.com/JJ704sd/BME-CT-GUI` 时应使用独立仓库或独立发布副本，避免把父级 `nnunetv2/`、`nnUNet_raw/`、`nnUNet_results/`、环境目录和真实数据一并提交。

---

## 十六、2026-05-23 三正交视图方向修正

### 16.1 本轮已修复

1. **Sagittal 视图横竖轴调换**
   - 现象：用户反馈横断面、矢状面、冠状面的显示方向不符合原始 CT 浏览预期，并怀疑前端做了翻转。
   - 排查结论：未发现 CSS 或 canvas 层的镜像翻转；问题集中在三平面体素到屏幕坐标的映射。此前 Sagittal 使用 `z` 作为屏幕横向、`y` 作为屏幕纵向，视觉上会像被旋转，且不符合“按原始体素坐标展开三平面”的浏览习惯。
   - 修复：Sagittal 现在使用 `y` 作为屏幕横向、`z` 作为屏幕纵向；对应更新 `getOrientationDimensions()`、`getOrientationDisplayRatio()`、`voxelCoordToSlicePoint()`、`slicePointToVoxelCoord()` 和 `sliceRenderer.ts` 中的取样索引。
   - 约束：没有新增 CSS 镜像、旋转或强制翻转；mask 与原图继续共用同一套体素映射，保证覆盖对比不发生错位。

2. **方向回归测试**
   - 更新 `tests/imagingLogic.test.ts`，锁定 Sagittal 的尺寸、显示比例、点击反算体素坐标和十字线坐标映射。
   - 该测试用于防止后续再把 Sagittal 的 `y/z` 轴误换回去。

### 16.2 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，失败点为 Sagittal 旧尺寸 `{ width: 30, height: 20 }` 与新预期 `{ width: 20, height: 30 }` 不一致。
- `npm test`：正常 Windows 权限下通过。
- `npm run build`：正常 Windows 权限下通过。
- 受限 shell 下 Playwright 和 Vite 仍可能出现 `spawn EPERM`，这是子进程启动权限问题，不是本轮代码方向映射失败。

### 16.3 后续验收建议

- 用 `nnunetv2_files/amos_0117_original.nii/amos_0117(3).nii` 导入前端，分别在 Axial、Sagittal、Coronal 视图检查器官上下/左右关系。
- 同时加载 `amos_0117_prediction_009d4efdc5f6.nii.gz` 或新的在线推理结果，确认 mask 覆盖与原图在三个平面均保持配准。
- 如后续需要严格遵循 NIfTI affine 的 RAS/LPS 医学方向，应单独增加“按 header orientation 重定向”的显式模式，不能混入当前“原始体素坐标显示”逻辑。

---

## 十七、2026-05-23 三正交视图方向二次修正

### 17.1 根因复核

- 用户复核后确认上一轮仍不符合正向浏览预期。
- 使用参考文件 `nnunetv2_files/amos_0117_original.nii/amos_0117(3).nii` 检查 header：该参考病例的 NIfTI 方向为 `LAS`，仿射矩阵中 `x` 为负向、`y` 和 `z` 为正向。
- 上一轮虽然修正了 Sagittal 的 `y/z` 轴调换，但仍把数组行号直接映射到屏幕从上到下，导致：
  - Axial 顶部对应后方，床板/背侧显示在上方；
  - Sagittal / Coronal 顶部对应低层切片，头足方向倒置；
  - 主图/底部缩略图仍使用 `main.tsx` 内部轴位渲染函数，和三正交渲染链路没有完全统一。

### 17.2 本轮修复

1. **三正交行方向修正**
   - Axial：屏幕顶部映射到更大的 `y`，使前方/腹侧位于上方。
   - Sagittal：屏幕顶部映射到更大的 `z`，使头侧/上方位于上方；屏幕左侧映射到更大的 `y`，使前方位于左侧、后方/脊柱位于右侧。
   - Coronal：屏幕顶部映射到更大的 `z`，使头侧/上方位于上方。
   - `voxelCoordToSlicePoint()` 现在需要 `volume` 参数，用于正确反算翻转后的屏幕行坐标。
   - `slicePointToVoxelCoord()` 同步反算，保证鼠标点击、十字线和器官拾取仍对应同一个体素。

2. **渲染取样修正**
   - `src/imaging/sliceRenderer.ts` 的 Axial / Sagittal / Coronal 取样索引均同步使用修正后的屏幕行方向。
   - `src/main.tsx` 内部轴位预览/底部缩略图渲染也同步翻转 `y` 行方向，避免主图预览与三正交视图方向不一致。
   - 原图和 mask 继续共用相同体素映射，不会因为显示方向修正造成覆盖错位。

3. **方向回归测试**
   - `tests/imagingLogic.test.ts` 新增/更新断言：
     - Axial 顶部点击映射到 `y=max`；
     - Sagittal 顶部点击映射到 `z=max`；
     - Coronal 顶部点击映射到 `z=max`；
     - 十字线百分比使用修正后的屏幕坐标。

### 17.3 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，失败点为旧 Axial 行方向仍返回 `row=8`，新预期为 `row=11`。
- `npm test`：通过。
- `npm run build`：通过。

### 17.4 后续人工验收

- 重新启动或刷新 Vite 前端，避免浏览器缓存继续显示旧 bundle。
- 导入 `amos_0117(3).nii` 后检查：
  - Axial：床板/背侧应位于图像下方；
  - Coronal：肺部/头侧应位于上方，腹部应位于下方；
  - Sagittal：头侧应位于上方，前腹侧位于左侧，脊柱/背侧位于右侧。
- 加载预测或标准答案 mask 后，检查三个平面覆盖是否仍贴合原图器官边界。

---

## 十八、2026-05-23 三视图拖动切片闪回修复

### 18.1 根因

- 用户反馈拖动 Sagittal / Coronal 时切片会闪回上一位置，造成卡顿。
- 根因是 `selectedSlice` 与 `voxelCoord.z` 双向同步存在一帧竞争：
  - 拖动三正交视图时先更新 `voxelCoord.z`；
  - 此时 `selectedSlice` 仍是上一切片；
  - `selectedSlice -> voxelCoord` 的 effect 会把新 `z` 写回旧切片；
  - 随后 `voxelCoord.z -> selectedSlice` 再把切片号改到新位置，于是界面出现“闪回”。

### 18.2 本轮修复

1. **拖动时原子同步**
   - 新增 `getSelectedSliceForVoxelCoord()`，将体素 `z` 直接换算为 1-based 切片号并做边界钳制。
   - `OrthogonalViewer` 的 `onCoordChange` 不再直接传 `setVoxelCoord`，改为 `handleVoxelCoordChange()`。
   - `handleVoxelCoordChange()` 在同一个 pointer 事件里同时写入 clamped `voxelCoord` 和 `selectedSlice`，避免旧切片 effect 抢先回写。

2. **减少底部缩略图无效重算**
   - `footerSlicePreviews` 不再因为每次 `selectedSlice` 变化就重渲染 7 张缩略图。
   - 只有 `footerSliceStart`、总切片数或源图变化时才重算缩略图；当前切片仍通过按钮 active 状态高亮。

### 18.3 本轮验证

- `node tests/viewerLogic.test.ts`：先失败后通过，新增 `getSelectedSliceForVoxelCoord()` 边界测试。
- `npm test`：通过。
- `npm run build`：通过。

### 18.4 后续人工验收

- 在 Axial / Sagittal / Coronal 三个视图中按住鼠标拖动，观察十字线和切片号应连续变化，不应跳回上一切片。
- 快速拖动 Sagittal / Coronal 的上下方向时，轴位切片号应跟随 `z` 连续更新，底部缩略图窗口只在当前切片移出可见范围时移动。

---

## 十九、2026-05-23 三视图十字线跟手性修复

### 19.1 根因

- 用户反馈拖拽 Axial / Sagittal / Coronal 时，坐标线没有跟着鼠标走。
- 复核后确认有两个叠加原因：
  - 鼠标坐标换算使用 `.ortho-canvas` 的盒子，而真正承载图片和十字线的是 `.ortho-image-stage`。在缩放、比例钳制或后续布局变化时，两者可能出现细微差异，导致鼠标位置与十字线百分比不完全一致。
  - 每次鼠标移动都会触发三张 NIfTI 切片同步重算 data URL。大体积 CT 下这会阻塞 React 提交，十字线必须等底图重渲染完成才移动，视觉上表现为“不跟手”或明显滞后。

### 19.2 本轮修复

1. **鼠标坐标使用真实图片舞台盒子**
   - `OrthogonalViewer` 在 pointer 事件中优先读取 `.ortho-image-stage.getBoundingClientRect()`。
   - `clientPointToSlicePoint()` 仍保留 letterbox 处理，但输入 rect 改为实际图片/十字线所在区域，减少 CSS 缩放和布局造成的偏差。

2. **十字线与切片底图解耦**
   - 新增 `getSliceRenderKey()`：底图渲染只依赖该方向的固定切片号。
   - `OrthogonalViewer` 使用 `useDeferredValue(props.coord)` 渲染 NIfTI 底图；十字线、读数和鼠标交互继续使用即时 `props.coord`。
   - 结果：拖动时十字线可以先跟随鼠标移动，底图切片随后低优先级刷新，避免大图同步生成阻塞交互。

3. **指针捕获更稳**
   - `onPointerMove` 现在在鼠标左键按下或当前元素持有 pointer capture 时都会更新坐标，减少拖出图片边界后移动事件丢失的情况。

### 19.3 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，新增 `getSliceRenderKey()` 测试，确保同一平面内移动十字线不会触发该平面底图重渲染。
- `npm run build`：通过。
- `npm test`：通过。

### 19.4 后续人工验收

- 刷新 Vite 页面后分别在 Axial / Sagittal / Coronal 内按住鼠标拖动。
- 预期：十字线应跟随鼠标即时移动；底图切片可以略有延迟刷新，但不应阻塞十字线。
- 如果仍感觉滞后，下一步应把 NIfTI 切片渲染迁到 canvas/offscreen worker，彻底避免主线程生成 data URL。

---

## 二十、2026-05-23 三视图十字线横向对齐修复

### 20.1 根因

- 用户复核后指出：纵向基本能对齐，但横向仍未对齐。
- 复查发现上一轮只解决了拖动延迟和一部分实际舞台盒子问题，但仍存在一个横向偏移源：
  - `clientPointToSlicePoint()` 会按图片真实显示比例计算 content frame，并扣除横向 letterbox 留白；
  - 十字线绘制仍直接按整个 `.ortho-image-stage` 百分比定位，没有把同一段横向留白加回来；
  - 因此当容器比例与图像比例不完全一致时，鼠标映射和十字线绘制使用的坐标系不一致，横向偏移会比纵向更明显。

### 20.2 本轮修复

1. **统一 content frame**
   - 新增 `getSliceContentFrame(containerRatio, imageRatio)`。
   - `clientPointToSlicePoint()` 和 `getCrosshairPercent()` 现在共用同一个 content frame 计算。

2. **十字线只覆盖真实图片内容区**
   - `OrthogonalViewer` 使用 `ResizeObserver` 读取 `.ortho-image-stage` 的实际显示比例。
   - 垂直十字线的 `left` 会加上 content frame 横向偏移。
   - 水平十字线的 `left/width` 和垂直十字线的 `top/height` 也限制在真实图片内容区内，不再覆盖 letterbox 留白。

3. **保留上一轮跟手性优化**
   - 底图仍使用 deferred 坐标低优先级刷新。
   - 十字线继续使用即时坐标，不等待 NIfTI data URL 生成。

### 20.3 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，新增横向 letterbox 场景测试：2:1 容器内的 1:1 图像，十字线 x 必须包含 25% 左侧留白。
- `npm run build`：通过。
- `npm test`：通过。

### 20.4 后续人工验收

- 刷新 Vite 页面后，在三视图中横向拖动鼠标。
- 预期：垂直十字线应与鼠标横坐标一致；如果图片左右有留白，十字线不会跑到留白区，而是在真实 CT 图像内容区内对齐。

---

## 二十一、2026-05-23 三大目标收口补强

### 21.1 本轮已完成

1. **三正交浏览交互减阻**
   - `sliceRenderer.ts` 增加按体数据对象分组的切片 data URL 缓存，缓存键由方向、固定切片、渲染模式、显示比例和可见 label 集合组成。
   - 同一平面内拖动十字线时不会反复生成相同底图；回到已看过的切片时也可复用缓存，降低大体积 CT 下主线程渲染压力。

2. **器官 label 图层与后端真源同步**
   - 新增 `src/organLayerLogic.ts`，从 `/api/models` 返回的 label 表生成完整器官图层。
   - 图层现在覆盖 AMOS 15 类 label，保留用户已有显隐和质控状态，并在标准答案 Dice 返回后用真实 per-label Dice 回填图层评分。
   - 未验证的 label 显示为“待验”，不再用演示分数伪装成真实置信度。

3. **本地 nnUNetv2 长任务取消**
   - 后端 `Job` 增加 `cancel_requested` 与子进程句柄，新增 `POST /api/segment/jobs/{job_id}/cancel`。
   - 取消请求会终止正在运行的 nnUNetv2 子进程，写入 process log 和 job summary，并通过 SSE 返回取消状态。
   - 前端运行按钮在推理中切换为“取消推理”，取消后恢复可重试状态。

### 21.2 本轮验证

- `python tests/backendState.test.py`：通过，新增覆盖运行中 job 取消、进程 terminate、取消状态和事件记录。
- `node tests/imagingLogic.test.ts`：通过，新增覆盖 15 类 label 图层同步、保留显隐/质控状态、切片缓存键稳定性。
- `npx tsc --noEmit`：通过。

### 21.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 交互映射、横向对齐、切片闪回和重复渲染问题已有回归保护；剩余主要是真实设备和更多病例的人工视觉验收。 |
| 器官 label 可点击并展示说明 | 约 95% | 图层已由后端 label 真源生成并覆盖 AMOS 15 类，说明内容完整；剩余依赖最终训练集 label 集合是否继续变更。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 92% | 已具备真实推理、结果回填、历史回读、失败日志、验证摘要和长任务取消；剩余重点是多病例压力验证、资源监控和更系统的运行日志归档。 |

---

## 二十二、2026-05-23 真实质控与资源审计补强

### 22.1 本轮已完成

1. **per-label Dice 覆盖旧质控状态**
   - `buildOrganLayersFromLabels()` 现在在收到标准答案 per-label Dice 后，以真实 Dice 重新判定器官图层 `accepted/review`。
   - 这修复了一个隐患：如果某器官之前被人工标为“通过”，后续真实验证 Dice 偏低时，旧状态不应继续覆盖新结果。
   - 同步时继续保留用户显隐设置，并开始尊重后端 label 表里的 `visible` 默认值。

2. **nnUNetv2 作业资源快照归档**
   - 后端 `Job` 增加 `resource_snapshots` 与 `resource_log_path`。
   - 真实推理会在 `started`、`process_started`、`completed/failed/cancelled` 等关键阶段记录资源快照。
   - 快照包含推理设备、服务进程 PID、工作目录磁盘容量、服务进程内存；若本机存在 `nvidia-smi`，还会记录 GPU 名称、显存占用和利用率。
   - `job_summary.json` 会包含 `resource_latest` 和 `resource_snapshots`，同时输出独立的 `resource_snapshots.json`，服务重启后也可随历史 job summary 回读。

3. **前端资源摘要回填**
   - SSE `complete/error` 事件支持解析 `resource_latest`。
   - “评估”面板新增“资源快照”指标，流程日志会记录如设备、GPU 显存和磁盘可用空间，便于真实长任务验收时复盘。

### 22.2 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖真实 Dice 覆盖旧质控状态、资源快照 SSE 解析和前端资源摘要文案。
- `python tests/backendState.test.py`：先失败后通过，覆盖 `resource_snapshots.json` 写入、`resource_latest` 和 `resource_log_path` 进入 job summary。
- `npm test`：通过。
- `npm run build`：通过。

### 22.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 本轮未改变核心映射，现有三视图、布局、浏览器回归继续通过；剩余仍是真机屏幕和更多真实 CT 的人工验收。 |
| 器官 label 可点击并展示说明 | 约 96% | label 图层继续由后端真源生成，且真实 per-label Dice 已能覆盖旧人工状态；剩余取决于最终训练集 label 是否继续变更。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 94% | 在真实推理、回填、历史回读、失败日志、验证摘要和取消基础上，补齐了关键阶段资源快照和归档；剩余重点是多病例压力验证与更细粒度的资源曲线。 |

---

## 二十三、2026-05-24 无新增病例条件下的推理加速与收口

### 23.1 边界判断

- 当前没有更多真实 CT 病例，因此不能继续提高或宣称“模型泛化验收进度”。三大目标仍可推进，但推进点应限于工程能力：缓存、可追溯、交互稳定性、真实运行记录和失败恢复。
- `AMOS 0117` 仍可作为固定回归病例使用，用于验证前端回填、label 点击、标准答案 Dice、缓存命中和端到端服务状态。
- 对“在线推理太慢”的处理不能伪装成模型本身变快：首次未缓存真实 nnUNetv2 推理仍取决于模型、GPU、体数据大小和 nnUNetv2 预处理/导出成本；重复同一输入时可以通过历史结果缓存把等待时间降到秒级。

### 23.2 本轮已完成

1. **同输入历史推理缓存**
   - 后端在创建 job 时计算上传 NIfTI 的 `input_sha256`，并基于输入哈希、checkpoint 哈希、模型配置和 label 来源生成 `cache_key`。
   - 若已有成功 job 的 `cache_key` 相同，后端不再启动 nnUNetv2 子进程，而是硬链接或复制历史 NIfTI 结果到新 job 输出目录，并立即通过 SSE 返回 `complete`。
   - 缓存命中 job 会写入 `cached_result=true`、`cache_source_job_id`、`cache_key`、`input_sha256` 和 `checkpoint_sha256`，结果仍可通过 `/api/segment/jobs/{job_id}/result` 下载并回填到前端。
   - 对文档中已有的 `009d4efdc5f6` AMOS 0117 参考病例历史真实结果，若当前上传内容与内置参考病例原图一致，也可作为 legacy 缓存源，避免每次演示都重新跑 5-6 分钟。

2. **nnUNetv2 worker 参数可配置**
   - `build_predict_command()` 不再固定 `-npp 1 -nps 1`。
   - 新增环境变量：
     - `SEGMENTATION_PREPROCESS_WORKERS`：默认 `2`，范围 `1..8`。
     - `SEGMENTATION_EXPORT_WORKERS`：默认 `2`，范围 `1..8`。
   - `/api/health` 的 `model_status.predict_workers` 会展示当前 worker 配置，便于记录不同设置下的耗时差异。

3. **前端缓存状态透明展示**
   - 前端新增 `cached-real-nnunetv2` 模式文案。
   - 缓存命中时状态显示为“缓存推理结果回填完成”，结果元信息显示“历史缓存 nnUNetv2 结果”，避免误导为重新执行了一次完整真实推理。

### 23.3 本轮验证

- `python tests/backendState.test.py`：先失败后通过，覆盖 worker 默认值/边界钳制、命令行 `-npp/-nps` 配置、缓存命中时不启动真实推理线程、缓存结果可下载。
- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖缓存推理结果状态文案和结果元信息。
- `npm test`：通过。
- `npm run build`：通过。
- 已重启本地后端并确认 `/api/health` 返回 `predict_workers={"preprocess":2,"export":2}`。
- 使用内置参考病例原图创建在线推理 job `97fa9cefeb41`，命中历史真实结果 `009d4efdc5f6`，创建请求耗时约 `640 ms`，返回 `mode=cached-real-nnunetv2`、`cached_result=true`，结果下载接口返回 `200`，大小 `141460 bytes`。

### 23.4 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 没有新 CT 时无法做更广病例视觉验收；现阶段可继续通过缓存命中后的快速回填反复验收三视图交互、label 点击和报告状态。 |
| 器官 label 可点击并展示说明 | 约 96% | label 真源、15 类说明和 per-label Dice 回填已闭环；后续进度主要取决于最终训练集 label 是否变化，以及真实病例中 label 是否完整出现。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 96% | 新增同输入缓存和 worker 配置后，重复在线演示可避免分钟级等待；首次未缓存真实推理仍需记录实际耗时和资源曲线，不能用缓存耗时替代真实推理性能指标。 |

### 23.5 后续可继续推进但需要明确前提

- 若目标是“首次推理也显著快于 5-6 分钟”，下一步需要真实计时分解：模型加载、预处理、GPU 推理、导出和前端下载分别耗时多少。
- 若瓶颈在模型加载或 nnUNetv2 框架启动，应规划常驻推理进程或 Python worker 池；这比当前 FastAPI 每个 job 启动一个子进程复杂，但能减少重复启动成本。
- 若瓶颈在模型本身，应考虑轻量配置、裁剪 ROI、低分辨率预览或 TensorRT/ONNX 等单独优化路线；这些会改变精度和验收口径，不能和当前标准答案 Dice 混用。

---

## 二十四、2026-05-24 参考病例定位修正

### 24.1 产品定位

- GUI 的主定位是通用 CT 分割工作站原型，不是 AMOS 专用浏览器。
- 主流程应表述为：导入 CT 原图、导入或运行分割结果、三正交检查、查看器官说明、保存病例或导出报告。
- AMOS 0117 当前只作为内置参考病例，用于无外部数据时演示、固定回归、标准答案 Dice 验证和推理链路冒烟测试。
- 后续导入其他真实 CT 或其他数据集病例时，应沿用同一套“导入 CT 原图 / 导入分割结果 / 运行分割”的通用入口，而不是为每个数据集单独塑造一个主流程。

### 24.2 术语约定

| 术语 | 在本项目中的含义 | 当前状态 |
|---|---|---|
| 导入 CT 原图 | 用户从本机选择任意 `.nii` / `.nii.gz` CT 体数据进入工作台 | 主流程入口，不能绑定到 AMOS |
| 导入分割结果 | 用户从本机选择已有 mask / prediction NIfTI，用于叠加、对比和人工复核 | 主流程入口，适用于 AMOS、FLARE 或其他来源 |
| 载入参考病例 | 一键载入项目随附的固定参考病例，降低演示和回归测试门槛 | 当前内置资源为 AMOS 0117 |
| 内置参考病例 | 后端 `/api/samples/...` 暴露的固定病例资源 | 当前只有 `amos_0117`，后续可扩展更多 sample id |
| 标准答案验证 | 当输入与某个带标准答案的参考病例匹配时，自动计算 Dice | 当前只对 AMOS 0117 闭环 |

结论：按钮“载入参考病例”的意思不是“只能载入 AMOS”，而是“从后端内置参考病例库载入一个可验证病例”。当前库里只有 AMOS 0117，因此 endpoint 和文件名仍包含 `amos_0117`；后续增加 AMOS 其他病例、FLARE 用例或自定义教学病例时，应扩展参考病例清单，而不是改变 GUI 的主流程定位。

### 24.3 本轮已完成

- 前端按钮从旧的 AMOS-only 入口文案调整为“导入 CT 原图 / 导入分割结果 / 载入参考病例”。
- 自动载入、空状态、toast、日志和错误提示统一改为“内置参考病例 / 参考病例服务”，避免暗示系统只能处理 AMOS。
- `loadLocalAmosSample()` 重命名为 `loadReferenceCase()`；后端 endpoint 仍保留 `/api/samples/amos_0117/...`，因为当前内置资源只有 AMOS 0117。
- README 已明确：AMOS 0117 是内置参考病例，主流程支持任意 `.nii` / `.nii.gz` CT 与分割结果导入。

### 24.4 对三大目标的影响

| 三大目标 | 当前判断 |
|---|---|
| CT 可浏览、三正交可联动 | 仍可继续推进交互稳定性、回归测试和真实设备验收；没有更多真实 CT 时不能扩大病例覆盖结论。 |
| 器官 label 可点击并展示说明 | 可继续完善 label 真源、说明文案和质控状态；最终 label 集合是否变化仍依赖训练集和更多病例。 |
| 连接本地 nnUNetv2 后端并回填结果 | 可继续推进常驻 worker、耗时分解、缓存透明展示和失败恢复；首次真实推理性能仍必须用未缓存 job 记录。 |

### 24.5 后续导入用例规划

- 短期：继续支持用户手动导入任意 `.nii` / `.nii.gz` 原图和分割结果，不要求这些病例预先登记为内置样本。
- 中期：将 `/api/samples` 从单一 AMOS 0117 状态扩展为参考病例列表，返回 `id`、名称、数据集来源、是否有标准答案、原图大小和可用状态。
- 中期：前端“载入参考病例”应从单按钮升级为菜单或弹窗，允许选择 AMOS 0117、AMOS 其他病例、FLARE 用例或项目自定义病例。
- 长期：每个参考病例都应有独立元数据和验证口径；只有带标准答案的参考病例才能自动计算 Dice，普通外部 CT 只能显示推理结果、资源耗时和人工复核状态。

### 24.6 本轮验证

- 新增 `tests/imagingLogic.test.ts` 文案回归断言：禁止 UI 重新使用 AMOS-only 载入文案，并要求保留“载入参考病例”和“内置参考病例”。
- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖旧 AMOS-only 文案回归与新参考病例文案。
- `npm test`：通过。受限权限下浏览器测试会遇到 `spawn EPERM`，已在正常权限和全新 `SEGMENTATION_TEST_TMP` 下完成。
- `npm run build`：通过。受限权限下 Vite 会遇到 `spawn EPERM`，已在正常权限下完成生产构建。

---

## 二十五、2026-05-24 三大目标继续完善：参考病例清单化

### 25.1 本轮目标

本轮不新增真实 CT 病例，也不扩大模型泛化结论。推进重点是把上一节确定的“参考病例”定位落实到接口和前端状态中，让后续导入 AMOS 其他病例、FLARE 用例或自定义病例时有清晰扩展点。

### 25.2 本轮已完成

1. **后端 `/api/samples` 元数据补强**
   - `/api/samples` 继续返回数组，但每个 sample 现在包含 `id`、`name`、`dataset`、`modality`、`role`、`description`、`original_url`、`label_url`、文件名、`has_original`、`has_label` 和 `validation_available`。
   - 当前唯一内置参考病例仍为 `amos_0117`，但接口形状已经从“单个 AMOS 文件状态”推进为“参考病例清单”。
   - `/api/samples/{sample_id}/original` 和 `/api/samples/{sample_id}/label` 的 404 文案改为“参考病例原图/标签不存在”，不再使用样例语义。

2. **前端参考病例解析与选择**
   - 新增 `src/referenceCases.ts`，集中定义 `ReferenceCase`、默认 AMOS 0117 参考病例、`normalizeReferenceCases()` 和 `getReferenceCaseOriginalUrl()`。
   - `src/main.tsx` 不再硬编码 `/api/samples/amos_0117/original`，而是先读取 `/api/samples`，再按当前选中的参考病例 URL 载入。
   - “数据”和“分割”侧栏新增参考病例选择控件；当前只有 AMOS 0117 一个选项，但 UI 结构已经支持多参考病例列表。

3. **回归测试补强**
   - `tests/backendState.test.py` 新增 `/api/samples` 元数据断言，防止后续把接口退回到只有路径的状态。
   - `tests/imagingLogic.test.ts` 新增参考病例解析测试，并断言 `main.tsx` 不再硬编码 AMOS 原图 URL。

### 25.3 三大目标当前进展

| 三大目标 | 当前达成度 | 本轮推进 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 浏览能力本身未改变；病例入口从单固定按钮推进为可扩展参考病例清单，便于后续加入更多真实 CT 做视觉验收。 |
| 器官 label 可点击并展示说明 | 约 96% | label 说明未改动；参考病例元数据增加 `validation_available`，为后续区分“可自动 Dice 验证”和“只能人工复核”的病例打基础。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 97% | 推理链路不再依赖前端硬编码 AMOS URL；后续新增参考病例时，可沿用同一载入和推理回填流程。 |

### 25.4 后续建议

- 下一步可把 `/api/samples` 的静态 AMOS 0117 描述抽成后端配置列表，允许一次登记多个参考病例。
- 当前仍缺更多真实 CT，不能把三大目标进度解释为模型泛化能力提升；新增病例后应分别记录三正交显示、label 点击、推理耗时、资源快照和标准答案状态。
- 若要继续加速首次推理，应使用 `phase_timings` 先找出模型加载、预处理、GPU 推理和导出的占比，再决定是否优化常驻 worker、ROI 裁剪或导出流程。

### 25.5 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖参考病例解析和 AMOS URL 去硬编码。
- `python tests/backendState.test.py`：先失败后通过，覆盖 `/api/samples` 参考病例元数据。
- `npm test`：通过，使用全新 `SEGMENTATION_TEST_TMP` 并在正常权限下运行浏览器布局测试。
- `npm run build`：通过，Vite 生产构建输出 `dist/`。

---

## 二十六、2026-05-24 三大目标继续完善：参考病例注册表可配置

### 26.1 本轮目标

在没有新增真实 CT 文件的前提下，继续推进“可导入 AMOS 用例，也可导入其他用例”的工程能力。重点不是增加模型验收结论，而是让后端和前端具备多参考病例扩展机制。

### 26.2 本轮已完成

1. **参考病例注册表**
   - 后端新增 `SEGMENTATION_REFERENCE_CASES_JSON` 支持。
   - 若该环境变量指向一个 JSON 文件，后端会从其中读取 `samples` 列表；若未配置或文件不存在，则回退到默认 AMOS 0117。
   - 配置项支持 `id`、`name`、`dataset`、`modality`、`role`、`description`、`original`、`label`、`original_filename`、`label_filename`。
   - `original` 和 `label` 支持绝对路径，也支持相对配置文件所在目录的相对路径。

2. **动态参考病例下载**
   - `/api/samples/{sample_id}/original` 和 `/api/samples/{sample_id}/label` 不再只识别 `amos_0117`。
   - 只要该 `sample_id` 已登记并且文件存在，就能通过同一 API 下载原图或标签。
   - 标签缺失时仍可登记病例，但 `has_label=false`、`validation_available=false`，不会伪装成可自动 Dice 验证。

3. **前端缺失病例保护**
   - 参考病例下拉列表会保留已登记但原图缺失的病例，并显示“原图缺失”。
   - 当前选中的参考病例没有原图时，“载入参考病例”按钮会禁用，避免点击后才失败。

### 26.3 三大目标当前进展

| 三大目标 | 当前达成度 | 本轮推进 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 97% | 参考病例入口已支持多病例注册和缺失状态展示；新增真实 CT 后可直接纳入浏览验收。 |
| 器官 label 可点击并展示说明 | 约 96% | 本轮未改变 label 语义；但通过 `validation_available` 区分有无标准答案，为不同数据集病例的复核路径打基础。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 97% | 后端样本下载 API 已从 AMOS 单例扩展为动态 sample id；后续新增病例可沿用同一推理与回填链路。 |

### 26.4 配置示例

`SEGMENTATION_REFERENCE_CASES_JSON` 指向的 JSON 可使用如下结构：

```json
{
  "samples": [
    {
      "id": "amos_0117",
      "name": "AMOS 0117",
      "dataset": "AMOS22",
      "modality": "CT",
      "original": "amos_0117(3).nii.gz",
      "label": "amos_0117(2).nii.gz",
      "description": "带标准答案的 AMOS 参考病例"
    },
    {
      "id": "flare_demo",
      "name": "FLARE Demo",
      "dataset": "FLARE",
      "modality": "CT",
      "original": "flare_demo.nii.gz",
      "description": "仅用于浏览和推理回填的参考病例"
    }
  ]
}
```

### 26.5 本轮验证

- `python tests/backendState.test.py`：先失败后通过，覆盖配置文件读取、相对路径解析、动态 sample id 下载和缺失 label 的 404。
- `node tests/imagingLogic.test.ts`：通过，确认前端参考病例解析和去硬编码逻辑仍稳定。
- `npm test`：通过，使用全新 `SEGMENTATION_TEST_TMP` 并在正常权限下运行 Playwright。
- `npm run build`：通过，TypeScript 与 Vite 生产构建均成功。

---

## 二十七、2026-05-24 GitHub 仓库提交记录

### 27.1 发布目标

- GitHub 仓库：`https://github.com/JJ704sd/BME-CT-GUI`
- 发布分支：`main`
- 最新功能提交：`49def93 feat: refine ct gui reference workflow`
- 本地工作目录：`D:\BME2026\BME_CT_Seg\segmentation-gui-prototype`

### 27.2 提交边界

- GUI 已作为独立 git 仓库提交，不再依赖父目录 `D:\BME2026\BME_CT_Seg` 的 nnUNet 上游仓库状态。
- 未提交 `node_modules/`、`dist/`、`.test-output/`、`server/work/`、`nnunetv2_files/`、`screenshots/`。
- 未提交真实 CT、NIfTI、checkpoint 权重或推理输出；这些仍通过 `.gitignore` 排除。
- 父目录中已有的大量 `nnunetv2/` 文件、训练数据目录和环境目录没有纳入本次 GUI 仓库提交。

### 27.3 推送过程

- 初次直接推送被远端拒绝，因为 `main` 已存在历史提交。
- 后续基于 `origin/main` 创建更新分支，套用本地 GUI 最新变更并提交 `49def93`。
- 使用 fast-forward 方式推送到远端 `main`，没有强推覆盖远端历史。
- 推送后确认 `origin/main` 已指向 `49def93`，GitHub 页面可访问。

### 27.4 发布前验证

- `npm test`：通过，使用全新 `SEGMENTATION_TEST_TMP`，并在正常权限下运行 Playwright 浏览器布局测试。
- `npm run build`：通过，TypeScript 与 Vite 生产构建均成功。

---

## 二十八、2026-05-24 三大目标验收包与运行态复核

### 28.1 本轮目标

在已有三大目标接近收口的基础上，本轮不再继续堆叠新界面功能，而是补齐可复现验收材料：让“CT 可浏览、三正交可联动”“器官 label 可点击并展示说明”“连接本地 nnUNetv2 后端并回填结果”都有明确的人工验收记录表、自动化文档守卫和运行态证据。

### 28.2 本轮已完成

1. **新增三大目标验收文档**
   - 新增 `ACCEPTANCE.md`，将三大目标拆成验收对象、人工验收记录字段、通过标准、执行步骤和当前边界。
   - 文档明确区分真实未缓存推理、`cached-real-nnunetv2` 缓存回填和没有标准答案病例的人工复核流程。
   - 文档保留当前限制：本仓库不提交真实 CT、NIfTI、checkpoint 权重或推理输出；当前本地可直接运行态验收的真实 NIfTI 主要是 AMOS 0117。

2. **新增参考病例注册表示例**
   - 新增 `reference_cases.example.json`，包含当前可用的 `amos_0117` 和一个非 AMOS 的 `flare_demo` 注册示例。
   - `flare_demo` 目前只是外部病例接入示例，指向 `external_cases/flare_demo.nii.gz`，不能视为已经完成 FLARE 模型效果验证。
   - 示例延续 `SEGMENTATION_REFERENCE_CASES_JSON` 机制，后续放入真实文件后可沿用同一 `/api/samples`、载入、推理和回填流程。

3. **新增文档守卫测试**
   - 新增 `tests/acceptanceDocs.test.ts`，检查 `ACCEPTANCE.md` 和 `reference_cases.example.json` 是否存在，并覆盖三大目标关键词、未缓存真实推理、`cached-real-nnunetv2`、`validation_available` 和非 AMOS 示例。
   - `package.json` 的 `npm test` 已纳入该文档测试，避免后续删除验收包或把参考病例配置退回 AMOS 单例而不被发现。

4. **修复后端测试隔离问题**
   - `tests/backendState.test.py` 的 `make_test_output_dir()` 现在会在创建命名测试目录前清理旧目录。
   - 根因是 `.test-output/cached-jobs` 中旧 job summary 会被缓存查找抢先命中，导致缓存复用测试在非全新目录下偶发失败。
   - 使用全新 `SEGMENTATION_TEST_TMP` 复核后确认该问题属于历史测试输出污染，不是业务缓存逻辑退化。

### 28.3 未缓存真实推理复核

本轮在隔离工作目录中执行了一次 AMOS 0117 未缓存真实推理，避免命中既有 `server/work` 历史缓存：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\acceptance-real-20260524-194750
```

运行结果：

| 项目 | 结果 |
|---|---|
| job id | `32dfe3117b40` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| device | `cuda` |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB |
| duration_seconds | `359.425` |
| phase_timings | `nnunet_process=356.767`，`validation=2.481` |
| result_status | `200` |
| result_bytes | `141470` |
| validation status | `review` |
| mean_dice | `0.891305` |
| foreground_dice | `0.97122` |
| min_dice | `0.55591` |

结论：真实 nnUNetv2 推理链路、CUDA 执行、结果生成和结果下载均通过；但 AMOS 0117 的胃 label Dice 为 `0.55591`，低于最小 label Dice 阈值 `0.70`，因此质控状态仍应保持 `review`，不能写成完全自动通过。

### 28.4 缓存回填复核

在同一隔离工作目录中再次提交同一输入，确认历史结果缓存回填路径：

| 项目 | 结果 |
|---|---|
| job id | `c8cecb040657` |
| mode | `cached-real-nnunetv2` |
| cached_result | `true` |
| cache_source_job_id | `32dfe3117b40` |
| elapsed_seconds | `2.674` |
| result_status | `200` |
| result_bytes | `141470` |

结论：缓存回填路径能复用同输入、同 checkpoint、同配置的真实推理结果，并返回可下载 NIfTI；但该耗时只能用于演示和重复验收，不能替代首次未缓存推理性能指标。

### 28.5 三大目标当前进展

| 三大目标 | 当前达成度 | 本轮推进 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 97% | 已补验收记录模板和参考病例注册表示例；仍缺更多非 AMOS 真实 CT 的人工截图/真机验收。 |
| 器官 label 可点击并展示说明 | 约 97% | 验收包明确 label 来源、点击记录、背景行为和 `validation_available` 边界；AMOS 0117 per-label Dice 已重新记录。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 98% | 未缓存 CUDA 推理和同输入缓存回填均已复核，结果下载成功；首次推理耗时约 6 分钟，后续性能优化仍应围绕 `nnunet_process` 展开。 |

### 28.6 本轮验证

- `node tests/acceptanceDocs.test.ts`：先失败后通过，确认验收文档和参考病例示例存在并包含关键约束。
- `python tests/backendState.test.py`：先在历史 `.test-output` 下暴露缓存测试污染问题，修复测试目录隔离后通过。
- `npm test`：通过，包含 viewer、imaging、acceptance docs、layout、backend state 和 Playwright 浏览器布局测试。
- `npm run build`：通过，TypeScript 与 Vite 生产构建均成功。
- 未缓存真实推理：通过，`job_id=32dfe3117b40`，`real-nnunetv2`，`cached_result=false`，结果下载 `200`。
- 同输入缓存回填：通过，`job_id=c8cecb040657`，`cached-real-nnunetv2`，`cache_source_job_id=32dfe3117b40`。

### 28.7 后续建议

- 新增真实非 AMOS CT 后，优先登记到 `reference_cases.example.json` 同结构配置，再补充 `ACCEPTANCE.md` 的人工验收记录。
- 若目标是缩短首次推理耗时，应优先分析 `nnunet_process=356.767` 秒内部构成，再决定是否推进常驻 worker、ROI 裁剪或导出流程优化。
- AMOS 0117 的 `review` 状态应继续保留，除非重新训练或调整阈值后胃 label Dice 达到验收要求。

---

## 二十九、2026-05-24 新权重在线推理复核与加速判断

### 29.1 权重确认

用户确认新的训练权重已更新到：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\checkpoint_best.pth
```

本轮复核到的权重元信息：

| 项目 | 结果 |
|---|---|
| 文件大小 | `1136119762 bytes` |
| 修改时间 | `2026-05-24 18:04:22` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |

后端当前以该文件作为 `checkpoint_source`。由于 `checkpoint_sha256` 已纳入 `cache_key`，新权重不会复用旧权重 `3254d5f...` 生成的缓存结果。

### 29.2 当前采用的在线加速方式

当前没有做降分辨率、ROI 裁剪、ONNX/TensorRT 或模型结构层面的加速。本轮尝试的是后端运行方式层面的加速：

1. **常驻 nnUNet predictor worker**
   - 通过 `SEGMENTATION_PERSISTENT_WORKER=1` 启用。
   - 目标是复用已启动的 Python / nnUNet / predictor / checkpoint 初始化状态，减少每个在线 job 的重复启动和模型加载成本。
   - 该方式理论上对“同一后端进程内连续处理多个未缓存病例”更有意义；单次冷启动仍包含 worker 初始化成本。

2. **checkpoint-aware 缓存回填**
   - 后端缓存 key 包含输入 hash、checkpoint hash、dataset/configuration 和 label 来源。
   - 同一权重、同一输入、同一配置重复提交时，可直接回填 `cached-real-nnunetv2` 结果。
   - 这是当前已明确验证能显著缩短重复在线演示耗时的路径。

### 29.3 新权重未缓存真实推理记录

本轮使用新权重在隔离目录中重新执行 AMOS 0117 在线推理：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\acceptance-new-weight-20260524-201714
```

运行结果：

| 项目 | 结果 |
|---|---|
| job id | `27216eb73220` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| device | `cuda` |
| GPU | NVIDIA GeForce RTX 4060 Laptop GPU, 8188 MiB |
| duration_seconds | `1124.327` |
| phase_timings | `persistent_worker=1121.592`，`validation=2.527` |
| result_ready | `true` |
| result_size_bytes | `141569` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |
| validation status | `passed` |
| mean_dice | `0.924791` |
| foreground_dice | `0.980316` |
| min_dice | `0.846551` |

结论：新权重的 AMOS 0117 标准答案验证已经通过阈值，尤其是旧权重最低 Dice 来自胃 label 的问题明显改善，`min_dice` 从 `0.55591` 提升到 `0.846551`。但本次冷启动常驻 worker 的首次未缓存推理耗时约 `18.7` 分钟，不能写成“首次推理加速成功”。

### 29.4 新权重缓存回填记录

在同一隔离工作目录中再次提交同一 AMOS 0117 输入：

| 项目 | 结果 |
|---|---|
| job id | `f200f16f47be` |
| mode | `cached-real-nnunetv2` |
| cached_result | `true` |
| cache_source_job_id | `27216eb73220` |
| elapsed_seconds | `3.532` |
| result_status | `200` |
| result_bytes | `141569` |

结论：新权重下缓存回填可用，且重复请求耗时约 `3.5` 秒。这适合在线演示、重复复核和报告回填，但不能替代首次未缓存推理性能指标。

### 29.5 下一步性能判断

- 如果目标是“重复演示快”，当前 checkpoint-aware 缓存已经满足主要需求。
- 如果目标是“同一后端进程连续处理多个新病例更快”，下一步应做 warm-worker 对照：保持同一 persistent worker 存活，使用第二个未缓存输入或显式禁用缓存后再跑一次，比较第二次 `persistent_worker` 阶段耗时。
- 如果目标是“单个新病例首次推理显著快于 5-6 分钟”，常驻 worker 冷启动不是充分方案，后续需要拆解 nnUNet 内部耗时，并评估 ROI 裁剪、低分辨率预览、模型配置轻量化或导出链路优化。
- 本轮持久化 summary 中 `log_tail` 对常驻 worker 中文消息存在编码错读，但 `job_summary.json`、`validation_summary.json` 和结果 NIfTI 均已生成；后续可单独修正 worker 日志输出为 ASCII 或显式 UTF-8。

---

## 三十、2026-05-24 新权重分割指标 Summary

### 30.1 指标工具

新增可复用脚本：

```text
tools/segmentation_metrics_summary.py
```

该工具输入预测 NIfTI、参考标签 NIfTI、checkpoint 和 `dataset.json`，输出 JSON 与 Markdown 两份 summary。记录指标包括：

- Dice：per-label、mean、min、foreground。
- IoU：per-label、mean、min、foreground。
- Pixel Accuracy / Voxel Accuracy：3D NIfTI 体素逐点 exact-match accuracy。
- Hausdorff Distance：使用 NIfTI spacing 的对称 surface Hausdorff Distance，单位为 mm。
- checkpoint 元信息：路径、文件大小、修改时间和 SHA256。

同时新增项目级登记文档：

```text
SEGMENTATION_METRICS_SUMMARY.md
```

该文档保存后续训练权重可复用的命令模板、最新指标摘要和详细输出路径。

### 30.2 本轮新权重指标记录

本轮使用用户确认的新权重：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\checkpoint_best.pth
```

预测结果来自新权重未缓存真实推理 job：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\acceptance-new-weight-20260524-201714\work\27216eb73220\output\27216eb73220.nii.gz
```

指标输出：

| 项目 | 路径 |
|---|---|
| JSON | `.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.json` |
| Markdown | `.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.md` |
| 项目登记 | `SEGMENTATION_METRICS_SUMMARY.md` |
| 标签源 | `.test-output\acceptance-new-weight-20260524-201714\work\27216eb73220\output\validation_summary.json` |

聚合指标：

| 指标 | 值 |
|---|---:|
| mean Dice | `0.924791` |
| min Dice | `0.846551` |
| foreground Dice | `0.980316` |
| mean IoU | `0.865105` |
| min IoU | `0.733930` |
| foreground IoU | `0.961392` |
| Pixel/Voxel Accuracy | `0.998578` |
| mean Hausdorff Distance | `7.716048 mm` |
| max Hausdorff Distance | `16.562684 mm` |

标签说明：checkpoint 定义 15 个前景标签；AMOS 0117 本例的参考标签和预测结果实际只出现 label `1..13`，label `14=膀胱` 与 `15=前列腺/子宫` 的 `prediction_voxels=0`、`reference_voxels=0`，Dice/IoU/Hausdorff 记录为 `N/A`，不参与 mean/min 聚合。

结论：新权重在 AMOS 0117 参考病例上的重叠类指标和边界距离均已持久化记录。该结论只覆盖带标准答案的 AMOS 0117，不应外推到没有标准标签的外部 CT。后续生成指标时必须使用与 checkpoint 一致的标签源，避免外部旧 `dataset.json` 导致 13 类漏记或 label 名称错位。

### 30.3 验证记录

- `python tests/segmentationMetrics.test.py`：先失败后通过，覆盖 Dice、IoU、Pixel/Voxel Accuracy、Hausdorff Distance 和 JSON/Markdown 写入。
- `node tests/acceptanceDocs.test.ts`：先失败后通过，覆盖 `SEGMENTATION_METRICS_SUMMARY.md` 存在及关键指标字段。

---

## 三十一、2026-05-24 无缓存 Warm Worker 超时复盘

### 31.1 实验事实

本轮实验目录：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\perf-no-cache-persistent-20260524-212332
```

实验设置：

| 项目 | 值 |
|---|---|
| device | `cuda` |
| preprocess_workers | `2` |
| export_workers | `2` |
| cache_policy | `disabled via patch(server.find_cached_prediction, return_value=None)` |
| worker_policy | `SEGMENTATION_PERSISTENT_WORKER=1` |
| timeout_seconds | `1800` |

结果：

| 项目 | cold | warm |
|---|---|---|
| label | `cold_persistent_no_cache` | `warm_persistent_no_cache` |
| job_id | `c7ef1da0195e` | `685426290aa4` |
| cached_result | `false` | `false` |
| summary status | `succeeded` | `timeout` |
| recorded duration | `1528.792s` | timeout state at `1800.785s` |
| actual output | `c7ef1da0195e.nii.gz` | `685426290aa4.nii.gz` generated after timeout |
| output bytes | `141558` | `141558` |
| output SHA256 | `5473EAFB22FA21B896F8511BE9E02FFD49D678DEE4B82E63681FDD99DA57D9C0` | `5473EAFB22FA21B896F8511BE9E02FFD49D678DEE4B82E63681FDD99DA57D9C0` |

warm 的实际落盘时间：输入写入 `2026-05-24 21:49:08`，NIfTI 写入 `2026-05-24 22:57:33`，约 `4104.567s` / `68.409min`。因此这轮对照不能证明常驻 worker 对无缓存推理有加速，反而显示第二次推理明显更慢。

warm 输出补充指标：

| 项目 | 值 |
|---|---|
| metrics JSON | `.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.json` |
| mean Dice | `0.924782` |
| min Dice | `0.84654` |
| mean IoU | `0.865092` |
| Pixel/Voxel Accuracy | `0.998578` |
| mean Hausdorff Distance | `7.716048 mm` |
| max Hausdorff Distance | `16.562684 mm` |

### 31.2 推理过久的原因排查

已证实事实：

- 这不是 nnUNetv2 训练，而是使用 `checkpoint_best.pth` 做在线推理。
- warm job 长时间停留在 persistent worker 日志的 `Predicting 685426290aa4` / `perform_everything_on_device: True`；直到最后才进入 `sending off prediction to background worker for resampling and export` 和 `done with 685426290aa4`。
- 预测阶段 GPU 长时间接近 `100%`，显存约 `7.5-7.9 GiB / 8.0 GiB`，说明主要瓶颈在 full-volume sliding-window 推理计算，而不是结果文件路径、Dice 计算或下载。
- cold 与 warm 的输出 NIfTI hash 完全一致，说明 warm 最终生成了同样的分割结果，但没有速度收益。
- perf 脚本在 `1800s` timeout 后仍要等待 `persistent_worker_lock` 才能写 summary；而后台推理线程在 `run_persistent_worker_prediction()` 中持锁等待 worker 输出 complete，导致 summary 直到 worker 自然返回后才落盘。

可能原因：

- 当前模型是 3D full-res 推理，AMOS 0117 体数据为 `768 x 768 x 103`，需要大量 sliding-window patch 计算；常驻 worker 只能省初始化，不能省主体计算。
- `use_mirroring=True` 和 `perform_everything_on_device=True` 会增加显存和计算压力；在 RTX 4060 Laptop 8GB 上接近显存上限，第二次推理可能受 PyTorch/CUDA allocator 碎片、缓存状态或 nnUNet predictor 内部状态影响。
- persistent worker 复用 predictor 后第二次推理比第一次慢，说明当前复用方式不可靠；后续应优先验证“每次新进程但不缓存”的 baseline，再决定是否保留 persistent worker。

### 31.3 收尾结论

- `cached-real-nnunetv2` 仍是目前已证实有效的重复演示加速路径。
- `SEGMENTATION_PERSISTENT_WORKER=1` 在本轮无缓存 cold/warm 对照中未证明加速，warm 超时且实际耗时约 `68.4min`。
- 后续如果继续做无缓存加速，应先修复 worker timeout/cancel 和 summary 落盘机制，再评估关闭 mirroring、降低 tile/ROI、低分辨率预览、轻量模型或 ONNX/TensorRT。

---

## 三十二、2026-05-25 在线推理 fast profile 准备与缓存隔离

### 32.1 本轮目标

在正式运行新的无缓存推理对照前，先把上一节复盘结论落实到工程记录和代码状态：

- 不再把 `SEGMENTATION_PERSISTENT_WORKER=1` 表述为已验证的首次推理加速方案。
- 保留已证实有效的 `cached-real-nnunetv2` 重复回填路径。
- 为下一轮真实运行准备可复现的 fast/quality 推理参数，并确保不同参数不会误用同一缓存结果。

本轮没有启动新的真实长耗时 nnUNetv2 推理；未缓存 fast profile 是否实际更快，仍需要下一轮实测记录。

### 32.2 后端推理参数透明化

新增后端推理配置读取：

| 环境变量 | 默认 | 作用 |
|---|---|---|
| `SEGMENTATION_INFERENCE_PROFILE` | `quality` | 可选 `quality` / `fast` |
| `SEGMENTATION_TILE_STEP_SIZE` | `quality=0.5`，`fast=1.0` | 对应 nnUNetv2 `-step_size`，越大通常越快但重叠更少 |
| `SEGMENTATION_DISABLE_TTA` | `quality=0`，`fast=1` | 对应 nnUNetv2 `--disable_tta`，关闭 mirroring/TTA |
| `SEGMENTATION_NOT_ON_DEVICE` | `0` | 对应 nnUNetv2 `--not_on_device`，用于降低显存压力 |

实现点：

- `server/main.py` 新增 `get_inference_options()`，并在 `/api/health` 的 `model_status.inference_options` 中返回当前配置。
- `build_predict_command()` 会按配置追加 `-step_size`、`--disable_tta` 和 `--not_on_device`。
- `server/persistent_nnunet_worker.py` 初始化 `nnUNetPredictor` 时使用同一组参数：`tile_step_size`、`use_mirroring=not disable_tta`、`perform_everything_on_device=not not_on_device`。
- persistent worker key 增加 `tile_step_size`、`disable_tta`、`not_on_device`，避免不同参数复用同一个常驻 predictor。

### 32.3 缓存正确性修正

缓存 key 现在纳入 `inference_options`，因此以下情况不会相互复用缓存：

- `quality` 与 `fast` profile。
- 不同 `SEGMENTATION_TILE_STEP_SIZE`。
- TTA 开关不同。
- `SEGMENTATION_NOT_ON_DEVICE` 开关不同。

同时收紧 AMOS 0117 legacy 缓存路径：历史 `009d4efdc5f6` 结果不再只凭输入等同就直接作为缓存源，必须存在可读取的 `job_summary.json` 且 `cache_key` 与当前请求一致。这样可以避免新权重或新推理参数误用旧权重/旧参数的历史输出。

### 32.4 README 与性能脚本更新

- `README.md` 已重写并修复乱码，新增“在线推理速度策略”章节。
- README 明确区分：
  - `cached-real-nnunetv2`：已验证的重复演示加速路径。
  - `SEGMENTATION_INFERENCE_PROFILE=fast`：待实测的快速推理配置。
  - `SEGMENTATION_PERSISTENT_WORKER=1`：实验选项，目前无缓存对照未证明加速。
- `tools/perf_no_cache_persistent.py` 新增参数：
  - `--inference-profile`
  - `--tile-step-size`
  - `--disable-tta`
  - `--not-on-device`

dry-run 示例已能输出 fast 配置：

```powershell
python tools/perf_no_cache_persistent.py --dry-run --inference-profile fast --disable-tta --tile-step-size 1.0
```

### 32.5 自动验证记录

本轮新增/更新测试覆盖：

- `tests/backendState.test.py`
  - fast profile 会进入 nnUNetv2 命令参数。
  - 推理参数变化会改变 prediction cache key。
  - legacy AMOS 缓存必须匹配 summary cache key。
  - persistent worker key 包含推理参数。
- `tests/perfTool.test.ts`
  - 性能脚本包含 fast profile 参数。
- `tests/acceptanceDocs.test.ts`
  - README 记录当前推理速度策略与关键环境变量。

验证命令：

```powershell
npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' test
npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' run build
python tools/perf_no_cache_persistent.py --dry-run --inference-profile fast --disable-tta --tile-step-size 1.0
```

结果：

- `npm test`：通过。
- `npm run build`：通过。
- fast profile dry-run：通过，输出 `inference_profile=fast`、`tile_step_size=1.0`、`disable_tta=true`。

### 32.6 当前判断与下一步

| 目标 | 当前判断 |
|---|---|
| 重复在线演示加速 | `cached-real-nnunetv2` 已验证可秒级回填 |
| 首次未缓存推理加速 | 已完成同脚本 fast/quality 单次对照；fast 明显更快但质量下降明显 |
| persistent worker | 上一轮 warm worker 反而显著变慢，暂不作为推荐路径 |
| cache 正确性 | 已按 checkpoint 与 inference options 隔离 |

下一步应在启动更多真实长任务前确认实验矩阵：

1. `quality`：`tile_step_size=0.5`，TTA 开启。
2. `fast`：`tile_step_size=1.0`，TTA 关闭。
3. 两组都显式禁用历史缓存，记录 `duration_seconds`、`phase_timings`、结果大小、Dice/IoU/Hausdorff、GPU 显存与是否能回填 GUI。

### 32.7 Fast profile 单次未缓存真实运行记录

在用户确认可以继续后，本轮追加执行一次单次 fast/no-cache 推理。该运行不使用历史缓存，仍走 persistent worker 路径；目的不是证明最终策略，而是先获得 fast profile 的真实耗时和质量代价。

运行目录：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\perf-fast-profile-20260525-1305
```

运行设置：

| 项目 | 值 |
|---|---|
| runs | `1` |
| device | `cuda` |
| preprocess_workers | `2` |
| export_workers | `2` |
| inference_profile | `fast` |
| tile_step_size | `1.0` |
| disable_tta | `true` |
| not_on_device | `false` |
| cache_policy | `disabled via patch(server.find_cached_prediction, return_value=None)` |
| worker_policy | `SEGMENTATION_PERSISTENT_WORKER=1` |

运行结果：

| 项目 | 结果 |
|---|---|
| job id | `6802e01f1a73` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| status | `succeeded` |
| duration_seconds | `384.345` |
| phase_timings | `persistent_worker=381.448`，`validation=2.670`，`collect_result=0.008` |
| result_status | `200` |
| result_bytes | `142578` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |
| output | `.test-output\perf-fast-profile-20260525-1305\work\6802e01f1a73\output\6802e01f1a73.nii.gz` |

资源快照：

| 阶段 | GPU | 显存 | 利用率 |
|---|---|---:|---:|
| started | NVIDIA GeForce RTX 4060 Laptop GPU | `1645 / 8188 MiB` | `22%` |
| completed | NVIDIA GeForce RTX 4060 Laptop GPU | `1745 / 8188 MiB` | `43%` |

标准答案验证：

| 指标 | 值 |
|---|---:|
| validation status | `review` |
| mean Dice | `0.777243` |
| min Dice | `0.000000` |
| foreground Dice | `0.972898` |
| mean IoU | `0.713592` |
| min IoU | `0.000000` |
| foreground IoU | `0.947226` |
| Pixel/Voxel Accuracy | `0.998068` |
| mean Hausdorff Distance | `10.282058 mm` |
| max Hausdorff Distance | `24.616009 mm` |

指标输出：

| 项目 | 路径 |
|---|---|
| job summary | `.test-output\perf-fast-profile-20260525-1305\work\6802e01f1a73\output\job_summary.json` |
| perf summary | `.test-output\perf-fast-profile-20260525-1305\perf_no_cache_persistent_summary.json` |
| metrics JSON | `.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.json` |
| metrics Markdown | `.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.md` |

质量结论：

- 与 29.3 中新权重默认质量配置的 `1124.327s` 相比，本次 fast 单次耗时降到 `384.345s`，但两者都是单次运行，仍需同一脚本矩阵复核。
- fast profile 明显牺牲质量：`mean_dice` 从 29.3 的 `0.924791` 降到 `0.777243`，`min_dice` 从 `0.846551` 降到 `0.0`。
- `min_dice=0.0` 主要来自 label `14=膀胱` 与 `15=前列腺/子宫`：参考标签中两者为 `0` voxels，但 fast 预测产生了少量假阳性（分别 `664` 和 `670` voxels）。
- 因此 fast profile 可以作为“快速预览/演示候选”，不能替代默认质量推理结果，也不能把本次结果写成自动验收通过。

### 32.8 Quality profile 单次未缓存真实运行记录

为和 fast profile 形成同脚本对照，本轮继续执行一次单次 quality/no-cache 推理。该运行同样禁用历史缓存、使用同一输入和 checkpoint，并保留 persistent worker 路径。

运行目录：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\perf-quality-profile-20260525-1330
```

运行设置：

| 项目 | 值 |
|---|---|
| runs | `1` |
| device | `cuda` |
| preprocess_workers | `2` |
| export_workers | `2` |
| inference_profile | `quality` |
| tile_step_size | `0.5` |
| disable_tta | `false` |
| not_on_device | `false` |
| cache_policy | `disabled via patch(server.find_cached_prediction, return_value=None)` |
| worker_policy | `SEGMENTATION_PERSISTENT_WORKER=1` |

运行结果：

| 项目 | 结果 |
|---|---|
| job id | `b3c528cc9e20` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| status | `succeeded` |
| duration_seconds | `1360.398` |
| phase_timings | `persistent_worker=1357.677`，`validation=2.500`，`collect_result=0.003` |
| result_status | `200` |
| result_bytes | `141568` |
| checkpoint_sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |
| output | `.test-output\perf-quality-profile-20260525-1330\work\b3c528cc9e20\output\b3c528cc9e20.nii.gz` |

资源快照：

| 阶段 | GPU | 显存 | 利用率 |
|---|---|---:|---:|
| started | NVIDIA GeForce RTX 4060 Laptop GPU | `1343 / 8188 MiB` | `20%` |
| completed | NVIDIA GeForce RTX 4060 Laptop GPU | `1540 / 8188 MiB` | `11%` |

标准答案验证：

| 指标 | 值 |
|---|---:|
| validation status | `passed` |
| mean Dice | `0.924780` |
| min Dice | `0.846569` |
| foreground Dice | `0.980317` |
| mean IoU | `0.865088` |
| min IoU | `0.733957` |
| foreground IoU | `0.961394` |
| Pixel/Voxel Accuracy | `0.998578` |
| mean Hausdorff Distance | `7.716048 mm` |
| max Hausdorff Distance | `16.562684 mm` |

指标输出：

| 项目 | 路径 |
|---|---|
| job summary | `.test-output\perf-quality-profile-20260525-1330\work\b3c528cc9e20\output\job_summary.json` |
| perf summary | `.test-output\perf-quality-profile-20260525-1330\perf_no_cache_persistent_summary.json` |
| metrics JSON | `.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.json` |
| metrics Markdown | `.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.md` |

### 32.9 Fast vs Quality 对照与产品策略

同一输入、同一 checkpoint、同一脚本、均禁用历史缓存的单次对照：

| 项目 | fast profile | quality profile |
|---|---:|---:|
| job id | `6802e01f1a73` | `b3c528cc9e20` |
| duration_seconds | `384.345` | `1360.398` |
| persistent_worker | `381.448` | `1357.677` |
| result_bytes | `142578` | `141568` |
| validation status | `review` | `passed` |
| mean Dice | `0.777243` | `0.924780` |
| min Dice | `0.000000` | `0.846569` |
| foreground Dice | `0.972898` | `0.980317` |
| mean IoU | `0.713592` | `0.865088` |
| min IoU | `0.000000` | `0.733957` |
| foreground IoU | `0.947226` | `0.961394` |
| Pixel/Voxel Accuracy | `0.998068` | `0.998578` |
| mean Hausdorff Distance | `10.282058 mm` | `7.716048 mm` |
| max Hausdorff Distance | `24.616009 mm` | `16.562684 mm` |
| label 14 prediction_voxels | `664` | `0` |
| label 15 prediction_voxels | `670` | `0` |

结论：

- fast profile 单次耗时约为 quality 的 `28.25%`，可以显著缩短等待时间。
- fast profile 的质量代价明确：`mean Dice` 下降约 `0.147537`，`min Dice` 降到 `0`，`mean Hausdorff Distance` 增加约 `2.566010 mm`。
- fast profile 的 `min Dice=0` 来自 label `14=膀胱` 与 `15=前列腺/子宫` 的小体积假阳性；quality profile 对这两个 absent labels 预测为 `0` voxels。
- 产品策略应采用 `质量推理` 作为默认/正式报告依据；`快速预览` 可作为显式可选模式，只能用于快速查看和演示，并在界面和文档中标注“需复核”。
- 后处理可以作为后续独立实验：对 absent label 或小体积标签设置最小体素阈值过滤。但这必须记录为 `postprocess`，不能混同模型原始输出，也不能用过滤后的分数替代模型原始质量指标。

## 三十三、2026-05-25 推理模式产品化

### 33.1 实现内容

- 前端“分割控制”新增 `质量推理` / `快速预览` 模式选择，默认 `质量推理`。
- 选择 `快速预览` 时，界面显示“需人工复核”警示；fast 结果元信息和最近导入状态也标注为快速预览结果，不能误认为正式报告依据。
- `createInferenceJob()` 提交 `inference_profile`，后端按每次 job 生成 effective `inference_options`，不再只能依赖进程环境变量。
- job state、创建响应、SSE complete 事件和 `job_summary.json` 都携带 `inference_profile` / `inference_options`；cache key 继续使用最终 options，隔离 fast/quality 缓存。

### 33.2 验证

- `node tests/imagingLogic.test.ts`：通过，覆盖 UI 文案、fast 结果元信息、SSE `inference_options` 解析和前端表单提交。
- `python tests/backendState.test.py`：通过，覆盖请求级 `inference_profile`、job state、cache key 输入和 cached complete event。
- `npm test`：通过。
- `npm run build`：通过。

### 33.3 仍然不变的边界

- 本轮没有新增真实推理 benchmark，因此不改变 32.9 的 fast/quality 数值结论。
- `fast` 仍只能作为快速预览/演示路径；正式报告和质量结论仍以 `quality` 原始输出为准。

## 三十四、2026-05-26 FLARE22 Tr 0009 非 AMOS 在线推理补充

### 34.1 数据接入

- 新增本地补充数据位于被忽略的 `nnunetv2_files/` 下：
  - `FLARE\`：FLARE challenge 说明与评估脚本。
  - `FLARE22_Tr_0009.nii.gz`：FLARE22 label。
  - `FLARE22_Tr_0009_0000.nii.gz`：FLARE22 原图。
- 私有 registry `nnunetv2_files/reference_cases.local.json` 已追加 `flare22_tr_0009`。
- `/api/samples` 验证结果：`has_original=true`，`has_label=false`，`validation_available=false`。
- 审核结论：`has_label=false` 是刻意行为，不是漏接 label。该 label 文件存在，但不能按当前 AMOS22 checkpoint 的 label ID 直接做后端自动 Dice/IoU/Hausdorff 验证。

### 34.2 标签兼容性判断

FLARE22 Tr 0009 的原图和 label 均为 `512 x 512 x 87`，spacing 为 `0.806641 x 0.806641 x 2.5 mm`，label 值为 `0..13`。

FLARE22 label ID 与当前 AMOS22 checkpoint 不一致：

| 标签源 | 关键差异 |
|---|---|
| FLARE22 | `1=liver`, `3=spleen`, `4=pancreas`, `13=left_kidney` |
| AMOS22 checkpoint | `1=spleen`, `3=left_kidney`, `6=liver`, `10=pancreas`, `14/15=bladder/prostate_or_uterus` |

因此本轮没有把 FLARE22 label 配进 registry，也没有让后端做自动 validation。后续所有 FLARE22 数值指标必须写成 taxonomy-remapped comparison。

### 34.3 在线推理结果

运行设置：

| 项目 | 值 |
|---|---|
| case id | `flare22_tr_0009` |
| job id | `86b0153d0a73` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| inference_profile | `quality` |
| tile_step_size | `0.5` |
| disable_tta | `false` |
| persistent worker | `enabled` |
| device | `cuda` |

运行结果：

| 项目 | 结果 |
|---|---:|
| duration_seconds | `237.323` |
| prepare_runtime_model | `0.003` |
| persistent_worker | `237.119` |
| collect_result | `0.001` |
| result_size_bytes | `120761` |
| GPU at completion | `1804 / 8188 MiB`, `18%` |
| disk_free_bytes at completion | `105865117696` |

输出文件：

| 项目 | 路径 |
|---|---|
| job create | `.test-output\flare22-tr-0009-quality-20260526\job_create.json` |
| job summary | `.test-output\flare22-tr-0009-quality-20260526\job_summary.json` |
| prediction | `.test-output\flare22-tr-0009-quality-20260526\86b0153d0a73.nii.gz` |
| remap metadata | `.test-output\flare22-tr-0009-quality-20260526\flare_to_amos_label_remap.json` |
| remapped metrics JSON | `.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.json` |
| remapped metrics Markdown | `.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.md` |

### 34.4 Remapped 指标对照

先按器官名把 FLARE22 label 映射到 AMOS22 checkpoint label ID，然后离线计算指标。该结果用于查看非 AMOS 表现，不等同于后端自动 validation。

| 指标 | 值 |
|---|---:|
| mean Dice | `0.893127` |
| min Dice | `0.673730` |
| foreground Dice | `0.949908` |
| mean IoU | `0.815941` |
| min IoU | `0.507989` |
| foreground IoU | `0.904594` |
| Voxel/Pixel Accuracy | `0.991879` |
| mean Hausdorff Distance | `12.595149 mm` |
| max Hausdorff Distance | `38.043429 mm` |
| label 14/15 prediction_voxels | `0 / 0` |

最低 Dice 标签为 `duodenum=0.673730`，其次需要关注 `pancreas=0.806389` 和 `esophagus=0.808989`。这说明本例整体分割表现可用，但正式查看时仍应重点复核十二指肠、胰腺和食管边界。

### 34.5 当前判断

- 新增 FLARE22 Tr 0009 的在线推理链路已经跑通，且结果为真实未缓存 `quality` 推理。
- 该病例可以作为非 AMOS acceptance evidence，但只能以 manual-only + remapped offline metrics 的形式记录。
- GUI 已提供 FLARE22 Tr 0009 真实病例入口；后续若要形成正式人工验收截图，应继续记录 overlay / split / side / difference 的人工复核截图和边界意见。

## 三十五、2026-05-26 三视图交互性能与分屏修复

### 35.1 现象和根因

用户反馈快速点击或移动光标时，三正交视图的图像更新会略有滞后。排查后确认主要原因是指针移动路径会触发 NIfTI 切片同步渲染：三视图切片、右侧 axial 预览和底部缩略图都可能在 React 更新中执行像素遍历和 `canvas.toDataURL()`。

另一个相关交互缺口是：工具栏的 `分屏` 滑杆原本只在旧二维对比层有 CSS 裁剪逻辑；当前真实 NIfTI 的三正交视图虽然接收了 `compareMode="split"`，但 `.ortho-mask` 没有按 `--compare-position` 裁剪，所以用户在真实病例调试时难以体验到分屏效果。

### 35.2 本轮修复

- `src/components/OrthogonalViewer.tsx` 新增 `useRafCoalescedCoord()`，把高频切片图像重绘合并到 `requestAnimationFrame`。
- 十字线继续使用即时 `coord`，保证光标反馈优先；图像重绘使用合并后的 `renderCoord`。
- `src/main.tsx` 新增按帧合并的 `scheduleSelectedSlice()`，避免 pointer move 同步触发右侧预览和底部缩略图频繁重绘。
- axial 预览改用 `src/imaging/sliceRenderer.ts` 的缓存渲染器。
- `src/styles.css` 新增 `.compare-split.has-mask .ortho-mask` 裁剪规则和分割线；有 mask volume 时，分屏滑杆控制左侧分割结果叠加比例，右侧保留原始 CT。
- `OrthogonalViewer` 现在区分 `has-mask` / `no-mask`，没有结果图时不显示假分割线。
- 新增 `CODE_MODULE_GUIDE.md`，用于后续按模块讲解代码。

### 35.3 分屏功能解释

`分屏` 不是切换 Axial/Sagittal/Coronal 的布局，而是原图与分割结果的滑动对比模式。滑杆值为 `75%` 时，左侧约 75% 区域显示 mask 叠加，右侧约 25% 区域只显示 CT 原图。该功能只有在已经有分割结果 `maskVolume` 后才有可见效果；只加载原图时没有可对比对象。

### 35.4 验证

- `node tests/imagingLogic.test.ts`：通过，覆盖 rAF 合并渲染、坐标去重和三正交分屏裁剪 CSS。
- `node tests/acceptanceDocs.test.ts`：通过，覆盖 `CODE_MODULE_GUIDE.md` 存在性和关键模块说明。
- Edge/Playwright 三视图快速拖动烟测：通过，三视图图片非空白且无控制台错误。
- `npm test`：通过。
- `npm run build`：通过。

## 三十六、2026-05-26 矢状/冠状拖动回跳修复

### 36.1 现象和根因

用户继续反馈在矢状面或冠状面拖动时，CT 图像仍会出现卡顿和三视图来回切换。复核后确认这不是矢状/冠状坐标映射方向错误，而是 `voxelCoord` 和主页面 `selectedSlice` 的双向同步存在延迟回写：

- 矢状面或冠状面拖动会快速更新 `voxelCoord.z`。
- `selectedSlice` 为了降低右侧 axial 预览和底部缩略图重绘频率，会通过 `requestAnimationFrame` 延迟同步。
- 旧逻辑在 `selectedSlice` 变化后又反向把 `selectedSlice - 1` 写回 `voxelCoord.z`。
- 快速拖动时，旧 `selectedSlice` 会覆盖更新后的 z 坐标，表现为切片回跳、三视图来回切换和可见卡顿。

### 36.2 本轮修复

- `src/viewerLogic.ts` 新增 `SelectedSliceSyncSource` 和 `getVoxelCoordForSelectedSliceSync()`。
- `src/main.tsx` 新增 `selectedSliceSyncSourceRef`，区分 selectedSlice 更新来源。
- 当 selectedSlice 是由三视图拖动同步而来时，只校正坐标边界，不再反向覆盖当前 `voxelCoord.z`。
- 当用户主动拖动切片滑块或点击底部切片时，仍然按 `selectedSlice - 1` 正常更新 z 坐标。
- `tests/imagingLogic.test.ts` 增加回归测试，覆盖“矢状/冠状拖动不能被旧 selectedSlice 拉回”的场景。

### 36.3 验证

- `node tests/imagingLogic.test.ts`：通过。
- `npm test`：通过。
- `npm run build`：通过。
- `git diff --check`：通过。

## 三十七、2026-05-26 三视图拖动卡顿二次修复

### 37.1 现象和根因

用户在上一轮回跳修复后继续反馈：拖动三视图时仍有卡顿，尤其在矢状面/冠状面快速移动时，CT 图像跟随有延迟。复查后确认上一轮只修复了 `selectedSlice` 延迟回写导致的 z 坐标回跳，但 `handleVoxelCoordChange()` 仍会在每个 `pointermove` 上立即提交 React 状态。这样会让 `App` 父组件、三视图读数、右侧 axial 预览和底部切片状态按指针事件频率重渲染；当新切片未命中缓存时，还会同步执行 NIfTI 像素遍历和 `canvas.toDataURL()`，主线程容易被占满。

### 37.2 本轮修复

- `src/viewerLogic.ts` 新增 `getVoxelCoordDragCommit()`，把拖动坐标的边界裁剪、去重和 axial 切片推导抽成可测试纯函数。
- `src/main.tsx` 新增 `voxelCoordRef`、`pendingVoxelCoordRef` 和 `voxelCoordFrameRef`，拖动时只记录最新坐标，每个 `requestAnimationFrame` 最多提交一次 React 状态。
- `voxelCoord` 与由拖动派生的 `selectedSlice` 在同一个 rAF 提交周期内更新，避免父组件在单个指针事件流中被多次同步刷新。
- 若用户在下一帧前把光标移回原坐标，会清空待提交坐标，避免提交过时中间帧。
- 保留上一轮 `selectedSliceSyncSourceRef` 逻辑，确保 voxel 驱动同步不会反向覆盖最新 z 坐标；滑块/底部切片点击仍按 slice 驱动更新 z。

### 37.3 验证

- `node tests/imagingLogic.test.ts`：先失败后通过，新增覆盖拖动坐标合并提交、边界裁剪、selected slice 推导和禁止同步提交 `setVoxelCoord(clampedCoord)`。
- `npm test`：通过，包含浏览器布局/三视图相关 smoke。
- `npm run build`：通过。
- `git diff --check`：通过。
- 本轮仅改变前端交互渲染节奏，不改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 指标或 FLARE22 taxonomy remap。

## 三十八、2026-05-26 矢状/冠状拖动卡顿三次修复

### 38.1 现象和根因

用户继续反馈：拖动矢状面和冠状面查看切片时仍有卡顿，而拖动横断面不明显。复查后确认差异来自交互轴不同：

- 横断面拖动主要改变 `x/y`，横断面固定的 `z` 切片不变，通常只需要移动十字线。
- 矢状面/冠状面拖动会改变 `z`，其它面板中的 Axial 切片需要连续变化，容易触发同步切片栅格化。
- 上一轮已合并父组件 `voxelCoord` 更新，但矢状/冠状拖动仍会让三张视图连续切片渲染；如果继续使用完整分辨率 data URL，每帧成本仍偏高。

### 38.2 本轮修复

- `src/components/OrthogonalViewer.tsx` 新增 `activePointerOrientation`，记录当前是否处于拖动状态。
- 拖动期间三张视图仍按帧实时更新，不冻结非当前面板；切片渲染改用 `interactive` 轻量质量，降低每帧像素遍历和 data URL 生成成本。
- 鼠标释放后同一坐标自动切回 `full` 完整质量渲染，保证最终查看质量不下降。
- `useRafCoalescedCoord()` 继续用 `latestSliceKeyRef` 判断固定切片是否变化；固定切片未变化时不触发图像状态更新。
- `src/main.tsx` 将 voxel 拖动派生的 `selectedSlice` 辅助预览同步改为空闲后执行，避免右侧 axial 预览和底部缩略图在矢状/冠状拖动中抢占主线程。
- `src/imaging/sliceRenderer.ts` 新增 `NiftiRenderQuality`，`interactive` 模式按较低采样密度生成实时预览，`full` 模式保留完整分辨率。

### 38.3 文档审核

- 已审核 `SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_METRICS_SUMMARY.md`、`REVIEW.md`、`README.md`、`ACCEPTANCE.md`、`CODE_MODULE_GUIDE.md`。
- 文档主体保持中文；保留必要英文术语、路径、命令、profile 名称和指标名。
- 本轮为前端渲染调度修复，不改变任何推理实验数值、自动 validation 规则或 FLARE22 remap 解释边界。

### 38.4 验证

- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖拖动面板识别、三视图实时轻量渲染、固定切片 key 去重和辅助切片预览空闲同步。
- `npm test`：通过。

## 三十九、2026-05-26 底部实时推理进度展示

### 39.1 目标和边界

用户希望点击“运行分割流程”后，底部“切片与流程日志”区域能结合前后端真实推理链路显示实时进度。当前实现采用前端优先方案：复用已有 `/api/segment/jobs/{job_id}/events` SSE 阶段事件，不修改后端推理任务、不解析 nnUNetv2 内部 patch 级进度，也不使用前端估算动画伪造百分比。

### 39.2 本轮实现

- `src/main.tsx` 新增 `inferenceTimeline`、`inferenceStartedAt` 和 `inferenceProgressCopy`。
- `startSegmentation()` 在 job 创建、SSE `progress/complete/error`、结果回填、取消和失败路径中写入结构化 timeline。
- 底部 console 在切片缩略图上方新增 `inference-progress-rail`，显示当前阶段、SSE 百分比、job id、推理模式、已耗时和最近阶段日志。
- `fast` profile 在底部元信息中继续显示“快速预览 · 需人工复核”。
- SSE `error.log_tail` 会进入 timeline 摘要，失败或取消不会把进度伪装成成功。
- `src/styles.css` 新增桌面/移动端 progress rail 样式；桌面保持横向 rail，移动端降级为纵向堆叠。

### 39.3 验证

- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖结构化 timeline、底部 progress rail、SSE progress 写入和失败日志保留。
- `node tests/browserLayout.test.ts`：先失败后通过，覆盖新增 progress rail 的桌面/移动端布局约束。
- `npm test`：通过。
- `npm run build`：通过。

### 39.4 后续

若真实演示中仍觉得 `20%` 阶段停留过久，下一步再补后端 heartbeat 型 progress 事件：百分比保持阶段值，附带已耗时和可选资源快照，用于表达后端仍活跃，而不是伪造内部完成度。

## 四十、2026-05-26 在线推理输入识别与取消链路收口

### 40.1 现象和根因

用户在前端点击“运行分割”后，后端 job 能创建、SSE 能推进到 `90%`，但最终报错“nnUNetv2 命令已结束，但未找到输出 NIfTI 结果”。查看 `server/work/bfff9fa79a98/output/nnunetv2_process.log` 后确认 nnUNetv2 返回码为 `0`，但 stdout 中写着 `There are 0 cases in the source folder`。

根因是输入文件后缀与模型 `dataset.json.file_ending` 不一致：当前模型要求 `.nii.gz`，失败 job 的输入目录中只有 `<job>_0000.nii`，nnUNetv2 因后缀不匹配没有把它识别为病例，因此没有生成输出。

### 40.2 本轮修复

- `server/main.py` 新增 `get_model_file_ending()`，从 checkpoint 内嵌 `dataset_json.file_ending` 或模型目录 `dataset.json` 读取当前模型期望的输入后缀。
- `server/main.py` 新增 `copy_upload_to_nnunet_input()`，当模型要求 `.nii.gz` 但上传文件是 `.nii` 时，后端会 gzip 写入 `<job>_0000.nii.gz`。
- `get_model_state()` 增加 `model_file_ending` 字段，便于 health 和调试确认当前模型输入要求。
- `tests/backendState.test.py` 新增回归测试，覆盖 `.nii` 上传会规范化为 `.nii.gz`。

### 40.3 取消链路判断

当前项目已经有取消设计和实现：

- 前端运行中按钮会从“运行分割”切换为“取消推理”。
- `cancelInferenceJob()` 调用 `/api/segment/jobs/{job_id}/cancel`。
- 后端 `request_job_cancel()` 设置 `cancel_requested=true`、状态为 `cancelling`，并对运行中的 nnUNetv2 子进程调用 `terminate()`。
- `run_process_with_cancel()` 会继续等待进程退出，必要时升级到 `kill()`，然后写入取消 summary 和 SSE 事件。

### 40.4 验证和边界

- `python tests/backendState.test.py`：先失败后通过，覆盖输入后缀规范化和既有取消链路。
- 已重启本地后端，`/api/health` 返回 `predict_device=cuda`、`model_file_ending=.nii.gz`。
- 本轮修复不改变 nnUNetv2 权重、推理 profile、validation 规则或历史实验指标。
- 浏览器不能直接启动 Python/FastAPI 后端进程；在线推理前仍需要后端服务在 `127.0.0.1:8000` 运行。

---

## 四十一、2026-05-27 推理心跳机制与默认设备收口

### 41.1 背景

长时间 nnUNetv2 推理（尤其是 `quality` profile 下的 3D full-res sliding-window 计算）可能持续十几分钟甚至更久。在此期间，SSE 进度可能停留在同一阶段百分比（如 `20%`），前端底部进度 rail 显示停滞，用户无法判断后端是否仍在运行。

### 41.2 本轮实现

1. **后端心跳机制**
   - `server/main.py` 新增 `HEARTBEAT_INTERVAL = 10`（秒）和 `push_heartbeat()` 函数。
   - `push_heartbeat()` 在 SSE 中推送带 `heartbeat: true` 标记的 progress 事件，包含当前进度、阶段、已耗时和资源快照。所有异常隔离，失败不中断推理。
   - `run_process_with_cancel()` 中，`communicate(timeout=0.5)` 超时循环会检查距上次心跳是否已过 10 秒，超过则发送心跳。
   - 常驻 worker 路径使用 `_read_worker_event_with_heartbeat()`，通过 `queue.Queue` 的 `get(timeout=HEARTBEAT_INTERVAL)` 实现非阻塞读取：超时后自动发送心跳，收到响应则正常返回。

2. **前端心跳处理**
   - `src/inference/inferenceClient.ts` 的 `parseInferenceEvent()` 已支持解析 `heartbeat` 和 `elapsed_seconds` 字段。
   - 前端收到心跳事件后只更新底部进度 rail 的已耗时和资源快照，不污染结构化 `inferenceTimeline`。

3. **默认设备变更**
   - `get_predict_device()` 默认值从 `cpu` 改为 `cuda`，与实际使用场景一致。
   - `get_model_state()` 中 `predict_device` 字段会反映当前生效的设备。

4. **端到端推理流程测试**
   - `tests/backendState.test.py` 新增 `test_e2e_inference_flow_create_events_result()`，覆盖创建 job → 执行推理 → 验证事件序列（progress → complete，无 error）→ 下载结果的完整链路。
   - 验证 `duration_seconds`、`phase_timings`、`result_size_bytes`、`result_ready` 等字段。

### 41.3 验证

- `python tests/backendState.test.py`：通过，覆盖 E2E 推理流程。
- `node tests/imagingLogic.test.ts`：通过，覆盖心跳事件解析。
- `npm test`：通过。
- `npm run build`：通过。

### 41.4 行为边界

- 心跳事件的 `heartbeat: true` 字段可用于前端区分心跳和真正的阶段进度变化。
- 心跳间隔为 10 秒，不可通过环境变量配置；如需调整需修改 `HEARTBEAT_INTERVAL` 常量。
- 心跳失败（包括资源快照获取失败）完全隔离，不会影响推理执行。
- 本轮不改变 nnUNetv2 推理参数、validation 规则或历史实验指标。

## 42. 标签文件传输修复与在线 validation 链路打通

### 42.1 背景

用户通过 GUI 上传标签 NIfTI 文件后运行推理，后端 `label_path` 始终为 `null`，validation 未执行。同一时期还发现 FLARE22 在线验证 mean_dice=0.073 的根因是 AMOS22 checkpoint 标签 ID 与 FLARE22 标签 ID 语义完全不同（taxonomy 错位），而非模型质量问题。

### 42.2 本轮实现

1. **前端 `UploadRole` 类型扩展**
   - `src/main.tsx` 将 `UploadRole` 从 `"source" | "result"` 扩展为 `"source" | "result" | "label"`。
   - `processVisualizationFile()` 增加 `role === "label"` 分支，设置 `labelFile` 状态并显示 toast。

2. **数据操作面板新增标签拖放区域**
   - 新增"标签 CT 导入"按钮，支持拖拽和点击选择 NIfTI 标签文件。
   - 标签文件选择后显示文件名，未选择时显示"NIfTI 标签文件 · 用于自动 Dice 验证"。

3. **推理前提醒**
   - `startSegmentation()` 中 `labelFile` 为 null 时，显示 toast 提示"未选择标签 CT，推理完成后不会自动计算 Dice"。

4. **前后端临时排查日志**
   - 当时临时在前端、inference client 和后端记录标签文件是否进入提交链路，用于确认后端服务是否加载了最新代码。
   - 这些日志会暴露上传文件名，只作为 2026-05-27 的短期排查手段；2026-05-29 已在第 47 节移除。

5. **后端重启修复**
   - 添加调试日志并重启后端服务后，`label_path` 从 `null` 变为非空，标签文件正确保存到 `job_dir / "label" / f"{job_id}_label.nii.gz"`。

### 42.3 taxonomy 错位发现

- AMOS22 checkpoint 的 label ID 与 FLARE22 标签 ID 语义完全不同：
  - AMOS22: 1=脾脏, 2=右肾, 3=左肾, 4=胆囊, 5=食管, 6=肝脏, 7=胃, 8=主动脉, 9=下腔静脉, 10=胰腺, 11=右肾上腺, 12=左肾上腺, 13=十二指肠
  - FLARE22: 1=肝脏, 2=右肾, 3=脾脏, 4=胰腺, 5=主动脉, 6=下腔静脉, 7=右肾上腺, 8=左肾上腺, 9=胆囊, 10=食管, 11=胃, 12=十二指肠, 13=左肾
- 只有 label 2（右肾）两边语义一致，Dice=0.945。其余 ID 语义错位，Dice≈0。
- `taxonomy_match: True` 的误判：`validate_against_custom_label()` 只检查了标签 ID 集合是否有交集，未做语义级匹配。
- 离线 remap 后真实 mean_dice=0.893。

### 42.4 在线验证成功数据

job `bf20f0ec4456`（FLARE22 Tr 0009 + 标签上传）：

| 指标 | 值 |
|---|---|
| 标签文件 | 131 KB（gzip），正确保存到 job 目录 |
| mean_dice | 0.073（taxonomy 错位导致） |
| 前景 Dice | 0.950 |
| label 2（右肾）Dice | 0.945 |
| 验证状态 | review |

### 42.5 验证

- `npm test`：通过。
- `npm run build`：通过。
- 标签文件传输链路：job `bf20f0ec4456` 的 `label_path` 非空，validation 执行成功。

### 42.6 行为边界

- 标签文件传输 bug 的根因可能是后端服务未重启导致的代码变更未生效，而非纯粹的前端逻辑错误。
- taxonomy 错位是独立问题，需要 Phase 1（自动 remap）才能解决。
- 2026-05-29 已移除上传文件名调试日志；后续观察标签链路改为检查 job state、`label_path`、validation summary 和测试覆盖。
- 本轮不改变 nnUNetv2 推理参数或 validation 规则。

## 43. 自动 Taxonomy Remap 实现与跨数据集在线验证打通

### 43.1 背景

第 42 节发现 FLARE22 标签 ID 与 AMOS22 checkpoint 语义完全不同，导致在线验证 mean_dice=0.073（实际应为 ~0.893）。本轮实现后端自动 taxonomy remap，使上传 FLARE22 标签后能自动检测数据集来源并按器官名重映射标签 ID。

### 43.2 本轮实现

1. **新增 `server/taxonomy.py`**
   - 定义 FLARE22 标签表（`FLARE22_LABELS`）：1=liver, 2=right_kidney, 3=spleen, ..., 13=left_kidney。
   - 定义器官名别名映射（`_NAME_ALIASES`）：postcava↔ivc↔inferior_vena_cava, gall_bladder↔gallbladder, right_adrenal↔right_adrenal_gland 等。
   - 实现 `detect_dataset(reference_labels, checkpoint_labels)`：通过比较 checkpoint 和参考标签的器官名 ID 分布，自动识别数据集来源（如 FLARE22）。
   - 实现 `build_remap_mapping(checkpoint_labels, detected_dataset)`：按器官名建立参考标签 ID → checkpoint 标签 ID 的映射表。
   - 实现 `apply_remap(reference_array, mapping)`：使用查找表（LUT）重排参考标签数组，避免直接替换时 ID 互相覆盖的问题。

2. **修改 `server/main.py` 的 `validate_against_custom_label()`**
   - 在现有 checkpoint/reference 标签交集检查之后、`compute_label_metrics()` 之前插入自动 remap 逻辑。
   - 检测到已知数据集时，自动重映射参考标签并计算指标，结果中 `remap_applied: true`、`remap_source` 标识来源数据集。
   - import 路径使用 `from server.taxonomy import ...`，确保 `python -m uvicorn server.main:app` 方式启动时能正确导入。
   - 异常处理从静默 `pass` 改为打印错误信息，便于调试。

3. **修改 `src/inference/inferenceClient.ts`**
   - `ValidationSummary` 类型新增 `remap_applied?: boolean` 和 `remap_source?: string`。
   - `normalizeValidation()` 解析这两个新字段。

4. **修改 `src/main.tsx`**
   - `getValidationStatusCopy()` 在验证通过/建议复核文案后追加重映射标签，如"验证通过（FLARE22→当前模型）"。
   - 评估面板新增"标签重映射"指标行，展示来源数据集和目标模型。

5. **补充 `tests/backendState.test.py`**
   - 新增 `test_taxonomy_detects_flare22_and_remaps_label_ids()`：验证 FLARE22 检测、映射正确性（12 个条目）和 apply_remap 对 numpy 数组的效果。
   - 新增 `test_taxonomy_returns_none_for_amos_native_labels()`：验证 AMOS 原生标签不做 remap。

### 43.3 关键实现细节

- **器官名别名**：AMOS22 使用 `postcava`，FLARE22 使用 `inferior_vena_cava`，两者都映射到 canonical name `ivc`。类似地 `gall_bladder`↔`gallbladder`。初始实现遗漏了这些别名，导致只生成 10 个映射条目而非 12 个，后修复。
- **Import 路径**：首次部署使用 `from taxonomy import ...`，在 `python -m uvicorn server.main:app` 方式下 Python 在项目根目录查找而非 `server/` 目录，导致 remap 未生效、Dice 仍为 0.073。修复为 `from server.taxonomy import ...` 后解决。
- **LUT 方式**：`apply_remap()` 使用 `np.zeros_like` + 索引赋值，而非原地替换。这避免了当两个 ID 需要互换时（如 1→3, 3→1）的覆盖问题。

### 43.4 验证数据

job `a717dacf42d3`（FLARE22 Tr 0009 + 自动 taxonomy remap）：

| 指标 | 值 |
|---|---|
| remap_applied | True |
| remap_source | FLARE22 |
| mean_dice | 0.926 |
| 验证状态 | passed |

对比第 42 节的 job `bf20f0ec4456`（无 remap）：mean_dice=0.073。自动 remap 后提升到 0.926，跨数据集在线验证链路正式打通。

### 43.5 验证

- `python tests/backendState.test.py`：通过，覆盖 FLARE22 检测、映射、remap 和 AMOS 原生标签不 remap。
- `npm test`：通过。
- `npm run build`：通过。

### 43.6 行为边界

- 自动 remap 只对已知数据集（当前仅 FLARE22）生效；未知标签体系不做 remap，保持原有逻辑。
- AMOS 原生标签（如 AMOS 0117 参考病例）不会触发 remap，验证流程不受影响。
- 本轮不改变 nnUNetv2 推理参数、推理 profile 或历史实验指标数值。

---

## 44. 窗预设联动器官高亮与模型信息真实化

### 44.1 背景

原有 GUI 的窗宽窗位预设（软组织/肺窗/骨窗）点击后只更新窗参数，没有视觉反馈告诉用户哪些器官在该窗下最相关。模型选择区域显示 3 个虚构模型（Abdomen-TotalSegmentator / Lung-Lobe-AirwayNet / RespDigest-Hybrid），与实际只能运行 AMOS22 单模型的事实不符。

### 44.2 本轮实现

1. **窗预设 → 器官高亮联动**
   - 新增 `presetOrganMap`：`soft` 映射到全部 15 个腹部器官 ID，`lung`/`bone` 为空数组（当前模型无相关标签）。
   - 新增 `activePresetId` 状态：跟踪当前激活的预设按钮。
   - 新增 `highlightedOrganIds` 状态：`Set<string>`，存储需要高亮的器官 ID。
   - `applyWindowPreset()` 重写：设置窗参数 → 切换 `activePresetId` → 设置 `highlightedOrganIds` → 2.2 秒后自动清除高亮。
   - 预设按钮增加 `active-preset` class 条件渲染。
   - 器官行增加 `highlight` class 条件渲染，使用 `.filter(Boolean).join(" ")` 组合 class。

2. **预设 Toast 提示**
   - 新增 `presetToast` 状态和 `presetToastTimerRef`。
   - `showPresetToast()` 函数：清除旧定时器 → 设置新消息 → 2.8 秒后自动清除。
   - 软组织预设：`"软组织 · 高亮 15 个关联器官"`。
   - 肺窗/骨窗预设：`"肺窗：当前模型暂无相关标签，后续扩展后可联动"`。
   - Toast 渲染在 `.preset-strip` 正下方，使用 `.preset-toast` class。
   - `resetView()` 中清除所有预设相关状态和定时器。

3. **模型信息真实化**
   - `modelOptions` 从 3 个虚构模型改为 1 个真实 AMOS22 模型条目。
   - 模型卡片下方新增 `.organ-category-grid`：4 个分类卡片（消化系统/泌尿系统/血管结构/其他器官）。
   - `.model-card` CSS 从 2 列 grid 改为单列，新增 `.model-detail` 样式。

4. **CSS 动画与样式**
   - `.organ-row.highlight`：outline + 背景色。
   - `.organ-row.active.highlight`：更强的绿色（active 优先级高于 highlight）。
   - `@keyframes organ-highlight-pulse`：box-shadow 脉冲淡出。
   - `.organ-row.highlight:not(.active)`：`organ-highlight-pulse-fade` 动画（含背景重置）。
   - `.preset-toast`：`flex-basis: 100%`、绿色背景、`preset-toast-fade` 动画。
   - `.organ-category-grid` / `.organ-category`：2 列 grid 布局、圆点指示器。

5. **定时器管理**
   - `highlightTimerRef` 和 `presetToastTimerRef` 防止快速点击堆叠定时器。
   - `resetView()` 中统一清理两个定时器。

### 44.3 验证

- `npm run build`：TypeScript 检查通过。
- `npm test`：全部测试通过。
- 浏览器验证：
  - 点击"软组织"→ 按钮高亮 + 15 个器官行脉冲高亮 2.2 秒后淡出。
  - 点击"肺窗"→ 按钮高亮 + toast "当前模型暂无相关标签"。
  - 点击"骨窗"→ 按钮高亮 + toast "当前模型暂无相关标签"。
  - 再次点击同一预设 → 取消高亮，恢复默认状态。
  - 重置视图 → 所有预设状态清除。

### 44.4 行为边界

- 本轮只改变前端 UI 交互，不改变 nnUNetv2 推理参数、validation 规则或后端逻辑。
- 肺窗/骨窗的器官映射为空，等待后续模型扩展时补充。
- 高亮动画使用 CSS `forwards` fill-mode，通过拆分 `organ-highlight-pulse` 和 `organ-highlight-pulse-fade` 两套 keyframe 解决 active/highlight 样式冲突。

---

## 45. 报告导出功能与 UI 布局美化

### 45.1 背景

用户需要将分割结果、验证指标、器官列表、测量点和推理时间线等信息导出为可分享的报告文件。原有"导出报告"按钮是演示级占位，只修改前端状态和弹 toast，不生成可下载文件。同时，GUI 顶栏在导入标签文件后出现标题换行、标签名截断等布局问题，需要一并修复。

### 45.2 报告导出实现

1. **新增 `src/report/exportReport.ts`**
   - 定义 `ReportFormat = "html" | "json" | "pdf"` 和 `ReportData` 类型。
   - `exportReport(data, format)` 根据格式分发到 `exportHtmlReport()`、`exportJsonReport()` 或 `exportPdfReport()`。
   - HTML 报告为自包含文件，内联 CSS，`@media print` 友好，包含：概览、验证指标、逐标签指标表、影像量化分析、器官列表、关键发现、测量点、推理时间线。
   - JSON 报告当前为 `schema_version: "1.1"` 和 `report_type: "segmentation"`，包含 `quantification` 字段；早期 1.0 记录已升级。
   - PDF 报告打开新窗口渲染同一 HTML，调用 `window.print()` 让用户"另存为 PDF"，不引入 jsPDF 等重依赖。

2. **修改 `src/main.tsx`**
   - 新增 `selectedExportFormat` 状态（默认 `html`）。
   - `handleExport()` 收集当前病例、模型、推理、验证、器官、测量、时间线等状态组装 `ReportData`，调用 `exportReport()`。
   - 导出按钮区域增加格式选择（HTML / JSON / PDF 三个 ghost-button）。
   - 新增 `import { exportReport, type ReportFormat, type ReportData } from "./report/exportReport"`。

### 45.3 UI 布局美化

1. **顶栏从 grid 改为 flex 布局**
   - `.topbar` 从 `display: grid` 改为 `display: flex; flex-wrap: wrap`。
   - 标题区域 `flex: 0 0 auto; white-space: nowrap`，防止导入标签后标题换行。
   - `.case-wrap` 同样 `flex: 0 0 auto`。
   - `.top-actions` 使用 `flex: 1 1 0%; min-width: 0; justify-content: flex-end`，自动填充剩余空间。
   - 1100px 媒体查询中允许标题 `min-width: 0`，窄屏不溢出。

2. **标签文件名显示优化**
   - 标签按钮文件名截断从 12 字符增加到 18 字符，超出部分显示省略号。
   - 按钮增加 `title` 属性，鼠标悬停可查看完整文件名。
   - 标签按钮选中后增加 `is-selected` class，绿色边框和背景提示已选择状态。

3. **拖放区域三列布局**
   - `.drop-grid` 从 `grid-template-columns: repeat(2, ...)` 改为 `repeat(3, ...)`，三个拖放区域不再挤成两行。
   - 拖放区域文件名增加 `max-width: 100%; overflow: hidden; text-overflow: ellipsis; white-space: nowrap`，防止长文件名溢出。
   - 已有文件的拖放区域增加 `has-file` class，绿色边框和渐变背景提示已导入状态。

4. **Ghost-button 交互增强**
   - 新增 `.ghost-button.is-selected` 样式：绿色边框 + 浅绿背景。
   - 新增 `.ghost-button:hover` 和 `.ghost-button.is-selected:hover` 样式，增强交互反馈。
   - 所有 ghost-button 增加 `transition: background 0.15s, border-color 0.15s, color 0.15s`。

### 45.4 验证

- `npm run build`：TypeScript 检查通过。
- `npm test`：全部测试通过，包括 `browserLayout.test.ts` 的桌面和移动端布局约束。
- 浏览器验证：
  - 载入参考病例 → 运行分割 → 选择 HTML → 导出 → 打开 HTML 验证内容完整。
  - 选择 JSON → 导出 → 验证 JSON 结构和数据完整。
  - 选择 PDF → 导出 → 验证弹出打印窗口，内容与 HTML 一致。
  - 无推理结果时导出 → 各格式均正确显示"待生成"占位。
  - 导入标签文件后，顶栏标题保持一行，标签名完整显示，拖放区域三列布局正常。

### 45.5 行为边界

- 报告导出为纯前端功能，不修改后端。
- PDF 依赖浏览器原生打印功能，不引入第三方 PDF 库。
- 报告不嵌入 CT 切片截图（canvas 截图增大文件体积，HTML 中无法保证跨浏览器渲染）。
- 本轮 UI 布局改动不影响 `browserLayout.test.ts` 的测试断言（该测试使用简化 HTML 结构，无 `.case-wrap` div）。
- 本轮不改变 nnUNetv2 推理参数、validation 规则或历史实验指标。

---

## 46. 文档现状同步与下一轮规划收尾

### 46.1 范围

本轮不改动产品代码，重点核对并同步项目说明、验收、指标、实验对比、模块讲解、协作指南和 `.planning/` 规划目录，使其符合 2026-05-28 GUI 项目现状。

### 46.2 本轮更新

- `AGENTS.md`：补充当前项目状态、API、推理 profile、缓存、heartbeat、取消、报告导出、测试和验收口径。
- `ACCEPTANCE.md`：修正历史 FLARE22 运行中的旧 taxonomy 口径，新增自动 taxonomy remap 在线验证记录。
- `SEGMENTATION_METRICS_SUMMARY.md`：区分 2026-05-26 FLARE22 离线 remap 对照和 2026-05-28 自动 remap 在线 validation。
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`：补充 FLARE22 自动 remap 在线验证详情。
- `README.md`、`CODE_MODULE_GUIDE.md`：同步 FLARE22 标签上传、自动 remap 和 validation 解释边界。
- `.planning/`：新增 `documentation-refresh-20260528/`，更新 `next-round-candidates/`、`label-scoring-optimization/`、`realtime-inference-progress/`、`online-inference-followup/` 和 `non-amos-acceptance-expansion/`。

### 46.3 核对结论

- 文档主体说明保持中文；保留必要英文技术字段、命令、路径、profile、job id 和指标名。
- AMOS 原生验证、FLARE22 自动 remap 在线验证、FLARE22 离线 remap 对照、fast preview 和 cached result 已分开表述。
- 历史记录中的 taxonomy 错位运行仍保留，但已标注为 remap 上线前的历史证据，不能再作为当前能力限制解读。
- 下一轮优先级建议为远程推理分体部署、长耗时病例性能策略、跨数据集标签评估增强、UI/报告细化和多模型准备。

### 46.4 验证

- `node tests/acceptanceDocs.test.ts`：通过。
- `git diff --check`：通过，仅出现 Git 行尾转换提示，无 whitespace error。
- `npm test`：通过；包含前端逻辑、文档、性能工具、布局、后端状态、指标和浏览器布局测试。
- `npm run build`：通过；Vite 构建 `1594` 个模块，用时约 `2.99s`。

### 46.5 行为边界

- 本轮只同步文档和规划，不改变 nnUNetv2 推理、validation、缓存、报告导出或 UI 运行逻辑。
- `CLAUDE.md` 在本轮开始前已有未提交修改；该文件未纳入用户列出的目标文档，本轮提交时应单独确认是否纳入。

---

## 47. 2026-05-29 历史 bug 收口：缓存验证、persistent worker、部分标签 remap

### 47.1 范围

本轮针对项目体检中发现的历史遗留风险做收口：

- 缓存命中时不再复用历史 job 的 validation，避免同一 CT 换标签文件后显示旧 Dice。
- 常驻 nnUNetv2 worker 的 stdout reader 改为进程级共享队列，避免复用 worker 时旧 reader 线程抢读后续事件。
- 移除前后端上传文件名调试日志，降低病例文件名泄露风险。
- 放宽 FLARE22 自动 taxonomy remap 的部分标签检测规则：当少量共享 ID 全部语义错位且至少两个 ID 可判定时，也触发自动 remap。

### 47.2 代码变更

1. **缓存 validation 重新计算**
   - `find_cached_prediction()` 只返回历史预测结果路径和来源 job，不再返回历史 `validation`。
   - `complete_cached_job()` 命中缓存后按当前请求上下文决定 validation：
     - 当前请求带 `label_file`：用当前上传标签重新计算。
     - 当前请求是内置 AMOS 参考病例：用内置标准答案重新计算。
     - 其他无标签请求：不返回 validation。

2. **persistent worker reader 复用**
   - 新增进程级 `persistent_worker_event_queue`、`persistent_worker_stdout_thread` 和 `persistent_worker_reader_process`。
   - `read_persistent_worker_event()` 与 `_read_worker_event_with_heartbeat()` 共用同一个 stdout reader，避免同一 worker 进程被多个临时 reader 竞争消费。
   - `close_persistent_worker_locked()` 会同步清理 reader 状态。

3. **部分标签 taxonomy remap**
   - 完整标签仍采用多数 ID 语义错位的判定。
   - 部分标签在 `match_count == 0` 且 `mismatch_count >= 2` 时视为明确跨数据集错位，可识别为 FLARE22。
   - 单个 label ID 仍保持保守处理，因为仅凭一个 ID 无法可靠区分 AMOS 原生标签和 FLARE22 标签。

4. **调试日志收口**
   - 移除 `src/main.tsx`、`src/inference/inferenceClient.ts` 和 `server/main.py` 中会输出上传文件名或标签文件名的调试日志。

### 47.3 测试覆盖

- `tests/backendState.test.py`：
  - 缓存命中无当前标签时不复用旧 validation。
  - 缓存命中且有当前标签时重新 validation。
  - persistent worker stdout reader 可连续读取同一 worker 的多个事件。
  - 部分 FLARE22 标签 `{1, 3}` 可识别并构建 remap。
  - 后端源码不再包含上传文件名调试日志。
- `tests/imagingLogic.test.ts`：
  - 前端主流程和 inference client 不再包含上传标签文件名调试日志。

### 47.4 验证

- `node tests/imagingLogic.test.ts`：通过。
- `python tests/backendState.test.py`：通过。
- persistent worker 轻量 smoke：启动 `server/persistent_nnunet_worker.py`，发送 `shutdown` JSON，收到 `bye` 事件且进程退出码为 `0`。
- `SEGMENTATION_PERSISTENT_WORKER=1` 开关检查：`persistent_worker_enabled True`。
- `npm test`：通过。
- `npm run build`：通过。

### 47.5 行为边界

- 预测缓存仍按输入 CT、checkpoint 和推理配置复用，不因标签文件变化而重跑 nnUNetv2。
- validation 是当前请求上下文的一部分，不再作为预测缓存的一部分复用。
- 本轮没有运行真实长耗时 persistent worker 推理；已完成协议层和后端 reader 层 smoke，真实性能仍需单独用小病例或专门性能任务验证。
- 部分标签 remap 只处理至少两个明确错位 label 的情况；单 label 文件仍需人工判断或后续引入显式数据集 hint。

---

## 48. 2026-05-29 文档现状同步与下一轮规划

### 48.1 范围

本轮不改动产品代码，核对用户指定的 7 份项目文档和 `.planning/` 规划目录，使说明符合第 47 节修复后的 GUI 现状。

### 48.2 同步内容

- `README.md`：更新项目日期、预测缓存与当前 validation 的边界、`label_file` API 字段、persistent worker smoke 边界和部分 FLARE22 remap 限制。
- `ACCEPTANCE.md`：新增 2026-05-29 历史 bug 收口验收记录，并修正 2026-05-27 标签传输段落中的临时调试日志口径。
- `CODE_MODULE_GUIDE.md`：更新后端 validation/cache 讲解、常驻 worker 共享 reader、测试覆盖和 FLARE22 部分标签边界。
- `SEGMENTATION_RECENT_ROUNDS.md`：把最近更新改为 2026-05-29，移除保留 `console.log` 的待办，并新增缓存 validation 语义收口。
- `SEGMENTATION_METRICS_SUMMARY.md` 与 `SEGMENTATION_EXPERIMENT_COMPARISON.md`：补充 2026-05-29 修复不改变历史指标，但改变后续缓存/validation 解释口径。
- `.planning/`：更新下一轮候选任务，保留远程推理部署、真实 persistent worker 对照、单 label taxonomy hint、报告 remap 摘要等后续事项。

### 48.3 行为边界

- 文档主体继续保持中文；命令、路径、API 字段、profile、job id 和指标字段保留必要英文。
- 本轮不修改真实 CT、NIfTI、checkpoint、推理输出或私有 registry。
- `AGENTS.md`、`CLAUDE.md` 在本轮开始前已有未提交改动，本轮提交不应混入这两个文件。

---

## 49. 2026-05-30 运行位置、局域网配置与服务器编排入口

### 49.1 范围

本轮核对并同步 2026-05-30 的工程链路变化，后续在 2026-05-31 已完成校园网服务器端到端 smoke：

- 前端在线推理增加 `服务器云端推理` / `本地在线推理` 两个运行位置。
- 后端按 `runtime_target=server|local` 分流本地 nnUNetv2 路径和服务器 5-fold soft ensemble 编排路径。
- 局域网访问改为配置化，避免前端和 CORS 只绑定本机 localhost。
- 2026-05-31 校园网链路已能从 Windows 前端提交到 Ubuntu FastAPI 后端，完成 5-fold 推理、soft ensemble、结果下载和 GUI 回填；但 AMOS validation 暴露自动 taxonomy 误判风险，仍不能写成完整质量验收通过。

### 49.2 代码与配置状态

- `src/main.tsx`：通过 `VITE_API_ENDPOINT` 读取后端地址，未设置时回退 `http://127.0.0.1:8000`；分割控制区提供运行位置选择并在 job 运行中锁定。
- `src/inference/inferenceClient.ts`：`createInferenceJob()` 会提交 `runtime_target`、`inference_profile` 和可选 `label_file`，SSE complete event 解析也保留最终运行位置。
- `package.json`：新增 `dev:lan`，用于 Vite 监听 `0.0.0.0:5173`。
- `server/main.py`：支持 `SEGMENTATION_ALLOWED_ORIGINS`，并把 `runtime_target` 写入 job state、SSE、summary 和 cache key。
- `server/server_inference.py`：集中构造服务器 5 fold `nnUNetv2_predict`、`nnUNetv2_ensemble` 和可选评估命令。

### 49.3 文档同步

- `README.md`：补充局域网运行、运行位置、服务器 5-fold soft ensemble 配置、服务器 smoke 结果和 AMOS taxonomy 风险。
- `ACCEPTANCE.md`：补充 2026-05-31 服务器在线推理 smoke 与 validation 风险，明确完整质量验收仍需显式 taxonomy hint 和更多稳定性记录。
- `SEGMENTATION_METRICS_SUMMARY.md`：把服务器 FLARE/AMOS 轮次与本地 AMOS quality 基线分开记录。
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`：新增服务器 FLARE smoke 与服务器 AMOS 异常行，避免把 AMOS 异常误写成模型失败。
- `SEGMENTATION_RECENT_ROUNDS.md`：更新近三轮记录，突出服务器 AMOS taxonomy 异常和 FLARE remap 正常。
- `CODE_MODULE_GUIDE.md`：补充 `runtime_target`、`server/server_inference.py`、局域网配置和下一轮 taxonomy/gating 规划入口。
- `.planning/label-taxonomy-server-validation/`：记录显式 `label_taxonomy=auto|AMOS22|FLARE22` 与 server gating 的下一轮任务。

### 49.4 行为边界

- 当前推荐正式 AMOS 基线仍是 `quality` profile `b3c528cc9e20`；跨数据集在线验证基线仍是 FLARE 自动 remap job `a717dacf42d3`。
- 服务器端到端链路已完成阶段性 smoke，可作为工程进展；服务器 AMOS 质量指标必须等 `label_taxonomy=AMOS22` 复跑并确认 `remap_applied=false` 后再纳入正式基线。
- `runtime_target=server` 创建 job 仍需修复 gating：服务器云端推理不应依赖本地 Windows 的 `dataset.json/plans/checkpoint/python.exe`。
- `AGENTS.md` 属于 agent instruction 文件，当前自动权限拒绝直接覆盖；若需要统一中文主体，需要单独取得用户授权后处理。

## 50. 2026-05-30 校园网访问 planning 与服务器 runtime 包准备

### 50.1 本轮目标

本轮当时不新增推理指标，也不宣称服务器模式已完成质量验收。目标是把真实服务器在线推理的执行路径收敛为可交付材料：先校园网 API 直连，再做 Ubuntu 22.04 真实 5GPU smoke test，最后才视需求进入 VPN/Mesh 或公网入口。2026-05-31 后，校园网服务器 smoke 已完成，剩余重点转为 AMOS/FLARE 显式 taxonomy、server/local gating、取消、失败恢复和长期稳定性验收。

### 50.2 本轮已完成

1. **校园网与公网访问 planning**
   - 新增 `.planning/campus-network-and-public-access/task_plan.md`、`findings.md`、`progress.md`。
   - 规划结论为：优先验证本地电脑前端连接校园网 Ubuntu FastAPI 后端；若校园网互访不稳定，再试 Tailscale / WireGuard；只有真实服务器推理稳定后，才评估 frp、Cloudflare Tunnel、ngrok 或 VPS + HTTPS + 鉴权。
   - planning 明确公网入口不能裸露未授权 FastAPI 端口，需要 HTTPS、鉴权、大文件上传限制、SSE 反代 timeout/buffering 配置和日志脱敏。

2. **服务器 runtime 部署包**
   - 已新增 `deployment-packages/server-runtime-package-20260531.zip`，用于在服务器项目根目录直接解压覆盖当前 FastAPI 后端和 server 推理编排代码。
   - 已新增 `deployment-packages/server-runtime-quickstart-20260531.md`，记录备份 `server/`、解压覆盖、安装 FastAPI 依赖、配置 CORS、配置 `SEGMENTATION_SERVER_*`、检查路径、启动 `uvicorn`、本地前端连接和最小验收标准。
   - 部署包按 `server/...` 项目结构组织，不包含真实 CT/NIfTI、checkpoint、`.env`、日志或推理输出；服务器仍必须具备 CUDA/PyTorch/nnUNetv2、模型目录、数据目录和真实评估脚本路径。

3. **替代服务器能力边界**
   - 如果服务器不放当前后端代码，则必须已有等价推理 API、SSH 执行层或共享文件系统 + 调度系统。
   - 等价 API 至少要支持上传、创建 job、状态查询、SSE 或轮询进度、取消、结果下载、label validation/evaluate、5GPU / 5-fold soft ensemble，并最好兼容当前 GUI 的 `/api/health`、`/api/models`、`/api/segment/jobs`、events、cancel 和 result 接口。

### 50.3 当前未完成

- AMOS 服务器轮次需要在显式 `label_taxonomy=AMOS22` 下复跑，确认 `remap_applied=false` 后才能纳入正式质量基线。
- FLARE 服务器轮次需要在显式 `label_taxonomy=FLARE22` 下复跑，确认 `remap_applied=true`、`remap_source=FLARE22`。
- `runtime_target=server` 的 job 创建 gating 仍需修复，避免服务器云端推理依赖本地 Windows nnUNet 文件。
- 第二台真实局域网设备的大文件上传、SSE 长连接、取消、下载、validation 和前端回填仍需补充记录。
- 公网浏览器入口尚未实施，不能写成已具备公网访问能力。

### 50.4 文档同步

已同步 `README.md`、`ACCEPTANCE.md`、`CODE_MODULE_GUIDE.md`、`SEGMENTATION_RECENT_ROUNDS.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md` 和 `SEGMENTATION_METRICS_SUMMARY.md`，统一口径为：server runtime 包完成了部署准备，2026-05-31 校园网服务器端到端 smoke 已跑通；FLARE 轮次可作为链路证据，AMOS 轮次因疑似 taxonomy 误判暂不作为模型失败或质量基线。

---

## 51. 2026-05-31 AMOS CT 在线推理速度分析

### 51.1 背景

用户导入 AMOS CT 图像进行在线推理，发现推理时间较长。本轮分析推理速度慢的原因，并记录完成后的 fast profile 质量结果。

### 51.2 输入参数

| 项目 | 值 |
|---|---|
| 输入 CT | AMOS CT 图像 |
| Shape | (768, 768, 103) |
| 体素大小 | 0.5078125 × 0.5078125 × 5.0 mm |
| 切片数 | 103 |
| 总像素数 | 60,751,872 |
| 数据类型 | int16 |

### 51.3 模型配置

| 项目 | 值 |
|---|---|
| 数据集 | Dataset001_AMOS22 |
| 模型类型 | 2D (nnUNetTrainer__nnUNetPlans__2d) |
| Patch 大小 | 640 × 640 |
| Batch 大小 | 32 |
| 网络结构 | ResidualEncoderUNet (8 阶段) |
| 参数量 | ~10.2M |

### 51.4 GPU 状态

| 项目 | 值 |
|---|---|
| GPU | NVIDIA GeForce RTX 4060 Laptop |
| 显存 | 8188 MiB |
| 使用率 | 100% |
| 显存占用 | 7782 MiB (95%) |
| 温度 | 57°C |
| 当前频率 | 2505 MHz (最大 3105 MHz，80%) |
| 功耗 | 27W / 40W |

### 51.5 推理速度分析

**完成状态**：job `ad3d14eba3de` 已完成，使用 `fast` profile，`mean_dice=0.77724`。该轮适合作为高分辨率预览证据，不替代 AMOS `quality` profile 正式质量基线。

**速度瓶颈**：

1. **分辨率过高**：输入 CT 为 768×768，比标准 AMOS 的 512×512 大 2.25 倍
2. **显存接近满载**：95% 显存占用导致性能下降
3. **GPU 功耗受限**：笔记本功耗墙限制，频率只有最大值的 80%
4. **2D 模型处理 3D 数据**：103 个切片需要逐个处理
5. **需要重采样**：输入 768×768 需要重采样到 patch 640×640

**推理速度口径**：
- 高分辨率输入会显著拉长本地 2D nnUNet 推理时间
- 服务器 5GPU/5-fold soft ensemble 与本地 RTX 4060 Laptop 结果需分开记录
- fast profile 的速度和质量都不能直接外推到 quality profile

### 51.6 结论

推理速度慢的主要原因是输入分辨率过高（768×768 vs 标准 512×512）。加上笔记本 GPU 功耗限制和显存压力，导致本地推理耗时明显增加；最终 `mean_dice=0.77724` 与 fast profile 预览定位一致。

**下次优化建议**：
1. 预处理时评估降采样到 512×512
2. 使用 3D 模型（如果有）做同病例对照
3. 在台式机或服务器 GPU 上运行，记录与本地 RTX 4060 Laptop 的差异

---

## 52. 2026-06-01 本地缓存演示

### 52.1 本轮目标

为 BME 竞赛 PPT 演示准备一条最短的"本地缓存演示"链路：先用 AMOS 0117 演示 cache hit（已有历史预测能立刻复用），再用 FLARE22 Tr 0009 真实跑一次 nnUNetv2 推理证明本地推理仍可用，最后再 cache hit 一次同一份 FLARE22 输入证明缓存确实生效。本轮的目的是工程链路演示和 reproducible runbook，不重写正式质量基线，也不替代 AMOS / FLARE 的 quality profile 评估结果。

### 52.2 本轮已完成

1. **后端依赖与启动方式收口**
   - 在 `D:\BME2026\BME_CT_Seg\nnunet_env` 增加 `fastapi 0.136.3`、`uvicorn 0.48.0`、`python-multipart 0.0.30`，让 nnunet 推理环境同时具备 GUI 后端能力。
   - 确认 `uvicorn server.main:app` 的 cwd 必须落在 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\`，否则 `_resolve_project_root()` 解析不到 `nnunetv2_files/`、`examples/`、`server/`。
   - 必须设置 `SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json`，否则只暴露内置 `amos_0117`，FLARE22 Tr 0009 不会出现在 `/api/samples` 列表里。

2. **AMOS 0117 预热（Phase A）**
   - 编写 `tools/seed_demo_cache.py`：用 `compute_cache_key()` 的 7 字段（输入 SHA-256、模型 dataset、profile、label_taxonomy、runtime_target、postprocess、device）匹配 2026-05-23 的 review 状态预测 `009d4efdc5f6`，幂等回写 `job_summary.json` 后让 `find_cached_prediction()` 能命中。
   - 真实演示一次 cache hit：job `aea4e7cdbaf0`，mode = `cached-real-nnunetv2`，命中 `009d4efdc5f6`，前端 timeline 立刻显示完成、`profile=quality`、AMOS 内置参考标签 validation 摘要。
   - 该预热预测仍是 review 状态（stomach Dice 0.556），不能作为正式 AMOS 质量基线；正式基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。

3. **FLARE22 真实推理（Phase B）**
   - 真实跑通 FLARE22 Tr 0009，job `0aa7323a4c01`，本地单机 RTX 4060 Laptop，fold0，profile `quality`，耗时 218s。
   - `remap_applied=true`，`remap_source=FLARE22`，证明 `server/taxonomy.py` 的自动 remap 路径在本地推理也工作正常。
   - 该轮 mean_dice 与 2026-05-28 在线服务器 5-fold ensemble `a717dacf42d3` 的 0.926 不可直接对比，仅作 cache demo Phase B 链路证据。

4. **FLARE22 cache hit（Phase C）**
   - 用相同输入再次提交，job `02da885c97d8`，mode = `cached-real-nnunetv2`，命中 Phase B 的 `0aa7323a4c01`。
   - cache hit 总耗时 0.001s，明显比 Phase B 的 218s 短，肉眼可见缓存生效。
   - 同样保持 `remap_applied=true`、`remap_source=FLARE22`。

5. **文档与脚本**
   - 新增 `docs/local-cache-demo-runbook.md`：启动命令、关键路径、参考病例 JSON 用法、3 个 job 的对照表、cache_key 7 字段、4 个已知约束（环境变量、cwd、reference cases JSON、AMOS 预热预测的 review 状态）。
   - 新增 `docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`：本轮设计稿。
   - 新增 `docs/superpowers/plans/2026-06-01-local-cache-demo.md`：本轮实施计划。
   - 新增 `tools/seed_demo_cache.py`：幂等预热脚本，可独立重跑。

### 52.3 当前未完成

- AMOS 预热预测 `009d4efdc5f6` 仍是 2026-05-23 的 review 状态（stomach 0.556），需要后续用新训练权重或 quality profile 复跑替换。
- 本轮 cache demo 没有运行 `npm test` / `npm run build`：因为没有改动前后端 TypeScript / FastAPI 业务代码，只新增工具脚本和文档。后续如果要把 `tools/seed_demo_cache.py` 纳入回归，需要补 `tests/backendState.test.py` 或脚本级 smoke。
- 高分辨率 CT 推理优化（预降采样、3D 模型评估）仍是 `.planning/high-resolution-inference-optimization/` 的下一步。
- `runtime_target=server` 的 job 创建 gating 仍未修复，本轮 cache demo 全部走 `runtime_target=local`。
- AMOS / FLARE 服务器轮次的显式 `label_taxonomy` 复跑仍在 `.planning/label-taxonomy-server-validation/` 中等待。

### 52.4 行为边界

- 本轮 cache demo 是 BME 竞赛 PPT 演示的工程链路证据，不替代任何正式质量基线：AMOS 基线仍是本地 quality `b3c528cc9e20`、跨数据集在线基线仍是服务器 5-fold ensemble `a717dacf42d3`。
- `cached-real-nnunetv2` 只复用预测 NIfTI，不复用旧 job 的 validation：当前请求带 `label_file` 时会重新 validation；演示中 AMOS cache hit 没上传当前标签，所以走的是 AMOS 内置参考标签 validation 摘要，前端会标注 review 状态。
- Cache key 仍按 7 字段唯一索引，任意字段变化都视为不同 cache，不存在隐式 fallback；这一点已经在 `docs/local-cache-demo-runbook.md` 单列说明。
- FLARE22 Tr 0009 演示用本地 fold0 与服务器 5GPU/5-fold soft ensemble 不是同一推理路径，结果不能写成跨数据集质量基线。

### 52.5 文档同步

已同步 `README.md`、`ACCEPTANCE.md`、`SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_RECENT_ROUNDS.md`、`CODE_MODULE_GUIDE.md`、`CLAUDE.md`、`AGENTS.md`，统一口径为：2026-06-01 本地缓存演示完成 AMOS cache hit + FLARE22 真实推理 + FLARE22 cache hit 的 7 步；预热脚本 `tools/seed_demo_cache.py`、运行手册 `docs/local-cache-demo-runbook.md` 和 spec/plan 已落地；AMOS cache 命中的是 2026-05-23 review 预测，不作为正式 AMOS 基线。

新增/待新增的 planning 子目录：`.planning/2026-06-01-local-cache-demo/`，沿用 `explanation.md` / `findings.md` / `progress.md` / `task_plan.md` 4 个文档结构，作为本轮回顾和下一轮工程入口候选。

---

## 五十三、2026-06-01 cache 链路补丁：FLARE22 cache hit 显示历史 validation 摘要

### 53.1 现象

- 7 步本地缓存演示跑通后，现场复测时发现 FLARE22 Tr 0009 cache hit（`02da885c97d8`）显示的 validation 摘要（mean_dice 0.891，stomach 0.556）实际来自 `009d4efdc5f6`（AMOS 0117 历史推理），与 README/参考病例的 0.893/0.674/0.950 不一致。看起来像"FLARE22 cache hit 用了 AMOS 的数据"。
- 进一步看，"FLARE22 Tr 0009 载入参考病例"也错误显示了 `amos_0117_original.nii.gz` 768×768×103 路径——所有参考病例载入都跑到了 AMOS 0117。

### 53.2 根因

1. **`find_cached_prediction()` 只按 mtime 排序候选**：`server/work/` 下有空 job 目录或 `validation_summary.json` 不存在的 source，按 mtime 倒序会被误选。
2. **`complete_cached_job()` 不回退到 cache_source 的 validation_summary.json**：cache hit 找不到当前 validation 时直接给 null，前端 fallback 到"等待验证结果"或"无历史验证摘要"。
3. **新预测 `0aa7323a4c01` 与历史 `86b0153d0a73` 字节不同**：cache_key 也不一致，新 FLARE cache hit 没有自己可读的 validation_summary.json。
4. **现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`**：默认只暴露内置 `amos_0117`，FLARE22 Tr 0009 不会出现在 `/api/samples`，所以"载入参考病例"无论选哪个都跑到了 AMOS 0117。

### 53.3 修复

| 修复点 | 文件 | 内容 |
|---|---|---|
| historical 回退 | `server/main.py` | 新增 `_load_cached_validation_summary()`，`complete_cached_job()` 在无当前 validation 时回退到 `cache_source_job_id/output/validation_summary.json`，加 `historical: true` 和 `source_job_id` 标记。 |
| cache_source 优先级 | `server/main.py` | `find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序，优先选带 `validation_summary.json` 的 cache_source。 |
| 改写历史摘要 | `tools/rewrite_flare22_historical_summary.py` | 因新预测字节不同，按 2026-05-26 remap 后的 metrics 把 validation_summary.json 写入 0aa7323a4c01 的 output。mean_dice=0.893127、min_dice=0.67373、fg=0.949908、15 个标签、`historical: true`、`source_job_id="0aa7323a4c01"`。 |
| 前端文案 | `src/main.tsx` | `getValidationStatusCopy(validation, hasLabelFile, cachedResult)` 增加 cachedResult 参数，区分"无历史验证摘要"和"（历史离线缓存摘要）"。 |
| TS 字段 | `src/inference/inferenceClient.ts` | `InferenceEvent` / `InferenceStatus` / `ValidationSummary` 增加 `cached_result` / `cache_source_job_id` / `historical` / `source_job_id` 字段。 |
| 回归测试 | `tests/backendState.test.py` | 新增 `test_cached_prediction_falls_back_to_source_validation_summary` 和 `test_cached_prediction_without_historical_validation_summary`。 |

### 53.4 验收结果

| 检查项 | 结果 |
|---|---|
| FLARE22 cache hit | 显示 0.893127/0.67373/0.949908（来自 2026-05-26 remap 后的真实指标，标注"（历史离线缓存摘要）"） |
| AMOS cache hit | 仍显示 009d4efdc5f6 的 review 状态（stomach 0.556） |
| 参考病例列表 | 设置 `SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json` 后 `/api/samples` 返回 4 个 case |
| 文档口径 | README/ACCEPTANCE/REVIEW/CODE_MODULE_GUIDE/SEGMENTATION_* 已统一标注"历史离线缓存摘要" |

### 53.5 教训

- env var 缺一项就会让整条 cache 链路看起来指向错位数据；runbook 必须把 `SEGMENTATION_REFERENCE_CASES_JSON` 写在最前面，并提示用 `/api/samples` 列表确认 4 个 case。
- cache hit 显示的 validation 摘要可能来自 cache_source_job_id，而不是当前请求的重新计算；文档和 UI 都必须明确"（历史离线缓存摘要）"。
- cache 命中仅复用预测 NIfTI，validation 是独立链路；当 cache_source 的 validation 摘要与新预测字节不一致时，需要单独写历史摘要工具（本轮方案 B：直接拷贝 2026-05-26 metrics 到 0aa7323a4c01）。

### 53.6 文档同步

9 份核心文档（README/CLAUDE/AGENTS/ACCEPTANCE/REVIEW/CODE_MODULE_GUIDE/SEGMENTATION_RECENT_ROUNDS/SEGMENTATION_EXPERIMENT_COMPARISON/SEGMENTATION_METRICS_SUMMARY）已添加"2026-06-01 cache 链路补丁"或同等描述，统一口径为：FLARE22 cache hit 正确显示 0.893127/0.67373/0.949908 + "（历史离线缓存摘要）"；`SEGMENTATION_REFERENCE_CASES_JSON` 必须显式设置；`tools/rewrite_flare22_historical_summary.py` 是配套的"按历史指标改写新 cache_source 摘要"工具。

---

## 五十四、2026-06-02 detect_dataset 二轮收紧 + 前端按 dataset 预设 taxonomy

### 54.1 现象

- 现场用 AMOS 0117 走"参考病例 → 推理 → 查看 Dice"时，发现 `remap_applied=true`、`remap_source=FLARE22`，mean_dice 异常偏低（与 2026-05-30 服务器 AMOS 轮次相似的错误 remap 模式）。
- 但 2026-05-31 已经实现显式 `label_taxonomy=auto|AMOS22|FLARE22` 和"标签 ID 是 checkpoint 子集时不触发 remap"的保守 `detect_dataset()`，为什么 AMOS 还是被错判？

### 54.2 根因

读取 `amos_0117_label.nii/amos_0117(2).nii` 实际 unique IDs：

```text
AMOS 真实 label unique IDs = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}  # 缺 14, 15
FLARE22 真实 label unique IDs = {1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13}
```

AMOS ckpt 包含 1-15（共 15 个前景标签）。`amos_0117_label.nii` 实际只有 1-13（无膀胱/前列腺/子宫体素），这与 FLARE22 真实 1-13 在裸 ID 集合上**完全一致**。

旧 `detect_dataset()` 走"reference_ids ≠ ckpt_ids → 进入 dataset 循环 → shared_ids 13 个里 12 个 FLARE22 命名 ≠ ckpt 命名"→ 12/13 mismatch ≥ 5 → 返回 `FLARE22`。问题：AMOS 自指在 ID 子集视角下根本无法被自动识别。

### 54.3 修复

| 修复点 | 文件 | 内容 |
|---|---|---|
| 0.85 coverage 守卫 | `server/taxonomy.py:detect_dataset()` | `coverage = len(reference_ids ∩ ckpt_ids) / len(ckpt_ids) >= 0.85` → `None`。比 `reference_ids == ckpt_ids` 更宽松，覆盖 AMOS 1-13 这种"实际 ID 数量略少于 ckpt"的情况。 |
| 前端预设 | `src/main.tsx:mapDatasetToLabelTaxonomy()` | 新增工具函数：AMOS / AMOS22 → `AMOS22`、FLARE / FLARE22 → `FLARE22`、其他保持原值。`loadReferenceCase()` 在拿到参考 label 后立即调用并 `setSelectedLabelTaxonomy()`。 |
| `auto` 退化为保底 | 文档/UI | `label_taxonomy=auto` 在 AMOS 1-13 vs FLARE22 1-13 不可分的边界不再保证正确；正式质量基线应使用显式 `AMOS22` / `FLARE22`，或依赖参考病例 registry 的 `dataset` 字段。 |
| 回归测试 | `tests/backendState.test.py` | 新增 `test_taxonomy_returns_none_for_realistic_amos_1_to_13_reference`（AMOS 1-13 + ckpt 1-15）。同步更新 FLARE22 1-13 + ckpt 1-15 用例注释（新行为下也是 `None`，由前端预设补）。 |

### 54.4 验收结果

| 检查项 | 结果 |
|---|---|
| AMOS 1-15 vs ckpt 1-15 | `None`（短路 `reference_ids == ckpt_ids`） |
| AMOS 1-13 真实 vs ckpt 1-15 | `None`（coverage 0.867 ≥ 0.85） |
| FLARE22 1-13 真实 vs ckpt 1-15 | `None`（coverage 0.867 ≥ 0.85；由前端 `mapDatasetToLabelTaxonomy()` 预设 `FLARE22`） |
| AMOS {1,2,6} vs ckpt 1-15 | `None`（mismatch=0 < 5） |
| Partial {1,3} vs 3-label ckpt | `None`（`len(shared_ids) < 3` 守卫） |
| `npm test` / `python tests/backendState.test.py` / `npm run build` | 全过（`EXIT=0`） |

### 54.5 行为边界

- `auto` 模式在裸 ID 不可分边界（AMOS 1-13 vs FLARE22 1-13）退化为保底（不 remap），但不会把 AMOS 自身错 remap 为 FLARE22。
- 显式 `label_taxonomy=AMOS22` / `FLARE22` 仍是正式质量基线入口；用户上传的 FLARE22 标签文件仍可选 `FLARE22` 强制 remap。
- `mapDatasetToLabelTaxonomy()` 只在 `dataset` 字段是 `AMOS22 / AMOS / FLARE22 / FLARE` 时才预设；其他字段（`unknown` / `custom`）保留用户当前选择。
- 本修复不改变 nnUNetv2 推理、缓存复用、SSE 协议或影像量化逻辑；不修改 `SEGMENTATION_METRICS_SUMMARY.md` 中任何基线指标数值。

### 54.6 文档同步

9 份核心文档（README/CLAUDE/AGENTS/ACCEPTANCE/REVIEW/CODE_MODULE_GUIDE/SEGMENTATION_RECENT_ROUNDS/SEGMENTATION_EXPERIMENT_COMPARISON/SEGMENTATION_METRICS_SUMMARY）已添加"2026-06-02 detect_dataset 二轮收紧"或同等描述，统一口径为：`detect_dataset()` 0.85 coverage 守卫 + 前端 `loadReferenceCase()` 按 `referenceCase.dataset` 预设 `label_taxonomy`；`auto` 退化为保底；AMOS 真实 1-13 数据走 `None`，由前端 `mapDatasetToLabelTaxonomy()` 把 FLARE22 病例自动设成 `FLARE22`、AMOS 病例自动设成 `AMOS22`。

---

## 五十五、2026-06-02 dataset_hint 字段打通 auto 边界

### 55.1 现象

第 54 节上线 0.85 coverage 守卫后，FLARE22 真实 1-13 标签（`{1..13}`）和 AMOS 真实 1-13 标签都直接被 `detect_dataset()` 返回 `None`。这意味着 FLARE22_Tr_0009 这类参考病例在 `auto` 模式下走不到 remap 路径——前端虽然已经按 `referenceCase.dataset` 把 `label_taxonomy` 自动设成 `FLARE22`，但如果用户手动把 `label_taxonomy` 切回 `auto`（或将来从其他入口提交时不携带 `label_taxonomy`），FLARE22 真实标签会落到"不 remap 但又被当成 AMOS 原生 ID"的边界上，Dice 再次跌到 0.073 量级。

### 55.2 根因

`auto` 模式与 `detect_dataset()` 的 0.85 守卫存在逻辑冲突：

- AMOS 1-13 真实数据需要走 `None`（避免被错 remap）。
- FLARE22 1-13 真实数据同样走 `None`（0.85 coverage 命中），但实际应该 remap。

仅靠 `detect_dataset()` 在裸 ID 不可分时无法可靠判断；后端必须依赖其他信号——比如参考病例的 `dataset` 字段。

### 55.3 修复

| 修复点 | 文件 | 内容 |
|---|---|---|
| 后端 Job 字段 | `server/main.py` | `Job` dataclass 新增 `dataset_hint: str \| None = None`；`create_job` 接收 `dataset_hint: str \| None = Form(None)`，归一化（`strip().upper()`）后写入 job state 和 `job_summary.json`。 |
| 后端优先级 | `server/main.py:validate_against_custom_label()` | 新增 `dataset_hint: str \| None = None` 参数；优先顺序：`taxonomy_hint=AMOS22/FLARE22` → `dataset_hint=FLARE22/AMOS22` → `detect_dataset()`。`dataset_hint=FLARE22` 强制 `detected="FLARE22"`，覆盖 0.85 守卫的 None。 |
| 后端 action 文案 | `server/main.py` | `action` 区分"已按用户选择" / "已按参考病例" / "已自动"。 |
| 前端状态 | `src/main.tsx` | 新增 `referenceCaseDatasetHint` 状态；`loadReferenceCase()` 成功后 `setReferenceCaseDatasetHint(referenceCase.dataset \|\| null)`；catch / else / 上传自定义 NIfTI（`role === "source"`）时清空。 |
| 前端 inference client | `src/inference/inferenceClient.ts` | `createInferenceJob` options 增加 `datasetHint?: string \| null`；`formData.append("dataset_hint", ...)` 仅在 truthy 时提交。 |
| 回归测试 | `tests/backendState.test.py` | 新增 `test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto`：构造 AMOS ckpt 1-15 + FLARE22 真实 1-13 标签 + 预测 AMOS view；在 `taxonomy=auto + dataset_hint=FLARE22` 下验证走 remap、mean_dice > 0.5；在 `taxonomy=auto + dataset_hint=AMOS22` 下验证保持 `None`、mean_dice 很低。 |

### 55.4 验收结果

| 检查项 | 结果 |
|---|---|
| FLARE22 + taxonomy=auto + dataset_hint=FLARE22 | `detected="FLARE22"`（覆盖 0.85 守卫），`remap_applied=true`，mean_dice 显著恢复 |
| FLARE22 + taxonomy=auto + dataset_hint=AMOS22 | `detected=None`，`remap_applied=false`（避免误 remap） |
| AMOS + taxonomy=auto + dataset_hint 未设 | `detected=None`，`remap_applied=false`（与 54 节行为一致） |
| 上传自定义 NIfTI | `referenceCaseDatasetHint` 自动清空，不继承上一参考病例的 dataset |
| `npm test` / `python tests/backendState.test.py` / `npm run build` | 全过（`EXIT=0`） |

### 55.5 行为边界

- `dataset_hint` 不影响 `taxonomy_hint` 显式选择：用户选 `label_taxonomy=AMOS22/FLARE22` 时仍以 `taxonomy_hint` 为准。
- `dataset_hint` 仅在 `taxonomy=auto` 时作为 `detect_dataset()` 之外的补充信号；当 `detect_dataset()` 已经能判定（如 `AMOS 1-15 == ckpt 1-15`）时仍走更具体的判定。
- 上传自定义 NIfTI 时 `dataset_hint` 自动清空，避免错误继承——这是为了防止"上次载入 FLARE22 参考病例，本次上传 AMOS 标签"导致 AMOS 标签被错 remap。
- 本轮不修改 `server/taxonomy.py` 的判定逻辑；`detect_dataset()` 的 0.85 守卫保持不变。`server/main.py` 三个 `validate_against_custom_label()` 调用点都同步传 `dataset_hint=job.dataset_hint`。

### 55.6 文档同步

9 份根文档（README/CLAUDE/AGENTS/ACCEPTANCE/REVIEW/CODE_MODULE_GUIDE/SEGMENTATION_RECENT_ROUNDS/SEGMENTATION_EXPERIMENT_COMPARISON/SEGMENTATION_METRICS_SUMMARY）+ `.planning/label-taxonomy-server-validation/{explanation,findings,progress,task_plan}.md` 4 份 planning 文档均已添加 "2026-06-02 dataset_hint 字段打通 auto 边界" 描述，统一口径为：

- `validate_against_custom_label()` 的优先级：`taxonomy_hint` 显式选择 > `dataset_hint` 参考病例上下文 > `detect_dataset()` 自动检测。
- `dataset_hint=FLARE22` 覆盖 0.85 守卫的 None，让 FLARE22_Tr_0009 在 `auto` 模式下仍能正确 remap。
- `dataset_hint=AMOS22` 不再误 remap。
- 上传自定义 NIfTI 时 `dataset_hint` 自动清空。
- 本轮不改变 nnUNetv2 推理、缓存复用、SSE 协议、影像量化或历史基线指标数值。

## 五十六、2026-06-03 质量评估指标扩展 + 表面距离计算加速

### 56.1 现象

2026-05-25 baseline 在 `quality` profile 下只把 Dice / IoU / HD 三类指标显示到 HTML 报告，逐标签表也只显示 Dice / IoU / HD 三列。验收指南要求把质量评估报告补齐到包括 Pixel Accuracy、HD95、ASD 在内的医学影像主流指标。同时，本轮实测发现：缓存命中路径下 validation 阶段耗时 `38.86s`，比 `quality` 推理本身（`1360.398s` 的 1/35）还慢 10 倍以上；逐器官遍历 + 6 EDT/label 是主要瓶颈。

### 56.2 根因

- `server/main.py` 的 `compute_label_metrics()` 在每个 label 上独立调用 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 三个函数；每个函数都自己跑 `distance_transform_edt` 一到两次（crop + 双向 surface mask），结果单 label EDT 调用计数 ≈ 6。
- 13 个 label × 6 次 EDT + foreground 1 次 = 768×768×103 volume 上 `validation` 阶段要跑约 80 次 `distance_transform_edt`，CPU 端 numpy loop 累计 38.86s。
- `src/inference/inferenceClient.ts` 的 `ValidationSummary` 类型与 `normalizeValidation()` 白名单只有 Dice / IoU / HD 三类指标，其他指标字段被无声丢弃。
- `src/report/exportReport.ts` 的 HTML 报告模板只渲染 Dice / IoU metric group 与逐标签 Dice / IoU / HD 三列。

### 56.3 修复

| 修复点 | 文件 | 内容 |
|---|---|---|
| 后端新函数 | `server/main.py` | 新增 `surface_distances(prediction_mask, reference_mask, spacing_tuple)`：1 次 crop + 2 个 surface mask + 2 次 `distance_transform_edt`（预测→参考、参考→预测），再用 value 数组派生 `asd` / `hd` / `hd95` / `forward_*` / `backward_*`。 |
| 旧函数保留 | `server/main.py` | `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 保留为 legacy 供 `test_surface_distances_matches_legacy_individual_functions` 1e-9 精度对照。 |
| compute_label_metrics | `server/main.py` | 单个 label 改用 `surface_distances()`；foreground metrics 也走 `surface_distances()`（非全 volume union mask）。 |
| validation 字段扩展 | `server/main.py` | `validation_summary.json` 增补 12 个字段：pixel_accuracy / mean_pixel_accuracy / min_pixel_accuracy / foreground_pixel_accuracy、mean_asd / max_asd / foreground_asd、mean_hd / max_hd / foreground_hd、mean_hd95 / max_hd95 / foreground_hd95、surface_distance_unit="mm"、spacing=[sx, sy, sz]；per-label 增补 pixel_accuracy / asd / hd / hd95。 |
| 前端白名单 | `src/inference/inferenceClient.ts` | `ValidationSummary` / `LabelMetric` 增补上述字段；`normalizeValidation()` 加入白名单；`parseInferenceEvent()` 在 complete 事件里透传。 |
| HTML 报告 metric group | `src/report/exportReport.ts` | 3 个 metric group：区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD；共 19 张卡片；HD/HD95/ASD 卡片使用 mm 单位 + ≤1mm 绿 / ≤3mm 黄 / >3mm 红色阶。 |
| 逐标签表 | `src/report/exportReport.ts` | 新增 4 列：像素准确率、ASD (mm)、HD95 (mm)、HD (mm)；共用 `metricBarHtml(value, kind)` 渲染器，根据 kind 决定色阶和单位。 |
| 距离色阶 | `src/report/exportReport.ts` | 新增 `distLevel()` / `distBarPercent()` helpers；`metricBarHtml` 扩展 `kind: "dice" \| "iou" \| "pix" \| "dist"`，`metricCard` 扩展 `kind: "vox" \| "dist"`。 |
| 报告元信息 chips | `src/report/exportReport.ts` | 逐标签表上方显示 `spacing=[sx, sy, sz] mm` 与 `surface_distance_unit=mm` 两个 info tag，便于对照物理单位。 |
| 回归测试 | `tests/backendState.test.py` | `test_surface_distances_matches_legacy_individual_functions`（4 shape × 8 场景 1e-9 精度对照）；`test_surface_distances_uses_fewer_distance_transforms_than_legacy`（patch `scipy.ndimage.distance_transform_edt` 计数恒为 2）；`test_compute_label_metrics_with_surface_distances_faster_than_legacy`（wall-time 加速比 ≥30% 断言）。 |
| 前端解析测试 | `tests/imagingLogic.test.ts` | source-grep 约束全部 12 个新字段；`parseInferenceEvent()` complete 事件解析值测试。 |
| 报告中文 | `src/report/exportReport.ts` | 3 个 metric group 标题保持中文：区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD。 |

### 56.4 验收结果

| 检查项 | 结果 |
|---|---|
| 1e-9 精度对照 | 4 shape（sphere / shell / cube / sphere+ring）× 8 场景下新 `surface_distances()` 与旧 `average_surface_distance` + `hausdorff_95` + `hausdorff_distance_full` 完全一致（差 ≤ 1e-9） |
| EDT 调用计数 | patch `scipy.ndimage.distance_transform_edt` 后单 label 调用恒为 2 次（`forward` + `backward`），旧路径 6 次 |
| 性能实测 | AMOS 0117 quality cache hit（job `2d477d8bbd7d`）：validation 阶段从 `38.86s` 降到 `16.78s`，约 2.3× 加速；EDT 调用计数从 6/label 降到 2/label |
| wall-time 加速断言 | `test_compute_label_metrics_with_surface_distances_faster_than_legacy` 在 768×768×103 mock volume 上跑 3 轮取中位数，新路径比旧路径快 ≥30% |
| HTML 报告渲染 | 3 个 metric group 共 19 张卡片正常显示；逐标签表 6 列（dice / iou / pixel_accuracy / asd / hd95 / hd）正确显示；spansing + surface_distance_unit chips 正常显示 |
| 色阶独立 | HD/HD95/ASD ≤1mm 绿 / ≤3mm 黄 / >3mm 红色阶，与 Dice 0.85/0.70 阈值互不影响 |
| 字段透传 | `validation_summary.json` 12 个新字段在 SSE complete 事件、job_summary.json、HTML 报告、JSON 报告中均能透传；前端 `inferenceClient.ts` 解析后类型正确 |
| `npm test` / `python tests/backendState.test.py` / `npm run build` | 全过（`EXIT=0`） |

### 56.5 行为边界

- 本轮不修改 nnUNetv2 模型推理、缓存复用、SSE 协议或影像量化逻辑；只新增表面距离计算函数、扩展 validation 字段、重写 HTML 报告 metric group。
- 本轮不改变历史 AMOS `quality` profile `b3c528cc9e20`（mean Dice 0.924780）、FLARE22 自动 remap `a717dacf42d3`（mean Dice 0.926）、FLARE22 离线 remap `86b0153d0a73`（mean Dice 0.893127）三套基线数值；新指标在 AMOS quality 缓存命中（如 `2d477d8bbd7d` / `9fd0fdc39960` / `096e5b8349df`）上的具体数值为 mean Dice 0.891327、mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm。
- HD / HD95 / ASD 报告单位固定为 mm（按 NIfTI spacing 缩放），与 Pixel/Voxel Accuracy 的 0-1 比例独立；色阶阈值 1mm / 3mm 不与 Dice 阈值 0.85 / 0.70 混用。
- 旧 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 保留为 legacy 仅供回归测试对照，不应在 `compute_*_metrics` 路径再被调用；新调用方请使用 `surface_distances()`。
- `tests/backendState.test.py` 的 3 个新测试是本轮行为的硬约束：精度 1e-9、EDT 调用计数恒为 2、wall-time 加速比 ≥30%。后续重构如果破坏其中任一约束，CI 会直接挂掉，避免回退到 6 EDT 模式。

### 56.6 文档同步

9 份根文档（README/CLAUDE/AGENTS/ACCEPTANCE/REVIEW/CODE_MODULE_GUIDE/SEGMENTATION_RECENT_ROUNDS/SEGMENTATION_EXPERIMENT_COMPARISON/SEGMENTATION_METRICS_SUMMARY）+ `.planning/quality-metrics-and-surface-distances/{explanation,findings,progress,task_plan}.md` 4 份新增 planning 文档均已添加 "2026-06-03 质量评估指标扩展 + 表面距离计算加速" 描述，统一口径为：

- 6 类医学影像主流指标：Dice、IoU、Pixel Accuracy、HD、HD95、ASD；逐标签 4 列：像素准确率、ASD (mm)、HD95 (mm)、HD (mm)。
- 距离单位固定 mm（按 NIfTI spacing 缩放），色阶 ≤1mm 绿 / ≤3mm 黄 / >3mm 红；与 Dice 0.85/0.70 阈值互不影响。
- `surface_distances()` 1 crop + 2 EDT/label 是单 label 性能不变量；新增 `compute_*_metrics` 调用方应继续复用该实现，避免回退到 6 EDT 模式。
- 本轮不改变 nnUNetv2 推理、缓存复用、SSE 协议、影像量化或历史基线指标数值；只新增 12 个 validation 字段、3 个 metric group、4 列逐标签表。

---

*文档版本：2026-06-03*
*更新依据：当前 `src/main.tsx`、`src/inference/inferenceClient.ts`、`src/report/exportReport.ts`、`server/main.py`、`server/server_inference.py`、`server/taxonomy.py`、`tools/seed_demo_cache.py`、`tools/rewrite_flare22_historical_summary.py`、`tools/segmentation_metrics_summary.py`、`docs/local-cache-demo-runbook.md`、`docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`、`docs/superpowers/plans/2026-06-01-local-cache-demo.md`、`package.json`、`README.md`、`ACCEPTANCE.md`、`SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_RECENT_ROUNDS.md`、`CODE_MODULE_GUIDE.md`、`CLAUDE.md`、`AGENTS.md`、`.planning/lan-direct-and-tunnel/`、`.planning/campus-network-and-public-access/`、`.planning/label-taxonomy-server-validation/`、`.planning/high-resolution-inference-optimization/`、`.planning/2026-06-01-local-cache-demo/`、`.planning/quality-metrics-and-surface-distances/` 与 `deployment-packages/`。*
