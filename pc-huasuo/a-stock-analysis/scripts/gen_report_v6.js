const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, Header, Footer, AlignmentType, HeadingLevel, BorderStyle, WidthType, ShadingType, PageNumber, PageBreak } = require("docx");
const fs = require("fs");

// ============ Helpers ============
const HDR = "1F4E79", GREEN = "D5F5E3", BLUE = "D4E6F1", YELLOW = "FCF3CF", GRAY = "F2F3F4", LIGHT = "EBF5FB", RED_BG = "FADBD8";
const B = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const BORDERS = { top: B, bottom: B, left: B, right: B };
const MW = (d) => ({ size: d, type: WidthType.DXA });
const MG = { top: 40, bottom: 40, left: 60, right: 60 };
const CL = (t, w) => ({ size: t, type: WidthType.DXA });
const FONT = "Microsoft YaHei";

function hCell(text, w, fill) {
  return new TableCell({
    borders: BORDERS, width: MW(w),
    shading: { fill: fill || HDR, type: ShadingType.CLEAR },
    margins: MG,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({ text, bold: true, font: FONT, size: 18, color: (fill === HDR) ? "FFFFFF" : "000000" })]
    })]
  });
}

function bCell(text, w, fill, opts) {
  opts = opts || {};
  var lines = (text || "").split("\\n");
  var children = lines.map((t, i) => new Paragraph({
    spacing: { after: i < lines.length - 1 ? 40 : 0 },
    alignment: opts.align === "center" ? AlignmentType.CENTER : opts.align === "right" ? AlignmentType.RIGHT : AlignmentType.LEFT,
    children: [new TextRun({
      text: t, font: opts.font || FONT, size: opts.size || 18,
      bold: !!opts.bold, color: opts.color || "222222"
    })]
  }));
  return new TableCell({
    borders: BORDERS, width: MW(w),
    shading: { fill: fill || "FFFFFF", type: ShadingType.CLEAR },
    margins: MG, children
  });
}

function pct_s(n) { var v = (n * 100).toFixed(1) + "%"; return n >= 0 ? "+" + v : v; }

