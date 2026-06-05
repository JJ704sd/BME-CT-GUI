# 中国生物医学工程竞赛 — 报告写作指南

> 适用项目：`segmentation-gui-prototype`（腹部 CT 多器官自动分割 + 浏览器端交互验证系统）
> 适用赛道：「呼吸-消化系统疾病」赛道 — 智能影像分析与评价（影像分析算法类）
> 报告硬约束：前言 + 问题引入 ≤ 2 页，方案设计 + 结果展示 + 讨论 ≤ 8 页，整体 ≤ 12 页
> 最近更新：2026-06-05（同步 6-04 HTML 报告第一轮美化（视觉层 + 信息层）+ 6-05 HTML 报告临床报告风格重构（封面 + 摘要 + TOC + 8 段章节 + 公式 tip + 严重度分布图 + caption/footnote + A4 打印页眉页码））

---

## 0. 一句话定位

> 基于 **nnU-Net v2** 在 AMOS22 上完成 15 个腹部器官的 5-fold 自动分割训练，结合 5-fold soft ensemble、跨数据集自动 taxonomy remap 与 **本地缓存演示（cache hit 约 0.001s vs 真实推理约 218s）**，配套浏览器端三正交 CT 联动浏览 + 三维形态学量化的部署验证系统，在 AMOS 0117 上取得 `mean Dice = 0.925`、`foreground Dice = 0.98`，在 FLARE22 Tr 0009 跨数据集验证中 `mean Dice = 0.926`。

**契合命题**：覆盖任务 1（影像智能分割）+ 任务 2（影像量化分析），建议以"腹部多器官自动分割 + 训练过程 + 部署验证"作为整体方案申报。

**工程亮点**（可放进前言"本文工作"或方案结尾的部署小节）：
- **预测结果缓存（7 字段 cache_key）**：相同 `input_sha256 + checkpoint_sha256 + checkpoint_dataset_name + checkpoint_configuration + labels_source + runtime_target + inference_options` 直接命中 `server/work/<job_id>/prediction.nii.gz`，**避免重复推理**，对评审现场"反复演示同一例"场景尤其友好。**`label_taxonomy` / `dataset_hint` 不在 cache_key 中**——它们只影响 validation 阶段的标签解释，不影响 NIfTI 预测结果；同一 CT 切换 taxonomy 仍会命中同一 cache slot，只是重算 validation。
- **cache hit 显示历史 validation 摘要**（2026-06-01 cache 链路补丁）：FLARE22 Tr 0009 cache hit 命中 `02da885c97d8` 时，前端正确显示 `mean_dice=0.893127 / min_dice=0.67373 / fg=0.949908` 并标注"（历史离线缓存摘要）"，避免张冠李戴。
- **HTML 报告临床报告风格重构**（2026-06-04 / 2026-06-05）：导出报告从"工程 dump"经"卡片式仪表板"升级为"临床评估报告"：封面（题图条 + 报告编号 + 主副标题 + 数据集/病例/生成时间三列）、执行摘要（通过 / 关注点 / 建议三栏）、目录（§1-§8 锚点导航）、8 段章节编号（报告概览 / 摘要 / 数据集 / 器官 / 体素 / 距离 / 关键发现 / 附录）、公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、严重度分布图（高/中/低 bar chart）、表格 caption + footnote、A4 打印页眉页码；视觉层有色阶图例、remap/historical 警告条、taxonomy 展示位、spacing 可视化、aiFindings 严重度排序、器官列表折叠、列固定/排序。字体 Source Han Serif / Songti SC + JetBrains Mono，答辩与评审现场可直接出 PDF。
- **`/api/samples` 参考病例列表**：通过 `SEGMENTATION_REFERENCE_CASES_JSON` env var 注入，演示现场只需一次 setenv 即可暴露 4 个 case（AMOS 0117、FLARE22 Tr 0009 等）。

---

## 1. 报告整体结构（建议 10–12 页）

| 章节 | 建议页数 | 命题硬约束 | 主体内容 |
|---|---|---|---|
| 摘要 | 1 | — | 目的—方法—结果—结论，4 段式 |
| 1. 前言与问题引入 | 1.5 | ≤ 2 页 | 临床痛点 + 现有方案不足 |
| 2. 方案设计 | 4.5 | 合计 ≤ 8 页 | **数据集 / 训练 / 创新点 / GUI 部署 / 服务器** |
| 3. 结果展示 | 3 | 合计 ≤ 8 页 | **训练曲线 / 消融 / 泛化 / GUI 验证** |
| 4. 讨论与展望 | 0.5 | 合计 ≤ 8 页 | 局限 + 改进 + 临床落地 |
| 参考文献 | 0.5 | 标注准确 | GB/T 7714 或 IEEE |

