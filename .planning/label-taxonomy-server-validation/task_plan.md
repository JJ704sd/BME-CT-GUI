# Label taxonomy and server validation task plan

## Context

服务器在线推理已经能完成 5-fold + soft ensemble + 前端回填，但 AMOS_0117 带标签验证报告出现异常：`mean_dice=0.076015`、`foreground_dice=0.979808`，且后端自动应用了 `FLARE22 → 当前模型` remap。当前目标是避免 AMOS 标签被误判为 FLARE22，并让 server 模式创建任务不依赖本地 nnUNet 文件。

## Phase 1：只读证据收集

- [ ] 保留成功 job 的 `job_summary.json`、`validation_summary.json`、预测 NIfTI 和后端日志。
- [ ] 对上传 label 文件打印 shape、affine/spacing、unique label IDs、每个 label voxel count。
- [ ] 对预测结果打印同样的 label ID 分布。
- [ ] 确认 CT、label、prediction 的体数据矩阵和 spacing 是否一致。

## Phase 2：确认 taxonomy 误判点

重点检查：

- `server/taxonomy.py`
- `server/main.py` 中 `validate_against_custom_label()`

要确认：

- `detect_dataset(reference_labels, labels)` 在什么条件下返回 `FLARE22`。
- AMOS22 原生标签是否可能被误判为 FLARE22。
- 单病例或部分标签文件是否因为包含错位 ID 而误触发 remap。

## Phase 3：增加显式 label taxonomy hint

推荐新增请求字段：

```text
label_taxonomy=auto|AMOS22|FLARE22
```

行为：

- `AMOS22`：不做 FLARE22 remap，直接按当前 AMOS checkpoint label ID 计算 Dice。
- `FLARE22`：强制执行 FLARE22 → AMOS22 remap 后计算 Dice。
- `auto`：保留现有自动检测逻辑，但 validation message 明确展示检测来源和 remap 状态。

涉及文件：

- `src/inference/inferenceClient.ts`：FormData 增加 `label_taxonomy`。
- `src/main.tsx`：在导入标签 CT 附近增加标签体系选择，默认建议 `AMOS22` 或按病例类型设置。
- `server/main.py`：`create_job()` 接收 `label_taxonomy`，保存到 job 或 validation options。
- `server/taxonomy.py`：复用现有 remap 方法，增加显式 hint 分支。
- `tests/backendState.test.py`：覆盖 AMOS hint 不 remap、FLARE hint remap、auto 保持现有逻辑。

## Phase 4：修复 server 模式 gating

当前观察到 `/api/models` 默认显示 `runtime_target=local` 且 missing 本地文件：

```text
dataset.json, plans.json, checkpoint_best.pth, nnUNetv2_python
```

但服务器云端推理只应依赖 server runtime 配置。需要调整：

- `runtime_target=server` 创建 job 时只检查 server 路径。
- `runtime_target=local` 才检查本地 nnUNet 文件。
- server 模式至少检查：`evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`。

涉及文件：

- `server/main.py`：`get_model_state(runtime_target)` required files 分支。
- `server/server_inference.py`：确认 server config 字段完整性。

## Phase 5：文档和下一轮交接

- [ ] 代码实现前先确认 AMOS 标签 unique IDs、spacing/affine 和 prediction 是否一致。
- [ ] 实现后复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`。
- [ ] 实现后复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`。
- [ ] 若 server 模式仍 503，优先检查 `runtime_target=server` 是否仍走了本地 nnUNet required files。
- [ ] 验证通过后再把服务器 AMOS 指标加入正式质量基线。

## Verification

### AMOS 标签验证

1. 启动服务器后端。
2. 本地前端设置：`VITE_API_ENDPOINT=http://10.102.1.202:8000`。
3. 上传 AMOS 原图 + AMOS label。
4. 选择 `label_taxonomy=AMOS22`。
5. 预期：
   - `remap_applied=false`
   - `remap_source` 为空或不出现
   - Dice 不再大面积为 0
   - GUI 显示 `Label 6=肝脏`、`Label 9=下腔静脉`

### FLARE 标签验证

1. 上传 FLARE 原图 + FLARE label。
2. 选择 `label_taxonomy=FLARE22`。
3. 预期：
   - `remap_applied=true`
   - `remap_source=FLARE22`
   - validation 按 AMOS 模型标签体系计算

### Server mode 创建任务验证

1. 前端选择“服务器云端推理”。
2. 创建 job。
3. 预期 `/api/segment/jobs` 不再因本地 `dataset.json/plans/checkpoint/python.exe` 缺失而 503。
4. 任务能进入 `5-fold 并行推理中`。
