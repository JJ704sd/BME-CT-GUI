export type OrganLabel = {
  label: number;
  id: string;
  nameZh: string;
  nameEn?: string;
  color: string;
  visible?: boolean;
};

export type OrganDetail = {
  id: string;
  nameZh: string;
  nameEn: string;
  anatomicalLocation: string;
  functionSummary: string;
  commonFindings: string;
  segmentationNotes: string;
};

export const defaultOrganLabels: OrganLabel[] = [
  { label: 1, id: "spleen", nameZh: "脾脏", nameEn: "Spleen", color: "#ef8aa8" },
  { label: 2, id: "right-kidney", nameZh: "右肾", nameEn: "Right kidney", color: "#7cc7ff" },
  { label: 3, id: "left-kidney", nameZh: "左肾", nameEn: "Left kidney", color: "#65d6ad" },
  { label: 4, id: "gallbladder", nameZh: "胆囊", nameEn: "Gallbladder", color: "#a5e567" },
  { label: 5, id: "esophagus", nameZh: "食管", nameEn: "Esophagus", color: "#ffd166" },
  { label: 6, id: "liver", nameZh: "肝脏", nameEn: "Liver", color: "#4fd1a5" },
  { label: 7, id: "stomach", nameZh: "胃", nameEn: "Stomach", color: "#b8a2ff" },
  { label: 8, id: "aorta", nameZh: "主动脉", nameEn: "Aorta", color: "#ff6b6b" },
  { label: 9, id: "ivc", nameZh: "下腔静脉", nameEn: "Inferior vena cava", color: "#8ec5ff" },
  { label: 10, id: "pancreas", nameZh: "胰腺", nameEn: "Pancreas", color: "#f4b95f" },
  { label: 11, id: "right-adrenal-gland", nameZh: "右肾上腺", nameEn: "Right adrenal gland", color: "#f28c28" },
  { label: 12, id: "left-adrenal-gland", nameZh: "左肾上腺", nameEn: "Left adrenal gland", color: "#d47cff" },
  { label: 13, id: "duodenum", nameZh: "十二指肠", nameEn: "Duodenum", color: "#ffb86b" },
  { label: 14, id: "bladder", nameZh: "膀胱", nameEn: "Bladder", color: "#70d6ff" },
  { label: 15, id: "prostate-or-uterus", nameZh: "前列腺/子宫", nameEn: "Prostate or uterus", color: "#ffa8d1" }
];

