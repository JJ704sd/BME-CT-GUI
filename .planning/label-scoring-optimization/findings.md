# 标签打分优化 — 发现记录

## 2026-05-27：标签文件传输 bug

**现象：** 用户通过"导入标签 CT"按钮选择文件后运行推理，后端 `label_path: null`，validation 未执行。

**排查过程：**
1. 前端 `labelFile` 状态曾通过临时日志确认正确；2026-05-29 已移除上传文件名日志，后续不再用控制台文件名作为验收证据。
2. 后端 `create_job()` 接收 `label_file: UploadFile | None = File(None)` 参数
3. 后端 job 目录无 `label/` 子目录，`job_summary.json` 中 `label_path: null`
4. 当时添加后端临时排查日志并重启服务后，标签文件正常传输；该类日志会暴露文件名，已在 2026-05-29 移除。

**根因分析：**
- `UploadRole = "source" | "result"` 不含 `"label"`，拖拽不支持标签文件
- 用户可能通过"导入分割结果"加载标签 NIfTI，文件进入 `resultImage` 而非 `labelFile`
- 原始按钮路径代码逻辑正确，但缺乏拖拽支持和缺失提示

**修复：**
- 扩展 `UploadRole` 为 `"source" | "result" | "label"`
- `processVisualizationFile()` 增加 `role === "label"` 分支
- 数据操作面板新增"标签 CT 导入"拖放区域
- `startSegmentation()` 中 `labelFile` 为 null 时 toast 提示
- 观察标签链路时检查 job state、`label_path` 和 validation summary，不保留上传文件名 `console.log`

## 2026-05-27：taxonomy 错位导致 Dice 无意义

**现象：** FLARE22 在线验证 mean_dice=0.073，但离线 remap 后 mean_dice=0.893。

**根因：** AMOS22 checkpoint 的 label ID 与 FLARE22 标签 ID 语义完全不同：
- AMOS22: 1=脾脏, 2=右肾, 3=左肾, 4=胆囊, 5=食管, 6=肝脏, 7=胃, 8=主动脉, 9=下腔静脉, 10=胰腺, 11=右肾上腺, 12=左肾上腺, 13=十二指肠
- FLARE22: 1=肝脏, 2=右肾, 3=脾脏, 4=胰腺, 5=主动脉, 6=下腔静脉, 7=右肾上腺, 8=左肾上腺, 9=胆囊, 10=食管, 11=胃, 12=十二指肠, 13=左肾

只有 label 2（右肾）两边语义一致，Dice=0.945。其余 ID 语义错位，Dice≈0。

**`taxonomy_match: True` 的误判：** `validate_against_custom_label()` 只检查了标签 ID 集合是否有交集（两边都有 1..13），未做语义级匹配。

## 2026-05-28：自动 taxonomy remap 结果

**实现结论：** `server/taxonomy.py` 已把 taxonomy 处理从“人工解释”推进到“后端自动检测并重映射”。FLARE22 标签上传后，后端会按器官名建立 FLARE22 ID → AMOS22 ID 的映射，再计算 validation。

**验证数据：**
- job `a717dacf42d3`
- 病例：FLARE22 Tr 0009
- `remap_applied=true`
- `remap_source=FLARE22`
- `mean_dice=0.926`
- validation 状态：`passed`

**解释边界：** 自动 remap 让跨数据集在线验证可解释，但它仍不是 AMOS 原生标签验证；后续新增数据集时必须补标签定义、别名映射和测试。

## 2026-05-29：缓存 validation 与部分标签边界

- 缓存命中只复用预测 NIfTI，validation 按当前请求重新计算；同一 CT 换标签文件不会再显示缓存来源 job 的旧 Dice。
- FLARE22 部分标签在 `match_count == 0` 且至少两个 ID 明确语义错位时可自动 remap。
- 单 label 文件仍保持保守处理，需要后续显式数据集 hint 或人工确认。
- 前后端上传文件名调试日志已移除；排查标签传输应使用 job id、`label_path`、validation summary 和测试结果。

## 2026-05-27：AMOS vs FLARE22 推理耗时差异

**数据：** AMOS 0117 (568 层) 1054s vs FLARE22 Tr 0009 (87 层) 214s。

**分析：** 耗时与体素数近似线性。AMOS ~149M 体素 vs FLARE22 ~23M 体素，比例 6.5x，耗时比例 4.9x。GPU 在两种情况下都达到 100% 利用率和 ~7.8 GiB 显存。

## 2026-05-27：上传数据量上限

**结论：** 无框架级硬限制。
- FastAPI/Starlette `MultiPartParser` 的 `max_part_size=1MB` 只对表单字段生效，文件上传（`UploadFile`）流式写入磁盘，无大小限制
- Vite 开发服务器无代理请求大小限制
- 前端浏览器 File API 使用引用，FormData 传输时才读入内存
- 实际瓶颈：可用 RAM + 磁盘空间
