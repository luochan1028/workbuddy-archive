#!/usr/bin/env python3
"""
全球投资情报看板 — Global Investment Intelligence Dashboard
==========================================================
为中国A股投资者设计的X(Twitter)监控仪表盘。
从推文流中提炼投资信号、格局洞察、跨账号主题聚类。
聚焦两个核心需求：
  1. 财务投资方向 — 关税/利率/币圈/科技/AI/中国市场
  2. 世界格局理解 — 地缘政治/政策博弈/大国关系

启动:
    python web_server.py              # 默认 0.0.0.0:8080
    python web_server.py --port 9090  # 自定义端口
"""

import argparse
import json
import logging
import os
import re
import sqlite3
from collections import Counter, defaultdict
from datetime import datetime, timedelta

from flask import Flask, jsonify, request, render_template_string

# ── 板块映射引擎 ──────────────────────────────────────────
try:
    from sector_mapper import (
        map_to_sectors,
        generate_investment_interpretation,
        build_sector_heatmap,
        A_SHARE_SECTORS,
    )
    SECTOR_MAPPER_AVAILABLE = True
except ImportError:
    SECTOR_MAPPER_AVAILABLE = False

# ── 格局追踪引擎 ──────────────────────────────────────────
try:
    from pattern_tracker import analyze_all as pattern_analyze_all, DIMS as PATTERN_DIMS
    PATTERN_AVAILABLE = True
except ImportError:
    PATTERN_AVAILABLE = False

# ── 账号画像引擎 ──────────────────────────────────────────
try:
    from account_profile import build_all as profile_build_all, build_theme_resonance
    PROFILE_AVAILABLE = True
except ImportError:
    PROFILE_AVAILABLE = False

# ── 变量检查（延迟 logger 初始化之后） ────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "tweets.db")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("intel-web")

app = Flask(__name__, template_folder=SCRIPT_DIR)

# ── 引擎可用性检查 ────────────────────────────────────────
if not SECTOR_MAPPER_AVAILABLE:
    logger.warning("sector_mapper.py 未找到，板块映射功能不可用")
if not PATTERN_AVAILABLE:
    logger.warning("pattern_tracker.py 未找到，格局追踪功能不可用")
if not PROFILE_AVAILABLE:
    logger.warning("account_profile.py 未找到，账号画像功能不可用")

# ═════════════════════════════════════════════════════════════
#  信号提取引擎 — Signal Extraction Engine
# ═════════════════════════════════════════════════════════════

SIGNAL_CATEGORIES = {
    "关税贸易": {
        "emoji": "🏷️", "color": "#e74c3c", "priority": 10,
        "keywords": [
            "tariff", "trade war", "trade deal", "sanction", "export control",
            "decouple", "de-risk", "supply chain", "reshoring", "WTO",
            "MFN", "section 301", "entity list", "import ban", "customs",
            "dumping", "subsidy", "CHIPS act", "chip ban", "半导体",
        ],
        "impact": "直接影响A股出口型企业、人民币汇率、中美关系预期"
    },
    "货币政策": {
        "emoji": "💰", "color": "#3498db", "priority": 9,
        "keywords": [
            "rate cut", "rate hike", "interest rate", "federal reserve",
            "inflation", "CPI", "PPI", "quantitative easing", "QE", "QT",
            "balance sheet", "yield curve", "bond market", "treasury",
            "Jerome Powell", "FOMC", "tightening", "hawkish", "dovish",
            "money supply", "liquidity", "dollar index", "USD", "DXY",
        ],
        "impact": "影响全球流动性、A股资金面、人民币汇率、黄金走势"
    },
    "加密币圈": {
        "emoji": "₿", "color": "#f39c12", "priority": 8,
        "keywords": [
            "bitcoin", "BTC", "ethereum", "ETH", "crypto", "blockchain",
            "DeFi", "NFT", "token", "mining", "stablecoin", "CBDC",
            "SEC crypto", "crypto regulation", "wallet", "exchange",
            "hash rate", "halving", "miner", "memecoin", "solana",
            "web3", "smart contract", "DAO",
        ],
        "impact": "影响币圈情绪、矿机股、区块链概念股、监管预期"
    },
    "科技AI": {
        "emoji": "🤖", "color": "#9b59b6", "priority": 8,
        "keywords": [
            "AI", "artificial intelligence", "machine learning", "deep learning",
            "ChatGPT", "OpenAI", "GPT", "LLM", "AGI", "singularity",
            "NVIDIA", "GPU", "semiconductor", "chip", "foundry",
            "TSMC", "ASML", "data center", "cloud computing",
            "autonomous", "self-driving", "robot", "automation",
            "quantum", "training", "inference", "transformer",
        ],
        "impact": "影响AI产业链（算力/芯片/应用）、科技股估值、中国AI对标概念"
    },
    "中国市场": {
        "emoji": "🇨🇳", "color": "#e74c3c", "priority": 9,
        "keywords": [
            "China", "Chinese", "Beijing", "CCP", "Xi Jinping",
            "A-share", "H-share", "CSI 300", "Shanghai", "Shenzhen",
            "yuan", "RMB", "CNY", "PBOC", "China market",
            "中概股", "Hang Seng", "Hong Kong", "Taiwan strait",
            "South China Sea", "BRI", "belt road", "Made in China 2025",
            "Alibaba", "Tencent", "BYD", "Huawei", "Xiaomi",
        ],
        "impact": "直接影响A股/港股/中概股、中资企业海外业务、地缘风险溢价"
    },
    "地缘政治": {
        "emoji": "🌍", "color": "#e67e22", "priority": 9,
        "keywords": [
            "war", "conflict", "NATO", "Russia", "Ukraine", "Putin",
            "Taiwan", "South China Sea", "Middle East", "Iran", "Israel",
            "North Korea", "missile", "nuclear", "military", "troops",
            "sanction", "embargo", "sovereignty", "territory",
            "geopolitic", "alliance", "security council", "UN",
        ],
        "impact": "影响全球风险偏好、军工股、能源/黄金避险、供应链安全"
    },
    "能源商品": {
        "emoji": "⛽", "color": "#27ae60", "priority": 7,
        "keywords": [
            "oil", "crude", "gas", "OPEC", "energy", "shale",
            "gold", "gold price", "commodity", "copper", "lithium",
            "rare earth", "uranium", "silver", "platinum",
            "pipeline", "refinery", "drilling", "offshore",
            "renewable", "solar", "wind", "nuclear",
        ],
        "impact": "影响大宗商品价格、资源股、新能源产业链"
    },
    "监管政策": {
        "emoji": "⚖️", "color": "#1abc9c", "priority": 7,
        "keywords": [
            "SEC", "CFTC", "regulation", "executive order",
            "antitrust", "monopoly", "break up", "DOJ",
            "lawsuit", "sue", "court ruling", "appeal",
            "ban", "restrict", "compliance", "FCC",
            "FDA", "EPA", "FTC", "whistleblower",
        ],
        "impact": "影响特定行业/公司的监管风险、合规成本、商业模式"
    },
}


def extract_signals(text: str) -> list[dict]:
    """从推文中提取投资信号"""
    text_lower = text.lower()
    signals = []
    for cat_name, cat_info in SIGNAL_CATEGORIES.items():
        matched = []
        for kw in cat_info["keywords"]:
            if kw.lower() in text_lower:
                matched.append(kw)
        if matched:
            signals.append({
                "category": cat_name,
                "emoji": cat_info["emoji"],
                "color": cat_info["color"],
                "priority": cat_info["priority"],
                "matched_keywords": matched[:5],
                "impact": cat_info["impact"],
            })
    # 按优先级排序
    signals.sort(key=lambda x: -x["priority"])
    return signals


def analyze_sentiment(text: str) -> str:
    text_lower = text.lower()
    positive = ["great", "best", "love", "win", "beautiful", "incredible",
                "fantastic", "amazing", "wonderful", "proud", "honor", "big",
                "good", "excellent", "success", "strong", "boom", "rally"]
    negative = ["terrible", "horrible", "disaster", "failed", "loser",
                "fake", "worst", "sad", "never", "bad", "radical", "witch",
                "crash", "collapse", "crisis", "danger", "threat", "fear"]
    pos = sum(text_lower.count(w) for w in positive)
    neg = sum(text_lower.count(w) for w in negative)
    if pos > neg + 1:
        return "positive"
    if neg > pos + 1:
        return "negative"
    return "neutral"


def extract_topics(text: str) -> list[str]:
    topics = re.findall(r'#(\w+)', text)
    tickers = re.findall(r'\$([A-Z]{1,5})', text)
    return topics + [f"${t}" for t in tickers]


# ═════════════════════════════════════════════════════════════
#  跨账号主题聚类 — Cross-Account Theme Clustering
# ═════════════════════════════════════════════════════════════

