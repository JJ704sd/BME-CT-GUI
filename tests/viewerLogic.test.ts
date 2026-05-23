import assert from "node:assert/strict";
import { buildCustomCaseId, getAlignmentCaptionCopy, getCustomCasePanelCopy, getDisplayAspectRatio, getRegistrationStatus, getSelectedSliceForVoxelCoord, getSplitPositionFromClientX, getStableSliceWindowStart, volumesShareDisplayGrid } from "../src/viewerLogic.ts";

assert.equal(buildCustomCaseId([]), "Custom_Case_001");
assert.equal(buildCustomCaseId(["Custom_Case_001", "Case_LUNG_112"]), "Custom_Case_002");
assert.equal(buildCustomCaseId(["Custom_Case_001", "Custom_Case_003"]), "Custom_Case_004");

const baseVolume = {
  columns: 640,
  rows: 320,
  slices: 87,
  spacing: "0.80 x 0.80 x 1.50 mm"
};

assert.equal(volumesShareDisplayGrid(baseVolume, { ...baseVolume }), true);
assert.equal(volumesShareDisplayGrid(baseVolume, { ...baseVolume, rows: 256 }), false);
assert.equal(volumesShareDisplayGrid(baseVolume, { ...baseVolume, spacing: "0.80 x 0.80 x 1.00 mm" }), false);

assert.equal(getDisplayAspectRatio({ volume: baseVolume }), "640 / 320");
assert.equal(getDisplayAspectRatio({ dimensions: "768x512" }), "768 / 512");
assert.equal(getDisplayAspectRatio({ dimensions: "640x320x87" }), "640 / 320");
assert.equal(getDisplayAspectRatio({}), "1 / 1");

assert.equal(getSplitPositionFromClientX(300, 100, 400), 50);
assert.equal(getSplitPositionFromClientX(351, 100, 400), 63);
assert.equal(getSplitPositionFromClientX(80, 100, 400), 25);
assert.equal(getSplitPositionFromClientX(520, 100, 400), 75);
assert.equal(getSplitPositionFromClientX(300, 100, 0), 50);

assert.equal(getStableSliceWindowStart(148, 150, 301, 7), 148);
assert.equal(getStableSliceWindowStart(148, 151, 301, 7), 148);
assert.equal(getStableSliceWindowStart(148, 155, 301, 7), 149);
assert.equal(getStableSliceWindowStart(148, 147, 301, 7), 147);
assert.equal(getStableSliceWindowStart(500, 301, 301, 7), 295);
assert.equal(getStableSliceWindowStart(-20, 1, 4, 7), 1);

assert.equal(getSelectedSliceForVoxelCoord({ x: 10, y: 20, z: 72 }, 103), 73);
assert.equal(getSelectedSliceForVoxelCoord({ x: 10, y: 20, z: -5 }, 103), 1);
assert.equal(getSelectedSliceForVoxelCoord({ x: 10, y: 20, z: 500 }, 103), 103);

assert.deepEqual(getRegistrationStatus({ dimensions: "640x320" }, null), {
  label: "等待结果图",
  ready: true,
  severity: "idle"
});
assert.deepEqual(getRegistrationStatus({ dimensions: "640x320" }, { dimensions: "640x320" }), {
  label: "像素矩阵匹配",
  ready: true,
  severity: "ok"
});
assert.deepEqual(getRegistrationStatus({ dimensions: "640x320" }, { dimensions: "512x512" }), {
  label: "像素矩阵不一致",
  ready: false,
  severity: "warning"
});
assert.deepEqual(getRegistrationStatus({ volume: baseVolume }, { volume: { ...baseVolume, spacing: "0.80 x 0.80 x 1.00 mm" } }), {
  label: "体数据矩阵或间距不一致",
  ready: false,
  severity: "warning"
});

assert.deepEqual(getCustomCasePanelCopy(0, false, false), {
  countLabel: "尚未保存自定义病例",
  saveHint: "先上传原图，再保存为自定义病例",
  canSave: false,
  canDeleteSelected: false
});
assert.deepEqual(getCustomCasePanelCopy(2, true, true), {
  countLabel: "已保存 2 个自定义病例",
  saveHint: "保存当前上传内容，便于后续切换复核",
  canSave: true,
  canDeleteSelected: true
});

assert.deepEqual(getAlignmentCaptionCopy(
  { dimensions: "640x320" },
  { dimensions: "512x512" },
  { label: "像素矩阵不一致", ready: false, severity: "warning" }
), {
  sourceDimension: "640x320",
  resultDimension: "512x512",
  statusTitle: "需复核",
  statusDetail: "像素矩阵不一致"
});

assert.deepEqual(getAlignmentCaptionCopy(
  {},
  null,
  { label: "等待结果图", ready: true, severity: "idle" }
), {
  sourceDimension: "演示切片",
  resultDimension: "内置掩膜",
  statusTitle: "待配对",
  statusDetail: "等待结果图"
});
