const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        PageNumber, PageBreak } = require('docx');
const fs = require('fs');

// ========== 通用样式 ==========
const border = { style: BorderStyle.SINGLE, size: 1, color: "999999" };
const borders = { top: border, bottom: border, left: border, right: border };
const cellMargins = { top: 60, bottom: 60, left: 100, right: 100 };
const headerFill = { fill: "1F4E79", type: ShadingType.CLEAR };
const greenFill = { fill: "D5F5E3", type: ShadingType.CLEAR };
const blueFill = { fill: "D4E6F1", type: ShadingType.CLEAR };
const yellowFill = { fill: "FCF3CF", type: ShadingType.CLEAR };
const redFill = { fill: "FADBD8", type: ShadingType.CLEAR };
const lightGrayFill = { fill: "F2F3F4", type: ShadingType.CLEAR };

function headerCell(text, width) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: headerFill,
    margins: cellMargins,
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text, bold: true, font: "Arial", size: 20, color: "FFFFFF" })] })]
  });
}

function bodyCell(text, width, fill, bold) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: fill || { fill: "FFFFFF", type: ShadingType.CLEAR },
    margins: cellMargins,
    children: [new Paragraph({ children: [new TextRun({ text, font: "Arial", size: 20, bold: !!bold })] })]
  });
}

function bodyCellCentered(text, width, fill) {
  return new TableCell({
    borders,
    width: { size: width, type: WidthType.DXA },
    shading: fill || { fill: "FFFFFF", type: ShadingType.CLEAR },
    margins: cellMargins,
    children: [new Paragraph({ alignment: AlignmentType.CENTER, children: [new TextRun({ text, font: "Arial", size: 20 })] })]
  });
}

function makeH1(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun({ text, font: "Arial", size: 32, bold: true })] });
}

function makeH2(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_2, children: [new TextRun({ text, font: "Arial", size: 28, bold: true })] });
}

function makeH3(text) {
  return new Paragraph({ heading: HeadingLevel.HEADING_3, children: [new TextRun({ text, font: "Arial", size: 24, bold: true })] });
}

function makePara(text, options) {
  const runs = [];
  if (options && options.bold) {
    runs.push(new TextRun({ text, font: "Arial", size: 22, bold: true }));
  } else {
    runs.push(new TextRun({ text, font: "Arial", size: 22 }));
  }
  return new Paragraph({ spacing: { after: 120 }, children: runs });
}

function makeBullet(text, ref) {
  return new Paragraph({
    numbering: { reference: ref, level: 0 },
    spacing: { after: 60 },
    children: [new TextRun({ text, font: "Arial", size: 22 })]
  });
}

// ========== 文档内容 ==========

const children = [];

// ---- 封面 ----
children.push(new Paragraph({ spacing: { before: 2400 }, children: [] }));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 200 },
  children: [new TextRun({ text: "AI 产业链选股策略", font: "Arial", size: 52, bold: true, color: "1F4E79" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 100 },
  children: [new TextRun({ text: "包含：原 Prompt 优化建议 + A 股适配版", font: "Arial", size: 28, color: "555555" })]
}));
children.push(new Paragraph({
  alignment: AlignmentType.CENTER,
  spacing: { after: 400 },
  children: [new TextRun({ text: "2026 年 5 月 30 日", font: "Arial", size: 24, color: "888888" })]
}));

// ===== 分隔页 =====
children.push(new Paragraph({ children: [new PageBreak()] }));

// ===== 目录 =====
children.push(makeH1("目录"));
children.push(new TableOfContents("目录", { hyperlink: true, headingStyleRange: "1-3" }));
children.push(new Paragraph({ children: [new PageBreak()] }));

// ============================================================
// 第一部分：原 Prompt 优化建议
// ============================================================
children.push(makeH1("第一部分：原 Prompt 优化修改建议"));

children.push(makePara("以下是对「AI 产业链选股 Prompt（v2.2）」的逐项优化建议，按优先级排序。"));

children.push(makeH2("1. 结构层面优化"));

