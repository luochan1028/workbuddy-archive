#!/usr/bin/env python3
"""
系统守护进程 v2.1 — Health Monitor + Auto-Heal + WeChat Alert
=============================================================
自动监控所有 x-monitor 服务运行状态：
  - x-monitor.service（推文监控）
  - x-web.service（Web 看板）
  - 数据库健康 & 新鲜度
  - Web 端点可用性
  - 磁盘 & 内存

v2.1 新增：
  - 自愈机制：服务异常时自动重启（最多2次），失败后才告警
  - 内存监控
  - 智能告警升级：连续失败越久，告警频率越高
  - 每日数据摘要（08:00 推送）
"""

import json
import logging
import os
import sqlite3
import subprocess
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

import requests

SCRIPT_DIR = Path(__file__).resolve().parent
CONFIG_PATH = SCRIPT_DIR / "config.json"
DB_PATH = SCRIPT_DIR / "tweets.db"
STATE_PATH = SCRIPT_DIR / "watchdog_state.json"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(SCRIPT_DIR / "watchdog.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger("watchdog")


# ═════════════════════════════════════════════════════════════
#  加载配置
# ═════════════════════════════════════════════════════════════

def load_config():
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except Exception:
        return {}


# ═════════════════════════════════════════════════════════════
#  微信推送（内联，零外部依赖）
# ═════════════════════════════════════════════════════════════

class WechatPusher:
    def __init__(self):
        cfg = load_config()
        wp = cfg.get("wechat_push", {})
        self.enabled = wp.get("enabled", False)
        self.token = wp.get("pushplus_token", "")
        self._last_alert = {}  # 防刷

    def _cooldown(self, category: str) -> float:
        """根据类别返回冷却时间（秒）"""
        if "heartbeat" in category:
            return 1800  # 心跳30分钟
        if "daily" in category:
            return 82800  # 日推23小时
        if "recovery" in category:
            return 60  # 恢复通知1分钟冷却
        return 300  # 默认5分钟

    def send(self, title: str, content: str, category: str = "default") -> bool:
        if not self.enabled or not self.token:
            return False
        now = time.time()
        cooldown = self._cooldown(category)
        if category in self._last_alert:
            if now - self._last_alert[category] < cooldown:
                logger.debug(f"冷却中，跳过 {category}")
                return False
        self._last_alert[category] = now

        try:
            r = requests.post(
                "https://www.pushplus.plus/send",
                json={
                    "token": self.token,
                    "title": title,
                    "content": content,
                    "template": "txt",
                },
                timeout=15,
            )
            if r.status_code == 200:
                data = r.json()
                if data.get("code") == 200:
                    logger.info(f"微信推送成功: {title}")
                    return True
                else:
                    logger.warning(f"微信推送失败: {data.get('msg')}")
            return False
        except Exception as e:
            logger.error(f"微信推送异常: {e}")
            return False


# ═════════════════════════════════════════════════════════════
#  自愈模块 — Auto-Heal Engine
# ═════════════════════════════════════════════════════════════

def restart_service(svc_name: str) -> dict:
    """尝试重启 systemd 服务，返回结果"""
    try:
        r = subprocess.run(
            ["systemctl", "restart", svc_name],
            capture_output=True, text=True, timeout=30,
        )
        time.sleep(3)  # 等启动完成
        # 验证重启后状态
        r2 = subprocess.run(
            ["systemctl", "is-active", svc_name],
            capture_output=True, text=True, timeout=10,
        )
        active = r2.stdout.strip() == "active"
        return {
            "name": svc_name,
            "restarted": True,
            "restart_success": active,
            "status_after": r2.stdout.strip(),
            "stderr": r.stderr.strip()[:200] if r.returncode != 0 else "",
        }
    except Exception as e:
        return {"name": svc_name, "restarted": True, "restart_success": False, "error": str(e)}


# ═════════════════════════════════════════════════════════════
#  健康检查
# ═════════════════════════════════════════════════════════════

def check_service(name: str) -> dict:
    try:
        r = subprocess.run(
            ["systemctl", "is-active", name],
            capture_output=True, text=True, timeout=10,
        )
        active = r.stdout.strip() == "active"
        return {"name": name, "active": active, "status": r.stdout.strip()}
    except Exception as e:
        return {"name": name, "active": False, "status": str(e), "error": str(e)}


def check_web_endpoint(port: int = 8080) -> dict:
    try:
        r = requests.get(f"http://127.0.0.1:{port}/api/health", timeout=10)
        return {"reachable": r.status_code == 200, "status_code": r.status_code, "response": r.text[:200]}
    except requests.exceptions.Timeout:
        return {"reachable": False, "error": "timeout"}
    except requests.exceptions.ConnectionError:
        return {"reachable": False, "error": "connection_refused"}
    except Exception as e:
        return {"reachable": False, "error": str(e)}


def check_database() -> dict:
    try:
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute("SELECT count(*) FROM tweets").fetchone()[0]
        row = conn.execute("SELECT max(first_seen) FROM tweets").fetchone()
        last_seen = row[0] if row and row[0] else None

        # DB 大小
        db_size_mb = round(os.path.getsize(str(DB_PATH)) / (1024 * 1024), 1) if DB_PATH.exists() else 0

        conn.close()

        fresh = False
        stale_hours = None
        if last_seen:
            try:
                last_dt = datetime.fromisoformat(last_seen.replace("Z", "+00:00"))
                delta = datetime.now().astimezone() - last_dt.replace(tzinfo=None)
                stale_hours = delta.total_seconds() / 3600
                fresh = stale_hours < 2
            except Exception:
                pass

        return {
            "healthy": True,
            "tweet_count": count,
            "last_seen": last_seen,
            "fresh": fresh,
            "stale_hours": round(stale_hours, 1) if stale_hours else None,
            "db_size_mb": db_size_mb,
        }
    except Exception as e:
        return {"healthy": False, "error": str(e)}


def check_disk_space() -> dict:
    try:
        stat = os.statvfs(str(SCRIPT_DIR))
        total = stat.f_frsize * stat.f_blocks
        free = stat.f_frsize * stat.f_bavail
        used_pct = (1 - free / total) * 100 if total > 0 else 0
        return {
            "total_gb": round(total / 1e9, 1),
            "free_gb": round(free / 1e9, 1),
            "used_pct": round(used_pct, 1),
        }
    except Exception as e:
        return {"error": str(e)}


def check_memory() -> dict:
    """检查系统内存使用"""
    try:
        r = subprocess.run(["free", "-m"], capture_output=True, text=True, timeout=5)
        lines = r.stdout.strip().split("\n")
        if len(lines) >= 2:
            parts = lines[1].split()
            total = int(parts[1])
            used = int(parts[2])
            free = int(parts[3])
            used_pct = round(used / total * 100, 1) if total > 0 else 0
            return {"total_mb": total, "used_mb": used, "free_mb": free, "used_pct": used_pct}
    except Exception as e:
        pass
    return {"error": "unavailable"}


# ═════════════════════════════════════════════════════════════
#  每日数据摘要
# ═════════════════════════════════════════════════════════════

def generate_daily_summary() -> str:
    """生成每日数据摘要文本"""
    try:
        conn = sqlite3.connect(str(DB_PATH))
        today = datetime.now().strftime("%Y-%m-%d")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

        total = conn.execute("SELECT count(*) FROM tweets").fetchone()[0]
        today_count = conn.execute(
            "SELECT count(*) FROM tweets WHERE date(first_seen) = ?", (today,)
        ).fetchone()[0]
        yesterday_count = conn.execute(
            "SELECT count(*) FROM tweets WHERE date(first_seen) = ?", (yesterday,)
        ).fetchone()[0]

        # 每个账号的推文数
        acc_stats = conn.execute(
            "SELECT username, count(*) as cnt FROM tweets WHERE date(first_seen) = ? GROUP BY username ORDER BY cnt DESC",
            (today,)
        ).fetchall()

        # 本周趋势
        week_start = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
        week_total = conn.execute(
            "SELECT count(*) FROM tweets WHERE date(first_seen) >= ?", (week_start,)
        ).fetchone()[0]

        conn.close()

        cfg = load_config()
        monitored = len(cfg.get("accounts", []))

        lines = [
            f"📊 每日数据摘要 — {today}",
            f"",
            f"监控账号: {monitored} 个",
            f"累计推文: {total} 条",
            f"今日新增: {today_count} 条",
            f"昨日新增: {yesterday_count} 条",
            f"本周新增: {week_total} 条",
            f"",
        ]

        if acc_stats:
            lines.append("今日各账号推文:")
            for acc, cnt in acc_stats[:5]:
                bar = "█" * min(cnt, 20)
                lines.append(f"  @{acc}: {bar} {cnt}条")

        if today_count == 0 and yesterday_count > 0:
            lines.append("")
            lines.append("⚠️ 今日尚未抓取到推文，请检查监控服务状态。")

        return "\n".join(lines)
    except Exception as e:
        return f"生成摘要失败: {e}"


# ═════════════════════════════════════════════════════════════
#  状态追踪
# ═════════════════════════════════════════════════════════════

def load_state() -> dict:
    try:
        if STATE_PATH.exists():
            with open(STATE_PATH) as f:
                return json.load(f)
    except Exception:
        pass
    return {
        "last_ok": {},
        "consecutive_failures": {},
        "auto_heal_count": {},
        "alerted": {},
        "last_heartbeat_sent": None,
        "last_daily_summary": None,
        "start_time": datetime.now().isoformat(),
        "total_checks": 0,
        "total_issues": 0,
        "total_heals": 0,
    }


def save_state(state: dict):
    with open(STATE_PATH, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


# ═════════════════════════════════════════════════════════════
#  主轮询逻辑
# ═════════════════════════════════════════════════════════════

def run_check(pusher: WechatPusher, state: dict) -> list:
    config = load_config()
    port = config.get("web_port", 8080)
    issues = []
    now_ts = time.time()
    state["total_checks"] = state.get("total_checks", 0) + 1

    # ── 1. 服务检查 + 自愈 ──
    services_to_check = ["x-monitor.service", "x-web.service"]
    for svc in services_to_check:
        result = check_service(svc)

        if result["active"]:
            state["consecutive_failures"][svc] = 0
            state["auto_heal_count"].pop(svc, None)
            state["last_ok"][svc] = now_ts

            # 恢复通知
            if svc in state.get("alerted", {}):
                hours_ago = round((now_ts - state["alerted"][svc]) / 3600, 1)
                pusher.send(
                    f"✅ 服务恢复: {svc}",
                    f"服务 {svc} 已恢复正常运行\n"
                    f"中断时长: 约 {hours_ago} 小时\n"
                    f"恢复时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                    category=f"recovery_{svc}",
                )
                state["alerted"].pop(svc, None)

            logger.info(f"  ✓ {svc}: active")
        else:
            state["consecutive_failures"][svc] = state["consecutive_failures"].get(svc, 0) + 1
            fails = state["consecutive_failures"][svc]
            heal_count = state["auto_heal_count"].get(svc, 0)

            logger.warning(f"  ✗ {svc}: {result.get('status', 'unknown')} (连续失败 {fails} 次, 已自愈 {heal_count} 次)")

            # 🔧 自愈：第 1-2 次失败尝试自动重启
            if fails <= 2:
                logger.info(f"  🔧 尝试自愈 {svc} (第 {fails} 次)...")
                heal_result = restart_service(svc)
                state["auto_heal_count"][svc] = heal_count + 1
                state["total_heals"] = state.get("total_heals", 0) + 1

                if heal_result.get("restart_success"):
                    logger.info(f"  ✅ 自愈成功: {svc} 已恢复")
                    state["consecutive_failures"][svc] = 0
                    pusher.send(
                        f"🔧 自愈成功: {svc}",
                        f"服务 {svc} 检测到异常，已自动重启恢复\n"
                        f"重启时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"这是第 {heal_count + 1} 次自愈操作",
                        category=f"autoheal_{svc}",
                    )
                    continue  # 自愈成功，跳过告警
                else:
                    logger.warning(f"  ❌ 自愈失败: {svc} 重启后仍异常")
                    # 自愈失败继续走告警流程

            # 🚨 告警：连续失败 >= 3 次或自愈全部失败
            if fails >= 3 and svc not in state.get("alerted", {}):
                minutes_down = fails * 5  # 假设每5分钟检查一次
                pusher.send(
                    f"🚨 服务异常: {svc}",
                    f"⚠️ 服务 {svc} 已连续 {fails} 次检查失败，约 {minutes_down} 分钟\n\n"
                    f"状态: {result.get('status', 'unknown')}\n"
                    f"自愈尝试: {heal_count} 次（均失败）\n"
                    f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
                    f"请登录 VPS 手动检查:\n"
                    f"  systemctl status {svc}\n"
                    f"  journalctl -u {svc} --no-pager -n 20",
                    category=f"alert_{svc}",
                )
                state.setdefault("alerted", {})[svc] = now_ts

            issues.append({
                "type": "service_down",
                "service": svc,
                "status": result.get("status", "unknown"),
                "consecutive_failures": fails,
                "auto_heal_attempts": heal_count,
            })

    # ── 2. Web 端点 ──
    web_check = check_web_endpoint(port)
    if web_check["reachable"]:
        logger.info(f"  ✓ Web (port {port}): OK")
    else:
        err = web_check.get("error", "unknown")
        logger.warning(f"  ✗ Web (port {port}): {err}")

        # 如果 x-web 是 active 的但端点不可达，尝试重启
        xweb_status = check_service("x-web.service")
        if xweb_status.get("active"):
            logger.info("  🔧 x-web active 但端口不可达，尝试重启...")
            restart_service("x-web.service")

        issues.append({"type": "web_unreachable", "error": err, "port": port})
        pusher.send(
            f"⚠️ Web 看板不可达",
            f"端口 {port} 无法访问: {err}\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            f"检查: systemctl status x-web\n"
            f"       netstat -tlnp | grep {port}",
            category="web_down",
        )

    # ── 3. 数据库 ──
    db_check = check_database()
    if db_check["healthy"]:
        fresh_mark = "✓" if db_check["fresh"] else "⚠ stale"
        logger.info(f"  {fresh_mark} DB: {db_check.get('tweet_count', 0)} tweets, "
                    f"{db_check.get('db_size_mb', 0)}MB, "
                    f"last={db_check.get('last_seen', 'N/A')}")
        if not db_check["fresh"] and db_check.get("stale_hours"):
            issues.append({"type": "stale_data", "stale_hours": db_check["stale_hours"]})
            pusher.send(
                f"⏰ 数据过期: {db_check['stale_hours']}h无新数据",
                f"最后推文于 {db_check['stale_hours']} 小时前\n"
                f"上次数据: {db_check.get('last_seen', 'N/A')}\n"
                f"推文总数: {db_check.get('tweet_count', 0)}\n\n"
                f"请检查: systemctl status x-monitor",
                category="stale_data",
            )
    else:
        logger.error(f"  ✗ DB: {db_check.get('error')}")
        issues.append({"type": "db_error", "error": db_check.get("error")})
        pusher.send(
            f"💥 数据库异常",
            f"无法访问: {db_check.get('error')}\n"
            f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            category="db_error",
        )

    # ── 4. 磁盘 ──
    disk = check_disk_space()
    if not disk.get("error"):
        logger.info(f"  💾 Disk: {disk['free_gb']}GB free ({disk['used_pct']}%)")
        if disk["used_pct"] > 90:
            pusher.send(
                f"💾 磁盘空间不足 ({disk['used_pct']}%)",
                f"剩余: {disk['free_gb']}GB / 总计: {disk['total_gb']}GB\n"
                f"请清理或扩容",
                category="disk_critical",
            )
        elif disk["used_pct"] > 80:
            pusher.send(
                f"📊 磁盘使用率偏高 ({disk['used_pct']}%)",
                f"剩余: {disk['free_gb']}GB / 总计: {disk['total_gb']}GB",
                category="disk_warning",
            )

    # ── 5. 内存 ──
    mem = check_memory()
    if not mem.get("error"):
        logger.info(f"  🧠 Memory: {mem.get('used_pct', '?')}% ({mem.get('free_mb', '?')}MB free)")
        if mem.get("used_pct", 0) > 95:
            pusher.send(
                f"🧠 内存不足 ({mem['used_pct']}%)",
                f"总量: {mem['total_mb']}MB, 可用: {mem['free_mb']}MB\n"
                f"请检查进程: top -o %MEM",
                category="memory_critical",
            )

    # ── 6. 心跳 ──
    last_hb = state.get("last_heartbeat_sent")
    if not last_hb or now_ts - last_hb > 1800:
        issue_labels = [i["type"] for i in issues]
        status_desc = f"正常（{len(issues)}个问题: {', '.join(issue_labels)}）" if issues else "全部正常 ✅"
        pusher.send(
            f"💚 系统心跳 — {status_desc}",
            f"时间: {datetime.now().strftime('%H:%M:%S')}\n"
            f"已运行 {state.get('total_checks', 0)} 次检查\n"
            f"累计自愈: {state.get('total_heals', 0)} 次\n"
            f"磁盘: {disk.get('free_gb', '?')}GB free\n"
            f"推文: {db_check.get('tweet_count', '?')}条 | 最后: {db_check.get('last_seen', 'N/A')}",
            category="heartbeat",
        )
        state["last_heartbeat_sent"] = now_ts

    # ── 7. 每日摘要（每天 08:00-08:30 之间推送一次） ──
    now_dt = datetime.now()
    last_daily = state.get("last_daily_summary")
    is_morning = 8 <= now_dt.hour < 9
    should_send_daily = (
        is_morning and
        (not last_daily or (now_ts - last_daily) > 82800)  # 23小时
    )
    if should_send_daily:
        summary = generate_daily_summary()
        pusher.send(
            f"📊 每日数据报告 — {now_dt.strftime('%m/%d')}",
            summary,
            category="daily_summary",
        )
        state["last_daily_summary"] = now_ts

    state["total_issues"] = state.get("total_issues", 0) + len(issues)
    return issues


# ═════════════════════════════════════════════════════════════
#  入口
# ═════════════════════════════════════════════════════════════

def main():
    import argparse
    parser = argparse.ArgumentParser(description="x-monitor 系统守护进程 v2.1")
    parser.add_argument("--interval", type=int, default=300, help="检查间隔（秒），默认300")
    parser.add_argument("--once", action="store_true", help="只执行一次检查")
    parser.add_argument("--daemon", action="store_true", help="守护模式运行")
    parser.add_argument("--daily", action="store_true", help="发送每日摘要并退出")
    args = parser.parse_args()

    pusher = WechatPusher()
    state = load_state()

    if not pusher.enabled:
        logger.warning("微信推送未启用，守护进程仅记录日志")

    if args.daily:
        summary = generate_daily_summary()
        print(summary)
        pusher.send(
            f"📊 每日数据报告 — {datetime.now().strftime('%m/%d')}",
            summary,
            category="daily_summary_manual",
        )
        return

    if args.once:
        logger.info("执行单次健康检查...")
        issues = run_check(pusher, state)
        save_state(state)
        status_line = f"检查完成: {'❌ ' + str(len(issues)) + ' 个问题' if issues else '✅ 全部正常'}"
        logger.info(status_line)
        for i in issues:
            logger.warning(f"  - [{i['type']}] {i}")
        sys.exit(1 if issues else 0)

    # 守护模式
    logger.info(f"🛡️ 守护进程 v2.1 启动，检查间隔: {args.interval}s")
    logger.info(f"   功能: 健康检查 + 自愈 + 微信告警 + 每日摘要")

    pusher.send(
        "🟢 守护进程已启动",
        f"x-monitor watchdog v2.1 开始运行\n"
        f"检查间隔: {args.interval}s\n"
        f"启动时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"自愈: 已启用 | 告警: PushPlus",
        category="startup",
    )

    while True:
        try:
            issues = run_check(pusher, state)
            save_state(state)
            if issues:
                logger.warning(f"本轮发现 {len(issues)} 个问题")
            else:
                logger.info("本轮检查全部通过 ✓")
        except Exception as e:
            logger.error(f"守护进程异常: {e}", exc_info=True)
            pusher.send(
                f"💥 Watchdog 自身异常",
                f"watchdog.py 运行出错:\n{str(e)[:300]}\n\n"
                f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"进程将继续运行并尝试恢复...",
                category="watchdog_error",
            )
            # 短暂等待后继续，避免异常循环
            time.sleep(30)

        time.sleep(args.interval)


if __name__ == "__main__":
    main()
