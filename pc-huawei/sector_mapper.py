#!/usr/bin/env python3
"""
板块映射引擎 — Sector Mapping Engine
=====================================
将投资信号映射到 A 股板块，输出利好/利空方向、影响程度、关键词匹配。
与中国投资者习惯一致：红色 = 涨/利好，绿色 = 跌/利空。

用法:
    from sector_mapper import map_to_sectors, generate_investment_interpretation
    sectors = map_to_sectors(signals, text)
    interpretation = generate_investment_interpretation(text, signals, sectors)
"""

import re
from collections import defaultdict
from typing import Optional


# ═════════════════════════════════════════════════════════════
#  板块定义 — 10 个核心 A 股板块
# ═════════════════════════════════════════════════════════════

A_SHARE_SECTORS = {
    "半导体芯片": {
        "emoji": "💻",
        "ref_stocks": ["中芯国际", "北方华创", "中微公司", "韦尔股份", "兆易创新"],
        "signal_links": ["关税贸易", "科技AI", "中国市场"],
        "bullish_keywords": [
            "chip demand", "semiconductor boom", "wafer", "expansion",
            "fab", "subsidy", "investment", "breakthrough", "AI chip",
            "NVIDIA strong", "TSMC growth", "chip shortage ease",
            "self-sufficiency", "国产替代", "突破", "量产", "扩产",
        ],
        "bearish_keywords": [
            "chip ban", "export control", "entity list", "sanction",
            "restrict", "embargo", "decouple", "blacklist",
            "supply chain disruption", "shortage worsening",
            "ASML ban", "chip war", "technology cold war",
        ],
        "impact_desc": "芯片制裁/出口管制直接影响国内半导体设备、代工、EDA产业链",
    },
    "人工智能": {
        "emoji": "🤖",
        "ref_stocks": ["科大讯飞", "海康威视", "商汤", "寒武纪", "浪潮信息"],
        "signal_links": ["科技AI", "监管政策"],
        "bullish_keywords": [
            "AI breakthrough", "AGI", "ChatGPT", "GPT-5", "new model",
            "launch", "AI investment", "data center build",
            "AI adoption", "enterprise AI", "AI agent",
            "training cluster", "scaling law", "transformer",
        ],
        "bearish_keywords": [
            "AI regulation", "ban AI", "restrict AI", "AI safety",
            "pause AI", "moratorium", "AI risk", "AI threat",
            "deepfake", "AI job loss", "AI copyright",
        ],
        "impact_desc": "AI技术突破/监管直接影响算力、大模型、AI应用标的",
    },
    "新能源锂电": {
        "emoji": "🔋",
        "ref_stocks": ["宁德时代", "比亚迪", "隆基绿能", "阳光电源", "赣锋锂业"],
        "signal_links": ["关税贸易", "能源商品", "中国市场", "科技AI"],
        "bullish_keywords": [
            "EV demand", "electric vehicle boom", "battery",
            "solar expansion", "wind power", "renewable growth",
            "lithium price up", "energy storage", "grid upgrade",
            "clean energy", "PV installation", "gigafactory",
            "BYD sales", "Tesla record", "new energy vehicle",
        ],
        "bearish_keywords": [
            "EV tariff", "battery tariff", "solar tariff",
            "anti-subsidy", "dumping", "overcapacity",
            "lithium price drop", "subsidy cut", "EU tariff",
            "trade barrier", "EV slowdown", "inventory glut",
        ],
        "impact_desc": "关税/补贴政策、原材料价格、海外需求直接影响新能源产业链",
    },
    "出口贸易": {
        "emoji": "🚢",
        "ref_stocks": ["海尔智家", "美的集团", "三一重工", "中远海控", "福耀玻璃"],
        "signal_links": ["关税贸易", "地缘政治", "中国市场"],
        "bullish_keywords": [
            "trade deal", "tariff cut", "tariff delay", "export growth",
            "supply chain recover", "de-escalation", "phase one deal",
            "MFN", "WTO ruling favorable", "customs easing",
        ],
        "bearish_keywords": [
            "tariff", "trade war", "sanction", "decouple",
            "export ban", "import ban", "entity list",
            "de-risk", "reshoring", "supply chain shift",
            "section 301", "anti-dumping", "countervailing duty",
        ],
        "impact_desc": "关税/贸易壁垒直接影响出口型企业营收和利润预期",
    },
    "加密货币": {
        "emoji": "₿",
        "ref_stocks": ["嘉楠科技", "比特大陆相关", "火币科技", "欧科云链"],
        "signal_links": ["加密币圈", "监管政策", "货币政策"],
        "bullish_keywords": [
            "bitcoin rally", "BTC ATH", "ETF approved", "institutional",
            "adoption", "halving", "bull run", "crypto boom",
            "stablecoin growth", "DeFi boom", "miner profitable",
            "hash rate up", "crypto friendly", "innovation hub",
        ],
        "bearish_keywords": [
            "crypto crash", "SEC lawsuit", "ban crypto",
            "exchange hack", "stablecoin collapse", "mining ban",
            "crackdown", "regulation tightening", "crypto winter",
            "FTX", "fraud", "rug pull", "delist",
        ],
        "impact_desc": "加密市场波动/监管直接影响矿机股、区块链概念、市场情绪",
    },
    "金融券商": {
        "emoji": "🏦",
        "ref_stocks": ["中信证券", "东方财富", "中国平安", "招商银行", "同花顺"],
        "signal_links": ["货币政策", "监管政策", "中国市场"],
        "bullish_keywords": [
            "rate cut", "dovish", "QE", "liquidity injection",
            "stimulus", "easing", "bull market", "stock rally",
            "bond rally", "yield curve steepen", "credit expansion",
            "China easing", "PBOC cut", "RRR cut",
        ],
        "bearish_keywords": [
            "rate hike", "hawkish", "QT", "tightening",
            "inflation", "inflation high", "bond crash", "yield curve invert",
            "financial crisis", "credit crunch", "deleveraging",
            "capital flight", "contagion", "no rate cut",
            "higher for longer", "maintain rate", "hold rate",
        ],
        "impact_desc": "利率/流动性变化直接影响券商、银行、保险的盈利和估值",
    },
    "军工": {
        "emoji": "🛡️",
        "ref_stocks": ["中航沈飞", "航发动力", "中国船舶", "中兵红箭"],
        "signal_links": ["地缘政治", "关税贸易"],
        "bullish_keywords": [
            "war", "conflict", "military buildup", "defense spending",
            "naval exercise", "missile test", "nuclear threat",
            "territorial dispute", "sovereignty", "sanction military",
            "weapons", "defense cooperation",
        ],
        "bearish_keywords": [
            "ceasefire", "peace deal", "de-escalation",
            "troops withdraw", "defense cut", "disarmament",
            "peace talk", "normalization",
        ],
        "impact_desc": "地缘冲突升级利好军工，缓和则利空军工板块",
    },
    "消费": {
        "emoji": "🛒",
        "ref_stocks": ["贵州茅台", "中国中免", "海天味业", "伊利股份"],
        "signal_links": ["货币政策", "中国市场"],
        "bullish_keywords": [
            "consumer confidence high", "retail sales up",
            "consumption boom", "travel boom", "tourism",
            "stimulus check", "tax cut", "wage growth",
            "China consumption recovery", "reopening",
        ],
        "bearish_keywords": [
            "inflation high", "consumer sentiment low",
            "retail slump", "spending cut", "recession",
            "lockdown", "consumption downgrade", "savings rate up",
        ],
        "impact_desc": "消费信心/通胀数据直接影响大消费板块估值",
    },
    "医药": {
        "emoji": "💊",
        "ref_stocks": ["药明康德", "恒瑞医药", "迈瑞医疗", "百济神州"],
        "signal_links": ["监管政策", "关税贸易"],
        "bullish_keywords": [
            "FDA approval", "breakthrough therapy", "drug approval",
            "clinical success", "biotech funding", "patent granted",
            "new drug", "vaccine success", "pandemic end",
        ],
        "bearish_keywords": [
            "FDA rejection", "drug price control", "patent cliff",
            "clinical trial fail", "biosecure act", "WuXi",
            "pharma sanction", "biotech winter", "pandemic",
        ],
        "impact_desc": "FDA审批/生物安全法案直接影响CXO、创新药企预期",
    },
    "地产基建": {
        "emoji": "🏗️",
        "ref_stocks": ["万科A", "保利发展", "中国建筑", "海螺水泥"],
        "signal_links": ["货币政策", "中国市场", "能源商品"],
        "bullish_keywords": [
            "infrastructure bill", "infrastructure investment",
            "housing market recovery", "property easing",
            "construction boom", "urbanization", "belt road",
            "real estate stimulus", "mortgage rate cut",
        ],
        "bearish_keywords": [
            "housing crash", "property crisis", "Evergrande",
            "real estate downturn", "mortgage stress",
            "construction slowdown", "overbuilding",
            "property tax", "default wave",
        ],
        "impact_desc": "基建投资/房地产政策直接影响建筑建材、开发商预期",
    },
}


