#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
A股早盘十分钟涨停抓取 + 成交量监控 + 微信推送
每天中午执行，抓取当日早盘10分钟内涨停的票
"""

import akshare as ak
import requests
import json
import pandas as pd
from datetime import datetime, timedelta
import os
import sys

# ============================================================
# 配置
# ============================================================
PUSHPLUS_TOKEN_FILE = os.path.expanduser("~/.workbuddy/skills/pushplus-wechat/token.txt")
OUTPUT_DIR = os.path.dirname(os.path.abspath(__file__))
EARLY_LIMIT = "094000"  # 10分钟内封板（含竞价涨停092500）
MIN_VOL_RATIO = 1.5     # 成交量放大倍数阈值

def get_pushplus_token():
    """读取PushPlus Token"""
    try:
        with open(PUSHPLUS_TOKEN_FILE, 'r') as f:
            return f.read().strip()
    except:
        return None

def send_wechat(title, content):
    """通过PushPlus推送微信消息"""
    token = get_pushplus_token()
    if not token:
        print("[ERROR] PushPlus Token未配置")
        return False
    
    try:
        resp = requests.post("http://www.pushplus.plus/send", json={
            "token": token,
            "title": title,
            "content": content,
            "template": "html"
        }, timeout=10)
        data = resp.json()
        if data.get("code") == 200:
            print("[OK] 微信推送成功")
            return True
        else:
            print(f"[ERROR] 推送失败: {data.get('msg')}")
            return False
    except Exception as e:
        print(f"[ERROR] 推送异常: {e}")
        return False

def fetch_today_zt():
    """获取今日涨停数据"""
    today = datetime.now().strftime("%Y%m%d")
    print(f"[INFO] 获取 {today} 涨停数据...")
    try:
        df = ak.stock_zt_pool_em(date=today)
        if df is None or len(df) == 0:
            print("[WARN] 今日暂无涨停数据（可能未收盘或非交易日）")
            return None
        print(f"[INFO] 今日涨停共 {len(df)} 只")
        return df
    except Exception as e:
        print(f"[ERROR] 获取涨停数据失败: {e}")
        return None

def fetch_history_volume(codes, lookback=5):
    """获取近期日线数据用于成交量对比"""
    print(f"[INFO] 获取 {len(codes)} 只股票近{lookback}日成交量...")
    
    volume_avg = {}
    for code in codes:
        try:
            # 用AKShare获取个股历史日线
            df = ak.stock_zh_a_hist(
                symbol=code,
                period="daily",
                start_date=(datetime.now() - timedelta(days=lookback+5)).strftime("%Y%m%d"),
                end_date=(datetime.now() - timedelta(days=1)).strftime("%Y%m%d"),
                adjust=""
            )
            if df is not None and len(df) >= 2:
                # 取最近 lookback 天的平均成交量
                avg_vol = df.tail(lookback)['成交量'].mean()
                last_vol = df.iloc[-1]['成交量']
                volume_avg[code] = {
                    'avg_vol': avg_vol,
                    'last_vol': last_vol,
                    'ratio': last_vol / avg_vol if avg_vol > 0 else 0
                }
        except Exception as e:
            print(f"  [WARN] {code} 成交量获取失败: {str(e)[:50]}")
    
    return volume_avg

def analyze_early_zt(df):
    """分析早盘十分钟涨停的票"""
    if df is None or len(df) == 0:
        return None
    
    # 筛选：首次封板时间在10分钟内（<= 094000）
    # 注意：092500 = 竞价涨停，也属于早盘涨停
    early_mask = df['首次封板时间'].notna() & (df['首次封板时间'] != '') & (df['首次封板时间'] <= EARLY_LIMIT)
    early_df = df[early_mask].copy()
    
    if len(early_df) == 0:
        print("[INFO] 今日无10分钟内涨停的票")
        return pd.DataFrame()
    
    print(f"[INFO] 早盘10分钟内涨停: {len(early_df)} 只")
    
    # 分类
    early_df['涨停类型'] = '未知'
    early_df.loc[early_df['首次封板时间'] <= '092500', '涨停类型'] = '竞价涨停'
    early_df.loc[(early_df['首次封板时间'] > '092500') & (early_df['首次封板时间'] <= '093000'), '涨停类型'] = '开盘秒板'
    early_df.loc[(early_df['首次封板时间'] > '093000') & (early_df['首次封板时间'] <= '093500'), '涨停类型'] = '5分钟板'
    early_df.loc[(early_df['首次封板时间'] > '093500') & (early_df['首次封板时间'] <= '094000'), '涨停类型'] = '10分钟板'
    
    return early_df

def build_report(early_df, vol_data):
    """生成分析报告"""
    if early_df is None or len(early_df) == 0:
        return None, "今日无早盘10分钟内涨停的票。"
    
    now = datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    
    # 构建HTML报告
    html_parts = [
        f'<h2>🔥 A股早盘10分钟涨停扫描</h2>',
        f'<p><b>日期：{date_str}（{now.strftime("%H:%M")} 更新）</b></p>',
        f'<p>📊 今日涨停总数：{len(early_df) if "total_zt" not in dir() else "N/A"}，早盘10分钟内涨停：<b style="color:red">{len(early_df)}只</b></p>',
        '<hr>',
        '<table border="1" cellpadding="6" cellspacing="0" style="border-collapse:collapse;width:100%;font-size:14px">',
        '<tr style="background:#e74c3c;color:white">',
        '<th>代码</th><th>名称</th><th>涨停类型</th><th>封板时间</th><th>炸板次数</th>',
        '<th>连板数</th><th>成交额(亿)</th><th>换手率</th><th>封板资金(亿)</th><th>成交量信号</th>',
        '</tr>'
    ]
    
    # 按封板时间排序
    early_df = early_df.sort_values('首次封板时间')
    
    # 成交量信号汇总
    vol_signals = []
    
    for _, row in early_df.iterrows():
        code = str(row['代码'])
        name = row['名称']
        zt_type = row['涨停类型']
        ftime = row['首次封板时间']
        ftime_str = f"{ftime[:2]}:{ftime[2:4]}:{ftime[4:6]}" if len(str(ftime)) >= 6 else str(ftime)
        zb_count = int(row.get('炸板次数', 0))
        lb_count = int(row.get('连板数', 0))
        amount = row.get('成交额', 0) / 1e8  # 转为亿
        turnover = row.get('换手率', 0)
        fb_fund = row.get('封板资金', 0) / 1e8
        
        # 成交量信号
        vol_signal = ""
        if code in vol_data:
            ratio = vol_data[code]['ratio']
            if ratio >= 2.0:
                vol_signal = f'<span style="color:red;font-weight:bold">🔥 放量{ratio:.1f}倍</span>'
                vol_signals.append(f"{name}({code})")
            elif ratio >= MIN_VOL_RATIO:
                vol_signal = f'<span style="color:orange">⚠ 放量{ratio:.1f}倍</span>'
                vol_signals.append(f"{name}({code})")
            elif ratio < 0.5:
                vol_signal = f'<span style="color:green">缩量</span>'
            else:
                vol_signal = '正常'
        
        # 炸板标记
        zb_mark = f'<span style="color:red">⚠{zb_count}次</span>' if zb_count > 0 else '0'
        
        # 连板标记
        lb_mark = f'<b>{lb_count}板</b>' if lb_count >= 2 else f'{lb_count}板'
        
        # 行背景色
        row_style = 'background:#fff5f5' if zb_count > 0 else ''
        if zt_type == '竞价涨停':
            row_style = 'background:#ffe0b2'
        
        html_parts.append(
            f'<tr style="{row_style}">'
            f'<td>{code}</td><td><b>{name}</b></td><td>{zt_type}</td><td>{ftime_str}</td>'
            f'<td>{zb_mark}</td><td>{lb_mark}</td>'
            f'<td>{amount:.2f}</td><td>{turnover:.2f}%</td><td>{fb_fund:.2f}</td>'
            f'<td>{vol_signal}</td>'
            f'</tr>'
        )
    
    html_parts.append('</table>')
    
    # 汇总分析
    html_parts.append('<hr><h3>📈 盘面分析</h3>')
    
    # 涨停类型分布
    type_counts = early_df['涨停类型'].value_counts()
    html_parts.append('<ul>')
    for t, c in type_counts.items():
        html_parts.append(f'<li>{t}：{c}只</li>')
    html_parts.append('</ul>')
    
    # 连板分布
    lb_gt1 = (early_df['连板数'] >= 2).sum()
    if lb_gt1 > 0:
        html_parts.append(f'<p>🔗 连板（≥2板）：<b>{lb_gt1}只</b></p>')
    
    # 炸板警告
    zb_total = (early_df['炸板次数'] > 0).sum()
    if zb_total > 0:
        html_parts.append(f'<p>⚠ 炸板股票：<b style="color:red">{zb_total}只</b>（封板质量需关注）</p>')
    
    # 成交量异常信号
    if vol_signals:
        html_parts.append(f'<p>📊 <b>成交量异常放量：</b>{", ".join(vol_signals)}</p>')
    
    html_parts.append('<hr><p style="color:#888;font-size:12px">数据来源：东方财富/AKShare | 自动推送时间：每个交易日中午</p>')
    
    html_content = '\n'.join(html_parts)
    
    # 保存CSV
    csv_path = os.path.join(OUTPUT_DIR, f"early_zt_{datetime.now().strftime('%Y%m%d')}.csv")
    early_df.to_csv(csv_path, index=False, encoding='utf-8-sig')
    print(f"[INFO] 数据已保存: {csv_path}")
    
    return html_content, None

def main():
    print("=" * 60)
    print("A股早盘10分钟涨停扫描 -", datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    print("=" * 60)
    
    # 1. 获取今日涨停数据
    df = fetch_today_zt()
    
    # 2. 筛选早盘10分钟内涨停
    early_df = analyze_early_zt(df)
    
    if early_df is None or len(early_df) == 0:
        # 推送空结果
        title = f"📊 早盘涨停扫描 {datetime.now().strftime('%m/%d')} - 无符合条件的票"
        content = "<p>今日无10分钟内涨停的A股。</p><p>可能是非交易日或市场行情平淡。</p>"
        send_wechat(title, content)
        return
    
    # 3. 获取成交量历史数据（只获取筛选后的股票）
    codes = early_df['代码'].astype(str).tolist()
    vol_data = fetch_history_volume(codes)
    
    # 4. 生成报告
    html_content, error = build_report(early_df, vol_data)
    
    if error:
        print(f"[WARN] {error}")
        return
    
    # 5. 推送微信
    title = f"🔥 早盘10分钟涨停扫描 {datetime.now().strftime('%m/%d')} - {len(early_df)}只"
    send_wechat(title, html_content)

if __name__ == "__main__":
    main()
