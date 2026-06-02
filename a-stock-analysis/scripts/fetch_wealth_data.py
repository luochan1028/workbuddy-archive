#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
2026年5月 财富市场全景数据拉取脚本（token已配置）
"""

import requests
import json
import csv
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TUSHARE_TOKEN = "edebe47ae8b45a3cbf775f5c5666c4f34971326dece381270e9f7aba"
API_URL = "https://www.codebuddy.cn/v2/tool/financedata"

def fetch(api_name, params, fields=""):
    payload = {
        "token": TUSHARE_TOKEN,
        "api_name": api_name,
        "params": params,
        "fields": fields
    }
    try:
        resp = requests.post(API_URL, json=payload, timeout=30)
        data = resp.json()
        if data.get("code") == 0:
            return data["data"]
        else:
            print("  [API错误] code=" + str(data.get("code")) + " msg=" + str(data.get("msg")))
            return None
    except Exception as e:
        print("  [请求异常] " + str(e))
        return None

def save_csv(filename, fields, items):
    filepath = filename
    with open(filepath, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(fields)
        for row in items:
            writer.writerow(row)
    print("  已保存: " + filepath + " (" + str(len(items)) + " 条)")

def main():
    print("=" * 60)
    print(" 2026年5月 财富市场全景数据拉取（token已配置）")
    print("=" * 60)

    # 1. 北向资金流向（5月全月）
    print("\n[1/6] 拉取北向资金流向（5月全月）...")
    data = fetch("moneyflow_hsgt", {
        "start_date": "20260501",
        "end_date":   "20260530"
    })
    if data and data.get("items"):
        save_csv("north_money_202605.csv", data["fields"], data["items"])
        try:
            total = sum(float(x[5]) for x in data["items"] if len(x) > 5 and x[5] and str(x[5]).replace("-","").replace(".","").isdigit())
            print("  5月北向资金累计净流入: " + str(round(total/10000, 2)) + " 亿元")
        except Exception as e:
            print("  数据已保存，请手动计算累计值. err=" + str(e))
    else:
        print("  北向资金数据获取失败或为空")

    # 2. ETF份额规模（上交所Top50）
    print("\n[2/6] 拉取ETF规模数据（上交所）...")
    data_sse = fetch("etf_share_size", {
        "exchange":   "SSE",
        "start_date": "20260501",
        "end_date":   "20260529"
    })
    print("  拉取ETF规模数据（深交所）...")
    data_szse = fetch("etf_share_size", {
        "exchange":   "SZSE",
        "start_date": "20260501",
        "end_date":   "20260529"
    })
    all_etf = []
    if data_sse and data_sse.get("items"):
        all_etf.extend(data_sse["items"])
        print("  上交所ETF: " + str(len(data_sse["items"])) + " 条")
    if data_szse and data_szse.get("items"):
        all_etf.extend(data_szse["items"])
        print("  深交所ETF: " + str(len(data_szse["items"])) + " 条")
    if all_etf:
        all_etf_sorted = sorted(all_etf, key=lambda x: float(x[3]) if len(x) > 3 and x[3] else 0, reverse=True)
        save_csv("etf_size_202605.csv", data_sse["fields"] if data_sse else data_szse["fields"], all_etf_sorted[:50])
        try:
            total_size = sum(float(x[3]) for x in all_etf_sorted[:50] if len(x) > 3 and x[3])
            print("  Top50 ETF总规模: " + str(round(total_size/10000, 2)) + " 亿元")
        except:
            pass

    # 3. 北向资金每日十大成交股（最新一天，看外资买什么）
    print("\n[3/6] 拉取北向资金十大成交股（最新交易日）...")
    data = fetch("hsgt_top10", {
        "trade_date": "20260529"
    })
    if data and data.get("items"):
        # 按买入金额排序
        items_sorted = sorted(data["items"], key=lambda x: float(x[4]) if len(x) > 4 and x[4] else 0, reverse=True)
        save_csv("hsgt_top10_20260529.csv", data["fields"], items_sorted)
        print("  外资买卖Top标的已保存（共 " + str(len(items_sorted)) + " 条）")
        # 打印Top10
        for i, row in enumerate(items_sorted[:10]):
            try:
                print("    " + str(i+1) + ". " + str(row[1]) + " | 买入:" + str(round(float(row[4])/10000, 2)) + "亿 卖出:" + str(round(float(row[5])/10000, 2)) + "亿 净:" + str(round(float(row[6])/10000, 2)) + "亿")
            except:
                pass
    else:
        # 尝试前一个交易日
        data2 = fetch("hsgt_top10", {"trade_date": "20260528"})
        if data2 and data2.get("items"):
            save_csv("hsgt_top10_20260528.csv", data2["fields"], data2["items"])
            print("  使用5/28数据（5/29可能非交易日），共 " + str(len(data2["items"])) + " 条")
        else:
            print("  北向十大成交股数据获取失败（可能非交易日）")

    # 4. 热门白马股行情（5月最新）
    print("\n[4/6] 拉取热门白马股5月行情...")
    hot_stocks = {
        "000001.SZ": "平安银行",
        "600519.SH": "贵州茅台",
        "300750.SZ": "宁德时代",
        "002594.SZ": "比亚迪",
        "601318.SH": "中国平安",
        "000858.SZ": "五粮液",
        "600036.SH": "招商银行",
        "601012.SH": "隆基绿能",
        "300059.SZ": "东方财富",
        "600900.SH": "长江电力",
    }
    all_stock_data = []
    fields_stock = None
    for ts_code in hot_stocks:
        data = fetch("daily", {
            "ts_code":     ts_code,
            "start_date": "20260501",
            "end_date":   "20260530"
        })
        if data and data.get("items"):
            if not fields_stock:
                fields_stock = data["fields"]
            latest = data["items"][0]
            all_stock_data.append(latest)
            try:
                print("  " + hot_stocks[ts_code] + "(" + ts_code + "): 收盘" + str(latest[4]) + " 涨跌幅" + str(latest[7]) + "% 成交额" + str(round(float(latest[9])/100000, 2)) + "亿")
            except:
                print("  " + hot_stocks[ts_code] + "(" + ts_code + "): 数据已获取")
        else:
            print("  " + hot_stocks[ts_code] + "(" + ts_code + "): 无数据")

    if all_stock_data and fields_stock:
        save_csv("hot_stocks_202605.csv", fields_stock, all_stock_data)

    # 5. 涨停板数据（打板标的有哪些）
    print("\n[5/6] 拉取近期涨停板数据...")
    data = fetch("limit_list_ths", {
        "trade_date": "20260529"
    })
    if not (data and data.get("items")):
        data = fetch("limit_list_ths", {"trade_date": "20260528"})
    if not (data and data.get("items")):
        data = fetch("limit_list_ths", {"trade_date": "20260527"})

    if data and data.get("items"):
        items = sorted(data["items"], key=lambda x: float(x[3]) if len(x) > 3 and x[3] else 0, reverse=True)
        save_csv("limit_up_latest.csv", data["fields"], items[:50])
        print("  涨停板数据: " + str(len(items)) + " 条（保存Top50）")
        for i, row in enumerate(items[:15]):
            try:
                print("    " + str(i+1) + ". " + str(row[1]) + "(" + str(row[0]) + ") 涨幅:" + str(row[3]) + "% 成交额:" + str(round(float(row[5])/100000000, 2)) + "亿")
            except:
                pass
    else:
        print("  涨停板数据获取失败（可能非交易日）")

    # 6. 个股资金流向（看大单/机构买什么）
    print("\n[6/6] 拉取热门股资金流向（大单净流入）...")
    moneyflow_stocks = ["000001.SZ","600519.SH","300750.SZ","002594.SZ","601318.SH"]
    all_mf = []
    fields_mf = None
    for ts_code in moneyflow_stocks:
        data = fetch("moneyflow", {
            "ts_code":    ts_code,
            "start_date": "20260520",
            "end_date":   "20260530"
        })
        if data and data.get("items"):
            if not fields_mf:
                fields_mf = data["fields"]
            all_mf.extend(data["items"])
            # 打印最新一天的大单净流入
            latest = data["items"][0]
            try:
                net = float(latest[17]) if len(latest) > 17 else 0  # net_mf_amount
                direction = "净流入" if net > 0 else "净流出"
                print("  " + ts_code + ": 最新大单" + direction + " " + str(round(abs(net)/10000, 2)) + "亿")
            except:
                pass
        else:
            print("  " + ts_code + ": 无资金流向数据")

    if all_mf and fields_mf:
        save_csv("moneyflow_hot_202605.csv", fields_mf, all_mf)

    print("\n" + "=" * 60)
    print(" 数据拉取完成！以下CSV文件已保存：")
    print("  1. north_money_202605.csv  - 北向资金流向（每日）")
    print("  2. etf_size_202605.csv     - ETF规模Top50")
    print("  3. hsgt_top10_XXXXXXXX.csv - 外资十大成交股（买了哪些）")
    print("  4. hot_stocks_202605.csv   - 热门白马股行情")
    print("  5. limit_up_latest.csv     - 最新涨停板标的")
    print("  6. moneyflow_hot_202605.csv - 热门股资金流向")
    print("=" * 60)

if __name__ == "__main__":
    main()
