# 本地缓存演示 实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在本机用项目自带的 `nnunetv2_files/` 中两例 CT（AMOS 0117、FLARE22 Tr 0009）和 `D:\BME2026\BME_CT_Seg\nnunet_env` venv，跑通"本地在线推理 → 缓存回填 → 二次命中"的 GUI 演示，并产出一份 runbook。

**Architecture:** 沿用项目现有架构，不改任何源码。`server/main.py` 已把 `nnunet_env\Scripts\nnUNetv2_predict_from_modelfolder.exe` / `python.exe` 写死为推理子进程入口；缺的是 `fastapi/uvicorn` 没装到该 venv。装好之后后端能起，前端用现有 `npm run dev` 即可。AMOS 0117 缓存已预热（`server/work/009d4efdc5f6/`），演示秒出；FLARE22 Tr 0009 没有现成预测，需实跑一次 nnUNetv2 推理把缓存写出来。

**Tech Stack:** FastAPI / uvicorn / Python 3.11 venv / nnUNetv2 2.7.0 / torch 2.11+cu128 / React + Vite / FastAPI SSE

**Working directory:** 所有"启动后端"操作必须在 `D:\BME2026\BME_CT_Seg` 父目录下进行（`server/main.py:39-44` 写死 `ROOT=parents[1]`、`PROJECT_ROOT=parents[2]`）。所有"启动前端"操作必须在 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` 子目录下。

**venv 入口（统一引用）：** `NNUNET_PY=D:/BME2026/BME_CT_Seg/nnunet_env/Scripts/python.exe`

**Spec:** `docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`

---

## Task 1: 在 `nnunet_env` 安装 FastAPI 后端依赖

**Files:** 无文件改动；只改 venv site-packages。

- [ ] **Step 1: 装依赖**

```bash
"$NNUNET_PY" -m pip install "fastapi>=0.115.0" "uvicorn[standard]>=0.30.0" "python-multipart>=0.0.9"
```

期望：3 个包安装完成，无 `ERROR`。可能出现的 warning：torch ABI 警告（`torch 2.11` 与 `uvicorn` 无关）可忽略。

- [ ] **Step 2: 验证可导入**

```bash
"$NNUNET_PY" -c "import fastapi, uvicorn, multipart; print('fastapi', fastapi.__version__); print('uvicorn', uvicorn.__version__)"
```

期望输出（版本号可能有 ±1 小版本差）：

```
fastapi 0.128.x
uvicorn 0.30.x 或更新
```

- [ ] **Step 3: 不做 commit（无代码改动）**

---

## Task 2: 启动后端并做健康检查

**Files:** 无文件改动。

- [ ] **Step 1: 启动后端（后台）**

```bash
cd D:/BME2026/BME_CT_Seg
"$NNUNET_PY" -m uvicorn server.main:app --host 127.0.0.1 --port 8000 > /tmp/uvicorn.log 2>&1 &
```

注：必须从 `D:\BME2026\BME_CT_Seg`（PROJECT_ROOT）启动，`server/main.py` 才能解析出 `ROOT=segmentation-gui-prototype` 和 `PROJECT_ROOT=BME_CT_Seg`。

- [ ] **Step 2: 等 5 秒并检查日志**

```bash
sleep 5 && head -30 /tmp/uvicorn.log
```

期望：看到 `Uvicorn running on http://127.0.0.1:8000` 和 `Application startup complete.`，不应有 `ImportError` / `ModuleNotFoundError`。

- [ ] **Step 3: 健康检查**

```bash
curl -s http://127.0.0.1:8000/api/health | head -c 600
```

期望：返回 JSON 含 `"status": "ok"`、`"model_status"` 字段。`model_status.ready` 在 `runtime_target=local` 下应反映 `nnunetv2_files/checkpoint_best.pth` 是否就绪。

- [ ] **Step 4: 列出样本**

```bash
curl -s http://127.0.0.1:8000/api/samples | head -c 800
```

期望：返回 `samples` 数组，至少包含：

- `id: "amos_0117"`、`dataset: "AMOS22"`、`has_original: true`、`has_label: true`
- `id: "flare22_tr_0009"`、`dataset: "FLARE22"`、`has_original: true`、`has_label: false`

