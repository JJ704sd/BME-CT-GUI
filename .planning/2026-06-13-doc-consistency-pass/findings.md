# 2026-06-13 文档一致性巡检 — Findings

## 一、`start_local_demo.py` smoke test 实际只采样 1 端点（关键发现）

**背景**：9 份主仓库 md（CLAUDE.md / AGENTS.md / README.md / README.zh-CN.md / REVIEW.md / ACCEPTANCE.md / CODE_MODULE_GUIDE.md / SEGMENTATION_EXPERIMENT_COMPARISON.md / SEGMENTATION_METRICS_SUMMARY.md / SEGMENTATION_RECENT_ROUNDS.md）从 6-06 commit `23e0c4d` 起就一直写"4 端点 smoke test"（`/api/health` ready / `/api/samples` 4 case / `/api/models` 1 model / 前端 HTTP 200）。

**实际代码**：`tools/start_local_demo.py:80-91 wait_for_samples()` 只 `urlopen(f"http://127.0.0.1:{backend_port}/api/samples")`，循环 15s 等到返回 `samples` 列表且长度 ≥1 即视为通过。

**结论**：6-06 commit `23e0c4d` 当天文档 commit message 与多份文档里写了"4 端点"是**6-06 当天写文档时多写了一个实际不存在的 smoke test 项**——`tools/start_local_demo.py` 当时实现就只 1 个端点采样。该不一致从 6-06 持续到 6-13 都没被任何 `tests/backendState.test.py` 或 source-grep 守护发现，因为文档不在测试范围内。

**修复**：本轮把所有"4 端点 smoke test"措辞统一改为"启动后采样 `/api/samples`（最多 15s）校验 4 例参考病例（AMOS 0117 / FLARE22 Tr 0009 / WORD / AbdomenCT-1K）已就绪"。`tools/start_local_demo.py` 代码本身**不动**——它的 1 端点采样已经够用（4 例参考病例是 demo 真正需要确认的就绪信号，`/api/health` / `/api/models` / 前端 5173 状态是次要信号）。

**lesson**（已写入 findings）：

1. **文档 commit 不能脱离测试范围**——CLAUDE.md / AGENTS.md / REVIEW.md / 9 份 md 里有大量事实声明（cache_key 字段数 / 端点列表 / SSE 字段名 / 4 例参考病例 ID）靠**人工纪律**而非 source-grep 守护，每次"代码 + 文档"同步提交都可能漂移。
2. **事实声明靠单一 source-of-truth**——比如 `cache_key` 7 字段靠 `tests/imagingLogic.test.ts` 与 `tests/backendState.test.py` 的 source-grep 守护，崩了能发现；但"4 端点 smoke test"没有 source-grep 守护，所以漂移 7 天没人发现。
3. **打包过程是文档一致性审查的好契机**——把代码真的跑一遍，发现不一致，比"为同步而同步"更可靠。

## 二、4 个本地 nnUNet 路径硬编码 → 评审机器不通用

**背景**：`server/main.py:39-45` 之前把 `NNUNET_RAW` / `NNUNET_PREPROCESSED` / `NNUNET_RESULTS` / `nnunetv2_files` 这 4 个本地路径常量硬编码为 `PROJECT_ROOT / "nnUNet_*"`（`PROJECT_ROOT = ROOT.parent`，即**仓库父目录**）。`PROJECT_ROOT.parent` 在不同评审机器上不一定存在 `nnUNet_raw/` 等子目录——评审机器把仓库放任意目录都会报 `missing`。

**修复**：本轮加 5 个 env var override（`SEGMENTATION_NNUNET_RAW` / `_PREPROCESSED` / `_RESULTS` / `_PYTHON` / `_FILES`），fallback 到原硬编码路径。改动**纯加法**——不删任何代码路径，不改 4 文件 gating 检查。

**lesson**：`PROJECT_ROOT` 是仓库外的约定（依赖父目录布局），不是仓库内的约定——这种**软依赖**评审机器不通用。后续应把"评审机器可任意布局"作为硬性不变量（CLAUDE.md 顶部加一条："`PROJECT_ROOT` 之外的所有路径必须 env var 可覆盖"）。

## 三、`server_inference.py` 6 个 server 路径默认值硬编码作者个人 Linux 路径

**背景**：`server_inference.py:60-77` 之前把 6 个 server 模式路径（`SEGMENTATION_SERVER_NNUNET_RAW` / `_RESULTS` / `_PREPROCESSED` / `_EVALUATE_SCRIPT` / `_OUTPUT_ROOT` / `_DATASET_JSON` / `_LABELS_DIR`）默认值硬编码为 `/mnt/data0/LUO_Zheng/...`——**作者个人 Ubuntu 服务器路径 + 姓名泄漏**。`/api/health.model_status.server_inference` 序列化进 JSON，评审打开健康检查就能看到作者姓名。

