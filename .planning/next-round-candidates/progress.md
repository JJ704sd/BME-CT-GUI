# 下一轮候选任务进度

## 2026-06-01：本地缓存演示 + cache 链路补丁已完成，进入下一轮规划

**状态：** 本地缓存演示 7 步 + 晚间 cache 链路补丁已完成，下一轮任务规划见本目录 `task_plan.md`（已更新到 2026-06-01）。

**背景：** 2026-06-01 在 BME 竞赛 PPT 演示窗口前完成"本地缓存演示 7 步"，AMOS 0117 cache hit + FLARE22 Tr 0009 真实推理 218s + FLARE22 cache hit 0.001s 的对照链路已落地；现场复测时发现 FLARE22 cache hit 显示的 validation 摘要来自错位 cache_source（`009d4efdc5f6`），已完成 cache 链路补丁：`_load_cached_validation_summary()` + `complete_cached_job()` historical 回退；`find_cached_prediction()` 优先选有 `validation_summary.json` 的 cache_source；`tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的历史摘要；前端 `getValidationStatusCopy()` 增加 cachedResult 参数；`tests/backendState.test.py` 新增 2 个回归测试。9 份核心文档已同步；新增 `tools/rewrite_flare22_historical_summary.py`。

## 2026-05-31：taxonomy fix 和高分辨率推理已完成

**状态：** 完成。详见 `.planning/label-taxonomy-server-validation/` 和 `.planning/high-resolution-inference-optimization/`。

**背景：** 2026-05-31 完成了显式 `label_taxonomy` 修复和 AMOS CT 高分辨率推理。taxonomy fix 验证通过（job `d56bcff76a8b`，`remap_applied=false`），AMOS CT 推理完成（job `ad3d14eba3de`，fast profile，mean_dice=0.77724）。新部署包 `server-runtime-package-20260531.zip` 已创建。

## 上一轮完成情况

### 2026-06-01-local-cache-demo [完成]

- [x] 后端依赖补充（`fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30`）
- [x] 参考病例 JSON 配置（`SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json`）
- [x] 预热脚本 `tools/seed_demo_cache.py`
- [x] Phase A：AMOS 0117 cache hit（job `aea4e7cdbaf0`）
- [x] Phase B：FLARE22 Tr 0009 真实推理（job `0aa7323a4c01`，218s）
- [x] Phase C：FLARE22 Tr 0009 cache hit（job `02da885c97d8`，0.001s）
- [x] 运行手册、设计稿、实施计划
- [x] 9 份核心文档同步
- [x] 4 份 planning 文档落地

### label-taxonomy-server-validation [部分完成]

### 2026-06-02 detect_dataset 二轮收紧 + dataset_hint 字段 [完成]

- [x] `detect_dataset()` 0.85 coverage 守卫（`taxonomy=auto` 时 AMOS 真实 1-13 标签不再被误判为 FLARE22）
- [x] 前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy`（AMOS → AMOS22、FLARE22 → FLARE22、其他保持原值）
- [x] `Job.dataset_hint` + 前端 `referenceCaseDatasetHint` 状态机（上传自定义 NIfTI 时自动清空）
- [x] `tests/backendState.test.py` 新增 AMOS 1-13 / FLARE22 1-13 / Partial {1,3} 真实 case 测试 + `test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto`
- [x] `npm test` / `python tests/backendState.test.py` / `npm run build` 全过

### 2026-06-03 质量评估指标扩展 + surface_distances 2 EDT [完成]

