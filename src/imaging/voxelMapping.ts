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
  if (orientation === "sagittal") return { width: volume.rows, height: volume.slices };
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
    ? volume.rows * spacingY
    : volume.columns * spacingX;
  const height = orientation === "coronal"
    ? volume.slices * spacingZ
    : orientation === "sagittal"
      ? volume.slices * spacingZ
    : volume.rows * spacingY;
  return clampDisplayRatio(width / Math.max(1e-6, height));
}

export function getOrientationDisplayAspect(orientation: Orientation, volume: VolumeGrid) {
  const spacingX = finitePositive(volume.spacingX, 1);
  const spacingY = finitePositive(volume.spacingY, 1);
  const spacingZ = finitePositive(volume.spacingZ, 1);
  const width = orientation === "sagittal"
    ? volume.rows * spacingY
    : volume.columns * spacingX;
  const height = orientation === "coronal"
    ? volume.slices * spacingZ
    : orientation === "sagittal"
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

export function getSliceRenderKey(orientation: Orientation, coord: VoxelCoord, volume: VolumeGrid) {
  const safe = clampVoxelCoord(coord, volume);
  return `${orientation}:${getSliceIndexForOrientation(orientation, safe)}`;
}

export function getSliceContentFrame(containerRatio: number, imageRatio: number) {
  const safeContainerRatio = Number.isFinite(containerRatio) && containerRatio > 0 ? containerRatio : 1;
  const safeImageRatio = Number.isFinite(imageRatio) && imageRatio > 0 ? imageRatio : 1;
  if (safeImageRatio > safeContainerRatio) {
    const height = (safeContainerRatio / safeImageRatio) * 100;
    return { left: 0, top: (100 - height) / 2, width: 100, height };
  }
  const width = (safeImageRatio / safeContainerRatio) * 100;
  return { left: (100 - width) / 2, top: 0, width, height: 100 };
}

function displayRowFromVoxel(index: number, maxExclusive: number) {
  return Math.max(0, maxExclusive - 1) - index;
}

function voxelIndexFromDisplayRow(row: number, maxExclusive: number) {
  return Math.max(0, maxExclusive - 1) - Math.round(row);
}

export function voxelCoordToSlicePoint(orientation: Orientation, coord: VoxelCoord, volume: VolumeGrid): SlicePoint {
  const safe = clampVoxelCoord(coord, volume);
  if (orientation === "sagittal") return { column: displayRowFromVoxel(safe.y, volume.rows), row: displayRowFromVoxel(safe.z, volume.slices) };
  if (orientation === "coronal") return { column: safe.x, row: displayRowFromVoxel(safe.z, volume.slices) };
  return { column: safe.x, row: displayRowFromVoxel(safe.y, volume.rows) };
}

export function slicePointToVoxelCoord(
  orientation: Orientation,
  point: SlicePoint,
  current: VoxelCoord,
  volume: VolumeGrid
): VoxelCoord {
  const next = orientation === "sagittal"
    ? { x: current.x, y: voxelIndexFromDisplayRow(point.column, volume.rows), z: voxelIndexFromDisplayRow(point.row, volume.slices) }
    : orientation === "coronal"
      ? { x: point.column, y: current.y, z: voxelIndexFromDisplayRow(point.row, volume.slices) }
      : { x: point.column, y: voxelIndexFromDisplayRow(point.row, volume.rows), z: current.z };
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
  const frame = getSliceContentFrame(rectRatio, imageRatio);
  const content = {
    left: rect.left + rect.width * (frame.left / 100),
    top: rect.top + rect.height * (frame.top / 100),
    width: rect.width * (frame.width / 100),
    height: rect.height * (frame.height / 100)
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

export function getCrosshairPercent(
  orientation: Orientation,
  coord: VoxelCoord,
  volume: VolumeGrid,
  containerRatio?: number,
  displayRatio = getOrientationDisplayRatio(orientation, volume)
) {
  const point = voxelCoordToSlicePoint(orientation, coord, volume);
  const dimensions = getOrientationDimensions(orientation, volume);
  const frame = getSliceContentFrame(containerRatio ?? displayRatio, displayRatio);
  return {
    x: frame.left + ((point.column + 0.5) / Math.max(1, dimensions.width)) * frame.width,
    y: frame.top + ((point.row + 0.5) / Math.max(1, dimensions.height)) * frame.height,
    left: frame.left,
    top: frame.top,
    width: frame.width,
    height: frame.height
  };
}
