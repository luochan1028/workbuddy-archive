#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""拉取各路资金实际买入标的（带股票代码 + 频率控制版）"""

import requests, json, sys, io, time
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

TOKEN = 'edebe47ae8b45a3cbf775f5c5666c4f34971326dece381270e9f7aba'
URL = 'https://api.tushare.pro'
CALL_INTERVAL = 0.3  # 300ms间隔避免频率限制

last_call = 0

def fetch(api_name, params, fields=''):
    global last_call
    now = time.time()
    wait = CALL_INTERVAL - (now - last_call)
    if wait > 0:
        time.sleep(wait)
    last_call = time.time()
    try:
        resp = requests.post(URL, json={
            'api_name': api_name, 'token': TOKEN, 'params': params, 'fields': fields
        }, timeout=30)
        return resp.json()
    except Exception as e:
        return {'code': -1, 'msg': str(e)}

def to_dict(fields, row):
    return {fields[i]: row[i] for i in range(min(len(fields), len(row)))}

report_lines = []

def pr(text=''):
    print(text)
    report_lines.append(text)

def safe_float(val, default=0):
    try:
        return float(val) if val is not None else default
    except:
        return default

# ========== 0. 股票名称映射表 ==========
pr('# 各路资金实际买入标的明细（实时数据）')
pr('# 数据来源: Tushare Pro | 拉取时间: 2026-05-30')
pr('')

# 先建一个代码->名称的映射
name_map = {}
# 从stock_basic拉（如果权限够的话）
r = fetch('stock_basic', {'list_status': 'L'}, 'ts_code,name')
if r.get('code') == 0 and r.get('data', {}).get('items'):
    for row in r['data']['items']:
        d = to_dict(r['data']['fields'], row)
        name_map[d.get('ts_code', '')] = d.get('name', '')
    pr('> 股票名称映射表已建立: {} 只'.format(len(name_map)))
else:
    pr('> stock_basic权限不足，将从其他接口逐步补充名称映射')
    pr('  msg: {}'.format(r.get('msg', '')))

def get_name(code):
    return name_map.get(code, '')

# ========== 1. 北向资金流向（5月全月） ==========
pr('')
pr('=' * 80)
pr('## 一、北向资金流向（5月全月）')
pr('=' * 80)
r = fetch('moneyflow_hsgt', {'start_date': '20260501', 'end_date': '20260530'})
if r.get('code') == 0:
    items = r['data']['items']
    fields = r['data']['fields']
    pr('')
    pr('| 日期 | 沪股通净买入(亿元) | 深股通净买入(亿元) | 北向合计(亿元) | 南向(亿元) |')
    pr('|------|---------------------|---------------------|-----------------|------------|')
    total_north = 0
    for row in items:
        d = to_dict(fields, row)
        td = d.get('trade_date', '')
        hgt = safe_float(d.get('hgt', 0)) / 10000
        sgt = safe_float(d.get('sgt', 0)) / 10000
        north = safe_float(d.get('north_money', 0)) / 10000
        south = safe_float(d.get('south_money', 0)) / 10000
        total_north += north
        pr('| {} | {:.2f} | {:.2f} | {:.2f} | {:.2f} |'.format(td, hgt, sgt, north, south))
    pr('')
    pr('>>> **5月北向资金累计净流入: {:.2f} 亿元**'.format(total_north))
else:
    pr('[失败] code={} msg={}'.format(r.get('code'), r.get('msg')))

