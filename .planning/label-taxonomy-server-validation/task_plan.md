# Label taxonomy and server validation task plan

## Context

服务器在线推理已经能完成 5-fold + soft ensemble + 前端回填，但历史 AMOS_0117 带标签验证报告出现异常：`mean_dice=0.076015`、`foreground_dice=0.979808`，且后端自动应用了 `FLARE22 → 当前模型` remap。当前源码已实现显式 `label_taxonomy=auto|AMOS22|FLARE22` 和更保守的 `detect_dataset()`，并已生成 `server-runtime-package-20260531.zip`。2026-06-02 进一步收紧 `detect_dataset()`（0.85 coverage 守卫 + 前端按 `referenceCase.dataset` 预设 taxonomy）。下一轮目标是把修复部署到服务器，复跑 AMOS/FLARE validation，并收口 server 模式 gating。

## Phase 1：服务器代码更新 [待执行]

- [ ] 上传 `deployment-packages/server-runtime-package-20260531.zip` 到服务器项目根目录。
- [ ] 备份服务器当前 `server/` 目录。
- [ ] 在项目根目录执行 `unzip -o server-runtime-package-20260531.zip`。
- [ ] 如依赖缺失，执行 `python -m pip install -r server/requirements.txt`。
- [ ] 重启 FastAPI 服务。
- [ ] 访问 `/api/health` 和 `/api/models`，确认后端已恢复服务。

## Phase 2：AMOS 显式 taxonomy 复跑 [待执行]

- [ ] 上传 AMOS 原图 + AMOS label。
- [ ] 选择 `runtime_target=server`。
- [ ] 选择 `label_taxonomy=AMOS22`。
- [ ] 记录 job id、duration、phase_timings、result_size_bytes。
- [ ] 检查 `validation.label_taxonomy=AMOS22`。
- [ ] 检查 `remap_applied=false`。
- [ ] 若 Dice 仍异常，先检查 shape、spacing/affine、reference unique IDs 和 prediction unique IDs，再判断模型质量。

## Phase 3：FLARE 显式 taxonomy 复跑 [待执行]

- [ ] 上传 FLARE 原图 + FLARE label。
- [ ] 选择 `runtime_target=server`。
- [ ] 选择 `label_taxonomy=FLARE22`。
- [ ] 记录 job id、duration、phase_timings、result_size_bytes。
- [ ] 检查 `validation.label_taxonomy=FLARE22`。
- [ ] 检查 `remap_applied=true`、`remap_source=FLARE22`。
- [ ] 记录 mean/min/foreground Dice，并继续把 FLARE 解释为跨数据集 remap 指标，不与 AMOS 原生基线混算。

## Phase 4：修复或验证 server 模式 gating [待执行]

当前需确认 `/api/models` 和 `/api/segment/jobs` 是否仍因为本地 Windows nnUNet 文件缺失而影响 `runtime_target=server`。

检查目标：

- [ ] `runtime_target=server` 创建 job 时只检查 server 路径。
- [ ] `runtime_target=local` 才检查本地 nnUNet 文件。
- [ ] server 模式至少检查：`evaluate_script`、`dataset_json`、`nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results`、`output_root`。
- [ ] `/api/segment/jobs` 不因本地 `dataset.json/plans/checkpoint/python.exe` 缺失而 503。

涉及文件：

- `server/main.py`：`get_model_state(runtime_target)`、`create_job()`。
- `server/server_inference.py`：server config 字段完整性。
- `tests/backendState.test.py`：增加或保留 server/local gating 覆盖。

## Phase 5：文档和验收收尾 [待执行]

- [ ] 将 AMOS 复跑结果写入 `SEGMENTATION_RECENT_ROUNDS.md`。
- [ ] 若 AMOS `remap_applied=false` 且 Dice 合理，再写入 `SEGMENTATION_METRICS_SUMMARY.md` 的正式服务器质量基线。
- [ ] 将 FLARE 复跑结果写入跨数据集 remap 证据，不与 AMOS 原生基线混算。
- [ ] 更新 `ACCEPTANCE.md`、`README.md`、`REVIEW.md` 中的服务器 validation 状态。
- [ ] 确认文档主体仍为中文。

## Verification

### AMOS 标签验证

1. 启动服务器后端。
2. 本地前端设置：`VITE_API_ENDPOINT=http://10.102.1.202:8000`。
3. 上传 AMOS 原图 + AMOS label。
4. 选择 `label_taxonomy=AMOS22`。
5. 预期：
   - `remap_applied=false`
   - `remap_source` 为空或不出现
   - Dice 不再因 ID 错位大面积为 0
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
