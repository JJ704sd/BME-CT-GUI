# 2026-06-13 文档一致性巡检 + 提交包打包 — Explanation

## 为什么需要这份说明

2026-06-13 当天为了完成 BME2026「呼吸-消化系统疾病」赛道的代码提交，需要把 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` 仓库打包成 `D:\BME2026\BME_CT_Seg\segmentation-submission-20260613\` 压缩包给评委。在打包过程中按"在别人电脑上能跑起来"的标准做了一次端到端实测，发现：

1. 提交包方向有真实可跑的代码 + 文档，但**打包后的文档里有些事实声明与代码实际行为不一致**——最显著的是"4 端点 smoke test"这一描述（9 份主仓库 md 都这么写）但 `tools/start_local_demo.py` 实际只采样 `/api/samples` 一个端点校验 4 例参考病例。
2. 提交包针对**评审在别人电脑上跑起来**这一新场景缺一份极简运行手册——之前 `docs/quickstart-launch-guide.md` 偏向内部演示团队，`README.md` 偏项目亮点，`README.zh-CN.md` 偏工程详版，**评审拿到包第一眼不知道该按哪个顺序操作**。
3. 提交包目标机器不一定是默认 `D:\BME2026\BME_CT_Seg\` 父目录布局——之前 4 个本地 nnUNet 路径是硬编码 `PROJECT_ROOT / "nnUNet_*"`，评审换目录就报 `missing`。这一节走"修代码加 env override + 文档说清楚"双线。

本轮不是新功能开发，是**文档/工程一致性收口**——回答三个问题：

- 评审打开压缩包后第一步看什么？
- 别人电脑在任意目录下能不能跑起来？
- 项目里描述的事实声明（commit hash / 端点数 / cache_key 字段数 / 4 例参考病例）现在还成立吗？

## 涉及范围

| 范围 | 是否改动 |
|---|---|
| 主仓库 `segmentation-gui-prototype` | ✅ 改动：9 份 md 修正"4 端点"措辞；新增 `RUN_ON_OTHER_PC.md`（主仓库版）；新增 `.planning/2026-06-13-doc-consistency-pass/` 4 份文档；`server/main.py` 顶部 5 个本地 nnUNet 路径常量改为 env override；`server/server_inference.py` 6 个 server 路径默认值脱敏作者个人路径；`tests/backendState.test.py` fixture 脱敏（去 BOM + 替换 `LUO_Zheng`） |
| 提交包 `segmentation-submission-20260613/` | ✅ 新建：53 文件 / 6.21 MB / zip 5.85 MB；含精简版 README + RUN_ON_OTHER_PC.md + 评审专用文档 |
| 真实数据集 / checkpoint / 推理输出 | ❌ 完全不在仓库，按 `.gitignore` 屏蔽 |
| 数据来源说明 | ✅ 在 README / README.zh-CN.md / RUN_ON_OTHER_PC.md / SUBMISSION_README.md 都标注 AMOS22 / FLARE22 官方渠道 |

## 与历史 planning 主题的关系

| 主题 | 关系 |
|---|---|
| `.planning/2026-06-11-launch-guide-and-doc-sync/` | 本轮在它 6-11 那次同步基础上做"事实一致性"复查；本轮不动 9 份 md 的整体结构与索引分工 |
| `.planning/next-round-candidates/` | 候选的 4 项待办（高分辨率推理优化 / 5-fold 提分 / 服务器 AMOS-FLARE 显式 taxonomy 复跑 / 跨数据集 cache 链路产品化）都**不在本轮范围**——本轮只做文档/工程一致性 |
| `.planning/2026-06-06-demo-day-wrapup/` | 本轮"4 端点 → 1 端点"修正影响 6-06 当天 commit `23e0c4d` 的措辞——但**不修改 6-06 当天的 planning 历史记录**（那是事实快照），只在 findings.md 里说明"6-13 发现" |

## 不变量回归保护

- ✅ AMOS / FLARE / cache / 6 类指标 / SSE / 报告样式 / validation 字段 / 影像量化逻辑全部不动
- ✅ 不修改 `tools/start_local_demo.py` 的 smoke test 实现（保持现状 1 端点采样），只更新文档措辞与代码 env override
- ✅ 9 份 md 不修改整体结构、章节顺序、导航，只替换"4 端点 smoke test"措辞为"启动后采样 `/api/samples` 校验 4 例参考病例"
- ✅ 不引入新依赖、不引入新 npm 包
- ✅ `cache_key` 7 字段、`ValidationSummary` 12 字段、AMOS baseline `b3c528cc9e20` mean_dice 0.924780、FLARE baseline `a717dacf42d3` mean Dice 0.926 等历史基线不变