def detect_cross_account_themes(grouped: dict) -> list[dict]:
    """检测多个账号共同讨论的主题"""
    if len(grouped) < 2:
        return []

    # 收集所有账号的 hashtag + ticker
    account_topics = {}
    for username, tweets in grouped.items():
        topics_set = set()
        for t in tweets:
            for tp in t.get("topics", []):
                topics_set.add(tp.lower())
        account_topics[username] = topics_set

    # 找共同话题（>=2 个账号提到）
    usernames = list(account_topics.keys())
    common_topics = []
    for i in range(len(usernames)):
        for j in range(i + 1, len(usernames)):
            shared = account_topics[usernames[i]] & account_topics[usernames[j]]
            for topic in shared:
                common_topics.append({
                    "topic": topic,
                    "accounts": [usernames[i], usernames[j]],
                    "count": 2,
                })

    # 去重合并
    merged = {}
    for ct in common_topics:
        key = ct["topic"]
        if key in merged:
            merged[key]["accounts"] = list(set(merged[key]["accounts"] + ct["accounts"]))
            merged[key]["count"] = len(merged[key]["accounts"])
        else:
            merged[key] = ct

    themes = sorted(merged.values(), key=lambda x: -x["count"])
    return themes[:8]


# ═════════════════════════════════════════════════════════════
#  每日简报生成 — Daily Intelligence Briefing
# ═════════════════════════════════════════════════════════════

def generate_daily_briefing(grouped: dict, all_signals: list, themes: list, date_str: str) -> dict:
    """生成面向中国投资者的每日情报简报"""
    total = sum(len(v) for v in grouped.values())
    if total == 0:
        return {
            "headline": "今日暂无推文数据",
            "summary": f"{date_str} 尚未捕获到推文，可能是监控服务正在初始化或各账号今日无新发布。",
            "market_signals": [],
            "risk_alerts": [],
            "hot_themes": [],
            "account_summary": [],
        }

    n_accounts = len(grouped)

    # ── 市场信号汇总 ──
    signal_stats = Counter()
    signal_tweets = defaultdict(list)
    for s in all_signals:
        signal_stats[s["category"]] += 1
        signal_tweets[s["category"]].append(s)

    top_signals = signal_stats.most_common(5)

    # ── 风险预警 ──
    risk_keywords = ["tariff", "sanction", "war", "ban", "crash", "crisis", "restrict", "decouple"]
    risk_alerts = []
    for username, tweets in grouped.items():
        for t in tweets:
            content = t["content"].lower()
            for rk in risk_keywords:
                if rk in content:
                    risk_alerts.append({
                        "source": f"@{username}",
                        "keyword": rk,
                        "tweet_id": t["tweet_id"],
                        "excerpt": t["content"][:120],
                        "time": t.get("pub_date", t.get("first_seen", "")),
                    })
                    break
    # 去重（同一关键字只保留一条）
    seen_risk = set()
    unique_risks = []
    for ra in risk_alerts:
        key = ra["keyword"] + ra["source"]
        if key not in seen_risk:
            seen_risk.add(key)
            unique_risks.append(ra)
    risk_alerts = unique_risks[:5]

    # ── 头条生成 ──
    if top_signals:
        top_cat = top_signals[0][0]
        headline = f"今日关注：{top_cat}信号突出，{n_accounts}个监控源共捕获{total}条推文"
    else:
        headline = f"今日监控日报 — {date_str}"

    # ── 摘要生成 ──
    parts = []
    parts.append(f"📅 {date_str}，监控 {n_accounts} 个关键X账号，共捕获 {total} 条推文。")

    if top_signals:
        parts.append("")
        parts.append("**投资信号聚焦：**")
        for cat, count in top_signals[:3]:
            percent = round(count / total * 100)
            cat_info = SIGNAL_CATEGORIES.get(cat, {})
            parts.append(f"  • {cat_info.get('emoji', '')} {cat}：{count}条推文涉及（占比{percent}%）")
            parts.append(f"    {cat_info.get('impact', '')}")

    if risk_alerts:
        parts.append("")
        parts.append("**⚠️ 风险提示：**")
        for ra in risk_alerts[:3]:
            parts.append(f"  • {ra['source']} 提及「{ra['keyword']}」：{ra['excerpt'][:80]}...")

    if themes:
        parts.append("")
        parts.append(f"**跨账号共识：** {len(themes)} 个话题被多个账号同时关注")
        for th in themes[:3]:
            parts.append(f"  • #{th['topic']} — 被 {', '.join(th['accounts'])} 同时提及")

    # ── 账号摘要 ──
    account_summary = []
    for username, tweets in sorted(grouped.items(), key=lambda x: -len(x[1])):
        acc_signals = Counter(s["category"] for s in all_signals if s.get("_username") == username)
        account_summary.append({
            "username": username,
            "count": len(tweets),
            "top_signals": [{"cat": c, "count": n} for c, n in acc_signals.most_common(3)],
        })

    return {
        "headline": headline,
        "summary": "\n".join(parts),
        "top_signals": [{"category": c, "count": n, "emoji": SIGNAL_CATEGORIES.get(c, {}).get("emoji", ""), "color": SIGNAL_CATEGORIES.get(c, {}).get("color", "#888")} for c, n in top_signals],
        "risk_alerts": risk_alerts,
        "hot_themes": themes,
        "account_summary": account_summary,
    }


# ═════════════════════════════════════════════════════════════
#  配置 & 数据库
# ═════════════════════════════════════════════════════════════

DEFAULT_CONFIG = {"accounts": ["realDonaldTrump"], "fetch_method": "html", "web_port": 8080}


def load_config() -> dict:
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)
            if "accounts" not in cfg:
                cfg["accounts"] = ["realDonaldTrump"]
            return cfg
    return dict(DEFAULT_CONFIG)


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


# ═════════════════════════════════════════════════════════════
#  API 路由
# ═════════════════════════════════════════════════════════════

@app.route("/api/intel")
def api_intel():
    """【核心API】返回完整情报数据：信号、板块映射、投资解读、简报、推文"""
    account = request.args.get("account", "")
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))

    conn = get_db()
    try:
        query = """
            SELECT username, tweet_id, content, pub_date, link, first_seen
            FROM tweets WHERE date(first_seen) = ?
        """
        params = [date_str]
        if account:
            query += " AND username = ?"
            params.append(account)
        query += " ORDER BY username, first_seen ASC"
        rows = conn.execute(query, params).fetchall()

        grouped = defaultdict(list)
        all_signals = []
        all_sentiments = Counter()

        for r in rows:
            d = dict(r)
            d["sentiment"] = analyze_sentiment(d["content"])
            d["topics"] = extract_topics(d["content"])
            d["signals"] = extract_signals(d["content"])
            all_sentiments[d["sentiment"]] += 1

            # 板块映射 + 投资解读
            if SECTOR_MAPPER_AVAILABLE:
                d["sectors"] = map_to_sectors(d["signals"], d["content"])
                d["interpretation"] = generate_investment_interpretation(
                    d["content"], d["signals"], d["sectors"], d["username"]
                )
            else:
                d["sectors"] = []
                d["interpretation"] = ""

            # 将账号名注入 signal 以便后续分组
            for s in d["signals"]:
                s["_username"] = d["username"]
            all_signals.extend(d["signals"])

            grouped[d["username"]].append(d)

        themes = detect_cross_account_themes(grouped)
        briefing = generate_daily_briefing(grouped, all_signals, themes, date_str)

        # 推文列表（flatten，带信号 + 板块 + 解读）
        all_tweets = []
        for username, tweets in grouped.items():
            for t in tweets:
                all_tweets.append({
                    "username": t["username"],
                    "tweet_id": t["tweet_id"],
                    "content": t["content"],
                    "pub_date": t.get("pub_date", ""),
                    "link": t.get("link", ""),
                    "first_seen": t.get("first_seen", ""),
                    "sentiment": t["sentiment"],
                    "topics": t["topics"],
                    "signals": t["signals"],
                    "sectors": t.get("sectors", []),
                    "interpretation": t.get("interpretation", ""),
                })

        # 按信号优先级排序
        def signal_sort_key(tweet):
            max_pri = max((s["priority"] for s in tweet["signals"]), default=0)
            return -max_pri

        all_tweets.sort(key=signal_sort_key)

        # 板块热度矩阵
        sector_heatmap = None
        if SECTOR_MAPPER_AVAILABLE:
            cfg = load_config()
            sector_heatmap = build_sector_heatmap(all_tweets, cfg.get("accounts", []))

        return jsonify({
            "date": date_str,
            "total": len(rows),
            "accounts_monitored": len(grouped),
            "sentiments": dict(all_sentiments),
            "briefing": briefing,
            "cross_themes": themes,
            "tweets": all_tweets,
            "sector_heatmap": sector_heatmap,
        })
    finally:
        conn.close()


@app.route("/api/signals")
def api_signals():
    """单独获取信号分布"""
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT username, content FROM tweets WHERE date(first_seen) = ?",
            (date_str,)
        ).fetchall()

        signal_counter = Counter()
        signal_by_account = defaultdict(Counter)
        for r in rows:
            sigs = extract_signals(r["content"])
            for s in sigs:
                signal_counter[s["category"]] += 1
                signal_by_account[r["username"]][s["category"]] += 1

        return jsonify({
            "date": date_str,
            "signals": [{"category": c, "count": n, "emoji": SIGNAL_CATEGORIES.get(c, {}).get("emoji", ""), "color": SIGNAL_CATEGORIES.get(c, {}).get("color", "#888")} for c, n in signal_counter.most_common()],
            "by_account": {u: dict(c) for u, c in signal_by_account.items()},
        })
    finally:
        conn.close()


