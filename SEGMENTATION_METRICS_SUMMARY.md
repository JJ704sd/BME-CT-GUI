# 分割指标汇总

本文档用于登记训练权重对应的分割指标。每次更换或训练出新权重后，使用同一套输入、参考标签和命令生成 JSON 与 Markdown，便于横向比较。

## 可复用命令

```powershell
python tools\segmentation_metrics_summary.py `
  --prediction <prediction.nii.gz> `
  --reference <reference-label.nii.gz> `
  --checkpoint <checkpoint_best.pth> `
  --labels-json <validation_summary.json> `
  --sample-id <sample-id> `
  --output-dir .test-output\<metrics-run-id> `
  --stem <run-name>-segmentation-metrics
```

输出文件：

- `<run-name>-segmentation-metrics.json`：结构化指标，适合脚本读取和后续对比。
- `<run-name>-segmentation-metrics.md`：人工阅读版指标摘要。

记录字段：

- Dice：逐标签、平均值、最低值、前景值。
- IoU：逐标签、平均值、最低值、前景值。
- Voxel Accuracy / Pixel Accuracy：3D NIfTI 中两者均为体素逐点 exact-match accuracy。
- Hausdorff Distance：按 NIfTI spacing 计算的对称 surface Hausdorff Distance，单位为 mm。
- Checkpoint 元数据：路径、文件大小、修改时间和 SHA256。

标签源要求：

- 优先使用本次推理生成的 `validation_summary.json`，因为它来自 checkpoint 内嵌的 `dataset_json`，能保留当前权重的完整标签定义。
- 不要混用旧的外部 `dataset.json`；如果标签集合不同，会导致 label 名称错位或漏记空标签。
- 本轮 checkpoint 定义 15 个前景标签。AMOS 0117 的参考标签实际只出现 label `1..13`；如果预测也没有 label `14/15`，它们记录为 N/A。如果预测出现 label `14/15` 假阳性，则 Dice/IoU 为 `0` 并应纳入 fast/quality 对照判断。
- 2026-05-26 后端新增输入后缀规范化，确保 `.nii` 上传会按当前模型 `file_ending=.nii.gz` 进入 nnUNetv2；该工程修复不改变本文件既有指标数值。
- 2026-05-27 标签文件传输修复后，后端在线 custom label validation 已可用。当上传的标签 ID 与 checkpoint 不一致时，`server/taxonomy.py` 会自动检测数据集来源（如 FLARE22）并按器官名重映射 ID，validation 结果中 `remap_applied: true` 表示已自动重映射。
- 2026-05-29 缓存命中时不再复用缓存来源 job 的 `validation`；预测 NIfTI 可复用，但 Dice/IoU/Hausdorff 必须来自本次请求的标签文件或内置参考标签。
- 2026-05-29 自动 remap 支持部分 FLARE22 标签：当至少两个共享 ID 明确语义错位且没有原生匹配时可识别为 FLARE22；单 label 文件仍不自动推断数据集来源。
- 2026-05-30 新增 `runtime_target=local|server` 和局域网访问配置后，本文件中的历史 AMOS/FLARE 指标不变；本地 fold0、服务器 5-fold ensemble 和不同 profile 的指标必须分开记录，不能混算。

## 当前 AMOS 基线运行

本轮新权重：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\checkpoint_best.pth
```

预测结果：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\acceptance-new-weight-20260524-201714\work\27216eb73220\output\27216eb73220.nii.gz
```

参考标签：

```text
D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\amos_0117(2).nii.gz
```

详细输出：

- JSON: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.json`
- Markdown: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.md`

无缓存 warm timeout 后补充输出：

- Prediction: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\perf-no-cache-persistent-20260524-212332\work\685426290aa4\output\685426290aa4.nii.gz`
- JSON: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.json`
- Markdown: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.md`
- 结果 SHA256：`5473EAFB22FA21B896F8511BE9E02FFD49D678DEE4B82E63681FDD99DA57D9C0`

2026-05-25 fast/quality no-cache profile 对照输出：

- 快速预览 prediction：`.test-output\perf-fast-profile-20260525-1305\work\6802e01f1a73\output\6802e01f1a73.nii.gz`
- 快速预览 JSON：`.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.json`
- 快速预览 Markdown：`.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.md`
- 质量推理 prediction：`.test-output\perf-quality-profile-20260525-1330\work\b3c528cc9e20\output\b3c528cc9e20.nii.gz`
- 质量推理 JSON：`.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.json`
- 质量推理 Markdown：`.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.md`

## 当前 AMOS 基线聚合指标

| 指标 | 数值 |
|---|---:|
| mean Dice | `0.924791` |
| min Dice | `0.846551` |
| foreground Dice | `0.980316` |
| mean IoU | `0.865105` |
| min IoU | `0.733930` |
| foreground IoU | `0.961392` |
| Voxel Accuracy | `0.998578` |
| Pixel Accuracy | `0.998578` |
| mean Hausdorff Distance | `7.716048 mm` |
| max Hausdorff Distance | `16.562684 mm` |

## 快速预览与质量推理无缓存对照

