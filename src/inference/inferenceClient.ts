import type { OrganLabel } from "../data/organDetails";

export type ValidationSummary = {
  status: "passed" | "review" | "unavailable";
  sample_id?: string;
  mean_dice?: number | null;
  min_dice?: number | null;
  foreground_dice?: number | null;
  mean_iou?: number | null;
  min_iou?: number | null;
  foreground_iou?: number | null;
  pixel_accuracy?: number | null;
  mean_pixel_accuracy?: number | null;
  min_pixel_accuracy?: number | null;
  foreground_pixel_accuracy?: number | null;
  mean_asd?: number | null;
  max_asd?: number | null;
  foreground_asd?: number | null;
  mean_hd?: number | null;
  max_hd?: number | null;
  foreground_hd?: number | null;
  mean_hd95?: number | null;
  max_hd95?: number | null;
  foreground_hd95?: number | null;
  surface_distance_unit?: string;
  spacing?: number[];
  accepted?: boolean;
  message?: string;
  taxonomy_match?: boolean;
  label_taxonomy?: LabelTaxonomy;
  remap_applied?: boolean;
  remap_source?: string;
  dataset_hint?: string;
  historical?: boolean;
  source_job_id?: string;
  thresholds?: {
    mean_dice?: number;
    min_label_dice?: number;
  };
  labels?: {
    label: number;
    name?: string;
    dice: number | null;
    iou?: number | null;
    pixel_accuracy?: number | null;
    asd?: number | null;
    hd?: number | null;
    hd95?: number | null;
    prediction_voxels?: number;
    reference_voxels?: number;
    intersection_voxels?: number;
    union_voxels?: number;
  }[];
};

export type ResourceSnapshot = {
  phase?: string;
  timestamp?: number;
  device?: string;
  server_pid?: number;
  process_pid?: number;
  disk_total_bytes?: number;
  disk_used_bytes?: number;
  disk_free_bytes?: number;
  server_process_memory_bytes?: number;
  gpu?: {
    name?: string;
    memory_used_mib?: number;
    memory_total_mib?: number;
    utilization_gpu_percent?: number;
  };
};

export type PhaseTimings = Record<string, number>;

export type InferenceProfile = "quality" | "fast";
export type RuntimeTarget = "local" | "server";
export type LabelTaxonomy = "auto" | "AMOS22" | "FLARE22";

export type InferenceOptions = {
  profile: InferenceProfile;
  tile_step_size?: number;
  disable_tta?: boolean;
  not_on_device?: boolean;
};

export type InferenceEvent =
  | { type: "progress"; progress: number; stage: string; heartbeat?: boolean; elapsed_seconds?: number }
  | { type: "complete"; progress: number; stage: string; duration_seconds?: number; result_size_bytes?: number; validation?: ValidationSummary; resource_latest?: ResourceSnapshot; phase_timings?: PhaseTimings; inference_options?: InferenceOptions; runtime_target?: RuntimeTarget; cached_result?: boolean; cache_source_job_id?: string }
  | { type: "error"; message: string; log_tail?: string; resource_latest?: ResourceSnapshot };

export type InferenceJobMode = "real-nnunetv2" | "cached-real-nnunetv2" | "debug-label-fallback" | "unavailable";