children.push(makeH3("1.1 增加「数据预处理」步骤"));
children.push(makePara("原 Prompt 直接让 AI 读 Excel 开始分析，但实际使用中 InvestingPro 导出的表格可能包含几十上百只股票、列名是英文、数据格式不一致。建议在「第一步」之前插入一个数据预处理环节："));
children.push(makeBullet("标准化列名（如 P/E → 市盈率、Market Cap → 市值）", "bullets"));
children.push(makeBullet("剔除空白行和明显不相关的行业（如消费品、医药等）", "bullets"));
children.push(makeBullet("标注数据时间点（财报数据是 TTM 还是 FY2025？）", "bullets"));
children.push(makeBullet("对极端值做标记（P/E > 200 或负值单独说明）", "bullets"));

children.push(makeH3("1.2 增加「行业分类辅助映射表」"));
children.push(makePara("很多股票的业务横跨多层（比如 AMD 既有 GPU 也有 FPGA），建议增加一条规则："));
children.push(makeBullet("若一家公司横跨多层，按「主营收入占比最高的层」归类，同时在备注里注明第二业务所属层", "bullets"));
children.push(makeBullet("提供一张常见 AI 股票 → 层级的速查表作为 AI 归类的锚定参考", "bullets"));

children.push(makeH3("1.3 增加「层间联动」分析"));
children.push(makePara("当前每层独立分析，但实际产业链是上下游关系。建议增加一个「产业链传导」小结："));
children.push(makeBullet("哪一层的景气度会先传到哪一层（例如：算力需求↑ → 光模块需求↑ → 衬底材料需求↑）", "bullets"));
children.push(makeBullet("当前处于传导链的哪个位置？是早期（布局上游）还是晚期（布局下游）？", "bullets"));

children.push(makeH2("2. 评分体系优化"));

children.push(makeH3("2.1 评分维度细化"));
children.push(makePara("当前四档评级（🟢🔵🟡🔴）依赖 AI 主观判断，建议增加半定量的打分体系作为辅助："));
children.push(makePara("引入 5 维度打分表（每项 1-5 分）：", { bold: true }));

// 打分维度表
const scoreTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [1560, 2340, 3120, 2340],
  rows: [
    new TableRow({ children: [
      headerCell("维度", 1560), headerCell("权重", 2340), headerCell("评估要点", 3120), headerCell("数据来源", 2340)
    ]}),
    new TableRow({ children: [
      bodyCellCentered("估值", 1560), bodyCellCentered("25%", 2340), bodyCell("P/E、P/S、PEG、距52周高点", 3120), bodyCell("InvestingPro 表格", 2340)
    ]}),
    new TableRow({ children: [
      bodyCellCentered("成长性", 1560, lightGrayFill), bodyCellCentered("25%", 2340, lightGrayFill), bodyCell("收入增速、EPS增速、订单/指引", 3120, lightGrayFill), bodyCell("InvestingPro + AI认知", 2340, lightGrayFill)
    ]}),
    new TableRow({ children: [
      bodyCellCentered("盈利质量", 1560), bodyCellCentered("20%", 2340), bodyCell("毛利率、净利率、ROIC、ROE", 3120), bodyCell("InvestingPro 表格", 2340)
    ]}),
    new TableRow({ children: [
      bodyCellCentered("瓶颈卡位", 1560, lightGrayFill), bodyCellCentered("20%", 2340, lightGrayFill), bodyCell("是否直接受益四大瓶颈", 3120, lightGrayFill), bodyCell("AI认知判断", 2340, lightGrayFill)
    ]}),
    new TableRow({ children: [
      bodyCellCentered("现金流", 1560), bodyCellCentered("10%", 2340), bodyCell("自由现金流/收入、负债率", 3120), bodyCell("InvestingPro 表格", 2340)
    ]}),
  ]
});
children.push(scoreTable);
children.push(makePara(""));
children.push(makeBullet("总分 ≥ 4.0 → 🟢 强烈关注", "bullets"));
children.push(makeBullet("总分 3.0-3.9 → 🔵 关注", "bullets"));
children.push(makeBullet("总分 2.0-2.9 → 🟡 观望", "bullets"));
children.push(makeBullet("总分 < 2.0 → 🔴 回避", "bullets"));

children.push(makeH3("2.2 增加「相对强度」指标"));
children.push(makePara("美股分析应加入相对标普 500/纳斯达克/费城半导体的相对强弱对比，让「跑赢/跑输」有数据支撑而非纯定性。"));

