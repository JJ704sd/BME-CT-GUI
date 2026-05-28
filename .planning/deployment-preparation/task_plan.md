# 部署准备与维护计划

**Scope:** 针对用户提出的三个关注点进行分析和规划

**当前状态：** 项目代码稳定，测试全部通过（2026-05-28）

## 关注点分析

### 1. 更新最佳模型参数权重

**结论：只会影响局部路径，不会导致项目整体大变动**

当前模型权重配置：
- 主要 checkpoint：`nnunetv2_files/checkpoint_best.pth`（硬编码路径）
- FLARE 模型目录：`nnUNet_results/Dataset001_FLARE/nnUNetTrainer__nnUNetPlans__2d/fold_0/checkpoint_best.pth`
- 运行时模型：`server/work/runtime_model/nnUNetTrainer__nnUNetPlans__2d/fold_0/checkpoint_best.pth`

**更新权重只需：**
1. 替换 `nnunetv2_files/checkpoint_best.pth` 文件
2. 重新运行验收测试验证新权重
3. 更新 README.md 中的验收记录表格
4. 更新 SEGMENTATION_METRICS_SUMMARY.md 中的指标数据

**不需要修改：**
- 前端代码
- API 接口
- 推理流程逻辑
- 项目架构

**建议操作流程：**
```bash
# 1. 备份旧权重
mv nnunetv2_files/checkpoint_best.pth nnunetv2_files/checkpoint_best.pth.bak

# 2. 放入新权重
cp /path/to/new/checkpoint_best.pth nnunetv2_files/

# 3. 运行验证
python tools/segmentation_metrics_summary.py --prediction <test_pred> --reference <test_ref> \
  --checkpoint nnunetv2_files/checkpoint_best.pth ...

# 4. 更新文档中的验收记录
```

---

### 1.5 替换改良版 nnUNet-v2 模型（重要）

**情况比单纯更新权重更复杂**，可能涉及以下变化：

#### 变化类型分析

| 变化类型 | 影响范围 | 需要修改的文件 |
|----------|----------|----------------|
| **权重文件更新** | 低 | `nnunetv2_files/checkpoint_best.pth` + 文档 |
| **模型架构变化**（如 2d→3d_fullres） | 中 | `server/main.py` 中的 `RUNTIME_MODEL_DIR` 路径 |
| **标签数量变化**（如 15→13 类） | 中-高 | 前端 `organDetails.ts` + 后端 `taxonomy.py` + 测试 |
| **数据集变化**（如 AMOS22→新数据集） | 高 | taxonomy 映射 + 参考病例 + 验收标准 |

#### 逐步替换流程

**Step 1: 预检查新模型文件**
```bash
# 检查新模型的 dataset.json（标签定义）
cat /path/to/new_model/dataset.json | python -m json.tool

# 检查新模型的 plans.json（架构配置）
cat /path/to/new_model/plans.json | python -m json.tool

# 对比标签差异
python -c "
import json
old = json.load(open('.test-output/acceptance-new-weight-20260524-201714/work/runtime_model/nnUNetTrainer__nnUNetPlans__2d/dataset.json'))
new = json.load(open('/path/to/new_model/dataset.json'))
print('旧模型标签:', old.get('labels', {}))
print('新模型标签:', new.get('labels', {}))
"
```

**Step 2: 根据变化类型执行对应操作**

**场景 A：只更新权重（标签和架构不变）**
```bash
# 1. 备份旧权重
mv nnunetv2_files/checkpoint_best.pth nnunetv2_files/checkpoint_best.pth.bak

# 2. 放入新权重
cp /path/to/new_checkpoint_best.pth nnunetv2_files/

# 3. 运行验收测试
npm test

# 4. 更新文档
# 更新 README.md 中的验收记录表格
# 更新 SEGMENTATION_METRICS_SUMMARY.md
```

