# GUI 原型审阅与改造建议（现状版）

> 基于 `segmentation-gui-prototype` 当前代码、运行中的本地服务以及 `nnunetv2_files` 资源整理。
> 目标是把这个原型收敛成一个可浏览 CT、可联动三正交视图、可点击器官说明、可连接本地分割后端的工作型 GUI。
> 当前结论：前端已经具备三正交浏览和 13 类器官说明，后端已接入本地 nnUNetv2 model folder 与真实推理命令，并会在配置不完整时明确拒绝创建任务；真实大体积作业仍需在本机服务运行态下做耗时验证。

---

## 一、现状总览

### 1.1 技术栈

| 项目 | 当前状态 |
|---|---|
| 前端 | React 19 + TypeScript + Vite |
| 医学图像 | `nifti-reader-js`，支持 `.nii` / `.nii.gz` |
| 普通图片 | PNG / JPG / WebP |
| 图标 | `lucide-react` |
| 样式 | `src/styles.css` 单文件 |
| 主入口 | `src/main.tsx` |
| 三正交视图 | `src/components/OrthogonalViewer.tsx` |
| 体素/切片映射 | `src/imaging/voxelMapping.ts` |
| NIfTI 切片渲染 | `src/imaging/sliceRenderer.ts` |
| 器官说明 | `src/data/organDetails.ts` |
| 推理客户端 | `src/inference/inferenceClient.ts` |
| 后端桥接 | `server/main.py` |
| 测试脚本 | `package.json` 已配置 `test` |

### 1.2 本地资源

`nnunetv2_files` 当前可见：

| 资源 | 说明 |
|---|---|
| `checkpoint_best.pth` | 模型权重文件 |
| `amos_0117(3).nii.gz` | AMOS 0117 参考病例原始 CT |
| `amos_0117(2).nii.gz` | AMOS 0117 参考病例标准答案 |
| `amos_0117_original.nii/` | 目录型解压参考病例，不是直接可读的单一文件 |
| `amos_0117_label.nii/` | 目录型解压标准答案，不是直接可读的单一文件 |

这些资源可用于演示和调试，但不能自动等同于完整、可验证的 nnUNetv2 生产结果目录。

### 1.3 运行态

- 前端可在 `http://127.0.0.1:5173` 访问。
- 后端健康检查可在 `http://127.0.0.1:8000/api/health` 访问。
- 当前后端会根据模型资源返回 `real-nnunetv2` 或 `unavailable`。本机检测到 `dataset.json`、`plans.json`、`fold_0/checkpoint_best.pth` 与 `nnUNetv2_predict_from_modelfolder.exe` 时为 `real-nnunetv2`。

---

## 二、已经完成的部分

### 2.1 前端图像浏览

- 已支持 NIfTI 读取、窗宽窗位、切片切换、overlay / split / side / difference 模式。
- 已有 Axial、Sagittal、Coronal 三正交视图。
- 三个视图共用同一体素坐标，不再是独立的百分比光标。
- 图片层已禁止原生拖拽和事件接管，鼠标交互由容器统一处理。

### 2.2 器官点击与说明

- 已有 `label -> organ` 的查找表。
- 已有器官说明面板。
- 点击 mask label 后可打开对应器官说明。
- 背景体素不会误弹器官说明。

### 2.3 后端桥接

`server/main.py` 目前已提供：

- `/api/health`
- `/api/models`
- `/api/samples`
- `/api/samples/{sample_id}/original`
- `/api/samples/{sample_id}/label`
- `/api/segment/jobs`
- `/api/segment/jobs/{job_id}`
- `/api/segment/jobs/{job_id}/events`
- `/api/segment/jobs/{job_id}/result`

作业创建现在会先检查本地 nnUNetv2 资源完整性。资源齐备时，后端调用 `nnUNetv2_predict_from_modelfolder.exe` 并返回输出目录中的真实结果；资源缺失时，接口返回 503，不再复制参考标签冒充分割结果。

### 2.4 测试与构建

- `package.json` 已配置 `npm test`。
- `npm test` 通过。
- `npm run build` 通过。
- 已有布局回归测试，覆盖三正交布局和关键 CSS 约束。

---

## 三、当前仍未完成或只完成一半的部分

| 目标 | 当前状态 | 结论 |
|---|---|---|
| 真实 nnUNetv2 在线推理 | 已接入本地 `nnUNetv2_predict_from_modelfolder.exe`，待实际大体积作业验证 | 部分完成 |
| 结果自动回填并替换手工导入 | 前端能接收后端结果，后端输出路径已改为真实 nnUNetv2 结果 | 基本完成 |
| 置信度阈值 | 仅保留 UI 控件，尚未与概率输出建立真实语义 | 未完成 |
| label 表稳定来源 | 后端从真实 `dataset.json` 读取，前端优先使用 `/api/models` 并保留 13 类 fallback | 基本完成 |
| 三正交桌面布局 | 已有 CSS 测试和 Playwright 盒模型回归检查 | 基本完成 |
| 三正交移动端布局 | 已有单列、高度约束和 Playwright 盒模型回归检查，仍需真机再验 | 部分完成 |
| 真实 3D 体渲染 | 目前仍是轻量预览，不是医学级 3D 工作台 | 未完成 |

---

## 四、设计要求

### 4.1 分割后端

1. 不要把“调试回退”写成“真实推理”。
2. 不要把 `volume.image` 当成完整 NIfTI 文件上传。
3. 不要把进度条当成真实任务状态，除非它来自后端 job state。
4. 不要把 SSE 文本进度和二进制结果混在一个响应里。
5. 如果模型配置不完整，要明确展示“不完整”，不要伪造成功流程。

### 4.2 三正交视图

1. 三个方向必须同时可读。
2. 不能为了“填满”而把图像拉成不自然形变。
3. 不能为了“保留物理比例”把 sagittal / coronal 压成肉眼看不清的小条。
4. 面板位置必须稳定，切片切换时不应左右漂移。
5. 鼠标拖动只能改变体素坐标，不应触发浏览器原生拖图或外层误响应。
6. 视图层级应清楚：容器负责布局，图像层负责显示，事件由容器统一接管。

### 4.3 交互与可读性

- 按钮优先使用图标或图标+短文本。
- 工具栏要紧凑，不要把屏幕切成过多互相争抢的卡片。
- 主视图区应稳定，不要因为切片变化改变页面主布局。
- 在小屏设备上，允许纵向滚动，但不要挤成不可用的缩略图。
- 文本和控件不得覆盖图像观察区域。

---

## 五、具体实现评估

### 5.1 `src/main.tsx`

职责：

- 组合整个页面。
- 管理病例、上传、结果、推理状态、报告草稿。
- 调用 `createInferenceJob()` / `downloadInferenceResult()`。

评价：

- 功能已经较多，仍然是协调层。
- 仍承担较多状态，后续适合继续拆薄，而不是继续堆逻辑。

### 5.2 `src/components/OrthogonalViewer.tsx`

职责：

- 三正交视图布局。
- 点击、滚轮、十字线联动。
- mask overlay。
- label 命中与器官说明触发。

评价：

- 方向模型是对的。
- 图片层的 pointer 处理已经隔离。
- 目前需要继续把比例和布局稳定性作为首要目标，而不是增加更多视觉效果。

### 5.3 `src/imaging/voxelMapping.ts`

职责：

- 体素坐标与切片坐标转换。
- 三方向切片尺寸计算。
- 视图显示比例计算。

评价：

- 这里是三正交视图的关键基础。
- 当前已加入显示比例钳制，避免极端病例把 sagittal / coronal 压得太窄。

### 5.4 `server/main.py`

职责：

- 健康检查。
- 模型/参考病例信息。
- 任务创建、事件流、结果下载。

评价：

- API 形状已经比较清楚。
- 执行路径已从调试回退切换到本地 nnUNetv2 model folder 调用；仍需要通过真实 CT 作业验证耗时、显存/内存占用和输出稳定性。

---

## 六、推荐的下一步

### 阶段 1：后端真实化

- 接入真正的 nnUNetv2 推理路径。
- 保留 `/api/health` 和 `/api/models`，但让它们反映真实模型状态。
- 让 `/api/segment/jobs/{job_id}/result` 返回真实模型输出。

### 阶段 2：模型配置收敛

