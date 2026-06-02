#!/usr/bin/env python3
"""
微信推送通知模块
================
支持 Server酱 (ftqq.com) / PushPlus / 企业微信机器人 三种渠道。
自动故障转移：Server酱 → PushPlus → 企业微信。

配置方式 (config.json):
{
  "wechat_push": {
    "enabled": true,
    "channel": "serverchan",        // serverchan | pushplus | wecom_bot
    "serverchan_sendkey": "SCTxxxx",
    "pushplus_token": "xxx",        // 备用
    "wecom_webhook": "xxx",         // 备用
    "enable_new_tweet": true,       // 新推文通知
    "enable_error_alert": true,     // 异常告警
    "enable_daily_summary": true,   // 每日摘要通知
    "new_tweet_limit": 3            // 每次最多推送几条新推文
  }
}

获取 SendKey:
1. 打开 https://sct.ftqq.com/ 用微信登录
2. 复制 SendKey，填入 config.json 的 serverchan_sendkey
3. 关注「方糖」公众号即可接收推送
"""

import json
import logging
import time
from typing import Optional

import requests

logger = logging.getLogger("wechat")

# ── 推送渠道基类 ──────────────────────────────────────────────

class PushChannel:
    """推送渠道抽象"""
    def send(self, title: str, content: str) -> bool:
        raise NotImplementedError


class ServerChanChannel(PushChannel):
    """Server酱 (方糖) — 推荐首选，免费每日 5 条"""

    def __init__(self, sendkey: str):
        self.sendkey = sendkey
        self.api = f"https://sctapi.ftqq.com/{sendkey}.send"

    def send(self, title: str, content: str) -> bool:
        try:
            # 截断过长内容（Server酱限制 64KB）
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
    """PushPlus — 备用渠道，免费每日 200 条"""

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
            # 企业微信机器人只支持纯文本 markdown，限制 4096 字符
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


# ── 通知管理器 ────────────────────────────────────────────────

