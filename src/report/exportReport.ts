import type { OrganDetail } from "../data/organDetails";
import type { InferenceStatus, ValidationSummary } from "../inference/inferenceClient";
import type { OrganLayer } from "../organLayerLogic";

export type ReportFormat = "html" | "json" | "pdf";

export type ReportData = {
  caseId: string;
  caseTarget: string;
  modelName: string;
  imageKind: string;
  imageDimensions?: string;
  resultKind: string;
  currentSlice: number;
  totalSlices: number;
  validation: ValidationSummary | null;
  inferenceStatus: InferenceStatus;
  organs: OrganLayer[];
  organDetails: Record<string, OrganDetail>;
  measurements: { id: number; label: string; x: number; y: number; hu: number; diameter: string; slice: number }[];
  timeline: { id: string; type: string; progress?: number; stage: string; message?: string; at: number }[];
  aiFindings: string[];
  generatedAt: string;
};

export function exportReport(data: ReportData, format: ReportFormat): void {
  switch (format) {
    case "html":
      exportHtmlReport(data, false);
      break;
    case "json":
      exportJsonReport(data);
      break;
    case "pdf":
      exportHtmlReport(data, true);
      break;
  }
}

function downloadFile(filename: string, content: string, mimeType: string) {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function formatDuration(seconds: number | undefined): string {
  if (!Number.isFinite(seconds) || seconds == null) return "—";
  const s = Math.max(0, Math.round(seconds));
  const m = Math.floor(s / 60);
  return m > 0 ? `${m}分${s % 60}秒` : `${s}秒`;
}

function formatBytes(bytes: number | undefined): string {
  if (!bytes) return "—";
  if (bytes < 1024) return `${bytes} B`;
  return `${(bytes / 1024).toFixed(1)} KB`;
}

function escapeHtml(text: string): string {
  return text.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
}

function buildHtmlContent(data: ReportData): string {
  const v = data.validation;
  const inf = data.inferenceStatus;
  const duration = inf.status === "succeeded" ? formatDuration(inf.duration_seconds) : "—";
  const resultSize = inf.status === "succeeded" ? formatBytes(inf.result_size_bytes) : "—";
  const jobId = (inf as { jobId?: string }).jobId ?? "—";
  const profile = (inf as { inference_options?: { profile?: string } }).inference_options?.profile ?? "—";

  const perLabelRows = v?.labels?.length
    ? v.labels.map((l) => `<tr>
        <td>${l.label}</td>
        <td>${escapeHtml(l.name ?? `Label ${l.label}`)}</td>
        <td>${l.dice != null ? l.dice.toFixed(6) : "N/A"}</td>
        <td>${l.prediction_voxels ?? "—"}</td>
        <td>${l.reference_voxels ?? "—"}</td>
      </tr>`).join("\n")
    : '<tr><td colspan="5">无逐标签数据</td></tr>';

  const organRows = data.organs.map((o) => {
    const detail = data.organDetails[o.id];
    return `<tr>
      <td><span style="display:inline-block;width:10px;height:10px;border-radius:50%;background:${o.color};margin-right:6px;vertical-align:middle;"></span>${escapeHtml(o.name)}</td>
      <td>${o.score != null ? o.score.toFixed(1) + "%" : "—"}</td>
      <td>${o.quality === "accepted" ? "通过" : "待复核"}</td>
      <td>${detail ? escapeHtml(detail.anatomicalLocation) : "—"}</td>
    </tr>`;
  }).join("\n");

  const measurementRows = data.measurements.length
    ? data.measurements.map((m) => `<tr>
        <td>${escapeHtml(m.label)}</td>
        <td>(${m.x.toFixed(1)}, ${m.y.toFixed(1)})</td>
        <td>${m.hu}</td>
        <td>${escapeHtml(m.diameter)}</td>
        <td>${m.slice}</td>
      </tr>`).join("\n")
    : '<tr><td colspan="5">暂无测量点</td></tr>';

  const timelineRows = data.timeline.length
    ? data.timeline.map((t) => `<tr>
        <td>${escapeHtml(t.stage)}</td>
        <td>${t.type}</td>
        <td>${t.progress != null ? t.progress + "%" : "—"}</td>
        <td>${new Date(t.at).toLocaleTimeString("zh-CN")}</td>
      </tr>`).join("\n")
    : '<tr><td colspan="4">无推理记录</td></tr>';

  const findingsHtml = data.aiFindings.length
    ? data.aiFindings.map((f) => `<li>${escapeHtml(f)}</li>`).join("\n")
    : "<li>暂无发现</li>";

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CT 分割报告 - ${escapeHtml(data.caseId)}</title>
<style>
  * { margin: 0; padding: 0; box-sizing: border-box; }
  body { font-family: -apple-system, "Microsoft YaHei", "PingFang SC", sans-serif; color: #1a1a2e; background: #fff; padding: 40px; line-height: 1.6; }
  h1 { font-size: 24px; margin-bottom: 4px; }
  h2 { font-size: 18px; margin: 28px 0 12px; padding-bottom: 6px; border-bottom: 2px solid #e0e0e0; }
  h3 { font-size: 15px; margin: 16px 0 8px; }
  .subtitle { color: #666; font-size: 13px; margin-bottom: 24px; }
  .grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 12px; margin-bottom: 20px; }
  .card { background: #f8f9fa; border-radius: 8px; padding: 14px; border: 1px solid #e9ecef; }
  .card .label { font-size: 12px; color: #666; margin-bottom: 4px; }
  .card .value { font-size: 16px; font-weight: 600; }
  table { width: 100%; border-collapse: collapse; margin-bottom: 20px; font-size: 13px; }
  th, td { padding: 8px 10px; text-align: left; border-bottom: 1px solid #e9ecef; }
  th { background: #f1f3f5; font-weight: 600; font-size: 12px; text-transform: uppercase; color: #495057; }
  tr:hover { background: #f8f9fa; }
  .status-passed { color: #2b8a3e; font-weight: 600; }
  .status-review { color: #e67700; font-weight: 600; }
  .status-unavailable { color: #868e96; }
  ul { padding-left: 20px; margin-bottom: 16px; }
  li { margin-bottom: 4px; font-size: 14px; }
  .footer { margin-top: 40px; padding-top: 16px; border-top: 1px solid #e0e0e0; font-size: 12px; color: #999; }
  @media print {
    body { padding: 20px; }
    h2 { break-after: avoid; }
    table { break-inside: avoid; }
    .card { break-inside: avoid; }
  }
</style>
</head>
<body>

<h1>CT 分割报告</h1>
<p class="subtitle">${escapeHtml(data.caseId)} · ${escapeHtml(data.caseTarget)} · 生成于 ${escapeHtml(data.generatedAt)}</p>

<h2>概览</h2>
<div class="grid">
  <div class="card"><div class="label">模型</div><div class="value">${escapeHtml(data.modelName)}</div></div>
  <div class="card"><div class="label">推理模式</div><div class="value">${escapeHtml(profile)}</div></div>
  <div class="card"><div class="label">耗时</div><div class="value">${duration}</div></div>
  <div class="card"><div class="label">结果大小</div><div class="value">${resultSize}</div></div>
  <div class="card"><div class="label">Job ID</div><div class="value" style="font-size:12px;word-break:break-all;">${escapeHtml(jobId)}</div></div>
  <div class="card"><div class="label">切片</div><div class="value">${data.currentSlice} / ${data.totalSlices}</div></div>
  <div class="card"><div class="label">原图</div><div class="value">${escapeHtml(data.imageKind)}</div></div>
  <div class="card"><div class="label">结果</div><div class="value">${escapeHtml(data.resultKind)}</div></div>
</div>

<h2>验证指标</h2>
${v ? `<div class="grid">
  <div class="card"><div class="label">验证状态</div><div class="value status-${v.status}">${v.status === "passed" ? "通过" : v.status === "review" ? "待复核" : "不可用"}</div></div>
  <div class="card"><div class="label">平均 Dice</div><div class="value">${v.mean_dice?.toFixed(6) ?? "—"}</div></div>
  <div class="card"><div class="label">最低 Dice</div><div class="value">${v.min_dice?.toFixed(6) ?? "—"}</div></div>
  <div class="card"><div class="label">前景 Dice</div><div class="value">${v.foreground_dice?.toFixed(6) ?? "—"}</div></div>
  ${v.remap_applied ? `<div class="card"><div class="label">标签重映射</div><div class="value">${escapeHtml(v.remap_source ?? "已知数据集")} → 当前模型</div></div>` : ""}
</div>` : '<p style="color:#868e96;">尚未执行验证（需导入标签 CT 或载入参考病例）</p>'}

${v?.labels?.length ? `<h3>逐标签指标</h3>
<table>
  <thead><tr><th>Label</th><th>器官</th><th>Dice</th><th>预测体素</th><th>参考体素</th></tr></thead>
  <tbody>${perLabelRows}</tbody>
</table>` : ""}

<h2>器官列表</h2>
<table>
  <thead><tr><th>器官</th><th>质控分数</th><th>状态</th><th>解剖位置</th></tr></thead>
  <tbody>${organRows}</tbody>
</table>

<h2>关键发现</h2>
<ul>${findingsHtml}</ul>

<h2>测量点</h2>
<table>
  <thead><tr><th>编号</th><th>坐标</th><th>HU</th><th>直径</th><th>切片</th></tr></thead>
  <tbody>${measurementRows}</tbody>
</table>

<h2>推理时间线</h2>
<table>
  <thead><tr><th>阶段</th><th>类型</th><th>进度</th><th>时间</th></tr></thead>
  <tbody>${timelineRows}</tbody>
</table>

<div class="footer">
  本报告由 CT 分割 GUI 原型自动生成 · ${escapeHtml(data.generatedAt)}
</div>

</body>
</html>`;
}

function exportHtmlReport(data: ReportData, printMode: boolean) {
  const html = buildHtmlContent(data);
  const filename = `segmentation-report-${data.caseId}-${Date.now()}.html`;

  if (printMode) {
    const win = window.open("", "_blank");
    if (win) {
      win.document.write(html);
      win.document.close();
      setTimeout(() => win.print(), 300);
    }
  } else {
    downloadFile(filename, html, "text/html;charset=utf-8");
  }
}

function exportJsonReport(data: ReportData) {
  const output = {
    schema_version: "1.0",
    report_type: "segmentation",
    generated_at: data.generatedAt,
    case: {
      id: data.caseId,
      target: data.caseTarget,
      image_kind: data.imageKind,
      image_dimensions: data.imageDimensions,
      result_kind: data.resultKind,
      current_slice: data.currentSlice,
      total_slices: data.totalSlices,
    },
    model: { name: data.modelName },
    validation: data.validation,
    inference: data.inferenceStatus,
    organs: data.organs.map((o) => ({
      id: o.id,
      name: o.name,
      color: o.color,
      score: o.score,
      quality: o.quality,
      visible: o.visible,
    })),
    measurements: data.measurements,
    timeline: data.timeline,
    findings: data.aiFindings,
  };

  const filename = `segmentation-report-${data.caseId}-${Date.now()}.json`;
  downloadFile(filename, JSON.stringify(output, null, 2), "application/json;charset=utf-8");
}
