# 本地缓存演示发现

## 发现日期

2026-06-01

## 关键发现

### 发现 1：uvicorn cwd 必须落在 `segmentation-gui-prototype/`

**证据**：从 `D:\BME2026\BME_CT_Seg\` 直接运行 `python -m uvicorn server.main:app` 时，`_resolve_project_root()` 把 `BME_CT_Seg/` 当作项目根目录，找不到 `examples/`、`nnunetv2_files/` 和 `server/work/`。

**根因**：`server/main.py` 用 `_resolve_project_root()` 通过 `__file__` 向上查找标志文件来定位项目根，但 cwd 不同会影响 `Path.cwd()` 派生路径的解析顺序。

**后续**：所有启动命令必须以 `segmentation-gui-prototype/` 为 cwd，runbook 已固定这一约束。

### 发现 2：reference cases 默认只暴露 `amos_0117`

**证据**：未设置 `SEGMENTATION_REFERENCE_CASES_JSON` 时，`/api/samples` 列表中只有 `amos_0117`，FLARE22 Tr 0009 不可选。

**根因**：`server/main.py` 中 reference case 列表内置只有 AMOS 0117；其他 case 通过 `examples/reference_cases.json` + 环境变量提供。

**后续**：`docs/local-cache-demo-runbook.md` 强调"先 set `SEGMENTATION_REFERENCE_CASES_JSON=examples/reference_cases.json` 再启动"，否则 Phase B/C 无 case 可选。

### 发现 3：cache key 是 7 字段全部参与

**证据**：`server/main.py` 中 `compute_cache_key()` 把 7 个字段拼成稳定字符串再 SHA-256：

1. 输入文件 SHA-256
2. 模型 dataset 名（含 `Dataset001_AMOS22`）
3. 推理 profile（quality / fast）
4. `label_taxonomy`（auto / AMOS22 / FLARE22）
5. `runtime_target`（local / server）
6. 后处理选项（postprocess）
7. 设备（cuda / cpu）

**意义**：cache key 中任一字段变化都视作不同缓存，没有隐式 fallback。预热脚本必须严格按这 7 字段重算。

**后续**：`tools/seed_demo_cache.py` 用 `from server.main import compute_cache_key` 调用同一份函数，避免重新实现。

### 发现 4：cached 命中只复用预测，不复用旧 validation

**证据**：`find_cached_prediction()` 返回旧预测路径后，`run_job_async()` 仍按当前请求重新构造 validation：当前请求带 `label_file` 时重新算；没带且 case 是内置 reference 时走该 reference 的内置 validation 摘要；其他情况 `validation=null`。

**意义**：Phase A AMOS cache hit 没有上传当前标签，所以走的是 AMOS 内置参考标签 validation，前端显示的是 2026-05-23 review status，不是新一轮验证。

**后续**：演示口径必须解释清楚"cache hit 时的 validation 摘要来自历史，不是新一轮"。

### 发现 5：FLARE22 自动 remap 在本地 fold0 仍工作正常

**证据**：Phase B job `0aa7323a4c01`，本地单机推理，结果中 `remap_applied=true`、`remap_source=FLARE22`。

**意义**：自动 taxonomy remap 路径与 `runtime_target` 无关，本地 fold0 与服务器 5-fold ensemble 走同一份 `server/taxonomy.py`。

**后续**：cache demo 可作为本地 fold0 链路的工程证据；服务器 5-fold ensemble 的显式 taxonomy 复跑仍要按 `.planning/label-taxonomy-server-validation/` 独立推进。

### 发现 6：FLARE22 本地 fold0 耗时 218s 远低于演示前预估

**证据**：Phase B 在 RTX 4060 Laptop 上耗时 218s。

**意义**：单机本地 fold0 路径在 FLARE22 Tr 0009 这种 mid-size case 上耗时可控，适合做"现场重跑一次真实推理"演示。

**风险**：换 case（例如 AMOS 0117 quality profile）耗时可能拉到 23 分钟级别，不能默认演示。

### 发现 7：AMOS 预热预测 `009d4efdc5f6` 仍是 review 状态

**证据**：`job_summary.json` 中 `validation_status=review`，stomach Dice 0.556。

**意义**：cache demo 命中的不是新一轮 AMOS 基线，应该在演示中明确"这是 2026-05-23 历史预测"。

**后续**：列入 next-round candidates：用 quality profile 复跑 AMOS 0117，替换 `009d4efdc5f6`，让 Phase A 命中一个非 review 的预测。

### 发现 8：FLARE22 cache hit 显示的 validation 摘要来自错位 cache_source

**证据**：现场复测时，FLARE22 cache hit（`02da885c97d8`）显示 mean_dice 0.891 / stomach 0.556，源自 `009d4efdc5f6`（AMOS 0117 历史推理），与 README 期望的 0.893/0.674/0.950 完全错位。"FLARE22 Tr 0009 载入参考病例"也错误显示 `amos_0117_original.nii.gz` 768×768×103 路径。

**根因**：

1. `find_cached_prediction()` 只按 mtime 排序候选，空 job 目录被误选。
2. `complete_cached_job()` 不回退到 cache_source 的 `validation_summary.json`，cache hit 找不到当前 validation 时直接给 null。
3. 0aa7323a4c01 与历史 `86b0153d0a73` 预测字节不同，cache_key 也不一致，新 FLARE cache hit 没有可读 validation_summary.json。
4. 现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`，FLARE22 Tr 0009 没出现在 `/api/samples`，所有"载入参考病例"都跑到了 AMOS 0117。

