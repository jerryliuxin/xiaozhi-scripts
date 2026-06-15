#!/usr/bin/env node
const WebSocket = require('ws');
const { execSync } = require('child_process');
const path = require('path');

const TOKEN='eyJhbGciOiJFUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VySWQiOjQxMjY4NSwiYWdlbnRJZCI6NTA1NTYzLCJlbmRwb2ludElkIjoiYWdlbnRfNTA1NTYzIiwicHVycG9zZSI6Im1jcC1lbmRwb2ludCIsImlhdCI6MTc3NjIyNDI5NSwiZXhwIjoxODA3NzgxODk1fQ.tI3mdf3mDns_reSWrQYHNWsyjaYhrLKV-QnId-rACX97D2lsbkjS0jEXdHl5SKQe9ZPmX7viJGzzJTYIoEpYOQ';
const ENDPOINT = 'wss://api.xiaozhi.me/mcp/?token=' + TOKEN;

// Sanitize shell arguments to prevent injection
function shellSafe(str) {
  if (!str) return '';
  return String(str).replace(/['"`$;|&(){}[\]<>!\\]/g, '\\$&');
}

// execSync with timeout + proper error handling
function runEduBackend(action, param = '') {
  const scriptPath = path.join(__dirname, 'edu_backend.py');
  const safeAction = shellSafe(action);
  const safeParam = shellSafe(param);
  try {
    const result = execSync(
      `python3 "${scriptPath}" "${safeAction}" ${safeParam}`,
      { encoding: 'utf-8', timeout: 15000 }
    );
    const parsed = JSON.parse(result);
    if (parsed.error) return `执行提示: ${parsed.error}`;
    if (parsed.prompt) return parsed.prompt;
    if (parsed.result) return typeof parsed.result === 'object' ? JSON.stringify(parsed.result, null, 2) : parsed.result;
    return JSON.stringify(parsed, null, 2);
  } catch (error) {
    return `教育后台执行失败: ${error.message.includes('timeout') ? '执行超时(>15s)' : error.message}`;
  }
}

const TOOLS = [
  // === 核心教育功能 ===
  { name: 'get_unlock_lesson', description: '获取剑桥 Unlock L3 (B1水平) 英语教材的每日教学内容与话题', inputSchema: { type: 'object', properties: { unit: { type: 'string', description: '单元号(1-8)，不填随机' } } } },
  { name: 'mickey_daily_chat', description: '和米奇(Mickey)进行每日英语对话任务，聊聊F1方程式赛车或今日有趣事实', inputSchema: { type: 'object', properties: {} } },
  { name: 'tell_story_or_song', description: '给小朋友讲故事或科普(科幻冒险、历史探秘、科学探索等五年级以上主题)', inputSchema: { type: 'object', properties: { theme: { type: 'string', description: '主题：科幻冒险, 历史探秘, 科学探索, 成语故事, 睡前科普' } }, required: ['theme'] } },
  { name: 'explain_to_child', description: '运用幼儿教育和青少年家庭教育系统知识，深入浅出地解答小朋友提出的任何"为什么"', inputSchema: { type: 'object', properties: { question: { type: 'string', description: '小朋友提出的问题' } }, required: ['question'] } },
  { name: 'interactive_adventure', description: '开启互动式多分支故事(Choose-Your-Own-Adventure)，让小朋友做决定', inputSchema: { type: 'object', properties: { setting: { type: 'string', description: '场景，例如：太空、恐龙世界、海底探险' } } } },
  { name: 'bilingual_math_logic', description: '双语逻辑与数学小挑战，带F1赛车主题的趣味智力题', inputSchema: { type: 'object', properties: {} } },
  { name: 'positive_reinforcement_praise', description: '运用正面管教(Positive Discipline)技巧，对小朋友的好行为进行具体事实表扬与能力肯定', inputSchema: { type: 'object', properties: { behavior: { type: 'string', description: '家长报告的小朋友具体好行为，例如：自己主动刷牙' } }, required: ['behavior'] } },
  { name: 'english_quiz_game', description: '英语闯关小游戏，答对问题可以获得积分奖励（难度自动根据积分调整）', inputSchema: { type: 'object', properties: { difficulty: { type: 'string', description: '难度：Auto(自动), Easy, Medium, Hard, Expert, Master' } } } },
  { name: 'chinese_recitation_challenge', description: '语文/国学背书大挑战，背诵正确可获得特殊奖励', inputSchema: { type: 'object', properties: { text_name: { type: 'string', description: '要背诵的课文或诗词名称，例如《静夜思》' } } } },

  // === 积分系统核心 ===
  { name: 'score', description: '查看当前积分、等级、连胜天数、运动/打卡统计和可用奖励', inputSchema: { type: 'object', properties: {} } },
  { name: 'welcome', description: '获取积分系统上线欢迎消息（首次使用）', inputSchema: { type: 'object', properties: {} } },
  { name: 'daily_tasks', description: '查看今日每日挑战任务列表（剑桥教材、口语练习、知识问答等）', inputSchema: { type: 'object', properties: {} } },
  { name: 'shop', description: '查看积分奖励商店（用积分兑换奖励），家长可确认兑换', inputSchema: { type: 'object', properties: { redeem: { type: 'boolean', description: '是否要兑换奖励：true表示兑换' }, parent_confirmed: { type: 'boolean', description: '家长确认：true表示家长已确认' } } } },
  { name: 'redeem_reward', description: '兑换积分奖励，需要家长确认后执行', inputSchema: { type: 'object', properties: { reward_id: { type: 'string', description: '奖励ID，例如: screen_time, weekend_trip, buy_book' }, parent_confirmed: { type: 'boolean', description: '家长确认：true表示家长已确认兑换' } } } },
  { name: 'q_history', description: '查看米奇之前问过的问题历史', inputSchema: { type: 'object', properties: { limit: { type: 'integer', description: '显示最近几条，默认5' } } } },
  { name: 'report', description: '生成米奇的今日学习报告', inputSchema: { type: 'object', properties: {} } },
  { name: 'tech_nature_news', description: '科技/自然新闻话题 — 每天随机推送趣味科技和自然事实，附带英语单词和互动问题', inputSchema: { type: 'object', properties: {} } },

  // === 口语练习 ===
  { name: 'speech_practice', description: '口语练习挑战，从基础/中级/进阶三个难度随机选句子，带评价功能', inputSchema: { type: 'object', properties: { difficulty: { type: 'string', description: '难度：基础, 中级, 进阶', enum: ['基础', '中级', '进阶'] }, completed_count: { type: 'integer', description: '家长确认完成了几句' }, quality: { type: 'string', description: '完成质量：excellent(优秀+5分/句), good(良好+5分/句), needs_improvement(需改进+3分/句)', enum: ['excellent', 'good', 'needs_improvement'] } } } },
  { name: 'speech_get_sentence', description: '获取一句口语练习句子（自动轮换避免重复）', inputSchema: { type: 'object', properties: { difficulty: { type: 'string', description: '难度：基础, 中级, 进阶', enum: ['基础', '中级', '进阶'] } } } },

  // === 运动打卡 ===
  { name: 'exercise', description: '记录运动打卡 — 跑步/跳绳/球类/游泳/骑行，记录后自动给积分', inputSchema: { type: 'object', properties: { type: { type: 'string', description: '运动类型: running(跑步), jump_rope(跳绳), ball(球类), swimming(游泳), cycling(骑行), other(其他)' }, duration: { type: 'string', description: '时长（分钟），跑步和骑行用，如"15"表示15分钟' }, count: { type: 'string', description: '数量，跳绳用，如"200"表示200个' } } } },
  { name: 'exercise_status', description: '查看今日运动状态、运动天数和运动成就', inputSchema: { type: 'object', properties: {} } },
  { name: 'exercise_achievements', description: '查看所有运动成就和当前进度', inputSchema: { type: 'object', properties: {} } },

  // === 每日打卡 ===
  { name: 'checkin', description: '每日打卡 — 早/中/晚三个时段自动打卡，连续打卡有额外奖励', inputSchema: { type: 'object', properties: { period: { type: 'string', description: '时段: morning(早), afternoon(中), evening(晚)，不填自动检测' } } } },
  { name: 'checkin_status', description: '查看今日打卡状态和连续打卡天数', inputSchema: { type: 'object', properties: {} } },
  { name: 'checkin_reminder', description: '获取智能打卡提醒（根据当前时段推送）', inputSchema: { type: 'object', properties: {} } },

  // === 每日挑战 ===
  { name: 'daily_quiz', description: '每日趣味挑战答题（科学/历史/英语/逻辑，15道题库），答对+10分', inputSchema: { type: 'object', properties: { answer: { type: 'string', description: '答案，如 A, B, C' } } } },
  { name: 'daily_challenge', description: '查看今日每日挑战任务列表（5项随机任务）', inputSchema: { type: 'object', properties: {} } },
  { name: 'claim_daily', description: '标记每日任务全部完成，领取额外奖励', inputSchema: { type: 'object', properties: {} } },

  // === 趋势分析 ===
  { name: 'trend_report', description: '获取综合积分趋势报告（包含本周、本月、各类别积分分布）', inputSchema: { type: 'object', properties: {} } },
  { name: 'weekly_report', description: '获取本周积分报告（每日积分、活跃度、最佳日）', inputSchema: { type: 'object', properties: {} } },
  { name: 'monthly_report', description: '获取本月积分报告（每日积分、总积分、活跃度、最佳日）', inputSchema: { type: 'object', properties: {} } },
  { name: 'category_breakdown', description: '获取各类别积分分布（学习/家务/运动/积极行为/每日奖励/惩罚的百分比）', inputSchema: { type: 'object', properties: {} } },

  // === 家长控制面板 ===
  { name: 'parent_stats', description: '家长统计面板：汇总所有模块数据（游戏/运动/打卡/挑战/商店/今日汇总）', inputSchema: { type: 'object', properties: {} } },
  { name: 'parent_reset', description: '家长重置积分数据（需要家长身份确认）', inputSchema: { type: 'object', properties: { what: { type: 'string', description: '重置范围: streak(仅连胜), score(仅积分), all(全部)', enum: ['streak', 'score', 'all'] } } } },
  { name: 'parent_add_reward', description: '家长添加自定义奖励到商店', inputSchema: { type: 'object', properties: { name: { type: 'string', description: '奖励名称' }, cost: { type: 'integer', description: '消耗积分' }, desc: { type: 'string', description: '奖励描述' }, category: { type: 'string', description: '分类，如：体验/娱乐/物质/学习' } } } },
  { name: 'parent_set_rules', description: '家长自定义积分规则', inputSchema: { type: 'object', properties: { field: { type: 'string', description: '规则字段，如 DAILY_COMPLETE_BONUS' }, value: { type: 'string', description: '新值' } } } },

  // === 激励系统 ===
  { name: 'chore', description: '记录家务劳动，米奇做家务后调用', inputSchema: { type: 'object', properties: { chore_name: { type: 'string', description: '家务名称，如：整理书桌、洗碗、倒垃圾' } } } },
  { name: 'positive', description: '记录积极行为（主动学习、自己收拾、分享等）', inputSchema: { type: 'object', properties: { action_type: { type: 'string', description: '行为类型: proactive(主动学习), cleaning(自己收拾), sharing(分享), listening(听指令)', enum: ['proactive', 'cleaning', 'sharing', 'listening'] } } } },
  { name: 'penalty', description: '扣分惩罚（抄袭、说谎、浪费粮食等）', inputSchema: { type: 'object', properties: { penalty_type: { type: 'string', description: '扣分类型: copying(抄袭), lying(说谎), wasting_food(浪费粮食)', enum: ['copying', 'lying', 'wasting_food'] } } } },
];

function connect() {
  let retryCount = 0; // 指数退避计数器
  console.log('[' + new Date().toISOString() + '] Connecting to xiaozhi edu MCP...');
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
          clientInfo: { name: 'jl-edu-mcp', version: '3.0' }
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
      // 核心教育功能
      if (name === 'get_unlock_lesson') {
        text = runEduBackend('unlock', args.unit || '1');
      } else if (name === 'mickey_daily_chat') {
        text = runEduBackend('mickey_f1');
      } else if (name === 'tell_story_or_song') {
        text = runEduBackend('story', args.theme || '科幻冒险');
      } else if (name === 'explain_to_child') {
        text = runEduBackend('explain', args.question);
      } else if (name === 'interactive_adventure') {
        text = runEduBackend('adventure', args.setting || '太空');
      } else if (name === 'bilingual_math_logic') {
        text = runEduBackend('math_logic');
      } else if (name === 'positive_reinforcement_praise') {
        text = runEduBackend('praise', args.behavior);
      } else if (name === 'english_quiz_game') {
        text = runEduBackend('english_quiz', args.difficulty || 'Auto');
      } else if (name === 'chinese_recitation_challenge') {
        text = runEduBackend('recitation', args.text_name || '《静夜思》');
      }
      
      // 积分系统核心
      else if (name === 'score') {
        text = runEduBackend('score');
      } else if (name === 'welcome') {
        text = runEduBackend('welcome');
      } else if (name === 'daily_tasks' || name === 'daily_challenge') {
        text = runEduBackend('daily_tasks');
      } else if (name === 'shop') {
        // 如果传了 redeem=true，尝试兑换
        if (args.redeem) {
          const rewardId = args.reward_id || 'screen_time';
          const parentConfirmed = args.parent_confirmed || false;
          text = runEduBackend('redeem', `${rewardId} ${parentConfirmed}`);
        } else {
          text = runEduBackend('shop');
        }
      } else if (name === 'redeem_reward') {
        // 兑换奖励（需要家长确认）
        const rewardId = args.reward_id || 'screen_time';
        const parentConfirmed = args.parent_confirmed ? 'true' : 'false';
        text = runEduBackend('redeem', `${rewardId} ${parentConfirmed}`);
      } else if (name === 'q_history') {
        const limit = args.limit || 5;
        text = runEduBackend('q_memory', String(limit));
      } else if (name === 'report') {
        text = runEduBackend('report');
      } else if (name === 'tech_nature_news') {
        text = runEduBackend('news');
      }
      
      // 口语练习
      else if (name === 'speech_practice') {
        const difficulty = args.difficulty || '中级';
        if (args.completed_count && args.quality) {
          // 家长确认后评分给分
          const points = args.completed_count * (args.quality === 'excellent' ? 5 : args.quality === 'good' ? 5 : 3);
          text = runEduBackend('positive', difficulty); // 先获取难度信息
          // 手动调用积分记录
          const scriptPath = path.join(__dirname, 'edu_backend.py');
          try {
            const result = execSync(
              `python3 "${scriptPath}" "speech" "${difficulty}"`,
              { encoding: 'utf-8', timeout: 15000 }
            );
            const parsed = JSON.parse(result);
            if (parsed.prompt) text = parsed.prompt;
            else if (parsed.result) text = typeof parsed.result === 'object' ? JSON.stringify(parsed.result, null, 2) : parsed.result;
            else text = JSON.stringify(parsed, null, 2);
          } catch(e) {
            text = runEduBackend('speech', difficulty);
          }
        } else {
          text = runEduBackend('speech', difficulty);
        }
      } else if (name === 'speech_get_sentence') {
        // 获取单句口语练习
        const scriptPath = path.join(__dirname, 'edu_backend.py');
        try {
          const result = execSync(
            `python3 -c "import sys; sys.path.insert(0, '.'); import speech_practice as sp; print(sp.get_sentence('${args.difficulty || '中级'}'))"`,
            { encoding: 'utf-8', cwd: __dirname, timeout: 5000 }
          );
          text = result.trim();
        } catch(e) {
          text = '获取句子失败';
        }
      }
      
      // 运动打卡
      else if (name === 'exercise') {
        // exercise <type> [duration/count]
        const exParts = [args.type || 'other'];
        if (['running', 'cycling'].includes(args.type) && args.duration) {
          exParts.push(String(args.duration));
        }
        if (args.type === 'jump_rope' && args.count) {
          exParts.push(String(args.count));
        }
        text = runEduBackend('exercise', exParts.join(' '));
      } else if (name === 'exercise_status') {
        text = runEduBackend('exercise_status');
      } else if (name === 'exercise_achievements') {
        text = runEduBackend('exercise_achievements');
      }
      
      // 每日打卡
      else if (name === 'checkin') {
        // 传具体时段或留空(自动检测)
        const period = args.period || '';
        text = runEduBackend('checkin', period);
      } else if (name === 'checkin_status') {
        text = runEduBackend('checkin_status');
      } else if (name === 'checkin_reminder') {
        text = runEduBackend('checkin_reminder');
      }
      
      // 每日挑战
      else if (name === 'daily_quiz') {
        // 提交答案或获取题目
        if (args.answer) {
          // 提交答案：调用 answer_daily_quiz 核对答案并记录积分
          const scriptPath = path.join(__dirname, 'edu_backend.py');
          try {
            const result = execSync(
              `python3 "${scriptPath}" "daily_quiz" "${args.answer}"`,
              { encoding: 'utf-8', cwd: __dirname, timeout: 15000 }
            );
            const parsed = JSON.parse(result);
            text = parsed.message || JSON.stringify(parsed, null, 2);
            if (parsed.correct) {
              text += `\n💡 解析: ${parsed.explanation}`;
            }
          } catch(e) {
            text = "答题提交失败，请重试。";
          }
        } else {
          text = runEduBackend('daily_quiz');
        }
      } else if (name === 'claim_daily') {
        text = runEduBackend('claim_daily');
      }
      
      // 趋势分析
      else if (name === 'trend_report') {
        text = runEduBackend('trend_report');
      } else if (name === 'weekly_report') {
        text = runEduBackend('weekly_report');
      } else if (name === 'monthly_report') {
        text = runEduBackend('monthly_report');
      } else if (name === 'category_breakdown') {
        text = runEduBackend('category_breakdown');
      }
      
      // 家长控制面板
      else if (name === 'parent_stats') {
        text = runEduBackend('parent_stats');
      } else if (name === 'parent_reset') {
        const what = args.what || 'all';
        text = runEduBackend('parent_reset', what);
      } else if (name === 'parent_add_reward') {
        // parent_add_reward <name> <cost> <desc> [category]
        const parts = [
          args.name || '自定义奖励',
          String(args.cost || 20),
          args.desc || '家长自定义奖励',
          args.category || '其他'
        ];
        text = runEduBackend('parent_add_reward', parts.join(' '));
      } else if (name === 'parent_set_rules') {
        text = runEduBackend('parent_set_rules', `${args.field} ${args.value}`);
      }
      
      // 激励系统
      else if (name === 'chore') {
        text = runEduBackend('chore', args.chore_name || '整理书桌');
      } else if (name === 'positive') {
        text = runEduBackend('positive', args.action_type || 'proactive');
      } else if (name === 'penalty') {
        text = runEduBackend('penalty', args.penalty_type || 'copying');
      }
      
      else {
        text = '未知工具: ' + name + '\n可用工具: ' + JSON.stringify(TOOLS.map(t => t.name));
      }
      
      ws.send(JSON.stringify({ jsonrpc: '2.0', id: msg.id, result: { content: [{ type: 'text', text: text }] } }));
    }
  });
}
console.log('xiaozhi Edu MCP Client v3.0 starting...');
connect();