export type InferenceStatus =
  | { status: "idle" }
  | { status: "submitting" }
  | { status: "running"; progress: number; stage: string; jobId?: string }
  | { status: "succeeded"; jobId?: string; mode?: InferenceJobMode; duration_seconds?: number; result_size_bytes?: number; resource_latest?: ResourceSnapshot; phase_timings?: PhaseTimings; inference_options?: InferenceOptions; cached_result?: boolean; cache_source_job_id?: string }
  | { status: "cancelled"; jobId?: string }
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
  for (const key of [
    "mean_dice",
    "min_dice",
    "foreground_dice",
    "mean_iou",
    "min_iou",
    "foreground_iou",
    "pixel_accuracy",
    "mean_pixel_accuracy",
    "min_pixel_accuracy",
    "foreground_pixel_accuracy",
    "mean_asd",
    "max_asd",
    "foreground_asd",
    "mean_hd",
    "max_hd",
    "foreground_hd",
    "mean_hd95",
    "max_hd95",
    "foreground_hd95"
  ] as const) {
    if (raw[key] === null) {
      summary[key] = null;
    } else if (raw[key] !== undefined && Number.isFinite(Number(raw[key]))) {
      summary[key] = Number(raw[key]);
    }
  }
  if (typeof raw.surface_distance_unit === "string") summary.surface_distance_unit = raw.surface_distance_unit;
  if (Array.isArray(raw.spacing) && raw.spacing.every((value) => Number.isFinite(Number(value)))) {
    summary.spacing = raw.spacing.map((value) => Number(value));
  }
  if (typeof raw.accepted === "boolean") summary.accepted = raw.accepted;
  if (typeof raw.taxonomy_match === "boolean") summary.taxonomy_match = raw.taxonomy_match;
  const labelTaxonomy = normalizeLabelTaxonomy(raw.label_taxonomy);
  if (labelTaxonomy) summary.label_taxonomy = labelTaxonomy;
  if (typeof raw.remap_applied === "boolean") summary.remap_applied = raw.remap_applied;
  if (typeof raw.remap_source === "string") summary.remap_source = raw.remap_source;
  if (typeof raw.dataset_hint === "string") summary.dataset_hint = raw.dataset_hint;
  if (raw.historical === true) summary.historical = true;
  if (typeof raw.source_job_id === "string") summary.source_job_id = raw.source_job_id;
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
        iou: metric.iou === null ? null : Number.isFinite(Number(metric.iou)) ? Number(metric.iou) : null,
        pixel_accuracy: metric.pixel_accuracy === null ? null : Number.isFinite(Number(metric.pixel_accuracy)) ? Number(metric.pixel_accuracy) : null,
        asd: metric.asd === null ? null : Number.isFinite(Number(metric.asd)) ? Number(metric.asd) : null,
        hd: metric.hd === null ? null : Number.isFinite(Number(metric.hd)) ? Number(metric.hd) : null,
        hd95: metric.hd95 === null ? null : Number.isFinite(Number(metric.hd95)) ? Number(metric.hd95) : null,
        prediction_voxels: Number.isFinite(Number(metric.prediction_voxels)) ? Number(metric.prediction_voxels) : undefined,
        reference_voxels: Number.isFinite(Number(metric.reference_voxels)) ? Number(metric.reference_voxels) : undefined,
        intersection_voxels: Number.isFinite(Number(metric.intersection_voxels)) ? Number(metric.intersection_voxels) : undefined,
        union_voxels: Number.isFinite(Number(metric.union_voxels)) ? Number(metric.union_voxels) : undefined
      }];
    });
  }
  return summary;
}

function normalizeResourceSnapshot(payload: unknown): ResourceSnapshot | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const raw = payload as Record<string, unknown>;
  const snapshot: ResourceSnapshot = {};
  for (const key of ["phase", "device"] as const) {
    if (raw[key] !== undefined) snapshot[key] = String(raw[key]);
  }
  for (const key of [
    "timestamp",
    "server_pid",
    "process_pid",
    "disk_total_bytes",
    "disk_used_bytes",
    "disk_free_bytes",
    "server_process_memory_bytes"
  ] as const) {
    if (Number.isFinite(Number(raw[key]))) snapshot[key] = Number(raw[key]);
  }
  if (raw.gpu && typeof raw.gpu === "object") {
    const gpuRaw = raw.gpu as Record<string, unknown>;
    const gpu: NonNullable<ResourceSnapshot["gpu"]> = {};
    if (gpuRaw.name !== undefined) gpu.name = String(gpuRaw.name);
    for (const key of ["memory_used_mib", "memory_total_mib", "utilization_gpu_percent"] as const) {
      if (Number.isFinite(Number(gpuRaw[key]))) gpu[key] = Number(gpuRaw[key]);
    }
    if (Object.keys(gpu).length) snapshot.gpu = gpu;
  }
  return Object.keys(snapshot).length ? snapshot : undefined;
}

function normalizePhaseTimings(payload: unknown): PhaseTimings | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const timings: PhaseTimings = {};
  for (const [key, value] of Object.entries(payload as Record<string, unknown>)) {
    if (Number.isFinite(Number(value))) timings[key] = Number(value);
  }
  return Object.keys(timings).length ? timings : undefined;
}

function normalizeInferenceOptions(payload: unknown): InferenceOptions | undefined {
  if (!payload || typeof payload !== "object") return undefined;
  const raw = payload as Record<string, unknown>;
  const profile = raw.profile === "fast" ? "fast" : raw.profile === "quality" ? "quality" : undefined;
  if (!profile) return undefined;
  const options: InferenceOptions = { profile };
  if (Number.isFinite(Number(raw.tile_step_size))) options.tile_step_size = Number(raw.tile_step_size);
  if (typeof raw.disable_tta === "boolean") options.disable_tta = raw.disable_tta;
  if (typeof raw.not_on_device === "boolean") options.not_on_device = raw.not_on_device;
  return options;
}

