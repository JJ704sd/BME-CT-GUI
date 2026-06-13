# 2026-06-13 文档一致性巡检 + 提交包打包 — Task Plan

## 任务目标

1. **打包代码**：把 `segmentation-gui-prototype` 仓库按 BME2026 评审需要的方式打包成 `segmentation-submission-20260613/` 压缩包
2. **保证能跑**：让评审在别人电脑上能按 `RUN_ON_OTHER_PC.md` 三步把 GUI 起来
3. **轻量巡检**：基于 6-11 那次 9 份 md 同步的现状，按"只改真不一致"原则做事实一致性复查
4. **新增 planning 主题**：`.planning/2026-06-13-doc-consistency-pass/` 4 份文档（explanation / findings / progress / task_plan）

## 任务清单

| # | 任务 | 状态 | 备注 |
|---|---|---|---|
| 1 | 读 BME2026 命题 PDF 第一页确认题目边界 | ✅ 完成 | 题目要求第 1 项（影像智能分割）+ 第 2 项（影像量化分析） |
| 2 | 第一次打包：robocopy 镜像（含数据集 / checkpoint / 推理缓存 / 日志） | ✅ 完成 | 7.1 GB → 发现漏排 `server\work` |
| 3 | 第二次打包：加 `/XD server\work` | ✅ 完成 | 7.3 MB / 88 文件 |
| 4 | 删除评审不需要的内部 / 历史文档 | ✅ 完成 | CLAUDE.md / AGENTS.md / REVIEW.md / ACCEPTANCE.md / CODE_MODULE_GUIDE.md / SEGMENTATION_*.md / docs/superpowers/ / docs/competition/ |
| 5 | 路径脱敏 `D:\BME2026\BME_CT_Seg\...` → `<PROJECT_ROOT>` / `<VENV_PY>` | ✅ 完成 | docs/demo-day-checklist.md / docs/local-cache-demo-runbook.md / deployment-packages/ 3 处 |
| 6 | 提交包精简：精简版 README.md / README.zh-CN.md / 新写 SUBMISSION_README.md | ✅ 完成 | 4 份 md 分工明确 |
| 7 | `server/main.py` 顶部 5 个本地 nnUNet 路径常量加 env var override | ✅ 完成 | 纯加法，不删任何代码路径 |
| 8 | `server/server_inference.py` 6 个 server 路径默认值脱敏 | ✅ 完成 | 占位符 `<需设置 SEGMENTATION_SERVER_* 环境变量>` + evaluate_script/labels_dir 识别为 None |
| 9 | `tests/backendState.test.py` fixture 替换 `LUO_Zheng` → `user_eval` + 去 UTF-8 BOM | ✅ 完成 | 31 处 fixture 全部替换 |
| 10 | 实跑后端：uvicorn 启动 7s 后，3 个端点全 HTTP 200 | ✅ 完成 | `/api/health` / `/api/samples` / `/api/models` |
| 11 | 评估"在别人电脑能否运行"——按功能清单 + 实测量两列回答 | ✅ 完成 | 用户确认 |
| 12 | 提交包新增 `RUN_ON_OTHER_PC.md`（极简 3 步操作清单 + 6 个 FAQ） | ✅ 完成 | 4 章结构 |
| 13 | 接收第二轮指令：依据项目实时进展检查 9 份 md | ✅ 完成 | 用户选 light-audit 路线 |
| 14 | **轻量审计**：grep `git log` / cache_key 字段数 / 端点数 / commit hash / 4 例参考病例 | ✅ 完成 | 发现唯一真实不一致：9 份 md "4 端点 smoke test" vs 代码实际 1 端点 |
| 15 | 9 份 md 统一措辞：把"4 端点 smoke test"改成"启动后采样 `/api/samples` 校验 4 例参考病例已就绪" | ✅ 完成 | 11 处编辑（ACCEPTANCE.md / AGENTS.md / README.md / README.zh-CN.md / REVIEW.md / CODE_MODULE_GUIDE.md / SEGMENTATION_EXPERIMENT_COMPARISON.md / SEGMENTATION_METRICS_SUMMARY.md / SEGMENTATION_RECENT_ROUNDS.md 各 1-5 处） |
| 16 | 主仓库新增 `RUN_ON_OTHER_PC.md` | ✅ 完成 | 评审在任何电脑上打开压缩包第一份要看 |
| 17 | 主仓库新增 `.planning/2026-06-13-doc-consistency-pass/` 4 份文档 | ✅ 完成 | explanation.md / findings.md / progress.md / task_plan.md |
| 18 | 最终审计：交叉对照 9 份 md 与 4 份 planning 文档与 RUN_ON_OTHER_PC.md 三方一致性 | ✅ 完成 | `git diff --stat` 统计 |
| 19 | 提交 GitHub | ✅ 完成 | `git add` + `git commit` + `git push` |