children.push(makeH2("3. 实操层面优化"));

children.push(makeH3("3.1 增加「仓位管理」框架"));
children.push(makePara("当前只有「分批 5-8 批 DCA」，建议补充："));
children.push(makeBullet("总仓位上限：单一股票 ≤ 5%、单一层级 ≤ 20%、AI 产业链总计 ≤ 40%（对小白而言）", "bullets"));
children.push(makeBullet("建仓节奏：首次建仓 20-30%，每跌 5-8% 加一批，不要追涨加仓", "bullets"));
children.push(makeBullet("止损线：单票跌 15-20% 必须重新评估，不设止损的小白最容易亏大钱", "bullets"));

children.push(makeH3("3.2 增加「定期复盘」模板"));
children.push(makePara("建议在 Prompt 末尾加入一个简单的月度/季度检查清单："));
children.push(makeBullet("□ 持仓股财报是否超预期/低于预期？", "bullets"));
children.push(makeBullet("□ 四大瓶颈是否有新变化（如 CoWoS 扩产进度）？", "bullets"));
children.push(makeBullet("□ 是否有新的催化剂/利空出现？", "bullets"));
children.push(makeBullet("□ 估值是否已进入极端区域（P/E 远超历史均值 2σ）？", "bullets"));

children.push(makeH2("4. 数据源层面优化"));

children.push(makeH3("4.1 补充数据源建议"));
children.push(makePara("当前只依赖 InvestingPro 导出的 Excel，但 InvestingPro 的免费版数据有限。建议在 Prompt 中提示用户："));
children.push(makeBullet("财报数据可用 Seeking Alpha / Yahoo Finance 交叉验证", "bullets"));
children.push(makeBullet("机构持仓变化可参考 WhaleWisdom（13F 文件）", "bullets"));
children.push(makeBullet("做空比例可查 MarketBeat / Fintel", "bullets"));
children.push(makeBullet("行业景气度可参考 SEMI 设备出货数据、台积电月度营收", "bullets"));

children.push(makeH2("5. 风险提示优化"));

children.push(makePara("当前风险提示只针对个股，建议增加以下宏观层面风险提示："));
children.push(makeBullet("半导体周期风险：AI 需求虽强，但传统半导体仍受周期影响，注意费城半导体指数的估值分位", "bullets"));
children.push(makeBullet("地缘政治风险：台积电/三星的地缘集中度、出口管制升级可能性", "bullets"));
children.push(makeBullet("AI 泡沫风险：参考 2000 年互联网泡沫，当非专业投资者大量涌入时需警惕", "bullets"));
children.push(makeBullet("汇率风险：对 A 股投资者而言，投资美股有汇率波动风险", "bullets"));

// ===== 分隔页 =====
children.push(new Paragraph({ children: [new PageBreak()] }));

// ============================================================
// 第二部分：A 股 AI 产业链选股策略
// ============================================================
children.push(makeH1("第二部分：适合 A 股的 AI 产业链选股策略"));

children.push(makeH2("一、A 股 vs 美股 AI 投资的本质差异"));

// A股美股对比表
const diffTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [2000, 3680, 3680],
  rows: [
    new TableRow({ children: [
      headerCell("对比维度", 2000), headerCell("美股 AI 投资", 3680), headerCell("A 股 AI 投资", 3680)
    ]}),
    new TableRow({ children: [
      bodyCell("核心逻辑", 2000, lightGrayFill, true),
      bodyCell("技术创新驱动，买「全球龙头」", 3680, lightGrayFill),
      bodyCell("国产替代 + 政策驱动，买「中国供应链」", 3680, lightGrayFill)
    ]}),
    new TableRow({ children: [
      bodyCell("代表标的", 2000, null, true),
      bodyCell("NVDA、AVGO、TSM — 全球垄断性企业", 3680),
      bodyCell("中芯国际、寒武纪、海光信息 — 国产替代标的", 3680)
    ]}),
    new TableRow({ children: [
      bodyCell("估值体系", 2000, lightGrayFill, true),
      bodyCell("PEG 为核心，市场愿给高增速高估值", 3680, lightGrayFill),
      bodyCell("政策溢价/国产替代溢价，P/E 经常偏高", 3680, lightGrayFill)
    ]}),
    new TableRow({ children: [
      bodyCell("核心风险", 2000, null, true),
      bodyCell("估值回调、技术路线变化", 3680),
      bodyCell("出口管制、技术封锁、概念炒作退潮", 3680, lightGrayFill)
    ]}),
    new TableRow({ children: [
      bodyCell("波动特征", 2000, lightGrayFill, true),
      bodyCell("趋势性强、回调幅度相对可控", 3680, lightGrayFill),
      bodyCell("题材驱动、暴涨暴跌、轮动极快", 3680)
    ]}),
    new TableRow({ children: [
      bodyCell("信息优势", 2000, null, true),
      bodyCell("信息透明、机构主导", 3680),
      bodyCell("内幕信息/政策先知优势明显，散户信息滞后", 3680, lightGrayFill)
    ]}),
  ]
});
children.push(diffTable);
children.push(makePara(""));