---

## 2. 各章节写作要点 + 配图建议

### 摘要（约 300–400 字）

四段式（目的—方法—结果—结论）。**结果段必须给硬数字**：`AMOS 0117 mean Dice = 0.925 / foreground Dice = 0.980 / Hausdorff 7.72 mm`；`FLARE22 Tr 0009 自动 remap 后 mean Dice = 0.926`；`服务器 5-GPU 5-fold soft ensemble 约 3 分 48 秒`。

---

### 第 1 章 前言与问题引入（≤ 2 页）

**写作要点**（约 800–1000 字）：

1. **临床痛点**（约 300 字）：CT 影像数据量指数增长 vs 放射科医生日均阅片量超负荷，疲劳导致漏诊误诊风险上升；RECIST 1.1 等二维手动测量的局限——耗时、观察者差异、不能反映三维形态/异质性。
2. **现有方案的不足**（约 300 字）：nnU-Net、Transformer 等模型虽然精度高，但多数以离线脚本形式存在，**训练配置不可复现、跨数据集标签体系错位（如 FLARE22 vs AMOS22 label ID 错位导致 Dice≈0）、缺乏标准化三维量化和报告输出**。
3. **本文工作**（约 200 字）：四点贡献——
    1. 基于 nnU-Net v2 自动 plans + 5-fold CV 完成 15 个腹部器官分割训练；
    2. 5-fold soft ensemble 与跨数据集自动 taxonomy remap；
    3. 服务器 5-GPU 部署与本地双运行位置；
    4. 浏览器端三正交 CT 联动 + 三维量化 + 标准化报告，作为训练成果的部署验证手段。
4. **关键词**：腹部 CT；多器官分割；nnU-Net v2；5-fold soft ensemble；跨数据集标签 remap；三维形态学量化。

**配图建议**：
- **图 1 系统总览**：`screenshots/desktop-final.png` 或 `screenshots/detail-rich.png`，体现"算法 + GUI"整体思路。**放在摘要后或前言开头**，1 张即可。

---

### 第 2 章 方案设计（4–4.5 页，命题重头戏）

> 直接决定 **算法先进性（30 分）+ 算法有效性和展示度（30 分）= 60 分**。

#### 2.1 数据集与标签体系（约 0.7 页 + 1 张图）

**写作要点**：

- **AMOS22**：CT 多器官分割数据集，200 例训练 + 100 例验证，**15 个前景标签**（spleen, right_kidney, left_kidney, gallbladder, esophagus, liver, stomach, aorta, ivc, pancreas, right_adrenal_gland, left_adrenal_gland, duodenum, bladder, prostate_or_uterus）。
- **FLARE22**：腹部 13 类器官，512×512×87 体数据，spacing `0.807/0.807/2.5 mm`，**用于跨数据集泛化验证**。
- 数据划分：AMOS22 5-fold cross-validation，**未使用 Mimics / 3D Slicer / ITK-SNAP 等人工交互软件**（命题明文禁止）。
- 预处理：spacing 重采样到统一分辨率、强度归一化、轴向排序。

**配图建议**：
- **图 2 标签色板 / 15 器官表**：用 `src/data/organDetails.ts` 的色值做一张"标签 ID—器官名（中英）—颜色"对照表，正文横版可放全表。

#### 2.2 nnU-Net v2 训练流水线（**重点，约 1.5 页 + 2 张图**）

**写作要点**：

- **自动 plans**：基于 dataset fingerprint（spacing、尺寸、强度分布）自动决定 patch size、batch size、spacing target、normalization scheme、网络拓扑（2D / 3D fullres / 3D lowres / cascade）。
- **5-fold cross-validation**：AMOS22 划分 5 折，每折独立训练 Residual Encoder UNet；fold 0/1/2/3/4 输出各自 `checkpoint_best.pth` 和 validation Dice。
- **训练配置**：
    - 损失函数：Dice + CrossEntropy 联合损失
    - 优化器：SGD / Adam + poly learning rate scheduler
    - 数据增强：随机旋转、缩放、gamma 校正、镜像
    - TTA（test-time augmentation）：默认开启（mirroring）
