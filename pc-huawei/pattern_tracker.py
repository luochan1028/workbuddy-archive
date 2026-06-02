#!/usr/bin/env python3
"""
格局追踪引擎 — Global Pattern Tracker
======================================
四大维度：中美关系 / Fed利率 / 加密风向 / AI竞争
每维度输出：趋势方向、关键事件、最新信号。
"""

import json, logging, os, sqlite3, re
from collections import defaultdict, Counter
from datetime import datetime, timedelta
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "tweets.db"
logger = logging.getLogger("pattern_tracker")

# ═══════════ 维度定义 ═══════════
DIMS = {
    "sino_us": {
        "name": "中美关系", "emoji": "🌏", "color": "#e74c3c",
        "desc": "中美贸易、科技、地缘政治关系的温度计",
        "kw": {
            "tariff": -1, "关税": -1, "trade war": -2, "贸易战": -2,
            "sanction": -2, "制裁": -2, "entity list": -2, "实体清单": -2,
            "decouple": -2, "脱钩": -2, "de-risk": -1,
            "export control": -1, "出口管制": -1, "ban": -2, "禁止": -2,
            "trade deal": 2, "贸易协议": 2, "cooperation": 1, "合作": 1,
            "dialogue": 1, "对话": 1, "summit": 1, "峰会": 1, "truce": 2,
            "Taiwan": -1, "台海": -1, "南海": -1, "South China Sea": -1,
            "Huawei": -1, "TikTok": -1, "China threat": -2,
        },
    },
    "fed_policy": {
        "name": "Fed利率路径", "emoji": "🏦", "color": "#3498db",
        "desc": "美联储货币政策走向：加息/降息预期、通胀、就业",
        "kw": {
            "rate cut": -1, "降息": -1, "easing": -1, "dovish": -1,
            "鸽派": -1, "soft landing": 0, "QE": -1, "量化宽松": -1,
            "rate hike": 1, "加息": 1, "tightening": 1, "hawkish": 1,
            "鹰派": 1, "higher for longer": 1, "maintain rate": 1,
            "inflation high": 1, "通胀上升": 1,
            "inflation cooling": -1, "CPI down": -1,
            "recession": -1, "衰退": -1, "hard landing": -1,
            "stimulus": -1, "stimulus check": -1, "taper": 1,
        },
    },
    "crypto": {
        "name": "加密风向", "emoji": "₿", "color": "#f39c12",
        "desc": "加密货币监管、市场情绪、机构采用",
        "kw": {
            "BTC ETF": 2, "Bitcoin ETF": 2, "crypto ETF": 2,
            "crypto friendly": 2, "pro crypto": 2, "bull market": 2, "牛市": 2,
            "institutional": 1, "adoption": 1, "采用": 1,
            "blockchain": 1, "区块链": 1, "rally": 1,
            "crypto ban": -2, "crackdown": -2, "禁止加密": -2,
            "SEC lawsuit": -1, "regulation hostile": -1,
            "crypto crash": -2, "崩盘": -2, "hack": -1, "rug pull": -2,
            "mining ban": -2, "挖矿禁止": -2, "stablecoin ban": -2,
        },
    },
    "ai_race": {
        "name": "AI竞争", "emoji": "🤖", "color": "#9b59b6",
        "desc": "全球AI技术竞赛：算力、模型、政策",
        "kw": {
            "GPT": 1, "AGI": 2, "superintelligence": 2,
            "AI breakthrough": 2, "new model": 1, "open source model": 1,
            "data center": 1, "数据中心": 1, "compute": 1, "算力": 1,
            "GPU": 1, "H100": 1, "B200": 1,
            "AI regulation": -1, "AI ban": -2, "AI safety": -1,
            "compute sanction": -2, "technology race": 1,
            "OpenAI": 1, "ChatGPT": 1, "xAI": 1, "Grok": 1,
            "AI investment": 1, "AI capex": 1,
            "robot": 1, "机器人": 1, "FSD": 1, "autonomous": 1,
        },
    },
}

def get_db():
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn

def score_tweet(text: str, keywords: dict) -> int:
    """单条推文的情感得分"""
    text_lower = text.lower()
    total = 0
    for kw, val in keywords.items():
        if kw.lower() in text_lower:
            total += val
    return total