class WeChatNotifier:
    """微信通知管理器，自动故障转移"""

    def __init__(self, config: dict):
        push_cfg = config.get("wechat_push", {})
        self.enabled = push_cfg.get("enabled", False)
        self.enable_new_tweet = push_cfg.get("enable_new_tweet", True)
        self.enable_error_alert = push_cfg.get("enable_error_alert", True)
        self.enable_daily_summary = push_cfg.get("enable_daily_summary", True)
        self.new_tweet_limit = push_cfg.get("new_tweet_limit", 3)
        self.channels = []
        self._last_error_send = 0  # 防止异常告警刷屏
        self._error_cooldown = 1800  # 同类型错误 30 分钟内不重复推送

        if not self.enabled:
            logger.info("微信推送未启用")
            return

        # 按优先级注册渠道
        channel = push_cfg.get("channel", "serverchan")

        if channel == "serverchan" or push_cfg.get("serverchan_sendkey"):
            sk = push_cfg.get("serverchan_sendkey", "")
            if sk:
                self.channels.append(ServerChanChannel(sk))
                logger.info("已注册 Server酱 推送渠道")

        if channel == "pushplus" or push_cfg.get("pushplus_token"):
            pt = push_cfg.get("pushplus_token", "")
            if pt:
                self.channels.append(PushPlusChannel(pt))
                logger.info("已注册 PushPlus 推送渠道（备用）")

        if channel == "wecom_bot" or push_cfg.get("wecom_webhook"):
            wh = push_cfg.get("wecom_webhook", "")
            if wh:
                self.channels.append(WeComBotChannel(wh))
                logger.info("已注册 企业微信机器人 推送渠道（备用）")

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

    # ── 业务通知方法 ──

    def new_tweets_alert(self, username: str, tweets_data: list[dict]):
        """新推文通知"""
        if not self.enable_new_tweet or not tweets_data:
            return

        count = len(tweets_data)
        display = tweets_data[:self.new_tweet_limit]
        lines = []

        for i, t in enumerate(display, 1):
            content = t.get("content", "")
            zh = t.get("translated", "")
            sentiment = t.get("sentiment", "")
            # 推文截断 200 字
            en_text = content[:200] + ("..." if len(content) > 200 else "")
            lines.append(f"> [{i}] {sentiment}")
            lines.append(f"> {en_text}")
            if zh:
                zh_text = zh[:200] + ("..." if len(zh) > 200 else "")
                lines.append(f"> 📝 {zh_text}")
            lines.append("")

        if count > len(display):
            lines.append(f"> ... 还有 {count - len(display)} 条新推文")

        title = f"🐦 @{username} 新推文 ({count}条)"
        content = "\n".join(lines)
        self._send(title, content)

    def error_alert(self, username: str, error_msg: str, consecutive: int = 0):
        """异常告警（带防刷保护）"""
        if not self.enable_error_alert:
            return

        # 防刷：同类型错误 30 分钟内不重复推
        cache_key = username + error_msg[:50]
        now = time.time()
        if now - self._last_error_send < self._error_cooldown:
            logger.debug(f"错误告警冷却中，跳过: {error_msg[:60]}")
            return

        self._last_error_send = now
        title = f"🚨 X监控异常 @{username}"
        content = f"**错误信息:** {error_msg}"
        if consecutive:
            content += f"\n\n连续失败次数: {consecutive}"
        content += f"\n\n时间: {time.strftime('%Y-%m-%d %H:%M:%S')}"
        self._send(title, content)

    def daily_summary_push(self, date_str: str, accounts_data: list[dict]):
        """每日摘要推送"""
        if not self.enable_daily_summary or not accounts_data:
            return

        total_tweets = sum(len(a.get("tweets", [])) for a in accounts_data)
        if total_tweets == 0:
            return  # 没推文就不推了

        lines = [f"📊 **{date_str} 推文日报**", ""]
        lines.append(f"监控账号: {len(accounts_data)} 个")
        lines.append(f"当日推文: {total_tweets} 条")
        lines.append("")

        for acc in accounts_data:
            name = acc["username"]
            tweets = acc.get("tweets", [])
            sentiments = acc.get("sentiment_dist", {})
            topics = acc.get("topics", [])
            lines.append(f"---")
            lines.append(f"### @{name} — {len(tweets)} 条")
            if sentiments:
                s_str = " ".join(f"{k}×{v}" for k, v in sentiments.items())
                lines.append(f"情感: {s_str}")
            if topics:
                lines.append(f"话题: {', '.join(topics[:3])}")
            # 精选 1-2 条重点推文
            highlights = acc.get("highlights", [])
            for h in highlights[:2]:
                zh = h.get("translated", "")
                text = h.get("content", "")[:100]
                lines.append(f"> {text}...")
                if zh:
                    lines.append(f"> 📝 {zh[:100]}...")
            lines.append("")

        title = f"📊 X推文日报 {date_str} — {total_tweets}条"
        content = "\n".join(lines)
        self._send(title, content)

    def heartbeat(self):
        """心跳检测（静默模式，只记日志不推送）"""
        if not self.enabled:
            return
        logger.debug("推送渠道心跳正常")


# ── 测试 ──────────────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)

    if len(sys.argv) < 2:
        print("用法: python wechat_notify.py SCT_SENDKEY 测试推送")
        sys.exit(1)

    cfg = {
        "wechat_push": {
            "enabled": True,
            "serverchan_sendkey": sys.argv[1],
            "enable_new_tweet": True,
            "enable_error_alert": True,
            "enable_daily_summary": True,
        }
    }

    notifier = WeChatNotifier(cfg)

    # 测试新推文通知
    notifier.new_tweets_alert("realDonaldTrump", [{
        "content": "MAKE AMERICA GREAT AGAIN! #MAGA",
        "translated": "让美国再次伟大！",
        "sentiment": "👍 正面",
    }])

    # 测试异常告警
    notifier.error_alert("realDonaldTrump", "所有 Nitter 实例均超时，请检查网络", 3)

    print("推送测试完成，请检查微信")
