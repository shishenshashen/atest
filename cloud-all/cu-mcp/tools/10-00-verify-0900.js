// 10:00 收尾 09:00 验证: MOC + 14 实物 mtime + 09:00 plan 落盘
const fs = require('fs');
const path = require('path');

const MT5_BASE = 'C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes\\Terminal\\D0E8209F77C8CF37AD8BF550E51FF075\\MQL5\\Experts';
const EA_LIST = [
  { name: 'MeanReversion_EA.mq5',  bytes: 13503, dir: 'minimax-ea' },
  { name: 'ScalperXAU.mq5',        bytes: 42824, dir: 'minimax-ea' },
  { name: 'TrendMA_EA.mq5',        bytes: 9169,  dir: 'minimax-ea' },
  { name: 'Breakout_EA.mq5',       bytes: 9530,  dir: 'minimax-ea' },
  { name: 'MyEA.mq5',              bytes: 12541, dir: 'minimax-ea' },
  { name: 'Dashboard.mq5',         bytes: 8361,  dir: 'minimax-ea' },
  { name: 'ScalperXAUv5simple.mq5', bytes: 6545, dir: 'minimax-ea' },
  { name: 'ScalperXAUv6debug.mq5', bytes: 1931,  dir: 'minimax-ea' },
  { name: 'ScalperXAUv7debug.mq5', bytes: 4515,  dir: 'minimax-ea' },
  { name: 'ScalperXAUv8.mq5',      bytes: 5436,  dir: 'minimax-ea' },
  { name: 'ScalperXAUv9.mq5',      bytes: 13186, dir: 'minimax-ea' },
  { name: 'Scalper_CsvProto.mq5',  bytes: 4595,  dir: 'minimax-ea' },
  { name: 'MiniMaxScalper.mq5',    bytes: 35357, dir: 'minimax-ea' },
  { name: 'MiniMaxScalper_v2.mq5', bytes: 37470, dir: 'minimax-ea' }
];

const MOC = 'C:\\ai\\obsidian-文件\\mt\\EA开发\\EA 开发知识库.md';
const PLAN_DIR = 'C:\\Users\\Administrator\\.mavis\\plans\\plan_f0a74f6e';

console.log('=== 1. MOC 状态 ===');
if (fs.existsSync(MOC)) {
  const s = fs.statSync(MOC);
  console.log(`MOC path: ${MOC}`);
  console.log(`MOC bytes: ${s.size}`);
  console.log(`MOC mtime: ${s.mtime.toISOString()}`);
} else {
  console.log(`MOC NOT FOUND: ${MOC}`);
}

console.log('\n=== 2. 14 实物 .mq5 mtime 验证 ===');
let unchanged = 0, changed = 0, missing = 0;
EA_LIST.forEach(ea => {
  const p = path.join(MT5_BASE, ea.dir, ea.name);
  if (fs.existsSync(p)) {
    const s = fs.statSync(p);
    const ok = s.size === ea.bytes ? '✅' : '⚠ SIZE';
    if (s.size === ea.bytes) unchanged++;
    else changed++;
    console.log(`  ${ok} ${ea.name}: ${s.size}B / ${s.mtime.toISOString()}`);
  } else {
    missing++;
    console.log(`  ❌ ${ea.name}: NOT FOUND at ${p}`);
  }
});
console.log(`\n  14 实物 UNCHANGED: ${unchanged}/14, changed: ${changed}, missing: ${missing}`);

console.log('\n=== 3. 09:00 plan_f0a74f6e 落盘 ===');
const files = [
  'state.json', 'decision.json', 'plan.yaml', 'board.md',
  'outputs/T2-wiki-link-audit/deliverable.md',
  'outputs/T3-broker-wiki-extension/deliverable.md',
  'daily-track2-result.md', 'daily-track3-result.md',
  'validate-results.json', 'track2-result.md', 'track3-result.md'
];
function walk(dir, depth = 0) {
  if (depth > 2) return;
  if (!fs.existsSync(dir)) {
    console.log(`  (dir not found: ${dir})`);
    return;
  }
  const items = fs.readdirSync(dir, { withFileTypes: true });
  items.forEach(item => {
    const p = path.join(dir, item.name);
    if (item.isDirectory()) {
      if (depth === 0) console.log(`  📁 ${item.name}/`);
      walk(p, depth + 1);
    } else {
      const s = fs.statSync(p);
      console.log(`    ${item.name}: ${s.size}B / ${s.mtime.toISOString()}`);
    }
  });
}
walk(PLAN_DIR);

console.log('\n=== 4. daily/2026-06-05.md §09:00 段确认 ===');
const daily = 'C:\\ai\\obsidian-文件\\mt\\00-任务调度中心\\daily\\2026-06-05.md';
if (fs.existsSync(daily)) {
  const txt = fs.readFileSync(daily, 'utf8');
  const m0900 = txt.indexOf('§09:00');
  const m1000 = txt.indexOf('§10:00');
  const mPlan = txt.indexOf('plan_f0a74f6e');
  console.log(`  daily size: ${fs.statSync(daily).size}B`);
  console.log(`  §09:00 位置: ${m0900}`);
  console.log(`  §10:00 位置: ${m1000} ${m1000 < 0 ? '(NOT YET)' : ''}`);
  console.log(`  plan_f0a74f6e 出现位置: ${mPlan}`);
  // 输出 §09:00 段头 200 字符
  if (m0900 >= 0) {
    const head = txt.substring(m0900, m0900 + 300).replace(/\n/g, ' | ');
    console.log(`  §09:00 段头: ${head}`);
  }
}

console.log('\n=== 5. 队列.md 顶部 09:00 区块状态 ===');
const qmd = 'C:\\ai\\obsidian-文件\\mt\\00-任务调度中心\\队列.md';
if (fs.existsSync(qmd)) {
  const txt = fs.readFileSync(qmd, 'utf8');
  const m = txt.indexOf('## 2026-06-05 09:00');
  if (m >= 0) {
    const head = txt.substring(m, m + 400).replace(/\n/g, ' | ');
    console.log(`  09:00 区块: ${head}`);
  } else {
    console.log('  ❌ 队列.md 09:00 区块未找到');
  }
}

console.log('\n=== 6. 归档.md 09:00 plan_f0a74f6e 条目 ===');
const amd = 'C:\\ai\\obsidian-文件\\mt\\00-任务调度中心\\归档.md';
if (fs.existsSync(amd)) {
  const txt = fs.readFileSync(amd, 'utf8');
  const m = txt.indexOf('plan_f0a74f6e');
  console.log(`  plan_f0a74f6e 出现位置: ${m} ${m < 0 ? '(NOT YET — 需补)' : ''}`);
  if (m >= 0) {
    const head = txt.substring(Math.max(0, m - 50), m + 200).replace(/\n/g, ' | ');
    console.log(`  context: ${head}`);
  }
}
