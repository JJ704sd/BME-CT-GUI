# 本地缓存演示进度

## 2026-06-01 晚：cache 链路补丁已完成

**状态：** 现场复测时发现 FLARE22 cache hit 显示的 validation 摘要来自错位 cache_source（`009d4efdc5f6`），已完成 cache 链路补丁：FLARE22 cache hit 现在能正确显示 0.893127/0.67373/0.949908 + "（历史离线缓存摘要）"。

**关键修复**：

- [x] `server/main.py` 新增 `_load_cached_validation_summary()`；`complete_cached_job()` 增加 historical 回退，加 `historical: true` 和 `source_job_id` 标记。
- [x] `find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序，优先选有 `validation_summary.json` 的 cache_source。
- [x] `tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的 `validation_summary.json`：`mean_dice=0.893127`、`min_dice=0.67373`、`fg=0.949908`、15 标签、`historical=True`、`source_job_id="0aa7323a4c01"`。
- [x] 前端 `getValidationStatusCopy(validation, hasLabelFile, cachedResult)` 区分"无历史验证摘要"和"（历史离线缓存摘要）"；`inferenceClient.ts` 增加 `cached_result` / `cache_source_job_id` / `historical` / `source_job_id` 字段。
- [x] `tests/backendState.test.py` 新增 2 个回归测试。
- [x] 9 份核心文档同步 cache 链路补丁描述。
- [x] `SEGMENTATION_REFERENCE_CASES_JSON` 必须显式设置才能让 `/api/samples` 暴露 4 个 reference case（已写入 runbook 头部）。

## 2026-06-01：cache demo 7 步全部跑通，9 份核心文档同步完成

**状态：** 本轮目标已达成，准备进入 GitHub 提交收尾。

**背景：** 为 BME 竞赛 PPT 演示准备最短、最可重现的"本地缓存演示"链路。三个 job 的对照表（cache hit → 真实推理 → cache hit）已落地，9 份核心文档已统一口径。

## 本轮已完成

### 1. 后端运行环境补充 [完成]

- [x] 在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装 `fastapi 0.136.3`
- [x] 在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装 `uvicorn 0.48.0`
- [x] 在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装 `python-multipart 0.0.30`
- [x] 验证 `uvicorn server.main:app` 必须以 `segmentation-gui-prototype/` 为 cwd

### 2. 参考病例 JSON 配置 [完成]

- [x] 确认 `examples/reference_cases.json` 已含 AMOS 0117 与 FLARE22 Tr 0009
- [x] 通过 `SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json` 让 `/api/samples` 暴露 4 个 reference case

### 3. AMOS 预热脚本 `tools/seed_demo_cache.py` [完成]

- [x] 用 `compute_cache_key()` 重算 7 字段 cache_key
- [x] 匹配 2026-05-23 历史预测 `009d4efdc5f6`
- [x] 幂等回写 `job_summary.json` 让 `find_cached_prediction()` 能命中
- [x] 可独立重跑：再次执行不会产生重复 entry

### 4. Phase A：AMOS 0117 cache hit [完成]

- [x] job `aea4e7cdbaf0`
- [x] mode = `cached-real-nnunetv2`
- [x] 命中 `009d4efdc5f6`
- [x] 前端 timeline 立刻显示完成
- [x] validation 摘要走 AMOS 内置参考标签（review status，stomach 0.556）

### 5. Phase B：FLARE22 Tr 0009 真实推理 [完成]

- [x] job `0aa7323a4c01`
- [x] mode = `real-nnunetv2`
- [x] 耗时 218s（本地单机 RTX 4060 Laptop fold0，profile quality）
- [x] `remap_applied=true`、`remap_source=FLARE22`
- [x] 结果 NIfTI 下载并在前端三视图回填

### 6. Phase C：FLARE22 Tr 0009 cache hit [完成]

- [x] job `02da885c97d8`
- [x] mode = `cached-real-nnunetv2`
- [x] 命中 Phase B `0aa7323a4c01`
- [x] 耗时 0.001s（与 Phase B 的 218s 形成肉眼可见对照）

### 7. 文档与脚本 [完成]

