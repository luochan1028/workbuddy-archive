#!/usr/bin/env python3
"""
快速测试监控脚本是否能正常拉取推文。
运行: python test_monitor.py
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from monitor_x import fetch_tweets_rss, TARGET_USERNAME, init_db, save_and_detect, display_tweets

def main():
    print("=" * 60)
    print("  X Monitor 连接测试")
    print("=" * 60)

    # 1. 测试数据库
    print("\n[1/3] 初始化数据库...")
    try:
        conn = init_db()
        print("  OK — 数据库就绪")
    except Exception as e:
        print(f"  FAIL — {e}")
        return

    # 2. 测试抓取
    print(f"\n[2/3] 抓取 @{TARGET_USERNAME} 推文...")
    try:
        tweets, instance = fetch_tweets_rss(TARGET_USERNAME, timeout=20)
        print(f"  OK — 使用实例: {instance}")
        print(f"  OK — 获取到 {len(tweets)} 条推文")

        if tweets:
            # 3. 测试存储
            print("\n[3/3] 测试存储与去重...")
            new = save_and_detect(conn, tweets, instance)
            print(f"  OK — 新推文: {len(new)} 条")
            print(f"  OK — 已存在: {len(tweets) - len(new)} 条")

            display_tweets(tweets[:5], "最新推文预览")
        else:
            print("\n  WARNING: 未获取到推文，请检查网络或 Nitter 实例状态")

    except Exception as e:
        print(f"\n  FAIL — {e}")
        print("  提示: 请确保网络能访问海外网站 (需要代理)")
        return
    finally:
        conn.close()

    print("\n" + "=" * 60)
    print("  测试完成! 运行以下命令开始监控:")
    print("  python monitor_x.py                  # 单次检查")
    print("  python monitor_x.py --daemon 900     # 每 15 分钟检查")
    print("=" * 60)

if __name__ == "__main__":
    main()
