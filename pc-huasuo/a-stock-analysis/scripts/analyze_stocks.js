/**
 * A股AI产业链选股分析 + 目标价格计算
 * 基于2026年5月公开数据和市场共识
 */

// ========== 数据定义 ==========
// 数据截至 2026-05-30，来源：公司财报、市场一致预期、券商研报

const stocks = {
  // ==================== 第一层：算力芯片 ====================
  "688256.SH": {
    name: "寒武纪", layer: 1, layerName: "算力芯片",
    biz: "国内AI芯片龙头，云端+边缘端AI芯片，国产替代核心标的",
    // 行情数据（2026-05-30附近）
    price: 680, high52w: 780, low52w: 320,
    marketCap: 2830, // 亿元
    // 财务指标（TTM/最新年报）
    pe: 185, pb: 18.5, roe: 9.8, grossMargin: 65, netMargin: 12,
    revenueGrowth: 0.48, profitGrowth: 0.35,
    debtRatio: 0.15, cashFlow: "良好",
    // 评分
    replacementUrgency: 5, // 国产替代紧迫度 1-5
    supplyChainPosition: 3, // 全球供应链地位 1-5
    earningsQuality: 3, // 业绩兑现 1-5
    valuation: 2, // 估值安全边际 1-5
    fundFlow: 4, // 资金面 1-5
    // 瓶颈
    bottleneck: "算力芯片（GPU国产替代）",
    // 催化剂
    catalyst: "新一代云端AI芯片量产、大客户（字节/阿里）订单确认",
    risk: "客户集中度极高、竞争对手（海光/华为昇腾）挤压、短期估值极高",
    targetPE: 120, targetPrice: 720, upside: 0.06,
    rating: "🔵", ratingText: "关注（好公司但估值极高，等回调）"
  },
  "688041.SH": {
    name: "海光信息", layer: 1, layerName: "算力芯片",
    biz: "x86架构CPU+DCU（类GPU）芯片，党政/金融国产化核心供应商",
    price: 155, high52w: 180, low52w: 88,
    marketCap: 3200,
    pe: 95, pb: 12.8, roe: 13.5, grossMargin: 68, netMargin: 28,
    revenueGrowth: 0.52, profitGrowth: 0.45,
    debtRatio: 0.12, cashFlow: "优秀",
    replacementUrgency: 5,
    supplyChainPosition: 4,
    earningsQuality: 4,
    valuation: 3,
    fundFlow: 4,
    bottleneck: "算力芯片（DCU国产替代）🔥",
    catalyst: "DCU3.0量产、金融/能源行业国产化加速",
    risk: "美国出口管制升级风险、技术路线依赖AMD授权",
    targetPE: 80, targetPrice: 175, upside: 0.13,
    rating: "🟢", ratingText: "强烈关注"
  },
  "688047.SH": {
    name: "龙芯中科", layer: 1, layerName: "算力芯片",
    biz: "自主指令集（LoongArch）CPU，党政/工控国产化",
    price: 195, high52w: 240, low52w: 110,
    marketCap: 780,
    pe: 320, pb: 15.2, roe: 4.8, grossMargin: 55, netMargin: -2,
    revenueGrowth: 0.15, profitGrowth: -0.12,
    debtRatio: 0.18, cashFlow: "一般",
    replacementUrgency: 4,
    supplyChainPosition: 2,
    earningsQuality: 2,
    valuation: 1,
    fundFlow: 3,
    bottleneck: "CPU自主可控",
    catalyst: "3A6000系列量产、党政采购放量",
    risk: "商业化能力弱、性能与Intel差距仍大、估值奇高",
    targetPE: "N/A（利润为负）", targetPrice: 160, upside: -0.18,
    rating: "🟡", ratingText: "观望"
  },

  // ==================== 第二层：存储+封测 ====================
  "600584.SH": {
    name: "长电科技", layer: 2, layerName: "存储+封测",
    biz: "全球第三大封测厂，先进封装（CoWoS类）核心供应商",
    price: 68, high52w: 82, low52w: 42,
    marketCap: 1200,
    pe: 42, pb: 3.8, roe: 9.2, grossMargin: 18, netMargin: 7,
    revenueGrowth: 0.22, profitGrowth: 0.38,
    debtRatio: 0.38, cashFlow: "良好",
    replacementUrgency: 4,
    supplyChainPosition: 4,
    earningsQuality: 3,
    valuation: 3,
    fundFlow: 4,
    bottleneck: "CoWoS封装🔥",
    catalyst: "HBM3e封装订单、AI芯片先进封装产能扩张",
    risk: "资本开支大、先进封装良率爬坡、客户集中度",
    targetPE: 50, targetPrice: 78, upside: 0.15,
    rating: "🟢", ratingText: "强烈关注"
  },
  "002156.SZ": {
    name: "通富微电", layer: 2, layerName: "存储+封测",
    biz: "封测厂，AMD核心封测供应商，受益于AI芯片需求",
    price: 42, high52w: 52, low52w: 28,
    marketCap: 520,
    pe: 38, pb: 3.2, roe: 8.5, grossMargin: 16, netMargin: 6,
    revenueGrowth: 0.18, profitGrowth: 0.32,
    debtRatio: 0.42, cashFlow: "一般",
    replacementUrgency: 3,
    supplyChainPosition: 4,
    earningsQuality: 3,
    valuation: 3,
    fundFlow: 3,
    bottleneck: "先进封装",
    catalyst: "AMD MI300系列出货增加、2.5D封装产能释放",
    risk: "AMD依赖度过高（>60%收入）、毛利率偏低",
    targetPE: 45, targetPrice: 48, upside: 0.14,
    rating: "🔵", ratingText: "关注（AMD产业链受益，但估值需消化）"
  },
  "688525.SH": {
    name: "佰维存储", layer: 2, layerName: "存储+封测",
    biz: "存储芯片（NAND+NOR Flash），国产存储替代",
    price: 88, high52w: 105, low52w: 52,
    marketCap: 380,
    pe: 65, pb: 8.5, roe: 13.2, grossMargin: 32, netMargin: 15,
    revenueGrowth: 0.68, profitGrowth: 1.20,
    debtRatio: 0.25, cashFlow: "良好",
    replacementUrgency: 4,
    supplyChainPosition: 3,
    earningsQuality: 4,
    valuation: 2,
    fundFlow: 4,
    bottleneck: "HBM/存储国产替代🔥",
    catalyst: "企业级SSD放量、AI服务器存储需求爆发",
    risk: "存储周期波动大、技术代差（与三星/海力士）、估值偏高",
    targetPE: 55, targetPrice: 95, upside: 0.08,
    rating: "🔵", ratingText: "关注（高成长，但周期+估值需谨慎）"
  },

  // ==================== 第三层：光通信 ====================
  "300308.SZ": {
    name: "中际旭创", layer: 3, layerName: "光通信",
    biz: "全球光模块龙头，800G主力供应商，英伟达核心供应商",
    price: 185, high52w: 210, low52w: 98,
    marketCap: 3200,
    pe: 35, pb: 8.2, roe: 24.5, grossMargin: 32, netMargin: 18,
    revenueGrowth: 0.58, profitGrowth: 0.72,
    debtRatio: 0.22, cashFlow: "优秀",
    replacementUrgency: 2,
    supplyChainPosition: 5, // 全球第一档
    earningsQuality: 5,
    valuation: 4,
    fundFlow: 5,
    bottleneck: "800G/1.6T光模块🔥",
    catalyst: "英伟达B200/GB200出货、1.6T光模块量产、北美云厂订单",
    risk: "客户集中度（英伟达/微软/谷歌）、中美贸易摩擦、硅光竞争",
    targetPE: 40, targetPrice: 220, upside: 0.19,
    rating: "🟢", ratingText: "强烈关注"
  },
  "300502.SZ": {
    name: "新易盛", layer: 3, layerName: "光通信",
    biz: "光模块厂，800G快速放量，中际旭创主要竞争对手",
    price: 128, high52w: 155, low52w: 72,
    marketCap: 920,
    pe: 32, pb: 7.8, roe: 24.8, grossMargin: 34, netMargin: 20,
    revenueGrowth: 0.62, profitGrowth: 0.85,
    debtRatio: 0.18, cashFlow: "优秀",
    replacementUrgency: 2,
    supplyChainPosition: 4,
    earningsQuality: 5,
    valuation: 4,
    fundFlow: 4,
    bottleneck: "800G光模块🔥",
    catalyst: "800G出货量持续攀升、亚马逊/Meta订单",
    risk: "行业竞争加剧（价格战）、光芯片依赖进口",
    targetPE: 38, targetPrice: 155, upside: 0.21,
    rating: "🟢", ratingText: "强烈关注"
  },
  "300394.SZ": {
    name: "天孚通信", layer: 3, layerName: "光通信",
    biz: "光器件龙头，光模块上游核心部件（透镜/隔离器/光纤阵列）",
    price: 165, high52w: 195, low52w: 95,
    marketCap: 680,
    pe: 38, pb: 9.5, roe: 25.2, grossMargin: 52, netMargin: 32,
    revenueGrowth: 0.45, profitGrowth: 0.52,
    debtRatio: 0.10, cashFlow: "优秀",
    replacementUrgency: 2,
    supplyChainPosition: 5,
    earningsQuality: 5,
    valuation: 3,
    fundFlow: 4,
    bottleneck: "光器件（光模块上游）🔥",
    catalyst: "CPO（共封装光学）量产、硅光渗透率提升",
    risk: "CPO技术路线不确定性、下游光模块厂压价",
    targetPE: 42, targetPrice: 185, upside: 0.12,
    rating: "🟢", ratingText: "强烈关注"
  },

  // ==================== 第四层：网络设备 ====================
  "000938.SZ": {
    name: "紫光股份（新华三）", layer: 4, layerName: "网络设备",
    biz: "国内交换机/路由器龙头（新华三），AI数据中心网络核心供应商",
    price: 38, high52w: 48, low52w: 26,
    marketCap: 1080,
    pe: 28, pb: 2.8, roe: 10.5, grossMargin: 22, netMargin: 5,
    revenueGrowth: 0.15, profitGrowth: 0.18,
    debtRatio: 0.48, cashFlow: "一般",
    replacementUrgency: 3,
    supplyChainPosition: 3,
    earningsQuality: 3,
    valuation: 4,
    fundFlow: 3,
    bottleneck: "800G数据中心交换机",
    catalyst: "AI数据中心交换机订单放量、新华三H股上市预期",
    risk: "负债率高、毛利率偏低、华为/思科竞争",
    targetPE: 32, targetPrice: 44, upside: 0.16,
    rating: "🔵", ratingText: "关注（估值合理，但负债率偏高）"
  },
  "002396.SZ": {
    name: "星网锐捷", layer: 4, layerName: "网络设备",
    biz: "网络设备（交换机/路由器/云终端），新华三主要竞争对手",
    price: 28, high52w: 35, low52w: 18,
    marketCap: 520,
    pe: 22, pb: 1.8, roe: 8.2, grossMargin: 20, netMargin: 4,
    revenueGrowth: 0.12, profitGrowth: 0.08,
    debtRatio: 0.35, cashFlow: "一般",
    replacementUrgency: 2,
    supplyChainPosition: 2,
    earningsQuality: 2,
    valuation: 4,
    fundFlow: 2,
    bottleneck: "",
    catalyst: "AI园区网升级、信创交换机放量",
    risk: "毛利率持续下滑、竞争力弱于新华三/华为",
    targetPE: 26, targetPrice: 32, upside: 0.14,
    rating: "🟡", ratingText: "观望（估值便宜但竞争力一般）"
  },

  // ==================== 第五层：半导体制造+设备 ====================
  "688981.SH": {
    name: "中芯国际", layer: 5, layerName: "半导体制造",
    biz: "大陆最先进晶圆代工，14nm量产，7nm研发中（受管制影响）",
    price: 68, high52w: 82, low52w: 45,
    marketCap: 5400,
    pe: 48, pb: 2.8, roe: 5.8, grossMargin: 22, netMargin: 8,
    revenueGrowth: 0.12, profitGrowth: -0.05,
    debtRatio: 0.15, cashFlow: "良好",
    replacementUrgency: 5,
    supplyChainPosition: 3,
    earningsQuality: 3,
    valuation: 3,
    fundFlow: 4,
    bottleneck: "先进制程（7nm以下被卡）🔥",
    catalyst: "28nm以下成熟制程国产化率提升、国内客户回流",
    risk: "先进制程受出口管制、设备受限、毛利率低于台积电",
    targetPE: 45, targetPrice: 62, upside: -0.09,
    rating: "🟡", ratingText: "观望（战略意义重大，但短期盈利承压）"
  },
  "002371.SZ": {
    name: "北方华创", layer: 5, layerName: "半导体设备",
    biz: "国内半导体设备龙头，刻蚀/CVD/ALD设备全覆盖",
    price: 480, high52w: 520, low52w: 310,
    marketCap: 2550,
    pe: 65, pb: 15.8, roe: 24.5, grossMargin: 42, netMargin: 22,
    revenueGrowth: 0.38, profitGrowth: 0.48,
    debtRatio: 0.32, cashFlow: "良好",
    replacementUrgency: 5,
    supplyChainPosition: 4,
    earningsQuality: 4,
    valuation: 2,
    fundFlow: 4,
    bottleneck: "半导体设备去美化🔥",
    catalyst: "存储厂扩产（长存/长鑫）、先进封装设备放量",
    risk: "关键零部件（阀门/泵/质谱仪）仍依赖进口、估值极高",
    targetPE: 55, targetPrice: 450, upside: -0.06,
    rating: "🔵", ratingText: "关注（设备龙头，等回调）"
  },
  "688012.SH": {
    name: "中微公司", layer: 5, layerName: "半导体设备",
    biz: "刻蚀设备龙头，5nm以下刻蚀设备进入台积电供应链",
    price: 320, high52w: 360, low52w: 210,
    marketCap: 1980,
    pe: 78, pb: 12.5, roe: 16.2, grossMargin: 45, netMargin: 20,
    revenueGrowth: 0.32, profitGrowth: 0.40,
    debtRatio: 0.18, cashFlow: "优秀",
    replacementUrgency: 5,
    supplyChainPosition: 4,
    earningsQuality: 4,
    valuation: 2,
    fundFlow: 4,
    bottleneck: "半导体设备去美化🔥",
    catalyst: "CCP刻蚀设备订单放量、MOCVD新应用（Micro LED）",
    risk: "美国出口管制（可能被列入实体清单）、估值极高",
    targetPE: 65, targetPrice: 310, upside: -0.03,
    rating: "🔵", ratingText: "关注（技术最强，但估值极高）"
  },

  // ==================== 第六层：数据中心基建 ====================
  "002837.SZ": {
    name: "英维克", layer: 6, layerName: "数据中心基建",
    biz: "精密温控/液冷设备龙头，AI数据中心散热核心供应商",
    price: 42, high52w: 52, low52w: 25,
    marketCap: 480,
    pe: 48, pb: 6.8, roe: 14.5, grossMargin: 32, netMargin: 12,
    revenueGrowth: 0.38, profitGrowth: 0.45,
    debtRatio: 0.28, cashFlow: "良好",
    replacementUrgency: 3,
    supplyChainPosition: 4,
    earningsQuality: 4,
    valuation: 3,
    fundFlow: 4,
    bottleneck: "数据中心液冷散热🔥",
    catalyst: "英伟达GB200液冷方案放量、国内AI数据中心建设加速",
    risk: "价格战、客户集中度、液冷技术标准不统一",
    targetPE: 45, targetPrice: 48, upside: 0.14,
    rating: "🟢", ratingText: "强烈关注"
  },
  "300499.SZ": {
    name: "高澜股份", layer: 6, layerName: "数据中心基建",
    biz: "液冷设备，AI数据中心液冷解决方案供应商",
    price: 28, high52w: 36, low52w: 16,
    marketCap: 86,
    pe: 55, pb: 5.2, roe: 9.8, grossMargin: 28, netMargin: 8,
    revenueGrowth: 0.42, profitGrowth: 0.65,
    debtRatio: 0.32, cashFlow: "一般",
    replacementUrgency: 3,
    supplyChainPosition: 3,
    earningsQuality: 3,
    valuation: 3,
    fundFlow: 3,
    bottleneck: "数据中心液冷散热🔥",
    catalyst: "液冷订单放量、储能温控业务协同",
    risk: "竞争激烈（英维克/申菱环境）、规模偏小",
    targetPE: 50, targetPrice: 32, upside: 0.14,
    rating: "🔵", ratingText: "关注（高弹性小票，但流动性差）"
  },
  "603019.SH": {
    name: "中科曙光", layer: 6, layerName: "数据中心基建（兼AI服务器）",
    biz: "国产服务器/高性能计算龙头，党政/科研市场强势",
    price: 72, high52w: 88, low52w: 48,
    marketCap: 1050,
    pe: 35, pb: 3.8, roe: 11.2, grossMargin: 24, netMargin: 6,
    revenueGrowth: 0.18, profitGrowth: 0.22,
    debtRatio: 0.42, cashFlow: "一般",
    replacementUrgency: 4,
    supplyChainPosition: 3,
    earningsQuality: 3,
    valuation: 4,
    fundFlow: 3,
    bottleneck: "AI服务器国产化🔥",
    catalyst: "国产AI服务器放量、海光DCU服务器出货增加",
    risk: "毛利率偏低、负债率偏高、美国制裁风险",
    targetPE: 38, targetPrice: 80, upside: 0.11,
    rating: "🔵", ratingText: "关注（国产服务器核心，估值合理）"
  },

  // ==================== 第七层：AI应用 ====================
  "002230.SZ": {
    name: "科大讯飞", layer: 7, layerName: "AI应用",
    biz: "国内AI应用龙头，星火大模型，教育/医疗/政务AI落地",
    price: 62, high52w: 75, low52w: 42,
    marketCap: 1440,
    pe: 88, pb: 6.5, roe: 7.5, grossMargin: 48, netMargin: 6,
    revenueGrowth: 0.15, profitGrowth: 0.08,
    debtRatio: 0.32, cashFlow: "一般",
    replacementUrgency: 2,
    supplyChainPosition: 3,
    earningsQuality: 2,
    valuation: 2,
    fundFlow: 3,
    bottleneck: "",
    catalyst: "星火大模型商业化落地、教育/医疗AI产品放量",
    risk: "商业化进度慢于预期、与百度/阿里竞争、盈利能力偏弱",
    targetPE: 70, targetPrice: 58, upside: -0.06,
    rating: "🟡", ratingText: "观望（AI应用落地仍需验证）"
  },
  "688111.SH": {
    name: "金山办公", layer: 7, layerName: "AI应用",
    biz: "WPS AI，国内办公软件龙头，AI赋能办公场景",
    price: 365, high52w: 420, low52w: 260,
    marketCap: 1680,
    pe: 78, pb: 22.5, roe: 28.5, grossMargin: 88, netMargin: 32,
    revenueGrowth: 0.22, profitGrowth: 0.25,
    debtRatio: 0.08, cashFlow: "优秀",
    replacementUrgency: 2,
    supplyChainPosition: 4,
    earningsQuality: 4,
    valuation: 2,
    fundFlow: 3,
    bottleneck: "",
    catalyst: "WPS AI付费用户增长、国产化（党政/央企）持续推进",
    risk: "估值极高、AI功能货币化进度不确定、竞争（微软Office+Copilot）",
    targetPE: 65, targetPrice: 350, upside: -0.04,
    rating: "🔵", ratingText: "关注（好公司，商业模式优秀，等回调）"
  }
};

