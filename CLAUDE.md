# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

本仓库是腹部 CT 多器官分割 GUI 原型 — React + TypeScript + Vite 前端，FastAPI + nnUNetv2 后端。目标作品：中国生物医学工程竞赛「呼吸-消化系统疾病」赛道。

## 关键不变量（必读）

这一节是该仓库最容易与其他项目混的反直觉事实，动手前先看完。

- **在线推理有两条运行位置**：`runtime_target=local`（开发保底）和 `runtime_target=server`（Linux 5-GPU / 5-fold soft ensemble）。`server` 创建 job 时只依赖 `SEGMENTATION_SERVER_*` env vars，**不应**被本地 Windows nnUNet 文件缺失阻断。
- **跨数据集标签语义由 `label_taxonomy` + `dataset_hint` 共同控制**：
  - `label_taxonomy ∈ {auto, AMOS22, FLARE22}` 是用户显式选项
  - `dataset_hint` 由前端 `loadReferenceCase()` 从 `referenceCase.dataset` 自动写入并随 job 提交（用户不直接改）
  - 后端优先级：`taxonomy_hint > dataset_hint > detect_dataset()`。`auto + dataset_hint=FLARE22` 强制 remap；上传自定义 NIfTI 时 `dataset_hint` 自动清空
  - **不要**把"AMOS / FLARE22 真实 unique IDs 不可分 → 误 remap"写成模型失败基线。这是 taxonomy 错位，已通过 `detect_dataset()` coverage 守卫 + `dataset_hint` 字段收口
- **预测缓存 ≠ validation 缓存**：`cached-real-nnunetv2` 只复用 NIfTI 预测结果，validation 按当前请求标签重算。cache_key 7 字段（与 `server/main.py:1880 build_prediction_cache_key()` 实际实现保持一致）：`input_sha256 + checkpoint_sha256 + checkpoint_dataset_name + checkpoint_configuration + labels_source + runtime_target + inference_options`，缺一不可。**`label_taxonomy` / `dataset_hint` 不在 cache_key 中**——它们只影响 validation 阶段的标签解释，不影响 NIfTI 预测结果；同一 CT 切换 taxonomy 仍会命中同一 cache slot，只是重算 validation
- **`quality` 是正式报告路径**，`fast` 仅作预览 / 演示候选（本地 AMOS 0117 fast mean Dice=0.777，对 label 14/15 有假阳性）
- **本地缓存演示前置**：`SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json`（4 例模板：AMOS 0117 / FLARE22 Tr 0009 / WORD 占位 / AbdomenCT-1K 占位），否则 `/api/samples` 只返回内置 `amos_0117`，FLARE22 Tr 0009 不会出现
- **AMOS 服务器轮次 0.076 不是模型失败基线**：是 AMOS 原生标签被自动误 remap 到 FLARE22，已在 auto taxonomy 边界加固中收口，待服务器窗口复跑确认 `remap_applied=false` 后才能纳入正式质量基线
- **质量评估口径以 6 类医学影像指标为准**：`mean_dice` / `min_dice` / `foreground_dice`、`mean_iou` / `min_iou` / `foreground_iou`、`pixel_accuracy` / `mean_pixel_accuracy` / `min_pixel_accuracy` / `foreground_pixel_accuracy`、`mean_hd` / `max_hd` / `foreground_hd`、`mean_hd95` / `max_hd95` / `foreground_hd95`、`mean_asd` / `max_asd` / `foreground_asd`，加 `surface_distance_unit="mm"` 和 `spacing=[sx, sy, sz]`。逐标签还有 `pixel_accuracy` / `asd` / `hd` / `hd95` 4 列。`tools/segmentation_metrics_summary.py` 的离线口径与 `server/main.py` 在线 validation 共用同一份 `surface_distances()` 实现；新增指标时必须同时改 backend（计算 + serialize）、`inferenceClient.ts`（白名单 + 类型）、`exportReport.ts`（HTML 报告模板）三处，不要只改一处
- **`surface_distances()` 2 EDT 是单 label 性能不变量**：每个 label 在 1 次 crop + 2 次 `distance_transform_edt`（预测→参考、参考→预测）后用 value 数组派生 `asd` / `hd` / `hd95`。新写 `compute_*_metrics` 时不应回退到 6 EDT 模式；旧 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 仅保留供回归测试对照，不再走主路径。AMOS 0117 quality cache hit validation 实测 38.86s → 16.78s（约 2.3× 加速）
- **AGENTS.md 是只读 agent 指令文件**：自动权限会拒绝直接覆盖；如需统一中文主体、修订编码风格或调整 PR 规范，必须**先取得用户单独授权**。CLAUDE.md 与 AGENTS.md 的分工：CLAUDE.md 放本仓库特定的非显然事实，AGENTS.md 放跨项目共享的工作流规范

## 安全 / 隐私边界（必读）

不提交真实 CT / NIfTI / checkpoint / 私有 registry / `.env` / 日志 / 推理输出。`.gitignore` 屏蔽 `nnunetv2_files/`、`server/work/`、`*.nii`、`*.nii.gz`、`*.pth`。局域网和远程优先 LAN / Tailscale / WireGuard；公网入口必须鉴权 + HTTPS + 大文件上传限制 + SSE 反代参数，不要长期开放未授权 CORS 或裸露后端端口。

## 常用命令

