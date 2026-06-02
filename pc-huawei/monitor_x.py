#!/usr/bin/env python3
"""
X/Twitter 账号监控 — 多账号推文追踪
=====================================
通过 Nitter HTML 免费获取推文，无需 API Key。
支持多实例故障转移、SQLite 持久化、变化检测、微信推送通知。

用法:
    python monitor_x.py                  # 检查所有账号一次
    python monitor_x.py --daemon 300     # 守护模式，每 300 秒轮询（systemd 用）
    python monitor_x.py --list 20        # 列出最近 20 条推文
    python monitor_x.py --stats          # 统计信息
    python monitor_x.py --daily          # 今日摘要
"""

import argparse
import json
import logging
import os
import sqlite3
import sys
import time
import hashlib
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from typing import Optional
from urllib.parse import urljoin

import re
from collections import Counter
from html.parser import HTMLParser

import feedparser
import requests

# ── 微信推送（可选依赖）────────────────────────────────────────
try:
    from wechat_notify import WeChatNotifier
    WECHAT_AVAILABLE = True
except ImportError:
    WECHAT_AVAILABLE = False

# ── 翻译模块（延迟加载，避免必装依赖） ─────────────────────────
_translator = None

def _get_translator():
    """延迟加载 Google 翻译器"""
    global _translator
    if _translator is None:
        try:
            from deep_translator import GoogleTranslator
            _translator = GoogleTranslator(source="en", target="zh-CN")
        except ImportError:
            logger.error("翻译功能需要 deep-translator 库，请运行: pip install deep-translator")
            return None
    return _translator


def translate_to_chinese(text: str) -> str:
    """将英文文本翻译为中文"""
    if not text or not text.strip():
        return ""
    translator = _get_translator()
    if translator is None:
        return "[翻译不可用]"

    try:
        # 分批处理长文本（Google 翻译单次限制 ~5000 字符）
        if len(text) <= 4000:
            return translator.translate(text)
        # 长文本分段翻译
        chunks = []
        remaining = text
        while remaining:
            chunk = remaining[:4000]
            # 尽量在句子边界断开
            if len(remaining) > 4000:
                last_period = max(chunk.rfind('. '), chunk.rfind('! '), chunk.rfind('? '))
                if last_period > 2000:
                    chunk = remaining[:last_period + 1]
            chunks.append(chunk)
            remaining = remaining[len(chunk):]
        translated = []
        for c in chunks:
            result = translator.translate(c)
            translated.append(result)
            if len(chunks) > 1:
                time.sleep(1)  # 避免频率限制
        return " ".join(translated)
    except Exception as e:
        logger.warning(f"翻译失败: {e}")
        return "[翻译失败]"


def analyze_sentiment(text: str) -> str:
    """简单情感/意图分析"""
    text_lower = text.lower()
    # 关键词检测
    positive = ["great", "best", "love", "win", "beautiful", "incredible",
                "fantastic", "amazing", "wonderful", "proud", "honor"]
    negative = ["terrible", "horrible", "disaster", "failed", "loser",
                "fake", "worst", "sad", "never", "bad", "radical"]
    urgent = ["breaking", "just in", "immediate", "emergency", "alert"]

    pos_count = sum(text_lower.count(w) for w in positive)
    neg_count = sum(text_lower.count(w) for w in negative)
    urg_count = sum(1 for w in urgent if w in text_lower)

    if urg_count > 0:
        return "⚡ 紧急"
    if pos_count > neg_count + 1:
        return "👍 正面"
    if neg_count > pos_count + 1:
        return "👎 负面"
    return "💬 一般"


def extract_topics(text: str) -> list[str]:
    """从推文中提取主题标签/关键词"""
    topics = []
    # 提取 #hashtags
    hashtags = re.findall(r'#(\w+)', text)
    topics.extend(hashtags)
    # 提取 $股票代码
    tickers = re.findall(r'\$([A-Z]{1,5})', text)
    topics.extend([f"${t}" for t in tickers])
    return topics[:5]  # 最多 5 个


# ═══════════════════════════════════════════════════════════════
#  每日摘要生成
# ═══════════════════════════════════════════════════════════════

