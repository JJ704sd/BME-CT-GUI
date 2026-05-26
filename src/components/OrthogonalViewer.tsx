import type { CSSProperties, PointerEvent, WheelEvent } from "react";
import { useEffect, useLayoutEffect, useMemo, useRef, useState } from "react";
import type { OrganLabel } from "../data/organDetails";
import type { Orientation, VoxelCoord } from "../imaging/voxelMapping";
import {
  clientPointToSlicePoint,
  getCrosshairPercent,
  getOrientationDisplayAspect,
  getOrientationDisplayRatio,
  getOrientationDimensions,
  getSliceRenderKey,
  getSliceIndexForOrientation,
  slicePointToVoxelCoord
} from "../imaging/voxelMapping";
import type { NiftiVolumeLike } from "../imaging/sliceRenderer";
import { getLabelAtVoxel, getVoxelValue, renderNiftiSliceToDataUrl } from "../imaging/sliceRenderer";
import { shouldUpdateVoxelCoord } from "../viewerLogic";

type CompareMode = "split" | "overlay" | "side" | "difference";

type OrthogonalViewerProps = {
  sourceVolume: NiftiVolumeLike;
  maskVolume?: NiftiVolumeLike;
  coord: VoxelCoord;
  opacity: number;
  compareMode: CompareMode;
  visibleLabels: Set<number>;
  labels: OrganLabel[];
  sourceName: string;
  resultName?: string;
  onCoordChange: (coord: VoxelCoord) => void;
  onOrganPick: (label: number, coord: VoxelCoord) => void;
};

const panels: { orientation: Orientation; title: string; subtitle: string }[] = [
  { orientation: "axial", title: "Axial", subtitle: "横断面" },
  { orientation: "sagittal", title: "Sagittal", subtitle: "矢状面" },
  { orientation: "coronal", title: "Coronal", subtitle: "冠状面" }
];

function stepCoord(orientation: Orientation, coord: VoxelCoord, delta: number, volume: NiftiVolumeLike): VoxelCoord {
  if (orientation === "sagittal") {
    return { ...coord, x: Math.max(0, Math.min(volume.columns - 1, coord.x + delta)) };
  }
  if (orientation === "coronal") {
    return { ...coord, y: Math.max(0, Math.min(volume.rows - 1, coord.y + delta)) };
  }
  return { ...coord, z: Math.max(0, Math.min(volume.slices - 1, coord.z + delta)) };
}

function useRafCoalescedCoord(coord: VoxelCoord) {
  const [renderCoord, setRenderCoord] = useState(coord);
  const latestCoordRef = useRef(coord);
  const frameRef = useRef<number | null>(null);

  useEffect(() => {
    latestCoordRef.current = coord;
    if (frameRef.current !== null) return;

    frameRef.current = requestAnimationFrame(() => {
      frameRef.current = null;
      const latestCoord = latestCoordRef.current;
      setRenderCoord((current) => shouldUpdateVoxelCoord(current, latestCoord) ? latestCoord : current);
    });
  }, [coord.x, coord.y, coord.z]);

  useEffect(() => () => {
    if (frameRef.current !== null) {
      cancelAnimationFrame(frameRef.current);
    }
  }, []);

  return renderCoord;
}