- 明确 `dataset.json`、`plans.json`、trainer、configuration、fold 的来源。
- 把 label 映射写成单一真源，不要前端和后端各写一套不一致的表。
- 置信度阈值要么真正生效，要么降级成只读质控提示。

### 阶段 3：三正交体验收口

- 继续验证桌面、窄屏和不同病例的显示比例。
- 保证 sagittal / coronal 不窄、不挤、不漂移。
- 把点击、滚轮、拖动都限制在容器内。

### 阶段 4：测试补强

- 保留现有单测。
- 增加浏览器级布局回归检查。
- 对后端 job state 做最小集成测试。

---

## 七、验收标准

1. 上传一个完整 `.nii` 或 `.nii.gz` 后，后端能创建任务并返回真实结果，而不是参考标签复制件。
2. 三正交视图在桌面上同时可读，Sagittal / Coronal 不会瘦到看不见。
3. 三正交视图在移动端不挤压成不可用缩略图。
4. 点击 mask 非背景体素后，能显示正确器官说明。
5. 鼠标拖动和切片切换不会让页面横移或抖动。
6. `npm test` 与 `npm run build` 保持通过。
7. 后端 health/models 接口与实际模型配置一致，不输出假的“已完成”状态。

---

## 八、待确认事项

1. `checkpoint_best.pth` 对应的真实 `dataset.json` / `plans.json` / trainer / configuration / fold 是否已经齐备并且可复现。
2. 当前 label 表是否完全等同于最终要支持的器官集合。
3. `confidenceThreshold` 的最终产品语义是“真实筛选阈值”还是“质控提示阈值”。
4. 3D 预览是否要升级为真正的医学体渲染，还是仅保留轻量预览。
5. 移动端是否要优先保证纵向可读，还是要保留部分并排布局。

---

## 九、2026-05-23 继续完成记录

### 9.1 已推进

- 后端作业创建已改为检查真实 nnUNetv2 model folder：`dataset.json`、`plans.json`、`fold_0/checkpoint_best.pth` 与 `nnUNetv2_predict_from_modelfolder.exe` 缺一则返回 503，不再把参考标签复制件伪装成真实推理结果。
- 后端真实推理路径已接入 `D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\nnUNetv2_predict_from_modelfolder.exe`，并设置 `nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results` 环境变量。默认设备为 CPU，可通过 `SEGMENTATION_DEVICE=cuda` 改为 GPU。
- `/api/health` 和 `/api/models` 现在返回 `model_status`、`mode`、`missing` 与 `confidence_threshold_effective`，前端可以明确展示模型是否可用。
- 前端推理文案已区分“真实 nnUNetv2 推理结果”和“调试标签回填结果（非真实推理）”，置信度控件降级为“质控提示”，不再暗示会筛选概率输出。
- 前端 label 表已补齐到 `dataset.json` 的 13 个标签，并会优先从 `/api/models` 读取后端 label 列表，接口不可用时才使用本地 fallback。
- 新增 `tests/backendState.test.py`，并纳入 `npm test`，覆盖模型配置缺失、job 拒绝创建、真实推理命令构造。

### 9.2 仍需验证

- 尚未在本轮执行完整大体积 nnUNetv2 推理，只验证了命令路径、配置探测、测试与前端构建。实际推理耗时和 GPU/CPU 资源占用仍需用真实服务启动后验证。
- 如果要让 `confidenceThreshold` 真正生效，需要启用概率输出并定义阈值如何作用于多标签结果；当前仍是质控提示。
- 浏览器级布局回归已补齐到 Playwright 盒模型检查；真机手动验证仍未完成。

### 9.3 本轮继续完善

- 后端从 `dataset.json` 读取 label 时已对齐前端 canonical id，尤其是 `inferior vena cava -> ivc`，避免点击 label 后落入未知器官说明。
- 前端 13 类默认 label 均已配置器官说明，点击肝脏、双肾、脾脏、胰腺、主动脉、下腔静脉、双侧肾上腺、胆囊、食管、胃、十二指肠均能展示非 fallback 的说明内容。
- `/api/segment/jobs/{job_id}` 增加 `result_ready`，并在下载结果时同时确认结果文件存在，减少前端对 409 下载响应的猜测。
- 新增 `tests/browserLayout.test.ts` 与 `npm run test:browser`，使用本机 Edge/Chrome 的 Playwright 盒模型检查桌面三列、移动单列、canvas 可读尺寸、无横向溢出、图像层 `object-fit: contain` 与 `pointer-events: none`。
- `npm test` 已纳入浏览器布局测试；在受限沙箱内需要提升权限启动本机浏览器。

---

## 十、当前功能与三大目标达成度

### 10.1 当前可实现的主要功能

1. **本地 CT / NIfTI 浏览**
   - 支持载入 `.nii` / `.nii.gz` 体数据，也保留 PNG / JPG / WebP 演示图导入。
   - 支持窗宽窗位、切片切换、缩放、透明度调节、split / overlay / side / difference 对比模式。
   - 支持载入内置参考病例（当前为 AMOS 0117）原图和标准答案，便于无外部数据时演示、回归和 Dice 验证。

2. **三正交联动查看**
   - Axial、Sagittal、Coronal 三个视图共用同一体素坐标。
   - 点击、拖动、滚轮切片会更新共享坐标和十字线位置。
   - 切片坐标、体素坐标、HU 值和当前 label 会同步显示。
   - 布局上已避免 sagittal / coronal 被压成不可读窄条，并通过 CSS 与 Playwright 盒模型测试做回归保护。

3. **分割结果叠加与器官说明**
   - 可将分割 mask 作为结果图层叠加到原图上。
   - 点击非背景 mask label 后，可打开对应器官说明卡片。
   - 当前默认支持 13 类：肝脏、右肾、脾脏、胰腺、主动脉、下腔静脉、右肾上腺、左肾上腺、胆囊、食管、胃、十二指肠、左肾。
   - 前端优先使用后端 `/api/models` 返回的 label 表；后端优先从真实 `dataset.json` 读取 label。

4. **本地 nnUNetv2 后端桥接**
   - `/api/health` 返回模型资源状态、路径、缺失项和当前模式。
   - `/api/models` 返回模型状态和 label 表。
   - `/api/segment/jobs` 创建真实 nnUNetv2 推理任务；配置缺失时返回 503，不伪造成成功流程。
   - `/api/segment/jobs/{job_id}` 返回 job state、进度、阶段、错误和 `result_ready`。
   - `/api/segment/jobs/{job_id}/events` 使用 SSE 发送文本状态。
   - `/api/segment/jobs/{job_id}/result` 单独返回二进制 NIfTI 结果，避免和 SSE 文本混在同一响应。

5. **测试与构建保障**
   - `npm test` 覆盖 viewer 逻辑、imaging 逻辑、CSS 布局约束、后端状态逻辑和浏览器盒模型回归。
   - `npm run build` 可完成 TypeScript 与 Vite 生产构建。
   - 浏览器测试和 Vite 构建在受限 shell 下可能遇到 `spawn EPERM`，需要在正常权限下运行。

### 10.2 三大目标达成度

| 三大目标 | 当前达成度 | 说明 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 90% | 体数据读取、三视图联动、十字线、滚轮/点击/拖动、桌面和移动端基础布局均已完成并有自动化回归；仍建议用更多真实病例和真机屏幕做视觉验收。 |
| 器官 label 可点击并展示说明 | 约 90% | 13 类 label 表与器官说明已补齐，后端 `dataset.json` 与前端 canonical id 已对齐；后续需要用最终训练集 label 集合确认是否还会新增或改名。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 70% | API 形状、模型资源探测、真实命令调用、job state、SSE 和结果下载已完成；尚未完成真实大体积 CT 的端到端耗时验证、GPU/CPU 资源评估和失败恢复策略。 |

结论：三个主要目标的“工作型 GUI 骨架”已经到位，可以用于本地演示、参考病例浏览、三正交检查和后端推理任务发起；距离稳定交付还差真实推理压力验证、置信度语义落地和更完整的异常处理。

### 10.3 后续迭代优先级

1. **真实推理验收**
   - 用一个完整 `.nii.gz` CT 文件从页面发起推理，记录 CPU/GPU、内存、耗时、输出文件名和前端回填结果。
   - 若 CPU 推理不可接受，明确要求 `SEGMENTATION_DEVICE=cuda` 并验证 CUDA 环境。
   - 将真实作业的 stdout/stderr 摘要写入 job state 或后端日志，便于定位失败。