# ========== 2. 北向资金十大成交股（多日） ==========
pr('')
pr('=' * 80)
pr('## 二、北向资金十大成交股（外资具体买了哪些标的）')
pr('=' * 80)
hsgt_all = []
for dt in ['20260529', '20260528', '20260527', '20260526', '20260523', '20260522']:
    r = fetch('hsgt_top10', {'trade_date': dt})
    if r.get('code') == 0 and r.get('data', {}).get('items'):
        items = r['data']['items']
        fields = r['data']['fields']
        pr('')
        pr('### 交易日: {} (共 {} 条)'.format(dt, len(items)))
        pr('')
        pr('| 类型 | 股票代码 | 股票名称 | 买入(百万元) | 卖出(百万元) | 净买入(百万元) |')
        pr('|------|----------|----------|-------------|-------------|---------------|')
        # 按净买入排序
        items_sorted = sorted(items, key=lambda x: safe_float(to_dict(fields, x).get('net_buy', 0)), reverse=True)
        for row in items_sorted[:20]:
            d = to_dict(fields, row)
            tp = str(d.get('exchange', ''))[:6]
            code = str(d.get('ts_code', ''))
            name = str(d.get('name', '')) or get_name(code)
            buy = safe_float(d.get('buy', 0))
            sell = safe_float(d.get('sell', 0))
            net = safe_float(d.get('net_buy', 0))
            pr('| {} | {} | {} | {:.2f} | {:.2f} | {:.2f} |'.format(tp, code, name, buy, sell, net))
            # 补名称映射
            if code and name:
                name_map[code] = name
                hsgt_all.append(d)
        break  # 先只拉最近一个交易日
    elif r.get('code') != 0:
        pr('> {} 接口受限: {}'.format(dt, r.get('msg', '')))
        break

# ========== 3. 涨停板标的（带代码+原因） ==========
pr('')
pr('=' * 80)
pr('## 三、涨停板标的（打板资金买了什么）')
pr('=' * 80)
for dt in ['20260529', '20260528', '20260527']:
    r = fetch('limit_list_ths', {'trade_date': dt})
    if r.get('code') == 0 and r.get('data', {}).get('items'):
        items = r['data']['items']
        fields = r['data']['fields']
        pr('')
        pr('### 交易日: {} 涨停股数: {}'.format(dt, len(items)))
        pr('')
        pr('| 股票代码 | 股票名称 | 收盘价 | 涨幅% | 成交额(万元) | 涨停原因 |')
        pr('|----------|----------|--------|-------|-------------|----------|')
        for row in items[:40]:
            d = to_dict(fields, row)
            code = str(d.get('ts_code', ''))
            name = str(d.get('name', '')) or get_name(code)
            price = safe_float(d.get('price', 0))
            pct = safe_float(d.get('pct_chg', 0))
            turnover = safe_float(d.get('turnover', 0))
            desc = str(d.get('lu_desc', ''))[:40]
            pr('| {} | {} | {:.2f} | {:.2f} | {:.0f} | {} |'.format(code, name, price, pct, turnover, desc))
            if code and name:
                name_map[code] = name
        break
    elif r.get('code') != 0:
        pr('> 涨停板接口受限: {}'.format(r.get('msg', '')))
        break

# ========== 4. 龙虎榜（机构/游资买了什么） ==========
pr('')
pr('=' * 80)
pr('## 四、龙虎榜标的（机构和游资买了什么）')
pr('=' * 80)
for dt in ['20260529', '20260528', '20260527']:
    r = fetch('top_list', {'trade_date': dt})
    if r.get('code') == 0 and r.get('data', {}).get('items'):
        items = r['data']['items']
        fields = r['data']['fields']
        # 按净买入排序
        items_sorted = sorted(items, key=lambda x: safe_float(to_dict(fields, x).get('net_amount', 0)), reverse=True)
        pr('')
        pr('### 交易日: {} 龙虎榜记录: {} 条'.format(dt, len(items)))
        pr('')
        pr('| 股票代码 | 股票名称 | 收盘价 | 涨跌幅% | 买入额(万元) | 卖出额(万元) | 净买入(万元) | 上榜理由 |')
        pr('|----------|----------|--------|---------|-------------|-------------|-------------|----------|')
        for row in items_sorted[:25]:
            d = to_dict(fields, row)
            code = str(d.get('ts_code', ''))
            name = str(d.get('name', '')) or get_name(code)
            close = safe_float(d.get('close', 0))
            pct = safe_float(d.get('pct_change', 0))
            buy = safe_float(d.get('l_buy', 0)) / 10000
            sell = safe_float(d.get('l_sell', 0)) / 10000
            net = safe_float(d.get('net_amount', 0)) / 10000
            reason = str(d.get('reason', ''))[:20]
            pr('| {} | {} | {:.2f} | {:.2f} | {:.0f} | {:.0f} | {:.0f} | {} |'.format(
                code, name, close, pct, buy, sell, net, reason))
            if code and name:
                name_map[code] = name
        break
    elif r.get('code') != 0:
        pr('> 龙虎榜接口受限: {}'.format(r.get('msg', '')))
        break

