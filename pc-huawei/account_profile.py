#!/usr/bin/env python3
"""
账号画像引擎 — Account Profile Builder
=======================================
为每个监控账号构建画像：
  - 关注领域雷达图 (7个维度)
  - 情感倾向分布
  - 对华态度变化趋势
  - 最近活跃度 + 影响力评分
  - 关键词云
"""

import json, logging, os, sqlite3, re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "tweets.db"
logger = logging.getLogger("account_profile")

# ═══════════ 领域分类 ═══════════
DOMAINS = {
    "trade_economy": {"name": "贸易经济", "emoji": "💰", "kw": ["tariff", "trade", "economy", "inflation", "关税", "贸易", "经济", "通胀"]},
    "tech_ai": {"name": "科技AI", "emoji": "🤖", "kw": ["AI", "GPT", "芯片", "GPU", "tech", "AI", "autonomous", "robot", "compute"]},
    "crypto_blockchain": {"name": "加密区块链", "emoji": "₿", "kw": ["bitcoin", "crypto", "blockchain", "BTC", "ETH", "加密", "区块链"]},
    "geopolitics": {"name": "地缘政治", "emoji": "🌍", "kw": ["war", "conflict", "Taiwan", "Ukraine", "NATO", "战争", "冲突", "制裁"]},
    "monetary_policy": {"name": "货币政策", "emoji": "🏦", "kw": ["rate", "Fed", "FOMC", "interest", "CPI", "利率", "降息", "加息"]},
    "china_related": {"name": "中国市场", "emoji": "🇨🇳", "kw": ["China", "Chinese", "Beijing", "中国", "人民币", "RMB", "A股"]},
    "society_culture": {"name": "社会文化", "emoji": "💬", "kw": ["freedom", "speech", "media", "民主", "自由", "言论", "culture"]},
}

CHINA_STANCE_KW = {
    "positive": ["China deal", "China cooperation", "China good", "中国合作", "中美友好", "trade deal"],
    "negative": ["China threat", "China virus", "China steal", "中国威胁", "Chinese communist", "CCP", "中共"],
    "neutral": ["China market", "China business", "China growth", "中国市场", "中国经济"],
}

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def build_profile(username: str, days: int = 30) -> dict:
    """构建单个账号画像"""
    conn = get_db()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT content, pub_date, first_seen FROM tweets WHERE username = ? AND date(first_seen) >= ? ORDER BY first_seen ASC",
            (username, cutoff)
        ).fetchall()

        if not rows:
            return {"username": username, "error": "no_data", "total_tweets": 0}

        total = len(rows)
        texts = [r["content"] for r in rows]

        # 1. 领域分布
        domain_counts = {}
        for dk, dv in DOMAINS.items():
            cnt = sum(1 for t in texts if any(kw.lower() in t.lower() for kw in dv["kw"]))
            domain_counts[dk] = round(cnt / total * 100, 1) if total > 0 else 0

        # 2. 情感分布
        sentiment_dist = {"positive": 0, "negative": 0, "neutral": 0}
        pos_words = ["great", "good", "best", "amazing", "excellent", "成功", "突破", "利好", "bullish", "record", "historic"]
        neg_words = ["bad", "terrible", "disaster", "fail", "wrong", "危机", "崩盘", "利空", "bearish", "crash"]
        for t in texts:
            p = sum(1 for w in pos_words if w.lower() in t.lower())
            n = sum(1 for w in neg_words if w.lower() in t.lower())
            if p > n:
                sentiment_dist["positive"] += 1
            elif n > p:
                sentiment_dist["negative"] += 1
            else:
                sentiment_dist["neutral"] += 1
        sentiment_pct = {k: round(v / total * 100, 1) for k, v in sentiment_dist.items()}

        # 3. 对华态度
        china_stance_scores = {"positive": 0, "negative": 0, "neutral": 0}
        for t in texts:
            for stance, kws in CHINA_STANCE_KW.items():
                for kw in kws:
                    if kw.lower() in t.lower():
                        china_stance_scores[stance] += 1
        total_china = sum(china_stance_scores.values())
        if total_china > 0:
            china_index = (
                china_stance_scores["positive"] * 2
                + china_stance_scores["neutral"] * 0
                + china_stance_scores["negative"] * -2
            ) / total_china
        else:
            china_index = 0
        china_stance_label = "友好" if china_index > 0.5 else ("敌对" if china_index < -0.5 else "务实/中性")

        # 4. 活跃度分析
        days_active = len(set((r.get("first_seen") or "")[:10] for r in rows))
        daily_avg = round(total / max(days_active, 1), 1)
        first_date = min((r.get("first_seen") or "")[:10] for r in rows)
        last_date = max((r.get("first_seen") or "")[:10] for r in rows)

        # 5. Top关键词
        all_words = " ".join(texts).lower()
        word_counts = Counter(re.findall(r'\b[a-z]{4,}\b', all_words))
        # 过滤常见停用词
        stopwords = {"this", "that", "with", "from", "have", "will", "they", "what", "when", "about", "just", "like", "make", "been", "more", "some", "very", "also", "than", "into", "other", "only", "over", "such", "even", "most", "much", "many", "well", "back", "down", "after", "could", "would", "their", "there", "which", "these", "those"}
        top_keywords = [(w, c) for w, c in word_counts.most_common(20) if w not in stopwords][:10]

        # 6. 每日活跃曲线
        daily_tweets = defaultdict(int)
        for r in rows:
            day = (r.get("first_seen") or "")[:10]
            daily_tweets[day] += 1
        activity_timeline = [
            {"date": d, "count": daily_tweets.get(d, 0)}
            for d in sorted(daily_tweets.keys())[-14:]
        ]

        return {
            "username": username,
            "period_days": days,
            "total_tweets": total,
            "active_days": days_active,
            "daily_avg": daily_avg,
            "first_seen": first_date,
            "last_seen": last_date,
            "domains": {dk: {"name": DOMAINS[dk]["name"], "emoji": DOMAINS[dk]["emoji"], "pct": domain_counts[dk]} for dk in DOMAINS},
            "sentiment": sentiment_pct,
            "china_stance": {
                "score": round(china_index, 2),
                "label": china_stance_label,
                "mentions": total_china,
            },
            "top_keywords": [{"word": w, "count": c} for w, c in top_keywords],
            "activity_timeline": activity_timeline,
        }
    finally:
        conn.close()