2. **置信度阈值语义**
   - 当前 `confidenceThreshold` 是质控提示，不会真实筛选概率输出。
   - 若要做真实阈值，需要启用 nnUNetv2 probability 输出，定义多标签概率图如何阈值化、如何处理互斥标签和后处理。
   - 若短期不做真实概率阈值，UI 应继续保持“质控提示”语义，避免误导。

3. **前端状态拆分**
   - `src/main.tsx` 仍承担病例、上传、推理、报告、布局控制等多类状态。
   - 后续建议拆出 `useCaseData`、`useInferenceJob`、`useViewerState` 等 hook 或小模块，降低主入口维护成本。

4. **真实病例和移动端验收**
   - 使用不同层厚、不同矩阵大小、不同器官标签密度的 CT 验证三正交比例。
   - 在真实移动端或窄屏设备检查纵向滚动、工具栏换行和 inspector 区域可读性。

5. **3D 预览定位**
   - 当前 3D 仍是轻量预览，不是医学级体渲染。
   - 如果项目目标是临床级观察，应单独规划基于 WebGL/volume rendering 的体渲染模块；如果只是演示，应在 UI 和文档中保持“轻量预览”定位。

---

## 十一、2026-05-23 本轮继续完善记录

### 11.1 本轮已完成

1. **内置参考病例标准答案验证链路**
   - 后端新增标准答案 Dice 计算能力：当上传内容与 `nnunetv2_files/amos_0117(3).nii.gz` 一致时，真实 nnUNetv2 推理完成后会自动读取输出结果，并与 `nnunetv2_files/amos_0117(2).nii.gz` 计算 per-label Dice、平均 Dice、最低 Dice 和前景 Dice。
   - `/api/segment/jobs/{job_id}` 会返回 `validation` 字段；SSE `complete` 事件也会携带验证摘要，前端可在“分割”和“评估”模块显示标准答案验证状态。
   - 当前验收阈值为：平均 Dice `>= 0.85` 且最低 label Dice `>= 0.70` 记为 `passed`；未达阈值为 `review`，不阻断结果下载，但提示人工复核。

2. **项目内训练权重接入**
   - 用户确认训练好的权重文件位于 `nnunetv2_files/checkpoint_best.pth`。
   - nnUNetv2 的 `predict_from_modelfolder` 仍要求权重位于 model folder 的 `fold_0/checkpoint_best.pth`，因此后端会在运行时准备 `server/work/runtime_model/nnUNetTrainer__nnUNetPlans__2d`，复用现有 `dataset.json` / `plans.json`，并把项目内权重链接或复制到 runtime model folder。
   - `/api/health` 的 `model_status` 会区分 `checkpoint_source`、`checkpoint_runtime`、`checkpoint_in_model_folder` 和 `checkpoint_source_matches_model_folder`，避免误判实际使用的权重来源。

3. **鼠标点击/拖动稳定性**
   - 坐标换算已改为只对实际图像内容区域生效；点到 `object-fit` 留白区时返回 `null`，不会再把坐标夹到边界导致十字线或切片乱跳。
   - `OrthogonalViewer` 增加 pointer release/cancel 处理，拖动结束后释放 pointer capture，减少后续交互串扰。
   - 新增回归测试覆盖横向和纵向 letterbox 点击映射。

4. **Sagittal / Coronal 可读性**
   - 桌面三正交布局从三等分横排改为：Axial 左侧跨两行，Sagittal / Coronal 在右侧上下排列。
   - 正交切片渲染会按体素 spacing 计算 display ratio，并将侧向切片重新采样到可读比例，避免原始 `slices x rows` 像素比例把 Sagittal 压成窄条。
   - 浏览器布局测试已更新：桌面要求 Sagittal / Coronal canvas 宽度至少 300px，所有正交 canvas 至少 180x140；移动端仍保持单列并要求 canvas 不退化成缩略图。

5. **前端标准答案验证展示**
   - “分割控制”面板新增“标准答案验证”状态卡。
   - “评估”面板优先展示真实验证得到的平均 Dice、最低 Dice 和标准答案状态；未运行参考病例推理时继续显示待验证。

### 11.2 三大目标当前判断

| 三大目标 | 当前达成度 | 本轮变化 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 93% | 点击映射已避开留白区，桌面正交布局已扩大侧向视图；仍需用更多真实 CT 和真机屏幕做人工视觉验收。 |
| 器官 label 可点击并展示说明 | 约 90% | 本轮未改 label 体系；13 类器官说明和后端 label 对齐仍保持可用。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 80% | 已新增内置参考病例标准答案 Dice 验证链路；仍需完成一次真实长耗时端到端推理记录，包括耗时、设备、内存和失败恢复。 |

### 11.3 AMOS 0117 参考病例真实推理验收记录

- 输入原图：`nnunetv2_files/amos_0117(3).nii.gz`
- 标准答案：`nnunetv2_files/amos_0117(2).nii.gz`
- 实际权重源：`nnunetv2_files/checkpoint_best.pth`
- checkpoint 元信息：`Dataset001_AMOS22`、`3d_fullres`、15 个前景标签。
- 推理设备：`SEGMENTATION_DEVICE=cuda`，本机检测到 `NVIDIA GeForce RTX 4060 Laptop GPU`。
- 成功 job：`009d4efdc5f6`
- 输出文件：`server/work/009d4efdc5f6/output/009d4efdc5f6.nii.gz`
- 下载接口：`/api/segment/jobs/009d4efdc5f6/result` 返回 `200 OK`，结果大小约 141 KB。
- 标准答案验证：
  - `mean_dice = 0.891327`
  - `foreground_dice = 0.971222`
  - `min_dice = 0.555985`
  - 当前状态：`review`，不是 `passed`。
  - 最低 Dice 标签：胃 `0.555985`，其次为食管 `0.793725`、左肾上腺 `0.815983`。

结论：真实 CUDA 推理链路已经跑通，结果可以自动回填并下载；但参考病例标准答案验收没有完全达标，因为最低 label Dice 未达到 `0.70`。后续界面和文档应继续显示“建议人工复核”，不能把该参考病例表述为模型效果已完全理想。

### 11.4 后续验收清单

**自动化验收**

1. `npm test` 必须通过，覆盖 viewer/imaging/layout/backend/browser 布局回归。
2. `npm run build` 必须通过，确认 TypeScript 与 Vite 生产构建可用。
3. `GET http://127.0.0.1:8000/api/health` 应返回 `status: ok`、`mode: real-nnunetv2`、`model_config_detected: true`、`missing: []`。
4. 使用 AMOS 0117 内置参考病例真实推理完成后，job state 或 SSE complete 事件应包含 `validation` 摘要。

**人工验收**

1. 打开 `http://127.0.0.1:5173`，载入内置参考病例，确认 Axial/Sagittal/Coronal 同时清晰可读。
2. 在三正交图像内容区点击和拖动，十字线应平稳移动；点击图像外留白区不应跳到边缘切片。
3. 运行分割流程后，结果 NIfTI 应自动回填到三正交视图；若输入是 AMOS 0117 参考病例，前端应显示标准答案验证状态。
4. 点击 mask 中非背景 label，应打开正确器官说明；点击背景不应弹出器官说明。
5. 若验证结果为 `review` 或 `unavailable`，不能在文档或 UI 中表述为“模型效果已达标”，必须保留人工复核提示。

---

## 十二、2026-05-23 切片栏与验证 JSON 修复记录

### 12.1 本轮已修复

1. **底部切片栏快速点击乱跳**
   - 原因：底部 7 个切片缩略图每次都按 `selectedSlice` 重新居中；快速点击时缩略图窗口会移动，导致鼠标下同一位置代表的切片号不断变化。
   - 修复：新增稳定窗口起点逻辑 `getStableSliceWindowStart()`，主界面增加 `footerSliceStart` 状态。只在当前切片移出可见窗口或总切片数变化时移动底部缩略图窗口。
   - 验收：`node tests/viewerLogic.test.ts` 已覆盖窗口内点击不漂移、越界时才平移、总切片数小于 7 时钳制到合法范围。

