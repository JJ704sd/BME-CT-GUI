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
- 本轮 checkpoint 定义 15 个前景标签，但 AMOS 0117 这份参考标签和预测结果只实际出现 label `1..13`，因此 label `14/15` 会保留为 N/A。

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