@app.route("/api/briefing")
def api_briefing():
    """每日简报（单独）"""
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT username, tweet_id, content, pub_date, link, first_seen FROM tweets WHERE date(first_seen) = ? ORDER BY username, first_seen ASC",
            (date_str,)
        ).fetchall()

        grouped = defaultdict(list)
        all_signals = []
        for r in rows:
            d = dict(r)
            d["topics"] = extract_topics(d["content"])
            sigs = extract_signals(d["content"])
            for s in sigs:
                s["_username"] = d["username"]
            all_signals.extend(sigs)
            d["signals"] = sigs
            grouped[d["username"]].append(d)

        themes = detect_cross_account_themes(grouped)
        briefing = generate_daily_briefing(grouped, all_signals, themes, date_str)
        return jsonify(briefing)
    finally:
        conn.close()


@app.route("/api/tweets")
def api_tweets():
    """推文列表（兼容旧API）"""
    account = request.args.get("account", "")
    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    limit = int(request.args.get("limit", 50))

    conn = get_db()
    try:
        query = """SELECT username, tweet_id, content, pub_date, link, source_instance, first_seen
                   FROM tweets WHERE date(first_seen) = ?"""
        params = [date_str]
        if account:
            query += " AND username = ?"
            params.append(account)
        query += " ORDER BY first_seen ASC LIMIT ?"
        params.append(limit)

        rows = conn.execute(query, params).fetchall()
        tweets = []
        for r in rows:
            d = dict(r)
            d["signals"] = extract_signals(d["content"])
            d["sentiment"] = analyze_sentiment(d["content"])
            d["topics"] = extract_topics(d["content"])
            tweets.append(d)

        return jsonify({
            "account": account or "all",
            "date": date_str,
            "count": len(rows),
            "tweets": tweets,
        })
    finally:
        conn.close()


@app.route("/api/accounts", methods=["GET", "POST", "DELETE"])
def api_accounts():
    """账号管理"""
    cfg = load_config()

    if request.method == "GET":
        stats = {}
        conn = get_db()
        try:
            for acc in cfg.get("accounts", []):
                count = conn.execute("SELECT COUNT(*) FROM tweets WHERE username = ?", (acc,)).fetchone()[0]
                today_count = conn.execute(
                    "SELECT COUNT(*) FROM tweets WHERE username = ? AND date(first_seen) = ?",
                    (acc, datetime.now().strftime("%Y-%m-%d"))
                ).fetchone()[0]
                stats[acc] = {"total_tweets": count, "today": today_count}
        finally:
            conn.close()
        return jsonify({"accounts": cfg.get("accounts", []), "stats": stats})

    if request.method == "POST":
        data = request.get_json()
        username = data.get("username", "").strip().lstrip("@")
        if not username:
            return jsonify({"error": "用户名不能为空"}), 400
        if username in cfg.get("accounts", []):
            return jsonify({"error": f"@{username} 已存在"}), 409
        cfg.setdefault("accounts", []).append(username)
        save_config(cfg)
        return jsonify({"success": True, "accounts": cfg["accounts"]})

    if request.method == "DELETE":
        data = request.get_json()
        username = data.get("username", "").strip().lstrip("@")
        if username not in cfg.get("accounts", []):
            return jsonify({"error": f"@{username} 不存在"}), 404
        cfg["accounts"].remove(username)
        if not cfg["accounts"]:
            cfg["accounts"] = ["realDonaldTrump"]
        save_config(cfg)
        return jsonify({"success": True, "accounts": cfg["accounts"]})

    return jsonify({"error": "method not allowed"}), 405


@app.route("/api/stats")
def api_stats():
    """整体统计"""
    conn = get_db()
    try:
        total = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
        today = datetime.now().strftime("%Y-%m-%d")
        today_count = conn.execute("SELECT COUNT(*) FROM tweets WHERE date(first_seen) = ?", (today,)).fetchone()[0]
        trend = []
        for i in range(6, -1, -1):
            d = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
            c = conn.execute("SELECT COUNT(*) FROM tweets WHERE date(first_seen) = ?", (d,)).fetchone()[0]
            trend.append({"date": d, "count": c})
        return jsonify({"total_tweets": total, "today_count": today_count, "trend_7d": trend})
    finally:
        conn.close()


@app.route("/api/categories")
def api_categories():
    """返回信号分类定义"""
    cats = {}
    for name, info in SIGNAL_CATEGORIES.items():
        cats[name] = {"emoji": info["emoji"], "color": info["color"], "priority": info["priority"], "impact": info["impact"]}
    return jsonify(cats)


@app.route("/api/sectors")
def api_sectors():
    """板块热度矩阵 API"""
    if not SECTOR_MAPPER_AVAILABLE:
        return jsonify({"error": "板块映射引擎未安装"}), 503

    date_str = request.args.get("date", datetime.now().strftime("%Y-%m-%d"))
    conn = get_db()
    try:
        rows = conn.execute(
            "SELECT username, tweet_id, content FROM tweets WHERE date(first_seen) = ?",
            (date_str,)
        ).fetchall()

        cfg = load_config()
        accounts = cfg.get("accounts", [])
        tweets = []
        for r in rows:
            d = dict(r)
            d["signals"] = extract_signals(d["content"])
            d["sectors"] = map_to_sectors(d["signals"], d["content"])
            tweets.append(d)

        heatmap = build_sector_heatmap(tweets, accounts)

        # 附加板块列表定义
        sector_defs = {}
        for name, info in A_SHARE_SECTORS.items():
            sector_defs[name] = {
                "emoji": info["emoji"],
                "ref_stocks": info["ref_stocks"][:3],
                "impact_desc": info["impact_desc"],
            }

        return jsonify({
            "date": date_str,
            "heatmap": heatmap,
            "sector_defs": sector_defs,
        })
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════
#  格局追踪 API / 账号画像 API / 主题共振 API / 健康检查 API
# ═════════════════════════════════════════════════════════════

@app.route("/api/patterns")
def api_patterns():
    """格局追踪：四大维度趋势分析"""
    if not PATTERN_AVAILABLE:
        return jsonify({"error": "格局追踪引擎未安装"}), 503
    days = request.args.get("days", 14, type=int)
    results = pattern_analyze_all(days=days)
    return jsonify(results)


@app.route("/api/profiles")
def api_profiles():
    """账号画像：所有账号的领域分布+对华态度+活跃度"""
    if not PROFILE_AVAILABLE:
        return jsonify({"error": "账号画像引擎未安装"}), 503
    cfg = load_config()
    accounts = cfg.get("accounts", [])
    days = request.args.get("days", 30, type=int)
    profiles = profile_build_all(accounts, days=days)
    return jsonify(profiles)


@app.route("/api/resonance")
def api_resonance():
    """主题共振：跨账号共同讨论的话题"""
    if not PROFILE_AVAILABLE:
        return jsonify({"error": "账号画像引擎未安装"}), 503
    cfg = load_config()
    accounts = cfg.get("accounts", [])
    days = request.args.get("days", 7, type=int)
    results = build_theme_resonance(accounts, days=days)
    return jsonify(results)


@app.route("/api/health")
def api_health():
    """健康检查端点（供 watchdog.py 使用）"""
    conn = get_db()
    try:
        tweet_count = conn.execute("SELECT count(*) FROM tweets").fetchone()[0]
        last_tweet = conn.execute("SELECT max(first_seen) FROM tweets").fetchone()[0]
        cfg = load_config()
        return jsonify({
            "status": "ok",
            "timestamp": datetime.now().isoformat(),
            "tweet_count": tweet_count,
            "last_tweet": last_tweet,
            "accounts_monitored": len(cfg.get("accounts", [])),
            "engines": {
                "sector_mapper": SECTOR_MAPPER_AVAILABLE,
                "pattern_tracker": PATTERN_AVAILABLE,
                "account_profile": PROFILE_AVAILABLE,
            },
        })
    finally:
        conn.close()


# ═════════════════════════════════════════════════════════════
#  微信推送配置与测试 API (v2.0 — 匹配原型设计)
# ═════════════════════════════════════════════════════════════

@app.route("/api/push/config", methods=["GET", "POST"])
def api_push_config():
    """推送配置读写"""
    cfg = load_config()
    push_cfg = cfg.get("wechat_push", {})

    if request.method == "GET":
        # 返回配置（隐藏敏感 token）
        return jsonify({
            "enabled": push_cfg.get("enabled", False),
            "channel": push_cfg.get("channel", "pushplus"),
            "has_serverchan_key": bool(push_cfg.get("serverchan_sendkey", "")),
            "has_pushplus_token": bool(push_cfg.get("pushplus_token", "")),
            "has_wecom_webhook": bool(push_cfg.get("wecom_webhook", "")),
            "enable_new_tweet": push_cfg.get("enable_new_tweet", True),
            "enable_error_alert": push_cfg.get("enable_error_alert", True),
            "enable_daily_summary": push_cfg.get("enable_daily_summary", True),
            "new_tweet_limit": push_cfg.get("new_tweet_limit", 3),
            "daily_push_hour": push_cfg.get("daily_push_hour", 21),
            "web_dashboard_url": push_cfg.get("web_dashboard_url", ""),
        })

    # POST: 更新配置
    data = request.get_json(force=True, silent=True) or {}
    if "enabled" in data:
        push_cfg["enabled"] = data["enabled"]
    if "channel" in data:
        push_cfg["channel"] = data["channel"]
    if "enable_new_tweet" in data:
        push_cfg["enable_new_tweet"] = data["enable_new_tweet"]
    if "enable_error_alert" in data:
        push_cfg["enable_error_alert"] = data["enable_error_alert"]
    if "enable_daily_summary" in data:
        push_cfg["enable_daily_summary"] = data["enable_daily_summary"]
    if "new_tweet_limit" in data:
        push_cfg["new_tweet_limit"] = int(data["new_tweet_limit"])
    if "daily_push_hour" in data:
        push_cfg["daily_push_hour"] = int(data["daily_push_hour"])
    if "web_dashboard_url" in data:
        push_cfg["web_dashboard_url"] = data["web_dashboard_url"]
    # Token 更新（仅在传入非空值时）
    if data.get("serverchan_sendkey"):
        push_cfg["serverchan_sendkey"] = data["serverchan_sendkey"]
    if data.get("pushplus_token"):
        push_cfg["pushplus_token"] = data["pushplus_token"]
    if data.get("wecom_webhook"):
        push_cfg["wecom_webhook"] = data["wecom_webhook"]

    cfg["wechat_push"] = push_cfg
    try:
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2, ensure_ascii=False)
        return jsonify({"ok": True, "message": "配置已保存"})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/push/test", methods=["POST"])
