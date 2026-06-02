#!/usr/bin/env python3
"""
诊断工具 — Diagnostics & Quick Fix
====================================
快速诊断 x-monitor 系统的健康状态，排查常见问题。

用法:
    python diag.py              # 全面诊断
    python diag.py --quick      # 快速检查
    python diag.py --fix        # 自动修复常见问题
"""

import json
import os
import sqlite3
import subprocess
import sys
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
DB_PATH = SCRIPT_DIR / "tweets.db"
CONFIG_PATH = SCRIPT_DIR / "config.json"

GREEN = "\033[0;32m"
RED = "\033[0;31m"
YELLOW = "\033[1;33m"
BLUE = "\033[0;34m"
NC = "\033[0m"


def ok(msg): print(f"  {GREEN}✓{NC} {msg}")
def fail(msg): print(f"  {RED}✗{NC} {msg}")
def warn(msg): print(f"  {YELLOW}!{NC} {msg}")
def info(msg): print(f"  {BLUE}→{NC} {msg}")


def check_python():
    """检查 Python 环境"""
    print(f"\n{'='*50}")
    print(f"  Python 环境")
    print(f"{'='*50}")
    ok(f"Python {sys.version.split()[0]}")
    ok(f"工作目录: {SCRIPT_DIR}")


def check_dependencies():
    """检查依赖包"""
    print(f"\n{'='*50}")
    print(f"  依赖检查")
    print(f"{'='*50}")
    deps = ["flask", "requests", "feedparser", "sqlite3"]
    for dep in deps:
        try:
            __import__(dep)
            ok(dep)
        except ImportError:
            fail(f"{dep} — pip install {dep}")

    try:
        __import__("deep_translator")
        ok("deep_translator (翻译)")
    except ImportError:
        warn("deep_translator 未安装，翻译功能不可用")


def check_config():
    """检查配置文件"""
    print(f"\n{'='*50}")
    print(f"  配置检查")
    print(f"{'='*50}")
    try:
        with open(CONFIG_PATH) as f:
            cfg = json.load(f)
        accounts = cfg.get("accounts", [])
        ok(f"config.json: {len(accounts)} 个监控账号")
        for acc in accounts:
            info(f"  @{acc}")

        wp = cfg.get("wechat_push", {})
        if wp.get("enabled"):
            token = wp.get("pushplus_token", "")
            if token and len(token) > 10:
                ok(f"微信推送: PushPlus (已配置)")
            else:
                warn("微信推送: 启用但 Token 可能无效")
        else:
            warn("微信推送: 未启用")
    except FileNotFoundError:
        fail("config.json 不存在！")
    except json.JSONDecodeError:
        fail("config.json 格式错误！")


def check_database():
    """检查数据库"""
    print(f"\n{'='*50}")
    print(f"  数据库检查")
    print(f"{'='*50}")
    if not DB_PATH.exists():
        fail(f"tweets.db 不存在！路径: {DB_PATH}")
        return

    try:
        conn = sqlite3.connect(str(DB_PATH))
        total = conn.execute("SELECT count(*) FROM tweets").fetchone()[0]
        db_size = round(os.path.getsize(str(DB_PATH)) / (1024 * 1024), 1)

        ok(f"数据库: {db_size}MB, {total} 条推文")

        # 最近数据
        last = conn.execute("SELECT max(first_seen) FROM tweets").fetchone()[0]
        if last:
            ok(f"最后推文: {last}")
            try:
                from datetime import datetime, timedelta
                last_dt = datetime.fromisoformat(last.replace("Z", "+00:00"))
                hours_ago = (datetime.now().astimezone() - last_dt.replace(tzinfo=None)).total_seconds() / 3600
                if hours_ago > 6:
                    warn(f"数据可能过期（{hours_ago:.1f} 小时未更新）")
                else:
                    ok(f"数据新鲜（{hours_ago:.1f} 小时前）")
            except Exception:
                pass

        # 账号统计
        accs = conn.execute(
            "SELECT username, count(*) as cnt FROM tweets GROUP BY username ORDER BY cnt DESC"
        ).fetchall()
        for acc, cnt in accs:
            info(f"  @{acc}: {cnt} 条")

        conn.close()
    except Exception as e:
        fail(f"数据库异常: {e}")