def build_all(usernames: list, days: int = 30) -> dict:
    """构建所有账号画像"""
    profiles = {}
    for u in usernames:
        profiles[u] = build_profile(u, days)
    return profiles

def build_theme_resonance(usernames: list, days: int = 7) -> dict:
    """跨账号主题共振分析：发现多个账号共同讨论的话题"""
    conn = get_db()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT username, content, first_seen FROM tweets WHERE date(first_seen) >= ?",
            (cutoff,)
        ).fetchall()

        # 按主题聚类
        themes = {
            "tariff_trade": {"name": "关税/贸易战", "emoji": "🚢", "kw": ["tariff", "trade war", "关税", "贸易战", "export", "import"], "accounts": set(), "count": 0},
            "ai_tech": {"name": "AI/科技", "emoji": "🤖", "kw": ["AI", "GPT", "artificial intelligence", "大模型", "OpenAI", "compute", "chip"], "accounts": set(), "count": 0},
            "crypto_market": {"name": "加密货币", "emoji": "₿", "kw": ["bitcoin", "crypto", "BTC", "blockchain", "加密", "token"], "accounts": set(), "count": 0},
            "fed_inflation": {"name": "通胀/利率", "emoji": "📊", "kw": ["inflation", "rate", "Fed", "CPI", "通胀", "利率", "FOMC"], "accounts": set(), "count": 0},
            "geopolitics": {"name": "地缘政治", "emoji": "🌍", "kw": ["war", "conflict", "Ukraine", "Taiwan", "Gaza", "战争", "冲突"], "accounts": set(), "count": 0},
            "china_market": {"name": "中国/市场", "emoji": "🇨🇳", "kw": ["China", "Chinese", "中国", "RMB", "A股", "Beijing"], "accounts": set(), "count": 0},
        }

        for r in rows:
            text = r["content"].lower()
            uname = r["username"]
            for tk, tv in themes.items():
                if any(kw.lower() in text for kw in tv["kw"]):
                    tv["accounts"].add(uname)
                    tv["count"] += 1

        resonance = []
        for tk, tv in themes.items():
            if len(tv["accounts"]) >= 2:  # 至少2个账号提及
                resonance.append({
                    "theme_key": tk,
                    "name": tv["name"],
                    "emoji": tv["emoji"],
                    "accounts": sorted(tv["accounts"]),
                    "account_count": len(tv["accounts"]),
                    "tweet_count": tv["count"],
                    "strength": "strong" if len(tv["accounts"]) >= 4 else ("medium" if len(tv["accounts"]) >= 3 else "weak"),
                })

        resonance.sort(key=lambda x: -x["account_count"])
        return {"period_days": days, "themes": resonance}
    finally:
        conn.close()


# ── 测试 ──
if __name__ == "__main__":
    profiles = build_all(["realDonaldTrump", "elonmusk"], 30)
    for u, p in profiles.items():
        print(f"\n@{u}: {p.get('total_tweets', 0)} tweets, active {p.get('active_days', 0)}/30 days")
        for dk, dv in p.get("domains", {}).items():
            print(f"  {dv['emoji']} {dv['name']}: {dv['pct']}%")
        print(f"  对华态度: {p.get('china_stance', {}).get('label', '?')} ({p.get('china_stance', {}).get('score', '?')})")

    ress = build_theme_resonance(["realDonaldTrump", "elonmusk", "CathieDWood", "justinsuntron", "federalreserve"], 7)
    print("\n跨账号共振主题:")
    for r in ress["themes"]:
        print(f"  {r['emoji']} {r['name']}: {len(r['accounts'])}个账号 ({', '.join(r['accounts'])}) x{r['tweet_count']} [{r['strength']}]")