同一 AMOS 0117 输入、同一 checkpoint、同一性能脚本，均禁用历史缓存：

| 指标 | 快速预览 profile | 质量推理 profile |
|---|---:|---:|
| job id | `6802e01f1a73` | `b3c528cc9e20` |
| duration_seconds | `384.345` | `1360.398` |
| persistent_worker | `381.448` | `1357.677` |
| result_bytes | `142578` | `141568` |
| validation status | `review` | `passed` |
| mean Dice | `0.777243` | `0.924780` |
| min Dice | `0.000000` | `0.846569` |
| foreground Dice | `0.972898` | `0.980317` |
| mean IoU | `0.713592` | `0.865088` |
| min IoU | `0.000000` | `0.733957` |
| foreground IoU | `0.947226` | `0.961394` |
| Voxel Accuracy | `0.998068` | `0.998578` |
| Pixel Accuracy | `0.998068` | `0.998578` |
| mean Hausdorff Distance | `10.282058 mm` | `7.716048 mm` |
| max Hausdorff Distance | `24.616009 mm` | `16.562684 mm` |
| label 14 prediction_voxels | `664` | `0` |
| label 15 prediction_voxels | `670` | `0` |

结论：

- `quality` 应作为默认/正式报告依据。
- `fast` 可作为快速预览或演示模式，但必须标注“需复核”。
- label `14/15` 的小体积假阳性只在本轮 `fast` profile 中出现；如要过滤，应作为独立 `postprocess` 实验记录，不能混同模型原始输出。
- 2026-05-25 后续实现已把 `quality/fast` 做成每次 job 的显式产品选择。`inference_options` 会随创建响应、job state、SSE complete 事件和 `job_summary.json` 保存；本节指标仍只代表上表两次原始模型输出，没有新增后处理分数。

## FLARE22 Tr 0009 标签体系重映射对照

2026-05-26 新增 FLARE22 Tr 0009 后执行一次 `quality` 在线推理。该病例的原始 FLARE22 label ID 顺序与当前 AMOS22 checkpoint 不一致；当时的下表指标来自离线 remap：先按器官名把 FLARE22 label 映射到 AMOS22 checkpoint label ID，再运行指标脚本，仅作为非 AMOS 对照证据。

2026-05-28 已将同一类映射能力产品化到后端 `server/taxonomy.py`：用户上传 FLARE22 标签文件时，后端会自动检测来源数据集并按器官名重映射后计算在线 Dice。最新在线验证记录见本节后面的“自动 taxonomy remap 在线验证”。

运行输出：

- Job summary：`.test-output\flare22-tr-0009-quality-20260526\job_summary.json`
- Prediction：`.test-output\flare22-tr-0009-quality-20260526\86b0153d0a73.nii.gz`
- Remapped reference：`.test-output\flare22-tr-0009-quality-20260526\FLARE22_Tr_0009_label_remapped_to_amos_ids.nii.gz`
- Remap metadata：`.test-output\flare22-tr-0009-quality-20260526\flare_to_amos_label_remap.json`
- Metrics JSON：`.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.json`
- Metrics Markdown：`.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.md`

推理记录：

| 指标 | 数值 |
|---|---:|
| job id | `86b0153d0a73` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| duration_seconds | `237.323` |
| phase_timings | `prepare_runtime_model=0.003`, `persistent_worker=237.119`, `collect_result=0.001` |
| result_size_bytes | `120761` |
| GPU at completion | `NVIDIA GeForce RTX 4060 Laptop GPU`, `1804 / 8188 MiB`, `18%` |

重映射后的聚合指标：

| 指标 | 数值 |
|---|---:|
| mean Dice | `0.893127` |
| min Dice | `0.673730` |
| foreground Dice | `0.949908` |
| mean IoU | `0.815941` |
| min IoU | `0.507989` |
| foreground IoU | `0.904594` |
| Voxel Accuracy | `0.991879` |
| Pixel Accuracy | `0.991879` |
| mean Hausdorff Distance | `12.595149 mm` |
| max Hausdorff Distance | `38.043429 mm` |
| label 14 prediction_voxels | `0` |
| label 15 prediction_voxels | `0` |

本次重映射对照中，逐标签最低值为 `duodenum` Dice `0.673730`、`pancreas` Dice `0.806389` 和 `esophagus` Dice `0.808989`；最高 Dice 为 `liver=0.968961`、`spleen=0.965952` 和 `gall_bladder=0.949364`。

解释边界：

- 这是 2026-05-26 的离线 remap 对照，不是当时的后端自动验证；不能与 AMOS 0117 原生标签指标混算。
- 该 remap 只适合作为 FLARE22 与 AMOS22 checkpoint 共有 13 个器官的器官名对齐检查。
- FLARE22 本例没有膀胱或前列腺/子宫标签；label `14/15` 仍为空，并且本次 `quality` 运行中对应预测体素为 `0`。

### 自动 taxonomy remap 在线验证

2026-05-28 自动 taxonomy remap 上线后，FLARE22 Tr 0009 上传标签文件即可在后端在线 validation 中自动重映射：