2. **`validation_summary.json` 中文字段乱码**
   - 原因：历史输出文件中的 `message` 和 `labels[].name` 已被二次编码成 mojibake，并且文件带 UTF-8 BOM，导致直接查看和部分解析工具显示异常。
   - 修复：后端新增 `write_validation_summary()`，统一用 UTF-8 无 BOM 写入验证摘要，`json.dumps(..., ensure_ascii=False)` 保留中文字段。
   - 已修复历史文件：`server/work/009d4efdc5f6/output/validation_summary.json`，现在 `message` 为“标准答案验证未达阈值，建议人工复核。”，标签名如“脾脏”“胃”等可正常读取。

3. **后端测试避免读取大权重**
   - `tests/backendState.test.py` 已改用 AMOS checkpoint 元信息 fixture，避免单测阶段加载 `checkpoint_best.pth` 造成长时间卡顿。
   - JSON 写入测试支持 `SEGMENTATION_TEST_TMP` 指定临时输出目录，避免当前受限环境下 Windows 系统 Temp 权限异常。

### 12.2 本轮验证结果

- `node tests/viewerLogic.test.ts`：通过。
- `node tests/imagingLogic.test.ts`：通过。
- `node tests/layoutRegression.test.ts`：通过。
- `python tests/backendState.test.py`：通过。
- `npm test`：通过。运行时使用 `SEGMENTATION_TEST_TMP=D:\Trae_develop_code\segmentation-test-tmp-direct`，并在正常权限下启动浏览器测试，避免 Playwright `spawn EPERM`。
- `npx tsc --noEmit`：通过。
- `npm run build`：通过。此前 Vite `spawn EPERM` 属于受限 shell 权限问题，正常权限下构建成功。
- 历史验证摘要文件已确认：无 UTF-8 BOM，`message` 和标签名为正常中文。

### 12.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 95% | 三正交布局、侧向视图可读性、点击留白区过滤、底部切片栏稳定窗口均已完成并有回归测试；仍建议继续用更多真实 CT 和真机屏幕做人工验收。 |
| 器官 label 可点击并展示说明 | 约 90% | AMOS/后端 label 与前端 canonical id 已对齐，13/15 类器官说明可用；后续需要确认最终训练集标签集合是否固定。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 85% | CUDA 真实推理链路已跑通，结果可下载/回填，AMOS 标准答案 Dice 摘要可生成且 JSON 中文输出已修复；仍需补充更完整的耗时记录、失败恢复和多病例压力验证。 |

---

## 十三、2026-05-23 作业可追溯性补强

### 13.1 本轮已完成

1. **推理耗时与结果大小记录**
   - `Job` 增加 `started_at`、`completed_at`、`duration_seconds` 和 `result_size_bytes`。
   - `/api/segment/jobs/{job_id}` 现在返回耗时、结果大小、结果路径、验证摘要和结果就绪状态。
   - SSE `complete` 事件会携带 `duration_seconds` 与 `result_size_bytes`，前端成功状态、日志和“评估”面板可显示推理耗时与输出大小。

2. **作业摘要持久化**
   - 成功或失败的真实 nnUNetv2 作业会在输出目录写入 `job_summary.json`。
   - `job_summary.json` 使用 UTF-8 无 BOM，保留中文验证信息。

3. **服务重启后的历史结果读取**
   - 如果内存中找不到 job，后端会回退读取 `server/work/<job_id>/output/job_summary.json`。
   - 对于旧作业，如果没有 `job_summary.json`，但存在 `<job_id>.nii.gz` 和 `validation_summary.json`，后端会合成历史摘要，并从 input/output 文件时间估算耗时。
   - 这使 `009d4efdc5f6` 这类已完成历史结果在服务重启后仍可通过 API 查询和下载。

### 13.2 本轮验证

- `npm test`：通过。
- `npm run build`：通过。
- 后端新增测试覆盖：job runtime 字段、`job_summary.json` 写入、重启后读取持久化摘要、无摘要旧输出回退。

### 13.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 95% | 交互和布局主问题已收口，后续以更多真实病例人工验收为主。 |
| 器官 label 可点击并展示说明 | 约 90% | 标签和器官说明仍保持可用，后续依赖最终标签集合确认。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 88% | 新增耗时、结果大小、job 摘要持久化和历史结果回读；剩余重点是多病例压力验证、失败恢复策略和更完整的运行日志归档。 |

---

## 十四、2026-05-23 推理失败诊断增强

### 14.1 本轮已完成

1. **nnUNetv2 子进程日志持久化**
   - 真实推理作业运行结束后，后端会把子进程 stdout/stderr 写入 `output/nnunetv2_process.log`。
   - 日志文件使用 UTF-8 无 BOM，保留中文和 nnUNetv2 原始错误信息。

2. **失败尾部日志进入 job 状态**
   - `Job` 增加 `log_tail` 与 `process_log_path`。
   - `job_summary.json` 会记录 `log_tail` 和日志路径。
   - 如果 nnUNetv2 返回非 0 退出码，SSE `error` 事件会带上 `log_tail`，前端错误信息会包含尾部日志，便于直接定位如 CUDA OOM、模型目录错误、输入格式错误等问题。

3. **历史结果兼容**
   - 新作业优先使用 `job_summary.json` 中的日志字段。
   - 旧作业如果存在 `nnunetv2_process.log`，后端历史摘要回读时也会补充日志尾部。

### 14.2 本轮验证

- `python tests/backendState.test.py`：通过，覆盖 process log 写入、UTF-8 内容、日志尾部和 job summary 字段。
- `node tests/imagingLogic.test.ts`：通过，覆盖 SSE error 事件的 `log_tail` 解析。
- `npx tsc --noEmit`：通过。
- `npm test`：通过。
- `npm run build`：通过。

### 14.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 95% | 当前主要交互缺陷已有测试保护，后续以更多病例和真机验收为主。 |
| 器官 label 可点击并展示说明 | 约 90% | label 与说明链路稳定，后续等待最终标签集合确认。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 89% | 新增子进程日志、失败尾部日志、job 摘要与历史回读后，端到端可追溯性更完整；剩余重点是多病例压力测试、长任务取消/重试和更细粒度资源监控。 |

---

## 十五、2026-05-23 GitHub 发布准备与 README 更新

### 15.1 本轮已完成

1. **补充 GitHub 首页 README**
   - 新增/更新 `README.md`，说明当前项目定位、主要功能、本地运行方式、API 概览、三大目标进度和参考 CT 推理结果。
   - README 明确记录 AMOS 0117 参考病例结果：`mean_dice=0.891327`、`foreground_dice=0.971222`、`min_dice=0.555985`，当前结论为 `review`，不能表述为完全通过验收。

2. **发布范围收口**
   - `.gitignore` 已排除 `node_modules/`、`dist/`、`.test-output/`、`server/work/`、`nnunetv2_files/`、`*.nii`、`*.nii.gz`、`*.pth`、`*.pt`。
   - GitHub 仓库只应提交 GUI 源码、文档、测试、示例静态图片和截图；真实 CT、模型权重和推理输出继续保留在本机。

3. **测试去除真实权重依赖**
   - `test_project_checkpoint_is_preferred_as_weight_source()` 改为在 `.test-output/` 下创建临时模型目录和假权重文件。
   - 该测试继续覆盖“项目 `checkpoint_best.pth` 优先于模型目录 checkpoint”的逻辑，但不再要求仓库内存在真实权重。

### 15.2 本轮验证

- 在独立发布副本 `D:\Trae_develop_code\BME-CT-GUI-publish` 中执行 `npm ci --no-audit --no-fund --prefer-online`：通过。
- `npm test`：通过。
- `npm run build`：通过。
- 受限 shell 下仍可能出现 Vite `spawn EPERM`，正常权限下构建与浏览器测试通过。

### 15.3 发布注意事项

- 原始 GUI 目录位于父级 nnUNet Git 仓库内部，不能直接从 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` 执行 `git add -A`。
- 发布到 `https://github.com/JJ704sd/BME-CT-GUI` 时应使用独立仓库或独立发布副本，避免把父级 `nnunetv2/`、`nnUNet_raw/`、`nnUNet_results/`、环境目录和真实数据一并提交。

---

## 十六、2026-05-23 三正交视图方向修正

### 16.1 本轮已修复

