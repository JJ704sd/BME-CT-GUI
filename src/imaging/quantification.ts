import type { OrganLabel } from "../data/organDetails";

export type NiftiMaskVolumeLike = {
  image: ArrayBuffer;
  columns: number;
  rows: number;
  slices: number;
  spacingX?: number;
  spacingY?: number;
  spacingZ?: number;
  datatypeCode: number;
  littleEndian: boolean;
  bytesPerVoxel: number;
  slope: number;
  intercept: number;
};

function getNiftiMaskValue(view: DataView, byteOffset: number, datatypeCode: number, littleEndian: boolean) {
  switch (datatypeCode) {
    case 2:
      return view.getUint8(byteOffset);
    case 4:
      return view.getInt16(byteOffset, littleEndian);
    case 8:
      return view.getInt32(byteOffset, littleEndian);
    case 16:
      return view.getFloat32(byteOffset, littleEndian);
    case 64:
      return view.getFloat64(byteOffset, littleEndian);
    case 256:
      return view.getInt8(byteOffset);
    case 512:
      return view.getUint16(byteOffset, littleEndian);
    case 768:
      return view.getUint32(byteOffset, littleEndian);
    default:
      throw new Error(`暂不支持该 NIfTI 数据类型：${datatypeCode}`);
  }
}

export type QuantificationStatus = "computed" | "empty" | "unavailable";

export type OrganQuantification = {
  label: number;
  id: string;
  name: string;
  voxelCount: number;
  volumeMl: number | null;
  bboxMm: { x: number; y: number; z: number } | null;
  maxDiameterMm: number | null;
  maxAxialAreaMm2: number | null;
  estimatedLengthMm: number | null;
  lumenAreaInterpretation: string;
  wallThicknessStatus: string;
  status: QuantificationStatus;
  note: string;
};

export type QuantificationSummary = {
  status: QuantificationStatus;
  spacingMm: { x: number; y: number; z: number } | null;
  organs: OrganQuantification[];
  note: string;
};

type MutableOrganStats = {
  label: OrganLabel;
  voxelCount: number;
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
  minZ: number;
  maxZ: number;
  axialCounts: Map<number, number>;
};

const vesselOrganIds = new Set(["aorta", "ivc"]);
const hollowOrganIds = new Set(["stomach", "gallbladder", "esophagus", "duodenum", "bladder", "colon", "rectum", "small-bowel", "large-bowel"]);

function getValidSpacing(volume: NiftiMaskVolumeLike) {
  const spacing = { x: volume.spacingX, y: volume.spacingY, z: volume.spacingZ };
  if (!Number.isFinite(spacing.x) || !Number.isFinite(spacing.y) || !Number.isFinite(spacing.z)) return null;
  if ((spacing.x ?? 0) <= 0 || (spacing.y ?? 0) <= 0 || (spacing.z ?? 0) <= 0) return null;
  return { x: spacing.x as number, y: spacing.y as number, z: spacing.z as number };
}

function createEmptyStats(label: OrganLabel): MutableOrganStats {
  return {
    label,
    voxelCount: 0,
    minX: Number.POSITIVE_INFINITY,
    maxX: Number.NEGATIVE_INFINITY,
    minY: Number.POSITIVE_INFINITY,
    maxY: Number.NEGATIVE_INFINITY,
    minZ: Number.POSITIVE_INFINITY,
    maxZ: Number.NEGATIVE_INFINITY,
    axialCounts: new Map()
  };
}

function updateStats(stats: MutableOrganStats, x: number, y: number, z: number) {
  stats.voxelCount += 1;
  stats.minX = Math.min(stats.minX, x);
  stats.maxX = Math.max(stats.maxX, x);
  stats.minY = Math.min(stats.minY, y);
  stats.maxY = Math.max(stats.maxY, y);
  stats.minZ = Math.min(stats.minZ, z);
  stats.maxZ = Math.max(stats.maxZ, z);
  stats.axialCounts.set(z, (stats.axialCounts.get(z) ?? 0) + 1);
}

