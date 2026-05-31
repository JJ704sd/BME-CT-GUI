# 下一轮候选任务解释

## 为什么需要这个说明

2026-05-31 项目已完成两项关键里程碑：显式 `label_taxonomy` 修复和 AMOS CT 高分辨率推理。本文档解释下一轮任务的背景和优先级依据。

## 当前项目状态

### 已完成

1. **label_taxonomy 修复**：`auto|AMOS22|FLARE22` 参数已实现，`detect_dataset()` 更保守（标签 ID 是 checkpoint 子集时不触发 remap），验证 job `d56bcff76a8b` 确认 AMOS22 选择时 `remap_applied=false`。
2. **AMOS CT 高分辨率推理**：768×768×103 输入，fast profile，mean_dice=0.77724（低于 quality 的 0.924791，符合预期）。
3. **部署包**：`server-runtime-package-20260531.zip` 已创建，包含更新后的 `taxonomy.py`。

### 待完成

1. **server mode gating**：`runtime_target=server` 创建 job 时仍可能因本地 Windows nnUNet 文件缺失而 503。
2. **服务器 validation 复跑**：需用显式 `label_taxonomy=AMOS22` 复跑 AMOS，确认 `remap_applied=false`。
3. **高分辨率推理优化**：768×768 输入面积是标准 512×512 的 2.25 倍，推理时间显著延长。

## 优先级依据

### 高优先级：server gating 修复

**原因**：服务器推理链路已跑通，但创建 job 时的路径检查仍依赖本地 Windows 文件。这会阻塞服务器模式的正常使用。

**影响范围**：`server/main.py` 中 `/api/segment/jobs` 的路径检查逻辑。

### 高优先级：服务器 validation 复跑

**原因**：2026-05-31 的服务器 AMOS 轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808`，且 `remap_source=FLARE22`，疑似 taxonomy 误判。需要用显式 `label_taxonomy=AMOS22` 复跑确认。

**影响范围**：服务器质量基线的可信度。

### 中高优先级：高分辨率推理优化

**原因**：768×768 输入导致推理时间显著延长（fast profile 约 6.4 分钟，quality 预计约 23 分钟）。预降采样（768→512）可缩短推理时间约 50%。

**影响范围**：前端推理选项、后端降采样逻辑、结果上采样。

### 中优先级：跨数据集标签评估增强

**原因**：自动 remap 已可用，但对未知数据集和异常指标的解释能力仍需增强。

**影响范围**：前端 UI 警告、报告导出。

## 与其他 planning 文档的关系

- `.planning/label-taxonomy-server-validation/`：taxonomy fix 已完成，server gating 和 validation 复跑是下一步。
- `.planning/high-resolution-inference-optimization/`：推理已完成，优化方案评估是下一步。
- `.planning/campus-network-and-public-access/`：校园网 smoke 已跑通，稳定性补验是下一步。

## 执行顺序建议

1. **server gating 修复**：解除服务器模式的阻塞点。
2. **服务器 validation 复跑**：确认 AMOS 服务器质量基线。
3. **高分辨率推理优化**：实现预降采样，缩短推理时间。
4. **跨数据集标签评估增强**：补单 label hint、remap 覆盖率提示。
5. **文档与验收口径再同步**：确保文档持续跟随代码变化。

---

*更新日期：2026-05-31*
