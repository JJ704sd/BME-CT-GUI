# 2026-06-11 启动操作手册独立化 + 文档巡检同步 — Progress

> 日期：2026-06-11
> 配套文档：explanation.md / findings.md / task_plan.md

## 状态总览

| 子任务 | 状态 | 备注 |
|---|---|---|
| 1. 新建 `docs/quickstart-launch-guide.md` | ✅ 完成 | 10 章，136 行 |
| 2. README.md 加 quickstart 索引行 | ✅ 完成 | 中文主体保留 |
| 3. AGENTS.md 加 quickstart 索引 + 6-11 段落 | ✅ 完成 | 中文主体保留 |
| 4. CLAUDE.md 加 quickstart 索引 + 6-11 不变量 | ✅ 完成 | 关键不变量段末尾追加 |
| 5. ACCEPTANCE.md 加 quickstart 索引 + 6-11 段落 | ✅ 完成 | 当前进行中段后追加 |
| 6. REVIEW.md 加 6-11 段 + 索引 | ✅ 完成 | 〇段重排，6-11 在顶 |
| 7. CODE_MODULE_GUIDE.md 加 quickstart 索引 + 6-11 段落 | ✅ 完成 | 状态段末尾追加 |
| 8. SEGMENTATION_METRICS_SUMMARY.md 加 quickstart 索引 + 6-11 段落 | ✅ 完成 | 当前进行中段后追加 |
| 9. SEGMENTATION_EXPERIMENT_COMPARISON.md 加 quickstart 索引 + 6-11 审核记录 | ✅ 完成 | 2026-05-26 审核记录后追加 |
| 10. SEGMENTATION_RECENT_ROUNDS.md 顶部加 6-11 新轮次 | ✅ 完成 | 顶部第 1 轮 |
| 11. 新 planning 主题 `.planning/2026-06-11-launch-guide-and-doc-sync/` 4 份文档 | ✅ 完成 | explanation / findings / progress / task_plan |
| 12. 中文主体审查 | ✅ 完成 | 9 份均合格 |
| 13. git commit + push | ⏳ 待执行 | 下一步 |

## 关键时间线

| 时间 | 事件 |
|---|---|
| 2026-06-11 19:49 | 用户首次启动 GUI；bash 工具前台跑 `tools/start_local_demo.py` 90s 超时连带 kill 整个进程组 |
| 2026-06-11 19:55 | 用 PowerShell `Start-Process` 后台启动成功，4 端点全过 |
| 2026-06-11 20:08 | 用户要求整理启动操作打包成文档 |
| 2026-06-11 20:15 | 新建 `docs/quickstart-launch-guide.md`（10 章 / 136 行） |
| 2026-06-11 20:25 | 9 份核心文档巡检 + 同步索引 |
| 2026-06-11 20:40 | 新 planning 主题落地 |
| 2026-06-11 20:50 | git commit + push（待执行） |

## 决策记录

| 决策 | 选项 | 选 | 理由 |
|---|---|---|---|
| 新文档放在哪？ | `docs/quickstart-launch-guide.md` / `QUICKSTART.md`（根目录） | docs 下 | 与现有 `docs/demo-day-checklist.md` / `docs/local-cache-demo-runbook.md` 同目录，文档组织更一致 |
| 是否要新文档索引段？还是只 README 加一行？ | 只 README 加 / 9 份都加 | 9 份都加 | 用户任务明确要求"评估是否同步"到多份文档；这次是新增独立文档，9 份核心文档都应该知道它的存在 |
| 新文档是否提到 cache demo / 演示当天？ | 完全不提 / 在"相关文档"段提一下 | 后者 | 让用户从 quickstart 自然滑到 checklist / runbook |
| `Start-Process` 命令放哪？ | 不放 / 放在 §1.2 后台段 | 放在 §1.2 | 这是最容易踩坑的坑；不放在启动文档里就太可惜了 |
| `Start-Process` 命令是否要包含完整 env 显式？ | 默认走脚本内 setenv / 显式 export 后再 Start-Process | 默认走脚本内 setenv | `tools/start_local_demo.py` 已经封装了 setenv，显式 export 多此一举；但在命令注释里要写清楚"脚本会 setenv `SEGMENTATION_REFERENCE_CASES_JSON` 等" |

## 与历史工作的关系

本次 6-11 工作延续 6-06 演示当天收口，但**仅文档**：不动 nnUNetv2 推理、缓存复用 7 字段、SSE 协议、validation 字段、HTML 报告样式或影像量化逻辑；不修改任何历史 AMOS / FLARE baseline。

它解决了 6-06 收口后的一个遗留缺口：演示当天用 `start_local_demo.py` 没问题，但日常启动没有任何独立文档；现在补上。

---

*更新日期：2026-06-11*