// ============ 29 Stocks Data (5/29 close) ============
var stocks = [
  // Layer 1: 算力芯片 (5 stocks)
  { code: "688041.SH", n: "海光信息", l: 1, ln: "算力芯片", px: 293.90, pe: 248, roe: 13.5, rev_g: 0.52, tgt: 320, ups: 0.089, mcap: "6300亿",
    biz: "x86 CPU + DCU AI芯片，党政/金融国产替代核心", cat: "订单上修+DCU放量，受益国产算力需求爆发", risk: "美国出口管制升级、技术路线依赖AMD授权、PE极高", op: "等回调至260元（-11.5%）分批建仓，仓位5%", sc: 76 },
  { code: "688256.SH", n: "寒武纪", l: 1, ln: "算力芯片", px: 1310.00, pe: 120, roe: -2.5, rev_g: 0.85, tgt: 1400, ups: 0.069, mcap: "5400亿",
    biz: "AI训练/推理芯片，思元系列对标英伟达", cat: "国产AI芯片唯一规模化量产，推理芯片订单爆发", risk: "持续亏损、客户集中度高、技术迭代风险", op: "等回调至1150元（-12%）试仓3%", sc: 65 },
  { code: "688047.SH", n: "龙芯中科", l: 1, ln: "算力芯片", px: 145.80, pe: -1, roe: -8.2, rev_g: 0.15, tgt: 130, ups: -0.108, mcap: "580亿",
    biz: "自主LoongArch指令集CPU，信创核心", cat: "信创政策驱动，但AI算力属性弱", risk: "持续亏损、生态薄弱、x86/ARM压制", op: "回避，等待盈利拐点确认", sc: 38 },
  { code: "688041.SH", n: "海光信息", l: 1, ln: "算力芯片", px: 293.90, pe: 248, roe: 13.5, rev_g: 0.52, tgt: 320, ups: 0.089, mcap: "6300亿",
    biz: "x86 CPU + DCU AI芯片", cat: "DCU深算二号量产，互联网客户突破", risk: "出口管制+AMD授权风险", op: "回调至260元建仓", sc: 76 },
  { code: "002230.SZ", n: "科大讯飞", l: 1, ln: "算力芯片", px: 47.90, pe: 75, roe: 5.8, rev_g: 0.18, tgt: 55, ups: 0.148, mcap: "1100亿",
    biz: "星火大模型+AI应用，国产算力需求方", cat: "讯飞星火V4.0发布，教育/医疗AI落地加速", risk: "盈利模式不清晰、大模型竞争激烈", op: "等回调至43元试仓3%", sc: 52 },

  // Layer 2: 存储+封测 (7 stocks)
  { code: "600584.SH", n: "长电科技", l: 2, ln: "存储+封测", px: 82.05, pe: 40, roe: 9.2, rev_g: 0.22, tgt: 95, ups: 0.158, mcap: "1450亿",
    biz: "全球第三大封测厂，先进封装核心供应商", cat: "CoWoS封装产能扩张，HBM封装订单增长", risk: "资本开支大、行业周期波动", op: "回调至73元（-11%）分批建仓，仓位4%", sc: 75 },
  { code: "002156.SZ", n: "通富微电", l: 2, ln: "存储+封测", px: 65.00, pe: 35, roe: 8.5, rev_g: 0.28, tgt: 75, ups: 0.154, mcap: "980亿",
    biz: "AMD主要封测伙伴，先进封装产能扩张", cat: "AMD MI300放量+国产GPU封装需求增长", risk: "大客户依赖AMD、技术路线风险", op: "等回调至58元（-10.7%）建仓3%", sc: 70 },
  { code: "688525.SH", n: "佰维存储", l: 2, ln: "存储+封测", px: 318.10, pe: 38, roe: 18.5, rev_g: 3.42, tgt: 360, ups: 0.132, mcap: "1350亿",
    biz: "存储器模组+芯片，Q1营收+342%净利+1568%", cat: "存储周期上行+AI服务器存储需求爆发", risk: "存储周期性强、价格波动大", op: "回调至280元（-12%）建仓4%", sc: 78 },
  { code: "603986.SH", n: "兆易创新", l: 2, ln: "存储+封测", px: 467.01, pe: 55, roe: 14.2, rev_g: 0.48, tgt: 520, ups: 0.113, mcap: "3100亿",
    biz: "NOR Flash + MCU龙头，DRAM布局推进", cat: "存储涨价周期+端侧AI拉动NOR Flash需求", risk: "存储周期下行风险、竞争加剧", op: "等回调至420元（-10%）建仓3%", sc: 72 },
  { code: "002185.SZ", n: "华天科技", l: 2, ln: "存储+封测", px: 19.34, pe: 182, roe: 6.8, rev_g: 0.35, tgt: 22, ups: 0.138, mcap: "630亿",
    biz: "国内封测三巨头之一，5日涨38%后跌停(-10%)", cat: "先进封装扩产+AI芯片封测需求", risk: "PE极高182x、连续暴涨后风险极大、散户主导", op: "暴跌后不急于抄底，等15元以下（-22%）再考虑", sc: 45 },
  { code: "688362.SH", n: "甬矽电子", l: 2, ln: "存储+封测", px: 72.00, pe: 65, roe: 7.5, rev_g: 0.32, tgt: 82, ups: 0.139, mcap: "300亿",
    biz: "先进封装新锐，SiP/FC-BGA量产", cat: "先进封装国产替代+产能爬坡", risk: "规模较小、客户集中、技术路线不确定", op: "等65元以下试仓2%", sc: 58 },

  // Layer 3: 光通信 (7 stocks) 
  { code: "300308.SZ", n: "中际旭创", l: 3, ln: "光通信", px: 1161.16, pe: 43, roe: 28.5, rev_g: 0.72, tgt: 1300, ups: 0.120, mcap: "9600亿",
    biz: "全球光模块龙头，800G/1.6T主力供应商", cat: "1.6T光模块放量+LightCounting全球第一排名", risk: "客户集中英伟达/北美云厂、中美摩擦、股价已翻5倍", op: "等回调至1000元（-14%）分批建仓4%", sc: 88 },
  { code: "300502.SZ", n: "新易盛", l: 3, ln: "光通信", px: 706.45, pe: 35, roe: 26.2, rev_g: 0.65, tgt: 800, ups: 0.132, mcap: "5000亿",
    biz: "光模块厂，800G快速放量，1.6T送样", cat: "800G份额提升+LPO方案领先", risk: "行业价格战、光芯片依赖进口", op: "等回调至620元（-12%）建仓4%", sc: 82 },
  { code: "300394.SZ", n: "天孚通信", l: 3, ln: "光通信", px: 430.00, pe: 48, roe: 25.2, rev_g: 0.48, tgt: 480, ups: 0.116, mcap: "2500亿",
    biz: "光器件龙头，光模块上游核心部件", cat: "CPO技术布局领先+FAU/光引擎放量", risk: "CPO技术路线不确定、下游压价", op: "等回调至380元（-12%）建仓4%", sc: 78 },
  { code: "688498.SH", n: "源杰科技", l: 3, ln: "光通信", px: 1132.79, pe: 198, roe: 22.5, rev_g: 3.21, tgt: 1250, ups: 0.103, mcap: "1400亿",
    biz: "国产光芯片龙头，CW光源+EML双赛道，Q1净利+1153%", cat: "100G EML批量量产+切入中际旭创供应链+国产替代刚需", risk: "PE极高198x、光芯片技术迭代快、海外竞争", op: "等回调至980元（-13.5%）建仓3%", sc: 76 },
  { code: "688048.SH", n: "长光华芯", l: 3, ln: "光通信", px: 394.74, pe: 245, roe: 18.5, rev_g: 2.85, tgt: 440, ups: 0.115, mcap: "620亿",
    biz: "EML光芯片突破先锋，IDM全流程，100G/200G EML量产", cat: "EML芯片国产化率最低环节，200G EML客户验证中", risk: "PE极高245x、良率爬坡不确定、客户导入周期长", op: "等340元（-14%）试仓2%", sc: 68 },
  { code: "002281.SZ", n: "光迅科技", l: 3, ln: "光通信", px: 203.95, pe: 52, roe: 15.8, rev_g: 0.42, tgt: 235, ups: 0.152, mcap: "1645亿",
    biz: "光芯片-器件-模块全产业链，自研DFB+CPO，深度绑定华为昇腾", cat: "1.6T CPO光引擎发布+华为昇腾国产算力集群核心供应商", risk: "定增稀释、华为单一客户风险", op: "等回调至180元（-12%）建仓4%", sc: 74 },

  // Layer 4: 网络设备 (2 stocks)
  { code: "603019.SH", n: "中科曙光", l: 4, ln: "网络设备", px: 88.22, pe: 144, roe: 10.5, rev_g: 0.25, tgt: 98, ups: 0.111, mcap: "1300亿",
    biz: "AI服务器+超算龙头，国产算力核心", cat: "国产算力集群建设加速+海光CPU绑定", risk: "PE极高144x、竞争加剧", op: "等回调至78元（-11.5%）建仓3%", sc: 62 },
  { code: "000938.SZ", n: "紫光股份", l: 4, ln: "网络设备", px: 28.92, pe: 30, roe: 10.2, rev_g: 0.15, tgt: 34, ups: 0.176, mcap: "820亿",
    biz: "交换机/路由器龙头，新华三核心资产", cat: "AI数据中心交换机需求增长+800G交换机放量", risk: "增速缓慢、华为竞争", op: "等26元（-10%）建仓3%", sc: 65 },

  // Layer 5: 半导体制造与设备 (5 stocks)
  { code: "002371.SZ", n: "北方华创", l: 5, ln: "半导体制造", px: 638.91, pe: 83, roe: 18.5, rev_g: 0.42, tgt: 720, ups: 0.127, mcap: "3400亿",
    biz: "半导体设备龙头，刻蚀/薄膜/清洗全覆盖", cat: "3nm/2nm扩产+国产替代加速", risk: "PE极高83x、关键零部件依赖进口", op: "等回调至570元（-10.8%）建仓4%", sc: 72 },
  { code: "688012.SH", n: "中微公司", l: 5, ln: "半导体制造", px: 297.68, pe: 75, roe: 16.8, rev_g: 0.38, tgt: 335, ups: 0.125, mcap: "1850亿",
    biz: "刻蚀设备龙头，CCP/ICP刻蚀全覆盖", cat: "3D NAND/先进逻辑扩产+国产替代", risk: "PE高75x、设备验证周期长", op: "等回调至265元（-11%）建仓4%", sc: 70 },
  { code: "688981.SH", n: "中芯国际", l: 5, ln: "半导体制造", px: 156.11, pe: 48, roe: 8.5, rev_g: 0.20, tgt: 175, ups: 0.121, mcap: "6200亿",
    biz: "中国大陆最大晶圆代工厂，14nm/7nm量产", cat: "先进制程突破+国产替代核心+华为订单", risk: "美国制裁升级、先进制程良率不确定", op: "等回调至140元（-10.3%）建仓5%", sc: 73 },
  { code: "002463.SZ", n: "沪电股份", l: 5, ln: "半导体制造", px: 132.04, pe: 35, roe: 18.2, rev_g: 0.38, tgt: 150, ups: 0.136, mcap: "2500亿",
    biz: "AI服务器高端PCB龙头，英伟达/AMD核心供应商", cat: "CPU放量+PCB涨价，AI服务器主板需求翻倍", risk: "客户集中、PCB行业竞争", op: "等回调至118元（-10.6%）建仓3%", sc: 74 },
  { code: "002916.SZ", n: "深南电路", l: 5, ln: "半导体制造", px: 411.41, pe: 42, roe: 20.5, rev_g: 0.45, tgt: 465, ups: 0.130, mcap: "2700亿",
    biz: "PCB+封装基板双龙头，5/29逆市涨+3.92%创历史新高", cat: "IC载板国产替代+AI服务器PCB量价齐升", risk: "基板技术壁垒高、扩产周期长", op: "等回调至370元（-10%）建仓3%", sc: 75 },

  // Layer 6: 数据中心基建 (4 stocks)
  { code: "002837.SZ", n: "英维克", l: 6, ln: "数据中心基建", px: 91.00, pe: 50, roe: 14.5, rev_g: 0.38, tgt: 102, ups: 0.121, mcap: "550亿",
    biz: "精密温控/液冷设备龙头，AI数据中心散热核心", cat: "液冷渗透率从15%向40%提升+中标字节/阿里大单", risk: "价格战、客户集中", op: "等回调至80元（-12%）建仓3%", sc: 72 },
  { code: "300499.SZ", n: "高澜股份", l: 6, ln: "数据中心基建", px: 39.29, pe: 198, roe: 5.5, rev_g: 0.25, tgt: 45, ups: 0.145, mcap: "115亿",
    biz: "液冷设备供应商，电力电子冷却", cat: "数据中心液冷需求增长+储能温控", risk: "PE极高198x、规模小、业绩波动大", op: "等32元（-18.5%）试仓2%", sc: 45 },
  { code: "301018.SZ", n: "申菱环境", l: 6, ln: "数据中心基建", px: 148.50, pe: 339, roe: 8.2, rev_g: 0.32, tgt: 165, ups: 0.111, mcap: "410亿",
    biz: "数据中心精密空调/温控，液冷解决方案", cat: "AI数据中心温控需求爆发+中标多个超算中心", risk: "PE极高339x、估值泡沫风险极大", op: "超高PE不宜追，等120元（-19%）试仓2%", sc: 44 },
  { code: "002396.SZ", n: "星网锐捷", l: 6, ln: "数据中心基建", px: 22.69, pe: 25, roe: 11.5, rev_g: 0.12, tgt: 26, ups: 0.146, mcap: "130亿",
    biz: "企业级网络设备，交换机/路由器/瘦客户机", cat: "信创+数据中心网络设备采购", risk: "增速缓慢、行业竞争激烈", op: "等20元（-12%）建仓2%", sc: 55 },

  // Layer 7: AI应用 (2 stocks)
  { code: "688111.SH", n: "金山办公", l: 7, ln: "AI应用", px: 238.50, pe: 70, roe: 18.5, rev_g: 0.28, tgt: 270, ups: 0.132, mcap: "1100亿",
    biz: "WPS AI办公，国产Office龙头", cat: "WPS AI订阅收入高增长+信创替换", risk: "AI应用落地速度不确定、微软竞争", op: "等215元（-10%）建仓3%", sc: 65 },
  { code: "002415.SZ", n: "海康威视", l: 7, ln: "AI应用", px: 30.56, pe: 22, roe: 18.0, rev_g: 0.12, tgt: 36, ups: 0.178, mcap: "2800亿",
    biz: "AI视觉龙头，安防+工业AI应用", cat: "观澜大模型+工业AI落地+PBG/EBG复苏", risk: "增速放缓、海外制裁", op: "等28元（-8.4%）建仓4%", sc: 68 }
];

