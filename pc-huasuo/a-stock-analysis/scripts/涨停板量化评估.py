import json
import os
import sys

# 设置输出编码
sys.stdout.reconfigure(encoding='utf-8')

# 读取涨停数据
with open('c:/Users/asus/WorkBuddy/20260530084842/涨停板数据_20260530.json', 'r', encoding='utf-8') as f:
    stocks = json.load(f)

def time_to_minutes(t):
    """将时间字符串 HHMMSS 转换为分钟数（从9:15开始）"""
    if not t or len(t) < 4:
        return 240
    try:
        h = int(t[:2])
        m = int(t[2:4])
        return (h - 9) * 60 + (m - 15)
    except:
        return 240

def evaluate_stock(stock):
    """对单只股票进行量化打分"""
    score = 0
    reasons = []
    
    # 1. 封板时间评分（越早越好，最高30分）
    first_time = stock.get('首次封板时间', '145000')
    minutes = time_to_minutes(first_time)
    if minutes <= 15:  # 9:30之前（一字板或秒板）
        time_score = 30
        reasons.append(f"9:30前涨停(+30)")
    elif minutes <= 30:  # 9:45前
        time_score = 25
        reasons.append(f"早盘强势封板(+25)")
    elif minutes <= 60:  # 10:15前
        time_score = 20
        reasons.append(f"上午快速封板(+20)")
    elif minutes <= 120:  # 11:15前
        time_score = 15
        reasons.append(f"上午封板(+15)")
    elif minutes <= 180:  # 13:30前
        time_score = 10
        reasons.append(f"下午早盘封板(+10)")
    else:
        time_score = 5
        reasons.append(f"尾盘封板(+5)")
    score += time_score
    
    # 2. 炸板次数评分（越少越好，最高20分）
    zha = stock.get('炸板次数', 0)
    if zha == 0:
        zha_score = 20
        reasons.append("未炸板(+20)")
    elif zha <= 1:
        zha_score = 12
        reasons.append(f"炸板{zha}次(+12)")
    elif zha <= 3:
        zha_score = 6
        reasons.append(f"炸板{zha}次(+6)")
    else:
        zha_score = 0
        reasons.append(f"炸板{zha}次(0)")
    score += zha_score
    
    # 3. 封板资金评分（相对流通市值的比例，最高25分）
    fengban = stock.get('封板资金', 0)
    liutong = stock.get('流通市值', 1)
    ratio = fengban / liutong * 100
    if ratio >= 5:
        fb_score = 25
        reasons.append(f"封单比{ratio:.2f}%(+25)")
    elif ratio >= 2:
        fb_score = 20
        reasons.append(f"封单比{ratio:.2f}%(+20)")
    elif ratio >= 1:
        fb_score = 15
        reasons.append(f"封单比{ratio:.2f}%(+15)")
    elif ratio >= 0.5:
        fb_score = 10
        reasons.append(f"封单比{ratio:.2f}%(+10)")
    else:
        fb_score = 5
        reasons.append(f"封单比{ratio:.2f}%(+5)")
    score += fb_score
    
    # 4. 连板数评分（当前连板数越高越有龙头相，最高15分）
    lianban = stock.get('连板数', 1)
    if lianban >= 5:
        lb_score = 15
        reasons.append(f"{lianban}连板龙头(+15)")
    elif lianban >= 3:
        lb_score = 12
        reasons.append(f"{lianban}连板(+12)")
    elif lianban >= 2:
        lb_score = 8
        reasons.append(f"{lianban}连板(+8)")
    else:
        lb_score = 4
        reasons.append(f"首板(+4)")
    score += lb_score
    
    # 5. 换手率评分（适中最好，最高10分）
    hsl = stock.get('换手率', 0)
    if 3 <= hsl <= 10:
        hsl_score = 10
        reasons.append(f"换手{hsl:.1f}%健康(+10)")
    elif 1 <= hsl <= 15:
        hsl_score = 7
        reasons.append(f"换手{hsl:.1f}%(+7)")
    elif hsl < 1:
        hsl_score = 4
        reasons.append(f"换手过低{hsl:.1f}%(+4)")
    else:
        hsl_score = 5
        reasons.append(f"换手偏高{hsl:.1f}%(+5)")
    score += hsl_score
    
    return {
        'code': stock['代码'],
        'name': stock['名称'],
        'price': stock['最新价'],
        'change': stock['涨跌幅'],
        'industry': stock['所属行业'],
        'lianban': lianban,
        'first_time': first_time,
        'zhaban': zha,
        'fengban_ratio': ratio,
        'hsl': hsl,
        'score': score,
        'reasons': reasons
    }

