# 影像量化分析计算说明

## 目标定位

当前版本的影像量化分析采用**纯前端 CPU 方案**：在前端获得分割结果 NIfTI mask 后，直接基于 mask 中的 label 体素分布和 NIfTI spacing 自动计算器官级量化指标，并写入评估面板、报告预览和 HTML/JSON/PDF 标准化报告。

该方案不修改后端推理、SSE、缓存、validation 或 job summary 逻辑。后端仍只负责原有 nnUNetv2 推理、结果下载和标签验证；量化计算发生在前端拿到 `resultImage.volume` 之后。

## 数据来源

前端量化模块读取的是分割结果体数据：

```text
resultImage.volume
```

可以理解为一个三维 label 数组：

```text
[x, y, z] → label id
```

同时 NIfTI volume 提供物理体素间距：

```text
spacingX, spacingY, spacingZ
```

例如 `0.8 × 0.8 × 2.5 mm` 表示一个体素对应真实空间中的 `0.8 × 0.8 × 2.5 mm³`。

主要实现位置：

- `src/imaging/quantification.ts`
- `src/main.tsx`
- `src/report/exportReport.ts`
- `tests/quantification.test.ts`

## 前端计算流程

前端对整个 mask 做一次 O(voxels) 单次遍历：

```text
for every voxel:
  label = mask[x, y, z]
  if label belongs to configured organs:
    update organ stats
```

每个器官累计：

- `voxelCount`：该 label 的体素数。
- `minX / maxX`：x 方向包围盒边界。
- `minY / maxY`：y 方向包围盒边界。
- `minZ / maxZ`：z 方向包围盒边界。
- `axialCounts[z]`：每个 z 切片上该 label 的体素数。

这样可以避免为每个器官重复扫描整个体数据。

## 指标计算方法

### 1. 体素数

体素数直接来自 label 计数：

```text
voxelCount = count(mask == label)
```

例如肝脏 label 为 `6`，则统计所有值为 `6` 的体素。

### 2. 器官体积

体积公式：

```text
volumeMl = voxelCount × spacingX × spacingY × spacingZ / 1000
```

其中：

- `spacingX × spacingY × spacingZ` 是单个体素体积，单位 mm³。
- `1000 mm³ = 1 ml`。

这是当前最可靠的量化指标，因为它直接来自自动分割 mask 和 NIfTI 物理间距。

### 3. 三维包围盒尺寸

每个方向的物理尺寸：

```text
bboxX = (maxX - minX + 1) × spacingX
bboxY = (maxY - minY + 1) × spacingY
bboxZ = (maxZ - minZ + 1) × spacingZ
```

单位为 mm。

### 4. 最大轴向截面积

当前计算最大 axial 横断面积：

```text
for each z slice:
  sliceArea = count(mask[:, :, z] == label) × spacingX × spacingY

maxAxialAreaMm2 = max(sliceArea)
```

单位为 mm²。

这表示器官在所有横断面中面积最大的那一层。

### 5. 头足向长度估算

当前长度估算使用 z 方向包围盒长度：

```text
estimatedLengthMm = (maxZ - minZ + 1) × spacingZ
```

它适合作为腹部器官在头足方向的保守长度估算，但不是中心线长度。

### 6. 三维最长径估算

当前最长径使用三维包围盒三个方向中的最大值：

```text
maxDiameterMm = max(bboxX, bboxY, bboxZ)
```

这是快速、可解释的整体跨度估算，不等同于严格的三维 Feret diameter。

## 管腔截面积解释

当前前端统一计算的是“最大轴向截面积”。不同器官的解释不同。

### 血管类标签

对主动脉 `aorta`、下腔静脉 `ivc`：

```text
最大轴向截面积可作为血管管腔截面积近似。
```

原因是这类 label 本身接近血管区域，最大横断面积可以作为管腔面积的近似表达。

### 空腔器官

对胃、胆囊、食管、十二指肠、膀胱等：

```text
当前为整体器官截面积估算，不等同于真实管腔截面积。
```

原因是当前 AMOS/FLARE 类标签通常是整体器官 mask，不区分器官壁、管腔和内容物。

## 壁厚处理

当前版本不输出壁厚数值。

原因：壁厚需要至少区分两个边界：

```text
外壁边界
内腔边界
```

但当前多器官分割标签主要是整体器官区域，不提供壁/腔分离标签。如果直接从整体 mask 推断壁厚，临床含义不可靠，容易误导。

因此 UI 和报告中只输出状态：

```text
当前标签未区分壁/腔，暂不输出壁厚数值。
```

## 标准化报告接入

报告导出中新增 `quantification` 字段，JSON schema 从 `1.0` 升级到 `1.1`。

HTML/PDF 报告新增“影像量化分析”章节，包含：