- **5-fold soft ensemble**：5 个 fold 输出 5 张 softmax 概率图，按体素平均生成最终分割，提升边界稳定性。

**配图建议**：
- **图 3 训练流水线**：方框图"AMOS22 → 5-fold split → 5× ResidualEncoderUNet → 5× softmax → 算术平均 → argmax → 标签 mask"。
- **图 4 训练曲线**（**重点图**）：从 nnU-Net fold_X `training_log_*.txt` 提取 **train loss / val Dice** 画双轴折线图，5 个 fold 用不同颜色叠加；横轴 epoch，纵轴左 loss 右 Dice。建议 matplotlib 模板：`x = epoch, y1 = train_loss, y2 = val_dice`。
- **图 5 训练配置 / 超参表**：表格列出 fold 数、patch size、batch size、optimizer、scheduler、epochs、TTA、tile step。

> **如果暂时拿不到 nnU-Net 训练 log**，先用 README/REVIEW 里现有的"旧模型首跑 vs 新权重首跑"对比曲线和`SEGMENTATION_METRICS_SUMMARY.md`里的"5 折指标分布"做替代，并明确写"完整 nnU-Net 训练曲线由 nnU-Net `training_log_*.txt` 解析生成"。

#### 2.3 跨数据集自动 Taxonomy Remap（**创新点，约 1 页 + 1 张图**）

**写作要点**（**重点写，这块撑 30 分"先进性"**）：

- **问题**：FLARE22 label ID 顺序与 AMOS22 checkpoint 不一致（仅 label 2 = 右肾恰好对齐），直接 Dice 会因语义错位接近 0（`mean_dice = 0.073`）。
- **方法**：在 `server/taxonomy.py` 维护 FLARE22 标签表、器官别名映射（`postcava → ivc`、`gall_bladder → gallbladder` 等）；后端根据 label ID 集合自动检测数据集来源，按器官名把参考标签重映射到 checkpoint 标签空间。
- **显式 hint**：前端提供 `label_taxonomy = auto | AMOS22 | FLARE22` 选项；`auto` 模式保守，**仅在多个明确错位 ID 时才触发 remap**，避免 AMOS 原生标签被误判（2026-06-02 进一步加固 coverage 守卫 + `dataset_hint` 字段，应对 AMOS / FLARE 真实 unique IDs 不可分场景）。
- **结果**：FLARE22 Tr 0009 在线验证 `mean_dice` 从 `0.073` 提升到 `0.926`，`foreground_dice = 0.95`。
- **cache 链路配套**（2026-06-01 补丁）：FLARE22 cache hit 在前端直接显示历史离线指标，避免重新推理再次触发"语义错位"误判；cache_key 7 字段（`input_sha256 + checkpoint_sha256 + checkpoint_dataset_name + checkpoint_configuration + labels_source + runtime_target + inference_options`）保证预测缓存与 validation 缓存独立。

**配图建议**：
- **图 6 Taxonomy remap 流程**：左 FLARE22 label ID 表 → 中"按器官名重排"算法 → 右 AMOS22 label ID 表 + 重映射后 Dice 提升数据。

#### 2.4 GUI 部署与验证（约 0.4 页 + 1 张图）

**写作要点**（**短而精，GUI 在这里是部署验证手段，不是报告主体**）：

- 三正交视图（Axial / Sagittal / Coronal）联动浏览，十字线同步、窗宽窗位、overlay / split / side / difference 四种对比模式。
- 点击非背景 label → 弹出器官说明（解剖位置、功能、常见病变、分割注意点）。
- **影像量化模块**（纯前端 CPU，基于 mask + NIfTI spacing）：器官体积（mm³）、体素数、最大轴向截面积、包围盒尺寸、头足向长度估算、三维最长径估算。
- 报告导出：HTML / JSON（schema_version 1.1，含 `quantification`）/ PDF（浏览器原生打印）。
- **本地缓存演示**（2026-06-01）：相同请求命中 `server/work/<job_id>/prediction.nii.gz` 时跳过完整 nnU-Net 推理；前端展示 `cached_result` + `cache_source_job_id` + `historical` + `source_job_id` 四个字段；演示现场配合 `docs/local-cache-demo-runbook.md` 与 `tools/seed_demo_cache.py` 复现"cache hit 约 0.001s vs 真实推理约 218s"。

