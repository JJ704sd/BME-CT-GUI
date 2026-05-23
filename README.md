# BME CT Segmentation GUI Prototype

本项目是一个面向腹部 CT 分割验证流程的本地 GUI 原型。前端使用 React + Vite，后端使用 FastAPI 桥接本机 nnUNetv2 推理环境，目标是完成 CT 浏览、三正交联动、分割结果叠加、器官标签说明和真实模型推理回填。

## 当前状态

- 前端入口：`http://127.0.0.1:5173`
- 后端健康检查：`http://127.0.0.1:8000/api/health`
- 当前后端模式：`real-nnunetv2`
- 当前验证设备：CUDA，可通过 `SEGMENTATION_DEVICE=cuda` 指定
- 主要进展记录见 [REVIEW.md](./REVIEW.md)

## 主要功能

- 支持 `.nii` / `.nii.gz` CT 体数据读取和浏览。
- 支持 Axial、Sagittal、Coronal 三正交视图联动。
- 支持窗宽窗位、切片切换、缩放、叠加透明度调节。
- 支持分割结果与原图的 `overlay`、`split`、`side`、`difference` 对比。
- 支持点击非背景 label 后显示对应器官说明。
- 支持本地 nnUNetv2 在线推理任务创建、SSE 进度、结果下载和 GUI 回填。
- 支持 AMOS 样例标准答案验证，输出 per-label Dice、平均 Dice、最低 Dice 和前景 Dice。
- 支持作业摘要持久化：耗时、结果大小、验证摘要、历史 job 回读。
- 支持 nnUNetv2 子进程日志持久化，失败时显示尾部日志，便于定位 CUDA OOM、输入格式或模型路径问题。

## 参考 CT 推理结果

已使用本地参考 CT 完成一次真实 CUDA 推理：

- 输入：`nnunetv2_files/amos_0117(3).nii.gz`
- 标准答案：`nnunetv2_files/amos_0117(2).nii.gz`
- 权重：`nnunetv2_files/checkpoint_best.pth`
- job id：`009d4efdc5f6`
- 推理耗时：`385.321 秒`，约 `6 分 25 秒`
- 输出：`server/work/009d4efdc5f6/output/009d4efdc5f6.nii.gz`
- 结果大小：`141460 bytes`
- 结果状态：`succeeded`

标准答案验证结果：

| 指标 | 数值 |
|---|---:|
| mean_dice | 0.891327 |
| foreground_dice | 0.971222 |
| min_dice | 0.555985 |
| 状态 | review |

当前样例没有完全自动通过验收，主要原因是胃的 Dice 为 `0.555985`，低于最低 label Dice 阈值 `0.70`。界面和文档均应保留“建议人工复核”的结论。

## 三大目标进度

| 目标 | 当前完成度 | 说明 |
|---|---:|---|
| CT 浏览、三正交联动 | 约 95% | 三视图联动、侧向视图放大、点击留白过滤、底部切片栏稳定窗口已完成并有回归测试。 |
| 器官 label 点击与说明 | 约 90% | AMOS 标签与前端器官说明已对齐，仍需最终确认训练集标签集合是否固定。 |
| 本地 nnUNetv2 推理与结果回填 | 约 89% | CUDA 推理跑通，结果可回填/下载/覆盖对比，已补耗时、结果大小、历史 job 回读和失败日志。 |

## 本地运行

安装前端依赖：

```powershell
npm install
```

启动前端：

```powershell
npm run dev -- --port 5173
```

启动后端：

```powershell
$env:SEGMENTATION_DEVICE='cuda'
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

后端依赖见：

```text
server/requirements.txt
```

## 模型和样例文件

模型权重、真实 CT 和推理输出不建议提交到 GitHub。当前 `.gitignore` 已排除：

- `nnunetv2_files/`
- `server/work/`
- `*.nii`
- `*.nii.gz`
- `*.pth`

本地运行真实推理时，需要自行准备：

```text
nnunetv2_files/checkpoint_best.pth
nnunetv2_files/amos_0117(3).nii.gz
nnunetv2_files/amos_0117(2).nii.gz
```

## API 概览

- `GET /api/health`：后端和模型状态。
- `GET /api/models`：模型与 label 表。
- `GET /api/samples`：本地样例文件状态。
- `POST /api/segment/jobs`：创建 nnUNetv2 推理任务。
- `GET /api/segment/jobs/{job_id}`：查询任务状态、耗时、结果大小和验证摘要。
- `GET /api/segment/jobs/{job_id}/events`：SSE 推理进度。
- `GET /api/segment/jobs/{job_id}/result`：下载结果 NIfTI。

## 验证命令

```powershell
npm test
npm run build
```

后端测试会在 `.test-output/` 下生成临时模型和作业文件，不需要提交真实 CT、`checkpoint_best.pth` 或其它训练权重。

在受限 shell 中，Vite 或 Playwright 可能因为 Windows 子进程创建被拦截而出现 `spawn EPERM`。正常权限下验证通过；如果在浏览器 overlay 中看到该错误，应重启 Vite 到正常权限环境，而不是修改业务代码。

## 当前限制

- `confidenceThreshold` 目前是质控提示，不会真实作用于多标签概率图。
- 轻量 3D 预览不是医学级体渲染工作台。
- 已完成单样例 CUDA 推理验证，仍需要更多病例的压力测试、取消/重试机制和资源监控。
- AMOS 样例结果处于 `review`，不能表述为模型效果完全达标。
