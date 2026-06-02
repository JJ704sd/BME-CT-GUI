export type ReferenceCase = {
  id: string;
  name: string;
  dataset: string;
  modality: string;
  role: string;
  description: string;
  originalUrl: string;
  labelUrl: string;
  originalFilename: string;
  labelFilename: string;
  validationAvailable: boolean;
  hasOriginal: boolean;
  hasLabel: boolean;
};

export const DEFAULT_REFERENCE_CASES: ReferenceCase[] = [
  {
    id: "amos_0117",
    name: "AMOS 0117",
    dataset: "AMOS22",
    modality: "CT",
    role: "built-in-reference",
    description: "内置参考病例，用于演示、回归和标准答案 Dice 验证。",
    originalUrl: "/api/samples/amos_0117/original",
    labelUrl: "/api/samples/amos_0117/label",
    originalFilename: "amos_0117_original.nii.gz",
    labelFilename: "amos_0117_label.nii.gz",
    validationAvailable: true,
    hasOriginal: true,
    hasLabel: true
  }
];

function readString(value: unknown, fallback: string): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

function readBoolean(value: unknown, fallback: boolean): boolean {
  return typeof value === "boolean" ? value : fallback;
}

export function normalizeReferenceCases(payload: unknown): ReferenceCase[] {
  if (!payload || typeof payload !== "object" || !Array.isArray((payload as { samples?: unknown }).samples)) {
    return DEFAULT_REFERENCE_CASES;
  }

  const normalized = (payload as { samples: unknown[] }).samples
    .map((item): ReferenceCase | null => {
      if (!item || typeof item !== "object") return null;
      const sample = item as Record<string, unknown>;
      const id = readString(sample.id, "");
      if (!id) return null;
      const hasOriginal = readBoolean(sample.has_original, true);
      const hasLabel = readBoolean(sample.has_label, readBoolean(sample.validation_available, false));
      return {
        id,
        name: readString(sample.name, id),
        dataset: readString(sample.dataset, "unknown"),
        modality: readString(sample.modality, "CT"),
        role: readString(sample.role, "built-in-reference"),
        description: readString(sample.description, ""),
        originalUrl: readString(sample.original_url, `/api/samples/${id}/original`),
        labelUrl: readString(sample.label_url, `/api/samples/${id}/label`),
        originalFilename: readString(sample.original_filename, `${id}_original.nii.gz`),
        labelFilename: readString(sample.label_filename, `${id}_label.nii.gz`),
        validationAvailable: readBoolean(sample.validation_available, hasOriginal && hasLabel),
        hasOriginal,
        hasLabel
      };
    })
    .filter((item): item is ReferenceCase => item !== null);

  return normalized.length ? normalized : DEFAULT_REFERENCE_CASES;
}

export function getReferenceCaseOriginalUrl(endpoint: string, referenceCase: ReferenceCase): string {
  if (/^https?:\/\//.test(referenceCase.originalUrl)) return referenceCase.originalUrl;
  return `${endpoint.replace(/\/$/, "")}${referenceCase.originalUrl.startsWith("/") ? "" : "/"}${referenceCase.originalUrl}`;
}

export function getReferenceCaseLabelUrl(endpoint: string, referenceCase: ReferenceCase): string {
  if (/^https?:\/\//.test(referenceCase.labelUrl)) return referenceCase.labelUrl;
  return `${endpoint.replace(/\/$/, "")}${referenceCase.labelUrl.startsWith("/") ? "" : "/"}${referenceCase.labelUrl}`;
}
