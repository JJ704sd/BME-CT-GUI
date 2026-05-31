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

## 当前结论

`label_taxonomy=auto|AMOS22|FLARE22` 已改善 validation/remap 解释链路，但它不改变原始 nnUNet 推理输出。服务器 AMOS 轮次必须用 `AMOS22` hint 复跑，确认 `remap_applied=false` 后才能判断真实器官 Dice；不要继续把 AMOS `mean_dice=0.076015` 当作模型失败结论写入质量基线。
