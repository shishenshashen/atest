// 06-05 01:00 巡检 实物落盘确认
const fs = require('fs');
const wikiPath = 'C:\\ai\\obsidian-文件\\mt\\EA开发\\04-避坑与速查\\08 5 速查调试小技巧 wiki.md';
const mocPath = 'C:\\ai\\obsidian-文件\\mt\\EA开发\\EA 开发知识库.md';

const a = fs.statSync(wikiPath);
const b = fs.statSync(mocPath);
const w = fs.readFileSync(wikiPath, 'utf8');

console.log('=== 06-05 01:00 巡检 T2 实物落盘确认 ===');
console.log('wiki:', a.size, 'bytes /', w.split('\n').length, 'lines / mtime', new Date(a.mtime).toISOString());
console.log('moc:', b.size, 'bytes / mtime', new Date(b.mtime).toISOString());
console.log('--- 6 章节段头 ---');
['## 摘要', '## 5 速查调试小技巧分类', '## 5 速查 调试小技巧 完整', '## 03 实盘反模式 4 条 详解', '## SOP 集成', '## 反模式', '## 链向'].forEach(k => {
  const n = (w.match(new RegExp(k.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'g')) || []).length;
  console.log(k, '=', n);
});
console.log('--- 03 实盘 4 子段 命中 ---');
['滑点检测', '延迟监控', '心跳日志', '重连机制'].forEach(k => {
  const n = (w.match(new RegExp(k, 'g')) || []).length;
  console.log(k, '=', n);
});
console.log('--- placeholders ---');
['TODO', '待补', 'FIXME', 'TBD', 'XXX'].forEach(k => {
  const n = (w.match(new RegExp(k, 'g')) || []).length;
  console.log(k, '=', n);
});
console.log('--- 推荐语违规 ---');
['强烈推荐', '最佳实践', '完美', '极致', '必杀技', '一招制胜'].forEach(k => {
  const n = (w.match(new RegExp(k, 'g')) || []).length;
  console.log(k, '=', n);
});
console.log('--- 5 速查现有 wiki 01-07 字节 (期望 UNCHANGED) ---');
['01 编译常见错误速查.md', '02 OrderSend 错误码速查.md', '03 实盘 vs 回测差异.md', '05 必查清单.md', '06 网格马丁警示.md', '07 5 必看陷阱统一 wiki.md'].forEach(f => {
  const p = 'C:\\ai\\obsidian-文件\\mt\\EA开发\\04-避坑与速查\\' + f;
  try {
    const s = fs.statSync(p);
    console.log(f, s.size, 'bytes / mtime', new Date(s.mtime).toISOString());
  } catch (e) {
    console.log(f, 'ERR', e.message);
  }
});
console.log('--- 11 实物 .mq5 mtime (期望 UNCHANGED 06-04 区间) ---');
const ea = 'C:\\Users\\Administrator\\AppData\\Roaming\\MetaQuotes\\Terminal\\D0E8209F77C8CF37AD8BF550E51FF075\\MQL5\\Experts\\minimax-ea';
['MeanReversion_EA.mq5', 'ScalperXAU.mq5', 'MyEA.mq5', 'Dashboard.mq5', 'TrendMA_EA.mq5', 'Breakout_EA.mq5'].forEach(f => {
  const p = ea + '\\' + f;
  try {
    const s = fs.statSync(p);
    console.log(f, s.size, 'bytes / mtime', new Date(s.mtime).toISOString());
  } catch (e) {
    console.log(f, 'ERR', e.message);
  }
});