def api_push_test():
    """发送测试推送"""
    cfg = load_config()
    try:
        from wechat_notify import WeChatNotifier
        notifier = WeChatNotifier(cfg)
        if not notifier.enabled:
            return jsonify({"ok": False, "error": "微信推送未启用或无有效渠道"}), 400

        data = request.get_json(force=True, silent=True) or {}
        push_type = data.get("type", "tweet")

        if push_type == "tweet":
            notifier.new_tweets_alert("test_account", [{
                "content": "This is a test tweet from x-monitor. Markets are looking strong today!",
                "translated": "这是来自x-monitor的测试推文。今日市场表现强劲！",
                "sentiment": "👍 正面",
                "priority": "high",
                "interpretation": "测试推送：模拟高优先级信号的完整推送格式，包含投资解读、信号标签和板块标注。",
                "signal_tags": ["关税/贸易", "科技AI"],
                "sector_tags": ["出口贸易", "人工智能"],
                "direction": "bullish",
            }])
        elif push_type == "alert":
            notifier.error_alert("test_account", "测试异常告警消息", consecutive=2,
                               instance_info={
                                   "failed": "xcancel.com",
                                   "switched_to": "nitter.net",
                                   "failover_count_hour": 2,
                                   "monitoring_ok": True,
                               })
        elif push_type == "daily":
            notifier.daily_summary_push("测试推送", {
                "one_line_summary": "这是一条测试推送：特朗普对华关税软化+马斯克FSD入华+AI开源，整体对A股偏暖。",
                "top_signals": [
                    {"signal": "特朗普释放贸易谈判积极信号", "sectors": ["出口贸易"], "direction": "bullish"},
                    {"signal": "马斯克FSD 13.0下周入华", "sectors": ["新能源/电动车"], "direction": "bullish"},
                    {"signal": "Grok-4开源", "sectors": ["AI/大模型"], "direction": "bullish"},
                ],
                "risk_warnings": ["AI竞争格局不确定性", "通胀数据反复风险"],
                "total_tweets": 28,
                "active_accounts": 5,
                "sector_overview": [
                    {"name": "新能源/电动车", "direction": "bullish", "summary": "利好(2次)"},
                    {"name": "AI/大模型", "direction": "bullish", "summary": "利好(2次)"},
                ],
            })
        elif push_type == "heartbeat":
            notifier.heartbeat({
                "total_tweets": 1234,
                "active_accounts": 5,
                "disk_free": "15.2GB",
                "db_healthy": True,
            })
        else:
            return jsonify({"ok": False, "error": f"未知推送类型: {push_type}"}), 400

        return jsonify({"ok": True, "message": f"测试推送({push_type})已发送"})

    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/push/preview")
def api_push_preview():
    """获取推送预览数据（用于前端微信预览界面）"""
    return jsonify({
        "tweet_push": {
            "title": "🔴 高优先级信号",
            "subtitle": "@realDonaldTrump · 刚刚",
            "en_text": '"Just had a great call with China\'s leadership. Making real progress on trade."',
            "cn_highlight": "特朗普释放关税软化信号，中美贸易谈判窗口或重启。对A股出口贸易板块利好。",
            "tags": [
                {"text": "关税/贸易", "type": "signal"},
                {"text": "出口贸易", "type": "sector"},
                {"text": "利好", "type": "direction", "dir": "up"},
            ],
        },
        "alert_push": {
            "title": "⚠️ 监控异常告警",
            "content": "Nitter实例 xcancel.com 返回异常，已自动切换至 nitter.net",
            "detail": "最近1小时内发生 2次 故障转移。当前监控仍正常运行。",
        },
        "daily_push": {
            "title": "📚 每日情报简报",
            "date": datetime.now().strftime("%Y年%-m月%-d日"),
            "one_line": "特朗普对华关税软化+马斯克FSD入华+AI开源，整体对A股偏暖。",
            "top_signals": [
                {"signal": "特朗普释放贸易谈判积极信号", "sector": "出口贸易", "dir": "up"},
                {"signal": "马斯克FSD 13.0下周入华", "sector": "新能源/电动车", "dir": "up"},
                {"signal": "Grok-4开源", "sector": "AI/大模型", "dir": "up"},
            ],
            "risks": ["AI竞争格局不确定性", "通胀数据反复风险", "中美谈判不确定性"],
        },
        "config": {
            "channel": "pushplus",
            "enable_new_tweet": True,
            "enable_error_alert": True,
            "enable_daily_summary": True,
            "daily_push_hour": 21,
        },
    })


# ═════════════════════════════════════════════════════════════
#  翻译 API
# ═════════════════════════════════════════════════════════════

_translator = None


def _get_translator():
    global _translator
    if _translator is None:
        try:
            from deep_translator import GoogleTranslator
            _translator = GoogleTranslator(source="en", target="zh-CN")
        except ImportError:
            return None
    return _translator


@app.route("/api/translate", methods=["POST"])
def api_translate():
    data = request.get_json()
    text = data.get("text", "")
    if not text:
        return jsonify({"translated": ""})
    translator = _get_translator()
    if not translator:
        return jsonify({"translated": "[翻译服务未安装]"})
    try:
        result = translator.translate(text[:4000])
        return jsonify({"translated": result})
    except Exception as e:
        return jsonify({"translated": f"[翻译失败: {e}]"})


# ═════════════════════════════════════════════════════════════
#  仪表盘页面
# ═════════════════════════════════════════════════════════════

@app.route("/")
def dashboard():
    html_path = os.path.join(SCRIPT_DIR, "templates", "index.html")
    if os.path.exists(html_path):
        with open(html_path, "r", encoding="utf-8") as f:
            return f.read()
    return render_template_string(DASHBOARD_HTML)


# ═════════════════════════════════════════════════════════════
#  仪表盘 HTML — 全球投资情报看板
# ═════════════════════════════════════════════════════════════

DASHBOARD_HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>全球投资情报看板</title>
<style>
:root {
  --bg: #0a0c14;
  --card-bg: #13161f;
  --card-border: #1e2233;
  --text: #dce0ea;
  --text-dim: #6b7084;
  --text-bright: #f0f2f8;
  --accent: #3b82f6;
  --accent-glow: rgba(59,130,246,0.15);
  /* 中国股市配色：红涨 */
  --red: #ef4444;
  --red-bg: rgba(239,68,68,0.12);
  --green: #22c55e;
  --green-bg: rgba(34,197,94,0.12);
  --orange: #f59e0b;
  --purple: #a855f7;
  --cyan: #06b6d4;
  --radius: 10px;
  --font: -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: var(--font);
  background: var(--bg);
  color: var(--text);
  line-height: 1.65;
  min-height: 100vh;
  -webkit-font-smoothing: antialiased;
}

/* Scrollbar */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: var(--bg); }
::-webkit-scrollbar-thumb { background: var(--card-border); border-radius: 3px; }

.app { max-width: 1200px; margin: 0 auto; padding: 16px 20px; }

