import assert from "node:assert/strict";
import { existsSync, readFileSync } from "node:fs";

const toolPath = new URL("../tools/perf_no_cache_persistent.py", import.meta.url);

assert.equal(existsSync(toolPath), true, "no-cache persistent worker performance tool should exist");

const source = readFileSync(toolPath, "utf8");
for (const required of [
  "SEGMENTATION_PERSISTENT_WORKER",
  "find_cached_prediction",
  "cold_persistent_no_cache",
  "warm_persistent_no_cache",
  "perf_no_cache_persistent_summary.json",
  "--dry-run"
]) {
  assert.equal(source.includes(required), true, `performance tool should include ${required}`);
}