## 实际改动文件清单

### 主仓库 `segmentation-gui-prototype`（提交增量）

```
.gitignore                                  (新增条目)
RUN_ON_OTHER_PC.md                          (新建)
.planning/2026-06-13-doc-consistency-pass/
  ├── explanation.md                        (新建)
  ├── findings.md                           (新建)
  ├── progress.md                           (新建)
  └── task_plan.md                          (新建)
server/main.py                              (顶部 5 个本地 nnUNet 路径加 env var override)
server/server_inference.py                  (6 个 server 路径默认值脱敏)
tests/backendState.test.py                  (31 处 fixture 替换 + 去 UTF-8 BOM)
ACCEPTANCE.md                               (1 处措辞修订)
AGENTS.md                                   (2 处措辞修订)
README.md                                   (1 处措辞修订)
README.zh-CN.md                             (2 处措辞修订)
REVIEW.md                                   (3 处措辞修订)
CODE_MODULE_GUIDE.md                        (2 处措辞修订)
SEGMENTATION_EXPERIMENT_COMPARISON.md       (3 处措辞修订)
SEGMENTATION_METRICS_SUMMARY.md             (1 处措辞修订)
SEGMENTATION_RECENT_ROUNDS.md               (5 处措辞修订)
```

### 提交包 `segmentation-submission-20260613/`（独立目录，不进主仓库）

```
.gitignore
RUN_ON_OTHER_PC.md                          (新建 — 比主仓库版更详细，含 6 个 FAQ)
README.md                                   (新建 — GitHub 风格摘要)
README.zh-CN.md                             (新建 — 工程详版)
SUBMISSION_README.md                        (新建 — 包内容清单)
package.json / package-lock.json / tsconfig.json / index.html / public/
src/ (14 个 .ts/.tsx/.css + assets)
server/ (4 个 .py + requirements.txt)
tests/ (10 个 .test.ts/.py)
tools/ (5 个 .py)
examples/reference_cases.json
docs/ (quickstart-launch-guide.md / demo-day-checklist.md)
deployment-packages/ (server-runtime-quickstart-*.md)
```

## 不在范围

- AMOS / FLARE 真实推理复跑（历史 baseline 已在 `next-round-candidates/` 列为待办）
- 5-fold ensemble（已在 `next-round-candidates/` 列为待办）
- 高分辨率推理优化（已在 `next-round-candidates/` 列为待办）
- 跨数据集 cache 链路产品化（已在 `next-round-candidates/` 列为待办）
- 修改 `tools/start_local_demo.py` 的 smoke test 实现（保持现状 1 端点采样）
- 修改 `.planning/2026-06-06-demo-day-wrapup/` 等历史 planning 主题（保留 6-06 当天的事实快照）

## lesson（写入 findings）

1. **文档 commit 不能脱离测试范围**——9 份 md 里的事实声明（cache_key 字段数 / 端点列表 / SSE 字段名）靠 source-grep 守护，"4 端点 smoke test"漂移 7 天没人发现。
2. **打包过程是文档一致性审查的好契机**——把代码真的跑一遍，发现不一致，比"为同步而同步"更可靠。
3. **`PROJECT_ROOT` 之外的所有路径必须 env var 可覆盖**——评审机器不通用硬编码路径。
4. **作者姓名、个人 Linux 服务器路径不应出现在默认值**——用占位符或 None。
5. **PowerShell `Set-Content -Encoding utf8` 会加 UTF-8 BOM**——跨平台工具链差异。

## 后续可继续

- 主仓库 README.md 顶部加一行指向 `RUN_ON_OTHER_PC.md`（类似 `README.zh-CN.md` 已有的索引段）
- 把"端点 smoke test 数量"加入 `tests/backendState.test.py` 的 source-grep 守护（防止再次漂移）
- 评估是否把"4 项 next-round 候选"任一项作为 `2026-06-XX-xxx/` 主题落地