# 校园网 API 直连与公网访问实施计划

**项目：** `segmentation-gui-prototype`  
**规划日期：** 2026-05-30  
**范围：** 在校园网环境下优先验证 GUI 前端连接 Ubuntu 22.04 服务器后端，并为后续外网浏览器直接访问保留可实施路径。

## 当前结论

推荐按下面顺序推进：

```text
1. 校园网 API 直连
2. Ubuntu 22.04 服务器真实 5GPU smoke test
3. 若校园网互访不稳定，再做 Tailscale / WireGuard
4. 只有确实需要外网浏览器直接访问时，再做 frp / Cloudflare Tunnel / VPS + HTTPS + 鉴权
```

当前不建议直接从公网穿透开始，因为项目包含医学影像大文件上传、长时间 SSE、取消任务、结果下载和 5GPU 推理。若未先跑通校园网直连，后续很难区分问题来自代码、服务器、校园网还是穿透层。

## 项目现状

已具备：

- 前端支持 `VITE_API_ENDPOINT`，可把 API 指向远端后端。
- 后端支持 `SEGMENTATION_ALLOWED_ORIGINS`，可按实际浏览器来源配置 CORS 白名单。
- 在线推理协议支持 `runtime_target=local|server`。
- `server` 路径已接入 job 生命周期、SSE、取消、结果下载和 validation 语义。
- server 5-fold 命令构造、缓存隔离、取消、complete 事件解析已有代码级测试覆盖。
- `runtime_target` 已进入预测缓存 key，避免 local/server 结果串用。

尚未完成：

- 校园网真实 API 直连 smoke test。
- Ubuntu 22.04 服务器真实 5GPU / 5-fold 推理 smoke test。
- 校园网环境下大文件上传、SSE 长连接、取消、下载稳定性验证。
- Tailscale / WireGuard 或公网穿透的实际选型。
- 外网浏览器入口的 HTTPS、鉴权、反代、大文件上传和 SSE 配置。

## 方案 A：校园网 API 直连

### 目标

你的电脑运行前端 GUI，Ubuntu 22.04 服务器运行 FastAPI 后端和 5GPU nnUNetv2 推理。

```text
你的电脑浏览器
  ↓
你的电脑 Vite 前端 :5173
  ↓ VITE_API_ENDPOINT
Ubuntu 服务器 FastAPI :8000
  ↓
5GPU / 5-fold nnUNetv2 推理
```

### A1. 确认网络地址

需要记录：

```text
服务器校园网 IP：
你的电脑校园网 IP：
前端访问地址：
后端 API 地址：
```

如果校园网启用了客户端隔离，同一校园网下设备可能仍无法互访。此时不要先改代码，应改用实验室局域网、管理员放行或 Tailscale / WireGuard。

### A2. 在 Ubuntu 服务器启动后端

在 GUI 项目根目录启动：

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

必须监听 `0.0.0.0`，不能只监听 `127.0.0.1`。

### A3. 配置后端 CORS

后端应放行你的前端真实浏览器来源：

```bash
export SEGMENTATION_ALLOWED_ORIGINS="http://<你的电脑校园网IP>:5173"
```

如果你用 `http://127.0.0.1:5173` 打开前端，就放行 `http://127.0.0.1:5173`。如果你用 `http://<你的电脑校园网IP>:5173` 打开前端，就放行该校园网地址。

### A4. 配置服务器推理环境

Ubuntu 服务器至少需要确认：

```text
SEGMENTATION_SERVER_GPUS
SEGMENTATION_SERVER_FOLDS
SEGMENTATION_SERVER_DATASET_ID
SEGMENTATION_SERVER_CONFIG
SEGMENTATION_SERVER_PLANS
SEGMENTATION_SERVER_NNUNET_RAW
SEGMENTATION_SERVER_NNUNET_PREPROCESSED
SEGMENTATION_SERVER_NNUNET_RESULTS
SEGMENTATION_SERVER_OUTPUT_ROOT
SEGMENTATION_SERVER_EVALUATE_SCRIPT
SEGMENTATION_SERVER_LABELS_DIR
SEGMENTATION_SERVER_DATASET_JSON
SEGMENTATION_SERVER_PREPROCESS_WORKERS
SEGMENTATION_SERVER_ENSEMBLE_PROCESSES
```

预期语义：

```text
fold 0 -> GPU 0
fold 1 -> GPU 1
fold 2 -> GPU 2
fold 3 -> GPU 3
fold 4 -> GPU 4
```

