#!/usr/bin/env python3
"""
微信推送通知模块 v2.0 — 匹配产品原型设计
==========================================
按照 prototype.html 中的「微信推送预览」设计，重构推送消息格式。

三种推送类型：
  1. 新推文即时通知 — 优先级 + 原文 + 翻译 + 投资解读 + 信号标签 + 板块标注 + 方向标签
  2. 系统异常告警 — Nitter实例详情 + 故障转移通知 + 当前监控状态
  3. 每日情报简报 — 一句话格局 + Top3信号 + 风险预警 + 看板链接

支持渠道：Server酱 / PushPlus / 企业微信机器人，自动故障转移。

配置方式 (config.json):
{
  "wechat_push": {
    "enabled": true,
    "channel": "pushplus",
    "serverchan_sendkey": "SCTxxxx",
    "pushplus_token": "xxx",
    "wecom_webhook": "xxx",
    "enable_new_tweet": true,
    "enable_error_alert": true,
    "enable_daily_summary": true,
    "new_tweet_limit": 3,
    "daily_push_hour": 21,
    "web_dashboard_url": ""
  }
}
"""

import json
import logging
import os
import time
from collections import defaultdict
from typing import Optional

import requests

logger = logging.getLogger("wechat")

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_PATH = os.path.join(SCRIPT_DIR, "config.json")

# ═════════════════════════════════════════════════════════════
#  推送渠道基类
# ═════════════════════════════════════════════════════════════

class PushChannel:
    """推送渠道抽象"""
    def send(self, title: str, content: str) -> bool:
        raise NotImplementedError


class ServerChanChannel(PushChannel):
    """Server酱 (方糖) — 免费每日 5 条"""

    def __init__(self, sendkey: str):
        self.sendkey = sendkey
        self.api = f"https://sctapi.ftqq.com/{sendkey}.send"

    def send(self, title: str, content: str) -> bool:
        try:
            if len(content) > 60000:
                content = content[:60000] + "\n...[已截断]"
            resp = requests.post(self.api, data={
                "title": title[:256],
                "desp": content,
            }, timeout=15)
            data = resp.json()
            if data.get("code") == 0:
                logger.info(f"Server酱推送成功: {title}")
                return True
            else:
                logger.warning(f"Server酱推送失败: {data.get('message')}")
                return False
        except Exception as e:
            logger.error(f"Server酱推送异常: {e}")
            return False


class PushPlusChannel(PushChannel):
    """PushPlus — 免费每日 200 条，支持 Markdown"""

    def __init__(self, token: str):
        self.token = token
        self.api = "https://www.pushplus.plus/send"

    def send(self, title: str, content: str) -> bool:
        try:
            resp = requests.post(self.api, json={
                "token": self.token,
                "title": title[:100],
                "content": content,
                "template": "markdown",
            }, timeout=15)
            data = resp.json()
            if data.get("code") == 200:
                logger.info(f"PushPlus推送成功: {title}")
                return True
            else:
                logger.warning(f"PushPlus推送失败: {data.get('msg')}")
                return False
        except Exception as e:
            logger.error(f"PushPlus推送异常: {e}")
            return False


class WeComBotChannel(PushChannel):
    """企业微信机器人 Webhook — 最后防线"""

    def __init__(self, webhook: str):
        self.webhook = webhook

    def send(self, title: str, content: str) -> bool:
        try:
            text = f"## {title}\n\n{content}"
            if len(text) > 4000:
                text = text[:4000] + "\n...[已截断]"
            resp = requests.post(self.webhook, json={
                "msgtype": "markdown",
                "markdown": {"content": text},
            }, timeout=15)
            data = resp.json()
            if data.get("errcode") == 0:
                logger.info(f"企业微信推送成功: {title}")
                return True
            else:
                logger.warning(f"企业微信推送失败: {data.get('errmsg')}")
                return False
        except Exception as e:
            logger.error(f"企业微信推送异常: {e}")
            return False


# ═════════════════════════════════════════════════════════════
#  防刷保护 — Rate Limiter
# ═════════════════════════════════════════════════════════════

