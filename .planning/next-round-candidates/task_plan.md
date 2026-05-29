# 下一轮候选任务规划

**范围：** 基于 2026-05-29 项目现状，规划下一轮可执行任务。

**当前状态：** 三大目标已接近收口：CT 浏览、三正交联动、在线 nnUNetv2 推理、SSE 进度、取消、预测缓存、标签上传、自动 taxonomy remap、报告导出和主要验收文档均已落地。2026-05-29 已修复缓存 validation 复用、persistent worker reader 竞争、上传文件名调试日志和部分 FLARE22 标签 remap 边界。最新文档刷新记录见 `.planning/documentation-sync-20260529/`。

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

---

## 推荐下一轮任务

### 1. 远程推理分体部署实施

**优先级：** 高

**前置文档：** `.planning/deployment-preparation/task_plan.md`

**目标：** 本地 Windows 前端 + 远程 Linux GPU 后端，实现“本地导入 CT → 远程推理 → 本地查看结果”。

**关键步骤：**

1. 远程 Linux 服务器部署后端（Ubuntu + CUDA + nnUNetv2 环境）。
2. 将 `server/main.py` 中 `nnunet_env/Scripts/*.exe` 的 Windows 路径改为跨平台 helper。
3. 将前端 `API_ENDPOINT` 从硬编码本机地址改为可配置项。
4. 复核 FastAPI CORS、SSE 跨域和大文件上传边界。
5. 做端到端验证：健康检查、样例列表、创建 job、SSE heartbeat、取消、结果下载、报告导出。

**风险：** 需要可用 Linux GPU 服务器；SSE 跨域和大文件上传需要真实网络环境验证。

---

### 2. 长耗时病例性能策略

**优先级：** 中高

**目标：** 降低 AMOS 0117 这类大体数据的等待成本，同时保持正式结果质量口径清晰。

**候选改进：**

- 基于体数据层数或体素数，在 UI 中提示预计耗时和推荐 profile。
- 继续保留 `quality` 为正式报告路径，`fast` 仅作为预览。
- 评估 `tile_step_size=0.75`、关闭 TTA、`not_on_device` 等参数对耗时和 Dice 的影响。
- 针对 persistent worker 设计真实小病例或第二个不同输入的连续无缓存对照；2026-05-29 reader 修复只证明事件读取稳定，不证明推理更快。

**风险：** 性能参数可能牺牲 Dice；所有速度结论都必须绑定 job id、输入、checkpoint、profile 和指标。

---

### 3. 跨数据集标签评估增强

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

### 4. UI 精细化与报告完善

**优先级：** 中

**目标：** 基于报告导出和工作站布局继续打磨演示体验。

**候选改进：**

- 报告中增加 remap 信息、profile 警告和缓存来源摘要。
- 三视图工具栏显示窗宽窗位数值。
- 器官分类卡片支持展开详情或定位到 organ layer。
- 底部 progress rail 增加更清晰的 resource snapshot 展示。

**风险：** 低到中，主要是前端和文档；需要通过浏览器布局测试避免遮挡三视图。

---

### 5. 多模型支持准备

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

1. **远程推理分体部署实施**：最接近交付部署价值，已有部署规划可接续。
2. **长耗时病例性能策略**：解决 AMOS 大体数据等待时间问题；persistent worker 需重新跑真实无缓存对照，不能沿用旧加速假设。
3. **跨数据集标签评估增强**：优先补单 label 显式数据集 hint、remap 覆盖率提示和报告映射摘要。
4. **UI 精细化与报告完善**：提升演示和答辩体验。
5. **多模型支持准备**：等待新模型或新 checkpoint 后再启动。

---

*更新日期：2026-05-29*