def daily_summary(conn: sqlite3.Connection, date_str: str = None):
    """
    生成指定日期的推文摘要（中英文对照，多账号）。
    date_str 格式: YYYY-MM-DD，默认为今天。
    """
    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    rows = conn.execute("""
        SELECT username, tweet_id, content, pub_date, link, first_seen
        FROM tweets
        WHERE date(first_seen) = ?
        ORDER BY username, first_seen ASC
    """, (date_str,)).fetchall()

    if not rows:
        print(f"\n  {date_str} 无推文记录")
        return

    # 按账号分组
    from collections import defaultdict
    grouped = defaultdict(list)
    for row in rows:
        grouped[row[0]].append(row)

    total = len(rows)
    all_sentiments = Counter()
    all_topics = []

    for username, tweets in grouped.items():
        for row in tweets:
            s = analyze_sentiment(row[2])
            all_sentiments[s] += 1
            all_topics.extend(extract_topics(row[2]))

    top_topics = [t for t, _ in Counter(all_topics).most_common(5)]

    print(f"\n{'=' * 72}")
    print(f"  每日推文摘要 — {date_str}")
    print(f"{'=' * 72}")
    print(f"  监控账号: {len(grouped)} 个")
    print(f"  当日推文: {total} 条")
    print(f"  情感分布: {'  '.join(f'{k}×{v}' for k, v in all_sentiments.most_common())}")
    if top_topics:
        print(f"  热门话题: {', '.join(top_topics)}")
    print(f"{'=' * 72}")

    for username, tweets in grouped.items():
        print(f"\n{'─' * 72}")
        print(f"  @{username} — {len(tweets)} 条")
        print(f"{'─' * 72}")
        for i, row in enumerate(tweets, 1):
            sentiment = analyze_sentiment(row[2])
            print(f"\n  [{i}] {row[3] or '未知'}  {sentiment}")
            print(f"  EN: {row[2][:300]}")
            zh = translate_to_chinese(row[2])
            print(f"  ZH: {zh[:300]}")
            if row[4]:
                print(f"  🔗 {row[4]}")

    print(f"\n{'=' * 72}")
    print(f"  — 摘要完毕 —")
    print(f"{'=' * 72}\n")

# ── 配置 ────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(SCRIPT_DIR, "tweets.db")
LOG_PATH = os.path.join(SCRIPT_DIR, "monitor.log")
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# 默认监控账号（config.json 中 accounts 不存在时兜底）
DEFAULT_ACCOUNTS = ["realDonaldTrump", "elonmusk", "CathieDWood",
                     "justinsuntron", "federalreserve"]

# Nitter 实例列表（优先级从高到低，自动故障转移）
# 仅使用支持 RSS 的实例（截至 2026-06，来源: status.d420.de）
# 优先: xcancel.com (97%可用率, 355ms, 美国)
NITTER_INSTANCES = [
    "https://xcancel.com",
    "https://nitter.net",
    "https://nitter.poast.org",
    "https://nitter.privacyredirect.com",
]

# ── 日志 ────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(LOG_PATH, encoding="utf-8"),
    ],
)
logger = logging.getLogger("x-monitor")