- 器官名称
- 体积
- 最大横断面积
- 估算长度
- 最长径
- 体素数
- 管腔解释

报告说明中保留边界：

```text
体积、截面积和长度由自动分割 mask 与 NIfTI spacing 估算；壁厚、精确管腔面积、中心线长度属于后续扩展。
```

## 当前方案的优点

1. **不改后端**：不影响原有 nnUNetv2 推理、SSE、缓存和 validation 流程。
2. **可解释**：每个指标都有明确公式和数据来源。
3. **低风险**：只依赖已加载到前端的 mask 和 spacing。
4. **可测试**：核心逻辑在纯函数模块中，可用 synthetic mask 做单元测试。
5. **符合赛题方向**：覆盖器官体积、截面积、长度估算和标准化报告生成。

## 当前限制

1. 长度是 z 向包围盒估算，不是器官中心线长度。
2. 最长径是包围盒最长边，不是严格三维最大径。
3. 非血管空腔器官的最大横断面积不是精确管腔面积。
4. 当前标签体系不支持壁厚计算。
5. 如果分割 mask 存在远处小假阳性，包围盒长度和最长径可能被拉大。

## 后续精度优化路径

### 1. 连通域清理

对每个器官只保留最大连通域，删除小孤岛。

收益：

- 减少假阳性对体积、包围盒和长度估算的影响。
- 尤其适合肝、脾、肾、胰腺等单器官结构。

### 2. PCA 主轴长度

收集器官体素坐标，计算主方向，并取体素点在主轴上的投影跨度。

收益：

- 比单纯 z 向长度更适合倾斜器官。
- 可用于肾脏、胰腺、主动脉、下腔静脉等结构的长轴估算。

### 3. 中心线长度

对食管、十二指肠、血管等管状结构，后续可做 skeleton / centerline 提取。

收益：

- 更接近管状结构真实走行长度。

代价：

- 算法复杂度更高。
- 对 mask 连续性和拓扑质量要求更高。

### 4. 精确三维最大径

后续可基于表面点、凸包或采样近似计算 3D Feret diameter。

收益：

- 比 `max(bboxX, bboxY, bboxZ)` 更接近真实最大径。

代价：

- 直接全点对全点距离复杂度高，需要近似或加速。

### 5. 形态学参数

可扩展：

- 表面积
- 球形度
- 紧致度
- elongation
- flatness
- 体积/包围盒比
- slice-wise 面积变化

这些指标更贴近赛题中“形态参数”的扩展方向。

### 6. 真正壁厚和精确管腔面积

需要新增标签或额外模型：

- 器官壁 label
- 管腔 label
- 内容物 / 空气 label
- 病灶 label

有了壁/腔分离后，才能可靠计算：

```text
壁厚 = 外壁边界到内腔边界的局部距离
管腔面积 = 管腔 label 在每层 slice 的面积
狭窄率 = 最小管腔面积 / 参考正常管腔面积
```

## 后续速度优化路径

### 1. Web Worker

把量化计算从 React 主线程移到 Web Worker。

收益：

- 大体积 CT 计算时页面不卡顿。
- 可以在 UI 上显示量化计算状态。

### 2. TypedArray 快路径

当前实现为兼容多种 NIfTI datatype，使用 DataView 读取体素。后续可针对常见 mask 类型做快路径：

- `Uint8Array`
- `Int16Array`
- `Uint16Array`

收益：

- 降低逐体素读取开销。
- 提升大体积 mask 遍历速度。

### 3. 分块 / 增量计算

按 z slice 或固定体素块分批处理：

```text
处理若干 slice
让出主线程
继续下一批
```

收益：

- 即使暂不引入 Worker，也能减少 UI 卡顿。
- 可显示量化计算进度。

### 4. 结果缓存

当前 `useMemo` 已避免同一个 `resultImage.volume` 重复计算。后续还可以把量化摘要缓存到：

- 前端 session state
- IndexedDB
- 后端 job summary（若未来允许修改后端）

## 推荐后续优先级

建议后续优化顺序：

1. Web Worker：先解决大体积 CT 可能造成的 UI 卡顿。
2. 连通域清理：提升体积、长度和最长径稳定性。
3. PCA 主轴长度：提升器官长度估算精度。
4. 管状结构中心线：增强食管、十二指肠、血管等结构的长度指标。
5. 新增壁/腔标签模型：再做真正壁厚、精确管腔面积和狭窄率。

## 验证建议

基础验证：

```bash
node tests/quantification.test.ts
npm run build
npm test
```

UI 验证：

1. 启动前端和后端。
2. 导入 CT 原图和分割结果，或运行在线分割。
3. 进入“评估”模块，检查“影像量化分析”面板。
4. 打开报告预览，检查量化表。
5. 分别导出 HTML / JSON / PDF，确认量化字段和说明存在。
