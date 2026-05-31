# 部署准备解释

## 这个主题解决什么问题

部署准备关注的不是单个功能，而是把当前 GUI + FastAPI + nnUNetv2 推理链路从本机开发状态迁移到更稳定的 Linux / 服务器环境。

核心目标是：

```text
前端交互不变
API 协议不变
job / SSE / cancel / result 体验不变
后端运行位置可以从 local 切到 server
```

## local 与 server 的区别

### local

`runtime_target=local` 表示后端使用本机配置的 nnUNetv2 文件和 Python 环境。

适合：

- 本机调试
- fallback
- 小规模验证

### server

`runtime_target=server` 表示后端走服务器 runtime 配置，通常对应 Linux 服务器、5GPU 和 5-fold soft ensemble。

适合：

- 正式推理
- 服务器验收
- 质量基线结果

## 更新权重和替换模型的区别

### 只更新权重

如果 label 数量、模型结构、dataset.json、plans.json 都不变，只替换 checkpoint，影响范围较小。

通常需要：

1. 替换 checkpoint。
2. 跑测试。
3. 跑至少一个真实病例 smoke。
4. 更新指标文档。

### 替换模型结构或标签体系

如果发生以下变化，影响范围会变大：

- 2d 改 3d_fullres
- label 数量变化
- label ID 语义变化
- 训练数据集变化
- plans/config 变化

这时不仅要改后端路径，还可能需要同步：

- 前端器官表
- 后端 taxonomy/remap
- validation 解释
- 报告字段
- acceptance 文档

## 服务器迁移为什么要做 E2E smoke

服务器环境变量配置正确，不代表完整链路一定可用。必须验证：

1. `/api/health`
2. `/api/models`
3. 上传 CT
4. 创建 job
5. SSE progress / heartbeat
6. 取消任务
7. 5 fold 是否都运行
8. ensemble 是否生成结果
9. evaluate 是否能执行
10. result NIfTI 是否可下载
11. 前端是否能回填 mask
12. validation/remap 是否符合预期

只有完整跑通，才能说明服务器部署可用。

## 为什么 deployment package 不包含数据和权重

部署包只应包含后端运行代码和操作说明，不应包含：

- 真实 CT/NIfTI
- checkpoint
- `.env`
- 日志
- 推理输出

原因：

- 权重和医学影像体积大。
- 真实数据可能敏感。
- `.env` 可能包含路径或凭据。
- 推理输出属于运行产物。

## 与网络访问的关系

部署准备和网络访问是两层问题：

```text
部署准备：服务器后端能不能跑
网络访问：前端浏览器能不能稳定访问它
```

不要在服务器后端还没跑通时直接排查公网穿透，否则问题来源会混在一起。

## 与量化功能的关系

量化功能不改变部署要求。它只需要前端成功拿到 result NIfTI mask。

因此部署 smoke 中如果要验证量化，应在原有链路后追加：

```text
结果下载并回填 -> 评估模块显示量化面板 -> 报告导出包含 quantification
```