def map_to_sectors(signals: list[dict], text: str = "") -> list[dict]:
    """
    将投资信号映射到 A 股板块，并判断利好/利空方向。

    Args:
        signals: extract_signals() 的输出列表
        text: 推文原文（用于关键词方向判断）

    Returns:
        [{"sector": "半导体芯片", "emoji": "💻", "direction": "bearish",
          "confidence": 0.85, "matched": ["chip ban"], "ref_stocks": [...]}, ...]
    """
    text_lower = text.lower()
    sector_scores: dict[str, dict] = {}

    for signal in signals:
        cat = signal["category"]
        # 找所有与此信号关联的板块
        for sector_name, sector_info in A_SHARE_SECTORS.items():
            if cat in sector_info["signal_links"]:
                if sector_name not in sector_scores:
                    sector_scores[sector_name] = {
                        "sector": sector_name,
                        "emoji": sector_info["emoji"],
                        "ref_stocks": sector_info["ref_stocks"],
                        "impact_desc": sector_info["impact_desc"],
                        "bullish_hits": 0,
                        "bearish_hits": 0,
                        "matched_keywords": [],
                        "signal_priority": 0,
                    }

                entry = sector_scores[sector_name]
                entry["signal_priority"] = max(entry["signal_priority"], signal["priority"])

                # 方向判断
                for kw in signal.get("matched_keywords", []):
                    entry["matched_keywords"].append(kw)

                # 检查利好/利空关键词
                for bkw in sector_info["bullish_keywords"]:
                    if bkw.lower() in text_lower:
                        entry["bullish_hits"] += 1
                for bkw in sector_info["bearish_keywords"]:
                    if bkw.lower() in text_lower:
                        entry["bearish_hits"] += 1

    # 确定方向 + 置信度
    result = []
    for entry in sector_scores.values():
        total_hits = entry["bullish_hits"] + entry["bearish_hits"]
        if entry["bullish_hits"] > entry["bearish_hits"]:
            entry["direction"] = "bullish"
        elif entry["bearish_hits"] > entry["bullish_hits"]:
            entry["direction"] = "bearish"
        else:
            entry["direction"] = "neutral"

        # 置信度：基于关键词命中数和信号优先级
        if total_hits > 0:
            entry["confidence"] = min(0.95, 0.4 + total_hits * 0.15 + entry["signal_priority"] * 0.03)
        else:
            # 无关键词命中但有信号关联，降低置信度
            entry["confidence"] = min(0.7, 0.3 + entry["signal_priority"] * 0.04)

        # 去重关键词
        entry["matched_keywords"] = list(set(entry["matched_keywords"]))[:5]

        # 清理内部字段
        for k in ["bullish_hits", "bearish_hits", "signal_priority"]:
            del entry[k]

        result.append(entry)

    # 按信号优先级 × 置信度排序
    result.sort(key=lambda x: -x["confidence"])
    return result[:8]  # 最多 8 个板块


