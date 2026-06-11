# GUI 项目启动操作手册（线下实时启动用）

> 适用对象：**任何时候**要把本地 GUI 跑起来的人 — 不管是初次接触、调试开发、还是临时演示。
> 不含 cache demo 细节（那一套走 `docs/demo-day-checklist.md` + `docs/local-cache-demo-runbook.md`）。

## TL;DR — 一行启动

打开 PowerShell，**`cd` 到项目根目录**，执行：

```powershell
& "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" tools\start_local_demo.py
```

等几秒看到 `Backend ready: ... Open the GUI at: http://127.0.0.1:5173/` 后，浏览器开 `http://127.0.0.1:5173/` 即可。

按 `Ctrl+C` 退出，前后端一起停。

---

## 0. 前置确认（30 秒看完）

第一次启动前**只**要确认这 3 件事，其他不用管：

| # | 检查项 | 命令 / 路径 |
|---|---|---|
| 1 | Python venv 存在 | `Test-Path "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe"` |
| 2 | Node 依赖已装 | 项目根目录有 `node_modules/`（没装就 `npm install`） |
| 3 | 当前 cwd 是项目根 | PowerShell 里 `Get-Location` 应输出 `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` |

模型权重、参考病例 NIfTI 这些**首次启动不强制** — 没权重后端只是返回 `mode=unavailable`，GUI 还能浏览内置 AMOS 0117 看三视图，但推理会失败。

---

## 1. 标准启动（推荐）

### 1.1 PowerShell 直接前台跑

适合：开发调试、临时打开看一下、看实时日志。

```powershell
# 必须先 cd 到项目根（uvicorn 需要从这里启动，否则 server 包找不到）
Set-Location D:\BME2026\BME_CT_Seg\segmentation-gui-prototype

& "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" tools\start_local_demo.py
```

成功标志（脚本会自动打印）：

```
Backend ready: N reference case(s) exposed at /api/samples:
  - <id> ...
Open the GUI at: http://127.0.0.1:5173/
```

### 1.2 后台跑（关闭终端也不停）

适合：演示挂在副屏、SSH 进去跑想断开就走。

```powershell
Set-Location D:\BME2026\BME_CT_Seg\segmentation-gui-prototype

# 先确保旧进程清掉
Get-Process | Where-Object { $_.ProcessName -match '^(node|python|uvicorn|vite)$' } | Stop-Process -Force -ErrorAction SilentlyContinue

# 丢后台（不挂终端，重启电脑才会停）
$env:SEGMENTATION_REFERENCE_CASES_JSON = "examples\reference_cases.json"
Start-Process -FilePath "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" `
    -ArgumentList "tools\start_local_demo.py" `
    -WorkingDirectory "D:\BME2026\BME_CT_Seg\segmentation-gui-prototype" `
    -RedirectStandardOutput ".\.test-output\demo_stdout.log" `
    -RedirectStandardError ".\.test-output\demo_stderr.log" `
    -WindowStyle Hidden
```

等 ~8 秒，浏览器访问 `http://127.0.0.1:5173/` 即可。日志看 `.test-output\demo_stdout.log`。

**为什么不能用 `npm run dev` 直接前台跑？** 工具（如 AI agent 的 bash 工具）超时后会把整个进程组连带 vite/uvicorn 一起 kill，进程不会真的"后台"。演示给真人看可以，但交给自动化/SSH 断开场景必须用 `Start-Process`。

---

## 2. 启动选项（脚本支持的 flag）

`tools/start_local_demo.py` 默认就够用。需要时：

| Flag | 用途 |
|---|---|
| `--no-persistent-worker` | 关闭常驻 nnUNetv2 worker（实验性，默认开） |
| `--device cpu` | 强制 CPU 推理（默认自动检测 CUDA，CUDA 不可用时回退 CPU） |
| `--reference-cases-json <path>` | 自定义参考病例 JSON |
| `--backend-port 8000` / `--frontend-port 5173` | 改端口 |
| `--dry-run` | 只打印将要执行的命令和 env，不真启动 |

例：纯 CPU 调试：

```powershell
& "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" tools\start_local_demo.py --device cpu
```

---

