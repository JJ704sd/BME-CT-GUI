import type { OrganDetail } from "../data/organDetails";
import type { InferenceStatus, ValidationSummary } from "../inference/inferenceClient";
import type { QuantificationSummary } from "../imaging/quantification";
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
  quantification: QuantificationSummary;
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

function formatMetric(value: number | null | undefined, digits = 4): string {
  if (value == null || !Number.isFinite(Number(value))) return "N/A";
  return Number(value).toFixed(digits);
}

function scoreLevel(value: number | null | undefined): "good" | "warn" | "bad" | "na" {
  if (value == null || !Number.isFinite(Number(value))) return "na";
  const v = Number(value);
  if (v >= 0.85) return "good";
  if (v >= 0.7) return "warn";
  return "bad";
}

function distLevel(value: number | null | undefined): "good" | "warn" | "bad" | "na" {
  if (value == null || !Number.isFinite(Number(value))) return "na";
  const v = Number(value);
  if (v <= 1) return "good";
  if (v <= 3) return "warn";
  return "bad";
}

function distBarPercent(value: number | null | undefined, max = 5): number {
  if (value == null || !Number.isFinite(Number(value))) return 0;
  const v = Math.max(0, Number(value));
  return Math.max(0, Math.min(100, (1 - Math.min(v, max) / max) * 100));
}

function statusLabel(status: ValidationSummary["status"] | undefined): string {
  if (status === "passed") return "通过";
  if (status === "review") return "待复核";
  return "不可用";
}

function statusBadgeHtml(status: ValidationSummary["status"] | undefined): string {
  const cls = status === "passed" ? "badge-passed" : status === "review" ? "badge-review" : "badge-na";
  return `<span class="badge ${cls}">${statusLabel(status)}</span>`;
}

function metricBarHtml(value: number | null | undefined, kind: "dice" | "iou" | "pix" | "dist", digits = 4): string {
  if (value == null || !Number.isFinite(Number(value))) return '<span class="muted">N/A</span>';
  const v = Number(value);
  if (kind === "dist") {
    const pct = distBarPercent(v).toFixed(1);
    const level = distLevel(v);
    return `<span class="metric-cell"><span class="metric-bar dist-${level}"><span class="metric-bar-fill" style="width:${pct}%"></span></span><span class="metric-num">${formatMetric(v, 2)}</span></span>`;
  }
  const nv = Math.max(0, Math.min(1, v));
  const pct = (nv * 100).toFixed(1);
  const level = scoreLevel(nv);
  return `<span class="metric-cell"><span class="metric-bar ${kind}-${level}"><span class="metric-bar-fill" style="width:${pct}%"></span></span><span class="metric-num">${formatMetric(v, digits)}</span></span>`;
}

function metricCard(label: string, value: number | null | undefined, suffix = "", kind: "dice" | "iou" | "pix" | "dist" | "vox" = "dice"): string {
  const digits = kind === "dist" ? 2 : 4;
  const display = value == null || !Number.isFinite(Number(value)) ? "—" : `${formatMetric(value, digits)}${suffix}`;
  const bar = kind === "vox"
    ? ""
    : kind === "dist"
      ? `<div class="card-bar dist-${distLevel(value)}"><div class="card-bar-fill" style="width:${distBarPercent(value).toFixed(1)}%"></div></div>`
      : `<div class="card-bar ${kind}-${scoreLevel(value)}"><div class="card-bar-fill" style="width:${value == null ? 0 : Math.max(0, Math.min(1, Number(value))) * 100}%"></div></div>`;
  const level = kind === "vox" ? "" : kind === "dist" ? ` bar-${distLevel(value)}` : ` bar-${scoreLevel(value)}`;
  return `<div class="metric-card${level}"><div class="card-label">${escapeHtml(label)}</div><div class="card-value">${display}</div>${bar}</div>`;
}