# 评估所有股票
results = [evaluate_stock(s) for s in stocks]

# 按得分排序
results.sort(key=lambda x: x['score'], reverse=True)

# 分级
S_tier = [r for r in results if r['score'] >= 85]
A_tier = [r for r in results if 70 <= r['score'] < 85]
B_tier = [r for r in results if 55 <= r['score'] < 70]
C_tier = [r for r in results if r['score'] < 55]

# 生成报告
report = []
report.append("# 涨停板量化评估报告 - 2026年5月30日")
report.append(f"\n共评估 **{len(results)}** 只涨停股票")
report.append("\n---\n")

def print_tier(tier, name):
    report.append(f"\n## {name}级（共{len(tier)}只）")
    if not tier:
        report.append("\n无")
        return
    for r in tier:
        report.append(f"\n### {r['name']}（{r['code']}）- 得分：**{r['score']}**")
        report.append(f"- **现价**：{r['price']}元 | **涨幅**：{r['change']:.2f}% | **行业**：{r['industry']}")
        report.append(f"- **连板**：{r['lianban']}连板 | **封板时间**：{r['first_time'][:2]}:{r['first_time'][2:4]}")
        report.append(f"- **炸板**：{r['zhaban']}次 | **封单比**：{r['fengban_ratio']:.2f}% | **换手**：{r['hsl']:.1f}%")
        report.append(f"- **加分项**：{'；'.join(r['reasons'])}")

print_tier(S_tier, "S")
print_tier(A_tier, "A")
print_tier(B_tier, "B")
print_tier(C_tier, "C")

report.append("\n---\n")
report.append("## 买入策略建议\n")

report.append("### 一、S级标的 - 核心仓位")
report.append("特征：封板早、未炸板、封单足、有连板基因")
report.append("操作：明日竞价或开盘直接跟，仓位可重")
report.append("注意：若次日一字板不给机会，放弃追高")
report.append("")

report.append("### 二、A级标的 - 参与仓位")
report.append("特征：整体结构较好，但某一项有瑕疵")
report.append("操作：开盘观察5分钟，确认承接有力后跟进")
report.append("注意：避免高开低走，设置止损位")
report.append("")

report.append("### 三、B级标的 - 观察为主")
report.append("特征：有明显短板（如炸板多、封板晚、换手异常）")
report.append("操作：仅在市场情绪极好时轻仓试错")
report.append("")

report.append("### 四、C级标的 - 回避")
report.append("特征：多项指标不合格，风险收益比差")
report.append("操作：不建议参与")
report.append("")

report.append("---\n")
report.append("## 跟板核心原则\n")
report.append("1. **只做龙头，不做杂毛**：优先连板股、早盘板、板块龙头")
report.append("2. **封单决定强度**：封单比>2%为安全，<0.5%容易炸")
report.append("3. **换手要健康**：3%-10%最佳，太高是出货、太低是没换手")
report.append("4. **炸板是减分项**：炸板次数越多，次日低开概率越大")
report.append("5. **板块效应**：同一板块涨停越多，龙头持续性越好")
report.append("6. **宁可错过，不可做错**：没有好标就空仓，打板不是每天都要打")
report.append("")
report.append("---\n")
report.append("*免责声明：本报告仅作数据整理和策略分析参考，不构成投资建议。股市有风险，入市需谨慎。*")

# 保存报告
report_text = '\n'.join(report)
with open('c:/Users/asus/WorkBuddy/20260530084842/涨停板量化评估报告.md', 'w', encoding='utf-8') as f:
    f.write(report_text)

print("评估完成！")
print(f"S级：{len(S_tier)}只")
print(f"A级：{len(A_tier)}只")
print(f"B级：{len(B_tier)}只")
print(f"C级：{len(C_tier)}只")
print("\n" + "="*60)
print("\nTOP 10 推荐标的：\n")
for i, r in enumerate(results[:10], 1):
    tag = "[S]" if r['score'] >= 85 else "[A]" if r['score'] >= 70 else ""
    print(f"{i}. {tag} {r['name']}（{r['code']}）- {r['lianban']}连板 - 得分{r['score']}")
    print(f"   封板{r['first_time'][:2]}:{r['first_time'][2:4]}|炸板{r['zhaban']}次|封单比{r['fengban_ratio']:.1f}%|换手{r['hsl']:.1f}%")
    print()
