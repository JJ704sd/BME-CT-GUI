# Segmentation Experiment Comparison

Generated: 2026-05-26

This document collects the historical segmentation experiment records for quick comparison. It is intended as a companion to `SEGMENTATION_METRICS_SUMMARY.md`: that file records the latest summary and command context, while this file keeps the cross-run comparison table.

## Data Sources

- `.test-output\acceptance-real-20260524-194750\work\32dfe3117b40\output\job_summary.json`
- `.test-output\perf-persistent-20260524-200515\work\a4b3806cfe1f\output\job_summary.json`
- `.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.md`
- `.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.md`
- `.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.md`
- `.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.md`
- `.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.md`
- `.test-output\*\job_summary.json` for runtime, status, cache, and validation metadata.

Notes:

- Old acceptance and old persistent runs only contain per-label Dice and voxel counts in `job_summary.json`; they do not include per-label IoU or Hausdorff Distance.
- AMOS 0117 records use the native checkpoint label taxonomy.
- FLARE22 Tr 0009 uses an offline organ-name remap into AMOS label IDs. It is useful as cross-dataset evidence, but should not be mixed directly with native AMOS validation.
- `N/A` means both prediction and reference are empty for that label. `0.000000` means the run predicted voxels for a label that was absent in the reference.

## Experiment Name Guide

Use this table when reading the comparison columns or debugging a historical result. The short names in later tables are intentionally compact, but each one maps to a specific purpose.

| Short name | Plain meaning | When to check it | Source run |
|---|---|---|---|
| 旧模型首跑 | 旧 checkpoint / 旧推理流程的第一次有效 AMOS 0117 验证 | 排查“为什么旧结果没过阈值”或对比新权重提升幅度 | `acceptance-real-20260524-194750`, job `32dfe3117b40` |
| 旧模型常驻 | 旧 checkpoint 在 persistent worker 流程下的复测 | 判断旧结果问题是否来自 worker 流程；结果与旧模型首跑基本一致 | `perf-persistent-20260524-200515`, job `a4b3806cfe1f` |
| 新权重首跑 | 更换到当前 checkpoint 后的第一次完整 AMOS 0117 验证 | 查看新权重相对旧模型的主要提升，尤其胃、食管、肾上腺 | `acceptance-new-weight-20260524-201714`, job `27216eb73220` |
| 新权重补算 | 同一新权重在 no-cache / warm persistent 场景下的补充指标 | 排查超时、缓存关闭或 warm worker 场景；指标应接近新权重首跑 | `segmentation-metrics-warm-timeout-20260524-2257`, job `685426290aa4` |
| 快速预览 | fast profile：关闭 TTA、较大 tile step，优先速度 | 排查演示/预览模式；不要作为正式质量结论，注意 label 14/15 假阳性 | `perf-fast-profile-20260525-1305`, job `6802e01f1a73` |
| 正式质量 | quality profile：开启 TTA、较稳的正式推理配置 | 正式报告、验收截图、基准对比优先使用这一列 | `perf-quality-profile-20260525-1330`, job `b3c528cc9e20` |
| 跨数据集 FLARE | FLARE22 病例按器官名 remap 到 AMOS 标签后的离线对照 | 排查模型在非 AMOS 数据上的泛化趋势；不能直接和 AMOS 原生验证混算 | `flare22-tr-0009-quality-20260526`, job `86b0153d0a73` |

## Experiment Overview