**配图建议**：
- **图 7 推理结果 + 量化报告截图**：`screenshots/orthogonal-current.png` 或 `screenshots/detail-rich.png`，1 张足以。

#### 2.5 服务器 5-GPU / 5-fold 部署（约 0.3 页 + 1 张图）

**写作要点**：

- 通过 `SEGMENTATION_SERVER_*` 环境变量配置 GPU / fold 映射、nnUNet 数据目录、输出根目录、评估脚本。
- 前端通过 `VITE_API_ENDPOINT` 指向服务器；后端按 `runtime_target=server` 串起 5-fold 并行 + soft ensemble。
- 校园网 Windows 前端直连 Ubuntu FastAPI 后端已跑通，FLARE 服务器轮次约 3 分 48 秒；AMOS 服务器轮次 `label_taxonomy=AMOS22` 显式 hint 已落地（与 FLARE 走同一套前端选项），可在下一轮服务器窗口复跑。

**配图建议**：
- **图 8 部署拓扑**："Windows GUI → 校园网 → Ubuntu 服务器（5×GPU）→ 5-fold 并行 → soft ensemble → 结果回填 GUI"。

---

### 第 3 章 结果展示（3 页，对应 20 分"结果准确性"）

#### 3.1 训练过程与逐器官指标（约 0.7 页 + 1–2 张表/图）

**写作要点**：训练侧给出 6 类医学影像主流指标（**mean Dice、foreground Dice、min Dice、Pixel Accuracy、HD、HD95、ASD**），用表格呈现（2026-06-03 起）。

| 病例 / 配置 | mean Dice | fg Dice | min Dice | Pixel Acc | mean HD (mm) | mean HD95 (mm) | mean ASD (mm) | 备注 |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| **新权重首跑**（AMOS 0117, fold0, quality） | **0.9248** | **0.9803** | 0.8466 | 0.9999 | 7.72 | 3.60 | 0.66 | 原生 AMOS 验证 |
| **正式质量**（AMOS 0117, quality + TTA） | 0.9248 | 0.9803 | 0.8466 | 0.9999 | 7.72 | 3.60 | 0.66 | 推荐基线 |
| **快速预览**（fast / TTA off） | 0.7772 | 0.9729 | 0.0000* | — | 10.28 | — | — | *label 14/15 假阳性 |
| **跨数据集 FLARE22**（remap 后） | 0.926 | 0.950 | 0.674 | — | 12.60 | — | — | FLARE22 标签按器官名 remap |
| **服务器 5-fold / FLARE22** | 0.891 | 0.951 | 0.657 | — | — | — | — | 校园网 smoke，约 3 分 48 秒 |

**配图建议**：
- **表 1 推理指标表**（上表）。
- **图 9 逐器官 Dice 条形图**（**重点图**）：横轴 15 个器官，纵轴 Dice，**新权重 vs 旧权重** 或 **AMOS 0117 vs FLARE22 remap** 用不同颜色叠加。脚本：`python tools/segmentation_metrics_summary.py --prediction ... --reference ... --output-dir ...`。

#### 3.2 5-fold soft ensemble vs 单 fold（约 0.4 页 + 1 张表/图）

**写作要点**：表格列出 fold 0/1/2/3/4 各自的 mean Dice 和 soft ensemble 后的 mean Dice，**典型结论是 soft ensemble 比单 fold 平均提升 0.5–1.5 Dice 点**，边界更稳定。**如果暂时没有完整 5-fold 数值**，可写"5-fold soft ensemble 设计目的"和"服务器 FLARE 轮次作为初步证据（mean Dice 0.891，与单 fold 接近）"，并标记为待补充。

**配图建议**：
- **图 10 5-fold Dice 分布 + ensemble**（柱状图 + 横线表示 ensemble 后的 mean）。

#### 3.3 推理配置消融（约 0.5 页 + 1 张表）

**写作要点**：

| 消融维度 | 配置 A | 配置 B | Dice 变化 | 耗时变化 |
|---|---|---|---:|---:|
| TTA | on (mirroring) | off | -0.15 | -22% |
| Tile step | 0.5 | 1.0 | -0.04 | -28% |
| Profile | quality | fast | -0.15 | -72% |
| 模型 | 2D | 3D fullres | 待补 | 显存↑ |

