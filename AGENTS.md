# 仓库协作指南

## 当前运行状态

截至 2026-06-06，项目已完成：

- **2026-06-06 演示当天收口 + B1-B4 演示关键 bug 修复**：`src/main.tsx` 修复 4 个演示当天容易翻车的边缘场景：
  - **B1 SSE 进度回退**：heartbeat 心跳事件没有 `percent` 字段时不再覆盖当前进度；只有带 `percent` 的事件才更新进度条。`tests/imagingLogic.test.ts` source-grep 守护 `event.percent` 检查。**2026-06-06 `76bb1ff` 补完**：6-06 `23e0c4d` 虚标，源码实际未做；同日 `76bb1ff` 真正实现 `parsed.heartbeat && parsed.progress === 0` 守护。
  - **B2 取消后残留进度**：取消 job 后后端不会继续写 progress 事件；前端不把 cancel 后的心跳误显示为"还在跑"。`cancel_job()` 与 `EventSourceHandler` 协同关闭。**2026-06-06 `76bb1ff` 补完**：6-06 `23e0c4d` 虚标；同日 `76bb1ff` 真正实现 `inferenceStatusRef` 镜像 + SSE onmessage 入口 cancelled 早退。
  - **B3 后端模型状态对外可读**：`/api/health` 的 `model_state` 字段从内部变量提升为可被 GUI 状态栏读取的稳定 JSON 字段，包含 `status` / `checkpoint_sha256` / `mode` / `missing` 4 个 key。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护。**2026-06-06 真实完成**。
  - **B4 SSE 基础异常重试**：`createInferenceEventSource` 暴露 `onretry` / `retryCount` 字段；单次断连后自动退避重连（200ms→2s 指数退避，最多 3 次）。`tests/imagingLogic.test.ts` source-grep 守护。**2026-06-06 `76bb1ff` 补完**：6-06 `23e0c4d` 虚标；同日 `76bb1ff` 真正抽出 `src/inference/createInferenceEventSource.ts` 工具并接入。
  - **演示启动脚本化**：`tools/start_local_demo.py` 一行启动：自动 setenv（`SEGMENTATION_REFERENCE_CASES_JSON`、`SEGMENTATION_DEVICE` 等）、spawn backend（uvicorn）+ frontend（vite dev）、轮询 4 个端点（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）、失败时打印 runbook 回退命令。`docs/demo-day-checklist.md` 是配套的一屏卡片。
  - **server mode gating 6 路径修复**：`server/main.py:1537-1604 get_model_state(runtime_target)` 接受 `runtime_target` 参数；`runtime_target=server` 只检查 6 个 `SEGMENTATION_SERVER_*` 路径（`server_evaluate_full.py` / `server_dataset.json` / `server_nnunet_raw` / `server_nnunet_preprocessed` / `server_nnunet_results` / `server_output_root`）；`runtime_target=local` 才检查本地 4 文件（`dataset.json` / `plans.json` / `checkpoint_best.pth` / `nnUNetv2_python`）。两组检查互斥，server 模式创建 job 不再因本地 Windows nnUNet 文件缺失而 503。`tests/backendState.test.py` 新增 3 个守护测试（`test_server_runtime_ready_does_not_require_local_model_files` 扩 4 server 路径 / `test_server_runtime_reports_missing_server_paths` / `test_local_runtime_does_not_check_server_paths`）。Smoke test 2026-06-06 验证 4 端点全过。
  - **AMOS 0117 演示口径（2026-06-05 决策，6-06 落地）**：cache hit `aea4e7cdbaf0` 命中的是 2026-05-23 quality profile 真实推理 `009d4efdc5f6`（review 状态，stomach Dice 0.556、mean_dice 0.891），stomach 0.556 是数据本身硬骨头，复跑 quality 不会显著改善。决策：接受现状，不复跑 AMOS 0117；正式 AMOS 报告基线仍是 `b3c528cc9e20`（mean_dice 0.924780）。已写入 `docs/local-cache-demo-runbook.md`。