注：实际样本 id 来自 `reference_cases.local.json`（见 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\reference_cases.local.json`）。如返回的样本 id 与上文不一致，按实际 id 推进。

- [ ] **Step 5: 不做 commit（无代码改动）**

---

## Task 3: 启动前端 dev server

**Files:** 无文件改动。

- [ ] **Step 1: 安装前端依赖（首次或 `node_modules` 缺失时）**

```bash
cd D:/BME2026/BME_CT_Seg/segmentation-gui-prototype
ls node_modules/.bin/vite 2>/dev/null || npm install
```

期望：`node_modules/.bin/vite` 存在。已存在则跳过 `npm install`。

- [ ] **Step 2: 启动前端（后台）**

```bash
cd D:/BME2026/BME_CT_Seg/segmentation-gui-prototype
npm run dev > /tmp/vite.log 2>&1 &
```

- [ ] **Step 3: 等 5 秒并检查日志**

```bash
sleep 5 && head -20 /tmp/vite.log
```

期望：看到 `Local: http://127.0.0.1:5173/`，无编译错误。

- [ ] **Step 4: 验证页面可达**

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://127.0.0.1:5173/
```

期望：`200`。

- [ ] **Step 5: 不做 commit（无代码改动）**

---

## Task 4: AMOS 0117 缓存命中演示

**Files:** 无代码改动；会在 `server/work/<new_job_id>/` 落盘新 job。

- [ ] **Step 1: 记录起始 job 列表**

```bash
ls D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/ > /tmp/jobs_before.txt
wc -l /tmp/jobs_before.txt
```

- [ ] **Step 2: 通过 curl 模拟"上传 AMOS 0117 + 创建 job"**

```bash
curl -s -X POST http://127.0.0.1:8000/api/segment/jobs \
  -F "file=@D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/nnunetv2_files/amos_0117(3).nii.gz" \
  -F "runtime_target=local" \
  -F "inference_profile=quality" \
  -F "label_taxonomy=AMOS22" \
  -F "label_file=@D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/nnunetv2_files/amos_0117(2).nii.gz"
```

期望：返回 JSON 含 `"cached_result": true`、`"cache_source_job_id": "009d4efdc5f6"`（或实际预热 job id）、`"mode": "cached-real-nnunetv2"`、`"job_id"`。

如果返回的 `cache_source_job_id` 不是 `009d4efdc5f6`，用实际返回值替代后面步骤的引用。

- [ ] **Step 3: 记录新 job_id 并抓 SSE 事件**

```bash
JOB_ID=<上一步返回的 job_id>
curl -s -N http://127.0.0.1:8000/api/segment/jobs/$JOB_ID/events | head -50
```

期望：立即看到 `type: "complete"` 事件（因为命中缓存，不会走真实推理），事件 payload 含：

- `cached_result: true`
- `cache_source_job_id: "009d4efdc5f6"`（或实际值）
- `runtime_target: "local"`
- `inference_options.profile: "quality"`
- `phase_timings` 至少含 `cache_hit` 阶段
- `validation` 字段（如传了 `label_file`）

- [ ] **Step 4: 验证新 job 目录与 cache_source 共享同一 cache_key**

```bash
NEW_JOB_DIR=$(ls -t D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/ | head -1)
echo "新 job 目录：$NEW_JOB_DIR"
diff <(cat D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/$NEW_JOB_DIR/output/job_summary.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['cache_key'])") \
     <(cat D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/009d4efdc5f6/output/job_summary.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['cache_key'])")
```

期望：无输出（两个 cache_key 完全相同）。

- [ ] **Step 5: 记录新 job_id 供 runbook 使用**

```bash
echo "AMOS cache hit job: $NEW_JOB_DIR" >> /tmp/demo_jobs.log
cat /tmp/demo_jobs.log
```

- [ ] **Step 6: 不做 commit（无代码改动）**

---

## Task 5: FLARE22 Tr 0009 真实推理（首次，5–20 分钟）

**Files:** 无代码改动；会在 `server/work/<new_job_id>/` 落盘新 job + NIfTI。

- [ ] **Step 1: 提交 FLARE job**

```bash
curl -s -X POST http://127.0.0.1:8000/api/segment/jobs \
  -F "file=@D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/nnunetv2_files/FLARE22_Tr_0009_0000.nii.gz" \
  -F "runtime_target=local" \
  -F "inference_profile=quality" \
  -F "label_taxonomy=FLARE22" > /tmp/flare_create.json
