const fs = require('fs');
const path = require('path');
const dir = 'EA开发/04-避坑与速查';
const files = [
  '01 编译常见错误.md',
  '02 OrderSend 错误码速查.md',
  '03 实盘 vs 回测差异.md',
  '04 经纪商差异（点差\\手数\\Filling）.md',
  '05 必查清单.md'
];

for (const f of files) {
  const content = fs.readFileSync(path.join(dir, f), 'utf-8');
  const idx = content.indexOf('## 反模式');
  if (idx === -1) { console.log(f, '— no ## 反模式'); continue; }
  const sub = content.substring(idx);
  const re = /### (反模式|永远不要) (\d+)/g;
  const matches = [];
  let m;
  while ((m = re.exec(sub)) !== null) {
    matches.push(m[1] + ' ' + m[2]);
  }
  console.log(f, '— entries:', matches.length, 'numbers:', matches.join(','));
}