class RateLimiter:
    """
    推送防刷保护。
    规则：
      - 同一账号每分钟最多 1 条新推文推送
      - 全渠道 5 分钟内最多 3 条推送
      - 同类错误 30 分钟内不重复推送
      - 心跳类 30 分钟冷却
      - 每日摘要 23 小时冷却
    """

    def __init__(self):
        self._account_push_times = defaultdict(list)  # account -> [timestamp, ...]
        self._global_push_times = []  # [timestamp, ...]
        self._category_last = {}  # category -> timestamp

    def can_push_tweet(self, username: str) -> bool:
        """检查某账号是否可以推送新推文"""
        now = time.time()
        # 同账号 1 分钟冷却
        times = self._account_push_times[username]
        times[:] = [t for t in times if now - t < 60]
        if times:
            return False
        # 全局 5 分钟内最多 3 条
        self._global_push_times[:] = [t for t in self._global_push_times if now - t < 300]
        if len(self._global_push_times) >= 3:
            return False
        return True

    def record_tweet_push(self, username: str):
        """记录一次新推文推送"""
        now = time.time()
        self._account_push_times[username].append(now)
        self._global_push_times.append(now)

    def can_push_category(self, category: str, cooldown: float = 1800) -> bool:
        """检查某类消息是否在冷却期"""
        now = time.time()
        last = self._category_last.get(category, 0)
        if now - last < cooldown:
            return False
        return True

    def record_category_push(self, category: str):
        """记录一次分类推送"""
        self._category_last[category] = time.time()


# ═════════════════════════════════════════════════════════════
#  通知管理器 v2.0
# ═════════════════════════════════════════════════════════════

