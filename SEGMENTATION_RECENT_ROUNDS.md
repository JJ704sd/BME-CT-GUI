# 近三轮分割推理滚动记录

> 本文档按时间滚动覆写，只保留最近三轮成功或具备诊断价值的推理数据。历史完整记录见 `SEGMENTATION_EXPERIMENT_COMPARISON.md`。

最近更新：2026-06-11

## 第 1 轮（最新）— 启动操作手册独立化 + 文档巡检同步

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-11 |
| 范围 | 把 `tools/start_local_demo.py` 的"线下实时启动"操作单独抽成 `docs/quickstart-launch-guide.md`，与 `docs/demo-day-checklist.md`（演示当天）和 `docs/local-cache-demo-runbook.md`（cache demo 7 步复跑）形成三档文档分工；9 份核心文档全部巡检并补索引 |
| 受影响逻辑 | 仅文档；`docs/quickstart-launch-guide.md` 新建（10 章：TL;DR / 前置确认 / 标准启动前台+后台 / 启动选项 / 验证 / 停服 / 手工回退 / 局域网 / 一页速记卡 / 相关文档）；9 份核心文档索引段加一行 |
| 文档同步 | `README.md` 加一行；`AGENTS.md` / `CLAUDE.md` / `REVIEW.md` / `ACCEPTANCE.md` / `CODE_MODULE_GUIDE.md` / `SEGMENTATION_METRICS_SUMMARY.md` / `SEGMENTATION_EXPERIMENT_COMPARISON.md` / `SEGMENTATION_RECENT_ROUNDS.md` 都加一行指向 `docs/quickstart-launch-guide.md` |
| 三档文档分工 | `quickstart-launch-guide.md`（任何时候要起 GUI） / `demo-day-checklist.md`（演示当天一屏快查） / `local-cache-demo-runbook.md`（cache demo 7 步复跑 + cache_key 7 字段） |
| 自动验证 | 不涉及代码改动；PowerShell `Start-Process` 后台跑 `tools/start_local_demo.py` 实测确认后端启动 + 采样 `/api/samples` 校验 4 例参考病例（AMOS 0117 / FLARE22 Tr 0009 / WORD / AbdomenCT-1K）已暴露；前台跑 90s 被 bash 工具超时连带 kill 整个进程组（uvicorn + vite 父进程一起被 kill），与 `docs/quickstart-launch-guide.md` 中"为什么必须用 Start-Process 后台启动"的描述一致 |

**问题描述：**

`docs/demo-day-checklist.md` 是面向"演示当天"的强约束前置 + 演示流程卡片（含权重 / NIfTI 前置 + 5 步演示流程 + runbook 回退命令）；`docs/local-cache-demo-runbook.md` 是面向 cache demo 的复跑手册（含 cache_key 7 字段）。但**任何时候**要让一个新同学或临场调试者把 GUI 起来时，没有"最简版"操作文档 — 他们要么读 39 行 checklist 还要做 cache demo 前置，要么读 103 行 runbook 被 cache_key 7 字段吓退。本次把"日常启动"这层独立成 `docs/quickstart-launch-guide.md`，与另两份明确分工。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| `docs/quickstart-launch-guide.md` 新建 | 10 章覆盖：TL;DR 一行启动 + Ctrl+C 停服 / 前置确认 30 秒看完的 3 件事 / 标准启动（前台调试用 + 后台演示用 `Start-Process` 含为什么必须脱离 bash 工具管控的教训）/ 启动选项 flag / 验证启动成功 5 类故障排查 / 停服两种姿势 / 手工回退两条命令 / 局域网联调 / 一页速记卡 / 相关文档 |
| 9 份核心文档索引同步 | README.md / AGENTS.md / CLAUDE.md / REVIEW.md / ACCEPTANCE.md / CODE_MODULE_GUIDE.md / SEGMENTATION_METRICS_SUMMARY.md / SEGMENTATION_EXPERIMENT_COMPARISON.md / SEGMENTATION_RECENT_ROUNDS.md 均新增一行指向 `docs/quickstart-launch-guide.md`，中文主体仍合格 |
| 三档文档分工明确 | 任何时候起 GUI → `quickstart-launch-guide.md`；演示当天 → `demo-day-checklist.md`；cache demo 复跑 → `local-cache-demo-runbook.md` |
| 新 planning 主题落地 | `.planning/2026-06-11-launch-guide-and-doc-sync/` 4 份文档（explanation / findings / progress / task_plan）记录本次启动操作手册独立化与文档巡检同步 |

**结论：** 把"线下实时启动操作"从演示当天 checklist 中独立出来，让日常启动有最简文档可读、演示当天仍走 checklist、cache demo 仍走 runbook；9 份核心文档均已补 quickstart 索引；本轮不修改任何推理 / 缓存 / SSE / validation / 报告代码，不改变 AMOS / FLARE 历史 baseline。

---

