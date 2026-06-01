# 下一轮候选任务解释

## 为什么需要这个说明

2026-06-01 项目已连续完成两项里程碑：本地缓存演示 7 步（AMOS cache hit → FLARE 真实推理 → FLARE cache hit），以及晚间的 cache 链路补丁（FLARE22 cache hit 现在能正确显示 0.893/0.674/0.950 + "（历史离线缓存摘要）"）。本文档解释下一轮任务的背景和优先级依据。

## 当前项目状态

### 已完成

1. **本地缓存演示 7 步**：AMOS 0117 cache hit（`aea4e7cdbaf0`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）。
2. **cache 链路补丁**：`_load_cached_validation_summary()` + `complete_cached_job()` 增加 historical 回退；`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序；`tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的 `validation_summary.json`；前端 `getValidationStatusCopy()` 增加 cachedResult 参数；`tests/backendState.test.py` 新增 2 个回归测试。
3. **env var 强制**：`SEGMENTATION_REFERENCE_CASES_JSON` 必须指向 `examples/reference_cases.json`（或 `nnunetv2_files/reference_cases.local.json`）才能让 `/api/samples` 暴露 4 个 reference case；runbook 已把这一项写在最前面。

### 待完成

1. **server mode gating**：`runtime_target=server` 创建 job 时仍可能因本地 Windows nnUNet 文件缺失而 503。
2. **服务器 validation 复跑**：需用显式 `label_taxonomy=AMOS22` 复跑 AMOS，确认 `remap_applied=false`。
3. **高分辨率推理优化**：768×768 输入面积是标准 512×512 的 2.25 倍，推理时间显著延长。
4. **跨数据集 cache 链路产品化**：当前 cache 链路补丁只针对 FLARE22 Tr 0009 + 0aa7323a4c01 这一对 cache_source；其他 cache_source 命中时若没有 `validation_summary.json`，仍然会显示"无历史验证摘要"。
5. **AMOS 预热预测复跑**：cache demo Phase A 命中的 `009d4efdc5f6` 仍是 2026-05-23 历史 review 状态（stomach 0.556）。

## 优先级依据

### 高优先级：AMOS 预热预测复跑

**原因**：cache demo Phase A 命中的是 2026-05-23 历史 review 预测（stomach 0.556），不能在 PPT 演示中当成 AMOS 质量基线。用 quality profile 复跑后可换更新预测，让 Phase A 在 cache demo 中挂上"非 review 状态预测"。

**影响范围**：`tools/seed_demo_cache.py`、`docs/local-cache-demo-runbook.md` 表格、PPT 演示口径。

### 高优先级：server gating 修复

**原因**：服务器推理链路已跑通，但创建 job 时的路径检查仍依赖本地 Windows 文件。这会阻塞服务器模式的正常使用。

**影响范围**：`server/main.py` 中 `/api/segment/jobs` 的路径检查逻辑。

### 高优先级：服务器 validation 复跑

**原因**：2026-05-31 的服务器 AMOS 轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808`，且 `remap_source=FLARE22`，疑似 taxonomy 误判。需要用显式 `label_taxonomy=AMOS22` 复跑确认。

**影响范围**：服务器质量基线的可信度。

### 中高优先级：高分辨率推理优化

**原因**：768×768 输入导致推理时间显著延长（fast profile 约 6.4 分钟，quality 预计约 23 分钟）。预降采样（768→512）可缩短推理时间约 50%。

**影响范围**：前端推理选项、后端降采样逻辑、结果上采样。

### 中优先级：跨数据集 cache 链路产品化

**原因**：当前 cache 链路补丁只针对 FLARE22 Tr 0009 这一具体 cache_source（`0aa7323a4c01`）。其他 cache_source 命中时如果 cache_source 的 output 没有 `validation_summary.json`，UI 仍会显示"无历史验证摘要"。需要把"按历史指标改写 cache_source 摘要"做成可复用工具。

**影响范围**：`tools/`、`server/main.py` 的 `complete_cached_job()` 回退路径、未来新增数据集的接入流程。

### 中优先级：跨数据集标签评估增强

**原因**：自动 remap 已可用，但对未知数据集和异常指标的解释能力仍需增强。

**影响范围**：前端 UI 警告、报告导出。

## 与其他 planning 文档的关系

- `.planning/2026-06-01-local-cache-demo/`：本地缓存演示 + cache 链路补丁已完成。
- `.planning/label-taxonomy-server-validation/`：taxonomy fix 已完成，server gating 和 validation 复跑是下一步。
- `.planning/high-resolution-inference-optimization/`：推理已完成，优化方案评估是下一步。
- `.planning/campus-network-and-public-access/`：校园网 smoke 已跑通，稳定性补验是下一步。

## 执行顺序建议

1. **AMOS 预热预测复跑**：让 cache demo Phase A 命中一个非 review 状态预测。
2. **server gating 修复**：解除服务器模式的阻塞点。
3. **服务器 validation 复跑**：确认 AMOS 服务器质量基线。
4. **高分辨率推理优化**：实现预降采样，缩短推理时间。
5. **跨数据集 cache 链路产品化**：把 cache 链路补丁做成通用机制。
6. **跨数据集标签评估增强**：补单 label hint、remap 覆盖率提示。
7. **文档与验收口径再同步**：确保文档持续跟随代码变化。

---

*更新日期：2026-06-01*
