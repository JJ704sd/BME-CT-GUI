# 文档现状同步发现

## 初始发现

- `README.md`、`CLAUDE.md`、`CODE_MODULE_GUIDE.md` 已记录 2026-05-28 的主要现状：FLARE22 自动 taxonomy remap、SSE heartbeat、取消推理、报告导出、缓存和 quality/fast profile。
- 原 `AGENTS.md` 比其他文档短，缺少部分最新约束，已纳入本轮同步范围。
- `.planning/` 已有多个历史任务目录，需要补充一个面向下一轮的规划入口，避免只靠历史计划推进。

## 核对发现

- `ACCEPTANCE.md` 中 2026-05-26 / 2026-05-27 的历史段落仍保留“remap 尚待实现”的旧口径，需要改为“历史运行如此，2026-05-28 已解决”。
- `SEGMENTATION_METRICS_SUMMARY.md` 的 FLARE22 部分需要区分 2026-05-26 离线 remap 对照和 2026-05-28 自动 remap 在线 validation。
- `CODE_MODULE_GUIDE.md` 中 FLARE22 标签上传说明需要从“只能离线处理”更新为“后端自动 remap 已上线”。
- `.planning/online-inference-followup/` 和 `.planning/non-amos-acceptance-expansion/` 的主体说明原本多为英文，已改为中文主体，保留必要 profile、job id 和命令字段。
- `.planning/realtime-inference-progress/task_plan.md` 仍写着 heartbeat 是后续候选，但当前后端已实现 heartbeat，需要同步。
