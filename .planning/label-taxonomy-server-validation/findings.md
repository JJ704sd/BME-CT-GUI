# Label taxonomy and server validation findings

## 2026-05-30：服务器在线推理已跑通，但 validation 出现标签体系错位迹象

**事实：** 服务器在线推理主链路已经跑通：前端提交 `runtime_target=server`，服务器执行 5-fold 推理、soft ensemble，并把 NIfTI 结果下载回前端显示。

**证据：** 导出报告 `segmentation-report-AMOS_0117-1780153069392.json` 中：

- `inference.status=succeeded`
- `jobId=5d8f5eee7b75`
- `mode=real-nnunetv2`
- `duration_seconds=586.453`
- `server_fold_predict=449.5s`
- `server_ensemble=131.116s`
- `result_size_bytes=141986`

## 2026-05-30：Dice 异常更像标签体系错位，不像模型完全失败

**事实：** 本次 validation 显示 `mean_dice=0.076015`、`min_dice=0`，但 `foreground_dice=0.979808`。

**判断：** 前景 Dice 很高说明预测前景总体和参考标签大体重合；逐器官 Dice 大面积为 0 更像 label ID 语义错位，而不是分割结果完全错误。

**关键异常：** 报告中同时出现：

- `sample_id=custom`
- `taxonomy_match=true`
- `remap_applied=true`
- `remap_source=FLARE22`
- message: `已自动重映射标签 ID（FLARE22 → 当前模型）...`

如果用户上传的是 `amos_0117(2).nii` 这类 AMOS 原生标签，那么后端把它判为 FLARE22 并 remap 就是误判。

## 2026-05-31：taxonomy fix 已完成

**事实：** 已实现显式 `label_taxonomy=auto|AMOS22|FLARE22`，并更新 `detect_dataset()` 为保守策略：当参考标签 ID 是 checkpoint 标签 ID 的子集时，不自动触发 FLARE22 remap。

**证据：** 本地验证 job `d56bcff76a8b` 在选择 `AMOS22` 时返回 `remap_applied=false`；前端也已在分割控制面板提供 `自动识别 / AMOS22 原生 / FLARE22 标签` 三种标签体系选项。

**判断：** AMOS 标签误判问题在当前源码中已修复。接下来需要把 20260531 runtime 包部署到服务器，并复跑 AMOS/FLARE 服务器 validation，确认服务器端也使用同一版逻辑。

## 2026-05-31：部署包结构已调整

**事实：** `server-runtime-package-20260531.zip` 内部已改为项目结构：

```text
server/main.py
server/taxonomy.py
server/server_inference.py
server/persistent_nnunet_worker.py
server/requirements.txt
```

**判断：** 服务器可以在项目根目录直接 `unzip -o server-runtime-package-20260531.zip` 覆盖后端文件，比上一版裸文件包更不容易放错目录。

## 仍需确认的证据

1. 服务器更新后，AMOS label 使用 `label_taxonomy=AMOS22` 是否稳定得到 `remap_applied=false`。
2. 服务器更新后，FLARE label 使用 `label_taxonomy=FLARE22` 是否稳定得到 `remap_applied=true`、`remap_source=FLARE22`。
3. 服务器实际模型的 `dataset.json`、checkpoint 标签定义和 `/api/models` 返回 labels 是否一致。
4. `runtime_target=server` 创建 job 是否仍会被本地 Windows nnUNet 文件缺失阻断。

## 2026-06-02：AMOS 真实 1-13 标签与 FLARE22 在裸 ID 集合上不可分

**事实：** AMOS 真实 `amos_0117_label.nii/amos_0117(2).nii` 实际 unique IDs = `{1..13}`（无 bladder/prostate 体素），FLARE22 真实 1-13 与之完全一致。在仅有裸 ID 信息的前提下，两者无法被任何 `detect_dataset()` 唯一分辨。

**判断：** 旧 `detect_dataset()`（"reference_ids ≠ ckpt_ids → 进入 dataset 循环 → 12/13 命名错位 ≥ 5" → `FLARE22`）会把 AMOS 真实 1-13 数据错判为 FLARE22，触发 `remap_applied=true`、AMOS Dice 严重下降。这是 2026-06-01 现场复测 AMOS 自身 dice 异常低的真正根因。

**修复：** `detect_dataset()` 新增 0.85 coverage 守卫（`len(reference_ids ∩ ckpt_ids) / len(ckpt_ids) >= 0.85 → None`），把这种边界直接退回到不 remap；正式 taxonomy 选择由前端 `loadReferenceCase()` 按 `referenceCase.dataset` 字段自动设置（AMOS 病例 → `AMOS22`、FLARE22 病例 → `FLARE22`）。

**证据：** 跑 `python tests/backendState.test.py`、`npm test`、`npm run build` 全过（`EXIT=0`）。`tests/backendState.test.py` 新增 `test_taxonomy_returns_none_for_realistic_amos_1_to_13_reference`。

## 当前结论

`label_taxonomy=auto|AMOS22|FLARE22` 已改善 validation/remap 解释链路，但它不改变原始 nnUNet 推理输出。`auto` 模式 2026-06-02 起在 AMOS 1-13 vs FLARE22 1-13 不可分的边界退化为保底（不 remap）；正式 taxonomy 应使用显式 `AMOS22` / `FLARE22` 或由前端按 `referenceCase.dataset` 字段自动设置。服务器 AMOS 轮次必须用 `AMOS22` hint 复跑，确认 `remap_applied=false` 后才能判断真实器官 Dice；不要继续把 AMOS `mean_dice=0.076015` 当作模型失败结论写入质量基线。

## 2026-06-02：dataset_hint 字段打通 auto 边界

**事实：** 0.85 coverage 守卫上线后，FLARE22 真实 1-13 标签也会被 `detect_dataset()` 判为 `None`，导致 FLARE22_Tr_0009 在 `auto` 模式下走不到 remap 路径。

**修复：** 新增 `dataset_hint` 表单字段，前端在 `loadReferenceCase()` 成功载入参考标签后把 `referenceCase.dataset` 写入 `referenceCaseDatasetHint` 状态并随 job 提交；后端 `validate_against_custom_label()` 在 `label_taxonomy=auto` 但 `dataset_hint=FLARE22` 时强制 `detected = "FLARE22"`，覆盖 0.85 守卫的 None。上传自定义 NIfTI 时前端清空 `referenceCaseDatasetHint` 避免错误继承。

**证据：** `tests/backendState.test.py` 新增 `test_validate_against_custom_label_uses_dataset_hint_when_taxonomy_is_auto`：在 `taxonomy=auto + dataset_hint=FLARE22` 下，FLARE22 真实 1-13 标签走 `detected="FLARE22"`，`remap_applied=true`，mean_dice 显著恢复；在 `taxonomy=auto + dataset_hint=AMOS22` 下保持 `None`，不误 remap。
