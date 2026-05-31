# 下一轮候选任务进度

## 2026-05-31：taxonomy fix 和高分辨率推理已完成，进入下一轮规划

**状态：** 上一轮任务已完成，下一轮任务规划中。

**背景：** 2026-05-31 完成了显式 `label_taxonomy` 修复和 AMOS CT 高分辨率推理。taxonomy fix 验证通过（job `d56bcff76a8b`，`remap_applied=false`），AMOS CT 推理完成（job `ad3d14eba3de`，fast profile，mean_dice=0.77724）。新部署包 `server-runtime-package-20260531.zip` 已创建。

## 上一轮完成情况

### label-taxonomy-server-validation [部分完成]

- [x] taxonomy 误判确认
- [x] 显式 label taxonomy hint 实现
- [x] 测试与验证（job `d56bcff76a8b`）
- [x] 部署包创建
- [ ] server mode gating 修复
- [ ] 服务器 validation 复跑

### high-resolution-inference-optimization [部分完成]

- [x] 速度瓶颈分析
- [x] 推理完成（job `ad3d14eba3de`）
- [x] 文档更新
- [ ] 优化方案评估
- [ ] 优化方案实现

## 下一轮候选任务

### 1. server mode gating 修复 [待开始]

**优先级：** 高

**目标：** `runtime_target=server` 创建 job 时只检查 server runtime 必需路径。

**关键步骤：**

- [ ] 修改 `/api/segment/jobs` 路径检查逻辑
- [ ] `runtime_target=server` 只检查 `evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`
- [ ] `runtime_target=local` 才检查本地 `dataset.json`、`plans`、`checkpoint`、`python.exe`
- [ ] 确认 `/api/models` 不再因本地文件缺失而报错

### 2. 服务器 validation 复跑 [待开始]

**优先级：** 高

**前置条件：** server gating 修复完成

**目标：** 用显式 `label_taxonomy=AMOS22` 复跑服务器 AMOS，确认 `remap_applied=false`。

**关键步骤：**

- [ ] 复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`
- [ ] 复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`
- [ ] 记录服务器质量基线指标

### 3. 高分辨率推理优化 [待开始]

**优先级：** 中高

**目标：** 实现预降采样，缩短高分辨率 CT 推理时间。

**关键步骤：**

- [ ] 评估预降采样方案可行性（768→512，预期推理时间减少约 50%）
- [ ] 在前端添加降采样选项
- [ ] 在后端实现降采样逻辑
- [ ] 测试降采样后的推理时间和分割质量
- [ ] 评估是否需要上采样到原始分辨率

### 4. 跨数据集标签评估增强 [待开始]

**优先级：** 中

**目标：** 增强未知数据集和异常指标的解释能力。

**关键步骤：**

- [ ] 对 remap 覆盖率不足或未知标签 ID 给出明确 UI 警告
- [ ] 为单 label 或少量标签文件增加显式数据集 hint 入口
- [ ] 在 per-label 表格中标出体素量级差异异常
- [ ] 记录 `remap_mapping` 的用户可读摘要

### 5. 文档与验收口径再同步 [持续]

**优先级：** 中

**目标：** 确保文档持续跟随代码变化。

**关键步骤：**

- [ ] 后续代码或配置变化后，及时同步核心文档
- [ ] 坚持"新工程链路不混入旧指标"的口径

## 当前结论

上一轮 taxonomy fix 和高分辨率推理已完成。下一轮优先修复 server gating，然后复跑服务器 validation，最后实现高分辨率推理优化。

---

*更新日期：2026-05-31*
