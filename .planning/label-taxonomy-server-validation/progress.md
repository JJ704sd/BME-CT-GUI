# Label taxonomy and server gating progress

## 2026-05-31：taxonomy fix 已完成

**状态：** taxonomy fix 已完成，server gating 待修复。

**背景：** 服务器在线推理主链路已经完成校园网 smoke：Windows 前端可以调用 Ubuntu FastAPI 后端，服务器执行 5-fold 并行推理、soft ensemble，并把 NIfTI 结果回填 GUI。但 AMOS 服务器轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808`，同时 validation 报告显示 `remap_applied=true`、`remap_source=FLARE22`。当前判断更像 AMOS 原生标签被自动误判为 FLARE22 后错误 remap，而不是模型完全失败。

## 已完成

### 1. taxonomy 误判确认 [已完成]

- [x] 检查 `server/taxonomy.py` 中 `detect_dataset()` 的 FLARE22 判定条件。
- [x] 检查 `server/main.py` 中 custom label validation 的 remap 调用路径。
- [x] 确认 AMOS22 原生标签可能触发 FLARE22 自动检测。
- [x] 记录误判触发所需的 label ID 组合。

### 2. 显式 label taxonomy hint [已完成]

- [x] 后端 `server/taxonomy.py` 支持显式 hint 分支。
- [x] `detect_dataset()` 更保守：标签 ID 是 checkpoint 子集时不触发 remap。
- [x] `AMOS22` hint 下不执行 FLARE remap。
- [x] `FLARE22` hint 下强制执行 FLARE22 → AMOS22 remap。
- [x] `auto` 保持现有自动检测逻辑，并明确展示 remap 状态。
- [x] `label_taxonomy` 已纳入缓存 key。

### 3. 测试与验证 [已完成]

- [x] `tests/backendState.test.py` 覆盖 AMOS hint 不 remap。
- [x] `tests/backendState.test.py` 覆盖 FLARE hint 强制 remap。
- [x] `tests/backendState.test.py` 覆盖 auto 保持现有逻辑。
- [x] 验证 job `d56bcff76a8b`：AMOS22 选择时 `remap_applied=false`，`mean_dice=0.77724`。

### 4. 部署包 [已完成]

- [x] 新部署包 `server-runtime-package-20260531.zip` 已创建。
- [x] 配套 `server-runtime-quickstart-20260531.md` 已编写。

## 待完成

### 5. server mode gating 修复 [待执行]

- [ ] `runtime_target=server` 创建 job 时只检查 server runtime 必需路径。
- [ ] `runtime_target=local` 才检查本地 nnUNet 文件。
- [ ] server 模式至少检查 `evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`。
- [ ] 确认 `/api/segment/jobs` 不再因本地 `dataset.json/plans/checkpoint/python.exe` 缺失而 503。

### 6. 服务器 validation 复跑 [待执行]

- [ ] 复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`。
- [ ] 复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`。

## 当前结论

taxonomy fix 已完成并验证通过。AMOS 标签不再被误判为 FLARE22。server mode gating 修复和服务器 validation 复跑是下一步工作。