function buildHtmlContent(data: ReportData): string {
  const v = data.validation;
  const inf = data.inferenceStatus;
  const duration = inf.status === "succeeded" ? formatDuration(inf.duration_seconds) : "—";
  const resultSize = inf.status === "succeeded" ? formatBytes(inf.result_size_bytes) : "—";
  const jobId = (inf as { jobId?: string }).jobId ?? "—";
  const profile = (inf as { inference_options?: { profile?: string } }).inference_options?.profile ?? "—";
  const cachedFlag = (inf as { cached_result?: boolean }).cached_result;
  const cacheSource = (inf as { cache_source_job_id?: string }).cache_source_job_id;
  const passedCount = v?.labels?.filter((l) => l.dice != null && Number(l.dice) >= 0.85).length ?? 0;
  const reviewCount = v?.labels?.filter((l) => l.dice != null && Number(l.dice) < 0.85).length ?? 0;
  const naCount = v?.labels?.filter((l) => l.dice == null).length ?? 0;

  const perLabelRows = v?.labels?.length
    ? v.labels.map((l) => `<tr>
        <td class="num">${l.label}</td>
        <td>${escapeHtml(l.name ?? `Label ${l.label}`)}</td>
        <td>${metricBarHtml(l.dice, "dice")}</td>
        <td>${metricBarHtml(l.iou, "iou")}</td>
        <td>${metricBarHtml(l.pixel_accuracy, "pix")}</td>
        <td>${metricBarHtml(l.asd, "dist")}</td>
        <td>${metricBarHtml(l.hd95, "dist")}</td>
        <td>${metricBarHtml(l.hd, "dist")}</td>
        <td class="num">${l.prediction_voxels?.toLocaleString() ?? "—"}</td>
        <td class="num">${l.reference_voxels?.toLocaleString() ?? "—"}</td>
      </tr>`).join("\n")
    : '<tr><td colspan="10" class="muted">无逐标签数据</td></tr>';

  const organRows = data.organs.map((o) => {
    const detail = data.organDetails[o.id];
    const score = o.score != null ? Number(o.score) : null;
    const level = scoreLevel(score != null ? score / 100 : null);
    const quality = o.quality === "accepted" ? "通过" : "待复核";
    const qualityClass = o.quality === "accepted" ? "tag-passed" : "tag-review";
    return `<tr>
      <td><span class="organ-dot" style="background:${o.color}"></span>${escapeHtml(o.name)}</td>
      <td>${score != null ? `<span class="score-pill ${level}">${score.toFixed(1)}%</span>` : '<span class="muted">—</span>'}</td>
      <td><span class="tag ${qualityClass}">${quality}</span></td>
      <td class="anatomical">${detail ? escapeHtml(detail.anatomicalLocation) : "—"}</td>
    </tr>`;
  }).join("\n");

  const quantificationRows = data.quantification.organs.length
    ? data.quantification.organs.slice(0, 12).map((organ) => `<tr>
        <td>${escapeHtml(organ.name)}</td>
        <td class="num">${organ.volumeMl != null ? organ.volumeMl.toFixed(1) + " ml" : "—"}</td>
        <td class="num">${organ.maxAxialAreaMm2 != null ? organ.maxAxialAreaMm2.toFixed(1) + " mm²" : "—"}</td>
        <td class="num">${organ.estimatedLengthMm != null ? organ.estimatedLengthMm.toFixed(1) + " mm" : "—"}</td>
        <td class="num">${organ.maxDiameterMm != null ? organ.maxDiameterMm.toFixed(1) + " mm" : "—"}</td>
        <td class="num">${organ.voxelCount || "—"}</td>
        <td class="anatomical">${escapeHtml(organ.lumenAreaInterpretation)}</td>
      </tr>`).join("\n")
    : '<tr><td colspan="7" class="muted">暂无量化指标</td></tr>';

  const measurementRows = data.measurements.length
    ? data.measurements.map((m) => `<tr>
        <td><span class="tag tag-measure">${escapeHtml(m.label)}</span></td>
        <td class="num">(${m.x.toFixed(1)}, ${m.y.toFixed(1)})</td>
        <td class="num">${m.hu}</td>
        <td>${escapeHtml(m.diameter)}</td>
        <td class="num">${m.slice}</td>
      </tr>`).join("\n")
    : '<tr><td colspan="5" class="muted">暂无测量点</td></tr>';

  const timelineRows = data.timeline.length
    ? data.timeline.map((t) => {
        const typeClass = t.type === "complete" ? "tag-passed" : t.type === "error" ? "tag-failed" : t.type === "progress" ? "tag-progress" : "tag-info";
        return `<tr>
          <td>${escapeHtml(t.stage)}</td>
          <td><span class="tag ${typeClass}">${escapeHtml(t.type)}</span></td>
          <td class="num">${t.progress != null ? t.progress + "%" : "—"}</td>
          <td class="num">${new Date(t.at).toLocaleTimeString("zh-CN")}</td>
        </tr>`;
      }).join("\n")
    : '<tr><td colspan="4" class="muted">无推理记录</td></tr>';

  const findingsHtml = data.aiFindings.length
    ? data.aiFindings.map((f) => `<li>${escapeHtml(f)}</li>`).join("\n")
    : "<li class=\"muted\">暂无发现</li>";

  const hasValidation = v != null;

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CT 分割报告 - ${escapeHtml(data.caseId)}</title>
<style>
  :root {
    --bg: #f5f7fa;
    --surface: #ffffff;
    --ink: #1a1d29;
    --ink-soft: #4a5168;
    --muted: #8b93a7;
    --line: #e5e9f0;
    --line-soft: #eef1f6;
    --accent: #4263eb;
    --good: #2b8a3e;
    --good-bg: #e6f4ea;
    --warn: #d97706;
    --warn-bg: #fff3e0;
    --bad: #c92a2a;
    --bad-bg: #fde8e8;
    --info-bg: #e7f0ff;
    --shadow: 0 1px 2px rgba(20, 25, 50, 0.04), 0 2px 8px rgba(20, 25, 50, 0.04);
    --radius: 10px;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { background: var(--bg); }
  body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Microsoft YaHei", "PingFang SC", "Hiragino Sans GB", sans-serif;
    color: var(--ink);
    line-height: 1.55;
    padding: 32px 16px;
  }
  .page {
    max-width: 1080px;
    margin: 0 auto;
    background: var(--surface);
    border-radius: 14px;
    box-shadow: var(--shadow);
    overflow: hidden;
  }
  .header {
    background: linear-gradient(135deg, #1a2b5c 0%, #2a4a8c 50%, #4263eb 100%);
    color: #fff;
    padding: 28px 36px 24px;
  }
  .header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .header h1 { font-size: 24px; font-weight: 600; letter-spacing: 0.5px; }
  .header .subtitle { margin-top: 6px; font-size: 13px; opacity: 0.82; }
  .header .meta-row { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 14px; }
  .chip { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: rgba(255, 255, 255, 0.16); border-radius: 999px; font-size: 12px; backdrop-filter: blur(4px); }
  .chip strong { font-weight: 600; }
  .badge { display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 13px; font-weight: 600; letter-spacing: 0.3px; }
  .badge-passed { background: var(--good-bg); color: var(--good); }
  .badge-review { background: var(--warn-bg); color: var(--warn); }
  .badge-na { background: #e9ecef; color: var(--muted); }
  .content { padding: 28px 36px 36px; }
  h2 {
    font-size: 17px; font-weight: 600;
    margin: 28px 0 14px;
    padding-bottom: 8px;
    border-bottom: 1px solid var(--line);
    display: flex; align-items: center; gap: 10px;
  }
  h2::before {
    content: ""; display: inline-block;
    width: 4px; height: 16px; border-radius: 2px;
    background: var(--accent);
  }
  h2:first-child { margin-top: 0; }
  h3 { font-size: 14px; font-weight: 600; color: var(--ink-soft); margin: 16px 0 8px; }

  .overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 10px;
  }
  .overview-card {
    background: #f8fafc;
    border: 1px solid var(--line-soft);
    border-radius: var(--radius);
    padding: 12px 14px;
  }
  .overview-card .label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.6px; margin-bottom: 4px; }
  .overview-card .value { font-size: 15px; font-weight: 600; color: var(--ink); word-break: break-all; }
  .overview-card .value.small { font-size: 12px; font-weight: 500; }

  .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
  .metric-card {
    background: var(--surface);
    border: 1px solid var(--line);
    border-radius: var(--radius);
    padding: 14px 16px;
    position: relative;
    overflow: hidden;
  }
  .metric-card.bar-good { border-color: #b8e0c2; background: linear-gradient(180deg, #f6fbf7 0%, #ffffff 60%); }
  .metric-card.bar-warn { border-color: #f5d8a0; background: linear-gradient(180deg, #fffaf0 0%, #ffffff 60%); }
  .metric-card.bar-bad { border-color: #f5b8b8; background: linear-gradient(180deg, #fef5f5 0%, #ffffff 60%); }
  .card-label { font-size: 11px; color: var(--muted); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
  .card-value { font-size: 22px; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
  .card-bar { height: 4px; background: var(--line-soft); border-radius: 2px; margin-top: 10px; overflow: hidden; }
  .card-bar-fill { height: 100%; border-radius: 2px; transition: width 0.3s; }
  .card-bar-fill, .dice-good .card-bar-fill, .iou-good .card-bar-fill, .pix-good .card-bar-fill { background: linear-gradient(90deg, #2b8a3e, #51cf66); }
  .card-bar-fill, .dice-warn .card-bar-fill, .iou-warn .card-bar-fill, .pix-warn .card-bar-fill { background: linear-gradient(90deg, #d97706, #f59f00); }
  .card-bar-fill, .dice-bad .card-bar-fill, .iou-bad .card-bar-fill, .pix-bad .card-bar-fill { background: linear-gradient(90deg, #c92a2a, #ff6b6b); }
  .card-bar-fill, .dice-na .card-bar-fill, .iou-na .card-bar-fill, .pix-na .card-bar-fill { background: var(--muted); }
  .card-bar-fill, .dist-good .card-bar-fill { background: linear-gradient(90deg, #2b8a3e, #51cf66); }
  .card-bar-fill, .dist-warn .card-bar-fill { background: linear-gradient(90deg, #d97706, #f59f00); }
  .card-bar-fill, .dist-bad .card-bar-fill { background: linear-gradient(90deg, #c92a2a, #ff6b6b); }
  .card-bar-fill, .dist-na .card-bar-fill { background: var(--muted); }

  .metric-group { margin-bottom: 18px; }
  .metric-group-title { font-size: 12px; font-weight: 600; color: var(--ink-soft); text-transform: uppercase; letter-spacing: 0.8px; margin-bottom: 10px; padding-left: 2px; }

  .label-stats { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 12px; }
  .tag { display: inline-block; padding: 3px 10px; border-radius: 999px; font-size: 12px; font-weight: 500; line-height: 1.5; }
  .tag-passed { background: var(--good-bg); color: var(--good); }
  .tag-review { background: var(--warn-bg); color: var(--warn); }
  .tag-failed { background: var(--bad-bg); color: var(--bad); }
  .tag-progress { background: var(--info-bg); color: var(--accent); }
  .tag-info { background: #eef1f6; color: var(--ink-soft); }
  .tag-measure { background: #f3e8ff; color: #7c3aed; font-family: ui-monospace, "SF Mono", Menlo, monospace; }

  .score-pill { display: inline-block; padding: 2px 10px; border-radius: 6px; font-size: 12px; font-weight: 600; font-variant-numeric: tabular-nums; }
  .score-pill.good { background: var(--good-bg); color: var(--good); }
  .score-pill.warn { background: var(--warn-bg); color: var(--warn); }
  .score-pill.bad { background: var(--bad-bg); color: var(--bad); }
  .score-pill.na { background: #eef1f6; color: var(--muted); }

  .organ-dot { display: inline-block; width: 10px; height: 10px; border-radius: 50%; margin-right: 6px; vertical-align: middle; box-shadow: 0 0 0 2px rgba(255, 255, 255, 0.8); }

  table { width: 100%; border-collapse: separate; border-spacing: 0; margin-bottom: 20px; font-size: 13px; background: var(--surface); border: 1px solid var(--line); border-radius: var(--radius); overflow: hidden; }
  thead th { background: #f8fafc; font-weight: 600; font-size: 11px; text-transform: uppercase; letter-spacing: 0.6px; color: var(--ink-soft); padding: 10px 12px; text-align: left; border-bottom: 1px solid var(--line); }
  thead th.num { text-align: right; }
  tbody td { padding: 9px 12px; border-bottom: 1px solid var(--line-soft); }
  tbody td.num { text-align: right; font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
  tbody td.anatomical { color: var(--ink-soft); font-size: 12px; }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover { background: #fafbfc; }
  tbody tr td.muted, .muted { color: var(--muted); }

  .metric-cell { display: inline-flex; align-items: center; gap: 8px; min-width: 110px; }
  .metric-num { font-size: 12px; font-variant-numeric: tabular-nums; color: var(--ink-soft); min-width: 42px; text-align: right; }
  .metric-bar { flex: 1; height: 6px; background: var(--line-soft); border-radius: 3px; overflow: hidden; min-width: 50px; }
  .metric-bar-fill { height: 100%; border-radius: 3px; }
  .dice-good .metric-bar-fill, .iou-good .metric-bar-fill, .pix-good .metric-bar-fill { background: linear-gradient(90deg, #2b8a3e, #51cf66); }
  .dice-warn .metric-bar-fill, .iou-warn .metric-bar-fill, .pix-warn .metric-bar-fill { background: linear-gradient(90deg, #d97706, #f59f00); }
  .dice-bad .metric-bar-fill, .iou-bad .metric-bar-fill, .pix-bad .metric-bar-fill { background: linear-gradient(90deg, #c92a2a, #ff6b6b); }
  .dice-na .metric-bar-fill, .iou-na .metric-bar-fill, .pix-na .metric-bar-fill { background: var(--muted); }
  .dist-good .metric-bar-fill { background: linear-gradient(90deg, #2b8a3e, #51cf66); }
  .dist-warn .metric-bar-fill { background: linear-gradient(90deg, #d97706, #f59f00); }
  .dist-bad .metric-bar-fill { background: linear-gradient(90deg, #c92a2a, #ff6b6b); }
  .dist-na .metric-bar-fill { background: var(--muted); }

  ul { padding-left: 22px; margin-bottom: 16px; }
  li { margin-bottom: 6px; font-size: 14px; }

  .footer {
    margin-top: 32px;
    padding: 18px 36px;
    border-top: 1px solid var(--line);
    background: #f8fafc;
    font-size: 12px;
    color: var(--muted);
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;
  }
  .footer .hint { font-style: italic; }

  @media print {
    body { background: #fff; padding: 0; }
    .page { box-shadow: none; border-radius: 0; max-width: none; }
    h2 { break-after: avoid; }
    table, .metric-card, .overview-card { break-inside: avoid; }
    thead { display: table-header-group; }
    .header { background: #1a2b5c !important; -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .card-bar, .metric-bar, .badge, .tag, .score-pill { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
  }
</style>
</head>
<body>
<div class="page">

<div class="header">
  <div class="header-row">
    <div>
      <h1>CT 分割报告 · ${escapeHtml(data.caseId)}</h1>
      <div class="subtitle">${escapeHtml(data.caseTarget)} · 生成于 ${escapeHtml(data.generatedAt)}${cachedFlag ? " · <em>缓存命中</em>" : ""}</div>
      <div class="meta-row">
        <span class="chip">模型 <strong>${escapeHtml(data.modelName)}</strong></span>
        <span class="chip">推理模式 <strong>${escapeHtml(profile)}</strong></span>
        <span class="chip">耗时 <strong>${duration}</strong></span>
        <span class="chip">结果 <strong>${resultSize}</strong></span>
        <span class="chip">切片 <strong>${data.currentSlice} / ${data.totalSlices}</strong></span>
        <span class="chip">Job <strong>${escapeHtml(jobId)}</strong>${cacheSource ? ` <span style="opacity:0.7">← ${escapeHtml(cacheSource)}</span>` : ""}</span>
      </div>
    </div>
    ${hasValidation ? `<div>${statusBadgeHtml(v.status)}</div>` : ""}
  </div>
</div>

<div class="content">

<h2>概览</h2>
<div class="overview-grid">
  <div class="overview-card"><div class="label">模型</div><div class="value small">${escapeHtml(data.modelName)}</div></div>
  <div class="overview-card"><div class="label">推理模式</div><div class="value">${escapeHtml(profile)}</div></div>
  <div class="overview-card"><div class="label">耗时</div><div class="value">${duration}</div></div>
  <div class="overview-card"><div class="label">结果大小</div><div class="value">${resultSize}</div></div>
  <div class="overview-card"><div class="label">Job ID</div><div class="value small">${escapeHtml(jobId)}</div></div>
  <div class="overview-card"><div class="label">切片进度</div><div class="value">${data.currentSlice} / ${data.totalSlices}</div></div>
  <div class="overview-card"><div class="label">原图</div><div class="value small">${escapeHtml(data.imageKind)}</div></div>
  <div class="overview-card"><div class="label">结果</div><div class="value small">${escapeHtml(data.resultKind)}</div></div>
</div>

${hasValidation ? `
<h2>验证指标</h2>
<div class="metric-group">
  <div class="metric-group-title">区域重叠度 · Dice / IoU</div>
  <div class="metric-grid">
    ${metricCard("平均 Dice", v.mean_dice, "", "dice")}
    ${metricCard("最低 Dice", v.min_dice, "", "dice")}
    ${metricCard("前景 Dice", v.foreground_dice, "", "dice")}
    ${metricCard("平均 IoU", v.mean_iou, "", "iou")}
    ${metricCard("最低 IoU", v.min_iou, "", "iou")}
    ${metricCard("前景 IoU", v.foreground_iou, "", "iou")}
  </div>
</div>
<div class="metric-group">
  <div class="metric-group-title">像素准确率 · Pixel Accuracy（越高越好）</div>
  <div class="metric-grid">
    ${metricCard("总准确率", v.pixel_accuracy, "", "pix")}
    ${metricCard("平均类别准确率", v.mean_pixel_accuracy, "", "pix")}
    ${metricCard("最低类别准确率", v.min_pixel_accuracy, "", "pix")}
    ${metricCard("前景准确率", v.foreground_pixel_accuracy, "", "pix")}
  </div>
</div>
<div class="metric-group">
  <div class="metric-group-title">表面距离 · HD / HD95 / ASD（${escapeHtml(v.surface_distance_unit ?? "mm")}，越低越好）</div>
  <div class="metric-grid">
    ${metricCard("平均 HD", v.mean_hd, " mm", "dist")}
    ${metricCard("最大 HD", v.max_hd, " mm", "dist")}
    ${metricCard("前景 HD", v.foreground_hd, " mm", "dist")}
    ${metricCard("平均 HD95", v.mean_hd95, " mm", "dist")}
    ${metricCard("最大 HD95", v.max_hd95, " mm", "dist")}
    ${metricCard("前景 HD95", v.foreground_hd95, " mm", "dist")}
    ${metricCard("平均 ASD", v.mean_asd, " mm", "dist")}
    ${metricCard("最大 ASD", v.max_asd, " mm", "dist")}
    ${metricCard("前景 ASD", v.foreground_asd, " mm", "dist")}
  </div>
</div>
<div class="label-stats">
  ${v.remap_applied ? `<span class="tag tag-progress">标签重映射 · ${escapeHtml(v.remap_source ?? "已知数据集")} → 当前模型</span>` : ""}
  ${v.historical ? `<span class="tag tag-info">历史离线缓存摘要</span>` : ""}
  ${v.accepted === true ? `<span class="tag tag-passed">通过验证阈值</span>` : ""}
  ${v.accepted === false ? `<span class="tag tag-review">未达阈值</span>` : ""}
  ${v.thresholds?.mean_dice != null ? `<span class="tag tag-info">mean_dice 阈值 ${Number(v.thresholds.mean_dice).toFixed(2)}</span>` : ""}
  ${v.spacing && v.spacing.length ? `<span class="tag tag-info">体素间距 (${escapeHtml(v.spacing.map((n) => Number(n).toFixed(2)).join(" × "))} mm)</span>` : ""}
</div>
${v.message ? `<p style="margin-top:10px;color:var(--ink-soft);font-size:13px;">${escapeHtml(v.message)}</p>` : ""}

<h3>逐标签指标 <span style="font-weight:400;color:var(--muted);font-size:12px;">（Dice ≥ 0.85 通过 · IoU 同口径 · 距离越低越好）</span></h3>
<table>
  <thead>
    <tr>
      <th class="num" style="width:60px">Label</th>
      <th>器官</th>
      <th>Dice</th>
      <th>IoU</th>
      <th>像素准确率</th>
      <th>ASD (mm)</th>
      <th>HD95 (mm)</th>
      <th>HD (mm)</th>
      <th class="num">预测体素</th>
      <th class="num">参考体素</th>
    </tr>
  </thead>
  <tbody>${perLabelRows}</tbody>
</table>
<div class="label-stats" style="margin-top:-8px;margin-bottom:20px;">
  <span class="tag tag-passed">通过 ${passedCount}</span>
  <span class="tag tag-review">待复核 ${reviewCount}</span>
  <span class="tag tag-info">N/A ${naCount}</span>
</div>
` : '<p style="color:var(--muted);font-size:13px;padding:14px;background:#f8fafc;border-radius:8px;border:1px dashed var(--line);">尚未执行验证（需导入标签 CT 或载入参考病例）</p>'}

<h2>器官列表</h2>
<table>
  <thead>
    <tr>
      <th>器官</th>
      <th>质控分数</th>
      <th>状态</th>
      <th>解剖位置</th>
    </tr>
  </thead>
  <tbody>${organRows}</tbody>
</table>

<h2>影像量化分析</h2>
<p style="color:var(--ink-soft);font-size:12px;margin-bottom:10px;">${escapeHtml(data.quantification.note)} 体积、截面积和长度由自动分割 mask 与 NIfTI spacing 估算；壁厚、精确管腔面积、中心线长度属于后续扩展。</p>
<table>
  <thead>
    <tr>
      <th>器官</th>
      <th class="num">体积</th>
      <th class="num">最大横断面积</th>
      <th class="num">估算长度</th>
      <th class="num">最长径</th>
      <th class="num">体素数</th>
      <th>管腔解释</th>
    </tr>
  </thead>
  <tbody>${quantificationRows}</tbody>
</table>

<h2>关键发现</h2>
<ul>${findingsHtml}</ul>

<h2>测量点</h2>
<table>
  <thead>
    <tr>
      <th>编号</th>
      <th class="num">坐标</th>
      <th class="num">HU</th>
      <th>直径</th>
      <th class="num">切片</th>
    </tr>
  </thead>
  <tbody>${measurementRows}</tbody>
</table>

<h2>推理时间线</h2>
<table>
  <thead>
    <tr>
      <th>阶段</th>
      <th>类型</th>
      <th class="num">进度</th>
      <th class="num">时间</th>
    </tr>
  </thead>
  <tbody>${timelineRows}</tbody>
</table>

</div>

<div class="footer">
  <span>本报告由 CT 分割 GUI 原型自动生成 · ${escapeHtml(data.generatedAt)}</span>
  <span class="hint">Dice / IoU 取自 ${escapeHtml(v?.sample_id ?? "当前病例")}${cachedFlag ? "（缓存命中）" : "的验证结果"}</span>
</div>

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
    schema_version: "1.1",
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
    quantification: data.quantification,
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
