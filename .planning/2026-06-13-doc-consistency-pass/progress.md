# 2026-06-13 文档一致性巡检 + 提交包打包 — Progress

| 时间 | 事件 | 验证 |
|---|---|---|
| 2026-06-13 20:30 | 收到 BME2026 命题 PDF（呼吸-消化系统疾病赛道，影像智能分析算法类），按题目要求开始打包 `segmentation-gui-prototype` 仓库 | 读 PDF 第一页确认题目边界 |
| 2026-06-13 20:33-20:46 | 第一次打包：robocopy 镜像 738 目录 / 2013 文件 / 7.1 GB → **发现漏排 `server\work` 目录**（约 6 GB 推理缓存 + 日志） | robocopy 报告目录数与文件数 |
| 2026-06-13 20:47-20:56 | 第二次打包：roboopy 加 `/XD server\work` → **7.3 MB** / 88 文件 / 51 目录 | `Get-ChildItem -Recurse` 统计 |
| 2026-06-13 20:57-22:08 | 多次精简提交包：删除 `CLAUDE.md` / `AGENTS.md` / `REVIEW.md` / `ACCEPTANCE.md` / `CODE_MODULE_GUIDE.md` / `SEGMENTATION_*.md` / `docs/superpowers/` / `docs/competition/` 等评审不需要的内部/历史文档；路径脱敏 `D:\BME2026\BME_CT_Seg\...` → `<PROJECT_ROOT>` / `<VENV_PY>` | 手工脱敏 + 重新打包 |
| 2026-06-13 21:07-22:00 | 提交包第二轮：精简版 README.md / README.zh-CN.md / 新写 SUBMISSION_README.md；`server/main.py` 顶部 4 个本地 nnUNet 路径常量加 env var override；`server/server_inference.py` 6 个 server 路径默认值脱敏；`tests/backendState.test.py` fixture 替换 `LUO_Zheng` → `user_eval` | `python -c "import server.main"` + `importlib.import_module(m)` 7 个核心依赖 |
| 2026-06-13 22:09-22:14 | 提交包第三轮：在打包目录下实跑后端（uvicorn 启动 7s 后）→ 3 个端点全 HTTP 200 / `model_state.ready=true` / `has_checkpoint=true` → 评估"在别人电脑上能不能跑" | 真实 `Invoke-WebRequest http://127.0.0.1:8765/api/health` 返回 JSON |
| 2026-06-13 22:14 | 新增 `RUN_ON_OTHER_PC.md`（针对评审在别人电脑上的极简操作清单）：4 章（准备清单 / 第 1 步装 venv / 第 2 步放数据 / 第 3 步启 GUI / 第 4 步试推理）+ 6 个 FAQ；中文主体、技术字段英文 | 写入 `RUN_ON_OTHER_PC.md` |
| 2026-06-13 22:18 | **关键问题**："在别人电脑能否运行 GUI 项目的什么内容"——按"功能清单 + 实测量"两列回答 | 静态分析 + 之前实跑证据 |
| 2026-06-14 00:25 | 收到第二轮指令：依据项目实时进展检查 9 份 md；用户选 light-audit 路线 | 用户决定 |
| 2026-06-14 00:25-00:50 | **轻量审计**：grep `git log` / 关键事实（cache_key 7 字段 / commit hash / 端点数 / 4 例参考病例 / 命名版本号）→ 发现唯一真实不一致是"4 端点 smoke test" | 9 份 md grep + `tools/start_local_demo.py` 实际代码对比 |
| 2026-06-14 00:50-01:10 | 9 份 md 统一措辞：把"4 端点 smoke test"改成"启动后采样 `/api/samples` 校验 4 例参考病例已就绪" | `Edit` 工具逐文件修改 + `grep "4 端点"` 0 命中根目录 md |
| 2026-06-14 01:10-01:30 | 新增 `RUN_ON_OTHER_PC.md` 主仓库版（在 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\RUN_ON_OTHER_PC.md`）；新增 `.planning/2026-06-13-doc-consistency-pass/` 4 份文档（explanation / findings / progress / task_plan） | `Write` 工具 + `git status` 验证 |
| 2026-06-14 01:30-01:45 | 最终审计：交叉对照 9 份 md 与 `.planning/2026-06-13-doc-consistency-pass/` 与 `RUN_ON_OTHER_PC.md` 三方一致性 | `git diff --stat` 统计改动 |
| 2026-06-14 01:45 | 提交 GitHub | `git commit` + `git push` |

## 验证清单

| 检查项 | 命令 / 方法 | 结果 |
|---|---|---|
| 主仓库工作树干净（提交前） | `git -C segmentation-gui-prototype status` | ✅ "On branch main, nothing to commit, working tree clean" |
| 9 份 md + 1 份新文件 + 4 份 planning 文档改动 | `git diff --stat` | 待提交后验证 |
| `tools/start_local_demo.py` smoke test 实际行为 | `Read tools/start_local_demo.py:80-91` | ✅ 确认是 `wait_for_samples()` 单端点采样 |
| `build_prediction_cache_key()` 7 字段 | `Read server/main.py:1942-1960` | ✅ 7 字段全在 |
| `examples/reference_cases.json` 4 例参考病例 | `ConvertFrom-Json` 解 | ✅ `amos_0117` / `flare22_tr_0009` / `word_case` / `abdomenct1k_case` |
| commit hash 真实性 | `git log --oneline \| grep <hash>` | ✅ 7 个 hash 全部真实存在 |
| 提交包文档措辞一致性 | grep 提交包目录 | ✅ 主仓库版本（精简版）+ 提交包版本（更详细）并行不冲突 |
| 中文主体 + 技术字段英文 | 每份 md 抽样 + cn% 统计（35-48%） | ✅ 通过 |