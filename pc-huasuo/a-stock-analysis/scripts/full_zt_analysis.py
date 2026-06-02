#!/usr/bin/env python3
"""
A股打板综合分析 - 使用AKShare多数据源
"""

import akshare as ak
import pandas as pd
import numpy as np
import time
import os
import warnings
warnings.filterwarnings('ignore')

OUTPUT_DIR = r"c:\Users\asus\WorkBuddy\20260530091900"

def safe_fetch(func, *args, **kwargs):
    """安全调用AKShare函数"""
    try:
        return func(*args, **kwargs)
    except:
        return None

def main():
    print("=" * 70)
    print(" A股打板综合分析报告")
    print(" 数据来源: AKShare + 东方财富")
    print("=" * 70)
    
    # ============================================================
    # 第一步: 获取最近可用的涨停数据（多日汇总）
    # ============================================================
    print("\n[1] 获取近期涨停板数据...")
    
    # 获取最近几天的涨停数据
    recent_dates = ['20260529', '20260528', '20260527', '20260526', '20260523', '20260522', '20260521', '20260520']
    all_zt = []
    for d in recent_dates:
        df = safe_fetch(ak.stock_zt_pool_em, date=d)
        if df is not None and not df.empty:
            df['trade_date'] = d
            all_zt.append(df)
            print(f"  {d}: {len(df)} 只涨停")
        time.sleep(0.2)
    
    if not all_zt:
        print("  [ERROR] 无法获取涨停数据")
        return
    
    df_zt = pd.concat(all_zt, ignore_index=True)
    print(f"  总计: {len(df_zt)} 条涨停记录, {df_zt['代码'].nunique()} 只个股")
    
    # ============================================================
    # 第二步: 涨停股统计
    # ============================================================
    print("\n[2] 近期涨停次数排名 (Top 20)...")
    zt_freq = df_zt['代码'].value_counts().reset_index()
    zt_freq.columns = ['代码', '涨停次数']
    name_map = df_zt[['代码', '名称']].drop_duplicates()
    zt_freq = zt_freq.merge(name_map, on='代码', how='left')
    
    print(f"  {'代码':<10} {'名称':<10} {'涨停次数':>8}")
    print("  " + "-" * 35)
    for _, r in zt_freq.head(20).iterrows():
        print(f"  {r['代码']:<10} {r['名称']:<10} {r['涨停次数']:>8}")
    
    # ============================================================
    # 第三步: 连板能力分析
    # ============================================================
    print("\n[3] 连板能力分析...")
    if '连板数' in df_zt.columns:
        lb_max = df_zt.groupby('代码').agg(
            最大连板=('连板数', 'max'),
            平均连板=('连板数', 'mean')
        ).reset_index()
        lb_max['平均连板'] = lb_max['平均连板'].round(1)
        lb_max = lb_max.merge(name_map, on='代码', how='left')
        lb_max = lb_max.sort_values('最大连板', ascending=False)
        
        print(f"  Top 10 连板能力:")
        for _, r in lb_max.head(10).iterrows():
            print(f"  {r['代码']:<10} {r['名称']:<10} 最大{r['最大连板']:.0f}连板, 平均{r['平均连板']:.1f}")
    
    # ============================================================
    # 第四步: 炸板率分析
    # ============================================================
    print("\n[4] 封板质量分析 (炸板率)...")
    if '炸板次数' in df_zt.columns:
        zb = df_zt.groupby('代码').agg(
            总炸板=('炸板次数', 'sum'),
            涨停次数=('代码', 'count')
        ).reset_index()
        zb['炸板率'] = (zb['总炸板'] / (zb['总炸板'] + zb['涨停次数'])).round(3)
        zb = zb.merge(name_map, on='代码', how='left')
        zb = zb.sort_values('炸板率')
        
        print(f"  Top 10 最低炸板率 (>=2次涨停):")
        zb_filtered = zb[zb['涨停次数'] >= 2].head(10)
        for _, r in zb_filtered.iterrows():
            print(f"  {r['代码']:<10} {r['名称']:<10} 炸板率:{r['炸板率']:.1%}, 涨停{r['涨停次数']}次")
    
    # ============================================================
    # 第五步: 封板资金分析
    # ============================================================
    print("\n[5] 封板资金分析...")
    if '封板资金' in df_zt.columns:
        fb = df_zt.groupby('代码').agg(
            平均封板资金=('封板资金', 'mean'),
            最大封板资金=('封板资金', 'max')
        ).reset_index()
        fb['平均封板资金_亿'] = (fb['平均封板资金'] / 1e8).round(2)
        fb = fb.merge(name_map, on='代码', how='left')
        fb = fb.sort_values('平均封板资金', ascending=False)
        
        print(f"  Top 10 平均封板资金 (亿元):")
        for _, r in fb.head(10).iterrows():
            print(f"  {r['代码']:<10} {r['名称']:<10} {r['平均封板资金_亿']:.2f}亿")
    
    # ============================================================
    # 第六步: 行业分布
    # ============================================================
    print("\n[6] 涨停行业分布...")
    if '所属行业' in df_zt.columns:
        ind = df_zt['所属行业'].value_counts().head(15)
        for name, cnt in ind.items():
            print(f"  {name:<15} {cnt}次")
    
    # ============================================================
    # 第七步: 综合评分
    # ============================================================
    print("\n[7] 综合评分...")
    
    # 构建评分表
    score = zt_freq[['代码', '名称', '涨停次数']].copy()
    
    # 合并连板数据
    if 'lb_max' in dir() and lb_max is not None and not lb_max.empty:
        score = score.merge(lb_max[['代码', '最大连板', '平均连板']], on='代码', how='left')
    else:
        score['最大连板'] = 0
        score['平均连板'] = 0
    
    # 合并炸板数据
    if 'zb' in dir() and zb is not None and not zb.empty:
        score = score.merge(zb[['代码', '炸板率']], on='代码', how='left')
    else:
        score['炸板率'] = 0
    
    # 合并封板资金
    if 'fb' in dir() and fb is not None and not fb.empty:
        score = score.merge(fb[['代码', '平均封板资金']], on='代码', how='left')
    else:
        score['平均封板资金'] = 0
    
    # 填充缺失值
    score = score.fillna(0)
    
    # 标准化
    for col in ['涨停次数', '最大连板', '平均连板', '平均封板资金']:
        if col in score.columns and score[col].max() > 0:
            score[f'{col}_norm'] = score[col] / score[col].max()
    
    # 炸板率（越低越好）
    if '炸板率' in score.columns:
        score['封板质量_norm'] = 1 - score['炸板率']
    
    # 综合评分
    weights = {'涨停次数_norm': 0.25, '最大连板_norm': 0.25, 
               '封板质量_norm': 0.20, '平均封板资金_norm': 0.15,
               '平均连板_norm': 0.15}
    
    final_score = 0
    for col, w in weights.items():
        if col in score.columns:
            final_score += score[col].fillna(0) * w
    
    score['综合评分'] = (final_score * 100).round(2)
    score = score.sort_values('综合评分', ascending=False).reset_index(drop=True)
    
    # 显示 Top 30
    print(f"\n  {'排名':<4} {'代码':<10} {'名称':<10} {'涨停':>6} {'最大连板':>6} {'炸板率':>6} {'封板资金(亿)':>10} {'评分':>6}")
    print("  " + "-" * 70)
    
    for i, row in score.head(30).iterrows():
        code = row['代码']
        name = row['名称']
        zt = int(row['涨停次数'])
        mlb = f"{row['最大连板']:.0f}" if row['最大连板'] > 0 else "-"
        zbr = f"{row['炸板率']:.1%}" if row['炸板率'] > 0 else "0%"
        fbz = f"{row['平均封板资金']/1e8:.2f}" if row['平均封板资金'] > 0 else "-"
        s = row['综合评分']
        print(f"  {i+1:<4} {code:<10} {name:<10} {zt:>6} {mlb:>6} {zbr:>6} {fbz:>10} {s:>6.1f}")
    
    # 保存结果
    result_file = os.path.join(OUTPUT_DIR, "full_zt_analysis.csv")
    score.to_csv(result_file, index=False, encoding='utf-8-sig')
    print(f"\n  完整结果已保存: {result_file}")
    
    # ============================================================
    # 结论
    # ============================================================
    print("\n" + "=" * 70)
    print(" 分析结论")
    print("=" * 70)
    print("""
  【重要说明】
  以上分析基于东方财富涨停板接口可获取的近期数据（约一周），
  样本量有限。如需更全面的3年历史数据分析，建议：
  
  1. 使用 Tushare Pro 付费接口获取完整历史涨停数据
  2. 使用 Wind/Choice 等专业金融终端
  3. 使用券商提供的量化交易API
  
  【当前数据维度参考】
  - 涨停频率：哪些股票近期最活跃
  - 连板能力：哪些股票容易形成连板
  - 封板质量：哪些股票炸板率低
  - 封板资金：哪些股票资金认可度高
  
  【打板策略建议】
  1. 优先选择综合评分高的股票
  2. 关注炸板率低的股票（封板更稳）
  3. 高连板能力 + 低炸板率 = 最优打板标的
  4. 结合当日市场情绪和板块轮动做出最终决策
""")
    
    return score

if __name__ == "__main__":
    main()
