# 本地缓存演示 — 设计文档

**日期：** 2026-06-01
**范围：** 用项目自带的 `nnunetv2_files/` 中两例 CT（AMOS 0117、FLARE22 Tr 0009）和 `D:\BME2026\BME_CT_Seg\nnunet_env` venv，跑通"本地在线推理 → 缓存回填 → 二次命中"的 GUI 演示。
**不在范围内：** 服务器 5-GPU / 5-fold soft ensemble 链路；taxonomy 自动 remap 行为改动；新功能开发。

---

## 1. 背景与现状

- `server/main.py` 第 39–60 行已固定 `PROJECT_ROOT = D:\BME2026\BME_CT_Seg`，并把 `nnunet_env\Scripts\nnUNetv2_predict_from_modelfolder.exe` / `python.exe` 作为推理子进程入口。**项目本地推理链路已与 venv 接通**。
- `server/work/runtime_model/nnUNetTrainer__nnUNetPlans__2d/` 下 `dataset.json`、`plans.json`（来自 FLARE）、`fold_0/checkpoint_best.pth`（AMOS 训练权重）齐全。
- `server/work/009d4efdc5f6/` 已为 AMOS 0117 预热过真实推理结果，`job_summary.json` 含 `cache_key`、`result_ready=true`、`result_path=server/work/009d4efdc5f6/output/009d4efdc5f6.nii.gz`，可直接命中 `cached-real-nnunetv2`。
- `nnunet_env` venv 已确认含 `torch 2.11.0+cu128 / CUDA RTX 4060 Laptop GPU / nnunetv2 2.7.0 / nibabel 5.4.2 / numpy 2.4.3`，但**未装 `fastapi / uvicorn / python-multipart`**，后端 FastAPI 无法启动。
- FLARE22 Tr 0009 暂未在任何 `server/work/<id>/` 中有真实推理结果，FLARE 端无缓存可命中。

## 2. 目标

启动后端与前端 GUI，跑通以下 4 个演示步骤并产出 1 份运行说明文档：

1. 启服务 + 健康检查通过
2. AMOS 0117 上传命中 `cached-real-nnunetv2`（秒级）
3. FLARE22 Tr 0009 真实推理（首次，写入新 cache）→ 二次上传命中
4. 把命令、job_id、cache_key、UI 截屏位记录在 `docs/local-cache-demo-runbook.md`

## 3. 实施阶段

### Phase 0 — 准备（约 5 分钟）

**操作：**
1. 在 `D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe` 装依赖：
   ```bash
   D:/BME2026/BME_CT_Seg/nnunet_env/Scripts/python.exe -m pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "python-multipart>=0.0.9"
   ```
2. 启动后端（必须从 `D:\BME2026\BME_CT_Seg` 父目录启动，因为 `ROOT = parents[1]`、`PROJECT_ROOT = parents[2]`）：
   ```bash
   cd D:\BME2026\BME_CT_Seg
   D:/BME2026/BME_CT_Seg/nnunet_env/Scripts/python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
   ```
3. 启动前端：
   ```bash
   cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
   npm run dev
   ```
4. 健康检查：
   ```bash
   curl http://127.0.0.1:8000/api/health
   curl http://127.0.0.1:8000/api/samples    # 应看到 amos_0117 + flare22_tr_0009
   ```

**成功标准：**
- `/api/health` 返回 `model_status.ready=true` 或 `runtime_target=local` 路径就绪
- `/api/samples` 至少包含 `amos_0117` 和 `flare22_tr_0009` 两项
- 前端 `http://127.0.0.1:5173` 可打开、能看到参考病例面板

### Phase 1 — AMOS 缓存命中（秒级）

**操作：**
1. 前端点"载入参考病例"→ 选 AMOS 0117 → 等待 /api/samples/amos_0117/original 下载完毕
2. 点"开始推理"上传 `amos_0117(3).nii.gz`
3. 观察 SSE 事件：`cache_hit` 阶段、`cached_result=true`、`cache_source_job_id=009d4efdc5f6`
4. 等待 `complete` 事件，模式应为 `cached-real-nnunetv2`
5. 加载 `amos_0117(2).nii.gz` 标签，验证 `validate_against_custom_label` 重新计算的 Dice

