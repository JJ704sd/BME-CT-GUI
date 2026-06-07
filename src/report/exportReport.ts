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

function spacingClass(mm: number): string {
  if (mm <= 0.7) return "s0-7";
  if (mm <= 1.0) return "s1-0";
  if (mm <= 1.2) return "s1-2";
  if (mm <= 1.5) return "s1-5";
  return "s2-0";
}

function spacingCellsHtml(spacing: number[]): string {
  return spacing
    .slice(0, 3)
    .map((n, i) => `<span class="spacing-cell ${spacingClass(Number(n))}" title="${Number(n).toFixed(3)} mm"></span><span class="spacing-axis">${["x", "y", "z"][i] ?? ""}</span>`)
    .join("");
}

type FindingSeverity = "high" | "medium" | "low";

function classifyFindingSeverity(text: string): FindingSeverity {
  const t = text.toLowerCase();
  if (/(错误|失败|异常|warning|error|failed|异常|不可用|缺失|崩溃|超时|越界|fail)/.test(t)) return "high";
  if (/(偏高|偏低|不稳定|待复核|review|warning|警告|下降|回落|偏差|不确定|可能)/.test(t)) return "medium";
  return "low";
}

function findingSeverityLabel(sev: FindingSeverity): string {
  return { high: "high", medium: "medium", low: "low" }[sev];
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

function distributionChartHtml(findings: string[]): string {
  if (!findings.length) return "";
  const buckets: Record<FindingSeverity, { label: string; items: string[] }> = {
    high: { label: "High", items: [] },
    medium: { label: "Medium", items: [] },
    low: { label: "Low", items: [] },
  };
  for (const f of findings) {
    buckets[classifyFindingSeverity(f)].items.push(f);
  }
  const total = findings.length;
  const maxCount = Math.max(1, ...Object.values(buckets).map((b) => b.items.length));
  const widthPct = (n: number): string => ((n / maxCount) * 100).toFixed(1);
  const rows: string[] = [];
  for (const key of ["high", "medium", "low"] as FindingSeverity[]) {
    const b = buckets[key];
    const pct = Number(widthPct(b.items.length));
    rows.push(`<div class="dc-row"><span class="dc-label">${b.label}</span><span class="dc-bar-track"><span class="dc-bar-fill ${key}" style="width:${pct}%"></span></span><span class="dc-val">${b.items.length} / ${total}</span></div>`);
  }
  return `<div class="dist-chart" aria-label="关键发现分布">
  <div class="dc-title">关键发现分布 · 按严重度 <span class="dc-en">Findings by Severity</span></div>
  <div class="dc-axis"><span>0</span><span>${maxCount}</span></div>
  ${rows.join("\n  ")}
  <div class="dc-legend">
    <span><span class="swatch bad"></span>High — 错误 / 失败 / 异常 / 不可用</span>
    <span><span class="swatch warn"></span>Medium — 偏高 / 偏低 / 待复核</span>
    <span><span class="swatch good"></span>Low — 一般观察</span>
  </div>
</div>`;
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
        <td class="num sticky-col">${l.label}</td>
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
      <td><span class="organ-stripe" style="background:${o.color}"></span><span class="organ-dot" style="background:${o.color}"></span>${escapeHtml(o.name)}</td>
      <td>${score != null ? `<span class="score-pill ${level}">${score.toFixed(1)}%</span>` : '<span class="muted">—</span>'}</td>
      <td><span class="tag ${qualityClass}">${quality}</span></td>
      <td class="anatomical">${detail ? escapeHtml(detail.anatomicalLocation) : "—"}</td>
    </tr>`;
  }).join("\n");

  const organListBlock = `
<details class="organ-list-details" open>
  <summary>器官列表（${data.organs.length} 个 · 点击折叠）</summary>
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
</details>`;

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
    ? data.aiFindings
        .map((f) => ({ text: f, sev: classifyFindingSeverity(f) }))
        .sort((a, b) => {
          const order: Record<FindingSeverity, number> = { high: 0, medium: 1, low: 2 };
          return order[a.sev] - order[b.sev];
        })
        .map((f) => `<li class="ai-finding severity-${f.sev}"><span class="sev-tag">${findingSeverityLabel(f.sev)}</span>${escapeHtml(f.text)}</li>`)
        .join("\n")
    : '<li class="ai-finding severity-low"><span class="sev-tag">low</span>暂无发现</li>';

  const hasValidation = v != null;

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>CT 分割报告 - ${escapeHtml(data.caseId)}</title>
<style>
  :root {
    --bg: #ffffff;
    --surface: #ffffff;
    --surface-alt: #fbfaf7;
    --paper: #f4f1ea;
    --ink: #11141b;
    --ink-soft: #3a4051;
    --muted: #6c7488;
    --line: #d8d3c5;
    --line-soft: #ebe7da;
    --rule: #2b2f3a;
    --accent: #1a3d6b;
    --accent-soft: #4a6a8c;
    --good: #1f5e2c;
    --good-bg: #e8f0e9;
    --warn: #8a5500;
    --warn-bg: #f5ecd9;
    --bad: #8a1c1c;
    --bad-bg: #f4e0e0;
    --info-bg: #ecf1f6;
    --shadow: none;
    --shadow-header: none;
    --radius: 2px;
    --serif: "Source Serif Pro", "Source Han Serif SC", "Noto Serif CJK SC", "Songti SC", "STSong", "SimSun", "Times New Roman", Times, serif;
    --mono: ui-monospace, "SF Mono", "JetBrains Mono", Menlo, Consolas, monospace;
  }
  * { margin: 0; padding: 0; box-sizing: border-box; }
  html, body { background: var(--surface); }
  body {
    font-family: var(--serif);
    color: var(--ink);
    line-height: 1.65;
    padding: 28px 18px;
    font-size: 14px;
    text-rendering: optimizeLegibility;
    -webkit-font-smoothing: antialiased;
  }
  .page {
    max-width: 920px;
    margin: 0 auto;
    background: var(--surface);
    border: 1px solid var(--line);
    padding: 0;
  }
  .header {
    background: var(--surface);
    color: var(--ink);
    padding: 32px 40px 22px;
    border-bottom: 3px double var(--rule);
  }
  .header-row { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; flex-wrap: wrap; }
  .header h1 { font-family: var(--serif); font-size: 26px; font-weight: 700; letter-spacing: 0.5px; color: var(--ink); }
  .header .subtitle { margin-top: 6px; font-size: 13px; color: var(--muted); font-style: italic; }
  .header .meta-row { display: flex; gap: 0; flex-wrap: wrap; margin-top: 16px; border-top: 1px solid var(--line); padding-top: 12px; }
  .chip {
    display: inline-flex; align-items: baseline; gap: 6px;
    padding: 0 12px 0 0; margin-right: 12px;
    background: transparent; border-radius: 0;
    font-family: var(--mono);
    font-size: 11px;
    color: var(--muted);
    border-right: 1px dotted var(--line);
  }
  .chip:last-child { border-right: none; }
  .chip strong { color: var(--ink); font-weight: 600; font-family: var(--serif); }
  .badge { display: inline-block; padding: 3px 10px; border: 1px solid currentColor; border-radius: 0; font-size: 12px; font-weight: 600; letter-spacing: 1px; text-transform: uppercase; }
  .badge-passed { color: var(--good); }
  .badge-review { color: var(--warn); }
  .badge-na { color: var(--muted); }
  .content { padding: 24px 40px 40px; }
  h2 {
    font-family: var(--serif);
    font-size: 19px; font-weight: 700;
    margin: 36px 0 16px;
    padding-bottom: 6px;
    border-bottom: 1px solid var(--rule);
    display: flex; align-items: baseline; gap: 12px;
    color: var(--ink);
  }
  h2 .section-num { font-family: var(--mono); font-size: 12px; font-weight: 500; color: var(--accent); letter-spacing: 1px; }
  h2 .section-en { font-family: var(--serif); font-size: 13px; font-weight: 400; font-style: italic; color: var(--muted); margin-left: auto; }
  h2:first-child { margin-top: 0; }
  h3 { font-family: var(--serif); font-size: 15px; font-weight: 600; color: var(--ink); margin: 20px 0 10px; padding-left: 10px; border-left: 3px solid var(--accent); }
  h4 { font-family: var(--serif); font-size: 13px; font-weight: 600; color: var(--ink-soft); margin: 14px 0 6px; }

  .overview-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 0;
    border: 1px solid var(--line);
    border-bottom: none;
  }
  .overview-card {
    background: var(--surface);
    border: none;
    border-bottom: 1px solid var(--line);
    border-right: 1px solid var(--line);
    border-radius: 0;
    padding: 10px 14px;
  }
  .overview-card:last-child { border-right: none; }
  .overview-card .label { font-family: var(--serif); font-size: 11px; color: var(--muted); letter-spacing: 0.4px; margin-bottom: 4px; font-style: italic; }
  .overview-card .value { font-family: var(--serif); font-size: 16px; font-weight: 600; color: var(--ink); word-break: break-all; font-variant-numeric: tabular-nums; }
  .overview-card .value.small { font-size: 12px; font-weight: 500; font-family: var(--mono); }

  .metric-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 0; border: 1px solid var(--line); border-bottom: none; }
  .metric-card {
    background: var(--surface);
    border: none;
    border-bottom: 1px solid var(--line);
    border-right: 1px solid var(--line);
    border-radius: 0;
    padding: 12px 16px;
    position: relative;
  }
  .metric-card:last-child { border-right: none; }
  .metric-card.bar-good { background: var(--good-bg); }
  .metric-card.bar-warn { background: var(--warn-bg); }
  .metric-card.bar-bad { background: var(--bad-bg); }
  .card-label { font-family: var(--serif); font-size: 11px; color: var(--muted); letter-spacing: 0.4px; margin-bottom: 6px; font-style: italic; }
  .card-value { font-family: var(--serif); font-size: 22px; font-weight: 700; color: var(--ink); font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; }
  .card-bar { height: 2px; background: rgba(0, 0, 0, 0.08); border-radius: 0; margin-top: 8px; overflow: hidden; }
  .card-bar-fill { height: 100%; border-radius: 0; transition: width 0.3s; }
  .card-bar-fill, .dice-good .card-bar-fill, .iou-good .card-bar-fill, .pix-good .card-bar-fill { background: var(--good); }
  .card-bar-fill, .dice-warn .card-bar-fill, .iou-warn .card-bar-fill, .pix-warn .card-bar-fill { background: var(--warn); }
  .card-bar-fill, .dice-bad .card-bar-fill, .iou-bad .card-bar-fill, .pix-bad .card-bar-fill { background: var(--bad); }
  .card-bar-fill, .dice-na .card-bar-fill, .iou-na .card-bar-fill, .pix-na .card-bar-fill { background: var(--muted); }
  .card-bar-fill, .dist-good .card-bar-fill { background: var(--good); }
  .card-bar-fill, .dist-warn .card-bar-fill { background: var(--warn); }
  .card-bar-fill, .dist-bad .card-bar-fill { background: var(--bad); }
  .card-bar-fill, .dist-na .card-bar-fill { background: var(--muted); }

  .metric-group { margin-bottom: 22px; }
  .metric-group-title { font-family: var(--serif); font-size: 13px; font-weight: 600; color: var(--ink); margin-bottom: 8px; padding-bottom: 4px; border-bottom: 1px dotted var(--line); display: flex; align-items: baseline; gap: 8px; }
  .metric-group-title .group-en { font-style: italic; font-weight: 400; color: var(--muted); font-size: 12px; margin-left: auto; }

  .label-stats { display: flex; gap: 0; flex-wrap: wrap; margin-top: 14px; border: 1px solid var(--line); }
  .tag { display: inline-block; padding: 4px 12px; border-radius: 0; font-size: 12px; font-weight: 500; line-height: 1.5; font-family: var(--serif); border-right: 1px solid var(--line); background: var(--surface); color: var(--ink); }
  .tag:last-child { border-right: none; }
  .tag-passed { background: var(--good-bg); color: var(--good); }
  .tag-review { background: var(--warn-bg); color: var(--warn); }
  .tag-failed { background: var(--bad-bg); color: var(--bad); }
  .tag-progress { background: var(--info-bg); color: var(--accent); }
  .tag-info { background: var(--surface-alt); color: var(--ink-soft); }
  .tag-measure { background: var(--surface-alt); color: var(--accent); font-family: var(--mono); }

  .score-pill { display: inline-block; padding: 1px 8px; border: 1px solid currentColor; border-radius: 0; font-size: 11px; font-weight: 600; font-variant-numeric: tabular-nums; font-family: var(--mono); }
  .score-pill.good { color: var(--good); }
  .score-pill.warn { color: var(--warn); }
  .score-pill.bad { color: var(--bad); }
  .score-pill.na { color: var(--muted); }

  .organ-dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 6px; vertical-align: middle; }

  /* ===== 器官色条 (Per-Organ Color Stripe) ===== */
  .organ-stripe { display: inline-block; width: 4px; height: 18px; margin-right: 8px; vertical-align: middle; }

  table { width: 100%; border-collapse: collapse; margin-bottom: 18px; font-size: 13px; background: var(--surface); border: 1px solid var(--line); font-family: var(--serif); }
  thead th { background: var(--surface-alt); font-family: var(--serif); font-weight: 700; font-size: 11px; letter-spacing: 0.4px; color: var(--ink); padding: 9px 12px; text-align: left; border-bottom: 2px solid var(--rule); border-right: 1px dotted var(--line-soft); }
  thead th:last-child { border-right: none; }
  thead th.num { text-align: right; }
  tbody td { padding: 7px 12px; border-bottom: 1px solid var(--line-soft); border-right: 1px dotted var(--line-soft); }
  tbody td:last-child { border-right: none; }
  tbody td.num { text-align: right; font-variant-numeric: tabular-nums; font-feature-settings: "tnum"; font-family: var(--mono); font-size: 12px; }
  tbody td.anatomical { color: var(--ink-soft); font-size: 12px; font-style: italic; }
  tbody tr:nth-child(even) td { background: var(--surface-alt); }
  tbody tr:last-child td { border-bottom: none; }
  tbody tr:hover td { background: var(--paper); }
  tbody tr td.muted, .muted { color: var(--muted); }

  .metric-cell { display: inline-flex; align-items: center; gap: 8px; min-width: 130px; }
  .metric-num { font-family: var(--mono); font-size: 12px; font-variant-numeric: tabular-nums; color: var(--ink); min-width: 50px; text-align: right; }
  .metric-bar { flex: 1; height: 3px; background: rgba(0, 0, 0, 0.08); border-radius: 0; overflow: hidden; min-width: 50px; }
  .metric-bar-fill { height: 100%; border-radius: 0; }
  .dice-good .metric-bar-fill, .iou-good .metric-bar-fill, .pix-good .metric-bar-fill { background: var(--good); }
  .dice-warn .metric-bar-fill, .iou-warn .metric-bar-fill, .pix-warn .metric-bar-fill { background: var(--warn); }
  .dice-bad .metric-bar-fill, .iou-bad .metric-bar-fill, .pix-bad .metric-bar-fill { background: var(--bad); }
  .dice-na .metric-bar-fill, .iou-na .metric-bar-fill, .pix-na .metric-bar-fill { background: var(--muted); }
  .dist-good .metric-bar-fill { background: var(--good); }
  .dist-warn .metric-bar-fill { background: var(--warn); }
  .dist-bad .metric-bar-fill { background: var(--bad); }
  .dist-na .metric-bar-fill { background: var(--muted); }

  ul { padding-left: 22px; margin-bottom: 16px; }
  li { margin-bottom: 6px; font-size: 14px; }

  /* ===== 色阶图例 ===== */
  .legend {
    display: flex; flex-wrap: wrap; gap: 24px;
    margin: 10px 0 20px;
    padding: 12px 18px;
    background: var(--surface-alt);
    border: 1px solid var(--line);
    border-radius: 0;
    font-size: 12px;
    color: var(--ink-soft);
    font-family: var(--serif);
  }
  .legend-group { display: flex; align-items: center; gap: 8px; }
  .legend-group .label-strong { color: var(--ink); font-weight: 600; margin-right: 4px; font-style: italic; }
  .legend-chip { display: inline-flex; align-items: center; gap: 4px; font-family: var(--mono); font-size: 11px; }
  .legend-chip .swatch {
    display: inline-block; width: 12px; height: 12px; border-radius: 0;
    box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.15);
  }
  .swatch-good { background: var(--good); }
  .swatch-warn { background: var(--warn); }
  .swatch-bad  { background: var(--bad); }

  /* ===== historical 顶部警告条（remap 信息已迁到 .tag 与摘要列表内联文字，2026-06-07 清理） ===== */
  .historical-banner {
    margin: 10px 0 18px; padding: 8px 14px;
    background: var(--surface-alt); color: var(--ink-soft);
    border: 1px solid var(--line); border-left: 3px solid var(--muted);
    border-radius: 0; font-size: 12px; font-style: italic;
    font-family: var(--serif);
  }

  /* ===== spacing 可视化 ===== */
  .spacing-bar { display: inline-flex; gap: 4px; vertical-align: middle; margin-left: 6px; align-items: center; }
  .spacing-cell { display: inline-block; width: 14px; height: 14px; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.15); }
  .spacing-cell.s0-7 { background: #c8d8b8; }
  .spacing-cell.s1-0 { background: #d8d6a0; }
  .spacing-cell.s1-2 { background: #e6c890; }
  .spacing-cell.s1-5 { background: #d9a878; }
  .spacing-cell.s2-0 { background: #c89178; }
  .spacing-axis { font-family: var(--mono); font-size: 10px; color: var(--ink-soft); margin-left: 1px; }

  /* ===== aiFindings 严重度 ===== */
  .ai-findings { list-style: none; padding: 0; margin: 0; }
  .ai-finding {
    padding: 8px 14px; margin-bottom: 4px;
    border-left: 3px solid var(--muted);
    background: var(--surface); border-radius: 0;
    font-size: 13px; color: var(--ink);
    font-family: var(--serif);
  }
  .ai-finding.severity-high   { border-left-color: var(--bad);  background: var(--bad-bg); }
  .ai-finding.severity-medium { border-left-color: var(--warn); background: var(--warn-bg); }
  .ai-finding.severity-low    { border-left-color: var(--good); background: var(--good-bg); }
  .ai-finding .sev-tag {
    display: inline-block; padding: 0 8px;
    font-family: var(--mono); font-size: 10px; font-weight: 600;
    letter-spacing: 0.5px; text-transform: uppercase;
    margin-right: 10px; color: var(--ink-soft);
    border: 1px solid currentColor;
  }
  .ai-finding.severity-high   .sev-tag { color: var(--bad); }
  .ai-finding.severity-medium .sev-tag { color: var(--warn); }
  .ai-finding.severity-low    .sev-tag { color: var(--good); }

  /* ===== 器官列表折叠 ===== */
  .organ-list-details { margin: 0; border: 1px solid var(--line); }
  .organ-list-details > summary {
    cursor: pointer; padding: 9px 14px;
    background: var(--surface-alt); border: none;
    border-radius: 0; font-size: 13px; font-weight: 600;
    color: var(--ink); font-family: var(--serif);
    list-style: none;
  }
  .organ-list-details > summary::-webkit-details-marker { display: none; }
  .organ-list-details > summary::before { content: "▸ "; color: var(--accent); font-weight: 400; }
  .organ-list-details[open] > summary::before { content: "▾ "; }
  .organ-list-details[open] > summary { border-bottom: 1px solid var(--line); }
  .organ-list-details table { margin: 0; border: none; border-radius: 0; }
  .organ-list-details > table tbody tr { break-inside: avoid; }

  /* ===== 逐标签表 sticky + sortable ===== */
  .label-table thead th { position: sticky; top: 0; z-index: 2; cursor: pointer; user-select: none; background: var(--surface-alt); }
  .label-table thead th .sort-ind { display: inline-block; margin-left: 4px; opacity: 0.3; font-size: 9px; font-family: var(--mono); }
  .label-table thead th.sort-asc  .sort-ind,
  .label-table thead th.sort-desc .sort-ind { opacity: 1; color: var(--accent); }
  .label-table thead th.num.sticky-col { position: sticky; left: 0; z-index: 3; }
  .label-table tbody td.sticky-col { position: sticky; left: 0; background: var(--surface); z-index: 1; box-shadow: 1px 0 0 var(--line); font-family: var(--serif); font-weight: 600; }
  .label-table tbody tr:nth-child(even) td.sticky-col { background: var(--surface-alt); }
  .label-table thead th.sticky-col { background: var(--surface-alt); z-index: 3; }
  .label-wrap { max-width: 100%; overflow-x: auto; }

  /* ===== 封面页 (Cover) ===== */
  .cover {
    padding: 60px 40px 50px;
    text-align: center;
    border-bottom: 1px solid var(--line);
    background: var(--surface);
  }
  .cover .cover-kicker {
    font-family: var(--mono); font-size: 11px; letter-spacing: 4px;
    color: var(--accent); text-transform: uppercase;
    margin-bottom: 24px;
  }
  .cover h1 {
    font-family: var(--serif); font-size: 36px; font-weight: 700;
    color: var(--ink); letter-spacing: 1px; line-height: 1.2;
    margin-bottom: 12px;
  }
  .cover .cover-subtitle {
    font-family: var(--serif); font-size: 17px; font-style: italic;
    color: var(--ink-soft); margin-bottom: 32px;
  }
  .cover .cover-divider {
    width: 80px; height: 1px; background: var(--rule);
    margin: 0 auto 32px;
  }
  .cover-meta {
    display: inline-block;
    text-align: left;
    font-family: var(--serif); font-size: 13px;
    color: var(--ink-soft); line-height: 1.9;
    border-top: 1px solid var(--line); border-bottom: 1px solid var(--line);
    padding: 14px 28px;
  }
  .cover-meta .field { display: flex; gap: 16px; }
  .cover-meta .field .k {
    display: inline-block; min-width: 90px;
    font-family: var(--mono); font-size: 11px;
    color: var(--muted); text-transform: uppercase; letter-spacing: 1px;
    padding-top: 2px;
  }
  .cover-meta .field .v { color: var(--ink); font-weight: 600; }
  .cover-status {
    margin-top: 32px;
    display: inline-block;
    border: 1px solid currentColor;
    padding: 6px 18px;
    font-family: var(--serif); font-size: 13px;
    font-weight: 600; letter-spacing: 2px; text-transform: uppercase;
  }
  .cover-status.pass { color: var(--good); }
  .cover-status.review { color: var(--warn); }
  .cover-status.na { color: var(--muted); }

  /* ===== 执行摘要 (Executive Summary) ===== */
  .exec-summary {
    margin: 24px 0 30px;
    padding: 18px 24px;
    background: var(--surface-alt);
    border-left: 4px solid var(--accent);
    font-family: var(--serif);
  }
  .exec-summary .es-title {
    font-size: 13px; font-weight: 700;
    color: var(--accent); letter-spacing: 1.5px;
    text-transform: uppercase; margin-bottom: 10px;
  }
  .exec-summary ul { list-style: none; padding: 0; margin: 0; }
  .exec-summary li { margin-bottom: 6px; font-size: 14px; line-height: 1.6; }
  .exec-summary li::before { content: "§ "; color: var(--accent); font-weight: 700; margin-right: 4px; }
  .exec-summary .es-conclusion {
    margin-top: 12px; padding-top: 10px;
    border-top: 1px dotted var(--line);
    font-size: 14px; color: var(--ink);
  }
  .exec-summary .es-conclusion strong { color: var(--accent); }

  /* ===== TOC ===== */
  .toc {
    margin: 0 0 32px;
    padding: 16px 24px;
    border: 1px solid var(--line);
    background: var(--surface);
    font-family: var(--serif);
  }
  .toc .toc-title {
    font-size: 12px; font-weight: 700; letter-spacing: 1.5px;
    text-transform: uppercase; color: var(--accent);
    margin-bottom: 8px;
  }
  .toc ol { list-style: none; padding: 0; margin: 0; counter-reset: toc-item; columns: 2; column-gap: 24px; }
  .toc li { counter-increment: toc-item; margin-bottom: 4px; break-inside: avoid; }
  .toc li a {
    color: var(--ink); text-decoration: none;
    display: flex; align-items: baseline; gap: 6px;
    font-size: 13px;
    border-bottom: 1px dotted transparent;
  }
  .toc li a:hover { color: var(--accent); border-bottom-color: var(--accent); }
  .toc li a::before { content: counter(toc-item, decimal-leading-zero); font-family: var(--mono); font-size: 11px; color: var(--accent); min-width: 22px; }
  .toc li .toc-en { font-style: italic; color: var(--muted); font-size: 12px; margin-left: 4px; }
  .toc li .toc-leader { flex: 1; border-bottom: 1px dotted var(--line); margin: 0 6px 4px; min-width: 12px; }
  .toc li .toc-page { font-family: var(--mono); font-size: 11px; color: var(--muted); }

  /* ===== 公式贴士 (Formula Tip) ===== */
  .formula-tip {
    display: flex; align-items: flex-start; gap: 12px;
    margin: 6px 0 10px;
    padding: 8px 14px;
    background: var(--surface-alt);
    border: 1px solid var(--line);
    border-left: 2px solid var(--accent);
    font-family: var(--serif); font-size: 12px;
    color: var(--ink-soft); line-height: 1.5;
  }
  .formula-tip .ft-eq {
    font-family: "Cambria Math", "STIX", "Times New Roman", serif;
    font-style: italic; font-size: 13px;
    color: var(--ink); white-space: nowrap;
  }
  .formula-tip .ft-desc { flex: 1; }

  /* ===== caption + footnote ===== */
  .table-caption {
    font-family: var(--serif); font-size: 13px;
    color: var(--ink-soft); margin: 6px 0 4px;
    padding-left: 0;
  }
  .table-caption .cap-num { font-family: var(--mono); font-size: 11px; color: var(--accent); font-weight: 600; margin-right: 6px; }
  .table-caption .cap-note { font-style: italic; color: var(--muted); font-size: 12px; }
  .footnotes {
    margin: 8px 0 20px;
    padding-top: 8px;
    border-top: 1px solid var(--line);
    font-family: var(--serif); font-size: 11px;
    color: var(--muted); line-height: 1.6;
  }
  .footnotes ol { list-style: none; padding: 0; margin: 0; counter-reset: fn-item; }
  .footnotes li { counter-increment: fn-item; padding-left: 22px; position: relative; }
  .footnotes li::before { content: counter(fn-item); position: absolute; left: 0; font-family: var(--mono); font-weight: 600; color: var(--accent); }
  sup.fn-ref { font-family: var(--mono); font-size: 9px; color: var(--accent); font-weight: 600; margin-left: 1px; cursor: help; }

  /* ===== 关键发现分布图 (Distribution Chart) ===== */
  .dist-chart {
    margin: 12px 0 18px;
    padding: 12px 16px;
    border: 1px solid var(--line);
    background: var(--surface);
  }
  .dist-chart .dc-title {
    font-family: var(--serif); font-size: 12px; font-weight: 600;
    color: var(--ink); margin-bottom: 8px;
    display: flex; align-items: baseline; gap: 8px;
  }
  .dist-chart .dc-title .dc-en { font-style: italic; color: var(--muted); font-weight: 400; font-size: 11px; }
  .dist-chart .dc-axis {
    display: flex; justify-content: space-between;
    font-family: var(--mono); font-size: 9px; color: var(--muted);
    border-bottom: 1px solid var(--rule);
    padding: 0 80px 2px 80px;
    margin-bottom: 4px;
  }
  .dist-chart .dc-row {
    display: grid; grid-template-columns: 70px 1fr 50px;
    align-items: center; gap: 6px;
    padding: 2px 0; font-size: 12px;
    font-family: var(--serif);
  }
  .dist-chart .dc-row .dc-label { text-align: right; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .dist-chart .dc-row .dc-bar-track { position: relative; height: 14px; background: var(--surface-alt); }
  .dist-chart .dc-row .dc-bar-fill { position: absolute; top: 0; height: 100%; background: var(--ink); }
  .dist-chart .dc-row .dc-bar-fill.good { background: var(--good); }
  .dist-chart .dc-row .dc-bar-fill.warn { background: var(--warn); }
  .dist-chart .dc-row .dc-bar-fill.bad  { background: var(--bad); }
  .dist-chart .dc-row .dc-bar-threshold {
    position: absolute; top: -2px; bottom: -2px; width: 1px;
    background: var(--bad);
  }
  .dist-chart .dc-row .dc-bar-threshold::after {
    content: attr(data-label); position: absolute;
    top: -12px; left: 2px; transform: translateX(-50%);
    font-family: var(--mono); font-size: 8px; color: var(--bad);
    white-space: nowrap;
  }
  .dist-chart .dc-row .dc-val { font-family: var(--mono); font-size: 11px; color: var(--ink); text-align: right; font-variant-numeric: tabular-nums; }
  .dist-chart .dc-legend {
    margin-top: 8px; padding-top: 6px; border-top: 1px dotted var(--line);
    display: flex; gap: 14px; font-size: 11px; color: var(--ink-soft);
    font-family: var(--serif);
  }
  .dist-chart .dc-legend .swatch { display: inline-block; width: 10px; height: 10px; vertical-align: middle; margin-right: 4px; box-shadow: inset 0 0 0 1px rgba(0,0,0,0.15); }
  .dist-chart .dc-legend .swatch.good { background: var(--good); }
  .dist-chart .dc-legend .swatch.warn { background: var(--warn); }
  .dist-chart .dc-legend .swatch.bad  { background: var(--bad); }

  .footer {
    margin-top: 36px;
    padding: 14px 40px;
    border-top: 1px solid var(--rule);
    background: var(--surface-alt);
    font-size: 11px;
    color: var(--muted);
    display: flex; justify-content: space-between; flex-wrap: wrap; gap: 8px;
    font-family: var(--serif); font-style: italic;
  }
  .footer .hint { font-style: italic; }

  @media print {
    @page { size: A4; margin: 18mm 14mm 22mm; }
    body { background: #fff; padding: 0; }
    .page { border: none; max-width: none; }
    h2 { break-after: avoid; }
    table, .metric-card, .overview-card, .dist-chart, .exec-summary, .cover { break-inside: avoid; }
    thead { display: table-header-group; }
    .cover { border-bottom: 2px solid #000; }
    .card-bar, .metric-bar, .badge, .tag, .score-pill, .swatch, .spacing-cell, .ai-finding, .dist-chart .dc-bar-fill, .cover-status, .formula-tip { -webkit-print-color-adjust: exact; print-color-adjust: exact; }
    .print-header, .print-footer { display: block !important; }
  }
  .print-header, .print-footer { display: none; }
  .print-header {
    position: fixed; top: 0; left: 0; right: 0;
    padding: 6px 14mm; font-size: 11px; color: var(--muted);
    border-bottom: 1px solid var(--line); background: #fff;
    display: flex; justify-content: space-between;
    font-family: var(--serif); font-style: italic;
  }
  .print-footer {
    position: fixed; bottom: 0; left: 0; right: 0;
    padding: 6px 14mm; font-size: 11px; color: var(--muted);
    border-top: 1px solid var(--line); background: #fff;
    display: flex; justify-content: space-between;
    font-family: var(--serif); font-style: italic;
  }
</style>
</head>
<body>
<div class="print-header"><span>CT 分割报告 · ${escapeHtml(data.caseId)}</span><span>${escapeHtml(data.generatedAt)}</span></div>
<div class="page">

<div class="cover">
  <div class="cover-kicker">CT Segmentation Validation Report</div>
  <h1>CT 分割验证报告</h1>
  <div class="cover-subtitle">${escapeHtml(data.caseId)} · ${escapeHtml(profile)} 推理模式</div>
  <div class="cover-divider"></div>
  <div class="cover-meta">
    <div class="field"><span class="k">Case</span><span class="v">${escapeHtml(data.caseId)}</span></div>
    <div class="field"><span class="k">Target</span><span class="v">${escapeHtml(data.caseTarget)}</span></div>
    <div class="field"><span class="k">Model</span><span class="v">${escapeHtml(data.modelName)}</span></div>
    <div class="field"><span class="k">Profile</span><span class="v">${escapeHtml(profile)}${cachedFlag ? " · 缓存命中" : ""}</span></div>
    <div class="field"><span class="k">Job ID</span><span class="v">${escapeHtml(jobId)}${cacheSource ? ` ← ${escapeHtml(cacheSource)}` : ""}</span></div>
    <div class="field"><span class="k">Generated</span><span class="v">${escapeHtml(data.generatedAt)}</span></div>
    <div class="field"><span class="k">Duration</span><span class="v">${duration} · ${resultSize}</span></div>
  </div>
  ${hasValidation ? `<div class="cover-status ${v.status === "passed" ? "pass" : v.status === "review" ? "review" : "na"}">${statusLabel(v.status)}</div>` : ""}
</div>

<div class="content">

${hasValidation ? `
<div class="exec-summary">
  <div class="es-title">执行摘要 · Executive Summary</div>
  <ul>
    <li>验证集规模 ${v.labels?.length ?? 0} 例 · 标签体系 <em>${escapeHtml(v.label_taxonomy ?? "auto")}</em>${v.taxonomy_match === false ? " (与模型不匹配，已自动 remap)" : ""}${v.remap_applied ? ` · 重映射自 <em>${escapeHtml(v.remap_source ?? "未知")}</em>` : ""}</li>
    <li>区域重叠度平均 Dice = <strong>${formatMetric(v.mean_dice, 4)}</strong>${v.thresholds?.mean_dice != null ? ` (阈值 ≥ ${Number(v.thresholds.mean_dice).toFixed(2)})` : ""}，最低 Dice = <strong>${formatMetric(v.min_dice, 4)}</strong>；通过 (Dice ≥ 0.85) 共 <strong>${passedCount}</strong> 例，待复核 <strong>${reviewCount}</strong> 例，N/A <strong>${naCount}</strong> 例。</li>
    <li>像素准确率均值 <strong>${formatMetric(v.mean_pixel_accuracy, 4)}</strong>，前景准确率 <strong>${formatMetric(v.foreground_pixel_accuracy, 4)}</strong>。</li>
    <li>表面距离：平均 HD95 = <strong>${formatMetric(v.mean_hd95, 2)} mm</strong>，平均 ASD = <strong>${formatMetric(v.mean_asd, 2)} mm</strong>${v.surface_distance_unit ? ` (单位：${escapeHtml(v.surface_distance_unit)})` : ""}。</li>
  </ul>
  <div class="es-conclusion">${v.status === "passed" ? `<strong>结论：</strong>通过验证阈值。模型在当前 case 表现稳定，可作为正式结果提交。` : v.status === "review" ? `<strong>结论：</strong>待复核。存在 Dice 低于阈值或 remap 路径，详见 §3 逐标签分析。` : `<strong>结论：</strong>验证未执行或不完整，结果仅供参考。`}</div>
</div>
` : ""}

<nav class="toc" aria-label="目录">
  <div class="toc-title">目录 · Table of Contents</div>
  <ol>
    <li><a href="#sec-overview"><span>概览</span><span class="toc-en">Overview</span><span class="toc-leader"></span><span class="toc-page">§1</span></a></li>
    <li><a href="#sec-metrics"><span>验证指标</span><span class="toc-en">Validation Metrics</span><span class="toc-leader"></span><span class="toc-page">§2</span></a></li>
    <li><a href="#sec-perorgan"><span>逐标签分析</span><span class="toc-en">Per-Organ Breakdown</span><span class="toc-leader"></span><span class="toc-page">§3</span></a></li>
    <li><a href="#sec-organs"><span>器官列表</span><span class="toc-en">Organ Roster</span><span class="toc-leader"></span><span class="toc-page">§4</span></a></li>
    <li><a href="#sec-quant"><span>影像量化</span><span class="toc-en">Quantification</span><span class="toc-leader"></span><span class="toc-page">§5</span></a></li>
    <li><a href="#sec-findings"><span>关键发现</span><span class="toc-en">Findings</span><span class="toc-leader"></span><span class="toc-page">§6</span></a></li>
    <li><a href="#sec-measure"><span>测量点</span><span class="toc-en">Measurements</span><span class="toc-leader"></span><span class="toc-page">§7</span></a></li>
    <li><a href="#sec-timeline"><span>推理时间线</span><span class="toc-en">Timeline</span><span class="toc-leader"></span><span class="toc-page">§8</span></a></li>
  </ol>
</nav>

<h2 id="sec-overview"><span class="section-num">§1</span><span>概览</span><span class="section-en">Overview</span></h2>
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
<h2 id="sec-metrics"><span class="section-num">§2</span><span>验证指标</span><span class="section-en">Validation Metrics</span></h2>
<div class="formula-tip">
  <span class="ft-eq">Dice = 2|A∩B| / (|A|+|B|)</span>
  <span class="ft-desc">两倍交集除以预测和参考体素数之和。≥ 0.85 视为通过。</span>
</div>
<div class="formula-tip">
  <span class="ft-eq">IoU = |A∩B| / |A∪B|</span>
  <span class="ft-desc">交集与并集之比。与 Dice 几何同构但更严苛。</span>
</div>
<div class="metric-group">
  <div class="metric-group-title">区域重叠度 · Dice / IoU <span class="group-en">Overlap (higher is better)</span></div>
  <div class="metric-grid">
    ${metricCard("平均 Dice", v.mean_dice, "", "dice")}
    ${metricCard("最低 Dice", v.min_dice, "", "dice")}
    ${metricCard("前景 Dice", v.foreground_dice, "", "dice")}
    ${metricCard("平均 IoU", v.mean_iou, "", "iou")}
    ${metricCard("最低 IoU", v.min_iou, "", "iou")}
    ${metricCard("前景 IoU", v.foreground_iou, "", "iou")}
  </div>
</div>
<div class="formula-tip">
  <span class="ft-eq">PA = Σ correct / Σ total</span>
  <span class="ft-desc">像素准确率（包含背景）。当类别极不平衡时需配合 mean class PA。</span>
</div>
<div class="metric-group">
  <div class="metric-group-title">像素准确率 · Pixel Accuracy <span class="group-en">Pixel Accuracy (higher is better)</span></div>
  <div class="metric-grid">
    ${metricCard("总准确率", v.pixel_accuracy, "", "pix")}
    ${metricCard("平均类别准确率", v.mean_pixel_accuracy, "", "pix")}
    ${metricCard("最低类别准确率", v.min_pixel_accuracy, "", "pix")}
    ${metricCard("前景准确率", v.foreground_pixel_accuracy, "", "pix")}
  </div>
</div>
<div class="formula-tip">
  <span class="ft-eq">HD95 = P₉₅ (d_b(A), d_a(B))</span>
  <span class="ft-desc">95% 分位的双向表面距离；对离群点鲁棒。</span>
</div>
<div class="metric-group">
  <div class="metric-group-title">表面距离 · HD / HD95 / ASD <span class="group-en">Surface Distance — unit: ${escapeHtml(v.surface_distance_unit ?? "mm")} (lower is better)</span></div>
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
  ${v.label_taxonomy ? `<span class="tag ${v.taxonomy_match ? "tag-passed" : "tag-review"}">taxonomy · ${escapeHtml(v.label_taxonomy)}${v.taxonomy_match ? "" : " (不匹配)"}</span>` : ""}
  ${v.dataset_hint ? `<span class="tag tag-info">dataset_hint · ${escapeHtml(v.dataset_hint)}</span>` : ""}
  ${v.accepted === true ? `<span class="tag tag-passed">通过验证阈值</span>` : ""}
  ${v.accepted === false ? `<span class="tag tag-review">未达阈值</span>` : ""}
  ${v.thresholds?.mean_dice != null ? `<span class="tag tag-info">mean_dice 阈值 ${Number(v.thresholds.mean_dice).toFixed(2)}</span>` : ""}
  ${v.spacing && v.spacing.length ? `<span class="tag tag-info">体素间距 (${escapeHtml(v.spacing.map((n) => Number(n).toFixed(2)).join(" × "))} mm) <span class="spacing-bar" title="spacing 可视化（绿→红）">${spacingCellsHtml(v.spacing)}</span></span>` : ""}
</div>
${v.historical ? `<div class="historical-banner" style="margin: 8px 0 18px;">（历史离线缓存摘要） — 当前 validation 未在本次 job 重新计算；如需重算请提交新 job 或上传新标签${v.source_job_id ? `（来源 job: ${escapeHtml(v.source_job_id)}）` : ""}</div>` : ""}
<div class="legend" aria-label="色阶图例">
  <div class="legend-group">
    <span class="label-strong">Dice / IoU / 像素准确率：</span>
    <span class="legend-chip"><span class="swatch swatch-good"></span> ≥ 0.85</span>
    <span class="legend-chip"><span class="swatch swatch-warn"></span> 0.70 – 0.85</span>
    <span class="legend-chip"><span class="swatch swatch-bad"></span> &lt; 0.70</span>
  </div>
  <div class="legend-group">
    <span class="label-strong">HD / HD95 / ASD (mm)：</span>
    <span class="legend-chip"><span class="swatch swatch-good"></span> ≤ 1</span>
    <span class="legend-chip"><span class="swatch swatch-warn"></span> 1 – 3</span>
    <span class="legend-chip"><span class="swatch swatch-bad"></span> &gt; 3</span>
  </div>
  <div class="legend-group">
    <span class="label-strong">关键发现严重度：</span>
    <span class="legend-chip"><span class="swatch swatch-bad"></span> high</span>
    <span class="legend-chip"><span class="swatch swatch-warn"></span> medium</span>
    <span class="legend-chip"><span class="swatch swatch-good"></span> low</span>
  </div>
</div>
${v.message ? `<p style="margin-top:10px;color:var(--ink-soft);font-size:13px;">${escapeHtml(v.message)}</p>` : ""}

<h3 id="sec-perorgan"><span class="section-num">§3</span><span>逐标签指标</span><span class="section-en">Per-Organ Breakdown</span></h3>
<div class="table-caption"><span class="cap-num">Table 3.1</span>逐标签验证结果。<span class="cap-note">点击列头排序；Dice ≥ 0.85 视为通过，<sup class="fn-ref" title="通过阈值定义于 ValidationSummary.thresholds.mean_dice">a</sup>。距离单位 mm，越低越好。<sup class="fn-ref" title="HD/HD95/ASD 通过 surface_distances (2 EDT) 计算">b</sup></span></div>
<div class="label-wrap">
<table class="label-table">
  <thead>
    <tr>
      <th class="num sticky-col" data-sort="label" style="width:60px">Label<span class="sort-ind">↕</span></th>
      <th data-sort="name">器官<span class="sort-ind">↕</span></th>
      <th data-sort="dice">Dice<span class="sort-ind">↕</span></th>
      <th data-sort="iou">IoU<span class="sort-ind">↕</span></th>
      <th data-sort="pixel_accuracy">像素准确率<span class="sort-ind">↕</span></th>
      <th data-sort="asd">ASD (mm)<span class="sort-ind">↕</span></th>
      <th data-sort="hd95">HD95 (mm)<span class="sort-ind">↕</span></th>
      <th data-sort="hd">HD (mm)<span class="sort-ind">↕</span></th>
      <th class="num" data-sort="prediction_voxels">预测体素<span class="sort-ind">↕</span></th>
      <th class="num" data-sort="reference_voxels">参考体素<span class="sort-ind">↕</span></th>
    </tr>
  </thead>
  <tbody>${perLabelRows}</tbody>
</table>
</div>
<div class="footnotes">
  <ol>
    <li>通过阈值 ${v.thresholds?.mean_dice != null ? `mean_dice ≥ ${Number(v.thresholds.mean_dice).toFixed(2)}` : "Dice ≥ 0.85"}；最低单标签 Dice ${v.thresholds?.min_label_dice != null ? `≥ ${Number(v.thresholds.min_label_dice).toFixed(2)}` : "（默认与 mean_dice 同）"}。</li>
    <li>HD / HD95 / ASD 来自 server/main.py surface_distances()（2 EDT 优化路径，每标签 2 次 EDT）。</li>
    <li>体素数与 spacing：${v.spacing && v.spacing.length ? `${v.spacing.map((n) => Number(n).toFixed(2)).join(" × ")} mm³/voxel` : "spacing 缺省"}。</li>
  </ol>
</div>
<div class="label-stats" style="margin-top:4px;margin-bottom:24px;">
  <span class="tag tag-passed">通过 ${passedCount}</span>
  <span class="tag tag-review">待复核 ${reviewCount}</span>
  <span class="tag tag-info">N/A ${naCount}</span>
</div>
` : '<p style="color:var(--muted);font-size:13px;padding:14px;background:var(--surface-alt);border:1px dashed var(--line);font-style:italic;">尚未执行验证（需导入标签 CT 或载入参考病例）。</p>'}

<h2 id="sec-organs"><span class="section-num">§4</span><span>器官列表</span><span class="section-en">Organ Roster</span></h2>
<div class="table-caption"><span class="cap-num">Table 4.1</span>本病例涉及的器官与质控分数。<span class="cap-note">色条对应 organ color；质控分数由 confidence × mask coverage 估算。</span></div>
${organListBlock}

<h2 id="sec-quant"><span class="section-num">§5</span><span>影像量化分析</span><span class="section-en">Quantification</span></h2>
<div class="table-caption"><span class="cap-num">Table 5.1</span>基于分割 mask 的影像量化。<span class="cap-note">${escapeHtml(data.quantification.note)} 体积、截面积和长度由 mask 与 NIfTI spacing 估算；壁厚、精确管腔面积、中心线长度属于后续扩展。</span></div>
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

<h2 id="sec-findings"><span class="section-num">§6</span><span>关键发现</span><span class="section-en">Findings</span></h2>
${data.aiFindings.length ? distributionChartHtml(data.aiFindings) : ""}
<div class="table-caption"><span class="cap-num">Table 6.1</span>关键发现按严重度排序（high → low）。<span class="cap-note">分类口径见 §6 上方分布图。</span></div>
<ul>${findingsHtml}</ul>

<h2 id="sec-measure"><span class="section-num">§7</span><span>测量点</span><span class="section-en">Measurements</span></h2>
<div class="table-caption"><span class="cap-num">Table 7.1</span>用户在正交视图上记录的感兴趣点（坐标、HU 值、估算直径、所在切片）。</div>
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

<h2 id="sec-timeline"><span class="section-num">§8</span><span>推理时间线</span><span class="section-en">Timeline</span></h2>
<div class="table-caption"><span class="cap-num">Table 8.1</span>推理过程事件（progress / complete / error）。</div>
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
<div class="print-footer"><span>segmentation-gui-prototype · 2026-06-03 · schema_version 1.1</span><span class="page-num"></span></div>
<script>
(function () {
  // 逐标签表 sticky thead / 列排序
  var table = document.querySelector('.label-table');
  if (table) {
    var headers = table.querySelectorAll('thead th');
    headers.forEach(function (th, idx) {
      th.addEventListener('click', function () {
        var dir = th.classList.contains('sort-asc') ? 'desc' : 'asc';
        headers.forEach(function (other) { other.classList.remove('sort-asc'); other.classList.remove('sort-desc'); other.querySelector('.sort-ind').textContent = '↕'; });
        th.classList.add('sort-' + dir);
        th.querySelector('.sort-ind').textContent = dir === 'asc' ? '↑' : '↓';
        var rows = Array.prototype.slice.call(table.querySelectorAll('tbody tr'));
        rows.sort(function (a, b) {
          var av = a.children[idx].textContent.trim();
          var bv = b.children[idx].textContent.trim();
          var an = parseFloat(av.replace(/,/g, ''));
          var bn = parseFloat(bv.replace(/,/g, ''));
          if (!isNaN(an) && !isNaN(bn)) {
            return dir === 'asc' ? an - bn : bn - an;
          }
          return dir === 'asc' ? av.localeCompare(bv, 'zh-CN') : bv.localeCompare(av, 'zh-CN');
        });
        var tbody = table.querySelector('tbody');
        rows.forEach(function (r) { tbody.appendChild(r); });
      });
    });
  }
  // 打印页码
  var numEl = document.querySelector('.print-footer .page-num');
  if (numEl) {
    var style = '@page { @bottom-right { content: counter(page) " / " counter(pages); } }';
    var s = document.createElement('style'); s.textContent = style; document.head.appendChild(s);
    numEl.textContent = '';
  }
})();
</script>
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