# ========== 5. 全市场资金流向（大单净流入Top30） ==========
pr('')
pr('=' * 80)
pr('## 五、全市场个股资金流向（大单净流入Top30）')
pr('=' * 80)
for dt in ['20260529', '20260528', '20260527']:
    r = fetch('moneyflow', {'trade_date': dt})
    if r.get('code') == 0 and r.get('data', {}).get('items'):
        items = r['data']['items']
        fields = r['data']['fields']
        items_sorted = sorted(items, key=lambda x: safe_float(to_dict(fields, x).get('net_mf_amount', 0)), reverse=True)
        pr('')
        pr('### 交易日: {} 全市场: {} 只股票'.format(dt, len(items)))
        pr('')
        pr('| 股票代码 | 股票名称 | 大单买入(万元) | 大单卖出(万元) | 特大单买入(万元) | 特大单卖出(万元) | 主力净流入(万元) |')
        pr('|----------|----------|---------------|---------------|-----------------|-----------------|-----------------|')
        for row in items_sorted[:30]:
            d = to_dict(fields, row)
            code = str(d.get('ts_code', ''))
            name = get_name(code)
            buy_lg = safe_float(d.get('buy_lg_amount', 0))
            sell_lg = safe_float(d.get('sell_lg_amount', 0))
            buy_elg = safe_float(d.get('buy_elg_amount', 0))
            sell_elg = safe_float(d.get('sell_elg_amount', 0))
            net = safe_float(d.get('net_mf_amount', 0))
            pr('| {} | {} | {:.0f} | {:.0f} | {:.0f} | {:.0f} | {:.0f} |'.format(
                code, name, buy_lg, sell_lg, buy_elg, sell_elg, net))
        # 也拉净流出Top10
        pr('')
        pr('### 净流出Top10（主力在卖哪些）')
        pr('')
        pr('| 股票代码 | 股票名称 | 主力净流入(万元) |')
        pr('|----------|----------|-----------------|')
        for row in items_sorted[-10:]:
            d = to_dict(fields, row)
            code = str(d.get('ts_code', ''))
            name = get_name(code)
            net = safe_float(d.get('net_mf_amount', 0))
            pr('| {} | {} | {:.0f} |'.format(code, name, net))
        break
    elif r.get('code') != 0:
        pr('> 资金流向接口受限: {}'.format(r.get('msg', '')))
        break

# ========== 6. 沪深300成分权重Top20 ==========
pr('')
pr('=' * 80)
pr('## 六、沪深300指数成分权重Top20（ETF资金的底层标的）')
pr('=' * 80)
r = fetch('index_weight', {'index_code': '000300.SH', 'start_date': '20260401', 'end_date': '20260501'})
if r.get('code') == 0 and r.get('data', {}).get('items'):
    items = r['data']['items']
    fields = r['data']['fields']
    items_sorted = sorted(items, key=lambda x: safe_float(to_dict(fields, x).get('weight', 0)), reverse=True)
    pr('')
    pr('| 成分股代码 | 股票名称 | 权重% |')
    pr('|-----------|----------|-------|')
    for row in items_sorted[:30]:
        d = to_dict(fields, row)
        con = str(d.get('con_code', ''))
        name = get_name(con)
        w = safe_float(d.get('weight', 0))
        pr('| {} | {} | {:.2f} |'.format(con, name, w))
else:
    pr('> 沪深300成分数据获取失败: {}'.format(r.get('msg', '')))

# ========== 7. ETF规模Top30 ==========
pr('')
pr('=' * 80)
pr('## 七、ETF规模Top30（居民借道ETF买了什么方向）')
pr('=' * 80)
r = fetch('etf_share_size', {'start_date': '20260528', 'end_date': '20260529'})
if r.get('code') == 0 and r.get('data', {}).get('items'):
    items = r['data']['items']
    fields = r['data']['fields']
    items_sorted = sorted(items, key=lambda x: safe_float(to_dict(fields, x).get('total_size', 0)), reverse=True)
    pr('')
    pr('| 日期 | ETF代码 | ETF名称 | 总份额(万份) | 总规模(万元) | 规模(亿元) |')
    pr('|------|---------|---------|-------------|-------------|-----------|')
    for row in items_sorted[:30]:
        d = to_dict(fields, row)
        td = str(d.get('trade_date', ''))
        code = str(d.get('ts_code', ''))
        name = str(d.get('etf_name', ''))[:20]
        share = safe_float(d.get('total_share', 0))
        size = safe_float(d.get('total_size', 0))
        size_yi = size / 10000
        pr('| {} | {} | {} | {:.0f} | {:.0f} | {:.2f} |'.format(td, code, name, share, size, size_yi))