**配图建议**：
- **表 2 消融实验**：上表。

#### 3.4 跨数据集泛化（FLARE22 remap 前后对比，约 0.3 页 + 1 张图）

**写作要点**：把 FLARE22 在 remap 前 `mean_dice = 0.073`、remap 后 `0.926` 两个数字并列，配直方图 / 表格；强调"显式 `label_taxonomy=AMOS22` 修复了 AMOS 标签被误判为 FLARE22 的问题"。

**配图建议**：
- **图 11 remap 前后逐器官 Dice 对比图**。

#### 3.5 GUI 部署验证（约 0.3 页 + 2 张图）

**配图清单**（用 `screenshots/` 已有截图）：
- **图 12 三正交视图 + 推理结果**：`screenshots/desktop-final.png` 或 `screenshots/rail-layout-final.png`。
- **图 13 量化 / 报告导出**：从 GUI 导出一份真实报告截一张图（HTML 或 PDF）。
- **可选 图 14 本地缓存演示截图**：截一张"FLARE22 Tr 0009 cache hit + 历史 validation 摘要"作为工程亮点（见 `docs/local-cache-demo-runbook.md` 复现步骤）。

---

### 第 4 章 讨论与展望（约 0.5 页）

**写作要点**：
1. **优势**：nnU-Net 自动 plans + 5-fold soft ensemble + 跨数据集 remap + 服务器/本地双部署 + GUI 量化报告齐全 + **本地缓存演示（cache hit 0.001s vs 真实推理 218s）**。
2. **局限**：
    - `fast` profile 牺牲质量，引入 label 14/15 假阳性；
    - 高分辨率 CT（768×768×103）推理耗时显著增加（2.25× 计算量），需预降采样或 3D 模型优化；
    - 服务器 AMOS 轮次 `label_taxonomy=AMOS22` 显式 hint 已落地但尚未在 5-GPU 服务器窗口复跑；
    - 当前数据集为单中心公开数据，多中心验证待扩展；
    - `confidenceThreshold` 当前是质控提示，不会真实作用概率图；
    - 2026-06-01 之前 cache hit 在前端展示的 validation 摘要曾出现"张冠李戴"（FLARE22 命中错位 cache_source），已通过 cache 链路补丁修复（`_load_cached_validation_summary()` + `find_cached_prediction()` 按 `has_validation_summary, mtime` 排序 + `tools/rewrite_flare22_historical_summary.py` 按历史指标改写 `validation_summary.json`）。
3. **展望**：高分辨率 CT 预降采样 / 3D 模型；多中心数据集（TotalSegmentator、AMOS2022 后续版本）；云端 HTTPS + 鉴权；与 PACS / RIS 集成；扩展到肺部分割（FLARE 肺、ATM'22）；**跨数据集 cache 链路产品化（通用 `tools/rewrite_cached_validation_summary.py`）+ 演示启动脚本化**；**服务器端复跑 `label_taxonomy=AMOS22/FLARE22` 显式 hint，把服务器 AMOS 轮次纳入正式质量基线**；**auto taxonomy 边界加固需在更多非 AMOS 真实数据集（如 FLARE23、TotalSegmentator）上验证裸 ID 不可分场景下的稳定性**。

---

### 参考文献（≥ 8 条，统一格式）

必引：
- Isensee F, et al. **nnU-Net: a self-configuring method for deep learning-based biomedical image segmentation.** *Nat Methods* 2021.
- Ji Y, et al. **AMOS: A Large-Scale Abdominal Multi-Organ Benchmark for Versatile Medical Image Segmentation.** *NeurIPS 2022*.
- Ma J, et al. **FLARE22 Challenge: Fast and Low-resource Abdominal CT Organ Segmentation.** 2023.
- Isensee F, et al. **nnU-Net v2.** 2024.
- Dice LR. **Measures of the amount of ecologic association between species.** *Ecology* 1945.
- Huttenlocher DP, et al. **Comparing images using the Hausdorff distance.** *PAMI* 1993.
- Ronneberger O, et al. **U-Net.** *MICCAI 2015*.
- Çiçek Ö, et al. **3D U-Net.** *MICCAI 2016*.

---

## 3. 答辩 PPT 结构（20 分"答辩现场表现"）