def generate_investment_interpretation(
    text: str,
    signals: list[dict],
    sectors: list[dict],
    username: str = "",
) -> str:
    """
    生成投资解读：基于信号和板块映射，用自然语言描述对 A 股投资者的意义。

    Args:
        text: 推文原文
        signals: extract_signals() 的输出
        sectors: map_to_sectors() 的输出
        username: 发推账号名

    Returns:
        中文投资解读字符串
    """
    if not signals and not sectors:
        return "暂无明显的市场投资信号。"

    lines = []
    account_ref = f"@{username}" if username else "该推文"

    # 1. 信号概览
    if signals:
        top_sig = signals[0]
        top_sig_name = top_sig["category"]
        lines.append(f"{account_ref}涉及「{top_sig_name}」相关信息。")

    # 2. 板块映射
    if sectors:
        high_conf = [s for s in sectors if s["direction"] != "neutral"]
        if high_conf:
            first = high_conf[0]
            dir_label = "利好" if first["direction"] == "bullish" else "利空" if first["direction"] == "bearish" else "中性影响"
            stocks_str = "、".join(first["ref_stocks"][:3])
            lines.append(f"→ 对【{first['sector']}】板块构成{dir_label}，关注 {stocks_str}。")

            # 第二个板块（如果有冲突方向）
            for s in high_conf[1:2]:
                s_dir = "利好" if s["direction"] == "bullish" else "利空"
                if first.get("direction") and first["direction"] not in ("neutral", s["direction"]):
                    lines.append(f"→ 同时可能对【{s['sector']}】板块形成{s_dir}，需综合评估。")
                    break

    # 3. 具体影响
    if sectors:
        first = sectors[0]
        lines.append(f"影响路径：{first.get('impact_desc', '待评估')}。")

    # 4. 风险提示
    risk_terms_in_text = []
    danger_words = ["war", "sanction", "ban", "crash", "crisis", "restrict", "decouple", "threat", "retaliate"]
    for dw in danger_words:
        if dw in text.lower():
            risk_terms_in_text.append(dw)
    if risk_terms_in_text:
        lines.append(f"⚠️ 注意：推文中提及 {', '.join(risk_terms_in_text[:3])}，短期内可能引发市场波动，建议关注后续发展。")

    return "\n".join(lines)


