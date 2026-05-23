import assert from "node:assert/strict";
import {
  clampVoxelCoord,
  clientPointToSlicePoint,
  getCrosshairPercent,
  getOrientationDisplayAspect,
  getOrientationDimensions,
  getSliceContentFrame,
  getSliceRenderKey,
  getSliceIndexForOrientation,
  slicePointToVoxelCoord,
  voxelCoordToSlicePoint
} from "../src/imaging/voxelMapping.ts";
import { buildLabelLookup, defaultOrganLabels, getOrganDetail } from "../src/data/organDetails.ts";
import { getInferenceResultMeta, getInferenceStatusCopy, normalizeModelLabels, parseInferenceEvent } from "../src/inference/inferenceClient.ts";

const volume = { columns: 10, rows: 20, slices: 30 };
const coord = { x: 4, y: 8, z: 12 };

assert.deepEqual(clampVoxelCoord({ x: -1, y: 99, z: 12 }, volume), { x: 0, y: 19, z: 12 });

assert.deepEqual(getOrientationDimensions("axial", volume), { width: 10, height: 20 });
assert.deepEqual(getOrientationDimensions("sagittal", volume), { width: 20, height: 30 });
assert.deepEqual(getOrientationDimensions("coronal", volume), { width: 10, height: 30 });

const letterboxedRect = { left: 0, top: 0, width: 400, height: 200 };
assert.deepEqual(
  clientPointToSlicePoint(100, 100, letterboxedRect, { width: 100, height: 100 }),
  { column: 0, row: 50 },
  "content starts at x=100 when a square slice is contained in a 2:1 canvas"
);
assert.equal(
  clientPointToSlicePoint(50, 100, letterboxedRect, { width: 100, height: 100 }),
  null,
  "clicks in the object-fit letterbox area should not move the voxel cursor"
);
assert.deepEqual(
  clientPointToSlicePoint(200, 100, { left: 0, top: 0, width: 200, height: 400 }, { width: 100, height: 100 }),
  { column: 99, row: 0 },
  "vertical letterboxing should map only the contained image box"
);
assert.deepEqual(getSliceContentFrame(2, 1), { left: 25, top: 0, width: 50, height: 100 });
assert.deepEqual(getSliceContentFrame(0.5, 1), { left: 0, top: 25, width: 100, height: 50 });

const anisotropicCt = { columns: 512, rows: 512, slices: 80, spacingX: 0.8, spacingY: 0.8, spacingZ: 5 };
assert.equal(getOrientationDisplayAspect("axial", anisotropicCt), "409.6 / 409.6");
assert.equal(getOrientationDisplayAspect("sagittal", anisotropicCt), "409.6 / 400");
assert.equal(getOrientationDisplayAspect("coronal", anisotropicCt), "409.6 / 400");
assert.equal(getOrientationDisplayAspect("sagittal", volume), "0.9 / 1");
assert.equal(getOrientationDisplayAspect("sagittal", { columns: 512, rows: 512, slices: 80, spacingX: 0.8, spacingY: 0.8, spacingZ: 1 }), "1.2 / 1");
assert.equal(getOrientationDisplayAspect("coronal", { columns: 512, rows: 512, slices: 80, spacingX: 0.8, spacingY: 0.8, spacingZ: 1 }), "1.2 / 1");

assert.equal(getSliceIndexForOrientation("axial", coord), 12);
assert.equal(getSliceIndexForOrientation("sagittal", coord), 4);
assert.equal(getSliceIndexForOrientation("coronal", coord), 8);
assert.equal(getSliceRenderKey("axial", coord, volume), getSliceRenderKey("axial", { ...coord, x: 8, y: 12 }, volume));
assert.notEqual(getSliceRenderKey("axial", coord, volume), getSliceRenderKey("axial", { ...coord, z: 18 }, volume));
assert.equal(getSliceRenderKey("sagittal", coord, volume), getSliceRenderKey("sagittal", { ...coord, y: 12, z: 18 }, volume));
assert.notEqual(getSliceRenderKey("sagittal", coord, volume), getSliceRenderKey("sagittal", { ...coord, x: 8 }, volume));
assert.equal(getSliceRenderKey("coronal", coord, volume), getSliceRenderKey("coronal", { ...coord, x: 8, z: 18 }, volume));
assert.notEqual(getSliceRenderKey("coronal", coord, volume), getSliceRenderKey("coronal", { ...coord, y: 12 }, volume));

assert.deepEqual(voxelCoordToSlicePoint("axial", coord, volume), { column: 4, row: 11 });
assert.deepEqual(voxelCoordToSlicePoint("sagittal", coord, volume), { column: 11, row: 17 });
assert.deepEqual(voxelCoordToSlicePoint("coronal", coord, volume), { column: 4, row: 17 });

