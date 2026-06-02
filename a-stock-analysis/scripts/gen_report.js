const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        PageNumber, PageBreak, ExternalHyperlink } = require('docx');
const fs = require('fs');

// ========== 数据 ==========
const data = JSON.parse(fs.readFileSync('ai_stock_analysis.json', 'utf8'));
const { stocks, layers } = data;

// ========== 样式 ==========
const border = { style: BorderStyle.SINGLE, size: 1, color: "AAAAAA" };
const borders = { top: border, bottom: border, left: border, right: border };
const cm = (dxa) => ({ size: dxa, type: WidthType.DXA });
const marg = { top: 60, bottom: 60, left: 100, right: 100 };

const HDR = "1F4E79", GREEN = "D5F5E3", BLUE = "D4E6F1",
      YELLOW = "FCF3CF", RED = "FADBD8", GRAY = "F2F3F4",
      LIGHT = "EBF5FB";

function hCell(text, width, fill, opts) {
  return new TableCell({
    borders, width: cm(width), shading: { fill: fill||HDR, type: ShadingType.CLEAR },
    margins: marg,
    children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [new TextRun({
        text, bold: true, font: "Arial", size: (opts&&opts.size)||(20),
        color: (fill===HDR) ? "FFFFFF" : "000000"
      })]
    })]
  });
}

function bCell(text, width, fill, opts) {
  const lines = (text||"").split('\n');
  const children = lines.map((t,i) => new Paragraph({
    spacing: { after: i<lines.length-1 ? 40 : 0 },
    children: [new TextRun({
      text: t, font: (opts&&opts.font)||"Arial", size: (opts&&opts.size)||(20),
      bold: !!(opts&&opts.bold), color: (opts&&opts.color)||"000000"
    })]
  }));
  return new TableCell({
    borders, width: cm(width),
    shading: { fill: fill||"FFFFFF", type: ShadingType.CLEAR },
    margins: marg, children
  });
}

function ratingFill(r) {
  if (r==="🟢") return GREEN;
  if (r==="🔵") return BLUE;
  if (r==="🟡") return YELLOW;
  if (r==="🔴") return RED;
  return "FFFFFF";
}

// ========== 段落/标题 ==========
function h1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, spacing: { before: 360, after: 200 },
    children: [new TextRun({ text, font: "Arial", size: 32, bold: true, color: HDR })] });
}
function h2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, spacing: { before: 280, after: 160 },
    children: [new TextRun({ text, font: "Arial", size: 28, bold: true, color: "2C3E50" })] });
}
function h3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, spacing: { before: 200, after: 100 },
    children: [new TextRun({ text, font: "Arial", size: 24, bold: true, color: "34495E" })] });
}
function p(text, opts) {
  return new Paragraph({
    spacing: { after: (opts&&opts.after)||(120) },
    children: [new TextRun({ text: text||"", font: "Arial", size: 22,
      bold: !!(opts&&opts.bold), color: (opts&&opts.color)||"000000" })]
  });
}
function bullet(text, ref) {
  return new Paragraph({
    numbering: { reference: ref||"bullets", level: 0 },
    spacing: { after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 22 })]
  });
}
function note(text) {
  return new Paragraph({
    spacing: { after: 80 },
    indent: { left: 360 },
    children: [new TextRun({ text, font: "Arial", size: 20, color: "888888", italics: true })]
  });
}

// ========== 数字格式化 ==========
function pct(n) { return (n*100).toFixed(1)+"%"; }
function pctSign(n) { const v = (n*100).toFixed(1); return n>=0 ? "+"+v+"%" : v+"%"; }
function price(n) { return n==null||n==="N/A" ? "N/A" : (typeof n==='number'? n.toFixed(0)+"元" : n); }

// ========== 内容组装 ==========
const children = [];
const today = "2026年5月30日";

// 封面
children.push(new Paragraph({ spacing: { before: 2400 }, children: [] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 240 },
  children: [new TextRun({ text: "A 股 AI 产业链选股分析报告", font: "Arial", size: 52, bold: true, color: HDR })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 160 },
  children: [new TextRun({ text: "基于七层产业链框架 · 含目标价格与操作建议", font: "Arial", size: 26, color: "555555" })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 400 },
  children: [new TextRun({ text: today, font: "Arial", size: 22, color: "888888" })] }));