**场景 B：模型架构变化（如 2d → 3d_fullres）**
```bash
# 1. 更新 server/main.py 中的模型目录路径
# 当前硬编码：
#   RUNTIME_MODEL_DIR = WORK_DIR / "runtime_model" / "nnUNetTrainer__nnUNetPlans__2d"
# 需要改为新架构路径，如：
#   RUNTIME_MODEL_DIR = WORK_DIR / "runtime_model" / "nnUNetTrainer__nnUNetPlans__3d_fullres"

# 2. 更新 nnunetv2_files/ 目录结构
# 需要放入完整的模型目录（包含 dataset.json, plans.json, fold_0/ 等）

# 3. 重新生成 runtime_model
# 后端会自动从 nnunetv2_files/ 复制到 server/work/runtime_model/

# 4. 运行完整测试
npm test
```

**场景 C：标签数量/类别变化（如 15 类 → 13 类）**
```bash
# 1. 更新前端器官详情数据
# 文件：src/data/organDetails.ts
# 需要修改：label 列表、颜色映射、中文名称、器官说明

# 2. 更新后端 taxonomy 映射
# 文件：server/taxonomy.py
# 需要修改：
#   - FLARE22_LABELS 字典（如果新数据集已知）
#   - KNOWN_DATASETS 字典
#   - _NAME_ALIASES 别名映射

# 3. 更新参考病例
# 如果新模型使用不同的数据集，需要更换参考病例文件
# nnunetv2_files/amos_0117(3).nii.gz → 新的参考 CT
# nnunetv2_files/amos_0117(2).nii.gz → 新的参考标签

# 4. 更新 reference_cases.json
# 修改参考病例配置文件

# 5. 更新验收标准
# README.md 中的验收记录表格
# VALIDATION_MEAN_DICE_THRESHOLD 和 VALIDATION_MIN_DICE_THRESHOLD

# 6. 更新测试用例
# tests/backendState.test.py 中的标签 ID 测试
# tests/imagingLogic.test.ts 中的器官 label 测试
```

**场景 D：完全更换数据集（如 AMOS22 → 新数据集）**
```bash
# 除了场景 C 的所有步骤外，还需要：

# 1. 更新 CLAUDE.md 中的数据集说明
# 修改：当前 checkpoint 为 AMOS22 Dataset001_AMOS22，15 个前景标签

# 2. 更新 .gitignore 排除规则（如果新数据集文件名模式不同）

# 3. 更新 nnunet_env 环境（如果需要特定版本的 nnUNetv2）

# 4. 重新运行完整验收流程
python tools/segmentation_metrics_summary.py ...
```

#### 模型替换检查清单

```markdown
## 替换前检查
- [ ] 新模型文件完整（checkpoint_best.pth + dataset.json + plans.json）
- [ ] 新模型标签数量已确认
- [ ] 新模型架构已确认（2d / 3d_fullres / 3d_lowres）
- [ ] 新模型训练数据集已确认
- [ ] 参考病例文件已准备（如果需要更换）

## 替换操作
- [ ] 备份旧模型文件
- [ ] 放入新模型文件
- [ ] 更新代码配置（如果架构变化）
- [ ] 更新前端器官数据（如果标签变化）
- [ ] 更新 taxonomy 映射（如果数据集变化）

## 替换后验证
- [ ] 后端启动正常
- [ ] 前端加载正常
- [ ] 参考病例推理成功
- [ ] 验收测试通过
- [ ] 文档已更新
```

#### 关键配置文件位置

| 文件 | 用途 | 何时需要修改 |
|------|------|--------------|
| `server/main.py:34` | `PROJECT_CHECKPOINT` 路径 | 权重文件名变化时 |
| `server/main.py:37-42` | 模型目录路径 | 架构变化时 |
| `src/data/organDetails.ts` | 前端器官详情 | 标签数量/名称变化时 |
| `server/taxonomy.py:16-30` | FLARE22 标签映射 | 数据集变化时 |
| `reference_cases.json` | 参考病例配置 | 参考病例变化时 |
| `README.md` | 验收记录 | 每次替换后 |

