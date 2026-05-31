import { useEffect, useMemo, useRef, useState, type ChangeEvent, type CSSProperties, type DragEvent, type PointerEvent } from "react";
import { createRoot } from "react-dom/client";
import * as nifti from "nifti-reader-js";
import {
  Activity,
  AlertTriangle,
  BadgeCheck,
  BarChart3,
  BrainCircuit,
  CheckCircle2,
  ChevronDown,
  CircleDot,
  ClipboardCheck,
  Columns2,
  Database,
  Download,
  Eye,
  EyeOff,
  FileStack,
  FileText,
  FolderOpen,
  Gauge,
  Layers3,
  ListChecks,
  MousePointer2,
  Pause,
  Plus,
  Play,
  RotateCcw,
  ScanLine,
  Settings2,
  SlidersHorizontal,
  Sparkles,
  Stethoscope,
  Target,
  Trash2,
  Upload,
  X,
  ZoomIn
} from "lucide-react";
import demoCtImage from "./assets/demo-abdomen-ct.png";
import { OrthogonalViewer } from "./components/OrthogonalViewer";
import { buildLabelLookup, defaultOrganLabels, getOrganDetail, organDetails as ORGAN_DETAIL_MAP } from "./data/organDetails";
import { exportReport, type ReportFormat } from "./report/exportReport";
import { cancelInferenceJob, createInferenceJob, downloadInferenceResult, fetchModelLabels, getInferenceResultMeta, getInferenceStatusCopy, getPhaseTimingSummary, getResourceSnapshotCopy, parseInferenceEvent, type InferenceOptions, type InferenceProfile, type InferenceStatus, type LabelTaxonomy, type PhaseTimings, type ResourceSnapshot, type RuntimeTarget, type ValidationSummary } from "./inference/inferenceClient";
import { summarizeSegmentationQuantification, formatQuantificationValue } from "./imaging/quantification";
import { renderNiftiSliceToDataUrl as renderOrientedNiftiSliceToDataUrl } from "./imaging/sliceRenderer";
import type { VoxelCoord } from "./imaging/voxelMapping";
import { buildOrganLayersFromLabels, formatOrganScore, getMeanOrganDice, type OrganLayer as Organ, type OrganLayerQuality as QualityState } from "./organLayerLogic";
import { DEFAULT_REFERENCE_CASES, getReferenceCaseOriginalUrl, normalizeReferenceCases, type ReferenceCase } from "./referenceCases";
import { buildCustomCaseId, getAlignmentCaptionCopy, getCustomCasePanelCopy, getDisplayAspectRatio, getRegistrationStatus, getSelectedSliceForVoxelCoord, getSplitPositionFromClientX, getStableSliceWindowStart, getVoxelCoordDragCommit, getVoxelCoordForSelectedSliceSync, shouldUpdateVoxelCoord, volumesShareDisplayGrid, type SelectedSliceSyncSource } from "./viewerLogic";
import "./styles.css";

const API_ENDPOINT = import.meta.env.VITE_API_ENDPOINT || "http://127.0.0.1:8000";

type ViewMode = "CT" | "Mask" | "3D";
type RunState = "idle" | "running" | "complete";
type ModuleId = "项目" | "数据" | "分割" | "评估" | "报告";
type CompareMode = "split" | "overlay" | "side" | "difference";
type UploadRole = "source" | "result" | "label";
type RemovalTarget = "source" | "result" | "session";
type NiftiRenderMode = "intensity" | "mask";
type InferenceTimelineEntry = {
  id: string;
  type: "info" | "progress" | "complete" | "error" | "cancelled";
  progress?: number;
  stage: string;
  message?: string;
  at: number;
};

type NiftiVolume = {
  image: ArrayBuffer;
  columns: number;
  rows: number;
  slices: number;
  spacingX: number;
  spacingY: number;
  spacingZ: number;
  datatypeCode: number;
  datatype: string;
  littleEndian: boolean;
  bytesPerVoxel: number;
  slope: number;
  intercept: number;
  spacing: string;
};

type LoadedImage = {
  src: string;
  name: string;
  kind: "Demo" | "Image" | "NIfTI";
  meta: string;
  dimensions?: string;
  sizeText?: string;
  format?: string;
  volume?: NiftiVolume;
  sliceIndex?: number;
  file?: File;
};

type CaseItem = {
  id: string;
  sex: string;
  age: number;
  phase: string;
  caseSummary?: string;
  slices: number;
  target: string;
  demoImage: string;
  imageName: string;
  imageMeta: string;
  organs: Organ[];
  referenceCaseId?: string;
  custom?: boolean;
  sourceImage?: LoadedImage;
  resultImage?: LoadedImage | null;
};

type Measurement = {
  id: number;
  label: string;
  x: number;
  y: number;
  hu: number;
  diameter: string;
  slice: number;
};

type ReportState = {
  draftSaved: boolean;
  reviewQueued: boolean;
  exportCount: number;
  lastExport: string;
};

const organSets = {
  abdomen: [
    { id: "liver", name: "肝脏", color: "#4fd1a5", score: 96.8, volume: "1421 ml", visible: true, quality: "accepted" },
    { id: "pancreas", name: "胰腺", color: "#f4b95f", score: 91.4, volume: "72 ml", visible: true, quality: "accepted" },
    { id: "stomach", name: "胃", color: "#7cc7ff", score: 93.1, volume: "318 ml", visible: true, quality: "review" },
    { id: "colon", name: "结肠", color: "#ef8aa8", score: 89.7, volume: "514 ml", visible: true, quality: "review" },
    { id: "gallbladder", name: "胆囊", color: "#a5e567", score: 88.9, volume: "31 ml", visible: false, quality: "review" }
  ] satisfies Organ[],
  lung: [
    { id: "right-lung", name: "右肺", color: "#4fd1a5", score: 95.2, volume: "2520 ml", visible: true, quality: "accepted" },
    { id: "left-lung", name: "左肺", color: "#7cc7ff", score: 94.7, volume: "2388 ml", visible: true, quality: "accepted" },
    { id: "airway", name: "气管树", color: "#f4b95f", score: 90.6, volume: "41 ml", visible: true, quality: "review" },
    { id: "vessel", name: "肺血管", color: "#ef8aa8", score: 88.5, volume: "126 ml", visible: true, quality: "review" },
    { id: "nodule", name: "肺结节", color: "#a5e567", score: 86.9, volume: "4.8 ml", visible: false, quality: "review" }
  ] satisfies Organ[],
  pancreas: [
    { id: "liver", name: "肝脏", color: "#4fd1a5", score: 95.9, volume: "1368 ml", visible: true, quality: "accepted" },
    { id: "pancreas", name: "胰腺", color: "#f4b95f", score: 92.6, volume: "83 ml", visible: true, quality: "accepted" },
    { id: "stomach", name: "胃", color: "#7cc7ff", score: 90.2, volume: "286 ml", visible: true, quality: "review" },
    { id: "spleen", name: "脾脏", color: "#ef8aa8", score: 91.5, volume: "178 ml", visible: true, quality: "review" },
    { id: "gallbladder", name: "胆囊", color: "#a5e567", score: 89.4, volume: "38 ml", visible: true, quality: "review" }
  ] satisfies Organ[]
};

const realCaseOrgans = buildOrganLayersFromLabels(defaultOrganLabels, []);

const cases: CaseItem[] = [
  {
    id: "AMOS_0117",
    sex: "本地",
    age: 0,
    phase: "AMOS22",
    caseSummary: "本地 AMOS22 · 有标准答案 · 质量验收基线",
    slices: 103,
    target: "腹部 15 标签器官",
    demoImage: demoCtImage,
    imageName: "amos_0117(3).nii.gz",
    imageMeta: "AMOS22 CT · 768x768x103 · 0.507812 x 0.507812 x 5.0 mm",
    organs: realCaseOrgans,
    referenceCaseId: "amos_0117"
  },
  {
    id: "FLARE22_Tr_0009",
    sex: "本地",
    age: 0,
    phase: "FLARE22",
    caseSummary: "本地 FLARE22 · manual-only · 已完成 quality 推理",
    slices: 87,
    target: "腹部 13 标签器官",
    demoImage: demoCtImage,
    imageName: "FLARE22_Tr_0009_0000.nii.gz",
    imageMeta: "FLARE22 CT · 512x512x87 · 0.806641 x 0.806641 x 2.5 mm",
    organs: realCaseOrgans,
    referenceCaseId: "flare22_tr_0009"
  }
];

const moduleItems: { id: ModuleId; icon: typeof FolderOpen; hint: string }[] = [
  { id: "项目", icon: FolderOpen, hint: "病例总览" },
  { id: "数据", icon: Database, hint: "导入与配准" },
  { id: "分割", icon: ScanLine, hint: "模型与图层" },
  { id: "评估", icon: BarChart3, hint: "质控指标" },
  { id: "报告", icon: FileText, hint: "导出与复核" }
];

const toolbarHints = [
  { label: "窗宽窗位", detail: "切换软组织与肺窗预设" },
  { label: "缩放", detail: "放大当前影像视图" },
  { label: "重置", detail: "恢复缩放与切片位置" },
  { label: "测量", detail: "在影像上添加测量标记" },
  { label: "热区", detail: "显示或隐藏 AI 关注区域" },
  { label: "分屏", detail: "拖动分割线对比原图与掩膜" }
];

const modelOptions = [
  { id: "abdomen", name: "AMOS22 腹部器官分割", scope: "15 类腹部器官 · 脾肾肝胆胰胃肠 · 血管 · 泌尿生殖", detail: "基于 AMOS22 公开数据集训练的 nnUNetv2 3D fullres 模型，支持腹部 CT 中 15 个前景器官的全自动分割。" }
];

const runtimeTargetOptions: { id: RuntimeTarget; label: string; detail: string; meta: string }[] = [
  { id: "server", label: "服务器云端推理", detail: "5-GPU 软投票集成", meta: "正式结果推荐" },
  { id: "local", label: "本地在线推理", detail: "保留本机 nnUNetv2 路径", meta: "服务器不可用时保底" }
];

const inferenceProfileOptions: { id: InferenceProfile; label: string; detail: string; meta: string }[] = [
  { id: "quality", label: "质量推理", detail: "默认正式结果", meta: "TTA 开启 · tile 0.5" },
  { id: "fast", label: "快速预览", detail: "需人工复核", meta: "TTA 关闭 · tile 1.0" }
];

const labelTaxonomyOptions: { id: LabelTaxonomy; label: string; detail: string; meta: string }[] = [
  { id: "auto", label: "自动识别", detail: "按标签 ID 组合自动判断", meta: "默认保守策略" },
  { id: "AMOS22", label: "AMOS22 原生", detail: "不执行 FLARE 重映射", meta: "AMOS 标签推荐" },
  { id: "FLARE22", label: "FLARE22", detail: "强制映射到当前模型", meta: "FLARE 标签推荐" }
];

const windowPresets = [
  { id: "soft", label: "软组织", level: 40, width: 360 },
  { id: "lung", label: "肺窗", level: -600, width: 1500 },
  { id: "bone", label: "骨窗", level: 300, width: 1500 }
];

const presetOrganMap: Record<string, string[]> = {
  soft: defaultOrganLabels.map((l) => l.id),
  lung: [],
  bone: [],
};

const runSteps = ["数据预处理", "器官候选区定位", "掩膜后处理", "质控指标刷新", "报告草稿同步"];
const baseLogs = ["演示病例已加载", "支持 PNG/JPG/WebP 与 .nii/.nii.gz 体数据", "侧栏支持导入、删除、质控与报告"];
const FOOTER_SLICE_COUNT = 7;
const INITIAL_VOXEL_COORD: VoxelCoord = { x: 256, y: 256, z: 150 };
const VOXEL_SLICE_SYNC_IDLE_MS = 120;

function toArrayBuffer(data: ArrayBufferLike) {
  if (data instanceof ArrayBuffer) return data;
  const copy = new Uint8Array(data.byteLength);
  copy.set(new Uint8Array(data));
  return copy.buffer;
}

function getNiftiValue(view: DataView, byteOffset: number, datatypeCode: number, littleEndian: boolean) {
  switch (datatypeCode) {
    case 2:
      return view.getUint8(byteOffset);
    case 4:
      return view.getInt16(byteOffset, littleEndian);
    case 8:
      return view.getInt32(byteOffset, littleEndian);
    case 16:
      return view.getFloat32(byteOffset, littleEndian);
    case 64:
      return view.getFloat64(byteOffset, littleEndian);
    case 256:
      return view.getInt8(byteOffset);
    case 512:
      return view.getUint16(byteOffset, littleEndian);
    case 768:
      return view.getUint32(byteOffset, littleEndian);
    default:
      throw new Error(`暂不支持该 NIfTI 数据类型：${datatypeCode}`);
  }
}

function parseNiftiVolume(buffer: ArrayBuffer): NiftiVolume {
  let data = buffer;
  if (nifti.isCompressed(data)) {
    data = toArrayBuffer(nifti.decompress(data));
  }
  if (!nifti.isNIFTI(data)) {
    throw new Error("该文件不是有效的 NIfTI 数据。");
  }

  const header = nifti.readHeader(data);
  const image = nifti.readImage(header, data);
  const datatype = typeof header.getDatatypeCodeString === "function"
    ? header.getDatatypeCodeString(header.datatypeCode)
    : `DT ${header.datatypeCode}`;
  const spacingX = header.pixDims[1] || 1;
  const spacingY = header.pixDims[2] || 1;
  const spacingZ = header.pixDims[3] || 1;

  return {
    image,
    columns: header.dims[1] || 1,
    rows: header.dims[2] || 1,
    slices: Math.max(1, header.dims[3] || 1),
    spacingX,
    spacingY,
    spacingZ,
    datatypeCode: header.datatypeCode,
    datatype,
    littleEndian: header.littleEndian,
    bytesPerVoxel: Math.max(1, header.numBitsPerVoxel / 8),
    slope: header.scl_slope && Number.isFinite(header.scl_slope) ? header.scl_slope : 1,
    intercept: Number.isFinite(header.scl_inter) ? header.scl_inter : 0,
    spacing: `${spacingX.toFixed(2)} x ${spacingY.toFixed(2)} x ${spacingZ.toFixed(2)} mm`
  };
}

