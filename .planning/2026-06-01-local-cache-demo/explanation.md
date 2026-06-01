# 本地缓存演示解释

## 为什么需要这一轮工作

2026-06-01 距离 BME 竞赛 PPT 演示窗口非常近，需要一条最短、最可重现的"本地缓存演示"链路，把项目的工程价值在一张幻灯片内讲清楚：

1. **直观证据**：cache hit → 真实推理 → cache hit 三步对照，0.001s 与 218s 的耗时差异肉眼可见。
2. **可复现**：所有命令、路径、环境变量必须能在另一台 Windows 单机被复述出来，避免演示时翻车。
3. **不污染基线**：本轮所用的两份预测都不是新一轮的正式质量基线，必须在文档里清楚分离工程演示与正式质量证据。

## 本轮范围

| 项目 | 范围 |
|---|---|
| 病例 | AMOS 0117（reference case，dataset=AMOS22）、FLARE22 Tr 0009（reference case，dataset=FLARE） |
| 推理路径 | `runtime_target=local`，nnUNetv2 fold0，profile `quality` |
| 数据流 | reference case → `POST /api/segment/jobs` → SSE 进度/完成 → `GET .../result` 下载 NIfTI |
| 缓存 | `find_cached_prediction()` 用 7 字段 cache_key 命中已有预测 |

## 与其他 planning 文档的关系

- `.planning/high-resolution-inference-optimization/`：高分辨率推理优化仍是独立工程入口，与本轮无依赖。
- `.planning/label-taxonomy-server-validation/`：本轮在 `runtime_target=local` 下复现 FLARE22 自动 remap 是工程链路证据，不替代该 planning 中尚未完成的服务器 AMOS / FLARE 显式 taxonomy 复跑。
- `.planning/next-round-candidates/`：本轮完成后，候选任务清单需要把"本地缓存演示"从下一轮入口移除，并把 AMOS 预热预测质量复跑列入跟踪。
- `.planning/documentation-sync-20260529/`、`.planning/documentation-refresh-20260528/`：本轮的 9 份核心文档更新继承同一份口径，强调"工程链路证据 ≠ 质量基线"。

## 优先级依据

| 优先级 | 工作 | 理由 |
|---|---|---|
| 高 | 跑通 7 步 cache demo | 竞赛 PPT 直接素材 |
| 高 | 写运行手册 `docs/local-cache-demo-runbook.md` | 第二位作者也能复现；演示时减少手抖风险 |
| 中 | 9 份核心文档同步 | 不让旧文档与现状偏差 |
| 中 | 写 4 份 planning 文档 | 把本轮经验纳入历史 |
| 中 | 提交 GitHub | 推到 `https://github.com/JJ704sd/BME-CT-GUI`，让仓库与本地一致 |
| 低 | AMOS 预热预测复跑 | 不在本轮范围；列入后续候选 |

## 演示边界

- 本轮 cache hit 不是新一轮 AMOS 质量评估。命中的 `009d4efdc5f6` 是 2026-05-23 历史预测，标签状态仍为 review（stomach Dice 0.556）；不能作为 PPT 上的"模型质量基线"。
- FLARE22 真实推理是单机 RTX 4060 Laptop fold0，不是服务器 5GPU/5-fold soft ensemble；不能直接和 `a717dacf42d3`（mean_dice 0.926）对比。
- 演示口径必须明确"工程链路 vs 质量基线"两层：cache demo 是链路证据，AMOS quality `b3c528cc9e20`（mean_dice 0.924780）才是质量基线。

## 后续建议

1. **AMOS 预热预测复跑**：用 quality profile 重新生成 AMOS 0117 预测，替换 `009d4efdc5f6`，让 cache demo Phase A 也能挂上一个 review status 不是 review 的预测。
2. **cache demo 脚本化**：考虑把 7 步 demo 包装成 `tools/run_local_cache_demo.py`，让 PPT 演示自动播放 3 个 job 的耗时对照。
3. **runbook 自动化校验**：补一个最小的 `tests/cacheDemoRunbook.test.py`，确认 runbook 中提到的 reference case JSON、cache_key 7 字段、4 个已知约束在代码里仍然成立。

---

*更新日期：2026-06-01*