children.push(makeH2("二、A 股 AI 产业链 7 层分类（中国版）"));

children.push(makePara("以下按 A 股实际情况重新划分 AI 产业链，每层给出 A 股代表性标的（仅为参考，实际选股需结合财报数据）。"));

// A股7层表
const aShareLayers = [
  {
    num: "一", emoji: "🎮", name: "算力芯片（AI 芯片）",
    desc: "AI 的「大脑」，但 A 股没有英伟达，核心逻辑是「国产替代 + 自主可控」",
    examples: "寒武纪、海光信息、景嘉微、龙芯中科",
    bottleneck: "算力缺口（国产GPU性能差距）"
  },
  {
    num: "二", emoji: "💾", name: "存储芯片与先进封装",
    desc: "HBM（高带宽内存）是 AI 算力的「高速公路」——A 股核心看封测环节",
    examples: "长电科技、通富微电、深科技、佰维存储、兆易创新",
    bottleneck: "CoWoS 封装、HBM 产能"
  },
  {
    num: "三", emoji: "🌈", name: "光通信 / 光模块",
    desc: "AI 数据中心内部用光传输数据，A 股在这个环节是全球核心供应商",
    examples: "中际旭创、新易盛、天孚通信、光迅科技",
    bottleneck: "800G/1.6T 光模块需求爆发"
  },
  {
    num: "四", emoji: "🌐", name: "网络设备与高速互联",
    desc: "把 GPU 服务器连成集群的交换机、高速背板",
    examples: "紫光股份（新华三）、锐捷网络、中兴通讯",
    bottleneck: "800G 交换机、高速 PCB"
  },
  {
    num: "五", emoji: "🏭", name: "半导体制造与设备",
    desc: "真正「造芯片」——晶圆代工、半导体设备、材料",
    examples: "中芯国际、北方华创、中微公司、沪硅产业",
    bottleneck: "先进制程受限（7nm以下被卡）"
  },
  {
    num: "六", emoji: "⚡", name: "数据中心基础设施",
    desc: "AI 机房的电力、散热、温控、服务器组装",
    examples: "英维克、高澜股份、科华数据、浪潮信息",
    bottleneck: "数据中心电力、液冷散热"
  },
  {
    num: "七", emoji: "💡", name: "AI 应用与软件",
    desc: "把 AI 能力用到具体场景（办公、编程、医疗、金融等）",
    examples: "科大讯飞、金山办公、拓尔思、中科曙光（软件层）",
    bottleneck: "应用落地速度、商业模式验证"
  },
];

aShareLayers.forEach(layer => {
  children.push(makeH3(`第${layer.num}层：${layer.emoji} ${layer.name}`));
  children.push(makePara(layer.desc));
  children.push(makePara(`代表标的（仅供参考）：${layer.examples}`, { bold: true }));
  children.push(makePara(`瓶颈方向：${layer.bottleneck}`));
});

children.push(makeH2("三、A 股 AI 选股核心逻辑"));

