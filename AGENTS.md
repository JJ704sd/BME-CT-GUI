# Repository Guidelines

## 项目结构与模块组织

- `src/`：前端 React + TypeScript 代码。`src/main.tsx` 负责页面状态和流程编排，`src/components/OrthogonalViewer.tsx` 负责三正交视图，`src/imaging/` 放 NIfTI 映射与切片渲染逻辑。
- `server/`：FastAPI 后端，桥接本机 nnUNetv2、任务状态、SSE 事件和结果下载。
- `tests/`：Node、Python 与 Playwright 盒模型测试。
- `tools/`：性能和指标脚本，例如 `segmentation_metrics_summary.py`。
- `public/`、`src/assets/`：前端静态资源。`nnunetv2_files/`、`.test-output/`、`server/work/` 是本地数据/输出目录，不进入提交。

## 构建、测试与本地运行

```powershell
npm install
npm run dev -- --port 5173

# 后端（默认 quality 模式，GPU 推理）
SEGMENTATION_DEVICE=cuda SEGMENTATION_INFERENCE_PROFILE=quality python -m uvicorn server.main:app --host 127.0.0.1 --port 8000

npm test
npm run build
```

- `npm run dev` 启动前端（端口 5173）。
- `uvicorn` 启动后端 API（端口 8000），健康检查：`GET /api/health`。
- `npm test` 运行前端逻辑、文档、后端状态、指标和浏览器布局测试。
- `npm run build` 执行 TypeScript 检查并生成 Vite 生产构建。

### 关键环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `SEGMENTATION_DEVICE` | `cuda` | 推理设备：`cuda` / `cpu` / `mps` |
| `SEGMENTATION_INFERENCE_PROFILE` | `quality` | `quality`（TTA 开）用于正式报告；`fast`（TTA 关）仅作预览 |
| `SEGMENTATION_PREPROCESS_WORKERS` | `2` | 预处理线程数 |
| `SEGMENTATION_EXPORT_WORKERS` | `2` | 导出线程数 |
| `CUDA_VISIBLE_DEVICES` | — | 多卡服务器选择 GPU |

### 推理模式说明

- **quality**（默认）：保留 TTA/mirroring，tile_step_size=0.5，适合正式结果。
- **fast**：关闭 TTA，tile_step_size=1.0，速度快但质量下降，需人工复核。

## 关键 API 端点

| 端点 | 用途 |
|------|------|
| `GET /api/health` | 后端状态、模型就绪情况、推理配置 |
| `GET /api/samples` | 参考病例列表 |
| `POST /api/segment/jobs` | 创建推理任务（表单：`file`, `inference_profile`, 可选 `label_file`） |
| `GET /api/segment/jobs/{id}/events` | SSE 推理进度（progress/complete/error/heartbeat） |
| `GET /api/segment/jobs/{id}/result` | 下载结果 NIfTI |

## 推理数据流

1. 前端 `createInferenceJob()` → POST `/api/segment/jobs`
2. 后端创建 Job → 后台线程执行 nnUNetv2 推理
3. 前端 `EventSource` 监听 SSE → 实时更新底部进度
4. 推理完成 → 前端下载 NIfTI → 回填三正交视图

## 编码风格与命名约定

- TypeScript 使用 2 空格缩进，React 组件使用 PascalCase，函数和变量使用 camelCase。
- Python 后端使用 2 空格缩进，保持现有 `server/main.py` 风格。
- 优先复用现有工具函数，例如 `viewerLogic.ts`、`sliceRenderer.ts`，避免在组件中重复实现成像逻辑。
- 文档主体说明使用中文；医学、API、文件名和命令可保留英文原名。

## 测试规范

- 新增前端逻辑时补充 `tests/*.test.ts`。
- 后端任务状态或缓存逻辑变更时补充 `tests/backendState.test.py`。
- 指标脚本变更时补充 `tests/segmentationMetrics.test.py`。
- 布局、分屏、三视图交互变更需确认 `npm run test:browser`。

## 提交与 Pull Request 规范

- 提交信息沿用现有格式：`feat: ...`、`fix: ...`、`docs: ...`、`merge ...`。
- PR 说明应包含变更范围、验证命令、是否影响推理指标、是否涉及真实数据。
- UI 或三正交视图变更建议附截图或说明观察路径。

## 安全与配置边界

- 不提交真实 CT、NIfTI、checkpoint、推理输出或私有 registry（见 `.gitignore`）。
- 本地病例通过 `SEGMENTATION_REFERENCE_CASES_JSON` 指向被忽略的 JSON。
- 跨数据集标签验证：后端 `server/taxonomy.py` 自动检测 FLARE22 等数据集并按器官名重映射标签 ID，validation 结果中 `remap_applied: true` 表示已自动重映射。

## Linux 部署注意

- `server/main.py:43-44` 的 Windows 路径（`Scripts/*.exe`）需改为 Linux 路径（`bin/*`），或使用跨平台方案（见 CLAUDE.md）。
- Linux 上需确保 `nnunet_env/bin/` 下可执行文件有执行权限：`chmod +x nnunet_env/bin/nnUNetv2_predict_from_modelfolder`。
- 多卡部署使用 `CUDA_VISIBLE_DEVICES` 选择 GPU，可启动多个实例做负载均衡。
