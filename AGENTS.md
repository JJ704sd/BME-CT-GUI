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
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
npm test
npm run build
```

- `npm run dev` 启动前端。
- `uvicorn` 启动后端 API。
- `npm test` 运行前端逻辑、文档、后端状态、指标和浏览器布局测试。
- `npm run build` 执行 TypeScript 检查并生成 Vite 生产构建。

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

- 不提交真实 CT、NIfTI、checkpoint、推理输出或私有 registry。
- 本地病例通过 `SEGMENTATION_REFERENCE_CASES_JSON` 指向被忽略的 JSON。
- FLARE22 标签与当前 AMOS22 checkpoint 标签体系不同，只能做人工复核或离线 remap 对照。