## 第 2 轮 — 演示当天 B1-B4 修复 + start_local_demo + server mode gating 收口

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-06（B3 真实完成 `23e0c4d`）；2026-06-06（B1 / B2 / B4 真实补完 `76bb1ff`） |
| 修复内容 | 4 个 demo-day 关键 bug（B1 SSE 进度回退 / B2 取消后残留进度 / B3 后端模型状态对外可读 / B4 SSE 基础异常重试）、演示启动脚本化、server mode gating 6 路径收口、AMOS 0117 演示口径修正、新建演示当天 checklist 短卡片 |
| 受影响逻辑 | `src/main.tsx` SSE onmessage 加 `parsed.heartbeat && parsed.progress === 0` 守护；新增 `inferenceStatusRef` 镜像 React state + cancelled 早退；`/api/health.model_state` 4 字段外露；新增 `src/inference/createInferenceEventSource.ts` 工具（`onretry` / `retryCount` / `onfatal` + 200ms→2s 指数退避 + 默认 3 次上限）；`tools/start_local_demo.py` 新建（setenv + spawn + 启动后采样 `/api/samples` 校验 4 例参考病例 + 失败时打印 runbook 回退）；`server/main.py:1537-1604 get_model_state(runtime_target)` 切换 6 项 server 路径与 4 项本地路径互斥检查 |
| 回归测试 | `tests/imagingLogic.test.ts` B1/B2/B4：新增 11 条 source-grep 断言守护 4 个核心改动（`createInferenceEventSource` / `inferenceStatusRef` / `parsed.heartbeat && parsed.progress === 0` / `onretry` / `retryCount` / `onfatal` / `handle.close()` 等）；`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护 B3；3 个 server gating 测试守护 6 路径 |
| 文档同步 | 9 份核心文档同步到 6-06 状态；4 份 planning 文档落地（`.planning/2026-06-06-demo-day-wrapup/`）；6-06 bug 扫描发现 `23e0c4d` 虚标后所有 9 份核心文档回退虚标并改写为"6-06 `23e0c4d` B3 真实 / 同日 `76bb1ff` B1·B2·B4 真实补完" |
| 自动验证 | `python tools/start_local_demo.py` smoke test 后端启动 + 4 例参考病例已暴露；`node tests/imagingLogic.test.ts`（11 条新断言全过）+ `python tests/backendState.test.py`（4 条新守护全过）+ `npm test` + `npm run build` 全过 |

**6-06 `23e0c4d` 文档虚标与同日 `76bb1ff` 补完说明：**

6-06 commit `23e0c4d` 在 commit message 与文档里写了 B1 / B2 / B4 都修复了，但实际源码只动了 B3（`/api/health.model_state`）。同日 bug 扫描时通过 source-grep 守护发现 `23e0c4d` 虚标：当时 `src/main.tsx` / `src/inference/` 代码里**没有** `createInferenceEventSource` 函数、**没有** `onretry` / `retryCount` 字符串、`tests/imagingLogic.test.ts` 也没有相应 source-grep 守护、SSE onmessage 直接 `setProgress(parsed.progress)` 无 `!== undefined` 守护。同日 commit `76bb1ff`（`fix(sse): B1 heartbeat percent guard + B2 cancel priority + B4 EventSource retry`）真实补完 B1 / B2 / B4 三个 bug，9 份核心文档同步回退虚标并改写为"6-06 `23e0c4d` B3 真实 / 同日 `76bb1ff` 补完"。

**问题描述（按真实 `23e0c4d` B3 + 同日 `76bb1ff` B1·B2·B4 复述）：**

1. **B1 SSE 进度回退**（高）：长耗时推理时，后端 heartbeat 心跳事件不带 `percent` 字段就被前端当成"进度"事件，进度条会从 60% 突然回退到 30% 然后再涨回去，破坏演示视觉。
2. **B2 取消后残留进度**（高）：取消 job 后后端可能继续写 progress 事件或心跳，前端在 React state 已变 `cancelled` 后还会被后续 SSE 事件覆盖显示为"还在跑"或"取消失败"，让评委怀疑系统稳定性。
3. **B3 后端模型状态不外露**（中高）：GUI 状态栏没法直接读 `/api/health.model_state`，需要在前端硬编码 fallback；评委问"模型加载好了吗"时无法即时回答。
4. **B4 SSE 断连无重试**（中）：网络抖动导致 EventSource 断开后，前端直接报错"推理失败"，但实际后端推理仍在跑；需要自动退避重连。
5. **演示启动无统一入口**：`start_local_demo.py` 缺失，每次演示都要手敲 uvicorn 命令、设置 7 个 env var、确认 `/api/samples` 4 个 case 都在；runbook 7 步是新用户门槛。
6. **server mode gating 不全**：`get_model_state(runtime_target=server)` 只检查 2 个 server 路径，缺 `nnUNet_raw` / `nnUNet_preprocessed` / `nnUNet_results` / `output_root`；server runtime 缺 4 项时 `state["missing"]` 不完整，前端展示"已就绪"但实际 server 无法跑 5-fold 推理。
7. **AMOS 0117 演示口径模糊**：原 runbook 写"复跑 AMOS 真实推理会得到更新更准的预测"，但实测 `009d4efdc5f6` 的 `job_summary.json` 显示这就是 2026-05-23 quality profile（`profile=quality` / `tile_step_size=0.5` / `disable_tta=false`）；README 写的 "0.925" 是历史早期权重（已废弃），不再是这个 cache hit 命中的同一预测。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| B1 heartbeat percent guard（6-06 `76bb1ff`） | `src/main.tsx` SSE onmessage 在 `parsed.type === "progress" && parsed.heartbeat && parsed.progress === 0` 时只更新 `stage` 不更新进度；heartbeat 心跳没有 `percent` 字段不再覆盖当前进度。`tests/imagingLogic.test.ts` source-grep 守护 `parsed.heartbeat && parsed.progress === 0` |
| B2 cancel priority（6-06 `76bb1ff`） | 新增 `inferenceStatusRef` 镜像 React state；SSE onmessage 入口先判 `inferenceStatusRef.current.status === "cancelled"` 早退 + `handle.close()` 阻止重试。`tests/imagingLogic.test.ts` source-grep 守护 `inferenceStatusRef.current.status === "cancelled"` |
| B3 /api/health.model_state（6-06 `23e0c4d` 真实完成） | `model_state` 字段从内部变量提升为可被 GUI 状态栏读取的稳定 JSON 字段（`status` / `checkpoint_sha256` / `mode` / `missing` 4 个 key）。`tests/backendState.test.py::test_health_exposes_model_state_for_gui_status_bar` 守护 |
| B4 EventSource retry（6-06 `76bb1ff`） | 抽出 `src/inference/createInferenceEventSource.ts` 工具，暴露 `onretry` / `retryCount` / `onfatal` 字段；onerror 时按 200ms→2s 指数退避重试，最多 3 次；3 次失败后 `onfatal` → reject Promise。`src/main.tsx` SSE 流接入新工具。`tests/imagingLogic.test.ts` 新增 11 条 source-grep 断言 |
| server_required_files 扩到 6 项 | `get_model_state(runtime_target=server)` 现在检查 `server_evaluate_full.py` / `server_dataset.json` / `server_nnunet_raw` / `server_nnunet_preprocessed` / `server_nnunet_results` / `server_output_root`；`local_required_files` 与 `server_required_files` 完全互斥 |
| server gating 3 测试 | `test_server_runtime_reports_missing_server_paths`（4 server 路径缺失时 missing 含对应项）+ `test_local_runtime_does_not_check_server_paths`（`runtime_target=local` 绝不报 server 路径缺失）+ 更新 `test_server_runtime_ready_does_not_require_local_model_files`（4 server + 4 本地路径全缺失，state.missing == []） |
| start_local_demo.py | setenv（`SEGMENTATION_REFERENCE_CASES_JSON` / `SEGMENTATION_DEVICE` / `SEGMENTATION_PERSISTENT_WORKER` 等）+ spawn backend（uvicorn）+ frontend（vite dev）+ 启动后采样 `/api/samples`（最多 15s）校验 4 例参考病例已暴露 + 失败时打印 runbook 回退命令；Ctrl+C 优雅清理子进程 |
| AMOS 0117 演示口径 | runbook 修正：移除"复跑 quality 会更好"假设；改写"2026-05-23 那次就是 quality profile；stomach 0.556 是数据本身的硬骨头；**决策：2026-06-05 接受现状，不复跑 AMOS 0117**"；PPT 直接用"质量推理 mean Dice 0.891，stomach 0.556（review 状态），反映真实临床难度" |
| demo-day-checklist | 一屏可读：前置确认 5 项（cwd / 4 文件存在 / 显存空闲）、演示流程 5 步（cd → start_local_demo → 等 → 浏览器打开 → Ctrl+C）、可能用到的兜底 curl、start_local_demo 失败时回退 runbook 命令 |

**结论：** B1 SSE 进度回退 + B2 取消后残留进度 + B4 SSE 断连无重试三个 BME 竞赛 PPT 演示现场容易被评委抓个正着的边缘 bug 在 6-06 `76bb1ff` 真实补完；B3 后端模型状态对外可读在 6-06 `23e0c4d` 真实完成；`start_local_demo.py` 脚本化演示启动，runbook 短卡片配合长卡 runbook 兜底；server mode gating 6 路径检查后，`runtime_target=server` 不会被本地 Windows nnUNet 文件缺失阻断，server runtime 缺路径时也会显式列出 missing 项；AMOS 0117 演示口径与现状一致（"stomach 0.556 是数据硬骨头"），不再误传"复跑会改善"。本轮不修改 nnUNetv2 推理、缓存复用 7 字段、HTML 报告样式或影像量化逻辑；不改变历史 AMOS/FLARE baseline。

---

## 第 2 轮 — HTML 报告临床报告风格重构（封面 + 摘要 + TOC + 公式 + 分布图）

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-05 |
| 范围 | 把 `src/report/exportReport.ts` 的 HTML 报告从"信息看板"重塑为"临床评估报告"。新增封面页、执行摘要、目录（TOC）锚点导航、§1-§8 章节编号 + 英文小标题、3 个指标公式小贴士（Dice / IoU、Pixel Accuracy、HD95）、严重度分布图（bar chart）、表格 caption + footnote、器官色条 4px、zebra 斑马纹、@media print A4 页眉页码 |
| 受影响逻辑 | `src/report/exportReport.ts` 新增 `--serif` / `--paper` / `--rule` / `--surface-alt` CSS 变量、`.cover` / `.exec-summary` / `.toc` / `.formula-tip` / `.dist-chart` / `.table-caption` / `.footnotes` 7 个新样式块；新增 `distributionChartHtml()` / `severityBuckets()` / `formulaTips()` 工具函数；输出模板改为先封面后正文，正文以 `<section id="sec-N">` 包 8 个小节（§1 报告概览 / §2 摘要 / §3 数据集 / §4 器官 / §5 体素 / §6 距离 / §7 关键发现 / §8 附录） |
| 样式族 | 字体 Source Han Serif / Songti SC + JetBrains Mono；A4 @page + `break-inside: avoid` 用于封面/分布图；square 化 badge / tag（细边框 1px） |
| 自动验证 | `npm test`、`npm run build` 全过（`EXIT=0`）；浏览器打开本地导出的 AMOS 0117 / FLARE22 报告，肉眼确认封面、TOC 跳转、公式 tip、严重度分布图、表格 caption、打印预览页眉页码 |

**问题描述：**

2026-06-04 第一轮美化把 HTML 报告从"工程 dump"提升为"卡片式仪表板"，但仍是 SaaS 风格（圆角大阴影 + 渐变蓝），与 BME 临床报告应有的"评估论文"风格有距离；用户希望报告像医生/算法专家递给同行的内部备忘录，封面应有题图、摘要、目录，公式应就地解释，结论应按严重度排序并出分布图。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| 字体 | `--serif: "Source Han Serif SC", "Songti SC", serif`（正文/标题）+ `--mono: "JetBrains Mono", monospace`（数值/代码/公式） |
| 封面页 `.cover` | 题图条 + 报告编号 + 主标题 + 副标题 + 数据集/病例/生成时间三列 + 操作员/系统指纹两列；`@media print` 下 `break-after: page` 独立分页 |
| 摘要 `.exec-summary` | 一段"总体通过 / 关注点 / 建议" 三栏式；右栏直接列 Dice / HD95 / Pass-Rate 三个核心数字 |
| TOC `.toc` | 8 条锚点链接（§1-§8），点击跳到对应 `<section id="sec-N">`；用 `aria-label` 标注 |
| 章节编号 | 每个 h2 加 `.section-num`（"§ N"） + `.section-en`（英文小标题）；`counter-reset: section` 保证编号连续 |
| 公式小贴士 `.formula-tip` | 3 张：Dice / IoU、Pixel Accuracy、HD95。每张含 LaTeX 风格公式 + 1-2 行白话解释；折叠式 `<details>` 默认展开 |
| 严重度分布图 `.dist-chart` | 对 aiFindings 列表做高/中/低三色桶的 bar chart；高/中/低 label 写明数量与百分比；`break-inside: avoid` |
| 表格 caption + footnote | 每个表前加 `.table-caption`（如"表 4-1 · 15 个器官的逐标签质量"）；表后加 `.footnotes`（如"注：Dice ≥ 0.85 视为通过；HD95 ≤ 3mm 视为临床可接受"） |
| 器官色条 | `.organ-stripe` 4px 色带 + 标签色用于"关键器官列" |
| 斑马纹 | 逐标签表 / 指标表加 `tr:nth-child(odd)` 浅灰行 |
| @media print | A4 + 页眉（`报告 · caseId · generatedAt`） + 页脚（`page X of Y` 用 CSS counter）；正文 padding 适配 |

**结论：** 报告风格从"信息仪表板"升级为"临床报告"。封面、摘要、目录、章节编号、公式 tip、严重度分布图、caption/footnote 全部就绪；打印预览（Ctrl+P）会按 A4 自动分页且带页眉页码。本轮不修改 nnUNetv2 推理、缓存复用、SSE 协议、validation 字段或量化逻辑；与 6-04 第一轮美化的所有功能（remap 警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条、aiFindings 严重度高亮 + 排序、器官列表折叠、逐标签表列固定 + 排序）保持兼容并叠加生效。

---

## 第 3 轮 — HTML 报告第一轮美化（视觉层 + 信息层）

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-04 |
| 范围 | 把 `src/report/exportReport.ts` 的 HTML 报告从"工程 dump"提升为"卡片式仪表板"。视觉层加色阶图例、Header 渐变、3 个 metric group 组标题图标、aiFindings 严重度高亮 + 排序、器官列表折叠、逐标签表列固定 + 列点击排序、`@media print` A4 页眉页码；信息层加 remap_applied 顶部警告条、taxonomy / dataset_hint 展示位、spacing 可视化（3 色块）、historical 警告条 |
| 受影响逻辑 | `src/report/exportReport.ts` 新增 `.legend` / `.remap-banner` / `.historical-banner` / `.spacing-bar` / `.severity-{high,medium,low}` / `.organ-list`（`<details><summary>`）/ `position: sticky` 表头 6 个新 CSS 块；新增 `getSeverityClass()` / 排序函数；HTML 末尾注入 `<script>` 实现列点击排序 |
| 字段透传 | `src/main.tsx:handleExport` 构造 `ReportData` 时透传 `validation.remap_applied` / `taxonomy_match` / `dataset_hint` / `historical` / `label_taxonomy`（这些字段已在 `inferenceClient.ts:117-147 normalizeValidation` 白名单） |
| 自动验证 | `npm test`、`npm run build` 全过（`EXIT=0`）；浏览器自检 9 项视觉/信息元素；`tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class |

