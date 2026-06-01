# Cache 链路补丁任务规划

**范围：** 2026-06-01 现场复测本地缓存演示时发现的 cache 链路错位修复 + 跨数据集 cache 链路产品化规划。

**当前状态：** 8 个修复点全部完成；9 份核心文档同步；4 份 planning 文档落地；现场复测通过。下一轮候选：跨数据集 cache 链路产品化、runbook 自动校验、演示启动脚本化。

---

## 本轮已完成（2026-06-01）

1. `_load_cached_validation_summary()` + `complete_cached_job()` historical 回退
2. `find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序
3. `tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的 `validation_summary.json`
4. 前端 `getValidationStatusCopy(validation, hasLabelFile, cachedResult)` 区分"无历史验证摘要"和"（历史离线缓存摘要）"
5. `inferenceClient.ts` 增加 `cached_result` / `cache_source_job_id` / `historical` / `source_job_id` 4 个字段
6. `tests/backendState.test.py` 新增 2 个回归测试
7. 9 份核心文档同步 cache 链路补丁描述
8. 4 份 planning 文档落地（`explanation.md` / `findings.md` / `progress.md` / `task_plan.md`）

---

## 推荐下一轮任务

### 1. 跨数据集 cache 链路产品化

**优先级：** 中

**前置文档：** 本目录 `findings.md` 待验证假设 1

**目标：** 把"按历史指标改写 cache_source 摘要"做成可复用机制，让其他数据集/其他 cache_source 也能享受 cache hit 时显示历史 validation 摘要的链路。

**关键步骤：**

1. 重构 `tools/rewrite_flare22_historical_summary.py` 为通用 `tools/rewrite_cached_validation_summary.py`，支持任意 source 路径、任意 target job 目录、任意指标 JSON。
2. 在 `server/main.py` 的 `complete_cached_job()` 中增强 historical 回退：除 `validation_summary.json` 外，尝试读 `job_summary.json` 中的历史指标。
3. 补充 `tests/backendState.test.py` 覆盖"cache_source 含历史指标但无 validation_summary.json"场景。
4. 更新 `docs/local-cache-demo-runbook.md` 增补"通用改写历史摘要"段落。

**风险：** 必须保留"`historical: true`"和"`source_job_id`"标记，避免误把当前请求的标签结果写成历史。

---

### 2. runbook 自动校验

**优先级：** 中

**前置文档：** 本目录 `findings.md` 待验证假设 3

**目标：** 写 `tests/cacheDemoRunbook.test.py`，自动确认 runbook 中提到的 4 个已知约束仍在代码里成立。

**关键步骤：**

1. 测试 `_resolve_project_root()` 在 cwd 不同时的解析行为，确认必须落在 `segmentation-gui-prototype/`。
2. 测试 `compute_cache_key()` 的 7 字段仍是 `input_sha + model_dataset + profile + label_taxonomy + runtime_target + postprocess + device`。
3. 测试 `examples/reference_cases.json` 解析后能产出 4 个 case；`SEGMENTATION_REFERENCE_CASES_JSON` 缺省时只暴露 `amos_0117`。
4. 测试 `tools/seed_demo_cache.py` 和 `tools/rewrite_flare22_historical_summary.py` 在重复运行下保持幂等。
5. 测试 `find_cached_prediction()` 候选排序在多个 cache_source 下优先选有 `validation_summary.json` 的。

**风险：** 这些测试不应启动真实后端服务；用 import 函数 + 临时目录的方式做单元测试即可。

---

### 3. 演示启动脚本化

**优先级：** 中

**前置文档：** 本目录 `findings.md` 发现 5

**目标：** 写 `tools/start_local_demo.py`，自动 setenv + spawn backend/frontend，把 `SEGMENTATION_REFERENCE_CASES_JSON` 等 env var 写死，避免演示现场漏设。

**关键步骤：**

1. `tools/start_local_demo.py` 接收 `--reference-cases-json` 参数（默认 `examples/reference_cases.json`）。
2. 自动 setenv：`SEGMENTATION_REFERENCE_CASES_JSON` / `SEGMENTATION_PERSISTENT_WORKER=1`（可选）/ `SEGMENTATION_DEVICE=cuda`（可选）。
3. 子进程 spawn：`python -m uvicorn server.main:app --host 127.0.0.1 --port 8000` 和 `npm run dev -- --port 5173`。
4. 输出 `curl http://127.0.0.1:8000/api/samples` 提示用户验证 4 个 case。
5. 补 `tests/startLocalDemo.test.py` dry-run 验证 env var 正确传递。

**风险：** 脚本不能取代手动 runbook 作为兜底；保留 runbook 作为停止脚本后的 fallback。

---

### 4. cache_source 失效清理

**优先级：** 低

**前置文档：** 本目录 `findings.md` 待验证假设 2

**目标：** 当 cache_source 被新预测覆盖时，自动清理过时的 `validation_summary.json`，避免历史指标与新预测不一致时被误用。

**关键步骤：**

1. 在 `find_cached_prediction()` 中检测"prediction path 已更新但 validation_summary.json 仍是旧的"场景。
2. 如果新 prediction 的 mtime 比 validation_summary.json 新，标记 cache_source 为 stale 并跳过。
3. 写清理脚本 `tools/cleanup_stale_cache_sources.py` 扫描并清理。
4. 补 `tests/backendState.test.py` 覆盖 stale cache_source 场景。

**风险：** 该清理不能误伤有效 cache_source；建议先仅警告不删除，留人工确认。

---

### 5. 独立 planning 入口（按需推进）

**优先级：** 各自独立

| 任务 | 入口 |
|---|---|
| server mode gating 修复 | `.planning/label-taxonomy-server-validation/` |
| AMOS/FLARE 服务器轮次显式 taxonomy 复跑 | `.planning/label-taxonomy-server-validation/` |
| 高分辨率推理优化 | `.planning/high-resolution-inference-optimization/` |
| AMOS 预热预测复跑 | `.planning/2026-06-01-local-cache-demo/task_plan.md` 任务 1 |

---

## 推荐执行顺序

1. **跨数据集 cache 链路产品化**（让 cache 链路补丁成为通用机制）。
2. **runbook 自动校验**（防止下次复现同样的困惑）。
3. **演示启动脚本化**（演示当天减少手输命令）。
4. **cache_source 失效清理**（持续）。
5. **独立 planning 入口**（按需推进）。

---

*更新日期：2026-06-01*