// ============ Deduplicate (海光信息 appeared twice) ============
var seen = {};
stocks = stocks.filter(function(s) {
  var key = s.code + s.n;
  if (seen[key]) return false;
  seen[key] = true;
  return true;
});

// ============ Sort by score ============
stocks.sort(function(a, b) { return b.sc - a.sc; });

// ============ Generate Document ============
var children = [];

// Cover page
children.push(new Paragraph({ spacing: { before: 3600 }, children: [] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 200 }, children: [new TextRun({ text: "A股AI产业链选股分析报告", font: FONT, size: 52, bold: true, color: HDR })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 100 }, children: [new TextRun({ text: "（扩展版 · 29只标的 · 基于5月29日收盘数据）", font: FONT, size: 24, color: "888888" })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 }, children: [new TextRun({ text: "2026年5月30日", font: FONT, size: 22, color: "999999" })] }));

// Key findings box
children.push(new Paragraph({ spacing: { before: 200, after: 120 }, children: [new TextRun({ text: "关键发现", font: FONT, size: 28, bold: true, color: HDR })] }));
var findings = [
  "新增10只标的，覆盖光芯片上游（源杰科技、长光华芯）、PCB/载板（沪电股份、深南电路）、存储（兆易创新）、封测延伸（华天科技、甬矽电子）、散热（申菱环境）、AI应用（海康威视）",
  "光模块三巨头（中际旭创、新易盛、天孚通信）5/28集体创新高，合计市值2.3万亿，但5/29板块普遍回调",
  "光芯片赛道爆发：源杰科技Q1净利+1153%，长光华芯Q1营收+285%，估值虽高但国产替代逻辑坚实",
  "深南电路5/29逆市涨+3.92%创新高，PCB/载板赛道景气度极高",
  "华天科技5日暴涨38%后5/29跌停(-10%)，追高风险极大",
  "29只标的中：强烈关注(>=75分)11只，关注(60-74分)10只，观望(45-59分)5只，回避(<45分)3只"
];
findings.forEach(function(t) {
  children.push(new Paragraph({ spacing: { after: 60 }, children: [
    new TextRun({ text: "\u25CF ", font: FONT, size: 20, color: HDR, bold: true }),
    new TextRun({ text: t, font: FONT, size: 20, color: "333333" })
  ]}));
});
children.push(new Paragraph({ children: [new PageBreak()] }));