cat /tmp/flare_create.json | head -c 800
```

期望：返回 JSON 含 `"cached_result": false`（首次必然 miss）、`"job_id"`、`"mode": "real-nnunetv2"`（或 `"unavailable"`，看 `model_state`）。

注：AMOS checkpoint 在 FLARE22 CT 上跑出的是 AMOS 标签空间（15 类）的预测，前端可叠加展示。

- [ ] **Step 2: 记录新 job_id 并跟踪 SSE**

```bash
FLARE_JOB_ID=$(python -c "import json; print(json.load(open('/tmp/flare_create.json'))['job_id'])")
echo "FLARE 真实推理 job: $FLARE_JOB_ID"
curl -s -N http://127.0.0.1:8000/api/segment/jobs/$FLARE_JOB_ID/events | head -200
```

期望：

- 看到 `type: "progress"` 事件，阶段名依次为 `preprocess` / `predict` / `export`
- `progress` 从 0% → 100% 渐进
- 5–20 分钟内出现 `type: "complete"` 事件，含 `duration_seconds`、`result_size_bytes`

- [ ] **Step 3: 验证 job 落盘**

```bash
ls -la D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/$FLARE_JOB_ID/output/
cat D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/$FLARE_JOB_ID/output/job_summary.json | head -c 1500
```

期望：

- `output/` 下有 `*.nii.gz` 文件，size > 0
- `job_summary.json` 含 `"result_ready": true`、`"cache_key"`（非空）、`"mode": "real-nnunetv2"`、`"result_path"`

- [ ] **Step 4: 不做 commit（无代码改动）**

---

## Task 6: FLARE22 Tr 0009 缓存命中演示（二次上传）

**Files:** 无代码改动；会在 `server/work/<another_job_id>/` 落盘新 job（cache hit）。

- [ ] **Step 1: 再次上传同一份 FLARE CT**

```bash
curl -s -X POST http://127.0.0.1:8000/api/segment/jobs \
  -F "file=@D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/nnunetv2_files/FLARE22_Tr_0009_0000.nii.gz" \
  -F "runtime_target=local" \
  -F "inference_profile=quality" \
  -F "label_taxonomy=FLARE22"
```

期望：返回 JSON 含 `"cached_result": true`、`"cache_source_job_id": "$FLARE_JOB_ID"`（Task 5 的 job_id）、`"mode": "cached-real-nnunetv2"`。

- [ ] **Step 2: 记录 FLARE cache hit job**

```bash
FLARE_HIT_JOB=$(ls -t D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/ | head -1)
echo "FLARE cache hit job: $FLARE_HIT_JIT" >> /tmp/demo_jobs.log
cat /tmp/demo_jobs.log
```

- [ ] **Step 3: 验证 cache_key 一致**

```bash
diff <(cat D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/$FLARE_HIT_JOB/output/job_summary.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['cache_key'])") \
     <(cat D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/$FLARE_JOB_ID/output/job_summary.json | python -c "import json,sys; d=json.load(sys.stdin); print(d['cache_key'])")
```

期望：无输出。

- [ ] **Step 4: 不做 commit（无代码改动）**

---

## Task 7: 写 runbook 文档

**Files:**
- Create: `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\docs\local-cache-demo-runbook.md`

- [ ] **Step 1: 创建 runbook 草稿**

用 Write 工具新建文件 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\docs\local-cache-demo-runbook.md`，内容如下（按需替换 `<JOB_ID>` 等占位符为实际值）：

