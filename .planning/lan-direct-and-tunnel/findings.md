# 局域网直连与内网穿透发现记录

**项目：** `segmentation-gui-prototype`  
**日期：** 2026-05-30  
**范围：** 前端局域网访问、后端 CORS、长任务 SSE、大文件上传、内网穿透方案。

## 2026-05-30：前端 API 地址需要脱离本机硬编码

**现象：** 本机开发时 `http://127.0.0.1:8000` 可用，但局域网设备打开前端后，如果前端仍请求 `127.0.0.1:8000`，浏览器会访问局域网设备自身的 8000 端口，而不是运行 FastAPI 的机器。

**结论：** 前端必须支持 `VITE_API_ENDPOINT`，启动前端时显式指向后端局域网 IP。

**落地方式：**

```ts
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || "http://127.0.0.1:8000";
```

**验收重点：**

- 本机不设置环境变量时仍默认访问 `http://127.0.0.1:8000`。
- 局域网联调时通过 `VITE_API_ENDPOINT=http://<后端IP>:8000` 切换 API。
- 创建 job、SSE、取消、下载结果都使用同一个 endpoint。

## 2026-05-30：Vite 需要监听 `0.0.0.0`

**现象：** `npm run dev` 默认只适合本机调试，局域网设备无法打开前端页面。

**结论：** 保留本机脚本，同时新增 `dev:lan` 供局域网调试。

**落地方式：**

```json
"dev:lan": "vite --host 0.0.0.0 --port 5173"
```

**验收重点：**

- 本机继续可用 `npm run dev`。
- 局域网调试使用 `npm run dev:lan`。
- Windows 防火墙需要放行 5173。

## 2026-05-30：后端 CORS 需要白名单配置

**现象：** 浏览器来源从 localhost 变成 `http://192.168.x.x:5173` 后，后端默认 CORS 会拦截跨域请求。

**结论：** 后端应支持 `SEGMENTATION_ALLOWED_ORIGINS`，不设置时保持 localhost 默认策略，设置后使用明确来源白名单。

**落地方式：**

```powershell
$env:SEGMENTATION_ALLOWED_ORIGINS='http://192.168.1.20:5173,http://192.168.1.30:5173'
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

**验收重点：**

- 浏览器控制台无 CORS 报错。
- `/api/models`、`/api/samples`、`/api/segment/jobs` 可访问。
- `/events` SSE 长连接不被 CORS 拦截。

## 2026-05-30：局域网 smoke test 不能只测 health

**结论：** 该项目是长任务医学影像推理 GUI，只测 `/api/health` 不足以说明链路可用。

**必须覆盖：**

1. 局域网设备打开前端。
2. 前端实际请求远端 FastAPI。
3. 上传 `.nii` / `.nii.gz`。
4. 选择 `本地在线推理` 或 `服务器云端推理`。
5. 创建 job 成功。
6. SSE 阶段进度持续更新。
7. 取消任务可终止后端子进程。
8. 推理完成后可下载并回填结果。
9. 上传标签文件后 validation 仍可执行。

## 2026-05-30：内网穿透优先 VPN / Mesh

**判断：** 当前项目涉及医疗影像、长时间推理和大文件传输，不适合优先裸露公网端口。

**推荐顺序：**

1. **Tailscale / WireGuard**：优先用于内部团队、固定访问者、敏感数据场景。
2. **frp + VPS + HTTPS + 访问控制**：仅在必须让外部浏览器直接访问、不能安装客户端时使用。
3. **Cloudflare Tunnel / 类托管隧道**：适合短期 demo，但需确认数据合规、上传大小和 SSE 支持。

## 风险记录

- 局域网 IP 变化会导致 `VITE_API_ENDPOINT` 和 CORS 白名单失效，建议固定后端机器 IP 或使用内网 DNS。
- Windows 防火墙可能分别拦截 5173 和 8000。
- 代理 / 隧道如果默认开启 buffering，会破坏 SSE 体验。
- 大文件上传需要验证代理层、隧道层和后端磁盘空间，不只看浏览器是否能打开页面。
- 不建议长期使用 `SEGMENTATION_ALLOWED_ORIGINS=*` 或直接公网暴露 FastAPI。