**修复要点：**

| 修改项 | 说明 |
|---|---|
| 色阶图例 `.legend` | metric group 顶部一行：HD/HD95/ASD 共用"≤1mm 绿 / ≤3mm 黄 / >3mm 红"；Dice/IoU 共用"≥0.85 绿 / ≥0.7 黄"；色块 + 阈值文字 |
| Header 渐变 | `linear-gradient(135deg, #0b3d91, #1a73e8)` → `linear-gradient(135deg, #1a73e8 0%, #4a90e2 50%, #6bb6ff 100%)` + `box-shadow: 0 4px 12px rgba(0,0,0,0.08)` |
| 分组节奏 | 3 个 metric group 加组标题图标（`OverlapIcon` / `PixelIcon` / `DistanceIcon` 内联 SVG）；卡片 `gap: 16px`；组间 `margin: 32px 0` |
| aiFindings | `<ul class="ai-findings">`；每条加 `.severity-{high,medium,low}`（红/黄/绿）；按严重度排序 |
| 器官列表 | `<details><summary>` 让 15 个器官可折叠，默认展开 |
| 逐标签表 | thead `position: sticky; top: 0`；首列 `position: sticky; left: 0; z-index: 2`；表头 `cursor: pointer` + `data-sort` 属性；列点击排序 |
| @media print | A4 + 页眉 caseId + 页脚 `page X of Y`（用 CSS counter） |
| remap_applied 警告条 | `.remap-banner.remap-on`（黄底红字"已自动 remap: FLARE22 → AMOS22"）/ `.remap-banner.remap-off`（绿底"标签体系已对齐"） |
| taxonomy / dataset_hint 展示位 | `.label-stats` tag 行加 `taxonomy: AMOS22` / `dataset_hint: AMOS22` tag；颜色按 `taxonomy_match` 区分 |
| spacing 可视化 | `.spacing-bar`：3 个小色块（sx/sy/sz）按 `min=0.5mm / max=2.0mm` 反向归一化，色阶绿 → 黄 |
| historical 警告条 | `.historical-banner`（灰底斜体"（历史离线缓存摘要，未在当前 job 重新验证）"） |