function toOrganQuantification(stats: MutableOrganStats, spacing: { x: number; y: number; z: number }): OrganQuantification {
  const { label } = stats;
  if (stats.voxelCount === 0) {
    return {
      label: label.label,
      id: label.id,
      name: label.nameZh,
      voxelCount: 0,
      volumeMl: null,
      bboxMm: null,
      maxDiameterMm: null,
      maxAxialAreaMm2: null,
      estimatedLengthMm: null,
      lumenAreaInterpretation: getLumenAreaInterpretation(label.id),
      wallThicknessStatus: getWallThicknessStatus(label.id),
      status: "empty",
      note: "该标签在当前分割 mask 中未出现。"
    };
  }

  const bboxMm = {
    x: (stats.maxX - stats.minX + 1) * spacing.x,
    y: (stats.maxY - stats.minY + 1) * spacing.y,
    z: (stats.maxZ - stats.minZ + 1) * spacing.z
  };
  const maxSliceVoxelCount = Math.max(...stats.axialCounts.values());
  const maxAxialAreaMm2 = maxSliceVoxelCount * spacing.x * spacing.y;

  return {
    label: label.label,
    id: label.id,
    name: label.nameZh,
    voxelCount: stats.voxelCount,
    volumeMl: stats.voxelCount * spacing.x * spacing.y * spacing.z / 1000,
    bboxMm,
    maxDiameterMm: Math.max(bboxMm.x, bboxMm.y, bboxMm.z),
    maxAxialAreaMm2,
    estimatedLengthMm: bboxMm.z,
    lumenAreaInterpretation: getLumenAreaInterpretation(label.id),
    wallThicknessStatus: getWallThicknessStatus(label.id),
    status: "computed",
    note: "体积、截面积和长度由自动分割 mask 与 NIfTI spacing 估算，需结合影像复核。"
  };
}

export function getLumenAreaInterpretation(organId: string): string {
  if (vesselOrganIds.has(organId)) return "最大轴向截面积可作为血管管腔截面积近似。";
  if (hollowOrganIds.has(organId)) return "当前为整体器官截面积估算，不等同于真实管腔截面积。";
  return "当前标签不属于典型管腔结构，截面积仅表示器官 mask 横断面积。";
}

export function getWallThicknessStatus(organId: string): string {
  if (hollowOrganIds.has(organId) || vesselOrganIds.has(organId)) return "当前标签未区分壁/腔，暂不输出壁厚数值。";
  return "当前器官标签不支持壁厚计算。";
}

export function formatQuantificationValue(value: number | null | undefined, unit: string): string {
  if (value == null || !Number.isFinite(value)) return "—";
  const digits = Math.abs(value) >= 100 ? 1 : 2;
  return `${value.toFixed(digits)} ${unit}`;
}

export function summarizeSegmentationQuantification(maskVolume: NiftiMaskVolumeLike | undefined | null, labels: OrganLabel[]): QuantificationSummary {
  if (!maskVolume) {
    return {
      status: "unavailable",
      spacingMm: null,
      organs: labels.map((label) => ({
        label: label.label,
        id: label.id,
        name: label.nameZh,
        voxelCount: 0,
        volumeMl: null,
        bboxMm: null,
        maxDiameterMm: null,
        maxAxialAreaMm2: null,
        estimatedLengthMm: null,
        lumenAreaInterpretation: getLumenAreaInterpretation(label.id),
        wallThicknessStatus: getWallThicknessStatus(label.id),
        status: "unavailable",
        note: "等待分割结果后自动计算。"
      })),
      note: "等待分割结果后自动计算体积、截面积和长度估算。"
    };
  }

  const spacing = getValidSpacing(maskVolume);
  if (!spacing) {
    return {
      status: "unavailable",
      spacingMm: null,
      organs: labels.map((label) => ({
        label: label.label,
        id: label.id,
        name: label.nameZh,
        voxelCount: 0,
        volumeMl: null,
        bboxMm: null,
        maxDiameterMm: null,
        maxAxialAreaMm2: null,
        estimatedLengthMm: null,
        lumenAreaInterpretation: getLumenAreaInterpretation(label.id),
        wallThicknessStatus: getWallThicknessStatus(label.id),
        status: "unavailable",
        note: "NIfTI 体素间距不可用，无法换算物理量。"
      })),
      note: "NIfTI 体素间距不可用，无法换算物理量。"
    };
  }

  const statsByLabel = new Map(labels.map((label) => [label.label, createEmptyStats(label)]));
  const view = new DataView(maskVolume.image);
  const sliceVoxelCount = maskVolume.columns * maskVolume.rows;
  const totalVoxels = sliceVoxelCount * maskVolume.slices;

  for (let index = 0; index < totalVoxels; index += 1) {
    const labelValue = Math.round(getNiftiMaskValue(view, index * maskVolume.bytesPerVoxel, maskVolume.datatypeCode, maskVolume.littleEndian) * maskVolume.slope + maskVolume.intercept);
    const stats = statsByLabel.get(labelValue);
    if (!stats) continue;
    const z = Math.floor(index / sliceVoxelCount);
    const inSliceIndex = index - z * sliceVoxelCount;
    const y = Math.floor(inSliceIndex / maskVolume.columns);
    const x = inSliceIndex - y * maskVolume.columns;
    updateStats(stats, x, y, z);
  }

  const organs = labels.map((label) => toOrganQuantification(statsByLabel.get(label.label) ?? createEmptyStats(label), spacing));
  const hasComputed = organs.some((organ) => organ.status === "computed");

  return {
    status: hasComputed ? "computed" : "empty",
    spacingMm: spacing,
    organs,
    note: hasComputed
      ? "已基于分割 mask 自动计算器官量化指标。"
      : "当前分割 mask 中未发现配置标签的前景体素。"
  };
}