function Panel(props: OrthogonalViewerProps & { orientation: Orientation; title: string; subtitle: string }) {
  const dimensions = getOrientationDimensions(props.orientation, props.sourceVolume);
  const displayAspect = getOrientationDisplayAspect(props.orientation, props.sourceVolume);
  const displayRatio = getOrientationDisplayRatio(props.orientation, props.sourceVolume);
  const stageRef = useRef<HTMLDivElement>(null);
  const [stageRatio, setStageRatio] = useState(displayRatio);
  const renderCoord = useRafCoalescedCoord(props.coord);
  const sourceSliceKey = getSliceRenderKey(props.orientation, renderCoord, props.sourceVolume);
  const maskSliceKey = props.maskVolume ? getSliceRenderKey(props.orientation, renderCoord, props.maskVolume) : "";
  const sourceSrc = useMemo(
    () => renderNiftiSliceToDataUrl(props.sourceVolume, renderCoord, "intensity", props.orientation),
    [props.sourceVolume, props.orientation, sourceSliceKey]
  );
  const maskSrc = useMemo(
    () => props.maskVolume ? renderNiftiSliceToDataUrl(props.maskVolume, renderCoord, "mask", props.orientation, props.visibleLabels) : "",
    [props.maskVolume, props.orientation, props.visibleLabels, maskSliceKey]
  );
  useLayoutEffect(() => {
    const stage = stageRef.current;
    if (!stage) return;
    const updateStageRatio = () => {
      const rect = stage.getBoundingClientRect();
      if (rect.width > 0 && rect.height > 0) {
        setStageRatio(rect.width / rect.height);
      }
    };
    updateStageRatio();
    const observer = new ResizeObserver(updateStageRatio);
    observer.observe(stage);
    return () => observer.disconnect();
  }, [displayRatio]);

  const crosshair = getCrosshairPercent(props.orientation, props.coord, props.sourceVolume, stageRatio, displayRatio);
  const slice = getSliceIndexForOrientation(props.orientation, props.coord) + 1;
  const sliceTotal = props.orientation === "sagittal" ? props.sourceVolume.columns : props.orientation === "coronal" ? props.sourceVolume.rows : props.sourceVolume.slices;

  function updateCoordFromPointer(event: PointerEvent<HTMLDivElement>, pickOrgan: boolean) {
    event.preventDefault();
    event.stopPropagation();
    if (pickOrgan && !event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.setPointerCapture(event.pointerId);
    }
    const stage = stageRef.current;
    const rect = (stage ?? event.currentTarget).getBoundingClientRect();
    const point = clientPointToSlicePoint(event.clientX, event.clientY, rect, dimensions, displayRatio);
    if (!point) return;
    const nextCoord = slicePointToVoxelCoord(props.orientation, point, props.coord, props.sourceVolume);
    if (shouldUpdateVoxelCoord(props.coord, nextCoord)) {
      props.onCoordChange(nextCoord);
    }
    if (pickOrgan && props.maskVolume) {
      const label = getLabelAtVoxel(props.maskVolume, nextCoord);
      if (label > 0) props.onOrganPick(label, nextCoord);
    }
  }

  function handleWheel(event: WheelEvent<HTMLDivElement>) {
    event.preventDefault();
    event.stopPropagation();
    props.onCoordChange(stepCoord(props.orientation, props.coord, event.deltaY > 0 ? 1 : -1, props.sourceVolume));
  }

  return (
    <div className={`ortho-panel ortho-${props.orientation}`}>
      <div className="ortho-title">
        <strong>{props.title}</strong>
        <span>{props.subtitle} · {slice}/{sliceTotal}</span>
      </div>
      <div
        className={`ortho-canvas compare-${props.compareMode} ${props.maskVolume ? "has-mask" : "no-mask"}`}
        style={{ "--slice-aspect": displayAspect, "--slice-pixel-aspect": `${displayRatio} / 1`, "--mask-opacity": props.opacity / 100 } as CSSProperties}
        onPointerDown={(event) => updateCoordFromPointer(event, true)}
        onPointerMove={(event) => {
          if (event.buttons === 1 || event.currentTarget.hasPointerCapture(event.pointerId)) updateCoordFromPointer(event, false);
        }}
        onPointerUp={(event) => {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
          }
        }}
        onPointerCancel={(event) => {
          if (event.currentTarget.hasPointerCapture(event.pointerId)) {
            event.currentTarget.releasePointerCapture(event.pointerId);
          }
        }}
        onWheel={handleWheel}
      >
        <div className="ortho-image-stage" ref={stageRef}>
          <img className="ortho-source" src={sourceSrc} alt={`${props.sourceName} ${props.title}`} draggable={false} />
          {props.maskVolume && maskSrc ? <img className="ortho-mask" src={maskSrc} alt={`${props.resultName ?? "mask"} ${props.title}`} draggable={false} /> : null}
          <span className="ortho-crosshair ortho-crosshair-x" style={{ left: `${crosshair.left}%`, top: `${crosshair.y}%`, width: `${crosshair.width}%` }} />
          <span className="ortho-crosshair ortho-crosshair-y" style={{ left: `${crosshair.x}%`, top: `${crosshair.top}%`, height: `${crosshair.height}%` }} />
        </div>
      </div>
    </div>
  );
}

export function OrthogonalViewer(props: OrthogonalViewerProps) {
  const label = props.maskVolume ? getLabelAtVoxel(props.maskVolume, props.coord) : 0;
  const labelName = props.labels.find((item) => item.label === label)?.nameZh ?? (label > 0 ? `Label ${label}` : "背景");
  const hu = Math.round(getVoxelValue(props.sourceVolume, props.coord));

  return (
    <div className="orthogonal-viewer">
      <div className="orthogonal-grid">
        {panels.map((panel) => <Panel key={panel.orientation} {...props} {...panel} />)}
      </div>
      <div className="voxel-readout">
        <span>Voxel ({props.coord.x}, {props.coord.y}, {props.coord.z})</span>
        <span>HU {hu}</span>
        <span>{label > 0 ? `${labelName} · Label ${label}` : "背景"}</span>
      </div>
    </div>
  );
}