function normalizeRuntimeTarget(payload: unknown): RuntimeTarget | undefined {
  return payload === "server" ? "server" : payload === "local" ? "local" : undefined;
}

function normalizeLabelTaxonomy(payload: unknown): LabelTaxonomy | undefined {
  return payload === "AMOS22" || payload === "FLARE22" || payload === "auto" ? payload : undefined;
}

export function parseInferenceEvent(raw: string): InferenceEvent {
  const line = raw.split(/\r?\n/).find((item) => item.startsWith("data:"));
  if (!line) throw new Error("无效的推理事件");
  const parsed = JSON.parse(line.replace(/^data:\s*/, ""));
  if (parsed.type === "error") {
    const event: InferenceEvent = { type: "error", message: String(parsed.message ?? "推理失败") };
    if (parsed.log_tail !== undefined) event.log_tail = String(parsed.log_tail);
    const resource = normalizeResourceSnapshot(parsed.resource_latest);
    if (resource) event.resource_latest = resource;
    return event;
  }
  const event: InferenceEvent = {
    type: parsed.type === "complete" ? "complete" : "progress",
    progress: Math.max(0, Math.min(100, Number(parsed.progress ?? 0))),
    stage: String(parsed.stage ?? "推理中")
  };
  if (event.type === "progress") {
    if (parsed.heartbeat === true) event.heartbeat = true;
    if (Number.isFinite(Number(parsed.elapsed_seconds))) event.elapsed_seconds = Number(parsed.elapsed_seconds);
  }
  if (event.type === "complete") {
    if (Number.isFinite(Number(parsed.duration_seconds))) event.duration_seconds = Number(parsed.duration_seconds);
    if (Number.isFinite(Number(parsed.result_size_bytes))) event.result_size_bytes = Number(parsed.result_size_bytes);
    const validation = normalizeValidation(parsed.validation);
    if (validation) event.validation = validation;
    const resource = normalizeResourceSnapshot(parsed.resource_latest);
    if (resource) event.resource_latest = resource;
    const phaseTimings = normalizePhaseTimings(parsed.phase_timings);
    if (phaseTimings) event.phase_timings = phaseTimings;
    const inferenceOptions = normalizeInferenceOptions(parsed.inference_options);
    if (inferenceOptions) event.inference_options = inferenceOptions;
    const runtimeTarget = normalizeRuntimeTarget(parsed.runtime_target);
    if (runtimeTarget) event.runtime_target = runtimeTarget;
    if (parsed.cached_result === true) event.cached_result = true;
    if (typeof parsed.cache_source_job_id === "string" && parsed.cache_source_job_id) {
      event.cache_source_job_id = parsed.cache_source_job_id;
    }
  }
  return event;
}