### A5. 在你的电脑启动前端

```bash
VITE_API_ENDPOINT=http://<服务器校园网IP>:8000 npm run dev:lan
```

浏览器打开：

```text
http://<你的电脑校园网IP>:5173
```

### A6. 校园网 API 直连验收

基础检查：

- [ ] 前端页面可打开。
- [ ] 浏览器 Network 中请求的是 `http://<服务器校园网IP>:8000`。
- [ ] `/api/health` 返回正常。
- [ ] `/api/models` 返回正常。
- [ ] 浏览器无 CORS 报错。
- [ ] `/api/models` 能看到 `runtime_target` / `server_inference` 状态。

上传与 job：

- [ ] 可以上传 CT / NIfTI。
- [ ] 可以选择服务器云端推理。
- [ ] `runtime_target=server` 被提交到后端。
- [ ] 后端创建 job 成功。
- [ ] job 状态中记录 `runtime_target=server`。

SSE 与取消：

- [ ] 前端能收到 SSE progress。
- [ ] heartbeat 能持续更新。
- [ ] 长时间推理过程中连接不中断。
- [ ] 点击取消后 job 进入 cancelling / cancelled。
- [ ] fold / ensemble / evaluate 子进程可被终止。

5GPU 推理：

- [ ] fold 0 跑在 GPU 0。
- [ ] fold 1 跑在 GPU 1。
- [ ] fold 2 跑在 GPU 2。
- [ ] fold 3 跑在 GPU 3。
- [ ] fold 4 跑在 GPU 4。
- [ ] `nnUNetv2_predict` 正常生成各 fold 输出。
- [ ] `nnUNetv2_ensemble` 正常生成 soft ensemble 结果。
- [ ] `evaluate_full.py` 正常执行。

结果回填：

- [ ] 结果 NIfTI 可以下载。
- [ ] 前端能回填显示预测 mask。
- [ ] validation 结果能显示。
- [ ] `phase_timings` 能显示主要耗时阶段。
- [ ] `resource_latest` 能显示 GPU / 资源信息。
- [ ] 缓存不会把 local 和 server 结果串用。

## 方案 B：Tailscale / WireGuard

### 适用条件

- 校园网设备互访不稳定。
- 需要跨校园网、宿舍网、实验室网访问。
- 访问者是固定团队成员，可以安装客户端。
- 不希望把医学影像服务暴露到公网。

### 实施方式

```text
你的电脑 / 访问设备
  ↓ 虚拟网 IP
Ubuntu 服务器 FastAPI :8000
  ↓
5GPU 推理
```

前端配置：

```bash
VITE_API_ENDPOINT=http://<服务器虚拟网IP>:8000 npm run dev:lan
```

后端 CORS：

```bash
export SEGMENTATION_ALLOWED_ORIGINS="http://<前端虚拟网IP>:5173"
```

### 验收

复用方案 A 的完整验收清单，只把校园网 IP 替换为虚拟网 IP。

### 结论

这是校园网直连不稳定时的首选替代方案，适合内部协作和受控演示。

## 方案 C：外网浏览器直接访问

### 适用条件

- 访问者不能安装 VPN / Mesh 客户端。
- 必须通过普通浏览器公网访问。
- 已经完成方案 A 或 B 的真实推理 smoke test。

### 推荐形态

```text
外网浏览器
  ↓ HTTPS
公网域名 / VPS / Tunnel
  ↓
前端页面
  ↓ /api 或 VITE_API_ENDPOINT
后端 FastAPI
  ↓
Ubuntu 5GPU 推理服务器
```

不推荐长期裸露：

```text
http://<公网IP>:8000
```

### 可选路线

| 路线 | 适合场景 | 备注 |
|---|---|---|
| frp + VPS + HTTPS | 长期或较正式外部访问 | 需要自己维护 VPS、Nginx/Caddy、证书和鉴权 |
| Cloudflare Tunnel | 有域名、希望快速 HTTPS 入口 | 需确认医学影像数据合规、上传大小和 SSE 支持 |
| ngrok | 临时 demo | 不建议长期使用 |

### 必须补齐的公网配置

- [ ] HTTPS。
- [ ] 登录、token 或 basic auth 等访问控制。
- [ ] 后端 CORS 精确白名单。
- [ ] Nginx / Caddy 反向代理。
- [ ] 大文件上传限制。
- [ ] SSE buffering 关闭。
- [ ] 请求超时加长。
- [ ] job 并发限制。
- [ ] 上传目录清理策略。
- [ ] 结果文件过期策略。
- [ ] 日志脱敏。
- [ ] 不暴露真实 CT 文件路径。
- [ ] 不提交 `.env`、日志、NIfTI、checkpoint。

