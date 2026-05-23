import type { OrganLabel } from "./data/organDetails";

export type OrganLayerQuality = "accepted" | "review";

export type OrganLayer = {
  id: string;
  name: string;
  color: string;
  score: number | null;
  volume: string;
  visible: boolean;
  quality: OrganLayerQuality;
};

type ValidationLabelMetric = {
  label: number;
  dice?: number | null;
};

function roundScore(value: number) {
  return Math.round(value * 1000) / 10;
}

export function buildOrganLayersFromLabels(
  labels: OrganLabel[],
  previousLayers: OrganLayer[] = [],
  validationLabels: ValidationLabelMetric[] = []
): OrganLayer[] {
  const previousById = new Map(previousLayers.map((organ) => [organ.id, organ]));
  const validationByLabel = new Map(validationLabels.map((metric) => [metric.label, metric]));

  return labels.map((label) => {
    const previous = previousById.get(label.id);
    const validation = validationByLabel.get(label.label);
    const validationDice = validation?.dice;
    const hasValidationScore = typeof validationDice === "number" && Number.isFinite(validationDice);
    const score = hasValidationScore ? roundScore(validationDice) : previous?.score ?? null;

    return {
      id: label.id,
      name: label.nameZh,
      color: label.color,
      score,
      volume: previous?.volume ?? "待测量",
      visible: previous?.visible ?? label.visible ?? true,
      quality: hasValidationScore ? (score !== null && score >= 85 ? "accepted" : "review") : previous?.quality ?? (score !== null && score >= 85 ? "accepted" : "review")
    };
  });
}

export function formatOrganScore(score: number | null) {
  return typeof score === "number" && Number.isFinite(score) ? `${score.toFixed(1)}%` : "待验";
}

export function getMeanOrganDice(organs: OrganLayer[]) {
  const scored = organs.filter((organ) => typeof organ.score === "number" && Number.isFinite(organ.score));
  if (!scored.length) return null;
  return scored.reduce((sum, organ) => sum + Number(organ.score) / 100, 0) / scored.length;
}