function formatBytes(value: number | undefined) {
  if (!Number.isFinite(value)) return "";
  const bytes = Math.max(0, Number(value));
  if (bytes >= 1024 * 1024 * 1024) return `${(bytes / 1024 / 1024 / 1024).toFixed(2)} GB`;
  if (bytes >= 1024 * 1024) return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
  if (bytes >= 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${bytes} B`;
}

export function getResourceSnapshotCopy(snapshot?: ResourceSnapshot | null) {
  if (!snapshot) return "待记录";
  const parts: string[] = [];
  if (snapshot.device) parts.push(`设备 ${snapshot.device}`);
  if (snapshot.gpu?.name && typeof snapshot.gpu.memory_used_mib === "number" && typeof snapshot.gpu.memory_total_mib === "number") {
    parts.push(`${snapshot.gpu.name} 显存 ${snapshot.gpu.memory_used_mib}/${snapshot.gpu.memory_total_mib} MiB`);
  } else if (snapshot.gpu?.name) {
    parts.push(snapshot.gpu.name);
  }
  const memory = formatBytes(snapshot.server_process_memory_bytes);
  if (memory) parts.push(`服务内存 ${memory}`);
  const diskFree = formatBytes(snapshot.disk_free_bytes);
  if (diskFree) parts.push(`磁盘可用 ${diskFree}`);
  return parts.length ? parts.join(" · ") : "已记录";
}

export function getPhaseTimingSummary(timings?: PhaseTimings | null) {
  if (!timings || !Object.keys(timings).length) return "待记录";
  const labels: Record<string, string> = {
    prepare_runtime_model: "模型准备",
    build_predict_command: "命令生成",
    nnunet_process: "nnUNetv2 子进程",
    server_fold_predict: "服务器 5-fold 推理",
    server_ensemble: "服务器 soft ensemble",
    server_validation: "服务器评估脚本",
    persistent_worker: "常驻 worker",
    collect_result: "结果整理",
    validation: "标准答案验证"
  };
  const [phase, seconds] = Object.entries(timings).sort((left, right) => right[1] - left[1])[0];
  const duration = seconds < 120
    ? `${seconds.toFixed(1)}秒`
    : `${Math.floor(seconds / 60)}分${(seconds % 60).toFixed(1)}秒`;
  return `${labels[phase] ?? phase} ${duration}`;
}

export function getInferenceStatusCopy(status: InferenceStatus) {
  if (status.status === "submitting") return "正在提交任务";
  if (status.status === "running") return `${status.stage} · ${status.progress}%`;
  if (status.status === "succeeded" && status.mode === "debug-label-fallback") return "调试标签回填完成（非真实推理）";
  if (status.status === "succeeded" && status.mode === "cached-real-nnunetv2") {
    const duration = formatDuration(status.duration_seconds);
    return duration ? `缓存推理结果回填完成 · ${duration}` : "缓存推理结果回填完成";
  }
  if (status.status === "succeeded") {
    const duration = formatDuration(status.duration_seconds);
    return duration ? `真实 nnUNetv2 推理完成 · ${duration}` : "真实 nnUNetv2 推理完成";
  }
  if (status.status === "cancelled") return "推理任务已取消";
  if (status.status === "failed") return status.message;
  return "等待推理";
}

export function getInferenceResultMeta(mode: InferenceJobMode | undefined, dimensions: string, inferenceOptions?: InferenceOptions) {
  if (inferenceOptions?.profile === "fast" && mode === "cached-real-nnunetv2") return `${dimensions} · 快速预览缓存 nnUNetv2 结果（需人工复核）`;
  if (inferenceOptions?.profile === "fast" && mode !== "debug-label-fallback" && mode !== "unavailable") return `${dimensions} · 快速预览 nnUNetv2 结果（需人工复核）`;
  if (mode === "cached-real-nnunetv2") return `${dimensions} · 历史缓存 nnUNetv2 结果`;
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
  options: { modelId: string; confidenceThreshold: number; postprocess: Record<string, boolean>; inferenceProfile?: InferenceProfile; runtimeTarget?: RuntimeTarget; labelTaxonomy?: LabelTaxonomy; datasetHint?: string | null; labelFile?: File }
) {
  const formData = new FormData();
  formData.append("file", file, file.name);
  if (options.labelFile) {
    formData.append("label_file", options.labelFile, options.labelFile.name);
  }
  formData.append("model_id", options.modelId);
  formData.append("confidence_threshold", String(options.confidenceThreshold));
  formData.append("postprocess", JSON.stringify(options.postprocess));
  formData.append("inference_profile", options.inferenceProfile ?? "quality");
  formData.append("runtime_target", options.runtimeTarget ?? "server");
  formData.append("label_taxonomy", options.labelTaxonomy ?? "auto");
  if (options.datasetHint) {
    formData.append("dataset_hint", options.datasetHint);
  }

  const response = await fetch(`${endpoint}/api/segment/jobs`, { method: "POST", body: formData });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "推理任务创建失败");
  }
  return await response.json() as {
    job_id: string;
    mode?: InferenceJobMode;
    runtime_target?: RuntimeTarget;
    label_taxonomy?: LabelTaxonomy;
    inference_profile?: InferenceProfile;
    inference_options?: InferenceOptions;
    confidence_threshold_effective?: boolean;
    model_status?: {
      ready?: boolean;
      status?: string;
      missing?: string[];
    };
    cached_result?: boolean;
    cache_source_job_id?: string;
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

export async function cancelInferenceJob(endpoint: string, jobId: string) {
  const response = await fetch(`${endpoint}/api/segment/jobs/${jobId}/cancel`, { method: "POST" });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || "取消推理任务失败");
  }
  return await response.json() as {
    job_id: string;
    status: "pending" | "running" | "cancelling" | "cancelled" | "succeeded" | "failed";
    cancel_requested?: boolean;
  };
}