- [x] `ValidationSummary` 增补 12 字段（Pixel Accuracy 4 项 + HD/HD95/ASD 9 项 + `surface_distance_unit` + `spacing`）
- [x] `LabelMetric` 增补 4 列（`pixel_accuracy` / `asd` / `hd` / `hd95`）
- [x] `server/main.py surface_distances()` 把单 label EDT 调用从 6 次合并到 2 次；旧 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 保留为 legacy
- [x] `src/report/exportReport.ts` 新增 3 个 metric group（区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD，共 19 张卡片）
- [x] AMOS 0117 quality cache hit validation 实测 38.86s → 16.78s（约 2.3× 加速）
- [x] 3 个新增回归测试（1e-9 精度、EDT 计数恒为 2、wall-time 加速比 ≥30%）
- [x] 6-03 6 类指标基线数值：mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm
- [x] `npm test` / `python tests/backendState.test.py` / `npm run build` 全过

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

## 下一轮候选任务（2026-06-01 起更新）

### 1. AMOS 预热预测复跑 [新增，待开始]

**优先级：** 高

**目标：** 用 quality profile 复跑 AMOS 0117，替换 cache demo Phase A 命中的 review status 预测 `009d4efdc5f6`。

**关键步骤：**

- [ ] 本地以 `runtime_target=local`、`profile=quality`、`label_taxonomy=AMOS22` 重新提交 AMOS 0117 job
- [ ] 确认 `validation_status` 不再是 review，stomach Dice 恢复到 0.8 以上
- [ ] 用 `tools/seed_demo_cache.py` 把新预测 entry 替换 `009d4efdc5f6`
- [ ] 更新 `docs/local-cache-demo-runbook.md` 中的 job 表格

### 2. server mode gating 修复 [待开始]

**优先级：** 高

**目标：** `runtime_target=server` 创建 job 时只检查 server runtime 必需路径。

**关键步骤：**

- [ ] 修改 `/api/segment/jobs` 路径检查逻辑
- [ ] `runtime_target=server` 只检查 `evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`
- [ ] `runtime_target=local` 才检查本地 `dataset.json`、`plans`、`checkpoint`、`python.exe`
- [ ] 确认 `/api/models` 不再因本地文件缺失而报错

### 3. 服务器 validation 复跑 [待开始]

**优先级：** 高

**前置条件：** server gating 修复完成

**目标：** 用显式 `label_taxonomy=AMOS22` 复跑服务器 AMOS，确认 `remap_applied=false`。

**关键步骤：**

- [ ] 复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`
- [ ] 复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`
- [ ] 记录服务器质量基线指标

### 4. 高分辨率推理优化 [待开始]

**优先级：** 中高

**目标：** 实现预降采样，缩短高分辨率 CT 推理时间。

**关键步骤：**

- [ ] 评估预降采样方案可行性（768→512，预期推理时间减少约 50%）
- [ ] 在前端添加降采样选项
- [ ] 在后端实现降采样逻辑
- [ ] 测试降采样后的推理时间和分割质量
- [ ] 评估是否需要上采样到原始分辨率

### 5. cache demo 脚本化 + runbook 自动校验 [新增，待开始]

**优先级：** 中

**目标：** 把 7 步 demo 包成 `tools/run_local_cache_demo.py`；写 `tests/cacheDemoRunbook.test.py` 自动确认 runbook 中提到的 4 个约束仍成立。

### 6. 跨数据集标签评估增强 [待开始]

**优先级：** 中

**目标：** 增强未知数据集和异常指标的解释能力。

**关键步骤：**

- [ ] 对 remap 覆盖率不足或未知标签 ID 给出明确 UI 警告
- [ ] 为单 label 或少量标签文件增加显式数据集 hint 入口
- [ ] 在 per-label 表格中标出体素量级差异异常
- [ ] 记录 `remap_mapping` 的用户可读摘要

### 7. 文档与验收口径再同步 [持续]

**优先级：** 中

**目标：** 确保文档持续跟随代码变化。

**关键步骤：**

- [ ] 后续代码或配置变化后，及时同步核心文档
- [ ] 坚持"新工程链路不混入旧指标"的口径

## 当前结论

2026-06-01 本地缓存演示已完成；下一轮优先复跑 AMOS 预热预测、修复 server gating、然后复跑服务器 validation，最后实现高分辨率推理优化。

---

*更新日期：2026-06-01*

