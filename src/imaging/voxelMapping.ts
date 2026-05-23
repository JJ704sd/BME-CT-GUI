export type Orientation = "axial" | "sagittal" | "coronal";

export type VolumeGrid = {
  columns: number;
  rows: number;
  slices: number;
  spacingX?: number;
  spacingY?: number;
  spacingZ?: number;
};

export type VoxelCoord = {
  x: number;
  y: number;
  z: number;
};

export type SlicePoint = {
  column: number;
  row: number;
};

function clamp(value: number, maxExclusive: number) {
  return Math.max(0, Math.min(Math.max(0, maxExclusive - 1), Math.round(value)));
}

export function clampVoxelCoord(coord: VoxelCoord, volume: VolumeGrid): VoxelCoord {
  return {
    x: clamp(coord.x, volume.columns),
    y: clamp(coord.y, volume.rows),
    z: clamp(coord.z, volume.slices)
  };
}

export function getOrientationDimensions(orientation: Orientation, volume: VolumeGrid) {
  if (orientation === "sagittal") return { width: volume.slices, height: volume.rows };
  if (orientation === "coronal") return { width: volume.columns, height: volume.slices };
  return { width: volume.columns, height: volume.rows };
}

function finitePositive(value: number | undefined, fallback: number) {
  return typeof value === "number" && Number.isFinite(value) && value > 0 ? value : fallback;
}

function formatAspectPart(value: number) {
  return Number(value.toFixed(3)).toString();
}

function clampDisplayRatio(ratio: number) {
  if (!Number.isFinite(ratio) || ratio <= 0) return 1;
  return Math.max(0.9, Math.min(1.2, ratio));
}

export function getOrientationDisplayRatio(orientation: Orientation, volume: VolumeGrid) {
  const spacingX = finitePositive(volume.spacingX, 1);
  const spacingY = finitePositive(volume.spacingY, 1);
  const spacingZ = finitePositive(volume.spacingZ, 1);
  const width = orientation === "sagittal"
    ? volume.slices * spacingZ
    : volume.columns * spacingX;
  const height = orientation === "coronal"
    ? volume.slices * spacingZ
    : volume.rows * spacingY;
  return clampDisplayRatio(width / Math.max(1e-6, height));
}

export function getOrientationDisplayAspect(orientation: Orientation, volume: VolumeGrid) {
  const spacingX = finitePositive(volume.spacingX, 1);
  const spacingY = finitePositive(volume.spacingY, 1);
  const spacingZ = finitePositive(volume.spacingZ, 1);
  const width = orientation === "sagittal"
    ? volume.slices * spacingZ
    : volume.columns * spacingX;
  const height = orientation === "coronal"
    ? volume.slices * spacingZ
    : volume.rows * spacingY;
  const physicalRatio = width / Math.max(1e-6, height);
  const displayRatio = getOrientationDisplayRatio(orientation, volume);
  if (displayRatio !== physicalRatio) {
    return `${formatAspectPart(displayRatio)} / 1`;
  }
  return `${formatAspectPart(width)} / ${formatAspectPart(height)}`;
}

export function getSliceIndexForOrientation(orientation: Orientation, coord: VoxelCoord) {
  if (orientation === "sagittal") return coord.x;
  if (orientation === "coronal") return coord.y;
  return coord.z;
}

export function voxelCoordToSlicePoint(orientation: Orientation, coord: VoxelCoord): SlicePoint {
  if (orientation === "sagittal") return { column: coord.z, row: coord.y };
  if (orientation === "coronal") return { column: coord.x, row: coord.z };
  return { column: coord.x, row: coord.y };
}

export function slicePointToVoxelCoord(
  orientation: Orientation,
  point: SlicePoint,
  current: VoxelCoord,
  volume: VolumeGrid
): VoxelCoord {
  const next = orientation === "sagittal"
    ? { x: current.x, y: point.row, z: point.column }
    : orientation === "coronal"
      ? { x: point.column, y: current.y, z: point.row }
      : { x: point.column, y: point.row, z: current.z };
  return clampVoxelCoord(next, volume);
}

export function clientPointToSlicePoint(
  clientX: number,
  clientY: number,
  rect: Pick<DOMRect, "left" | "top" | "width" | "height">,
  dimensions: { width: number; height: number },
  displayRatio = dimensions.width / Math.max(1, dimensions.height)
): SlicePoint | null {
  const imageRatio = Number.isFinite(displayRatio) && displayRatio > 0
    ? displayRatio
    : dimensions.width / Math.max(1, dimensions.height);
  const rectRatio = rect.width / Math.max(1, rect.height);
  const content = imageRatio > rectRatio
    ? {
        left: rect.left,
        top: rect.top + (rect.height - rect.width / imageRatio) / 2,
        width: rect.width,
        height: rect.width / imageRatio
      }
    : {
        left: rect.left + (rect.width - rect.height * imageRatio) / 2,
        top: rect.top,
        width: rect.height * imageRatio,
        height: rect.height
      };
  if (
    clientX < content.left ||
    clientY < content.top ||
    clientX > content.left + content.width ||
    clientY > content.top + content.height
  ) {
    return null;
  }
  const column = ((clientX - content.left) / Math.max(1, content.width)) * dimensions.width;
  const row = ((clientY - content.top) / Math.max(1, content.height)) * dimensions.height;
  return {
    column: clamp(column, dimensions.width),
    row: clamp(row, dimensions.height)
  };
}

export function getCrosshairPercent(orientation: Orientation, coord: VoxelCoord, volume: VolumeGrid) {
  const point = voxelCoordToSlicePoint(orientation, coord);
  const dimensions = getOrientationDimensions(orientation, volume);
  return {
    x: ((point.column + 0.5) / Math.max(1, dimensions.width)) * 100,
    y: ((point.row + 0.5) / Math.max(1, dimensions.height)) * 100
  };
}