```bash
# 前端
npm install
npm run dev                 # 127.0.0.1:5173
npm run dev:lan             # 0.0.0.0:5173 局域网
npm run build               # tsc + vite build
npm run preview

# 后端（先激活 D:\BME2026\BME_CT_Seg\nnunet_env）
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000

# 测试
npm test                                                    # 全跑（node + python + playwright）
node tests/<name>.test.ts                                   # 单个 .ts（viewerLogic / imagingLogic / quantification / acceptanceDocs / perfTool / layoutRegression / browserLayout 等）
python tests/<name>.test.py                                 # 单个 .py（backendState / segmentationMetrics）

# 离线指标
python tools/segmentation_metrics_summary.py --prediction <p.nii.gz> --reference <r.nii.gz> --checkpoint checkpoint_best.pth --labels-json validation_summary.json --sample-id <id> --output-dir <dir> --stem <name>
```

Python venv 在 `D:\BME2026\BME_CT_Seg\nnunet_env`（fastapi / uvicorn / python-multipart / numpy / nibabel 已装）。`npm test` 的完整套件顺序与单测名见 `package.json` 的 `scripts.test`。

## 架构（高层）

**前端 `src/`**：
- `main.tsx` — 主界面编排（大文件，新可测试逻辑优先下沉到独立模块）
- `components/OrthogonalViewer.tsx` — Axial / Sagittal / Coronal 联动 + mask 叠加 + 器官拾取
- `imaging/voxelMapping.ts` — 纯几何 / 坐标模块，体素-切片-屏幕映射。改动配 `tests/imagingLogic.test.ts`
- `imaging/sliceRenderer.ts` — NIfTI 切片 → data URL 渲染
- `imaging/quantification.ts` — 纯前端 CPU 量化（体积、截面积、包围盒等）
- `inference/inferenceClient.ts` — 与 FastAPI 通信：创建 job、SSE、下载 NIfTI、规范化 `/api/models` label 表、白名单 + 透传 6 类验证指标
- `report/exportReport.ts` — HTML / JSON（`schema_version 1.1`，含 `quantification`）/ PDF；3 个 metric group（Dice/IoU、Pixel Accuracy、HD/HD95/ASD）+ 4 列逐标签
- `data/organDetails.ts` — 15 器官 label / 颜色 / 中英文说明
- `viewerLogic.ts` / `organLayerLogic.ts` / `referenceCases.ts` — 主界面可拆出的纯 UI 逻辑

**后端 `server/`**：
- `main.py` — FastAPI 主入口，job 生命周期 / SSE / 取消 / 缓存 / validation（含 `surface_distances()` 2 EDT）/ 结果下载
- `taxonomy.py` — 跨数据集标签检测 + 自动 remap（核心：`detect_dataset()` 0.85 守卫、`validate_against_custom_label()`）
- `server_inference.py` — 服务器 5-GPU / 5-fold 编排
- `persistent_nnunet_worker.py` — 常驻 worker 实验路径

**测试 `tests/`**：`.test.ts` 直接用 `node:assert`，不依赖 jest/vitest runner；`.test.py` 用 stdlib unittest；`browserLayout.test.ts` 用 playwright。

**部署与设计材料**：
- `deployment-packages/server-runtime-package-20260531.zip` — Ubuntu 服务器最小后端更新包（不含真实数据），配套 `server-runtime-quickstart-20260531.md`
- `docs/superpowers/specs/<date>-<topic>-design.md` 与 `docs/superpowers/plans/<date>-<topic>.md` — 重大变更的设计 / 实施计划
- `docs/competition/BME_COMPETITION_GUIDE.md` — 竞赛报告写作指南（关键发现、组织形式、禁词）
- `docs/local-cache-demo-runbook.md` — 本地缓存演示 7 步复跑手册

## 文档协作（变更同步清单）

涉及推理质量 / 缓存 / taxonomy / 量化 / 报告 / 局域网 / 服务器 runtime / 验收的改动，**必须**评估是否同步：

- `README.md` — 入口与状态
- `ACCEPTANCE.md` — 验收口径
- `REVIEW.md` — 完整 review
- `SEGMENTATION_EXPERIMENT_COMPARISON.md` / `SEGMENTATION_METRICS_SUMMARY.md` / `SEGMENTATION_RECENT_ROUNDS.md` — 实验 / 指标 / 轮次
- `CODE_MODULE_GUIDE.md` — 模块讲解材料
- `docs/local-cache-demo-runbook.md` — 缓存演示复跑
- `docs/competition/BME_COMPETITION_GUIDE.md` — 报告写作指南
- `.planning/<topic>/{explanation,findings,progress,task_plan}.md` — 当前主题的 planning 4 文档

涉及质量评估指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD）字段新增或计算路径变更，**还**必须评估是否同步：

- `src/inference/inferenceClient.ts` 的 `ValidationSummary` / `LabelMetric` 白名单与类型定义
- `src/report/exportReport.ts` 的 HTML 报告 metric group 与逐标签列
- `tools/segmentation_metrics_summary.py` 的离线指标（必须与后端在线口径一致）
- `tests/backendState.test.py` 验证新字段在 SSE / job state / cached 链路里被透传
- `tests/imagingLogic.test.ts` 验证前端能解析新字段

## 当前重点

读 `SEGMENTATION_RECENT_ROUNDS.md` 顶部拿当前活跃 `.planning/` 主题。**不要**假设本文件或 README 的"当前状态"节是新鲜的——它们会在一周内过时；先看 `SEGMENTATION_RECENT_ROUNDS.md`。

## 其他约定

编码风格 / 命名 / 提交 / PR / 测试规范等常规约定 → 见 `AGENTS.md`，不要在 CLAUDE.md 重复维护。
