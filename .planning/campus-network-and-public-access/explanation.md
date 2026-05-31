# 校园网直连与公网访问解释

## 为什么优先校园网 API 直连

当前系统不是普通静态网页，而是包含：

- 医学影像大文件上传
- 长时间 nnUNetv2 推理
- SSE 进度流
- 取消任务
- 结果 NIfTI 下载
- 服务器 5GPU / 5-fold soft ensemble

如果一开始就做公网穿透，问题可能来自代码、服务器、校园网、防火墙、反向代理、HTTPS、CORS 或 SSE 缓冲，很难定位。因此推荐先把最短链路跑通：

```text
本机浏览器
  ↓
本机 Vite 前端
  ↓ VITE_API_ENDPOINT
校园网 Ubuntu FastAPI 后端
  ↓
5GPU nnUNetv2 推理
```

## 各访问方式的定位

### 1. 校园网 API 直连

适合：

- 前端电脑和 Ubuntu 服务器在同一校园网或实验室网络。
- 需要先验证真实服务器推理链路。
- 访问者数量少，主要是开发/验收人员。

优点：

- 链路最短。
- 变量最少。
- 易于定位后端、SSE、CORS 和上传问题。

限制：

- 如果校园网启用了客户端隔离，同网段也可能互访失败。
- 只能在校园网或实验室网络内访问。

### 2. Tailscale / WireGuard

适合：

- 校园网互访不稳定。
- 访问设备固定。
- 不希望把医学影像服务暴露到公网。

优点：

- 安全边界比公网裸露更好。
- 适合内部协作和答辩前远程调试。
- 不需要处理复杂公网反代。

限制：

- 访问设备需要安装客户端或配置 VPN。
- 不适合完全开放给任意浏览器访问。

### 3. frp / Cloudflare Tunnel / VPS + HTTPS

适合：

- 必须让外部浏览器无需 VPN 直接访问。
- 有明确公网展示需求。
- 能承担 HTTPS、鉴权、上传限制和反代维护成本。

优点：

- 外部访问最方便。

限制：

- 安全风险最高。
- 必须处理鉴权、HTTPS、大文件上传、SSE 长连接和超时。
- 不建议在未完成校园网 smoke 前直接做。

## 前端与后端地址关系

前端页面地址和后端 API 地址可以不同。

例如：

```text
前端页面：http://你的电脑IP:5173
后端 API：http://服务器IP:8000
```

前端通过环境变量指定后端：

```bash
VITE_API_ENDPOINT=http://服务器IP:8000 npm run dev:lan
```

后端通过 CORS 放行前端来源：

```bash
SEGMENTATION_ALLOWED_ORIGINS=http://你的电脑IP:5173
```

注意：CORS 放行的是浏览器页面来源，不是后端 API 地址。

## 为什么不能只测 /api/health

`/api/health` 只能证明 HTTP 请求通。

完整链路还必须验证：

1. `/api/models` 是否能返回模型状态。
2. 大文件上传是否成功。
3. `/api/segment/jobs` 是否能创建 job。
4. SSE `/events` 是否持续连接。
5. heartbeat 是否能长期收到。
6. 取消任务是否能终止子进程。
7. result NIfTI 是否能下载。
8. 前端是否能回填 mask。
9. validation/remap 是否符合标签体系预期。

医学影像推理链路的主要风险通常出现在上传、SSE、长耗时任务和结果下载，而不是 health check。

## 反向代理必须注意什么

如果后续做公网 HTTPS 入口，Nginx / 反代至少要支持：

```nginx
client_max_body_size 2048m;
proxy_read_timeout 3600s;
proxy_send_timeout 3600s;
proxy_buffering off;
```

原因：

- CT/NIfTI 文件可能很大。
- 推理可能持续数分钟到十几分钟。
- SSE 需要关闭代理缓冲。
- 下载结果不能被中途截断。

## 安全边界

公网方案必须补：

- HTTPS
- 鉴权
- 上传大小限制
- CORS 白名单
- 后端端口不直接裸露
- 日志中避免泄露本地敏感路径和文件名

如果只是团队内部验证，优先使用校园网直连或 Tailscale/WireGuard。

## 与量化功能的关系

量化功能只在前端拿到结果 mask 后运行，不改变网络访问方式。

但如果走公网/隧道，报告导出和量化展示仍依赖结果 NIfTI 是否能完整下载并回填到前端。因此访问链路验证仍要包含：

```text
推理完成 -> 下载 result NIfTI -> 前端显示 mask -> 量化面板出现 -> 报告导出含 quantification
```