children.push(makeH3("3.1 三大主线"));
children.push(makeBullet("主线一：国产替代（最硬逻辑）— 被卡脖子的环节，政策扶持力度最大", "bullets"));
children.push(makeBullet("  重点关注：先进封装（CoWoS 替代方案）、半导体设备（去美化）、EDA 工具", "bullets"));
children.push(makeBullet("主线二：全球供应链（业绩确定性最高）— A 股公司在全球 AI 供应链中不可替代的环节", "bullets"));
children.push(makeBullet("  重点关注：光模块（中际旭创是全球龙头）、高速 PCB、服务器代工", "bullets"));
children.push(makeBullet("主线三：AI 应用落地（弹性最大但确定性最低）— AI 赋能各行业带来的增量", "bullets"));
children.push(makeBullet("  重点关注：AI+办公、AI+医疗、AI+金融、智能驾驶", "bullets"));

children.push(makeH3("3.2 A 股专属评分体系"));
children.push(makePara("与美股不同，A 股选股需加入以下特有维度："));

// A股评分表
const aScoreTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [1872, 1872, 5616],
  rows: [
    new TableRow({ children: [
      headerCell("评分维度", 1872), headerCell("权重", 1872), headerCell("评估要点（A 股特有）", 5616)
    ]}),
    new TableRow({ children: [
      bodyCell("国产替代紧迫度", 1872, null, true), bodyCellCentered("20%", 1872),
      bodyCell("该环节国产化率？被列入「卡脖子」清单的优先级？是否有大基金扶持？", 5616)
    ]}),
    new TableRow({ children: [
      bodyCell("全球供应链地位", 1872, lightGrayFill, true), bodyCellCentered("20%", 1872, lightGrayFill),
      bodyCell("在全球 AI 供应链中是否不可替代？海外大客户（英伟达/谷歌/微软）订单占比？", 5616, lightGrayFill)
    ]}),
    new TableRow({ children: [
      bodyCell("业绩兑现能力", 1872, null, true), bodyCellCentered("25%", 1872),
      bodyCell("收入/利润是否已经体现在财报上？（A 股概念炒作多，业绩兑现是关键分水岭）", 5616)
    ]}),
    new TableRow({ children: [
      bodyCell("估值安全边际", 1872, lightGrayFill, true), bodyCellCentered("20%", 1872, lightGrayFill),
      bodyCell("P/E 分位数 vs 历史区间？距 52 周高点回撤幅度？（A 股高波动，估值回撤是常态）", 5616, lightGrayFill)
    ]}),
    new TableRow({ children: [
      bodyCell("资金面信号", 1872, null, true), bodyCellCentered("15%", 1872),
      bodyCell("北向资金持仓变化？龙虎榜机构净买入？大宗交易折溢价？（A 股资金面信号重要）", 5616)
    ]}),
  ]
});
children.push(aScoreTable);
children.push(makePara(""));

children.push(makeH2("四、A 股 AI 投资操作指南"));

children.push(makeH3("4.1 选股渠道（替代 InvestingPro）"));
children.push(makePara("InvestingPro 主要覆盖美股，A 股数据应从以下渠道获取："));
children.push(makeBullet("同花顺 iFinD / Wind 金融终端（专业版，机构常用）", "bullets"));
children.push(makeBullet("东方财富 Choice 数据（性价比较高，散户友好）", "bullets"));
children.push(makeBullet("雪球 / 同花顺 App（免费，适合初步筛选）", "bullets"));
children.push(makeBullet("上市公司财报原文（巨潮资讯网 cninfo.com.cn）", "bullets"));
children.push(makeBullet("北向资金流向 → 东方财富网「沪深港通」频道", "bullets"));
children.push(makeBullet("龙虎榜数据 → 同花顺/东方财富龙虎榜页面", "bullets"));

children.push(makeH3("4.2 A 股特有风险提示"));
children.push(makeBullet("概念炒作风险：A 股 AI 概念股众多，很多公司只是蹭概念、无实质业务", "bullets"));
children.push(makeBullet("大股东减持风险：A 股解禁期后大股东减持常见，需关注解禁时间表", "bullets"));
children.push(makeBullet("ST/退市风险：连续亏损可能被 ST，注册制下退市常态化", "bullets"));
children.push(makeBullet("政策风险：行业监管政策变化（如 AI 监管新规、反垄断）", "bullets"));
children.push(makeBullet("流动性风险：小盘股流动性差，大资金进出困难", "bullets"));
children.push(makeBullet("信息不对称风险：A 股内幕交易处罚力度不如美股，散户处于信息劣势", "bullets"));