class WeChatNotifier:
    """微信通知管理器 v2.0 — 匹配产品原型设计"""

    def __init__(self, config: dict):
        push_cfg = config.get("wechat_push", {})
        self.enabled = push_cfg.get("enabled", False)
        self.enable_new_tweet = push_cfg.get("enable_new_tweet", True)
        self.enable_error_alert = push_cfg.get("enable_error_alert", True)
        self.enable_daily_summary = push_cfg.get("enable_daily_summary", True)
        self.new_tweet_limit = push_cfg.get("new_tweet_limit", 3)
        self.daily_push_hour = push_cfg.get("daily_push_hour", 21)
        self.web_dashboard_url = push_cfg.get("web_dashboard_url", "")
        self.channels = []
        self.limiter = RateLimiter()

        if not self.enabled:
            logger.info("微信推送未启用")
            return

        # 按优先级注册渠道
        channel = push_cfg.get("channel", "pushplus")

        if channel == "serverchan" or push_cfg.get("serverchan_sendkey"):
            sk = push_cfg.get("serverchan_sendkey", "")
            if sk:
                self.channels.append(ServerChanChannel(sk))
                logger.info("已注册 Server酱 推送渠道")

        if channel == "pushplus" or push_cfg.get("pushplus_token"):
            pt = push_cfg.get("pushplus_token", "")
            if pt:
                self.channels.append(PushPlusChannel(pt))
                logger.info("已注册 PushPlus 推送渠道")

        if channel == "wecom_bot" or push_cfg.get("wecom_webhook"):
            wh = push_cfg.get("wecom_webhook", "")
            if wh:
                self.channels.append(WeComBotChannel(wh))
                logger.info("已注册 企业微信机器人 推送渠道")

        if not self.channels:
            logger.warning("微信推送已启用但无有效渠道配置！")
            self.enabled = False

    def _send(self, title: str, content: str) -> bool:
        """通过可用渠道发送，自动故障转移"""
        if not self.enabled or not self.channels:
            return False

        for ch in self.channels:
            if ch.send(title, content):
                return True
            time.sleep(1)  # 渠道间隔

        logger.error("所有推送渠道均失败")
        return False

    # ── 1. 新推文即时通知 ────────────────────────────────────

    def new_tweets_alert(self, username: str, tweets_data: list[dict]):
        """
        新推文即时通知 — 匹配原型设计

        原型格式：
          🔴 高优先级信号
          @username · 刚刚
          "English original..."  (灰色小字)
          中文翻译 + 投资解读摘要 (红色高亮)
          [关税/贸易] [出口贸易] [利好]

        tweets_data 字段：
          - content: 英文原文
          - translated: 中文翻译
          - sentiment: 情感标签
          - priority: "high"/"medium"/"low" (新增)
          - interpretation: 投资解读 (新增)
          - signal_tags: 信号标签列表 (新增)
          - sector_tags: 板块标签列表 (新增)
          - direction: "bullish"/"bearish"/"neutral" (新增)
        """
        if not self.enable_new_tweet or not tweets_data:
            return

        # 防刷检查
        if not self.limiter.can_push_tweet(username):
            logger.debug(f"推送冷却中，跳过 @{username}")
            return

        count = len(tweets_data)
        display = tweets_data[:self.new_tweet_limit]

        # 只推送高优先级和中优先级
        high_priority = [t for t in display if t.get("priority") in ("high", "medium")]
        if not high_priority:
            # 低优先级不推送，记日志
            logger.info(f"@{username} {count}条低优先级推文，跳过推送")
            return

        lines = []

        for i, t in enumerate(high_priority, 1):
            priority = t.get("priority", "medium")
            priority_icon = "🔴" if priority == "high" else "🟡" if priority == "medium" else "⚪"
            priority_text = "高优先级信号" if priority == "high" else "中优先级信号" if priority == "medium" else "低优先级"

            lines.append(f"### {priority_icon} {priority_text}")
            lines.append(f"@{username} · 刚刚")
            lines.append("")

            # 英文原文（灰色风格用引用块模拟）
            content = t.get("content", "")
            en_text = content[:200] + ("..." if len(content) > 200 else "")
            lines.append(f"> *{en_text}*")
            lines.append("")

            # 中文翻译
            zh = t.get("translated", "")
            if zh:
                zh_text = zh[:200] + ("..." if len(zh) > 200 else "")
                lines.append(f"📝 {zh_text}")
                lines.append("")

            # 投资解读（核心新增 — 蓝色高亮）
            interpretation = t.get("interpretation", "")
            if interpretation:
                interp_text = interpretation[:300] + ("..." if len(interpretation) > 300 else "")
                lines.append(f"💡 **解读：** {interp_text}")
                lines.append("")

            # 信号标签 + 板块标签 + 方向标签
            tags_line_parts = []

            for tag in t.get("signal_tags", [])[:2]:
                tags_line_parts.append(f"`{tag}`")

            for tag in t.get("sector_tags", [])[:2]:
                tags_line_parts.append(f"`{tag}`")

            direction = t.get("direction", "neutral")
            dir_map = {"bullish": "📈利好", "bearish": "📉利空", "neutral": "➡️中性"}
            dir_text = dir_map.get(direction, "➡️中性")
            tags_line_parts.append(f"**{dir_text}**")

            if tags_line_parts:
                lines.append(" ".join(tags_line_parts))

            lines.append("---")

        if count > len(high_priority):
            lines.append(f"还有 {count - len(high_priority)} 条推文，详见Web看板")

        # 看板链接
        if self.web_dashboard_url:
            lines.append(f"\n[📱 查看完整看板]({self.web_dashboard_url})")

        title = f"🐦 @{username} 新推文 ({len(high_priority)}条信号)"
        content = "\n".join(lines)

        self.limiter.record_tweet_push(username)
        self._send(title, content)

    # ── 2. 系统异常告警 ──────────────────────────────────────

    def error_alert(self, username: str, error_msg: str, consecutive: int = 0,
                    instance_info: dict = None):
        """
        系统异常告警 — 匹配原型设计

        原型格式：
          ⚠️ 监控异常告警
          Nitter实例 xcancel.com 返回异常，已自动切换至 nitter.net
          最近1小时内发生 2次 故障转移。当前监控仍正常运行。

        新增参数：
          - instance_info: {"failed": "xcancel.com", "switched_to": "nitter.net",
                            "failover_count_hour": 2, "monitoring_ok": True}
        """
        if not self.enable_error_alert:
            return

        # 防刷保护
        cache_key = f"error_{username}_{error_msg[:30]}"
        if not self.limiter.can_push_category(cache_key, cooldown=1800):
            logger.debug(f"错误告警冷却中，跳过: {error_msg[:60]}")
            return

        lines = []
        lines.append("### ⚠️ 监控异常告警")
        lines.append("")

        if instance_info:
            failed = instance_info.get("failed", "")
            switched = instance_info.get("switched_to", "")
            failover_count = instance_info.get("failover_count_hour", 0)
            monitoring_ok = instance_info.get("monitoring_ok", True)

            if failed and switched:
                lines.append(f"Nitter实例 **{failed}** 返回异常，已自动切换至 **{switched}**")
            elif failed:
                lines.append(f"Nitter实例 **{failed}** 返回异常")
            else:
                lines.append(f"**错误信息:** {error_msg}")

            if failover_count > 0:
                lines.append(f"")
                lines.append(f"最近1小时内发生 **{failover_count}次** 故障转移。")

            if monitoring_ok:
                lines.append(f"当前监控仍**正常运行**。")
            else:
                lines.append(f"⚠️ 当前监控**已中断**，请尽快手动处理！")

        else:
            lines.append(f"**错误信息:** {error_msg}")

        if consecutive:
            lines.append(f"")
            lines.append(f"连续失败次数: **{consecutive}**")

        lines.append(f"\n🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}")

        # 排查建议
        lines.append(f"\n---")
        lines.append(f"排查命令：")
        lines.append(f"```bash")
        lines.append(f"systemctl status x-monitor")
        lines.append(f"journalctl -u x-monitor -n 20 --no-pager")
        lines.append(f"```")

        title = f"🚨 X监控异常 @{username}"
        content = "\n".join(lines)

        self.limiter.record_category_push(cache_key)
        self._send(title, content)

    # ── 3. 每日情报简报 ──────────────────────────────────────

    def daily_summary_push(self, date_str: str, summary_data: dict):
        """
        每日情报简报 — 匹配原型设计

        原型格式：
          📚 每日情报简报
          2026年6月1日 星期一
          ◆ 一句话格局
          特朗普对华关税软化+马斯克FSD入华+AI开源，整体对A股偏暖。
          ---
          🔴 Top 3 信号
          1. 特朗普释放贸易谈判积极信号 → 出口贸易 利好
          2. 马斯克FSD 13.0下周入华 → 新能源/电动车 利好
          3. Grok-4开源 → AI/大模型 利好
          ---
          ⚠️ 风险预警
          AI竞争格局不确定性 | 通胀数据反复风险 | 中美谈判不确定性
          ---
          点击查看完整看板 →

        summary_data 字段：
          - one_line_summary: 一句话格局
          - top_signals: [{"signal": "...", "sectors": ["..."], "direction": "bullish"}, ...]
          - risk_warnings: ["...", ...]
          - total_tweets: int
          - active_accounts: int
        """
        if not self.enable_daily_summary or not summary_data:
            return

        # 冷却检查
        if not self.limiter.can_push_category("daily_summary", cooldown=82800):
            return

        lines = []
        lines.append("### 📚 每日情报简报")
        lines.append(f"**{date_str}**")
        lines.append("")

        # 一句话格局
        one_line = summary_data.get("one_line_summary", "今日无重大信号。")
        lines.append("**◆ 一句话格局**")
        lines.append(f"{one_line}")
        lines.append("")

        # 数据概览
        total = summary_data.get("total_tweets", 0)
        active = summary_data.get("active_accounts", 0)
        if total > 0:
            lines.append(f"📊 当日推文 {total} 条 | 监控账号 {active} 个")
            lines.append("")

        # Top 3-5 信号
        top_signals = summary_data.get("top_signals", [])
        if top_signals:
            lines.append("---")
            lines.append("**🔴 Top 信号**")
            for i, sig in enumerate(top_signals[:5], 1):
                signal_text = sig.get("signal", "")
                sectors = sig.get("sectors", [])
                direction = sig.get("direction", "neutral")

                dir_map = {"bullish": "📈利好", "bearish": "📉利空", "neutral": "➡️中性"}
                dir_text = dir_map.get(direction, "➡️中性")
                sector_str = "、".join(sectors[:2]) if sectors else "待观察"

                lines.append(f"{i}. {signal_text} → {sector_str} **{dir_text}**")
            lines.append("")

        # 板块影响概览
        sector_overview = summary_data.get("sector_overview", [])
        if sector_overview:
            lines.append("---")
            lines.append("**📊 板块影响概览**")
            for s in sector_overview[:6]:
                dir_map = {"bullish": "📈", "bearish": "📉", "neutral": "➡️"}
                icon = dir_map.get(s.get("direction", "neutral"), "➡️")
                lines.append(f"{icon} {s['name']}: {s.get('summary', '无信号')}")
            lines.append("")

        # 风险预警
        risks = summary_data.get("risk_warnings", [])
        if risks:
            lines.append("---")
            lines.append("**⚠️ 风险预警**")
            lines.append(" | ".join(risks[:5]))
            lines.append("")

        # 看板链接
        lines.append("---")
        if self.web_dashboard_url:
            lines.append(f"[📱 点击查看完整看板]({self.web_dashboard_url})")
        else:
            lines.append("查看完整看板 → Web Dashboard")

        title = f"📊 每日情报简报 {date_str} — {total}条信号"
        content = "\n".join(lines)

        self.limiter.record_category_push("daily_summary")
        self._send(title, content)

    # ── 4. 心跳 ──────────────────────────────────────────────

    def heartbeat(self, status_data: dict = None):
        """心跳通知 — 静默模式，仅确认服务存活"""
        if not self.enabled:
            return

        if not self.limiter.can_push_category("heartbeat", cooldown=1800):
            logger.debug("心跳冷却中，跳过")
            return

        if not status_data:
            status_data = {}

        total = status_data.get("total_tweets", "?")
        accounts = status_data.get("active_accounts", "?")
        disk = status_data.get("disk_free", "?")
        db_ok = status_data.get("db_healthy", True)

        status_icon = "✅" if db_ok else "⚠️"
        lines = [
            f"### 💚 系统心跳 {status_icon}",
            f"",
            f"监控账号: {accounts} 个",
            f"推文总数: {total} 条",
            f"磁盘剩余: {disk}",
            f"数据库: {'正常' if db_ok else '异常'}",
            f"",
            f"🕐 {time.strftime('%H:%M:%S')}",
        ]

        title = f"💚 心跳正常"
        content = "\n".join(lines)

        self.limiter.record_category_push("heartbeat")
        self._send(title, content)

    # ── 5. 自愈通知 ──────────────────────────────────────────

    def auto_heal_notify(self, service_name: str, heal_result: dict):
        """自愈通知 — 服务异常后自动重启成功"""
        if not self.enabled:
            return

        if not self.limiter.can_push_category(f"autoheal_{service_name}", cooldown=60):
            return

        success = heal_result.get("restart_success", False)
        icon = "🔧" if success else "❌"
        status = "已恢复" if success else "仍异常"

        lines = [
            f"### {icon} 自愈{status}: {service_name}",
            f"",
            f"服务 {service_name} 检测到异常，已自动重启",
            f"重启结果: **{status}**",
            f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}",
        ]

        title = f"🔧 自愈{status}: {service_name}"
        content = "\n".join(lines)

        self.limiter.record_category_push(f"autoheal_{service_name}")
        self._send(title, content)


