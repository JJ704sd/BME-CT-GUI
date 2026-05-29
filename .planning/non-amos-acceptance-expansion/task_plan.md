# 非 AMOS 验收扩展规划

**目标：** 在不提交私有影像数据的前提下，用本地非 AMOS CT 病例扩展 GUI 验收证据。

**当前基线：** `main`，提交 `dafe400 fix: close segmentation validation regressions`。

**核心规则：** `quality` 仍是正式验收 profile。`fast` 只能作为预览或对照路径，必须继续标注“需人工复核”。

**2026-05-28 现状：** 自动 taxonomy remap 已实现。FLARE22 这类已知标签体系不再只能归为 `manual-only`；用户上传标签文件后，后端可按器官名重映射并产出在线 validation。跨数据集指标仍必须与 AMOS 原生标签指标分开解释。

**2026-05-29 现状：** 部分 FLARE22 标签在至少两个明确错位 label 时可自动 remap；单 label 文件仍不能自动推断数据集来源。缓存命中只复用预测 NIfTI，当前标签的 validation 必须重新计算。

## 状态

- [x] 确认 main 基线已通过 `npm test` 和 `npm run build`。
- [x] 确认 tracked 示例 registry 只包含 AMOS 和占位外部样例。
- [x] 确认本地 `nnunetv2_files/` 包含 AMOS 0117 资源和当前 checkpoint。
- [x] 识别候选非 AMOS `.nii` / `.nii.gz` 文件。
- [x] 创建私有本地参考病例 registry。
- [x] 验证 `/api/samples` 对注册病例的 metadata。
- [x] 完成 FLARE22 Tr 0009 的在线推理、离线 remap 指标和自动 remap 在线验证记录。
- [x] 用证据更新验收、指标和对比文档。
- [x] 增加模块级代码讲解文档：`CODE_MODULE_GUIDE.md`。
- [ ] 为更多非 AMOS 病例执行 GUI 人工验收。
- [ ] 仅在标签语义可兼容或可 remap 时记录分割指标。

## 规则与约束

- 不提交真实 CT、NIfTI、checkpoint、prediction 或私有患者路径。
- 真实本地病例 registry 放在被忽略的位置，优先使用 `nnunetv2_files/reference_cases.local.json`，再用 `SEGMENTATION_REFERENCE_CASES_JSON` 指向它。
- `reference_cases.example.json` 只作为公开 schema / example，不写入私有真实路径。
- 只有当病例有真实标签，且标签语义与 checkpoint 匹配或可通过 `server/taxonomy.py` 自动 remap 时，才记录 Dice、IoU 或 Hausdorff 指标。
- 对单 label 或 remap 覆盖率不足的病例，先记录为人工复核或显式数据集 hint 待补，不声明自动指标通过。
- 无标签病例只记录浏览、推理、结果下载、GUI 回填和人工复核。
- 基准和推理输出保留在 `.test-output/`。
- 原始模型指标与任何后处理实验指标必须分开。

## 私有病例登记模板

| 字段 | 要求 |
|---|---|
| `case_id` | 稳定本地 ID，例如 `flare22_tr_0009` |
| `dataset` | 数据集来源，例如 `FLARE22`、`Local`、`External` |
| `original_path` | 本地 CT 原图路径，不提交 |
| `label_path` | 本地标签路径或 `none` |
| `has_label` | `true` / `false` |
| `expected_validation` | 标签语义匹配或可 remap 时为 `metrics`，否则为 `manual-only` |
| `notes` | 解剖覆盖、spacing、隐私和不确定性说明 |

## 已完成证据

### FLARE22 Tr 0009 未上传标签在线推理

- job id：`86b0153d0a73`
- profile：`quality`
- cached_result：`false`
- duration_seconds：`237.323`
- result_size_bytes：`120761`
- registry 行为：`validation_available=false`
- 解释：未上传标签且不作为 AMOS 原生 label 注册，因此后端自动 validation 关闭。

### FLARE22 Tr 0009 离线 remap 指标

- mean Dice：`0.893127`
- foreground Dice：`0.949908`
- min Dice：`0.673730`
- weakest label：`duodenum`
- 解释：这是离线按器官名 remap 的跨数据集对照，不是 AMOS 原生标签验证。

### FLARE22 Tr 0009 自动 remap 在线验证

- job id：`a717dacf42d3`
- profile：`quality`
- cached_result：`false`
- remap_applied：`true`
- remap_source：`FLARE22`
- mean Dice：`0.926`
- validation status：`passed`
- 解释：自动 remap 后，跨数据集在线 validation 链路已打通，但指标仍应与 AMOS 原生标签指标分开解释。

## 后续阶段

### Phase 1：扩展病例池

- [ ] 在本地选择更多非 AMOS CT 原图。
- [ ] 为每个病例记录 case id、dataset、shape、spacing、标签状态和隐私边界。
- [ ] 对无标签病例只做浏览、推理和人工复核。
- [ ] 对有标签病例先判断是否可直接匹配或自动 remap。

### Phase 2：跨数据集指标解释增强

- [ ] 对未知数据集显示“无法自动重映射”的 UI 提示。
- [ ] 对 remap 覆盖率不足的标签显示人工映射建议。
- [ ] 为单 label 文件增加显式数据集 hint 设计，避免自动误判。
- [ ] 在报告导出中记录 `remap_applied`、`remap_source` 和关键映射摘要。

### Phase 3：验收文档更新

- [ ] 新增病例后同步更新 `ACCEPTANCE.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md` 和 `SEGMENTATION_RECENT_ROUNDS.md`。
- [ ] 明确每个病例是 AMOS 原生、跨数据集 remap、无标签人工复核还是快速预览。
- [ ] 不把缓存回填耗时写成首次未缓存推理耗时。

## 停止条件

- 未知标签 taxonomy 时停止自动指标解释，只保留人工复核。
- remap 失败或覆盖不足时，不声明模型质量通过。
- 任何包含私有路径、真实 CT 或 checkpoint 的文件不得进入提交。