- **2026-06-05 HTML 报告临床报告风格重构（第二轮美化）**：`src/report/exportReport.ts` 从"卡片式仪表板"重塑为"临床评估报告"。新增 7 个 CSS 块：`.cover` 封面页（题图条 + 报告编号 + 主副标题 + 数据集/病例/生成时间三列）、`.exec-summary` 执行摘要（通过 / 关注点 / 建议三栏）、`.toc` 目录（§1-§8 锚点导航）、`.formula-tip` 公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、`.dist-chart` 严重度分布图（高/中/低 bar chart）、`.table-caption` 表格标题、`.footnotes` 脚注；新增 3 个工具函数 `distributionChartHtml()` / `severityBuckets()` / `formulaTips()`；正文模板按 §1 报告概览 / §2 摘要 / §3 数据集 / §4 器官 / §5 体素 / §6 距离 / §7 关键发现 / §8 附录 8 段章节编号排版；字体改为 Source Han Serif / Songti SC + JetBrains Mono；@media print 改为 A4 + 顶部 caseId + 底部 page X of Y。本轮不动 nnUNetv2 推理、缓存复用、SSE 协议、validation 字段或影像量化逻辑；与 2026-06-04 第一轮美化的所有功能（remap 警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条、aiFindings 严重度排序、器官列表折叠、列固定/排序）兼容并叠加。
- **2026-06-04 HTML 报告第一轮美化（视觉层 + 信息层）**：`src/report/exportReport.ts` 从"工程 dump"提升为"卡片式仪表板"。视觉层：色阶图例、Header 渐变、3 个 metric group 组标题图标、aiFindings 严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定 + 列点击排序、@media print A4 页眉页码。信息层：remap_applied 顶部警告条（`.remap-banner.remap-on` 黄底红字 / `.remap-banner.remap-off` 绿底）、taxonomy / dataset_hint 展示位、spacing 可视化（`.spacing-bar` 3 色块按 min=0.5mm / max=2.0mm 反向归一化）、historical 警告条（`.historical-banner` 灰底斜体）。`src/main.tsx:handleExport` 构造 `ReportData` 时透传 `validation.remap_applied` / `taxonomy_match` / `dataset_hint` / `historical` / `label_taxonomy`（已在 `src/inference/inferenceClient.ts:117-147 normalizeValidation` 白名单）。`tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class。
- **2026-06-03 质量评估指标扩展 + 表面距离计算加速**：把 quality 评估报告补齐到 Dice、IoU、Pixel Accuracy、Hausdorff Distance（含 HD95、ASD）等 6 类医学影像主流指标。`server/main.py` 新增 `surface_distances()`（1 crop + 2 EDT/label），把单 label 的 `distance_transform_edt` 调用从 6 次合并到 2 次；`src/inference/inferenceClient.ts` 在 `ValidationSummary` / `LabelMetric` 增补 12 个新字段（pixel_accuracy 4 项 + HD/HD95/ASD 9 项 + surface_distance_unit + spacing）；`src/report/exportReport.ts` 报告模板新增 3 个 metric group（区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD）和 4 个逐标签列（像素准确率、ASD (mm)、HD95 (mm)、HD (mm)）。AMOS 0117 quality 缓存命中：validation 阶段从 38.86s 降到 16.78s（约 2.3× 加速）。3 个新增回归测试覆盖新函数精度（1e-9）、EDT 调用计数恒为 2、wall-time 加速比 ≥30%。
- 显式 `label_taxonomy=auto|AMOS22|FLARE22` 功能，修复了 AMOS 标签被误判为 FLARE22 的问题
- **2026-06-02 detect_dataset 二轮收紧 + 前端按 dataset 预设 taxonomy**：AMOS 真实 label 只含 1-13（缺 14/15 bladder/prostate 体素），与 FLARE22 真实 1-13 在裸 ID 集合上不可分；`detect_dataset()` 在参考覆盖 ckpt 标签 ≥ 0.85 时直接返回 `None`（不再自动 remap），由前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy`（AMOS → AMOS22、FLARE22 → FLARE22），用户仍可在 UI 切换。`auto` 退化为保底。
- **2026-06-02 dataset_hint 字段打通 auto 边界**：`loadReferenceCase()` 成功载入参考标签后把 `referenceCase.dataset` 写入 `referenceCaseDatasetHint` 状态；创建 job 时通过新增 `dataset_hint` 表单字段提交给后端。后端 `validate_against_custom_label()` 在 `label_taxonomy=auto` 但 `dataset_hint=FLARE22` 时强制 remap（即便 `detect_dataset` 返回 `None`），保证 FLARE22_Tr_0009 这类参考病例在 `auto` 模式下也能正确 remap。
- AMOS CT 高分辨率在线推理（768×768×103，fast profile，mean_dice=0.77724）
- 服务器 5GPU/5-fold soft ensemble 校园网 smoke 已跑通
- 新部署包 `server-runtime-package-20260531.zip` 已创建
- **本地缓存演示 7 步**：AMOS 0117 cache hit（`aea4e7cdbaf0`，命中 `009d4efdc5f6`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）
- **2026-06-01 晚间 cache 链路补丁**：FLARE22 cache hit 正确显示历史 validation 摘要（0.893/0.674/0.950），不再混用 AMOS 数据。后端 `complete_cached_job()` 增加 historical 回退、`find_cached_prediction()` 优先有 `validation_summary.json` 的 cache_source；前端 `getValidationStatusCopy()` 区分"无历史验证摘要"和"（历史离线缓存摘要）"；新增 `tools/rewrite_flare22_historical_summary.py`。
- **新增脚本/文档**：`tools/seed_demo_cache.py`（幂等预热 AMOS cache hit）、`tools/rewrite_flare22_historical_summary.py`（按 2026-05-26 remap 后的 metrics 改写 0aa7323a4c01 的历史摘要）、`docs/local-cache-demo-runbook.md`（运行说明手册）、`docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`、`docs/superpowers/plans/2026-06-01-local-cache-demo.md`
- **后端依赖补充**：在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装了 `fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30`