- [x] `tools/seed_demo_cache.py`：幂等预热脚本
- [x] `docs/local-cache-demo-runbook.md`：运行手册（启动命令、关键路径、cache_key 7 字段、4 个已知约束）
- [x] `docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`：设计稿
- [x] `docs/superpowers/plans/2026-06-01-local-cache-demo.md`：实施计划

### 8. 核心文档同步 [完成]

- [x] `SEGMENTATION_RECENT_ROUNDS.md`：把 2026-06-01 cache demo 列为最新轮，AMOS 预热预测 review status 单列为新问题；新增"问题 6：FLARE22 cache hit 显示 AMOS 数据 [已修复]"
- [x] `SEGMENTATION_EXPERIMENT_COMPARISON.md`：补 3 行实验总览、3 行实验名称说明、1 节 2026-06-01 审核记录；新增"2026-06-01 cache 链路补丁审核记录"
- [x] `SEGMENTATION_METRICS_SUMMARY.md`：当前运行状态加 2026-06-01 cache demo 5 条，备注 AMOS cache hit 复用 `009d4efdc5f6`；备注 cache 链路补丁
- [x] `CODE_MODULE_GUIDE.md`：补 `tools/seed_demo_cache.py` 和 `tools/rewrite_flare22_historical_summary.py` 步骤、当前运行状态、数据与文档边界
- [x] `AGENTS.md`：当前运行状态、文档协作章节、cache 链路补丁
- [x] `CLAUDE.md`：当前运行状态、文档协作章节、cache 链路补丁
- [x] `README.md`：当前运行状态、新增"2026-06-01 本地缓存演示补充"节、cache 链路补丁
- [x] `REVIEW.md`：新增"52. 2026-06-01 本地缓存演示"节和"五十三、2026-06-01 cache 链路补丁"节，更新文档版本和更新依据
- [x] `ACCEPTANCE.md`：当前运行状态加 2026-06-01 cache demo 5 条，新增"2026-06-01 本地缓存演示验收记录"和"2026-06-01 cache 链路补丁验收记录"节

### 9. planning 4 文档 [完成]

- [x] `.planning/2026-06-01-local-cache-demo/explanation.md`
- [x] `.planning/2026-06-01-local-cache-demo/findings.md`
- [x] `.planning/2026-06-01-local-cache-demo/progress.md`（本文档）
- [x] `.planning/2026-06-01-local-cache-demo/task_plan.md`

## 当前未完成

### 本轮范围内但未做

- [x] cache 链路补丁（2026-06-01 晚）：`_load_cached_validation_summary()` + `complete_cached_job()` historical 回退；`find_cached_prediction()` 优先选有 `validation_summary.json` 的 cache_source；`tools/rewrite_flare22_historical_summary.py`；前端文案；2 个回归测试。
- [ ] 跨数据集 cache 链路产品化：本轮补丁只针对 FLARE22 + 0aa7323a4c01；下一轮可重构为通用 `tools/rewrite_cached_validation_summary.py`。

### 本轮范围外的后续工作

- [ ] AMOS 预热预测 `009d4efdc5f6` 用 quality profile 复跑替换（让 Phase A 不再命中 review status）
- [ ] cache demo 脚本化：包装成 `tools/run_local_cache_demo.py`
- [ ] runbook 自动校验：`tests/cacheDemoRunbook.test.py`
- [ ] 高分辨率 CT 推理优化（独立 planning 入口）
- [ ] `runtime_target=server` 创建 job gating 修复（独立 planning 入口）
- [ ] AMOS/FLARE 服务器轮次显式 taxonomy 复跑（独立 planning 入口）

## 收尾步骤

- [x] 9 份核心文档同步
- [x] 4 份 planning 文档落地
- [ ] git status 全审 + commit
- [ ] git push 到 `https://github.com/JJ704sd/BME-CT-GUI`

## 当前结论

2026-06-01 本地缓存演示已完成全部 9 个子任务（环境、参考病例、预热脚本、3 个 Phase、文档/脚本、9 份核心文档同步、4 份 planning）。下一步进入 git 提交收尾。

---

*更新日期：2026-06-01*
