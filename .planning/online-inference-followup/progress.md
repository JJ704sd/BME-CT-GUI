# 在线推理后续进度

## 2026-05-25

- 创建下一轮在线推理后续规划文件。
- 确认当时分支为 `codex/update-ct-gui-prototype`。
- 确认最新已推送提交为 `ed5cf86 docs: record quality inference comparison`。
- 创建规划文件前确认工作树干净。
- 记录产品策略：`quality` 是正式/默认路径，`fast` 只作快速预览并必须标注“需人工复核”。
- 下一步计划：实现用户可见的推理模式选择，并把所选 profile 写入 job state 和结果摘要。

## 2026-05-25 后续实现

- 完成 Phase 1 产品化推理模式选择：
  - 前端“分割控制”暴露 `质量推理` / `快速预览`，默认 `quality`。
  - 快速预览显示可见的 `需人工复核` 警告，fast 结果元信息不会被误认为正式质量输出。
  - `createInferenceJob()` 每次 job 都发送 `inference_profile`。
  - 后端 `/api/segment/jobs` 将请求级 `quality` / `fast` 解析为最终 `inference_options`。
  - 最终参数写入创建响应、job state、SSE complete 事件、`job_summary.json` 和 cache key 输入。
- 更新 `README.md`、`REVIEW.md` 和 `SEGMENTATION_METRICS_SUMMARY.md`，记录产品化模式选择且不改变基准结论。
- 完成验证：
  - `node tests/imagingLogic.test.ts`
  - `python tests/backendState.test.py`（使用隔离 `SEGMENTATION_TEST_TMP`）
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' test`
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' run build`
- 剩余计划：检查 git diff，然后提交并推送后续工作。

## 2026-05-25 main 基线收口

- 确认当前活动分支为 `main`，跟踪 `origin/main`。
- 确认可选推理 profile 工作当时已合并并推送，提交为 `838e77e merge selectable inference profiles`；当前主分支基线见 2026-05-29 补记。
- 更新后续计划，让剩余工作从基准记录纪律、后处理实验门禁和更广泛参考病例验证开始，而不是重复 Phase 1。
- 计划运行基线验证：
  - `npm test`
  - `npm run build`
- 已完成验证：
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' test` 退出码 0。
  - `npm --prefix 'D:\BME2026\BME_CT_Seg\segmentation-gui-prototype' run build` 退出码 0；Vite 构建 `1595` 个模块，用时 `5.04s`。
- `git status --short` 当时只显示 `.planning/online-inference-followup/` 下的规划文件改动。

## 2026-05-28 文档刷新补记

- 将本规划文件主体改为中文，保留必要英文技术字段和命令名。
- 补充自动 taxonomy remap、报告导出和远程部署作为下一轮在线推理相关背景。

## 2026-05-29 历史 bug 收口补记

- 当前主分支基线为 `dafe400 fix: close segmentation validation regressions`。
- 预测缓存和 validation 语义已拆开：缓存命中仍能快速回填 NIfTI，但当前标签的 Dice 需要重新计算。
- persistent worker 的 stdout reader 改为共享队列；后续仍需真实无缓存连续推理对照来评估速度。