| 页 | 内容 | 备注 |
|---|---|---|
| 1 | 封面 | 标题、团队、学校、指导教师 |
| 2 | 临床痛点 + 现有不足 | 配 1 张 CT 三视图 |
| 3 | 数据集与标签体系 | AMOS22 + FLARE22 |
| 4 | 训练流水线（5-fold + 自动 plans） | 配流水线图 |
| 5 | 训练曲线 + 5-fold 软投票 | 配训练曲线、5-fold Dice 分布 |
| 6 | 核心创新：跨数据集 taxonomy remap | 配流程图 + 前后对比 |
| 7 | 核心创新：服务器 5-GPU / 5-fold soft ensemble | 配部署拓扑 |
| 8 | 推理 / 消融指标表 | 配逐器官 Dice 条形图 |
| 9 | GUI 部署验证 | 三视图 + 量化报告 2 张 |
| 10 | 讨论 + 展望 + Q&A | 留 5 分钟答疑 |

---

## 4. 关键配图素材索引（团队直接对照拍/截/画）

| 编号 | 建议内容 | 已有素材 / 来源 | 章节 |
|---|---|---|---|
| 图 1 | 系统总览（GUI 主界面） | `screenshots/desktop-final.png` | 摘要 / 前言 |
| 图 2 | 15 器官标签色板表 | 用 `src/data/organDetails.ts` 做 | 2.1 |
| 图 3 | 训练流水线图 | 手画 / draw.io | 2.2 |
| 图 4 | 训练曲线（5-fold 叠加） | 解析 nnU-Net `training_log_*.txt` | 2.2（**重点**） |
| 图 5 | 训练超参表 | 整理 | 2.2 |
| 图 6 | Taxonomy remap 流程 | 手画 + remap 前后 Dice 数字 | 2.3（**重点**） |
| 图 7 | GUI 推理结果 + 量化 | `screenshots/orthogonal-current.png` | 2.4 |
| 图 8 | 服务器部署拓扑 | 手画 | 2.5 |
| 表 1 | 推理指标总表 | 现有 `SEGMENTATION_EXPERIMENT_COMPARISON.md` | 3.1 |
| 图 9 | 逐器官 Dice 条形图 | `tools/segmentation_metrics_summary.py` 重出 | 3.1（**重点**） |
| 图 10 | 5-fold Dice 分布 + ensemble | 解析 / 手画 | 3.2 |
| 表 2 | 消融实验表 | 整理 README/REVIEW 现有数据 | 3.3 |
| 图 11 | remap 前后对比 | 用现有 `0.073 vs 0.926` 数字 | 3.4 |
| 图 12 | GUI 三视图 + 推理结果 | `screenshots/rail-layout-final.png` | 3.5 |
| 图 13 | 量化 / 报告导出 | 实际导出一份报告截图 | 3.5 |

> **如果训练侧素材暂缺**：用 README / REVIEW / `SEGMENTATION_EXPERIMENT_COMPARISON.md` 中"旧模型首跑 vs 新权重首跑"对比、"5 折指标分布"、"quality vs fast"、FLARE remap 前后等已有数据替代，并在文中标注"完整 nnU-Net 训练日志由训练脚本生成后接入"。

---

## 5. 必须避免的扣分项

- ❌ 使用 Mimics / 3D Slicer / ITK-SNAP 等人工交互软件（命题明文禁止）。
- ❌ 把 FLARE22 remap 前 `0.073` 当模型失败基线（这是 taxonomy 错位）。
- ❌ 把 2026-05-31 服务器 AMOS 轮次 `mean_dice=0.076015` 当模型失败基线（`remap_source=FLARE22`，是 AMOS 原生标签被自动误 remap，**非模型质量问题**；已在 2026-06-02 auto taxonomy 边界加固中收口，待服务器窗口复跑确认 `remap_applied=false` 后才能纳入正式质量基线）。
- ❌ 把 persistent worker 没验证的"加速"写进结果。
- ❌ 写"未经验证的多中心 / 跨中心"结论。
- ❌ 提交真实 CT / NIfTI / checkpoint / 推理输出到 GitHub（`.gitignore` 已屏蔽）。
- ❌ 演示现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，把 `/api/samples` 退回成 1 个 case。
- ❌ 报告里写 cache hit "加速 X 倍"但没明确 cache_key 7 字段（容易让评审误以为只是 UI 缓存）。
- ❌ 正文前言超 2 页 / 整体超 12 页。
- ❌ 参考文献缺标注或格式混乱。
- ❌ 整篇都在介绍 GUI，训练过程只字未提（用户最强调的扣分点）。