**结论：** 报告信息密度和可读性都明显提升。cache hit 显示历史摘要、FLARE22 自动 remap、AMOS 原生无 remap 三种状态都有专门提示；aiFindings 按严重度排序并上色，临床使用者能直接定位高严重度问题；打印预览有页眉页码。本轮不修改 nnUNetv2 推理、缓存复用、SSE 协议、validation 字段或量化逻辑；6-05 第二轮临床报告风格重塑与本轮所有功能兼容并叠加生效。

---

## 第 4 轮 — 质量评估指标扩展 + 表面距离计算加速

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-03 |
| 范围 | 把质量评估报告补齐到 Dice、IoU、Pixel Accuracy、Hausdorff Distance（含 HD95、ASD）等医学影像主流指标；同步收紧 6 EDT/label 的性能瓶颈，把每个 label 的 `distance_transform_edt` 调用从 6 次合并到 2 次 |
| 受影响逻辑 | `server/main.py` 新增 `surface_distances()`（1 crop + 2 EDT/label）并替换 `compute_label_metrics()`；保留 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 旧函数供回归测试对照；`src/inference/inferenceClient.ts` 在 `ValidationSummary` / `LabelMetric` 增补 12 个新字段（`pixel_accuracy` 4 项 + HD/HD95/ASD 9 项 + `surface_distance_unit` + `spacing`）；`src/report/exportReport.ts` 报告模板新增 3 个 metric group（区域重叠度 · Dice / IoU、像素准确率 · Pixel Accuracy、表面距离 · HD / HD95 / ASD）和 4 个逐标签列 |
| 回归测试 | `tests/backendState.test.py` 新增 `test_surface_distances_matches_legacy_individual_functions`（4 shape × 8 场景，1e-9 精度）、`test_surface_distances_uses_fewer_distance_transforms_than_legacy`（patch `scipy.ndimage.distance_transform_edt` 计数恒为 2）、`test_compute_label_metrics_with_surface_distances_faster_than_legacy`（壁钟测试，断言新路径比旧路径快 ≥30%）；`tests/imagingLogic.test.ts` 新增对全部新 metric 字段的 source-grep 约束和 `parseInferenceEvent()` complete 事件解析值测试 |
| 自动验证 | `python tests/backendState.test.py`、`npm test`、`npm run build` 全过（`EXIT=0`） |

**问题描述：**

