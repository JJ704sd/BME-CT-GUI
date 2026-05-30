# 局域网直连与内网穿透实施计划

**范围：** 将当前本机运行的 CT 分割 GUI，扩展为可在局域网访问，并为后续内网穿透提供可落地路径。  
**规划日期：** 2026-05-30  
**推荐顺序：** 先做局域网直连，再做内网穿透。

## 目标

本规划拆成两条路径：

1. **局域网直连**
   - 同一局域网内的电脑 / 平板可以打开 GUI。
   - 前端可以访问远端 FastAPI 后端。
   - 上传 CT、SSE 进度、取消任务、下载结果都可用。

2. **内网穿透**
   - 外部网络也能访问 GUI 和 API。
   - 不直接裸露后端公网端口。
   - 优先选择安全性更高的 VPN / Mesh 方案，必要时再使用 frp + HTTPS。

## 当前约束

- 前端 `API_ENDPOINT` 当前仍偏本机硬编码，需要配置化。
- Vite 默认开发服务只监听 `127.0.0.1`，局域网设备不能访问。
- 后端 CORS 目前只适合 localhost / 127.0.0.1。
- 在线推理包含大文件上传、长时间 SSE、结果下载，不能只验证普通 JSON 请求。

## 路径一：局域网直连

### Phase 1：前端 API 地址配置化

修改目标：

```ts
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || "http://127.0.0.1:8000";
```

开发启动示例：

```powershell
$env:VITE_API_ENDPOINT='http://192.168.1.20:8000'
npm run dev -- --host 0.0.0.0 --port 5173
```

验收：

- [ ] 不改代码即可切换后端 API 地址。
- [ ] 本机默认仍能访问 `http://127.0.0.1:8000`。
- [ ] 局域网设备访问前端时，API 指向正确后端地址。

### Phase 2：新增局域网前端启动脚本

建议在 `package.json` 增加：

```json
{
  "dev:lan": "vite --host 0.0.0.0 --port 5173"
}
```

验收：

- [ ] `npm run dev:lan` 可启动前端。
- [ ] 另一台局域网设备可访问 `http://<前端机器IP>:5173`。

### Phase 3：后端监听局域网地址

启动命令：

```powershell
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

验收：

- [ ] 本机可访问 `http://127.0.0.1:8000/api/health`。
- [ ] 局域网设备可访问 `http://<后端机器IP>:8000/api/health`。
- [ ] Windows 防火墙已放行 8000 / 5173 端口。

### Phase 4：后端 CORS 配置化

建议新增环境变量：

```powershell
$env:SEGMENTATION_ALLOWED_ORIGINS='http://192.168.1.20:5173,http://192.168.1.30:5173'
```

后端策略：

- 如果设置 `SEGMENTATION_ALLOWED_ORIGINS`，优先使用明确白名单。
- 如果未设置，保持当前 localhost 默认策略。
- 不建议正式长期使用 `*`。

验收：

- [ ] 浏览器控制台无 CORS 报错。
- [ ] `/api/models`、`/api/samples`、`/api/segment/jobs` 可正常访问。
- [ ] SSE `/events` 能持续连接。

### Phase 5：局域网推理 smoke test

最小验证链路：

- [ ] 局域网设备打开前端。
- [ ] 导入 `.nii` / `.nii.gz`。
- [ ] 选择 `本地在线推理` 或 `服务器云端推理`。
- [ ] 创建 job 成功。
- [ ] SSE 阶段进度正常显示。
- [ ] 可以取消任务，或推理完成后下载结果。
- [ ] 上传标签文件时 validation 仍可执行。

## 路径二：内网穿透

## 推荐方案 A：Tailscale / WireGuard

适合：内部团队、敏感数据、固定访问者。

实施步骤：

1. 后端机器加入 Tailscale / WireGuard 网络。
2. 访问设备加入同一虚拟网络。
3. 获取后端机器虚拟 IP，例如 `100.x.x.x`。
4. 前端配置：

```powershell
$env:VITE_API_ENDPOINT='http://100.x.x.x:8000'
```

5. 后端 CORS 放行虚拟网前端来源。

验收：

- [ ] 外网设备通过虚拟网 IP 打开前端。
- [ ] `/api/health` 可访问。
- [ ] 上传、SSE、取消、下载可用。
- [ ] 不暴露公网裸端口。

结论：

**这是当前项目最推荐的穿透方案。**

## 推荐方案 B：frp + VPS + HTTPS

适合：需要外部浏览器直接访问、不能要求用户安装 VPN 客户端。

推荐入口：

```text
https://ct-seg.example.com/      -> 前端
https://ct-seg.example.com/api/  -> 后端
```

实施步骤：

1. VPS 部署 `frps`。
2. 内网机器部署 `frpc`。
3. VPS 上用 Nginx 做 HTTPS 和路径反代。
4. 前端 API 尽量使用同源 `/api`，减少 CORS 问题。
5. 反代配置必须支持大文件和 SSE。

Nginx 关键方向：

```nginx
client_max_body_size 2048m;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
proxy_buffering off;
```

验收：

- [ ] 公网域名可打开前端。
- [ ] `/api/health` 返回正常。
- [ ] HTTPS 证书正常。
- [ ] 大文件上传不被截断。
- [ ] SSE 不被代理缓冲。
- [ ] 未授权用户无法访问。

结论：

**适合正式外部演示，但必须配 HTTPS 和访问控制。**

## 临时方案 C：Cloudflare Tunnel / 类托管隧道

适合：短期 demo。

注意：

- 医疗影像数据路径会经过第三方，需要确认合规。
- 必须验证上传大小、长连接、SSE 支持。
- 不建议作为长期敏感数据入口。

## 安全加固要求

无论采用哪条穿透路径，都至少需要：

- HTTPS 或 VPN 加密通道。
- 访问控制。
- 不裸露未授权后端公网端口。
- 上传大小限制。
- 推理任务并发限制。
- 日志脱敏。
- SSE 断线后可通过 job state 查询兜底。

## 实施优先级

1. `VITE_API_ENDPOINT` 配置化。
2. `dev:lan` 脚本。
3. `SEGMENTATION_ALLOWED_ORIGINS`。
4. 局域网 smoke test。
5. Tailscale / WireGuard PoC。
6. 如确需公网浏览器入口，再做 frp + HTTPS。

## 预期修改文件

- `src/main.tsx`
- `package.json`
- `server/main.py`
- `README.md`
- 可选新增 `.env.example`

## 验证命令

```powershell
npm test
npm run build
```

局域网联调命令示例：

```powershell
$env:VITE_API_ENDPOINT='http://192.168.1.20:8000'
npm run dev:lan
```

```powershell
$env:SEGMENTATION_ALLOWED_ORIGINS='http://192.168.1.20:5173'
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```