| Run | Job ID | Sample | Profile / mode | Status | Cached | Duration (s) | Mean Dice | Min Dice | Foreground Dice | Mean IoU | Voxel Accuracy | Mean HD (mm) |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 旧模型首跑 | `32dfe3117b40` | AMOS 0117 | real-nnUNetv2 | review | false | 359.425 | 0.891305 | 0.555910 | 0.971220 | N/A | N/A | N/A |
| 旧模型首跑缓存 | `c8cecb040657` | AMOS 0117 | cached-real-nnUNetv2 | review | true | 0.000 | 0.891305 | 0.555910 | 0.971220 | N/A | N/A | N/A |
| 旧模型常驻 | `a4b3806cfe1f` | AMOS 0117 | real-nnUNetv2 | review | false | 356.950 | 0.891327 | 0.555985 | 0.971222 | N/A | N/A | N/A |
| 新权重首跑 | `27216eb73220` | AMOS 0117 | real-nnUNetv2 | passed | false | 1124.327 | 0.924791 | 0.846551 | 0.980316 | 0.865105 | 0.998578 | 7.716048 |
| 新权重缓存 | `f200f16f47be` | AMOS 0117 | cached-real-nnUNetv2 | passed | true | 0.000 | 0.924791 | 0.846551 | 0.980316 | N/A | N/A | N/A |
| 新权重补算 | `685426290aa4` | AMOS 0117 | real-nnUNetv2 | metrics available after timeout | false | >=1800.785 | 0.924782 | 0.846540 | 0.980316 | 0.865092 | 0.998578 | 7.716048 |
| 快速预览 | `6802e01f1a73` | AMOS 0117 | fast, TTA off | review | false | 384.345 | 0.777243 | 0.000000 | 0.972898 | 0.713592 | 0.998068 | 10.282058 |
| 正式质量 | `b3c528cc9e20` | AMOS 0117 | quality, TTA on | passed | false | 1360.398 | 0.924780 | 0.846569 | 0.980317 | 0.865088 | 0.998578 | 7.716048 |
| 跨数据集 FLARE | `86b0153d0a73` | FLARE22 Tr 0009 | quality, offline remap | comparison only | false | 237.323 | 0.893127 | 0.673730 | 0.949908 | 0.815941 | 0.991879 | 12.595149 |

## Per-label Dice Comparison

| Label | Organ | 旧模型首跑 | 旧模型常驻 | 新权重首跑 | 新权重补算 | 快速预览 | 正式质量 | 跨数据集 FLARE |
|---:|---|---:|---:|---:|---:|---:|---:|---:|
| 1 | 脾脏 | 0.979075 | 0.979085 | 0.985234 | 0.985251 | 0.982458 | 0.985242 | 0.965952 |
| 2 | 右肾 | 0.978732 | 0.978704 | 0.982296 | 0.982287 | 0.980218 | 0.982291 | 0.945245 |
| 3 | 左肾 | 0.985639 | 0.985648 | 0.987893 | 0.987893 | 0.985947 | 0.987897 | 0.947873 |
| 4 | 胆囊 | 0.950326 | 0.950342 | 0.953659 | 0.953696 | 0.950942 | 0.953681 | 0.949364 |
| 5 | 食管 | 0.793738 | 0.793725 | 0.857557 | 0.857525 | 0.808644 | 0.857552 | 0.808989 |
| 6 | 肝脏 | 0.984248 | 0.984249 | 0.988545 | 0.988547 | 0.985892 | 0.988546 | 0.968961 |
| 7 | 胃 | 0.555910 | 0.555985 | 0.846551 | 0.846540 | 0.726965 | 0.846569 | 0.945877 |
| 8 | 主动脉 | 0.977634 | 0.977631 | 0.985093 | 0.985077 | 0.981288 | 0.985077 | 0.890352 |
| 9 | 下腔静脉 | 0.923898 | 0.923908 | 0.933244 | 0.933255 | 0.897143 | 0.933227 | 0.912817 |
| 10 | 胰腺 | 0.899112 | 0.899086 | 0.888885 | 0.888910 | 0.850866 | 0.888887 | 0.806389 |
| 11 | 右肾上腺 | 0.851592 | 0.851822 | 0.883697 | 0.883697 | 0.866420 | 0.883697 | 0.924658 |
| 12 | 左肾上腺 | 0.815983 | 0.815983 | 0.858547 | 0.858371 | 0.852301 | 0.858371 | 0.870446 |
| 13 | 十二指肠 | 0.891081 | 0.891079 | 0.871085 | 0.871116 | 0.789567 | 0.871101 | 0.673730 |
| 14 | 膀胱 | N/A | N/A | N/A | N/A | 0.000000 | N/A | N/A |
| 15 | 前列腺/子宫 | N/A | N/A | N/A | N/A | 0.000000 | N/A | N/A |

## Old Acceptance Details

Run: `acceptance-real-20260524-194750`, job `32dfe3117b40`