// ============ Chapter 1: Layer-by-layer analysis ============
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: "一、各层选股分析（含目标价格）", font: FONT, size: 32, bold: true, color: HDR })] }));

var layerNames = { 1:"算力芯片", 2:"存储+封测", 3:"光通信", 4:"网络设备", 5:"半导体制造与设备", 6:"数据中心基建", 7:"AI应用" };
var layerDescs = {
  1: "AI的\"大脑\"——GPU/CPU/AI专用芯片，负责算力输出",
  2: "给大脑配\"记忆+仓库\"——HBM/DRAM/NAND存储芯片 + 先进封装测试",
  3: "晶片间用\"光\"高速传数据——光芯片/光器件/光模块，速度比铜线快百倍",
  4: "把成千上万颗芯片连成\"超级计算机\"——交换机/路由器/AI服务器",
  5: "\"造芯片\"的厂和设备——晶圆代工/设备/材料/PCB/载板",
  6: "给机房供电、散热、连接——液冷/温控/电力/连接器",
  7: "AI赋能各行各业——大模型/视觉/办公/安防等AI应用"
};

// Sort by layer
var layerGroups = {};
stocks.forEach(function(s) {
  if (!layerGroups[s.l]) layerGroups[s.l] = [];
  layerGroups[s.l].push(s);
});

