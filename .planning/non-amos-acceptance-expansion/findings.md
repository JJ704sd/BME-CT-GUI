# 非 AMOS 验收扩展发现

## 当前证据

- 活动基线为 `main`，历史提交 `838e77e merge selectable inference profiles`。
- tracked 的 `reference_cases.example.json` 只作为公开示例；真实非 AMOS 病例通过被忽略的本地 registry 管理。
- `.gitignore` 已排除 `nnunetv2_files/`、`.test-output/`、`server/work/`、`*.nii`、`*.nii.gz`、`*.pth` 和 `*.pt`。
- 当前可复用的非 AMOS 证据主要是 FLARE22 Tr 0009：未上传标签时 registry 中 `validation_available=false`，上传标签后可通过自动 taxonomy remap 在线 validation。

## 关键决策

- 私有病例 registry 使用 `nnunetv2_files/reference_cases.local.json` 或由 `SEGMENTATION_REFERENCE_CASES_JSON` 指向的外部路径。
- `reference_cases.example.json` 保持公开 schema / example，不写入私有真实路径。
- 无标签外部病例只做浏览、推理、下载、GUI 回填和人工复核。
- 有标签但 taxonomy 不同的病例，只有在 `server/taxonomy.py` 可识别并可按器官名 remap 时才记录 Dice、IoU 或 Hausdorff。
- `quality` 是正式验收路径；`fast` 和后处理实验只能单独记录为对照。

## FLARE22 发现

- 本地 FLARE 数据与当前 AMOS22 checkpoint 的标签 ID 语义不同：例如 FLARE22 的 `1=liver`，而 AMOS22 的 `1=spleen`。
- 2026-05-26 的 FLARE22 Tr 0009 `quality` 在线推理成功，job `86b0153d0a73`，耗时 `237.323s`，结果大小 `120761` bytes。
- 离线按器官名 remap 后，FLARE22 Tr 0009 指标为 mean Dice `0.893127`，foreground Dice `0.949908`，min Dice `0.673730`。
- 2026-05-28 自动 taxonomy remap 上线后，FLARE22 Tr 0009 上传标签在线 validation 通过，job `a717dacf42d3`，mean Dice `0.926`，`remap_applied=true`。

## 风险

- 单个非 AMOS 病例只能扩展证据宽度，不能证明广泛泛化。
- 私有数据路径容易在复制命令时泄漏到文档；公开文档应使用 case id、dataset 和脱敏说明。
- 跨数据集 remap 后的指标不能与 AMOS 原生标签指标混算。
- 首次未缓存推理可能持续数分钟到十几分钟；缓存命中必须单独记录。

## 待确认问题

- 下一批可公开描述但不泄露路径的非 AMOS 病例有哪些？
- 新增数据集是否具备可 remap 的标签定义和器官名别名？
- 是否需要生成脱敏截图作为后续 PR 或答辩材料？
