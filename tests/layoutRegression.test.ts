import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

const css = readFileSync(new URL("../src/styles.css", import.meta.url), "utf8");

const orthogonalShell = css.match(/\.orthogonal-shell\s*\{([\s\S]*?)\n\}/);
assert.ok(orthogonalShell, "missing .orthogonal-shell rule");
assert.match(orthogonalShell[1], /width:\s*min\(100%,\s*1120px\);/);
assert.match(orthogonalShell[1], /height:\s*100%;/);
assert.match(orthogonalShell[1], /min-height:\s*0;/);

const orthogonalGrid = css.match(/\.orthogonal-grid\s*\{([\s\S]*?)\n\}/);
assert.ok(orthogonalGrid, "missing .orthogonal-grid rule");
assert.match(orthogonalGrid[1], /grid-template-columns:\s*minmax\(320px,\s*1\.05fr\)\s*minmax\(320px,\s*0\.95fr\);/);
assert.match(orthogonalGrid[1], /grid-template-rows:\s*repeat\(2,\s*minmax\(0,\s*1fr\)\);/);
assert.match(orthogonalGrid[1], /height:\s*100%;/);
assert.match(orthogonalGrid[1], /min-width:\s*0;/);
assert.match(orthogonalGrid[1], /min-height:\s*0;/);

const orthoPanel = css.match(/\.ortho-panel\s*\{([\s\S]*?)\n\}/);
assert.ok(orthoPanel, "missing .ortho-panel rule");
assert.match(orthoPanel[1], /min-width:\s*0;/);
assert.match(orthoPanel[1], /min-height:\s*0;/);

const orthoCanvas = css.match(/\.ortho-canvas\s*\{([\s\S]*?)\n\}/);
assert.ok(orthoCanvas, "missing .ortho-canvas rule");
assert.match(orthoCanvas[1], /height:\s*auto;/);
assert.match(orthoCanvas[1], /aspect-ratio:\s*var\(--slice-aspect,\s*1 \/ 1\);/);

const orthoImageStage = css.match(/\.ortho-image-stage\s*\{([\s\S]*?)\n\}/);
assert.ok(orthoImageStage, "missing .ortho-image-stage rule");
assert.match(orthoImageStage[1], /aspect-ratio:\s*var\(--slice-pixel-aspect,\s*var\(--slice-aspect,\s*1 \/ 1\)\);/);

const orthoSource = css.match(/\.ortho-image-stage img\s*\{([\s\S]*?)\n\}/);
assert.ok(orthoSource, "missing .ortho-image-stage img rule");
assert.match(orthoSource[1], /object-fit:\s*contain;/);
assert.match(orthoSource[1], /pointer-events:\s*none;/);
assert.match(orthoSource[1], /user-select:\s*none;/);
assert.match(orthoSource[1], /-webkit-user-drag:\s*none;/);

assert.match(css, /@media \(max-width:\s*700px\)[\s\S]*?\.viewer-frame\s*\{[\s\S]*?height:\s*clamp\(560px,\s*82vh,\s*660px\);/);
assert.match(css, /@media \(max-width:\s*700px\)[\s\S]*?\.orthogonal-grid\s*\{[\s\S]*?grid-template-columns:\s*1fr;/);
assert.match(css, /@media \(max-width:\s*700px\)[\s\S]*?\.ortho-axial\s*\{[\s\S]*?grid-row:\s*auto;/);