assert.deepEqual(slicePointToVoxelCoord("axial", { column: 3, row: 7 }, coord, volume), { x: 3, y: 12, z: 12 });
assert.deepEqual(slicePointToVoxelCoord("sagittal", { column: 13, row: 7 }, coord, volume), { x: 4, y: 6, z: 22 });
assert.deepEqual(slicePointToVoxelCoord("coronal", { column: 6, row: 11 }, coord, volume), { x: 6, y: 8, z: 18 });
assert.deepEqual(slicePointToVoxelCoord("axial", { column: 0, row: 0 }, coord, volume), { x: 0, y: 19, z: 12 });
assert.deepEqual(slicePointToVoxelCoord("sagittal", { column: 0, row: 0 }, coord, volume), { x: 4, y: 19, z: 29 });
assert.deepEqual(slicePointToVoxelCoord("coronal", { column: 0, row: 0 }, coord, volume), { x: 0, y: 8, z: 29 });
const axialCrosshair = getCrosshairPercent("axial", coord, volume);
assert.equal(axialCrosshair.x, 45);
assert.ok(Math.abs(axialCrosshair.y - 57.5) < 1e-9);
const letterboxedCrosshair = getCrosshairPercent("axial", { x: 0, y: 19, z: 12 }, { columns: 100, rows: 100, slices: 30 }, 2, 1);
assert.equal(letterboxedCrosshair.left, 25);
assert.equal(letterboxedCrosshair.width, 50);
assert.equal(letterboxedCrosshair.x, 25.25);

const lookup = buildLabelLookup([
  { label: 1, id: "liver", nameZh: "肝脏", color: "#4fd1a5" },
  { label: 4, id: "pancreas", nameZh: "胰腺", color: "#f4b95f" }
]);
assert.equal(lookup.byLabel.get(4)?.id, "pancreas");
assert.equal(lookup.byId.get("liver")?.label, 1);
assert.equal(getOrganDetail("liver").functionSummary.includes("代谢"), true);
assert.equal(defaultOrganLabels.length, 15);
assert.equal(buildLabelLookup(defaultOrganLabels).byLabel.get(9)?.id, "ivc");
assert.equal(buildLabelLookup(defaultOrganLabels).byLabel.get(14)?.id, "bladder");
assert.equal(buildLabelLookup(defaultOrganLabels).byLabel.get(15)?.id, "prostate-or-uterus");
for (const label of defaultOrganLabels) {
  assert.notEqual(getOrganDetail(label.id).segmentationNotes.includes("待完善"), true, `${label.id} should have an organ detail`);
}

assert.deepEqual(parseInferenceEvent('data: {"type":"progress","progress":45,"stage":"推理中"}\n\n'), {
  type: "progress",
  progress: 45,
  stage: "推理中"
});
assert.deepEqual(parseInferenceEvent('data: {"type":"error","message":"推理失败","log_tail":"CUDA out of memory"}\n\n'), {
  type: "error",
  message: "推理失败",
  log_tail: "CUDA out of memory"
});
assert.deepEqual(parseInferenceEvent('data: {"type":"complete","progress":100,"stage":"完成","duration_seconds":386.42,"result_size_bytes":141460,"validation":{"status":"passed","sample_id":"amos_0117","mean_dice":0.91,"min_dice":0.77,"foreground_dice":0.93,"accepted":true,"message":"达标"}}\n\n'), {
  type: "complete",
  progress: 100,
  stage: "完成",
  duration_seconds: 386.42,
  result_size_bytes: 141460,
  validation: {
    status: "passed",
    sample_id: "amos_0117",
    mean_dice: 0.91,
    min_dice: 0.77,
    foreground_dice: 0.93,
    accepted: true,
    message: "达标"
  }
});
assert.equal(getInferenceStatusCopy({ status: "running", progress: 45, stage: "推理中" }), "推理中 · 45%");
assert.equal(getInferenceStatusCopy({ status: "succeeded", mode: "real-nnunetv2", duration_seconds: 386.42 }), "真实 nnUNetv2 推理完成 · 6分26秒");
assert.equal(getInferenceStatusCopy({ status: "succeeded", mode: "debug-label-fallback" }), "调试标签回填完成（非真实推理）");
assert.equal(getInferenceStatusCopy({ status: "failed", message: "模型配置不完整" }), "模型配置不完整");
assert.equal(getInferenceResultMeta("real-nnunetv2", "512x512x100"), "512x512x100 · nnUNetv2 真实推理结果");
assert.equal(getInferenceResultMeta("debug-label-fallback", "512x512x100"), "512x512x100 · 调试标签回填结果（非真实推理）");
assert.deepEqual(normalizeModelLabels({
  models: [{
    labels: [
      { label: "4", id: "pancreas", nameZh: "胰腺", color: "#f4b95f" },
      { label: 0, id: "background", nameZh: "背景", color: "#000000" },
      { label: 10, id: "", nameZh: "食管", color: "#ffd166" }
    ]
  }]
}), [
  { label: 4, id: "pancreas", nameZh: "胰腺", color: "#f4b95f" },
  { label: 10, id: "label-10", nameZh: "食管", color: "#ffd166" }
]);