# ═════════════════════════════════════════════════════════════
#  辅助函数 — 生成推送数据
# ═════════════════════════════════════════════════════════════

def build_tweet_push_data(tweet, username: str = "") -> dict:
    """
    从推文对象构建推送所需的数据字典。
    集成信号提取和板块映射。

    Args:
        tweet: Tweet 对象（需有 content, translated, sentiment 属性）
        username: 账号名

    Returns:
        推送数据字典
    """
    content = getattr(tweet, "content", "")
    translated = getattr(tweet, "translated", "")
    sentiment = getattr(tweet, "sentiment", "💬 一般")

    # 信号提取
    signal_tags = []
    sector_tags = []
    direction = "neutral"
    interpretation = ""
    priority = "low"

    try:
        from web_server import extract_signals
        signals = extract_signals(content)
        if signals:
            signal_tags = [s["category"] for s in signals[:3]]
            # 优先级：取最高信号优先级
            max_pri = max(s["priority"] for s in signals)
            if max_pri >= 9:
                priority = "high"
            elif max_pri >= 7:
                priority = "medium"
    except ImportError:
        signals = []

    # 板块映射
    try:
        from sector_mapper import map_to_sectors, generate_investment_interpretation
        if signals:
            sectors = map_to_sectors(signals, content)
            if sectors:
                sector_tags = [s["sector"] for s in sectors[:3]]
                direction = sectors[0].get("direction", "neutral")
                # 中文方向映射
                dir_cn = {"bullish": "利好", "bearish": "利空", "neutral": "中性"}
                interpretation = generate_investment_interpretation(
                    content, signals, sectors, username
                )
    except ImportError:
        pass

    return {
        "content": content,
        "translated": translated,
        "sentiment": sentiment,
        "priority": priority,
        "interpretation": interpretation,
        "signal_tags": signal_tags,
        "sector_tags": sector_tags,
        "direction": direction,
    }