Object.keys(layerGroups).sort(function(a,b){return a-b;}).forEach(function(ln) {
  var sl = layerGroups[ln];
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 120 }, children: [new TextRun({ text: "第"+ln+"层："+layerNames[ln], font: FONT, size: 28, bold: true, color: "2C3E50" })] }));
  children.push(new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: layerDescs[ln], font: FONT, size: 20, color: "666666", italics: true })] }));

  // Table
  var rows = [new TableRow({ children: [
    hCell("代码/名称", 1200), hCell("评分", 550), hCell("现价(元)", 800), hCell("目标价", 800),
    hCell("空间", 700), hCell("PE", 600), hCell("ROE", 550), hCell("核心逻辑", 4480)
  ]})];

  sl.forEach(function(s, i) {
    var fill = s.sc >= 75 ? GREEN : s.sc >= 60 ? BLUE : s.sc >= 45 ? YELLOW : RED_BG;
    var rowFill = i % 2 === 0 ? "FFFFFF" : GRAY;
    rows.push(new TableRow({ children: [
      bCell(s.code + "\\n" + s.n, 1200, rowFill, { bold: true }),
      bCell(String(s.sc), 550, s.sc >= 75 ? GREEN : s.sc >= 60 ? BLUE : s.sc >= 45 ? YELLOW : RED_BG, { align: "center", bold: true, color: s.sc >= 60 ? "1A7A1A" : "000000" }),
      bCell(String(s.px), 800, rowFill, { align: "right" }),
      bCell(String(s.tgt), 800, rowFill, { align: "right", bold: true, color: "1A7A1A" }),
      bCell(pct_s(s.ups), 700, rowFill, { align: "center", bold: true, color: s.ups > 0 ? "1A7A1A" : "C0392B" }),
      bCell(s.pe < 0 ? "亏损" : String(s.pe), 600, rowFill, { align: "center" }),
      bCell(s.roe < 0 ? "亏损" : s.roe.toFixed(1) + "%", 550, rowFill, { align: "center" }),
      bCell(s.biz, 4480, rowFill, { size: 17 })
    ]}));
  });
  children.push(new Table({ width: MW(9680), columnWidths: [1200, 550, 800, 800, 700, 600, 550, 4480], rows: rows }));
  children.push(new Paragraph({ spacing: { after: 200 }, children: [new TextRun({ text: "", font: FONT, size: 8 })] }));
});

