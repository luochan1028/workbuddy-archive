#!/usr/bin/env python3
"""
A股打板分析 - 过去3年数据
使用 AKShare 获取涨停数据并分析最适合打板的股票
"""

import akshare as ak
import pandas as pd
import json
import time
import os
from datetime import datetime, timedelta
from collections import defaultdict

OUTPUT_DIR = r"c:\Users\asus\WorkBuddy\20260530091900"
os.makedirs(OUTPUT_DIR, exist_ok=True)

def fetch_zt_pool(date_str):
    """获取某日的涨停板数据（东方财富）"""
    try:
        df = ak.stock_zt_pool_em(date=date_str)
        if df is not None and not df.empty:
            df['trade_date'] = date_str
        return df
    except Exception as e:
        return None

def analyze_zt_data():
    """主分析函数"""
    print("=" * 70)
    print(" A股打板分析 - 过去3年（2023-05 ~ 2026-05）")
    print("=" * 70)
    
    # 定义时间范围
    start_date = "20230501"
    end_date = "20260530"
    
    # 生成交易日列表
    print("\n[1/5] 生成交易日列表...")
    start_dt = datetime(2023, 5, 1)
    end_dt = datetime(2026, 5, 30)
    trade_dates = []
    current = start_dt
    while current <= end_dt:
        if current.weekday() < 5:
            trade_dates.append(current.strftime("%Y%m%d"))
        current += timedelta(days=1)
    
    print(f"  生成 {len(trade_dates)} 个工作日日期")
    
    # 分批获取数据 - 只取最近的关键日期作为样本
    # 过去3年有约800个交易日，全部拉取太慢
    # 策略：均匀采样，每月取约3-4个交易日
    print(f"\n[2/5] 开始拉取涨停板数据（均匀采样方式）...")
    print("  说明：每10个工作日采样1天，预计约80个交易日样本")
    
    all_zt_data = []
    failed_dates = []
    sample_count = 0
    
    for i, date_str in enumerate(trade_dates):
        # 均匀采样：每10个工作日取1个
        if i % 10 != 0:
            continue
        
        sample_count += 1
        if sample_count % 10 == 0:
            print(f"  进度: {sample_count} 个样本已拉取...")
        
        df = fetch_zt_pool(date_str)
        if df is not None and not df.empty:
            all_zt_data.append(df)
        else:
            failed_dates.append(date_str)
        time.sleep(0.3)
    
    if not all_zt_data:
        print("\n  [ERROR] 未获取到任何涨停数据")
        return
    
    print(f"\n  成功获取 {len(all_zt_data)} 个交易日的数据")
    print(f"  失败/无数据日期: {len(failed_dates)} 个")
    
    # 合并数据
    print("\n[3/5] 合并并清洗数据...")
    df_all = pd.concat(all_zt_data, ignore_index=True)
    print(f"  总记录数: {len(df_all)}")
    print(f"  字段: {list(df_all.columns)}")
    
    # AKShare 返回的字段名
    CODE_COL = '代码'
    NAME_COL = '名称'
    
    # 保存原始数据
    raw_file = os.path.join(OUTPUT_DIR, "zt_data_raw.csv")
    df_all.to_csv(raw_file, index=False, encoding="utf-8-sig")
    print(f"  原始数据已保存: {raw_file}")
    
    # 统计分析
    print("\n[4/5] 统计分析各股票打板表现...")
    
    # 1. 涨停次数统计
    zt_count = df_all[CODE_COL].value_counts().reset_index()
    zt_count.columns = [CODE_COL, '涨停次数']
    
    # 添加名称
    name_map = df_all[[CODE_COL, NAME_COL]].drop_duplicates()
    zt_count = zt_count.merge(name_map, on=CODE_COL, how='left')
    zt_count = zt_count.sort_values('涨停次数', ascending=False).reset_index(drop=True)
    print(f"  共 {len(zt_count)} 只股票出现过涨停")
    
    # 2. 连板能力统计
    # 使用 AKShare 返回的 '连板数' 字段
    if '连板数' in df_all.columns:
        print("\n  使用 '连板数' 字段统计连板能力...")
        lb_stats = df_all.groupby(CODE_COL).agg(
            最大连板数=('连板数', 'max'),
            平均连板数=('连板数', 'mean'),
            连板总次数=('连板数', 'sum')
        ).reset_index()
        lb_stats['平均连板数'] = lb_stats['平均连板数'].round(2)
    else:
        lb_stats = pd.DataFrame(columns=[CODE_COL, '最大连板数', '平均连板数', '连板总次数'])
    
    # 3. 炸板次数统计
    if '炸板次数' in df_all.columns:
        zb_stats = df_all.groupby(CODE_COL).agg(
            总炸板次数=('炸板次数', 'sum'),
            平均炸板次数=('炸板次数', 'mean')
        ).reset_index()
        zb_stats['平均炸板次数'] = zb_stats['平均炸板次数'].round(2)
        zb_stats['炸板率'] = (zb_stats['总炸板次数'] / (zb_stats['总炸板次数'] + 
                               df_all[CODE_COL].value_counts().reindex(zb_stats[CODE_COL]).fillna(0).values)).round(3)
    else:
        zb_stats = pd.DataFrame(columns=[CODE_COL, '总炸板次数', '平均炸板次数', '炸板率'])
    
    # 4. 封板资金统计
    if '封板资金' in df_all.columns:
        fb_stats = df_all.groupby(CODE_COL).agg(
            平均封板资金=('封板资金', 'mean'),
            最大封板资金=('封板资金', 'max')
        ).reset_index()
        fb_stats['平均封板资金'] = fb_stats['平均封板资金'].round(0).astype(int)
        fb_stats['最大封板资金'] = fb_stats['最大封板资金'].round(0).astype(int)
    else:
        fb_stats = pd.DataFrame(columns=[CODE_COL, '平均封板资金', '最大封板资金'])
    
    # 5. 换手率统计
    if '换手率' in df_all.columns:
        hs_stats = df_all.groupby(CODE_COL).agg(
            平均换手率=('换手率', 'mean'),
            最大换手率=('换手率', 'max')
        ).reset_index()
        hs_stats['平均换手率'] = hs_stats['平均换手率'].round(2)
    else:
        hs_stats = pd.DataFrame(columns=[CODE_COL, '平均换手率', '最大换手率'])
    
    # 合并所有统计
    print("\n[5/5] 综合评分...")
    df_score = zt_count.copy()
    
    if not lb_stats.empty:
        df_score = df_score.merge(lb_stats, on=CODE_COL, how='left').fillna(0)
    if not zb_stats.empty:
        df_score = df_score.merge(zb_stats, on=CODE_COL, how='left').fillna(0)
    if not fb_stats.empty:
        df_score = df_score.merge(fb_stats, on=CODE_COL, how='left').fillna(0)
    if not hs_stats.empty:
        df_score = df_score.merge(hs_stats, on=CODE_COL, how='left').fillna(0)
    
    # 综合评分公式：
    # - 涨停次数权重 25%
    # - 最大连板数权重 25%
    # - 封板质量（1-炸板率）权重 20%
    # - 封板资金权重 15%
    # - 连板稳定性（平均连板数）权重 15%
    
    # 先对各维度进行标准化（0-100分制）
    for col in ['涨停次数', '最大连板数', '平均连板数', '平均封板资金']:
        if col in df_score.columns and df_score[col].max() > 0:
            df_score[f'{col}_归一'] = (df_score[col] / df_score[col].max() * 100).round(2)
    
    # 炸板率越低越好
    if '炸板率' in df_score.columns:
        df_score['封板质量_归一'] = ((1 - df_score['炸板率']) * 100).round(2)
    
    # 综合评分
    score = 0
    if '涨停次数_归一' in df_score.columns:
        score += df_score['涨停次数_归一'] * 0.25
    if '最大连板数_归一' in df_score.columns:
        score += df_score['最大连板数_归一'] * 0.25
    if '封板质量_归一' in df_score.columns:
        score += df_score['封板质量_归一'] * 0.20
    if '平均封板资金_归一' in df_score.columns:
        score += df_score['平均封板资金_归一'] * 0.15
    if '平均连板数_归一' in df_score.columns:
        score += df_score['平均连板数_归一'] * 0.15
    
    df_score['综合评分'] = score.round(2)
    
    # 只保留有意义的列
    display_cols = [CODE_COL, NAME_COL, '涨停次数', '最大连板数', '平均连板数', 
                    '总炸板次数', '炸板率', '平均封板资金', '平均换手率', '综合评分']
    display_cols = [c for c in display_cols if c in df_score.columns]
    
    df_score = df_score.sort_values('综合评分', ascending=False).reset_index(drop=True)
    
    print("\n" + "=" * 70)
    print(" *** A股打板综合评分 - Top 30 ***")
    print("=" * 70)
    print(f"\n{'排名':<5}{'代码':<10}{'名称':<10}{'涨停次数':<8}{'最大连板':<8}{'炸板率':<8}{'综合评分':<8}")
    print("-" * 70)
    
    for i, row in df_score.head(30).iterrows():
        name = row.get(NAME_COL, '')
        code = row[CODE_COL]
        zt_c = int(row['涨停次数'])
        max_lb = int(row.get('最大连板数', 0))
        zb_r = f"{row.get('炸板率', 0):.2f}" if '炸板率' in row else '-'
        score = row['综合评分']
        print(f"{i+1:<5}{code:<10}{name:<10}{zt_c:<8}{max_lb:<8}{zb_r:<8}{score:<8.2f}")
    
    # 保存完整结果
    result_file = os.path.join(OUTPUT_DIR, "zt_analysis_result.csv")
    df_score.to_csv(result_file, index=False, encoding="utf-8-sig")
    
    # 保存为 JSON
    result_json = os.path.join(OUTPUT_DIR, "zt_analysis_result.json")
    df_score.head(100).to_json(result_json, orient='records', force_ascii=False)
    
    print(f"\n完整结果已保存:")
    print(f"   - {result_file} (CSV)")
    print(f"   - {result_json} (JSON, Top 100)")
    
    print("\n" + "=" * 70)
    print(" 分析完成！")
    print("=" * 70)
    
    # 额外分析：哪些行业板块最容易出涨停？
    if '所属行业' in df_all.columns:
        print("\n\n[附] 涨停最多的行业板块 Top 10")
        industry_zt = df_all['所属行业'].value_counts().head(10)
        for ind, count in industry_zt.items():
            print(f"   {ind}: {count} 次涨停")
    
    return df_score

if __name__ == "__main__":
    analyze_zt_data()