2026-05-25 验收 baseline 在 quality profile 下计算 Dice、IoU、HD 三类指标已经稳定，但验收指南要求把质量评估报告补齐到包括 Pixel Accuracy、Hausdorff Distance 在内的医学影像主流指标。本轮之前，HTML 报告只有 Dice / IoU 卡片，逐标签表也只有 Dice / IoU / HD 三列；用户上传标签后看到的是不完整质量视图。`tools/segmentation_metrics_summary.py` 在 offline 端其实已经能输出 Pixel Accuracy、HD、HD95、ASD，但前端 `inferenceClient.ts` 的白名单里没有这些字段，整条 validation 通路会无声丢弃。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| 后端 `surface_distances()` | 单个 label 的 surface distance 一次性完成：1 次 crop + 2 个 surface mask + 2 次 `distance_transform_edt`（预测→参考、参考→预测），再用 value 数组算 `asd` / `hd` / `hd95` / `forward_*` / `backward_*`，省掉 `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 各跑一次的重复 EDT |
| 旧函数保留 | `average_surface_distance` / `hausdorff_95` / `hausdorff_distance_full` 保留为 legacy，供 `test_surface_distances_matches_legacy_individual_functions` 做 1e-9 精度对照 |
| compute_label_metrics | 单个 label 改用 `surface_distances()`；foreground 也走 `surface_distances()`（非全 volume union mask） |
| 字段扩展 | 12 个新字段（pixel_accuracy / mean_pixel_accuracy / min_pixel_accuracy / foreground_pixel_accuracy、mean_asd / max_asd / foreground_asd、mean_hd / max_hd / foreground_hd、mean_hd95 / max_hd95 / foreground_hd95、surface_distance_unit="mm"、spacing=[sx, sy, sz]）；per-label 增补 `pixel_accuracy` / `asd` / `hd` / `hd95` |
| 前端白名单 | `normalizeValidation()` 添加上述字段到白名单；`parseInferenceEvent()` 解析时把这些字段透传 |
| HTML 报告 | 新增"区域重叠度 · Dice / IoU"、"像素准确率 · Pixel Accuracy"、"表面距离 · HD / HD95 / ASD"3 个 metric group（共 19 张卡片，HD/HD95/ASD 卡片用 mm 单位 + 越低越好的色阶 ≤1mm 绿、≤3mm 黄、>3mm 红）；逐标签表加 4 列：像素准确率、ASD (mm)、HD95 (mm)、HD (mm)；逐标签表 chips 显示 `spacing` 和 `surface_distance_unit` |
| 性能实测 | AMOS 0117 quality 缓存命中：旧路径 `38.86s` → 新路径 `16.78s`，约 2.3× 加速（CPU `distance_transform_edt` 调用次数从每 label 6 次降到 2 次） |

**结论：** 质量评估报告已补齐到 Dice / IoU / Pixel Accuracy / HD / HD95 / ASD 共 6 类医学影像主流指标。HTML 报告、JSON 报告、PDF 报告三层都同步支持新字段；逐标签表现已能直接看出哪个器官的边界差距（HD/HD95/ASD mm）最大。`surface_distances()` 2 EDT 优化让 768×768×103 这类高分辨率 CT 的 validation 不再比推理本身慢一个数量级。本轮不修改 nnUNetv2 推理、缓存复用、SSE 协议或影像量化逻辑；也不改变历史 AMOS `quality` profile（`b3c528cc9e20`，mean Dice 0.924780）、FLARE22 自动 remap（`a717dacf42d3`，mean Dice 0.926）和 FLARE22 离线 remap（`86b0153d0a73`，mean Dice 0.893127）三套基线数值；新指标在 AMOS quality 缓存命中（`2d477d8bbd7d` / `aea4e7cdbaf0` / `9fd0fdc39960` / `096e5b8349df`）上的具体数值为 mean Dice 0.891327、mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm。

---

## 第 5 轮 — dataset_hint 字段打通 auto 边界

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-02 |
| 修复内容 | 新增 `dataset_hint` 表单字段：前端 `loadReferenceCase()` 把 `referenceCase.dataset` 写入 `referenceCaseDatasetHint` 状态并随 job 提交；后端 `validate_against_custom_label()` 在 `taxonomy=auto + dataset_hint=FLARE22` 时强制 remap，覆盖 0.85 守卫的 None |
| 受影响逻辑 | `server/main.py:Job.dataset_hint` / `create_job` / `validate_against_custom_label()`；`src/main.tsx:referenceCaseDatasetHint` 状态；`src/inference/inferenceClient.ts:createInferenceJob` 新增 `datasetHint` 选项 |
| 回归测试 | `tests/backendState.test.py` 新增 `test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto`（FLARE22 真实 1-13 + AMOS ckpt 1-15，验证 `taxonomy=auto + dataset_hint=FLARE22` 走 remap、`taxonomy=auto + dataset_hint=AMOS22` 不 remap） |
| 自动验证 | `python tests/backendState.test.py`、`npm test`、`npm run build` 全过（`EXIT=0`） |

**问题描述：**

第 1 轮 0.85 coverage 守卫上线后，FLARE22 真实 1-13 标签也会被 `detect_dataset()` 返回 `None`，导致 FLARE22_Tr_0009 在 `taxonomy=auto` 模式下走不到 remap 路径——即使前端已经按 `referenceCase.dataset` 把 `label_taxonomy` 自动设成 `FLARE22`，但如果用户把 `label_taxonomy` 切回 `auto`，Dice 仍会跌到 0.073 量级。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| 后端 Job 字段 | `Job.dataset_hint: str \| None = None`；`create_job` 接收 `dataset_hint: str \| None = Form(None)`，归一化（`strip().upper()`）后写入 job state |
| 后端优先级 | `taxonomy_hint=AMOS22/FLARE22` → `dataset_hint=FLARE22/AMOS22` → `detect_dataset()`；`dataset_hint=FLARE22` 覆盖 0.85 守卫的 None |
| 后端 action 文案 | 区分"已按用户选择" / "已按参考病例" / "已自动" |
| 前端状态 | `referenceCaseDatasetHint` 在 `loadReferenceCase()` 成功后写入 `referenceCase.dataset`；catch / else / 上传自定义 NIfTI（`role === "source"`）时清空 |
| 前端 inference client | `createInferenceJob` options 增加 `datasetHint?: string \| null`；`formData.append("dataset_hint", ...)` |
| `auto` 行为 | 仍为保底；`dataset_hint` 是 auto 边界下让 FLARE22 真实 1-13 仍能 remap 的补充信号 |

**结论：** FLARE22 真实 1-13 病例在 `taxonomy=auto` 下能正确 remap（`remap_applied=true`、`remap_source=FLARE22`）；`dataset_hint=AMOS22` 不误 remap；上传自定义 NIfTI 时 `referenceCaseDatasetHint` 自动清空。本轮不修改 `server/taxonomy.py` 的判定逻辑、不改变 nnUNetv2 推理、缓存复用、SSE 协议、影像量化或历史基线指标数值。

---

## 第 6 轮 — detect_dataset 二轮收紧 + 前端按 dataset 预设 taxonomy

| 项目 | 值 |
||---|
| 日期 | 2026-06-02 |
| 修复内容 | `detect_dataset()` 收紧：参考覆盖 ckpt 标签 ≥ 0.85 时返回 `None`（`auto` 退化为保底）；前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy` |
| 受影响逻辑 | `server/taxonomy.py:detect_dataset()`、`src/main.tsx:mapDatasetToLabelTaxonomy()` 与 `loadReferenceCase()` |
| 回归测试 | `tests/backendState.test.py` 新增 AMOS 1-13 + ckpt 1-15 真实 case 测试；更新 FLARE22 1-13 + ckpt 1-15 用例注释 |
| 自动验证 | `python tests/backendState.test.py`、`npm test`、`npm run build` 全过（`EXIT=0`） |

**问题描述：**

2026-06-01 现场复测时发现，AMOS 0117 自身标签在 `detect_dataset()` 中仍可能被错判为 FLARE22，触发 `remap_applied=true`，AMOS 推理 Dice 异常偏低。原因：

- AMOS 真实 `amos_0117_label.nii/amos_0117(2).nii` 实际 unique IDs 为 `{1..13}`，缺 14/15（bladder/prostate）。
- FLARE22 真实标签 unique IDs 也是 `{1..13}`。
- 两者在裸 ID 集合上不可分，仅靠命名对比无法稳定区分。

**修复要点：**

| 修改项 | 说明 |
|---|---|
| `detect_dataset()` 0.85 守卫 | `coverage = len(reference_ids ∩ ckpt_ids) / len(ckpt_ids) >= 0.85` → `None` |
| 前端预设 | `loadReferenceCase()` 在拿到参考 label 后立即调用 `mapDatasetToLabelTaxonomy()`；AMOS/AMOS22 → `AMOS22`、FLARE/FLARE22 → `FLARE22`、其他保持原值 |
| `auto` 行为 | 退化为保底策略；`label_taxonomy=AMOS22` / `FLARE22` 显式选择仍是正式质量基线入口；`dataset_hint` 字段补充 auto 边界下 FLARE22 真实 1-13 的 remap 路径 |
| 用户体验 | 用户仍可在 UI 切换 taxonomy；前端预设只是默认值 |

