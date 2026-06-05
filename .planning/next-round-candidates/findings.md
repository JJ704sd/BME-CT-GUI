# 下一轮候选任务发现

## 发现日期

2026-06-05（吸纳 6-02 detect_dataset 收紧 + dataset_hint + 6-03 6 类指标扩展 + surface_distances 2 EDT + 6-04 HTML 报告第一轮美化 + 6-05 HTML 报告临床报告风格重构）

## 关键发现

### 发现 1：本地缓存演示 7 步已跑通

**证据**：AMOS 0117 cache hit（`aea4e7cdbaf0`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）。

**意义**：cache_key 7 字段隔离已实测正确；cache hit 与真实推理的耗时对照（0.001s vs 218s）肉眼可见。

**后续**：本轮目标已达成，下一轮任务规划见本目录 `task_plan.md`。

### 发现 2：cache 链路补丁后 FLARE22 cache hit 显示历史 validation 摘要

**证据**：FLARE22 cache hit 现在显示 0.893127/0.67373/0.949908（"（历史离线缓存摘要）"）；AMOS cache hit 仍显示 review 状态（stomach 0.556）。`server/main.py` 的 `complete_cached_job()` 增加 historical 回退；`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序。

**意义**：cache hit 不再混用错位 cache_source 的 validation；`tools/rewrite_flare22_historical_summary.py` 是配套的"按历史指标改写 cache_source 摘要"工具。

**后续**：下一轮需要把"按历史指标改写 cache_source 摘要"做成可复用机制，让其他数据集/其他 cache_source 也能享受这条链路。

### 发现 3：`SEGMENTATION_REFERENCE_CASES_JSON` 是 cache 链路的前置条件

**证据**：现场复测时漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，导致 `/api/samples` 只返回内置 `amos_0117`，FLARE22 Tr 0009 不可选；所有"载入参考病例"都跑到了 AMOS 0117。

**意义**：env var 缺一项就会让整条 cache 链路看起来指向错位数据；runbook 必须把这一项写在最前面，并提示用 `/api/samples` 列表确认 4 个 case。

**后续**：runbook 已更新；下一轮要把这个约束写到启动脚本或 smoke test 里。

### 发现 4：AMOS 预热预测 `009d4efdc5f6` 仍是 review 状态

**证据**：cache demo Phase A 命中的 `009d4efdc5f6` 是 2026-05-23 历史推理，stomach Dice 0.556，`validation_status=review`。

**意义**：cache demo 命中的不是新一轮 AMOS 基线，演示口径必须明确"这是 2026-05-23 历史预测"。

**后续**：列入 next-round candidates：用 quality profile 复跑 AMOS 0117，替换 `009d4efdc5f6`，让 Phase A 命中一个非 review 的预测。

### 发现 5：server mode gating 仍需修复

**证据**：`/api/models` 默认仍可能显示 `runtime_target=local` 并报告本地 Windows nnUNet 文件缺失。

**影响**：服务器模式创建 job 时可能因本地文件缺失而 503。

**后续**：`runtime_target=server` 只检查 server runtime 必需路径（`evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`）。

### 发现 6：服务器链路已跑通但质量基线未定

**证据**：2026-05-31 校园网服务器 smoke。

| 轮次 | 结果 | 状态 |
|---|---|---|
| FLARE | mean Dice 约 0.891 | 可用，链路证据 |
| AMOS | mean Dice 0.076015 | 疑似 taxonomy 误判 |

**意义**：服务器推理、ensemble、下载和 GUI 回填链路可用，但 AMOS 质量基线需复跑确认。

### 发现 7：fast/quality profile 对照数据完整

**证据**：`SEGMENTATION_METRICS_SUMMARY.md` 中的对照表。

| 指标 | fast | quality |
|---|---|---|
| 耗时 | 384.345s | 1360.398s |
| mean Dice | 0.777243 | 0.924780 |
| min Dice | 0.000000 | 0.846569 |
| label 14/15 假阳性 | 有 | 无 |

**意义**：`quality` 应继续作为正式报告基线，`fast` 仅作为预览模式。

### 发现 8：HTML 报告视觉与信息两轮美化已收口

**证据**：2026-06-04 / 2026-06-05 连续两轮对 `src/report/exportReport.ts` 做美化。6-04 把"工程 dump"提升为"卡片式仪表板"：色阶图例、Header 渐变、3 个 metric group 加组标题图标、aiFindings 严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定 + 列点击排序、@media print A4 页眉页码；信息层加 remap_applied 顶部警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条。6-05 把"卡片式仪表板"重塑为"临床评估报告"：`.cover` 封面页（题图条 + 报告编号 + 主副标题 + 数据集/病例/生成时间三列）、`.exec-summary` 执行摘要、`.toc` 目录（§1-§8 锚点导航）、`.formula-tip` 公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、`.dist-chart` 严重度分布图、`.table-caption` 表格标题、`.footnotes` 脚注；正文模板按 §1 报告概览 / §2 摘要 / §3 数据集 / §4 器官 / §5 体素 / §6 距离 / §7 关键发现 / §8 附录 8 段章节编号排版；字体改为 Source Han Serif / Songti SC + JetBrains Mono；@media print 改为 A4 + 顶部 caseId + 底部 page X of Y。

**意义**：HTML 报告输出从"工程 dump"经"卡片式仪表板"升级为"临床评估报告"；打印预览（Ctrl+P）会按 A4 自动分页且带页眉页码，可直接出 PDF 给临床同行。`npm test` 与 `npm run build` 全过；`tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class（`.legend` / `.remap-banner` / `.historical-banner` / `.spacing-bar`）。

