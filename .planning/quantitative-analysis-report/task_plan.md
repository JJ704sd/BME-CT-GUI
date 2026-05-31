# 影像量化分析与标准化报告规划

## Context

赛题文本明确给出“影像量化分析题”：完成肺部、腹部 CT 影像中单个或多个指标的自动量化计算，并生成标准化报告；可选指标包括各器官体积、壁厚、管腔截面积、长度，以及病灶大小、体积、形态参数等。当前项目已经具备腹部 CT NIfTI 导入、三正交浏览、nnUNetv2 自动分割、标签验证、报告预览与 HTML/JSON/PDF 导出，因此下一轮最自然的功能丰富方向是：基于已有分割 mask 自动计算可解释的量化指标，并把结果写入评估面板和标准化报告。

本规划只面向后续持续跟进；第一阶段明确采用**纯前端 CPU 量化方案**，不修改后端推理、SSE、缓存、validation 或 job summary 逻辑。

## 当前项目可复用基础

- `src/main.tsx`
  - 已有“项目 / 数据 / 分割 / 评估 / 报告”模块。
  - 已有 `LoadedImage.volume`、`resultImage`、`validationSummary`、`organs`、`measurements`、报告预览和 `handleExport()`。
  - 当前测量点仍偏演示性质，可作为“人工测量/复核点”保留。
  - 第一阶段只需新增前端量化 summary 计算与展示，不改后端。
- `src/organLayerLogic.ts`
  - `OrganLayer` 已有 `volume: string` 字段，目前多为“待测量”或演示值，适合改成真实量化结果展示。
- `src/report/exportReport.ts`
  - 已支持 HTML / JSON / PDF 三种报告导出。
  - 报告已有概览、验证指标、逐标签指标、器官列表、关键发现、测量点、推理时间线。
  - 第一阶段只扩展前端报告结构，不动后端 job summary。
- `src/imaging/sliceRenderer.ts`
  - 已有 `NiftiVolumeLike`、体素 spacing、`getVoxelValue()` / `getLabelAtVoxel()`，可复用为 mask 统计基础。
- `src/imaging/voxelMapping.ts`
  - 已有体素坐标、方向视图、spacing 相关逻辑，可保持只读复用。
- `src/inference/inferenceClient.ts`
  - `ValidationSummary.labels` 已承接 label、名称、预测体素数等字段，可后续扩展前端类型。
- 测试
  - TypeScript 测试直接用 Node + `node:assert`。
  - 可新增 `tests/quantification.test.ts` 或合入 `tests/imagingLogic.test.ts`。
  - 第一阶段不需要改 `server/main.py`。

## 推荐第一阶段范围

优先做**基于分割 mask 的器官级量化**，不做需要额外标签或复杂中心线算法的临床指标伪实现。

第一阶段建议自动计算：

1. 各器官体素数。
2. 各器官体积：`voxel_count * spacingX * spacingY * spacingZ / 1000`，单位 ml。
3. 三维包围盒尺寸：x / y / z 方向物理尺寸，单位 mm。
4. 最大轴向截面积：逐 z 切片统计该 label 的最大面积，单位 mm²。
5. 头足向长度估算：用 z 方向包围盒长度作为保守估算，单位 mm。
6. 三维包围盒最长径：`max(bboxX, bboxY, bboxZ)`，作为整体器官最大径估算。
7. 管腔解释字段：主动脉、下腔静脉等血管类标签的最大轴向截面积可标注为“管腔截面积近似”；胃肠、胆囊、膀胱等空腔器官只能标注为“器官整体截面积估算”。
8. 壁厚状态字段：当前标签体系未区分壁/腔，不输出壁厚数值，只输出“需专用壁/管腔标签”。
9. 每个指标附带状态：`computed` / `empty` / `unavailable`。
10. 报告说明：体积、截面积、长度来自自动分割 mask 与 NIfTI spacing；壁厚和真实管腔指标需要专用壁/管腔标签或后续算法。

这样可以直接呼应赛题“各器官体积、管腔截面积、长度的计算或估算”，同时保持诚实边界。

## 不建议第一阶段直接做的内容

### 壁厚

当前 AMOS/FLARE 多器官标签主要是器官整体区域，不区分胃肠壁、管腔、内容物或病变边界。若直接从整体 mask 推壁厚，临床含义不可靠。建议第一阶段只在报告中说明：

- 壁厚指标需要胃肠壁/管腔分离标签，或额外边界/中心线算法。
- 当前版本不生成壁厚数值，避免误导。

### 管腔截面积

主动脉、下腔静脉等血管标签可近似看作管腔/血管区域，最大轴向截面积可作为“截面积估算”。但胃、肠、胆囊、膀胱等空腔器官的整体标签不等于管腔标签。建议：

- 第一阶段统一输出“最大轴向截面积”。
- 对主动脉、下腔静脉可标注“可作为管腔截面积近似”。
- 对胃肠等器官标注“需专用管腔标签”。

### 中心线长度

食管、十二指肠等管状结构更适合 skeleton/centerline 长度，但实现和验证成本更高。第一阶段先用 z 向包围盒长度估算，报告中明确“长度估算”。

## 推荐实现步骤

### Phase 1：纯函数量化模块

新增 `src/imaging/quantification.ts`。

建议类型：

```ts
type QuantificationStatus = "computed" | "empty" | "unavailable";

type OrganQuantification = {
  label: number;
  id: string;
  name: string;
  voxelCount: number;
  volumeMl: number | null;
  bboxMm: { x: number; y: number; z: number } | null;
  maxDiameterMm: number | null;
  maxAxialAreaMm2: number | null;
  estimatedLengthMm: number | null;
  lumenAreaInterpretation: string;
  wallThicknessStatus: string;
  status: QuantificationStatus;
  note: string;
};

type QuantificationSummary = {
  status: QuantificationStatus;
  spacingMm: { x: number; y: number; z: number } | null;
  organs: OrganQuantification[];
  note: string;
};
```

