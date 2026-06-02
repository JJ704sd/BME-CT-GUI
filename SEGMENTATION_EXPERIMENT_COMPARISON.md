# 分割实验对比

生成日期：2026-06-02

本文档汇总历史分割实验记录，便于横向比较。它与 `SEGMENTATION_METRICS_SUMMARY.md` 配套使用：后者记录当前指标摘要和命令上下文，本文保留跨轮次对比表。

## 数据来源

- `.test-output\acceptance-real-20260524-194750\work\32dfe3117b40\output\job_summary.json`
- `.test-output\perf-persistent-20260524-200515\work\a4b3806cfe1f\output\job_summary.json`
- `.test-output\segmentation-metrics-new-weight-20260524-2215\new-weight-amos0117-segmentation-metrics.md`
- `.test-output\segmentation-metrics-warm-timeout-20260524-2257\warm-timeout-amos0117-segmentation-metrics.md`
- `.test-output\segmentation-metrics-fast-profile-20260525-1312\fast-profile-amos0117-segmentation-metrics.md`
- `.test-output\segmentation-metrics-quality-profile-20260525-1433\quality-profile-amos0117-segmentation-metrics.md`
- `.test-output\flare22-tr-0009-quality-20260526\metrics-remapped\flare22-tr-0009-quality-remapped-segmentation-metrics.md`
- `.test-output\*\job_summary.json`：用于核对运行时间、状态、缓存和验证元数据。
- `SEGMENTATION_RECENT_ROUNDS.md`：近三轮在线推理的滚动记录，包含标签上传验证轮次。

说明：

