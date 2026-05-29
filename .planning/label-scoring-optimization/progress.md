# 标签打分优化 — 进度记录

## 2026-05-27：标签文件传输修复

**完成：**
- 扩展 `UploadRole` 类型支持 `"label"`
- `processVisualizationFile()` 增加 label 分支
- 数据操作面板新增标签拖放区域
- `startSegmentation()` 增加缺失提示
- 当时添加前端和后端临时排查日志确认标签链路；2026-05-29 已移除上传文件名日志
- `npm test` + `npm run build` 通过

**验证：**
- job `bf20f0ec4456`：`label_path` 非空，validation 执行成功
- 标签文件 131 KB（gzip），正确保存到 job 目录

## 2026-05-27：近三轮数据收集

**记录：**
- 第 1 轮 `bf20f0ec4456`：FLARE22 + 标签，mean_dice=0.073（taxonomy 错位）
- 第 2 轮 `d2510866dd8c`：FLARE22 无标签，无验证
- 第 3 轮 `b6e04914f852`：AMOS 0117，1054s

**文档：**
- 创建 `SEGMENTATION_RECENT_ROUNDS.md`（滚动覆写，近三轮）
- 创建 `.planning/label-scoring-optimization/` 规划目录

## 待办

- [x] Phase 1：taxonomy 自动 remap
- [x] GUI 自动重映射提示
- [ ] Phase 2：GUI 异常指标提示增强
- [ ] Phase 3：AMOS 耗时优化
- [ ] Phase 4：标签传输稳定性观察

## 2026-05-28：自动 taxonomy remap 上线

**完成：**
- 新增 `server/taxonomy.py`，集中维护 FLARE22 标签表、器官名别名、数据集检测和 ID 重映射。
- 后端 validation 在计算 Dice 前自动对 FLARE22 标签进行器官名重映射。
- 前端评估面板显示 `remap_applied` 提示，避免把跨数据集指标误认为 AMOS 原生验证。

**验证：**
- job `a717dacf42d3`：FLARE22 Tr 0009 + 标签上传，`remap_applied=true`，`remap_source=FLARE22`。
- 自动 remap 后在线 validation `mean_dice=0.926`，状态 `passed`。

**剩余：**
- 异常指标提示还可继续增强，例如低覆盖率 remap、未知数据集和 per-label 体素差异提示。

## 2026-05-29：标签链路历史风险收口

- 缓存命中不再复用缓存来源 job 的 validation；当前标签文件会重新计算 Dice，无当前标签时不返回旧 validation。
- FLARE22 部分标签在至少两个明确错位 ID 时可自动 remap；单 label 文件仍保留人工判断边界。
- 前后端上传文件名日志已移除，后续观察标签链路改为检查 job state、`label_path`、validation summary 和测试覆盖。