| Label | Organ | Dice | Pred voxels | Ref voxels |
|---:|---|---:|---:|---:|
| 1 | 脾脏 | 0.979075 | 200907 | 202345 |
| 2 | 右肾 | 0.978732 | 107369 | 106851 |
| 3 | 左肾 | 0.985639 | 111167 | 113191 |
| 4 | 胆囊 | 0.950326 | 30239 | 29048 |
| 5 | 食管 | 0.793738 | 30931 | 33395 |
| 6 | 肝脏 | 0.984248 | 967171 | 986422 |
| 7 | 胃 | 0.555910 | 20838 | 44133 |
| 8 | 主动脉 | 0.977634 | 187095 | 187440 |
| 9 | 下腔静脉 | 0.923898 | 53805 | 54077 |
| 10 | 胰腺 | 0.899112 | 58764 | 59991 |
| 11 | 右肾上腺 | 0.851592 | 1851 | 1855 |
| 12 | 左肾上腺 | 0.815983 | 2362 | 2393 |
| 13 | 十二指肠 | 0.891081 | 47882 | 47914 |
| 14 | 膀胱 | N/A | 0 | 0 |
| 15 | 前列腺/子宫 | N/A | 0 | 0 |

## Old Persistent Details

Run: `perf-persistent-20260524-200515`, job `a4b3806cfe1f`

| Label | Organ | Dice | Pred voxels | Ref voxels |
|---:|---|---:|---:|---:|
| 1 | 脾脏 | 0.979085 | 200911 | 202345 |
| 2 | 右肾 | 0.978704 | 107369 | 106851 |
| 3 | 左肾 | 0.985648 | 111163 | 113191 |
| 4 | 胆囊 | 0.950342 | 30238 | 29048 |
| 5 | 食管 | 0.793725 | 30927 | 33395 |
| 6 | 肝脏 | 0.984249 | 967173 | 986422 |
| 7 | 胃 | 0.555985 | 20840 | 44133 |
| 8 | 主动脉 | 0.977631 | 187096 | 187440 |
| 9 | 下腔静脉 | 0.923908 | 53806 | 54077 |
| 10 | 胰腺 | 0.899086 | 58763 | 59991 |
| 11 | 右肾上腺 | 0.851822 | 1850 | 1855 |
| 12 | 左肾上腺 | 0.815983 | 2362 | 2393 |
| 13 | 十二指肠 | 0.891079 | 47880 | 47914 |
| 14 | 膀胱 | N/A | 0 | 0 |
| 15 | 前列腺/子宫 | N/A | 0 | 0 |

## New Weight Details

Run: `segmentation-metrics-new-weight-20260524-2215`, job `27216eb73220`

| Label | Organ | Dice | IoU | HD mm | Pred voxels | Ref voxels |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 脾脏 | 0.985234 | 0.970898 | 5.025721 | 201624 | 202345 |
| 2 | 右肾 | 0.982296 | 0.965208 | 7.090247 | 108355 | 106851 |
| 3 | 左肾 | 0.987893 | 0.976075 | 5.000000 | 111878 | 113191 |
| 4 | 胆囊 | 0.953659 | 0.911423 | 5.000000 | 30705 | 29048 |
| 5 | 食管 | 0.857557 | 0.750634 | 6.774050 | 28728 | 33395 |
| 6 | 肝脏 | 0.988545 | 0.977349 | 10.757801 | 980121 | 986422 |
| 7 | 胃 | 0.846551 | 0.733930 | 16.562684 | 37060 | 44133 |
| 8 | 主动脉 | 0.985093 | 0.970624 | 5.103452 | 190707 | 187440 |
| 9 | 下腔静脉 | 0.933244 | 0.874843 | 5.000000 | 57763 | 54077 |
| 10 | 胰腺 | 0.888885 | 0.799994 | 10.166236 | 66473 | 59991 |
| 11 | 右肾上腺 | 0.883697 | 0.791627 | 5.000000 | 1954 | 1855 |
| 12 | 左肾上腺 | 0.858547 | 0.752152 | 8.140854 | 2492 | 2393 |
| 13 | 十二指肠 | 0.871085 | 0.771613 | 10.687574 | 44589 | 47914 |
| 14 | 膀胱 | N/A | N/A | N/A | 0 | 0 |
| 15 | 前列腺/子宫 | N/A | N/A | N/A | 0 | 0 |

## Warm No-cache Details

Run: `segmentation-metrics-warm-timeout-20260524-2257`, job `685426290aa4`

