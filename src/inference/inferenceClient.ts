import type { OrganLabel } from "../data/organDetails";

export type ValidationSummary = {
  status: "passed" | "review" | "unavailable";
  sample_id?: string;
  mean_dice?: number | null;
  min_dice?: number | null;
  foreground_dice?: number | null;
  accepted?: boolean;
  message?: string;
  thresholds?: {
    mean_dice?: number;
    min_label_dice?: number;
  };
  labels?: {
    label: number;
    name?: string;
    dice: number | null;
    prediction_voxels?: number;
    reference_voxels?: number;
    intersection_voxels?: number;
  }[];
};

export type InferenceEvent =
  | { type: "progress"; progress: number; stage: string }
  | { type: "complete"; progress: number; stage: string; duration_seconds?: number; result_size_bytes?: number; validation?: ValidationSummary }
  | { type: "error"; message: string; log_tail?: string };

export type InferenceJobMode = "real-nnunetv2" | "debug-label-fallback" | "unavailable";

export type InferenceStatus =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "running"; progress: number; stage: string; jobId?: string }
  | { status: "succeeded"; jobId?: string; mode?: InferenceJobMode; duration_seconds?: number; result_size_bytes?: number }
  | { status: "failed"; message: string; jobId?: string };

function formatDuration(seconds: number | undefined) {
  if (!Number.isFinite(seconds)) return "";
  const totalSeconds = Math.max(0, Math.round(Number(seconds)));
  const minutes = Math.floor(totalSeconds / 60);
  const remainingSeconds = totalSeconds % 60;
  return minutes > 0 ? `${minutes}分${remainingSeconds}秒` : `${remainingSeconds}秒`;
}

function normalizeValidation(payload: unknown): ValidationSummary | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const raw = payload as Record<string, unknown>;
  const status = raw.status === "passed" || raw.status === "review" || raw.status === "unavailable"
    ? raw.status
    : "unavailable";
  const summary: ValidationSummary = { status };
  if (raw.sample_id !== undefined) summary.sample_id = String(raw.sample_id);
  for (const key of ["mean_dice", "min_dice", "foreground_dice"] as const) {
    if (raw[key] === null) {
      summary[key] = null;
    } else if (raw[key] !== undefined && Number.isFinite(Number(raw[key]))) {
      summary[key] = Number(raw[key]);
    }
  }
  if (typeof raw.accepted === "boolean") summary.accepted = raw.accepted;
  if (raw.message !== undefined) summary.message = String(raw.message);
  if (raw.thresholds && typeof raw.thresholds === "object") {
    const thresholds = raw.thresholds as Record<string, unknown>;
    summary.thresholds = {};
    if (Number.isFinite(Number(thresholds.mean_dice))) summary.thresholds.mean_dice = Number(thresholds.mean_dice);
    if (Number.isFinite(Number(thresholds.min_label_dice))) summary.thresholds.min_label_dice = Number(thresholds.min_label_dice);
  }
  if (Array.isArray(raw.labels)) {
    summary.labels = raw.labels.flatMap((item): NonNullable<ValidationSummary["labels"]> => {
      if (!item || typeof item !== "object") return [];
      const label = Number((item as { label?: unknown }).label);
      if (!Number.isFinite(label)) return [];
      const metric = item as Record<string, unknown>;
      return [{
        label,
        name: metric.name === undefined ? undefined : String(metric.name),
        dice: metric.dice === null ? null : Number.isFinite(Number(metric.dice)) ? Number(metric.dice) : null,
        prediction_voxels: Number.isFinite(Number(metric.prediction_voxels)) ? Number(metric.prediction_voxels) : undefined,
        reference_voxels: Number.isFinite(Number(metric.reference_voxels)) ? Number(metric.reference_voxels) : undefined,
        intersection_voxels: Number.isFinite(Number(metric.intersection_voxels)) ? Number(metric.intersection_voxels) : undefined
      }];
    });
  }
  return summary;
}

