#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日涨停板筛选 + 次日监控列表生成
收盘后自动运行，筛选出次日重点监控的股票
"""

import urllib.request
import json
import ssl
import os
from datetime import datetime, timedelta
from pathlib import Path

# 配置
TOKEN_FILE = "c:/Users/asus/.workbuddy/skills/pushplus-wechat/token.txt"
PUSHPLUS_URL = "http://www.pushplus.plus/send"
WATCHLIST_FILE = "c:/Users/asus/WorkBuddy/20260530084842/monitor_watchlist.json"
REPORT_FILE = "c:/Users/asus/WorkBuddy/20260530084842/涨停板量化评估报告.md"

# 同花顺/东方财富 涨停数据接口
ZT_URL = "http://pageb2c.xueqiu.com/page-b2c/indicator-quotation-web/v1/quotation/daily-limit?size=100&order=desc&orderBy=continuous_limit_up_count&page=1"


def load_token():
    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except:
        return None


def push_wechat(title, content):
    token = load_token()
    if not token:
        return False
    
    data = {"token": token, "title": title, "content": content, "template": "html"}
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        req = urllib.request.Request(
            PUSHPLUS_URL,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json'}
        )
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        return result.get('code') == 200
    except:
        return False


def get_zt_data_from_akshare():
    """使用akshare获取今日涨停数据"""
    try:
        import akshare as ak
        today_str = datetime.now().strftime('%Y%m%d')
        try:
            df = ak.stock_zt_pool_em(date=today_str)
        except:
            df = ak.stock_zt_pool_em()  # 获取最新
        return df.to_dict(orient='records')
    except Exception as e:
        print(f"[ERROR] akshare获取失败: {e}")
        return []


def get_stock_detail(code):
    """获取个股详情"""
    if code.startswith('6'):
        secid = f"1.{code}"
    else:
        secid = f"0.{code}"
    
    url = f"http://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f46,f47,f48,f19,f20,f92,f117,f60,f57,f58"
    
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        data = json.loads(resp.read().decode('utf-8'))
        
        if data.get('rc') != 0 or not data.get('data'):
            return None
        
        d = data['data']
        return {
            'code': code,
            'name': d.get('f58', code),
            'price': d.get('f43', 0) / 100 if d.get('f43') else 0,
            'volume': d.get('f47', 0),
            'amount': d.get('f48', 0),
            'bid_vol': d.get('f20', 0),
            'turnover_rate': d.get('f92', 0) / 100 if d.get('f92') else 0,
            'float_cap': d.get('f117', 0),
            'pre_close': d.get('f60', 0) / 100 if d.get('f60') else 0,
        }
    except:
        return None


def evaluate_stock(stock, detail):
    """量化评估单只股票"""
    score = 50
    reasons = []
    
    # 连板加分
    limit_times = stock.get('连板数', stock.get('limit_times', 1))
    if limit_times == 1:
        score += 15
        reasons.append("首板(潜力大)")
    elif limit_times == 2:
        score += 10
        reasons.append("2连板")
    elif limit_times == 3:
        score += 5
        reasons.append("3连板")
    elif limit_times >= 5:
        score -= 10
        reasons.append(f"{limit_times}连板(高位风险)")
    
    # 封单比
    if detail and detail['float_cap'] > 0 and detail['bid_vol'] > 0:
        seal_amount = detail['bid_vol'] * 100 * detail['price']
        seal_ratio = seal_amount / detail['float_cap']
        if seal_ratio >= 0.05:
            score += 20
            reasons.append(f"封单比{seal_ratio*100:.1f}%[强]")
        elif seal_ratio >= 0.02:
            score += 10
            reasons.append(f"封单比{seal_ratio*100:.1f}%")
        elif seal_ratio >= 0.005:
            score += 0
        else:
            score -= 10
            reasons.append(f"封单比{seal_ratio*100:.1f}%[弱]")
    
    # 换手率
    if detail:
        turnover = detail['turnover_rate']
        if 3 <= turnover <= 10:
            score += 10
            reasons.append(f"换手{turnover:.1f}%[健康]")
        elif turnover <= 15:
            score += 5
            reasons.append(f"换手{turnover:.1f}%")
        elif turnover > 20:
            score -= 10
            reasons.append(f"换手{turnover:.1f}%[过高]")
    
    # 炸板次数（从akshare数据中获取）
    open_num = stock.get('炸板次数', stock.get('open_num', 0))
    if open_num == 0:
        score += 10
        reasons.append("未炸板")
    elif open_num <= 2:
        score += 0
        reasons.append(f"炸板{open_num}次")
    else:
        score -= 10
        reasons.append(f"炸板{open_num}次[多]")
    
    # 成交额（越大越好，说明资金认可）
    if detail and detail['amount'] > 0:
        if detail['amount'] >= 1e9:
            score += 5
            reasons.append("成交额>1亿")
    
    # 分级
    if score >= 80:
        grade = 'S'
    elif score >= 70:
        grade = 'A'
    elif score >= 60:
        grade = 'B'
    else:
        grade = 'C'
    
    return {
        'code': stock.get('代码', stock.get('ts_code', '')),
        'name': stock.get('名称', stock.get('name', '')),
        'grade': grade,
        'score': score,
        'limit_times': limit_times,
        'reason': ' | '.join(reasons),
        'price': detail['price'] if detail else 0,
        'turnover': detail['turnover_rate'] if detail else 0,
        'seal_ratio': (detail['bid_vol'] * 100 * detail['price'] / detail['float_cap']) if detail and detail['float_cap'] > 0 else 0,
    }


def run_screening():
    """主筛选流程"""
    print(f"\n{'='*60}")
    print(f"每日涨停板筛选启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # 1. 获取涨停数据
    print("[1/4] 获取今日涨停数据...")
    zt_data = get_zt_data_from_akshare()
    if not zt_data:
        print("[ERROR] 获取涨停数据失败")
        return
    
    print(f"  获取到 {len(zt_data)} 只涨停股票")
    
    # 2. 逐只评估
    print("[2/4] 量化评估...")
    results = []
    for i, stock in enumerate(zt_data):
        code = stock.get('代码', stock.get('ts_code', ''))
        name = stock.get('名称', stock.get('name', ''))
        print(f"  [{i+1}/{len(zt_data)}] {name}({code})", end='')
        
        detail = get_stock_detail(code)
        result = evaluate_stock(stock, detail)
        results.append(result)
        print(f" -> {result['grade']}级 {result['score']}分")
    
    # 3. 排序分级
    print("[3/4] 排序分级...")
    results.sort(key=lambda x: x['score'], reverse=True)
    
    s_grade = [r for r in results if r['grade'] == 'S']
    a_grade = [r for r in results if r['grade'] == 'A']
    b_grade = [r for r in results if r['grade'] == 'B']
    c_grade = [r for r in results if r['grade'] == 'C']
    
    # 4. 生成监控列表（取S级+A级前5）
    print("[4/4] 生成监控列表...")
    watchlist = s_grade + a_grade[:5]
    
    # 保存监控列表
    watchlist_json = [
        {
            'code': r['code'],
            'name': r['name'],
            'grade': r['grade'],
            'score': r['score'],
            'reason': r['reason']
        }
        for r in watchlist
    ]
    
    with open(WATCHLIST_FILE, 'w', encoding='utf-8') as f:
        json.dump(watchlist_json, f, ensure_ascii=False, indent=2)
    
    print(f"  监控列表已保存: {len(watchlist_json)} 只股票")
    
    # 5. 生成报告
    report_lines = [
        f"# 涨停板量化评估报告 - {datetime.now().strftime('%Y年%m月%d日')}",
        "",
        f"**评估时间**: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
        f"**涨停总数**: {len(zt_data)} 只",
        "",
        "---",
        "",
        f"## S级（{len(s_grade)}只）- 核心跟仓",
        "",
    ]
    
    for i, r in enumerate(s_grade, 1):
        report_lines.extend([
            f"### {i}. {r['name']}（{r['code']}）· {r['limit_times']}连板 · 得分{r['score']}",
            "",
            f"- **价格**: {r['price']:.2f} 元",
            f"- **封单比**: {r['seal_ratio']*100:.2f}%",
            f"- **换手率**: {r['turnover']:.2f}%",
            f"- **评估**: {r['reason']}",
            "",
        ])
    
    report_lines.extend([
        f"## A级（{len(a_grade)}只）- 可参与",
        "",
    ])
    for i, r in enumerate(a_grade, 1):
        report_lines.extend([
            f"{i}. **{r['name']}**（{r['code']}）· {r['limit_times']}连板 · 得分{r['score']} · {r['reason']}",
        ])
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 监控列表",
        "",
        "以下股票已加入明日早盘监控：",
        "",
    ])
    for r in watchlist:
        report_lines.append(f"- **{r['name']}**（{r['code']}）{r['grade']}级 {r['score']}分")
    
    report_lines.extend([
        "",
        "---",
        "",
        "## 跟板核心原则",
        "",
        "1. **只做龙头，不做杂毛**",
        "2. **封单比 > 2%** 安全，< 0.5% 易炸",
        "3. **换手 3%-10%** 最佳",
        "4. **炸板次数越少越好**",
        "5. **宁可错过，不可做错**",
        "",
    ])
    
    with open(REPORT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(report_lines))
    
    print(f"  报告已保存: {REPORT_FILE}")
    
    # 6. 推送微信通知
    print("[5/4] 推送微信通知...")
    title = f"涨停板筛选完成 · {datetime.now().strftime('%m/%d')}"
    
    content_lines = [
        f"<h2>涨停板量化评估 - {datetime.now().strftime('%m/%d')}</h2>",
        f"<p>共评估 <b>{len(zt_data)}</b> 只涨停股票</p>",
        "<hr>",
        f"<h3>S级（{len(s_grade)}只）- 核心跟仓</h3>",
    ]
    
    for r in s_grade[:3]:
        content_lines.append(
            f"<p><b>{r['name']}（{r['code']}）</b> · {r['limit_times']}连板 · 得分{r['score']}<br/>"
            f"封单比{r['seal_ratio']*100:.2f}% | 换手{r['turnover']:.2f}% | {r['reason']}</p>"
        )
    
    content_lines.extend([
        "<hr>",
        f"<h3>A级（{min(len(a_grade), 5)}只）- 可参与</h3>",
        "<p>" + " · ".join([f"{r['name']}({r['score']}分)" for r in a_grade[:5]]) + "</p>",
        "<hr>",
        f"<p><b>明日监控 {len(watchlist)} 只股票</b></p>",
        "<p><small>明早9:25开始自动监控，满足条件微信通知</small></p>",
    ])
    
    if push_wechat(title, '\n'.join(content_lines)):
        print("  微信推送成功")
    else:
        print("  微信推送失败")
    
    print(f"\n{'='*60}")
    print("筛选完成！")
    print(f"{'='*60}\n")


if __name__ == '__main__':
    run_screening()