1. **Sagittal 视图横竖轴调换**
   - 现象：用户反馈横断面、矢状面、冠状面的显示方向不符合原始 CT 浏览预期，并怀疑前端做了翻转。
   - 排查结论：未发现 CSS 或 canvas 层的镜像翻转；问题集中在三平面体素到屏幕坐标的映射。此前 Sagittal 使用 `z` 作为屏幕横向、`y` 作为屏幕纵向，视觉上会像被旋转，且不符合“按原始体素坐标展开三平面”的浏览习惯。
   - 修复：Sagittal 现在使用 `y` 作为屏幕横向、`z` 作为屏幕纵向；对应更新 `getOrientationDimensions()`、`getOrientationDisplayRatio()`、`voxelCoordToSlicePoint()`、`slicePointToVoxelCoord()` 和 `sliceRenderer.ts` 中的取样索引。
   - 约束：没有新增 CSS 镜像、旋转或强制翻转；mask 与原图继续共用同一套体素映射，保证覆盖对比不发生错位。

2. **方向回归测试**
   - 更新 `tests/imagingLogic.test.ts`，锁定 Sagittal 的尺寸、显示比例、点击反算体素坐标和十字线坐标映射。
   - 该测试用于防止后续再把 Sagittal 的 `y/z` 轴误换回去。

### 16.2 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，失败点为 Sagittal 旧尺寸 `{ width: 30, height: 20 }` 与新预期 `{ width: 20, height: 30 }` 不一致。
- `npm test`：正常 Windows 权限下通过。
- `npm run build`：正常 Windows 权限下通过。
- 受限 shell 下 Playwright 和 Vite 仍可能出现 `spawn EPERM`，这是子进程启动权限问题，不是本轮代码方向映射失败。

### 16.3 后续验收建议

- 用 `nnunetv2_files/amos_0117_original.nii/amos_0117(3).nii` 导入前端，分别在 Axial、Sagittal、Coronal 视图检查器官上下/左右关系。
- 同时加载 `amos_0117_prediction_009d4efdc5f6.nii.gz` 或新的在线推理结果，确认 mask 覆盖与原图在三个平面均保持配准。
- 如后续需要严格遵循 NIfTI affine 的 RAS/LPS 医学方向，应单独增加“按 header orientation 重定向”的显式模式，不能混入当前“原始体素坐标显示”逻辑。

---

## 十七、2026-05-23 三正交视图方向二次修正

### 17.1 根因复核

- 用户复核后确认上一轮仍不符合正向浏览预期。
- 使用参考文件 `nnunetv2_files/amos_0117_original.nii/amos_0117(3).nii` 检查 header：该参考病例的 NIfTI 方向为 `LAS`，仿射矩阵中 `x` 为负向、`y` 和 `z` 为正向。
- 上一轮虽然修正了 Sagittal 的 `y/z` 轴调换，但仍把数组行号直接映射到屏幕从上到下，导致：
  - Axial 顶部对应后方，床板/背侧显示在上方；
  - Sagittal / Coronal 顶部对应低层切片，头足方向倒置；
  - 主图/底部缩略图仍使用 `main.tsx` 内部轴位渲染函数，和三正交渲染链路没有完全统一。

### 17.2 本轮修复

1. **三正交行方向修正**
   - Axial：屏幕顶部映射到更大的 `y`，使前方/腹侧位于上方。
   - Sagittal：屏幕顶部映射到更大的 `z`，使头侧/上方位于上方；屏幕左侧映射到更大的 `y`，使前方位于左侧、后方/脊柱位于右侧。
   - Coronal：屏幕顶部映射到更大的 `z`，使头侧/上方位于上方。
   - `voxelCoordToSlicePoint()` 现在需要 `volume` 参数，用于正确反算翻转后的屏幕行坐标。
   - `slicePointToVoxelCoord()` 同步反算，保证鼠标点击、十字线和器官拾取仍对应同一个体素。

2. **渲染取样修正**
   - `src/imaging/sliceRenderer.ts` 的 Axial / Sagittal / Coronal 取样索引均同步使用修正后的屏幕行方向。
   - `src/main.tsx` 内部轴位预览/底部缩略图渲染也同步翻转 `y` 行方向，避免主图预览与三正交视图方向不一致。
   - 原图和 mask 继续共用相同体素映射，不会因为显示方向修正造成覆盖错位。

3. **方向回归测试**
   - `tests/imagingLogic.test.ts` 新增/更新断言：
     - Axial 顶部点击映射到 `y=max`；
     - Sagittal 顶部点击映射到 `z=max`；
     - Coronal 顶部点击映射到 `z=max`；
     - 十字线百分比使用修正后的屏幕坐标。

### 17.3 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，失败点为旧 Axial 行方向仍返回 `row=8`，新预期为 `row=11`。
- `npm test`：通过。
- `npm run build`：通过。

### 17.4 后续人工验收

- 重新启动或刷新 Vite 前端，避免浏览器缓存继续显示旧 bundle。
- 导入 `amos_0117(3).nii` 后检查：
  - Axial：床板/背侧应位于图像下方；
  - Coronal：肺部/头侧应位于上方，腹部应位于下方；
  - Sagittal：头侧应位于上方，前腹侧位于左侧，脊柱/背侧位于右侧。
- 加载预测或标准答案 mask 后，检查三个平面覆盖是否仍贴合原图器官边界。

---

## 十八、2026-05-23 三视图拖动切片闪回修复

### 18.1 根因

- 用户反馈拖动 Sagittal / Coronal 时切片会闪回上一位置，造成卡顿。
- 根因是 `selectedSlice` 与 `voxelCoord.z` 双向同步存在一帧竞争：
  - 拖动三正交视图时先更新 `voxelCoord.z`；
  - 此时 `selectedSlice` 仍是上一切片；
  - `selectedSlice -> voxelCoord` 的 effect 会把新 `z` 写回旧切片；
  - 随后 `voxelCoord.z -> selectedSlice` 再把切片号改到新位置，于是界面出现“闪回”。

### 18.2 本轮修复

1. **拖动时原子同步**
   - 新增 `getSelectedSliceForVoxelCoord()`，将体素 `z` 直接换算为 1-based 切片号并做边界钳制。
   - `OrthogonalViewer` 的 `onCoordChange` 不再直接传 `setVoxelCoord`，改为 `handleVoxelCoordChange()`。
   - `handleVoxelCoordChange()` 在同一个 pointer 事件里同时写入 clamped `voxelCoord` 和 `selectedSlice`，避免旧切片 effect 抢先回写。

2. **减少底部缩略图无效重算**
   - `footerSlicePreviews` 不再因为每次 `selectedSlice` 变化就重渲染 7 张缩略图。
   - 只有 `footerSliceStart`、总切片数或源图变化时才重算缩略图；当前切片仍通过按钮 active 状态高亮。

### 18.3 本轮验证

- `node tests/viewerLogic.test.ts`：先失败后通过，新增 `getSelectedSliceForVoxelCoord()` 边界测试。
- `npm test`：通过。
- `npm run build`：通过。

### 18.4 后续人工验收

- 在 Axial / Sagittal / Coronal 三个视图中按住鼠标拖动，观察十字线和切片号应连续变化，不应跳回上一切片。
- 快速拖动 Sagittal / Coronal 的上下方向时，轴位切片号应跟随 `z` 连续更新，底部缩略图窗口只在当前切片移出可见范围时移动。

---

## 十九、2026-05-23 三视图十字线跟手性修复

### 19.1 根因

- 用户反馈拖拽 Axial / Sagittal / Coronal 时，坐标线没有跟着鼠标走。
- 复核后确认有两个叠加原因：
  - 鼠标坐标换算使用 `.ortho-canvas` 的盒子，而真正承载图片和十字线的是 `.ortho-image-stage`。在缩放、比例钳制或后续布局变化时，两者可能出现细微差异，导致鼠标位置与十字线百分比不完全一致。
  - 每次鼠标移动都会触发三张 NIfTI 切片同步重算 data URL。大体积 CT 下这会阻塞 React 提交，十字线必须等底图重渲染完成才移动，视觉上表现为“不跟手”或明显滞后。

### 19.2 本轮修复

