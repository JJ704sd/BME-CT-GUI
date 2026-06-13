# RUN_ON_OTHER_PC.md — 在别的电脑上把 GUI 跑起来

> 这份文档假设你拿到的是打包好的代码压缩包，按下面 3 步操作就能把 GUI 起在 `http://127.0.0.1:5173/`，并用本地 nnU-Netv2 做在线推理。
>
> 整个过程预计 10–20 分钟（其中 `pip install nnunetv2` 和 `npm install` 占大头，看网络）。

---

## 准备清单（一次性把这些备齐）

1. **本项目源码**：解压压缩包到任意目录，例如 `D:\review\segmentation-gui-prototype`（下面统称 `<项目根>`）
2. **Python 3.10+**（推荐 3.11）：[python.org](https://www.python.org/downloads/) 下载安装，**安装时勾选 Add to PATH**
3. **Node.js 18+**（推荐 20 LTS）：[nodejs.org](https://nodejs.org/) 下载安装
4. **一个含 nnU-Netv2 模型产物的目录**（详见下方「数据与权重」）
5. **一块 NVIDIA GPU**（推理走 CUDA；如纯 CPU 也能起后端，但推理会非常慢甚至不可用）

---

## 第 1 步：装 Python 虚拟环境与依赖

打开 PowerShell（Windows）或 Terminal（macOS/Linux），执行：

```bash
# 1.1 在项目根**上一层**创建 venv（与项目根同级的父目录，记为 <父目录>）
#    即 <父目录>/nnunet_env/，这是默认值；想放别处就修改 1.5 步的环境变量。
cd <项目根>/..
python -m venv nnunet_env

# 1.2 激活 venv
#    Windows PowerShell:
& .\nnunet_env\Scripts\Activate.ps1
#    Linux / macOS:
source nnunet_env/bin/activate

# 1.3 升级 pip
python -m pip install --upgrade pip

# 1.4 装本项目的 4 个核心依赖
pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "python-multipart>=0.0.9" "nibabel>=5.0"

# 1.5 装 nnU-Netv2（按官方 README；下面给一个最常见的 PyTorch + CUDA 12.x 组合）
#    如果你已经有 PyTorch CUDA 版本，跳过这步的 torch 命令。
pip install torch torchvision --index-url https://download.pytorch.org/whl/cu121
pip install nnunetv2

# 1.6 验证装好
python -c "import fastapi, nibabel, nnunetv2; print('all OK')"
```

> ⚠️ `nnunetv2` 安装这一步容易卡：如果 PyTorch / CUDA / nnunetv2 三者版本不匹配，推理时会爆错。最稳的版本组合是 **PyTorch 2.1+ CUDA 12.x + nnunetv2 2.x**。如果你的 GPU 是 RTX 30/40 系列，推荐 CUDA 11.8 或 12.x。

---

## 第 2 步：放好数据与模型权重

本项目用的是 **AMOS22** 和 **FLARE22** 两个公开数据集，加一个训练好的 nnU-Netv2 模型产物。

### 2.1 推荐布局（与默认值一致，最省事）

把以下文件和目录放到 `<项目根>/..`（与 `segmentation-gui-prototype` 同级的父目录）下：

```
<父目录>/
├── segmentation-gui-prototype/         ← 解压得到的项目根
├── nnunet_env/                         ← 第 1 步创建的 venv
├── nnUNet_raw/                         ← AMOS22 / FLARE22 训练数据（从官方下载）
├── nnUNet_preprocessed/                ← nnU-Netv2 预处理结果（运行 nnUNetv2_plan_and_preprocess 自动生成）
└── nnUNet_results/                     ← nnU-Netv2 训练产物（包含 dataset.json / plans.json / checkpoint_best.pth）
    └── Dataset001_FLARE/
        └── nnUNetTrainer__nnUNetPlans__2d/
            ├── dataset.json
            ├── plans.json
            └── fold_0/
                └── checkpoint_best.pth   ← 推理权重（~1.1 GB）
```

### 2.2 不放默认位置怎么办（自由布局）

把数据集 / venv / 权重放任意位置都行——通过环境变量告诉项目。**完整的 5 个环境变量**（按需设置）：

```bash
# Windows PowerShell
$env:SEGMENTATION_NNUNET_RAW          = "D:\your\path\nnUNet_raw"
$env:SEGMENTATION_NNUNET_PREPROCESSED  = "D:\your\path\nnUNet_preprocessed"
$env:SEGMENTATION_NNUNET_RESULTS      = "D:\your\path\nnUNet_results"
$env:SEGMENTATION_NNUNET_PYTHON       = "D:\your\path\venv\Scripts\python.exe"
$env:SEGMENTATION_NNUNET_FILES        = "D:\your\path\nnunetv2_files"  # 可选：demo NIfTI 目录
```

```bash
# Linux / macOS
export SEGMENTATION_NNUNET_RAW="/your/path/nnUNet_raw"
export SEGMENTATION_NNUNET_PREPROCESSED="/your/path/nnUNet_preprocessed"
export SEGMENTATION_NNUNET_RESULTS="/your/path/nnUNet_results"
export SEGMENTATION_NNUNET_PYTHON="/your/path/venv/bin/python"
export SEGMENTATION_NNUNET_FILES="/your/path/nnunetv2_files"  # 可选
```

### 2.3 数据来源

| 数据集 | 链接 | 用途 |
|---|---|---|
| AMOS22 | <https://amos22.grand-challenge.org/> | 15 类腹部器官训练 + 验证 |
| FLARE22 | <https://flare22.grand-challenge.org/> | 13 类腹部器官训练 + 验证 |
| nnU-Netv2 | <https://github.com/MIC-DKFZ/nnUNet> | 训练框架 |
| 参考病例 JSON | `项目根/examples/reference_cases.json` | 4 例内置 demo（AMOS / FLARE / WORD / AbdomenCT-1K） |

---

## 第 3 步：装前端依赖 + 启动 GUI

新开两个终端（venv 激活状态）：

```bash
# 终端 1 — 后端（首次启动会有 [reference-cases] WARN，意思是 demo NIfTI 没放，
# 那是 demo 数据，不影响 inference 跑通；想消除警告就把 demo NIfTI 放到 nnunetv2_files/）
cd <项目根>
<VENV_PY> -m uvicorn server.main:app --host 127.0.0.1 --port 8000

# 终端 2 — 前端
cd <项目根>
npm install                # 首次需要，下载约 200 MB 依赖
npm run dev                # → http://127.0.0.1:5173/
```

> `<VENV_PY>` = 你的 venv Python 路径。Windows: `<父目录>\nnunet_env\Scripts\python.exe`；Linux/macOS: `<父目录>/nnunet_env/bin/python`。

### 3.1 一键启动（可选）

如果不想开两个终端，可以用项目自带的脚本（自动 spawn 后端 + 前端 + 健康检查）：

```bash
cd <项目根>
<VENV_PY> tools/start_local_demo.py
```

等几秒，看到 `Open the GUI at: http://127.0.0.1:5173/` 就成了。失败时它会打印回退命令，详见 `docs/quickstart-launch-guide.md`。

---

## 第 4 步：验证 + 试一次推理

### 4.1 健康检查（3 个端点）

```bash
curl http://127.0.0.1:8000/api/health
#   → model_state.ready: true, model_state.missing: []  ← 准备好
#   → 若 missing 非空，按缺失文件名补齐对应文件

curl http://127.0.0.1:8000/api/samples
#   → 返回 4 个参考病例（AMOS / FLARE / WORD / AbdomenCT-1K）

curl http://127.0.0.1:8000/api/models
#   → 返回模型元信息
```

### 4.2 在浏览器做一次推理

1. 浏览器打开 <http://127.0.0.1:5173/>
2. 在「参考病例」列表点选 **AMOS 0117**（或 FLARE22 Tr 0009）
3. 点 **Run inference**（或对应按钮），等几十秒到几分钟（取决于 GPU）
4. 完成后三视图会显示分割 mask + 底部进度条 100%
5. 右侧面板会出 6 类指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD）+ 15 器官逐标签表
6. 点 **Export Report** 可下载临床风格 HTML 报告

---

## 常见问题

### Q1: 后端起不来，报 `ModuleNotFoundError: No module named 'fastapi'`
A: venv 没激活。看终端标题栏有没有 `(nnunet_env)`；没有就重新 `& .\nnunet_env\Scripts\Activate.ps1`。

### Q2: `model_state.missing` 不为空
A: 健康检查返回 JSON 里 `missing` 字段会列具体缺失的文件名，例如：
```json
{"missing": ["checkpoint_best.pth", "plans.json"]}
```
按文件名去 `<项目根>/..` 下找到对应文件并补齐；或在 §2.2 设环境变量指向正确位置。

### Q3: 前端 `npm install` 卡住或报 peer dependency 错
A: 试 `npm install --legacy-peer-deps`，或在 `package.json` 所在的目录运行 `rm -rf node_modules package-lock.json && npm install`。

### Q4: 推理时报 `CUDA out of memory`
A: 设 `SEGMENTATION_TILE_STEP_SIZE=0.8`（默认 quality=0.5，最激进；调到 0.8-1.0 可省显存），或换 `SEGMENTATION_INFERENCE_PROFILE=fast`（跳过 TTA，最省）。

### Q5: 只想看代码 / 跑测试，不想跑推理
A: 装好 venv 后执行 `node tests/<name>.test.ts`（前端测试）和 `<VENV_PY> tests/<name>.test.py`（后端测试）。这些测试不需要 GPU 也不需要数据集。

### Q6: 在哪能看到更详细的工程说明
A: `README.md`（项目亮点）/ `README.zh-CN.md`（工程详版）/ `docs/quickstart-launch-guide.md`（演示手册）/ `docs/demo-day-checklist.md`（演示当天 checklist）。

---

## 一句话总结

```bash
# 解压 → 装 venv → 放好 nnUNet_results 数据集 → 跑两个 npm/uvicorn 命令 → 浏览器开 5173 → 点 Run inference
```

祝评审顺利 🚀