---

## 6. 自检清单（提交前逐项打勾）

- [ ] 摘要含 `mean Dice = 0.925` / `foreground Dice = 0.98` 这类硬数字
- [ ] 前言 ≤ 2 页，方案 + 结果 + 讨论 ≤ 8 页，总 ≤ 12 页
- [ ] **方案设计 ≥ 2 页在讲训练**（数据 / 自动 plans / 5-fold CV / 损失函数 / 训练曲线）
- [ ] **结果展示有训练曲线 / 5-fold 分布 / 消融表**（训练为主体）
- [ ] GUI 章节 ≤ 1 页，仅作为部署验证手段
- [ ] 跨数据集 taxonomy remap 作为创新点重点写（占创新性 30 分大头）
- [ ] 关键硬数字有逐器官 Dice 表 / 图支撑
- [ ] GUI 截图 2–3 张，不喧宾夺主
- [ ] 讨论里写出 ≥ 3 条诚实局限
- [ ] 参考文献 ≥ 8 条，格式统一
- [ ] 答辩 PPT ≥ 10 页，留 Q&A 时间
- [ ] 全程未使用 Mimics / 3D Slicer / ITK-SNAP
- [ ] 仓库中不包含真实患者数据 / checkpoint
- [ ] **本地缓存演示**（如现场演示）：启动前确认 `SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json`，`/api/samples` 返回 4 个 case；FLARE22 cache hit 摘要标注"（历史离线缓存摘要）"
- [ ] **工程亮点口径一致**：cache hit 数字以 2026-06-01 cache 链路补丁后的 `0.893127 / 0.67373 / 0.949908` 为准（不是旧的 `0.891`）
- [ ] **taxonomy 修复口径一致**：不要把 0.076 当模型失败基线（已在 2026-06-02 auto taxonomy 边界加固中收口）

---

## 附录 A：项目核心信息速查

- **训练 / 推理框架**：nnU-Net v2（5-fold cross-validation + soft ensemble + TTA）
- **数据集**：AMOS22（训练 / 验证 15 个前景标签）、FLARE22（跨数据集 remap 验证）
- **15 个 AMOS22 前景标签**：spleen, right_kidney, left_kidney, gallbladder, esophagus, liver, stomach, aorta, ivc, pancreas, right_adrenal_gland, left_adrenal_gland, duodenum, bladder, prostate_or_uterus
- **训练后端**：`server/main.py`（FastAPI）、`server/server_inference.py`（5-GPU/5-fold 编排）、`server/taxonomy.py`（跨数据集 remap + 2026-06-02 auto taxonomy 边界加固）
- **GUI 前端**：`src/main.tsx`、`src/components/OrthogonalViewer.tsx`、`src/imaging/quantification.ts`、`src/inference/inferenceClient.ts`
- **报告导出**：`src/report/exportReport.ts`（HTML / JSON / PDF）
- **指标工具**：`tools/segmentation_metrics_summary.py`
- **缓存与本地演示工具**：`tools/seed_demo_cache.py`（预置 AMOS 0117 / FLARE22 Tr 0009 cache 命中样例）、`tools/rewrite_flare22_historical_summary.py`（按 2026-05-26 remap 后指标改写 FLARE22 历史 `validation_summary.json`）
- **本地缓存演示 runbook**：`docs/local-cache-demo-runbook.md`（7 步复现指南，前置 `SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json`）
- **测试**：`npm test`、`python tests/backendState.test.py`、`python tests/segmentationMetrics.test.py`
- **运行环境**：Windows 11 + RTX 4060 Laptop GPU 8 GB（本地）、Ubuntu 22.04 + 5× GPU（服务器 5-fold soft ensemble）
- **部署包**：`deployment-packages/server-runtime-package-20260531.zip`
- **核心数字**：AMOS 0117 mean Dice 0.925 / fg Dice 0.980 / HD 7.72 mm；FLARE22 remap 后 mean Dice 0.926；服务器 5-fold / FLARE22 约 0.891；**FLARE22 cache hit `02da885c97d8` 显示 mean_dice=0.893127 / min_dice=0.67373 / fg=0.949908（"（历史离线缓存摘要）"）**。
