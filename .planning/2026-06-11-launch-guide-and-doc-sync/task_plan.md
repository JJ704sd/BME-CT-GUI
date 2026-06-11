# 2026-06-11 启动操作手册独立化 + 文档巡检同步 — Task Plan

> 日期：2026-06-11
> 配套文档：explanation.md / findings.md / progress.md

## 范围

仅文档工作，不涉及任何代码改动。

## 已完成任务（2026-06-11）

- [x] **新建 `docs/quickstart-launch-guide.md`**：10 章（TL;DR / 前置确认 / 标准启动前台+后台 / 启动选项 / 验证 / 停服 / 手工回退 / 局域网 / 一页速记卡 / 相关文档），136 行。
- [x] **README.md 加 quickstart 索引行**：在"代码讲解材料"行后追加一行 + 三档分工说明。
- [x] **AGENTS.md 加 quickstart 索引 + 6-11 段落**：在"5-fold 提分策略"行后追加 "2026-06-11 增量"段。
- [x] **CLAUDE.md 加 quickstart 索引 + 6-11 不变量**：在"部署与设计材料"段加一行；关键不变量段末尾追加"2026-06-11 启动操作手册独立化"条。
- [x] **ACCEPTANCE.md 加 quickstart 索引 + 6-11 段落**：在"5-fold 提分策略"行后追加 "2026-06-11 增量"段。
- [x] **REVIEW.md 加 6-11 段 + 索引**：把 "〇、2026-06-06" 改为 "〇、2026-06-11"，并在该段顶部插入新的 "2026-06-11 启动操作手册独立化" 小节。
- [x] **CODE_MODULE_GUIDE.md 加 quickstart 索引 + 6-11 段落**：在 "2026-05-31 已完成" 段后追加 "2026-06-11 增量" 段。
- [x] **SEGMENTATION_METRICS_SUMMARY.md 加 quickstart 索引 + 6-11 段落**：在"当前进行中"段后追加 "2026-06-11 增量" 段。
- [x] **SEGMENTATION_EXPERIMENT_COMPARISON.md 加 quickstart 索引 + 6-11 审核记录**：在"2026-05-26 审核记录"段后追加 "2026-06-11 启动操作手册独立化审核记录" 段。
- [x] **SEGMENTATION_RECENT_ROUNDS.md 顶部加 6-11 新轮次**：把原"第 1 轮（演示当天 B1-B4）"改为"第 2 轮"，新插入"第 1 轮（最新）— 启动操作手册独立化 + 文档巡检同步"。
- [x] **新 planning 主题 `.planning/2026-06-11-launch-guide-and-doc-sync/` 4 份文档落地**：explanation.md / findings.md / progress.md / task_plan.md。
- [x] **中文主体审查**：9 份核心文档复审，无中文乱码 / 中英混杂 / 中文段落不完整等问题。

## 待完成任务

- [x] **git commit**：本地 commit `87dc21a docs: add quickstart-launch-guide + sync 9 core docs + new planning topic (6-11)`，14 files changed, 543 insertions(+), 3 deletions(-)。
- [ ] **git push**：到 GitHub 远程仓库 `JJ704sd/BME-CT-GUI`。**当前网络受限**：本机 `github.com:443` 不可达（"Failed to connect to github.com port 443 via 127.0.0.1 ... Could not connect to server"），SSH 协议因 host key 未配置也不能用。commit 已保存在本地 ahead of origin/main 1 commit，需要在能访问 GitHub 的网络下手动 `git push origin main`，或先 `git remote add <proxy-url>` 走代理。
- [ ] **后续若新增 GUI 启动方式**（Docker / VSCode DevContainer 等），同步更新 `docs/quickstart-launch-guide.md`。
- [ ] **后续若 `tools/start_local_demo.py` 新增 CLI flag**，同步更新 `docs/quickstart-launch-guide.md` 的"启动选项"段。

## 文档分工总表

| 场景 | 文档 | 体量 |
|---|---|---|
| 任何时候要把 GUI 起来（开发 / 调试 / 临时演示） | `docs/quickstart-launch-guide.md`（本次新增） | 136 行 |
| 演示当天一屏快查（权重 / NIfTI / 显存前置 + 5 步流程） | `docs/demo-day-checklist.md` | 39 行 |
| 本地缓存演示 7 步复跑（cache_key 7 字段 / 4 已知约束） | `docs/local-cache-demo-runbook.md` | 103 行 |

## 推荐下一轮任务（不属于本轮范围）

来自 `.planning/2026-06-06-demo-day-wrapup/task_plan.md` 已有的下一轮候选：

1. **高分辨率 CT 推理优化**（预降采样 768→512，独立 planning）。
2. **5-fold 提分策略**（服务器 5-fold ensemble，独立 planning）。
3. **服务器 AMOS/FLARE 显式 taxonomy 复跑**（确认服务器质量基线，独立 planning）。
4. **跨数据集 cache 链路产品化**（让 cache 链路补丁成为通用机制）。
5. **runbook 自动校验**（防止下次复现同样的困惑；可考虑同步加 quickstart-launch-guide 校验）。
6. **跨数据集标签评估增强**（持续）。
7. **文档与验收口径再同步**（持续；本次 6-11 同步算一轮）。

## 风险

- **远程 SSH / 自动化场景下 `Start-Process` 后台启动的可靠性**：当前只在 PowerShell 本地窗口测试，未在真实 SSH 场景验证。
- **新同学用 quickstart 文档能否 5 分钟内把 GUI 起来**：本轮验证是我自己；建议找一位非项目成员做一遍真实新用户体验测试。
- **9 份核心文档加索引行后的可维护性**：后续每次文档改动都要注意 quickstart 索引是否仍然准确（CLAUDE.md 第 17 行已经写了"不要假设本文件或 README 的"当前状态"节是新鲜的"），需在每次文档同步时检查。

---

*更新日期：2026-06-11*