# 标签打分优化规划

**目标：** 解决跨数据集在线验证 Dice 无意义的问题，使 GUI 质量评估面板对任意 CT + 标签组合都能给出有参考价值的分数。

**当前基线：** 标签文件传输链路已修复（2026-05-27）；2026-05-28 已实现自动 taxonomy remap，FLARE22 在线验证从 mean_dice=0.073 提升到 0.926（job `a717dacf42d3`）。2026-05-29 已移除上传文件名调试日志，并修复缓存命中复用旧 validation 的风险。

## 状态

- [x] 修复标签文件传输 bug（UploadRole 扩展 + 标签拖拽区域 + 后端保存路径验证）
- [x] 验证标签文件能正确到达后端并触发 validation
- [x] 确认 Dice 低的根因是 taxonomy 错位而非模型质量问题
- [x] 收集近三轮在线推理数据并建立滚动记录文档
- [x] 实现 taxonomy 自动 remap
- [x] GUI 展示自动重映射提示
- [ ] GUI 异常指标提示增强
- [ ] AMOS 大体数据耗时优化
- [x] 标签传输稳定性观察改为测试和 job state 验证，不再保留上传文件名日志
- [ ] 单 label 或少量标签文件的显式数据集 hint

## 近三轮数据

| 轮次 | job_id | 病例 | 标签 | 耗时 | mean_dice | 问题 |
|---|---|---|---|---|---|---|
| 1 | `a717dacf42d3` | FLARE22 512×512×87 | 已上传 | ~220s | 0.926 | 自动 remap 后通过 |
| 2 | `bf20f0ec4456` | FLARE22 512×512×87 | 已上传 | 223s | 0.073 | remap 前 taxonomy 错位 |
| 3 | `b6e04914f852` | AMOS 512×512×568 | 内置 | 1054s | — | 未记录 |

离线 remap 参考：FLARE22 mean_dice=0.893, min_dice=0.674, fg_dice=0.950。自动 remap 在线验证最新记录：mean_dice=0.926，validation status=`passed`。

---

## Phase 1：taxonomy 自动 remap（P0）

**目标：** 当用户上传的标签文件 ID 体系与当前 checkpoint 不一致时，自动按器官名重映射，在线验证 mean_dice 从 0.073 提升到可解释区间。

**状态：** 已完成。当前实现位于 `server/taxonomy.py`，并通过 FLARE22 Tr 0009 在线验证得到 mean_dice=0.926。

### 1.1 后端：检测 taxonomy 不匹配

文件：`server/main.py`，函数 `validate_against_custom_label()`

- [x] 读取 checkpoint 的 `dataset.json` 获取 `labels` 字段（ID→器官名映射）
- [x] 读取用户标签文件中出现的 ID 集合
- [x] 按器官名建立映射表
- [x] 检测 FLARE22 来源并在 validation 结果中记录 remap 信息

### 1.2 后端：重映射参考标签

文件：`server/main.py`、`server/taxonomy.py`

- [x] 在 `compute_label_metrics()` 前，按映射表重排参考标签的 ID
- [x] 生成重映射后的参考数组，传入 `compute_label_metrics()`
- [x] 在 validation 结果中增加 `remap_applied`、`remap_source` 和映射相关字段

### 1.3 映射表定义

文件：`server/taxonomy.py`

FLARE22→AMOS22 映射：

| FLARE22 ID | FLARE22 名称 | AMOS22 ID | AMOS22 名称 |
|---|---|---|---|
| 1 | liver | 6 | 肝脏 |
| 2 | right_kidney | 2 | 右肾 |
| 3 | spleen | 1 | 脾脏 |
| 4 | pancreas | 10 | 胰腺 |
| 5 | aorta | 8 | 主动脉 |
| 6 | IVC | 9 | 下腔静脉 |
| 7 | R_adrenal | 11 | 右肾上腺 |
| 8 | L_adrenal | 12 | 左肾上腺 |
| 9 | gallbladder | 4 | 胆囊 |
| 10 | esophagus | 5 | 食管 |
| 11 | stomach | 7 | 胃 |
| 12 | duodenum | 13 | 十二指肠 |
| 13 | left_kidney | 3 | 左肾 |

- [x] 实现 `build_remap_mapping(checkpoint_labels, reference_labels)` 函数
- [x] 支持 FLARE22 → 当前 AMOS22 checkpoint 的器官名映射
- [x] 对未知或无法映射的标签保留清晰边界，不强行解释为 AMOS 原生验证
- [x] 支持至少两个明确错位 label 的 FLARE22 部分标签自动 remap
- [ ] 为单 label 文件设计显式数据集 hint，避免证据不足时自动推断来源

### 1.4 前端：显示 remap 信息

文件：`src/main.tsx`

- [x] 当 validation 结果包含 `remap_applied: true` 时，在评估面板显示"已自动重映射标签 ID"
- [ ] 显示完整映射前后对比（可选）

### 验证

- [x] 用 FLARE22 Tr 0009 + 标签文件重新推理，确认自动 remap 后 mean_dice=0.926
- [x] 确认 AMOS 0117 原有验证口径不变
- [x] `npm test` + `npm run build`

---

## Phase 2：GUI 异常指标提示（P1）

**目标：** 当验证结果异常时，给用户明确提示，避免误判模型质量。

文件：`src/main.tsx`

- [ ] 当 `taxonomy_match: false` 时，评估面板显示警告："标签 ID 与当前模型不匹配"
- [ ] 当 `mean_dice < 0.3` 且 `taxonomy_match: true` 时，显示"分割质量较低，建议人工复核"
- [ ] 当 `mean_dice < 0.3` 且存在 remap 时，显示"标签重映射后质量仍低，建议检查数据"
- [ ] 在 per-label 表格中，对 dice=0 且 pred/ref 体素量级差异 >10x 的标签标注"疑似错位"

### 验证

- [ ] 用 FLARE22 无 remap 推理，确认显示"标签 ID 不匹配"警告
- [ ] 用 AMOS 0117 推理，确认无异常警告
- [ ] `npm test` + `npm run build`

---

## Phase 3：AMOS 大体数据耗时优化（P2）

**目标：** AMOS 568 层切片推理从 1054s 降到 <500s。

- [ ] 测试 `fast` profile 对 AMOS 0117 的耗时和 mean_dice
- [ ] 测试 `tile_step_size` 从 0.5 调到 0.75 的影响
- [ ] 测试 `disable_tta: true` 的影响
- [ ] 为 >300 层切片的输入自动建议使用 `fast` profile

---

## Phase 4：标签传输稳定性观察（P3）

**目标：** 确认标签文件传输 bug 不复发，同时避免通过上传文件名日志暴露病例信息。

- [x] 移除前端和后端上传文件名调试日志
- [x] 用回归测试约束前端主流程、inference client 和后端源码不再输出上传文件名
- [ ] 每次真实推理后检查 job state、`label_path`、validation summary 是否与当前标签文件一致
- [ ] 若再次出现 null，收集 job id、请求字段、后端结构化错误和 `server/work/<job_id>`，不依赖控制台文件名日志

---

## 停止条件

- 自动 remap 生效前不声称在线验证对跨数据集有效；当前仅对已知且可映射的数据集生效。
- 若自动 remap 覆盖率 < 50%，改为提示用户手动映射。
- 若 AMOS 耗时优化导致 mean_dice 下降 > 0.02，回退到 quality profile。