def check_services():
    """检查 systemd 服务"""
    print(f"\n{'='*50}")
    print(f"  服务状态")
    print(f"{'='*50}")
    for svc in ["x-monitor", "x-web", "x-watchdog"]:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", f"{svc}.service"],
                capture_output=True, text=True, timeout=5,
            )
            status = r.stdout.strip()
            if status == "active":
                ok(f"{svc}: {GREEN}active{NC}")
            else:
                fail(f"{svc}: {status}")
        except Exception:
            fail(f"{svc}: 无法检查（非 systemd 环境？）")


def check_network():
    """检查网络可达性"""
    print(f"\n{'='*50}")
    print(f"  网络检查")
    print(f"{'='*50}")
    try:
        import requests
        r = requests.get("http://127.0.0.1:8080/api/health", timeout=5)
        if r.status_code == 200:
            ok(f"Web 端点: HTTP 200")
            data = r.json()
            ok(f"引擎: sector_mapper={data.get('engines',{}).get('sector_mapper')} "
               f"pattern={data.get('engines',{}).get('pattern_tracker')} "
               f"profile={data.get('engines',{}).get('account_profile')}")
        else:
            fail(f"Web 端点: HTTP {r.status_code}")
    except Exception as e:
        fail(f"Web 端点不可达: {e}")

    # Nitter 可达性
    instances = [
        "https://xcancel.com",
        "https://nitter.net",
        "https://nitter.poast.org",
    ]
    for inst in instances[:2]:
        try:
            import requests
            r = requests.get(inst, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
            if r.status_code in (200, 403):  # 403 = Cloudflare block, still reachable
                ok(f"Nitter: {inst} (HTTP {r.status_code})")
            else:
                warn(f"Nitter: {inst} (HTTP {r.status_code})")
        except Exception:
            fail(f"Nitter: {inst} 不可达")


def auto_fix():
    """自动修复常见问题"""
    print(f"\n{'='*50}")
    print(f"  自动修复")
    print(f"{'='*50}")

    fixes_applied = 0

    # 1. 确保数据库存在
    if not DB_PATH.exists():
        info("创建数据库...")
        conn = sqlite3.connect(str(DB_PATH))
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
        conn.commit()
        conn.close()
        ok("数据库已创建")
        fixes_applied += 1

    # 2. 确保日志文件存在
    for logf in ["monitor.log", "web.log", "watchdog.log"]:
        p = SCRIPT_DIR / logf
        if not p.exists():
            p.touch()
            ok(f"创建日志文件: {logf}")
            fixes_applied += 1

    # 3. 填充种子数据（如果数据库为空）
    if DB_PATH.exists():
        conn = sqlite3.connect(str(DB_PATH))
        count = conn.execute("SELECT count(*) FROM tweets").fetchone()[0]
        conn.close()
        if count == 0:
            info("数据库为空，填充示例数据...")
            try:
                subprocess.run(
                    [sys.executable, str(SCRIPT_DIR / "seed_data.py"), "--days", "3"],
                    cwd=str(SCRIPT_DIR), timeout=30,
                )
                ok("种子数据已填充")
                fixes_applied += 1
            except Exception as e:
                fail(f"种子数据填充失败: {e}")

    # 4. 重启异常服务
    for svc in ["x-monitor", "x-web", "x-watchdog"]:
        try:
            r = subprocess.run(
                ["systemctl", "is-active", f"{svc}.service"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip() != "active":
                info(f"重启 {svc}...")
                subprocess.run(["systemctl", "restart", f"{svc}.service"], timeout=15)
                ok(f"{svc} 已重启")
                fixes_applied += 1
        except Exception:
            pass

    if fixes_applied == 0:
        ok("未发现需要修复的问题")
    else:
        ok(f"共修复 {fixes_applied} 个问题")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="x-monitor 系统诊断工具")
    parser.add_argument("--quick", action="store_true", help="快速检查")
    parser.add_argument("--fix", action="store_true", help="自动修复")
    args = parser.parse_args()

    print(f"{BLUE}╔══════════════════════════════════════════════════╗{NC}")
    print(f"{BLUE}║  x-monitor 系统诊断 v2.1                           ║{NC}")
    print(f"{BLUE}╚══════════════════════════════════════════════════╝{NC}")
    print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if args.fix:
        auto_fix()
        return

    check_python()
    check_dependencies()
    check_config()
    check_database()

    if not args.quick:
        check_services()
        check_network()

    print(f"\n{'='*50}")
    print(f"  诊断完成")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