1. **鼠标坐标使用真实图片舞台盒子**
   - `OrthogonalViewer` 在 pointer 事件中优先读取 `.ortho-image-stage.getBoundingClientRect()`。
   - `clientPointToSlicePoint()` 仍保留 letterbox 处理，但输入 rect 改为实际图片/十字线所在区域，减少 CSS 缩放和布局造成的偏差。

2. **十字线与切片底图解耦**
   - 新增 `getSliceRenderKey()`：底图渲染只依赖该方向的固定切片号。
   - `OrthogonalViewer` 使用 `useDeferredValue(props.coord)` 渲染 NIfTI 底图；十字线、读数和鼠标交互继续使用即时 `props.coord`。
   - 结果：拖动时十字线可以先跟随鼠标移动，底图切片随后低优先级刷新，避免大图同步生成阻塞交互。

3. **指针捕获更稳**
   - `onPointerMove` 现在在鼠标左键按下或当前元素持有 pointer capture 时都会更新坐标，减少拖出图片边界后移动事件丢失的情况。

### 19.3 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，新增 `getSliceRenderKey()` 测试，确保同一平面内移动十字线不会触发该平面底图重渲染。
- `npm run build`：通过。
- `npm test`：通过。

### 19.4 后续人工验收

- 刷新 Vite 页面后分别在 Axial / Sagittal / Coronal 内按住鼠标拖动。
- 预期：十字线应跟随鼠标即时移动；底图切片可以略有延迟刷新，但不应阻塞十字线。
- 如果仍感觉滞后，下一步应把 NIfTI 切片渲染迁到 canvas/offscreen worker，彻底避免主线程生成 data URL。

---

## 二十、2026-05-23 三视图十字线横向对齐修复

### 20.1 根因

- 用户复核后指出：纵向基本能对齐，但横向仍未对齐。
- 复查发现上一轮只解决了拖动延迟和一部分实际舞台盒子问题，但仍存在一个横向偏移源：
  - `clientPointToSlicePoint()` 会按图片真实显示比例计算 content frame，并扣除横向 letterbox 留白；
  - 十字线绘制仍直接按整个 `.ortho-image-stage` 百分比定位，没有把同一段横向留白加回来；
  - 因此当容器比例与图像比例不完全一致时，鼠标映射和十字线绘制使用的坐标系不一致，横向偏移会比纵向更明显。

### 20.2 本轮修复

1. **统一 content frame**
   - 新增 `getSliceContentFrame(containerRatio, imageRatio)`。
   - `clientPointToSlicePoint()` 和 `getCrosshairPercent()` 现在共用同一个 content frame 计算。

2. **十字线只覆盖真实图片内容区**
   - `OrthogonalViewer` 使用 `ResizeObserver` 读取 `.ortho-image-stage` 的实际显示比例。
   - 垂直十字线的 `left` 会加上 content frame 横向偏移。
   - 水平十字线的 `left/width` 和垂直十字线的 `top/height` 也限制在真实图片内容区内，不再覆盖 letterbox 留白。

3. **保留上一轮跟手性优化**
   - 底图仍使用 deferred 坐标低优先级刷新。
   - 十字线继续使用即时坐标，不等待 NIfTI data URL 生成。

### 20.3 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，新增横向 letterbox 场景测试：2:1 容器内的 1:1 图像，十字线 x 必须包含 25% 左侧留白。
- `npm run build`：通过。
- `npm test`：通过。

### 20.4 后续人工验收

- 刷新 Vite 页面后，在三视图中横向拖动鼠标。
- 预期：垂直十字线应与鼠标横坐标一致；如果图片左右有留白，十字线不会跑到留白区，而是在真实 CT 图像内容区内对齐。

---

## 二十一、2026-05-23 三大目标收口补强

### 21.1 本轮已完成

1. **三正交浏览交互减阻**
   - `sliceRenderer.ts` 增加按体数据对象分组的切片 data URL 缓存，缓存键由方向、固定切片、渲染模式、显示比例和可见 label 集合组成。
   - 同一平面内拖动十字线时不会反复生成相同底图；回到已看过的切片时也可复用缓存，降低大体积 CT 下主线程渲染压力。

2. **器官 label 图层与后端真源同步**
   - 新增 `src/organLayerLogic.ts`，从 `/api/models` 返回的 label 表生成完整器官图层。
   - 图层现在覆盖 AMOS 15 类 label，保留用户已有显隐和质控状态，并在标准答案 Dice 返回后用真实 per-label Dice 回填图层评分。
   - 未验证的 label 显示为“待验”，不再用演示分数伪装成真实置信度。

3. **本地 nnUNetv2 长任务取消**
   - 后端 `Job` 增加 `cancel_requested` 与子进程句柄，新增 `POST /api/segment/jobs/{job_id}/cancel`。
   - 取消请求会终止正在运行的 nnUNetv2 子进程，写入 process log 和 job summary，并通过 SSE 返回取消状态。
   - 前端运行按钮在推理中切换为“取消推理”，取消后恢复可重试状态。

### 21.2 本轮验证

- `python tests/backendState.test.py`：通过，新增覆盖运行中 job 取消、进程 terminate、取消状态和事件记录。
- `node tests/imagingLogic.test.ts`：通过，新增覆盖 15 类 label 图层同步、保留显隐/质控状态、切片缓存键稳定性。
- `npx tsc --noEmit`：通过。

### 21.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 交互映射、横向对齐、切片闪回和重复渲染问题已有回归保护；剩余主要是真实设备和更多病例的人工视觉验收。 |
| 器官 label 可点击并展示说明 | 约 95% | 图层已由后端 label 真源生成并覆盖 AMOS 15 类，说明内容完整；剩余依赖最终训练集 label 集合是否继续变更。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 92% | 已具备真实推理、结果回填、历史回读、失败日志、验证摘要和长任务取消；剩余重点是多病例压力验证、资源监控和更系统的运行日志归档。 |

---

## 二十二、2026-05-23 真实质控与资源审计补强

### 22.1 本轮已完成

1. **per-label Dice 覆盖旧质控状态**
   - `buildOrganLayersFromLabels()` 现在在收到标准答案 per-label Dice 后，以真实 Dice 重新判定器官图层 `accepted/review`。
   - 这修复了一个隐患：如果某器官之前被人工标为“通过”，后续真实验证 Dice 偏低时，旧状态不应继续覆盖新结果。
   - 同步时继续保留用户显隐设置，并开始尊重后端 label 表里的 `visible` 默认值。

2. **nnUNetv2 作业资源快照归档**
   - 后端 `Job` 增加 `resource_snapshots` 与 `resource_log_path`。
   - 真实推理会在 `started`、`process_started`、`completed/failed/cancelled` 等关键阶段记录资源快照。
   - 快照包含推理设备、服务进程 PID、工作目录磁盘容量、服务进程内存；若本机存在 `nvidia-smi`，还会记录 GPU 名称、显存占用和利用率。
   - `job_summary.json` 会包含 `resource_latest` 和 `resource_snapshots`，同时输出独立的 `resource_snapshots.json`，服务重启后也可随历史 job summary 回读。

3. **前端资源摘要回填**
   - SSE `complete/error` 事件支持解析 `resource_latest`。
   - “评估”面板新增“资源快照”指标，流程日志会记录如设备、GPU 显存和磁盘可用空间，便于真实长任务验收时复盘。

### 22.2 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖真实 Dice 覆盖旧质控状态、资源快照 SSE 解析和前端资源摘要文案。
- `python tests/backendState.test.py`：先失败后通过，覆盖 `resource_snapshots.json` 写入、`resource_latest` 和 `resource_log_path` 进入 job summary。
- `npm test`：通过。
- `npm run build`：通过。

### 22.3 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 本轮未改变核心映射，现有三视图、布局、浏览器回归继续通过；剩余仍是真机屏幕和更多真实 CT 的人工验收。 |
| 器官 label 可点击并展示说明 | 约 96% | label 图层继续由后端真源生成，且真实 per-label Dice 已能覆盖旧人工状态；剩余取决于最终训练集 label 是否继续变更。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 94% | 在真实推理、回填、历史回读、失败日志、验证摘要和取消基础上，补齐了关键阶段资源快照和归档；剩余重点是多病例压力验证与更细粒度的资源曲线。 |

---

## 二十三、2026-05-24 无新增病例条件下的推理加速与收口

### 23.1 边界判断