/* ── Top Bar ── */
.topbar {
  display: flex; justify-content: space-between; align-items: center;
  padding: 12px 0; border-bottom: 1px solid var(--card-border); margin-bottom: 20px;
  flex-wrap: wrap; gap: 12px;
}
.topbar-brand { display: flex; align-items: center; gap: 10px; }
.topbar-logo {
  width: 32px; height: 32px; background: linear-gradient(135deg, var(--accent), var(--purple));
  border-radius: 8px; display: flex; align-items: center; justify-content: center;
  font-size: 16px; font-weight: 700; color: #fff;
}
.topbar h1 { font-size: 18px; font-weight: 700; color: var(--text-bright); }
.topbar-sub { font-size: 12px; color: var(--text-dim); font-weight: 400; margin-left: 4px; }
.topbar-controls { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
.topbar-controls input[type="date"] {
  padding: 7px 12px; border: 1px solid var(--card-border); border-radius: var(--radius);
  background: var(--card-bg); color: var(--text); font-size: 13px; font-family: var(--font);
  outline: none;
}
.topbar-controls input[type="date"]:focus { border-color: var(--accent); }
.btn {
  padding: 7px 16px; border: 1px solid var(--card-border); border-radius: var(--radius);
  background: var(--card-bg); color: var(--text); font-size: 13px; cursor: pointer;
  font-family: var(--font); transition: all 0.15s; white-space: nowrap;
  display: inline-flex; align-items: center; gap: 5px;
}
.btn:hover { border-color: var(--accent); background: var(--accent-glow); }
.btn-primary { background: var(--accent); border-color: var(--accent); color: #fff; font-weight: 600; }
.btn-primary:hover { opacity: 0.9; }
.btn-sm { padding: 4px 10px; font-size: 12px; }

/* ── Grid ── */
.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 340px;
  gap: 16px;
  align-items: start;
}
@media (max-width: 900px) {
  .dashboard-grid { grid-template-columns: 1fr; }
}

/* ── Cards ── */
.card {
  background: var(--card-bg); border: 1px solid var(--card-border);
  border-radius: var(--radius); overflow: hidden;
}
.card-header {
  padding: 14px 18px; border-bottom: 1px solid var(--card-border);
  display: flex; justify-content: space-between; align-items: center;
}
.card-header h2 { font-size: 14px; font-weight: 600; color: var(--text-bright); display: flex; align-items: center; gap: 6px; }
.card-body { padding: 16px 18px; }

/* ── Briefing (Hero) ── */
.briefing { border-left: 3px solid var(--accent); }
.briefing-headline { font-size: 20px; font-weight: 700; color: var(--text-bright); margin-bottom: 12px; line-height: 1.4; }
.briefing-summary { font-size: 14px; color: var(--text-dim); line-height: 1.9; white-space: pre-line; }

/* ── Signal Heat ── */
.signal-grid { display: flex; gap: 8px; flex-wrap: wrap; }
.signal-chip {
  padding: 6px 12px; border-radius: 6px; font-size: 12px; font-weight: 600;
  display: flex; align-items: center; gap: 5px;
}
.signal-chip .count { opacity: 0.7; font-weight: 400; }

/* ── Risk Alerts ── */
.risk-item {
  padding: 10px; border-left: 3px solid var(--red); margin-bottom: 8px;
  background: var(--red-bg); border-radius: 0 6px 6px 0; font-size: 13px;
}
.risk-source { font-weight: 600; color: var(--red); font-size: 12px; margin-bottom: 3px; }
.risk-excerpt { color: var(--text-dim); font-size: 12px; line-height: 1.5; }

/* ── Theme Chips ── */
.theme-item {
  display: flex; align-items: center; gap: 8px; padding: 8px 0;
  border-bottom: 1px solid rgba(255,255,255,0.04); font-size: 13px;
}
.theme-item:last-child { border-bottom: none; }
.theme-topic { font-weight: 600; color: var(--accent); }
.theme-accounts { font-size: 11px; color: var(--text-dim); }

/* ── Tweet List ── */
.tweet-card {
  padding: 16px; border-bottom: 1px solid var(--card-border);
  transition: background 0.15s;
}
.tweet-card:last-child { border-bottom: none; }
.tweet-card:hover { background: rgba(255,255,255,0.02); }
.tweet-card.high-signal { border-left: 3px solid var(--red); padding-left: 13px; }
.tweet-meta {
  display: flex; justify-content: space-between; align-items: center;
  margin-bottom: 8px; flex-wrap: wrap; gap: 4px;
}
.tweet-account { font-weight: 700; font-size: 13px; color: var(--accent); }
.tweet-time { font-size: 11px; color: var(--text-dim); }
.tweet-content-en { font-size: 14px; line-height: 1.7; margin-bottom: 6px; color: var(--text-bright); }
.tweet-content-zh { font-size: 13px; line-height: 1.7; color: var(--text-dim); border-left: 2px solid var(--accent); padding-left: 10px; margin-top: 8px; margin-bottom: 8px; }
.tweet-signal-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 6px; }
.signal-tag {
  padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
  display: flex; align-items: center; gap: 3px;
}
.tweet-link { font-size: 11px; margin-top: 6px; }
.tweet-link a { color: var(--text-dim); text-decoration: none; }
.tweet-link a:hover { color: var(--accent); }

/* ── Sidebar ── */
.sidebar { display: flex; flex-direction: column; gap: 16px; }

/* ── Account Card ── */
.acc-row { display: flex; justify-content: space-between; align-items: center; padding: 8px 0; border-bottom: 1px solid rgba(255,255,255,0.03); font-size: 13px; }
.acc-row:last-child { border-bottom: none; }
.acc-name { font-weight: 600; }
.acc-stats { font-size: 11px; color: var(--text-dim); }
.acc-bar { height: 3px; border-radius: 2px; margin-top: 2px; transition: width 0.3s; }

/* ── Modal ── */
.modal-overlay { display: none; position: fixed; top: 0; left: 0; width: 100%; height: 100%; background: rgba(0,0,0,0.7); z-index: 100; justify-content: center; align-items: center; }
.modal-overlay.show { display: flex; }
.modal { background: var(--card-bg); border: 1px solid var(--card-border); border-radius: var(--radius); padding: 24px; width: 420px; max-width: 90vw; }
.modal h3 { margin-bottom: 14px; font-size: 16px; color: var(--text-bright); }
.modal input { width: 100%; padding: 9px 12px; border: 1px solid var(--card-border); border-radius: var(--radius); background: var(--bg); color: var(--text); font-size: 13px; margin-bottom: 10px; font-family: var(--font); outline: none; }
.modal input:focus { border-color: var(--accent); }
.modal-btn-row { display: flex; gap: 8px; justify-content: flex-end; margin-top: 14px; }
.acc-item { display: flex; justify-content: space-between; align-items: center; padding: 8px 10px; background: var(--bg); border-radius: 6px; margin-bottom: 6px; font-size: 13px; }
.acc-item .del-btn { background: none; border: none; color: var(--red); cursor: pointer; font-size: 16px; padding: 0 4px; line-height: 1; }

/* ── Empty ── */
.empty-state { text-align: center; padding: 50px 20px; color: var(--text-dim); }
.empty-icon { font-size: 36px; margin-bottom: 10px; opacity: 0.5; }

/* ── Loading ── */
.loading-pulse { text-align: center; padding: 40px; }
.pulse-dot { display: inline-block; width: 8px; height: 8px; background: var(--accent); border-radius: 50%; animation: pulse 1.2s ease infinite; margin: 0 3px; }
.pulse-dot:nth-child(2) { animation-delay: 0.2s; }
.pulse-dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes pulse { 0%, 100% { transform: scale(1); opacity: 0.4; } 50% { transform: scale(1.4); opacity: 1; } }

/* ── Signal Legend ── */
.legend-row { display: flex; align-items: center; gap: 6px; font-size: 11px; color: var(--text-dim); }
.legend-dot { width: 8px; height: 8px; border-radius: 2px; }

/* ── Sector Heatmap ── */
.heatmap-table { border-collapse: collapse; width: 100%; font-size: 12px; }
.heatmap-table th { padding: 8px 6px; text-align: center; font-weight: 600; color: var(--text-dim); font-size: 11px; white-space: nowrap; border-bottom: 1px solid var(--card-border); }
.heatmap-table th:first-child { text-align: left; }
.heatmap-table td { padding: 6px; text-align: center; border-bottom: 1px solid rgba(255,255,255,0.03); }
.heatmap-table td:first-child { text-align: left; font-weight: 600; white-space: nowrap; }
.heatmap-cell {
  display: inline-flex; align-items: center; justify-content: center;
  width: 48px; height: 30px; border-radius: 4px; font-size: 10px; font-weight: 700;
}

/* ── Sector Tags on Tweet Cards ── */
.tweet-sector-tags { display: flex; gap: 5px; flex-wrap: wrap; margin-top: 4px; }
.sector-tag {
  padding: 2px 8px; border-radius: 4px; font-size: 11px; font-weight: 600;
  display: flex; align-items: center; gap: 3px;
  border: 1px solid;
}
.tweet-interpretation {
  font-size: 13px; line-height: 1.7; color: #f0c040;
  background: rgba(240,192,64,0.06); border: 1px solid rgba(240,192,64,0.15);
  border-radius: 6px; padding: 10px 12px; margin-top: 8px;
}

/* ── Nav Tabs ── */
.nav-tabs {
  display: flex; gap: 6px; margin-bottom: 20px; flex-wrap: wrap;
  padding-bottom: 12px; border-bottom: 1px solid var(--card-border);
}
.nav-tab {
  padding: 8px 18px; border-radius: 8px; font-size: 13px; font-weight: 600;
  cursor: pointer; border: 1px solid var(--card-border);
  background: var(--card-bg); color: var(--text-dim);
  transition: all 0.15s; white-space: nowrap;
}
.nav-tab:hover { border-color: var(--accent); color: var(--text); }
.nav-tab.active { background: var(--accent); border-color: var(--accent); color: #fff; }
.view-panel { display: none; }
.view-panel.active { display: block; }

/* ── Pattern Tracker ── */
.pattern-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(260px, 1fr)); gap: 14px; margin-bottom: 16px; }
.pattern-card {
  background: var(--card-bg); border: 1px solid var(--card-border);
  border-radius: var(--radius); padding: 16px;
}
.pattern-card h3 { font-size: 14px; margin-bottom: 10px; display: flex; align-items: center; gap: 6px; }
.pattern-meter {
  height: 8px; border-radius: 4px; background: var(--card-border);
  margin: 8px 0; position: relative; overflow: hidden;
}
.pattern-meter-fill {
  height: 100%; border-radius: 4px; transition: width 0.5s ease;
}
.pattern-status { font-size: 13px; font-weight: 700; margin-bottom: 4px; }
.pattern-trend { font-size: 11px; color: var(--text-dim); }
.pattern-events { margin-top: 8px; }
.pattern-event {
  padding: 6px 8px; border-radius: 4px; background: rgba(255,255,255,0.03);
  margin-bottom: 4px; font-size: 11px; color: var(--text-dim);
  border-left: 2px solid rgba(255,255,255,0.1);
}
.pattern-event .ev-date { font-size: 10px; opacity: 0.5; }
.pattern-event .ev-source { font-weight: 600; color: var(--text); font-size: 11px; }

