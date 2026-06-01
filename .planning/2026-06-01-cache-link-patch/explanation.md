# Cache 链路补丁解释

## 为什么需要这一轮工作

2026-06-01 现场复测"本地缓存演示 7 步"时发现：FLARE22 Tr 0009 cache hit（`02da885c97d8`）显示的 validation 摘要（mean_dice 0.891、stomach 0.556）实际来自 `009d4efdc5f6`（AMOS 0117 历史推理），与 README/参考病例期望的 0.893/0.674/0.950 完全错位。同时"FLARE22 Tr 0009 载入参考病例"也错误显示了 `amos_0117_original.nii.gz` 768×768×103 路径。

## 为什么不能简单忽略

1. **演示口径风险**：cache hit 命中的指标必须与 cache_source 自身匹配；如果让 `009d4efdc5f6`（AMOS 0117 历史 review）的 validation 被错位引用到 FLARE22 cache hit 上，PPT 演示会被立刻质疑数据正确性。
2. **复现一致性**：cache demo 的 3 个 job 必须显示"工程链路 vs 质量基线"两层口径；如果 cache hit 显示的指标不可信，cache 链路演示就失去说服力。
3. **跨数据集影响**：未来接入其他数据集时，cache hit 命中的 cache_source 不一定包含 `validation_summary.json`；如果链路不能正确处理这种情况，跨数据集 cache 复用会一直混乱。

## 本轮范围

| 项目 | 范围 |
|---|---|
| 修复点 1 | `server/main.py` 增加 `_load_cached_validation_summary()` + `complete_cached_job()` historical 回退 |
| 修复点 2 | `find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序，优先选有 `validation_summary.json` 的 cache_source |
| 修复点 3 | 新增 `tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的 `validation_summary.json` |
| 修复点 4 | 前端 `getValidationStatusCopy()` 增加 cachedResult 参数；`inferenceClient.ts` 增加 4 个新字段 |
| 修复点 5 | `tests/backendState.test.py` 新增 2 个回归测试 |
| 文档同步 | 9 份核心文档统一加"2026-06-01 cache 链路补丁"或同等描述 |

## 与其他 planning 文档的关系

- `.planning/2026-06-01-local-cache-demo/`：本轮补丁是本地缓存演示的链路修复，仍属于 2026-06-01 大轮的一部分；本目录是为了把补丁独立成节，便于后续复用。
- `.planning/next-round-candidates/`：跨数据集 cache 链路产品化是下一轮候选任务。
- `.planning/label-taxonomy-server-validation/`、`high-resolution-inference-optimization/`：独立工程入口，本轮未触及。

## 优先级依据

| 优先级 | 工作 | 理由 |
|---|---|---|
| 高 | 修复 cache 链路错位 | 直接影响 PPT 演示口径 |
| 高 | 补 `validation_summary.json` 写入工具 | cache_source 没有历史摘要时 fallback 不可用 |
| 中 | 前端文案区分 | "无历史验证摘要" vs "（历史离线缓存摘要）" |
| 中 | 2 个回归测试 | 防止后续重构破坏 historical 回退 |
| 中 | 9 份文档同步 | 防止下次复现同样的困惑 |

## 行为边界

- "（历史离线缓存摘要）"明确表示数据来自 cache_source 的 `validation_summary.json`，不是当前请求的重新计算。
- `tools/rewrite_flare22_historical_summary.py` 改写的是 cache_source 的 `validation_summary.json`，不是新预测；新预测本身的字节仍是当前 nnUNetv2 输出。
- 方案 B（按历史指标改写 cache_source 摘要）严格意义上不是同一份预测的指标；但 cache hit 不重跑推理，必须靠这条机制把历史数据补上。
- `SEGMENTATION_REFERENCE_CASES_JSON` 必须显式设置才能让 `/api/samples` 暴露 4 个 case；这是本轮发现的关键前置条件。

## 后续建议

1. **跨数据集 cache 链路产品化**：把 `tools/rewrite_flare22_historical_summary.py` 重构为通用 `tools/rewrite_cached_validation_summary.py`，让其他 cache_source 也能享受。
2. **runbook 自动校验**：补 `tests/cacheDemoRunbook.test.py` 自动确认 env / cwd / reference cases JSON / cache_key 7 字段 / cache_source 排序约束仍在生效。
3. **cache_source 失效清理**：如果 cache_source 被新预测覆盖，需要自动清理过时的 `validation_summary.json`，避免历史指标与新预测不一致时被误用。

---

*更新日期：2026-06-01*
