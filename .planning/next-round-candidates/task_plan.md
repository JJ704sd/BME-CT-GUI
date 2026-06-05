# 下一轮候选任务规划

**范围：** 基于 2026-06-05 项目现状，规划下一轮可执行任务。

**当前状态：** 本地缓存演示 7 步 + cache 链路补丁 + detect_dataset 二轮收紧 + dataset_hint 字段 + 6 类医学影像指标扩展 + surface_distances 2 EDT + HTML 报告第一轮美化（视觉层 + 信息层）+ HTML 报告临床报告风格重构（封面 + 摘要 + TOC + 8 段章节 + 公式 tip + 严重度分布图 + caption/footnote + 打印页眉页码）均已收口。9 份核心文档全部同步到 6-05 状态，4 份 planning 文档落地。当前阻塞点转为 `runtime_target=server` 创建任务不应依赖本地 nnUNet 文件、服务器 AMOS validation 需用显式 taxonomy 复跑、高分辨率 CT 推理需优化、AMOS 预热预测需复跑、跨数据集 cache 链路需产品化、演示启动脚本需自动化、runbook 校验需自动化。

**本轮已完成（2026-06-01）：**

- 本地缓存演示 7 步（AMOS cache hit + FLARE 真实推理 218s + FLARE cache hit 0.001s）
- cache 链路补丁（historical 回退 + find_cached_prediction 优先选有 validation_summary.json 的 cache_source + tools/rewrite_flare22_historical_summary.py + 2 个新测试）
- 9 份核心文档同步
- `.planning/2026-06-01-local-cache-demo/` 4 份 planning 文档落地

**本轮已完成（2026-06-02）：**

- `detect_dataset()` 0.85 coverage 守卫（`taxonomy=auto` 时 AMOS 真实 1-13 标签不再被误判为 FLARE22）
- 前端 `loadReferenceCase()` 按 `referenceCase.dataset` 自动设置 `label_taxonomy`
- `Job.dataset_hint` + 前端 `referenceCaseDatasetHint` 状态机（`taxonomy=auto + dataset_hint=FLARE22` 强制 remap）

**本轮已完成（2026-06-03）：**

- 6 类医学影像指标扩展（Dice / IoU / Pixel Accuracy / HD / HD95 / ASD），`ValidationSummary` 增补 12 字段
- `server/main.py surface_distances()` 把单 label EDT 调用从 6 次合并到 2 次（AMOS 0117 quality cache hit validation 38.86s → 16.78s，约 2.3× 加速）
- `src/report/exportReport.ts` 3 个 metric group（19 张卡片）+ 逐标签 4 列新指标
- 3 个新增回归测试（1e-9 精度、EDT 计数恒为 2、wall-time 加速比 ≥30%）
- 6-03 baseline 数值：mean Pixel Accuracy 0.999855、mean HD 9.59281mm、mean HD95 3.596449mm、mean ASD 0.660724mm
- 10 份核心文档同步到 6-03 现状 + 新建 `examples/reference_cases.json`（4 例模板）

**本轮已完成（2026-06-04）：**

- HTML 报告第一轮美化（视觉层）：色阶图例、Header 渐变、3 个 metric group 加组标题图标、aiFindings 严重度排序 + `.severity-{high,medium,low}` 高亮、器官列表用 `<details><summary>` 折叠、逐标签表列固定 + 列点击排序、@media print A4 页眉页码
- HTML 报告第一轮美化（信息层）：remap_applied 顶部警告条、taxonomy / dataset_hint 展示位、spacing 可视化、historical 警告条
- `src/main.tsx:handleExport` 透传 5 个 validation 字段
- `tests/imagingLogic.test.ts` 新增 source-grep 断言保护 4 个新 class
- 9 份核心文档同步到 6-04

**本轮已完成（2026-06-05）：**

- HTML 报告临床报告风格重构：`.cover` 封面页、`.exec-summary` 执行摘要、`.toc` 目录（§1-§8 锚点导航）、`.formula-tip` 公式小贴士（Dice / IoU、Pixel Accuracy、HD95 三张）、`.dist-chart` 严重度分布图、`.table-caption` 表格标题、`.footnotes` 脚注
- 章节编号 `.section-num`（"§ N"） + `.section-en`（英文小标题）
- 字体 Source Han Serif / Songti SC + JetBrains Mono
- @media print 改为 A4 + 顶部 caseId + 底部 page X of Y
- 3 个新工具函数 `distributionChartHtml()` / `severityBuckets()` / `formulaTips()`
- `npm test` / `npm run build` 全过
- 9 份核心文档同步到 6-05
- 4 份 planning 文档落地（`explanation.md` / `findings.md` / `progress.md` / `task_plan.md`）

---

## 推荐下一轮任务

### 1. AMOS 预热预测复跑

**优先级：** 高

**前置文档：** `.planning/2026-06-01-local-cache-demo/findings.md` 发现 4

**目标：** 用 quality profile 复跑 AMOS 0117，替换 cache demo Phase A 命中的 review status 预测 `009d4efdc5f6`，让 Phase A 在 PPT 演示中也能挂上一个 stomach Dice 不再是 0.556 的预测。

