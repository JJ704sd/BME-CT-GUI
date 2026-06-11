# 2026-06-11 启动操作手册独立化 + 文档巡检同步 — Explanation

> 日期：2026-06-11
> 配套文档：findings.md / progress.md / task_plan.md

## 背景

2026-06-06 演示当天收口后，仓库有 3 份与"启动 GUI"相关的文档：

- `docs/demo-day-checklist.md`（39 行） — 演示当天一屏快查卡片，含权重 / NIfTI 前置确认 5 项 + 5 步演示流程 + runbook 回退命令。
- `docs/local-cache-demo-runbook.md`（103 行） — 本地缓存演示 7 步复跑手册，含启动命令、关键路径、cache_key 7 字段、4 个已知约束。
- `tools/start_local_demo.py`（222 行） — 一键启动脚本（setenv + spawn backend/frontend + 健康检查）。

但是**任何时候**要让一个新同学或临场调试者把 GUI 起来时，没有"最简版"操作文档。他们要么读 39 行 checklist 还要做 cache demo 的 5 项前置确认，要么读 103 行 runbook 被 cache_key 7 字段吓退。`tools/start_local_demo.py` 的设计在 PowerShell 上有一处易踩坑：用 `python tools/start_local_demo.py` 前台跑会被自动化 bash 工具的超时机制连带 kill 整个进程组（uvicorn / vite 父进程被一起杀掉）。

本次工作把这层"日常启动"独立成 `docs/quickstart-launch-guide.md`，与另外两份明确分工；同步做一轮 9 份核心文档巡检；落地新 planning 主题。

## 范围

仅文档工作，**不涉及任何代码改动**：

- 新建 `docs/quickstart-launch-guide.md`（10 章，136 行）。
- 9 份核心文档（README / AGENTS / CLAUDE / ACCEPTANCE / REVIEW / CODE_MODULE_GUIDE / SEGMENTATION_METRICS_SUMMARY / SEGMENTATION_EXPERIMENT_COMPARISON / SEGMENTATION_RECENT_ROUNDS）各加一行 quickstart 索引。
- 部分核心文档新增 6-11 段落，记录本次工作（状态同步 + planning 主题索引）。
- 新 planning 主题 `.planning/2026-06-11-launch-guide-and-doc-sync/` 4 份文档落地。

## 三档文档分工

| 场景 | 文档 | 体量 |
|---|---|---|
| 任何时候要把 GUI 起来（开发 / 调试 / 临时演示） | `docs/quickstart-launch-guide.md`（本次新增） | 136 行 |
| 演示当天一屏快查（权重 / NIfTI / 显存前置 + 5 步流程） | `docs/demo-day-checklist.md` | 39 行 |
| 本地缓存演示 7 步复跑（cache_key 7 字段 / 4 已知约束） | `docs/local-cache-demo-runbook.md` | 103 行 |

## `Start-Process` 后台启动的设计依据

本次启动文档明确写到：

- **前台跑适用场景**：开发调试、临时打开看实时日志、PowerShell 直接启动。命令：`& "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" tools/start_local_demo.py`。Ctrl+C 退出。
- **后台跑适用场景**：演示挂在副屏、SSH 进去想断开就走、自动化工具管控。命令：PowerShell `Start-Process -FilePath python -ArgumentList tools/start_local_demo.py -WorkingDirectory <项目根> -WindowStyle Hidden`。日志输出到 `.test-output\demo_stdout.log` / `demo_stderr.log`。

设计依据：

- 2026-06-11 实测：用 `bash` 工具前台跑 `python tools/start_local_demo.py` 时，工具 90s 超时后会把整个进程组连带杀掉（uvicorn / vite 父进程都被 kill），导致浏览器访问 127.0.0.1:5173 报 ERR_CONNECTION_REFUSED。
- 用 PowerShell `Start-Process` 后台启动，进程脱离 bash 工具管控，重启电脑才停；适合演示和 SSH 场景。
- 前台跑依然保留（适合调试），但文档里显式提示这个坑。

## 中文主体审查

9 份核心文档的中文主体说明在本次巡检中复审一遍：均符合"中文为主体、技术字段保留英文"的原则（job id / Dice / IoU / HD / profile / checkpoint / API 路径等英文术语保留）。无中文乱码或夹杂英文段落的情况。

## 后续可规划方向

- `tests/startLocalDemo.test.py` 是否需要新增 quickstart-launch-guide 文档存在性 / 关键 flag / 段落 anchor 的 source-grep 守护？现有守护范围已含脚本本身功能行为（spawn / wait_for_samples / 回退），但文档存在性 + anchor 校验还没有。
- `docs/quickstart-launch-guide.md` 与 `docs/demo-day-checklist.md` / `docs/local-cache-demo-runbook.md` 之间的链接交叉引用是否齐全？后续可在 3 份文档末尾加一个"相关文档"段，统一指向另两份。
- 后续若新增 GUI 启动方式（如 Docker / VSCode DevContainer），`docs/quickstart-launch-guide.md` 是最自然的承载位置。

---

*更新日期：2026-06-11*