# ═════════════════════════════════════════════════════════════
#  板块热度数据生成
# ═════════════════════════════════════════════════════════════

def build_sector_heatmap(
    tweets: list[dict],
    accounts: list[str],
) -> dict:
    """
    生成板块热度矩阵（用于前端热力图）。
    返回: {sectors: [...], accounts: [...], matrix: [[score, ...], ...]}

    每个 matrix[i][j] 的值 = 该板块在该账号推文中的影响分数
    正值 = 利好，负值 = 利空
    """
    # 初始化
    sector_names = list(A_SHARE_SECTORS.keys())
    matrix = [[0.0 for _ in accounts] for _ in sector_names]

    for tweet in tweets:
        username = tweet.get("username", "")
        if username not in accounts:
            continue
        acc_idx = accounts.index(username)

        text = tweet.get("content", "")
        signals = tweet.get("signals", [])
        sectors = map_to_sectors(signals, text)

        for s in sectors:
            try:
                sec_idx = sector_names.index(s["sector"])
            except ValueError:
                continue

            score = s["confidence"] * 10  # 0-10 区间
            if s["direction"] == "bearish":
                score = -score
            elif s["direction"] == "neutral":
                score *= 0.3

            matrix[sec_idx][acc_idx] += score

    return {
        "sectors": [
            {"name": n, "emoji": A_SHARE_SECTORS[n]["emoji"]}
            for n in sector_names
        ],
        "accounts": accounts,
        "matrix": [[round(v, 2) for v in row] for row in matrix],
    }


# ═════════════════════════════════════════════════════════════
#  CLI 测试
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    # 模拟信号输入
    from web_server import extract_signals

    test_tweets = [
        ("realDonaldTrump", "We will impose 60% tariffs on Chinese goods. The trade deficit is a disaster."),
        ("elonmusk", "Tesla FSD is now approved in China! Huge milestone for autonomous driving."),
        ("federalreserve", "Inflation remains elevated. We may need to maintain higher rates for longer."),
        ("CathieDWood", "Bitcoin ETF inflows hit record. Institutional adoption accelerating."),
    ]

    for username, text in test_tweets:
        print(f"\n{'='*70}")
        print(f"@{username}: {text[:80]}...")
        print(f"{'='*70}")

        sigs = extract_signals(text)
        print(f"信号: {[s['category'] for s in sigs]}")

        sectors = map_to_sectors(sigs, text)
        print(f"板块映射:")
        for s in sectors:
            dir_icon = "📈" if s["direction"] == "bullish" else "📉" if s["direction"] == "bearish" else "➖"
            print(f"  {dir_icon} {s['emoji']} {s['sector']} ({s['direction']}) — 置信度{s['confidence']:.0%}")
            print(f"      关键词: {s['matched_keywords']}")
            print(f"      参考: {', '.join(s['ref_stocks'][:3])}")

        interp = generate_investment_interpretation(text, sigs, sectors, username)
        print(f"\n📝 投资解读: {interp}")
