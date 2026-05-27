# 标签打分优化规划

**目标：** 解决跨数据集在线验证 Dice 无意义的问题，使 GUI 质量评估面板对任意 CT + 标签组合都能给出有参考价值的分数。

**当前基线：** 标签文件传输链路已修复（2026-05-27），但 FLARE22 在线验证 mean_dice=0.073（实际离线 remap 后 0.893），根因是 AMOS22 checkpoint 标签 ID 与 FLARE22 标签 ID 语义不匹配。

## Status

- [x] 修复标签文件传输 bug（UploadRole 扩展 + 拖拽区域 + 调试日志）
- [x] 验证标签文件能正确到达后端并触发 validation
- [x] 确认 Dice 低的根因是 taxonomy 错位而非模型质量问题
- [x] 收集近三轮在线推理数据并建立滚动记录文档
- [ ] 实现 taxonomy 自动 remap
- [ ] GUI 异常指标提示
- [ ] AMOS 大体数据耗时优化
- [ ] 标签传输稳定性持续观察

## 近三轮数据

| 轮次 | job_id | 病例 | 标签 | 耗时 | mean_dice | 问题 |
|---|---|---|---|---|---|---|
| 1 | `bf20f0ec4456` | FLARE22 512×512×87 | 已上传 | 223s | 0.073 | taxonomy 错位 |
| 2 | `d2510866dd8c` | FLARE22 512×512×87 | 未上传 | 214s | — | 无验证 |
| 3 | `b6e04914f852` | AMOS 512×512×568 | 内置 | 1054s | — | 未记录 |

离线 remap 参考：FLARE22 mean_dice=0.893, min_dice=0.674, fg_dice=0.950。

---

## Phase 1：taxonomy 自动 remap（P0）

**目标：** 当用户上传的标签文件 ID 体系与当前 checkpoint 不一致时，自动按器官名重映射，在线验证 mean_dice 从 0.073 → ~0.893。

### 1.1 后端：检测 taxonomy 不匹配

文件：`server/main.py`，函数 `validate_against_custom_label()`

- [ ] 读取 checkpoint 的 `dataset.json` 获取 `labels` 字段（ID→器官名映射）
- [ ] 读取用户标签文件中出现的 ID 集合
- [ ] 按器官名建立双向映射表
- [ ] 若映射覆盖率 < 80%，返回 `taxonomy_match: false` 并附带映射详情

### 1.2 后端：重映射参考标签

文件：`server/main.py`

- [ ] 在 `compute_label_metrics()` 前，按映射表重排参考标签的 ID
- [ ] 生成临时重映射后的参考数组，传入 `compute_label_metrics()`
- [ ] 在 validation 结果中增加 `remap_applied: bool` 和 `remap_mapping: dict`

### 1.3 映射表定义

文件：`server/main.py` 或 `server/taxonomy.py`（新建）

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

- [ ] 实现 `build_remap_mapping(checkpoint_labels, reference_labels)` 函数
- [ ] 支持 AMOS22↔FLARE22 双向映射
- [ ] 对未知 ID 保留原值并标记

### 1.4 前端：显示 remap 信息

文件：`src/main.tsx`

- [ ] 当 validation 结果包含 `remap_applied: true` 时，在评估面板显示"已自动重映射标签 ID"
- [ ] 显示映射前后对比（可选）

### 验证

- [ ] 用 FLARE22 Tr 0009 + 标签文件重新推理，确认 mean_dice ≈ 0.893
- [ ] 确认 AMOS 0117 原有验证不受影响
- [ ] `npm test` + `npm run build`

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

**目标：** 确认标签文件传输 bug 不复发。

- [ ] 保留 `console.log` 调试日志两周
- [ ] 每次推理后检查 `label_path` 是否非空
- [ ] 若再次出现 null，收集浏览器控制台日志和后端日志

---

## Stop Conditions

- Phase 1 完成前不声称在线验证对跨数据集有效。
- 若自动 remap 覆盖率 < 50%，改为提示用户手动映射。
- 若 AMOS 耗时优化导致 mean_dice 下降 > 0.02，回退到 quality profile。
