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
- `CLAUDE.md` 是本轮开始前已有的未暂存修改，未纳入该提交。
