import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const acceptancePath = new URL("../ACCEPTANCE.md", import.meta.url);
const registryPath = new URL("../reference_cases.example.json", import.meta.url);
const metricsSummaryPath = new URL("../SEGMENTATION_METRICS_SUMMARY.md", import.meta.url);

assert.equal(existsSync(acceptancePath), true, "ACCEPTANCE.md should document the three-goal验收包");
assert.equal(existsSync(registryPath), true, "reference_cases.example.json should show how to register more than AMOS");
assert.equal(existsSync(metricsSummaryPath), true, "SEGMENTATION_METRICS_SUMMARY.md should document reusable segmentation metrics");

const acceptance = readFileSync(acceptancePath, "utf8");
const metricsSummary = readFileSync(metricsSummaryPath, "utf8");
const registry = JSON.parse(readFileSync(registryPath, "utf8")) as {
  samples?: Array<Record<string, unknown>>;
};

for (const required of [
  "CT 可浏览、三正交可联动",
  "器官 label 可点击并展示说明",
  "连接本地 nnUNetv2 后端并回填结果",
  "未缓存真实推理",
  "cached-real-nnunetv2",
  "validation_available",
  "人工验收记录",
  "新权重运行态记录",
  "checkpoint_sha256",
  "persistent_worker",
  "warm_persistent_no_cache",
  "perf_no_cache_persistent_summary.json",
  "4104.567"
]) {
  assert.equal(acceptance.includes(required), true, `ACCEPTANCE.md should mention ${required}`);
}

assert.ok(Array.isArray(registry.samples), "example registry should expose a samples array");
assert.ok(registry.samples.length >= 2, "example registry should include AMOS plus at least one external case");
assert.ok(registry.samples.some((sample) => sample.id === "amos_0117"), "example registry should retain AMOS 0117");
assert.ok(
  registry.samples.some((sample) => sample.id !== "amos_0117" && sample.dataset !== "AMOS22"),
  "example registry should include a non-AMOS reference-case example"
);

for (const required of [
  "Dice",
  "IoU",
  "Pixel Accuracy",
  "Voxel Accuracy",
  "Hausdorff Distance",
  "checkpoint_best.pth",
  "segmentation_metrics_summary.py",
  "new-weight-amos0117-segmentation-metrics.json",
  "validation_summary.json",
  "膀胱",
  "前列腺/子宫"
]) {
  assert.equal(metricsSummary.includes(required), true, `SEGMENTATION_METRICS_SUMMARY.md should mention ${required}`);
}
