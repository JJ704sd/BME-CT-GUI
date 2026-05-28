# 文档现状同步计划

## 目标

对 GUI 项目的主要说明文档、验收记录、指标说明和 `.planning` 目录进行现状核对与同步，确保主体说明仍为中文，并在完成后提交到 GitHub。

## 范围

- `README.md`
- `ACCEPTANCE.md`
- `REVIEW.md`
- `SEGMENTATION_EXPERIMENT_COMPARISON.md`
- `SEGMENTATION_METRICS_SUMMARY.md`
- `SEGMENTATION_RECENT_ROUNDS.md`
- `CODE_MODULE_GUIDE.md`
- `AGENTS.md`
- `.planning/`

## 检查清单

- [x] 核对代码和现有文档对 API、推理 profile、缓存、heartbeat、取消、报告导出、taxonomy remap 的描述是否一致。
- [x] 修正文档中已经过期或容易误解的说明。
- [x] 检查文档主体语言，必要时把说明文字改回中文，保留技术名词、命令、job id、指标字段英文。
- [x] 增补下一轮工作 planning 文档，清理或标注过期规划。
- [x] 运行验证命令，记录结果。
- [ ] 检查 git diff，提交并推送到 GitHub。

## 当前状态

- 进行中：验证和 GitHub 提交。
