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
import { createInferenceEventSource, DEFAULT_INFERENCE_EVENT_SOURCE_BASE_DELAY_MS, DEFAULT_INFERENCE_EVENT_SOURCE_MAX_DELAY_MS, DEFAULT_INFERENCE_EVENT_SOURCE_MAX_RETRIES } from "../src/inference/createInferenceEventSource.ts";
import { buildOrganLayersFromLabels } from "../src/organLayerLogic.ts";
import { DEFAULT_REFERENCE_CASES, getReferenceCaseOriginalUrl, normalizeReferenceCases } from "../src/referenceCases.ts";
import { getVoxelCoordDragCommit, getVoxelCoordForSelectedSliceSync, shouldUpdateVoxelCoord } from "../src/viewerLogic.ts";

const mainSource = readFileSync(new URL("../src/main.tsx", import.meta.url), "utf8");
const inferenceClientSource = readFileSync(new URL("../src/inference/inferenceClient.ts", import.meta.url), "utf8");
const inferenceEventSourceSource = readFileSync(new URL("../src/inference/createInferenceEventSource.ts", import.meta.url), "utf8");
const orthogonalViewerSource = readFileSync(new URL("../src/components/OrthogonalViewer.tsx", import.meta.url), "utf8");
const stylesSource = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");
const exportReportSource = readFileSync(new URL("../src/report/exportReport.ts", import.meta.url), "utf8");