---

### 2. Linux 服务器部署

**需要修改的 Windows 特定代码：**

#### 2.1 路径配置（server/main.py:43-44）
```python
# 当前 Windows 特定
NNUNET_PREDICT_COMMAND = PROJECT_ROOT / "nnunet_env" / "Scripts" / "nnUNetv2_predict_from_modelfolder.exe"
NNUNET_PYTHON_COMMAND = PROJECT_ROOT / "nnunet_env" / "Scripts" / "python.exe"

# Linux 修改为
NNUNET_PREDICT_COMMAND = PROJECT_ROOT / "nnunet_env" / "bin" / "nnUNetv2_predict_from_modelfolder"
NNUNET_PYTHON_COMMAND = PROJECT_ROOT / "nnunet_env" / "bin" / "python"
```

#### 2.2 推荐的跨平台方案
```python
import sys
from pathlib import Path

def get_platform_commands(project_root: Path):
    if sys.platform == "win32":
        return {
            "predict": project_root / "nnunet_env" / "Scripts" / "nnUNetv2_predict_from_modelfolder.exe",
            "python": project_root / "nnunet_env" / "Scripts" / "python.exe",
        }
    else:
        return {
            "predict": project_root / "nnunet_env" / "bin" / "nnUNetv2_predict_from_modelfolder",
            "python": project_root / "nnunet_env" / "bin" / "python",
        }
```

#### 2.3 其他需要检查的点
- **路径分隔符**：当前使用 `pathlib.Path`，已自动处理跨平台 ✅
- **进程管理**：`subprocess.Popen` 在 Linux 上行为一致 ✅
- **select.select()**：已在 CLAUDE.md 中标注 Windows 不适用，使用 queue.Queue 替代 ✅
- **文件权限**：Linux 上需要确保 `nnunet_env/bin/` 下的可执行文件有执行权限

#### 2.4 部署检查清单
```bash
# 1. 确保 Python 环境
python3 -m venv nnunet_env
source nnunet_env/bin/activate
pip install -r server/requirements.txt
pip install torch nnunetv2

# 2. 设置执行权限
chmod +x nnunet_env/bin/nnUNetv2_predict_from_modelfolder

# 3. 显卡选择与环境变量配置
# 查看可用显卡
nvidia-smi

# 选择特定显卡（多卡服务器）
export CUDA_VISIBLE_DEVICES=0        # 使用第一张卡
export CUDA_VISIBLE_DEVICES=1        # 使用第二张卡
export CUDA_VISIBLE_DEVICES=0,1      # 使用前两张卡（推理只用主卡）

# 推理设备配置
export SEGMENTATION_DEVICE=cuda      # GPU 推理（默认）
export SEGMENTATION_DEVICE=cpu       # CPU 推理（无 GPU 或调试用）

# 推理质量配置
export SEGMENTATION_INFERENCE_PROFILE=quality  # 正式报告（默认）
export SEGMENTATION_INFERENCE_PROFILE=fast     # 快速预览

# 性能调优（根据显存调整）
export SEGMENTATION_PREPROCESS_WORKERS=2   # 预处理线程数
export SEGMENTATION_EXPORT_WORKERS=2       # 导出线程数
export SEGMENTATION_NOT_ON_DEVICE=0        # 0=全在 GPU，1=降低显存占用

# 4. 启动后端服务
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# 5. 启动前端（开发模式）
npm run dev -- --host 0.0.0.0 --port 5173

# 6. 生产构建前端
npm run build
# 使用 nginx 或其他 web server 托管 dist/ 目录
```

