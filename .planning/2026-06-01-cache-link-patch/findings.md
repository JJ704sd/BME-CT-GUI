# Cache 链路补丁发现

## 发现日期

2026-06-01

## 关键发现

### 发现 1：FLARE22 cache hit 命中的 cache_source 与显示的 validation 不一致

**证据**：FLARE22 cache hit（`02da885c97d8`）显示的 mean_dice 0.891、stomach 0.556 实际来自 `009d4efdc5f6`（AMOS 0117 历史推理），与 README 期望的 0.893/0.674/0.950 完全错位。"FLARE22 Tr 0009 载入参考病例"也错误显示 `amos_0117_original.nii.gz` 768×768×103 路径。

**根因**：1) `find_cached_prediction()` 只按 mtime 排序候选，空 job 目录被误选；2) `complete_cached_job()` 不回退到 cache_source 的 `validation_summary.json`，cache hit 找不到当前 validation 时直接给 null；3) 0aa7323a4c01 与历史 `86b0153d0a73` 预测字节不同，cache_key 也不一致；4) 现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`。

**意义**：cache hit 不再混用错位 cache_source 的 validation；cache 链路补丁可作为跨数据集复用的起点。

**后续**：下一轮可把这条链路产品化（通用 `tools/rewrite_cached_validation_summary.py`）。

### 发现 2：cache_source 没有 validation_summary.json 时整条链路会断

**证据**：0aa7323a4c01 是新跑的预测，output 目录里没有 `validation_summary.json`；`complete_cached_job()` 找不到当前 validation，又不回退到 cache_source 的旧摘要。

**意义**：cache hit 的 validation 显示依赖 cache_source 的 `validation_summary.json` 存在；缺失时整条链路会断。

**后续**：补 `tools/rewrite_flare22_historical_summary.py` 按历史指标改写 cache_source 的 `validation_summary.json`；未来可产品化为通用工具。

### 发现 3：`SEGMENTATION_REFERENCE_CASES_JSON` 是 cache 链路的前置条件

**证据**：现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，`/api/samples` 只返回内置 `amos_0117`，FLARE22 Tr 0009 不可选；所有"载入参考病例"都跑到了 AMOS 0117。

**意义**：env var 缺一项就会让整条 cache 链路看起来指向错位数据；runbook 必须把这一项写在最前面。

**后续**：runbook 已更新；下一轮要把这个约束写到启动脚本或 smoke test 里。

### 发现 4：cache_key 7 字段隔离与"按历史指标改写 cache_source 摘要"互补

**证据**：cache_key 7 字段（input_sha / checkpoint_sha / checkpoint_dataset_name / checkpoint_configuration / labels_source / runtime_target / inference_options）保证不同请求不混用缓存；0aa7323a4c01 与历史 `86b0153d0a73` 因为推理配置不同 cache_key 也不一致，所以不能直接复用历史的 `validation_summary.json`。

**意义**：cache_key 隔离防止"张冠李戴"，但同时也意味着新 cache_source 必须自备 `validation_summary.json`；本轮补的 `tools/rewrite_flare22_historical_summary.py` 是解决"自备"问题的一次性工具。

**后续**：通用化后可以让任何 cache_source 都"自备"摘要。

### 发现 5：现场复测时漏设的 env var 必须用启动脚本固化

**证据**：现场复测时手动启动后端，漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，导致 4 个 case 退化为 1 个。

**意义**：手动启动容易漏 env var；下一轮可以考虑：
- `tools/start_demo.py` 自动 setenv + spawn backend/frontend；
- `tests/cacheDemoRunbook.test.py` smoke 测试 `/api/samples` 暴露 4 个 case；
- 启动脚本把 `SEGMENTATION_REFERENCE_CASES_JSON` 写进 `server/main.py` 的 fallback 默认值（仅 demo 用）。

**后续**：下一轮根据"演示自动化"和"runbook 自动校验"任务推进。

## 待验证假设

1. **跨数据集 cache 链路可产品化**：把 `tools/rewrite_flare22_historical_summary.py` 重构为通用 `tools/rewrite_cached_validation_summary.py` 后，其他 cache_source 也能享受 cache hit 时显示历史 validation 摘要。
2. **env var 可在 server 启动时自动 setenv**：补一个 demo 启动脚本 `tools/start_local_demo.py`，把 `SEGMENTATION_REFERENCE_CASES_JSON` 等 env var 写死。
3. **runbook 的 4 个已知约束可以自动校验**：写 `tests/cacheDemoRunbook.test.py` 自动确认 env / cwd / reference cases JSON / cache_key 7 字段 / cache_source 排序约束仍在生效。

## 数据来源

- `.planning/2026-06-01-local-cache-demo/` 的 `findings.md` / `progress.md` / `task_plan.md`
- `server/main.py` 中 `_load_cached_validation_summary()`、`complete_cached_job()`、`find_cached_prediction()`
- `tools/rewrite_flare22_historical_summary.py`
- `src/main.tsx` 中 `getValidationStatusCopy()`、`src/inference/inferenceClient.ts`
- `tests/backendState.test.py` 中新增的 2 个测试
- 现场复测时的截图与对话记录

---

*更新日期：2026-06-01*