children.push(makeH3("4.3 A 股建仓策略"));
children.push(makePara("A 股波动远超美股，建仓策略需更保守："));
children.push(makeBullet("单票仓位上限：3%（比美股 5% 更保守）", "bullets"));
children.push(makeBullet("AI 产业链总仓位：不超过 30%", "bullets"));
children.push(makeBullet("建仓节奏：首次 15-20%，每跌 8-10% 加一批（A 股波动大，间隔要拉大）", "bullets"));
children.push(makeBullet("止损线：单票跌 12-15% 止损（比美股更紧，A 股下跌动能更强）", "bullets"));
children.push(makeBullet("加仓禁区：涨停板不追、利好消息当日不追、北向资金大幅流出时不加", "bullets"));

children.push(makeH2("五、A 股 AI 产业链选股 Prompt（可直接使用）"));

children.push(makePara("以下是一份可直接配合 A 股数据使用的选股 Prompt："));

children.push(new Paragraph({ children: [new PageBreak()] }));

// ---- A股Prompt内容 ----
children.push(makeH2("A 股 AI 产业链选股 Prompt（七层 · 小白友好版 v1.0）"));

children.push(makeH3("角色"));
children.push(makePara("你是一位深耕 A 股的 AI 产业链分析师。你面对的是想布局 A 股 AI 赛道、但对产业链还不够熟悉的小白。要求：通俗解释、不堆术语、重点说清楚「为什么这只票值得看」和「有什么坑」。用简体中文输出。"));

children.push(makeH3("输入说明"));
children.push(makePara("我会提供一份从同花顺/东方财富/Wind 导出的股票数据表格。请严格只用表格里的股票做分析，不要自行添加表格外的股票。表格里缺的数据可用你已知信息补充，缺失标注 N/A，绝不编造。"));

children.push(makeH3("第一步：按 A 股 AI 产业链七层归类"));
children.push(makePara("将表格中每只股票归入以下层级。不属于这七层的票剔除。"));

// A股7层简表
const aLayerTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [1200, 2800, 2800, 2560],
  rows: [
    new TableRow({ children: [
      headerCell("层", 1200), headerCell("层级名称", 2800), headerCell("大白话", 2800), headerCell("A股代表（仅参考）", 2560)
    ]}),
    ...[
      ["一", "算力芯片", "AI 的大脑，国产替代核心", "寒武纪、海光信息"],
      ["二", "存储+封测", "给大脑配仓库，卡在先进封装", "长电科技、通富微电"],
      ["三", "光通信", "用光传数据，A 股全球最强环节", "中际旭创、新易盛"],
      ["四", "网络设备", "连接 GPU 集群", "紫光股份、锐捷网络"],
      ["五", "半导体制造", "造芯片的厂和设备", "中芯国际、北方华创"],
      ["六", "数据中心基建", "供电散热、服务器", "英维克、浪潮信息"],
      ["七", "AI 应用/软件", "把 AI 用到实际场景", "科大讯飞、金山办公"],
    ].map((row, i) => new TableRow({ children: [
      bodyCellCentered(row[0], 1200, i % 2 === 0 ? null : lightGrayFill),
      bodyCell(row[1], 2800, i % 2 === 0 ? null : lightGrayFill, true),
      bodyCell(row[2], 2800, i % 2 === 0 ? null : lightGrayFill),
      bodyCell(row[3], 2560, i % 2 === 0 ? null : lightGrayFill),
    ]}))
  ]
});
children.push(aLayerTable);
children.push(makePara(""));

children.push(makeH3("第二步：标记 A 股专属「卡脖子」标签 🔥"));
children.push(makePara("当前 A 股 AI 投资四大卡脖子方向："));
children.push(makeBullet("① 先进封装（CoWoS 被禁后的替代方案）", "bullets"));
children.push(makeBullet("② 先进制程（7nm 以下被封锁，国产突破预期）", "bullets"));
children.push(makeBullet("③ 半导体设备/材料（去美化、自主可控）", "bullets"));
children.push(makeBullet("④ 算力芯片（GPU/NPU 国产替代）", "bullets"));
children.push(makePara("凡直接受益以上任一方向的票，标注 🔥 并注明方向。"));