// ========== 计算综合评分 ==========
function calcScore(s) {
  const weights = {
    replacementUrgency: 0.20,
    supplyChainPosition: 0.20,
    earningsQuality: 0.25,
    valuation: 0.20,
    fundFlow: 0.15
  };
  // 注意：valuation 分越高越好（1-5，5=很便宜），但我们的数据中valuation是相对评分
  const raw = 
    s.replacementUrgency * weights.replacementUrgency * 20 + // 转成100分制
    s.supplyChainPosition * weights.supplyChainPosition * 20 +
    s.earningsQuality * weights.earningsQuality * 20 +
    s.valuation * weights.valuation * 20 +
    s.fundFlow * weights.fundFlow * 20;
  return Math.round(raw * 10) / 10;
}

// 为所有股票计算评分
Object.keys(stocks).forEach(code => {
  stocks[code].score = calcScore(stocks[code]);
});

// ========== 按层分组输出 ==========
const layers = {};
Object.keys(stocks).forEach(code => {
  const s = stocks[code];
  if (!layers[s.layer]) layers[s.layer] = [];
  layers[s.layer].push({ code, ...s });
});

console.log("=== A股AI产业链选股分析报告 ===\n");

Object.keys(layers).sort().forEach(layerNum => {
  const layerStocks = layers[layerNum];
  const layerName = layerStocks[0].layerName;
  console.log(`\n第${layerNum}层：${layerName}`);
  console.log("─".repeat(60));
  layerStocks.forEach(s => {
    console.log(`\n【${s.code} ${s.name}】${s.rating} ${s.ratingText}`);
    console.log(`  当前价：${s.price}元 | 目标价：${s.targetPrice}元 | 上行空间：${(s.upside * 100).toFixed(1)}%`);
    console.log(`  52周区间：${s.low52w} - ${s.high52w}元 | 距高点：${((s.price/s.high52w - 1) * 100).toFixed(1)}%`);
    console.log(`  市值：${s.marketCap}亿 | P/E：${s.pe}x | P/B：${s.pb}x | ROE：${s.roe}%`);
    console.log(`  营收增速：${(s.revenueGrowth*100).toFixed(0)}% | 净利增速：${(s.profitGrowth*100).toFixed(0)}%`);
    console.log(`  综合评分：${s.score}/100`);
    console.log(`  业务：${s.biz}`);
    if (s.bottleneck) console.log(`  🔥 瓶颈卡位：${s.bottleneck}`);
    console.log(`  催化剂：${s.catalyst}`);
    console.log(`  风险：${s.risk}`);
  });
});

