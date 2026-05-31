# 下一轮候选任务发现

## 发现日期

2026-05-31

## 关键发现

### 发现 1：taxonomy fix 已验证通过

**证据**：job `d56bcff76a8b`，AMOS22 选择时 `remap_applied=false`。

**意义**：AMOS 原生标签不再被误判为 FLARE22，解决了服务器 AMOS 轮次 `mean_dice=0.076015` 的根因。

**后续**：需要用显式 `label_taxonomy=AMOS22` 复跑服务器 AMOS，确认 `remap_applied=false` 后纳入正式质量基线。

### 发现 2：高分辨率 CT 推理速度瓶颈明确

**证据**：job `ad3d14eba3de`，768×768×103 输入，fast profile，mean_dice=0.77724。

**瓶颈分析**：

| 因素 | 影响 | 说明 |
|---|---|---|
| 输入分辨率 | 高 | 面积 2.25 倍于标准 512×512 |
| GPU 显存 | 中 | 8GB 显存占用 95% |
| GPU 功率 | 中 | 笔记本散热限制，27W/40W |
| 2D 模型 | 中 | 逐切片处理 103 层 |

**后续**：预降采样（768→512）是最直接的优化路径，预计推理时间减少约 50%。

### 发现 3：fast/quality profile 对照数据完整

**证据**：`SEGMENTATION_METRICS_SUMMARY.md` 中的对照表。

| 指标 | fast | quality |
|---|---|---|
| 耗时 | 384.345s | 1360.398s |
| mean Dice | 0.777243 | 0.924780 |
| min Dice | 0.000000 | 0.846569 |
| label 14/15 假阳性 | 有 | 无 |

**意义**：`quality` 应继续作为正式报告基线，`fast` 仅作为预览模式。

### 发现 4：server mode gating 仍需修复

**证据**：`/api/models` 默认仍可能显示 `runtime_target=local` 并报告本地 Windows nnUNet 文件缺失。

**影响**：服务器模式创建 job 时可能因本地文件缺失而 503。

**后续**：`runtime_target=server` 只检查 server runtime 必需路径（`evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`）。

### 发现 5：服务器链路已跑通但质量基线未定

**证据**：2026-05-31 校园网服务器 smoke。

| 轮次 | 结果 | 状态 |
|---|---|---|
| FLARE | mean Dice 约 0.891 | 可用，链路证据 |
| AMOS | mean Dice 0.076015 | 疑似 taxonomy 误判 |

**意义**：服务器推理、ensemble、下载和 GUI 回填链路可用，但 AMOS 质量基线需复跑确认。

## 待验证假设

1. **预降采样不影响 Dice**：768→512 降采样后，mean Dice 是否仍在 0.85 以上？
2. **server gating 修复后服务器模式可用**：修复后 `/api/segment/jobs` 是否不再因本地文件缺失而 503？
3. **显式 AMOS22 复跑可解决误判**：服务器 AMOS 轮次用 `label_taxonomy=AMOS22` 后，`remap_applied` 是否为 false？

## 数据来源

- `.planning/label-taxonomy-server-validation/progress.md`
- `.planning/high-resolution-inference-optimization/progress.md`
- `SEGMENTATION_METRICS_SUMMARY.md`
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`
- `SEGMENTATION_RECENT_ROUNDS.md`

---

*更新日期：2026-05-31*
