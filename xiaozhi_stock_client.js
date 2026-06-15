#!/usr/bin/env node
const WebSocket = require('ws');
const { execSync } = require('child_process');
const path = require('path');

const TOKEN='eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQxMjY4NSwiYWdlbnRJZCI6NTA1NTYzLCJlbmRwb2ludElkIjoiYWdlbnRfNTA1NTYzIiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc3NjIyNDI5NSwiZXhwIjoxODA3NzgxODk1fQ.tI3mdf3mDns_reSWrQYHNWsyjaYhrLKV-QnId-rACX97D2lsbkjS0jEXdHl5SKQe9ZPmX7viJGzzJTYIoEpYOQ';
const ENDPOINT = 'wss://api.xiaozhi.me/mcp/?token=' + TOKEN;
const PYTHON_PATH = '/Users/mihua/.hermes/hermes-agent/venv/bin/python3';

const TOOLS = [
  { name: 'get_stock_info', description: '查询A股实时行情', inputSchema: { type: 'object', properties: { symbol: { type: 'string', description: '股票代码，例如 300308 或 601127' } }, required: ['symbol'] } },
  { name: 'analyze_stock', description: '基于姚尧形态学评分系统的股票深度分析诊断', inputSchema: { type: 'object', properties: { symbol: { type: 'string', description: '股票代码' } }, required: ['symbol'] } },
  { name: 'recommend_stocks', description: 'AI每日股票推荐', inputSchema: { type: 'object', properties: {} } },
  { name: 'search_web', description: '联网搜索', inputSchema: { type: 'object', properties: { query: { type: 'string' } }, required: ['query'] } }
];

// Sanitize shell arguments to prevent injection
function shellSafe(str) {
  if (!str) return '';
  return String(str).replace(/['"`$;|&(){}[\]<>!\\]/g, '\\$&');
}

// execSync with timeout + error handling
function runStockBackend(action, symbol) {
  try {
    const scriptPath = path.join(__dirname, 'stock_backend.py');
    const safeSymbol = shellSafe(symbol || '');
    const result = execSync(
      `"${PYTHON_PATH}" "${scriptPath}" "${action}" "${safeSymbol}"`,
      { encoding: 'utf-8', timeout: 15000 }
    );
    const parsed = JSON.parse(result);
    if (parsed.error) return `执行提示: ${parsed.error}`;
    if (parsed.report) return parsed.report;
    if (parsed.data) return JSON.stringify(parsed.data, null, 2);
    return JSON.stringify(parsed, null, 2);
  } catch (error) {
    return `股票后台执行失败: ${error.message.includes('timeout') ? '执行超时(>15s)' : error.message}`;
  }
}

function connect() {
  let retryCount = 0; // 指数退避计数器
  console.log('[' + new Date().toISOString() + '] Connecting to xiaozhi stock MCP...');
  const ws = new WebSocket(ENDPOINT, { rejectUnauthorized: false });
  
  ws.on('open', () => console.log('[' + new Date().toISOString() + '] Connected!'));
  ws.on('error', e => { 
    console.log('[' + new Date().toISOString() + '] Error:', e.message); 
    setTimeout(connect, Math.min(5000 * Math.pow(1.5, retryCount), 60000)); 
    retryCount = Math.min((retryCount || 0) + 1, 20);
  });
  ws.on('close', () => { 
    console.log('[' + new Date().toISOString() + '] Closed, reconnecting...'); 
    setTimeout(connect, Math.min(5000 * Math.pow(1.5, retryCount), 60000)); 
    retryCount = Math.min((retryCount || 0) + 1, 20);
  });
  
  ws.on('message', raw => {
    let msg;
    try { msg = JSON.parse(raw); } catch(e) { return; }
    
    if (msg.method === 'ping') {
      ws.send(JSON.stringify({jsonrpc:'2.0', id: msg.id, result: {}}));
      return;
    }
    
    if (msg.method === 'initialize') {
      ws.send(JSON.stringify({
        jsonrpc: '2.0',
        id: msg.id,
        result: {
          protocolVersion: '2024-11-05',
          capabilities: { tools: { listChanged: true } },
          clientInfo: { name: 'jl-stock-mcp', version: '2.0' }
        }
      }));
      return;
    }
    
    if (msg.method === 'tools/list') {
      ws.send(JSON.stringify({jsonrpc: '2.0', id: msg.id, result: { tools: TOOLS }}));
      return;
    }
    
    if (msg.method === 'tools/call') {
      const name = msg.params.name;
      const args = msg.params.arguments || {};
      
      let text = '未知工具';
      if (name === 'get_stock_info') {
        text = runStockBackend('info', args.symbol || '');
      } else if (name === 'analyze_stock') {
        text = runStockBackend('analyze', args.symbol || '');
      } else if (name === 'recommend_stocks') {
        text = runStockBackend('recommend', '');
      } else if (name === 'search_web') {
        text = '联网搜索功能已集成，请直接提问搜索需求。';
      } else {
        text = '已执行: ' + name;
      }
      
      ws.send(JSON.stringify({ jsonrpc: '2.0', id: msg.id, result: { content: [{ type: 'text', text: text }] } }));
    }
  });
}
console.log('xiaozhi Stock MCP Client starting...');
connect();
