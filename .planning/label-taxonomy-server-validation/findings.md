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

## 需要继续确认的证据

1. 上传 label 文件的 unique label IDs 和各 label voxel count。
2. 上传 label 文件到底是 AMOS22 原生标签还是 FLARE22 标签。
3. `server/taxonomy.py` 的 `detect_dataset()` 是否在 AMOS 原生标签上误触发 FLARE22。
4. 当前服务器实际模型的 `dataset.json`、checkpoint 标签定义和 `/api/models` 返回 labels 是否一致。

## 2026-05-31：文档同步后的当前结论

**事实：** 项目文档已把服务器在线推理状态从“部署准备 / 待 smoke”更新为“校园网 smoke 已跑通，但 validation taxonomy 仍需修复”。

**关键判断：** `label_taxonomy=auto|AMOS22|FLARE22` 能改善当前 FLARE 高 Dice / AMOS 低 Dice 的映射问题，但它改善的是 validation/remap 解释链路，不改变原始 nnUNet 推理输出。AMOS 轮次必须用 `AMOS22` hint 复跑，确认 `remap_applied=false` 后才能判断真实器官 Dice。

**How to apply:** 下一轮代码任务应优先实现显式 taxonomy hint 和 server gating；不要继续把 AMOS `mean_dice=0.076015` 当作模型失败结论写入质量基线。