建议函数：

- `summarizeSegmentationQuantification(maskVolume, labels)`
- `formatQuantificationValue(value, unit)`
- `getLumenAreaInterpretation(organId)`
- `getWallThicknessStatus(organId)`

设计约束：

- 只依赖 mask volume 和 label 表。
- 不读取 DOM，不修改 React state。
- spacing 缺失或不合法时返回 `unavailable`。
- label 未出现时返回 `empty`，不要报错。
- 保持 O(voxels) 单次遍历，避免为每个 label 重复扫全 volume。

### Phase 2：接入前端 UI

修改 `src/main.tsx`。

建议方式：

1. 基于 `resultImage?.volume` 和 `modelLabels` 用 `useMemo` 生成 `quantificationSummary`。
2. 生成 `quantificationById` 方便按器官查找。
3. 将器官列表中的 `organ.volume` 展示更新为真实体积文本，例如 `1421.3 ml`。
4. 在“评估”模块增加“影像量化分析”面板：
   - 总状态：等待分割结果 / 已计算 / 无前景标签 / spacing 不可用。
   - 展示前若干个已计算器官：体积、最大横断面积、估算长度、最长径。
   - 对主动脉/下腔静脉提示“可作为管腔截面积近似”；对胃肠等提示“整体器官截面积，不等同于真实管腔”。
   - 壁厚统一显示“当前标签未区分壁/腔，暂不输出数值”。
5. 报告预览 modal 增加“量化指标”小表。
6. 不改变已有推理、SSE、下载、缓存、validation 的逻辑。

### Phase 3：扩展报告导出

修改 `src/report/exportReport.ts`。

建议：

1. `ReportData` 增加 `quantification: QuantificationSummary`。
2. HTML/PDF 增加“影像量化分析”章节。
3. JSON 导出：
   - `schema_version` 从 `1.0` 升级到 `1.1`。
   - 新增 `quantification` 字段。
   - 保留原字段，避免破坏已有报告消费者。
4. 报告 footer 或章节说明中写明：
   - 当前量化结果由自动分割 mask 与 NIfTI spacing 估算。
   - 壁厚、精确管腔面积、中心线长度属于后续扩展。

### Phase 4：后续可选后端持久化（本阶段不做）

第一阶段明确不修改后端逻辑。若未来希望后端 job summary 也保留量化摘要，可另起任务扩展 `server/main.py`：

1. 从 nibabel 读取预测 NIfTI header zooms。
2. 在 `compute_label_metrics()` 或独立函数中加入 `prediction_volume_ml`。
3. 写入 `validation_summary.json` / `job_summary.json`。
4. 前端仍可独立从 result mask 计算，后端字段只作为持久化补充。

本轮实现不做后端增强，避免影响已有推理、SSE、缓存和 validation 链路。

## UI 文案建议

- 面板标题：`影像量化分析`
- 状态文案：
  - `等待分割结果后自动计算体积、截面积和长度估算。`
  - `已基于分割 mask 自动计算器官量化指标。`
  - `NIfTI 体素间距不可用，无法换算物理量。`
- 表头：
  - `器官`
  - `体积`
  - `最大横断面积`
  - `估算长度`
  - `体素数`
- 说明：
  - `体积、截面积和长度由自动分割 mask 与 NIfTI spacing 估算；壁厚和精确管腔指标需专用标签或后续算法。`

## 测试计划

### TypeScript 纯函数测试

新增 `tests/quantification.test.ts` 或加入 `tests/imagingLogic.test.ts`：

1. synthetic 3D mask：确认体素数正确。
2. spacing = `2 x 3 x 4 mm`：确认体积 ml 正确。
3. 多 slice label：确认最大轴向面积正确。
4. bbox：确认 x/y/z 物理尺寸和 z 向估算长度正确。
5. 缺失 spacing：返回 `unavailable`。
6. label 不存在：返回 `empty`。

### 构建与回归

建议命令：

```bash
npm run build
npm test
```

### UI 验证

1. 启动前端：`npm run dev -- --port 5173`。
2. 导入 CT 和分割结果 NIfTI。
3. 进入“评估”模块，确认出现量化面板。
4. 进入“报告”模块，打开报告预览，确认量化表存在。
5. 分别导出 HTML / JSON / PDF，确认量化字段和中文说明存在。

## 风险与护栏

- 不修改 nnUNetv2 推理命令、cache key、SSE 主流程。
- 不把壁厚、胃肠管腔面积写成已可靠完成的临床指标。
- 不依赖 `server/work/` 或 `nnunetv2_files/` 的本地私有数据作为源代码逻辑。
- 新逻辑优先放纯函数模块，避免继续膨胀 `src/main.tsx`。
- 报告中必须保留“估算”和“需复核”边界，避免过度承诺。

## 持续跟进清单

- [x] 新增纯函数量化模块。
- [x] 新增量化单元测试。
- [x] 前端“评估”模块接入量化面板。
- [x] 报告预览接入量化表。
- [x] HTML/JSON/PDF 报告导出接入量化字段。
- [ ] 后续如确有需要，再另起任务扩展后端 job summary 持久化量化字段。
- [x] README / ACCEPTANCE / REVIEW 中同步新增功能边界。

## 推荐优先级

建议把本任务放在 `.planning/next-round-candidates/task_plan.md` 的“显式标签体系选择与 server gating 修复”之后执行。原因：当前服务器推理链路和标签体系修复仍影响正式质量基线；量化功能可以并行开发，但正式报告展示最好建立在明确的 label taxonomy 和可靠分割结果之上。

*创建日期：2026-05-31*