/* ── Account Profiles ── */
.profile-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(280px, 1fr)); gap: 14px; }
.profile-card {
  background: var(--card-bg); border: 1px solid var(--card-border);
  border-radius: var(--radius); padding: 16px;
}
.profile-header { display: flex; align-items: center; gap: 10px; margin-bottom: 12px; }
.profile-avatar {
  width: 40px; height: 40px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-size: 18px; font-weight: 700; color: #fff;
}
.profile-name { font-size: 15px; font-weight: 700; }
.profile-stats { font-size: 11px; color: var(--text-dim); }
.domain-bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; font-size: 12px; }
.domain-bar-label { width: 70px; text-align: right; color: var(--text-dim); white-space: nowrap; }
.domain-bar-track { flex: 1; height: 6px; border-radius: 3px; background: var(--card-border); overflow: hidden; }
.domain-bar-fill { height: 100%; border-radius: 3px; transition: width 0.4s; }
.domain-bar-pct { width: 36px; font-size: 11px; text-align: right; color: var(--text-dim); }
.stance-badge {
  display: inline-block; padding: 3px 10px; border-radius: 4px; font-size: 12px; font-weight: 600;
}

/* ── Resonance ── */
.resonance-card {
  background: var(--card-bg); border: 1px solid var(--card-border);
  border-radius: var(--radius); padding: 16px; margin-bottom: 12px;
  border-left: 3px solid var(--accent);
}
.resonance-card.strong { border-left-color: var(--red); }
.resonance-card.medium { border-left-color: var(--orange); }
.resonance-card.weak { border-left-color: var(--text-dim); }
.resonance-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px; }
.resonance-topic { font-size: 16px; font-weight: 700; display: flex; align-items: center; gap: 8px; }
.resonance-accounts { display: flex; gap: 6px; flex-wrap: wrap; margin-top: 8px; }
.resonance-account {
  padding: 3px 10px; border-radius: 15px; background: var(--accent-glow);
  font-size: 12px; color: var(--accent); font-weight: 600;
}
</style>
</head>
<body>
<div class="app">

  <!-- Top Bar -->
  <div class="topbar">
    <div class="topbar-brand">
      <div class="topbar-logo">II</div>
      <div>
        <h1>全球投资情报看板 <span class="topbar-sub">Investment Intelligence</span></h1>
      </div>
    </div>
    <div class="topbar-controls">
      <input type="date" id="datePicker">
      <button class="btn btn-primary" onclick="refreshAll()">刷新情报</button>
      <button class="btn" onclick="openAccountManager()">账号管理</button>
    </div>
  </div>

  <!-- Nav Tabs -->
  <div class="nav-tabs">
    <div class="nav-tab active" onclick="switchView('dashboard', this)">📋 情报看板</div>
    <div class="nav-tab" onclick="switchView('patterns', this)">🌏 格局追踪</div>
    <div class="nav-tab" onclick="switchView('profiles', this)">👤 账号画像</div>
    <div class="nav-tab" onclick="switchView('resonance', this)">🔗 主题共振</div>
  </div>

  <!-- View 1: Dashboard -->
  <div class="view-panel active" id="view-dashboard">
  <!-- Dashboard Grid -->
  <div class="dashboard-grid">
    <!-- Main Column -->
    <div class="main-col">
      <!-- Briefing -->
      <div class="card briefing" id="briefingCard" style="margin-bottom:16px;"></div>

      <!-- Signal Heat Map -->
      <div class="card" style="margin-bottom:16px;">
        <div class="card-header"><h2>📊 投资信号热力图</h2></div>
        <div class="card-body"><div class="signal-grid" id="signalGrid"></div></div>
      </div>

      <!-- Sector Heatmap -->
      <div class="card" style="margin-bottom:16px;">
        <div class="card-header"><h2>🔥 板块影响矩阵</h2><span style="font-size:11px;color:var(--text-dim);">红=利好 绿=利空</span></div>
        <div class="card-body" style="overflow-x:auto;" id="sectorHeatmap"></div>
      </div>

      <!-- Tweet List -->
      <div class="card">
        <div class="card-header">
          <h2>📋 推文情报流</h2>
          <span style="font-size:12px;color:var(--text-dim);" id="tweetCount"></span>
        </div>
        <div class="card-body" style="padding:0;" id="tweetList"></div>
      </div>
    </div>

    <!-- Sidebar -->
    <div class="sidebar">
      <!-- Risk Alerts -->
      <div class="card">
        <div class="card-header"><h2>⚠️ 风险预警</h2></div>
        <div class="card-body" id="riskPanel" style="max-height:300px;overflow-y:auto;"></div>
      </div>

      <!-- Cross Themes -->
      <div class="card">
        <div class="card-header"><h2>🔗 跨账号共识主题</h2></div>
        <div class="card-body" id="themePanel"></div>
      </div>

      <!-- Account Status -->
      <div class="card">
        <div class="card-header"><h2>👤 账号活跃度</h2></div>
        <div class="card-body" id="accountPanel"></div>
      </div>

      <!-- Signal Legend -->
      <div class="card">
        <div class="card-header"><h2>📖 信号图例</h2></div>
        <div class="card-body" id="legendPanel"></div>
      </div>
    </div>
  </div>
</div>
  </div><!-- /view-dashboard -->

  <!-- View 2: Patterns -->
  <div class="view-panel" id="view-patterns">
    <div class="pattern-row" id="patternGrid">
      <div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>
    </div>
  </div>

  <!-- View 3: Profiles -->
  <div class="view-panel" id="view-profiles">
    <div class="profile-grid" id="profileGrid">
      <div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>
    </div>
  </div>

  <!-- View 4: Resonance -->
  <div class="view-panel" id="view-resonance">
    <div id="resonancePanel">
      <div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>
    </div>
  </div>

</div><!-- /app -->

<!-- Account Modal -->
<div class="modal-overlay" id="accountModal">
  <div class="modal">
    <h3>账号管理</h3>
    <div style="display:flex;gap:8px;">
      <input type="text" id="newAccount" placeholder="输入 X 用户名（不含 @）" style="flex:1;">
      <button class="btn btn-primary" onclick="addAccount()">添加</button>
    </div>
    <div id="accountList" style="margin-top:12px;max-height:300px;overflow-y:auto;"></div>
    <div class="modal-btn-row">
      <button class="btn" onclick="closeAccountManager()">关闭</button>
    </div>
  </div>
</div>

<script>
// ── State ──
let showZh = true;
let accounts = [];
let currentData = null;

// ── Init ──
document.getElementById('datePicker').value = new Date().toISOString().split('T')[0];
loadAccounts().then(() => { refreshAll(); loadSignalLegend(); });

// ── Data Loading ──
async function loadAccounts() {
  const r = await fetch('/api/accounts');
  const d = await r.json();
  accounts = d.accounts;
  return d;
}

async function refreshAll() {
  const date = document.getElementById('datePicker').value;
  const briefingCard = document.getElementById('briefingCard');
  const signalGrid = document.getElementById('signalGrid');
  const sectorHeatmap = document.getElementById('sectorHeatmap');
  const tweetList = document.getElementById('tweetList');
  const riskPanel = document.getElementById('riskPanel');
  const themePanel = document.getElementById('themePanel');
  const accountPanel = document.getElementById('accountPanel');

  briefingCard.innerHTML = '<div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>';
  signalGrid.innerHTML = '';
  sectorHeatmap.innerHTML = '<div style="text-align:center;color:var(--text-dim);padding:20px;">加载板块数据...</div>';
  tweetList.innerHTML = '<div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>';
  riskPanel.innerHTML = '<div style="color:var(--text-dim);font-size:13px;text-align:center;">加载中...</div>';
  themePanel.innerHTML = '<div style="color:var(--text-dim);font-size:13px;text-align:center;">加载中...</div>';

  const r = await fetch(`/api/intel?date=${date}`);
  currentData = await r.json();

  renderBriefing(currentData.briefing);
  renderSignals(currentData.briefing.top_signals || []);
  renderSectorHeatmap(currentData.sector_heatmap);
  renderTweets(currentData.tweets || []);
  renderRisks(currentData.briefing.risk_alerts || []);
  renderThemes(currentData.cross_themes || []);
  renderAccountStatus(currentData.briefing.account_summary || []);
  document.getElementById('tweetCount').textContent = `共 ${currentData.total} 条`;
}

// ── Briefing ──
function renderBriefing(b) {
  if (!b || b.headline === '今日暂无推文数据') {
    document.getElementById('briefingCard').innerHTML = `
      <div class="card-header"><h2>📰 每日情报简报</h2></div>
      <div class="card-body">
        <div class="briefing-headline" style="font-size:16px;color:var(--text-dim);">今日暂无推文数据</div>
        <div class="briefing-summary">监控服务可能正在初始化，或今日各账号暂未发布新推文。请稍后再试。</div>
      </div>`;
    return;
  }
  document.getElementById('briefingCard').innerHTML = `
    <div class="card-header"><h2>📰 每日情报简报</h2><span style="font-size:11px;color:var(--text-dim);">${currentData.date}</span></div>
    <div class="card-body">
      <div class="briefing-headline">${escHtml(b.headline)}</div>
      <div class="briefing-summary">${b.summary}</div>
    </div>`;
}