for (const copy of ["载入 AMOS " + "样例", "本地 AMOS " + "样例", "AMOS CT " + "样例"]) {
  assert.equal(mainSource.includes(copy), false, `UI should not use AMOS-only copy: ${copy}`);
}
assert.equal(mainSource.includes("载入参考病例"), true, "UI should expose built-in data as a reference case");
assert.equal(mainSource.includes("内置参考病例"), true, "UI should distinguish the built-in reference case from arbitrary imported CT cases");
assert.equal(mainSource.includes("api/samples/amos_0117/original"), false, "UI should load reference cases through sample metadata, not a hard-coded AMOS URL");
assert.equal(mainSource.includes("质量推理"), true, "UI should expose the default quality inference profile");
assert.equal(mainSource.includes("快速预览"), true, "UI should expose the fast preview inference profile");
assert.equal(mainSource.includes("需人工复核"), true, "UI should warn that fast preview results require review");
assert.equal(mainSource.includes("inferenceTimeline"), true, "front-end should keep structured inference timeline state for bottom progress");
assert.equal(mainSource.includes("appendInferenceTimelineEntry"), true, "SSE progress and terminal events should append structured timeline entries");
assert.equal(mainSource.includes("inferenceStartedAt"), true, "front-end should track inference start time for elapsed runtime copy");
assert.equal(mainSource.includes("inference-progress-rail"), true, "bottom console should render a structured inference progress rail");
assert.equal(mainSource.includes("inference-progress-track"), true, "bottom console should render a real progressbar track from SSE progress");
assert.equal(mainSource.includes("parsed.log_tail"), true, "failed SSE events should preserve backend log_tail for review");
assert.equal(mainSource.includes("parsed.heartbeat"), true, "SSE handler should distinguish heartbeat events from normal progress");
assert.equal(mainSource.includes("setInferenceStartedAt"), true, "heartbeat events should sync frontend elapsed timer with backend reality");
assert.equal(mainSource.includes("createInferenceEventSource"), true, "SSE handler should route through createInferenceEventSource factory with retry support (B4)");
assert.equal(mainSource.includes("inferenceStatusRef"), true, "SSE onmessage should consult a ref-mirrored status so cancel state takes priority (B2)");
assert.equal(mainSource.includes('inferenceStatusRef.current.status === "cancelled"'), true, "cancel state must short-circuit incoming SSE progress events (B2)");
assert.equal(mainSource.includes("parsed.heartbeat && parsed.progress === 0"), true, "heartbeat with no progress must not drop the progress rail to 0% (B1)");
assert.equal(inferenceEventSourceSource.includes("onretry"), true, "createInferenceEventSource must expose onretry hook for retry visibility (B4)");
assert.equal(inferenceEventSourceSource.includes("retryCount"), true, "createInferenceEventSource must expose retryCount for visibility (B4)");
assert.equal(inferenceEventSourceSource.includes("onfatal"), true, "createInferenceEventSource must call onfatal after retries are exhausted (B4)");
assert.equal(inferenceEventSourceSource.includes("Math.min(maxDelayMs, baseDelayMs * Math.pow(2, retryCount))"), true, "createInferenceEventSource must use exponential backoff (B4)");
assert.equal(inferenceEventSourceSource.includes("maxRetries ?? DEFAULT_INFERENCE_EVENT_SOURCE_MAX_RETRIES"), true, "createInferenceEventSource must cap retries at 3 by default (B4)");
assert.equal(DEFAULT_INFERENCE_EVENT_SOURCE_MAX_RETRIES, 3, "default SSE retry cap should be 3");
assert.equal(DEFAULT_INFERENCE_EVENT_SOURCE_BASE_DELAY_MS, 200, "default SSE base retry delay should be 200ms");
assert.equal(DEFAULT_INFERENCE_EVENT_SOURCE_MAX_DELAY_MS, 2000, "default SSE max retry delay should be 2s");
assert.equal(mainSource.includes("[inference] labelFile"), false, "front-end should not log uploaded label filenames");
assert.equal(inferenceClientSource.includes("console.log"), false, "inference client should not log uploaded filenames or label presence");
assert.equal(mainSource.includes("const idleProgress = inferenceTimeline.length ? clampedProgress : 0"), true, "waiting progress rail should not show the previous 100% baseline before any inference event");
for (const mockCaseId of ["Case_FLARE_024", "Case_LUNG_112", "Case_PANC_038"]) {
  assert.equal(mainSource.includes(mockCaseId), false, `top case selector should not expose mock case ${mockCaseId}`);
}
for (const realCaseId of ["AMOS_0117", "FLARE22_Tr_0009"]) {
  assert.equal(mainSource.includes(realCaseId), true, `top case selector should expose local real case ${realCaseId}`);
}
assert.equal(orthogonalViewerSource.includes("useRafCoalescedCoord"), true, "orthogonal slice images should coalesce fast cursor moves before rerendering");
assert.equal(orthogonalViewerSource.includes("latestSliceKeyRef"), true, "orthogonal panels should skip image render state updates when their fixed slice key is unchanged");
assert.equal(orthogonalViewerSource.includes("activePointerOrientation"), true, "orthogonal viewer should know which panel is being dragged");
assert.equal(orthogonalViewerSource.includes("interactiveRenderMode"), true, "orthogonal viewer should keep all three views live with a lightweight drag render mode");
assert.equal(orthogonalViewerSource.includes("deferImageUpdates"), false, "orthogonal panels should not freeze non-active views while dragging");
assert.equal(mainSource.includes("setSelectedSlice(getSelectedSliceForVoxelCoord"), false, "cursor movement should not synchronously rerender axial previews on every pointer event");
assert.equal(mainSource.includes("scheduleVoxelCoordChange"), true, "orthogonal cursor movement should coalesce voxel state updates before rerendering App");
assert.equal(mainSource.includes("setVoxelCoord(clampedCoord);"), false, "orthogonal cursor movement should not commit voxel state synchronously on every pointer event");
assert.equal(mainSource.includes("scheduleSelectedSliceAfterVoxelIdle"), true, "sagittal/coronal drags should defer expensive selected-slice preview sync until cursor movement idles");
assert.equal(mainSource.includes("commitSelectedSliceFromVoxel(commit.selectedSlice);"), false, "coalesced voxel frames should not immediately rerender selected-slice previews");
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
assert.deepEqual(
  getVoxelCoordForSelectedSliceSync({ x: 4, y: 8, z: 20 }, 13, volume, "voxel"),
  { x: 4, y: 8, z: 20 },
  "voxel-driven selected-slice sync should not rewind a newer sagittal/coronal drag z coordinate"
);
assert.deepEqual(
  getVoxelCoordForSelectedSliceSync({ x: 4, y: 8, z: 20 }, 13, volume, "slice"),
  { x: 4, y: 8, z: 12 },
  "slider/footer selected-slice changes should still move the axial coordinate"
);
assert.deepEqual(
  getVoxelCoordDragCommit({ x: 4, y: 8, z: 12 }, { x: 12, y: -4, z: 42 }, volume),
  {
    coord: { x: 9, y: 0, z: 29 },
    selectedSlice: 30
  },
  "orthogonal drags should clamp once and derive the selected axial slice from the coalesced voxel coordinate"
);
assert.equal(
  getVoxelCoordDragCommit({ x: 4, y: 8, z: 12 }, { x: 4, y: 8, z: 12 }, volume),
  null,
  "unchanged orthogonal cursor positions should not schedule a React state update"
);

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
assert.deepEqual(parseInferenceEvent('data: {"type":"complete","progress":100,"stage":"服务器 5-fold soft ensemble 推理结果已生成","runtime_target":"server","validation":{"status":"review","sample_id":"case_001","mean_dice":0.82,"accepted":false},"phase_timings":{"server_fold_predict":240.5,"server_ensemble":18.2,"server_validation":6.4},"resource_latest":{"phase":"completed","device":"cuda","gpu":{"name":"NVIDIA A100","memory_used_mib":20340,"memory_total_mib":40960}}}\n\n'), {
  type: "complete",
  progress: 100,
  stage: "服务器 5-fold soft ensemble 推理结果已生成",
  runtime_target: "server",
  validation: {
    status: "review",
    sample_id: "case_001",
    mean_dice: 0.82,
    accepted: false
  },
  phase_timings: {
    server_fold_predict: 240.5,
    server_ensemble: 18.2,
    server_validation: 6.4
  },
  resource_latest: {
    phase: "completed",
    device: "cuda",
    gpu: {
      name: "NVIDIA A100",
      memory_used_mib: 20340,
      memory_total_mib: 40960
    }
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
assert.deepEqual(parseInferenceEvent('data: {"type":"progress","progress":20,"stage":"常驻 nnUNetv2 worker 推理中","heartbeat":true,"elapsed_seconds":45.123}\n\n'), {
  type: "progress",
  progress: 20,
  stage: "常驻 nnUNetv2 worker 推理中",
  heartbeat: true,
  elapsed_seconds: 45.123
});
assert.deepEqual(parseInferenceEvent('data: {"type":"progress","progress":20,"stage":"nnUNetv2 命令运行中"}\n\n'), {
  type: "progress",
  progress: 20,
  stage: "nnUNetv2 命令运行中"
});

{
  const e2eEvents = [
    'data: {"type":"progress","progress":8,"stage":"任务已提交到本地 nnUNetv2"}\n\n',
    'data: {"type":"progress","progress":14,"stage":"已准备项目指定训练权重"}\n\n',
    'data: {"type":"progress","progress":20,"stage":"常驻 nnUNetv2 worker 推理中"}\n\n',
    'data: {"type":"progress","progress":20,"stage":"常驻 nnUNetv2 worker 推理中","heartbeat":true,"elapsed_seconds":30.5}\n\n',
    'data: {"type":"progress","progress":20,"stage":"常驻 nnUNetv2 worker 推理中","heartbeat":true,"elapsed_seconds":61.0}\n\n',
    'data: {"type":"progress","progress":90,"stage":"整理 nnUNetv2 输出"}\n\n',
    'data: {"type":"complete","progress":100,"stage":"真实 nnUNetv2 推理结果已生成","duration_seconds":120.5,"result_size_bytes":141569,"phase_timings":{"persistent_worker":118.2,"collect_result":0.3},"resource_latest":{"phase":"completed","gpu":{"name":"RTX 4060","memory_used_mib":7500,"memory_total_mib":8192}}}\n\n',
  ];
  const parsed = e2eEvents.map((raw) => parseInferenceEvent(raw));
  const nonHeartbeatProgress = parsed.filter((e) => e.type === "progress" && !e.heartbeat);
  const heartbeats = parsed.filter((e) => e.type === "progress" && e.heartbeat);
  const complete = parsed.filter((e) => e.type === "complete");

  assert.equal(nonHeartbeatProgress.length, 4, "E2E should have 4 non-heartbeat progress events");
  assert.equal(heartbeats.length, 2, "E2E should have 2 heartbeat events");
  assert.equal(complete.length, 1, "E2E should have 1 complete event");
  assert.equal(heartbeats[0].elapsed_seconds, 30.5, "first heartbeat should report elapsed_seconds");
  assert.equal(complete[0].duration_seconds, 120.5, "complete event should report duration");
  assert.equal(complete[0].result_size_bytes, 141569, "complete event should report result size");
  assert.equal(complete[0].phase_timings?.persistent_worker, 118.2, "complete event should include phase timings");
  assert.equal(complete[0].resource_latest?.gpu?.name, "RTX 4060", "complete event should include resource snapshot");

  const statusFlow = parsed.map((e) => {
    if (e.type === "error") return "failed";
    if (e.type === "complete") return "succeeded";
    return "running";
  });
  assert.deepEqual(statusFlow, ["running", "running", "running", "running", "running", "running", "succeeded"]);
}

{
  const failEvents = [
    'data: {"type":"progress","progress":20,"stage":"推理中"}\n\n',
    'data: {"type":"error","message":"CUDA out of memory","log_tail":"RuntimeError: CUDA out of memory"}\n\n',
  ];
  const parsed = failEvents.map((raw) => parseInferenceEvent(raw));
  assert.equal(parsed[0].type, "progress");
  assert.equal(parsed[1].type, "error");
  assert.equal(parsed[1].message, "CUDA out of memory");
  assert.equal(parsed[1].log_tail, "RuntimeError: CUDA out of memory");
}

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
    inferenceProfile: "fast",
    runtimeTarget: "server",
    labelTaxonomy: "AMOS22"
  });
  assert.equal(submittedFormData?.get("inference_profile"), "fast");
  assert.equal(submittedFormData?.get("runtime_target"), "server");
  assert.equal(submittedFormData?.get("label_taxonomy"), "AMOS22");
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

// --- IoU coverage in inference client / exported HTML report ---
assert.equal(inferenceClientSource.includes("mean_iou"), true, "ValidationSummary type should expose mean_iou");
assert.equal(inferenceClientSource.includes("foreground_iou"), true, "ValidationSummary type should expose foreground_iou");
assert.equal(inferenceClientSource.includes("union_voxels"), true, "per-label validation should expose union_voxels for IoU computation");
for (const key of ["mean_iou", "min_iou", "foreground_iou"]) {
  assert.equal(
    inferenceClientSource.includes(`"${key}"`),
    true,
    `normalizeValidation whitelist should include ${key}`
  );
}
assert.equal(exportReportSource.includes("mean_iou"), true, "HTML report should render mean_iou");
assert.equal(exportReportSource.includes("foreground_iou"), true, "HTML report should render foreground_iou");
assert.equal(exportReportSource.includes("平均 IoU"), true, "HTML report should label mean IoU in Chinese");
assert.equal(exportReportSource.includes("前景 IoU"), true, "HTML report should label foreground IoU in Chinese");
assert.equal(exportReportSource.includes("metricBarHtml(l.iou"), true, "per-label table should render IoU column with bar visualization");
assert.equal(exportReportSource.includes("--accent:"), true, "HTML report should use a unified accent color variable for visual coherence");
assert.equal(exportReportSource.includes("metric-card.bar-good"), true, "HTML report should color-code metric cards by score tier");
assert.equal(exportReportSource.includes(".metric-bar-fill"), true, "HTML report should render inline metric bar visualizations");

// --- Quality assessment coverage: pixel accuracy + HD / HD95 / ASD ---
for (const key of [
  "mean_pixel_accuracy",
  "min_pixel_accuracy",
  "foreground_pixel_accuracy",
  "mean_asd",
  "max_asd",
  "foreground_asd",
  "mean_hd",
  "max_hd",
  "foreground_hd",
  "mean_hd95",
  "max_hd95",
  "foreground_hd95"
] as const) {
  assert.equal(inferenceClientSource.includes(`${key}?:`), true, `ValidationSummary type should declare ${key}`);
  assert.equal(
    inferenceClientSource.includes(`"${key}"`),
    true,
    `normalizeValidation whitelist should include ${key}`
  );
}
for (const key of ["pixel_accuracy", "asd", "hd", "hd95"] as const) {
  assert.equal(
    inferenceClientSource.includes(`metric.${key}`),
    true,
    `normalizeValidation should parse per-label ${key}`
  );
}
assert.equal(inferenceClientSource.includes("surface_distance_unit"), true, "ValidationSummary should propagate surface distance unit");
assert.equal(inferenceClientSource.includes("raw.spacing"), true, "ValidationSummary should propagate NIfTI spacing array");
const completeWithDistance = parseInferenceEvent(
  'data: {"type":"complete","progress":100,"stage":"完成","validation":{"status":"review","sample_id":"case_42","mean_dice":0.83,"min_dice":0.61,"foreground_dice":0.91,"mean_iou":0.71,"min_iou":0.45,"foreground_iou":0.84,"pixel_accuracy":0.95,"mean_pixel_accuracy":0.74,"min_pixel_accuracy":0.62,"foreground_pixel_accuracy":0.96,"mean_asd":1.42,"max_asd":4.21,"foreground_asd":1.18,"mean_hd":8.55,"max_hd":15.43,"foreground_hd":7.12,"mean_hd95":3.01,"max_hd95":5.27,"foreground_hd95":2.85,"surface_distance_unit":"mm","spacing":[1.0,1.0,2.0],"labels":[{"label":1,"name":"liver","dice":0.9,"iou":0.81,"pixel_accuracy":0.96,"asd":0.42,"hd":2.1,"hd95":1.4,"prediction_voxels":120,"reference_voxels":115,"intersection_voxels":108,"union_voxels":127}]}}\n\n'
) as Extract<ReturnType<typeof parseInferenceEvent>, { type: "complete" }>;
assert.equal(completeWithDistance.type, "complete");
const distanceValidation = completeWithDistance.validation;
assert.equal(distanceValidation?.pixel_accuracy, 0.95);
assert.equal(distanceValidation?.mean_pixel_accuracy, 0.74);
assert.equal(distanceValidation?.foreground_pixel_accuracy, 0.96);
assert.equal(distanceValidation?.mean_asd, 1.42);
assert.equal(distanceValidation?.max_asd, 4.21);
assert.equal(distanceValidation?.foreground_asd, 1.18);
assert.equal(distanceValidation?.mean_hd, 8.55);
assert.equal(distanceValidation?.max_hd, 15.43);
assert.equal(distanceValidation?.foreground_hd, 7.12);
assert.equal(distanceValidation?.mean_hd95, 3.01);
assert.equal(distanceValidation?.max_hd95, 5.27);
assert.equal(distanceValidation?.foreground_hd95, 2.85);
assert.equal(distanceValidation?.surface_distance_unit, "mm");
assert.deepEqual(distanceValidation?.spacing, [1.0, 1.0, 2.0]);
assert.equal(distanceValidation?.labels?.[0].pixel_accuracy, 0.96);
assert.equal(distanceValidation?.labels?.[0].asd, 0.42);
assert.equal(distanceValidation?.labels?.[0].hd, 2.1);
assert.equal(distanceValidation?.labels?.[0].hd95, 1.4);

assert.equal(exportReportSource.includes("总准确率"), true, "HTML report should label overall pixel accuracy");
assert.equal(exportReportSource.includes("平均类别准确率"), true, "HTML report should label mean class accuracy");
assert.equal(exportReportSource.includes("前景准确率"), true, "HTML report should label foreground accuracy");
assert.equal(exportReportSource.includes("平均 HD"), true, "HTML report should label mean HD");
assert.equal(exportReportSource.includes("最大 HD"), true, "HTML report should label max HD");
assert.equal(exportReportSource.includes("平均 HD95"), true, "HTML report should label mean HD95");
assert.equal(exportReportSource.includes("平均 ASD"), true, "HTML report should label mean ASD");
assert.equal(exportReportSource.includes("ASD (mm)"), true, "per-label table should show ASD column with mm unit");
assert.equal(exportReportSource.includes("HD95 (mm)"), true, "per-label table should show HD95 column with mm unit");
assert.equal(exportReportSource.includes("HD (mm)"), true, "per-label table should show HD column with mm unit");
assert.equal(exportReportSource.includes("像素准确率"), true, "per-label table should have a pixel accuracy column header");
for (const metric of ["metricBarHtml(l.pixel_accuracy", "metricBarHtml(l.asd", "metricBarHtml(l.hd95", "metricBarHtml(l.hd"] as const) {
  assert.equal(exportReportSource.includes(metric), true, `per-label row should call ${metric}`);
}
for (const card of [
  "metricCard(\"总准确率\"",
  "metricCard(\"平均类别准确率\"",
  "metricCard(\"前景准确率\"",
  "metricCard(\"平均 HD\"",
  "metricCard(\"最大 HD\"",
  "metricCard(\"前景 HD\"",
  "metricCard(\"平均 HD95\"",
  "metricCard(\"最大 HD95\"",
  "metricCard(\"前景 HD95\"",
  "metricCard(\"平均 ASD\"",
  "metricCard(\"最大 ASD\"",
  "metricCard(\"前景 ASD\""
] as const) {
  assert.equal(exportReportSource.includes(card), true, `HTML report should render ${card}`);
}
assert.equal(exportReportSource.includes("dist-good"), true, "HTML report should style distance bars");
assert.equal(exportReportSource.includes("pix-good"), true, "HTML report should style pixel accuracy bars");

// --- 6-05 clinical-paper report style: cover, exec-summary, toc, formula-tip, dist-chart, captions, footnotes, section-num/en ---
for (const className of [
  "cover",
  "exec-summary",
  "toc",
  "formula-tip",
  "dist-chart",
  "table-caption",
  "footnotes",
  "section-num",
  "section-en"
] as const) {
  assert.equal(
    exportReportSource.includes(`.${className}`),
    true,
    `HTML report should keep the 6-05 clinical-paper class .${className}`
  );
}
// --- 6-04 visual+info layer: legend / historical-banner / spacing-bar / severity-{high,medium,low} / organ-list-details ---
// (remap-banner CSS block was removed on 2026-06-07 — its visual is now expressed via .tag.tag-progress and inline summary copy)
for (const className of [
  "legend",
  "historical-banner",
  "spacing-bar",
  "severity-high",
  "severity-medium",
  "severity-low",
  "organ-list-details"
] as const) {
  assert.equal(
    exportReportSource.includes(`.${className}`),
    true,
    `HTML report should keep the 6-04 visual layer class .${className}`
  );
}
assert.equal(exportReportSource.includes("distBarPercent"), true, "HTML report should invert distance bars so smaller is better");
