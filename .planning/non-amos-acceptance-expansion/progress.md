# 非 AMOS 验收扩展进度

## 2026-05-25 规划启动

- 创建 `.planning/non-amos-acceptance-expansion/`，用于跟踪 AMOS 0117 之外的验收扩展。
- 明确 `reference_cases.example.json` 只作公开示例，真实病例 registry 必须放在被忽略路径。
- 确认当时 `nnunetv2_files/` 主要包含 AMOS 0117 资源和当前 checkpoint。

## 2026-05-26 候选病例与 registry

- 在本地 FLARE 数据中找到可用于非 AMOS 验收扩展的 NIfTI 候选。
- 建立被忽略的私有 registry：`nnunetv2_files/reference_cases.local.json`。
- 验证 `/api/samples` 能返回私有病例 metadata，并在没有 compatible label 时显示 `validation_available=false`。
- 确认使用默认 Python 环境运行 FastAPI；`nnunet_env` 主要用于 nnUNetv2 推理命令。

## 2026-05-26 FLARE22 Tr 0009 在线推理

- 用户提供 FLARE22 Tr 0009 原图和标签。
- 确认原图和标签 shape / spacing 一致，但标签 ID 采用 FLARE22 taxonomy。
- 将 `flare22_tr_0009` 加入私有 registry，原图可通过 `/api/samples` 暴露；标签不作为 AMOS 原生 label 注册。
- 完成 `quality` 在线推理，job `86b0153d0a73`，未命中缓存，耗时 `237.323s`。
- 离线按器官名 remap 后得到 mean Dice `0.893127`，为跨数据集对照证据。

## 2026-05-26 GUI 交互补强

- 真实 NIfTI 三视图交互中完成拖动卡顿缓解、split 模式可见性、矢状/冠状拖动回跳修复和底部进度展示。
- 新增 `CODE_MODULE_GUIDE.md`，用于模块级代码讲解和交接。

## 2026-05-28 自动 taxonomy remap

- `server/taxonomy.py` 上线后，FLARE22 标签上传可自动按器官名重映射再计算 validation。
- job `a717dacf42d3` 在线 validation mean Dice `0.926`，状态 `passed`。
- 该进展把 FLARE22 从“只能离线 remap 对照”推进为“可在线 remap validation”，但仍必须与 AMOS 原生标签指标分开解释。

## 2026-05-29 部分标签与缓存 validation 边界

- FLARE22 部分标签在至少两个明确错位 ID 时可自动 remap；单 label 文件仍需要显式数据集 hint 或人工判断。
- 缓存命中只复用预测 NIfTI，非 AMOS 或自定义标签 validation 必须以当前请求标签重新计算。
- 相关文档已要求不把缓存回填耗时写成首次未缓存推理耗时，也不把缓存来源 job 的 Dice 当成当前标签结果。

## 剩余任务

- 为更多非 AMOS 病例补充 registry、人工 GUI 验收和可解释指标。
- 为未知数据集设计 remap 覆盖率不足时的 UI 提示。
- 为单 label 文件设计显式数据集 hint 和报告解释字段。
- 如需公开截图，先确认脱敏和提交边界。
