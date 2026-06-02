#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
涨停股买入条件实时监控
监控今日筛选出的重点股票，满足买入条件时微信推送通知
"""

import urllib.request
import json
import ssl
import os
import time
from datetime import datetime
from pathlib import Path

# ============ 配置 ============
# PushPlus Token
TOKEN_FILE = "c:/Users/asus/.workbuddy/skills/pushplus-wechat/token.txt"
PUSHPLUS_URL = "http://www.pushplus.plus/send"

# 监控列表文件
WATCHLIST_FILE = "c:/Users/asus/WorkBuddy/20260530084842/monitor_watchlist.json"

# 状态记录文件（避免重复推送）
STATE_FILE = "c:/Users/asus/WorkBuddy/20260530084842/monitor_state.json"

# 买入条件阈值
CONDITIONS = {
    "封单比最小值": 0.02,      # 封单比 > 2%
    "封单比理想值": 0.05,      # 封单比 > 5% 为理想
    "换手率上限": 0.15,        # 换手率 < 15%
    "换手率理想上限": 0.10,    # 换手率 < 10% 最理想
    "接近涨停阈值": 0.995,     # 当前价 >= 涨停价 * 0.995
    "炸板回落阈值": 0.97,      # 从涨停回落不超过 3%
}

# 东方财富API
EM_API = "http://push2.eastmoney.com/api/qt/stock/get"


# ============ 工具函数 ============

def load_token():
    """读取PushPlus Token"""
    try:
        with open(TOKEN_FILE, 'r', encoding='utf-8') as f:
            return f.read().strip()
    except Exception as e:
        print(f"[ERROR] 读取Token失败: {e}")
        return None


def load_watchlist():
    """加载监控列表"""
    try:
        with open(WATCHLIST_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"[ERROR] 加载监控列表失败: {e}")
        return []


def load_state():
    """加载推送状态（避免重复推送）"""
    try:
        with open(STATE_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def save_state(state):
    """保存推送状态"""
    try:
        with open(STATE_FILE, 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[ERROR] 保存状态失败: {e}")


def get_stock_data(code):
    """
    获取单只股票实时数据
    code: 如 '301439' 或 'sh600162'
    """
    # 判断市场: 0=深市, 1=沪市, 0.港股通深市... 
    # 创业板/深市: 0.code
    # 沪市: 1.code
    # 北交所: 0.code (bj开头)
    if code.startswith('6'):
        secid = f"1.{code}"
    else:
        secid = f"0.{code}"
    
    url = f"{EM_API}?secid={secid}&fields=f43,f44,f45,f46,f47,f48,f19,f20,f92,f117,f60"
    
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
        
        # 解析数据（价格类需除100）
        result = {
            'code': code,
            'name': d.get('f58', code),
            'price': d.get('f43', 0) / 100 if d.get('f43') else 0,
            'high': d.get('f44', 0) / 100 if d.get('f44') else 0,
            'low': d.get('f45', 0) / 100 if d.get('f45') else 0,
            'open': d.get('f46', 0) / 100 if d.get('f46') else 0,
            'volume': d.get('f47', 0),           # 成交量(手)
            'amount': d.get('f48', 0),           # 成交额(元)
            'bid_price': d.get('f19', 0) / 100 if d.get('f19') else 0,  # 买一价
            'bid_vol': d.get('f20', 0),          # 买一量(手)
            'turnover_rate': d.get('f92', 0) / 100 if d.get('f92') else 0,  # 换手率%
            'float_cap': d.get('f117', 0),       # 流通市值(元)
            'pre_close': d.get('f60', 0) / 100 if d.get('f60') else 0,  # 昨收
        }
        
        # 计算涨停价
        if code.startswith('68') or code.startswith('30') or code.startswith('8'):
            result['limit_up_price'] = round(result['pre_close'] * 1.2, 2)
        else:
            result['limit_up_price'] = round(result['pre_close'] * 1.1, 2)
        
        # 计算封单比
        if result['price'] >= result['limit_up_price'] * 0.999 and result['bid_vol'] > 0 and result['float_cap'] > 0:
            # 封单金额 = 买一量(手) * 100(股/手) * 买一价
            seal_amount = result['bid_vol'] * 100 * result['bid_price']
            result['seal_ratio'] = seal_amount / result['float_cap']
        else:
            result['seal_ratio'] = 0
        
        return result
        
    except Exception as e:
        print(f"[ERROR] 获取 {code} 数据失败: {e}")
        return None


def evaluate_stock(data, ref_data=None):
    """
    评估股票是否满足买入条件
    返回: (signal_type, score, details)
    signal_type: None/'秒板'/'回封'/'强势高开'
    """
    if not data:
        return None, 0, "无数据"
    
    code = data['code']
    price = data['price']
    high = data['high']
    low = data['low']
    open_price = data['open']
    limit_up = data['limit_up_price']
    turnover = data['turnover_rate']
    seal_ratio = data['seal_ratio']
    bid_vol = data['bid_vol']
    
    details = []
    score = 0
    signal = None
    
    # 条件1: 已涨停且封单足够
    is_limit_up = price >= limit_up * 0.999
    seal_ok = seal_ratio >= CONDITIONS['封单比最小值']
    seal_good = seal_ratio >= CONDITIONS['封单比理想值']
    turnover_ok = turnover <= CONDITIONS['换手率上限']
    turnover_good = turnover <= CONDITIONS['换手率理想上限']
    
    # 条件2: 炸板回封判断
    # 曾经到过涨停(最高价=涨停价)，当前又涨停，且中间有过回落
    was_limit_up = high >= limit_up * 0.999
    is_broken = was_limit_up and low < limit_up * CONDITIONS['炸板回落阈值']
    is_resealed = is_broken and is_limit_up
    
    # 条件3: 强势高开
    # 开盘价 >= 昨日涨停价，且当前继续上涨
    strong_open = open_price >= limit_up * 0.99 and price >= open_price
    
    # ===== 信号判断 =====
    
    # A. 开盘秒板（9:30-9:35 内封死涨停，封单比>2%）
    if is_limit_up and seal_ok and turnover_ok:
        if not is_broken:
            signal = '秒板'
            score = 80
            details.append(f"开盘秒板，封单比 {seal_ratio*100:.2f}%")
        elif is_resealed and seal_ok:
            signal = '回封'
            score = 70
            details.append(f"炸板回封，封单比 {seal_ratio*100:.2f}%")
    
    # B. 强势高开（高开5%以上且快速拉升）
    elif strong_open and not is_limit_up:
        # 高开但未涨停，观察是否值得追
        gain_pct = (price - data['pre_close']) / data['pre_close'] * 100
        if gain_pct >= 5 and turnover <= 10:
            signal = '强势高开'
            score = 50
            details.append(f"强势高开 {gain_pct:.1f}%，换手 {turnover:.2f}%")
    
    # 加分项
    if seal_good:
        score += 10
        details.append(f"封单比优秀 ({seal_ratio*100:.1f}%)")
    if turnover_good:
        score += 5
        details.append(f"换手率健康 ({turnover:.2f}%)")
    if bid_vol > 50000:
        score += 5
        details.append(f"封单量大 ({bid_vol}手)")
    
    # 减分项
    if is_broken and not is_resealed:
        score -= 20
        details.append("炸板未回封，风险高")
    if turnover > 15:
        score -= 15
        details.append(f"换手率过高 ({turnover:.2f}%)")
    
    # 最终判断
    if score >= 70 and signal in ['秒板', '回封']:
        return signal, score, " | ".join(details)
    elif score >= 50 and signal == '强势高开':
        return signal, score, " | ".join(details)
    else:
        return None, score, " | ".join(details) if details else "不满足买入条件"


def push_wechat(title, content):
    """推送微信通知"""
    token = load_token()
    if not token:
        print("[ERROR] Token不可用")
        return False
    
    data = {
        "token": token,
        "title": title,
        "content": content,
        "template": "html"
    }
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(
            PUSHPLUS_URL,
            data=json.dumps(data).encode('utf-8'),
            headers={'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'}
        )
        resp = urllib.request.urlopen(req, context=ctx, timeout=10)
        result = json.loads(resp.read().decode('utf-8'))
        
        if result.get('code') == 200:
            print(f"[OK] 微信推送成功: {title}")
            return True
        else:
            print(f"[FAIL] 微信推送失败: {result}")
            return False
            
    except Exception as e:
        print(f"[ERROR] 推送异常: {e}")
        return False


def run_monitor():
    """主监控循环"""
    print(f"\n{'='*60}")
    print(f"涨停股买入监控启动 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    watchlist = load_watchlist()
    if not watchlist:
        print("[WARN] 监控列表为空，请先创建 watchlist")
        return
    
    state = load_state()
    today = datetime.now().strftime('%Y%m%d')
    
    signals_found = []
    
    for stock in watchlist:
        code = stock['code']
        name = stock.get('name', code)
        
        print(f"\n监控: {name}({code})")
        
        # 获取实时数据
        data = get_stock_data(code)
        if not data:
            print(f"  [SKIP] 获取数据失败")
            continue
        
        # 打印当前状态
        print(f"  价格: {data['price']:.2f} | 涨停价: {data['limit_up_price']:.2f}")
        print(f"  换手: {data['turnover_rate']:.2f}% | 封单比: {data['seal_ratio']*100:.2f}%")
        
        # 评估买入条件
        signal, score, details = evaluate_stock(data)
        
        if signal:
            print(f"  [SIGNAL] {signal} | 得分: {score} | {details}")
            
            # 检查今天是否已经推送过该信号
            state_key = f"{today}_{code}_{signal}"
            if state_key not in state:
                # 推送微信
                title = f"买入信号 · {name}({code}) · {signal}"
                content = f"""<h2>{name} ({code}) - {signal}</h2>
