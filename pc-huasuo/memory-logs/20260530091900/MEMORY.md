# 长期记忆

## 项目配置

- **工作目录**: `c:\Users\asus\WorkBuddy\20260530091900`
- **数据源**: AKShare (东方财富接口) — finance-data-retrieval API 在 WorkBuddy 中无法直接调用
- **微信推送**: PushPlus，Token 存储在 `~/.workbuddy/skills/pushplus-wechat/token.txt`

## 定时任务

| 名称 | ID | 频率 | 说明 |
|------|-----|------|------|
| AIHOT 每日早报推送 | aihot | 每日 9:00 | AI 行业动态推送 |
| 早盘10分钟涨停扫描+微信推送 | 10 | 工作日 12:00 | 抓取A股早盘涨停+成交量监控 |

## 关键踩坑

- `finance-data-retrieval` 的 API (codebuddy.cn/v2/tool/financedata) 需要 CodeBuddy IDE 内置认证，WorkBuddy 环境返回 401
- AKShare `stock_zt_pool_em` 仅支持最近 ~7天 数据查询，不支持长期历史回溯
- AKShare `stock_zh_a_hist` 获取成交量时偶尔会 Connection aborted，属于正常网络波动
- Windows PowerShell 下 curl 是 Invoke-WebRequest 别名，参数格式不同，需用 curl.exe 或 Python requests
