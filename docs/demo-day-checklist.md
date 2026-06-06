# 演示当天 Checklist

> 一屏可读的快捷卡片。详细 7 步与已知约束见 `docs/local-cache-demo-runbook.md`（如果 start_local_demo 失败，回退到 runbook 手工命令）。

**前置确认（每天第一次演示前）：**

- [ ] `D:\BME2026\BME_CT_Seg\segmentation-gui-prototype` 是 cwd
- [ ] `nnunetv2_files\checkpoint_best.pth`（1.1 GB）存在
- [ ] `nnunetv2_files\amos_0117(3).nii.gz`（原图）+ `amos_0117(2).nii.gz`（label）存在
- [ ] `nnunetv2_files\FLARE22_Tr_0009_0000.nii.gz`（原图）+ `FLARE22_Tr_0009.nii.gz`（label）存在
- [ ] RTX 4060 上没别的进程吃显存（`nvidia-smi` 应能看到空闲）

**演示流程：**

1. `cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype`
2. `python tools/start_local_demo.py`
3. 等 ~5s，看到 `Backend ready: 4 reference case(s) exposed at /api/samples:` + 4 行 case 列表 + `Open the GUI at: http://127.0.0.1:5173/`
4. 浏览器打开 `http://127.0.0.1:5173/`
5. Ctrl+C 退出

**演示中可能用到：**

- 验证后端：`curl http://127.0.0.1:8000/api/samples`（应返回 4 个 sample）
- 验证前端：`curl -I http://127.0.0.1:5173/`（应 HTTP 200）
- 重新预热缓存：`python tools/seed_demo_cache.py`（幂等；缺 `validation_summary.json` 时会补上）
- 后端日志：脚本 stdout 实时打印；前端 SSE 进度从 GUI 底部进度条看

**如果 `start_local_demo` 失败回退 runbook：**

```bash
cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
SEGMENTATION_REFERENCE_CASES_JSON="D:/BME2026/BME_CT_Seg/segmentation-gui-prototype/examples/reference_cases.json" \
  "D:/BME2026/BME_CT_Seg/nnunet_env/Scripts/python.exe" -m uvicorn server.main:app --host 127.0.0.1 --port 8000
# 另一窗口
cd D:\BME2026\BME_CT_Seg\segmentation-gui-prototype
npm run dev
```

详见 `docs/local-cache-demo-runbook.md` 的「启动命令」段。