// ── Signal Heat ──
function renderSignals(signals) {
  const el = document.getElementById('signalGrid');
  if (!signals.length) {
    el.innerHTML = '<span style="color:var(--text-dim);font-size:13px;">暂无投资信号</span>';
    return;
  }
  const maxCount = Math.max(...signals.map(s => s.count), 1);
  el.innerHTML = signals.map(s => {
    const opacity = 0.25 + (s.count / maxCount) * 0.75;
    return `<div class="signal-chip" style="background:${s.color}${Math.round(opacity*255).toString(16).padStart(2,'0')};color:${s.color};border:1px solid ${s.color}33;">
      ${s.emoji} ${s.category} <span class="count">×${s.count}</span>
    </div>`;
  }).join('');
}

// ── Sector Heatmap ──
function renderSectorHeatmap(heatmapData) {
  const el = document.getElementById('sectorHeatmap');
  if (!heatmapData || !heatmapData.sectors || !heatmapData.sectors.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:13px;text-align:center;padding:20px;">暂无板块影响数据</div>';
    return;
  }

  const { sectors, accounts, matrix } = heatmapData;
  // 找最大绝对值用于色彩缩放
  let maxAbs = 0;
  matrix.forEach(row => row.forEach(v => { if (Math.abs(v) > maxAbs) maxAbs = Math.abs(v); }));
  if (maxAbs === 0) maxAbs = 1;

  function heatColor(val) {
    if (Math.abs(val) < 0.3) return {bg: 'transparent', color: '#6b7084'};
    const ratio = Math.min(Math.abs(val) / maxAbs, 1);
    if (val > 0) {
      // 红 = 利好
      const r = 239, g = Math.round(68 + (1-ratio)*100), b = Math.round(68 + (1-ratio)*100);
      return {bg: `rgba(239,${g},${b},${0.15+ratio*0.6})`, color: `#ef4444`};
    } else {
      // 绿 = 利空
      const r = Math.round(34 + (1-ratio)*150), g = 197, b = Math.round(94 + (1-ratio)*100);
      return {bg: `rgba(${r},197,${b},${0.15+ratio*0.6})`, color: `#22c55e`};
    }
  }

  let html = '<table class="heatmap-table"><thead><tr><th>板块</th>';
  accounts.forEach(a => { html += `<th>@${escHtml(a)}</th>`; });
  html += '</tr></thead><tbody>';

  sectors.forEach((sec, i) => {
    html += `<tr><td>${sec.emoji} ${sec.name}</td>`;
    accounts.forEach((acc, j) => {
      const val = matrix[i][j];
      const hc = heatColor(val);
      const displayVal = val === 0 ? '' : (val > 0 ? '+' + val.toFixed(1) : val.toFixed(1));
      html += `<td><span class="heatmap-cell" style="background:${hc.bg};color:${hc.color};">${displayVal}</span></td>`;
    });
    html += '</tr>';
  });

  html += '</tbody></table>';
  el.innerHTML = html;
}

// ── Tweet List ──
function renderTweets(tweets) {
  const el = document.getElementById('tweetList');
  if (!tweets.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">📭</div><p>该日期暂无推文</p></div>';
    return;
  }
  const sentMap = {positive:'👍', negative:'👎', neutral:'➖'};
  el.innerHTML = tweets.map(t => {
    const hasHighSignal = t.signals && t.signals.length > 0;
    const signalTags = (t.signals||[]).slice(0,3).map(s =>
      `<span class="signal-tag" style="background:${s.color}22;color:${s.color};">${s.emoji} ${s.category}</span>`
    ).join('');

    // 板块标签
    const sectorTags = (t.sectors||[]).slice(0,3).map(s => {
      const dirColor = s.direction==='bullish'?'#ef4444':s.direction==='bearish'?'#22c55e':'#888';
      const dirIcon = s.direction==='bullish'?'📈':s.direction==='bearish'?'📉':'➖';
      return `<span class="sector-tag" style="color:${dirColor};border-color:${dirColor}33;background:${dirColor}0d;">${s.emoji} ${s.sector} ${dirIcon}</span>`;
    }).join('');

    return `
    <div class="tweet-card ${hasHighSignal ? 'high-signal' : ''}" id="tweet-${escAttr(t.tweet_id)}">
      <div class="tweet-meta">
        <span class="tweet-account">@${escHtml(t.username)} ${sentMap[t.sentiment]||''}</span>
        <span class="tweet-time">${escHtml(t.pub_date || t.first_seen || '')}</span>
      </div>
      <div class="tweet-content-en">${escHtml(t.content)}</div>
      ${showZh ? `<div class="tweet-content-zh" id="zh-${t.tweet_id}"><em style="opacity:0.4;">翻译中...</em></div>` : ''}
      ${signalTags ? `<div class="tweet-signal-tags">${signalTags}</div>` : ''}
      ${sectorTags ? `<div class="tweet-sector-tags">${sectorTags}</div>` : ''}
      ${t.interpretation ? `<div class="tweet-interpretation">📝 ${escHtml(t.interpretation)}</div>` : ''}
      ${t.link ? `<div class="tweet-link"><a href="${escHtml(t.link)}" target="_blank">查看原文 →</a></div>` : ''}
    </div>`;
  }).join('');

  if (showZh) {
    tweets.forEach(t => translateTweet(t.tweet_id, t.content));
  }
}

async function translateTweet(id, text) {
  try {
    const r = await fetch('/api/translate', {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify({text})});
    const d = await r.json();
    const el = document.getElementById('zh-'+id);
    if (el) el.textContent = d.translated || '[翻译失败]';
  } catch(e) {
    const el = document.getElementById('zh-'+id);
    if (el) el.textContent = '[翻译失败]';
  }
}

// ── Risk Alerts ──
function renderRisks(risks) {
  const el = document.getElementById('riskPanel');
  if (!risks.length) {
    el.innerHTML = '<div style="color:var(--green);font-size:13px;text-align:center;">✅ 暂无明显风险信号</div>';
    return;
  }
  el.innerHTML = risks.map(r => `
    <div class="risk-item" onclick="scrollToTweet('${escHtml(r.tweet_id || '')}')" style="cursor:pointer;" title="点击查看推文详情">
      <div class="risk-source">${escHtml(r.source)} → ${escHtml(r.keyword)} <span style="font-size:10px;opacity:0.5;">🔗</span></div>
      <div class="risk-excerpt">${escHtml(r.excerpt)}</div>
    </div>
  `).join('');
}

function scrollToTweet(tweetId) {
  if (!tweetId) return;
  const card = document.getElementById('tweet-' + tweetId);
  if (card) {
    card.scrollIntoView({ behavior: 'smooth', block: 'center' });
    card.style.transition = 'all 0.3s';
    card.style.boxShadow = '0 0 20px rgba(239,68,68,0.6)';
    card.style.borderColor = '#ef4444';
    card.style.borderWidth = '2px';
    setTimeout(() => {
      card.style.boxShadow = '';
      card.style.borderColor = '';
      card.style.borderWidth = '';
    }, 3000);
  }
}

// ── Cross Themes ──
function renderThemes(themes) {
  const el = document.getElementById('themePanel');
  if (!themes.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:13px;text-align:center;">暂无跨账号共识主题</div>';
    return;
  }
  el.innerHTML = themes.map(t => `
    <div class="theme-item">
      <span class="theme-topic">#${escHtml(t.topic)}</span>
      <span class="theme-accounts">${t.accounts.map(a => '@'+escHtml(a)).join(', ')}</span>
    </div>
  `).join('');
}

// ── Account Status ──
function renderAccountStatus(accSummary) {
  const el = document.getElementById('accountPanel');
  if (!accSummary.length) {
    el.innerHTML = '<div style="color:var(--text-dim);font-size:13px;text-align:center;">暂无数据</div>';
    return;
  }
  const maxCount = Math.max(...accSummary.map(a => a.count), 1);
  const colors = ['#3b82f6','#a855f7','#06b6d4','#f59e0b','#22c55e'];
  el.innerHTML = accSummary.map((a,i) => {
    const pct = Math.round(a.count/maxCount*100);
    const color = colors[i % colors.length];
    return `
      <div class="acc-row">
        <span class="acc-name">@${escHtml(a.username)}</span>
        <span class="acc-stats">${a.count}条</span>
      </div>
      <div class="acc-bar" style="width:${pct}%;background:${color};"></div>
    `;
  }).join('');
}

// ── Signal Legend ──
async function loadSignalLegend() {
  const r = await fetch('/api/categories');
  const cats = await r.json();
  const el = document.getElementById('legendPanel');
  el.innerHTML = Object.entries(cats).map(([name, info]) => `
    <div class="legend-row" style="margin-bottom:6px;">
      <span class="legend-dot" style="background:${info.color};"></span>
      <span style="font-weight:600;">${info.emoji} ${name}</span>
      <span style="font-size:10px;opacity:0.6;">${info.impact.slice(0,18)}...</span>
    </div>
  `).join('');
}