def build_daily_summary_data(conn, date_str: str = None) -> dict:
    """
    构建每日情报简报所需的数据。

    Args:
        conn: SQLite 连接
        date_str: 日期字符串 YYYY-MM-DD

    Returns:
        summary_data 字典
    """
    from datetime import datetime, timedelta

    if date_str is None:
        date_str = datetime.now().strftime("%Y-%m-%d")

    # 当日推文
    rows = conn.execute("""
        SELECT username, content, pub_date, link, first_seen
        FROM tweets
        WHERE date(first_seen) = ?
        ORDER BY first_seen ASC
    """, (date_str,)).fetchall()

    if not rows:
        return {
            "one_line_summary": f"{date_str} 无推文记录。",
            "top_signals": [],
            "risk_warnings": [],
            "total_tweets": 0,
            "active_accounts": 0,
            "sector_overview": [],
        }

    # 按账号分组统计
    account_counts = defaultdict(int)
    all_signals = []
    all_sectors = []
    all_risks = []
    sector_direction_map = defaultdict(lambda: {"bullish": 0, "bearish": 0, "neutral": 0})

    try:
        from web_server import extract_signals
        from sector_mapper import map_to_sectors
        has_engines = True
    except ImportError:
        has_engines = False

    for row in rows:
        username, content, pub_date, link, first_seen = row
        account_counts[username] += 1

        if not has_engines:
            continue

        signals = extract_signals(content)
        sectors = map_to_sectors(signals, content)

        for sig in signals:
            all_signals.append({
                "username": username,
                "signal": sig["category"],
                "priority": sig["priority"],
                "content_preview": content[:80],
            })

            # 风险关键词检测
            danger_words = ["war", "sanction", "ban", "crash", "crisis",
                          "restrict", "decouple", "threat", "retaliate"]
            for dw in danger_words:
                if dw in content.lower():
                    risk_desc = f"{sig['category']}相关风险"
                    if risk_desc not in all_risks:
                        all_risks.append(risk_desc)

        for sec in sectors:
            sec_name = sec["sector"]
            sec_dir = sec.get("direction", "neutral")
            sector_direction_map[sec_name][sec_dir] += 1
            all_sectors.append(sec)

    # 一句话格局 — 基于信号汇总
    one_line = _generate_one_line_summary(all_signals, sector_direction_map)

    # Top 信号
    top_signals = _rank_signals(all_signals)

    # 板块概览
    sector_overview = _build_sector_overview(sector_direction_map)

    return {
        "one_line_summary": one_line,
        "top_signals": top_signals,
        "risk_warnings": all_risks[:5],
        "total_tweets": len(rows),
        "active_accounts": len(account_counts),
        "sector_overview": sector_overview,
    }


