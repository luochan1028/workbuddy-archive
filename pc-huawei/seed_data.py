#!/usr/bin/env python3
"""
数据初始化脚本 — 预填充历史推文
=================================
用于新部署或清空数据库后的数据预热。
从模拟数据中创建近期推文，让看板立即可用。

用法:
    python seed_data.py                  # 填充所有5个账号的示例数据
    python seed_data.py --days 7         # 填充最近7天
    python seed_data.py --clear          # 清空数据库后重新填充
"""

import argparse
import hashlib
import json
import logging
import os
import sqlite3
import sys
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from random import choice, randint, uniform

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "tweets.db"

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("seed_data")

# ═════════════════════════════════════════════════════════════
#  推文模板库 — 按账号 + 主题 + 情感
# ═════════════════════════════════════════════════════════════

TWEET_TEMPLATES = {
    "realDonaldTrump": {
        "关税贸易": [
            ("We will impose massive tariffs on Chinese goods. The trade deficit with China is a DISASTER and it ENDS NOW!", "negative"),
            ("Just signed an Executive Order to increase tariffs on China by another 25%. They have taken advantage of us for too long!", "negative"),
            ("China wants a deal. They need a deal more than we do. We are in a very strong position. Tariffs are a beautiful thing!", "negative"),
            ("Negotiations with China are going very well. Phase Two of the trade deal will be even better than Phase One!", "positive"),
        ],
        "货币政策": [
            ("The Federal Reserve should CUT RATES immediately! Our competitors are way ahead. We need lower rates and a weaker dollar!", "negative"),
            ("Jerome Powell is doing a terrible job. The economy would be BOOMING if the Fed would just lower interest rates!", "negative"),
            ("Great GDP numbers today! The economy is roaring back despite the Fed's terrible policies. America First!", "positive"),
        ],
        "中国市场": [
            ("China is not our friend. They have been ripping us off for decades. That stops with me!", "negative"),
            ("Many companies are leaving China and coming back to America. We are bringing back the supply chain!", "negative"),
            ("I have great respect for President Xi. We have a very good relationship despite the trade issues.", "positive"),
        ],
        "科技AI": [
            ("America must lead the world in AI and technology. We cannot let China get ahead of us in this critical race!", "negative"),
            ("Big Tech companies are doing incredible work on AI. The future of America is bright with these innovations!", "positive"),
        ],
        "地缘政治": [
            ("Our military is now the STRONGEST it has ever been. Nobody would dare challenge the United States of America!", "positive"),
            ("The situation in Taiwan is very complex. We will continue to support our friends in the region.", "neutral"),
        ],
    },
    "elonmusk": {
        "科技AI": [
            ("Grok 3 is coming. It will be the most powerful AI model on Earth. The pace of improvement is staggering.", "positive"),
            ("FSD (Full Self-Driving) version 13 is mind-blowing. The car drives better than most humans now.", "positive"),
            ("xAI is hiring the best engineers in the world. We're building a truly maximally curious AI.", "positive"),
            ("AI compute is the new oil. Whoever controls the GPUs controls the future.", "neutral"),
        ],
        "中国市场": [
            ("Tesla Shanghai factory is one of the most efficient manufacturing plants on Earth. Incredible team in China!", "positive"),
            ("FSD is now approved for testing in China. This is a huge milestone for autonomous driving in the world's largest auto market.", "positive"),
            ("China EV market is insanely competitive. BYD and others are making great cars. Iron sharpens iron!", "positive"),
        ],
        "加密币圈": [
            ("Bitcoin is interesting. Dogecoin is the people's crypto. Memes are the purest form of communication.", "positive"),
            ("Crypto has the potential to increase individual freedom and reduce government control over money.", "positive"),
        ],
        "货币政策": [
            ("The Fed needs to cut rates. They are operating on lagging data and will cause unnecessary economic pain.", "negative"),
            ("Commercial real estate is the next shoe to drop. Refinancing at these rates is brutal.", "negative"),
        ],
    },
    "CathieDWood": {
        "科技AI": [
            ("AI is the most transformative technology since the internet. We are in the early innings of a multi-decade revolution.", "positive"),
            ("Tesla is not a car company. It's an AI and robotics company that happens to also make cars. The valuation will reflect this eventually.", "positive"),
            ("The convergence of AI, blockchain, and genomics will create $200 trillion in value by 2030.", "positive"),
        ],
        "加密币圈": [
            ("Bitcoin is digital gold and will reach $1.5 million per coin by 2030. Institutional adoption is accelerating.", "positive"),
            ("DeFi is rebuilding the entire financial system from scratch. The total addressable market is the global financial system.", "positive"),
        ],
        "货币政策": [
            ("Deflation is the real risk, not inflation. The Fed will be forced to cut rates aggressively in 2025.", "positive"),
            ("Innovation is inherently deflationary. AI and robotics will drive costs down across every sector.", "neutral"),
        ],
    },
    "justinsuntron": {
        "加密币圈": [
            ("TRON network just hit a new ATH in daily active users. The future of decentralized internet is being built on TRON!", "positive"),
            ("Just acquired another major crypto asset. The crypto winter is over. We are entering the golden age of Web3!", "positive"),
            ("Stablecoins on TRON now exceed $60 billion in circulation. TRON is the highway of the digital economy!", "positive"),
        ],
        "科技AI": [
            ("AI + Blockchain is the biggest opportunity of our generation. Decentralized AI will change everything.", "positive"),
        ],
        "中国市场": [
            ("China's digital economy is growing faster than any other country. The future is being built in Asia!", "positive"),
        ],
    },
    "federalreserve": {
        "货币政策": [
            ("The Committee decided to maintain the target range for the federal funds rate at 5.25 to 5.5 percent.", "neutral"),
            ("Recent indicators suggest that economic activity has been expanding at a solid pace. Job gains remain strong.", "neutral"),
            ("Inflation has eased over the past year but remains elevated. The Committee remains highly attentive to inflation risks.", "neutral"),
            ("The Committee does not expect it will be appropriate to reduce the target range until it has gained greater confidence that inflation is moving sustainably toward 2 percent.", "neutral"),
        ],
    },
}