# ── 数据库 ──────────────────────────────────────────────────
def init_db():
    """初始化 SQLite 数据库"""
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    conn.execute("""
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
    # 兼容旧表：如果 username 列不存在则添加
    try:
        conn.execute("SELECT username FROM tweets LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE tweets ADD COLUMN username TEXT NOT NULL DEFAULT 'realDonaldTrump'")
        # 重建唯一约束
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_username_tweet ON tweets(username, tweet_id)")

    conn.execute("""
        CREATE TABLE IF NOT EXISTS check_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            check_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            username TEXT DEFAULT '',
            new_count INTEGER DEFAULT 0,
            total_checked INTEGER DEFAULT 0,
            instance_used TEXT,
            duration_ms INTEGER,
            error TEXT
        )
    """)
    try:
        conn.execute("SELECT username FROM check_log LIMIT 1")
    except sqlite3.OperationalError:
        conn.execute("ALTER TABLE check_log ADD COLUMN username TEXT DEFAULT ''")

    conn.commit()
    return conn


@dataclass
class Tweet:
    tweet_id: str
    content: str
    pub_date: Optional[str] = None
    link: Optional[str] = None
    media_urls: list = field(default_factory=list)
    username: str = ""  # 关联的 X 账号


# ── 抓取 ────────────────────────────────────────────────────
def fetch_tweets_rss(username: str, timeout: int = 15) -> tuple[list[Tweet], str]:
    """
    通过 Nitter RSS 抓取推文。
    返回 (tweets, 使用的实例URL)
    自动尝试多个实例直到成功。
    """
    for instance in NITTER_INSTANCES:
        rss_url = f"{instance.rstrip('/')}/{username}/rss"
        try:
            logger.info(f"尝试 Nitter 实例: {instance}")
            resp = requests.get(rss_url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (compatible; X-Monitor/1.0)",
                "Accept": "application/rss+xml, application/xml, text/xml",
            })
            resp.raise_for_status()

            feed = feedparser.parse(resp.content)
            if not feed.entries:
                logger.warning(f"实例 {instance} 返回空内容，尝试下一个")
                continue

            tweets = []
            for entry in feed.entries:
                tweet_id = entry.get("id", "")
                if not tweet_id:
                    link = entry.get("link", "")
                    parts = link.rstrip("/").split("/")
                    tweet_id = parts[-1] if parts else hashlib.md5(link.encode()).hexdigest()[:16]

                content = entry.get("title", "") or entry.get("summary", "")

                # 跳过 Nitter RSS 占位/限流条目
                skip_phrases = [
                    "RSS reader not yet whitelisted",
                    "This browser is not supported",
                    "JavaScript is not available",
                ]
                if any(p.lower() in content.lower() for p in skip_phrases):
                    logger.debug(f"跳过 RSS 占位条目: {content[:60]}")
                    continue

                # 清理 HTML 标签
                content = content.replace("&#39;", "'").replace("&quot;", '"').replace("&amp;", "&")
                # 移除 Nitter 可能附加的 "via @username" 后缀
                if "via @" in content:
                    content = content.split("via @")[0].strip()

                tweets.append(Tweet(
                    tweet_id=str(tweet_id),
                    content=content,
                    pub_date=entry.get("published", ""),
                    link=entry.get("link", ""),
                ))

            logger.info(f"实例 {instance} 获取到 {len(tweets)} 条推文")
            return tweets, instance

        except requests.RequestException as e:
            logger.warning(f"实例 {instance} 失败: {e}")
            continue

    raise RuntimeError(f"所有 Nitter 实例均不可用，共 {len(NITTER_INSTANCES)} 个")


# ── HTML 页面抓取（主方案，Nitter RSS 经常被限流） ────────
def _extract_tweet_id(link: str) -> str:
    """从推文链接提取纯数字 ID"""
    if not link:
        return ""
    # 匹配 /status/数字 或 /i/status/数字
    m = re.search(r'/status/(\d+)', link)
    return m.group(1) if m else link


def _clean_html(text: str) -> str:
    """去除 HTML 标签，解码实体"""
    # 先去掉所有 HTML 标签
    text = re.sub(r'<[^>]+>', '', text)
    # 解码常见实体
    text = text.replace('&#39;', "'").replace('&quot;', '"').replace('&amp;', '&')
    text = text.replace('&lt;', '<').replace('&gt;', '>').replace('&nbsp;', ' ')
    text = text.replace('&apos;', "'")
    return text.strip()


def _parse_nitter_html(html: str, instance: str) -> list[Tweet]:
    """
    从 Nitter HTML 页面解析推文列表。
    Nitter 页面结构：每条推文在 .timeline-item 或 .tweet-body 中。
    使用正则提取关键字段，不依赖第三方解析库。
    """
    tweets = []
    username_pattern = re.compile(r'@(\w+)')

    # 匹配推文容器 — Nitter 的不同版本结构略有不同
    # 找 tweet-content / tweet-body / timeline-item
    tweet_blocks = re.findall(
        r'<div[^>]*class="[^"]*tweet-content[^"]*"[^>]*>(.*?)</div>\s*</div>\s*<div[^>]*class="[^"]*tweet-footer',
        html, re.DOTALL
    )
    if not tweet_blocks:
        # 备用：更宽松的匹配
        tweet_blocks = re.findall(
            r'class="tweet-content[^"]*"[^>]*>(.*?)</div>\s*</div>',
            html, re.DOTALL
        )

    # 匹配推文链接和日期
    link_matches = re.findall(
        r'<a[^>]*href="(/[^"]+/status/\d+)[^"]*"[^>]*>.*?<span[^>]*class="[^"]*tweet-date[^"]*"[^>]*>.*?title="([^"]+)"',
        html, re.DOTALL
    )
    # 更通用的匹配
    if not link_matches:
        link_matches = re.findall(
            r'href="(/[^/]+/status/\d+(?:[^"]*))"',
            html
        )
        link_matches = [(m, "") for m in link_matches]

    # 获取每条推文的媒体链接（图片/视频缩略图）
    media_urls = re.findall(
        r'<img[^>]*src="([^"]*(?:media|tweet_video_thumb|ext_tw_video_thumb)[^"]*)"',
        html
    )

    # 匹配推文文本内容
    content_matches = re.findall(
        r'class="tweet-content[^"]*"[^>]*>(.*?)</div>',
        html, re.DOTALL
    )

    for i, content_raw in enumerate(content_matches):
        content = _clean_html(content_raw)
        if not content or len(content) < 2:
            continue

        # 跳过系统消息
        skip_phrases = [
            "RSS reader not yet whitelisted",
            "This browser is not supported",
            "JavaScript is not available",
            "We've detected that JavaScript",
        ]
        if any(p.lower() in content.lower() for p in skip_phrases):
            continue

        link = ""
        if i < len(link_matches):
            link = instance.rstrip('/') + link_matches[i][0] if isinstance(link_matches[i], tuple) else link_matches[i]

        tweet_id = _extract_tweet_id(link)
        if not tweet_id:
            tweet_id = hashlib.md5(content.encode()).hexdigest()[:16]

        pub_date = link_matches[i][1] if (i < len(link_matches) and isinstance(link_matches[i], tuple) and len(link_matches[i]) > 1) else ""

        tweets.append(Tweet(
            tweet_id=tweet_id,
            content=content,
            pub_date=pub_date,
            link=link,
            media_urls=[],
        ))

    return tweets


def fetch_tweets_html(username: str, timeout: int = 15) -> tuple[list[Tweet], str]:
    """
    通过抓取 Nitter HTML 页面获取推文（主方案）。
    返回 (tweets, 使用的实例URL)
    """
    for instance in NITTER_INSTANCES:
        page_url = f"{instance.rstrip('/')}/{username}"
        try:
            logger.info(f"尝试 Nitter HTML: {instance}")
            resp = requests.get(page_url, timeout=timeout, headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                              "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml",
                "Accept-Language": "en-US,en;q=0.9",
            })
            resp.raise_for_status()

            tweets = _parse_nitter_html(resp.text, instance)
            if not tweets:
                logger.warning(f"实例 {instance} HTML 未解析到推文，尝试下一个")
                continue

            logger.info(f"实例 {instance} HTML 获取到 {len(tweets)} 条推文")
            return tweets, instance

        except requests.RequestException as e:
            logger.warning(f"实例 {instance} HTML 失败: {e}")
            continue

    raise RuntimeError(f"所有 Nitter 实例 HTML 抓取均失败")


def fetch_tweets_api(username: str, bearer_token: str, timeout: int = 15) -> list[Tweet]:
    """
    备用方案：通过 X API v2 获取推文（需要 Bearer Token）。
    适合有开发者账号的用户。
    """
    user_url = f"https://api.twitter.com/2/users/by/username/{username}"
    headers = {"Authorization": f"Bearer {bearer_token}"}

    try:
        resp = requests.get(user_url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        user_id = resp.json()["data"]["id"]

        tweets_url = f"https://api.twitter.com/2/users/{user_id}/tweets"
        params = {
            "max_results": 10,
            "tweet.fields": "created_at,entities,attachments",
            "exclude": "retweets,replies",
        }
        resp = requests.get(tweets_url, headers=headers, params=params, timeout=timeout)
        resp.raise_for_status()

        tweets = []
        for t in resp.json().get("data", []):
            tweets.append(Tweet(
                tweet_id=t["id"],
                content=t["text"],
                pub_date=t.get("created_at", ""),
                link=f"https://x.com/{username}/status/{t['id']}",
            ))
        return tweets
    except Exception as e:
        logger.error(f"X API 请求失败: {e}")
        return []


# ── 存储与检测 ──────────────────────────────────────────────
def save_and_detect(conn: sqlite3.Connection, tweets: list[Tweet], source: str) -> list[Tweet]:
    """保存推文到数据库，返回新推文列表（含 username）"""
    new_tweets = []
    cursor = conn.cursor()

    for tweet in tweets:
        content_hash = hashlib.sha256(tweet.content.encode()).hexdigest()[:16]
        username = tweet.username or "unknown"

        # 检查是否已存在（username + tweet_id 联合唯一）
        existing = cursor.execute(
            "SELECT id, content_hash FROM tweets WHERE username = ? AND tweet_id = ?",
            (username, tweet.tweet_id,)
        ).fetchone()

        if existing:
            # 已存在，检查内容是否有变化（编辑过的推文）
            if existing[1] != content_hash:
                cursor.execute("""
                    UPDATE tweets
                    SET content = ?, content_hash = ?, last_updated = CURRENT_TIMESTAMP
                    WHERE username = ? AND tweet_id = ?
                """, (tweet.content, content_hash, username, tweet.tweet_id))
                logger.info(f"[@{username}] 推文已编辑: {tweet.tweet_id[:16]}...")
            continue

        # 新推文
        media_json = json.dumps(tweet.media_urls, ensure_ascii=False) if tweet.media_urls else None
        cursor.execute("""
            INSERT INTO tweets (tweet_id, username, content, content_hash, pub_date, link, source_instance, media_urls, is_new)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, (tweet.tweet_id, username, tweet.content, content_hash, tweet.pub_date,
              tweet.link, source, media_json))
        new_tweets.append(tweet)

    conn.commit()
    return new_tweets


