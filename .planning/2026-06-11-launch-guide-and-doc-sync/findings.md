# 2026-06-11 启动操作手册独立化 + 文档巡检同步 — Findings

> 日期：2026-06-11
> 配套文档：explanation.md / progress.md / task_plan.md

## 关键发现

### 发现 1：GUI 启动文档缺失中间档

**证据**：

- `docs/demo-day-checklist.md`（39 行）面向演示当天，含权重 / NIfTI / 显存等强约束前置。
- `docs/local-cache-demo-runbook.md`（103 行）面向 cache demo 复跑，含 cache_key 7 字段。
- `tools/start_local_demo.py`（222 行）已实现一键启动，但没有任何独立文档把它的 flag、停服、故障排查写出来。

**意义**：新同学 / 临时调试者没有"最简版"操作文档；要起 GUI 必须读完 39 行 checklist 或 103 行 runbook，超出实际需要。

**行动**：本次新建 `docs/quickstart-launch-guide.md`（10 章，136 行），与 checklist / runbook 形成三档分工。

### 发现 2：bash 工具超时连带 kill 整个进程组

**证据**：2026-06-11 实测 — 用 bash 工具前台跑 `python tools/start_local_demo.py`，工具 90s 超时后把整个进程组连带杀掉，浏览器访问 `http://127.0.0.1:5173/` 报 ERR_CONNECTION_REFUSED。`Get-NetTCPConnection -LocalPort 5173,8000` 显示无监听。

**意义**：演示挂副屏、SSH 断开、自动化启动等场景下，前台跑不可靠；必须用 `Start-Process` 把脚本丢到后台独立进程组。

**行动**：`docs/quickstart-launch-guide.md` § 1.2 明确写了 `Start-Process` 后台跑的命令片段，并解释了"为什么不能用前台跑"的原因。

### 发现 3：9 份核心文档均已同步到 6-06 状态

**证据**：

- `git log --oneline -10` 显示最近 4 个 commit 都是文档同步工作（`f604227` / `b4dc8fc` / `af93e21` / `645854e`）。
- 6-06 `f604227 docs: sync 9 core docs + .planning to 2026-06-05 state` 是最近一次大规模文档同步。
- 6-06 `b4dc8fc docs: correct 6-07 to 6-06 in 16 docs (76bb1ff was committed same day)` 修日期笔误。
- 6-06 `af93e21 docs: fix B1-B4 descriptions in REVIEW / RECENT_ROUNDS / AGENTS to match 6-07 real implementation` 修 B1-B4 描述与 `76bb1ff` 真实实现一致。

**意义**：6-06 之后的文档状态是干净的；本次 6-11 工作只需要补 quickstart 索引和 6-11 段落，不需要重新梳理已有描述。

**行动**：本次只对每份核心文档加一行 quickstart 索引；不动已有章节结构。

### 发现 4：CLAUDE.md 关键不变量段已固化 6-06 收口

**证据**：`CLAUDE.md` 第 25-32 行有 "2026-06-06 演示当天收口不变量" 段，含 B1-B4 + start_local_demo + server gating 6 路径 + AMOS 0117 决策。

**意义**：6-11 工作也应在 CLAUDE.md 关键不变量段固化一行，标注 quickstart 文档作为三档分工的入口。

**行动**：CLAUDE.md 关键不变量段末尾加一条"2026-06-11 启动操作手册独立化"不变量。

### 发现 5：中文主体审查通过

**证据**：本次复审 9 份核心文档的中文段落，均符合"中文为主体、技术字段保留英文"的原则：

- README / ACCEPTANCE / REVIEW / SEGMENTATION_RECENT_ROUNDS / SEGMENTATION_EXPERIMENT_COMPARISON / SEGMENTATION_METRICS_SUMMARY / CODE_MODULE_GUIDE / AGENTS 的"当前运行状态 / 当前进行中"段落都是中文叙述。
- 技术字段保留：job id (`aea4e7cdbaf0`)、Dice / IoU / HD / profile (`quality` / `fast`)、checkpoint 路径、`/api/health` API 路径、Python 包名 (`fastapi 0.136.3`) 等。
- 无中英混杂段落、无中文乱码。

**意义**：本次工作不破坏中文主体原则。

**行动**：新增段落严格遵守同一原则。

## 待验证假设

1. **`Start-Process` 后台启动在 SSH 断开 / 自动化场景下不挂**：当前只在 PowerShell 本地窗口测试；远程 SSH 场景是否同样可靠，待真实使用时验证。
2. **`docs/quickstart-launch-guide.md` 与 `docs/demo-day-checklist.md` / `docs/local-cache-demo-runbook.md` 的交叉引用足够清楚**：3 份文档末尾应统一加"相关文档"段指向另两份。当前仅 `quickstart-launch-guide.md` 末尾有"相关文档"段；另两份暂未加。
3. **`tools/start_local_demo.py` 在 CLI flag 变化时 quickstart 文档能跟上**：文档里列了 `--no-persistent-worker` / `--device` / `--reference-cases-json` / `--backend-port` / `--frontend-port` / `--dry-run`；若后续新增 flag（如 `--enable-tailscale`）需同步更新文档。
4. **新同学用 quickstart 文档能 5 分钟内把 GUI 起来**：本轮验证是我自己；建议找一位非项目成员做一遍真实新用户体验测试，验证文档可读性。

## 数据来源

- `tools/start_local_demo.py` 222 行源码
- `docs/demo-day-checklist.md` 39 行
- `docs/local-cache-demo-runbook.md` 103 行
- `git log --oneline -15` 看最近文档同步历史
- 2026-06-11 bash 工具超时实测现象

---

*更新日期：2026-06-11*