- 当前没有更多真实 CT 病例，因此不能继续提高或宣称“模型泛化验收进度”。三大目标仍可推进，但推进点应限于工程能力：缓存、可追溯、交互稳定性、真实运行记录和失败恢复。
- `AMOS 0117` 仍可作为固定回归病例使用，用于验证前端回填、label 点击、标准答案 Dice、缓存命中和端到端服务状态。
- 对“在线推理太慢”的处理不能伪装成模型本身变快：首次未缓存真实 nnUNetv2 推理仍取决于模型、GPU、体数据大小和 nnUNetv2 预处理/导出成本；重复同一输入时可以通过历史结果缓存把等待时间降到秒级。

### 23.2 本轮已完成

1. **同输入历史推理缓存**
   - 后端在创建 job 时计算上传 NIfTI 的 `input_sha256`，并基于输入哈希、checkpoint 哈希、模型配置和 label 来源生成 `cache_key`。
   - 若已有成功 job 的 `cache_key` 相同，后端不再启动 nnUNetv2 子进程，而是硬链接或复制历史 NIfTI 结果到新 job 输出目录，并立即通过 SSE 返回 `complete`。
   - 缓存命中 job 会写入 `cached_result=true`、`cache_source_job_id`、`cache_key`、`input_sha256` 和 `checkpoint_sha256`，结果仍可通过 `/api/segment/jobs/{job_id}/result` 下载并回填到前端。
   - 对文档中已有的 `009d4efdc5f6` AMOS 0117 参考病例历史真实结果，若当前上传内容与内置参考病例原图一致，也可作为 legacy 缓存源，避免每次演示都重新跑 5-6 分钟。

2. **nnUNetv2 worker 参数可配置**
   - `build_predict_command()` 不再固定 `-npp 1 -nps 1`。
   - 新增环境变量：
     - `SEGMENTATION_PREPROCESS_WORKERS`：默认 `2`，范围 `1..8`。
     - `SEGMENTATION_EXPORT_WORKERS`：默认 `2`，范围 `1..8`。
   - `/api/health` 的 `model_status.predict_workers` 会展示当前 worker 配置，便于记录不同设置下的耗时差异。

3. **前端缓存状态透明展示**
   - 前端新增 `cached-real-nnunetv2` 模式文案。
   - 缓存命中时状态显示为“缓存推理结果回填完成”，结果元信息显示“历史缓存 nnUNetv2 结果”，避免误导为重新执行了一次完整真实推理。

### 23.3 本轮验证

- `python tests/backendState.test.py`：先失败后通过，覆盖 worker 默认值/边界钳制、命令行 `-npp/-nps` 配置、缓存命中时不启动真实推理线程、缓存结果可下载。
- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖缓存推理结果状态文案和结果元信息。
- `npm test`：通过。
- `npm run build`：通过。
- 已重启本地后端并确认 `/api/health` 返回 `predict_workers={"preprocess":2,"export":2}`。
- 使用内置参考病例原图创建在线推理 job `97fa9cefeb41`，命中历史真实结果 `009d4efdc5f6`，创建请求耗时约 `640 ms`，返回 `mode=cached-real-nnunetv2`、`cached_result=true`，结果下载接口返回 `200`，大小 `141460 bytes`。

### 23.4 三大目标当前进度

| 三大目标 | 当前达成度 | 当前判断 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 没有新 CT 时无法做更广病例视觉验收；现阶段可继续通过缓存命中后的快速回填反复验收三视图交互、label 点击和报告状态。 |
| 器官 label 可点击并展示说明 | 约 96% | label 真源、15 类说明和 per-label Dice 回填已闭环；后续进度主要取决于最终训练集 label 是否变化，以及真实病例中 label 是否完整出现。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 96% | 新增同输入缓存和 worker 配置后，重复在线演示可避免分钟级等待；首次未缓存真实推理仍需记录实际耗时和资源曲线，不能用缓存耗时替代真实推理性能指标。 |

### 23.5 后续可继续推进但需要明确前提

- 若目标是“首次推理也显著快于 5-6 分钟”，下一步需要真实计时分解：模型加载、预处理、GPU 推理、导出和前端下载分别耗时多少。
- 若瓶颈在模型加载或 nnUNetv2 框架启动，应规划常驻推理进程或 Python worker 池；这比当前 FastAPI 每个 job 启动一个子进程复杂，但能减少重复启动成本。
- 若瓶颈在模型本身，应考虑轻量配置、裁剪 ROI、低分辨率预览或 TensorRT/ONNX 等单独优化路线；这些会改变精度和验收口径，不能和当前标准答案 Dice 混用。

---

## 二十四、2026-05-24 参考病例定位修正

### 24.1 产品定位

- GUI 的主定位是通用 CT 分割工作站原型，不是 AMOS 专用浏览器。
- 主流程应表述为：导入 CT 原图、导入或运行分割结果、三正交检查、查看器官说明、保存病例或导出报告。
- AMOS 0117 当前只作为内置参考病例，用于无外部数据时演示、固定回归、标准答案 Dice 验证和推理链路冒烟测试。
- 后续导入其他真实 CT 或其他数据集病例时，应沿用同一套“导入 CT 原图 / 导入分割结果 / 运行分割”的通用入口，而不是为每个数据集单独塑造一个主流程。

### 24.2 术语约定

| 术语 | 在本项目中的含义 | 当前状态 |
|---|---|---|
| 导入 CT 原图 | 用户从本机选择任意 `.nii` / `.nii.gz` CT 体数据进入工作台 | 主流程入口，不能绑定到 AMOS |
| 导入分割结果 | 用户从本机选择已有 mask / prediction NIfTI，用于叠加、对比和人工复核 | 主流程入口，适用于 AMOS、FLARE 或其他来源 |
| 载入参考病例 | 一键载入项目随附的固定参考病例，降低演示和回归测试门槛 | 当前内置资源为 AMOS 0117 |
| 内置参考病例 | 后端 `/api/samples/...` 暴露的固定病例资源 | 当前只有 `amos_0117`，后续可扩展更多 sample id |
| 标准答案验证 | 当输入与某个带标准答案的参考病例匹配时，自动计算 Dice | 当前只对 AMOS 0117 闭环 |

结论：按钮“载入参考病例”的意思不是“只能载入 AMOS”，而是“从后端内置参考病例库载入一个可验证病例”。当前库里只有 AMOS 0117，因此 endpoint 和文件名仍包含 `amos_0117`；后续增加 AMOS 其他病例、FLARE 用例或自定义教学病例时，应扩展参考病例清单，而不是改变 GUI 的主流程定位。

### 24.3 本轮已完成

- 前端按钮从旧的 AMOS-only 入口文案调整为“导入 CT 原图 / 导入分割结果 / 载入参考病例”。
- 自动载入、空状态、toast、日志和错误提示统一改为“内置参考病例 / 参考病例服务”，避免暗示系统只能处理 AMOS。
- `loadLocalAmosSample()` 重命名为 `loadReferenceCase()`；后端 endpoint 仍保留 `/api/samples/amos_0117/...`，因为当前内置资源只有 AMOS 0117。
- README 已明确：AMOS 0117 是内置参考病例，主流程支持任意 `.nii` / `.nii.gz` CT 与分割结果导入。

### 24.4 对三大目标的影响

| 三大目标 | 当前判断 |
|---|---|
| CT 可浏览、三正交可联动 | 仍可继续推进交互稳定性、回归测试和真实设备验收；没有更多真实 CT 时不能扩大病例覆盖结论。 |
| 器官 label 可点击并展示说明 | 可继续完善 label 真源、说明文案和质控状态；最终 label 集合是否变化仍依赖训练集和更多病例。 |
| 连接本地 nnUNetv2 后端并回填结果 | 可继续推进常驻 worker、耗时分解、缓存透明展示和失败恢复；首次真实推理性能仍必须用未缓存 job 记录。 |

### 24.5 后续导入用例规划

- 短期：继续支持用户手动导入任意 `.nii` / `.nii.gz` 原图和分割结果，不要求这些病例预先登记为内置样本。
- 中期：将 `/api/samples` 从单一 AMOS 0117 状态扩展为参考病例列表，返回 `id`、名称、数据集来源、是否有标准答案、原图大小和可用状态。
- 中期：前端“载入参考病例”应从单按钮升级为菜单或弹窗，允许选择 AMOS 0117、AMOS 其他病例、FLARE 用例或项目自定义病例。
- 长期：每个参考病例都应有独立元数据和验证口径；只有带标准答案的参考病例才能自动计算 Dice，普通外部 CT 只能显示推理结果、资源耗时和人工复核状态。