# 没有模板的账号的通用推文
GENERIC_TWEETS = [
    ("The global economy continues to show resilience despite geopolitical tensions.", "neutral"),
    ("Technology stocks lead market rally as AI optimism grows.", "positive"),
    ("Investors remain cautious ahead of key economic data releases this week.", "neutral"),
]


def generate_tweet_id(content: str) -> str:
    """生成伪推文ID"""
    h = hashlib.md5(content.encode()).hexdigest()
    return f"18{int(h[:14], 16) % 10**17:017d}"


def seed_database(days: int = 3, clear: bool = False, accounts: list = None):
    """填充数据库"""
    conn = sqlite3.connect(str(DB_PATH))
    cursor = conn.cursor()

    # 确保表存在
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS tweets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tweet_id TEXT NOT NULL,
            username TEXT NOT NULL DEFAULT 'realDonaldTrump',
            content TEXT NOT NULL,
            content_hash TEXT NOT NULL,
            pub_date TEXT,
            link TEXT,
            source_instance TEXT,
            media_urls TEXT,
            is_new INTEGER DEFAULT 1,
            first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            UNIQUE(username, tweet_id)
        )
    """)

    if clear:
        cursor.execute("DELETE FROM tweets")
        logger.info("已清空数据库")

    existing = cursor.execute("SELECT count(*) FROM tweets").fetchone()[0]
    if existing > 0 and not clear:
        logger.info(f"数据库中已有 {existing} 条推文，跳过填充（使用 --clear 强制重建）")
        conn.close()
        return

    if not accounts:
        cfg_path = SCRIPT_DIR / "config.json"
        if cfg_path.exists():
            with open(cfg_path) as f:
                cfg = json.load(f)
            accounts = cfg.get("accounts", list(TWEET_TEMPLATES.keys()))
        else:
            accounts = list(TWEET_TEMPLATES.keys())

    total_inserted = 0
    now = datetime.now()

    for username in accounts:
        templates = TWEET_TEMPLATES.get(username, {})
        if not templates:
            # 使用通用推文
            for day_offset in range(days):
                for _ in range(randint(1, 3)):
                    content, sentiment = choice(GENERIC_TWEETS)
                    tweet_id = generate_tweet_id(content + username + str(day_offset) + str(_))
                    _insert_tweet(cursor, username, tweet_id, content, now, day_offset)
                    total_inserted += 1
            continue

        for day_offset in range(days):
            # 每个账号每天 3-8 条推文
            daily_count = randint(3, 8)
            used_topics = set()

            for _ in range(daily_count):
                topic = choice(list(templates.keys()))
                if topic in used_topics and len(used_topics) < len(templates):
                    continue
                used_topics.add(topic)

                content, sentiment = choice(templates[topic])
                tweet_id = generate_tweet_id(content + str(day_offset) + username + str(_))
                _insert_tweet(cursor, username, tweet_id, content, now, day_offset)
                total_inserted += 1

    conn.commit()
    conn.close()
    logger.info(f"✅ 数据初始化完成: 插入了 {total_inserted} 条推文，覆盖 {days} 天，{len(accounts)} 个账号")


def _insert_tweet(cursor, username: str, tweet_id: str, content: str, now: datetime, day_offset: int):
    """插入单条推文"""
    content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]
    tweet_time = now - timedelta(
        days=day_offset,
        hours=randint(0, 23),
        minutes=randint(0, 59),
    )
    first_seen = tweet_time.strftime("%Y-%m-%d %H:%M:%S")
    pub_date = tweet_time.strftime("%Y-%m-%d %H:%M:%S")
    link = f"https://x.com/{username}/status/{tweet_id}"

    try:
        cursor.execute("""
            INSERT OR IGNORE INTO tweets (tweet_id, username, content, content_hash, pub_date, link, source_instance, is_new, first_seen)
            VALUES (?, ?, ?, ?, ?, ?, 'seed_data', 0, ?)
        """, (tweet_id, username, content, content_hash, pub_date, link, first_seen))
    except sqlite3.IntegrityError:
        pass  # 跳过重复


def main():
    parser = argparse.ArgumentParser(description="x-monitor 数据初始化")
    parser.add_argument("--days", type=int, default=3, help="生成天数（默认3天）")
    parser.add_argument("--clear", action="store_true", help="清空旧数据")
    parser.add_argument("--accounts", type=str, nargs="*", help="指定账号列表")
    args = parser.parse_args()

    seed_database(days=args.days, clear=args.clear, accounts=args.accounts)

    # 打印结果
    conn = sqlite3.connect(str(DB_PATH))
    total = conn.execute("SELECT count(*) FROM tweets").fetchone()[0]
    acc_stats = conn.execute(
        "SELECT username, count(*) as cnt FROM tweets GROUP BY username ORDER BY cnt DESC"
    ).fetchall()
    date_range = conn.execute(
        "SELECT min(date(first_seen)), max(date(first_seen)) FROM tweets"
    ).fetchone()
    conn.close()

    print(f"\n[Database Overview]")
    print(f"   Total tweets: {total}")
    print(f"   Date range: {date_range[0]} ~ {date_range[1]}")
    print(f"   Accounts:")
    for acc, cnt in acc_stats:
        bar = "#" * min(cnt, 40)
        print(f"     @{acc}: {bar} {cnt}")


if __name__ == "__main__":
    main()