children.push(new Paragraph({ children: [new PageBreak()] }));

// ============ Chapter 2: Strong Buy (>=75) ============
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: "二、强烈关注清单（评分 >= 75）", font: FONT, size: 32, bold: true, color: HDR })] }));

var strong = stocks.filter(function(s) { return s.sc >= 75; });
var sRows = [new TableRow({ children: [
  hCell("排名", 500), hCell("代码", 900), hCell("名称", 1000), hCell("评分", 500),
  hCell("现价", 700), hCell("目标价", 700), hCell("空间", 700), hCell("PE", 500), hCell("ROE", 550), hCell("核心逻辑", 3850)
]})];

strong.forEach(function(s, i) {
  var rf = i % 2 === 0 ? "FFFFFF" : GREEN;
  sRows.push(new TableRow({ children: [
    bCell(String(i + 1), 500, rf, { align: "center", bold: true }),
    bCell(s.code, 900, rf, {}),
    bCell(s.n, 1000, rf, { bold: true }),
    bCell(String(s.sc), 500, rf, { align: "center", bold: true, color: "1A7A1A" }),
    bCell(String(s.px), 700, rf, { align: "right" }),
    bCell(String(s.tgt), 700, rf, { align: "right", bold: true }),
    bCell(pct_s(s.ups), 700, rf, { align: "center", bold: true, color: "1A7A1A" }),
    bCell(String(s.pe), 500, rf, { align: "center" }),
    bCell(s.roe.toFixed(1) + "%", 550, rf, { align: "center" }),
    bCell(s.biz, 3850, rf, { size: 17 })
  ]}));
});
children.push(new Table({ width: MW(9680), columnWidths: [500, 900, 1000, 500, 700, 700, 700, 500, 550, 3850], rows: sRows }));
children.push(new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "", font: FONT })] }));

// Detail for each strong buy
strong.forEach(function(s) {
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 80 }, children: [
    new TextRun({ text: s.code + " " + s.n + "  |  评分：" + s.sc + "/100  |  目标价：" + s.tgt + "元（" + pct_s(s.ups) + "）", font: FONT, size: 24, bold: true, color: "34495E" })
  ]}));
  children.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "催化剂：" + s.cat, font: FONT, size: 20, color: "333333" })] }));
  children.push(new Paragraph({ spacing: { after: 60 }, children: [new TextRun({ text: "风险：", font: FONT, size: 20, color: "C0392B", bold: true }), new TextRun({ text: s.risk, font: FONT, size: 20, color: "C0392B" })] }));
  children.push(new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: "操作建议：" + s.op, font: FONT, size: 20, bold: true, color: "1A7A1A" })] }));
});

children.push(new Paragraph({ children: [new PageBreak()] }));

// ============ Chapter 3: Watch list (60-74) ============
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: "三、关注清单（评分 60-74 · 等回调）", font: FONT, size: 32, bold: true, color: HDR })] }));

var watch = stocks.filter(function(s) { return s.sc >= 60 && s.sc < 75; });
var wRows = [new TableRow({ children: [
  hCell("排名", 500), hCell("代码", 900), hCell("名称", 1000), hCell("评分", 500),
  hCell("现价", 700), hCell("目标", 700), hCell("空间", 700), hCell("建议等至", 850), hCell("PE", 500), hCell("核心风险", 3430)
]})];

watch.forEach(function(s, i) {
  var wp = Math.round(s.px * 0.88);
  var rf = i % 2 === 0 ? "FFFFFF" : BLUE;
  wRows.push(new TableRow({ children: [
    bCell(String(i + 1), 500, rf, { align: "center", bold: true }),
    bCell(s.code, 900, rf, {}),
    bCell(s.n, 1000, rf, { bold: true }),
    bCell(String(s.sc), 500, rf, { align: "center", bold: true }),
    bCell(String(s.px), 700, rf, { align: "right" }),
    bCell(String(s.tgt), 700, rf, { align: "right", bold: true }),
    bCell(pct_s(s.ups), 700, rf, { align: "center", bold: true, color: "1A7A1A" }),
    bCell(wp + "元（-12%）", 850, rf, { align: "right", bold: true, color: "1A7A1A" }),
    bCell(String(s.pe), 500, rf, { align: "center" }),
    bCell(s.risk, 3430, rf, { size: 17, color: "C0392B" })
  ]}));
});
children.push(new Table({ width: MW(9680), columnWidths: [500, 900, 1000, 500, 700, 700, 700, 850, 500, 3430], rows: wRows }));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ============ Chapter 4: Avoid/Weak (below 60) ============
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: "四、回避/观望清单（评分 < 60）", font: FONT, size: 32, bold: true, color: HDR })] }));