```markdown
# 本地缓存演示 Runbook

> 日期：2026-06-01
> 适用项目：`D:\BME2026\BME_CT_Seg\segmentation-gui-prototype`
> 配套 spec：`docs/superpowers/specs/2026-06-01-local-cache-demo-design.md`

## 启动命令

后端（必须从 `D:\BME2026\BME_CT_Seg` 启动，`server/main.py` 的 `PROJECT_ROOT` 解析依赖此 cwd）：

```bash
cd D:\BME2026\BME_CT_Seg
D:/BME2026/BME_CT_Seg/nnunet_env/Scripts/python.exe -m uvicorn server.main:app --host 127.0.0.1 --port 8000
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
| 项目根 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` |
| 父 PROJECT_ROOT | `D:\BME2026\BME_CT_Seg` |
| venv | `D:\BME2026\BME_CT_Seg\nnunet_env` |
| 推理子进程入口 | `D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\nnUNetv2_predict_from_modelfolder.exe` |
| CT 原图 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\amos_0117(3).nii.gz` / `FLARE22_Tr_0009_0000.nii.gz` |
| AMOS 标签 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\nnunetv2_files\amos_0117(2).nii.gz` |
| runtime model | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\server\work\runtime_model\nnUNetTrainer__nnUNetPlans__2d` |
| 预热 AMOS 缓存 | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\server\work\009d4efdc5f6` |
| 本次产生的所有 job | `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\server\work\<job_id>\` |

## 本次演示落盘的 job

| 用途 | job_id | 模式 | cache_key（截前 16 位） | 备注 |
|---|---|---|---|---|
| AMOS cache hit | `<amos_hit_job_id>` | `cached-real-nnunetv2` | `<...>` | 命中 009d4efdc5f6 |
| FLARE 真实推理 | `<flare_real_job_id>` | `real-nnunetv2` | `<...>` | 5–20 分钟 |
| FLARE cache hit | `<flare_hit_job_id>` | `cached-real-nnunetv2` | `<...>` | 命中上一行 |

填表方法：

```bash
cat /tmp/demo_jobs.log
cat D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/server/work/<job_id>/output/job_summary.json | python -c "import json,sys; d=json.load(sys.stdin); print('mode:', d['mode']); print('cache_key:', d['cache_key'][:16])"
```

## cache_key 字段（7 个）

`build_prediction_cache_key()` 哈希这些字段，**任一不一致就失配**：

1. `input_sha256`（输入文件 SHA-256，非路径）
2. `checkpoint_sha256`（`nnunetv2_files/checkpoint_best.pth` 的 SHA-256）
3. `checkpoint_dataset_name`
4. `checkpoint_configuration`
5. `labels_source`（内置 AMOS label vs 用户上传 label）
6. `runtime_target`（`local` vs `server`，互不混用）
7. `inference_options`（`quality` vs `fast` 等 profile，TTA、tile_step 也算）

命中缓存时 `validate_against_custom_label` 仍按**当前请求**的 label 重算 Dice，不复用旧 validation 指标。

## 已知约束

- 后端启动必须从 `D:\BME2026\BME_CT_Seg`（不是 `segmentation-gui-prototype` 子目录）启动。
- `nnunet_env` 缺 `fastapi/uvicorn`；首次演示前要装。
- 真实推理时间与 GPU 强相关；RTX 4060 8GB 上 FLARE22 Tr 0009 fast profile 预计 5–15 分钟，quality profile 可能 15–30 分钟。
- `confidenceThreshold` 当前是 UI 提示，不真实作用概率图。
- FLARE22 label 与 AMOS22 标签 ID 不同；`label_taxonomy=FLARE22` 触发 `server/taxonomy.py` 自动 remap。
```

- [ ] **Step 2: 验证文件存在**

```bash
ls -la D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/docs/local-cache-demo-runbook.md
```

期望：文件存在，size > 0。

- [ ] **Step 3: 提交（可选）**

如希望进入 git：

```bash
cd D:/BME2026/BME_CT_Seg/segmentation-gui-prototype
git add docs/local-cache-demo-runbook.md
git status
# 确认只 add 了这一个文件再继续
git commit -m "docs: add local cache demo runbook"
```

注：此步可选。如果 `git status` 输出超过预期文件，请停下来人工确认，不执行 commit。

- [ ] **Step 4: 演示结束**

停止后端与前端：

```bash
pkill -f "uvicorn server.main:app"
pkill -f "vite"
```

---

## Self-Review Notes（写计划时自检）

- **Spec 覆盖：** Phase 0→4 → Task 1→7，全覆盖。Risk 表的 4 个回退项（fastapi/torch 冲突、nnUNetv2_predict 缺失、显存不足、推理过慢）未单独建任务，因为它们都属于"该步骤执行时如果失败就停下来报告"，不需要额外的 plan task。Spec 6 节"不在本次范围"无任务对应（设计如此）。
- **占位：** 全文无 TBD/TODO；"可选"用括号明确标记（Task 7 Step 3）。
- **类型一致：** 引用了 `server/main.py:39-44`、`server/main.py:1536`、`server/work/009d4efdc5f6/`、`reference_cases.local.json` 这些锚点，与 Task 4 Step 4 用的 path 拼写一致。
- **DRY：** cache_key 字段描述只在 Task 7 runbook 里写一次，不在每个 Task 里复述。