def _generate_one_line_summary(signals: list, sector_dirs: dict) -> str:
    """生成一句话格局总结"""
    if not signals:
        return "今日无重大投资信号，市场平淡。"

    # 统计信号类别
    sig_counts = defaultdict(int)
    for s in signals:
        sig_counts[s["signal"]] += 1

    top_cats = sorted(sig_counts.items(), key=lambda x: -x[1])[:3]
    cat_names = [c[0] for c in top_cats]

    # 判断整体方向
    bullish_count = sum(v.get("bullish", 0) for v in sector_dirs.values())
    bearish_count = sum(v.get("bearish", 0) for v in sector_dirs.values())

    if bullish_count > bearish_count * 2:
        direction = "整体对A股偏暖"
    elif bearish_count > bullish_count * 2:
        direction = "整体对A股偏冷"
    elif bullish_count > bearish_count:
        direction = "整体偏暖但需谨慎"
    else:
        direction = "多空交织，方向不明"

    parts = "、".join(cat_names)
    return f"今日{parts}相关信号活跃，{direction}。"


def _rank_signals(signals: list) -> list:
    """对信号排序，返回 Top 信号"""
    # 按优先级×出现次数排序
    sig_score = defaultdict(lambda: {"priority": 0, "count": 0, "examples": []})
    for s in signals:
        key = (s["username"], s["signal"])
        sig_score[key]["priority"] = max(sig_score[key]["priority"], s["priority"])
        sig_score[key]["count"] += 1
        if not sig_score[key]["examples"]:
            sig_score[key]["examples"].append(s["content_preview"])

    ranked = sorted(sig_score.items(), key=lambda x: -(x[1]["priority"] * x[1]["count"]))

    result = []
    for (username, signal), info in ranked[:5]:
        result.append({
            "signal": f"@{username} {signal}相关",
            "sectors": [],  # 将在后续填充
            "direction": "bullish" if info["priority"] >= 8 else "neutral",
        })

    return result