#### 2.5 多显卡服务器场景
```bash
# 场景：服务器有 4 张 GPU，需要启动 4 个推理服务实例
# 实例 1 - 端口 8000，使用 GPU 0
CUDA_VISIBLE_DEVICES=0 SEGMENTATION_DEVICE=cuda python -m uvicorn server.main:app --host 0.0.0.0 --port 8000

# 实例 2 - 端口 8001，使用 GPU 1
CUDA_VISIBLE_DEVICES=1 SEGMENTATION_DEVICE=cuda python -m uvicorn server.main:app --host 0.0.0.0 --port 8001

# 实例 3 - 端口 8002，使用 GPU 2
CUDA_VISIBLE_DEVICES=2 SEGMENTATION_DEVICE=cuda python -m uvicorn server.main:app --host 0.0.0.0 --port 8002

# 实例 4 - 端口 8003，使用 GPU 3
CUDA_VISIBLE_DEVICES=3 SEGMENTATION_DEVICE=cuda python -m uvicorn server.main:app --host 0.0.0.0 --port 8003

# 前端负载均衡配置（nginx 示例）
# upstream backend {
#     server 127.0.0.1:8000;
#     server 127.0.0.1:8001;
#     server 127.0.0.1:8002;
#     server 127.0.0.1:8003;
# }
```

#### 2.6 显存不足时的降级策略
```bash
# 如果 GPU 显存不足（OOM），按以下顺序尝试：

# 方案 1：关闭 TTA（节省约 50% 显存）
export SEGMENTATION_DISABLE_TTA=1

# 方案 2：降低 tile step size（减少显存峰值）
export SEGMENTATION_TILE_STEP_SIZE=0.25

# 方案 3：关闭 perform_everything_on_device（CPU 做部分计算）
export SEGMENTATION_NOT_ON_DEVICE=1

# 方案 4：使用 CPU 推理（最慢但不依赖 GPU）
export SEGMENTATION_DEVICE=cpu

# 方案 5：使用快速模式（综合优化）
export SEGMENTATION_INFERENCE_PROFILE=fast
```

---

### 3. 遗留 Bug 检查

**测试状态：**
- ✅ 前端测试（viewerLogic, imagingLogic, acceptanceDocs, perfTool, layoutRegression）：全部通过
- ✅ 后端测试（backendState, segmentationMetrics）：全部通过
- ✅ 浏览器布局测试（browserLayout）：通过

**已知限制（非 bug，设计如此）：**
1. `confidenceThreshold` 是质控提示，不真实作用于多标签概率图
2. `fast` 模式会牺牲质量，需要人工复核
3. 单个新病例首次推理可能需要分钟级到十几分钟

**潜在改进点：**
1. **模型路径硬编码**：当前 `checkpoint_best.pth` 路径硬编码，可改为环境变量配置
2. **错误提示优化**：部分错误信息可以更友好
3. **日志增强**：可以添加更详细的推理进度日志

---

## 更新后的 Planning 文档结构

建议在 `.planning/` 下新增以下规划：

```
.planning/
├── deployment-preparation/      # 本次新增
│   └── task_plan.md            # 部署准备计划
├── online-inference-followup/  # 已有，可归档
├── label-scoring-optimization/ # 已有
├── non-amos-acceptance-expansion/ # 已有
└── realtime-inference-progress/  # 已有
```

---

## 建议的后续行动

### 短期（等新权重就绪）
1. 准备新权重验证脚本
2. 更新文档模板，方便快速替换验收记录

### 中期（Linux 部署）
1. 实现跨平台路径配置
2. 编写 Linux 部署文档
3. 准备 Docker 容器化方案（可选）

### 长期（持续维护）
1. 建立 CI/CD 流程
2. 添加更多测试用例
3. 监控生产环境性能

---

## 总结

| 关注点 | 影响范围 | 风险等级 | 建议 |
|--------|----------|----------|------|
| 更新模型权重 | 局部（权重文件+文档） | 低 | 等实验跑完后直接替换 |
| **替换改良版模型** | **取决于变化类型** | **低-高** | **先确认变化类型，再按对应场景操作** |
| Linux 部署 | 中等（需要修改路径配置） | 中 | 提前准备跨平台代码 |
| 修复遗留 bug | 低（测试已通过） | 低 | 持续优化 |

