# 下一轮候选任务规划

**范围：** 基于 2026-05-30 项目现状，规划下一轮可执行任务。

**当前状态：** 三大目标已接近收口：CT 浏览、三正交联动、在线 nnUNetv2 推理、SSE 进度、取消、预测缓存、标签上传、自动 taxonomy remap、报告导出和主要验收文档均已落地。2026-05-29 已修复缓存 validation 复用、persistent worker reader 竞争、上传文件名调试日志和部分 FLARE22 标签 remap 边界。2026-05-30 已增加 `本地在线推理` / `服务器云端推理` 运行位置、局域网配置化、服务器 5-fold soft ensemble 编排入口、校园网访问 planning 和服务器 runtime 包。2026-05-31 已完成 Windows 前端通过校园网调用 Ubuntu FastAPI 后端的 5-fold + soft ensemble + GUI 回填 smoke；当前阻塞点转为 AMOS 原生标签可能被误判为 FLARE22、以及 `runtime_target=server` 创建任务不应依赖本地 nnUNet 文件。最新执行规划见 `.planning/label-taxonomy-server-validation/`。

**本轮已完成（2026-05-28）：**

- 报告导出功能：`src/report/exportReport.ts`，支持 HTML / JSON / PDF 三种格式。
- UI 布局美化：顶栏 flex 布局、标签名显示优化、拖放区域三列、ghost-button 交互增强。
- 自动 taxonomy remap：FLARE22 标签在线验证 mean_dice 从 `0.073` 提升到 `0.926`。
- 文档同步：`README.md`、`ACCEPTANCE.md`、`REVIEW.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md`、`SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_RECENT_ROUNDS.md`、`CODE_MODULE_GUIDE.md`、`AGENTS.md` 和 `.planning/`。

**本轮已完成（2026-05-29）：**

- 缓存命中只复用预测 NIfTI，validation 改为按当前请求标签文件或内置参考标签重新计算。
- persistent worker stdout reader 改为进程级共享队列，并通过轻量 shutdown smoke；真实长耗时加速仍未证明。
- 前后端上传文件名调试日志已移除，标签链路观察改为依赖 job state、`label_path` 和 validation summary。
- FLARE22 部分标签在至少两个明确错位 label 时可自动 remap；单 label 文件仍保守处理。

**本轮已完成（2026-05-30）：**

- 前端 API 地址支持 `VITE_API_ENDPOINT`，`package.json` 新增 `dev:lan`，后端 CORS 支持 `SEGMENTATION_ALLOWED_ORIGINS`。
- 前端分割控制支持 `runtime_target=server|local`，后端把本地路径和服务器 5-fold soft ensemble 编排路径分开。
- 本机局域网 IP smoke 已验证前端 200、后端 health 200 和 CORS allow-origin；第二台真实设备完整推理链路仍待验收。
- 新增 `.planning/campus-network-and-public-access/`，明确当前推荐顺序为校园网 API 直连、Ubuntu 22.04 真实 5GPU smoke test、必要时 Tailscale/WireGuard，最后才做公网浏览器入口。
- 2026-05-31 已完成 Windows 前端通过校园网调用 Ubuntu FastAPI 后端的 5-fold + soft ensemble + GUI 回填 smoke；FLARE 轮次可作为链路证据，AMOS 轮次因疑似 taxonomy 误判暂不作为质量基线。
- 新增 `deployment-packages/server-runtime-package-20260530.zip` 和 `deployment-packages/server-runtime-quickstart-20260530.md`，用于服务器后端 runtime 部署准备；该准备本身不等同于质量验收通过。
- 穿透方案阶段性推荐 Tailscale / WireGuard；frp + HTTPS 只在必须提供无客户端公网浏览器入口时考虑。

---

## 推荐下一轮任务

### 1. 显式标签体系选择与 server gating 修复

**优先级：** 高

**前置文档：** `.planning/label-taxonomy-server-validation/`

**目标：** 在服务器在线推理已跑通后，避免 AMOS 原生标签被自动误判为 FLARE22，并让 `runtime_target=server` 创建任务只检查 server runtime 必需路径。

**关键步骤：**

1. 在前端和后端新增 `label_taxonomy=auto|AMOS22|FLARE22`。
2. `AMOS22` hint 下跳过 FLARE remap，`FLARE22` hint 下强制 FLARE22 → AMOS22 remap，`auto` 保留现有检测逻辑。
3. `runtime_target=server` 创建 job 时只检查服务器配置路径，不再要求本地 Windows `dataset.json/plans/checkpoint/python.exe`。
4. 复跑 AMOS 原图 + AMOS label，确认 `remap_applied=false` 后再判断真实器官 Dice。
5. 复跑 FLARE 原图 + FLARE label，确认 `remap_applied=true`、`remap_source=FLARE22`。