def _build_sector_overview(sector_dirs: dict) -> list:
    """构建板块影响概览"""
    overview = []
    for name, dirs in sector_dirs.items():
        total = sum(dirs.values())
        if total == 0:
            continue

        if dirs["bullish"] > dirs["bearish"]:
            direction = "bullish"
            summary = "利好"
        elif dirs["bearish"] > dirs["bullish"]:
            direction = "bearish"
            summary = "利空"
        else:
            direction = "neutral"
            summary = "待观察"

        overview.append({
            "name": name,
            "direction": direction,
            "summary": f"{summary}({total}次提及)",
        })

    overview.sort(key=lambda x: -sum(sector_dirs[x["name"]].values()))
    return overview


# ═════════════════════════════════════════════════════════════
#  测试
# ═════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("用法: python wechat_notify.py <pushplus_token|sct_sendkey> [channel]")
        print("  channel: pushplus (默认) | serverchan | wecom")
        sys.exit(1)

    token = sys.argv[1]
    channel = sys.argv[2] if len(sys.argv) > 2 else "pushplus"

    cfg = {
        "wechat_push": {
            "enabled": True,
            "channel": channel,
            "pushplus_token": token if channel == "pushplus" else "",
            "serverchan_sendkey": token if channel == "serverchan" else "",
            "wecom_webhook": token if channel == "wecom" else "",
            "enable_new_tweet": True,
            "enable_error_alert": True,
            "enable_daily_summary": True,
            "new_tweet_limit": 3,
            "daily_push_hour": 21,
            "web_dashboard_url": "http://your-server:8080",
        }
    }

    notifier = WeChatNotifier(cfg)

    # 测试1: 新推文通知（匹配原型格式）
    print("\n--- 测试1: 新推文即时通知 ---")
    notifier.new_tweets_alert("realDonaldTrump", [{
        "content": "Just had a great call with China's leadership. We're making real progress on trade. Big things coming!",
        "translated": "刚刚与中国领导层进行了很棒的沟通。我们在贸易方面取得了实质性进展，大事即将发生！",
        "sentiment": "👍 正面",
        "priority": "high",
        "interpretation": "特朗普罕见使用\"great\"\"real progress\"等正面词汇，与此前强硬关税措辞形成明显反差。这可能是中美贸易谈判窗口重新打开的信号，对A股出口贸易板块是潜在利好。",
        "signal_tags": ["关税/贸易"],
        "sector_tags": ["出口贸易"],
        "direction": "bullish",
    }])

    # 测试2: 系统异常告警（匹配原型格式）
    print("\n--- 测试2: 系统异常告警 ---")
    notifier.error_alert(
        "realDonaldTrump",
        "Nitter实例 xcancel.com 返回异常",
        consecutive=2,
        instance_info={
            "failed": "xcancel.com",
            "switched_to": "nitter.net",
            "failover_count_hour": 2,
            "monitoring_ok": True,
        }
    )

    # 测试3: 每日情报简报（匹配原型格式）
    print("\n--- 测试3: 每日情报简报 ---")
    notifier.daily_summary_push("2026年6月5日 星期四", {
        "one_line_summary": "特朗普对华关税软化+马斯克FSD入华+AI开源，整体对A股偏暖。",
        "top_signals": [
            {"signal": "特朗普释放贸易谈判积极信号", "sectors": ["出口贸易"], "direction": "bullish"},
            {"signal": "马斯克FSD 13.0下周入华", "sectors": ["新能源/电动车"], "direction": "bullish"},
            {"signal": "Grok-4开源", "sectors": ["AI/大模型"], "direction": "bullish"},
        ],
        "risk_warnings": [
            "AI竞争格局不确定性",
            "通胀数据反复风险",
            "中美谈判不确定性",
        ],
        "total_tweets": 28,
        "active_accounts": 5,
        "sector_overview": [
            {"name": "新能源/电动车", "direction": "bullish", "summary": "利好(2次提及)"},
            {"name": "AI/大模型", "direction": "bullish", "summary": "利好(2次提及)"},
            {"name": "出口贸易", "direction": "bullish", "summary": "利好(1次提及)"},
            {"name": "数字货币", "direction": "bullish", "summary": "利好(2次提及)"},
        ],
    })

    print("\n推送测试完成，请检查微信")