def analyze_dimension(dim_key: str, days: int = 14) -> dict:
    """分析一个格局维度"""
    dim = DIMS[dim_key]
    conn = get_db()
    try:
        cutoff = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        rows = conn.execute(
            "SELECT username, content, pub_date, first_seen FROM tweets WHERE date(first_seen) >= ? ORDER BY first_seen ASC",
            (cutoff,)
        ).fetchall()

        daily_scores = defaultdict(lambda: {"score": 0, "count": 0, "tweets": []})
        key_events = []
        total_score = 0
        total_count = 0

        for r in rows:
            s = score_tweet(r["content"], dim["kw"])
            if s == 0:
                continue
            day = (r.get("first_seen") or r.get("pub_date") or "")[:10]
            daily_scores[day]["score"] += s
            daily_scores[day]["count"] += 1
            total_score += s
            total_count += 1

            if abs(s) >= 2:  # 强信号事件
                excerpt = r["content"][:80] + "..." if len(r["content"]) > 80 else r["content"]
                key_events.append({
                    "date": day,
                    "source": f"@{r['username']}",
                    "excerpt": excerpt,
                    "score": s,
                    "impact": "strong_positive" if s >= 2 else "strong_negative",
                })

        # 趋势计算
        avg_score = round(total_score / total_count, 2) if total_count > 0 else 0
        sorted_days = sorted(daily_scores.keys())
        trend_direction = "neutral"
        trend_change_pct = 0

        if len(sorted_days) >= 3:
            first_half = sorted_days[:len(sorted_days)//2]
            second_half = sorted_days[len(sorted_days)//2:]
            first_avg = sum(daily_scores[d]["score"] / max(daily_scores[d]["count"], 1) for d in first_half) / len(first_half)
            second_avg = sum(daily_scores[d]["score"] / max(daily_scores[d]["count"], 1) for d in second_half) / len(second_half)

            if abs(first_avg) < 0.01:
                trend_change_pct = 0
            else:
                trend_change_pct = round((second_avg - first_avg) / abs(first_avg) * 100)

            if trend_change_pct > 20:
                trend_direction = "escalating" if second_avg > 0 else "improving"
            elif trend_change_pct < -20:
                trend_direction = "improving" if second_avg > 0 else "escalating"
            else:
                trend_direction = "stable"

        # 最新信号
        recent_events = [e for e in key_events if e["date"] >= sorted_days[-3] if sorted_days][-5:] if sorted_days else []
        daily_timeline = [
            {"date": d, "score": round(v["score"] / max(v["count"], 1), 2), "count": v["count"]}
            for d in sorted_days[-7:]
        ]

        status_map = {-2: "紧张", -1: "偏冷", 0: "中性", 1: "偏暖", 2: "友好"}
        status = status_map.get(round(avg_score), "中性")

        return {
            "dim_key": dim_key,
            "name": dim["name"], "emoji": dim["emoji"], "color": dim["color"],
            "description": dim["desc"],
            "period_days": days,
            "total_signals": total_count,
            "avg_sentiment": avg_score,
            "status": status,
            "trend_direction": trend_direction,
            "trend_change_pct": trend_change_pct,
            "daily_timeline": daily_timeline,
            "recent_key_events": recent_events,
            "key_events": key_events[-10:],
        }
    finally:
        conn.close()

def analyze_all(days: int = 14) -> dict:
    """分析全部四个维度"""
    results = {}
    for key in DIMS:
        results[key] = analyze_dimension(key, days)
    return results

def generate_summary(results: dict) -> str:
    """生成格局总结文本"""
    lines = []
    for key, dim in DIMS.items():
        r = results.get(key, {})
        status = r.get("status", "?")
        trend = r.get("trend_direction", "?")
        trend_icons = {"escalating": "↑紧张", "improving": "↓缓和", "stable": "→持平"}
        lines.append(f"{dim['emoji']} {dim['name']}: {status} ({trend_icons.get(trend, trend)})")
    return "\n".join(lines)

# ── 测试 ──
if __name__ == "__main__":
    results = analyze_all(14)
    print(generate_summary(results))
    for k, r in results.items():
        print(f"\n{r['emoji']} {r['name']}: score={r['avg_sentiment']} trend={r['trend_direction']}({r['trend_change_pct']}%) events={len(r['key_events'])}")