function clampSliceIndex(sliceIndex: number, slices: number) {
  return Math.max(0, Math.min(Math.max(0, slices - 1), sliceIndex));
}

function renderNiftiSliceToDataUrl(volume: NiftiVolume, sliceIndex: number, mode: NiftiRenderMode = "intensity") {
  const { columns, rows, bytesPerVoxel, datatypeCode, littleEndian, slope, intercept } = volume;
  const safeSliceIndex = clampSliceIndex(sliceIndex, volume.slices);
  const view = new DataView(volume.image);
  const values = new Float32Array(columns * rows);
  const maskPalette = [
    [80, 232, 190],
    [244, 185, 95],
    [124, 199, 255],
    [239, 138, 168],
    [165, 229, 103],
    [174, 141, 255]
  ];
  let min = Number.POSITIVE_INFINITY;
  let max = Number.NEGATIVE_INFINITY;

  for (let y = 0; y < rows; y += 1) {
    for (let x = 0; x < columns; x += 1) {
      const sourceY = rows - 1 - y;
      const sourceIndex = x + sourceY * columns + safeSliceIndex * columns * rows;
      const value = getNiftiValue(view, sourceIndex * bytesPerVoxel, datatypeCode, littleEndian) * slope + intercept;
      const displayIndex = x + y * columns;
      values[displayIndex] = value;
      if (mode === "intensity" && Number.isFinite(value)) {
        min = Math.min(min, value);
        max = Math.max(max, value);
      }
    }
  }

  if (!Number.isFinite(min) || !Number.isFinite(max) || min === max) {
    min = 0;
    max = 1;
  }

  const canvas = document.createElement("canvas");
  canvas.width = columns;
  canvas.height = rows;
  const context = canvas.getContext("2d");
  if (!context) throw new Error("浏览器无法创建 Canvas 渲染上下文。");
  const imageData = context.createImageData(columns, rows);

  for (let index = 0; index < values.length; index += 1) {
    const pixelOffset = index * 4;
    if (mode === "mask") {
      const label = Math.round(values[index]);
      if (label <= 0 || !Number.isFinite(label)) {
        imageData.data[pixelOffset + 3] = 0;
      } else {
        const color = maskPalette[(label - 1) % maskPalette.length];
        imageData.data[pixelOffset] = color[0];
        imageData.data[pixelOffset + 1] = color[1];
        imageData.data[pixelOffset + 2] = color[2];
        imageData.data[pixelOffset + 3] = 190;
      }
    } else {
      const normalized = Math.max(0, Math.min(1, (values[index] - min) / Math.max(1e-6, max - min)));
      const gray = Math.round(normalized * 255);
      imageData.data[pixelOffset] = gray;
      imageData.data[pixelOffset + 1] = gray;
      imageData.data[pixelOffset + 2] = gray;
      imageData.data[pixelOffset + 3] = 255;
    }
  }

  context.putImageData(imageData, 0, 0);
  return canvas.toDataURL("image/png");
}

function renderCachedAxialNiftiSliceToDataUrl(volume: NiftiVolume, sliceIndex: number, mode: NiftiRenderMode = "intensity") {
  const safeSliceIndex = clampSliceIndex(sliceIndex, volume.slices);
  return renderOrientedNiftiSliceToDataUrl(volume, { x: 0, y: 0, z: safeSliceIndex }, mode, "axial");
}

function getImageDimensions(src: string) {
  return new Promise<string>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(`${image.naturalWidth}x${image.naturalHeight}`);
    image.onerror = () => reject(new Error("无法读取图片尺寸"));
    image.src = src;
  });
}

function getReadableFileType(file: File, fallback: string) {
  if (file.type) return file.type.replace("image/", "").toUpperCase();
  if (file.name.toLowerCase().endsWith(".nii.gz")) return "NII.GZ";
  const extension = file.name.split(".").pop();
  return extension ? extension.toUpperCase() : fallback;
}

function revokeObjectUrl(src?: string) {
  if (src?.startsWith("blob:")) URL.revokeObjectURL(src);
}

function formatDiceMetric(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(3) : "待验证";
}

function formatSeconds(value: number | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "待记录";
  const totalSeconds = Math.max(0, Math.round(value));
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  return minutes > 0 ? `${minutes}分${seconds}秒` : `${seconds}秒`;
}

function formatClockTime(timestamp: number) {
  return new Date(timestamp).toLocaleTimeString("zh-CN", {
    hour12: false,
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit"
  });
}

function formatBytes(value: number | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "待生成";
  if (value >= 1024 * 1024) return `${(value / 1024 / 1024).toFixed(2)} MB`;
  if (value >= 1024) return `${(value / 1024).toFixed(1)} KB`;
  return `${value} B`;
}

function getValidationStatusCopy(validation: ValidationSummary | null, hasLabelFile: boolean) {
  if (!validation) return hasLabelFile ? "等待验证结果" : "未提供标签 CT";
  if (validation.taxonomy_match === false) return "标签 ID 不匹配";
  const remapTag = validation.remap_applied ? `（${validation.remap_source ?? "已知数据集"}→当前模型）` : "";
  if (validation.status === "passed") return `验证通过${remapTag}`;
  if (validation.status === "review") return `建议人工复核${remapTag}`;
  return "无法自动验证";
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}

function DemoMaskPreview({ src }: { src: string }) {
  return (
    <div className="demo-mask-preview">
      <img src={src} alt="" />
      <span className="mask-shape mask-liver" />
      <span className="mask-shape mask-pancreas" />
      <span className="mask-shape mask-stomach" />
    </div>
  );
}

function OrganDetailCard({ organId, label, coord, onClose }: { organId: string; label?: number; coord: VoxelCoord; onClose: () => void }) {
  const detail = getOrganDetail(organId);
  return (
    <aside className="organ-detail-card">
      <div className="organ-detail-head">
        <div>
          <span>器官说明</span>
          <strong>{detail.nameZh} <em>{detail.nameEn}</em></strong>
        </div>
        <button onClick={onClose} aria-label="关闭器官说明">×</button>
      </div>
      <dl>
        <dt>解剖位置</dt><dd>{detail.anatomicalLocation}</dd>
        <dt>生理功能</dt><dd>{detail.functionSummary}</dd>
        <dt>常见关注</dt><dd>{detail.commonFindings}</dd>
        <dt>分割提示</dt><dd>{detail.segmentationNotes}</dd>
      </dl>
      <div className="organ-detail-foot">
        <span>Label {label ?? "-"}</span>
        <span>Voxel ({coord.x}, {coord.y}, {coord.z})</span>
      </div>
    </aside>
  );
}