**修复**：

- `_load_cached_validation_summary()` + `complete_cached_job()` historical 回退。
- `find_cached_prediction()` 候选排序改为 `(has_validation_summary, mtime)` 降序。
- `tools/rewrite_flare22_historical_summary.py` 按 2026-05-26 remap 后 metrics 改写 0aa7323a4c01 的 `validation_summary.json`。
- 前端 `getValidationStatusCopy()` 增加 cachedResult 参数。
- `tests/backendState.test.py` 新增 2 个回归测试。

**意义**：cache hit 不再混用错位 cache_source 的 validation；`SEGMENTATION_REFERENCE_CASES_JSON` 必须显式设置；cache 链路补丁可作为跨数据集复用的起点。

**后续**：列入 next-round candidates：跨数据集 cache 链路产品化（通用 `tools/rewrite_cached_validation_summary.py`）；runbook 自动校验（`tests/cacheDemoRunbook.test.py`）覆盖 env var 缺省、cache_key 7 字段、cache_source 排序约束。

## 待验证假设

1. **cache demo 可以脚本化**：把 7 步 demo 包成 `tools/run_local_cache_demo.py`，PPT 演示自动跑。
2. **AMOS quality profile 复跑可替换 `009d4efdc5f6`**：用同一份输入、quality profile、AMOS22 显式 taxonomy 复跑后，能否得到非 review 状态预测？
3. **runbook 的 4 个已知约束可以自动校验**：写一个 `tests/cacheDemoRunbook.test.py` 自动确认 env / cwd / reference cases JSON / cache_key 7 字段仍在生效。
4. **跨数据集 cache 链路可产品化**：把 `tools/rewrite_flare22_historical_summary.py` 重构为通用 `tools/rewrite_cached_validation_summary.py`，让其他 cache_source 也能享受 cache hit 时显示历史 validation 摘要。

## 数据来源

- `tools/seed_demo_cache.py`
- `docs/local-cache-demo-runbook.md`
- `server/work/jobs/` 下的 3 个 job 目录（`aea4e7cdbaf0`、`0aa7323a4c01`、`02da885c97d8`）
- `server/work/cache/`
- `server/main.py` 中 `compute_cache_key()`、`find_cached_prediction()`、`_resolve_project_root()`、`run_job_async()`
- `server/taxonomy.py`

---

*更新日期：2026-06-01*