| 指标 | 数值 |
|---|---:|
| job id | `a717dacf42d3` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| profile | `quality` |
| remap_applied | `true` |
| remap_source | `FLARE22` |
| mean Dice | `0.926` |
| validation status | `passed` |

解释边界：

- 该记录证明跨数据集在线 validation 链路已打通，但仍是 FLARE22 标签按器官名重映射后的指标，不是 AMOS 原生标签验证。
- `remap_applied: true` 是解释指标的关键字段；缺少该字段时，不应把 FLARE22 原始 label ID 直接当作 AMOS22 label ID 解读。
- 当前部分标签自动 remap 只覆盖至少两个明确错位 ID 的情况；只有单个 label ID 的文件仍应记录为人工判断或等待显式数据集 hint。

Checkpoint 元数据：

| 字段 | 数值 |
|---|---|
| size_bytes | `1136119762` |
| modified_time | `2026-05-24T10:04:22+00:00` |
| sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |

## 当前 AMOS 基线逐标签指标

| 标签 | 名称 | Dice | IoU | Hausdorff Distance (mm) |
|---:|---|---:|---:|---:|
| 1 | 脾脏 | `0.985234` | `0.970898` | `5.025721` |
| 2 | 右肾 | `0.982296` | `0.965208` | `7.090247` |
| 3 | 左肾 | `0.987893` | `0.976075` | `5.000000` |
| 4 | 胆囊 | `0.953659` | `0.911423` | `5.000000` |
| 5 | 食管 | `0.857557` | `0.750634` | `6.774050` |
| 6 | 肝脏 | `0.988545` | `0.977349` | `10.757801` |
| 7 | 胃 | `0.846551` | `0.733930` | `16.562684` |
| 8 | 主动脉 | `0.985093` | `0.970624` | `5.103452` |
| 9 | 下腔静脉 | `0.933244` | `0.874843` | `5.000000` |
| 10 | 胰腺 | `0.888885` | `0.799994` | `10.166236` |
| 11 | 右肾上腺 | `0.883697` | `0.791627` | `5.000000` |
| 12 | 左肾上腺 | `0.858547` | `0.752152` | `8.140854` |
| 13 | 十二指肠 | `0.871085` | `0.771613` | `10.687574` |
| 14 | 膀胱 | `N/A` | `N/A` | `N/A` |
| 15 | 前列腺/子宫 | `N/A` | `N/A` | `N/A` |

## 备注

### 2026-05-26 GUI 运行时渲染说明

本轮 GUI 交互性能优化不改变本指标汇总中的任何数值。代码改动只影响前端渲染节奏：

- `src/components/OrthogonalViewer.tsx` 使用 `requestAnimationFrame` 合并高频切片图像更新。
- `src/main.tsx` 按动画帧调度 axial 预览切片更新，并让右侧预览和底部缩略图复用共享切片缓存渲染器。
- 十字线反馈仍保持即时；较重的 `canvas.toDataURL()` 切片栅格化在快速移动光标时减少同步触发。
- 矢状/冠状拖动回跳修复只改变前端 `voxelCoord` 与 `selectedSlice` 的同步方向，不改变任何分割结果或指标计算。
- 三视图拖动卡顿二次修复进一步把 `voxelCoord` 本身的 React 状态提交合并到每帧一次，并与拖动派生的 `selectedSlice` 同帧提交；该改动仍只影响前端渲染节奏。
- 矢状/冠状拖动卡顿三次修复增加拖动状态识别，拖动期间三视图使用 `interactive` 轻量切片实时预览，释放后恢复完整质量；这是 GUI 交互优化，不影响 NIfTI 输出或指标脚本。
- 本轮没有改变 nnUNetv2 推理、validation、Dice/IoU/Hausdorff 计算，也没有改变 FLARE22 taxonomy-remap 指标。

- 本文档记录的是 AMOS 0117 参考病例上的指标，不代表所有外部 CT 都具备同等效果。
- 2026-05-27 标签文件传输修复后，后端在线 custom label validation 链路已打通。job `bf20f0ec4456`（FLARE22 + 标签上传）验证了 `label_path` 非空、validation 正常执行。2026-05-28 实现自动 taxonomy remap 后，job `a717dacf42d3` 在线验证 mean_dice=0.926，验证通过。
- 2026-05-29 修复缓存 validation 语义后，缓存命中的指标不得解释为缓存来源 job 的旧标签结果；同一 CT 换标签文件时，validation 会重新计算。
- 2026-05-29 移除上传文件名调试日志后，标签链路排查应依赖 job state、`label_path`、validation summary 和测试覆盖，而不是控制台文件名输出。
- 2026-05-30 的运行位置选择、局域网配置和服务器 5-fold soft ensemble 编排入口属于工程链路更新；在真实 Linux 服务器端到端推理和第二台局域网设备 smoke test 完成前，不新增服务器质量指标，也不替换当前 AMOS `quality` 基线。
- 没有标准标签的病例不能计算 Dice、IoU 或 Hausdorff Distance，只能记录推理耗时、资源快照和人工复核结论。
- 后续训练权重应保留每次的 JSON 原始输出，并把关键聚合指标追加到本文档。
