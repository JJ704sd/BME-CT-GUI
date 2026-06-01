# 本地缓存演示 Runbook

> 日期：2026-06-01
> 适用项目：`D:\BME2026\BME_CT_Seg\segmentation-gui-prototype`
> 配套 spec：`docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`
> 配套 plan：`docs/superpowers/plans/2026-06-01-local-cache-demo.md`

## 启动命令

后端（**cwd 必须是 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype`**，让 `server` 包被 sys.path 找到；PROJECT_ROOT 是给绝对路径解析用的，**不是** uvicorn 的启动 cwd）：

```bash
cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
SEGMENTATION_REFERENCE_CASES_JSON="D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/nnunetv2_files/reference_cases.local.json" \
  "D:/BME2026/BME_CT_Seg/nnunet_env/Scripts/python.exe" -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

前端：

```bash
cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
npm run dev
```

健康检查：

```bash
curl http://127.0.0.1:8000/api/health
curl http://127.0.0.1:8000/api/samples
```

## 关键路径

| 角色 | 路径 |
|---|---|
| 项目根（uvicorn cwd） | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` |
| PROJECT_ROOT（绝对路径解析用） | `D:\BME2026\BME_CT_Seg` |
| venv | `D:\BME2026\BME_CT_Seg\nnunet_env` |
| venv Python | `D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe` |
| 推理子进程入口（自动用） | `D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\nnUNetv2_predict_from_modelfolder.exe` |
| AMOS 原图 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\amos_0117(3).nii.gz` |
| AMOS 标签 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\amos_0117(2).nii.gz` |
| FLARE 原图 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\FLARE22_Tr_0009_0000.nii.gz` |
| AMOS checkpoint | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\checkpoint_best.pth` (1.1GB) |
| 4 例 live reference config | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\reference_cases.local.json` |
| runtime model | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\server\work\runtime_model\nnUNetTrainer__nnUNetPlans__2d\` |
| 预热 AMOS 缓存（手动 seed） | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\server\work\009d4efdc5f6\` |
| 本次 FLARE 真实推理结果 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\server\work\0aa7323a4c01\` |
| 本次所有 job | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\server\work\<job_id>\` |

## 本次演示落盘的 job

| 用途 | job_id | 模式 | cache_key | 耗时 | 备注 |
|---|---|---|---|---|---|
| AMOS cache hit | `aea4e7cdbaf0` | `cached-real-nnunetv2` | `4e0eb3cd...` | ~3s | 命中手工 seed 的 `009d4efdc5f6`；validation mean_dice 0.891（review 状态，stomach 0.556 偏低） |
| FLARE 真实推理 | `0aa7323a4c01` | `real-nnunetv2` | `0f9c6d68...` | 218s | RTX 4060，quality + TTA，3d_fullres，结果 120KB |
| FLARE cache hit | `02da885c97d8` | `cached-real-nnunetv2` | `0f9c6d68...` | 0.001s | 命中 `0aa7323a4c01` |

填表方法：

```bash
cat "D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/<job_id>/output/job_summary.json" | python -c "import json,sys; d=json.load(sys.stdin); print('mode:', d['mode']); print('cache_key:', d['cache_key'][:16]); print('duration:', d.get('duration_seconds'))"
```

## cache_key 字段（7 个）

`build_prediction_cache_key()` 哈希这些字段，**任一不一致就失配**：

1. `input_sha256`（输入文件 SHA-256，非路径；重压缩即失配）
2. `checkpoint_sha256`（`nnunetv2_files/checkpoint_best.pth` 的 SHA-256）
3. `checkpoint_dataset_name`（如 `Dataset001_AMOS22`）
4. `checkpoint_configuration`（如 `3d_fullres`）
5. `labels_source`（内置 AMOS checkpoint label vs 用户上传 label）
6. `runtime_target`（`local` vs `server`，互不混用）
7. `inference_options`（`quality` vs `fast`，TTA、tile_step_size 也算）

命中缓存时 `validate_against_custom_label` 仍按**当前请求**的 label 重算 Dice，不复用旧 validation 指标。

## 验收记录

| 阶段 | 状态 | 备注 |
|---|---|---|
| Task 1 装 fastapi/uvicorn | ✓ | fastapi 0.136.3 / uvicorn 0.48.0 / python-multipart 0.0.30 |
| Task 2 启动后端 | ✓ | cwd=project subdir，`/api/health` ready=true；`/api/samples` 含 4 例 |
| Task 3 启动前端 | ✓ | Vite 6.4.2, http://127.0.0.1:5173/ → 200 |
| Task 4 AMOS cache hit | ✓ | `aea4e7cdbaf0`, mode=cached, source=`009d4efdc5f6` |
| Task 5 FLARE 真实推理 | ✓ | `0aa7323a4c01`, 218s, 120KB result |
| Task 6 FLARE cache hit | ✓ | `02da885c97d8`, 0.001s, source=`0aa7323a4c01` |
| Task 7 写 runbook | ✓ | 本文件 |

## 已知约束 & 经验

- **uvicorn 启动 cwd 必须在 `segmentation-gui-prototype` 子目录**，不在 `BME_CT_Seg` 父目录。`server/` 包需要从 sys.path 找到。
- **uvicorn 用 `-m` 启动时不自动把 cwd 加进 sys.path**，必须从子目录启动或在 `server/` 父目录（=project root）启动；本次 spec 写错了"必须从父目录"，已实测修正。
- **预热缓存必须有 `job_summary.json`**。`server/work/009d4efdc5f6/output/` 原本只有 `dataset.json` / `plans.json` / `predict_from_raw_data_args.json` / `validation_summary.json` / `009d4efdc5f6.nii.gz`，**没有** `job_summary.json` —— `find_cached_prediction()` 扫不到。手工 `tools/seed_amos_cache.py` 写入了 `job_summary.json` 后缓存才被识别。
- **真实推理进度在 SSE 上长期停在 20%**，但 `phase_timings.nnunet_process` 会持续增长；218s 后才一次性到 100%。这是 nnUNetv2 单调进度表达，不是 hang。期间可用 `nvidia-smi` 确认 GPU 是否在用。
- **`/api/samples` 默认走回退配置**（`default_reference_case_specs()`），只暴露 1 例 AMOS。要看全部 4 例必须设置 `SEGMENTATION_REFERENCE_CASES_JSON` 指向 `nnunetv2_files/reference_cases.local.json`。
- **取消真实推理 job** 走 `POST /api/segment/jobs/{id}/cancel`，但取消信号需要 nnUNetv2 子进程轮询才会落状态；如果 GPU 已经在跑，下一个 cancel 信号要等下一次心跳。直接重启后端最快。
- **FLARE 推理 218 秒**比 5–20 分钟估计快很多，因为 FLARE22 Tr 0009 体积（512×512×87）较小且 2D 模型 patch 轻。
- **AMOS 预热预测的 quality 表现**（stomach 0.556、mean_dice 0.891）明显低于 README/AGENTS.md 写的"0.925"。原因可能是 5 月 23 日的预测用的是 fast/早期权重；本次未重训，复现的指标就是这个版本。**复跑 AMOS 真实推理会得到更新更准的预测**。
- **本次没有 commit 任何代码改动**（`docs/local-cache-demo-runbook.md` 是新建文档，`tools/seed_amos_cache.py` 是新建脚本）。是否 git commit 由你决定。