<p><b>当前价格:</b> {data['price']:.2f} 元</p>
<p><b>涨停价:</b> {data['limit_up_price']:.2f} 元</p>
<p><b>封单比:</b> {data['seal_ratio']*100:.2f}%</p>
<p><b>换手率:</b> {data['turnover_rate']:.2f}%</p>
<p><b>得分:</b> {score}/100</p>
<p><b>详情:</b> {details}</p>
<hr>
<p><small>监控时间: {datetime.now().strftime('%H:%M:%S')}</small></p>
"""
                if push_wechat(title, content):
                    state[state_key] = {
                        'time': datetime.now().strftime('%H:%M:%S'),
                        'signal': signal,
                        'score': score
                    }
                    signals_found.append({
                        'code': code,
                        'name': name,
                        'signal': signal,
                        'score': score
                    })
            else:
                print(f"  [SKIP] 今天已推送过 {signal} 信号")
        else:
            print(f"  [PASS] {details}")
    
    # 保存状态
    save_state(state)
    
    print(f"\n{'='*60}")
    if signals_found:
        print(f"本次监控发现 {len(signals_found)} 个买入信号，已推送微信")
    else:
        print("本次监控未发现买入信号")
    print(f"{'='*60}\n")
    
    return signals_found


def run_monitor_loop(duration_minutes=30, interval_seconds=60):
    """持续监控循环"""
    print(f"启动持续监控: 时长 {duration_minutes}分钟, 间隔 {interval_seconds}秒")
    
    end_time = time.time() + duration_minutes * 60
    check_count = 0
    
    while time.time() < end_time:
        check_count += 1
        print(f"\n>>> 第 {check_count} 次检查 <<<")
        run_monitor()
        
        remaining = end_time - time.time()
        if remaining > 0:
            print(f"等待 {interval_seconds} 秒后进行下一次检查...")
            time.sleep(interval_seconds)
    
    print(f"监控结束，共检查 {check_count} 次")


if __name__ == '__main__':
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == '--loop':
        # 持续监控模式
        duration = int(sys.argv[2]) if len(sys.argv) > 2 else 30
        interval = int(sys.argv[3]) if len(sys.argv) > 3 else 60
        run_monitor_loop(duration, interval)
    else:
        # 单次检查模式
        run_monitor()