当前进行中：

- 高分辨率 CT 推理优化评估（预降采样方案）
- 服务器 AMOS/FLARE 显式 taxonomy 复跑验证 `remap_applied` 状态（校园网服务器窗口；AMOS 0117 演示口径决策后已不再复跑 AMOS 0117，但仍需在新服务器上复跑确认 `remap_applied=false` 后纳入正式基线）
- 质量评估指标新口径推广：把 surface_distances 2 EDT 模式应用到后续 3D 模型评估和跨数据集验证
- 跨数据集 cache 链路产品化：把 `tools/rewrite_flare22_historical_summary.py` 重构为通用 `tools/rewrite_cached_validation_summary.py`，让其他数据集/其他 cache_source 也能享受 cache hit 显示历史 validation 摘要
- runbook 自动校验：写 `tests/cacheDemoRunbook.test.py` 自动确认 runbook 中 4 个已知约束仍在代码里成立
- 5-fold 提分策略：用 `nnUNetv2_ensemble -np 5` 拿全部 5 个 fold 的 softmax 概率图后取 mean，再做 argmax；当前服务器只跑 fold 0 单次，5-fold ensemble 预计 +2-3% Dice

## 项目结构与模块组织

本仓库是本地腹部 CT 分割 GUI 原型。前端使用 React + TypeScript + Vite，主要代码位于 `src/`：主应用在 `src/main.tsx`，三正交联动视图在 `src/components/OrthogonalViewer.tsx`，NIfTI 几何映射、切片渲染和影像量化在 `src/imaging/`，推理 API 封装在 `src/inference/`，报告导出在 `src/report/`。后端位于 `server/`，负责 nnUNetv2 job 编排、SSE 进度、预测缓存、validation、taxonomy remap、本地/服务器运行位置分流。测试位于 `tests/`，离线指标与性能工具位于 `tools/`。真实 CT、模型权重、私有 registry 和生成输出只能放在被忽略目录，例如 `nnunetv2_files/`、`.test-output/`、`server/work/`。

## 构建、测试与开发命令

常用命令从仓库根目录运行：

```powershell
npm install
npm run dev -- --port 5173
npm run dev:lan
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
npm test
npm run build
```

- `npm run dev` 默认只监听 `127.0.0.1`，适合本机开发。
- `npm run dev:lan` 监听 `0.0.0.0:5173`，用于局域网设备访问。
- 启动后端前先确认 Python 环境、nnUNetv2 和模型文件可用；在线推理前检查 `GET /api/health`。
- `npm test` 会运行前端逻辑、后端状态、指标、文档和浏览器布局测试。
- `npm run build` 会执行 TypeScript 检查并生成 Vite 生产构建。

## 局域网与运行位置配置

前端 API 地址通过 `VITE_API_ENDPOINT` 配置，未设置时回退 `http://127.0.0.1:8000`。局域网联调示例：

```powershell
$env:VITE_API_ENDPOINT='http://<后端机器IP>:8000'
npm run dev:lan
```

后端通过 `SEGMENTATION_ALLOWED_ORIGINS` 放行实际浏览器来源：

