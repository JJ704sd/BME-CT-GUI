import type { Orientation, VoxelCoord } from "./voxelMapping";
import { clampVoxelCoord, getOrientationDimensions, getOrientationDisplayRatio, getSliceIndexForOrientation } from "./voxelMapping";

export type NiftiVolumeLike = {
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

export type NiftiRenderMode = "intensity" | "mask";

const maskPalette = [
  [80, 232, 190],
  [244, 185, 95],
  [124, 199, 255],
  [239, 138, 168],
  [165, 229, 103],
  [174, 141, 255],
  [255, 107, 107],
  [142, 197, 255],
  [184, 162, 255],
  [255, 184, 107]
];

export function getNiftiValue(view: DataView, byteOffset: number, datatypeCode: number, littleEndian: boolean) {
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

function getSourceIndex(orientation: Orientation, column: number, row: number, fixedSlice: number, volume: NiftiVolumeLike) {
  if (orientation === "sagittal") {
    return fixedSlice + row * volume.columns + column * volume.columns * volume.rows;
  }
  if (orientation === "coronal") {
    return column + fixedSlice * volume.columns + row * volume.columns * volume.rows;
  }
  return column + row * volume.columns + fixedSlice * volume.columns * volume.rows;
}

function getDisplayCanvasSize(dimensions: { width: number; height: number }, displayRatio: number) {
  const ratio = Number.isFinite(displayRatio) && displayRatio > 0 ? displayRatio : dimensions.width / Math.max(1, dimensions.height);
  const longSide = Math.max(dimensions.width, dimensions.height);
  if (ratio >= 1) {
    return {
      width: longSide,
      height: Math.max(1, Math.round(longSide / ratio))
    };
  }
  return {
    width: Math.max(1, Math.round(longSide * ratio)),
    height: longSide
  };
}

export function getVoxelValue(volume: NiftiVolumeLike, coord: VoxelCoord) {
  const safe = clampVoxelCoord(coord, volume);
  const index = safe.x + safe.y * volume.columns + safe.z * volume.columns * volume.rows;
  const view = new DataView(volume.image);
  return getNiftiValue(view, index * volume.bytesPerVoxel, volume.datatypeCode, volume.littleEndian) * volume.slope + volume.intercept;
}

export function getLabelAtVoxel(volume: NiftiVolumeLike | undefined, coord: VoxelCoord) {
  if (!volume) return 0;
  return Math.round(getVoxelValue(volume, coord));
}

export function renderNiftiSliceToDataUrl(
  volume: NiftiVolumeLike,
  coord: VoxelCoord,
  mode: NiftiRenderMode,
  orientation: Orientation,
  visibleLabels?: Set<number>
) {
  const dimensions = getOrientationDimensions(orientation, volume);
  const fixedSlice = getSliceIndexForOrientation(orientation, clampVoxelCoord(coord, volume));
  const view = new DataView(volume.image);
  const values = new Float32Array(dimensions.width * dimensions.height);
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (let row = 0; row < dimensions.height; row += 1) {
    for (let column = 0; column < dimensions.width; column += 1) {
      const sourceIndex = getSourceIndex(orientation, column, row, fixedSlice, volume);
      const value = getNiftiValue(view, sourceIndex * volume.bytesPerVoxel, volume.datatypeCode, volume.littleEndian) * volume.slope + volume.intercept;
      const displayIndex = column + row * dimensions.width;
      values[displayIndex] = value;
      if (mode === "intensity" && Number.isFinite(value)) {
        min = Math.min(min, value);
        max = Math.max(max, value);
      }
    }
  }

  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
    min = 0;
    max = 1;
  }

  const canvas = document.createElement("canvas");
  canvas.width = dimensions.width;
  canvas.height = dimensions.height;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器无法创建 Canvas 渲染上下文。");
  const imageData = context.createImageData(dimensions.width, dimensions.height);

  for (let index = 0; index < values.length; index += 1) {
    const pixelOffset = index * 4;
    if (mode === "mask") {
      const label = Math.round(values[index]);
      if (label <= 0 || !Number.isFinite(label) || (visibleLabels && !visibleLabels.has(label))) {
        imageData.data[pixelOffset + 3] = 0;
      } else {
        const color = maskPalette[(label - 1) % maskPalette.length];
        imageData.data[pixelOffset] = color[0];
        imageData.data[pixelOffset + 1] = color[1];
        imageData.data[pixelOffset + 2] = color[2];
        imageData.data[pixelOffset + 3] = 210;
      }
    } else {
      const normalized = Math.max(0, Math.min(1, (values[index] - min) / Math.max(1e-6, max - min)));
      const gray = Math.round(normalized * 255);
      imageData.data[pixelOffset] = gray;
      imageData.data[pixelOffset + 1] = gray;
      imageData.data[pixelOffset + 2] = gray;
      imageData.data[pixelOffset + 3] = 255;
    }
  }

  context.putImageData(imageData, 0, 0);
  const displaySize = getDisplayCanvasSize(dimensions, getOrientationDisplayRatio(orientation, volume));
  if (displaySize.width === dimensions.width && displaySize.height === dimensions.height) {
    return canvas.toDataURL("image/png");
  }
  const outputCanvas = document.createElement("canvas");
  outputCanvas.width = displaySize.width;
  outputCanvas.height = displaySize.height;
  const outputContext = outputCanvas.getContext("2d");
  if (!outputContext) throw new Error("浏览器无法创建 Canvas 渲染上下文。");
  outputContext.imageSmoothingEnabled = mode === "intensity";
  outputContext.drawImage(canvas, 0, 0, outputCanvas.width, outputCanvas.height);
  return outputCanvas.toDataURL("image/png");
}
