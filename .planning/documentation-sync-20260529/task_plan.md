# 2026-05-29 文档现状同步计划

## 目标

核对 `SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_METRICS_SUMMARY.md`、`REVIEW.md`、`README.md`、`ACCEPTANCE.md`、`CODE_MODULE_GUIDE.md`、`SEGMENTATION_RECENT_ROUNDS.md` 与当前 GUI 项目状态是否一致，并同步 `.planning/` 下一轮工作建议。

## 检查清单

- [x] 确认上一轮 bugfix 已提交并推送到 GitHub。
- [x] 审阅 7 份目标文档中关于缓存 validation、persistent worker、taxonomy remap、调试日志和当前验证结果的表述。
- [x] 修正文档中过时、混淆或非中文主体说明。
- [x] 增补 `.planning/` 下一轮候选任务，删除或降级已完成/已过时事项。
- [x] 运行文档测试、全量测试、构建和 Git whitespace 检查。
- [ ] 只提交本轮文档与 planning 变更并推送到 `origin/main`。

## 边界

- 不修改真实 CT、NIfTI、checkpoint、推理输出或私有 registry。
- 不把已有但无关的 `AGENTS.md`、`CLAUDE.md` 工作区改动混入本轮提交。
- 不改变 nnUNetv2 推理行为；本轮是文档与规划同步。