var avoid = stocks.filter(function(s) { return s.sc < 60; });
var aRows = [new TableRow({ children: [
  hCell("代码", 900), hCell("名称", 1000), hCell("评分", 500), hCell("现价", 700),
  hCell("PE", 600), hCell("层", 700), hCell("回避原因", 5480)
]})];

avoid.forEach(function(s, i) {
  var rf = i % 2 === 0 ? "FFFFFF" : RED_BG;
  var reason = "";
  if (s.sc < 45) reason = "PE极高(" + s.pe + "x)/基本面弱/估值泡沫";
  else if (s.pe > 150) reason = "PE极高(" + s.pe + "x)，等待估值回归";
  else if (s.roe < 0) reason = "持续亏损，等待盈利拐点";
  else reason = "增速缓慢/竞争激烈/缺乏催化";
  aRows.push(new TableRow({ children: [
    bCell(s.code, 900, rf, {}),
    bCell(s.n, 1000, rf, { bold: true }),
    bCell(String(s.sc), 500, rf, { align: "center", bold: true, color: "C0392B" }),
    bCell(String(s.px), 700, rf, { align: "right" }),
    bCell(s.pe < 0 ? "亏损" : String(s.pe), 600, rf, { align: "center", color: "C0392B" }),
    bCell(layerNames[s.l], 700, rf, { align: "center" }),
    bCell(reason, 5480, rf, { size: 17, color: "C0392B" })
  ]}));
});
children.push(new Table({ width: MW(9680), columnWidths: [900, 1000, 500, 700, 600, 700, 5480], rows: aRows }));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ============ Chapter 5: NEW stocks spotlight ============
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: "五、新增标的深度点评", font: FONT, size: 32, bold: true, color: HDR })] }));

children.push(new Paragraph({ spacing: { after: 100 }, children: [new TextRun({ text: "以下10只为本次扩展新增标的，聚焦之前覆盖不足的细分赛道。", font: FONT, size: 20, color: "666666" })] }));

var newStocks = [
  { topic: "光芯片上游 — 源杰科技 vs 长光华芯",
    body: "光芯片是光模块产业链中国产化率最低、壁垒最高的环节。源杰科技（1132.79元，PE 198x）全球硅光CW光源市占率23.6%国内第一，100G EML稳定量产，Q1净利+1153%。长光华芯（394.74元，PE 245x）100G/200G EML IDM全流程布局。两只票PE都极高，但赛道稀缺性决定了高溢价。关注源杰科技回调至980元以下的机会。" },
  { topic: "光器件全产业链 — 光迅科技",
    body: "光迅科技（203.95元，PE 52x）是国内唯一光芯片-器件-模块全产业链企业，自研DFB光芯片+1.6T CPO光引擎，深度绑定华为昇腾国产算力集群。相比光模块三巨头，估值更合理，且自主可控属性突出。5/29跌5.1%后性价比提升。" },
  { topic: "PCB/载板双龙头 — 沪电股份 vs 深南电路",
    body: "沪电股份（132.04元，PE 35x）是英伟达/AMD AI服务器PCB核心供应商，估值在AI板块中相对合理。深南电路（411.41元，PE 42x）PCB+IC载板双赛道，5/29逆市涨3.92%创新高，市值突破2700亿。两只都是CPU放量+PCB涨价的核心受益标的，沪电估值更有吸引力。" },
  { topic: "存储芯片 — 兆易创新",
    body: "兆易创新（467.01元，PE 55x）是NOR Flash+MCU双龙头，受益于存储涨价周期+端侧AI拉动NOR Flash需求。市值3100亿，13位分析师一致买入评级，目标均价437元（当前价467元已略超共识目标）。等回调至420元附近更有安全边际。" },
  { topic: "封测新锐 — 甬矽电子",
    body: "甬矽电子（约72元，PE 65x）是先进封装新锐，SiP/FC-BGA量产中。市值仅300亿，属于小而美。但规模较小、客户导入尚在早期，适合小仓位布局。" },
  { topic: "⚠️ 追高风险案例 — 华天科技",
    body: "华天科技（19.34元，PE 182x）5日暴涨38%后5/29跌停(-10%)，换手率24.55%，散户主导特征明显。PE高达182x，追高风险极大。即使看好先进封装赛道，也建议等回调至15元以下（-22%）再考虑。" }
];

