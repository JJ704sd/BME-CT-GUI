# 校园网 API 直连与公网访问发现记录

**项目：** `segmentation-gui-prototype`  
**日期：** 2026-05-30  
**范围：** 校园网内前端连接远端 Ubuntu 后端、内网穿透、外网浏览器访问。

## 2026-05-30：当前阶段应先做校园网 API 直连

**判断：** 当前 GUI 项目的代码侧已经支持远端 API 地址、CORS 白名单和 `runtime_target=server`，因此下一步重点不是继续大改 GUI，而是用真实校园网和真实 Ubuntu 22.04 服务器做 smoke test。

**依据：**

- 前端可通过 `VITE_API_ENDPOINT` 指向远端 FastAPI。
- 后端可通过 `SEGMENTATION_ALLOWED_ORIGINS` 放行实际前端来源。
- server 推理路径已接入 job / SSE / cancel / download / validation。
- 代码级测试已覆盖 server 配置、命令构造、缓存隔离、取消和 complete 事件解析。

**如何应用：** 先验证 `你的电脑前端 -> 校园网 Ubuntu 后端 -> 5GPU 推理`，不要先引入公网 tunnel 的额外变量。

## 2026-05-30：校园网 API 直连可以避免先把前端部署到服务器

**判断：** 如果校园网允许设备互访，可以只在你的电脑运行 Vite 前端，在 Ubuntu 服务器运行 FastAPI 后端和 5GPU 推理，不必先把前端代码部署到服务器。

**关键条件：**

- 服务器后端监听 `0.0.0.0:8000`。
- 你的电脑前端使用 `VITE_API_ENDPOINT=http://<服务器校园网IP>:8000`。
- 后端 CORS 放行你的前端实际来源。
- 校园网不阻断你的电脑访问服务器 8000 端口。

**风险：** 校园网可能存在客户端隔离、防火墙限制或长连接中断。必须用 `/api/models`、上传、SSE、取消、下载完整验证，不能只测 `/api/health`。

## 2026-05-30：Tailscale / WireGuard 是校园网不稳定时的首选替代

**判断：** 如果校园网设备互访不稳定，或后续需要跨宿舍网、实验室网、校外网络访问，但访问者可以安装客户端，优先选择 Tailscale / WireGuard。

**原因：**

- 更接近局域网访问模型。
- 对大文件上传和 SSE 长连接更友好。
- 不需要把医学影像服务暴露给整个公网。
- 安全边界比 frp 裸转发更清晰。

**如何应用：** 把 `VITE_API_ENDPOINT` 换成服务器虚拟网 IP，并按虚拟网前端来源配置 `SEGMENTATION_ALLOWED_ORIGINS`，然后复跑校园网完整验收清单。

## 2026-05-30：外网浏览器直接访问应放在真实服务器 smoke test 之后

**判断：** 外网浏览器入口不是当前第一步。只有当校园网或 VPN/Mesh 路径已经证明服务器推理可用后，再进入公网入口设计。

**原因：** 公网入口会额外引入：

- HTTPS
- 鉴权
- 反向代理
- 大文件上传限制
- SSE buffering / timeout 配置
- CORS 或同源 `/api` 策略
- job 并发限制
- 日志脱敏和文件清理

如果真实服务器推理还没跑通，直接做公网穿透会让排错变复杂。

## 2026-05-30：公网入口不能裸露未授权 FastAPI 端口

**判断：** 不建议长期使用 `http://<公网IP>:8000` 直接暴露后端。

**最低要求：**

- HTTPS 或 VPN 加密通道。
- 访问控制。
- 精确 CORS 白名单。
- 大文件上传限制。
- SSE 反代关闭 buffering。
- 请求超时适配长时间推理。
- 上传结果和临时文件有清理策略。
- 不记录或暴露医学影像隐私路径。

## 风险清单

- 校园网客户端隔离导致同网设备无法互访。
- Ubuntu 防火墙未放行 8000。
- 浏览器实际 Origin 与 `SEGMENTATION_ALLOWED_ORIGINS` 不一致。
- 校园网或代理断开 SSE 长连接。
- 大 NIfTI 上传被网关、代理或 tunnel 截断。
- `SEGMENTATION_SERVER_*` 配置缺失导致 server runtime 不 ready。
- 公网入口如果无鉴权，会暴露医学影像上传和推理能力。
