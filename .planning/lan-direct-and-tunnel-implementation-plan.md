# 局域网直连与内网穿透落地规划

**项目：** `segmentation-gui-prototype`  
**目标：** 把当前本机可用的 CT 分割 GUI，整理成两条可执行接入路径：`局域网直连` 和 `内网穿透`。  
**当前日期：** 2026-05-30

## 1. 当前状态

项目当前已经具备：

- React + Vite 前端，默认入口 `http://127.0.0.1:5173`
- FastAPI 后端，默认健康检查 `http://127.0.0.1:8000/api/health`
- 在线推理 API：创建 job、SSE 进度、取消任务、下载结果
- 本地在线推理 / 服务器云端推理选项
- 长任务推理、上传 NIfTI、下载 NIfTI 结果

当前主要限制：

- 前端 API 地址仍以本机调试为主
- Vite 默认只监听 `127.0.0.1`
- 后端 CORS 当前只适合本机回环来源
- 还没有统一的局域网 / 穿透部署配置

## 2. 总体策略

建议分两条路径推进，但先后顺序要明确：

1. **先落地局域网直连**
   - 这是所有远程访问的基础。
   - 局域网能跑通，说明 API 地址、CORS、SSE、上传下载都基本打通。

2. **再接内网穿透**
   - 内网穿透只是把访问入口从局域网 IP 换成隧道地址。
   - 不应在 API 配置还硬编码时直接做穿透，否则问题会混在一起，很难排查。

---

# 路径一：局域网直连

## 3. 目标

在同一局域网内，另一台电脑可以直接访问 GUI，并调用运行后端推理服务。

目标访问形态：

```text
前端：http://<运行前端机器的局域网IP>:5173
后端：http://<运行后端机器的局域网IP>:8000
健康检查：http://<后端IP>:8000/api/health
```

如果前后端在同一台机器上：

```text
前端：http://192.168.1.20:5173
后端：http://192.168.1.20:8000
```

如果前端在本机、后端在服务器：

```text
前端：http://192.168.1.10:5173
后端：http://192.168.1.20:8000
```

## 4. 需要修改的内容

### 4.1 前端 API 地址配置化

当前前端不应继续依赖固定：

```ts
const API_ENDPOINT = "http://127.0.0.1:8000";
```

建议改成：

```ts
const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || "http://127.0.0.1:8000";
```

这样启动前端时可以切换：

```bash
VITE_API_ENDPOINT=http://192.168.1.20:8000 npm run dev -- --host 0.0.0.0 --port 5173
```

Windows PowerShell 示例：

```powershell
$env:VITE_API_ENDPOINT='http://192.168.1.20:8000'
npm run dev -- --host 0.0.0.0 --port 5173
```

### 4.2 前端监听局域网地址

当前 `package.json` 中 dev 脚本默认只监听 `127.0.0.1`，局域网设备无法访问。

开发期可以临时启动：

```bash
npm run dev -- --host 0.0.0.0 --port 5173
```

后续可新增脚本：

```json
{
  "dev:lan": "vite --host 0.0.0.0 --port 5173"
}
```

### 4.3 后端监听局域网地址

后端启动时使用：

```bash
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

PowerShell 示例：

```powershell
python -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

如果只做本机调试，仍然可以使用：

```bash
python -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

### 4.4 后端 CORS 改成可配置

当前 CORS 只适合：

```text
localhost / 127.0.0.1
```

局域网访问时，浏览器来源会变成：

```text
http://192.168.1.20:5173
http://192.168.1.30:5173
```

建议新增环境变量：

```bash
SEGMENTATION_ALLOWED_ORIGINS=http://192.168.1.20:5173,http://192.168.1.30:5173
```

后端逻辑建议：

- 如果设置了 `SEGMENTATION_ALLOWED_ORIGINS`，优先使用明确白名单
- 如果没设置，保持当前 localhost 默认策略
- 不建议正式长期使用 `*`

### 4.5 Windows 防火墙

如果后端或前端在 Windows 上运行，需要放行端口：

- 前端：5173
- 后端：8000

检查方式：

```powershell
Test-NetConnection 192.168.1.20 -Port 8000
Test-NetConnection 192.168.1.20 -Port 5173
```

浏览器检查：

```text
http://192.168.1.20:8000/api/health
http://192.168.1.20:5173
```

## 5. 局域网直连验收清单

### 5.1 基础连通

- [ ] 前端机器能打开 `http://<前端IP>:5173`
- [ ] 浏览器能打开 `http://<后端IP>:8000/api/health`
- [ ] 前端页面无 CORS 报错
- [ ] `/api/models` 能正常返回模型信息

### 5.2 推理链路

