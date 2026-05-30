# 校园网 API 直连与公网访问进度记录

**项目：** `segmentation-gui-prototype`  
**日期：** 2026-05-30

## 2026-05-30：planning 文档创建完成

**完成：**

- 新增 `.planning/campus-network-and-public-access/task_plan.md`
- 新增 `.planning/campus-network-and-public-access/findings.md`
- 新增 `.planning/campus-network-and-public-access/progress.md`

**规划结论：**

当前推荐按下面顺序推进：

1. 校园网 API 直连。
2. Ubuntu 22.04 服务器真实 5GPU / 5-fold smoke test。
3. 如果校园网互访不稳定，再试 Tailscale / WireGuard。
4. 如果必须外网浏览器直接访问，再做 frp / Cloudflare Tunnel / VPS + HTTPS + 鉴权。

## 2026-05-31：校园网服务器端到端 smoke 已跑通

**完成：**

- Windows 前端已通过校园网 API endpoint 调用 Ubuntu FastAPI 后端。
- `runtime_target=server` 已能进入 5-fold 并行推理、soft ensemble、结果下载和 GUI 回填。
- FLARE 服务器轮次在自动 remap 后 Dice 合理，可作为服务器链路跑通证据。
- AMOS 服务器轮次出现 `mean_dice=0.076015`、`foreground_dice=0.979808` 且 `remap_source=FLARE22`，更像 AMOS 原生标签被误 remap。

**当前状态：**

- 校园网 API 直连和服务器 5GPU E2E smoke 已完成阶段性验证。
- 下一轮重点转为 `.planning/label-taxonomy-server-validation/`：显式 `label_taxonomy=auto|AMOS22|FLARE22`、server mode gating、AMOS/FLARE 复跑验证。
- 第二台真实局域网设备的大文件上传、SSE 长连接、取消、下载、validation 和前端回填仍需补充记录。
- 外网浏览器入口尚未实施，不应写成已验收通过。

## 待执行清单

### Phase 1：校园网 API 直连

- [ ] 记录 Ubuntu 服务器校园网 IP。
- [ ] 记录你的电脑校园网 IP。
- [ ] Ubuntu 后端监听 `0.0.0.0:8000`。
- [ ] 前端设置 `VITE_API_ENDPOINT=http://<服务器校园网IP>:8000`。
- [ ] 后端设置 `SEGMENTATION_ALLOWED_ORIGINS=http://<前端实际来源>`。
- [ ] 验证 `/api/health`。
- [ ] 验证 `/api/models`。
- [ ] 验证浏览器无 CORS 报错。

### Phase 2：真实 server 推理 smoke test

- [ ] 上传小型或脱敏 NIfTI。
- [ ] 创建 `runtime_target=server` job。
- [ ] 验证 SSE progress / heartbeat。
- [ ] 验证取消任务。
- [ ] 验证 5 个 fold 与 5 张 GPU 映射。
- [ ] 验证 ensemble。
- [ ] 验证 evaluate。
- [ ] 验证结果下载。
- [ ] 验证前端回填 mask。
- [ ] 验证 validation / remap。

### Phase 3：Tailscale / WireGuard PoC

触发条件：校园网直连不可用或不稳定。

- [ ] 服务器加入虚拟网络。
- [ ] 访问设备加入同一虚拟网络。
- [ ] 前端改用服务器虚拟网 IP。
- [ ] 后端放行虚拟网前端来源。
- [ ] 复跑 Phase 1 和 Phase 2 验收。

### Phase 4：外网浏览器入口

触发条件：真实 server 推理已稳定跑通，且访问者不能安装 VPN / Mesh 客户端。

- [ ] 选择 frp + VPS + HTTPS、Cloudflare Tunnel 或 ngrok。
- [ ] 配置 HTTPS。
- [ ] 配置鉴权。
- [ ] 配置大文件上传限制。
- [ ] 配置 SSE 反代。
- [ ] 配置 CORS 或同源 `/api`。
- [ ] 验证上传、SSE、取消、下载、validation、回填。

## 校园网 smoke test 记录模板

```text
测试日期：
服务器系统：Ubuntu 22.04
服务器校园网 IP：
前端电脑校园网 IP：
前端访问地址：
后端 API 地址：
VITE_API_ENDPOINT：
SEGMENTATION_ALLOWED_ORIGINS：

基础检查：
- [ ] 前端页面可打开
- [ ] /api/health 可访问
- [ ] /api/models 可返回
- [ ] 浏览器无 CORS 报错
- [ ] /api/models 显示 server_inference 状态

推理链路：
- [ ] 上传原图成功
- [ ] 运行位置选择 server
- [ ] 创建 job 成功
- [ ] SSE 进度持续更新
- [ ] heartbeat 持续更新
- [ ] 取消任务可用
- [ ] 下载结果可用
- [ ] 标签 validation 可用
- [ ] 前端结果回填可用

5GPU 验证：
- [ ] fold 0 -> GPU 0
- [ ] fold 1 -> GPU 1
- [ ] fold 2 -> GPU 2
- [ ] fold 3 -> GPU 3
- [ ] fold 4 -> GPU 4
- [ ] ensemble 成功
- [ ] evaluate 成功

问题记录：
-
```
