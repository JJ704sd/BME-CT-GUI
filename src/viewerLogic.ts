export type DisplayGridVolume = {
  columns: number;
  rows: number;
  slices: number;
  spacing: string;
};

export type DisplayImageLike = {
  dimensions?: string;
  volume?: Partial<DisplayGridVolume>;
};

export type DisplayVoxelCoord = {
  x: number;
  y: number;
  z: number;
};

export function shouldUpdateVoxelCoord(current: DisplayVoxelCoord, next: DisplayVoxelCoord) {
  return current.x !== next.x || current.y !== next.y || current.z !== next.z;
}

export function volumesShareDisplayGrid(source: DisplayGridVolume, result: DisplayGridVolume) {
  return source.columns === result.columns
    && source.rows === result.rows
    && source.slices === result.slices
    && source.spacing === result.spacing;
}

export function buildCustomCaseId(existingIds: string[]) {
  const next = existingIds.reduce((highest, id) => {
    const match = /^Custom_Case_(\d+)$/.exec(id);
    return match ? Math.max(highest, Number(match[1])) : highest;
  }, 0) + 1;
  return `Custom_Case_${String(next).padStart(3, "0")}`;
}

export function getDisplayAspectRatio(image: DisplayImageLike) {
  if (image.volume?.columns && image.volume.rows) {
    return `${image.volume.columns} / ${image.volume.rows}`;
  }
  const match = image.dimensions?.match(/^(\d+)x(\d+)(?:x\d+)?$/);
  if (match) {
    return `${Number(match[1])} / ${Number(match[2])}`;
  }
  return "1 / 1";
}

export function getSplitPositionFromClientX(clientX: number, rectLeft: number, rectWidth: number) {
  if (!Number.isFinite(rectWidth) || rectWidth <= 0) {
    return 50;
  }

  const rawPercent = ((clientX - rectLeft) / rectWidth) * 100;
  return Math.max(25, Math.min(75, Math.round(rawPercent)));
}

export function getStableSliceWindowStart(
  currentStart: number,
  selectedSlice: number,
  totalSlices: number,
  preferredCount: number
) {
  const safeTotal = Math.max(1, Math.floor(totalSlices));
  const visibleCount = Math.max(1, Math.min(Math.floor(preferredCount), safeTotal));
  const maxStart = Math.max(1, safeTotal - visibleCount + 1);
  const safeSelected = Math.max(1, Math.min(safeTotal, Math.floor(selectedSlice)));
  const normalizedStart = Math.max(1, Math.min(maxStart, Math.floor(currentStart)));
  const normalizedEnd = normalizedStart + visibleCount - 1;

  if (safeSelected < normalizedStart) {
    return safeSelected;
  }

  if (safeSelected > normalizedEnd) {
    return Math.max(1, Math.min(maxStart, safeSelected - visibleCount + 1));
  }

  return normalizedStart;
}

export function getSelectedSliceForVoxelCoord(coord: DisplayVoxelCoord, totalSlices: number) {
  const safeTotal = Math.max(1, Math.floor(totalSlices));
  const slice = Math.round(coord.z) + 1;
  return Math.max(1, Math.min(safeTotal, slice));
}

export function getRegistrationStatus(source: DisplayImageLike, result?: DisplayImageLike | null) {
  if (!result) {
    return { label: "等待结果图", ready: true, severity: "idle" as const };
  }

  if (source.volume && result.volume) {
    const sourceVolume = source.volume;
    const resultVolume = result.volume;
    const hasFullGrid = sourceVolume.columns && sourceVolume.rows && sourceVolume.slices && sourceVolume.spacing
      && resultVolume.columns && resultVolume.rows && resultVolume.slices && resultVolume.spacing;

    if (hasFullGrid) {
      return volumesShareDisplayGrid(sourceVolume as DisplayGridVolume, resultVolume as DisplayGridVolume)
        ? { label: "体数据矩阵与间距匹配", ready: true, severity: "ok" as const }
        : { label: "体数据矩阵或间距不一致", ready: false, severity: "warning" as const };
    }
  }

  if (source.volume || result.volume) {
    return { label: "原图与结果类型不一致", ready: false, severity: "warning" as const };
  }

  if (source.dimensions && result.dimensions) {
    return source.dimensions === result.dimensions
      ? { label: "像素矩阵匹配", ready: true, severity: "ok" as const }
      : { label: "像素矩阵不一致", ready: false, severity: "warning" as const };
  }

  return { label: "自动适配显示", ready: true, severity: "idle" as const };
}

export function getCustomCasePanelCopy(customCaseCount: number, hasLocalSource: boolean, selectedIsCustom: boolean) {
  return {
    countLabel: customCaseCount > 0 ? `已保存 ${customCaseCount} 个自定义病例` : "尚未保存自定义病例",
    saveHint: hasLocalSource ? "保存当前上传内容，便于后续切换复核" : "先上传原图，再保存为自定义病例",
    canSave: hasLocalSource,
    canDeleteSelected: selectedIsCustom
  };
}

export function getAlignmentCaptionCopy(
  source: DisplayImageLike,
  result: DisplayImageLike | null | undefined,
  registrationStatus: { label: string; severity: "idle" | "ok" | "warning" }
) {
  return {
    sourceDimension: source.dimensions ?? "演示切片",
    resultDimension: result?.dimensions ?? "内置掩膜",
    statusTitle: registrationStatus.severity === "warning" ? "需复核" : registrationStatus.severity === "ok" ? "已匹配" : "待配对",
    statusDetail: registrationStatus.label
  };
}
