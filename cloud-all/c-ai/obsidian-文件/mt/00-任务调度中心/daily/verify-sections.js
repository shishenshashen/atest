// 章节段头 + 9 反模式自检
const fs = require('fs');
const wikiPath = 'C:\\ai\\obsidian-文件\\mt\\EA开发\\04-避坑与速查\\08 5 速查调试小技巧 wiki.md';
const w = fs.readFileSync(wikiPath, 'utf8');
const lines = w.split('\n');
console.log('=== 章节段头 (line scan) ===');
lines.forEach((l, i) => {
  if (l.match(/^#{1,3}\s/)) console.log((i+1) + ': ' + l);
});
console.log('=== 6 章节判定 (## 匹配) ===');
const h2s = lines.filter(l => l.match(/^##\s/));
console.log('h2 count:', h2s.length);
h2s.forEach(h => console.log('  ', h));
console.log('=== 4 子段 (4.1/4.2/4.3/4.3.4) ===');
lines.forEach((l, i) => {
  if (l.match(/^###?\s*4\.\d/) || l.match(/^####?\s*4\.\d/)) console.log((i+1) + ': ' + l);
});