**修复**：默认值改为占位符字符串 `<需设置 SEGMENTATION_SERVER_* 环境变量>`。`evaluate_script` / `labels_dir` 占位符在 dataclass 构造时识别为 None，不出现在 JSON。`tests/backendState.test.py` 31 处 fixture 同步替换 `LUO_Zheng` → `user_eval`（保留路径模板与 Linux 服务器目录结构，仅替换用户名）。

**lesson**：作者姓名、个人 Linux 服务器路径这类**身份信息**不应该出现在默认值——默认值要么是"明显的占位符"（如 `<需自填>`），要么是 `None`，要么是 `Path.cwd()` 这类**与开发者无关**的路径。`server_required_files` 检查是触发条件，不依赖默认值存在——所以默认 None / 占位符不影响健康检查正确性。

## 四、`tests/backendState.test.py` 被 PowerShell `Set-Content` 引入 UTF-8 BOM

**背景**：本轮用 `Set-Content -Encoding utf8` 修改 test 文件，PowerShell 默认给文件加了 UTF-8 BOM (`U+FEFF`)。Python 3.11 解析时报 `SyntaxError: invalid non-printable character U+FEFF`。原本的 31 处 `LUO_Zheng` 替换工作做完，但因为 BOM 导致测试套件在评审机器上根本 import 不了。

**修复**：用 `[System.IO.File]::WriteAllText($f, $content, $utf8NoBom)` 强制无 BOM 重写。

**lesson**：跨平台工具链差异——PowerShell 默认 utf8 = utf8-BOM；Linux `WriteAllText` 默认无 BOM。如果未来要支持 PowerShell 编辑测试文件，要么在 CI 加 BOM 检测，要么统一要求 `core.quotepath off` + LF。

## 五、`examples/reference_cases.json` 与所有 md 描述的 4 例参考病例一致

**证据**：`examples/reference_cases.json` 真实包含 4 例：`amos_0117` / `flare22_tr_0009` / `word_case` / `abdomenct1k_case`。与 CLAUDE.md / AGENTS.md / README.md / docs/quickstart-launch-guide.md / docs/local-cache-demo-runbook.md / docs/demo-day-checklist.md 描述完全一致。

**审计方法**：`ConvertFrom-Json` 解 JSON → `.samples.Count` → 逐条打印 id 与 name → 与文档描述交叉对比。**未修改任何内容**。

## 六、`build_prediction_cache_key()` 仍是 7 字段

**证据**：`server/main.py:1942-1960` 函数体：

```python
payload = {
  "input_sha256": input_sha256,
  "checkpoint_sha256": get_checkpoint_sha256(),
  "checkpoint_dataset_name": state.get("checkpoint_dataset_name"),
  "checkpoint_configuration": state.get("checkpoint_configuration"),
  "labels_source": state.get("labels_source"),
  "runtime_target": normalize_runtime_target(str(runtime_target)) if runtime_target else normalize_runtime_target(),
  "inference_options": state.get("inference_options") or get_inference_options(),
}
```

与 CLAUDE.md 顶部不变量、`docs/local-cache-demo-runbook.md` §cache_key 字段、`SEGMENTATION_RECENT_ROUNDS.md` 一致。**未修改**。

## 七、commit hash 引用全部真实

**审计范围**：9 份 md 提到的 commit hash（`76bb1ff` / `23e0c4d` / `30b0068` / `5a937d5` / `5d84e24` / `645854e`）全部能在 `git log` 中找到：

- `30b0068` 2026-06-11 docs(planning): record README split + GitHub About area walkthrough (6-11)
- `5a937d5` 2026-06-11 docs: split README.md into showcase + engineering-detail (6-11)
- `5d84e24` 2026-06-11 docs: add quickstart-launch-guide + sync 9 core docs + new planning topic (6-11)
- `645854e` 2026-06-07 refactor(exportReport): remove dead remap-banner CSS + add 6-04 source-grep guards
- `af93e21` 2026-06-07 docs: fix B1-B4 descriptions in REVIEW / RECENT_ROUNDS / AGENTS to match 6-07 real implementation
- `76bb1ff` 2026-06-06 fix(sse): B1 heartbeat percent guard + B2 cancel priority + B4 EventSource retry
- `23e0c4d` 2026-06-06 feat: demo-day wrapup — B1-B4 fixes + start_local_demo + server gating 6 paths

**未修改**。

## 八、4 项 next-round 候选**不在本轮范围**

`.planning/next-round-candidates/explanation.md:35-40` 列出的 4 项待办（高分辨率推理优化 / 5-fold 提分 / 服务器 AMOS-FLARE 显式 taxonomy 复跑 / 跨数据集 cache 链路产品化）都**不在本轮范围**——本轮只做"文档一致性巡检 + 提交包打包"。**未修改**。