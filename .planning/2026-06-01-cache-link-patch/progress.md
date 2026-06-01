# Cache 链路补丁进度

## 2026-06-01：cache 链路补丁完成

**状态：** 全部完成。FLARE22 cache hit 现在能正确显示历史 validation 摘要（0.893127/0.67373/0.949908，"（历史离线缓存摘要）"）；参考病例列表必须设置 `SEGMENTATION_REFERENCE_CASES_JSON` 才返回 4 个 case。

**背景：** 现场复测时发现 FLARE22 cache hit 显示的 validation 摘要来自错位 cache_source（`009d4efdc5f6` 的 AMOS 摘要），同时"FLARE22 Tr 0009 载入参考病例"错误显示 AMOS 0117 路径。根因是 4 个：`find_cached_prediction()` 选错 cache_source、`complete_cached_job()` 不回退历史 validation、0aa7323a4c01 与历史 `86b0153d0a73` 字节不同、漏设 `SEGMENTATION_REFERENCE_CASES_JSON`。

## 本轮已完成

### 1. 后端 historical 回退 [完成]

- [x] `server/main.py` 新增 `_load_cached_validation_summary()` 函数
- [x] `complete_cached_job()` 在无当前 validation 时回退到 `cache_source_job_id/output/validation_summary.json`
- [x] 回退时加 `historical: true` 和 `source_job_id` 标记
- [x] `message` 默认填 "（历史离线缓存摘要，未在当前 job 重新验证）"

### 2. cache_source 优先级 [完成]

- [x] `find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序
- [x] 优先选带 `validation_summary.json` 的 cache_source，避免命中空 job 目录
- [x] 同等优先级下用 mtime 倒序，最新优先

### 3. 改写 FLARE22 历史摘要 [完成]

- [x] `tools/rewrite_flare22_historical_summary.py` 读取 2026-05-26 remap 后 metrics
- [x] 写入 `server/work/0aa7323a4c01/output/validation_summary.json`
- [x] 验证结果：`mean_dice=0.893127`、`min_dice=0.67373`、`fg=0.949908`、15 标签、`historical=True`、`source_job_id="0aa7323a4c01"`

### 4. 前端文案与字段 [完成]

- [x] `src/main.tsx` 中 `getValidationStatusCopy(validation, hasLabelFile, cachedResult)` 增加 cachedResult 参数
- [x] 区分"无历史验证摘要"和"（历史离线缓存摘要）"
- [x] `src/inference/inferenceClient.ts` 增加 `cached_result` / `cache_source_job_id` / `historical` / `source_job_id` 4 个字段
- [x] TypeScript 类型同步更新

### 5. 回归测试 [完成]

- [x] `tests/backendState.test.py` 新增 `test_cached_prediction_falls_back_to_source_validation_summary`
- [x] `tests/backendState.test.py` 新增 `test_cached_prediction_without_historical_validation_summary`
- [x] 修复测试中 `events[-1]["validation"]` 的 KeyError（用 `last_event.get("validation")`）

### 6. 文档同步 [完成]

- [x] `README.md`：新增 cache 链路补丁描述
- [x] `CLAUDE.md`：当前运行状态加 cache 链路补丁
- [x] `AGENTS.md`：当前运行状态加 cache 链路补丁
- [x] `REVIEW.md`：新增"五十三、2026-06-01 cache 链路补丁"节
- [x] `ACCEPTANCE.md`：新增"2026-06-01 cache 链路补丁验收记录"节
- [x] `CODE_MODULE_GUIDE.md`：补 `tools/rewrite_flare22_historical_summary.py` 步骤、数据与文档边界
- [x] `SEGMENTATION_RECENT_ROUNDS.md`：新增"问题 6：FLARE22 cache hit 显示 AMOS 数据 [已修复]"
- [x] `SEGMENTATION_EXPERIMENT_COMPARISON.md`：新增"2026-06-01 cache 链路补丁审核记录"
- [x] `SEGMENTATION_METRICS_SUMMARY.md`：备注 cache 链路补丁后的 FLARE22 cache hit 显示

### 7. env var 强制 [完成]

- [x] `docs/local-cache-demo-runbook.md` 把 `SEGMENTATION_REFERENCE_CASES_JSON` 写在最前面
- [x] runbook 增补"用 `/api/samples` 列表确认 4 个 case"的验证步骤
- [x] 现场复测时确认：`SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json` 启动后 `/api/samples` 返回 4 个 case

### 8. planning 4 文档 [完成]

- [x] `.planning/2026-06-01-cache-link-patch/explanation.md`
- [x] `.planning/2026-06-01-cache-link-patch/findings.md`
- [x] `.planning/2026-06-01-cache-link-patch/progress.md`（本文档）
- [x] `.planning/2026-06-01-cache-link-patch/task_plan.md`

## 当前未完成

### 本轮范围内但未做

- [x] 8 个修复点全部完成
- [x] 9 份核心文档同步
- [x] 4 份 planning 文档落地
- [x] 自动验证：`python tests/backendState.test.py` 通过

### 本轮范围外的后续工作

- [ ] 跨数据集 cache 链路产品化（通用 `tools/rewrite_cached_validation_summary.py`）
- [ ] runbook 自动校验（`tests/cacheDemoRunbook.test.py`）
- [ ] 演示启动脚本化（`tools/start_local_demo.py` 把 env var 写死）
- [ ] cache_source 失效清理（新预测覆盖旧预测时清理过时 `validation_summary.json`）

## 收尾步骤

- [x] 9 份核心文档同步
- [x] 4 份 planning 文档落地
- [ ] git status 全审 + commit
- [ ] git push 到 `https://github.com/JJ704sd/BME-CT-GUI`

## 当前结论

2026-06-01 cache 链路补丁已落地 8 个修复点，FLARE22 cache hit 现在能正确显示历史 validation 摘要（0.893127/0.67373/0.949908，"（历史离线缓存摘要）"）；`SEGMENTATION_REFERENCE_CASES_JSON` 必须显式设置；现场复测已通过。下一步进入 git 提交收尾。

---

*更新日期：2026-06-01*