export const organDetails: Record<string, OrganDetail> = {
  liver: {
    id: "liver",
    nameZh: "肝脏",
    nameEn: "Liver",
    anatomicalLocation: "右上腹，位于膈肌下方，邻近胃、胆囊和右肾。",
    functionSummary: "参与代谢、解毒、胆汁分泌、凝血因子合成和糖原储存。",
    commonFindings: "常见关注点包括脂肪肝、肝硬化、囊肿、血管瘤和占位性病变。",
    segmentationNotes: "肝顶、肝门和邻近胃肠气体区域容易出现边界不稳定，需要结合多平面复核。"
  },
  pancreas: {
    id: "pancreas",
    nameZh: "胰腺",
    nameEn: "Pancreas",
    anatomicalLocation: "横跨上腹后腹膜，头部邻近十二指肠，尾部接近脾门。",
    functionSummary: "具有外分泌消化酶和内分泌胰岛素、胰高血糖素分泌功能。",
    commonFindings: "常见关注点包括胰腺炎、囊性病变、萎缩和胰腺肿瘤。",
    segmentationNotes: "胰腺细长且边界与周围脂肪、血管接近，矢状面和冠状面复核很重要。"
  },
  stomach: {
    id: "stomach",
    nameZh: "胃",
    nameEn: "Stomach",
    anatomicalLocation: "位于左上腹和上腹部，连接食管与十二指肠。",
    functionSummary: "负责食物储存、机械搅拌和胃酸、胃蛋白酶相关消化。",
    commonFindings: "胃扩张、壁增厚、肿瘤和术后形态改变会影响分割表现。",
    segmentationNotes: "胃内容物和充盈程度变化大，需警惕与肠管或脾脏边界混淆。"
  },
  gallbladder: {
    id: "gallbladder",
    nameZh: "胆囊",
    nameEn: "Gallbladder",
    anatomicalLocation: "位于肝脏下方胆囊窝内，通过胆囊管连接胆道系统。",
    functionSummary: "储存和浓缩胆汁，并在进食后释放至消化道。",
    commonFindings: "常见关注点包括胆囊结石、胆囊炎、胆囊萎缩和壁增厚。",
    segmentationNotes: "胆囊体积差异大，萎缩或术后缺如时应显示低置信提示。"
  },
  spleen: {
    id: "spleen",
    nameZh: "脾脏",
    nameEn: "Spleen",
    anatomicalLocation: "左上腹，邻近胃底、胰尾和左肾。",
    functionSummary: "参与免疫应答、血细胞过滤和血小板储备。",
    commonFindings: "脾大、梗死、囊肿和外伤改变是常见影像关注点。",
    segmentationNotes: "脾门处与血管和胰尾关系密切，局部切片需复核。"
  },
  "right-kidney": {
    id: "right-kidney",
    nameZh: "右肾",
    nameEn: "Right kidney",
    anatomicalLocation: "位于右侧腹膜后，上极邻近肝脏，下方与腰大肌和肾周脂肪相邻。",
    functionSummary: "负责滤过血液、生成尿液，并参与水电解质平衡和血压调节。",
    commonFindings: "常见关注点包括肾囊肿、积水、结石、萎缩和占位性病变。",
    segmentationNotes: "肾门、集合系统和肾周脂肪边界容易与血管或邻近器官混淆，应结合冠状面复核。"
  },
  "left-kidney": {
    id: "left-kidney",
    nameZh: "左肾",
    nameEn: "Left kidney",
    anatomicalLocation: "位于左侧腹膜后，邻近脾脏、胰尾、胃后壁和腰大肌。",
    functionSummary: "负责滤过血液、生成尿液，并参与酸碱、电解质和容量稳态调节。",
    commonFindings: "常见关注点包括肾囊肿、积水、结石、局灶占位和肾周炎性改变。",
    segmentationNotes: "左肾上极与脾脏、胰尾距离近，横断面和冠状面联动检查可减少边界误判。"
  },
  aorta: {
    id: "aorta",
    nameZh: "主动脉",
    nameEn: "Aorta",
    anatomicalLocation: "位于腹膜后中线偏左，自膈肌下行至髂动脉分叉。",
    functionSummary: "承担全身动脉供血主干功能，将心脏输出血流输送至腹部和下肢分支。",
    commonFindings: "常见关注点包括动脉瘤、夹层、钙化、狭窄和术后支架改变。",
    segmentationNotes: "钙化壁、增强相差异和邻近下腔静脉可能影响边界，需重点检查连续性。"
  },
  ivc: {
    id: "ivc",
    nameZh: "下腔静脉",
    nameEn: "Inferior vena cava",
    anatomicalLocation: "位于腹膜后中线偏右，沿主动脉右侧上行进入肝后段并汇入右心房。",
    functionSummary: "汇集下肢、盆腔和腹部静脉血，是下半身静脉回流的主要通道。",
    commonFindings: "常见关注点包括受压、血栓、扩张、滤器和肝后段显示不清。",
    segmentationNotes: "增强时相和邻近主动脉会影响对比度，应在矢状面和冠状面确认管腔连续性。"
  },
  "right-adrenal-gland": {
    id: "right-adrenal-gland",
    nameZh: "右肾上腺",
    nameEn: "Right adrenal gland",
    anatomicalLocation: "位于右肾上极内侧，邻近肝脏后方和下腔静脉。",
    functionSummary: "分泌糖皮质激素、盐皮质激素和儿茶酚胺，参与应激、血压和代谢调节。",
    commonFindings: "常见关注点包括腺瘤、增生、转移灶和出血。",
    segmentationNotes: "结构细小且与肝脏、下腔静脉距离近，低分辨率或厚层 CT 中需谨慎复核。"
  },
  "left-adrenal-gland": {
    id: "left-adrenal-gland",
    nameZh: "左肾上腺",
    nameEn: "Left adrenal gland",
    anatomicalLocation: "位于左肾上极内侧，邻近胃后壁、脾脏和胰尾。",
    functionSummary: "分泌肾上腺皮质和髓质相关激素，参与代谢、血压和应激反应调节。",
    commonFindings: "常见关注点包括腺瘤、增生、转移灶和出血。",
    segmentationNotes: "左肾上腺呈细长或倒 V 形，容易与血管、胰尾或胃壁边界混淆。"
  },
  esophagus: {
    id: "esophagus",
    nameZh: "食管",
    nameEn: "Esophagus",
    anatomicalLocation: "胸腹交界区位于后纵隔和膈肌食管裂孔附近，腹段连接胃贲门。",
    functionSummary: "负责将食物和液体从咽部输送到胃内。",
    commonFindings: "常见关注点包括壁增厚、扩张、反流相关改变、肿瘤和术后形态改变。",
    segmentationNotes: "管腔可塌陷或含气，腹段与胃贲门交界不清时需要多平面确认。"
  },
  duodenum: {
    id: "duodenum",
    nameZh: "十二指肠",
    nameEn: "Duodenum",
    anatomicalLocation: "位于上腹部，环绕胰头，从幽门延续至空肠起始部。",
    functionSummary: "接收胃内容物、胆汁和胰液，是消化吸收早期过程的重要通道。",
    commonFindings: "常见关注点包括扩张、壁增厚、憩室、炎症和邻近胰头病变受累。",
    segmentationNotes: "十二指肠形态弯曲且含气或含液变化大，胰头周围边界需结合连续切片判断。"
  },
  bladder: {
    id: "bladder",
    nameZh: "膀胱",
    nameEn: "Bladder",
    anatomicalLocation: "位于盆腔前下方，充盈时向上扩展，邻近前列腺、子宫或直肠。",
    functionSummary: "储存尿液，并通过排尿反射将尿液排出体外。",
    commonFindings: "常见关注点包括充盈不足、壁增厚、结石、憩室和术后形态改变。",
    segmentationNotes: "膀胱体积随充盈程度变化明显，低充盈时边界容易与盆腔软组织混淆。"
  },
  "prostate-or-uterus": {
    id: "prostate-or-uterus",
    nameZh: "前列腺/子宫",
    nameEn: "Prostate or uterus",
    anatomicalLocation: "位于盆腔中央区域，男性多对应前列腺，女性多对应子宫。",
    functionSummary: "该标签按 AMOS22 数据集定义合并盆腔生殖器官，用于粗定位和分割质控。",
    commonFindings: "常见关注点包括体积增大、术后缺如、肌瘤、钙化和邻近膀胱或直肠边界不清。",
    segmentationNotes: "该合并标签具有性别相关差异，验收时应结合病例性别和盆腔连续切片复核。"
  }
};

export function buildLabelLookup(labels: OrganLabel[]) {
  return {
    byLabel: new Map(labels.map((label) => [label.label, label])),
    byId: new Map(labels.map((label) => [label.id, label]))
  };
}

export function getOrganDetail(id: string): OrganDetail {
  return organDetails[id] ?? {
    id,
    nameZh: id,
    nameEn: id,
    anatomicalLocation: "当前模型标签表包含该结构，但尚未配置详细解剖说明。",
    functionSummary: "请在器官说明数据库中补充该结构的功能说明。",
    commonFindings: "暂无固定说明，建议结合三正交视图进行人工复核。",
    segmentationNotes: "该标签可用于定位与可见性控制，说明内容待完善。"
  };
}
