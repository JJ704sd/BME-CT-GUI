# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 项目概述

智能 CT 器官分割工作站 — 基于 nnUNetv2 的腹部 CT 器官分割 GUI。前端 React + TypeScript + Vite（端口 5173），后端 FastAPI + Python（端口 8000）。当前 checkpoint 为 AMOS22 `Dataset001_AMOS22`，15 个前景标签。

## 常用命令

```bash
# 前端开发
npm run dev                    # Vite dev server, http://127.0.0.1:5173
npm run build                  # tsc + vite build (生产构建前必须通过)
npm run preview                # 预览生产构建

# 后端开发
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
# 环境变量（可选）：
#   SEGMENTATION_DEVICE=cuda|cpu
#   SEGMENTATION_PERSISTENT_WORKER=1
#   SEGMENTATION_PREPROCESS_WORKERS=2
#   SEGMENTATION_EXPORT_WORKERS=2
#   SEGMENTATION_INFERENCE_PROFILE=quality|fast
#   SEGMENTATION_REFERENCE_CASES_JSON=<path-to-reference-cases.json>

# 测试（全部顺序执行，前端 + 后端 + 浏览器布局）
npm test

# 单独运行某个测试
node tests/viewerLogic.test.ts
node tests/imagingLogic.test.ts
python tests/backendState.test.py
python tests/segmentationMetrics.test.py

# 离线指标计算
python tools/segmentation_metrics_summary.py --prediction <pred.nii.gz> --reference <ref.nii.gz> --checkpoint <checkpoint_best.pth> --labels-json <validation_summary.json> --sample-id <id> --output-dir <dir> --stem <name>
```

## 架构

### 前端（`src/`）

- **`main.tsx`**（~2000 行）：主容器，管理全局 UI 状态、NIfTI 解析、参考病例、在线推理、底部实时进度。产品流程编排中心。
- **`components/OrthogonalViewer.tsx`**：Axial/Sagittal/Coronal 三正交视图。使用 `requestAnimationFrame` 合并高频拖动渲染，`interactive`/`full` 两种切片质量模式。
- **`imaging/voxelMapping.ts`**：纯函数 — 体素坐标 ↔ 切片坐标映射、十字线位置计算、contain 布局下的鼠标偏移修正。
- **`imaging/sliceRenderer.ts`**：NIfTI 切片 → canvas → data URL 渲染。WeakMap 做 volume 级缓存，`interactive` 模式用于拖动实时预览。
- **`inference/inferenceClient.ts`**：封装 `/api/segment/jobs` 的创建、SSE 监听、结果下载。`parseInferenceEvent()` 解析 progress/complete/error/heartbeat 事件。
- **`data/organDetails.ts`**：13 个器官的 label、颜色、中文名、说明文案。
- **`organLayerLogic.ts`**：label 列表 → UI 器官层，合并 validation 分数。
- **`referenceCases.ts`**：归一化 `/api/samples` 返回值。
- **`viewerLogic.ts`**：纯 UI 逻辑 — 坐标去重、拖动提交合并、切片同步方向判断。

### 后端（`server/`）

- **`main.py`**（~1700 行）：FastAPI 主文件。Job 生命周期管理、nnUNetv2 推理调度、SSE 事件推送、结果缓存、validation、资源快照、heartbeat。
- **`persistent_nnunet_worker.py`**：常驻 nnUNet predictor worker，通过 stdin/stdout JSON 协议通信。

### 关键数据流

1. 前端 `startSegmentation()` → `createInferenceJob()` POST `/api/segment/jobs`
2. 后端创建 Job → 后台线程执行推理（`run_real_job`）
3. 前端 `EventSource` 监听 `/api/segment/jobs/{id}/events` SSE
4. 推理完成 → 前端 `downloadInferenceResult()` → `parseNiftiVolume()` → 回填三视图

### 两条推理路径

- **非持久**：`subprocess.Popen` + `communicate(timeout=0.5)` 轮询，支持取消和心跳
- **持久 worker**：`persistent_nnunet_worker.py` 通过 stdin 接收请求、stdout 返回 JSON，使用 `queue.Queue` + 读取线程实现非阻塞心跳

### 缓存机制

相同输入 SHA256 + checkpoint SHA256 + inference options → `cached-real-nnunetv2` 模式，直接返回历史结果。cache key 由 `build_prediction_cache_key()` 生成。

## 测试结构

| 文件 | 覆盖范围 | 运行方式 |
|---|---|---|
| `tests/viewerLogic.test.ts` | 纯 UI 逻辑函数 | `node` |
| `tests/imagingLogic.test.ts` | 坐标映射、切片 key、器官 label、SSE 事件解析、heartbeat、E2E 事件序列 | `node` |
| `tests/acceptanceDocs.test.ts` | 验收文档存在性和关键内容 | `node` |
| `tests/perfTool.test.ts` | 性能工具 dry-run | `node` |
| `tests/layoutRegression.test.ts` | 布局回归约束 | `node` |
| `tests/browserLayout.test.ts` | Playwright 浏览器布局（需 `npx playwright install`） | `node` |
| `tests/backendState.test.py` | Job 状态、缓存、registry、validation、heartbeat、E2E API 流程 | `python` |
| `tests/segmentationMetrics.test.py` | 指标脚本输出 | `python` |

前端测试用 `node:assert/strict`，不依赖 Jest/Vitest。后端测试用 `unittest.mock.patch` + FastAPI `TestClient`。

## 重要约束

- **不提交真实数据**：`nnunetv2_files/`、`.test-output/`、`server/work/`、`*.nii`、`*.nii.gz`、`*.pth` 均在 `.gitignore` 中。
- **Windows 平台**：`select.select()` 不适用于 subprocess pipe，持久 worker 心跳使用 `queue.Queue` + 线程实现。
- **前端 monolith**：`main.tsx` 约 2000 行，承载产品流程编排。底层成像逻辑已拆分到 `imaging/`、`inference/`、`viewerLogic.ts`，不应再往 `main.tsx` 塞底层逻辑。
- **三视图联动核心**：`voxelCoord` 状态驱动三个方向。`selectedSlice` 主要服务 axial 预览和滑条。拖动时 `scheduleVoxelCoordChange()` 合并到每帧一次。
- **推理 profile**：`quality`（默认，TTA 开）用于正式报告；`fast`（TTA 关）仅作预览，必须标注"需人工复核"。
- **Label taxonomy**：AMOS22 checkpoint 的 label ID 顺序与 FLARE22 不同。跨数据集指标必须用离线 remap，不能混入 AMOS 原生验证。
- **心跳机制**：`push_heartbeat()` 全部异常隔离，失败不影响推理。前端心跳事件只更新耗时，不污染 timeline。