### 反代配置重点

如果使用 Nginx / Caddy，需要重点覆盖：

```text
大文件上传
长时间 SSE
长推理请求超时
鉴权
HTTPS
```

Nginx 方向示例：

```nginx
client_max_body_size 2048m;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
proxy_buffering off;
```

具体配置应在真实域名、VPS、端口和入口方式确定后再写，不提前写死。

## 风险与处理

| 风险 | 说明 | 处理 |
|---|---|---|
| 校园网客户端隔离 | 同校园网设备之间可能不能互访 | 改用实验室局域网、管理员放行或 Tailscale/WireGuard |
| 服务器防火墙 | Ubuntu 可能未放行 8000 | 临时放行端口或用反代 |
| CORS 错误 | Origin 与白名单不一致 | 以浏览器实际访问地址为准配置 |
| SSE 中断 | 校园网网关或代理断开长连接 | 观察 heartbeat，必要时改 VPN/Mesh 或配置反代 |
| 大文件上传失败 | 校园网、代理或 tunnel 限制上传 | 先小 NIfTI，再真实 CT；公网入口配置上传限制 |
| server 配置缺失 | `SEGMENTATION_SERVER_*` 不完整 | 先看 `/api/models` 和 `/api/health` |
| 公网安全风险 | 医学影像和推理服务暴露 | HTTPS、鉴权、白名单、并发限制和日志脱敏必须落实 |

## 执行顺序

### 第一阶段：校园网 API 直连

目标：验证你的电脑前端可以稳定连接 Ubuntu 服务器后端。

- [ ] 记录服务器校园网 IP 和你的电脑校园网 IP。
- [ ] 后端监听 `0.0.0.0:8000`。
- [ ] 前端设置 `VITE_API_ENDPOINT=http://<服务器校园网IP>:8000`。
- [ ] 后端设置 `SEGMENTATION_ALLOWED_ORIGINS`。
- [ ] 验证 `/api/health`、`/api/models`。
- [ ] 验证浏览器无 CORS 报错。

### 第二阶段：真实 5GPU 推理 smoke test

目标：确认 server 路径不仅代码可用，而且真实服务器可跑完。

- [ ] 上传真实或小型脱敏 NIfTI。
- [ ] 创建 `runtime_target=server` job。
- [ ] 观察 SSE progress / heartbeat。
- [ ] 观察 5 个 fold 的 GPU 映射。
- [ ] 验证 ensemble / evaluate。
- [ ] 验证结果下载和前端回填。
- [ ] 验证取消任务。

### 第三阶段：Tailscale / WireGuard PoC

触发条件：校园网直连不稳定，或需要跨网络但访问者可安装客户端。

- [ ] 服务器和访问设备加入同一虚拟网络。
- [ ] 将 API endpoint 换成服务器虚拟网 IP。
- [ ] 按虚拟网前端来源配置 CORS。
- [ ] 复跑第一、第二阶段验收。

### 第四阶段：外网浏览器入口

触发条件：真实服务器推理已跑通，且必须给不能安装客户端的访问者使用。

- [ ] 选择 frp + VPS + HTTPS、Cloudflare Tunnel 或 ngrok。
- [ ] 配置 HTTPS 和鉴权。
- [ ] 配置大文件上传和 SSE 反代。
- [ ] 精确配置 CORS 或同源 `/api`。
- [ ] 复跑上传、SSE、取消、下载、validation、结果回填。

## 文档同步要求

每阶段完成后再同步事实结果，不提前写验收通过。

需要更新：

- `.planning/campus-network-and-public-access/progress.md`
- `.planning/lan-direct-and-tunnel/progress.md`
- `.planning/deployment-preparation/task_plan.md`
- `README.md`
- `ACCEPTANCE.md`
- `REVIEW.md`

## 当前推荐下一步

先执行第一阶段：校园网 API 直连。

成功标准不是只看 `/api/health`，而是至少完成：

```text
前端页面 -> 远端 /api/models -> 上传小 NIfTI -> 创建 runtime_target=server job -> SSE 有进度 -> 可取消或完成 -> 可下载结果
```

在这之前，不建议把公网访问写成已完成，也不建议直接暴露 FastAPI 公网端口。
