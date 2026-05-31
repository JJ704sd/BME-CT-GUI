import assert from "node:assert/strict";
import { defaultOrganLabels } from "../src/data/organDetails.ts";
import { formatQuantificationValue, getLumenAreaInterpretation, getWallThicknessStatus, summarizeSegmentationQuantification, type NiftiMaskVolumeLike } from "../src/imaging/quantification.ts";

function makeMaskVolume(values: number[], spacing = { x: 2, y: 3, z: 4 }): NiftiVolumeLike {
  const image = new Uint8Array(values).buffer;
  return {
    image,
    columns: 4,
    rows: 3,
    slices: 2,
    spacingX: spacing.x,
    spacingY: spacing.y,
    spacingZ: spacing.z,
    datatypeCode: 2,
    littleEndian: true,
    bytesPerVoxel: 1,
    slope: 1,
    intercept: 0
  };
}

const liverLabel = defaultOrganLabels.find((label) => label.id === "liver")!;
const aortaLabel = defaultOrganLabels.find((label) => label.id === "aorta")!;
const stomachLabel = defaultOrganLabels.find((label) => label.id === "stomach")!;
const labels = [liverLabel, aortaLabel, stomachLabel];
const values = Array(24).fill(0);

values[0] = liverLabel.label;
values[1] = liverLabel.label;
values[4] = liverLabel.label;
values[16] = liverLabel.label;
values[5] = aortaLabel.label;
values[6] = aortaLabel.label;

const summary = summarizeSegmentationQuantification(makeMaskVolume(values), labels);
const liver = summary.organs.find((organ) => organ.id === "liver")!;
const aorta = summary.organs.find((organ) => organ.id === "aorta")!;
const stomach = summary.organs.find((organ) => organ.id === "stomach")!;

assert.equal(summary.status, "computed");
assert.deepEqual(summary.spacingMm, { x: 2, y: 3, z: 4 });
assert.equal(liver.status, "computed");
assert.equal(liver.voxelCount, 4);
assert.equal(liver.volumeMl, 0.096);
assert.deepEqual(liver.bboxMm, { x: 4, y: 6, z: 8 });
assert.equal(liver.maxAxialAreaMm2, 18);
assert.equal(liver.estimatedLengthMm, 8);
assert.equal(liver.maxDiameterMm, 8);
assert.equal(aorta.maxAxialAreaMm2, 12);
assert.equal(aorta.lumenAreaInterpretation, "最大轴向截面积可作为血管管腔截面积近似。");
assert.equal(stomach.status, "empty");
assert.equal(stomach.volumeMl, null);
assert.equal(getLumenAreaInterpretation("stomach"), "当前为整体器官截面积估算，不等同于真实管腔截面积。");
assert.equal(getWallThicknessStatus("stomach"), "当前标签未区分壁/腔，暂不输出壁厚数值。");
assert.equal(formatQuantificationValue(1421.345, "ml"), "1421.3 ml");
assert.equal(formatQuantificationValue(null, "ml"), "—");

const unavailable = summarizeSegmentationQuantification({ ...makeMaskVolume(values), spacingZ: 0 }, labels);
assert.equal(unavailable.status, "unavailable");
assert.equal(unavailable.organs.every((organ) => organ.status === "unavailable"), true);

const empty = summarizeSegmentationQuantification(makeMaskVolume(Array(24).fill(0)), labels);
assert.equal(empty.status, "empty");
assert.equal(empty.organs.every((organ) => organ.status === "empty"), true);