- [ ] 可以导入 CT 原图
- [ ] 可以选择 `本地在线推理` 或 `服务器云端推理`
- [ ] 可以创建 job
- [ ] SSE 进度能持续更新
- [ ] 取消推理可用
- [ ] 推理完成后可以下载 / 回填结果
- [ ] 上传标签后 validation 仍可执行

### 5.3 网络稳定性

- [ ] 大文件上传不会中断
- [ ] 长时间推理期间 SSE 心跳正常
- [ ] 浏览器刷新后可通过 job 查询恢复状态

## 6. 局域网直连推荐落地顺序

1. 修改前端 `API_ENDPOINT` 为 `VITE_API_ENDPOINT`
2. 新增 `dev:lan` 启动脚本
3. 修改后端 CORS 为环境变量白名单
4. 用 `0.0.0.0` 启动前后端
5. 用另一台局域网设备访问并完成一次 smoke test
6. 更新 README 的局域网运行命令

---

# 路径二：内网穿透

## 7. 目标

让不在同一局域网内的设备也能访问 GUI 和后端 API，同时避免裸露未授权公网端口。

目标访问形态：

```text
https://ct-seg.example.com
https://ct-seg.example.com/api/health
```

或：

```text
http://<穿透域名或公网地址>
http://<穿透域名或公网地址>/api/health
```

## 8. 内网穿透方案选择

## 8.1 首选：Tailscale / WireGuard 类 Mesh VPN

### 适用情况

- 访问者是自己或固定团队成员
- 可以安装客户端
- 数据比较敏感
- 不希望把服务直接挂到公网

### 架构

```text
远程电脑 / 平板
  ↓ Tailscale / WireGuard 虚拟网络
运行 GUI / 后端的机器
  ↓
FastAPI + Vite / 静态前端
```

### 落地方式

1. 在后端机器安装 Tailscale / WireGuard
2. 在访问设备安装同一网络客户端
3. 确认后端机器的虚拟网 IP，例如：

```text
100.x.x.x
```

4. 前端 API 地址指向：

```bash
VITE_API_ENDPOINT=http://100.x.x.x:8000
```

5. 后端 CORS 放行：

```bash
SEGMENTATION_ALLOWED_ORIGINS=http://100.x.x.x:5173
```

如果前端也部署在同一台机器上，只需要访问：

```text
http://100.x.x.x:5173
```

### 优点

- 安全性最好
- 不需要暴露公网端口
- 对上传、下载、SSE 比较友好
- 运维成本比 frp + HTTPS 更低

### 缺点

- 访问端需要安装客户端
- 不适合公开演示给任意用户

### 结论

**这是本项目最推荐的内网穿透方案。**

---

## 8.2 次选：frp + VPS + HTTPS 反向代理

### 适用情况

- 希望外部浏览器直接访问
- 有公网 VPS
- 可以接受维护反向代理和证书
- 需要稳定域名

### 架构

```text
外部浏览器
  ↓ HTTPS
公网 VPS / Nginx / frps
  ↓ frp 隧道
内网机器 / frpc
  ↓
前端服务 + FastAPI 后端
```

### 推荐入口设计

不要暴露两个公网端口，建议统一成一个域名：

```text
https://ct-seg.example.com/        -> 前端
https://ct-seg.example.com/api/*   -> 后端
```

这样有两个好处：

- 前端可以使用同源 `/api`
- CORS 问题大幅减少

### 需要注意

Nginx / 反代必须支持：

- 大文件上传
- 长连接 SSE
- 下载较大结果文件
- 较长超时时间

关键配置方向：

```nginx
client_max_body_size 2048m;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
proxy_buffering off;
```

### 优点

- 浏览器访问体验最好
- 可以用正式域名和 HTTPS
- 不要求访问者安装客户端

### 缺点

- 运维复杂度高
- 安全责任更重
- 需要公网 VPS 和证书
- 如果没有认证，风险较高

### 结论

**适合正式演示或需要外部浏览器访问的场景，但必须加访问控制。**

---

## 8.3 临时方案：Cloudflare Tunnel / 类托管隧道

### 适用情况

- 临时演示
- 不想配置 VPS
- 可以接受第三方隧道服务

### 优点

- 快速
- 不需要公网 IP
- 配置比 frp 简单

### 缺点

- 数据路径依赖第三方
- 医疗影像场景要谨慎
- 需要确认上传大小、连接超时、SSE 支持

### 结论

**适合短期 demo，不建议作为敏感数据长期生产入口。**

## 9. 内网穿透落地顺序

### Phase 1：沿用局域网配置

先完成路径一的所有改造：

- API 地址可配置
- CORS 可配置
- 前后端可监听局域网地址
- SSE / 上传 / 下载已在局域网验证过

### Phase 2：选择穿透方式

建议决策：