**回归测试覆盖：**

| 用例 | reference | checkpoint | 期望 |
|---|---|---|---|
| AMOS 自指 1-15 | `{1..15}` | `{1..15}` | `None`（短路 `==`） |
| AMOS 真实 1-13 | `{1..13}` | `{1..15}` | `None`（coverage 0.867 ≥ 0.85） |
| FLARE22 真实 1-13 | `{1..13}` | `{1..15}` | `None`（coverage 0.867 ≥ 0.85；前端预设补 / `dataset_hint=FLARE22` 覆盖） |
| AMOS 子集 {1,2,6} | `{1,2,6}` | `{1..15}` | `None`（进入循环，mismatch=0 < 5） |
| Partial {1,3} | `{1,3}` | `{1,3,6}` | `None`（`len(shared_ids) < 3` 守卫） |

**结论：** `auto` 模式在裸 ID 不可分的边界（AMOS 1-13 vs FLARE22 1-13）退化为保底，避免错误 remap。正式 taxonomy 由前端 `loadReferenceCase()` 按 `referenceCase.dataset` 字段预设；`dataset_hint` 字段补充 `auto` 边界下 FLARE22 真实 1-13 的 remap 路径；用户仍可在 UI 切换。本修复不改变 nnUNetv2 推理、缓存复用、SSE 协议或影像量化逻辑。

---

## 第 7 轮 — 本地缓存演示 7 步验证

| 项目 | 值 |
|---|---|
| 日期 | 2026-06-01 |
| 病例 | AMOS 0117 + FLARE22 Tr 0009（项目自带 4 例 reference cases） |
| 运行位置 | 本地 RTX 4060（`runtime_target=local`） |
| 目的 | 跑通“同输入 → 真实 nnUNetv2 推理 → 缓存回填 → 二次命中”全链路，并沉淀可重跑脚本与运行说明 |
| 新增脚本 | `tools/seed_demo_cache.py`（替换了仅 AMOS 版的 `tools/seed_amos_cache.py`） |
| 新增运行说明 | `docs/local-cache-demo-runbook.md`（启动命令、关键路径、cache_key 7 字段、已知约束） |
| 新增 spec/plan | `docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`、`docs/superpowers/plans/2026-06-01-local-cache-demo.md` |
| 后端依赖 | 在 `D:\BME2026\BME_CT_Seg\nnunet_env` 装了 `fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30` |

**4 步演示结果：**

| 演示步骤 | job_id | mode | cache_key（前 16 位） | 耗时 | 结果 |
|---|---|---|---|---|---|
| AMOS 0117 cache hit | `aea4e7cdbaf0` | `cached-real-nnunetv2` | `4e0eb3cd29145b70` | ~3s | 命中手工 seed 的 `009d4efdc5f6`；validation `review`，mean_dice 0.891（stomach 0.556 偏低） |
| FLARE 真实推理 | `0aa7323a4c01` | `real-nnunetv2` | `0f9c6d68e314b3d7` | 218s | RTX 4060，quality + TTA，3d_fullres，结果 120KB |
| FLARE cache hit | `02da885c97d8` | `cached-real-nnunetv2` | `0f9c6d68e314b3d7` | 0.001s | 命中 `0aa7323a4c01` |

**7 步任务验收：**

| 阶段 | 状态 | 备注 |
|---|---|---|
| Task 1 装 fastapi/uvicorn | ✓ | fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30 |
| Task 2 启动后端 | ✓ | cwd=project subdir，`/api/health` ready=true；`/api/samples` 含 4 例（设置 `SEGMENTATION_REFERENCE_CASES_JSON` 后） |
| Task 3 启动前端 | ✓ | Vite 6.4.2, http://127.0.0.1:5173/ → 200 |
| Task 4 AMOS cache hit | ✓ | `aea4e7cdbaf0`, mode=cached, source=`009d4efdc5f6` |
| Task 5 FLARE 真实推理 | ✓ | `0aa7323a4c01`, 218s, 120KB result |
| Task 6 FLARE cache hit | ✓ | `02da885c97d8`, 0.001s, source=`0aa7323a4c01` |
| Task 7 写 runbook | ✓ | `docs/local-cache-demo-runbook.md` |

**cache_key 7 字段（任一不一致即失配）：**

1. `input_sha256`（输入文件 SHA-256，非路径；重压缩即失配）
2. `checkpoint_sha256`（`nnunetv2_files/checkpoint_best.pth` 的 SHA-256）
3. `checkpoint_dataset_name`（如 `Dataset001_AMOS22`）
4. `checkpoint_configuration`（如 `3d_fullres`）
5. `labels_source`（内置 AMOS checkpoint label vs 用户上传 label）
6. `runtime_target`（`local` vs `server`，互不混用）
7. `inference_options`（`quality` vs `fast`，TTA、tile_step_size 也算）

**结论：** 本地 4 步演示完整跑通，cache_key 7 字段隔离正确，二次命中耗时 < 5s；AMOS 预热预测的 review 状态（stomach 0.556）属于 5 月 23 日历史推理结果，本次未重训，复跑 AMOS 真实推理会得到更新更准的预测。`tools/seed_demo_cache.py` 幂等可重跑，便于在演示前预热 AMOS 缓存或在新机器上确认 FLARE 缓存存在。

---

## 第 8 轮 — label_taxonomy 修复与 AMOS CT 推理完成

| 项目 | 值 |
|---|---|
| 日期 | 2026-05-31 |
| 修复内容 | 显式 `label_taxonomy=auto\|AMOS22\|FLARE22`，`detect_dataset()` 更保守 |
| 验证 job | `d56bcff76a8b`（AMOS22 选择，`remap_applied=false`） |
| AMOS CT 推理 | job `ad3d14eba3de`，768×768×103，fast profile，mean_dice=0.77724 |
| 部署包 | `server-runtime-package-20260531.zip` |

**label_taxonomy 修复要点：**

| 修改项 | 说明 |
|---|---|
| `detect_dataset()` | 标签 ID 是 checkpoint 子集时不触发 remap |
| `label_taxonomy` 参数 | `auto`：保守检测；`AMOS22`：强制不 remap；`FLARE22`：强制 remap |
| 缓存 key | `label_taxonomy` 已纳入，不同标签体系结果不会混用 |
| 测试更新 | `tests/backendState.test.py` 已更新期望值 |

**AMOS CT 推理速度分析：**