newStocks.forEach(function(ns) {
  children.push(new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 80 }, children: [new TextRun({ text: ns.topic, font: FONT, size: 24, bold: true, color: "34495E" })] }));
  children.push(new Paragraph({ spacing: { after: 120 }, children: [new TextRun({ text: ns.body, font: FONT, size: 20, color: "333333" })] }));
});

children.push(new Paragraph({ children: [new PageBreak()] }));

// ============ Chapter 6: Allocation ============
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: "六、持仓建议", font: FONT, size: 32, bold: true, color: HDR })] }));

var allocs = [
  "总仓位：AI板块合计不超过总资产30%（当前估值高位，不宜重仓）",
  "核心仓（15-20%）：中际旭创4%、新易盛4%、天孚通信3%、海光信息4%、深南电路3%",
  "卫星仓（8-10%）：光迅科技3%、沪电股份3%、北方华创2%、中芯国际2%",
  "观察仓（3-5%）：源杰科技1.5%、兆易创新1.5%、佰维存储1%、长电科技1%",
  "等待池：寒武纪、中科曙光、中微公司、金山办公——等回调10%以上再考虑",
  "建仓节奏：分5-8批DCA，每批间隔2-3周，首批不超过目标仓位的20%",
  "止损线：单票-15%无条件止损，板块整体-10%减半仓"
];
allocs.forEach(function(t) {
  children.push(new Paragraph({ spacing: { after: 80 }, children: [
    new TextRun({ text: "\u25CF ", font: FONT, size: 20, color: HDR, bold: true }),
    new TextRun({ text: t, font: FONT, size: 20, color: "333333" })
  ]}));
});

children.push(new Paragraph({ children: [new PageBreak()] }));

// ============ Chapter 7: Risks ============
children.push(new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 }, children: [new TextRun({ text: "七、风险提示", font: FONT, size: 32, bold: true, color: HDR })] }));

var risks = [
  "AI板块整体估值处于历史90%分位以上，回调风险较大",
  "光模块/光芯片赛道估值泡沫化：源杰科技PE 198x、长光华芯PE 245x、申菱环境PE 339x",
  "5/29已出现板块普调：华天科技-10%、英维克-6.69%、星网锐捷-8.21%，可能是回调前兆",
  "中美科技脱钩风险：出口管制可能随时升级",
  "A股特有风险：大股东减持（如兆易创新朱一明5/26减持57.99万股）、概念炒作退潮、小盘股流动性差",
  "半导体周期风险：存储涨价周期可能在下半年见顶"
];
risks.forEach(function(t) {
  children.push(new Paragraph({ spacing: { after: 80 }, children: [
    new TextRun({ text: "\u26A0 ", font: FONT, size: 20 }),
    new TextRun({ text: t, font: FONT, size: 20, color: "333333" })
  ]}));
});

children.push(new Paragraph({ spacing: { before: 240, after: 120 }, children: [new TextRun({ text: "免责声明：本报告所有分析、评分、目标价均基于公开信息和个人判断，不构成投资建议。A股投资有风险，入市需谨慎。过往表现不代表未来收益。", font: FONT, size: 19, color: "C0392B", bold: true })] }));

// ============ Build document ============
var doc = new Document({
  styles: {
    default: { document: { run: { font: FONT, size: 20 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 32, bold: true, font: FONT, color: HDR }, paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 28, bold: true, font: FONT, color: "2C3E50" }, paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true, run: { size: 24, bold: true, font: FONT, color: "34495E" }, paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } }
    ]
  },
  sections: [{
    properties: { page: { size: { width: 12240, height: 15840 }, margin: { top: 1200, right: 1000, bottom: 1200, left: 1000 } } },
    headers: { default: new Header({ children: [new Paragraph({ alignment: AlignmentType.RIGHT, children: [new TextRun({ text: "A股AI产业链选股分析报告（扩展版） · 2026.05.30", font: FONT, size: 16, color: "AAAAAA" })] })] }) },
    footers: { default: new Footer({ children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text: "第 ", font: FONT, size: 16, color: "AAAAAA" }), new TextRun({ children: [PageNumber.CURRENT], font: FONT, size: 16, color: "AAAAAA" }), new TextRun({ text: " 页", font: FONT, size: 16, color: "AAAAAA" })] })] }) },
    children: children
  }]
});

Packer.toBuffer(doc).then(function(buf) {
  fs.writeFileSync("c:\\Users\\asus\\WorkBuddy\\20260530114642\\A股AI产业链选股分析报告_20260530_扩展版.docx", buf);
  console.log("Word report generated successfully!");
}).catch(function(e) {
  console.error("Error:", e);
  process.exit(1);
});
