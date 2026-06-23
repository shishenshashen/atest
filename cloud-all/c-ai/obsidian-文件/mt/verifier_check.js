const fs = require('fs');

// Final verifier checks
const p = 'EA开发/EA 开发知识库.md';
const c = fs.readFileSync(p, 'utf-8');

// Check 1: MOC contains '## 反模式 段统一'
console.log('Check 1: MOC contains ## 反模式 段统一:', c.includes('## 反模式 段统一') ? 'PASS' : 'FAIL');

// Check 2: MOC 速查 entries count (should be 7 now: 01-06 + new)
const idx = c.indexOf('## 避坑与速查');
const idx2 = c.indexOf('## 怎么用这套知识库');
const sub = c.substring(idx, idx2);
const entryRe = /^- \[\[/gm;
const entries = (sub.match(entryRe) || []).length;
console.log('Check 2: MOC 速查 entries:', entries, '(expected 7, was 6)');

// Check 3: MOC size
const sz = Buffer.byteLength(c, 'utf-8');
console.log('Check 3: MOC size:', sz, 'bytes (was 6521, expected > 6521)');

// Check 4: 0 placeholders in MOC + 5 速查
const placeholders = (c.match(/TODO|待补|FIXME|TBD|XXX/g) || []).length;
const dir = 'EA开发/04-避坑与速查';
const files = ['01 编译常见错误.md','02 OrderSend 错误码速查.md','03 实盘 vs 回测差异.md','04 经纪商差异（点差\\手数\\Filling）.md','05 必查清单.md'];
let totalPh = placeholders;
for (const f of files) {
  const fc = fs.readFileSync(dir + '/' + f, 'utf-8');
  totalPh += (fc.match(/TODO|待补|FIXME|TBD|XXX/g) || []).length;
}
console.log('Check 4: Total placeholders (MOC + 5 速查):', totalPh, '(expected 0)');

// Check 5: 5 wikis total anti-patterns = 55 (31 baseline + 24 new)
let total = 0;
for (const f of files) {
  const fc = fs.readFileSync(dir + '/' + f, 'utf-8');
  const idx3 = fc.indexOf('## 反模式');
  if (idx3 === -1) continue;
  const sub2 = fc.substring(idx3);
  const re = /### (反模式|永远不要) (\d+)/g;
  let m;
  while ((m = re.exec(sub2)) !== null) {
    total++;
  }
}
console.log('Check 5: Total anti-patterns in 5 wikis:', total, '(expected 55 = 31 baseline + 24 new)');

// Check 6: 0 placeholders for "推荐立即接入" marketing
let mktPh = 0;
const mktRe = /推荐立即接入|强烈推荐|最强大|无敌/;
if (mktRe.test(c)) mktPh++;
for (const f of files) {
  const fc = fs.readFileSync(dir + '/' + f, 'utf-8');
  if (mktRe.test(fc)) mktPh++;
}
console.log('Check 6: Marketing violation (推荐立即接入/强烈推荐/最强大/无敌):', mktPh, '(expected 0)');