children.push(new Paragraph({ alignment: AlignmentType.CENTER, spacing: { after: 600 },
  children: [new TextRun({ text: "⚠️ 本报告为研究学习框架，非投资建议，投资决策需自行判断", font: "Arial", size: 20, color: "AAAAAA", italics: true })] }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// 目录
children.push(h1("目录"));
children.push(new TableOfContents("目录", { hyperlink: true, headingStyleRange: "1-3" }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ========== 第一章：方法论 ==========
children.push(h1("一、分析框架与方法论"));
children.push(p("本报告采用「A 股 AI 产业链七层分类法」，结合国产替代紧迫度、全球供应链地位、业绩兑现能力、估值安全边际、资金面信号五大维度进行综合评分。"));
children.push(h2("1.1  七层产业链分类"));

const layerDefs = [
  [1, "🎮 算力芯片", "AI 的「大脑」，国产替代核心逻辑"],
  [2, "💾 存储+封测", "给大脑配「仓库」，先进封装卡脖子"],
  [3, "🌈 光通信", "A 股在全球 AI 供应链中最强的环节"],
  [4, "🌐 网络设备", "连接 GPU 集群的交换机与高速互联"],
  [5, "🏭 半导体制造/设备", "造芯片的厂和设备，去美化核心战场"],
  [6, "⚡ 数据中心基建", "AI 机房的电力、散热、服务器"],
  [7, "💡 AI 应用/软件", "把 AI 能力落地到具体场景"],
];
const layerTableRows = [new TableRow({ children: [
  hCell("层", 1200), hCell("名称", 2800), hCell("大白话", 5360)
]})];
layerDefs.forEach(([n, name, desc], i) => {
  layerTableRows.push(new TableRow({ children: [
    bCell(String(n), 1200, i%2?GRAY:null, { bold:true, align:"center" }),
    bCell(name, 2800, i%2?GRAY:null, { bold:true }),
    bCell(desc, 5360, i%2?GRAY:null, {}),
  ]}));
});
children.push(new Table({ width: cm(9360), columnWidths: [1200,2800,5360], rows: layerTableRows }));
children.push(note("注：每层代表 AI 产业链的一个关键环节，优先选卡在瓶颈上的公司。"));
children.push(p(""));

children.push(h2("1.2  五大评分维度"));
const dimRows = [new TableRow({ children: [
  hCell("维度", 1872), hCell("权重", 1404), hCell("评估要点（A 股特有）", 6084)
]})];
[["国产替代紧迫度","20%","该环节国产化率？是否被列入「卡脖子」清单？大基金是否扶持？",GRAY],
 ["全球供应链地位","20%","A 股公司在全球 AI 供应链中是否不可替代？海外大客户订单占比？",null],
 ["业绩兑现能力","25%","收入/利润是否已经体现在财报？（A 股概念炒作多，业绩兑现是关键分水岭）",GRAY],
 ["估值安全边际","20%","P/E 分位数 vs 历史区间？距 52 周高点回撤幅度？",null],
 ["资金面信号","15%","北向资金持仓变化？龙虎榜机构净买入？",GRAY],
].forEach(([d,w,n,fill],i) => {
  dimRows.push(new TableRow({ children: [
    bCell(d,1872,fill,{bold:true}),
    bCell(w,1404,fill,{bold:true,align:"center"}),
    bCell(n,6084,fill,{}),
  ]}));
});
children.push(new Table({ width: cm(9360), columnWidths: [1872,1404,6084], rows: dimRows }));
children.push(p(""));

children.push(h2("1.3  评级标准"));
[["🟢 强烈关注","评分 ≥ 75 分，业绩已兑现，国产替代核心，估值相对合理",GREEN],
 ["🔵 关注","评分 60–74 分，好公司好赛道，但估值偏高，等回调",BLUE],
 ["🟡 观望","评分 45–59 分，概念为主，业绩待验证，或估值已透支",YELLOW],
 ["🔴 回避","评分 < 45 分，基本面弱，纯概念炒作，或技术路线被替代",RED],
].forEach(([r,desc,fill]) => {
  children.push(new Paragraph({
    spacing: { after: 80 },
    children: [
      new TextRun({ text: r+"  ", font: "Arial", size: 24, bold: true }),
      new TextRun({ text: desc, font: "Arial", size: 22 })
    ]
  }));
});
children.push(p(""));

// ========== 第二章：各层分析 ==========
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("二、各层选股分析（含目标价格）"));

const LAYER_META = {
  1: { emoji:"🎮", name:"算力芯片", desc:"AI 的「大脑」，A 股没有英伟达，核心逻辑是「国产替代+自主可控」。寒武纪是纯 AI 芯片代表，海光信息走 x86+DCU 路线更成熟，龙芯走完全自主指令集但商业化最弱。" },
  2: { emoji:"💾", name:"存储+封测", desc:"AI 服务器需要大量 HBM（高带宽内存）和先进封装（CoWoS 类）。A 股封测厂（长电/通富）在全球有竞争力；存储芯片（佰维）受益于 AI 服务器 SSD 需求爆发。" },
  3: { emoji:"🌈", name:"光通信", desc:"这是 A 股在全球 AI 供应链中最强的环节。中际旭创、新易盛的 800G 光模块直接供货英伟达/微软/谷歌，业绩已大幅兑现。天孚通信是上游核心器件，毛利率最高。" },
  4: { emoji:"🌐", name:"网络设备", desc:"AI 数据中心需要大量 800G 交换机。紫光股份（新华三）是国内交换机龙头，直接受益于国内 AI 数据中心建设。但毛利率偏低、负债率偏高是要关注的风险。" },
  5: { emoji:"🏭", name:"半导体制造/设备", desc:"中芯国际是大陆最先进的晶圆代工厂，但受出口管制影响，先进制程突围困难。北方华创和中微公司是设备国产替代核心，但估值极高，需要等回调。" },
  6: { emoji:"⚡", name:"数据中心基建", desc:"AI 数据中心液冷散热是 2026 年最明确的增量。英维克是液冷龙头，订单放量确定性强。高澜股份是小票高弹性。中科曙光是国产服务器龙头。" },
  7: { emoji:"💡", name:"AI 应用/软件", desc:"AI 应用落地是弹性最大但确定性最低的环节。科大讯飞（星火大模型）商业化还在早期。金山办公（WPS AI）商业模式最清晰，但估值极高。" },
};

Object.keys(layers).sort((a,b)=>a-b).forEach(layerNum => {
  const meta = LAYER_META[layerNum];
  const stocksInLayer = layers[layerNum].sort((a,b) => b.score - a.score);

  children.push(h2(`第${layerNum}层：${meta.emoji} ${meta.name}`));
  children.push(p(meta.desc));

  // 分析表格
  const headCells = [
    hCell("代码/名称", 1400), hCell("评级", 800), hCell("评分", 600),
    hCell("现价/目标价", 1400), hCell("上行空间", 900), hCell("P/E", 700),
    hCell("ROE", 600), hCell("营收增速", 900), hCell("核心逻辑", 1960)
  ];
  const rows = [new TableRow({ children: headCells })];

  stocksInLayer.forEach((s, i) => {
    const fill = s.rating === "🟢" ? GREEN : s.rating === "🔵" ? BLUE : s.rating === "🟡" ? YELLOW : RED;
    const even = i%2===0;
    const bg = even ? "FFFFFF" : GRAY;
    rows.push(new TableRow({ children: [
      bCell(`${s.code}\n${s.name}`, 1400, bg, { bold:true, size:20 }),
      bCell(s.rating, 800, fill, { align:"center", size:24 }),
      bCell(String(s.score), 600, bg, { align:"center", bold:true }),
      bCell(`${s.price}元\n→ ${s.targetPrice}元`, 1400, bg, {}),
      bCell(pctSign(s.upside), 900, bg, { align:"center", bold:true,
        color: s.upside>=0.1?"1A7A1A":"C0392B" }),
      bCell(String(s.pe), 700, bg, { align:"center" }),
      bCell(`${s.roe}%`, 600, bg, { align:"center" }),
      bCell(pct(s.revenueGrowth), 900, bg, { align:"center" }),
      bCell(s.biz.replace(/，/g, "，\n").substring(0,80), 1960, bg, { size:18 }),
    ]}));
  });
  children.push(new Table({ width: cm(9360), columnWidths: [1400,800,600,1400,900,700,600,900,1960], rows }));
  children.push(p(""));

  // 逐股点评
  stocksInLayer.forEach(s => {
    children.push(h3(`${s.rating} ${s.code} ${s.name}  |  评分：${s.score}/100  |  目标价：${s.targetPrice}元（${pctSign(s.upside)}）`));
    if (s.bottleneck) children.push(p(`🔥 卡位瓶颈：${s.bottleneck}`));
    children.push(p(`为什么关注：${s.biz}`));
    children.push(p(`催化剂：${s.catalyst}`));
    children.push(p(`风险提示：${s.risk}`, { color: "C0392B" }));
    const entry = s.upside > 0.1
      ? `当前价 ${s.price} 元，距目标价还有 ${pctSign(s.upside)} 空间。建议等待回调至 ${Math.round(s.targetPrice * 0.92)} 元附近分批建仓（约 ${pct(((s.price-s.targetPrice*0.92)/s.price)} 回撤）。`
      : `当前价已接近或高于目标价，不建议追高。建议等待回调至 ${Math.round(s.targetPrice * 0.90)} 元附近再考虑建仓。`;
    children.push(p(`操作建议：${entry}`));
    children.push(p(""));
  });

  children.push(new Paragraph({ children: [new PageBreak()] }));
});

// ========== 第三章：强势关注清单 ==========
children.push(h1("三、🟢 强烈关注清单（优先配置）"));
children.push(p("以下股票综合评分 ≥ 75 分，基本面扎实、业绩已兑现、估值相对合理，是 A 股 AI 产业链的首选配置方向。"));

const strongList = Object.keys(stocks)
  .filter(c => stocks[c].rating === "🟢")
  .sort((a,b) => stocks[b].score - stocks[a].score);

const strongRows = [new TableRow({ children: [
  hCell("排名", 600), hCell("代码", 900), hCell("名称", 1200), hCell("层级", 1200),
  hCell("评分", 600), hCell("现价", 800), hCell("目标价", 800), hCell("空间", 800),
  hCell("核心逻辑（一句话）", 3200)
]})];

strongList.forEach((code, i) => {
  const s = stocks[code];
  strongRows.push(new TableRow({ children: [
    bCell(String(i+1), 600, GREEN, { align:"center", bold:true }),
    bCell(s.code, 900, i%2?LIGHT:GREEN, {}),
    bCell(s.name, 1200, i%2?LIGHT:GREEN, { bold:true }),
    bCell(s.layerName, 1200, i%2?LIGHT:GREEN, {}),
    bCell(String(s.score), 600, i%2?LIGHT:GREEN, { align:"center", bold:true }),
    bCell(`${s.price}元`, 800, i%2?LIGHT:GREEN, { align:"right" }),
    bCell(`${s.targetPrice}元`, 800, i%2?LIGHT:GREEN, { align:"right", bold:true }),
    bCell(pctSign(s.upside), 800, i%2?LIGHT:GREEN, { align:"center", bold:true,
      color: s.upside>=0.1?"1A7A1A":"C0392B" }),
    bCell(s.biz.substring(0,40)+"...", 3200, i%2?LIGHT:GREEN, { size:18 }),
  ]}));
});
children.push(new Table({ width: cm(9360), columnWidths: [600,900,1200,1200,600,800,800,800,3200], rows: strongRows }));
children.push(p(""));

// ========== 第四章：关注清单 ==========
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("四、🔵 关注清单（等回调再进）"));
children.push(p("以下股票基本面优秀，但当前估值偏高或距目标价空间有限，建议放入自选股，等待回调至合理区间后再分批建仓。"));

const watchList = Object.keys(stocks)
  .filter(c => stocks[c].rating === "🔵")
  .sort((a,b) => stocks[b].score - stocks[a].score);

const watchRows = [new TableRow({ children: [
  hCell("排名", 600), hCell("代码", 900), hCell("名称", 1200), hCell("层级", 1200),
  hCell("评分", 600), hCell("现价", 800), hCell("目标价", 800), hCell("距目标", 900),
  hCell("建议等待回调至", 1200), hCell("核心风险", 1560)
]})];
watchList.forEach((code, i) => {
  const s = stocks[code];
  const waitPrice = Math.round(s.targetPrice * 0.90);
  watchRows.push(new TableRow({ children: [
    bCell(String(i+1), 600, BLUE, { align:"center", bold:true }),
    bCell(s.code, 900, i%2?LIGHT:BLUE, {}),
    bCell(s.name, 1200, i%2?LIGHT:BLUE, { bold:true }),
    bCell(s.layerName, 1200, i%2?LIGHT:BLUE, {}),
    bCell(String(s.score), 600, i%2?LIGHT:BLUE, { align:"center" }),
    bCell(`${s.price}元`, 800, i%2?LIGHT:BLUE, { align:"right" }),
    bCell(`${s.targetPrice}元`, 800, i%2?LIGHT:BLUE, { align:"right" }),
    bCell(pctSign(s.upside), 900, i%2?LIGHT:BLUE, { align:"center",
      color: s.upside>0?"1A7A1A":"C0392B" }),
    bCell(`${waitPrice}元（-10%）`, 1200, i%2?LIGHT:BLUE, { align:"right", bold:true, color:"1A7A1A" }),
    bCell(s.risk.split("、")[0], 1560, i%2?LIGHT:BLUE, { size:18 }),
  ]}));
});
children.push(new Table({ width: cm(9360), columnWidths: [600,900,1200,1200,600,800,800,900,1200,1560], rows: watchRows }));
children.push(p(""));

// ========== 第五章：持仓建议 ==========
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("五、持仓配置建议"));

children.push(h2("5.1  A 股 AI 产业链仓位管理（小白友好）"));
[["单票仓位上限","3%","A 股波动比美股大，单票上限比美股（5%）更保守，避免一只票暴雷影响整体"],
 ["AI 产业链总仓位","≤ 30%","AI 板块波动大，不宜 all-in，保留 70% 现金/债券/宽基做压舱石"],
 ["首次建仓比例","15–20%","不要一次性买满，先建立试探仓，确认走势后再加"],
 ["加仓节奏","每跌 8–10% 加一批","A 股波动大，拉开加仓间距，避免刚加仓就继续跌"],
 ["止损线","单票 -12~15%","A 股下跌动能强，必须设止损，跌超线说明逻辑破了，别死扛"],
 ["禁区","涨停板不追、利好当日不追","A 股「利好出货」是常态，追涨容易被套在山岗上"],
].forEach(([k,v,n],i) => {
  children.push(new Paragraph({ spacing: { after: 80 }, children: [
    new TextRun({ text: `▸ ${k}：`, font:"Arial", size:22, bold:true, color: HDR }),
    new TextRun({ text: `${v}  `, font:"Arial", size:22, bold:true, color: "1A7A1A" }),
    new TextRun({ text: n, font:"Arial", size:20, color: "555555" }),
  ]}));
});
children.push(p(""));

children.push(h2("5.2  推荐持仓结构（参考）"));
const allocRows = [new TableRow({ children: [
  hCell("仓位类型", 1872), hCell("建议占比", 1404), hCell("配置方向", 6084)
]})];
[["核心仓（🟢强烈关注）","15–20%","中际旭创+海光信息+英维克，3只分散风险",GRAY],
 ["观察仓（🔵关注）","5–10%","选择 2 只估值最合理/空间最大的，等回调建仓",null],
 ["低仓/预备仓","5%","现金，等待大盘调整或个股利空砸出的黄金坑",GRAY],
 ["非 AI 仓（压舱石）","≥ 60%","沪深 300ETF/债券基金/现金，避免 AI 板块回调时满仓被埋",null],
].forEach(([t,p,d,f],i) => {
  allocRows.push(new TableRow({ children: [
    bCell(t,1872,f,{bold:true}),
    bCell(p,1404,f,{bold:true,align:"center"}),
    bCell(d,6084,f,{}),
  ]}));
});
children.push(new Table({ width: cm(9360), columnWidths: [1872,1404,6084], rows: allocRows }));
children.push(p(""));

// ========== 第六章：风险提示 ==========
children.push(new Paragraph({ children: [new PageBreak()] }));
children.push(h1("六、风险提示"));

children.push(h2("6.1  个股风险"));
bullet("寒武纪：客户集中度极高（字节/阿里），竞争对手（海光/华为昇腾）挤压，估值极高（P/E 185x）");
bullet("海光信息：技术路线依赖 AMD 授权，若美国升级出口管制存在授权风险");
bullet("中际旭创/新易盛：客户集中度（英伟达/北美云厂），中美贸易摩擦可能影响供货");
bullet("北方华创/中微公司：估值极高（P/E 65-78x），关键零部件仍依赖进口，若被列入实体清单影响极大");
bullet("中芯国际：先进制程（7nm 以下）受出口管制，短期盈利承压");

children.push(h2("6.2  行业系统性风险"));
bullet("国产化进度不及预期：部分公司估值已提前反映国产化预期，若进度慢于预期将大幅回调");
bullet("AI 资本开支退潮：若北美云厂（微软/谷歌/Meta）削减 AI 资本开支，供应链将受冲击");
bullet("A 股政策市风险：AI 板块对政策敏感，监管收紧（如限制 AI 应用）将影响估值");
bullet("估值泡沫破裂风险：参照 2000 年互联网泡沫，当普通投资者大量涌入时需警惕");

children.push(h2("6.3  A 股特有风险"));
bullet("大股东减持：解禁期后大股东减持是 A 股常态，需关注解禁时间表");
bullet("概念炒作退潮：部分公司仅蹭 AI 概念，无实质业务，炒作过后将大幅回落");
bullet("北向资金流出：北向资金是 A 股 AI 板块重要增量资金，持续流出将导致板块承压");
bullet("流动性风险：小盘股（如高澜股份 86 亿市值）流动性差，大资金进出困难");

children.push(p(""));
children.push(new Paragraph({
  spacing: { before: 240, after: 120 },
  children: [new TextRun({
    text: "⚠️ 免责声明：本报告所有分析、评分、目标价均基于公开信息和知识库推断，不构成投资建议。A 股投资有风险，入市需谨慎。",
    font: "Arial", size: 20, color: "C0392B", bold: true
  })]
}));

// ========== 生成文档 ==========
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: HDR },
        paragraph: { spacing: { before: 360, after: 200 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2C3E50" },
        paragraph: { spacing: { before: 280, after: 160 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "34495E" },
        paragraph: { spacing: { before: 200, after: 100 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: { size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1200, bottom: 1440, left: 1200 } }
    },
    headers: { default: new Header({ children: [new Paragraph({
      alignment: AlignmentType.RIGHT,
      children: [new TextRun({ text: "A 股 AI 产业链选股分析报告 · 2026.05", font:"Arial", size:18, color:"999999" })]
    })] })},
    footers: { default: new Footer({ children: [new Paragraph({
      alignment: AlignmentType.CENTER,
      children: [
        new TextRun({ text: "第 ", font:"Arial", size:18, color:"999999" }),
        new TextRun({ children: [PageNumber.CURRENT], font:"Arial", size:18, color:"999999" }),
        new TextRun({ text: " 页", font:"Arial", size:18, color:"999999" }),
      ]
    })] })},
    children
  }]
});

const outPath = "c:\\Users\\asus\\WorkBuddy\\20260530114642\\A股AI产业链选股分析报告_20260530.docx";
Packer.toBuffer(doc).then(buf => {
  fs.writeFileSync(outPath, buf);
  console.log("Word 报告生成成功：" + outPath);
}).catch(err => {
  console.error("生成失败：", err);
  process.exit(1);
});