## 3. 验证启动成功（不出图就排查）

跑完后等 5 秒，**按顺序**验：

```powershell
# 1. 后端健康（应该 200，mode 字段决定能否推理）
curl http://127.0.0.1:8000/api/health

# 2. 前端可达（应该 200）
curl -I http://127.0.0.1:5173/

# 3. 参考病例（应该返回 samples 列表）
curl http://127.0.0.1:8000/api/samples
```

| 现象 | 原因 / 排查 |
|---|---|
| `curl : 連線被拒`（Connection refused）| 进程没起来或刚被工具超时杀掉。检查 1.2 节后台启动方式 |
| `/api/health` 返回 `mode: unavailable` | checkpoint / dataset.json / plans.json 缺一个，看 README 的"模型和参考病例文件"段 |
| `/api/samples` 只返回 1 例 AMOS | 缺 `SEGMENTATION_REFERENCE_CASES_JSON` env，脚本里已经默认设了；如果是手工启动的记得手动 export |
| 浏览器报 `ERR_CONNECTION_REFUSED` 但端口又在 Listen | PowerShell 里跑 `Get-NetTCPConnection -LocalPort 5173,8000 -State Listen` 确认监听是 `127.0.0.1` 而不是 IPv6 `[::]`；如果是 IPv6，浏览器用 `http://[::1]:5173/` 或换 `0.0.0.0` |
| Vite 报 `EADDRINUSE` | 端口被占；`Get-Process node \| Stop-Process -Force` 后重试 |

---

## 4. 停服

### 前台跑（1.1）
脚本所在 PowerShell 窗口按 `Ctrl+C`，脚本会负责关掉两个子进程。

### 后台跑（1.2）

```powershell
Get-Process | Where-Object { $_.ProcessName -match '^(node|python)$' -and $_.CommandLine -match 'start_local_demo|uvicorn|vite' } | Stop-Process
```

或者暴力清（会杀所有 node/python，不影响系统）：

```powershell
Get-Process node, python | Stop-Process -Force
```

---

## 5. 如果 `start_local_demo.py` 挂了 — 手工启动回退

脚本就是下面两条命令的封装，挂了就直接拆开跑：

**窗口 1 — 后端**：

```powershell
Set-Location D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
$env:SEGMENTATION_REFERENCE_CASES_JSON = "D:\BME2026\BME_CT_Seg\segmentation-gui-prototype\examples\reference_cases.json"
& "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" -m uvicorn server.main:app --host 127.0.0.1 --port 8000
```

**窗口 2 — 前端**：

```powershell
Set-Location D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
npm run dev
```

两条都报 ready 后浏览器开 `http://127.0.0.1:5173/`。

---

## 6. 局域网联调

想从别的机器访问本机 GUI（比如手机、平板、另一台电脑）：

**后端机器**（跑推理的那台）：

```powershell
& "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" -m uvicorn server.main:app --host 0.0.0.0 --port 8000
```

**前端机器**（开浏览器的那台；可以和后端是同一台）：

```powershell
Set-Location D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
$env:VITE_API_ENDPOINT = "http://<后端机器IP>:8000"
npm run dev:lan
```

手机/平板开 `http://<前端机器IP>:5173`。

---

## 7. 一页速记卡（贴工位用）

```
启动:
  cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
  & "D:\BME2026\BME_CT_Seg\nnunet_env\Scripts\python.exe" tools\start_local_demo.py

访问:
  GUI:   http://127.0.0.1:5173/
  后端:  http://127.0.0.1:8000/api/health

停服:
  Ctrl+C  (前台)   /   Get-Process node,python | Stop-Process -Force   (后台)

端口冲突:
  Get-Process node,python | Stop-Process -Force

找不到 server 包:
  检查 cwd 是不是项目根目录（必须是 segmentation-gui-prototype，不是 BME_CT_Seg）
```

---

## 相关文档

- `docs/demo-day-checklist.md` — 演示当天一屏快查卡（前置约束 + 回退命令）
- `docs/local-cache-demo-runbook.md` — cache demo 7 步复跑手册 + cache_key 7 字段说明
- `README.md`「本地运行」段 — 完整 env vars 列表与模型权重准备