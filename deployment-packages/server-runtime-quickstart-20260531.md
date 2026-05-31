# 服务器 Runtime 部署快速指南

日期：2026-05-31

## 更新内容

本次更新修复了标签体系自动检测误判问题：

- **问题**：AMOS 原生标签被自动检测为 FLARE22，导致错误的标签重映射和近零 Dice 分数
- **修复**：`detect_dataset()` 现在更保守，如果标签 ID 是 checkpoint 的子集，不会自动触发 remap
- **新增**：`label_taxonomy` 参数支持显式选择 `auto|AMOS22|FLARE22`

## 部署步骤

### 1. 上传文件到服务器

将以下文件上传到 Ubuntu 服务器的 FastAPI 后端目录：

```
server/main.py
server/taxonomy.py
server/server_inference.py
server/persistent_nnunet_worker.py
server/requirements.txt
```

### 2. 重启 FastAPI 服务器

```bash
# 在服务器上
cd /path/to/segmentation-gui-prototype
pkill -f uvicorn
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

### 3. 验证部署

```bash
# 检查服务器状态
curl http://localhost:8000/api/health

# 检查 label_taxonomy 功能
curl -X POST http://localhost:8000/api/segment/jobs \
  -F "file=@test.nii.gz" \
  -F "label_taxonomy=AMOS22" \
  -F "inference_profile=quality"
```

## 标签体系选择说明

| 选项 | 行为 | 适用场景 |
|---|---|---|
| `auto` | 保守检测，标签 ID 是 checkpoint 子集时不触发 remap | 默认选项 |
| `AMOS22` | 强制不执行 FLARE remap | AMOS 原生标签 |
| `FLARE22` | 强制执行 FLARE22 → AMOS22 remap | FLARE22 标签 |

## 验证清单

- [ ] 服务器健康检查通过
- [ ] 上传 AMOS 标签 + 选择 `AMOS22` → `remap_applied=false`
- [ ] 上传 FLARE 标签 + 选择 `FLARE22` → `remap_applied=true`
- [ ] 选择 `auto` + AMOS 标签 → 不触发 remap
- [ ] Dice 指标正常（不再出现近零分数）

## 注意事项

1. **必须重启服务器**：代码更新后必须重启 FastAPI 才能生效
2. **前端兼容性**：旧版前端仍然可以工作，但不会发送 `label_taxonomy` 参数
3. **缓存语义**：`label_taxonomy` 已纳入缓存 key，不同标签体系的结果不会混用
