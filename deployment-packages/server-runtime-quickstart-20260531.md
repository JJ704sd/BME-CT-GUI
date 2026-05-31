# 服务器 Runtime 部署快速指南

日期：2026-05-31

## 更新内容

本次更新修复了标签体系自动检测误判问题：

- **问题**：AMOS 原生标签曾被自动检测为 FLARE22，导致错误标签重映射和近零 Dice 分数
- **修复**：`detect_dataset()` 现在更保守；如果参考标签 ID 是 checkpoint 标签 ID 的子集，不会自动触发 remap
- **新增**：`label_taxonomy` 参数支持显式选择 `auto|AMOS22|FLARE22`
- **部署包调整**：zip 内已按项目结构放置为 `server/...`，可在项目根目录直接解压覆盖

## 包内容

`server-runtime-package-20260531.zip` 解压后包含：

```text
server/main.py
server/taxonomy.py
server/server_inference.py
server/persistent_nnunet_worker.py
server/requirements.txt
```

不包含模型权重、CT 数据、推理输出、前端构建产物。

## 推荐部署步骤

### 1. 上传部署包

将 `server-runtime-package-20260531.zip` 上传到 Ubuntu 服务器的项目根目录，例如：

```bash
/path/to/segmentation-gui-prototype/server-runtime-package-20260531.zip
```

项目根目录应能看到已有的 `server/` 目录。

### 2. 备份当前后端代码

```bash
cd /path/to/segmentation-gui-prototype
cp -a server "server.backup.$(date +%Y%m%d-%H%M%S)"
```

### 3. 解压覆盖后端文件

```bash
cd /path/to/segmentation-gui-prototype
unzip -o server-runtime-package-20260531.zip
```

如服务器缺少依赖，可补装：

```bash
python -m pip install -r server/requirements.txt
```

### 4. 重启 FastAPI 服务

如果你是手动启动的 uvicorn：

```bash
pkill -f uvicorn
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

如果服务器用 systemd / supervisor / tmux 管理服务，请用对应方式重启；核心要求是让 `server/main.py` 重新加载。

## 验证部署

```bash
curl http://localhost:8000/api/health
```

检查 `label_taxonomy` 参数是否可用：

```bash
curl -X POST http://localhost:8000/api/segment/jobs \
  -F "file=@test.nii.gz" \
  -F "label_taxonomy=AMOS22" \
  -F "inference_profile=quality"
```

## 标签体系选择说明

| 选项 | 行为 | 适用场景 |
|---|---|---|
| `auto` | 保守检测；标签 ID 是 checkpoint 子集时不触发 remap | 默认选项 |
| `AMOS22` | 强制不执行 FLARE remap | AMOS 原生标签 |
| `FLARE22` | 强制执行 FLARE22 → AMOS22 remap | FLARE22 标签 |

## 验证清单

- [ ] 服务器健康检查通过
- [ ] 上传 AMOS 标签 + 选择 `AMOS22` → `remap_applied=false`
- [ ] 上传 FLARE 标签 + 选择 `FLARE22` → `remap_applied=true`
- [ ] 选择 `auto` + AMOS 标签 → 不触发 remap
- [ ] Dice 指标正常，不再出现近零分数

## 注意事项

1. **必须重启服务器**：代码覆盖后必须重启 FastAPI 才能生效。
2. **前端兼容性**：旧版前端仍可工作，但不会发送 `label_taxonomy` 参数，只会走默认 `auto`。
3. **缓存语义**：`label_taxonomy` 已纳入缓存 key，不同标签体系的结果不会混用。
4. **解压位置**：必须在项目根目录解压，不能在 `server/` 目录里解压。zip 内部已经包含 `server/` 前缀。
