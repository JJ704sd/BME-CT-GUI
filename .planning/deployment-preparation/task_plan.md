# 部署准备与维护计划

**范围：** 针对当前在线推理、局域网访问和云服务器迁移做准备。

**当前状态：** 前端已支持 `VITE_API_ENDPOINT`，后端已支持 `SEGMENTATION_ALLOWED_ORIGINS`，在线推理已拆分为 `runtime_target=local|server` 两条路径。`deployment-packages/server-runtime-package-20260530.zip` 与 `deployment-packages/server-runtime-quickstart-20260530.md` 已准备完成；每次发布前仍需重新运行 `npm test`、`npm run build` 和 `git diff --check`。

## 关注点分析

### 1. 更新最佳模型参数权重

**结论：** 只影响局部路径，不会改变项目整体架构。

当前模型权重配置：
- 主要 checkpoint：`nnunetv2_files/checkpoint_best.pth`
- 运行时模型：`server/work/runtime_model/nnUNetTrainer__nnUNetPlans__2d/fold_0/checkpoint_best.pth`

**更新权重只需：**
1. 替换 `nnunetv2_files/checkpoint_best.pth`
2. 重新运行验收测试
3. 更新 `README.md`
4. 更新 `SEGMENTATION_METRICS_SUMMARY.md`

**不需要修改：**
- 前端交互
- API 结构
- 运行位置选择
- SSE / 取消 / 下载流程

---

### 2. Linux / 云服务器部署

**目标：** 让后端可以稳定迁移到云服务器，并保持当前 GUI 的 job / SSE / result 体验不变。

**当前部署材料：** `deployment-packages/server-runtime-package-20260530.zip` 是服务器 runtime 包；`deployment-packages/server-runtime-quickstart-20260530.md` 是解压后最短操作清单。它们只提供后端代码和操作说明，不包含真实 CT/NIfTI、checkpoint、`.env`、日志或推理输出。

#### 2.1 服务器迁移的最小前提

- 服务器具备 CUDA、PyTorch、nnUNetv2 和可用 GPU。
- `nnUNet_raw`、`nnUNet_preprocessed`、`nnUNet_results` 路径完整。
- 模型目录、`dataset.json`、`plans.json` 和 checkpoint 文件可用。
- `SEGMENTATION_SERVER_*` 环境变量已配置。

#### 2.2 推荐的运行语义

前端提交时继续使用：

```text
runtime_target=local|server
inference_profile=quality|fast
```

- `local`：本机 nnUNetv2 fallback。
- `server`：Linux 服务器 5-GPU / 5-fold soft ensemble。

#### 2.3 云服务器配置重点

建议至少确认这些变量：

- `SEGMENTATION_SERVER_GPUS`
- `SEGMENTATION_SERVER_FOLDS`
- `SEGMENTATION_SERVER_DATASET_ID`
- `SEGMENTATION_SERVER_CONFIG`
- `SEGMENTATION_SERVER_PLANS`
- `SEGMENTATION_SERVER_NNUNET_RAW`
- `SEGMENTATION_SERVER_NNUNET_PREPROCESSED`
- `SEGMENTATION_SERVER_NNUNET_RESULTS`
- `SEGMENTATION_SERVER_OUTPUT_ROOT`
- `SEGMENTATION_SERVER_EVALUATE_SCRIPT`
- `SEGMENTATION_SERVER_LABELS_DIR`
- `SEGMENTATION_SERVER_DATASET_JSON`

#### 2.4 迁移后必须验证的链路

1. `/api/health`
2. `/api/models`
3. 上传 CT
4. 创建 job
5. SSE 进度 / heartbeat
6. 取消任务
7. 结果下载
8. 标签 validation / remap
9. 5 个 fold 是否按 GPU / fold 映射执行
10. 前端是否能正确回填结果

#### 2.5 网络访问建议

- 局域网、VPN / Mesh 优先。
- 如果必须公网浏览器访问，再考虑 frp + HTTPS。
- 公网入口必须加鉴权、HTTPS、上传限制和 SSE 反代配置。
- 不要长期使用裸露后端端口或无限制 CORS。

---

### 3. 替换改良版 nnUNet-v2 模型

**情况比单纯更新权重更复杂。**

#### 变化类型

| 变化类型 | 影响范围 |
|----------|----------|
| 权重更新 | 低 |
| 架构变化（如 2d → 3d_fullres） | 中 |
| 标签数量变化 | 中-高 |
| 数据集变化 | 高 |

#### 处理原则

- 权重变化：只替换 checkpoint 并回归测试。
- 架构变化：同步更新后端模型目录与运行配置。
- 标签变化：同步前端器官表、后端 taxonomy 和测试。
- 数据集变化：同时更新 reference cases、验收口径和文档。

---

### 4. 遗留问题检查

**当前重点不是重构，而是完成迁移验收。**

优先关注：
- 运行位置 `local/server` 是否在前后端协议里一致。
- 缓存是否因 `runtime_target` 区分开。
- 服务器路径是否真正完成 E2E smoke test。
- 文档是否仍然与当前实现一致。

---

## 建议的后续行动

### 短期
1. 固化服务器迁移配置表。
2. 做真实 Linux 云服务器 E2E smoke test。
3. 把结果同步到 `README.md`、`ACCEPTANCE.md`、`REVIEW.md`。

### 中期
1. 验证 `server/server_inference.py` 的 5-fold 编排是否稳定。
2. 完成公网 / VPN 访问方案的取舍。
3. 补充取消、SSE、结果下载的异常场景测试。

### 长期
1. 形成可重复的云服务器部署清单。
2. 把迁移验收流程写成固定 planning 模板。
3. 逐步增强多模型或多数据集支持。

---

## 更新后的 Planning 文档结构

建议保留当前目录化管理：

```
.planning/
├── lan-direct-and-tunnel/
│   ├── findings.md
│   ├── progress.md
│   └── task_plan.md
├── deployment-preparation/
│   └── task_plan.md
└── ...
```

## 总结

- 当前主线已经从“局域网能否直连”推进到“云服务器能否稳定迁移并完成在线推理”。
- 后续 planning 的核心应是：服务器环境准备、运行位置一致性、E2E smoke test、网络安全边界和验收口径同步。