### 替换改良版模型的影响评估

| 变化类型 | 代码改动量 | 测试影响 | 文档更新 |
|----------|------------|----------|----------|
| 只更新权重 | 0 行 | 低 | 验收记录 |
| 架构变化（2d→3d） | 1-2 行 | 低 | 验收记录 |
| 标签数量变化 | 10-30 行 | 中 | 多个文档 |
| 数据集完全更换 | 50-100 行 | 高 | 全面更新 |

**关键结论：**
1. 项目架构稳定，基础框架不会变
2. 替换模型的影响取决于"变化程度"
3. 建议先确认新模型的具体变化类型，再按对应场景操作
4. 最复杂的情况（数据集完全更换）也只需要修改配置文件，不需要重写核心逻辑

---

## 远程推理分体部署流程

### 目标

本地电脑运行前端 GUI，GPU 服务器只运行后端推理服务。用户在本地导入 CT 图像，点击"运行分割"后，前端将图像上传到远程服务器进行推理，推理完成后结果回传到本地 GUI 查看。

### 架构概览

```
┌──────────────────────────┐          ┌──────────────────────────────────┐
│    本地电脑 (Windows)     │          │     GPU 服务器 (Linux)           │
│                          │  HTTP/SSE │                                  │
│  ┌────────────────────┐  │ ────────▶ │  ┌────────────────────────────┐ │
│  │  前端 GUI          │  │          │  │  FastAPI 后端              │ │
│  │  Vite dev server   │  │ ◀──────── │  │  uvicorn :8000             │ │
│  │  http://localhost   │  │          │  │  - nnUNetv2 推理           │ │
│  │  :5173             │  │          │  │  - CUDA GPU 加速           │ │
│  └────────────────────┘  │          │  └────────────────────────────┘ │
│                          │          │                                  │
│  API_ENDPOINT 指向 ────────────────────▶  监听 0.0.0.0:8000           │
│  <服务器IP>:8000        │          │                                  │
└──────────────────────────┘          └──────────────────────────────────┘
```

### 数据流

1. 用户在本地 GUI 导入 CT 原图（或载入参考病例）
2. 点击"运行分割" → 前端 `POST /api/segment/jobs` 上传 CT 文件到远程服务器
3. 后端创建推理 Job → 后台线程执行 nnUNetv2 推理
4. 前端 `EventSource` 监听 `GET /api/segment/jobs/{id}/events` SSE 实时获取进度
5. 推理完成 → 前端 `GET /api/segment/jobs/{id}/result` 下载 NIfTI 结果
6. 前端解析 NIfTI → 回填三正交视图 → 本地查看分割结果

### 前置知识：分体架构的关键改动

分体部署只需改两处代码：

1. **前端** `src/main.tsx` 的 `API_ENDPOINT`：从 `http://127.0.0.1:8000` 改为 `http://<服务器IP>:8000`
2. **后端** `server/main.py`：添加 CORS 中间件（本地前端跨域请求会被浏览器拦截）

CORS 配置加在 `app = FastAPI(...)` 之后：

