# 局域网直连与内网穿透进度记录

**项目：** `segmentation-gui-prototype`  
**日期：** 2026-05-30

## 2026-05-30：规划拆分完成

**完成：**

- 创建主实施计划：`.planning/lan-direct-and-tunnel/task_plan.md`
- 补齐发现记录：`.planning/lan-direct-and-tunnel/findings.md`
- 补齐进度记录：`.planning/lan-direct-and-tunnel/progress.md`

**规划范围：**

- 局域网直连：前端地址配置、Vite 监听、后端监听、CORS 白名单、完整推理 smoke test。
- 内网穿透：Tailscale / WireGuard、frp + HTTPS、Cloudflare Tunnel 等方案的适用边界。
- 安全要求：HTTPS 或 VPN、访问控制、不裸露后端公网端口、SSE 与大文件上传验证。

**文档归档：**

- `.planning/lan-api-access-and-nat-traversal.md` 与 `.planning/lan-direct-and-tunnel-implementation-plan.md` 是早期散落在 `.planning/` 根目录的同主题草案。
- 当前有效版本已收敛到 `.planning/lan-direct-and-tunnel/` 目录下的 `task_plan.md`、`findings.md` 和 `progress.md`。
- 早期根目录草案已删除，避免重复维护和审阅入口混乱。

## 2026-05-30：局域网配置化代码侧状态

**已完成：**

- 前端 API 地址支持 `VITE_API_ENDPOINT`，未设置时回退到 `http://127.0.0.1:8000`。
- `package.json` 已增加 `dev:lan`：`vite --host 0.0.0.0 --port 5173`。
- 后端 CORS 支持 `SEGMENTATION_ALLOWED_ORIGINS`，未设置时保留 localhost / 127.0.0.1 默认策略。

**仍需验证：**

- 用真实局域网 IP 启动前端和后端。
- 从另一台设备打开前端。
- 完成上传、SSE、取消、下载、标签 validation 的 smoke test。

## 2026-05-30：测试状态

**已完成：**

- `npm test` 已通过。
- `npm run build` 已通过。

**后续如有代码变更：**

- 需要重新运行 `npm test`。
- 需要重新运行 `npm run build`。

## 2026-05-30：局域网 smoke test 记录

**当前机器局域网 IP：** `10.154.28.9`

**本机可验证结果：**

- `npm run dev:lan -- --strictPort` 可启动 Vite，并可通过 `http://10.154.28.9:5173` 返回 `200`。
- 后端用 `--host 0.0.0.0 --port 8000` 可启动，并可通过 `http://10.154.28.9:8000/api/health` 返回 `200`。
- 设置 `SEGMENTATION_ALLOWED_ORIGINS='http://10.154.28.9:5173'` 后，`Origin: http://10.154.28.9:5173` 请求 `/api/models` 会返回 `access-control-allow-origin: http://10.154.28.9:5173`。

**未完成项：**

- 尚未用第二台真实局域网设备打开页面。
- 尚未在第二台设备上完成真实 CT 上传、SSE、取消、下载和标签 validation。

**发现的问题：**

- 从 workspace 根目录直接运行 `python -m uvicorn server.main:app` 会因为当前目录不在项目根而报 `ModuleNotFoundError: No module named 'server'`。解决方式是进入项目目录运行，或显式设置 `PYTHONPATH`。
- `SEGMENTATION_ALLOWED_ORIGINS` 需要使用实际浏览器来源；如果只放行 `127.0.0.1:5173`，从 `10.154.28.9:5173` 访问时不会返回对应 CORS allow-origin。

## 2026-05-30：穿透方案阶段性决策

**推荐：** 当前优先选择 **Tailscale / WireGuard**。

**原因：**

- 当前项目处理 CT / NIfTI 医学影像，不适合优先暴露公网入口。
- 在线推理链路包含大文件上传、长时间 SSE、取消任务和结果下载，VPN / Mesh 更接近局域网直连，变量更少。
- 固定团队或内部演示场景下，安装客户端的成本低于维护公网 HTTPS、鉴权、反代 buffering 和上传限制。

**frp + VPS + HTTPS 的适用条件：**

- 访问者不能安装 VPN / Mesh 客户端。
- 必须提供普通浏览器公网入口。
- 已准备好 HTTPS、访问控制、Nginx 大文件上传限制和 SSE 反代配置。

**下一步建议：**

1. 先用 Tailscale / WireGuard 做 PoC。
2. 复用本次局域网配置：`VITE_API_ENDPOINT=http://<虚拟网IP>:8000`，`SEGMENTATION_ALLOWED_ORIGINS=http://<前端虚拟网IP>:5173`。
3. 跑完整上传、SSE、取消、下载、标签 validation。
4. 只有在确实需要无客户端公网访问时，再进入 frp + HTTPS 路线。

## 待办清单

- [x] Phase 1：前端 `VITE_API_ENDPOINT` 配置化。
- [x] Phase 2：新增 `dev:lan` 脚本。
- [x] Phase 3：后端 `SEGMENTATION_ALLOWED_ORIGINS` CORS 白名单。
- [ ] Phase 4：局域网 smoke test。
- [ ] Phase 5：基于 smoke test 结果决定 Tailscale / WireGuard 或 frp。

## 局域网 smoke test 记录模板

```text
测试日期：
前端机器 IP：
后端机器 IP：
访问设备：
前端地址：http://<前端IP>:5173
后端地址：http://<后端IP>:8000
VITE_API_ENDPOINT：
SEGMENTATION_ALLOWED_ORIGINS：

基础检查：
- [ ] 前端页面可打开
- [ ] /api/health 可访问
- [ ] 浏览器无 CORS 报错
- [ ] /api/models 可返回

推理链路：
- [ ] 上传原图成功
- [ ] 运行位置可选
- [ ] 创建 job 成功
- [ ] SSE 进度持续更新
- [ ] 取消任务可用
- [ ] 下载结果可用
- [ ] 标签 validation 可用

问题记录：
-
```