| 场景 | 推荐方案 |
|---|---|
| 只给自己和团队用 | Tailscale / WireGuard |
| 要给外部浏览器直接访问 | frp + VPS + HTTPS |
| 临时演示 | Cloudflare Tunnel |

### Phase 3：接入隧道

#### Tailscale / WireGuard

- 前端 `VITE_API_ENDPOINT` 指向虚拟网 IP
- 后端 CORS 放行虚拟网访问来源
- 不暴露公网端口

#### frp

- VPS 部署 frps
- 内网机器部署 frpc
- Nginx 做 HTTPS 和 `/api` 反代
- 前端 API 地址改成同源 `/api` 或公网 API 地址

### Phase 4：安全加固

至少补充：

- HTTPS
- 访问密码 / 登录认证 / VPN ACL
- 上传大小限制
- 任务并发限制
- 日志脱敏
- 反代超时配置

## 10. 内网穿透验收清单

### 10.1 基础访问

- [ ] 外网设备可以打开前端
- [ ] 外网设备可以访问 `/api/health`
- [ ] 浏览器控制台无 CORS 错误
- [ ] HTTPS 证书正常

### 10.2 推理链路

- [ ] 可以上传 `.nii` / `.nii.gz`
- [ ] 可以创建推理 job
- [ ] SSE 进度不断流
- [ ] 可以取消 job
- [ ] 可以下载结果
- [ ] 上传标签后 validation 可用

### 10.3 安全

- [ ] 未授权用户不能访问
- [ ] 后端端口没有裸露公网
- [ ] 日志不记录敏感文件内容
- [ ] 隧道 / 反代有访问控制

## 11. 两条路径的关键差异

| 项目 | 局域网直连 | 内网穿透 |
|---|---|---|
| 访问范围 | 同一局域网 | 外部网络 |
| 实现复杂度 | 低 | 中-高 |
| 安全风险 | 中 | 高 |
| 是否需要公网资源 | 不需要 | frp 需要 VPS；VPN 不一定需要 |
| 是否适合敏感数据 | 可控 | 必须加固 |
| SSE 稳定性 | 较好 | 取决于隧道/反代 |
| 推荐优先级 | 第一阶段必做 | 第二阶段评估后做 |

## 12. 建议最终落地方案

### 第一阶段：局域网直连

必须做，作为所有后续远程访问的基础。

最小改动：

- `VITE_API_ENDPOINT`
- `dev:lan`
- `SEGMENTATION_ALLOWED_ORIGINS`
- 后端 `0.0.0.0` 启动文档

### 第二阶段：Tailscale / WireGuard

如果主要是自己或团队访问，优先做这个。

原因：

- 医疗影像数据更安全
- 不裸露公网端口
- 对长任务和大文件更友好

### 第三阶段：frp + HTTPS

只有在确实需要“外部浏览器直接打开”时再做。

要求：

- 必须有 HTTPS
- 必须有访问控制
- 必须确认上传和 SSE 超时配置

## 13. 后续实现任务拆分

### 任务 1：局域网配置化

- [ ] 前端读取 `VITE_API_ENDPOINT`
- [ ] 新增 `dev:lan` 脚本
- [ ] 后端 CORS 支持 `SEGMENTATION_ALLOWED_ORIGINS`
- [ ] README 增加局域网启动示例
- [ ] 跑通 `npm test` 和 `npm run build`

### 任务 2：局域网 smoke test

- [ ] 本机启动前端 `0.0.0.0:5173`
- [ ] 本机启动后端 `0.0.0.0:8000`
- [ ] 另一台局域网设备访问前端
- [ ] 验证 `/api/health`
- [ ] 验证一次 job 创建 / SSE / 取消或下载

### 任务 3：内网穿透 PoC

先选一种：

- [ ] Tailscale / WireGuard PoC
- [ ] frp + VPS PoC
- [ ] Cloudflare Tunnel demo

PoC 不先改业务代码，只替换访问入口和配置。

### 任务 4：安全和部署固化

- [ ] 访问控制
- [ ] HTTPS
- [ ] 上传大小和超时
- [ ] SSE 反代配置
- [ ] 运行手册

## 14. 推荐下一步

下一步建议直接实现“局域网配置化”：

1. 修改 `src/main.tsx`，把 `API_ENDPOINT` 改为 `import.meta.env.VITE_API_ENDPOINT || "http://127.0.0.1:8000"`
2. 修改 `package.json`，新增 `dev:lan`
3. 修改 `server/main.py`，让 CORS 支持 `SEGMENTATION_ALLOWED_ORIGINS`
4. 更新 README
5. 运行测试和构建

这一步完成后，再用实际局域网 IP 验证；验证通过后再决定用 Tailscale / WireGuard 还是 frp。
