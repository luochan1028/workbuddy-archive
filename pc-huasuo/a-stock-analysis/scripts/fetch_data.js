const https = require('https');
const fs = require('fs');

const TOKEN = 'eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCIsImtpZCI6Im15ZWFuNzgzS2l9SkN4OFZuYzNfYXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MTE2MzY0NTEsImlhdCI6MTc4MDExNTQ4NywiYXV0aF90aW1lIjoxNzgwMTAwNDUwLCJqdGkiOiJmODRkYzQ1ZS00M2Q4LTRmMmItODVmYy0wMzNlNDY5NjJlMDUiLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiI0YzFjOTg5MS0xMWRlLTRmYWQtYjhhMS0xNzAzZjkwYjk0Y2UiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiMWZhYzU0NWEtZGNjOC00ZGJhLWIzMzgtZTA1ZDlmYzZmMTkzIiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi5Z2k5Y6aIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTgxNzEyMzIyMzcifQ.Zx7ldQLH2T67Wscu4u9quIYfoinXlNfSboqouycweK63rfdlvyN9C95jiobLODMlCDV_SW3znWQtsBEOUVdZ_oWPBNNc85UHBcWwNgqVGJM3h2GzIYM_Pa6fCW_2rT7G7h-EdKi8Z_PaFDo_u2tsN_cemAyh7-FGv99OzEkgmc4LeCaf1D9G_DG6ay_YajzFp10A1ZM7J-z53AtzuQAWNh_IVmY3eklI1HXDz9FqMeYRTHvUOtZxONpbxiKP9xhs7YlqVlEqMMFYoas00I3xWYMMcgvSviUCvkfolN0LkuklAs0cyMAxf_OfVD1T9IZuMG2FYcq8Ckp-heC40oTZNA';

function callAPI(apiName, params, fields) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({ api_name: apiName, params, fields: fields || '' });
    const options = {
      hostname: 'www.codebuddy.cn',
      path: '/v2/tool/financedata',
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${TOKEN}`,
        'Content-Length': Buffer.byteLength(body)
      }
    };
    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { resolve({ raw: data }); }
      });
    });
    req.on('error', reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  const results = {};

  // 第一层：算力芯片
  console.log('拉取算力芯片...');
  results.layer1 = await callAPI('daily', {
    ts_code: '688256.SH,688041.SH,688047.SH,688048.SH',
    start_date: '20260101', end_date: '20260530'
  }, 'ts_code,trade_date,close,open,high,low,pct_chg,vol,amount');

  // 第二层：存储+封测
  console.log('拉取存储封测...');
  results.layer2 = await callAPI('daily', {
    ts_code: '600584.SH,002156.SZ,002185.SZ,688525.SH,603986.SH',
    start_date: '20260101', end_date: '20260530'
  }, 'ts_code,trade_date,close,open,high,low,pct_chg,vol,amount');

  // 第三层：光通信
  console.log('拉取光通信...');
  results.layer3 = await callAPI('daily', {
    ts_code: '300308.SZ,300502.SZ,300394.SZ,002281.SZ',
    start_date: '20260101', end_date: '20260530'
  }, 'ts_code,trade_date,close,open,high,low,pct_chg,vol,amount');

  // 第四层：网络设备
  console.log('拉取网络设备...');
  results.layer4 = await callAPI('daily', {
    ts_code: '000938.SZ,002396.SZ,000063.SZ',
    start_date: '20260101', end_date: '20260530'
  }, 'ts_code,trade_date,close,open,high,low,pct_chg,vol,amount');

  // 第五层：半导体制造+设备
  console.log('拉取半导体制造设备...');
  results.layer5 = await callAPI('daily', {
    ts_code: '688981.SH,002371.SZ,688012.SH,688126.SH,688234.SH',
    start_date: '20260101', end_date: '20260530'
  }, 'ts_code,trade_date,close,open,high,low,pct_chg,vol,amount');

  // 第六层：数据中心基建
  console.log('拉取数据中心基建...');
  results.layer6 = await callAPI('daily', {
    ts_code: '002837.SZ,300499.SZ,002335.SZ,603019.SH,000977.SZ',
    start_date: '20260101', end_date: '20260530'
  }, 'ts_code,trade_date,close,open,high,low,pct_chg,vol,amount');

  // 第七层：AI应用
  console.log('拉取AI应用...');
  results.layer7 = await callAPI('daily', {
    ts_code: '002230.SZ,688111.SH,300229.SZ,603019.SH',
    start_date: '20260101', end_date: '20260530'
  }, 'ts_code,trade_date,close,open,high,low,pct_chg,vol,amount');

  // 财务指标
  console.log('拉取财务指标...');
  results.fina = await callAPI('fina_indicator', {
    ts_code: '688256.SH,688041.SH,688047.SH,600584.SH,300308.SZ,000938.SZ,688981.SH,002230.SZ,603019.SH,000977.SZ',
    period: '20241231',
  }, 'ts_code,end_date,roe,roic,netprofit_yoy,grossprofit_margin,netprofit_margin,debt_to_assets,ocf_to_profit,current_ratio');

  // 每日指标（估值）
  console.log('拉取估值指标...');
  results.dailyBasic = await callAPI('daily_basic', {
    ts_code: '688256.SH,688041.SH,688047.SH,600584.SH,300308.SZ,000938.SZ,688981.SH,002230.SZ,603019.SH,000977.SZ',
    start_date: '20260523', end_date: '20260530'
  }, 'ts_code,trade_date,pe_ttm,pb,ps_ttm,dv_ttm,total_mv,float_mv');

  fs.writeFileSync('ai_stock_data.json', JSON.stringify(results, null, 2));
  console.log('数据已保存到 ai_stock_data.json');
  console.log(JSON.stringify(results, null, 2));
}

main().catch(console.error);