// ── Account Manager ──
function openAccountManager() { document.getElementById('accountModal').classList.add('show'); renderAccountList(); }
function closeAccountManager() { document.getElementById('accountModal').classList.remove('show'); }
function renderAccountList() {
  const r = accounts.map(a => `<div class="acc-item"><span>@${escHtml(a)}</span><button class="del-btn" onclick="removeAccount('${escHtml(a)}')">×</button></div>`).join('');
  document.getElementById('accountList').innerHTML = r;
}
async function addAccount() {
  const input = document.getElementById('newAccount');
  const name = input.value.trim();
  if (!name) return;
  const r = await fetch('/api/accounts', {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})});
  if (r.ok) {
    await loadAccounts();
    renderAccountList();
    input.value = '';
    refreshAll();
  } else {
    const d = await r.json();
    alert(d.error || '添加失败');
  }
}
async function removeAccount(name) {
  if (!confirm(`确定删除 @${name}？`)) return;
  const r = await fetch('/api/accounts', {method:'DELETE',headers:{'Content-Type':'application/json'},body:JSON.stringify({username:name})});
  if (r.ok) { await loadAccounts(); renderAccountList(); refreshAll(); }
}

// ── View Navigation ──
function switchView(name, tab) {
  document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
  tab.classList.add('active');
  document.querySelectorAll('.view-panel').forEach(p => p.classList.remove('active'));
  document.getElementById('view-' + name).classList.add('active');
  if (name === 'patterns') loadPatterns();
  else if (name === 'profiles') loadProfiles();
  else if (name === 'resonance') loadResonance();
}

// ── Pattern Tracker ──
async function loadPatterns() {
  const el = document.getElementById('patternGrid');
  el.innerHTML = '<div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>';
  const r = await fetch('/api/patterns?days=14');
  const data = await r.json();
  if (data.error) { el.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>'+escHtml(data.error)+'</p></div>'; return; }
  renderPatterns(data);
}

function renderPatterns(data) {
  const el = document.getElementById('patternGrid');
  const dims = ['sino_us', 'fed_policy', 'crypto', 'ai_race'];
  const trendIcons = {escalating: '↑紧张', improving: '↓缓和', stable: '→持平', neutral: '→持平'};
  el.innerHTML = dims.map(key => {
    const d = data[key];
    if (!d) return '';
    const score = d.avg_sentiment || 0;
    const absScore = Math.min(Math.abs(score), 2);
    const meterPct = absScore / 2 * 100;
    const meterColor = score > 0 ? '#ef4444' : (score < 0 ? '#22c55e' : '#6b7084');
    const events = (d.recent_key_events || []).slice(0, 3);
    return `<div class="pattern-card">
      <h3>${d.emoji} ${d.name} <span style="font-size:11px;color:var(--text-dim);margin-left:auto;">${d.period_days}d</span></h3>
      <div class="pattern-status" style="color:${meterColor};">${d.status || '中性'} (${(score>0?'+':'')+score.toFixed(1)})</div>
      <div class="pattern-trend">趋势: ${trendIcons[d.trend_direction] || d.trend_direction} | 变化 ${(d.trend_change_pct||0)>0?'+':''}${d.trend_change_pct||0}%</div>
      <div class="pattern-meter"><div class="pattern-meter-fill" style="width:${meterPct}%;background:${meterColor};"></div></div>
      <div style="font-size:11px;color:var(--text-dim);margin-top:4px;">${d.total_signals||0} 条相关信号</div>
      ${events.length ? '<div class="pattern-events">'+events.map(e => 
        `<div class="pattern-event"><span class="ev-date">${e.date}</span> <span class="ev-source">${escHtml(e.source)}</span>: ${escHtml(e.excerpt||'')}</div>`
      ).join('')+'</div>' : ''}
    </div>`;
  }).join('');
}

// ── Account Profiles ──
let loadedProfiles = false;
async function loadProfiles() {
  if (loadedProfiles) return;
  const el = document.getElementById('profileGrid');
  el.innerHTML = '<div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>';
  const r = await fetch('/api/profiles?days=30');
  const data = await r.json();
  if (data.error) { el.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>'+escHtml(data.error)+'</p></div>'; return; }
  renderProfiles(data);
  loadedProfiles = true;
}

function renderProfiles(data) {
  const el = document.getElementById('profileGrid');
  const avatarColors = ['#e74c3c','#3498db','#22c55e','#f39c12','#9b59b6','#f72585'];
  const profiles = Object.entries(data);
  el.innerHTML = profiles.map(([username, p], i) => {
    if (p.error) return `<div class="profile-card"><div class="profile-header"><div class="profile-avatar" style="background:var(--text-dim);">?</div><div><div class="profile-name">@${escHtml(username)}</div><div class="profile-stats">暂无数据</div></div></div></div>`;
    const domains = p.domains || {};
    const topDomains = Object.entries(domains).sort((a,b) => b[1].pct - a[1].pct).slice(0, 5);
    const colors = ['#ef4444','#3b82f6','#22c55e','#f39c12','#a855f7','#06b6d4','#ec4899'];
    return `<div class="profile-card">
      <div class="profile-header">
        <div class="profile-avatar" style="background:${avatarColors[i%avatarColors.length]};">${username[0].toUpperCase()}</div>
        <div>
          <div class="profile-name">@${escHtml(username)}</div>
          <div class="profile-stats">${p.total_tweets||0} 条推文 · 活跃 ${p.active_days||0}/${p.period_days||30}d · 日均 ${p.daily_avg||0}条</div>
        </div>
      </div>
      ${topDomains.map(([dk, dv], di) => `
        <div class="domain-bar-row">
          <span class="domain-bar-label">${dv.emoji} ${dv.name}</span>
          <div class="domain-bar-track"><div class="domain-bar-fill" style="width:${dv.pct}%;background:${colors[di%colors.length]};"></div></div>
          <span class="domain-bar-pct">${dv.pct}%</span>
        </div>
      `).join('')}
      <div style="margin-top:10px;font-size:12px;display:flex;justify-content:space-between;align-items:center;">
        <span>对华态度: <span class="stance-badge" style="background:${(p.china_stance?.score||0)>0?'rgba(34,197,94,0.15)':'rgba(239,68,68,0.15)'};color:${(p.china_stance?.score||0)>0?'var(--green)':'var(--red)'};">${p.china_stance?.label||'?'}</span></span>
        <span style="color:var(--text-dim);">${p.china_stance?.mentions||0}条中国相关</span>
      </div>
    </div>`;
  }).join('');
}

// ── Theme Resonance ──
let loadedResonance = false;
async function loadResonance() {
  if (loadedResonance) return;
  const el = document.getElementById('resonancePanel');
  el.innerHTML = '<div class="loading-pulse"><div class="pulse-dot"></div><div class="pulse-dot"></div><div class="pulse-dot"></div></div>';
  const r = await fetch('/api/resonance?days=7');
  const data = await r.json();
  if (data.error) { el.innerHTML = '<div class="empty-state"><div class="empty-icon">⚠️</div><p>'+escHtml(data.error)+'</p></div>'; return; }
  renderResonance(data);
  loadedResonance = true;
}

function renderResonance(data) {
  const el = document.getElementById('resonancePanel');
  const themes = data.themes || [];
  if (!themes.length) {
    el.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><p>过去7天内未发现跨账号共振话题</p></div>';
    return;
  }
  const strengthLabels = {strong:'强共振',medium:'中',weak:'弱'};
  el.innerHTML = `
    <div style="font-size:13px;color:var(--text-dim);margin-bottom:12px;">过去 ${data.period_days||7} 天，${themes.length} 个话题被多人同时提及</div>
    ${themes.map(t => `
    <div class="resonance-card ${t.strength}">
      <div class="resonance-header">
        <span class="resonance-topic">${t.emoji} ${t.name} <span style="font-size:11px;opacity:0.6;">[${strengthLabels[t.strength]||t.strength}]</span></span>
        <span style="font-size:12px;color:var(--text-dim);">${t.tweet_count} 条推文</span>
      </div>
      <div class="resonance-accounts">
        ${t.accounts.map(a => `<span class="resonance-account">@${escHtml(a)}</span>`).join('')}
        <span style="font-size:11px;color:var(--text-dim);margin-left:4px;">${t.account_count}人共同关注</span>
      </div>
    </div>`).join('')}`;
}

// ── Utils ──
function escHtml(s) { const d = document.createElement('div'); d.textContent = s; return d.innerHTML; }
function escAttr(s) { return String(s).replace(/[<>\"'&]/g, ''); }
</script>
</body>
</html>"""


# ═════════════════════════════════════════════════════════════
#  启动
# ═════════════════════════════════════════════════════════════

def main():
    parser = argparse.ArgumentParser(description="全球投资情报看板")
    parser.add_argument("--port", type=int, default=8080, help="端口号 (默认 8080)")
    parser.add_argument("--host", type=str, default="0.0.0.0", help="绑定地址")
    parser.add_argument("--debug", action="store_true", help="调试模式")
    args = parser.parse_args()

    print(f"""
╔══════════════════════════════════════════════════╗
║     全球投资情报看板 — Investment Intelligence      ║
╠══════════════════════════════════════════════════╣
║  地址: http://{args.host}:{args.port}                    ║
║  数据库: {DB_PATH}
╚══════════════════════════════════════════════════╝
    """)
    app.run(host=args.host, port=args.port, debug=args.debug)


if __name__ == "__main__":
    main()