```python
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # 或指定 ["http://localhost:5173"]
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

> SSE（EventSource）跨域需要后端响应 `Content-Type: text/event-stream`，当前 FastAPI SSE 实现已满足，只需 CORS 配置即可。

---

### Step 1: 云服务器选择与配置

#### 1.1 推荐配置

| 用途 | CPU | 内存 | GPU | 磁盘 | 参考价格 |
|------|-----|------|-----|------|----------|
| 开发测试 | 4 核 | 16GB | T4 16GB | 100GB SSD | ¥2-3/小时 |
| 正式推理 | 8 核 | 32GB | V100 32GB | 200GB SSD | ¥5-8/小时 |
| 高并发 | 16 核 | 64GB | A100 80GB | 500GB SSD | ¥15-25/小时 |

#### 1.2 推荐云平台

- **阿里云**：GPU 实例（gn6i/gn7i 系列）
- **腾讯云**：GPU 实例（GN7/GN10X 系列）
- **AutoDL**：学术友好，按量计费
- **矩池云**：专注 AI 推理

#### 1.3 系统镜像选择

```
推荐：Ubuntu 22.04 LTS + CUDA 11.8 + cuDNN 8.6
或：PyTorch 2.0+ 镜像（已预装 CUDA）
```

### Step 2: 环境准备

#### 2.1 SSH 登录服务器

```bash
ssh root@<服务器IP>
# 或使用云平台提供的 WebShell
```

#### 2.2 基础环境安装

```bash
# 更新系统
apt update && apt upgrade -y

# 安装基础工具
apt install -y git python3-pip python3-venv

# 验证 GPU
nvidia-smi
# 应该显示 GPU 型号和 CUDA 版本
```

#### 2.3 克隆项目

```bash
cd /opt
git clone https://github.com/JJ704sd/segmentation-gui-prototype.git
cd segmentation-gui-prototype
```

#### 2.4 上传模型文件

```bash
# 方法 1：scp 上传（本地终端，Linux/Mac/Windows PowerShell 均可）
scp nnunetv2_files/checkpoint_best.pth root@<服务器IP>:/opt/segmentation-gui-prototype/nnunetv2_files/
scp "nnunetv2_files/amos_0117(3).nii.gz" root@<服务器IP>:/opt/segmentation-gui-prototype/nnunetv2_files/

# 方法 2：云平台文件管理器上传
# 通过 Web 界面直接上传到对应目录

# 方法 3：wget 下载（如果有在线存储）
wget -O nnunetv2_files/checkpoint_best.pth "<模型下载链接>"
```

### Step 3: 后端部署

#### 3.1 Python 环境配置

```bash
# 创建虚拟环境
cd /opt/segmentation-gui-prototype
python3 -m venv nnunet_env
source nnunet_env/bin/activate

# 安装依赖
pip install -r server/requirements.txt

# 安装 PyTorch（根据 CUDA 版本选择）
# CUDA 11.8
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118

# CUDA 12.1
pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu121

# 安装 nnUNetv2
pip install nnunetv2

# 验证安装
python -c "import torch; print(torch.cuda.is_available())"
# 应该输出 True
```

#### 3.2 修改代码（Linux 适配）

```bash
# 编辑 server/main.py，修改 Windows 特定路径
sed -i 's|Scripts/nnUNetv2_predict_from_modelfolder.exe|bin/nnUNetv2_predict_from_modelfolder|g' server/main.py
sed -i 's|Scripts/python.exe|bin/python|g' server/main.py

# 或者使用跨平台方案（推荐）
# 在 server/main.py 中添加：
```

```python
import sys
from pathlib import Path

def get_platform_command(project_root: Path, command_name: str) -> Path:
    if sys.platform == "win32":
        return project_root / "nnunet_env" / "Scripts" / f"{command_name}.exe"
    else:
        return project_root / "nnunet_env" / "bin" / command_name

# 然后替换硬编码路径：
NNUNET_PREDICT_COMMAND = get_platform_command(PROJECT_ROOT, "nnUNetv2_predict_from_modelfolder")
NNUNET_PYTHON_COMMAND = get_platform_command(PROJECT_ROOT, "python")
```

#### 3.3 配置环境变量

```bash
# 创建环境变量文件
cat > /etc/profile.d/segmentation.sh << 'EOF'
export SEGMENTATION_DEVICE=cuda
export SEGMENTATION_INFERENCE_PROFILE=quality
export SEGMENTATION_PREPROCESS_WORKERS=2
export SEGMENTATION_EXPORT_WORKERS=2
export CUDA_VISIBLE_DEVICES=0
EOF