**风险：** 该修复只影响 validation/remap 解释和 server gating，不改变 nnUNet 原始预测输出。

---

### 2. 服务器在线推理稳定性补验

**优先级：** 高

**前置文档：** `.planning/label-taxonomy-server-validation/`

**目标：** 在 2026-05-31 校园网服务器端到端 smoke 已跑通的基础上，补齐取消、失败恢复、更多病例 validation 和长期稳定性记录。

**关键步骤：**

1. 在 Linux 服务器确认 nnUNetv2、CUDA、`nnUNet_raw/preprocessed/results` 和 checkpoint 目录可用。
2. 保留成功 job 的 `job_summary.json`、`validation_summary.json`、预测 NIfTI 和后端日志。
3. 对 AMOS/FLARE 分别记录 label/prediction unique IDs、voxel count、shape 和 spacing/affine。
4. 下载结果回填 GUI；带标签文件时确认显式 taxonomy hint 与 validation message 一致。
5. 取消运行中 job，确认 5 个 fold、ensemble 或 evaluate 子进程都退出。

**风险：** 服务器链路可运行不等于质量基线已完成；AMOS 服务器指标必须先排除 taxonomy 误判。

---

### 3. 长耗时病例性能策略

**优先级：** 中高

**目标：** 降低 AMOS 0117 这类大体数据的等待成本，同时保持正式结果质量口径清晰。

**候选改进：**

- 基于体数据层数或体素数，在 UI 中提示预计耗时和推荐 profile。
- 继续保留 `quality` 为正式报告路径，`fast` 仅作为预览。
- 评估 `tile_step_size=0.75`、关闭 TTA、`not_on_device` 等参数对耗时和 Dice 的影响。
- 针对 persistent worker 设计真实小病例或第二个不同输入的连续无缓存对照；2026-05-29 reader 修复只证明事件读取稳定，不证明推理更快。

**风险：** 性能参数可能牺牲 Dice；所有速度结论都必须绑定 job id、输入、checkpoint、profile 和指标。

---

### 4. 跨数据集标签评估增强

**优先级：** 中

**目标：** 在自动 remap 已可用的基础上，增强未知数据集和异常指标的解释能力。

**候选改进：**

- 对 remap 覆盖率不足或未知标签 ID 给出明确 UI 警告。
- 为单 label 或少量标签文件增加显式数据集 hint 入口，避免仅凭一个 ID 误判 AMOS 原生标签或 FLARE22 标签。
- 在 per-label 表格中标出体素量级差异异常、Dice 为 0 的疑似错位标签。
- 记录 `remap_mapping` 的用户可读摘要，便于报告导出。
- 为新增数据集建立标签表、别名映射和后端测试模板。

**风险：** 需要避免把 remap 后的跨数据集指标写成 AMOS 原生验证。

---

### 5. 文档与验收口径再同步

**优先级：** 中

**目标：** 继续保持 README、ACCEPTANCE、REVIEW、指标汇总和近期轮次记录与代码现状一致，尤其是 `runtime_target`、局域网配置和服务器模式的边界说明。

**关键步骤：**

1. 在后续代码或配置变化后，及时同步 7 份核心文档的中文主体说明。
2. 对 `SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md` 和 `SEGMENTATION_RECENT_ROUNDS.md` 继续坚持“新工程链路不混入旧指标”的口径。
3. 如果需要统一 agent instruction 文档中文化，先确认权限范围，再处理 `AGENTS.md` / `CLAUDE.md`。

**风险：** 这类工作本身不难，但容易在没有同步代码现状时写入过时结论。

---

### 6. 多模型支持准备

**优先级：** 低（等待新 checkpoint）

**目标：** 当前只有 AMOS22 单模型，为未来多模型切换预留结构。

**候选改进：**

- `modelOptions` 从硬编码改为从 `/api/models` 动态获取。
- 后端增加模型目录扫描和模型信息 API。
- 前端模型卡片改为可点击切换。
- 肺窗/骨窗预设在对应模型可用时自动启用器官映射。

**风险：** 没有新 checkpoint 时难以完成真实验收。

---

## 推荐执行顺序

1. **真实局域网与 Tailscale / WireGuard smoke test**：最贴近当前待验收项。
2. **服务器在线推理稳定性补验**：在已跑通的服务器链路上补齐取消、失败恢复、更多病例 validation 和长期稳定性证据。
3. **长耗时病例性能策略**：继续优化 AMOS 大体数据等待时间。
4. **跨数据集标签评估增强**：补单 label hint、remap 覆盖率提示和报告摘要。
5. **文档与验收口径再同步**：确保文档持续跟随代码变化。
6. **多模型支持准备**：等待新模型或新 checkpoint 后再启动。

---

*更新日期：2026-05-30*