**后续**：本轮不修改 6 类指标、`surface_distances()` 2 EDT 或 `ValidationSummary` / `LabelMetric` 白名单；后续若新增 validation 字段（`remap_applied` / `taxonomy_match` / `dataset_hint` / `historical` / `label_taxonomy` / `quantification`）或新视觉元素，必须同时改 `inferenceClient.ts normalizeValidation` 白名单 + `exportReport.ts` 模板 + `tests/imagingLogic.test.ts` source-grep 断言三处。

## 待验证假设

1. **预降采样不影响 Dice**：768→512 降采样后，mean Dice 是否仍在 0.85 以上？
2. **server gating 修复后服务器模式可用**：修复后 `/api/segment/jobs` 是否不再因本地文件缺失而 503？
3. **显式 AMOS22 复跑可解决误判**：服务器 AMOS 轮次用 `label_taxonomy=AMOS22` 后，`remap_applied` 是否为 false？
4. **跨数据集 cache 链路可产品化**：其他 cache_source 命中时能否复用 historical 回退机制？
5. **演示启动脚本能否避免现场漏设 env var**：`tools/start_local_demo.py` 是否能在不写任何 env var 的情况下正确 spawn 后端 + 前端并暴露 4 个 reference case？
6. **runbook 4 个已知约束仍成立**：`tests/cacheDemoRunbook.test.py` 自动校验 cache_key 7 字段、`SEGMENTATION_REFERENCE_CASES_JSON` 4 例模板、`find_cached_prediction` 排序、`tools/seed_demo_cache.py` 幂等性，是否都能通过？

## 数据来源

- `.planning/2026-06-01-local-cache-demo/` 的 `findings.md` / `progress.md` / `task_plan.md`
- `.planning/label-taxonomy-server-validation/progress.md`
- `.planning/high-resolution-inference-optimization/progress.md`
- `SEGMENTATION_METRICS_SUMMARY.md`
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`
- `SEGMENTATION_RECENT_ROUNDS.md`
- `tools/seed_demo_cache.py` / `tools/rewrite_flare22_historical_summary.py`
- `docs/local-cache-demo-runbook.md`
- `src/report/exportReport.ts` 6-04 / 6-05 改动
- `tests/imagingLogic.test.ts` 4 个新 class 的 source-grep 断言

---

*更新日期：2026-06-05*
