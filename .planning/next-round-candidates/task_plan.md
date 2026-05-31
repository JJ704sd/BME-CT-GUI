# 下一轮候选任务规划

**范围：** 基于 2026-05-31 项目现状，规划下一轮可执行任务。

**当前状态：** 三大目标已接近收口：CT 浏览、三正交联动、在线 nnUNetv2 推理、SSE 进度、取消、预测缓存、标签上传、自动 taxonomy remap、报告导出和主要验收文档均已落地。2026-05-31 已完成显式 `label_taxonomy=auto|AMOS22|FLARE22` 修复（`detect_dataset()` 更保守）、AMOS CT 高分辨率推理（768×768×103，fast profile，mean_dice=0.77724）和新部署包 `server-runtime-package-20260531.zip`。当前阻塞点转为 `runtime_target=server` 创建任务不应依赖本地 nnUNet 文件、服务器 AMOS validation 需用显式 taxonomy 复跑、高分辨率 CT 推理需优化。

**本轮已完成（2026-05-31）：**

- 显式 `label_taxonomy=auto|AMOS22|FLARE22`：`detect_dataset()` 更保守，标签 ID 是 checkpoint 子集时不触发 remap。
- 验证 job `d56bcff76a8b`：AMOS22 选择时 `remap_applied=false`，`mean_dice=0.77724`。
- AMOS CT 高分辨率推理：job `ad3d14eba3de`，768×768×103，fast profile，mean_dice=0.77724。
- 新部署包：`server-runtime-package-20260531.zip`，包含更新后的 `taxonomy.py`。
- 文档同步：9 份核心文档已更新，`.planning/` 历史文档已更新。

---

## 推荐下一轮任务

### 1. server mode gating 修复

**优先级：** 高

**前置文档：** `.planning/label-taxonomy-server-validation/`

**目标：** `runtime_target=server` 创建 job 时只检查 server runtime 必需路径，不再要求本地 Windows `dataset.json/plans/checkpoint/python.exe`。

**关键步骤：**

1. 修改 `/api/segment/jobs` 路径检查逻辑。
2. `runtime_target=server` 只检查 `SEGMENTATION_SERVER_EVALUATE_SCRIPT`、`SEGMENTATION_SERVER_DATASET_JSON`、`SEGMENTATION_SERVER_NNUNET_RAW`、`SEGMENTATION_SERVER_NNUNET_PREPROCESSED`、`SEGMENTATION_SERVER_NNUNET_RESULTS`、`SEGMENTATION_SERVER_OUTPUT_ROOT`。
3. `runtime_target=local` 才检查本地 `dataset.json`、`plans`、`checkpoint`、`python.exe`。
4. 确认 `/api/models` 不再因本地文件缺失而报错。

**风险：** 该修复只影响 job 创建时的路径检查，不改变 nnUNet 原始预测输出。

---

### 2. 服务器 validation 复跑

**优先级：** 高

**前置条件：** server gating 修复完成

**目标：** 用显式 `label_taxonomy=AMOS22` 复跑服务器 AMOS，确认 `remap_applied=false` 后纳入正式质量基线。

**关键步骤：**

1. 复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`。
2. 复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`。
3. 记录服务器质量基线指标（mean Dice、min Dice、foreground Dice）。
4. 与本地 quality 基线（`b3c528cc9e20`，mean Dice 0.924780）对比。

**风险：** 服务器链路可运行不等于质量基线已完成；AMOS 服务器指标必须先排除 taxonomy 误判。

---

### 3. 高分辨率推理优化

**优先级：** 中高

**前置文档：** `.planning/high-resolution-inference-optimization/`

**目标：** 实现预降采样，缩短高分辨率 CT 推理时间。

**关键步骤：**

1. 评估预降采样方案可行性（768→512，预期推理时间减少约 50%）。
2. 在前端添加降采样选项（如 `inference_resolution=original|downsampled_512`）。
3. 在后端实现降采样逻辑（使用 `scipy.ndimage.zoom` 或类似方法）。
4. 测试降采样后的推理时间和分割质量。
5. 评估是否需要上采样到原始分辨率。

**风险：** 降采样可能丢失细节信息；所有速度和质量结论都必须绑定 job id、输入、checkpoint、profile 和指标。

---

### 4. 跨数据集标签评估增强

**优先级：** 中

**目标：** 在自动 remap 已可用的基础上，增强未知数据集和异常指标的解释能力。

**候选改进：**

- 对 remap 覆盖率不足或未知标签 ID 给出明确 UI 警告。
- 为单 label 或少量标签文件增加显式数据集 hint 入口。
- 在 per-label 表格中标出体素量级差异异常、Dice 为 0 的疑似错位标签。
- 记录 `remap_mapping` 的用户可读摘要，便于报告导出。

**风险：** 需要避免把 remap 后的跨数据集指标写成 AMOS 原生验证。

---

### 5. 文档与验收口径再同步

**优先级：** 中

**目标：** 继续保持 README、ACCEPTANCE、REVIEW、指标汇总和近期轮次记录与代码现状一致。

**关键步骤：**

1. 在后续代码或配置变化后，及时同步 9 份核心文档的中文主体说明。
2. 对 `SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md` 和 `SEGMENTATION_RECENT_ROUNDS.md` 继续坚持"新工程链路不混入旧指标"的口径。

**风险：** 这类工作本身不难，但容易在没有同步代码现状时写入过时结论。

---

### 6. 多模型支持准备

**优先级：** 低（等待新 checkpoint）

**目标：** 当前只有 AMOS22 单模型，为未来多模型切换预留结构。

**候选改进：**

- `modelOptions` 从硬编码改为从 `/api/models` 动态获取。
- 后端增加模型目录扫描和模型信息 API。
- 前端模型卡片改为可点击切换。

**风险：** 没有新 checkpoint 时难以完成真实验收。

---

## 推荐执行顺序

1. **server mode gating 修复**：解除服务器模式的阻塞点。
2. **服务器 validation 复跑**：确认 AMOS 服务器质量基线。
3. **高分辨率推理优化**：实现预降采样，缩短推理时间。
4. **跨数据集标签评估增强**：补单 label hint、remap 覆盖率提示和报告摘要。
5. **文档与验收口径再同步**：确保文档持续跟随代码变化。
6. **多模型支持准备**：等待新模型或新 checkpoint 后再启动。

---

*更新日期：2026-05-31*
