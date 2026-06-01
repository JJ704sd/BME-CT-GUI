# 文档现状同步进度

## 2026-05-28

- 建立本轮文档刷新计划。
- 下一步：批量读取目标文档和 `.planning` 目录，标记过期口径与需要补充的位置。

## 2026-05-28 文档同步

- 更新 `AGENTS.md`，补充当前项目状态、API、推理 profile、缓存、heartbeat、取消、报告导出、测试和验收口径。
- 更新 `ACCEPTANCE.md`，补充 2026-05-28 自动 taxonomy remap 在线验证记录，并修正历史段落的旧口径。
- 更新 `SEGMENTATION_METRICS_SUMMARY.md` 和 `SEGMENTATION_EXPERIMENT_COMPARISON.md`，区分 FLARE22 离线 remap 与自动 remap 在线验证。
- 更新 `README.md` 和 `CODE_MODULE_GUIDE.md` 中 FLARE22 validation / remap 的说明。
- 更新 `.planning/next-round-candidates/`、`.planning/label-scoring-optimization/`、`.planning/realtime-inference-progress/`、`.planning/online-inference-followup/` 和 `.planning/non-amos-acceptance-expansion/`。

## 2026-05-28 待验证

- 运行文档相关测试、全量 `npm test` 和 `npm run build`。
- 检查 git diff，确认不提交真实数据或无关文件。

## 2026-05-28 验证记录

- `node tests/acceptanceDocs.test.ts`：通过。
- `git diff --check`：通过；仅出现 Git 行尾转换提示，无 whitespace error。
- `npm test`：首次在沙箱内失败于 `.test-output` 创建权限；以正常权限重跑后通过。
- `npm run build`：通过；Vite 构建 `1594` 个模块，用时约 `2.99s`。

## 2026-05-28 GitHub 收尾

- 提交 `0364d2e docs: sync gui docs and planning` 已推送到 `origin/main`。

## 2026-06-01 后续

- 后续 2026-06-01 已完成本地缓存演示 7 步 + cache 链路补丁，本目录的 9 份核心文档同步目标已包含在 2026-06-01 大轮内重新执行：
  - `README.md` / `CLAUDE.md` / `AGENTS.md` 加 "2026-06-01 本地缓存演示补充" 与 "2026-06-01 cache 链路补丁" 描述。
  - `REVIEW.md` 新增 "五十二、2026-06-01 本地缓存演示" 与 "五十三、2026-06-01 cache 链路补丁" 两节。
  - `ACCEPTANCE.md` 新增 "2026-06-01 本地缓存演示验收记录" 与 "2026-06-01 cache 链路补丁验收记录" 两节。
  - `CODE_MODULE_GUIDE.md` 补 `tools/seed_demo_cache.py` 和 `tools/rewrite_flare22_historical_summary.py` 步骤。
  - `SEGMENTATION_RECENT_ROUNDS.md` / `SEGMENTATION_EXPERIMENT_COMPARISON.md` / `SEGMENTATION_METRICS_SUMMARY.md` 各自加 cache 链路补丁审核记录或备注。
  - 主体说明继续保持中文；URL、技术字段保留英文。
- `CLAUDE.md` 是本轮开始前已有的未暂存修改，未纳入该提交。