### 24.6 本轮验证

- 新增 `tests/imagingLogic.test.ts` 文案回归断言：禁止 UI 重新使用 AMOS-only 载入文案，并要求保留“载入参考病例”和“内置参考病例”。
- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖旧 AMOS-only 文案回归与新参考病例文案。
- `npm test`：通过。受限权限下浏览器测试会遇到 `spawn EPERM`，已在正常权限和全新 `SEGMENTATION_TEST_TMP` 下完成。
- `npm run build`：通过。受限权限下 Vite 会遇到 `spawn EPERM`，已在正常权限下完成生产构建。

---

## 二十五、2026-05-24 三大目标继续完善：参考病例清单化

### 25.1 本轮目标

本轮不新增真实 CT 病例，也不扩大模型泛化结论。推进重点是把上一节确定的“参考病例”定位落实到接口和前端状态中，让后续导入 AMOS 其他病例、FLARE 用例或自定义病例时有清晰扩展点。

### 25.2 本轮已完成

1. **后端 `/api/samples` 元数据补强**
   - `/api/samples` 继续返回数组，但每个 sample 现在包含 `id`、`name`、`dataset`、`modality`、`role`、`description`、`original_url`、`label_url`、文件名、`has_original`、`has_label` 和 `validation_available`。
   - 当前唯一内置参考病例仍为 `amos_0117`，但接口形状已经从“单个 AMOS 文件状态”推进为“参考病例清单”。
   - `/api/samples/{sample_id}/original` 和 `/api/samples/{sample_id}/label` 的 404 文案改为“参考病例原图/标签不存在”，不再使用样例语义。

2. **前端参考病例解析与选择**
   - 新增 `src/referenceCases.ts`，集中定义 `ReferenceCase`、默认 AMOS 0117 参考病例、`normalizeReferenceCases()` 和 `getReferenceCaseOriginalUrl()`。
   - `src/main.tsx` 不再硬编码 `/api/samples/amos_0117/original`，而是先读取 `/api/samples`，再按当前选中的参考病例 URL 载入。
   - “数据”和“分割”侧栏新增参考病例选择控件；当前只有 AMOS 0117 一个选项，但 UI 结构已经支持多参考病例列表。

3. **回归测试补强**
   - `tests/backendState.test.py` 新增 `/api/samples` 元数据断言，防止后续把接口退回到只有路径的状态。
   - `tests/imagingLogic.test.ts` 新增参考病例解析测试，并断言 `main.tsx` 不再硬编码 AMOS 原图 URL。

### 25.3 三大目标当前进展

| 三大目标 | 当前达成度 | 本轮推进 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 96% | 浏览能力本身未改变；病例入口从单固定按钮推进为可扩展参考病例清单，便于后续加入更多真实 CT 做视觉验收。 |
| 器官 label 可点击并展示说明 | 约 96% | label 说明未改动；参考病例元数据增加 `validation_available`，为后续区分“可自动 Dice 验证”和“只能人工复核”的病例打基础。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 97% | 推理链路不再依赖前端硬编码 AMOS URL；后续新增参考病例时，可沿用同一载入和推理回填流程。 |

### 25.4 后续建议

- 下一步可把 `/api/samples` 的静态 AMOS 0117 描述抽成后端配置列表，允许一次登记多个参考病例。
- 当前仍缺更多真实 CT，不能把三大目标进度解释为模型泛化能力提升；新增病例后应分别记录三正交显示、label 点击、推理耗时、资源快照和标准答案状态。
- 若要继续加速首次推理，应使用 `phase_timings` 先找出模型加载、预处理、GPU 推理和导出的占比，再决定是否优化常驻 worker、ROI 裁剪或导出流程。

### 25.5 本轮验证

- `node tests/imagingLogic.test.ts`：先失败后通过，覆盖参考病例解析和 AMOS URL 去硬编码。
- `python tests/backendState.test.py`：先失败后通过，覆盖 `/api/samples` 参考病例元数据。
- `npm test`：通过，使用全新 `SEGMENTATION_TEST_TMP` 并在正常权限下运行浏览器布局测试。
- `npm run build`：通过，Vite 生产构建输出 `dist/`。

---

## 二十六、2026-05-24 三大目标继续完善：参考病例注册表可配置

### 26.1 本轮目标

在没有新增真实 CT 文件的前提下，继续推进“可导入 AMOS 用例，也可导入其他用例”的工程能力。重点不是增加模型验收结论，而是让后端和前端具备多参考病例扩展机制。

### 26.2 本轮已完成

1. **参考病例注册表**
   - 后端新增 `SEGMENTATION_REFERENCE_CASES_JSON` 支持。
   - 若该环境变量指向一个 JSON 文件，后端会从其中读取 `samples` 列表；若未配置或文件不存在，则回退到默认 AMOS 0117。
   - 配置项支持 `id`、`name`、`dataset`、`modality`、`role`、`description`、`original`、`label`、`original_filename`、`label_filename`。
   - `original` 和 `label` 支持绝对路径，也支持相对配置文件所在目录的相对路径。

2. **动态参考病例下载**
   - `/api/samples/{sample_id}/original` 和 `/api/samples/{sample_id}/label` 不再只识别 `amos_0117`。
   - 只要该 `sample_id` 已登记并且文件存在，就能通过同一 API 下载原图或标签。
   - 标签缺失时仍可登记病例，但 `has_label=false`、`validation_available=false`，不会伪装成可自动 Dice 验证。

3. **前端缺失病例保护**
   - 参考病例下拉列表会保留已登记但原图缺失的病例，并显示“原图缺失”。
   - 当前选中的参考病例没有原图时，“载入参考病例”按钮会禁用，避免点击后才失败。

### 26.3 三大目标当前进展

| 三大目标 | 当前达成度 | 本轮推进 |
|---|---:|---|
| CT 可浏览、三正交可联动 | 约 97% | 参考病例入口已支持多病例注册和缺失状态展示；新增真实 CT 后可直接纳入浏览验收。 |
| 器官 label 可点击并展示说明 | 约 96% | 本轮未改变 label 语义；但通过 `validation_available` 区分有无标准答案，为不同数据集病例的复核路径打基础。 |
| 连接本地 nnUNetv2 后端并回填结果 | 约 97% | 后端样本下载 API 已从 AMOS 单例扩展为动态 sample id；后续新增病例可沿用同一推理与回填链路。 |

### 26.4 配置示例

`SEGMENTATION_REFERENCE_CASES_JSON` 指向的 JSON 可使用如下结构：

```json
{
  "samples": [
    {
      "id": "amos_0117",
      "name": "AMOS 0117",
      "dataset": "AMOS22",
      "modality": "CT",
      "original": "amos_0117(3).nii.gz",
      "label": "amos_0117(2).nii.gz",
      "description": "带标准答案的 AMOS 参考病例"
    },
    {
      "id": "flare_demo",
      "name": "FLARE Demo",
      "dataset": "FLARE",
      "modality": "CT",
      "original": "flare_demo.nii.gz",
      "description": "仅用于浏览和推理回填的参考病例"
    }
  ]
}
```

### 26.5 本轮验证

- `python tests/backendState.test.py`：先失败后通过，覆盖配置文件读取、相对路径解析、动态 sample id 下载和缺失 label 的 404。
- `node tests/imagingLogic.test.ts`：通过，确认前端参考病例解析和去硬编码逻辑仍稳定。
- `npm test`：通过，使用全新 `SEGMENTATION_TEST_TMP` 并在正常权限下运行 Playwright。
- `npm run build`：通过，TypeScript 与 Vite 生产构建均成功。

---

*文档版本：2026-05-24*
*更新依据：当前 `src/main.tsx`、`src/components/OrthogonalViewer.tsx`、`src/imaging/voxelMapping.ts`、`src/imaging/sliceRenderer.ts`、`src/data/organDetails.ts`、`src/inference/inferenceClient.ts`、`server/main.py`、`server/requirements.txt`、`tests/*.test.ts` 与本地运行验证结果。*