children.push(makeH3("第三步：A 股小白评级"));
children.push(makeBullet("🟢 强烈关注：业绩已兑现 + 国产替代核心 + 估值合理", "bullets"));
children.push(makeBullet("🔵 关注：好赛道好公司，但估值偏高/等回调", "bullets"));
children.push(makeBullet("🟡 观望：概念为主、业绩待验证、或估值已透支", "bullets"));
children.push(makeBullet("🔴 回避：纯概念炒作、无实质业务、或基本面恶化", "bullets"));

children.push(makeH3("输出格式（按层分组）"));
children.push(makePara("每层：一句话大白话说明 → 然后给表格："));

// A股输出格式表
const outFmtTable = new Table({
  width: { size: 9360, type: WidthType.DXA },
  columnWidths: [1200, 2000, 800, 800, 1400, 1400, 1400],
  rows: [
    new TableRow({ children: [
      headerCell("代码", 1200), headerCell("公司(做什么)", 2000), headerCell("🔥", 800), headerCell("评级", 800),
      headerCell("为什么好", 1400), headerCell("估值/风险", 1400), headerCell("怎么操作", 1400)
    ]}),
  ]
});
children.push(outFmtTable);
children.push(makePara(""));

children.push(makeH3("补充模块"));
children.push(makePara("🚫 避开清单：列出被剔除的票，尤其点名「挂 AI 概念但无实质业务」的纯炒作股。"));
children.push(makePara("✅ 下一步："));
children.push(makeBullet("把 🟢🔵 票加入自选股，在同花顺/东方财富设置价格提醒", "bullets"));
children.push(makeBullet("盯紧三件事：最新财报、北向资金动向、距 52 周高点位置", "bullets"));
children.push(makeBullet("别追涨停板——等回调到 20 日/60 日均线附近再考虑", "bullets"));
children.push(makeBullet("每个卡脖子方向至少放 1 只 🔥 票", "bullets"));

children.push(makeH3("规则"));
children.push(makeBullet("简体中文输出；数据不擅自换算；缺失标 N/A", "bullets"));
children.push(makeBullet("这是研究框架，不是投资建议", "bullets"));

// ============================================================
// 生成文档
// ============================================================
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 22 } } },
    paragraphStyles: [
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial", color: "1F4E79" },
        paragraph: { spacing: { before: 360, after: 240 }, outlineLevel: 0 } },
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial", color: "2C3E50" },
        paragraph: { spacing: { before: 280, after: 180 }, outlineLevel: 1 } },
      { id: "Heading3", name: "Heading 3", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 24, bold: true, font: "Arial", color: "34495E" },
        paragraph: { spacing: { before: 200, after: 120 }, outlineLevel: 2 } },
    ]
  },
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "\u2022", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    properties: {
      page: {
        size: { width: 12240, height: 15840 },
        margin: { top: 1440, right: 1200, bottom: 1440, left: 1200 }
      }
    },
    headers: {
      default: new Header({
        children: [new Paragraph({
          alignment: AlignmentType.RIGHT,
          children: [new TextRun({ text: "AI 产业链选股策略 · 2026.05", font: "Arial", size: 18, color: "999999" })]
        })]
      })
    },
    footers: {
      default: new Footer({
        children: [new Paragraph({
          alignment: AlignmentType.CENTER,
          children: [
            new TextRun({ text: "第 ", font: "Arial", size: 18, color: "999999" }),
            new TextRun({ children: [PageNumber.CURRENT], font: "Arial", size: 18, color: "999999" }),
            new TextRun({ text: " 页", font: "Arial", size: 18, color: "999999" }),
          ]
        })]
      })
    },
    children
  }]
});

const outputPath = "c:\\Users\\asus\\WorkBuddy\\20260530114642\\AI产业链选股策略_优化建议与A股适配版.docx";

Packer.toBuffer(doc).then(buffer => {
  fs.writeFileSync(outputPath, buffer);
  console.log("DOCX 生成成功: " + outputPath);
}).catch(err => {
  console.error("生成失败:", err);
  process.exit(1);
});