export function parseInferenceEvent(raw: string): InferenceEvent {
  const line = raw.split(/\r?\n/).find((item) => item.startsWith("data:"));
  if (!line) throw new Error("无效的推理事件");
  const parsed = JSON.parse(line.replace(/^data:\s*/, ""));
  if (parsed.type === "error") {
    const event: InferenceEvent = { type: "error", message: String(parsed.message ?? "推理失败") };
    if (parsed.log_tail !== undefined) event.log_tail = String(parsed.log_tail);
    return event;
  }
  const event: InferenceEvent = {
    type: parsed.type === "complete" ? "complete" : "progress",
    progress: Math.max(0, Math.min(100, Number(parsed.progress ?? 0))),
    stage: String(parsed.stage ?? "推理中")
  };
  if (event.type === "complete") {
    if (Number.isFinite(Number(parsed.duration_seconds))) event.duration_seconds = Number(parsed.duration_seconds);
    if (Number.isFinite(Number(parsed.result_size_bytes))) event.result_size_bytes = Number(parsed.result_size_bytes);
    const validation = normalizeValidation(parsed.validation);
    if (validation) event.validation = validation;
  }
  return event;
}

export function getInferenceStatusCopy(status: InferenceStatus) {
  if (status.status === "submitting") return "正在提交任务";
  if (status.status === "running") return `${status.stage} · ${status.progress}%`;
  if (status.status === "succeeded" && status.mode === "debug-label-fallback") return "调试标签回填完成（非真实推理）";
  if (status.status === "succeeded") {
    const duration = formatDuration(status.duration_seconds);
    return duration ? `真实 nnUNetv2 推理完成 · ${duration}` : "真实 nnUNetv2 推理完成";
  }
  if (status.status === "failed") return status.message;
  return "等待推理";
}

export function getInferenceResultMeta(mode: InferenceJobMode | undefined, dimensions: string) {
  if (mode === "debug-label-fallback") return `${dimensions} · 调试标签回填结果（非真实推理）`;
  if (mode === "unavailable") return `${dimensions} · 模型不可用，未生成真实结果`;
  return `${dimensions} · nnUNetv2 真实推理结果`;
}

export function normalizeModelLabels(payload: unknown): OrganLabel[] {
  if (!payload || typeof payload !== "object") return [];
  const models = (payload as { models?: unknown }).models;
  if (!Array.isArray(models) || !models.length) return [];
  const labels = (models[0] as { labels?: unknown }).labels;
  if (!Array.isArray(labels)) return [];

  return labels.flatMap((item): OrganLabel[] => {
    if (!item || typeof item !== "object") return [];
    const raw = item as Partial<OrganLabel>;
    const label = Number(raw.label);
    if (!Number.isFinite(label) || label <= 0) return [];
    const normalized: OrganLabel = {
      label,
      id: raw.id ? String(raw.id) : `label-${label}`,
      nameZh: raw.nameZh ? String(raw.nameZh) : `Label ${label}`,
      color: raw.color ? String(raw.color) : "#8ec5ff"
    };
    if (raw.nameEn) normalized.nameEn = String(raw.nameEn);
    if (typeof raw.visible === "boolean") normalized.visible = raw.visible;
    return [normalized];
  });
}

export async function fetchModelLabels(endpoint: string): Promise<OrganLabel[]> {
  const response = await fetch(`${endpoint}/api/models`);
  if (!response.ok) return [];
  return normalizeModelLabels(await response.json());
}

export async function createInferenceJob(
  endpoint: string,
  file: File,
  options: { modelId: string; confidenceThreshold: number; postprocess: Record<string, boolean> }
) {
  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("model_id", options.modelId);
  formData.append("confidence_threshold", String(options.confidenceThreshold));
  formData.append("postprocess", JSON.stringify(options.postprocess));

  const response = await fetch(`${endpoint}/api/segment/jobs`, { method: "POST", body: formData });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "推理任务创建失败");
  }
  return await response.json() as {
    job_id: string;
    mode?: InferenceJobMode;
    confidence_threshold_effective?: boolean;
    model_status?: {
      ready?: boolean;
      status?: string;
      missing?: string[];
    };
  };
}

export async function downloadInferenceResult(endpoint: string, jobId: string) {
  const response = await fetch(`${endpoint}/api/segment/jobs/${jobId}/result`);
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "推理结果下载失败");
  }
  return await response.arrayBuffer();
}