| Label | Organ | Dice | IoU | HD mm | Pred voxels | Ref voxels |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 脾脏 | 0.985251 | 0.970932 | 5.025721 | 201627 | 202345 |
| 2 | 右肾 | 0.982287 | 0.965190 | 7.090247 | 108355 | 106851 |
| 3 | 左肾 | 0.987893 | 0.976075 | 5.000000 | 111878 | 113191 |
| 4 | 胆囊 | 0.953696 | 0.911490 | 5.000000 | 30709 | 29048 |
| 5 | 食管 | 0.857525 | 0.750585 | 6.774050 | 28728 | 33395 |
| 6 | 肝脏 | 0.988547 | 0.977354 | 10.757801 | 980116 | 986422 |
| 7 | 胃 | 0.846540 | 0.733914 | 16.562684 | 37061 | 44133 |
| 8 | 主动脉 | 0.985077 | 0.970594 | 5.103452 | 190711 | 187440 |
| 9 | 下腔静脉 | 0.933255 | 0.874862 | 5.000000 | 57766 | 54077 |
| 10 | 胰腺 | 0.888910 | 0.800034 | 10.166236 | 66474 | 59991 |
| 11 | 右肾上腺 | 0.883697 | 0.791627 | 5.000000 | 1954 | 1855 |
| 12 | 左肾上腺 | 0.858371 | 0.751882 | 8.140854 | 2493 | 2393 |
| 13 | 十二指肠 | 0.871116 | 0.771662 | 10.687574 | 44588 | 47914 |
| 14 | 膀胱 | N/A | N/A | N/A | 0 | 0 |
| 15 | 前列腺/子宫 | N/A | N/A | N/A | 0 | 0 |

## Fast Profile Details

Run: `segmentation-metrics-fast-profile-20260525-1312`, job `6802e01f1a73`

| Label | Organ | Dice | IoU | HD mm | Pred voxels | Ref voxels |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 脾脏 | 0.982458 | 0.965522 | 6.423376 | 202407 | 202345 |
| 2 | 右肾 | 0.980218 | 0.961203 | 6.218303 | 108695 | 106851 |
| 3 | 左肾 | 0.985947 | 0.972283 | 5.000000 | 112093 | 113191 |
| 4 | 胆囊 | 0.950942 | 0.906473 | 5.000000 | 30127 | 29048 |
| 5 | 食管 | 0.808644 | 0.678759 | 7.393862 | 26347 | 33395 |
| 6 | 肝脏 | 0.985892 | 0.972176 | 10.805636 | 978790 | 986422 |
| 7 | 胃 | 0.726965 | 0.571049 | 24.616009 | 29180 | 44133 |
| 8 | 主动脉 | 0.981288 | 0.963264 | 5.630694 | 187508 | 187440 |
| 9 | 下腔静脉 | 0.897143 | 0.813472 | 10.025754 | 52294 | 54077 |
| 10 | 胰腺 | 0.850866 | 0.740441 | 18.369346 | 64407 | 59991 |
| 11 | 右肾上腺 | 0.866420 | 0.764322 | 5.000000 | 1933 | 1855 |
| 12 | 左肾上腺 | 0.852301 | 0.742618 | 8.632812 | 2387 | 2393 |
| 13 | 十二指肠 | 0.789567 | 0.652301 | 20.550959 | 40304 | 47914 |
| 14 | 膀胱 | 0.000000 | 0.000000 | N/A | 664 | 0 |
| 15 | 前列腺/子宫 | 0.000000 | 0.000000 | N/A | 670 | 0 |

## Quality Profile Details

Run: `segmentation-metrics-quality-profile-20260525-1433`, job `b3c528cc9e20`

| Label | Organ | Dice | IoU | HD mm | Pred voxels | Ref voxels |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 脾脏 | 0.985242 | 0.970912 | 5.025721 | 201627 | 202345 |
| 2 | 右肾 | 0.982291 | 0.965199 | 7.090247 | 108354 | 106851 |
| 3 | 左肾 | 0.987897 | 0.976084 | 5.000000 | 111879 | 113191 |
| 4 | 胆囊 | 0.953681 | 0.911464 | 5.000000 | 30712 | 29048 |
| 5 | 食管 | 0.857552 | 0.750627 | 6.774050 | 28726 | 33395 |
| 6 | 肝脏 | 0.988546 | 0.977351 | 10.757801 | 980113 | 986422 |
| 7 | 胃 | 0.846569 | 0.733957 | 16.562684 | 37063 | 44133 |
| 8 | 主动脉 | 0.985077 | 0.970593 | 5.103452 | 190709 | 187440 |
| 9 | 下腔静脉 | 0.933227 | 0.874814 | 5.000000 | 57765 | 54077 |
| 10 | 胰腺 | 0.888887 | 0.799997 | 10.166236 | 66475 | 59991 |
| 11 | 右肾上腺 | 0.883697 | 0.791627 | 5.000000 | 1954 | 1855 |
| 12 | 左肾上腺 | 0.858371 | 0.751882 | 8.140854 | 2493 | 2393 |
| 13 | 十二指肠 | 0.871101 | 0.771638 | 10.687574 | 44585 | 47914 |
| 14 | 膀胱 | N/A | N/A | N/A | 0 | 0 |
| 15 | 前列腺/子宫 | N/A | N/A | N/A | 0 | 0 |