function App() {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const resultFileInputRef = useRef<HTMLInputElement>(null);
  const labelFileInputRef = useRef<HTMLInputElement>(null);
  const [labelFile, setLabelFile] = useState<File | null>(null);
  const autoLoadAttemptedRef = useRef(false);
  const activeJobIdRef = useRef<string | null>(null);
  const [viewMode, setViewMode] = useState<ViewMode>("Mask");
  const [runState, setRunState] = useState<RunState>("complete");
  const [progress, setProgress] = useState(100);
  const [activeModule, setActiveModule] = useState<ModuleId>("分割");
  const [selectedSlice, setSelectedSlice] = useState(151);
  const [footerSliceStart, setFooterSliceStart] = useState(1);
  const [voxelCoord, setVoxelCoord] = useState<VoxelCoord>(INITIAL_VOXEL_COORD);
  const [selectedCase, setSelectedCase] = useState(cases[0]);
  const [customCases, setCustomCases] = useState<CaseItem[]>([]);
  const [showCaseMenu, setShowCaseMenu] = useState(false);
  const [showReport, setShowReport] = useState(false);
  const [pendingRemoval, setPendingRemoval] = useState<RemovalTarget | null>(null);
  const [selectedOrganId, setSelectedOrganId] = useState("liver");
  const [zoom, setZoom] = useState(1);
  const [windowLevel, setWindowLevel] = useState(40);
  const [windowWidth, setWindowWidth] = useState(360);
  const [activePresetId, setActivePresetId] = useState<string | null>("soft");
  const [highlightedOrganIds, setHighlightedOrganIds] = useState<Set<string>>(new Set());
  const [presetToast, setPresetToast] = useState<string | null>(null);
  const presetToastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const highlightTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const [selectedExportFormat, setSelectedExportFormat] = useState<ReportFormat>("html");
  const [maskOpacity, setMaskOpacity] = useState(58);
  const [comparePosition, setComparePosition] = useState(52);
  const [isDraggingSplit, setIsDraggingSplit] = useState(false);
  const splitDragActiveRef = useRef(false);
  const pendingSelectedSliceRef = useRef<number | null>(null);
  const selectedSliceFrameRef = useRef<number | null>(null);
  const selectedSliceSyncSourceRef = useRef<SelectedSliceSyncSource>("slice");
  const pendingVoxelSelectedSliceRef = useRef<number | null>(null);
  const voxelSelectedSliceTimerRef = useRef<number | null>(null);
  const voxelCoordRef = useRef<VoxelCoord>(INITIAL_VOXEL_COORD);
  const pendingVoxelCoordRef = useRef<VoxelCoord | null>(null);
  const voxelCoordFrameRef = useRef<number | null>(null);
  const [compareMode, setCompareMode] = useState<CompareMode>("split");
  const [measureMode, setMeasureMode] = useState(false);
  const [heatmapVisible, setHeatmapVisible] = useState(true);
  const [loadedImage, setLoadedImage] = useState<LoadedImage>({
    src: cases[0].demoImage,
    name: cases[0].imageName,
    kind: "Demo",
    meta: cases[0].imageMeta
  });
  const [resultImage, setResultImage] = useState<LoadedImage | null>(null);
  const [organs, setOrgans] = useState<Organ[]>(cases[0].organs);
  const [modelLabels, setModelLabels] = useState(defaultOrganLabels);
  const [measurements, setMeasurements] = useState<Measurement[]>([
    { id: 1, label: "M1", x: 51.8, y: 52.4, hu: 48, diameter: "18.6 mm", slice: 151 }
  ]);
  const [logs, setLogs] = useState(baseLogs);
  const [toast, setToast] = useState("演示病例已加载");
  const [inferenceStatus, setInferenceStatus] = useState<InferenceStatus>({ status: "idle" });
  const [inferenceTimeline, setInferenceTimeline] = useState<InferenceTimelineEntry[]>([]);
  const [inferenceStartedAt, setInferenceStartedAt] = useState<number | null>(null);
  const [elapsedNow, setElapsedNow] = useState(() => Date.now());
  const [validationSummary, setValidationSummary] = useState<ValidationSummary | null>(null);
  const [sampleLoadState, setSampleLoadState] = useState<{ status: "idle" | "loading" | "ready" | "failed"; message: string }>({ status: "idle", message: "等待载入内置参考病例" });
  const [referenceCases, setReferenceCases] = useState<ReferenceCase[]>(DEFAULT_REFERENCE_CASES);
  const [selectedReferenceCaseId, setSelectedReferenceCaseId] = useState(DEFAULT_REFERENCE_CASES[0]?.id ?? "");
  const [selectedOrganDetail, setSelectedOrganDetail] = useState<{ id: string; label?: number; coord: VoxelCoord } | null>(null);
  const [dragTarget, setDragTarget] = useState<UploadRole | null>(null);
  const [lastImport, setLastImport] = useState("等待导入本地影像或分割结果图");
  const [selectedModelId, setSelectedModelId] = useState("abdomen");
  const [selectedInferenceProfile, setSelectedInferenceProfile] = useState<InferenceProfile>("quality");
  const [selectedLabelTaxonomy, setSelectedLabelTaxonomy] = useState<LabelTaxonomy>("auto");
  const [selectedRuntimeTarget, setSelectedRuntimeTarget] = useState<RuntimeTarget>("server");
  const [resultInferenceOptions, setResultInferenceOptions] = useState<InferenceOptions | null>(null);
  const [confidenceThreshold, setConfidenceThreshold] = useState(72);
  const [postprocessConfig, setPostprocessConfig] = useState({
    removeIslands: true,
    smoothBoundary: true,
    fillHoles: true
  });
  const [reportState, setReportState] = useState<ReportState>({
    draftSaved: false,
    reviewQueued: false,
    exportCount: 0,
    lastExport: "尚未导出"
  });

  const compareModeLabel: Record<CompareMode, string> = {
    split: "滑动分屏",
    overlay: "透明叠加",
    side: "左右并排",
    difference: "差异增强"
  };
  const allCases = useMemo(() => [...cases, ...customCases], [customCases]);
  const currentTotalSlices = loadedImage.volume?.slices ?? resultImage?.volume?.slices ?? selectedCase.slices;
  const currentSliceIndex = clampSliceIndex(selectedSlice - 1, currentTotalSlices);
  const selectedOrgan = organs.find((organ) => organ.id === selectedOrganId) ?? organs[0];
  const selectedModel = modelOptions.find((model) => model.id === selectedModelId) ?? modelOptions[0];
  const selectedInferenceProfileOption = inferenceProfileOptions.find((item) => item.id === selectedInferenceProfile) ?? inferenceProfileOptions[0];
  const selectedLabelTaxonomyOption = labelTaxonomyOptions.find((item) => item.id === selectedLabelTaxonomy) ?? labelTaxonomyOptions[0];
  const selectedRuntimeTargetOption = runtimeTargetOptions.find((item) => item.id === selectedRuntimeTarget) ?? runtimeTargetOptions[0];
  const inferenceOptionsLocked = inferenceStatus.status === "submitting" || inferenceStatus.status === "running" || runState === "running";
  const fastProfileNeedsReview = selectedInferenceProfile === "fast" || resultInferenceOptions?.profile === "fast";
  const resultProfileCopy = resultInferenceOptions?.profile === "fast" ? "快速预览 · 需人工复核" : resultInferenceOptions?.profile === "quality" ? "质量推理" : selectedInferenceProfileOption.label;
  const selectedReferenceCase = referenceCases.find((item) => item.id === selectedReferenceCaseId) ?? referenceCases[0] ?? DEFAULT_REFERENCE_CASES[0];
  const selectedReferenceCaseMeta = selectedReferenceCase
    ? `${selectedReferenceCase.dataset} · ${selectedReferenceCase.validationAvailable ? "有标准答案" : "无标准答案"}`
    : "未发现参考病例";
  const canLoadSelectedReferenceCase = Boolean(selectedReferenceCase?.hasOriginal);
  const visibleOrgans = useMemo(() => new Set(organs.filter((organ) => organ.visible).map((organ) => organ.id)), [organs]);
  const quantificationSummary = useMemo(() => summarizeSegmentationQuantification(resultImage?.volume, modelLabels), [modelLabels, resultImage]);
  const quantificationById = useMemo(() => new Map(quantificationSummary.organs.map((organ) => [organ.id, organ])), [quantificationSummary]);
  const displayedOrgans = useMemo(() => organs.map((organ) => {
    const quantification = quantificationById.get(organ.id);
    return quantification?.status === "computed"
      ? { ...organ, volume: formatQuantificationValue(quantification.volumeMl, "ml") }
      : organ;
  }), [organs, quantificationById]);
  const computedQuantificationOrgans = quantificationSummary.organs.filter((organ) => organ.status === "computed");
  const quantificationPreviewOrgans = computedQuantificationOrgans.slice(0, 6);
  const quantificationStatusCopy = quantificationSummary.status === "computed"
    ? "已基于分割 mask 自动计算器官量化指标。"
    : quantificationSummary.status === "empty"
      ? "当前分割 mask 中未发现配置标签的前景体素。"
      : resultImage?.volume
        ? "NIfTI 体素间距不可用，无法换算物理量。"
        : "等待分割结果后自动计算体积、截面积和长度估算。";
  const labelLookup = useMemo(() => buildLabelLookup(modelLabels), [modelLabels]);
  const visibleLabels = useMemo(() => new Set(modelLabels.filter((label) => visibleOrgans.has(label.id) || !organs.some((organ) => organ.id === label.id)).map((label) => label.label)), [modelLabels, organs, visibleOrgans]);
  const acceptedCount = organs.filter((organ) => organ.quality === "accepted").length;
  const reviewCount = organs.length - acceptedCount;
  const scoredMeanDice = getMeanOrganDice(displayedOrgans);
  const averageDice = scoredMeanDice === null ? "待验证" : scoredMeanDice.toFixed(3);
  const displayedAverageDice = validationSummary?.mean_dice != null ? formatDiceMetric(validationSummary.mean_dice) : averageDice;
  const validationStatusCopy = getValidationStatusCopy(validationSummary, Boolean(labelFile));
  const validationMessage = validationSummary?.message ?? (labelFile ? "推理完成后将自动用标签 CT 计算 Dice。" : "导入标签 CT 或载入参考病例后，可自动计算 Dice。");
  const inferenceDurationCopy = inferenceStatus.status === "succeeded" ? formatSeconds(inferenceStatus.duration_seconds) : "待记录";
  const inferenceResultSizeCopy = inferenceStatus.status === "succeeded" ? formatBytes(inferenceStatus.result_size_bytes) : "待生成";
  const inferenceResourceCopy = inferenceStatus.status === "succeeded" ? getResourceSnapshotCopy(inferenceStatus.resource_latest) : "待记录";
  const inferencePhaseTimingCopy = inferenceStatus.status === "succeeded" ? getPhaseTimingSummary(inferenceStatus.phase_timings) : "待记录";
  const inferenceProgressCopy = useMemo(() => {
    const clampedProgress = Math.max(0, Math.min(100, Math.round(
      inferenceStatus.status === "running"
        ? inferenceStatus.progress
        : inferenceStatus.status === "succeeded"
          ? 100
          : progress
    )));
    const jobId = inferenceStatus.status === "running" || inferenceStatus.status === "succeeded" || inferenceStatus.status === "cancelled" || inferenceStatus.status === "failed"
      ? inferenceStatus.jobId
      : activeJobIdRef.current ?? undefined;
    const activeProfile = inferenceStatus.status === "succeeded" && inferenceStatus.inference_options?.profile
      ? inferenceStatus.inference_options.profile
      : selectedInferenceProfile;
    const profileCopy = activeProfile === "fast" ? "快速预览 · 需人工复核" : "质量推理";
    const elapsedSeconds = inferenceStatus.status === "succeeded"
      ? inferenceStatus.duration_seconds
      : inferenceStartedAt
        ? (elapsedNow - inferenceStartedAt) / 1000
        : undefined;
    const latestTimeline = inferenceTimeline[0];
    if (inferenceStatus.status === "submitting") {
      return {
        title: "正在提交任务",
        stage: latestTimeline?.message ?? `正在提交${selectedRuntimeTargetOption.label}任务`,
        percent: clampedProgress,
        percentCopy: `${clampedProgress}%`,
        jobCopy: jobId ? `Job ${jobId}` : "Job 待创建",
        profileCopy,
        elapsedCopy: "待开始",
        tone: "running"
      };
    }
    if (inferenceStatus.status === "running") {
      return {
        title: "推理运行中",
        stage: inferenceStatus.stage,
        percent: clampedProgress,
        percentCopy: `${clampedProgress}%`,
        jobCopy: jobId ? `Job ${jobId}` : "Job 待创建",
        profileCopy,
        elapsedCopy: elapsedSeconds === undefined ? "待记录" : formatSeconds(elapsedSeconds),
        tone: "running"
      };
    }
    if (inferenceStatus.status === "succeeded") {
      return {
        title: "推理完成",
        stage: getInferenceStatusCopy(inferenceStatus),
        percent: 100,
        percentCopy: "100%",
        jobCopy: jobId ? `Job ${jobId}` : "Job 已结束",
        profileCopy,
        elapsedCopy: elapsedSeconds === undefined ? "待记录" : formatSeconds(elapsedSeconds),
        tone: "complete"
      };
    }
    if (inferenceStatus.status === "failed") {
      const firstLine = inferenceStatus.message.split(/\r?\n/).find(Boolean) ?? "推理失败";
      return {
        title: "推理失败",
        stage: firstLine,
        percent: clampedProgress,
        percentCopy: `${clampedProgress}%`,
        jobCopy: jobId ? `Job ${jobId}` : "Job 未完成",
        profileCopy,
        elapsedCopy: elapsedSeconds === undefined ? "待记录" : formatSeconds(elapsedSeconds),
        tone: "error"
      };
    }
    if (inferenceStatus.status === "cancelled") {
      return {
        title: "已取消",
        stage: "推理任务已取消",
        percent: clampedProgress,
        percentCopy: `${clampedProgress}%`,
        jobCopy: jobId ? `Job ${jobId}` : "Job 已取消",
        profileCopy,
        elapsedCopy: elapsedSeconds === undefined ? "待记录" : formatSeconds(elapsedSeconds),
        tone: "cancelled"
      };
    }
    const idleProgress = inferenceTimeline.length ? clampedProgress : 0;
    return {
      title: "等待在线推理",
      stage: latestTimeline?.message ?? `选择原图后可运行${selectedRuntimeTargetOption.label}`,
      percent: idleProgress,
      percentCopy: idleProgress > 0 ? `${idleProgress}%` : "0%",
      jobCopy: "Job 待创建",
      profileCopy,
      elapsedCopy: "待记录",
      tone: "idle"
    };
  }, [elapsedNow, inferenceStartedAt, inferenceStatus, inferenceTimeline, progress, selectedInferenceProfile, selectedRuntimeTargetOption.label]);
  const hasLocalSource = loadedImage.kind !== "Demo";
  const hasImportedFiles = hasLocalSource || Boolean(resultImage);
  const customCasePanelCopy = useMemo(
    () => getCustomCasePanelCopy(customCases.length, hasLocalSource, Boolean(selectedCase.custom)),
    [customCases.length, hasLocalSource, selectedCase.custom]
  );
  const imageContrast = Math.max(0.82, Math.min(1.34, 1.08 + (360 - windowWidth) / 1800 + Math.abs(windowLevel - 40) / 2200));
  const imageBrightness = Math.max(0.7, Math.min(1.16, 0.92 + (windowLevel - 40) / 1800));

  const loadedDisplaySrc = useMemo(
    () => loadedImage.volume ? renderCachedAxialNiftiSliceToDataUrl(loadedImage.volume, currentSliceIndex, "intensity") : loadedImage.src,
    [currentSliceIndex, loadedImage]
  );
  const resultDisplaySrc = useMemo(
    () => resultImage?.volume ? renderCachedAxialNiftiSliceToDataUrl(resultImage.volume, currentSliceIndex, "mask") : resultImage?.src,
    [currentSliceIndex, resultImage]
  );
  const displayAspectRatio = useMemo(() => getDisplayAspectRatio(loadedImage), [loadedImage]);
  const registrationStatus = useMemo(() => getRegistrationStatus(loadedImage, resultImage), [loadedImage, resultImage]);
  const volumeRegistration = registrationStatus.label;
  const alignmentCaption = useMemo(
    () => getAlignmentCaptionCopy(loadedImage, resultImage, registrationStatus),
    [loadedImage, registrationStatus, resultImage]
  );
  const footerSlicePreviews = useMemo(() => {
    const count = Math.min(FOOTER_SLICE_COUNT, currentTotalSlices);
    const start = getStableSliceWindowStart(footerSliceStart, footerSliceStart, currentTotalSlices, FOOTER_SLICE_COUNT);
    return Array.from({ length: count }, (_, index) => {
      const slice = start + index;
      return {
        slice,
        src: loadedImage.volume ? renderCachedAxialNiftiSliceToDataUrl(loadedImage.volume, slice - 1, "intensity") : loadedDisplaySrc
      };
    });
  }, [currentTotalSlices, footerSliceStart, loadedImage]);

  const readinessChecks = [
    { label: "原图", value: loadedImage.kind === "Demo" ? "演示图" : "本地文件", ready: true },
    { label: "结果图", value: resultImage ? "已导入" : "内置掩膜", ready: true },
    {
      label: "尺寸校验",
      value: resultImage ? registrationStatus.label : "等待结果图",
      ready: registrationStatus.ready
    },
    {
      label: "NIfTI 同步",
      value: loadedImage.volume && resultImage?.volume ? `切片 ${selectedSlice}` : loadedImage.volume ? "等待掩膜体数据" : "二维图像模式",
      ready: Boolean(loadedImage.volume && resultImage?.volume) || !loadedImage.volume
    },
    {
      label: "体数据配准",
      value: volumeRegistration,
      ready: registrationStatus.ready
    },
    { label: "对比模式", value: compareModeLabel[compareMode], ready: true }
  ];

  const comparisonStats = [
    { label: "对比模式", value: compareModeLabel[compareMode] },
    { label: "原图来源", value: loadedImage.kind },
    { label: "结果来源", value: resultImage ? resultImage.kind : "模拟掩膜" },
    { label: "原图尺寸", value: loadedImage.dimensions ?? "演示切片" },
    { label: "结果尺寸", value: resultImage?.dimensions ?? "随原图生成" },
    { label: "体数据配准", value: volumeRegistration },
    { label: "同步切片", value: `${selectedSlice}/${currentTotalSlices}` },
    { label: "叠加透明度", value: `${maskOpacity}%` }
  ];

  const aiFindings = [
    `${selectedOrgan.name} 质控状态 ${formatOrganScore(selectedOrgan.score)}`,
    `当前切片 ${selectedSlice} 已显示 ${visibleOrgans.size} 个器官`,
    reviewCount > 0 ? `${reviewCount} 个器官建议人工复核` : "所有器官已通过质控",
    measurements.length > 0 ? `已记录 ${measurements.length} 个测量点` : "尚未添加测量点"
  ];

  function commitSelectedSliceFromVoxel(nextSlice: number) {
    const safeSlice = Math.max(1, Math.min(currentTotalSlices, Math.round(nextSlice)));
    setSelectedSlice((slice) => {
      if (slice === safeSlice) return slice;
      selectedSliceSyncSourceRef.current = "voxel";
      return safeSlice;
    });
  }

  function scheduleSelectedSlice(nextSlice: number) {
    pendingSelectedSliceRef.current = Math.max(1, Math.min(currentTotalSlices, Math.round(nextSlice)));
    if (selectedSliceFrameRef.current !== null) return;

    selectedSliceFrameRef.current = requestAnimationFrame(() => {
      selectedSliceFrameRef.current = null;
      const pendingSlice = pendingSelectedSliceRef.current;
      pendingSelectedSliceRef.current = null;
      if (pendingSlice === null) return;
      commitSelectedSliceFromVoxel(pendingSlice);
    });
  }

  function scheduleSelectedSliceAfterVoxelIdle(nextSlice: number) {
    pendingVoxelSelectedSliceRef.current = Math.max(1, Math.min(currentTotalSlices, Math.round(nextSlice)));
    if (voxelSelectedSliceTimerRef.current !== null) {
      window.clearTimeout(voxelSelectedSliceTimerRef.current);
    }

    voxelSelectedSliceTimerRef.current = window.setTimeout(() => {
      voxelSelectedSliceTimerRef.current = null;
      const pendingSlice = pendingVoxelSelectedSliceRef.current;
      pendingVoxelSelectedSliceRef.current = null;
      if (pendingSlice === null) return;
      commitSelectedSliceFromVoxel(pendingSlice);
    }, VOXEL_SLICE_SYNC_IDLE_MS);
  }

  function scheduleVoxelCoordChange(nextCoord: VoxelCoord) {
    if (!loadedImage.volume) {
      if (!shouldUpdateVoxelCoord(voxelCoordRef.current, nextCoord)) return;
      voxelCoordRef.current = nextCoord;
      setVoxelCoord(nextCoord);
      return;
    }

    const pendingCommit = getVoxelCoordDragCommit(voxelCoordRef.current, nextCoord, loadedImage.volume);
    if (!pendingCommit) {
      pendingVoxelCoordRef.current = null;
      return;
    }
    pendingVoxelCoordRef.current = pendingCommit.coord;
    if (voxelCoordFrameRef.current !== null) return;

    voxelCoordFrameRef.current = requestAnimationFrame(() => {
      voxelCoordFrameRef.current = null;
      const pendingCoord = pendingVoxelCoordRef.current;
      pendingVoxelCoordRef.current = null;
      if (!pendingCoord || !loadedImage.volume) return;
      const commit = getVoxelCoordDragCommit(voxelCoordRef.current, pendingCoord, loadedImage.volume);
      if (!commit) return;
      voxelCoordRef.current = commit.coord;
      setVoxelCoord(commit.coord);
      scheduleSelectedSliceAfterVoxelIdle(commit.selectedSlice);
    });
  }

  useEffect(() => () => {
    if (selectedSliceFrameRef.current !== null) {
      cancelAnimationFrame(selectedSliceFrameRef.current);
    }
    if (voxelCoordFrameRef.current !== null) {
      cancelAnimationFrame(voxelCoordFrameRef.current);
    }
    if (voxelSelectedSliceTimerRef.current !== null) {
      window.clearTimeout(voxelSelectedSliceTimerRef.current);
    }
  }, []);

  useEffect(() => {
    voxelCoordRef.current = voxelCoord;
  }, [voxelCoord]);

  useEffect(() => {
    if (!loadedImage.volume) return;
    const syncSource = selectedSliceSyncSourceRef.current;
    selectedSliceSyncSourceRef.current = "slice";
    setVoxelCoord((coord) => {
      const nextCoord = getVoxelCoordForSelectedSliceSync(coord, selectedSlice, loadedImage.volume!, syncSource);
      return shouldUpdateVoxelCoord(coord, nextCoord) ? nextCoord : coord;
    });
  }, [loadedImage.volume, selectedSlice]);

  useEffect(() => {
    setSelectedSlice((slice) => Math.max(1, Math.min(slice, currentTotalSlices)));
  }, [currentTotalSlices]);

  useEffect(() => {
    setFooterSliceStart((start) => getStableSliceWindowStart(start, selectedSlice, currentTotalSlices, FOOTER_SLICE_COUNT));
  }, [currentTotalSlices, selectedSlice]);

  useEffect(() => {
    if (!loadedImage.volume) return;
    const nextSlice = getSelectedSliceForVoxelCoord(voxelCoord, loadedImage.volume.slices);
    if (nextSlice !== selectedSlice) {
      scheduleSelectedSliceAfterVoxelIdle(nextSlice);
    }
  }, [voxelCoord.z, loadedImage.volume, currentTotalSlices, selectedSlice]);

  useEffect(() => {
    setToast(getInferenceStatusCopy(inferenceStatus));
  }, [inferenceStatus]);

  useEffect(() => {
    if (runState !== "running" || inferenceStartedAt === null) return;
    setElapsedNow(Date.now());
    const timer = window.setInterval(() => setElapsedNow(Date.now()), 1000);
    return () => window.clearInterval(timer);
  }, [inferenceStartedAt, runState]);

  useEffect(() => {
    void fetchModelLabels(API_ENDPOINT)
      .then((labels) => {
        if (labels.length) {
          setModelLabels(labels);
          syncOrganLayers(labels);
        }
      })
      .catch(() => {
        setModelLabels(defaultOrganLabels);
        syncOrganLayers(defaultOrganLabels);
      });
  }, []);

  useEffect(() => {
    void fetch(`${API_ENDPOINT}/api/samples`)
      .then((response) => {
        if (!response.ok) throw new Error("参考病例列表不可用");
        return response.json();
      })
      .then((payload) => {
        const nextCases = normalizeReferenceCases(payload);
        setReferenceCases(nextCases);
        setSelectedReferenceCaseId((current) => nextCases.some((item) => item.id === current) ? current : nextCases[0]?.id ?? current);
        setSampleLoadState((current) => current.status === "idle" ? { ...current, message: `可载入 ${nextCases[0]?.name ?? "内置参考病例"}` } : current);
      })
      .catch(() => {
        setReferenceCases(DEFAULT_REFERENCE_CASES);
        setSelectedReferenceCaseId(DEFAULT_REFERENCE_CASES[0]?.id ?? "");
      });
  }, []);

  useEffect(() => {
    if (autoLoadAttemptedRef.current || loadedImage.volume) return;
    autoLoadAttemptedRef.current = true;
    void loadReferenceCase();
  }, [loadedImage.volume]);

  function handleVoxelCoordChange(nextCoord: VoxelCoord) {
    if (!loadedImage.volume) {
      scheduleVoxelCoordChange(nextCoord);
      return;
    }
    scheduleVoxelCoordChange(nextCoord);
  }

  function updateSplitPositionFromPointer(event: PointerEvent<HTMLDivElement>) {
    if (compareMode !== "split" || measureMode) return;
    const rect = event.currentTarget.getBoundingClientRect();
    setComparePosition(getSplitPositionFromClientX(event.clientX, rect.left, rect.width));
  }

  function handleSplitPointerDown(event: PointerEvent<HTMLDivElement>) {
    if (compareMode !== "split" || measureMode) return;
    event.preventDefault();
    event.stopPropagation();
    event.currentTarget.setPointerCapture(event.pointerId);
    splitDragActiveRef.current = true;
    setIsDraggingSplit(true);
    updateSplitPositionFromPointer(event);
  }

  function handleSplitPointerMove(event: PointerEvent<HTMLDivElement>) {
    if (!splitDragActiveRef.current || compareMode !== "split" || measureMode) return;
    event.preventDefault();
    event.stopPropagation();
    updateSplitPositionFromPointer(event);
  }

  function handleSplitPointerEnd(event: PointerEvent<HTMLDivElement>) {
    if (!splitDragActiveRef.current) return;
    event.preventDefault();
    event.stopPropagation();
    if (event.currentTarget.hasPointerCapture(event.pointerId)) {
      event.currentTarget.releasePointerCapture(event.pointerId);
    }
    splitDragActiveRef.current = false;
    setIsDraggingSplit(false);
  }

  function syncOrganLayers(labels = modelLabels, validationLabels?: ValidationSummary["labels"]) {
    setOrgans((items) => buildOrganLayersFromLabels(labels, items, validationLabels));
    setSelectedOrganId((current) => labels.some((label) => label.id === current) ? current : labels[0]?.id ?? current);
  }

  function appendInferenceTimelineEntry(entry: Omit<InferenceTimelineEntry, "id" | "at"> & { at?: number }) {
    const at = entry.at ?? Date.now();
    setInferenceTimeline((items) => [{
      ...entry,
      at,
      id: `${at}-${entry.type}-${entry.progress ?? "na"}-${items.length}`
    }, ...items].slice(0, 8));
  }

  async function startSegmentation(sourceOverride?: LoadedImage) {
    let sourceImage = sourceOverride ?? loadedImage;
    if (!sourceImage.volume || !sourceImage.file) {
      const loaded = await loadReferenceCase();
      if (!loaded) {
        setInferenceStatus({ status: "failed", message: "请先导入 .nii/.nii.gz 原图，或确认本地参考病例服务已启动" });
        return;
      }
      sourceImage = loaded;
    }

    setRunState("running");
    setProgress(0);
    setViewMode("Mask");
    setCompareMode("overlay");
    setValidationSummary(null);
    setResultInferenceOptions(null);
    activeJobIdRef.current = null;
    const submitAt = Date.now();
    setInferenceStartedAt(null);
    setElapsedNow(submitAt);
    setInferenceTimeline([{
      id: `${submitAt}-info-submit`,
      type: "info",
      progress: 0,
      stage: "提交任务",
      message: `提交${selectedRuntimeTargetOption.label}任务：${selectedModel.name} · ${selectedInferenceProfileOption.label}`,
      at: submitAt
    }]);
    setInferenceStatus({ status: "submitting" });
    setLogs([`提交${selectedRuntimeTargetOption.label}任务：${selectedModel.name} · ${selectedInferenceProfileOption.label}`, `质控提示阈值 ${confidenceThreshold}% · 后处理 ${Object.values(postprocessConfig).filter(Boolean).length}/3`, ...baseLogs]);
    if (!labelFile) {
      setToast("未选择标签 CT，推理完成后不会自动计算 Dice。可通过「标签 CT 导入」补充。");
    }

    try {
      const endpoint = API_ENDPOINT;
      const job = await createInferenceJob(endpoint, sourceImage.file!, {
        modelId: selectedModelId,
        confidenceThreshold,
        postprocess: postprocessConfig,
        inferenceProfile: selectedInferenceProfile,
        runtimeTarget: selectedRuntimeTarget,
        labelTaxonomy: selectedLabelTaxonomy,
        labelFile: labelFile ?? undefined,
      });
      activeJobIdRef.current = job.job_id;
      let inferenceOptions = job.inference_options;
      const startedAt = Date.now();
      setInferenceStartedAt(startedAt);
      setElapsedNow(startedAt);
      appendInferenceTimelineEntry({
        type: "progress",
        progress: 1,
        stage: job.cached_result ? "命中历史缓存，正在回填结果" : job.mode === "debug-label-fallback" ? "使用本地标签调试回退" : "后端真实推理已启动",
        message: job.cached_result ? "命中历史缓存，等待结果回填" : `后端 job 已创建：${job.job_id}`,
        at: startedAt
      });
      setInferenceStatus({
        status: "running",
        jobId: job.job_id,
        progress: 1,
        stage: job.cached_result ? "命中历史缓存，正在回填结果" : job.mode === "debug-label-fallback" ? "使用本地标签调试回退" : "后端真实推理已启动"
      });

      let durationSeconds: number | undefined;
      let resultSizeBytes: number | undefined;
      let resourceLatest: ResourceSnapshot | undefined;
      let phaseTimings: PhaseTimings | undefined;
      await new Promise<void>((resolve, reject) => {
        const events = new EventSource(`${endpoint}/api/segment/jobs/${job.job_id}/events`);
        events.onmessage = (event) => {
          try {
            const parsed = parseInferenceEvent(`data: ${event.data}`);
            if (parsed.type === "error") {
              const logTailSummary = parsed.log_tail?.split(/\r?\n/).filter(Boolean).slice(-2).join(" / ");
              appendInferenceTimelineEntry({
                type: "error",
                stage: parsed.message,
                message: logTailSummary ? `${parsed.message} · ${logTailSummary}` : parsed.message
              });
              events.close();
              reject(new Error(parsed.log_tail ? `${parsed.message}\n${parsed.log_tail}` : parsed.message));
              return;
            }
            setProgress(parsed.progress);
            setInferenceStatus({ status: "running", jobId: job.job_id, progress: parsed.progress, stage: parsed.stage });
            if (parsed.type === "progress" && parsed.heartbeat) {
              if (Number.isFinite(parsed.elapsed_seconds)) {
                setInferenceStartedAt(Date.now() - (parsed.elapsed_seconds as number) * 1000);
              }
              setLogs((items) => [`后端运行中 · ${parsed.stage} · ${parsed.progress}%`, ...items].slice(0, 8));
            } else {
              appendInferenceTimelineEntry({
                type: parsed.type === "complete" ? "complete" : "progress",
                progress: parsed.progress,
                stage: parsed.stage,
                message: parsed.type === "complete" ? "阶段事件完成，正在下载分割结果" : parsed.stage
              });
              setLogs((items) => [`${parsed.stage} · ${parsed.progress}%`, ...items].slice(0, 8));
            }
            if (parsed.type === "complete") {
              const validation = parsed.validation;
              if (validation) {
                setValidationSummary(validation);
                syncOrganLayers(modelLabels, validation.labels);
                setLogs((items) => [`标准答案验证：${formatDiceMetric(validation.mean_dice)} · ${validation.message ?? "已生成验证摘要"}`, ...items].slice(0, 8));
              }
              durationSeconds = parsed.duration_seconds;
              resultSizeBytes = parsed.result_size_bytes;
              resourceLatest = parsed.resource_latest;
              phaseTimings = parsed.phase_timings;
              if (parsed.inference_options) inferenceOptions = parsed.inference_options;
              if (resourceLatest) {
                setLogs((items) => [`资源记录：${getResourceSnapshotCopy(resourceLatest)}`, ...items].slice(0, 8));
              }
              if (phaseTimings) {
                setLogs((items) => [`耗时瓶颈：${getPhaseTimingSummary(phaseTimings)}`, ...items].slice(0, 8));
              }
              events.close();
              resolve();
            }
          } catch (error) {
            events.close();
            reject(error);
          }
        };
        events.onerror = () => {
          events.close();
          reject(new Error(`无法连接${selectedRuntimeTargetOption.label}服务，请确认后端已在 ${API_ENDPOINT} 启动`));
        };
      });

      const resultBuffer = await downloadInferenceResult(endpoint, job.job_id);
      const resultVol = parseNiftiVolume(resultBuffer);
      const sliceIndex = Math.min(resultVol.slices - 1, voxelCoord.z);
      const resultKindLabel = selectedRuntimeTarget === "server"
        ? (inferenceOptions?.profile === "fast" ? "服务器快速预览结果（需人工复核）" : job.cached_result ? "服务器缓存结果" : "服务器 5-fold 软投票结果")
        : (inferenceOptions?.profile === "fast"
          ? "快速预览结果（需人工复核）"
          : job.cached_result ? "缓存推理结果" : job.mode === "debug-label-fallback" ? "调试结果" : "真实推理结果");
      setResultImage({
        src: renderCachedAxialNiftiSliceToDataUrl(resultVol, sliceIndex, "mask"),
        name: `${sourceImage.name.replace(/\.nii(\.gz)?$/i, "")}_seg.nii.gz`,
        kind: "NIfTI",
        meta: getInferenceResultMeta(job.mode, `${resultVol.columns}x${resultVol.rows}x${resultVol.slices}`, inferenceOptions),
        dimensions: `${resultVol.columns}x${resultVol.rows}x${resultVol.slices}`,
        sizeText: `${(resultBuffer.byteLength / 1024 / 1024).toFixed(2)} MB`,
        format: "NII.GZ",
        volume: resultVol,
        sliceIndex
      });
      setResultInferenceOptions(inferenceOptions ?? null);
      setProgress(100);
      setRunState("complete");
      setElapsedNow(Date.now());
      setInferenceStatus({ status: "succeeded", jobId: job.job_id, mode: job.mode, duration_seconds: durationSeconds, result_size_bytes: resultSizeBytes, resource_latest: resourceLatest, phase_timings: phaseTimings, inference_options: inferenceOptions });
      activeJobIdRef.current = null;
      setLastImport(`${resultKindLabel}就绪：${job.job_id}`);
      appendInferenceTimelineEntry({
        type: "complete",
        progress: 100,
        stage: "结果已回填三视图",
        message: `分割结果已加载 · ${formatSeconds(durationSeconds)} · ${formatBytes(resultSizeBytes)}`
      });
      setLogs((items) => [`分割结果已加载到三正交视图 · ${formatSeconds(durationSeconds)} · ${formatBytes(resultSizeBytes)}`, ...items].slice(0, 8));
    } catch (error) {
      const message = error instanceof Error ? error.message : "推理失败";
      setRunState("idle");
      setElapsedNow(Date.now());
      if (message.includes("取消")) {
        setInferenceStatus({ status: "cancelled", jobId: activeJobIdRef.current ?? undefined });
      } else {
        setInferenceStatus({ status: "failed", message, jobId: activeJobIdRef.current ?? undefined });
      }
      appendInferenceTimelineEntry({
        type: message.includes("取消") ? "cancelled" : "error",
        stage: message.includes("取消") ? "推理已取消" : "推理失败",
        message: message.split(/\r?\n/).filter(Boolean).slice(0, 2).join(" · ") || message
      });
      activeJobIdRef.current = null;
      setLogs((items) => [`${message.includes("取消") ? "推理已取消" : "推理失败"}：${message}`, ...items].slice(0, 8));
    }
  }

  async function cancelSegmentation() {
    const jobId = activeJobIdRef.current;
    if (!jobId) {
      setToast("任务正在提交，本地 job 创建后可取消");
      return;
    }
    try {
      await cancelInferenceJob(API_ENDPOINT, jobId);
      setRunState("idle");
      setElapsedNow(Date.now());
      setInferenceStatus({ status: "cancelled", jobId });
      appendInferenceTimelineEntry({
        type: "cancelled",
        stage: "推理已取消",
        message: `已请求取消推理任务：${jobId}`
      });
      setLogs((items) => [`已请求取消推理任务：${jobId}`, ...items].slice(0, 8));
    } catch (error) {
      const message = error instanceof Error ? error.message : "取消推理任务失败";
      setInferenceStatus({ status: "failed", message, jobId });
      appendInferenceTimelineEntry({
        type: "error",
        stage: "取消失败",
        message
      });
      setLogs((items) => [`取消失败：${message}`, ...items].slice(0, 8));
    }
  }

  function resetView() {
    setZoom(1);
    setWindowLevel(40);
    setWindowWidth(360);
    setActivePresetId("soft");
    setHighlightedOrganIds(new Set());
    setPresetToast(null);
    if (highlightTimerRef.current) { clearTimeout(highlightTimerRef.current); highlightTimerRef.current = null; }
    if (presetToastTimerRef.current) { clearTimeout(presetToastTimerRef.current); presetToastTimerRef.current = null; }
    setSelectedSlice(Math.min(currentTotalSlices, Math.floor(currentTotalSlices / 2) + 1));
    setToast("视图已重置");
  }

  function applyWindowPreset(preset: typeof windowPresets[number]) {
    setWindowLevel(preset.level);
    setWindowWidth(preset.width);
    const isSamePreset = activePresetId === preset.id;
    setActivePresetId(isSamePreset ? null : preset.id);
    const organIds = presetOrganMap[preset.id] ?? [];
    if (isSamePreset) {
      setHighlightedOrganIds(new Set());
      setPresetToast(null);
      if (highlightTimerRef.current) { clearTimeout(highlightTimerRef.current); highlightTimerRef.current = null; }
    } else if (organIds.length > 0) {
      setHighlightedOrganIds(new Set(organIds));
      showPresetToast(`${preset.label} · 高亮 ${organIds.length} 个关联器官`);
      if (highlightTimerRef.current) clearTimeout(highlightTimerRef.current);
      highlightTimerRef.current = setTimeout(() => { setHighlightedOrganIds(new Set()); highlightTimerRef.current = null; }, 2200);
    } else {
      setHighlightedOrganIds(new Set());
      showPresetToast(`${preset.label}：当前模型暂无相关标签，后续扩展后可联动`);
    }
    setLogs((items) => [`窗宽窗位切换：${preset.label} · WL ${preset.level} / WW ${preset.width}`, ...items].slice(0, 8));
  }

  function showPresetToast(message: string) {
    if (presetToastTimerRef.current) clearTimeout(presetToastTimerRef.current);
    setPresetToast(message);
    presetToastTimerRef.current = setTimeout(() => setPresetToast(null), 2800);
  }

  async function selectCase(nextCase: CaseItem) {
    setSelectedCase(nextCase);
    setShowCaseMenu(false);
    const nextSource = nextCase.sourceImage ?? { src: nextCase.demoImage, name: nextCase.imageName, kind: "Demo" as const, meta: nextCase.imageMeta };
    const nextResult = nextCase.resultImage ?? null;
    const nextSlice = nextSource.sliceIndex ?? Math.floor((nextSource.volume?.slices ?? nextCase.slices) / 2);
    const displaySlice = Math.max(1, nextSlice + 1);
    setSelectedSlice(displaySlice);
    setViewMode("CT");
    setLoadedImage(nextSource);
    setResultImage(nextResult);
    setResultInferenceOptions(null);
    setValidationSummary(null);
    setOrgans(nextCase.organs);
    setSelectedOrganId(nextCase.organs[0].id);
    setMeasurements([{ id: 1, label: "M1", x: 51.8, y: 52.4, hu: 48, diameter: "18.6 mm", slice: displaySlice }]);
    setLogs((items) => [`病例切换：${nextCase.id} · ${nextCase.target}`, ...items].slice(0, 8));
    setLastImport(`${nextCase.custom ? "自定义" : "本地"}病例就绪：${nextCase.id}`);
    if (nextCase.referenceCaseId) {
      setSelectedReferenceCaseId(nextCase.referenceCaseId);
      const referenceCase = referenceCases.find((item) => item.id === nextCase.referenceCaseId)
        ?? DEFAULT_REFERENCE_CASES.find((item) => item.id === nextCase.referenceCaseId);
      if (referenceCase?.hasOriginal) {
        await loadReferenceCase(referenceCase);
      }
    }
  }

  function createCustomCaseFromCurrent() {
    if (!hasLocalSource) {
      setToast("请先导入 CT 原图，再新建自定义病例");
      return;
    }
    const id = buildCustomCaseId(allCases.map((caseItem) => caseItem.id));
    const slices = loadedImage.volume?.slices ?? resultImage?.volume?.slices ?? selectedCase.slices;
    const nextCase: CaseItem = {
      id,
      sex: "自定义",
      age: 0,
      phase: loadedImage.format ?? loadedImage.kind,
      slices,
      target: resultImage ? "自定义原图与结果图" : "自定义原图",
      demoImage: loadedImage.src,
      imageName: loadedImage.name,
      imageMeta: loadedImage.meta,
      organs: organs.map((organ) => ({ ...organ })),
      custom: true,
      sourceImage: loadedImage,
      resultImage
    };
    setCustomCases((items) => [...items, nextCase]);
    void selectCase(nextCase);
    setToast(`已新建自定义病例 ${id}`);
  }

  function customCasesUseSrc(src?: string) {
    return Boolean(src && customCases.some((caseItem) => caseItem.sourceImage?.src === src || caseItem.resultImage?.src === src));
  }

  function revokeCaseAssets(caseItem: CaseItem) {
    revokeObjectUrl(caseItem.sourceImage?.src);
    revokeObjectUrl(caseItem.resultImage?.src);
  }

  function deleteCustomCase(caseId: string) {
    const deletedCase = customCases.find((caseItem) => caseItem.id === caseId);
    if (!deletedCase) return;
    setCustomCases((items) => items.filter((caseItem) => caseItem.id !== caseId));
    if (selectedCase.id === caseId) void selectCase(cases[0]);
    revokeCaseAssets(deletedCase);
    setToast(`已删除自定义病例 ${caseId}`);
  }

  function resetSourceImage() {
    if (!customCasesUseSrc(loadedImage.src)) revokeObjectUrl(loadedImage.src);
    if (!customCasesUseSrc(resultImage?.src)) revokeObjectUrl(resultImage?.src);
    const fallbackSource = selectedCase.sourceImage ?? { src: selectedCase.demoImage, name: selectedCase.imageName, kind: "Demo" as const, meta: selectedCase.imageMeta };
    setLoadedImage(fallbackSource);
    setResultImage(null);
    setResultInferenceOptions(null);
    setLastImport(`本地文件已移除，恢复演示病例：${selectedCase.id}`);
    setToast("本地上传文件已从当前演示中移除");
  }

  function clearResultImage() {
    if (!customCasesUseSrc(resultImage?.src)) revokeObjectUrl(resultImage?.src);
    setResultImage(null);
    setResultInferenceOptions(null);
    setLastImport("结果图已清除，当前使用内置掩膜预览");
    setToast("结果图已移除");
  }

  function requestRemoval(target: RemovalTarget) {
    if (target === "source" && !hasLocalSource) return;
    if (target === "result" && !resultImage) return;
    if (target === "session" && !hasImportedFiles) {
      setToast("当前没有需要清空的本地导入文件");
      return;
    }
    setPendingRemoval(target);
  }

  function confirmRemoval() {
    if (pendingRemoval === "result") clearResultImage();
    if (pendingRemoval === "source" || pendingRemoval === "session") resetSourceImage();
    setPendingRemoval(null);
  }

  async function loadVisualizationFile(file: File): Promise<LoadedImage> {
    const lowerName = file.name.toLowerCase();
    const sizeText = `${(file.size / 1024 / 1024).toFixed(2)} MB`;
    if (lowerName.endsWith(".nii") || lowerName.endsWith(".nii.gz")) {
      const volume = parseNiftiVolume(await file.arrayBuffer());
      const sliceIndex = Math.floor(volume.slices / 2);
      const dimensions = `${volume.columns}x${volume.rows}x${volume.slices}`;
      return {
        src: renderCachedAxialNiftiSliceToDataUrl(volume, sliceIndex),
        name: file.name,
        kind: "NIfTI",
        meta: `${dimensions} 路 ${volume.datatype} 路 ${volume.spacing}`,
        dimensions,
        sizeText,
        format: lowerName.endsWith(".nii.gz") ? "NII.GZ" : "NII",
        volume,
        sliceIndex,
        file
      };
    }
    if (file.type.startsWith("image/") || /\.(png|jpg|jpeg|webp)$/i.test(lowerName)) {
      const src = URL.createObjectURL(file);
      const dimensions = await getImageDimensions(src).catch(() => undefined);
      return {
        src,
        name: file.name,
        kind: "Image",
        meta: `${sizeText} · ${dimensions ?? "浏览器预览"}`,
        dimensions,
        sizeText,
        format: getReadableFileType(file, "IMAGE"),
        file
      };
    }
    throw new Error("暂不支持该格式。请上传 PNG/JPG/WebP 或 NIfTI(.nii/.nii.gz) 文件。");
  }

  async function processVisualizationFile(file: File, role: UploadRole) {
    if (role === "label") {
      setLabelFile(file);
      setToast(`标签文件已选择：${file.name}`);
      return;
    }
    const image = await loadVisualizationFile(file);
    if (role === "source") {
      setLoadedImage(image);
      setValidationSummary(null);
      if (image.volume) setSelectedSlice((image.sliceIndex ?? Math.floor(image.volume.slices / 2)) + 1);
      if (image.volume) setVoxelCoord({ x: Math.floor(image.volume.columns / 2), y: Math.floor(image.volume.rows / 2), z: image.sliceIndex ?? Math.floor(image.volume.slices / 2) });
      if (image.volume) syncOrganLayers(modelLabels);
      setLogs((items) => [`原图已载入：${file.name}`, ...items].slice(0, 8));
      setToast("原图已载入，可继续导入分割结果对比");
      setLastImport(`原图就绪：${file.name}`);
      return;
    }
    setResultImage(image);
    setResultInferenceOptions(null);
    setValidationSummary(null);
    if (!loadedImage.volume && image.volume) setSelectedSlice((image.sliceIndex ?? Math.floor(image.volume.slices / 2)) + 1);
    if (image.volume) syncOrganLayers(modelLabels);
    setViewMode("CT");
    setCompareMode("split");
    const mismatch = loadedImage.volume && image.volume
      ? !volumesShareDisplayGrid(loadedImage.volume, image.volume)
      : Boolean(image.dimensions && loadedImage.dimensions && image.dimensions !== loadedImage.dimensions);
    setLogs((items) => [`结果图已载入：${file.name}`, ...items].slice(0, 8));
    setToast(mismatch ? "结果图已载入，但尺寸与原图不一致，建议复核配准" : "结果图已载入，正在进行同步对比");
    setLastImport(mismatch ? `结果图需复核：${file.name}` : `结果图就绪：${file.name}`);
  }

  async function loadReferenceCase(referenceCase = selectedReferenceCase): Promise<LoadedImage | null> {
    try {
      if (!referenceCase) throw new Error("未找到可载入的参考病例");
      setSelectedReferenceCaseId(referenceCase.id);
      setSampleLoadState({ status: "loading", message: `正在从本地后端读取 ${referenceCase.name}...` });
      setToast(`正在载入参考病例：${referenceCase.name}`);
      const response = await fetch(getReferenceCaseOriginalUrl(API_ENDPOINT, referenceCase));
      if (!response.ok) throw new Error(`无法从本地后端读取 ${referenceCase.name}，请确认 server 已启动`);
      const buffer = await response.arrayBuffer();
      const file = new File([buffer], referenceCase.originalFilename, { type: "application/octet-stream" });
      const image = await loadVisualizationFile(file);
      setLoadedImage(image);
      setValidationSummary(null);
      if (image.volume) {
        setSelectedSlice((image.sliceIndex ?? Math.floor(image.volume.slices / 2)) + 1);
        setVoxelCoord({ x: Math.floor(image.volume.columns / 2), y: Math.floor(image.volume.rows / 2), z: image.sliceIndex ?? Math.floor(image.volume.slices / 2) });
        syncOrganLayers(modelLabels);
      }
      setLogs((items) => [`内置参考病例已载入：${referenceCase.name} / ${file.name}`, ...items].slice(0, 8));
      setToast(`参考病例已载入：${referenceCase.name}`);
      setSampleLoadState({ status: "ready", message: `${referenceCase.name} 已载入 · ${referenceCase.dataset} · ${referenceCase.validationAvailable ? "有标准答案" : "无标准答案"}` });
      setLastImport(`原图就绪：${file.name}`);
      setActiveModule("分割");
      return image;
    } catch (error) {
      const message = error instanceof Error ? error.message : "内置参考病例载入失败";
      setToast(message);
      setSampleLoadState({ status: "failed", message });
      return null;
    }
  }

  async function handleFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await processVisualizationFile(file, "source");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "文件解析失败");
    } finally {
      event.target.value = "";
    }
  }

  async function handleResultFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    try {
      await processVisualizationFile(file, "result");
    } catch (error) {
      setToast(error instanceof Error ? error.message : "结果图解析失败");
    } finally {
      event.target.value = "";
    }
  }

  function handleLabelFileSelected(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    if (!file) return;
    setLabelFile(file);
    setToast(`标签文件已选择：${file.name}`);
    event.target.value = "";
  }

  function handleDrag(event: DragEvent<HTMLElement>, role: UploadRole | null) {
    event.preventDefault();
    setDragTarget(role);
  }

  async function handleDrop(event: DragEvent<HTMLElement>, role: UploadRole) {
    event.preventDefault();
    setDragTarget(null);
    const file = event.dataTransfer.files?.[0];
    if (!file) return;
    try {
      await processVisualizationFile(file, role);
    } catch (error) {
      setToast(error instanceof Error ? error.message : "鏂囦欢瑙ｆ瀽澶辫触");
    }
  }

  function handleCanvasClick() {
    if (!measureMode) return;
    const nextId = measurements.length + 1;
    const x = 38 + (nextId * 9) % 28;
    const y = 43 + (nextId * 7) % 22;
    setMeasurements((items) => [...items, { id: nextId, label: `M${nextId}`, x, y, hu: windowLevel + nextId * 12, diameter: `${(9 + nextId * 2.4).toFixed(1)} mm`, slice: selectedSlice }].slice(-6));
    setLogs((items) => [`新增测量标记：切片 ${selectedSlice}`, ...items].slice(0, 8));
  }

  function toggleOrgan(id: string) {
    setSelectedOrganId(id);
    setSelectedOrganDetail({ id, coord: voxelCoord });
    setOrgans((items) => items.map((organ) => organ.id === id ? { ...organ, visible: !organ.visible } : organ));
  }

  function setOrganQuality(id: string, quality: QualityState) {
    setSelectedOrganId(id);
    setOrgans((items) => items.map((organ) => organ.id === id ? { ...organ, quality } : organ));
  }

  function switchModule(moduleId: ModuleId) {
    setActiveModule(moduleId);
    setToast(`已切换到${moduleId}模块`);
  }

  function saveReportDraft() {
    setReportState((state) => ({ ...state, draftSaved: true }));
    setToast("报告草稿已保存");
  }

  function queueReportReview() {
    setReportState((state) => ({ ...state, reviewQueued: true }));
    setToast("已加入复核清单");
  }

  function handleExport(overrideFormat?: ReportFormat) {
    const format = overrideFormat ?? selectedExportFormat;
    exportReport({
      caseId: selectedCase.id,
      caseTarget: selectedCase.target,
      modelName: selectedModel.name,
      imageKind: loadedImage.kind,
      imageDimensions: loadedImage.dimensions,
      resultKind: resultImage?.kind ?? "无",
      currentSlice: selectedSlice,
      totalSlices: currentTotalSlices,
      validation: validationSummary,
      quantification: quantificationSummary,
      inferenceStatus,
      organs: displayedOrgans,
      organDetails: ORGAN_DETAIL_MAP,
      measurements,
      timeline: inferenceTimeline,
      aiFindings,
      generatedAt: new Date().toLocaleString("zh-CN"),
    }, format);
    setReportState((state) => ({ ...state, exportCount: state.exportCount + 1, lastExport: new Date().toLocaleTimeString() }));
    setToast(`已导出 ${format.toUpperCase()} 分割报告`);
  }

  return (
    <main className="app-shell">
      <nav className="rail">
        <div className="brand"><BrainCircuit size={25} /></div>
        {moduleItems.map((item) => {
          const Icon = item.icon;
          return (
            <button
              key={item.id}
              className={activeModule === item.id ? "active" : ""}
              data-hint={item.hint}
              title={`${item.id} 路 ${item.hint}`}
              aria-current={activeModule === item.id ? "page" : undefined}
              onClick={() => switchModule(item.id)}
            >
              <Icon size={22} />
              <span>{item.id}</span>
            </button>
          );
        })}
        <div className="rail-status" title="本地演示服务运行中">
          <i />
          <span>本地</span>
        </div>
      </nav>

      <section className="main-stage">
        <input ref={fileInputRef} type="file" hidden accept=".nii,.nii.gz,.png,.jpg,.jpeg,.webp,image/*" onChange={handleFileSelected} />
        <input ref={resultFileInputRef} type="file" hidden accept=".nii,.nii.gz,.png,.jpg,.jpeg,.webp,image/*" onChange={handleResultFileSelected} />
        <input ref={labelFileInputRef} type="file" hidden accept=".nii,.nii.gz" onChange={handleLabelFileSelected} />

        <header className="topbar">
          <div>
            <h1>智能 CT 器官分割工作站</h1>
            <p>原图与分割结果图对比可视化</p>
          </div>
          <div className="case-wrap">
            <button className="case-selector" onClick={() => setShowCaseMenu((value) => !value)}>
              <Stethoscope size={18} />
              <span>{selectedCase.id}</span>
              <ChevronDown size={16} />
            </button>
            {showCaseMenu ? (
              <div className="case-menu">
                {allCases.map((caseItem) => (
                  <div key={caseItem.id} className={caseItem.custom ? "case-row custom-case-row" : "case-row"}>
                    <button className={selectedCase.id === caseItem.id ? "case-option active" : "case-option"} onClick={() => void selectCase(caseItem)}>
                      <strong>{caseItem.id}</strong>
                      <span>{caseItem.caseSummary ?? `${caseItem.sex} · ${caseItem.age || "-"} 岁 · ${caseItem.phase}`}</span>
                      <small>{caseItem.target} · {caseItem.slices} 层</small>
                    </button>
                    {caseItem.custom ? (
                      <button className="case-delete" title="删除自定义病例" aria-label={`删除 ${caseItem.id}`} onClick={() => deleteCustomCase(caseItem.id)}>
                        <Trash2 size={15} />
                      </button>
                    ) : null}
                  </div>
                ))}
                <button className="case-create" onClick={createCustomCaseFromCurrent} disabled={!hasLocalSource}>
                  <Plus size={15} />
                  <span>从当前上传新建病例</span>
                </button>
              </div>
            ) : null}
          </div>
          <div className="top-actions">
            <button className="ghost-button" onClick={() => fileInputRef.current?.click()}><Upload size={17} />导入 CT 原图</button>
            <button className="ghost-button" onClick={() => resultFileInputRef.current?.click()}><Upload size={17} />导入分割结果</button>
            <button className={`ghost-button${labelFile ? " is-selected" : ""}`} onClick={() => labelFileInputRef.current?.click()} title={labelFile?.name}><Upload size={17} />{labelFile ? `标签：${labelFile.name.length > 18 ? labelFile.name.slice(0, 18) + "…" : labelFile.name}` : "导入标签 CT"}</button>
            <button className="ghost-button" onClick={() => void loadReferenceCase()}><Database size={17} />载入参考病例</button>
            <button className="primary-button" onClick={() => runState === "running" ? void cancelSegmentation() : void startSegmentation()} disabled={inferenceStatus.status === "submitting"}>
              {runState === "running" ? <Pause size={17} /> : <Play size={17} />}
              {inferenceStatus.status === "submitting" ? "提交中" : runState === "running" ? "取消推理" : "运行分割"}
            </button>
            <div className="export-group">
              <select value={selectedExportFormat} onChange={(e) => setSelectedExportFormat(e.target.value as ReportFormat)} className="export-format-select">
                <option value="html">HTML</option>
                <option value="json">JSON</option>
                <option value="pdf">PDF</option>
              </select>
              <button className="ghost-button" onClick={() => handleExport()}><Download size={17} />导出报告</button>
            </div>
          </div>
        </header>

        <section className="content-grid">
          <section className="study-column">
            <div className="viewer-toolbar">
              <div className="tool-group">
                <button title="窗宽窗位" onClick={() => setWindowLevel((value) => value === 40 ? 80 : 40)}><SlidersHorizontal size={18} /></button>
                <button title="缩放" onClick={() => setZoom((value) => value >= 1.18 ? 1 : value + 0.09)}><ZoomIn size={18} /></button>
                <button title="重置视图" onClick={resetView}><RotateCcw size={18} /></button>
                <button className={measureMode ? "active-tool" : ""} title="测量标记" onClick={() => setMeasureMode((value) => !value)}><MousePointer2 size={18} /></button>
                <button className={heatmapVisible ? "active-tool" : ""} title="AI 热区提示" onClick={() => setHeatmapVisible((value) => !value)}><Target size={18} /></button>
                <button className={compareMode === "split" ? "active-tool" : ""} title="前后对比" onClick={() => setCompareMode("split")}><Columns2 size={18} /></button>
              </div>
              <div className="scan-status">
                <CircleDot size={12} />
                切片 {selectedSlice}/{currentTotalSlices} · WL {windowLevel}/WW {windowWidth} · {zoom.toFixed(2)}x
              </div>
              <div className="preset-strip" aria-label="窗宽窗位预设">
                {windowPresets.map((preset) => (
                  <button key={preset.id} className={activePresetId === preset.id ? "active-preset" : ""} onClick={() => applyWindowPreset(preset)}>{preset.label}</button>
                ))}
              </div>
              {presetToast ? <div className="preset-toast">{presetToast}</div> : null}
              <label className="range-control slice-range">
                切片
                <input type="range" min="1" max={currentTotalSlices} value={selectedSlice} onChange={(event) => setSelectedSlice(Number(event.target.value))} />
                <span>{selectedSlice}/{currentTotalSlices}</span>
              </label>
              <label className="range-control">
                透明度
                <input type="range" min="20" max="85" value={maskOpacity} onChange={(event) => setMaskOpacity(Number(event.target.value))} />
                <span>{maskOpacity}%</span>
              </label>
              {compareMode === "split" ? (
                <label className="range-control compare-range">
                  分屏
                  <input type="range" min="25" max="75" value={comparePosition} onChange={(event) => setComparePosition(Number(event.target.value))} />
                  <span>{comparePosition}%</span>
                </label>
              ) : null}
              <div className="tool-group">
                {(["split", "overlay", "side", "difference"] as CompareMode[]).map((mode) => (
                  <button key={mode} className={compareMode === mode ? "active-tool" : ""} onClick={() => setCompareMode(mode)}>
                    {mode === "split" ? "分屏" : mode === "overlay" ? "叠加" : mode === "side" ? "并排" : "差异"}
                  </button>
                ))}
              </div>
              <div className="tool-help-strip" aria-label="工具栏说明">
                {toolbarHints.map((item) => (
                  <span key={item.label}>
                    <strong>{item.label}</strong>
                    <small>{item.detail}</small>
                  </span>
                ))}
              </div>
            </div>

            <div
              className={`viewer-frame mode-${viewMode.toLowerCase()} compare-${compareMode}`}
              style={{
                "--mask-opacity": maskOpacity / 100,
                "--compare-position": `${comparePosition}%`,
                "--image-contrast": imageContrast,
                "--image-brightness": imageBrightness,
                "--display-aspect-ratio": displayAspectRatio
              } as CSSProperties}
            >
              <div className="ruler horizontal" />
              <div className="ruler vertical" />
              <div className={measureMode ? "ct-canvas measure-mode" : "ct-canvas"} style={{ "--zoom": zoom } as CSSProperties} onClick={handleCanvasClick}>
                {viewMode === "3D" ? (
                  <div className="volume-preview">
                    {organs.filter((organ) => organ.visible).map((organ, index) => (
                      <span className={`volume-lobe volume-${organ.id}`} key={organ.id} style={{ "--organ-color": organ.color, "--i": index } as CSSProperties} />
                    ))}
                  </div>
                ) : loadedImage.volume ? (
                  <div className="orthogonal-shell">
                    <OrthogonalViewer
                      sourceVolume={loadedImage.volume}
                      maskVolume={resultImage?.volume}
                      coord={voxelCoord}
                      opacity={maskOpacity}
                      compareMode={compareMode}
                      visibleLabels={visibleLabels}
                      labels={modelLabels}
                      sourceName={loadedImage.name}
                      resultName={resultImage?.name}
                      onCoordChange={handleVoxelCoordChange}
                      onOrganPick={(label, coord) => {
                        const organLabel = labelLookup.byLabel.get(label);
                        if (!organLabel) return;
                        setSelectedOrganId(organLabel.id);
                        setSelectedOrganDetail({ id: organLabel.id, label, coord });
                      }}
                    />
                    {selectedOrganDetail ? (
                      <OrganDetailCard
                        organId={selectedOrganDetail.id}
                        label={selectedOrganDetail.label}
                        coord={selectedOrganDetail.coord}
                        onClose={() => setSelectedOrganDetail(null)}
                      />
                    ) : null}
                  </div>
                ) : (
                  <div className="sample-load-panel">
                    <Database size={34} />
                    <strong>{sampleLoadState.status === "loading" ? "正在载入内置参考病例" : sampleLoadState.status === "failed" ? "内置参考病例载入失败" : "等待载入胸腹部 CT 原图"}</strong>
                    <span>{sampleLoadState.message} · 当前文件：{loadedImage.name} · 类型：{loadedImage.kind} · 未检测到 NIfTI 体数据</span>
                    <div>
                      <button onClick={() => void loadReferenceCase()} disabled={sampleLoadState.status === "loading"}>
                        <Database size={16} />{sampleLoadState.status === "loading" ? "载入中" : "载入参考病例"}
                      </button>
                      <button onClick={() => fileInputRef.current?.click()}>
                        <Upload size={16} />导入 NIfTI
                      </button>
                    </div>
                  </div>
                )}
                <div className="crosshair x" />
                <div className="crosshair y" />
              </div>
              <div className={`viewer-caption registration-${registrationStatus.severity}`}>
                <span>
                  <strong>原图</strong>
                  <em>{loadedImage.name}</em>
                  <small>{alignmentCaption.sourceDimension}</small>
                </span>
                <span className="registration-caption">
                  <strong>{alignmentCaption.statusTitle}</strong>
                  <em>{alignmentCaption.statusDetail}</em>
                </span>
                <span>
                  <strong>结果</strong>
                  <em>{resultImage?.name ?? "内置掩膜预览"}</em>
                  <small>{alignmentCaption.resultDimension}</small>
                </span>
              </div>
            </div>
          </section>

          <aside className="inspector">
            {activeModule === "项目" ? (
              <>
                <section className="panel module-card">
                  <div className="panel-title">
                    <div>
                      <h2>项目总览</h2>
                      <p>{selectedCase.id} · {selectedCase.target}</p>
                    </div>
                    <FolderOpen size={24} />
                  </div>
                  <div className="module-kpis">
                    <Metric label="病例阶段" value={selectedCase.phase} />
                    <Metric label="切片数" value={`${currentTotalSlices}`} />
                    <Metric label="当前模块" value={activeModule} />
                  </div>
                </section>
                <section className="panel insight-card">
                  <div className="section-head"><h2><Sparkles size={18} />项目提示</h2></div>
                  <div className="finding-list">
                    <div className="finding-row"><CheckCircle2 size={15} /><span>支持本地图片与 .nii/.nii.gz 体数据可视化。</span></div>
                    <div className="finding-row"><CheckCircle2 size={15} /><span>原图体数据与标签体数据共用同一切片滑块，便于同步对比。</span></div>
                  </div>
                </section>
              </>
            ) : null}

            {activeModule === "数据" ? (
              <>
                <section className="panel file-card">
                  <div className="section-head">
                    <h2><Database size={18} />对比文件</h2>
                    <span className="detail-chip">{compareModeLabel[compareMode]}</span>
                  </div>
                  <div className="file-stack">
                    <div className="file-preview-card">
                      <div className="file-thumb"><img src={loadedDisplaySrc} alt={`${loadedImage.name} 预览`} /></div>
                      <div className="file-meta">
                        <strong>原图 · {loadedImage.name}</strong>
                        <span>{loadedImage.meta}</span>
                        <div className="file-tags">
                          <small>{loadedImage.kind}</small>
                          <small>{loadedImage.format ?? "DEMO"}</small>
                          <small>{loadedImage.sizeText ?? "内置资源"}</small>
                        </div>
                        <div className="file-card-actions">
                          <button className="danger-action" onClick={() => requestRemoval("source")} disabled={!hasLocalSource}><Trash2 size={14} />移除本地原图</button>
                        </div>
                      </div>
                    </div>
                    <div className="file-preview-card">
                      <div className={resultImage ? "file-thumb" : "file-thumb simulated"}><img src={resultDisplaySrc ?? loadedDisplaySrc} alt={`${resultImage?.name ?? "模拟结果"} 预览`} /></div>
                      <div className="file-meta">
                        <strong>结果 · {resultImage?.name ?? "内置掩膜预览"}</strong>
                        <span>{resultImage?.meta ?? "未导入分割结果时，前端使用内置掩膜进行对比演示。"}</span>
                        <div className="file-tags">
                          <small>{resultImage?.kind ?? "掩膜"}</small>
                          <small>{resultImage?.format ?? "SIM"}</small>
                          <small>{resultImage?.sizeText ?? "前端生成"}</small>
                        </div>
                        <div className="file-card-actions">
                          <button className="danger-action" onClick={() => requestRemoval("result")} disabled={!resultImage}><Trash2 size={14} />移除结果图</button>
                        </div>
                      </div>
                    </div>
                  </div>
                </section>
                <section className="panel">
                  <div className="section-head"><h2><Upload size={18} />数据操作</h2><span className="detail-chip">{resultImage ? "对比就绪" : "等待结果"}</span></div>
                  <div className="drop-grid">
                    <button className={dragTarget === "source" ? "drop-zone active" : "drop-zone"} onClick={() => fileInputRef.current?.click()} onDragEnter={(event) => handleDrag(event, "source")} onDragOver={(event) => handleDrag(event, "source")} onDragLeave={(event) => handleDrag(event, null)} onDrop={(event) => handleDrop(event, "source")}>
                      <Upload size={18} /><strong>原图导入</strong><span>PNG / JPG / WebP / NIfTI</span>
                    </button>
                    <button className={dragTarget === "result" ? "drop-zone active" : "drop-zone"} onClick={() => resultFileInputRef.current?.click()} onDragEnter={(event) => handleDrag(event, "result")} onDragOver={(event) => handleDrag(event, "result")} onDragLeave={(event) => handleDrag(event, null)} onDrop={(event) => handleDrop(event, "result")}>
                      <FileStack size={18} /><strong>结果图导入</strong><span>掩膜 / 叠加图 / NIfTI 标签</span>
                    </button>
                    <button className={`${dragTarget === "label" ? "drop-zone active" : "drop-zone"}${labelFile ? " has-file" : ""}`} onClick={() => labelFileInputRef.current?.click()} onDragEnter={(event) => handleDrag(event, "label")} onDragOver={(event) => handleDrag(event, "label")} onDragLeave={(event) => handleDrag(event, null)} onDrop={(event) => handleDrop(event, "label")} title={labelFile?.name}>
                      <Upload size={18} /><strong>标签 CT 导入</strong><span>{labelFile ? labelFile.name : "NIfTI 标签文件 · 用于自动 Dice 验证"}</span>
                    </button>
                  </div>
                  <div className="readiness-card"><div><span>实时载入状态</span><strong>{lastImport}</strong></div><BadgeCheck size={19} /></div>
                  <div className="custom-case-card">
                    <div>
                      <span>自定义病例</span>
                      <strong>{customCasePanelCopy.countLabel}</strong>
                      <small>{customCasePanelCopy.saveHint}</small>
                    </div>
                    <div className="custom-case-actions">
                      <button onClick={createCustomCaseFromCurrent} disabled={!customCasePanelCopy.canSave}><Plus size={15} />保存当前病例</button>
                      <button className="danger-action" onClick={() => deleteCustomCase(selectedCase.id)} disabled={!customCasePanelCopy.canDeleteSelected}><Trash2 size={15} />删除当前病例</button>
                    </div>
                  </div>
                  <div className="ready-list">
                    {readinessChecks.map((item) => (
                      <div className={item.ready ? "ready-item ready" : "ready-item"} key={item.label}>
                        <CheckCircle2 size={14} /><span>{item.label}</span><strong>{item.value}</strong>
                      </div>
                    ))}
                  </div>
                  <div className="action-stack">
                    <div className="reference-case-control">
                      <label htmlFor="reference-case-data">参考病例</label>
                      <select id="reference-case-data" value={selectedReferenceCaseId} onChange={(event) => setSelectedReferenceCaseId(event.target.value)}>
                        {referenceCases.map((item) => <option key={item.id} value={item.id} disabled={!item.hasOriginal}>{item.name}{item.hasOriginal ? "" : "（原图缺失）"}</option>)}
                      </select>
                      <small>{selectedReferenceCaseMeta}</small>
                    </div>
                    <button onClick={() => fileInputRef.current?.click()}><Upload size={16} />导入 CT 原图</button>
                    <button onClick={() => void loadReferenceCase()} disabled={!canLoadSelectedReferenceCase}><Database size={16} />载入参考病例</button>
                    <button onClick={() => resultFileInputRef.current?.click()}><Upload size={16} />导入分割结果</button>
                    <button onClick={() => requestRemoval("result")} disabled={!resultImage}><Trash2 size={16} />清除结果</button>
                    <button onClick={() => requestRemoval("session")} disabled={!hasImportedFiles}><RotateCcw size={16} />清空本次导入</button>
                  </div>
                </section>
                <section className="panel metric-panel">
                  <h2><Gauge size={18} />对比状态</h2>
                  {comparisonStats.map((item) => <Metric key={item.label} label={item.label} value={item.value} />)}
                </section>
              </>
            ) : null}

            {activeModule === "分割" ? (
              <>
                <section className="panel">
                  <div className="section-head"><h2><ScanLine size={18} />分割控制</h2><span className="detail-chip">{runState === "running" ? `${progress}%` : "可操作"}</span></div>
                  <div className="model-list">
                    {modelOptions.map((model) => (
                      <div key={model.id} className="model-card active">
                        <strong>{model.name}</strong>
                        <span>{model.scope}</span>
                        <small className="model-detail">{model.detail}</small>
                      </div>
                    ))}
                    <div className="organ-category-grid">
                      <div className="organ-category"><i /><span>消化系统</span><small>肝脏 · 胰腺 · 胆囊 · 胃 · 食管 · 十二指肠</small></div>
                      <div className="organ-category"><i /><span>泌尿系统</span><small>左肾 · 右肾 · 膀胱</small></div>
                      <div className="organ-category"><i /><span>血管结构</span><small>主动脉 · 下腔静脉</small></div>
                      <div className="organ-category"><i /><span>其他器官</span><small>脾脏 · 双侧肾上腺 · 前列腺/子宫</small></div>
                    </div>
                  </div>
                  <div className="option-section-label">运行位置</div>
                  <div className="inference-profile-grid" aria-label="运行位置">
                    {runtimeTargetOptions.map((target) => {
                      const isSelected = selectedRuntimeTarget === target.id;
                      return (
                        <button
                          key={target.id}
                          type="button"
                          className={isSelected ? "profile-option runtime-option active" : "profile-option runtime-option"}
                          aria-pressed={isSelected}
                          disabled={inferenceOptionsLocked}
                          onClick={() => {
                            if (inferenceOptionsLocked) return;
                            setSelectedRuntimeTarget(target.id);
                            setLogs((items) => [`已选择运行位置：${target.label}`, ...items].slice(0, 8));
                          }}
                        >
                          <span className="option-title"><span>{isSelected ? "已选择" : inferenceOptionsLocked ? "已锁定" : "可选择"}</span>{target.label}</span>
                          <strong>{target.detail}</strong>
                          <small>{target.meta}</small>
                        </button>
                      );
                    })}
                  </div>
                  <div className="option-section-label">推理模式</div>
                  <div className="inference-profile-grid" aria-label="推理模式">
                    {inferenceProfileOptions.map((profile) => {
                      const isSelected = selectedInferenceProfile === profile.id;
                      return (
                        <button
                          key={profile.id}
                          type="button"
                          className={isSelected ? "profile-option active" : "profile-option"}
                          aria-pressed={isSelected}
                          disabled={inferenceOptionsLocked}
                          onClick={() => {
                            if (inferenceOptionsLocked) return;
                            setSelectedInferenceProfile(profile.id);
                            setLogs((items) => [`已选择推理模式：${profile.label}`, ...items].slice(0, 8));
                          }}
                        >
                          <span className="option-title"><span>{isSelected ? "已选择" : inferenceOptionsLocked ? "已锁定" : "可选择"}</span>{profile.label}</span>
                          <strong>{profile.detail}</strong>
                          <small>{profile.meta}</small>
                        </button>
                      );
                    })}
                  </div>
                  <div className="option-section-label">标签体系</div>
                  <div className="inference-profile-grid" aria-label="标签体系">
                    {labelTaxonomyOptions.map((taxonomy) => {
                      const isSelected = selectedLabelTaxonomy === taxonomy.id;
                      return (
                        <button
                          key={taxonomy.id}
                          type="button"
                          className={isSelected ? "profile-option active" : "profile-option"}
                          aria-pressed={isSelected}
                          disabled={inferenceOptionsLocked}
                          onClick={() => {
                            if (inferenceOptionsLocked) return;
                            setSelectedLabelTaxonomy(taxonomy.id);
                            setLogs((items) => [`已选择标签体系：${taxonomy.label}`, ...items].slice(0, 8));
                          }}
                        >
                          <span className="option-title"><span>{isSelected ? "已选择" : inferenceOptionsLocked ? "已锁定" : "可选择"}</span>{taxonomy.label}</span>
                          <strong>{taxonomy.detail}</strong>
                          <small>{taxonomy.meta}</small>
                        </button>
                      );
                    })}
                  </div>
                  <div className="runtime-selection-summary">
                    当前{inferenceOptionsLocked ? "已锁定" : "将提交到"}：<strong>{selectedRuntimeTargetOption.label}</strong> · {selectedInferenceProfileOption.label} · {selectedLabelTaxonomyOption.label}
                  </div>
                  {fastProfileNeedsReview ? (
                    <div className="profile-warning">
                      <AlertTriangle size={16} />
                      <span>快速预览仅用于缩短等待时间，结果需人工复核，不能作为正式报告依据。</span>
                    </div>
                  ) : null}
                  <label className="slider-row">质控提示<input type="range" min="50" max="95" value={confidenceThreshold} onChange={(event) => setConfidenceThreshold(Number(event.target.value))} /><strong>{confidenceThreshold}%</strong></label>
                  <div className="toggle-grid">
                    {Object.entries(postprocessConfig).map(([key, checked]) => (
                      <button key={key} className={checked ? "toggle-card on" : "toggle-card"} onClick={() => setPostprocessConfig((config) => ({ ...config, [key]: !config[key as keyof typeof postprocessConfig] }))}>
                        {checked ? <Eye size={15} /> : <EyeOff size={15} />} {key === "removeIslands" ? "去除孤岛" : key === "smoothBoundary" ? "边界平滑" : "填充空洞"}
                      </button>
                    ))}
                  </div>
                  <div className="action-stack">
                    <div className="reference-case-control">
                      <label htmlFor="reference-case-segmentation">参考病例</label>
                      <select id="reference-case-segmentation" value={selectedReferenceCaseId} onChange={(event) => setSelectedReferenceCaseId(event.target.value)}>
                        {referenceCases.map((item) => <option key={item.id} value={item.id} disabled={!item.hasOriginal}>{item.name}{item.hasOriginal ? "" : "（原图缺失）"}</option>)}
                      </select>
                      <small>{selectedReferenceCaseMeta}</small>
                    </div>
                    <button onClick={() => void loadReferenceCase()} disabled={!canLoadSelectedReferenceCase}><Database size={16} />载入参考病例</button>
                    <button onClick={() => runState === "running" ? void cancelSegmentation() : void startSegmentation()} disabled={inferenceStatus.status === "submitting"}>
                      {runState === "running" ? <Pause size={16} /> : <Play size={16} />}{inferenceStatus.status === "submitting" ? "提交中" : runState === "running" ? "取消推理" : "运行分割流程"}
                    </button>
                  </div>
                  <div className={`validation-card ${validationSummary?.status ?? "pending"}`}>
                    <div>
                      <span>标签验证</span>
                      <strong>{validationStatusCopy}</strong>
                      <small>{validationMessage}</small>
                    </div>
                    <BadgeCheck size={19} />
                  </div>
                </section>
                <section className="panel">
                  <div className="section-head"><h2><Layers3 size={18} />器官图层</h2><span className="detail-chip">{visibleOrgans.size}/{organs.length}</span></div>
                  <div className="organ-list">
                    {organs.map((organ) => {
                      const isActive = selectedOrganId === organ.id;
                      const isHighlight = highlightedOrganIds.has(organ.id);
                      const cls = ["organ-row", isActive && "active", isHighlight && "highlight"].filter(Boolean).join(" ");
                      const quantification = quantificationById.get(organ.id);
                      return (
                        <button key={organ.id} className={cls} onClick={() => toggleOrgan(organ.id)}>
                          <i style={{ background: organ.color }} /><span>{organ.name}</span><small>{quantification?.status === "computed" ? formatQuantificationValue(quantification.volumeMl, "ml") : organ.volume}</small><strong>{formatOrganScore(organ.score)}</strong>
                        </button>
                      );
                    })}
                  </div>
                </section>
              </>
            ) : null}

            {activeModule === "评估" ? (
              <>
                <section className="panel metric-panel">
                  <h2><BarChart3 size={18} />质量评估</h2>
                  <Metric label="平均 Dice" value={displayedAverageDice} />
                  <Metric label="最低 Dice" value={formatDiceMetric(validationSummary?.min_dice)} />
                  <Metric label="前景 Dice" value={formatDiceMetric(validationSummary?.foreground_dice)} />
                  <Metric label="标签验证" value={validationStatusCopy} />
                  {validationSummary?.remap_applied ? <Metric label="标签重映射" value={`${validationSummary.remap_source ?? "已知数据集"} → 当前模型`} /> : null}
                  <Metric label="运行位置" value={selectedRuntimeTargetOption.label} />
                  <Metric label="推理模式" value={resultProfileCopy} />
                  <Metric label="推理耗时" value={inferenceDurationCopy} />
                  <Metric label="瓶颈阶段" value={inferencePhaseTimingCopy} />
                  <Metric label="结果大小" value={inferenceResultSizeCopy} />
                  <Metric label="资源快照" value={inferenceResourceCopy} />
                  <Metric label="待复核器官" value={`${reviewCount}`} />
                  <Metric label="配准状态" value={volumeRegistration} />
                </section>
                <section className="panel quantification-panel">
                  <div className="section-head"><h2><Gauge size={18} />影像量化分析</h2><span className="detail-chip">{computedQuantificationOrgans.length}/{quantificationSummary.organs.length}</span></div>
                  <p className="panel-note">{quantificationStatusCopy}</p>
                  <div className="quantification-table">
                    <div className="quantification-row head"><span>器官</span><span>体积</span><span>最大横断面积</span><span>估算长度</span><span>最长径</span></div>
                    {(quantificationPreviewOrgans.length ? quantificationPreviewOrgans : quantificationSummary.organs.slice(0, 4)).map((organ) => (
                      <div className="quantification-row" key={organ.id}>
                        <span>{organ.name}</span>
                        <span>{formatQuantificationValue(organ.volumeMl, "ml")}</span>
                        <span>{formatQuantificationValue(organ.maxAxialAreaMm2, "mm²")}</span>
                        <span>{formatQuantificationValue(organ.estimatedLengthMm, "mm")}</span>
                        <span>{formatQuantificationValue(organ.maxDiameterMm, "mm")}</span>
                      </div>
                    ))}
                  </div>
                  <small>{computedQuantificationOrgans[0]?.lumenAreaInterpretation ?? "体积、截面积和长度由自动分割 mask 与 NIfTI spacing 估算。"}</small>
                  <small>{computedQuantificationOrgans[0]?.wallThicknessStatus ?? "壁厚和精确管腔指标需专用标签或后续算法。"}</small>
                </section>
                <section className="panel">
                  <div className="section-head"><h2><ClipboardCheck size={18} />质控标记</h2></div>
                  <div className="organ-list">
                    {organs.map((organ) => (
                      <div className="qc-row" key={organ.id}>
                        <span>{organ.name}</span>
                        <button onClick={() => setOrganQuality(organ.id, "accepted")}>通过</button>
                        <button onClick={() => setOrganQuality(organ.id, "review")}>复核</button>
                      </div>
                    ))}
                  </div>
                </section>
                <section className="panel insight-card">
                  <div className="section-head"><h2><Sparkles size={18} />AI 发现</h2></div>
                  <div className="finding-list">{aiFindings.map((finding) => <div className="finding-row" key={finding}><CheckCircle2 size={15} /><span>{finding}</span></div>)}</div>
                </section>
              </>
            ) : null}

            {activeModule === "报告" ? (
              <>
                <section className="panel metric-panel">
                  <h2><FileText size={18} />报告状态</h2>
                  <Metric label="草稿" value={reportState.draftSaved ? "已保存" : "未保存"} />
                  <Metric label="复核" value={reportState.reviewQueued ? "已入队" : "未入队"} />
                  <Metric label="导出次数" value={`${reportState.exportCount}`} />
                  <Metric label="最近导出" value={reportState.lastExport} />
                </section>
                <section className="panel">
                  <div className="section-head"><h2><Download size={18} />报告操作</h2></div>
                  <div className="action-stack">
                    <button onClick={() => setShowReport(true)}><FileText size={16} />打开报告预览</button>
                    <button onClick={saveReportDraft}><ClipboardCheck size={16} />保存报告草稿</button>
                    <div className="export-format-buttons">
                      <button onClick={() => handleExport("html")}><FileText size={14} />HTML</button>
                      <button onClick={() => handleExport("json")}><Download size={14} />JSON</button>
                      <button onClick={() => handleExport("pdf")}><FileText size={14} />PDF</button>
                    </div>
                    <button onClick={queueReportReview}><ClipboardCheck size={16} />加入复核清单</button>
                  </div>
                </section>
              </>
            ) : null}
          </aside>
        </section>

        <footer className="bottom-console">
          <div className="console-head">
            <h2><ListChecks size={18} />切片与流程日志</h2>
            <span><Activity size={14} />{inferenceProgressCopy.title}</span>
          </div>
          <section className={`inference-progress-rail is-${inferenceProgressCopy.tone}`} aria-label="实时推理进度">
            <div className="inference-progress-main">
              <div className="inference-progress-top">
                <strong>{inferenceProgressCopy.stage}</strong>
                <span>{inferenceProgressCopy.percentCopy}</span>
              </div>
              <div className="inference-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={100} aria-valuenow={inferenceProgressCopy.percent}>
                <span style={{ width: `${inferenceProgressCopy.percent}%` }} />
              </div>
              <div className="inference-progress-meta">
                <span>{inferenceProgressCopy.jobCopy}</span>
                <span>{inferenceProgressCopy.profileCopy}</span>
                <span>耗时 {inferenceProgressCopy.elapsedCopy}</span>
                <span>SSE 阶段事件</span>
              </div>
            </div>
            <ol className="inference-timeline" aria-label="推理阶段日志">
              {(inferenceTimeline.length ? inferenceTimeline : [{
                id: "timeline-idle",
                type: "info" as const,
                progress: 0,
                stage: "等待在线推理",
                message: "尚未收到后端阶段事件",
                at: Date.now()
              }]).slice(0, 3).map((entry) => (
                <li key={entry.id} data-kind={entry.type}>
                  <span>{entry.progress === undefined ? entry.type === "error" ? "ERR" : entry.type === "cancelled" ? "STOP" : "INFO" : `${entry.progress}%`}</span>
                  <p>{entry.message ?? entry.stage}</p>
                  <time>{formatClockTime(entry.at)}</time>
                </li>
              ))}
            </ol>
          </section>
          <div className="footer-slices" aria-label="底部切片时间轴">
            {footerSlicePreviews.map(({ slice, src }) => (
              <button className={selectedSlice === slice ? "footer-slice active" : "footer-slice"} key={slice} onClick={() => setSelectedSlice(slice)}>
                <img src={src} alt="" />
                <span>{slice}</span>
              </button>
            ))}
          </div>
          <div className="log-grid">
            {logs.slice(0, 4).map((log, index) => (
              <div className="log-line" key={`${log}-${index}`}>
                <ClipboardCheck size={16} />
                <span>{String(index + 1).padStart(2, "0")}</span>
                <p>{log}</p>
              </div>
            ))}
          </div>
        </footer>
      </section>

      {pendingRemoval ? (
        <section className="report-modal" role="dialog" aria-label="确认移除文件">
          <div className="confirm-card">
            <h2>{pendingRemoval === "result" ? "移除结果图？" : pendingRemoval === "source" ? "移除本地原图？" : "清空本次导入？"}</h2>
            <p>该操作只会移除当前浏览器会话中的文件，不会删除你电脑磁盘上的原始文件。</p>
            <div className="modal-actions">
              <button onClick={() => setPendingRemoval(null)}>取消</button>
              <button className="danger-action" onClick={confirmRemoval}>确认移除</button>
            </div>
          </div>
        </section>
      ) : null}

      {showReport ? (
        <section className="report-modal" role="dialog" aria-label="分割报告预览">
          <div className="report-sheet">
            <header>
              <div><h2>分割报告预览</h2><p>{selectedCase.id} · {selectedCase.target} · 自动生成</p></div>
              <button onClick={() => setShowReport(false)} title="关闭报告"><X size={20} /></button>
            </header>
            <div className="report-summary">
              <Metric label="模型" value={selectedModel.name} />
              <Metric label="平均 Dice" value={displayedAverageDice} />
              <Metric label="原图" value={loadedImage.kind} />
              <Metric label="结果" value={resultImage ? resultImage.kind : "模拟掩膜"} />
              <Metric label="同步切片" value={`${selectedSlice}/${currentTotalSlices}`} />
              <Metric label="配准" value={volumeRegistration} />
            </div>
            <div className="report-body">
              <h3>关键发现</h3>
              {aiFindings.map((finding) => <p key={finding}>- {finding}</p>)}
              <h3>量化指标</h3>
              <div className="quantification-table report-quantification-table">
                <div className="quantification-row head"><span>器官</span><span>体积</span><span>最大横断面积</span><span>估算长度</span><span>体素数</span></div>
                {(quantificationPreviewOrgans.length ? quantificationPreviewOrgans : quantificationSummary.organs.slice(0, 4)).map((organ) => (
                  <div className="quantification-row" key={organ.id}>
                    <span>{organ.name}</span>
                    <span>{formatQuantificationValue(organ.volumeMl, "ml")}</span>
                    <span>{formatQuantificationValue(organ.maxAxialAreaMm2, "mm²")}</span>
                    <span>{formatQuantificationValue(organ.estimatedLengthMm, "mm")}</span>
                    <span>{organ.voxelCount || "—"}</span>
                  </div>
                ))}
              </div>
              <p className="panel-note">{quantificationSummary.note} 壁厚和精确管腔指标需专用标签或后续算法。</p>
            </div>
          </div>
        </section>
      ) : null}

      {toast ? <div className="toast">{toast}</div> : null}
    </main>
  );
}

createRoot(document.getElementById("root")!).render(<App />);
