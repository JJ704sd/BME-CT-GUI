# 本地缓存演示任务规划

**范围：** 2026-06-01 BME 竞赛 PPT 演示的"本地缓存演示"链路 + 后续候选任务。

**当前状态：** 本轮 7 步 demo + 9 份核心文档同步 + 4 份 planning + cache 链路补丁 已完成；准备 git 提交收尾。

---

## 本轮已完成（2026-06-01）

1. 后端依赖补充：`D:\BME2026\BME_CT_Seg\nnunet_env` 装 `fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30`
2. 参考病例 JSON：通过 `SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json` 暴露 4 个 reference case
3. 预热脚本 `tools/seed_demo_cache.py`：幂等 cache_key 重算 + `job_summary.json` 回写
4. Phase A：AMOS 0117 cache hit（job `aea4e7cdbaf0`，命中 `009d4efdc5f6`）
5. Phase B：FLARE22 Tr 0009 真实推理（job `0aa7323a4c01`，218s）
6. Phase C：FLARE22 Tr 0009 cache hit（job `02da885c97d8`，0.001s）
7. 运行手册 `docs/local-cache-demo-runbook.md` + 设计稿 + 实施计划
8. 9 份核心文档同步：`README` / `CLAUDE` / `AGENTS` / `ACCEPTANCE` / `REVIEW` / `CODE_MODULE_GUIDE` / `SEGMENTATION_RECENT_ROUNDS` / `SEGMENTATION_EXPERIMENT_COMPARISON` / `SEGMENTATION_METRICS_SUMMARY`
9. 4 份 planning 文档：本目录的 `explanation.md` / `findings.md` / `progress.md` / `task_plan.md`
10. cache 链路补丁（2026-06-01 晚）：`_load_cached_validation_summary()` + `complete_cached_job()` historical 回退；`find_cached_prediction()` 优先选有 `validation_summary.json` 的 cache_source；`tools/rewrite_flare22_historical_summary.py`；前端 `getValidationStatusCopy()` 增加 cachedResult 参数；`tests/backendState.test.py` 新增 2 个回归测试

---

## 推荐下一轮任务

### 1. AMOS 预热预测复跑

**优先级：** 高

**前置文档：** 本目录 `findings.md` 发现 7、`progress.md` 本轮范围外的后续工作

**目标：** 用 quality profile 复跑 AMOS 0117，替换当前 cache hit 命中的 review status 预测 `009d4efdc5f6`，让 Phase A 在 PPT 演示中也能挂上一个 stomach Dice 不再是 0.556 的预测。

**关键步骤：**

1. 在本地以 `runtime_target=local`、`profile=quality`、`label_taxonomy=AMOS22` 重新提交 AMOS 0117 job。
2. 检查 `validation_status` 不再是 review，stomach Dice 恢复到 0.8 以上。
3. 用 `tools/seed_demo_cache.py` 把新的预测 entry 替换 `009d4efdc5f6`，让 Phase A 自动命中新预测。
4. 更新 `docs/local-cache-demo-runbook.md` 中的 job 表格。

**风险：** quality profile 在 AMOS 0117 上耗时约 23 分钟，演示当天不要现场重跑；提前完成。

---

### 2. 跨数据集 cache 链路产品化

**优先级：** 中

**前置文档：** 本目录 `findings.md` 发现 8

**目标：** 把"按历史指标改写 cache_source 摘要"做成可复用机制，让其他数据集/其他 cache_source 也能享受 cache hit 时显示历史 validation 摘要的链路。

**关键步骤：**

1. 重构 `tools/rewrite_flare22_historical_summary.py` 为通用 `tools/rewrite_cached_validation_summary.py`，支持任意 source 路径、任意 target job 目录、任意指标 JSON。
2. 在 `server/main.py` 的 `complete_cached_job()` 中增强 historical 回退：除 `validation_summary.json` 外，尝试读 `job_summary.json` 中的历史指标。
3. 补充 `tests/backendState.test.py` 覆盖"cache_source 含历史指标但无 validation_summary.json"场景。
4. 更新 `docs/local-cache-demo-runbook.md` 增补"通用改写历史摘要"段落。

**风险：** 必须保留"`historical: true`"和"`source_job_id`"标记，避免误把当前请求的标签结果写成历史。

---

### 3. cache demo 脚本化

**优先级：** 中

**前置文档：** 本目录 `explanation.md` 后续建议 2

**目标：** 把 7 步 demo 包成 `tools/run_local_cache_demo.py`，自动按顺序触发 3 个 job 并打印对照表，避免演示当天手输命令。

**关键步骤：**

1. 编写 `tools/run_local_cache_demo.py`，参数化 `--phase a|b|c|all`、`--server-url`、`--reference-cases-json`。
2. 子命令封装：调用 `tools/seed_demo_cache.py`（Phase A pre-warm）、`POST /api/segment/jobs`、SSE 监听、`GET .../result`。
3. 完成后打印 markdown 风格的对照表，PPT 演示可截屏。
4. 补 `tests/cacheDemoRun.test.py` 用 mock 后端跑 dry-run，确认 cache_key 字段计算正确。

**风险：** 自动化时务必保留"手动 7 步" runbook 作为兜底，避免脚本出 bug 时无路可退。

---

### 4. runbook 自动校验

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

### 5. 高分辨率推理优化（独立 planning 入口）

**优先级：** 中高

**前置文档：** `.planning/high-resolution-inference-optimization/`

**目标：** 实现预降采样（768→512），缩短 AMOS 高分辨率推理时间。本轮 cache demo 没有触及该工作，仍由原 planning 入口推进。

---

### 6. server mode gating 修复（独立 planning 入口）

**优先级：** 高

**前置文档：** `.planning/label-taxonomy-server-validation/`

**目标：** `runtime_target=server` 创建 job 时不再依赖本地 Windows nnUNet 文件。本轮 cache demo 全部走 `local`，未触及该工作。

---

### 7. AMOS / FLARE 服务器轮次显式 taxonomy 复跑（独立 planning 入口）

**优先级：** 高

**前置文档：** `.planning/label-taxonomy-server-validation/`

**目标：** 把 2026-05-31 服务器 AMOS 轮次的 taxonomy 误判排除后再纳入正式质量基线。本轮 cache demo 在本地复现了 FLARE22 自动 remap，但服务器轮次仍未复跑。

---

### 8. 文档与验收口径再同步

**优先级：** 中

**目标：** 后续代码或配置变化后，及时同步 9 份核心文档的中文主体说明。本轮已完成同步，继续保持口径一致即可。

---

## 推荐执行顺序

1. **AMOS 预热预测复跑**（让 cache demo Phase A 命中一个非 review 状态预测）。
2. **server mode gating 修复**（解除服务器模式阻塞，独立 planning）。
3. **AMOS/FLARE 服务器显式 taxonomy 复跑**（确认服务器质量基线，独立 planning）。
4. **高分辨率推理优化**（预降采样，独立 planning）。
5. **跨数据集 cache 链路产品化**（把 cache 链路补丁做成通用机制）。
6. **cache demo 脚本化 + runbook 自动校验**（演示前 polish）。
7. **文档与验收口径再同步**（持续）。

---

*更新日期：2026-06-01*