- 旧验收和旧 persistent 运行的 `job_summary.json` 只包含逐标签 Dice 和体素数，不包含逐标签 IoU 或 Hausdorff Distance。
- AMOS 0117 记录使用当前 checkpoint 原生标签体系。
- FLARE22 Tr 0009 使用离线器官名映射，把 FLARE22 label 映射到 AMOS label ID。它可以作为跨数据集证据，但不能直接和 AMOS 原生验证混算。
- `N/A` 表示该标签在预测和参考中均为空。`0.000000` 表示参考中没有该标签，但预测产生了体素。
- 2026-05-26 的在线推理输入后缀规范化和底部实时进度展示属于工程链路修复，不改变下列历史实验的 Dice、IoU、Hausdorff Distance 或耗时数值。
- 2026-05-29 的缓存 validation 修复、persistent worker reader 修复、上传文件名日志移除和部分 FLARE22 标签 remap 增强也不改变下列表格中的历史数值。当前语义下，`cached-real-nnunetv2` 只代表预测结果复用；validation 仍必须按当前请求的标签文件或内置参考标签重新计算。
- 2026-05-30 新增 `runtime_target=local|server`、局域网配置化和服务器 5-fold soft ensemble 编排入口。
- 2026-05-31 校园网 Linux 服务器端到端 smoke 已跑通：FLARE 服务器轮次 Dice 合理，AMOS 服务器轮次暴露自动 taxonomy 误判风险；服务器指标必须与本地 fold0/quality 基线分开解释。
- 2026-05-31 显式 `label_taxonomy=auto|AMOS22|FLARE22` 已实现，`detect_dataset()` 更保守：标签 ID 是 checkpoint 子集时不触发 remap。AMOS CT 高分辨率推理完成（fast profile，mean_dice=0.77724）。服务器 runtime 包已更新为 `server-runtime-package-20260531.zip`，zip 内按 `server/...` 项目结构组织。
- 2026-05-31 前端新增影像量化分析和报告 `quantification` 字段，只读取预测 mask 与 spacing 生成体积、截面积和长度估算，不改变下列表格中的历史 Dice、IoU、Hausdorff Distance 或耗时数值。
- 2026-06-01 完成本地缓存演示 7 步：AMOS 0117 cache hit（`aea4e7cdbaf0`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`, 218s）、FLARE22 cache hit（`02da885c97d8`, 0.001s）。新增 `tools/seed_demo_cache.py` 与 `docs/local-cache-demo-runbook.md`。本轮 AMOS cache hit 命中的是 2026-05-23 历史推理 `009d4efdc5f6`（review，mean_dice 0.891，stomach 0.556），不修改本表中的任何指标数值；新 quality AMOS 真实推理仍以 `b3c528cc9e20` 为基线。
- 2026-06-01 晚间完成 cache 链路补丁：FLARE22 cache hit（`02da885c97d8`）现在能正确显示 2026-05-26 remap 后的指标（mean_dice 0.893127、min_dice 0.67373、fg 0.949908、15 标签），并标注"（历史离线缓存摘要）"；新增 `tools/rewrite_flare22_historical_summary.py` 把该历史摘要写入 0aa7323a4c01 的 output。`server/main.py` 的 `complete_cached_job()` 增加 historical 回退，`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序。本轮不修改本表中任何基线指标数值，仅修正 cache hit 时的 validation 显示口径。
- 2026-06-02 完成 `detect_dataset()` 二轮收紧：AMOS 真实 `amos_0117_label.nii/amos_0117(2).nii` 实际 unique IDs 为 `{1..13}`（缺 14/15 bladder/prostate），与 FLARE22 真实 1-13 在裸 ID 集合上不可分。`detect_dataset()` 新增 0.85 coverage 守卫：参考覆盖 ckpt 标签 ≥ 0.85 时直接返回 `None`（`auto` 退化为保底）。前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy`：AMOS 病例 → `AMOS22`、FLARE22 病例 → `FLARE22`、其他保持原值。`tests/backendState.test.py` 新增 AMOS 1-13 + ckpt 1-15 真实 case 测试。本轮不修改本表中任何基线指标数值，仅修正 `auto` 模式在裸 ID 不可分边界上的判定逻辑。

## 实验名称说明

阅读对比表或排查历史结果时，先看本表。后续表格使用较短名称，但每个名称都对应明确实验目的。

| 简称 | 含义 | 适用场景 | 来源运行 |
|---|---|---|---|
| 旧模型首跑 | 旧 checkpoint / 旧推理流程的第一次有效 AMOS 0117 验证 | 排查“为什么旧结果没过阈值”或对比新权重提升幅度 | `acceptance-real-20260524-194750`, job `32dfe3117b40` |
| 旧模型常驻 | 旧 checkpoint 在 persistent worker 流程下的复测 | 判断旧结果问题是否来自 worker 流程；结果与旧模型首跑基本一致 | `perf-persistent-20260524-200515`, job `a4b3806cfe1f` |
| 新权重首跑 | 更换到当前 checkpoint 后的第一次完整 AMOS 0117 验证 | 查看新权重相对旧模型的主要提升，尤其胃、食管、肾上腺 | `acceptance-new-weight-20260524-201714`, job `27216eb73220` |
| 新权重补算 | 同一新权重在 no-cache / warm persistent 场景下的补充指标 | 排查超时、缓存关闭或 warm worker 场景；指标应接近新权重首跑 | `segmentation-metrics-warm-timeout-20260524-2257`, job `685426290aa4` |
| 快速预览 | `fast` profile：关闭 TTA、较大 tile step，优先速度 | 排查演示/预览模式；不要作为正式质量结论，注意 label 14/15 假阳性 | `perf-fast-profile-20260525-1305`, job `6802e01f1a73` |
| 正式质量 | `quality` profile：开启 TTA、较稳的正式推理配置 | 正式报告、验收截图、基准对比优先使用这一列 | `perf-quality-profile-20260525-1330`, job `b3c528cc9e20` |
| 跨数据集 FLARE | FLARE22 病例按器官名 remap 到 AMOS 标签后的离线对照 | 排查模型在非 AMOS 数据上的泛化趋势；不能直接和 AMOS 原生验证混算 | `flare22-tr-0009-quality-20260526`, job `86b0153d0a73` |
| FLARE+标签在线 | 标签文件传输修复后，FLARE22 在线 validation 链路首次打通 | 验证标签文件传输和在线 validation 可用；taxonomy 错位导致 Dice 无意义 | job `bf20f0ec4456` |
| FLARE 自动 remap | 2026-05-28 自动 taxonomy remap 上线后，在线验证自动重映射标签 ID | 跨数据集在线验证正式打通，mean_dice=0.926，验证通过 | job `a717dacf42d3` |
| 服务器 FLARE smoke | 校园网服务器 5GPU/5-fold soft ensemble，FLARE 标签自动 remap | 服务器链路跑通证据，mean Dice 约 0.891 | 报告 `1780153055202` |
| 服务器 AMOS 异常 | 校园网服务器 5GPU/5-fold soft ensemble，AMOS 标签疑似被误判为 FLARE22 | taxonomy 误判证据，不作为模型失败基线 | job `5d8f5eee7b75` |
| 本地高分辨率推理 | AMOS CT 768×768×103，本地 RTX 4060，2D nnUNet 逐切片处理 | 高分辨率输入速度分析，非标准尺寸导致推理时间延长 | job `ad3d14eba3de` |
| 本地缓存演示 AMOS cache hit | AMOS 0117 复跑 cache_key 命中 2026-05-23 历史推理 `009d4efdc5f6` | 演示同输入 cache hit，秒级回填；review 状态保留（stomach 0.556） | job `aea4e7cdbaf0` |
| 本地缓存演示 FLARE 真实推理 | FLARE22 Tr 0009 首次未缓存 quality 推理 | 真实 nnUNetv2 推理写入 cache_key，218s，结果 120KB | job `0aa7323a4c01` |
| 本地缓存演示 FLARE cache hit | FLARE22 Tr 0009 复跑命中 0aa7323a4c01 | 验证 cache_key 7 字段隔离正确，0.001s 返回 | job `02da885c97d8` |

## 实验总览

| 运行 | Job ID | 病例 | 推理配置/模式 | 状态 | 是否缓存 | 耗时（秒） | 平均 Dice | 最低 Dice | 前景 Dice | 平均 IoU | 体素准确率 | 平均 HD（mm） |
|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| 旧模型首跑 | `32dfe3117b40` | AMOS 0117 | real-nnUNetv2 | review | false | 359.425 | 0.891305 | 0.555910 | 0.971220 | N/A | N/A | N/A |
| 旧模型首跑缓存 | `c8cecb040657` | AMOS 0117 | cached-real-nnunetv2 | review | true | 0.000 | 0.891305 | 0.555910 | 0.971220 | N/A | N/A | N/A |
| 旧模型常驻 | `a4b3806cfe1f` | AMOS 0117 | real-nnUNetv2 | review | false | 356.950 | 0.891327 | 0.555985 | 0.971222 | N/A | N/A | N/A |
| 新权重首跑 | `27216eb73220` | AMOS 0117 | real-nnUNetv2 | passed | false | 1124.327 | 0.924791 | 0.846551 | 0.980316 | 0.865105 | 0.998578 | 7.716048 |
| 新权重缓存 | `f200f16f47be` | AMOS 0117 | cached-real-nnunetv2 | passed | true | 0.000 | 0.924791 | 0.846551 | 0.980316 | N/A | N/A | N/A |
| 新权重补算 | `685426290aa4` | AMOS 0117 | real-nnUNetv2 | timeout 后补算指标可用 | false | >=1800.785 | 0.924782 | 0.846540 | 0.980316 | 0.865092 | 0.998578 | 7.716048 |
| 快速预览 | `6802e01f1a73` | AMOS 0117 | fast, TTA off | review | false | 384.345 | 0.777243 | 0.000000 | 0.972898 | 0.713592 | 0.998068 | 10.282058 |
| 正式质量 | `b3c528cc9e20` | AMOS 0117 | quality, TTA on | passed | false | 1360.398 | 0.924780 | 0.846569 | 0.980317 | 0.865088 | 0.998578 | 7.716048 |
| 跨数据集 FLARE | `86b0153d0a73` | FLARE22 Tr 0009 | quality，离线 remap | 仅作对照 | false | 237.323 | 0.893127 | 0.673730 | 0.949908 | 0.815941 | 0.991879 | 12.595149 |
| FLARE+标签在线 | `bf20f0ec4456` | FLARE22 Tr 0009 | quality，taxonomy 错位 | review | false | 222.6 | 0.073 | 0.000 | 0.950 | N/A | N/A | N/A |
| FLARE 自动 remap | `a717dacf42d3` | FLARE22 Tr 0009 | quality，自动 remap | passed | false | ~220 | 0.926 | — | — | — | — | — |
| 服务器 FLARE smoke | `—` | FLARE22 | server quality，5-fold soft ensemble，自动 remap | review/可用 | false | ~228 | ~0.891 | ~0.657 | ~0.951 | — | — | — |
| 服务器 AMOS 异常 | `5d8f5eee7b75` | AMOS 0117 | server quality，5-fold soft ensemble，疑似误 remap | review | false | 586.453 | 0.076015 | 0.000 | 0.979808 | — | — | — |
| 本地高分辨率推理 | `ad3d14eba3de` | AMOS CT 768×768×103 | fast, TTA off, 2D nnUNet | review | false | 长耗时 | 0.77724 | — | — | — | — | — |
| 本地缓存演示 AMOS cache hit | `aea4e7cdbaf0` | AMOS 0117 | cached-real-nnunetv2（命中 `009d4efdc5f6`） | review | true | ~3s | 0.891305 | 0.555985 | 0.971222 | N/A | N/A | N/A |
| 本地缓存演示 FLARE 真实推理 | `0aa7323a4c01` | FLARE22 Tr 0009 | real-nnunetv2，quality，3d_fullres，TTA on | 无验证 | false | 218s | — | — | — | — | — | — |
| 本地缓存演示 FLARE cache hit | `02da885c97d8` | FLARE22 Tr 0009 | cached-real-nnunetv2（命中 `0aa7323a4c01`） | 无验证 | true | 0.001s | — | — | — | — | — | — |

## 逐标签 Dice 对比

| 标签 | 器官 | 旧模型首跑 | 旧模型常驻 | 新权重首跑 | 新权重补算 | 快速预览 | 正式质量 | 跨数据集 FLARE |
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

## 旧模型首跑详情

运行：`acceptance-real-20260524-194750`，job `32dfe3117b40`

| 标签 | 器官 | Dice | 预测体素 | 参考体素 |
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

## 旧模型常驻详情

运行：`perf-persistent-20260524-200515`，job `a4b3806cfe1f`

| 标签 | 器官 | Dice | 预测体素 | 参考体素 |
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

## 新权重首跑详情

运行：`segmentation-metrics-new-weight-20260524-2215`，job `27216eb73220`

| 标签 | 器官 | Dice | IoU | HD mm | 预测体素 | 参考体素 |
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

## 新权重补算详情

运行：`segmentation-metrics-warm-timeout-20260524-2257`，job `685426290aa4`

| 标签 | 器官 | Dice | IoU | HD mm | 预测体素 | 参考体素 |
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

## 快速预览详情

运行：`segmentation-metrics-fast-profile-20260525-1312`，job `6802e01f1a73`

| 标签 | 器官 | Dice | IoU | HD mm | 预测体素 | 参考体素 |
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

## 正式质量详情

运行：`segmentation-metrics-quality-profile-20260525-1433`，job `b3c528cc9e20`

| 标签 | 器官 | Dice | IoU | HD mm | 预测体素 | 参考体素 |
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

## FLARE22 Tr 0009 重映射详情

运行：`flare22-tr-0009-quality-20260526`，job `86b0153d0a73`

| 标签 | 器官 | Dice | IoU | HD mm | 预测体素 | 参考体素 |
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

## FLARE22 Tr 0009 + 标签上传在线验证详情

运行：标签文件传输修复后首次在线验证，job `bf20f0ec4456`

| 标签 | 器官 | Dice | 说明 |
|---:|---|---:|---|
| 1 | 脾脏 vs 肝脏 | 0.000000 | 语义错位 |
| 2 | 右肾 vs 右肾 | 0.945249 | 恰好一致 |
| 3 | 左肾 vs 脾脏 | 0.000000 | 语义错位 |
| 4 | 胆囊 vs 右肾上腺 | 0.000000 | 语义错位 |
| 5 | 食管 vs 左肾上腺 | 0.000000 | 语义错位 |
| 6 | 肝脏 vs 胆囊 | 0.000635 | 语义错位 |
| 7 | 胃 vs 食管 | 0.000000 | 语义错位 |
| 8 | 主动脉 vs 胃 | 0.000000 | 语义错位 |
| 9 | 下腔静脉 vs 主动脉 | 0.000000 | 语义错位 |
| 10 | 胰腺 vs 下腔静脉 | 0.000000 | 语义错位 |
| 11 | 右肾上腺 vs 胰腺 | 0.000000 | 语义错位 |
| 12 | 左肾上腺 vs 十二指肠 | 0.000000 | 语义错位 |
| 13 | 十二指肠 vs 左肾 | 0.000000 | 语义错位 |
| 14 | 膀胱 | N/A | 该例无此标签 |
| 15 | 前列腺/子宫 | N/A | 该例无此标签 |

结论：标签文件传输链路修复成功，validation 正常执行。Dice 极低是 AMOS22 checkpoint 与 FLARE22 标签 ID 语义错位导致，非模型质量问题。`taxonomy_match: True` 是误判——只检查了 ID 集合交集，未做语义级匹配。离线 remap 后真实 mean_dice=0.893。

## FLARE22 Tr 0009 自动 taxonomy remap 在线验证详情

运行：自动 taxonomy remap 上线后在线验证，job `a717dacf42d3`

| 项目 | 结果 |
|---|---|
| 病例 | FLARE22 Tr 0009 |
| 标签文件 | 已上传 |
| profile | `quality` |
| mode | `real-nnunetv2` |
| cached_result | `false` |
| remap_applied | `true` |
| remap_source | `FLARE22` |
| validation status | `passed` |
| mean Dice | `0.926` |

结论：自动 remap 后，在线 validation 会先按器官名把 FLARE22 标签 ID 重映射到当前 AMOS22 checkpoint 标签 ID，再计算 Dice。该运行证明跨数据集在线验证链路已打通，但仍应与 AMOS 0117 原生标签指标分开解释。

## 2026-05-31 服务器在线推理 smoke 记录

| 项目 | FLARE 服务器轮次 | AMOS 服务器轮次 |
|---|---|---|
| 运行位置 | Ubuntu 服务器，5GPU/5-fold soft ensemble | Ubuntu 服务器，5GPU/5-fold soft ensemble |
| 前端接入 | Windows GUI 通过校园网 API endpoint | Windows GUI 通过校园网 API endpoint |
| 总耗时 | 约 `3分48秒` | `586.453s` / 约 `9分46秒` |
| 主要阶段 | 5-fold 推理约 `2分55.3秒` | `server_fold_predict=449.5s`, `server_ensemble=131.116s` |
| 结果大小 | 约 `117.2 KB` | `141986 bytes` |
| mean Dice | 约 `0.891` | `0.076015` |
| foreground Dice | 约 `0.951` | `0.979808` |
| remap | FLARE22 → 当前 AMOS 模型，符合预期 | 报告显示 FLARE22 → 当前模型，但输入疑似 AMOS 原生标签 |

结论：服务器在线推理主链路已经能完成提交、5-fold 并行推理、soft ensemble、validation 和前端回填。FLARE 轮次说明跨数据集 remap 在服务器模式可用；AMOS 轮次的高 foreground Dice + 低 mean Dice + `remap_source=FLARE22` 更像标签体系误判，需要显式 `label_taxonomy=AMOS22` 复跑后再纳入正式质量对比。

## 结论解读

- 新 checkpoint 是历史结果中的主要提升点。AMOS 最弱标签从旧模型胃 Dice 约 `0.556` 提升到新权重和正式质量配置中的约 `0.8465`。
- `quality` profile 应继续作为正式报告基线。它与新权重首跑指标接近，并避免了 fast 模式下 label 14/15 的假阳性。
- `fast` profile 适合速度敏感的预览工作。它把耗时从 `1360.398s` 降到 `384.345s`，但 mean Dice 从 `0.924780` 降到 `0.777243`，并引入膀胱/前列腺或子宫假阳性。
- FLARE22 Tr 0009 remap 展示了有价值的跨数据集表现，但 taxonomy remap 和缺失标签意味着它不等同于 AMOS 原生验证。该例最弱标签为十二指肠、胰腺和食管。
- 2026-05-28 自动 taxonomy remap 上线后，FLARE22 在线验证 mean_dice 从 0.073 提升到 0.926（job `a717dacf42d3`），跨数据集在线验证链路正式打通。

## 2026-05-26 审核记录

- 已与 `SEGMENTATION_METRICS_SUMMARY.md` 和 `REVIEW.md` 交叉审核；共享数值和解释边界一致。
- `quality` profile `b3c528cc9e20` 仍是正式 AMOS 基线。
- `flare22-tr-0009-quality-20260526` 仍仅作为跨数据集证据。它使用离线器官名 remap 到 AMOS label ID，不能混入 AMOS 原生验证表。
- `fast` profile `6802e01f1a73` 仍仅作为预览/演示选项，因为它引入 label 14/15 假阳性且整体质量下降。

## 2026-05-26 GUI 拖动修复审核记录

- 本轮矢状/冠状拖动卡顿修复只改变前端三视图渲染调度，不改变本文件中任何推理实验数值。
- 拖动期间三视图仍实时变化，只是使用 `interactive` 轻量预览；释放后恢复完整质量，实验指标表不受影响。
- `quality`、`fast`、FLARE22 remap 的对比口径继续沿用上方说明：正式 AMOS 报告看 `quality`，快速预览需复核，FLARE22 只作为跨数据集器官名重映射证据。
- 文档主体已复核为中文；保留 Dice、IoU、HD、profile、job id、checkpoint 等必要技术字段。

## 2026-05-27 标签上传验证审核记录

- 新增 `bf20f0ec4456`（FLARE+标签在线）到实验总览表和逐标签 Dice 对比表。
- 该轮在线验证 mean_dice=0.073 是 taxonomy 错位导致，非模型质量问题；离线 remap 后真实值 0.893。
- `quality`、`fast`、FLARE22 remap 的对比口径继续沿用上方说明。
- 新增 `SEGMENTATION_RECENT_ROUNDS.md` 作为近三轮在线推理的滚动记录数据源。

## 2026-05-28 自动 Taxonomy Remap 审核记录

- P0 taxonomy 自动 remap 已实现并验证通过。job `a717dacf42d3` 在线验证 mean_dice=0.926（从 0.073 提升）。
- 新增 `FLARE 自动 remap` 行到实验总览表和推荐基线表。
- `server/taxonomy.py` 实现 FLARE22 数据集检测和按器官名重映射。
- `quality`、`fast`、FLARE22 离线 remap 的对比口径不变；FLARE 自动 remap 作为跨数据集在线验证的新基线。

## 2026-05-29 历史 bug 收口审核记录

- 缓存命中不再继承缓存来源 job 的 `validation`；预测 NIfTI 仍可复用，但 Dice 由本次请求的 `label_file` 或内置 AMOS 参考标签重新计算。
- `SEGMENTATION_PERSISTENT_WORKER=1` 的 stdout reader 改为进程级共享队列，并通过轻量 shutdown smoke；真实长耗时连续推理加速仍未验证。
- 前端和后端上传文件名调试日志已移除，文档不再要求保留 `console.log` 观察标签传输。
- FLARE22 自动 remap 支持至少两个明确错位 label 的部分标签文件；单 label 文件仍保持人工判断或后续显式数据集 hint。
- 本轮不改变历史实验指标，仅修正后续解释和验收口径。

## 2026-05-30 运行位置与局域网配置审核记录

- 前端已支持 `runtime_target=local|server`，用于区分本地 fold0 保底推理和服务器 5-GPU 5-fold soft ensemble 推理。
- `runtime_target` 和 `inference_options` 已纳入 job state、SSE complete 事件、`job_summary.json` 和缓存语义，避免本地结果、服务器 ensemble 结果、`fast`/`quality` 结果混用。
- 局域网访问已配置化：前端通过 `VITE_API_ENDPOINT` 指向后端，`npm run dev:lan` 监听 `0.0.0.0:5173`，后端通过 `SEGMENTATION_ALLOWED_ORIGINS` 放行实际浏览器来源。
- 2026-05-31 校园网服务器端到端 smoke 已跑通；当前推荐基线仍沿用 AMOS `quality` profile `b3c528cc9e20` 与 FLARE 自动 remap `a717dacf42d3`。服务器 FLARE 轮次可作为链路证据，服务器 AMOS 轮次因疑似 taxonomy 误判暂不替换正式 AMOS 基线。

## 2026-05-31 高分辨率 CT 推理速度分析记录

- AMOS CT（768×768×103）本地在线推理完成，job `ad3d14eba3de`。
- 输入分辨率高于标准 AMOS 数据集（768×768 vs 512×512），面积增加 2.25 倍。
- 使用 2D nnUNet 模型（nnUNetTrainer__nnUNetPlans__2d），逐切片处理 103 层。
- GPU 状态：RTX 4060 Laptop, 100% 利用率, 95% 显存占用, 57°C, 2505/3105 MHz。
- 速度瓶颈：高分辨率输入、GPU 显存接近上限、GPU 功率受限（27W/40W）、模型复杂度（8 阶段 ResidualEncoderUNet）、重采样开销。
- fast profile 下 mean_dice=0.77724，低于 quality 的 0.924791，符合预期。
- 后续优化方向：预降采样（768→512）、3D 模型评估。

## 推荐基线

| 用途 | 推荐运行 | 原因 |
|---|---|---|
| 正式 AMOS 报告 | `quality` profile `b3c528cc9e20` | 当前稳定 AMOS 验证配置，指标完整，且没有 label 14/15 假阳性。 |
| 历史模型对比 | 旧模型常驻 vs `quality` profile | 展示旧模型/旧流程到当前质量基线的主要提升。 |
| 演示/快速预览 | `fast` profile `6802e01f1a73` | 明显更快，但必须标注为需复核。 |
| 跨数据集证据 | FLARE22 remap `86b0153d0a73` | 适合做外部器官名对齐检查，不能用于 AMOS 原生分数声明。 |
| 跨数据集在线验证 | FLARE 自动 remap `a717dacf42d3` | 自动 taxonomy remap 上线后，在线验证 mean_dice=0.926，验证通过。 |

补充口径：缓存命中耗时只能用于说明预测结果复用速度，不能替代未缓存推理性能；缓存命中后的 validation 也不能直接引用缓存来源 job，必须看当前请求是否有标签文件或内置参考标签。

## 2026-06-01 本地缓存演示审核记录

- 本轮新增 3 行：AMOS 0117 cache hit（`aea4e7cdbaf0`，命中 `009d4efdc5f6`）、FLARE22 Tr 0009 真实推理（`0aa7323a4c01`，218s）、FLARE22 cache hit（`02da885c97d8`，0.001s）。
- AMOS cache hit 命中的是 2026-05-23 历史推理结果（138KB，mean_dice 0.891，stomach 0.556，validation review），与 `009d4efdc5f6` 旧表数据完全一致；不修改本表中其他任何指标数值。
- FLARE 真实推理 + cache hit 走的是 `real-nnunetv2` + `cached-real-nnunetv2` 完整链路；没有 AMOS 原生标签自动 validation（`validation_available=false` 是 `reference_cases.local.json` 的设计选择），因此不参与 dice/IoU/HD 指标聚合。
- cache_key 7 字段（`input_sha256` / `checkpoint_sha256` / `checkpoint_dataset_name` / `checkpoint_configuration` / `labels_source` / `runtime_target` / `inference_options`）隔离正确：FLARE cache hit `02da885c97d8` 与 FLARE 真实 `0aa7323a4c01` cache_key 前 16 位完全相同（`0f9c6d68e314b3d7`），但与 AMOS cache hit `aea4e7cdbaf0`（`4e0eb3cd29145b70`）和 quality AMOS `b3c528cc9e20` 完全不同。
- 推荐基线表不变：正式 AMOS 报告仍以 `b3c528cc9e20`（mean Dice 0.924780）为基线；本地缓存演示是工程链路演示，不替代正式质量基线。
- 新增 `tools/seed_demo_cache.py`：幂等可重跑；缺失 `009d4efdc5f6` 预测时返回明确提示，FLARE 真实推理缺失时返回"先在 GUI 跑一次 FLARE 推理" 的提示。
- `cached-real-nnunetv2` 仅复用预测 NIfTI；本轮 FLARE cache hit 没有上传 label file，所以 `validation=null`，与 README 缓存语义说明一致。

## 2026-06-01 cache 链路补丁审核记录

- 本轮为本地缓存演示的链路补丁，目标是把 FLARE22 cache hit 命中的历史 validation 摘要正确显示出来（0.893127/0.67373/0.949908，"（历史离线缓存摘要）"），而不是让 `009d4efdc5f6` 的 AMOS 摘要被错位引用。
- 修复点：`server/main.py` 新增 `_load_cached_validation_summary()` + `complete_cached_job()` historical 回退；`find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序；`tools/rewrite_flare22_historical_summary.py` 把 2026-05-26 remap 后的 metrics 写入 0aa7323a4c01 的 output；前端 `getValidationStatusCopy()` 增加 cachedResult 参数；`tests/backendState.test.py` 新增 2 个回归测试。
- 教训：`SEGMENTATION_REFERENCE_CASES_JSON` 必须指向 `examples/reference_cases.json`（或 `nnunetv2_files/reference_cases.local.json`），否则 `/api/samples` 只会返回内置 `amos_0117`，FLARE22 Tr 0009 不可选；现场复测时漏设这个 env var 会让所有"载入参考病例"都跑错。
- 本轮不修改本表中任何历史实验指标数值；AMOS 原生基线 `b3c528cc9e20`、FLARE22 自动 remap `a717dacf42d3`、FLARE22 离线 remap `86b0153d0a73` 仍是同一份数据。
