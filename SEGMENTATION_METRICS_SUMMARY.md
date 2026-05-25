# Segmentation Metrics Summary

本文档用于登记训练权重对应的分割指标。每次更换或训练出新权重后，使用同一套输入、参考标签和命令生成 JSON 与 Markdown，便于横向比较。

## Reusable Command

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
- `<run-name>-segmentation-metrics.md`：人工阅读版 summary。

记录字段：

- Dice：per-label、mean、min、foreground。
- IoU：per-label、mean、min、foreground。
- Voxel Accuracy / Pixel Accuracy：3D NIfTI 中两者均为体素逐点 exact-match accuracy。
- Hausdorff Distance：按 NIfTI spacing 计算的对称 surface Hausdorff Distance，单位为 mm。
- Checkpoint metadata：路径、文件大小、修改时间和 SHA256。

标签源要求：

- 优先使用本次推理生成的 `validation_summary.json`，因为它来自 checkpoint 内嵌的 `dataset_json`，能保留当前权重的完整标签定义。
- 不要混用旧的外部 `dataset.json`；如果标签集合不同，会导致 label 名称错位或漏记空标签。
- 本轮 checkpoint 定义 15 个前景标签。AMOS 0117 的参考标签实际只出现 label `1..13`；如果预测也没有 label `14/15`，它们记录为 N/A。如果预测出现 label `14/15` 假阳性，则 Dice/IoU 为 `0` 并应纳入 fast/quality 对照判断。

## Latest Run

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
- Result SHA256: `5473EAFB22FA21B896F8511BE9E02FFD49D678DEE4B82E63681FDD99DA57D9C0`

2026-05-25 fast/quality no-cache profile 对照输出：

- Fast prediction: `.test-output\perf-fast-profile-20260525-1305\work\6802e01f1a73\output\6802e01f1a73.nii.gz`
- Fast JSON: `.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.json`
- Fast Markdown: `.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.md`
- Quality prediction: `.test-output\perf-quality-profile-20260525-1330\work\b3c528cc9e20\output\b3c528cc9e20.nii.gz`
- Quality JSON: `.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.json`
- Quality Markdown: `.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.md`

## Latest Aggregate Metrics

| Metric | Value |
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

## Fast vs Quality No-cache Profile Comparison

同一 AMOS 0117 输入、同一 checkpoint、同一性能脚本，均禁用历史缓存：

| Metric | Fast profile | Quality profile |
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
- label `14/15` 的小体积假阳性只在本轮 fast profile 中出现；如要过滤，应作为独立 `postprocess` 实验记录，不能混同模型原始输出。
- 2026-05-25 后续实现已把 `quality/fast` 做成每次 job 的显式产品选择。`inference_options` 会随创建响应、job state、SSE complete 事件和 `job_summary.json` 保存；本节指标仍只代表上表两次原始模型输出，没有新增后处理分数。

Checkpoint metadata：

| Field | Value |
|---|---|
| size_bytes | `1136119762` |
| modified_time | `2026-05-24T10:04:22+00:00` |
| sha256 | `45021cef5f37868f8e76f4c372b5d911eef259db6d38943779ba25318c37e6c7` |

## Latest Per-label Metrics

| Label | Name | Dice | IoU | Hausdorff Distance (mm) |
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

## Notes

- 本文档记录的是 AMOS 0117 参考病例上的指标，不代表所有外部 CT 都具备同等效果。
- 没有标准标签的病例不能计算 Dice、IoU 或 Hausdorff Distance，只能记录推理耗时、资源快照和人工复核结论。
- 后续训练权重应保留每次的 JSON 原始输出，并把关键聚合指标追加到本文档。
