# CLAUDE.md

本文件为 Claude Code 在本仓库工作时的操作指南。

## 项目概述

本仓库是腹部 CT 分割 GUI 原型。前端使用 React + TypeScript + Vite，后端使用 FastAPI + Python + nnUNetv2。当前在线推理支持两条运行位置：

- `local`：本地在线推理，作为开发调试和保底路径。
- `server`：服务器云端推理，走 Linux 服务器 5-GPU / 5-fold soft ensemble 编排；2026-05-31 已完成校园网端到端 smoke，但 AMOS validation 仍需显式 taxonomy 复跑确认。

前端通过 `VITE_API_ENDPOINT` 指向后端；后端通过 `SEGMENTATION_ALLOWED_ORIGINS` 放行实际浏览器来源。

## 常用命令

```bash
# 前端开发
npm run dev
npm run dev:lan
npm run build
npm run preview

# 后端开发
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# 测试
npm test
python tests/backendState.test.py
python tests/segmentationMetrics.test.py
node tests/viewerLogic.test.ts
node tests/imagingLogic.test.ts

# 指标
python tools/segmentation_metrics_summary.py --prediction <pred.nii.gz> --reference <ref.nii.gz> --checkpoint <checkpoint_best.pth> --labels-json <validation_summary.json> --sample-id <id> --output-dir <dir> --stem <name>
```

## 代码结构

### 前端 `src/`

- `main.tsx`：主界面编排，负责病例、三视图、在线推理、运行位置、标签上传、报告导出。
- `components/OrthogonalViewer.tsx`：三正交视图联动。
- `imaging/voxelMapping.ts`：体素与切片坐标映射。
- `imaging/sliceRenderer.ts`：NIfTI 切片渲染与缓存。
- `inference/inferenceClient.ts`：创建 job、监听 SSE、下载结果，提交 `runtime_target` 和 `inference_profile`。
- `report/exportReport.ts`：HTML / JSON / PDF 报告导出。
- `data/organDetails.ts`：器官标签、颜色、中文说明。

### 后端 `server/`

- `main.py`：FastAPI 主入口，负责 job 生命周期、SSE、取消、缓存、validation、结果下载。
- `taxonomy.py`：跨数据集标签检测与自动 remap。
- `server_inference.py`：服务器推理编排，负责 5-fold 命令、GPU / fold 映射、ensemble 和评估命令。
- `persistent_nnunet_worker.py`：常驻 worker 路径。

## 运行位置与推理语义

### local

- 适合开发、调试、服务器不可用时 fallback。
- 继续保留现有本地 nnUNetv2 路径。

### server

- 适合正式推理候选路径、服务器部署和远程验收。
- 走 Linux 服务器 5 个 fold 并行推理，再做 soft ensemble。
- 校园网端到端 smoke 已跑通：Windows 前端可调用 Ubuntu FastAPI 后端，完成 5-fold 推理、soft ensemble、结果下载和 GUI 回填。
- FLARE 服务器轮次在 remap 后可作为链路证据；AMOS 服务器轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808` 且 `remap_source=FLARE22`，更像 taxonomy 误判，不得写成模型失败基线。
- 迁移到云服务器时，必须保证 `SEGMENTATION_SERVER_*` 环境变量完整，尤其是 GPU / fold 映射、nnUNet 目录、输出目录和评估脚本。

## 重要约束

- 不提交真实 CT、NIfTI、checkpoint、推理输出、私有 registry、`.env` 或日志。
- 局域网和远程访问优先使用 LAN / Tailscale / WireGuard；只有必须提供普通公网浏览器入口时才考虑 frp + HTTPS。
- 公网入口必须配置鉴权、HTTPS、大文件上传限制和 SSE 反代参数，不裸露未授权后端端口。
- 缓存只复用预测 NIfTI，不复用旧 job 的 validation 结果；`runtime_target` 必须进入缓存 key。
- `quality` 是正式报告路径，`fast` 仅作预览。
- 自动 taxonomy remap 解决 FLARE22 → AMOS22 在线验证，但 AMOS 原生标签不能只靠自动检测；下一轮优先实现 `label_taxonomy=auto|AMOS22|FLARE22`。
- `runtime_target=server` 创建 job 时应只依赖 server runtime 配置，不应被本地 Windows nnUNet 文件缺失阻断。

## 测试与验收

提交前优先确认：

```bash
npm test
npm run build
git diff --check
```

若涉及服务器迁移，还要验证：

- `/api/health`
- `/api/models`
- 上传 CT
- 创建 job
- SSE 进度与心跳
- 取消任务
- 结果下载
- 标签 validation / remap
- 5 个 fold 是否按预期跑在对应 GPU 上

## 文档协作

涉及局域网、服务器运行位置、验证口径或迁移策略的改动，要同步检查：

- `README.md`
- `ACCEPTANCE.md`
- `REVIEW.md`
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`
- `SEGMENTATION_METRICS_SUMMARY.md`
- `SEGMENTATION_RECENT_ROUNDS.md`
- `CODE_MODULE_GUIDE.md`
- `.planning/`

当前下一轮工程入口是 `.planning/label-taxonomy-server-validation/`：先补显式标签体系 hint 和 server mode gating，再复跑 AMOS/FLARE 服务器 validation。

## 云服务器迁移注意

后端迁移到云服务器时，优先按下面顺序推进：

1. 先把服务器上的 CUDA、PyTorch、nnUNetv2、模型权重和数据目录准备齐。
2. 通过 `SEGMENTATION_SERVER_*` 配好 dataset、plans、fold、GPU、输出和评估路径。
3. 前端先走 `VITE_API_ENDPOINT` 指向云服务器或 VPN / Mesh 虚拟 IP。
4. 后端只放行可信前端来源，避免使用无限制 CORS。
5. 先做 LAN / VPN / Mesh smoke test，再考虑公网入口。
6. 迁移验收必须覆盖上传、SSE、取消、下载、标签 validation 和结果回填，不只看 health。