# 使环境变量生效
source /etc/profile.d/segmentation.sh
```

#### 3.4 创建 systemd 服务

```bash
# 创建后端服务文件
cat > /etc/systemd/system/segmentation-backend.service << 'EOF'
[Unit]
Description=Segmentation Backend Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/segmentation-gui-prototype
Environment=PATH=/opt/segmentation-gui-prototype/nnunet_env/bin:/usr/local/bin:/usr/bin:/bin
Environment=SEGMENTATION_DEVICE=cuda
Environment=SEGMENTATION_INFERENCE_PROFILE=quality
ExecStart=/opt/segmentation-gui-prototype/nnunet_env/bin/python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
EOF

# 使服务生效
systemctl daemon-reload
systemctl enable segmentation-backend
systemctl start segmentation-backend

# 查看服务状态
systemctl status segmentation-backend
```

### Step 4: 本地前端配置

前端运行在本地 Windows 电脑上，无需部署到服务器。

#### 4.1 修改 API_ENDPOINT

按"前置知识"中说明，编辑 `src/main.tsx` 的 `API_ENDPOINT` 为远程服务器地址。

#### 4.2 本地启动前端

```powershell
cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
npm run dev -- --port 5173
```

浏览器打开 `http://127.0.0.1:5173`，前端会自动连接远程服务器的后端 API。

#### 4.3 参考病例说明

- **参考病例**（`nnunetv2_files/amos_0117(3).nii.gz` 等）需要同时存在于服务器端的 `nnunetv2_files/` 目录中
- "载入参考病例"功能通过 `GET /api/samples/{id}/original` 从后端下载 CT 文件，分体架构下会从远程服务器下载
- 本地自定义上传的 CT 文件通过 `POST /api/segment/jobs` 直接上传到远程服务器

### Step 5: 验证部署

#### 5.1 服务器端验证

```bash
# SSH 登录服务器
ssh root@<服务器IP>

# 检查后端服务状态
systemctl status segmentation-backend

# 检查健康接口
curl http://localhost:8000/api/health
# 应返回 {"status":"ok","mode":"real-nnunetv2",...}

# 检查 GPU 状态
nvidia-smi
```

#### 5.2 本地验证

```powershell
# 测试跨域连接（PowerShell）
Invoke-WebRequest -Uri "http://<服务器IP>:8000/api/health" -UseBasicParsing

# 或在浏览器直接访问
# http://<服务器IP>:8000/api/health

# 启动本地前端
npm run dev -- --port 5173
```

#### 5.3 功能验证清单

```markdown
# 服务器端
- [ ] systemd 服务运行正常
- [ ] /api/health 返回 ok
- [ ] GPU 显示可用

# 本地前端
- [ ] 页面正常加载
- [ ] 健康检查显示远程后端已连接
- [ ] 可以载入参考病例（从远程服务器下载）
- [ ] 可以本地上传 CT 文件
- [ ] 推理任务可以创建
- [ ] SSE 进度正常推送（跨域）
- [ ] 推理结果可以下载并回填三视图
- [ ] 标签验证功能正常
```

### Step 6: 安全与优化

#### 6.1 防火墙配置

```bash
# 服务器开放必要端口
ufw allow 22/tcp       # SSH
ufw allow 8000/tcp     # 后端 API
ufw enable

# 注意：如果使用云平台，还需在安全组/防火墙规则中开放 8000 端口
```

#### 6.2 日志管理

```bash
# 查看后端日志
journalctl -u segmentation-backend -f

# 查看后端服务状态
systemctl status segmentation-backend
```

#### 6.3 生产环境加固（可选）

```bash
# 限制 API 访问来源（替代 CORS * 通配符）
# 在 server/main.py 中将 allow_origins 改为具体地址：
# allow_origins=["http://你的域名:5173", "http://你的公网IP:5173"]

# 使用 nginx 反向代理 + HTTPS（如有域名）
apt install -y nginx certbot python3-certbot-nginx
```

