# 服务器在线推理最短操作清单

**适用包：** `server-runtime-package-20260530.zip`  
**目标：** 本地电脑运行前端 GUI，Ubuntu 22.04 服务器运行 FastAPI 后端和 5GPU nnUNetv2 推理。

## 一、服务器解压后怎么启动

### 1. 解压代码包

把压缩包传到 Ubuntu 22.04 服务器后执行：

```bash
unzip server-runtime-package-20260530.zip -d segmentation-gui-prototype
cd segmentation-gui-prototype
```

### 2. 进入 Python / nnUNet 环境

例如：

```bash
conda activate <你的nnUNet环境名>
```

确认基础环境：

```bash
python --version
nvidia-smi
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.device_count())"
nnUNetv2_predict -h
nnUNetv2_ensemble -h
```

预期：

```text
torch.cuda.is_available() = True
GPU 数量 >= 5
nnUNetv2_predict 可执行
nnUNetv2_ensemble 可执行
```

### 3. 安装后端运行依赖

如果服务器环境里还没有 FastAPI / uvicorn：

```bash
pip install fastapi uvicorn python-multipart
```

如果启动时报缺包，再按报错补，例如：

```bash
pip install psutil nibabel numpy
```

不要盲目覆盖已有 nnUNet / PyTorch / CUDA 环境。

### 4. 配置 CORS

把 `<你的电脑校园网IP>` 换成运行前端的电脑 IP：

```bash
export SEGMENTATION_ALLOWED_ORIGINS="http://<你的电脑校园网IP>:5173"
```

如果浏览器实际打开的是：

```text
http://127.0.0.1:5173
```

那就配置：

```bash
export SEGMENTATION_ALLOWED_ORIGINS="http://127.0.0.1:5173"
```

原则：浏览器地址栏里的前端 Origin 是什么，就放行什么。

### 5. 配置 server 推理环境变量

下面路径必须替换成服务器上的真实路径：

```bash
export SEGMENTATION_SERVER_GPUS="0,1,2,3,4"
export SEGMENTATION_SERVER_FOLDS="0,1,2,3,4"

export SEGMENTATION_SERVER_DATASET_ID="1"
export SEGMENTATION_SERVER_CONFIG="3d_fullres"
export SEGMENTATION_SERVER_PLANS="nnUNetResEncUNetXLPlans"

export SEGMENTATION_SERVER_NNUNET_RAW="/path/to/nnUNet_raw"
export SEGMENTATION_SERVER_NNUNET_PREPROCESSED="/path/to/nnUNet_preprocessed"
export SEGMENTATION_SERVER_NNUNET_RESULTS="/path/to/nnUNet_results"

export SEGMENTATION_SERVER_OUTPUT_ROOT="/path/to/gui_jobs"

export SEGMENTATION_SERVER_EVALUATE_SCRIPT="/path/to/evaluate_full.py"
export SEGMENTATION_SERVER_LABELS_DIR="/path/to/labels"
export SEGMENTATION_SERVER_DATASET_JSON="/path/to/dataset.json"

export SEGMENTATION_SERVER_PREPROCESS_WORKERS="4"
export SEGMENTATION_SERVER_ENSEMBLE_PROCESSES="8"
```

如果输出目录不存在：

```bash
mkdir -p "$SEGMENTATION_SERVER_OUTPUT_ROOT"
```

### 6. 检查关键路径

```bash
ls "$SEGMENTATION_SERVER_NNUNET_RAW"
ls "$SEGMENTATION_SERVER_NNUNET_PREPROCESSED"
ls "$SEGMENTATION_SERVER_NNUNET_RESULTS"
ls "$SEGMENTATION_SERVER_OUTPUT_ROOT"
ls "$SEGMENTATION_SERVER_EVALUATE_SCRIPT"
ls "$SEGMENTATION_SERVER_LABELS_DIR"
ls "$SEGMENTATION_SERVER_DATASET_JSON"
```

如果任何一个失败，先修路径，不要先联调 GUI。

### 7. 启动后端

在解压后的项目根目录运行：

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

不要用 `--host 127.0.0.1`，否则本地电脑访问不到服务器后端。

## 二、本地电脑怎么连接服务器

### 1. 启动前端

在本地电脑项目目录：

```bash
cd D:/BME2026/BME_CT_Seg/segmentation-gui-prototype
```

PowerShell：

```powershell
$env:VITE_API_ENDPOINT="http://<服务器校园网IP>:8000"
npm run dev:lan
```

浏览器打开：

```text
http://<你的电脑校园网IP>:5173
```