**关键步骤：**

1. 在本地以 `runtime_target=local`、`profile=quality`、`label_taxonomy=AMOS22` 重新提交 AMOS 0117 job。
2. 检查 `validation_status` 不再是 review，stomach Dice 恢复到 0.8 以上。
3. 用 `tools/seed_demo_cache.py` 把新的预测 entry 替换 `009d4efdc5f6`，让 Phase A 自动命中新预测。
4. 更新 `docs/local-cache-demo-runbook.md` 中的 job 表格。

**风险：** quality profile 在 AMOS 0117 上耗时约 23 分钟，演示当天不要现场重跑；提前完成。

---

### 2. server mode gating 修复

**优先级：** 高

**前置文档：** `.planning/label-taxonomy-server-validation/`

**目标：** `runtime_target=server` 创建 job 时只检查 server runtime 必需路径，不再要求本地 Windows `dataset.json/plans/checkpoint/python.exe`。

**关键步骤：**

1. 修改 `/api/segment/jobs` 路径检查逻辑。
2. `runtime_target=server` 只检查 `SEGMENTATION_SERVER_EVALUATE_SCRIPT`、`SEGMENTATION_SERVER_DATASET_JSON`、`SEGMENTATION_SERVER_NNUNET_RAW`、`SEGMENTATION_SERVER_NNUNET_PREPROCESSED`、`SEGMENTATION_SERVER_NNUNET_RESULTS`、`SEGMENTATION_SERVER_OUTPUT_ROOT`。
3. `runtime_target=local` 才检查本地 `dataset.json`、`plans`、`checkpoint`、`python.exe`。
4. 确认 `/api/models` 不再因本地文件缺失而报错。

**风险：** 该修复只影响 job 创建时的路径检查，不改变 nnUNet 原始预测输出。

---

### 3. 服务器 validation 复跑

**优先级：** 高

**前置条件：** server gating 修复完成

**目标：** 用显式 `label_taxonomy=AMOS22` 复跑服务器 AMOS，确认 `remap_applied=false` 后纳入正式质量基线。

**关键步骤：**

1. 复跑 AMOS：选择 `label_taxonomy=AMOS22`，预期 `remap_applied=false`。
2. 复跑 FLARE：选择 `label_taxonomy=FLARE22`，预期 `remap_applied=true`、`remap_source=FLARE22`。
3. 记录服务器质量基线指标（mean Dice、min Dice、foreground Dice）。
4. 与本地 quality 基线（`b3c528cc9e20`，mean Dice 0.924780）对比。

**风险：** 服务器链路可运行不等于质量基线已完成；AMOS 服务器指标必须先排除 taxonomy 误判。

---

### 4. 高分辨率推理优化

**优先级：** 中高

**前置文档：** `.planning/high-resolution-inference-optimization/`

**目标：** 实现预降采样，缩短高分辨率 CT 推理时间。

**关键步骤：**

1. 评估预降采样方案可行性（768→512，预期推理时间减少约 50%）。
2. 在前端添加降采样选项（如 `inference_resolution=original|downsampled_512`）。
3. 在后端实现降采样逻辑（使用 `scipy.ndimage.zoom` 或类似方法）。
4. 测试降采样后的推理时间和分割质量。
5. 评估是否需要上采样到原始分辨率。

**风险：** 降采样可能丢失细节信息；所有速度和质量结论都必须绑定 job id、输入、checkpoint、profile 和指标。

---

### 5. 跨数据集 cache 链路产品化

**优先级：** 中

**前置文档：** `.planning/next-round-candidates/findings.md` 发现 2

**目标：** 把"按历史指标改写 cache_source 摘要"做成可复用机制，让其他数据集/其他 cache_source 也能享受 cache hit 时显示历史 validation 摘要的链路。

**关键步骤：**

1. 重构 `tools/rewrite_flare22_historical_summary.py` 为通用 `tools/rewrite_cached_validation_summary.py`，支持任意 source 路径、任意 target job 目录、任意指标 JSON。
2. 在 `server/main.py` 的 `complete_cached_job()` 中增强 historical 回退：除 `validation_summary.json` 外，尝试读 `job_summary.json` 中的历史指标。
3. 补充 `tests/backendState.test.py` 覆盖"cache_source 含历史指标但无 validation_summary.json"场景。
4. 更新 `docs/local-cache-demo-runbook.md` 增补"通用改写历史摘要"段落。

**风险：** 必须保留"`historical: true`"和"`source_job_id`"标记，避免误把当前请求的标签结果写成历史。

---

### 6. 演示启动脚本化

**优先级：** 中

**前置文档：** `.planning/next-round-candidates/findings.md` 发现 3 + 发现 5

**目标：** 写 `tools/start_local_demo.py`，自动 setenv + spawn backend/frontend，避免演示现场漏设 `SEGMENTATION_REFERENCE_CASES_JSON`、`SEGMENTATION_PERSISTENT_WORKER`、`SEGMENTATION_DEVICE` 等环境变量。