## FLARE22 Tr 0009 Remap Details

Run: `flare22-tr-0009-quality-20260526`, job `86b0153d0a73`

| Label | Organ | Dice | IoU | HD mm | Pred voxels | Ref voxels |
|---:|---|---:|---:|---:|---:|---:|
| 1 | 脾脏 | 0.965952 | 0.934146 | 5.064649 | 94799 | 90086 |
| 2 | 右肾 | 0.945245 | 0.896175 | 12.998884 | 108115 | 118275 |
| 3 | 左肾 | 0.947873 | 0.900911 | 11.618134 | 109927 | 119435 |
| 4 | 胆囊 | 0.949364 | 0.903608 | 3.325866 | 17026 | 17159 |
| 5 | 食管 | 0.808989 | 0.679245 | 13.367029 | 5415 | 7312 |
| 6 | 肝脏 | 0.968961 | 0.939790 | 20.269804 | 997417 | 951329 |
| 7 | 胃 | 0.945877 | 0.897313 | 8.815001 | 99001 | 95650 |
| 8 | 主动脉 | 0.890352 | 0.802374 | 13.957965 | 86261 | 102936 |
| 9 | 下腔静脉 | 0.912817 | 0.839616 | 15.532763 | 59206 | 51331 |
| 10 | 胰腺 | 0.806389 | 0.675587 | 13.962242 | 74761 | 107062 |
| 11 | 右肾上腺 | 0.924658 | 0.859873 | 2.747970 | 2466 | 2498 |
| 12 | 左肾上腺 | 0.870446 | 0.770610 | 4.033205 | 3302 | 3807 |
| 13 | 十二指肠 | 0.673730 | 0.507989 | 38.043429 | 36940 | 45927 |
| 14 | 膀胱 | N/A | N/A | N/A | 0 | 0 |
| 15 | 前列腺/子宫 | N/A | N/A | N/A | 0 | 0 |

## Interpretation

- The new checkpoint is the main historical improvement. The weakest AMOS label changed from stomach Dice about `0.556` in the old runs to about `0.8465` in the new weight and quality runs.
- The quality profile should remain the baseline for formal reporting. It reproduces the new-weight metrics closely and avoids the label 14/15 false positives seen in fast mode.
- The fast profile is useful for speed-sensitive preview work. It reduced runtime from `1360.398s` to `384.345s`, but lowered mean Dice from `0.924780` to `0.777243` and introduced bladder/prostate-or-uterus false positives.
- FLARE22 Tr 0009 remap shows useful cross-dataset behavior, but the taxonomy remap and missing labels mean it is not equivalent to native AMOS validation. Its weakest labels were duodenum, pancreas, and esophagus.

## 2026-05-26 Audit Notes

- Reviewed this comparison against `SEGMENTATION_METRICS_SUMMARY.md` and `REVIEW.md`; the shared numeric values and interpretation boundaries are aligned.
- `quality profile b3c528cc9e20` remains the formal AMOS baseline.
- `flare22-tr-0009-quality-20260526` remains cross-dataset evidence only. It uses an offline organ-name remap into AMOS label IDs and must not be mixed into native AMOS validation tables.
- `fast profile 6802e01f1a73` remains a preview/demo option only because it introduced label 14/15 false positives and lower aggregate quality.

## Recommended Baselines

| Purpose | Recommended run | Reason |
|---|---|---|
| Formal AMOS report | quality profile `b3c528cc9e20` | Highest stable AMOS validation profile with full metrics and no label 14/15 false positives. |
| Historical model comparison | old persistent vs quality profile | Shows the major gain from the old model/process to the current quality baseline. |
| Demo / quick preview | fast profile `6802e01f1a73` | Much faster, but must be labeled as review-only. |
| Cross-dataset evidence | FLARE22 remap `86b0153d0a73` | Useful for external organ-name-aligned checking, not for native AMOS score claims. |