或本机打开：

```text
http://127.0.0.1:5173
```

注意：你实际打开哪个地址，服务器 `SEGMENTATION_ALLOWED_ORIGINS` 就要放行哪个地址。

### 2. 先测 API

浏览器访问：

```text
http://<服务器校园网IP>:8000/api/health
http://<服务器校园网IP>:8000/api/models
```

重点检查 `/api/models`：

```text
runtime_target
server_inference
missing
ready/status
```

如果 `missing` 里有 `server_evaluate_full.py` 或 `server_dataset.json`，说明服务器环境变量或路径还没配对。

### 3. 在 GUI 里跑 server 推理

1. 上传小型或脱敏 NIfTI。
2. 选择 **服务器云端推理**。
3. 创建 job。
4. 服务器另开 SSH：

```bash
watch -n 1 nvidia-smi
```

确认 5 张 GPU 上出现对应推理进程。

## 三、最小验收标准

第一轮不要追求公网访问，先确认：

```text
本地电脑 GUI
  -> 校园网 Ubuntu FastAPI
  -> runtime_target=server job
  -> 5GPU 推理启动
  -> SSE 有进度
  -> 可以取消
  -> 至少一轮可以完成并下载结果
```

验收项：

- [ ] `/api/health` 可访问。
- [ ] `/api/models` 可访问。
- [ ] 浏览器无 CORS 报错。
- [ ] GUI 能上传 NIfTI。
- [ ] GUI 能创建 `runtime_target=server` job。
- [ ] SSE progress / heartbeat 正常。
- [ ] `nvidia-smi` 能看到 5GPU 推理进程。
- [ ] 取消任务可终止服务器子进程。
- [ ] 完成任务可下载结果。
- [ ] 前端能回填 mask。
- [ ] validation / remap 能正常显示。

## 四、如果服务器上不放当前后端代码，需要满足什么条件

服务器可以不放当前项目的 `server/main.py`、`server/server_inference.py`，但必须已经具备等价的“后端能力”。否则本地 GUI 不能直接命令服务器 GPU 推理。

### 情况 A：服务器已有等价推理 API

服务器已有 HTTP 服务，至少支持：

```text
1. 接收 CT / NIfTI 上传
2. 创建推理 job
3. 返回 job_id
4. 查询 job 状态
5. SSE 或轮询进度
6. 取消任务
7. 下载结果
8. label validation / evaluate
9. 5GPU / 5-fold soft ensemble
10. 返回前端需要的字段格式
```

最好兼容当前 GUI 接口：

```text
GET  /api/health
GET  /api/models
POST /api/segment/jobs
GET  /api/segment/jobs/{job_id}/events
POST /api/segment/jobs/{job_id}/cancel
GET  /api/segment/jobs/{job_id}/result
```

如果不兼容，就要改前端 `src/inference/inferenceClient.ts` 适配对方 API。

### 情况 B：本地后端通过 SSH 控制服务器

架构变成：

```text
浏览器 GUI
  ↓
本地 FastAPI 后端
  ↓ SSH
Ubuntu 服务器 nnUNetv2
```

服务器需要：

```text
1. SSH 可访问
2. 本地机器有服务器账号或密钥
3. 服务器上有 nnUNetv2 / CUDA / PyTorch / 模型 / 数据目录
4. 本地后端能上传 CT 到服务器
5. 本地后端能远程启动 5 个 fold
6. 本地后端能远程取消进程
7. 本地后端能把结果拉回本地
8. 本地后端能处理 SSE / job 状态
```

这个方案理论可行，但不推荐作为第一轮，因为远程进程管理、取消、断线恢复、日志和结果同步都会更复杂。

### 情况 C：服务器有共享文件系统和调度系统

例如服务器已有：

```text
共享目录
SLURM / PBS / Kubernetes / 自研任务队列
```

需要满足：

```text
1. 本地电脑和服务器都能访问同一个共享目录
2. 有任务提交命令，例如 sbatch / qsub
3. 能查询任务状态
4. 能取消任务
5. 推理脚本能固定读取输入、写出输出
6. 本地后端能读取输出并提供下载
```

适合正式集群，但比当前校园网 smoke test 更复杂。

## 五、结论

当前最推荐：

```text
服务器上放 server runtime 包
服务器启动 FastAPI
本地前端通过 API 命令服务器推理
```

如果服务器不放这份后端代码，服务器也必须已经有等价的推理 API、SSH 执行层或任务调度系统。

一句话：

```text
服务器可以不放这份后端代码，但不能没有“后端能力”。
```
