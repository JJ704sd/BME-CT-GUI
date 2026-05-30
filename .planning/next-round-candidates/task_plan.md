# 下一轮候选任务规划

**范围：** 基于 2026-05-30 项目现状，规划下一轮可执行任务。

**当前状态：** 三大目标已接近收口：CT 浏览、三正交联动、在线 nnUNetv2 推理、SSE 进度、取消、预测缓存、标签上传、自动 taxonomy remap、报告导出和主要验收文档均已落地。2026-05-29 已修复缓存 validation 复用、persistent worker reader 竞争、上传文件名调试日志和部分 FLARE22 标签 remap 边界。2026-05-30 已增加 `本地在线推理` / `服务器云端推理` 运行位置、局域网配置化和服务器 5-fold soft ensemble 编排入口；真实第二台局域网设备与 Linux 服务器端到端推理仍需单独验收。最新局域网规划记录见 `.planning/lan-direct-and-tunnel/`。

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
- 穿透方案阶段性推荐 Tailscale / WireGuard；frp + HTTPS 只在必须提供无客户端公网浏览器入口时考虑。

---

## 推荐下一轮任务

### 1. 真实局域网与 Tailscale / WireGuard smoke test

**优先级：** 高

**前置文档：** `.planning/lan-direct-and-tunnel/`

**目标：** 用第二台真实设备完成局域网直连或 VPN/Mesh 访问，验证前端打开、后端 API、上传、SSE、取消、下载和标签 validation 全链路。

**关键步骤：**

1. 用真实前端机器 IP 和后端机器 IP 启动 `npm run dev:lan` 与 `uvicorn --host 0.0.0.0`。
2. 设置 `VITE_API_ENDPOINT=http://<后端IP>:8000` 和 `SEGMENTATION_ALLOWED_ORIGINS=http://<前端IP>:5173`。
3. 从第二台设备打开 `http://<前端IP>:5173`，检查 `/api/health`、`/api/models` 和浏览器 CORS。
4. 执行上传 CT、创建 job、SSE 进度、取消任务、下载结果和标签 validation smoke test。
5. 如果跨网络访问，优先用 Tailscale / WireGuard 复用同一套配置；只有必须公网普通浏览器入口时才评估 frp + HTTPS。

**风险：** 真实网络、防火墙、浏览器来源和大文件上传限制可能与本机 smoke 不同。

---

### 2. Linux 服务器 5-fold ensemble 端到端验证

**优先级：** 高

**前置文档：** `.planning/deployment-preparation/task_plan.md`

**目标：** 验证“服务器云端推理”从 GUI 提交到 Linux 服务器 5 张 GPU 并行 fold、soft ensemble、结果下载和 validation 的完整链路。

**关键步骤：**

1. 在 Linux 服务器确认 nnUNetv2、CUDA、`nnUNet_raw/preprocessed/results` 和 checkpoint 目录可用。
2. 配置 `SEGMENTATION_SERVER_*` 环境变量、fold/GPU 映射和输出目录。
3. 选择 `服务器云端推理` + `质量推理` 提交一个小病例或 FLARE22 Tr 0009 job。
4. 观察 5 个 fold 进程是否分别绑定 GPU，`nnUNetv2_ensemble` 是否生成最终 NIfTI。
5. 下载结果回填 GUI；带标签文件时确认 validation 和自动 taxonomy remap 仍正确。
6. 取消运行中 job，确认 5 个 fold、ensemble 或 evaluate 子进程都退出。

**风险：** 服务器路径已经有命令编排入口，但尚未完成真实 Linux 端到端推理；不要提前写成质量验收通过。

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
2. **Linux 服务器 5-fold ensemble 端到端验证**：验证新增服务器编排入口是否真实可用。
3. **长耗时病例性能策略**：继续优化 AMOS 大体数据等待时间。
4. **跨数据集标签评估增强**：补单 label hint、remap 覆盖率提示和报告摘要。
5. **文档与验收口径再同步**：确保文档持续跟随代码变化。
6. **多模型支持准备**：等待新模型或新 checkpoint 后再启动。

---

*更新日期：2026-05-30*
