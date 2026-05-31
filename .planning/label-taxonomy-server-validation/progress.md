# Label taxonomy and server gating progress

## 2026-05-31：progress 文档初始化

**状态：** 待执行。

**背景：** 服务器在线推理主链路已经完成校园网 smoke：Windows 前端可以调用 Ubuntu FastAPI 后端，服务器执行 5-fold 并行推理、soft ensemble，并把 NIfTI 结果回填 GUI。但 AMOS 服务器轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808`，同时 validation 报告显示 `remap_applied=true`、`remap_source=FLARE22`。当前判断更像 AMOS 原生标签被自动误判为 FLARE22 后错误 remap，而不是模型完全失败。

## 待办进度

### 1. 只读证据收集

- [ ] 保留成功 AMOS 服务器 job 的 `job_summary.json`。
- [ ] 保留成功 AMOS 服务器 job 的 `validation_summary.json`。
- [ ] 保留预测 NIfTI 路径和后端日志尾部。
- [ ] 打印上传 AMOS label 的 shape、spacing/affine、unique label IDs、voxel count。
- [ ] 打印 prediction 的 shape、spacing/affine、unique label IDs、voxel count。
- [ ] 确认 CT、label、prediction 的体数据矩阵和 spacing 是否一致。

### 2. taxonomy 误判确认

- [ ] 检查 `server/taxonomy.py` 中 `detect_dataset()` 的 FLARE22 判定条件。
- [ ] 检查 `server/main.py` 中 custom label validation 的 remap 调用路径。
- [ ] 确认 AMOS22 原生标签是否可能触发 FLARE22 自动检测。
- [ ] 记录误判触发所需的 label ID 组合。

### 3. 显式 label taxonomy hint

目标字段：

```text
label_taxonomy=auto|AMOS22|FLARE22
```

- [ ] 前端 `src/main.tsx` 增加标签体系选择控件。
- [ ] 前端 `src/inference/inferenceClient.ts` 在 FormData 中提交 `label_taxonomy`。
- [ ] 后端 `server/main.py` 接收并保存 `label_taxonomy`。
- [ ] 后端 `server/taxonomy.py` 支持显式 hint 分支。
- [ ] `AMOS22` hint 下不执行 FLARE remap。
- [ ] `FLARE22` hint 下强制执行 FLARE22 → AMOS22 remap。
- [ ] `auto` 保持现有自动检测逻辑，并明确展示 remap 状态。

### 4. server mode gating 修复

- [ ] `runtime_target=server` 创建 job 时只检查 server runtime 必需路径。
- [ ] `runtime_target=local` 才检查本地 nnUNet 文件。
- [ ] server 模式至少检查 `evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`。
- [ ] 确认 `/api/segment/jobs` 不再因本地 `dataset.json/plans/checkpoint/python.exe` 缺失而 503。

### 5. 测试与复跑

- [ ] `tests/backendState.test.py` 覆盖 AMOS hint 不 remap。
- [ ] `tests/backendState.test.py` 覆盖 FLARE hint 强制 remap。
- [ ] `tests/backendState.test.py` 覆盖 auto 保持现有逻辑。
- [ ] `tests/backendState.test.py` 覆盖 server mode 不依赖本地 nnUNet required files。
- [ ] 复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`。
- [ ] 复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`。

## 当前结论

在显式 taxonomy hint 和 server gating 修复完成前，不应把 AMOS 服务器轮次的 `mean_dice=0.076015` 写入正式模型失败结论。FLARE 服务器轮次可以作为服务器链路跑通证据；AMOS 服务器质量必须等 `label_taxonomy=AMOS22` 复跑后再判断。