### Step 7: 多用户/高并发方案

#### 7.1 多实例负载均衡

```bash
# 启动多个后端实例（不同 GPU，不同端口）
CUDA_VISIBLE_DEVICES=0 SEGMENTATION_DEVICE=cuda python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
CUDA_VISIBLE_DEVICES=1 SEGMENTATION_DEVICE=cuda python -m uvicorn server.main:app --host 0.0.0.0 --port 8001

# 前端切换不同实例：修改 API_ENDPOINT 为对应端口
# 或使用 nginx 做反向代理负载均衡
```

#### 7.2 使用 Docker（可选）

```dockerfile
# Dockerfile — 仅后端推理服务
FROM nvidia/cuda:11.8.0-runtime-ubuntu22.04

RUN apt-get update && apt-get install -y python3 python3-pip python3-venv

WORKDIR /app
COPY . .

RUN python3 -m venv nnunet_env && \
    nnunet_env/bin/pip install -r server/requirements.txt && \
    nnunet_env/bin/pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118 && \
    nnunet_env/bin/pip install nnunetv2

EXPOSE 8000

CMD ["nnunet_env/bin/python", "-m", "uvicorn", "server.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### 部署流程图

```
┌─────────────────────────────────────────────────────────────┐
│                    分体部署流程总结                           │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  GPU 服务器端：                                              │
│  1. 选择云服务器（GPU 实例）                                 │
│     ↓                                                       │
│  2. 安装基础环境（Python, CUDA）                             │
│     ↓                                                       │
│  3. 克隆项目代码 + 上传模型文件                              │
│     ↓                                                       │
│  4. 配置 Python 环境（nnunet_env）                           │
│     ↓                                                       │
│  5. 修改代码（Linux 路径适配 + CORS）                        │
│     ↓                                                       │
│  6. 启动后端服务（systemd）                                  │
│                                                             │
│  本地电脑端：                                                │
│  7. 修改 API_ENDPOINT + 启动 CORS（见"前置知识"）           │
│     ↓                                                       │
│  8. npm run dev 启动前端                                     │
│     ↓                                                       │
│  9. 浏览器访问 localhost:5173 验证                           │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 常见问题排查

| 问题 | 可能原因 | 解决方案 |
|------|----------|----------|
| 前端显示"无法连接" | API_ENDPOINT 未修改或服务器未启动 | 检查 `src/main.tsx:52` 的地址，确认服务器 `curl http://<IP>:8000/api/health` |
| CORS 跨域错误 | 后端未配置 CORS 中间件 | 在 `server/main.py` 添加 `CORSMiddleware` |
| SSE 进度不推送 | 跨域 SSE 被浏览器拦截 | 确认 CORS 配置正确，检查浏览器控制台错误 |
| 推理超时 | GPU 显存不足 | 降低并发或使用更大显存 GPU，尝试 `SEGMENTATION_INFERENCE_PROFILE=fast` |
| 模型加载失败 | checkpoint 路径错误 | 检查服务器上 `nnunetv2_files/` 目录 |
| 参考病例加载失败 | 参考病例文件未上传到服务器 | 确认服务器 `nnunetv2_files/` 下有 `.nii.gz` 文件 |
| 上传 CT 失败 | 文件过大或网络超时 | 检查 uvicorn 超时配置，确认防火墙开放 8000 端口 |

### 成本估算

| 项目 | 开发测试 | 正式生产 |
|------|----------|----------|
| 服务器（仅后端） | ¥2-3/小时 | ¥5-8/小时 |
| 存储 | ¥0.5/GB/月 | ¥1/GB/月 |
| 流量（CT 上传+结果下载） | ¥0.8/GB | ¥0.8/GB |
| **月成本估算** | ¥500-800 | ¥2000-5000 |

**建议**：分体架构下前端不消耗服务器资源，成本主要来自推理计算。先使用按量计费测试，确认稳定后再转包月。不推理时可关机节省费用。
