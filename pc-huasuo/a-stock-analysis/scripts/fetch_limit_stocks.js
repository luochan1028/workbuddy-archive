#!/usr/bin/env node

/**
 * 获取完整涨停板股票列表并保存
 */

const https = require('https');
const fs = require('fs');
const path = require('path');

function fetchStockList(type = 'zt', page = 1, pageSize = 200) {
  return new Promise((resolve, reject) => {
    let url;
    
    switch (type) {
      case 'strong':
        url = `https://push2.eastmoney.com/api/qt/clist/get?pn=${page}&pz=${pageSize}&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18`;
        break;
      case 'cy':
        url = `https://push2.eastmoney.com/api/qt/clist/get?pn=${page}&pz=${pageSize}&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18`;
        break;
      case 'kc':
        url = `https://push2.eastmoney.com/api/qt/clist/get?pn=${page}&pz=${pageSize}&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:1+t:2&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18`;
        break;
      case 'zt':
      default:
        url = `https://push2.eastmoney.com/api/qt/clist/get?pn=${page}&pz=${pageSize}&po=1&np=1&fltt=2&invt=2&fid=f3&fs=m:0+t:6,m:0+t:80,m:1+t:2,m:1+t:23&fields=f1,f2,f3,f4,f5,f6,f7,f8,f9,f10,f12,f13,f14,f15,f16,f17,f18`;
        break;
    }

    const timeout = setTimeout(() => reject(new Error('请求超时')), 15000);
    
    const req = https.get(url, { 
      headers: { 
        'Referer': 'https://finance.eastmoney.com',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
      } 
    }, (res) => {
      let data = '';
      res.on('data', chunk => data += chunk);
      res.on('end', () => {
        clearTimeout(timeout);
        try {
          const json = JSON.parse(data);
          if (!json.data || !json.data.diff) {
            resolve([]);
            return;
          }
          
          const stocks = json.data.diff.map(item => ({
            code: item.f12,
            name: item.f14,
            price: item.f2,
            change: item.f4,
            percent: item.f3,
            volume: item.f5,  // 成交量(手)
            amount: item.f6,   // 成交额(元)
            turnover: item.f8, // 换手率
            pe: item.f9,       // 市盈率
            pb: item.f10,      // 市净率
            high: item.f15,    // 最高
            low: item.f16,     // 最低
            open: item.f17,    // 开盘
            prevClose: item.f18 // 昨收
          })).filter(s => s.price > 0);
          
          // 根据类型过滤
          if (type === 'zt') {
            return resolve(stocks.filter(s => s.percent >= 9.9));
          } else if (type === 'strong') {
            return resolve(stocks.filter(s => s.percent >= 7));
          } else if (type === 'cy' || type === 'kc') {
            return resolve(stocks.filter(s => s.percent >= 19.9));
          }
          
          resolve(stocks);
        } catch (e) {
          reject(e);
        }
      });
    });
    
    req.on('error', (e) => {
      clearTimeout(timeout);
      reject(e);
    });
  });
}

async function main() {
  try {
    console.log('正在获取涨停板股票数据...');
    const stocks = await fetchStockList('zt');
    
    console.log(`共获取到 ${stocks.length} 只涨停板股票`);
    
    // 保存为 JSON
    const jsonFile = path.join(__dirname, '涨停板股票_' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '.json');
    fs.writeFileSync(jsonFile, JSON.stringify(stocks, null, 2), 'utf8');
    console.log(`JSON 数据已保存到: ${jsonFile}`);
    
    // 保存为文本
    const textFile = path.join(__dirname, '涨停板股票_' + new Date().toISOString().slice(0, 10).replace(/-/g, '') + '.txt');
    let text = `涨停板股票筛选报告 - ${new Date().toLocaleDateString('zh-CN')}\n`;
    text += `共 ${stocks.length} 只股票涨停\n`;
    text += '='.repeat(80) + '\n\n';
    
    stocks.forEach((s, i) => {
      text += `${i+1}. ${s.name} (${s.code}) - 价格: ${s.price}, 涨幅: +${s.percent}%, `;
      text += `换手率: ${s.turnover}%, 成交额: ${(s.amount/100000000).toFixed(2)}亿, `;
      text += `市盈率: ${s.pe}, 市净率: ${s.pb}\n`;
    });
    
    fs.writeFileSync(textFile, text, 'utf8');
    console.log(`文本报告已保存到: ${textFile}`);
    
    // 输出前20只到控制台
    console.log('\n前20只涨停股票:');
    stocks.slice(0, 20).forEach((s, i) => {
      console.log(`${i+1}. ${s.name} (${s.code}) +${s.percent}% 换手:${s.turnover}%`);
    });
    
  } catch (e) {
    console.error(`Error: ${e.message}`);
    process.exit(1);
  }
}

main();