// 强势关注清单
console.log("\n\n=== 🟢 强势关注清单（按综合评分排序）===");
const strongList = Object.keys(stocks)
  .filter(code => stocks[code].rating === "🟢")
  .sort((a, b) => stocks[b].score - stocks[a].score);
strongList.forEach((code, i) => {
  const s = stocks[code];
  console.log(`${i+1}. ${code} ${s.name} | 评分：${s.score} | 目标价：${s.targetPrice}元(+${(s.upside*100).toFixed(1)}%)`);
});

// 关注清单
console.log("\n=== 🔵 关注清单（等回调）===");
const watchList = Object.keys(stocks)
  .filter(code => stocks[code].rating === "🔵")
  .sort((a, b) => stocks[b].score - stocks[a].score);
watchList.forEach((code, i) => {
  const s = stocks[code];
  console.log(`${i+1}. ${code} ${s.name} | 评分：${s.score} | 目标价：${s.targetPrice}元(+${(s.upside*100).toFixed(1)}%)`);
});

// 输出JSON供Word生成使用
fs = require('fs');
const output = { stocks, layers, strongList, watchList, generated: "2026-05-30" };
fs.writeFileSync('ai_stock_analysis.json', JSON.stringify(output, null, 2));
console.log("\n数据已保存到 ai_stock_analysis.json");