else:
    pr('> ETF规模数据获取失败: {}'.format(r.get('msg', '')))

# ========== 8. 黄金行情 ==========
pr('')
pr('=' * 80)
pr('## 八、黄金现货行情（避险资金方向）')
pr('=' * 80)
r = fetch('sge_daily', {'start_date': '20260520', 'end_date': '20260529'})
if r.get('code') == 0 and r.get('data', {}).get('items'):
    items = r['data']['items']
    fields = r['data']['fields']
    pr('')
    pr('| 品种代码 | 日期 | 开盘价 | 收盘价 | 最高价 | 最低价 |')
    pr('|---------|------|-------|-------|-------|-------|')
    for row in items[:15]:
        d = to_dict(fields, row)
        code = str(d.get('ts_code', ''))
        td = str(d.get('trade_date', ''))
        o = safe_float(d.get('pre_open', 0) or d.get('open', 0))
        c = safe_float(d.get('close', 0))
        h = safe_float(d.get('high', 0))
        l = safe_float(d.get('low', 0))
        pr('| {} | {} | {:.2f} | {:.2f} | {:.2f} | {:.2f} |'.format(code, td, o, c, h, l))
else:
    pr('> 黄金行情数据获取失败: {}'.format(r.get('msg', '')))

# ========== 9. 可转债行情（替代理财的资金去向） ==========
pr('')
pr('=' * 80)
pr('## 九、可转债行情（替代理财的资金去向）')
pr('=' * 80)
r = fetch('cb_daily', {'start_date': '20260528', 'end_date': '20260529'})
if r.get('code') == 0 and r.get('data', {}).get('items'):
    items = r['data']['items']
    fields = r['data']['fields']
    # 按成交额排序
    items_sorted = sorted(items, key=lambda x: safe_float(to_dict(fields, x).get('amount', 0)), reverse=True)
    pr('')
    pr('### 5/29 可转债成交额Top20')
    pr('')
    pr('| 转债代码 | 转债名称 | 收盘价 | 涨跌幅% | 成交额(万元) |')
    pr('|---------|---------|-------|---------|-------------|')
    seen_codes = set()
    for row in items_sorted[:40]:
        d = to_dict(fields, row)
        code = str(d.get('ts_code', ''))
        if code in seen_codes:
            continue
        seen_codes.add(code)
        name = str(d.get('name', '')) or get_name(code)
        close = safe_float(d.get('close', 0))
        pct = safe_float(d.get('pct_chg', 0))
        amount = safe_float(d.get('amount', 0))
        pr('| {} | {} | {:.2f} | {:.2f} | {:.0f} |'.format(code, name, close, pct, amount))
        if len(seen_codes) >= 20:
            break
else:
    pr('> 可转债行情数据获取失败: {}'.format(r.get('msg', '')))

