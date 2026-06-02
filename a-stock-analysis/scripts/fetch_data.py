#!/usr/bin/env python3
"""拉取过去3年A股涨停数据并分析最适合打板的股票"""

import requests
import json
import time
import sys
import os

API_URL = "https://www.codebuddy.cn/v2/tool/financedata"
OUTPUT_DIR = r"c:\Users\asus\WorkBuddy\20260530091900"

# Token from IDE session
TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MTE2MzY0NTEsImlhdCI6MTc4MDEwNjUxMCwiYXV0aF90aW1lIjoxNzgwMTAwNDUwLCJqdGkiOiI0OTU1ODBmYS1iZDZlLTQ2OGEtOGRkMS05Y2FmYzY4MWVlODUiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiI0YzFjOTg5MS0xMWRlLTRmYWQtYjhhMS0xNzAzZjkwYjk0Y2UiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiMWZhYzU0NWEtZGNjOC00ZGJhLWIzMzgtZTA1ZDlmYzZmMTkzIiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi5Z2k5Y6aIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTgxNzEyMzIyMzcifQ.eP71TbYioRLFsRw_OYcXyYLh35xMCAqrkEaS-vFB8KpCP_rCH-6Uj-MuDAeB9aIJqX-pgv_P1FMF2gjk0i-hVGyiON_3wBzvCegTR2DfGu6YXmG7bmJ7mg__jRd_Z8NKlHa3T0OoJB1_8_aaGLZa9sPcIOZgE-xc2wKEqrfZ8dpAZ0cOWTPSxFOaVqhS_nc81nLWoiGzI8t_Uj3wlTMCpU4X4h6fEu2Ip-kuFq6J_SRox7Y327aasd9Y__B-JB1VlhW1MRVq4uYksjLKhARgaZa2MTuGD1viaYL7lAWbdxXVS8LLl_s3GGOQs_cJCrAhghf4rkUJadBoNwNJJ-jdMw"

# 按半年分批拉取
PERIODS = [
    ("20230501", "20230630"),
    ("20230701", "20231231"),
    ("20240101", "20240630"),
    ("20240701", "20241231"),
    ("20250101", "20250530"),
]

def call_api(api_name, params, fields="", retries=3):
    """调用金融数据 API"""
    body = {
        "api_name": api_name,
        "params": params,
        "fields": fields
    }
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {TOKEN}"
    }
    for attempt in range(retries):
        try:
            resp = requests.post(API_URL, json=body, headers=headers, timeout=120)
            result = resp.json()
            if result.get("code") == 0:
                return result
            else:
                print(f"  API error: {result.get('msg')} (code={result.get('code')})")
                if attempt < retries - 1:
                    print(f"  Retrying in 3s...")
                    time.sleep(3)
        except Exception as e:
            print(f"  Request failed: {e}")
            if attempt < retries - 1:
                time.sleep(3)
    return None

def fetch_limit_data(start_date, end_date):
    """拉取涨停数据（limit_list_d）"""
    print(f"Fetching limit_list_d: {start_date} ~ {end_date}")
    result = call_api(
        "limit_list_d",
        {
            "start_date": start_date,
            "end_date": end_date,
            "limit_type": "U"
        },
        "ts_code,name,trade_date,pct_chg,open_times,up_stat,limit_times,limit,float_mv,turnover_ratio,fd_amount,first_time"
    )
    if result:
        items = result.get("data", {}).get("items", [])
        print(f"  Got {len(items)} records")
        return items
    return []

def fetch_limit_step(start_date, end_date):
    """拉取连板天梯数据"""
    print(f"Fetching limit_step: {start_date} ~ {end_date}")
    result = call_api(
        "limit_step",
        {
            "start_date": start_date,
            "end_date": end_date
        },
        "ts_code,name,trade_date,nums"
    )
    if result:
        items = result.get("data", {}).get("items", [])
        print(f"  Got {len(items)} records")
        return items
    return []

def fetch_limit_ths(start_date, end_date):
    """拉取同花顺涨停封板率数据"""
    print(f"Fetching limit_list_ths (涨停池): {start_date} ~ {end_date}")
    result = call_api(
        "limit_list_ths",
        {
            "start_date": start_date,
            "end_date": end_date,
            "limit_type": "涨停池"
        },
        "ts_code,name,trade_date,limit_up_suc_rate,status,limit_order,limit_amount"
    )
    if result:
        items = result.get("data", {}).get("items", [])
        print(f"  Got {len(items)} records")
        return items
    return []

def main():
    print("=" * 60)
    print("A股打板分析 - 过去3年数据拉取")
    print("=" * 60)
    
    # Step 1: 拉取所有涨停数据
    all_limit_items = []
    for start, end in PERIODS:
        items = fetch_limit_data(start, end)
        all_limit_items.extend(items)
        time.sleep(0.5)
    
    # 保存原始数据
    with open(os.path.join(OUTPUT_DIR, "all_limit_data.json"), "w", encoding="utf-8") as f:
        json.dump(all_limit_items, f, ensure_ascii=False)
    print(f"\nTotal limit records: {len(all_limit_items)}")
    
    # Step 2: 拉取连板天梯数据
    all_step_items = []
    for start, end in PERIODS:
        items = fetch_limit_step(start, end)
        all_step_items.extend(items)
        time.sleep(0.5)
    
    with open(os.path.join(OUTPUT_DIR, "all_step_data.json"), "w", encoding="utf-8") as f:
        json.dump(all_step_items, f, ensure_ascii=False)
    print(f"Total step records: {len(all_step_items)}")
    
    # Step 3: 拉取同花顺涨停数据
    print("\nFetching limit_list_ths (from 20231101)...")
    ths_items = fetch_limit_ths("20231101", "20250530")
    with open(os.path.join(OUTPUT_DIR, "all_ths_data.json"), "w", encoding="utf-8") as f:
        json.dump(ths_items, f, ensure_ascii=False)
    print(f"Total THS records: {len(ths_items)}")
    
    print("\n" + "=" * 60)
    print("数据拉取完成！")
    print("=" * 60)

if __name__ == "__main__":
    main()