| 瓶颈因素 | 说明 |
|---|---|
| 输入分辨率 | 768×768 是标准 512×512 的 1.5 倍，面积 2.25 倍 |
| GPU 显存 | 8GB 显存占用 95%，接近上限 |
| GPU 功率 | 27W/40W，受限于笔记本散热 |
| 模型复杂度 | 8 阶段 ResidualEncoderUNet，约 10.2M 参数 |
| 2D 模型处理 3D 数据 | 逐切片处理 103 层，每层需独立推理 |
| 重采样开销 | nnUNetv2 需将 768×768 重采样到模型 patch 640×640 |

**结论：** label_taxonomy 修复已完成，AMOS 标签不再被误判为 FLARE22。AMOS CT 高分辨率推理完成，fast profile 下 mean_dice=0.77724（低于 quality 的 0.924791，符合预期）。建议后续高分辨率 CT 可考虑预降采样以加速推理。

---

## 第 9 轮 — 服务器 AMOS 0117 validation 异常

| 项目 | 值 |
|---|---|
| job_id | `5d8f5eee7b75` |
| 日期 | 2026-05-30 |
| 病例 | AMOS 0117 |
| 运行位置 | Ubuntu 服务器，5GPU / 5-fold soft ensemble |
| 前端接入 | Windows GUI 通过校园网 API endpoint |
| 模式 | `real-nnunetv2` |
| 缓存 | 否 |
| 推理配置 | quality / tile_step=0.5 / TTA on |
| 总耗时 | `586.453s`（约 9分46秒） |
| 主要阶段 | `server_fold_predict=449.5s`, `server_ensemble=131.116s`, `validation=5.51s` |
| 结果大小 | `141986 bytes` |
| remap_applied | `true` |
| remap_source | `FLARE22` |

**验证结果：**

| 指标 | 值 | 状态 |
|---|---:|---|
| 平均 Dice | `0.076015` | 未通过 |
| 最低 Dice | `0.000000` | 未通过 |
| 前景 Dice | `0.979808` | 前景总体高度重合 |
| validation status | `review` | 建议人工复核 |

**结论：** 服务器推理、soft ensemble、下载和 GUI 回填链路已跑通。该轮 Dice 异常不应直接解读为模型完全失败，因为 foreground Dice 很高，但报告显示 AMOS 标签被自动当作 FLARE22 执行 remap。下一步需用显式 `label_taxonomy=AMOS22` 复跑，并确认 `remap_applied=false`。

---

## 第 10 轮 — 服务器 FLARE22 + 自动 remap 在线验证

| 项目 | 值 |
|---|---|
| 日期 | 2026-05-30 |
| 病例 | FLARE22 |
| 运行位置 | Ubuntu 服务器，5GPU / 5-fold soft ensemble |
| 前端接入 | Windows GUI 通过校园网 API endpoint |
| 模式 | `real-nnunetv2` |
| 缓存 | 否 |
| 推理配置 | quality / tile_step=0.5 / TTA on |
| 总耗时 | 约 `3分48秒` |
| 瓶颈阶段 | 服务器 5-fold 推理约 `2分55.3秒` |
| 结果大小 | 约 `117.2 KB` |
| remap | FLARE22 → 当前 AMOS 模型 |

**验证结果（自动重映射后）：**

| 指标 | 值 | 状态 |
|---|---:|---|
| 平均 Dice | 约 `0.891` | 可用，仍需复核最低标签 |
| 最低 Dice | 约 `0.657` | 低于 0.70，建议人工复核 |
| 前景 Dice | 约 `0.951` | 前景重合良好 |

**结论：** FLARE 服务器轮次说明服务器模式下 5-fold 推理、soft ensemble、自动 taxonomy remap、validation 和前端回填均可工作。该结果是服务器链路跑通证据，但仍应与 AMOS 原生标签质量基线分开解释。

---

## 历史基线 — FLARE22 + 自动 Taxonomy Remap 在线验证（本地）

| 项目 | 值 |
|---|---|
| job_id | `a717dacf42d3` |
| 日期 | 2026-05-28 |
| 病例 | FLARE22 Tr 0009 |
| 标签文件 | 已上传（自动 taxonomy remap） |
| 模式 | real-nnunetv2 |
| 缓存 | 否 |
| 推理配置 | quality / tile_step=0.5 / TTA on |
| remap_applied | True |
| remap_source | FLARE22 |

**验证结果（自动重映射后）：**

| 指标 | 值 | 阈值 | 状态 |
|---|---:|---:|---|
| 平均 Dice | `0.926` | ≥ 0.85 | 通过 |
| 验证状态 | passed | — | 自动验证通过 |

**结论：** 自动 taxonomy remap 上线后，FLARE22 标签在线验证从 mean_dice=0.073 提升到 0.926。后端自动检测 FLARE22 数据集并按器官名重映射标签 ID，无需手动干预。跨数据集在线验证链路正式打通。

---

## 近三轮趋势

| 维度 | 第 1 轮（B1-B4 + start_local_demo + server gating） | 第 2 轮（HTML 报告临床报告风格重构） | 第 3 轮（HTML 报告第一轮美化） |
|---|---|---|---|
| 范围 | cache demo Phase A taxonomy 链路收口 + 演示启动脚本化 + server mode gating 6 路径 | 封面 + 摘要 + TOC + 公式 tip + 严重度分布图 + caption/footnote + 打印页眉页码 | 色阶图例 + remap/historical 警告条 + taxonomy 展示位 + spacing 可视化 + aiFindings 排序 + 器官折叠 + 列固定/排序 |
| 改动 | `validate_against_debug_label` 接 taxonomy 字段、`complete_cached_job` 覆盖 historical、`find_cached_prediction` degenerate warning、`server_required_files` 2→6 项、新建 `tools/start_local_demo.py` + 12 测试 | exportReport.ts +7 个新 CSS 块 + 3 个工具函数；8 段章节结构 | exportReport.ts +6 个新 CSS 块 + 2 个工具函数；HTML 注入列排序脚本 |
| 耗时影响 | smoke test 后端启动 + 4 例参考病例已暴露；start_local_demo.py 一行启动 ≈5s | 仅影响导出/打印渲染时间（与 6-04 同量级） | 仅影响导出渲染时间 |
| 验证口径 | 6 个新 backend 测试 + 12 个 start_local_demo 测试 + 9 个 6-05 CSS source-grep；AMOS 0117 演示口径文档化 | 9 项视觉/信息元素 + 打印预览；`tests/imagingLogic.test.ts` source-grep 保护 4 个新 class | 9 项视觉/信息元素浏览器自检；同 source-grep 保护 |
| 核心问题 | 演示当天 4 类关键 bug 收口 + 启动流程脚本化 + server gating 不会因本地文件缺失误判 | 报告从仪表板升级为临床报告，演示与答辩可直出 PDF | 信息密度与可读性提升，cache hit / remap / historical 三态都有专门提示 |

---

## 待解决问题

