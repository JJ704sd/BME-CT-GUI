import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import {
  clampVoxelCoord,
  clientPointToSlicePoint,
  getCrosshairPercent,
  getOrientationDisplayAspect,
  getOrientationDimensions,
  getSliceContentFrame,
  getSliceImageCacheKey,
  getSliceRenderKey,
  getSliceIndexForOrientation,
  slicePointToVoxelCoord,
  voxelCoordToSlicePoint
} from "../src/imaging/voxelMapping.ts";
import { buildLabelLookup, defaultOrganLabels, getOrganDetail } from "../src/data/organDetails.ts";
import { createInferenceJob, getInferenceResultMeta, getInferenceStatusCopy, getPhaseTimingSummary, getResourceSnapshotCopy, normalizeModelLabels, parseInferenceEvent } from "../src/inference/inferenceClient.ts";
import { buildOrganLayersFromLabels } from "../src/organLayerLogic.ts";
import { DEFAULT_REFERENCE_CASES, getReferenceCaseOriginalUrl, normalizeReferenceCases } from "../src/referenceCases.ts";
import { shouldUpdateVoxelCoord } from "../src/viewerLogic.ts";

const mainSource = readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
const orthogonalViewerSource = readFileSync(new URL("../src/components/OrthogonalViewer.tsx", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

for (const copy of ["载入 AMOS " + "样例", "本地 AMOS " + "样例", "AMOS CT " + "样例"]) {
  assert.equal(mainSource.includes(copy), false, `UI should not use AMOS-only copy: ${copy}`);
}
assert.equal(mainSource.includes("载入参考病例"), true, "UI should expose built-in data as a reference case");
assert.equal(mainSource.includes("内置参考病例"), true, "UI should distinguish the built-in reference case from arbitrary imported CT cases");
assert.equal(mainSource.includes("api/samples/amos_0117/original"), false, "UI should load reference cases through sample metadata, not a hard-coded AMOS URL");
assert.equal(mainSource.includes("质量推理"), true, "UI should expose the default quality inference profile");
assert.equal(mainSource.includes("快速预览"), true, "UI should expose the fast preview inference profile");
assert.equal(mainSource.includes("需人工复核"), true, "UI should warn that fast preview results require review");
for (const mockCaseId of ["Case_FLARE_024", "Case_LUNG_112", "Case_PANC_038"]) {
  assert.equal(mainSource.includes(mockCaseId), false, `top case selector should not expose mock case ${mockCaseId}`);
}
for (const realCaseId of ["AMOS_0117", "FLARE22_Tr_0009"]) {
  assert.equal(mainSource.includes(realCaseId), true, `top case selector should expose local real case ${realCaseId}`);
}
assert.equal(orthogonalViewerSource.includes("useRafCoalescedCoord"), true, "orthogonal slice images should coalesce fast cursor moves before rerendering");
assert.equal(mainSource.includes("setSelectedSlice(getSelectedSliceForVoxelCoord"), false, "cursor movement should not synchronously rerender axial previews on every pointer event");
assert.equal(stylesSource.includes(".compare-split.has-mask .ortho-mask"), true, "orthogonal split mode should clip the mask layer only when a mask exists");
assert.equal(orthogonalViewerSource.includes("has-mask"), true, "orthogonal split mode should know when a mask volume is present");
assert.equal(stylesSource.includes("var(--compare-position"), true, "orthogonal split mode should use the split slider position");

assert.deepEqual(normalizeReferenceCases({
  samples: [
    {
      id: "amos_0117",
      name: "AMOS 0117",
      dataset: "AMOS22",
      modality: "CT",
      role: "built-in-reference",
      original_url: "/api/samples/amos_0117/original",
      label_url: "/api/samples/amos_0117/label",
      original_filename: "amos_0117_original.nii.gz",
      label_filename: "amos_0117_label.nii.gz",
      validation_available: true,
      has_original: true,
      has_label: true
    }
  ]
}), [
  {
    id: "amos_0117",
    name: "AMOS 0117",
    dataset: "AMOS22",
    modality: "CT",
    role: "built-in-reference",
    description: "",
    originalUrl: "/api/samples/amos_0117/original",
    labelUrl: "/api/samples/amos_0117/label",
    originalFilename: "amos_0117_original.nii.gz",
    labelFilename: "amos_0117_label.nii.gz",
    validationAvailable: true,
    hasOriginal: true,
    hasLabel: true
  }
]);
assert.equal(getReferenceCaseOriginalUrl("http://127.0.0.1:8000", DEFAULT_REFERENCE_CASES[0]), "http://127.0.0.1:8000/api/samples/amos_0117/original");

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
assert.equal(getSliceImageCacheKey("sagittal", coord, volume, "intensity"), getSliceImageCacheKey("sagittal", { ...coord, y: 12, z: 18 }, volume, "intensity"));
assert.notEqual(getSliceImageCacheKey("sagittal", coord, volume, "intensity"), getSliceImageCacheKey("sagittal", { ...coord, x: 8 }, volume, "intensity"));
assert.equal(getSliceImageCacheKey("axial", coord, volume, "mask", new Set([3, 1])), getSliceImageCacheKey("axial", coord, volume, "mask", new Set([1, 3])));
assert.notEqual(getSliceImageCacheKey("axial", coord, volume, "mask", new Set([3, 1])), getSliceImageCacheKey("axial", coord, volume, "mask", new Set([1])));
assert.equal(shouldUpdateVoxelCoord(coord, { ...coord }), false);
assert.equal(shouldUpdateVoxelCoord(coord, { ...coord, z: coord.z + 1 }), true);

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
const previousOrganLayers = [
  { id: "liver", name: "肝脏", color: "#4fd1a5", score: 96.8, volume: "1421 ml", visible: false, quality: "accepted" as const }
];
const syncedOrganLayers = buildOrganLayersFromLabels(defaultOrganLabels, previousOrganLayers);
assert.equal(syncedOrganLayers.length, 15);
assert.equal(syncedOrganLayers.find((organ) => organ.id === "liver")?.visible, false);
assert.equal(syncedOrganLayers.find((organ) => organ.id === "liver")?.quality, "accepted");
assert.equal(syncedOrganLayers.find((organ) => organ.id === "bladder")?.name, "膀胱");
assert.equal(syncedOrganLayers.find((organ) => organ.id === "prostate-or-uterus")?.score, null);
const validationSyncedLayers = buildOrganLayersFromLabels(defaultOrganLabels, previousOrganLayers, [
  { label: 6, dice: 0.552 },
  { label: 10, dice: 0.918 }
]);
assert.equal(validationSyncedLayers.find((organ) => organ.id === "liver")?.score, 55.2);
assert.equal(validationSyncedLayers.find((organ) => organ.id === "liver")?.quality, "review");
assert.equal(validationSyncedLayers.find((organ) => organ.id === "pancreas")?.score, 91.8);
assert.equal(validationSyncedLayers.find((organ) => organ.id === "pancreas")?.quality, "accepted");

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
assert.deepEqual(parseInferenceEvent('data: {"type":"complete","progress":100,"stage":"完成","resource_latest":{"phase":"completed","timestamp":100.5,"device":"cuda","disk_free_bytes":4294967296,"gpu":{"name":"RTX 4060","memory_used_mib":512,"memory_total_mib":8192}}}\n\n'), {
  type: "complete",
  progress: 100,
  stage: "完成",
  resource_latest: {
    phase: "completed",
    timestamp: 100.5,
    device: "cuda",
    disk_free_bytes: 4294967296,
    gpu: {
      name: "RTX 4060",
      memory_used_mib: 512,
      memory_total_mib: 8192
    }
  }
});
assert.deepEqual(parseInferenceEvent('data: {"type":"complete","progress":100,"stage":"完成","phase_timings":{"prepare_runtime_model":0.42,"persistent_worker":68.7,"validation":2.1}}\n\n'), {
  type: "complete",
  progress: 100,
  stage: "完成",
  phase_timings: {
    prepare_runtime_model: 0.42,
    persistent_worker: 68.7,
    validation: 2.1
  }
});
assert.deepEqual(parseInferenceEvent('data: {"type":"complete","progress":100,"stage":"完成","inference_options":{"profile":"fast","tile_step_size":1,"disable_tta":true,"not_on_device":false}}\n\n'), {
  type: "complete",
  progress: 100,
  stage: "完成",
  inference_options: {
    profile: "fast",
    tile_step_size: 1,
    disable_tta: true,
    not_on_device: false
  }
});
assert.equal(getInferenceStatusCopy({ status: "running", progress: 45, stage: "推理中" }), "推理中 · 45%");
assert.equal(getInferenceStatusCopy({ status: "succeeded", mode: "real-nnunetv2", duration_seconds: 386.42 }), "真实 nnUNetv2 推理完成 · 6分26秒");
assert.equal(getInferenceStatusCopy({ status: "succeeded", mode: "cached-real-nnunetv2", duration_seconds: 0.38 }), "缓存推理结果回填完成 · 0秒");
assert.equal(getInferenceStatusCopy({ status: "succeeded", mode: "debug-label-fallback" }), "调试标签回填完成（非真实推理）");
assert.equal(getInferenceStatusCopy({ status: "cancelled", jobId: "cancel0001" }), "推理任务已取消");
assert.equal(getInferenceStatusCopy({ status: "failed", message: "模型配置不完整" }), "模型配置不完整");
assert.equal(getResourceSnapshotCopy({
  phase: "completed",
  timestamp: 100.5,
  device: "cuda",
  disk_free_bytes: 4294967296,
  gpu: { name: "RTX 4060", memory_used_mib: 512, memory_total_mib: 8192 }
}), "设备 cuda · RTX 4060 显存 512/8192 MiB · 磁盘可用 4.00 GB");
assert.equal(getPhaseTimingSummary({
  prepare_runtime_model: 0.42,
  persistent_worker: 68.7,
  validation: 2.1
}), "常驻 worker 68.7秒");
assert.equal(getInferenceResultMeta("real-nnunetv2", "512x512x100"), "512x512x100 · nnUNetv2 真实推理结果");
assert.equal(getInferenceResultMeta("cached-real-nnunetv2", "512x512x100"), "512x512x100 · 历史缓存 nnUNetv2 结果");
assert.equal(getInferenceResultMeta("debug-label-fallback", "512x512x100"), "512x512x100 · 调试标签回填结果（非真实推理）");
assert.equal(getInferenceResultMeta("real-nnunetv2", "512x512x100", { profile: "fast", tile_step_size: 1, disable_tta: true, not_on_device: false }), "512x512x100 · 快速预览 nnUNetv2 结果（需人工复核）");
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

const originalFetch = globalThis.fetch;
let submittedFormData: FormData | undefined;
try {
  globalThis.fetch = async (_input, init) => {
    submittedFormData = init?.body as FormData;
    return new Response(JSON.stringify({
      job_id: "profilejob001",
      mode: "real-nnunetv2",
      cached_result: false,
      inference_profile: "fast",
      inference_options: {
        profile: "fast",
        tile_step_size: 1,
        disable_tta: true,
        not_on_device: false
      }
    }), {
      status: 200,
      headers: { "content-type": "application/json" }
    });
  };
  const createdJob = await createInferenceJob("http://127.0.0.1:8000", new File(["nifti"], "case.nii.gz"), {
    modelId: "abdomen",
    confidenceThreshold: 72,
    postprocess: { removeIslands: true },
    inferenceProfile: "fast"
  });
  assert.equal(submittedFormData?.get("inference_profile"), "fast");
  assert.equal(createdJob.inference_profile, "fast");
  assert.deepEqual(createdJob.inference_options, {
    profile: "fast",
    tile_step_size: 1,
    disable_tta: true,
    not_on_device: false
  });
} finally {
  globalThis.fetch = originalFetch;
}