```powershell
$env:SEGMENTATION_ALLOWED_ORIGINS='http://<前端机器IP>:5173'
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

在线推理支持 `runtime_target=local|server`：

- `local`：本地 nnUNetv2 保底路径，适合开发调试和服务器不可用时使用。
- `server`：Linux 服务器 5-GPU / 5-fold soft ensemble 编排入口，已完成校园网端到端 smoke；FLARE 服务器轮次可作为链路证据，AMOS 服务器轮次因疑似 taxonomy 误判暂不作为质量基线。显式 `label_taxonomy` 已实现，后续复跑可避免误判。

## 编码风格与命名约定

优先使用 TypeScript。React 组件使用 PascalCase，函数、变量和 hook 使用 camelCase。坐标、成像、状态和推理事件等纯逻辑优先放到 `src/imaging/`、`src/inference/`、`src/viewerLogic.ts` 或其他可测试模块中，不要继续膨胀 `src/main.tsx`。后端 Python 保持当前项目风格，helper 要小而明确。文档主体使用中文；命令、API 字段、路径、profile、job id、Dice / IoU / HD 等技术字段可保留英文。

## 测试规范

为修改点添加聚焦测试：

- 前端纯逻辑：`tests/*.test.ts`
- job state、缓存、validation、taxonomy：`tests/backendState.test.py`
- 指标脚本：`tests/segmentationMetrics.test.py`
- 三视图或布局：`tests/layoutRegression.test.ts` 和 `npm run test:browser`

提交前优先运行：

```powershell
npm test
npm run build
git diff --check
```

无法运行时必须在交付说明中写明原因，不能宣称测试通过。

## 文档与验收口径

涉及推理质量、性能、缓存、taxonomy、影像量化、报告导出、局域网、服务器运行位置或验收证据的变更，应评估是否同步：

- `README.md`
- `ACCEPTANCE.md`
- `REVIEW.md`
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`
- `SEGMENTATION_METRICS_SUMMARY.md`
- `SEGMENTATION_RECENT_ROUNDS.md`
- `CODE_MODULE_GUIDE.md`
- `.planning/`

AMOS 原生验证、FLARE22 自动 remap 在线验证、FLARE22 离线 remap 对照、fast preview、cached result、本地 fold0 和服务器 5-fold ensemble 必须分开表述，不能混成同一类证据。`cached-real-nnunetv2` 只表示预测 NIfTI 复用，validation 仍绑定当前请求标签文件或内置参考标签。2026-05-31 服务器 smoke 已跑通后，后续文档不得继续写成”服务器端到端待 smoke”；但服务器 AMOS 指标必须等显式 `label_taxonomy=AMOS22` 复跑并确认 `remap_applied=false` 后，才能纳入正式质量基线。显式 `label_taxonomy` 功能已实现。`detect_dataset()` 在 2026-06-02 进一步收紧：参考标签覆盖 ckpt 标签 ≥ 0.85 时返回 `None`（避免 AMOS 1-13 真实数据被错判为 FLARE22）。正式 taxonomy 选择由前端 `loadReferenceCase()` 按 `referenceCase.dataset` 字段预设（AMOS → AMOS22，FLARE22 → FLARE22）；`auto` 模式仅作保底策略。2026-06-01 本地缓存演示新增的 AMOS 0117 cache hit 命中的是 2026-05-23 历史推理 `009d4efdc5f6`（review，stomach 0.556），与本地 quality AMOS 真实推理 `b3c528cc9e20`（mean_dice 0.924780）必须分开记录；该 cache hit 是工程链路演示，不替代正式质量基线。

## 提交与 PR 规范

提交信息沿用现有风格：`feat: ...`、`fix: ...`、`docs: ...`。PR 说明应包含变更范围、验证命令、用户可见影响、是否影响推理指标或缓存语义、是否涉及真实数据。UI、三正交视图或报告导出变更建议附截图或明确手工验证路径。

## 安全与配置边界

不要提交真实 CT/NIfTI、checkpoint、私有 registry、`.env`、日志或生成推理输出。局域网和穿透场景不要长期使用无限制 CORS 或裸露未授权公网后端端口。医学影像访问优先考虑局域网、Tailscale 或 WireGuard；只有必须提供普通公网浏览器入口时再评估 frp + HTTPS，并配置鉴权、HTTPS、大文件上传限制和 SSE 反代参数。
