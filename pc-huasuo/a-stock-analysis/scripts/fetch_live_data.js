// 拉取19只AI产业链股票最新数据
const https = require("https");
const fs = require("fs");

const TOKEN = "eyJhbGciOiJSUzI1NiIsInR5cCIgOiAiSldUIiwia2lkIiA6ICJteWZFenA3ODNLaV9KQ3g4Vm5jM1hfaXg2alpyYjZDZjVPTWtHWk1QSTNzIn0.eyJleHAiOjE4MTE2MzY0NTEsImlhdCI6MTc4MDEyMjU1NSwiYXV0aF90aW1lIjoxNzgwMTAwNDUwLCJqdGkiOiI0YTQyNzA3OS00MGVkLTQ2NzctYWU0OS03M2YzOGE0ODY2MDciLCJpc3MiOiJodHRwczovL3d3dy5jb2RlYnVkZHkuY24vYXV0aC9yZWFsbXMvY29waWxvdCIsImF1ZCI6ImFjY291bnQiLCJzdWIiOiI0YzFjOTg5MS0xMWRlLTRmYWQtYjhhMS0xNzAzZjkwYjk0Y2UiLCJ0eXAiOiJCZWFyZXIiLCJhenAiOiJjb25zb2xlIiwic2lkIjoiMWZhYzU0NWEtZGNjOC00ZGJhLWIzMzgtZTA1ZDlmYzZmMTkzIiwiYWNyIjoiMCIsImFsbG93ZWQtb3JpZ2lucyI6WyIqIl0sInJlYWxtX2FjY2VzcyI6eyJyb2xlcyI6WyJkZWZhdWx0LXJvbGVzIiwib2ZmbGluZV9hY2Nlc3MiLCJ1bWFfYXV0aG9yaXphdGlvbiJdfSwicmVzb3VyY2VfYWNjZXNzIjp7ImFjY291bnQiOnsicm9sZXMiOlsibWFuYWdlLWFjY291bnQiLCJtYW5hZ2UtYWNjb3VudC1saW5rcyIsInZpZXctcHJvZmlsZSJdfX0sInNjb3BlIjoib3BlbmlkIHByb2ZpbGUgb2ZmbGluZV9hY2Nlc3MgZW1haWwiLCJlbWFpbF92ZXJpZmllZCI6ZmFsc2UsIm5pY2tuYW1lIjoi5Z2k5Y6aIiwicHJlZmVycmVkX3VzZXJuYW1lIjoiMTgxNzEyMzIyMzcifQ.A_-n_8YuWGoCDK3u7ipery5Ocm4e5-doOYhN8nH3GiQiCUvwfBfU1Wneu6ACHCVG1EylBwxUIFh9xEY88oZ34Q1FaBGioDAeBjvnPqPFRZ94IrUzAr-JLQ1GBoe_-NPbf-a8ED8l-stGxDF1I2qXQ_f6QejLePR3Iu1_iYevkthg5f9imerOKY5qGIkW-9cqKQj5oXJbR2I-kO6pT9ITBrSAKwJOEogta2ovkAXt-TSzZlqw08INvlVlxExo2nbMtFYOuLgDeNfXYwMCNHKbCLKwC_79XM4sR4J3beinz4DDMwAaVQhnFRM5SaJvo3K7d7YOIHZaswhAFJFje_GvIw";

const stockCodes = [
  "688041.SH", "300308.SZ", "300502.SZ", "300394.SZ", "600584.SH",
  "002837.SZ", "002156.SZ", "688525.SH", "000938.SZ", "603019.SH",
  "002371.SZ", "688012.SH", "688981.SH", "688256.SH", "688047.SH",
  "002230.SZ", "688111.SH", "002396.SZ", "300499.SZ"
];

function callAPI(apiName, params, fields) {
  return new Promise((resolve, reject) => {
    const body = JSON.stringify({
      api_name: apiName,
      params: params,
      fields: fields || ""
    });
    const options = {
      hostname: "www.codebuddy.cn",
      port: 443,
      path: "/v2/tool/financedata",
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + TOKEN,
        "Content-Length": Buffer.byteLength(body)
      }
    };
    const req = https.request(options, (res) => {
      let data = "";
      res.on("data", chunk => data += chunk);
      res.on("end", () => {
        try {
          resolve(JSON.parse(data));
        } catch (e) {
          resolve({ raw: data, statusCode: res.statusCode });
        }
      });
    });
    req.on("error", reject);
    req.write(body);
    req.end();
  });
}

async function main() {
  console.log("=== 拉取日线行情 (daily) ===");
  const codesStr = stockCodes.join(",");
  
  // 1. 日线行情 - 最近5个交易日
  const dailyRes = await callAPI("daily", {
    ts_code: codesStr,
    start_date: "20260522",
    end_date: "20260530"
  }, "ts_code,trade_date,close,pre_close,pct_chg,vol,amount");
  console.log("daily:", JSON.stringify(dailyRes).substring(0, 500));

  // 2. 每日指标 - 最新一天
  const basicRes = await callAPI("daily_basic", {
    ts_code: codesStr,
    trade_date: "20260529"
  }, "ts_code,trade_date,close,pe,pe_ttm,pb,total_mv,circ_mv,turnover_rate");
  console.log("daily_basic:", JSON.stringify(basicRes).substring(0, 500));

  // 3. 财务指标 - 单只测试
  const finaRes = await callAPI("fina_indicator", {
    ts_code: "688041.SH",
    period: "20260331"
  }, "ts_code,end_date,roe,gross_margin,debt_to_assets,eps,revenue_ps");
  console.log("fina_indicator (688041):", JSON.stringify(finaRes).substring(0, 500));
}

main().catch(err => console.error("Error:", err.message));