### 问题 0：质量评估指标已收口（2026-06-03）

**现状：** 2026-06-03 已把 quality 评估报告补齐到 6 类医学影像主流指标（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD），逐标签表现已能直接显示 HD/HD95/ASD mm 列；`surface_distances()` 把单 label EDT 调用从 6 次合并到 2 次，AMOS 0117 quality cache hit 的 validation 阶段从 38.86s 降到 16.78s（约 2.3× 加速）。

**行动：** 后续在新增 3D 模型或新数据集时，应在 `compute_label_metrics()` 调用入口直接复用 `surface_distances()`；新增 `surface_distances()` 调用方时需要确认仍然只调用 2 次 EDT，不要回退到旧 6 EDT 模式。HD/HD95/ASD 报告卡片使用 ≤1mm 绿 / ≤3mm 黄 / >3mm 红的色阶；与 `quality` profile 的 0.85/0.70 阈值不同，避免把距离指标和 Dice 阈值混用。

### 问题 1：高分辨率 CT 推理速度优化

**现状：** 2026-05-31 的 AMOS CT（768×768×103）推理已完成，fast profile mean_dice=0.77724，低于 quality 基线 0.924791。主要瓶颈是输入分辨率高于模型训练时的标准尺寸，导致计算量增加约 2.25 倍。

**行动：**

- 短期：保留当前 fast profile 作为高分辨率预览证据，但不得作为正式质量基线。
- 中期：考虑在推理前对高分辨率 CT 进行预降采样（如 768→512），可显著缩短推理时间。
- 长期：评估是否需要训练支持更高分辨率的模型，或在 nnUNetv2 配置中调整 patch size。

### 问题 1：AMOS 原生标签可能被误判为 FLARE22 [已修复]

**现状：** 已实现显式 `label_taxonomy=auto|AMOS22|FLARE22`，`detect_dataset()` 更保守：标签 ID 是 checkpoint 子集时不触发 remap。验证 job `d56bcff76a8b` 确认 AMOS22 选择时 `remap_applied=false`。

**行动：** 后续服务器 AMOS validation 复跑时使用 `label_taxonomy=AMOS22`，确认 `remap_applied=false` 后纳入正式质量基线。

### 问题 2：server 模式 gating 仍需收口

**现状：** `/api/models` 默认仍可能显示 `runtime_target=local` 并报告本地 Windows nnUNet 文件缺失；服务器云端推理创建 job 时不应依赖本地 `dataset.json/plans/checkpoint/python.exe`。

**行动：**

- `runtime_target=server` 只检查 server runtime 必需路径。
- `runtime_target=local` 才检查本地 nnUNet 文件。
- 保留 `/api/models` 和 job summary 中的最终 runtime target，避免误读当前运行位置。

### 问题 3：标签文件传输和缓存 validation 语义已收口

**现状：** 标签上传入口、FormData `label_file`、后端保存路径和在线 validation 已有回归覆盖；缓存命中只复用预测 NIfTI，不复用旧 validation。

**行动：** 后续观察改为检查 job summary、`label_path`、`validation_summary.json` 和 validation 结果，不再依赖控制台文件名日志。

### 问题 4：量化报告需跟随结果回填验证

**现状：** 影像量化分析已作为纯前端能力接入，计算依赖推理完成后的预测 mask 和 NIfTI spacing，不改变服务器推理、缓存或 validation 链路。

**行动：** 后续每次做服务器 smoke 或报告验收时，在“结果下载并回填 GUI”之后补充检查：评估模块是否显示量化面板、HTML/JSON/PDF 报告是否包含 `quantification`，并确认壁厚和精确管腔指标仍显示为不可用/后续扩展。

### 问题 5：AMOS 预热预测质量偏低（cache hit 暴露 review 状态）

**现状：** 2026-06-01 本地缓存演示发现 AMOS 0117 预热预测（`009d4efdc5f6`，2026-05-23 推理，138KB）validation 为 review，mean_dice 0.891，stomach 0.556。该预测是当前唯一会被 cache hit 复用的 AMOS 推理结果；首次未缓存新推理可换更新预测（job `b3c528cc9e20` quality 模式 mean_dice 0.924780、stomach 0.846569）。

**行动：**

- 演示前允许 `tools/seed_demo_cache.py` 把 009d4efdc5f6 写为 cache hit，标签上明确是 review 不是 passed。
- 若需 quality 模式 AMOS 验证，优先做真实新推理（已通过 `find_cached_prediction()` 复用现成 `b3c528cc9e20` 缓存）。
- 后续如果 AMOS 重新训练或新 checkpoint 接入，需重跑 `tools/seed_demo_cache.py` 让 `cache_key` 重新指向新预测，否则历史 cache hit 会继续给出旧指标。

### 问题 6：FLARE22 cache hit 显示 AMOS 数据 [已修复]

**现状：** 2026-06-01 晚间现场复测时，FLARE22 Tr 0009 cache hit（`02da885c97d8`）显示的 validation 摘要来自 `009d4efdc5f6`（AMOS 0117 历史推理），mean_dice 0.891（stomach 0.556），与 README/参考病例的 0.893/0.674/0.950 不一致。看起来像是"FLARE22 cache hit 用了 AMOS 的数据"。

**根因：** 1) `find_cached_prediction()` 只按 mtime 排序候选，空 job 目录被误选；2) `complete_cached_job()` 不回退到 cache_source_job_id 的 `validation_summary.json`，cache hit 找不到当前 validation 时直接给 null；3) 0aa7323a4c01 与 2026-05-26 历史 `86b0153d0a73` 的预测字节不同，cache_key 不一致，无法直接复算；4) 现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，导致 FLARE22 Tr 0009 根本没出现在 `/api/samples`，所有"参考病例载入"都跑到了 AMOS 0117。

**行动：**

- 已实现 `complete_cached_job()` 的 historical 回退：读 `cache_source_job_id/output/validation_summary.json`，加 `historical: true` 和 `source_job_id`。
- 已修改 `find_cached_prediction()` 排序为 `(has_validation_summary, mtime)` 降序，优先选有摘要的 cache_source。
- 已写 `tools/rewrite_flare22_historical_summary.py`，按 2026-05-26 remap 后的 metrics 把 validation_summary.json 写入 0aa7323a4c01 的 output；前端显示 0.893127/0.673730/0.949908 + "（历史离线缓存摘要）"。
- 前端 `getValidationStatusCopy()` 增加 `cachedResult` 参数；`inferenceClient.ts` 增加 `cached_result` / `cache_source_job_id` / `historical` / `source_job_id` 字段。
- `tests/backendState.test.py` 增加 2 个回归测试。
- 教训：env var 缺一项就会让整条 cache 链路看起来指向错位数据；runbook 必须把 `SEGMENTATION_REFERENCE_CASES_JSON` 写在最前面，并在 `/api/samples` 列表中确认 4 个 case。