**成功标准：**
- 端到端 ≤ 5s（不含手动点按钮）
- `job_summary.json` 写在 `server/work/<新 job_id>/output/`，`cache_source_job_id=009d4efdc5f6`
- 预测 mask 叠加到三视图，器官可点击
- 量化、报告导出可触发

### Phase 2 — FLARE 真实推理（首次，5–20 分钟）

**操作：**
1. 前端载入参考病例 → 选 FLARE22 Tr 0009
2. 点"开始推理"上传 `FLARE22_Tr_0009_0000.nii.gz`
3. 后端 `find_cached_prediction` miss → 走真实子进程 `nnUNetv2_predict_from_modelfolder.exe -i ... -o ... -m runtime_model -f 0 -chk checkpoint_best.pth -device cuda`
4. 等待 SSE 进度（preprocess → predict → export 三阶段）
5. 完成后 `server/work/<新 job_id>/output/<job_id>.nii.gz` + `job_summary.json` 落盘，`mode=real-nnunetv2`、`cache_key` 持久化

**成功标准：**
- 推理在 RTX 4060 上 5–20 分钟内完成
- `server/work/<id>/output/<id>.nii.gz` 文件 > 0 字节、`job_summary.json` 含 `cache_key` + `result_ready=true`
- 不出现 "RuntimeError: out of memory"、"device mismatch" 或 "checkpoint not found"

### Phase 3 — FLARE 缓存命中（秒级）

**操作：**
1. 再次上传同一份 FLARE22 Tr 0009
2. `find_cached_prediction` 命中 Phase 2 写入的 cache_key
3. 验证 `mode=cached-real-nnunetv2`、`cache_source_job_id=<Phase 2 的 id>`

**成功标准：**
- 端到端 ≤ 5s
- UI 表现与 Phase 2 末态一致

### Phase 4 — 写 runbook

**操作：** 写 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\docs\local-cache-demo-runbook.md`，内容：
- 命令清单（Phase 0 的 3 条命令）
- 关键路径：PROJECT_ROOT / nnunet_env / runtime_model / cache_key 落盘位置
- 两个 case 的 job_id、`cache_key`、耗时
- 截图位（前端三视图 + 器官说明面板 + 量化报告）
- 已知的 7 项 cache_key 字段列表（输入 SHA、checkpoint SHA、dataset 名、config 名、labels_source、runtime_target、inference_options）

---

## 4. 风险与回退

| 风险 | 触发条件 | 回退 |
|---|---|---|
| `fastapi/uvicorn` 与 torch 2.11 存在二进制冲突 | `pip install` 报 `ImportError` 或 `OSError: [WinError 193]` | 改用 `python -m pip install --no-deps fastapi uvicorn` 后单独装 `python-multipart` |
| `nnUNetv2_predict_from_modelfolder.exe` 在 venv 中不存在 | 报 `FileNotFoundError` | 回退到 `python.exe -c "<entrypoint>"` 直接调用 `predict_entry_point_modelfolder()`（项目代码已经支持） |
| RTX 4060 显存不足 | `RuntimeError: CUDA out of memory` | 设置 `SEGMENTATION_DEVICE=cpu` 跑 FLARE 推理，或 `inference_profile=fast` 减小 tile |
| FLARE 推理时间超过 30 分钟 | 推理慢于预期 | 不阻塞 Phase 4；runbook 写明耗时、后续优化方向（预降采样等） |

## 5. 验收

- 4 个 Phase 全部完成
- 产生 1 份 `docs/local-cache-demo-runbook.md`
- 2 个真实 job_id + cache_key 落盘
- 前端三视图、器官拾取、量化、报告导出在 AMOS 与 FLARE 上都可触发

## 6. 不在本次范围

- 服务器模式 `runtime_target=server` 的任何改动
- taxonomy 自动 remap 修复
- `nnunetv2_files/` 之外的数据接入
- 5-fold soft ensemble
- 任何持久化部署包（`deployment-packages/`）的更新