def update_check_log(conn: sqlite3.Connection, username: str, new_count: int, total: int,
                     instance: str, duration_ms: int, error: str = None):
    """记录检查日志"""
    conn.execute("""
        INSERT INTO check_log (username, new_count, total_checked, instance_used, duration_ms, error)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (username, new_count, total, instance, duration_ms, error))
    conn.commit()


# ── 展示 ────────────────────────────────────────────────────
def display_tweets(tweets: list[Tweet], title: str = "新推文", translate: bool = False):
    """格式化输出推文，可选中英对照"""
    if not tweets:
        print(f"\n  {title}: 无")
        return

    print(f"\n{'=' * 72}")
    print(f"  {title} ({len(tweets)} 条)")
    print(f"{'=' * 72}")

    for i, t in enumerate(tweets, 1):
        pub = t.pub_date or "未知时间"
        sentiment = analyze_sentiment(t.content)
        print(f"\n  [{i}] {pub}  {sentiment}")
        print(f"  EN: {t.content[:300]}")
        if translate:
            zh = translate_to_chinese(t.content)
            print(f"  ZH: {zh[:300]}")
        if t.link:
            print(f"  🔗 {t.link}")


def list_recent(conn: sqlite3.Connection, limit: int = 20, translate: bool = False):
    """列出数据库中最近的推文"""
    rows = conn.execute("""
        SELECT username, tweet_id, content, pub_date, link, is_new, first_seen
        FROM tweets ORDER BY first_seen DESC LIMIT ?
    """, (limit,)).fetchall()

    print(f"\n{'=' * 72}")
    print(f"  数据库最近 {len(rows)} 条推文")
    print(f"{'=' * 72}")
    for row in rows:
        tag = " [NEW]" if row[5] else ""
        sentiment = analyze_sentiment(row[2])
        print(f"\n  @{row[0]}  {row[3]}{tag}  {sentiment}")
        print(f"  EN: {row[2][:300]}")
        if translate:
            zh = translate_to_chinese(row[2])
            print(f"  ZH: {zh[:300]}")
        if row[4]:
            print(f"  🔗 {row[4]}")


def show_stats(conn: sqlite3.Connection):
    """展示统计"""
    total = conn.execute("SELECT COUNT(*) FROM tweets").fetchone()[0]
    new_count = conn.execute("SELECT COUNT(*) FROM tweets WHERE is_new = 1").fetchone()[0]
    last_check = conn.execute(
        "SELECT check_time, new_count, instance_used FROM check_log ORDER BY id DESC LIMIT 1"
    ).fetchone()

    print(f"\n{'=' * 40}")
    print(f"  X 监控统计")
    print(f"{'=' * 40}")
    print(f"  总推文数:    {total}")
    print(f"  新推文数:    {new_count}")
    if last_check:
        print(f"  上次检查:    {last_check[0]}")
        print(f"  上次新增:    {last_check[1]} 条")
        print(f"  使用实例:    {last_check[2]}")


# ── 导出 ────────────────────────────────────────────────────
def export_json(conn: sqlite3.Connection, output_path: str, limit: int = 100):
    """导出推文为 JSON"""
    rows = conn.execute("""
        SELECT tweet_id, content, pub_date, link, first_seen
        FROM tweets ORDER BY first_seen DESC LIMIT ?
    """, (limit,)).fetchall()

    data = [
        {
            "tweet_id": r[0],
            "content": r[1],
            "pub_date": r[2],
            "link": r[3],
            "first_seen": r[4],
        }
        for r in rows
    ]
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    logger.info(f"已导出 {len(data)} 条推文到 {output_path}")


# ── 主逻辑 ──────────────────────────────────────────────────
def _load_accounts() -> list[str]:
    """从 config.json 加载监控账号列表"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("accounts", DEFAULT_ACCOUNTS)
        except (json.JSONDecodeError, KeyError):
            pass
    return DEFAULT_ACCOUNTS


def _load_wechat_notifier() -> Optional[object]:
    """加载微信推送器（如果已配置）"""
    if not WECHAT_AVAILABLE:
        return None
    if not os.path.exists(CONFIG_PATH):
        return None
    try:
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            config = json.load(f)
        push_cfg = config.get("wechat_push", {})
        if push_cfg.get("enabled") and push_cfg.get("serverchan_sendkey"):
            return WeChatNotifier(config)
    except Exception:
        pass
    return None


def run_once(conn: sqlite3.Connection, use_api: bool = False,
             target_username: str = None) -> tuple[list[Tweet], str]:
    """执行一次检查（单账号），返回 (新推文列表, 错误信息或空串)"""
    start = time.time()
    instance_used = ""
    error_msg = ""
    new_tweets = []

    cfg = {}
    if os.path.exists(CONFIG_PATH):
        with open(CONFIG_PATH, "r", encoding="utf-8") as f:
            cfg = json.load(f)

    username = target_username or DEFAULT_ACCOUNTS[0]

    try:
        if use_api:
            token = cfg.get("x_bearer_token", "")
            if not token:
                return [], "未配置 X Bearer Token"
            tweets = fetch_tweets_api(username, token)
            instance_used = "X_API_v2"
        else:
            fetch_method = cfg.get("fetch_method", "html")
            if fetch_method == "rss":
                tweets, instance_used = fetch_tweets_rss(username)
            else:
                try:
                    tweets, instance_used = fetch_tweets_html(username)
                except RuntimeError:
                    logger.warning(f"[@{username}] HTML 抓取失败，尝试 RSS 备用...")
                    tweets, instance_used = fetch_tweets_rss(username)

        # 标注账号
        for t in tweets:
            t.username = username

        new_tweets = save_and_detect(conn, tweets, instance_used)
        update_check_log(conn, username, len(new_tweets), len(tweets), instance_used,
                        int((time.time() - start) * 1000))

        if new_tweets:
            logger.info(f"[@{username}] 发现 {len(new_tweets)} 条新推文")
            # 翻译新推文
            for t in new_tweets:
                try:
                    t.translated = translate_to_chinese(t.content)
                except Exception:
                    t.translated = ""
                t.sentiment = analyze_sentiment(t.content)
            new_tweets.reverse()  # 按时间正序

    except Exception as e:
        error_msg = str(e)
        logger.error(f"[@{username}] 检查失败: {error_msg}")
        update_check_log(conn, username, 0, 0, instance_used or "none",
                        int((time.time() - start) * 1000), error_msg)

    return new_tweets, error_msg


def run_daemon(conn: sqlite3.Connection, interval: int = 300, use_api: bool = False):
    """守护进程模式，轮询所有账号，集成微信推送"""
    accounts = _load_accounts()
    notifier = _load_wechat_notifier()

    logger.info(f"守护模式启动，间隔 {interval}s，监控 {len(accounts)} 个账号")
    logger.info(f"账号列表: {', '.join(accounts)}")
    if notifier:
        logger.info("微信推送: 已启用")
    else:
        logger.info("微信推送: 未配置")

    # 每账号的连续失败计数
    fail_counts = {a: 0 for a in accounts}
    max_failures = len(NITTER_INSTANCES) * 2
    last_heartbeat = 0  # 心跳时间戳

    while True:
        cycle_start = time.time()
        total_new = 0

        for username in accounts:
            try:
                new_tweets, error = run_once(conn, use_api, username)
                total_new += len(new_tweets)

                if error:
                    fail_counts[username] += 1
                    logger.warning(f"[@{username}] 第 {fail_counts[username]} 次连续失败")

                    # 连续失败 ≥ 3 且启用微信推送 → 告警
                    if fail_counts[username] >= 3 and notifier:
                        notifier.error_alert(username, error, fail_counts[username])

                    if fail_counts[username] >= max_failures:
                        logger.critical(f"[@{username}] 连续失败 {max_failures} 次，暂时跳过")
                else:
                    fail_counts[username] = 0

                    # 有新推文 + 微信推送 → 通知
                    if new_tweets and notifier:
                        tweets_data = [{
                            "content": t.content,
                            "translated": getattr(t, "translated", ""),
                            "sentiment": getattr(t, "sentiment", "💬 一般"),
                            "link": t.link or "",
                        } for t in new_tweets]
                        notifier.new_tweets_alert(username, tweets_data)

                # 标记已通知
                for t in new_tweets:
                    conn.execute(
                        "UPDATE tweets SET is_new = 0 WHERE username = ? AND tweet_id = ?",
                        (username, t.tweet_id)
                    )

                # 账号间间隔 5 秒，避免被 Nitter 限流
                time.sleep(5)

            except Exception as e:
                fail_counts[username] += 1
                logger.error(f"[@{username}] 轮询异常: {e}")
                if fail_counts[username] >= 3 and notifier:
                    notifier.error_alert(username, str(e), fail_counts[username])

        conn.commit()

        # 静默心跳（每 30 分钟发一次确认存活）
        now = time.time()
        if now - last_heartbeat > 1800:
            last_heartbeat = now
            if notifier:
                notifier.heartbeat()
            logger.info(f"💓 心跳正常 | {len(accounts)}账号 | 本轮新增{total_new}条")

        cycle_duration = time.time() - cycle_start
        sleep_time = max(interval - cycle_duration, 10)
        logger.info(f"本轮耗时 {cycle_duration:.1f}s，休眠 {sleep_time:.0f}s")
        time.sleep(sleep_time)


# ── CLI ─────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="X/Twitter 账号监控 — Trump 推文追踪",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python monitor_x.py                    # 检查一次
  python monitor_x.py --daemon 300       # 每 5 分钟检查
  python monitor_x.py --list 20          # 查看最近 20 条
  python monitor_x.py --stats            # 统计
  python monitor_x.py --export tweets.json
  python monitor_x.py --api              # 使用 X API v2（需配置 Token）
        """
    )
    parser.add_argument("--daemon", type=int, metavar="N",
                        help="守护模式，每 N 秒检查一次")
    parser.add_argument("--list", type=int, metavar="N",
                        help="列出最近 N 条推文")
    parser.add_argument("--stats", action="store_true",
                        help="显示统计信息")
    parser.add_argument("--export", type=str, metavar="PATH",
                        help="导出推文为 JSON")
    parser.add_argument("--api", action="store_true",
                        help="使用 X API v2（需要 Bearer Token）")
    parser.add_argument("--init", action="store_true",
                        help="仅初始化数据库")
    parser.add_argument("--quiet", "-q", action="store_true",
                        help="静默模式，只输出新推文")
    parser.add_argument("--translate", "-t", action="store_true",
                        help="显示中文翻译（中英对照）")
    parser.add_argument("--daily", type=str, nargs="?", metavar="DATE", const="today",
                        help="生成每日摘要（默认今天，可指定日期 YYYY-MM-DD）")

    args = parser.parse_args()

    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    conn = init_db()

    if args.init:
        logger.info(f"数据库已初始化: {DB_PATH}")
        conn.close()
        return

    if args.stats:
        show_stats(conn)
        conn.close()
        return

    if args.list:
        list_recent(conn, args.list, translate=args.translate)
        conn.close()
        return

    if args.daily:
        date_str = None if args.daily == "today" else args.daily
        daily_summary(conn, date_str)
        conn.close()
        return

    if args.export:
        export_json(conn, args.export)
        conn.close()
        return

    if args.daemon:
        try:
            run_daemon(conn, args.daemon, args.api)
        except KeyboardInterrupt:
            logger.info("收到中断信号，守护模式退出")
        finally:
            conn.close()
        return

    # 默认：单次检查所有账号
    accounts = _load_accounts()
    print(f"\n  检查 {len(accounts)} 个账号...")
    total_new = 0
    for username in accounts:
        new_tweets, error = run_once(conn, args.api, username)
        if error:
            print(f"\n  ❌ @{username}: {error}")
        else:
            display_tweets(new_tweets, f"@{username} 新推文", translate=args.translate)
            total_new += len(new_tweets)

    if total_new == 0:
        print(f"\n  所有账号无新推文")
    conn.close()


if __name__ == "__main__":
    main()