**关键步骤：**

1. `tools/start_local_demo.py` 接收 `--reference-cases-json` 参数（默认 `examples/reference_cases.json`）。
2. 自动 setenv：`SEGMENTATION_REFERENCE_CASES_JSON` / `SEGMENTATION_PERSISTENT_WORKER=1`（可选）/ `SEGMENTATION_DEVICE=cuda`（可选）。
3. 子进程 spawn：`python -m uvicorn server.main:app --host 127.0.0.1 --port 8000` 和 `npm run dev -- --port 5173`。
4. 输出 `curl http://127.0.0.1:8000/api/samples` 提示用户验证 4 个 case。
5. 补 `tests/startLocalDemo.test.py` dry-run 验证 env var 正确传递。

**风险：** 脚本不能取代手动 runbook 作为兜底；保留 runbook 作为停止脚本后的 fallback。

---

### 7. runbook 自动校验

**优先级：** 中

**前置文档：** `.planning/next-round-candidates/findings.md` 待验证假设 6

**目标：** 写 `tests/cacheDemoRunbook.test.py`，自动确认 runbook 中提到的 4 个已知约束仍在代码里成立。

**关键步骤：**

1. 测试 `_resolve_project_root()` 在 cwd 不同时的解析行为，确认必须落在 `segmentation-gui-prototype/`。
2. 测试 `compute_cache_key()` 的 7 字段仍是 `input_sha256 + checkpoint_sha256 + checkpoint_dataset_name + checkpoint_configuration + labels_source + runtime_target + inference_options`（与 `server/main.py:1880 build_prediction_cache_key()` 实际实现保持一致）。
3. 测试 `examples/reference_cases.json` 解析后能产出 4 个 case；`SEGMENTATION_REFERENCE_CASES_JSON` 缺省时只暴露 `amos_0117`。
4. 测试 `tools/seed_demo_cache.py` 和 `tools/rewrite_flare22_historical_summary.py` 在重复运行下保持幂等。
5. 测试 `find_cached_prediction()` 候选排序在多个 cache_source 下优先选有 `validation_summary.json` 的。

**风险：** 这些测试不应启动真实后端服务；用 import 函数 + 临时目录的方式做单元测试即可。

---

### 8. 跨数据集标签评估增强

**优先级：** 中

**目标：** 在自动 remap 已可用的基础上，增强未知数据集和异常指标的解释能力。

**候选改进：**

- 对 remap 覆盖率不足或未知标签 ID 给出明确 UI 警告。
- 为单 label 或少量标签文件增加显式数据集 hint 入口。
- 在 per-label 表格中标出体素量级差异异常、Dice 为 0 的疑似错位标签。
- 记录 `remap_mapping` 的用户可读摘要，便于报告导出。

**风险：** 需要避免把 remap 后的跨数据集指标写成 AMOS 原生验证。

---

### 9. 文档与验收口径再同步

**优先级：** 中

**目标：** 继续保持 README、ACCEPTANCE、REVIEW、指标汇总和近期轮次记录与代码现状一致。

**关键步骤：**

1. 在后续代码或配置变化后，及时同步 9 份核心文档的中文主体说明。
2. 对 `SEGMENTATION_METRICS_SUMMARY.md`、`SEGMENTATION_EXPERIMENT_COMPARISON.md` 和 `SEGMENTATION_RECENT_ROUNDS.md` 继续坚持"新工程链路不混入旧指标"的口径。
3. 后续若新增 validation 字段或新视觉元素，必须同时改 `inferenceClient.ts normalizeValidation` 白名单 + `exportReport.ts` 模板 + `tests/imagingLogic.test.ts` source-grep 断言三处。

**风险：** 这类工作本身不难，但容易在没有同步代码现状时写入过时结论。

---

### 10. 多模型支持准备

**优先级：** 低（等待新 checkpoint）

**目标：** 当前只有 AMOS22 单模型，为未来多模型切换预留结构。

**候选改进：**

- `modelOptions` 从硬编码改为从 `/api/models` 动态获取。
- 后端增加模型目录扫描和模型信息 API。
- 前端模型卡片改为可点击切换。

**风险：** 没有新 checkpoint 时难以完成真实验收。

---

## 推荐执行顺序

1. **AMOS 预热预测复跑**（让 cache demo Phase A 命中一个非 review 状态预测）。
2. **server mode gating 修复**（解除服务器模式的阻塞点，独立 planning）。
3. **AMOS/FLARE 服务器显式 taxonomy 复跑**（确认服务器质量基线，独立 planning）。
4. **高分辨率推理优化**（预降采样，独立 planning）。
5. **跨数据集 cache 链路产品化**（让 cache 链路补丁成为通用机制）。
6. **演示启动脚本化**（演示当天减少手输命令）。
7. **runbook 自动校验**（防止下次复现同样的困惑）。
8. **跨数据集标签评估增强**（持续）。
9. **文档与验收口径再同步**（持续）。
10. **多模型支持准备**（等待新模型或新 checkpoint 后再启动）。

---

*更新日期：2026-06-05*