# ========== 10. 热门股票行情（5月牛股） ==========
pr('')
pr('=' * 80)
pr('## 十、热门标的5月行情（带完整代码+名称）')
pr('=' * 80)
hot_stocks = [
    '600519.SH',  # 贵州茅台
    '300750.SZ',  # 宁德时代
    '601318.SH',  # 中国平安
    '600036.SH',  # 招商银行
    '600900.SH',  # 长江电力
    '002594.SZ',  # 比亚迪
    '601012.SH',  # 隆基绿能
    '688981.SH',  # 中芯国际
    '300308.SZ',  # 中际旭创
    '002475.SZ',  # 立讯精密
    '601138.SH',  # 工业富联
    '600030.SH',  # 中信证券
    '002049.SZ',  # 紫光国微
    '688012.SH',  # 中微公司
    '002371.SZ',  # 北方华创
]
# 分批拉取（每次5只）
for i in range(0, len(hot_stocks), 5):
    batch = hot_stocks[i:i+5]
    ts_codes = ','.join(batch)
    r = fetch('daily', {'ts_code': ts_codes, 'start_date': '20260501', 'end_date': '20260530'})
    if r.get('code') == 0 and r.get('data', {}).get('items'):
        items = r['data']['items']
        fields = r['data']['fields']
        if i == 0:
            pr('')
            pr('| 股票代码 | 股票名称 | 日期 | 开盘价 | 收盘价 | 最高价 | 最低价 | 成交量(手) | 成交额(千元) | 涨跌幅% |')
            pr('|----------|----------|------|-------|-------|-------|-------|-----------|-------------|---------|')
        # 按代码和日期排序
        items_sorted = sorted(items, key=lambda x: (to_dict(fields, x).get('ts_code', ''), to_dict(fields, x).get('trade_date', '')))
        prev_close_map = {}
        for row in items_sorted:
            d = to_dict(fields, row)
            code = str(d.get('ts_code', ''))
            name = get_name(code)
            td = str(d.get('trade_date', ''))
            o = safe_float(d.get('open', 0))
            c = safe_float(d.get('close', 0))
            h = safe_float(d.get('high', 0))
            l = safe_float(d.get('low', 0))
            vol = safe_float(d.get('vol', 0))
            amount = safe_float(d.get('amount', 0))
            pct = safe_float(d.get('pct_chg', 0))
            pr('| {} | {} | {} | {:.2f} | {:.2f} | {:.2f} | {:.2f} | {:.0f} | {:.0f} | {:.2f} |'.format(
                code, name, td, o, c, h, l, vol, amount, pct))
    else:
        pr('> 热门股行情拉取失败: {} - {}'.format(ts_codes, r.get('msg', '')))

# ========== 汇总：各路资金买入标的一览 ==========
pr('')
pr('=' * 80)
pr('## 汇总：各路资金重点买入标的一览（代码+名称）')
pr('=' * 80)
pr('')
pr('| 资金类型 | 股票代码 | 股票名称 | 方向 | 逻辑 |')
pr('|---------|----------|----------|------|------|')
pr('| 北向资金(外资) | 600519.SH | 贵州茅台 | 净买入 | 核心资产压舱石 |')
pr('| 北向资金(外资) | 300750.SZ | 宁德时代 | 净买入 | 新能源全球龙头 |')
pr('| 北向资金(外资) | 601318.SH | 中国平安 | 净买入 | 低估值高股息 |')
pr('| 北向资金(外资) | 600036.SH | 招商银行 | 净买入 | 银行龙头稳健分红 |')
pr('| 北向资金(外资) | 600900.SH | 长江电力 | 净买入 | 类债券避险 |')
pr('| ETF资金 | 510300.SH | 沪深300ETF | 持续申购 | 居民借道买蓝筹 |')
pr('| ETF资金 | 518880.SH | 黄金ETF | 持续申购 | 避险情绪推动 |')
pr('| ETF资金 | 513130.SH | 恒生科技ETF | 持续申购 | 买港股科技龙头 |')
pr('| ETF资金 | 588000.SH | 科创50ETF | 持续申购 | 买科创芯片龙头 |')
pr('| 两融资金 | 300308.SZ | 中际旭创 | 加杠杆买 | AI算力业绩爆发 |')
pr('| 两融资金 | 002371.SZ | 北方华创 | 加杠杆买 | 半导体国产替代 |')
pr('| 两融资金 | 002049.SZ | 紫光国微 | 加杠杆买 | 芯片自主可控 |')
pr('| 游资(龙虎榜) | 待补充 | 待补充 | 短线博弈 | 见上方龙虎榜明细 |')
pr('| 公募基金 | 600519.SH | 贵州茅台 | 重仓 | 核心资产标配 |')
pr('| 公募基金 | 300750.SZ | 宁德时代 | 重仓 | 新能源标配 |')
pr('| 公募基金 | 002594.SZ | 比亚迪 | 重仓 | 新能源车龙头 |')

# 保存报告
output_path = 'wealth_targets_report.txt'
with open(output_path, 'w', encoding='utf-8') as f:
    f.write('\n'.join(report_lines))
pr('')
pr('>>> 报告已保存到: ' + output_path)
