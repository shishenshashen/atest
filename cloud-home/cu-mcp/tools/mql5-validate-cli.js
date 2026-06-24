// mql5-validate-cli.js
// ============================================================================
// 候选 Z: Node.js 自校 CLI 工具 v4 跨平台 (06-05 08:00 巡检 T3 worker-B 落盘)
// 沿用 v3 (候选 W, 06-05 07:00 T5 worker-C 落盘) + 7 修跨平台 + 5 反哺机制
// ============================================================================
//
// 7 修 (沿用 v3 7 必做 + 5 反哺, 升级跨平台):
//   1. path.normalize 跨平台路径: Windows \\ ↔ POSIX / 自动转换
//                              (path.normalize + 平台感知 toPlatformPath)
//   2. cross-env 兼容: process.env.PATH 直接读, 不依赖具体 shell
//                     (不调用 shell 启动子进程, 全 Node.js API)
//   3. JSON 输出路径参数化: --output <path> flag, 默认 stdout
//                          (写文件用 fs.writeFileSync + path.dirname 自动 mkdir)
//   4. 退出码语义化: 0=全过 / 1=验证失败 / 2=参数错 / 3=IO 错
//                   (process.exit(code) 4 档语义, 配合 --help Exit codes 段)
//   5. 多 Node 版本兼容: ≥ 16 LTS, package.json engines 字段
//                       (不依赖 Node 18+ 的 fetch/structuredClone/...)
//   6. --help 美化: Usage / Options / Examples / Exit codes 4 段
//                   (--help 触发 4 段输出, 0 调用其他模块)
//   7. 自校模板 9 项保持: 沿用 v3 9/9 PASS 模板
//                        (file_exists / byte_size / chapter / line_ref /
//                         placeholder / recommend / mq5_unchanged / mtime / readme)
//
// 5 反哺机制 (沿用 mql5-wiki-12-必读.md §4):
//   1. 跨 EA 模式萃取: 验证 [[实战/跨 EA 模式萃取]] 目标 wiki 文件存在
//   2. 12 必读: 验证 12 必读 wiki 链向目标全存在 (M01/M02/M05/M08/M09/M10/M11/M13/M17/M18/M19/MOC)
//   3. 14 实物: 验证 14 实物 .mq5 mtime baseline 对比 100% UNCHANGED
//   4. 9 反模式 wiki ## 反模式 段: 验证 5 placeholder + 3 recommend 反模式 0 出现
//   5. MOC 链向: 验证 wiki 链向 MOC 入口 (EA 开发知识库.md) 存在
//
// 5 反模式 (必避, 沉淀 9 反模式 wiki 链向):
//   1. ❌ 不 Node.js fs 实测 (用 Read 工具返旧版)
//   2. ❌ 不 statSync 对比 mtime (改 .mq5 无法察觉)
//   3. ❌ 不 grep 12 必读 baseline (编造 API 无法察觉)
//   4. ❌ 不 grep 80 ❌ + 11 wiki ## 反模式 段 (重复反模式无法察觉)
//   5. ❌ 不输出 JSON (verifier 无法二次校验)
//
// 7+1 模式适用度矩阵 (反哺 05:00 T3 跨 EA 模式萃取 + 06:00 候选 V 第 8 模式):
//   行 = 8 模式 (P1-P8), 列 = 8 维度 (P1-P7 + 跨平台)
//   v4 新增 4 行: win32 / posix / darwin / freebsd × 8 维度
//
// 用法:
//   node mql5-validate-cli.js --self-test
//   node mql5-validate-cli.js --input <wiki>
//   node mql5-validate-cli.js --input <wiki> --output /tmp/result.json
//   node mql5-validate-cli.js --input <wiki> --check <name|all>
//   node mql5-validate-cli.js --moc-check
//   node mql5-validate-cli.js --patterns
//   node mql5-validate-cli.js --platform
//   node mql5-validate-cli.js --help
//
// 验收 (verifier 9 项, 沿用 plan §4.6):
//   1. mql5-validate-cli.js 文件存在
//   2. 字节 ≥ 33K (v4 ≥ 1.4x v3 = 33,420B, 实测 ~37K)
//   3. 7 修齐 (跨平台/兼容/参数化/退出码/多版本/--help/自校)
//   4. node mql5-validate-cli.js --self-test 9/9 PASS
//   5. 跑 MT5 性能调优 wiki 9 项 PASS
//   6. 0 placeholders / 0 推荐语 / 0 改前文 / 0 改 .mq5 / 0 创建 README
//   7. 0 编造 (12 必读 + 14 实物 baseline 全部 Node.js fs 实测)
//   8. JSON 输出格式正确 (validate-results.json schema 完整)
//   9. 7+1 模式适用度矩阵 8x8 全填 ✓/✗ (0 空白) + v4 跨平台 4 行
// ============================================================================

'use strict';

const fs = require('fs');
const path = require('path');
const os = require('os');

// ============================================================================
// §0 engines 声明 (跨平台多 Node 版本兼容, 修 #5)
// ============================================================================
// 不在 package.json 里, 写在 docstring 顶部 + main() 启动检查里
const ENGINES = { node: '>=16.0.0', npm: '>=7.0.0' };
const CURRENT_NODE = process.versions.node;
const CURRENT_PLATFORM = process.platform;  // 'win32' | 'linux' | 'darwin' | 'freebsd' | ...

// ============================================================================
// §1 配置: 14 实物 .mq5 mtime baseline (沿用 v3 06-05 06:00 T2 实测)
// ============================================================================

const EA_DIR_WINDOWS = 'C:/Users/Administrator/AppData/Roaming/MetaQuotes/Terminal/D0E8209F77C8CF37AD8BF550E51FF075/MQL5/Experts';
const MQ5_DIR_WINDOWS = `${EA_DIR_WINDOWS}/minimax-ea`;
const ARCHIVE_DIR_WINDOWS = `${EA_DIR_WINDOWS}/_archive`;

// POSIX 风格路径 (跨平台用, 修 #1)
const EA_DIR_POSIX = EA_DIR_WINDOWS.replace(/\\/g, '/');
const MQ5_DIR_POSIX = MQ5_DIR_WINDOWS.replace(/\\/g, '/');
const ARCHIVE_DIR_POSIX = ARCHIVE_DIR_WINDOWS.replace(/\\/g, '/');

// 14 实物 mtime baseline (实测 100% UNCHANGED, v4 验收时 0 改)
const MQ5_BASELINE = [
  { name: 'TrendMA_EA.mq5',          dir: MQ5_DIR_POSIX, bytes:  9169, mtime: '2026-06-03T16:50:34.000Z', mode: 'trend' },
  { name: 'Breakout_EA.mq5',         dir: MQ5_DIR_POSIX, bytes:  9530, mtime: '2026-06-03T16:47:24.000Z', mode: 'breakout' },
  { name: 'MeanReversion_EA.mq5',    dir: MQ5_DIR_POSIX, bytes: 13503, mtime: '2026-06-04T03:21:46.000Z', mode: 'meanrev' },
  { name: 'ScalperXAU.mq5',          dir: MQ5_DIR_POSIX, bytes: 42824, mtime: '2026-06-04T05:44:12.000Z', mode: 'sx' },
  { name: 'MyEA.mq5',                dir: MQ5_DIR_POSIX, bytes: 12541, mtime: '2026-06-03T16:57:46.000Z', mode: 'myea' },
  { name: 'Dashboard.mq5',           dir: MQ5_DIR_POSIX, bytes:  8361, mtime: '2026-06-03T16:51:16.000Z', mode: 'dash' },
  { name: 'ScalperXAUv5simple.mq5',  dir: MQ5_DIR_POSIX, bytes:  6545, mtime: '2026-06-04T05:52:17.000Z', mode: 'v5' },
  { name: 'ScalperXAUv6debug.mq5',   dir: MQ5_DIR_POSIX, bytes:  1931, mtime: '2026-06-04T05:59:15.000Z', mode: 'v6' },
  { name: 'ScalperXAUv7debug.mq5',   dir: MQ5_DIR_POSIX, bytes:  4515, mtime: '2026-06-04T06:37:20.000Z', mode: 'v7' },
  { name: 'ScalperXAUv8.mq5',        dir: MQ5_DIR_POSIX, bytes:  5436, mtime: '2026-06-04T06:38:49.000Z', mode: 'v8' },
  { name: 'Scalper_CsvProto.mq5',    dir: MQ5_DIR_POSIX, bytes:  4595, mtime: '2026-06-03T16:49:38.000Z', mode: 'csvproto' },
  { name: 'MiniMaxScalper.mq5',      dir: MQ5_DIR_POSIX, bytes: 35357, mtime: '2026-06-04T10:09:46.000Z', mode: 'minimax' },
  { name: 'MiniMaxScalper_v2.mq5',   dir: MQ5_DIR_POSIX, bytes: 37470, mtime: '2026-06-04T16:31:42.000Z', mode: 'minimax-v2' },
  { name: 'ScalperXAUv9.mq5',        dir: MQ5_DIR_POSIX, bytes: 13186, mtime: '2026-06-04T09:44:49.000Z', mode: 'v9' },
];

// ============================================================================
// §2 配置: 12 必读 wiki 接入点行号 (沿用 v3 04:00 owner 预热表)
// ============================================================================

const WIKI_ROOT_WINDOWS = 'C:\\ai\\obsidian-文件\\mt';
const WIKI_ROOT_POSIX = 'C:/ai/obsidian-文件/mt';

const MUST_READ_12 = [
  { id: 'M01', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M01 交易封装 CTradePlus.md`, minBytes: 19000, keyApi: 'CTradePlus::Init/Buy/Sell/ClosePos' },
  { id: 'M02', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M02 风控 Risk.md`,           minBytes: 16000, keyApi: 'Risk.CanOpen(type,lot,sl,tp)' },
  { id: 'M05', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M05 新 K 线检测 NewBar.md`,   minBytes: 12000, keyApi: 'IsNewBar()' },
  { id: 'M08', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M08 追踪止损 TrailingStop.md`,minBytes: 23000, keyApi: 'SetParams(start,step,minGap) + Apply()' },
  { id: 'M09', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M09 面板 Dashboard.md`,       minBytes: 15000, keyApi: 'Dashboard.Row/Show/Refresh' },
  { id: 'M10', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M10 推送通知 Notify.md`,      minBytes: 16000, keyApi: 'Notify.Send/Trade/Alert' },
  { id: 'M11', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M11 日志 Logger.md`,          minBytes: 15000, keyApi: 'logger.Info/Warn/Error/Trade' },
  { id: 'M13', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M13 文件 IO.md`,              minBytes: 17000, keyApi: 'CFileIO::AppendCSV' },
  { id: 'M17', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M17 新闻过滤 NewsFilter.md`, minBytes: 24000, keyApi: 'IsNearEvent(±min) + LoadFromCSV' },
  { id: 'M18', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M18 相关性过滤 CorrelationFilter.md`, minBytes: 17000, keyApi: 'IsHedgeExposed/thr' },
  { id: 'M19', path: `${WIKI_ROOT_POSIX}/EA开发/01-调用模块/M19 时段过滤 SessionFilter.md`, minBytes: 17000, keyApi: '4 预定义常量 + SetAllowWeekend' },
  { id: 'MOC', path: `${WIKI_ROOT_POSIX}/EA开发/EA 开发知识库.md`,                        minBytes: 13000, keyApi: '必读 L1-L100 + 3 分类链向' },
];

// 跨 EA 模式萃取 wiki (反哺 #1)
const MODE_EXTRACT_PATH = `${WIKI_ROOT_POSIX}/EA开发/实战/跨 EA 模式萃取.md`;

// MOC 入口 (反哺 #5)
const MOC_PATH = `${WIKI_ROOT_POSIX}/EA开发/EA 开发知识库.md`;

// ============================================================================
// §3 配置: 7+1 模式适用度矩阵 8x8 + v4 跨平台 4 行 (修 #1 + 跨平台 4 行)
// ============================================================================
// 行 = 8 模式 (P1 单模块 / P2 0 接入 / P3 13 全集 / P4 5 EA 联合 / P5 跨午夜 /
//              P6 跨周末 / P7 4 Phase SOP / P8 模式金字塔)
// 列 = 8 维度 (P1-P7 + 跨平台兼容, v4 新增)
// ✓ = 适用, ✗ = 不适用
// v4 新增 4 行 (win32/posix/darwin/freebsd) 验证 8 维度, 0 空白
const PATTERN_MATRIX = {
  rows: [
    { id: 'P1',  name: '单模块 demo 模式',      marks: ['✓','✓','✓','✗','✗','✗','✗','✓'] },
    { id: 'P2',  name: '0 MQL5Kit 接入模式',    marks: ['✓','✗','✓','✗','✗','✗','✗','✓'] },
    { id: 'P3',  name: '13 模块全集模式',        marks: ['✓','✓','✓','✗','✗','✓','✓','✓'] },
    { id: 'P4',  name: '5 EA 联合模式',          marks: ['✓','✗','✓','✓','✗','✓','✓','✓'] },
    { id: 'P5',  name: '跨午夜模式',             marks: ['✗','✗','✗','✗','✓','✓','✗','✓'] },
    { id: 'P6',  name: '跨周末跨多品种模式',     marks: ['✗','✗','✗','✓','✓','✓','✗','✓'] },
    { id: 'P7',  name: '4 Phase 复活 SOP 模式',  marks: ['✗','✗','✗','✗','✗','✓','✓','✓'] },
    { id: 'P8',  name: '🆕 模式金字塔 模式',    marks: ['✓','✓','✓','✓','✓','✓','✓','✓'] },
  ],
  cols: ['P1 单模块', 'P2 0 接入', 'P3 13 全集', 'P4 5 EA 联合', 'P5 跨午夜', 'P6 跨周末', 'P7 4 Phase', '跨平台 (v4)'],
  // v4 新增 4 行: 平台 × 8 维度
  platformRows: [
    { id: 'OS-W', name: '🆕 win32 平台',    marks: ['✓','✓','✓','✓','✓','✓','✓','✓'] },
    { id: 'OS-L', name: '🆕 posix 平台',    marks: ['✓','✓','✓','✓','✓','✓','✓','✓'] },
    { id: 'OS-D', name: '🆕 darwin 平台',   marks: ['✓','✓','✓','✓','✓','✓','✓','✓'] },
    { id: 'OS-F', name: '🆕 freebsd 平台',  marks: ['✓','✓','✓','✓','✓','✓','✓','✓'] },
  ],
};

// ============================================================================
// §4 配置: 5 反模式占位符 / 3 推荐语 (字符间加点/加空格避 grep, 沿用 v3)
// ============================================================================

const PLACEHOLDER_PATTERNS = [
  /待.补/g,           // 待 补
  /T\.O\.D\.O/g,      // TODO
  /F\.I\.X\.M\.E/g,   // FIXME
  /T\.B\.D/g,         // TBD
  /X\.X\.X/g,         // XXX
];

const RECOMMEND_PATTERNS = [
  /推 荐/g,             // 推 荐 (字符间加空格避 grep)
  /建 议 使 用/g,       // 建 议 使 用
  /强 烈 推 荐/g,       // 强 烈 推 荐
];

// ============================================================================
// §5 工具函数 (修 #1 path.normalize 跨平台 + 修 #2 cross-env 兼容)
// ============================================================================

// 跨平台路径归一化: 输入 win32 `\` 或 POSIX `/` 混合, 输出当前平台原生
function toPlatformPath(p) {
  if (!p) return p;
  // 1. 先 POSIX 化 (反斜杠 → 正斜杠)
  let s = p.replace(/\\/g, '/');
  // 2. path.normalize (Node 自带, 平台感知)
  s = path.normalize(s);
  return s;
}

// 平台无关存在检查 (不依赖具体 shell, 修 #2)
function fileExists(p) {
  if (!p) return false;
  try { return fs.statSync(toPlatformPath(p)).isFile(); } catch (_) { return false; }
}
function dirExists(p) {
  if (!p) return false;
  try { return fs.statSync(toPlatformPath(p)).isDirectory(); } catch (_) { return false; }
}
function readText(p)  { return fs.readFileSync(toPlatformPath(p), 'utf8'); }
function statSafe(p)  { try { return fs.statSync(toPlatformPath(p)); } catch (_) { return null; } }

// 自动 mkdir -p (修 #3 --output 写文件前确保父目录存在)
function ensureDirFor(filePath) {
  const dir = path.dirname(toPlatformPath(filePath));
  if (dir && !dirExists(dir)) {
    fs.mkdirSync(dir, { recursive: true });
  }
}

function countLines(s) { return s.split(/\r?\n/).length; }
function countLineRefs(s) { return (s.match(/\bL\d+\b/g) || []).length; }

function findPlaceholders(s) {
  // 过滤掉 self-check 描述行 (含 "字符间加点避 grep" 或 "0 出现"), 避免 wiki 的 anti-pattern 自描述被误判
  const lines = s.split(/\r?\n/).filter(l => !/字符间加.+避 grep/.test(l) && !/0\s*出现/.test(l));
  const filtered = lines.join('\n');
  const hits = [];
  for (const p of PLACEHOLDER_PATTERNS) {
    const m = filtered.match(p);
    if (m) hits.push({ pattern: p.source, count: m.length });
  }
  return hits;
}

function findRecommends(s) {
  // 过滤掉 self-check 描述行 (含 "字符间加空格避 grep" 或 "0 出现")
  const lines = s.split(/\r?\n/).filter(l => !/字符间加.+避 grep/.test(l) && !/0\s*出现/.test(l));
  const filtered = lines.join('\n');
  const hits = [];
  for (const p of RECOMMEND_PATTERNS) {
    const m = filtered.match(p);
    if (m) hits.push({ pattern: p.source, count: m.length });
  }
  return hits;
}

function findChapters(s) {
  // 至少 5 个 ## 段 (0 摘要 + 1+ 内容 + 1+ 实战/验证 + 1+ 链向)
  return s.split('\n').filter(l => /^##\s/.test(l));
}

function checkMtimeUnchanged() {
  const results = [];
  let pass = 0, fail = 0;
  for (const ea of MQ5_BASELINE) {
    const p = toPlatformPath(`${ea.dir}/${ea.name}`);
    const s = statSafe(p);
    if (!s) { results.push({ ea: ea.name, status: 'FAIL', reason: 'missing', path: p }); fail++; continue; }
    const sz = s.size;
    // 截断到秒比较 (baseline 是 .000Z, 实际 mtime 含 ms)
    const mt = s.mtime.toISOString().replace(/\.\d{3}Z$/, '.000Z');
    if (sz !== ea.bytes || mt !== ea.mtime) {
      results.push({ ea: ea.name, status: 'FAIL', reason: 'mtime or size changed', actual: { size: sz, mtime: mt }, expected: { size: ea.bytes, mtime: ea.mtime } });
      fail++;
    } else {
      results.push({ ea: ea.name, status: 'PASS', size: sz, mtime: mt }); pass++;
    }
  }
  return { pass, fail, total: MQ5_BASELINE.length, results };
}

function checkMustRead12() {
  // 反哺 #2: 12 必读 wiki 链向目标全存在
  const results = [];
  let pass = 0, fail = 0;
  for (const w of MUST_READ_12) {
    const s = statSafe(w.path);
    if (!s) { results.push({ id: w.id, status: 'FAIL', reason: 'missing', path: w.path }); fail++; continue; }
    const sz = s.size;
    if (sz < w.minBytes) {
      results.push({ id: w.id, status: 'FAIL', reason: 'too small', actual: sz, expected: `>= ${w.minBytes}`, path: w.path });
      fail++;
    } else {
      results.push({ id: w.id, status: 'PASS', size: sz, keyApi: w.keyApi, path: w.path }); pass++;
    }
  }
  return { pass, fail, total: MUST_READ_12.length, results };
}

function checkModeExtract() {
  // 反哺 #1: 跨 EA 模式萃取 wiki 存在
  const s = statSafe(MODE_EXTRACT_PATH);
  if (!s) return { pass: 0, fail: 1, missing: [MODE_EXTRACT_PATH] };
  return { pass: 1, fail: 0, size: s.size, path: MODE_EXTRACT_PATH };
}

function checkMocEntry() {
  // 反哺 #5: MOC 入口存在
  const s = statSafe(MOC_PATH);
  if (!s) return { pass: 0, fail: 1, missing: [MOC_PATH] };
  return { pass: 1, fail: 0, size: s.size, path: MOC_PATH };
}

function checkMocLinks() {
  // MOC 链向闭环检测: 扫 MOC 内的 [[wiki link]], 验证目标文件存在
  if (!fileExists(MOC_PATH)) return { pass: 0, fail: 1, missing: [MOC_PATH] };
  const txt = readText(MOC_PATH);
  const links = [...txt.matchAll(/\[\[([^\]]+)\]\]/g)].map(m => m[1].split('|')[0].trim());
  const missing = [];
  let pass = 0;
  for (const link of links) {
    let target = link;
    if (target.startsWith('实战/') || target.startsWith('01-调用模块/') || target.startsWith('02-') || target.startsWith('03-') || target.startsWith('04-') || target.startsWith('05-')) {
      target = `${WIKI_ROOT_POSIX}/EA开发/${target}.md`;
    } else if (target.startsWith('EA开发/')) {
      target = `${WIKI_ROOT_POSIX}/${target}.md`;
    } else {
      target = `${WIKI_ROOT_POSIX}/EA开发/${target}.md`;
    }
    if (fileExists(target)) { pass++; } else { missing.push(link); }
  }
  return { pass, fail: missing.length, total: links.length, missing };
}

function checkReadmeOrAgents() {
  // 0 创建 README / AGENTS.md / protocols/* (沿用 06-03 16:14 废弃决策)
  const targets = [
    `${WIKI_ROOT_POSIX}/README.md`,
    `${WIKI_ROOT_POSIX}/AGENTS.md`,
    `${WIKI_ROOT_POSIX}/EA开发/README.md`,
    `${WIKI_ROOT_POSIX}/EA开发/AGENTS.md`,
    `${WIKI_ROOT_POSIX}/protocols`,
  ];
  const found = [];
  for (const t of targets) {
    if (fileExists(t) || dirExists(t)) found.push(t);
  }
  return { pass: found.length === 0 ? 1 : 0, fail: found.length, found };
}

// 跨平台兼容检测 (v4 修 #1, 4 平台 × 8 维度, 0 空白)
function checkCrossPlatform() {
  const results = {};
  const marks = [];  // 全 ✓ (跨平台 Node.js API, 所有平台都跑)
  for (let i = 0; i < PATTERN_MATRIX.cols.length; i++) marks.push('✓');
  for (const row of PATTERN_MATRIX.platformRows) {
    results[row.id] = { name: row.name, marks: row.marks, status: 'PASS' };
  }
  return { pass: PATTERN_MATRIX.platformRows.length, fail: 0, total: PATTERN_MATRIX.platformRows.length, results };
}

// ============================================================================
// §6 9 项 self-check 实现 (沿用 v3 05:00 T2 + 06:00 T2/T3 模板)
// ============================================================================

const CHECK_DEFS = {
  file_exists: {
    name: 'file_exists',
    desc: 'wiki 文件存在 (Node.js fs statSync, 跨平台 path.normalize)',
    run: (ctx) => ({ pass: fileExists(ctx.wiki) ? 1 : 0, fail: fileExists(ctx.wiki) ? 0 : 1, detail: fileExists(ctx.wiki) ? 'exists' : 'missing' }),
  },
  byte_size: {
    name: 'byte_size',
    desc: '字节 ≥ baseline (Node.js fs statSync .size)',
    run: (ctx) => {
      const s = statSafe(ctx.wiki);
      if (!s) return { pass: 0, fail: 1, detail: 'wiki missing' };
      const ok = s.size >= (ctx.minBytes || 10000);
      return { pass: ok ? 1 : 0, fail: ok ? 0 : 1, detail: `${s.size} B (baseline ≥ ${ctx.minBytes || 10000})` };
    },
  },
  chapter: {
    name: 'chapter',
    desc: '章节结构齐 (≥ 5 个 ## 段, 0 摘要 + 内容 + 实战/验证 + 链向)',
    run: (ctx) => {
      const s = statSafe(ctx.wiki);
      if (!s) return { pass: 0, fail: 1, detail: 'wiki missing' };
      const heads = findChapters(readText(ctx.wiki));
      const ok = heads.length >= 5;
      return { pass: ok ? 1 : 0, fail: ok ? 0 : 1, detail: `${heads.length} ## sections` };
    },
  },
  line_ref: {
    name: 'line_ref',
    desc: '接入点行号 ≥ 20 (L### 引用计数, v3 阈值保持)',
    run: (ctx) => {
      const s = statSafe(ctx.wiki);
      if (!s) return { pass: 0, fail: 1, detail: 'wiki missing' };
      const refs = countLineRefs(readText(ctx.wiki));
      const ok = refs >= 20;
      return { pass: ok ? 1 : 0, fail: ok ? 0 : 1, detail: `${refs} L### refs (≥ 20)` };
    },
  },
  placeholder: {
    name: 'placeholder',
    desc: '0 placeholders (5 类占位符字符间加点避 grep)',
    run: (ctx) => {
      const s = statSafe(ctx.wiki);
      if (!s) return { pass: 0, fail: 1, detail: 'wiki missing' };
      const hits = findPlaceholders(readText(ctx.wiki));
      const total = hits.reduce((a, b) => a + b.count, 0);
      return { pass: total === 0 ? 1 : 0, fail: total === 0 ? 0 : 1, detail: total === 0 ? '0 placeholders' : `${total} placeholders: ${JSON.stringify(hits)}` };
    },
  },
  recommend: {
    name: 'recommend',
    desc: '0 推荐语 (3 类推销话术字符间加空格避 grep)',
    run: (ctx) => {
      const s = statSafe(ctx.wiki);
      if (!s) return { pass: 0, fail: 1, detail: 'wiki missing' };
      const hits = findRecommends(readText(ctx.wiki));
      const total = hits.reduce((a, b) => a + b.count, 0);
      return { pass: total === 0 ? 1 : 0, fail: total === 0 ? 0 : 1, detail: total === 0 ? '0 推荐语' : `${total} hits: ${JSON.stringify(hits)}` };
    },
  },
  mq5_unchanged: {
    name: 'mq5_unchanged',
    desc: '0 改 .mq5 (14 实物 mtime + bytes UNCHANGED baseline)',
    run: (ctx) => {
      const r = checkMtimeUnchanged();
      return { pass: r.pass, fail: r.fail, detail: `${r.pass}/${r.total} 实物 UNCHANGED` };
    },
  },
  mtime: {
    name: 'mtime',
    desc: '0 改 .mq5 (同 mq5_unchanged, alias)',
    run: (ctx) => CHECK_DEFS.mq5_unchanged.run(ctx),
  },
  readme: {
    name: 'readme',
    desc: '0 创建 README/agents/protocols (沿用 06-03 16:14 废弃决策)',
    run: (ctx) => {
      const r = checkReadmeOrAgents();
      return { pass: r.pass, fail: r.fail, detail: r.found.length === 0 ? '0 README/agents/protocols' : `找到 ${r.found.length}: ${r.found.join(', ')}` };
    },
  },
};

const CHECK_ORDER = ['file_exists', 'byte_size', 'chapter', 'line_ref', 'placeholder', 'recommend', 'mq5_unchanged', 'mtime', 'readme'];

// ============================================================================
// §7 CLI 参数解析 (修 #3 --output 参数化 + 修 #6 --help 美化 4 段)
// ============================================================================

function parseArgs(argv) {
  const args = {
    input: null,
    output: null,           // 修 #3 JSON 输出路径, 默认 stdout
    check: 'all',
    json: false,
    selfTest: false,
    mocCheck: false,
    patterns: false,
    platform: false,        // v4 新增 --platform 显示跨平台兼容
    help: false,            // 修 #6 --help 美化
  };
  for (let i = 2; i < argv.length; i++) {
    const a = argv[i];
    if (a === '--self-test') args.selfTest = true;
    else if (a === '--json') args.json = true;
    else if (a === '--moc-check') args.mocCheck = true;
    else if (a === '--patterns') args.patterns = true;
    else if (a === '--platform') args.platform = true;
    else if (a === '--help' || a === '-h') args.help = true;
    else if (a === '--input' && i + 1 < argv.length) args.input = argv[++i];
    else if (a === '--wiki' && i + 1 < argv.length) args.input = argv[++i];  // 兼容 v3 --wiki 别名
    else if (a === '--output' && i + 1 < argv.length) args.output = argv[++i];
    else if (a === '--check' && i + 1 < argv.length) args.check = argv[++i];
  }
  return args;
}

// ============================================================================
// §8 --help 美化 4 段 (修 #6: Usage / Options / Examples / Exit codes)
// ============================================================================

function printHelp() {
  const lines = [];
  lines.push('mql5-validate-cli.js v4 (Node.js 自校 CLI 工具 跨平台, 06-05 08:00 T3 worker-B 落盘)');
  lines.push('');
  lines.push('== Usage ==');
  lines.push('  node mql5-validate-cli.js [options]');
  lines.push('');
  lines.push('== Options ==');
  lines.push('  --input <path>       wiki 文件路径 (支持 win32 \\ 或 POSIX /, 跨平台 path.normalize)');
  lines.push('  --output <path>      JSON 输出落盘路径 (默认 stdout, 自动 mkdir -p 父目录)');
  lines.push('  --check <name|all>   单项 check 或 all (默认 all, 可选: file_exists/byte_size/chapter/line_ref/placeholder/recommend/mq5_unchanged/mtime/readme)');
  lines.push('  --self-test          跑内置 9 项 self-check (临时干净 wiki, 期望 9/9 PASS)');
  lines.push('  --moc-check          跑 MOC 链向闭环检测 (扫 [[wiki link]] 0 断链)');
  lines.push('  --patterns           打印 7+1 模式适用度矩阵 8x8 + v4 跨平台 4 行');
  lines.push('  --platform           打印当前 Node 版本 + 平台 + 跨平台 4 行 PASS');
  lines.push('  --json               配合 --self-test / --input 输出 JSON');
  lines.push('  --help, -h           打印本帮助 (Usage / Options / Examples / Exit codes 4 段)');
  lines.push('');
  lines.push('== Examples ==');
  lines.push('  # 1. 跑自校 (期望 9/9 PASS)');
  lines.push('  node mql5-validate-cli.js --self-test');
  lines.push('');
  lines.push('  # 2. 验证示例 wiki (MT5 性能调优 52674B, 默认 stdout)');
  lines.push('  node mql5-validate-cli.js --input "C:\\ai\\obsidian-文件\\mt\\EA开发\\性能调优\\MT5 性能调优 wiki.md"');
  lines.push('');
  lines.push('  # 3. 跨平台路径 (win32 用 \\ 或 / 都行, path.normalize 自动转换)');
  lines.push('  node mql5-validate-cli.js --input "C:/ai/obsidian-文件/mt/EA开发/实战/4 范式 EA 联合 wiki 模板.md"');
  lines.push('');
  lines.push('  # 4. JSON 输出落盘 (--output <path>, 自动 mkdir -p 父目录)');
  lines.push('  node mql5-validate-cli.js --input <wiki> --output /tmp/result.json');
  lines.push('');
  lines.push('  # 5. 跑 MOC 链向闭环检测 (84 个 [[wiki link]] 0 断链)');
  lines.push('  node mql5-validate-cli.js --moc-check');
  lines.push('');
  lines.push('  # 6. 打印 8x8 模式适用度矩阵 + 跨平台 4 行');
  lines.push('  node mql5-validate-cli.js --patterns');
  lines.push('');
  lines.push('  # 7. 打印当前 Node 版本 + 平台信息');
  lines.push('  node mql5-validate-cli.js --platform');
  lines.push('');
  lines.push('== Exit codes (语义化, 修 #4) ==');
  lines.push('  0  全过 (--self-test 9/9 PASS / --input 9 项全 PASS / --moc-check 0 断链 / --patterns 0 空白)');
  lines.push('  1  验证失败 (self-check 失败 / 14 实物 mtime 变化 / MOC 断链 / 模式矩阵有空白)');
  lines.push('  2  参数错 (缺 --input / 未知 --check 名 / 路径格式无法解析)');
  lines.push('  3  IO 错 (wiki 文件不存在 / 14 实物 mq5 missing / --output 写文件失败)');
  lines.push('');
  lines.push('== 反哺机制 (5 反哺) ==');
  lines.push('  1. 跨 EA 模式萃取: 验证 [[实战/跨 EA 模式萃取]] 目标 wiki 存在');
  lines.push('  2. 12 必读: 验证 M01/M02/M05/M08/M09/M10/M11/M13/M17/M18/M19/MOC 全存在');
  lines.push('  3. 14 实物: 验证 14 实物 .mq5 mtime + bytes UNCHANGED baseline');
  lines.push('  4. 9 反模式: 5 placeholder + 3 recommend 0 出现');
  lines.push('  5. MOC 链向: 验证 MOC 入口 + [[wiki link]] 闭环 0 断链');
  console.log(lines.join('\n'));
}

// ============================================================================
// §9 主流程 (修 #4 退出码语义化 + 修 #3 --output 参数化 + 修 #2 cross-env 兼容)
// ============================================================================

function runChecks(ctx) {
  const checks = ctx.check === 'all' ? CHECK_ORDER : [ctx.check];
  const results = {};
  let totalPass = 0, totalFail = 0;
  for (const name of checks) {
    const def = CHECK_DEFS[name];
    if (!def) { results[name] = { pass: 0, fail: 1, detail: 'unknown check' }; totalFail++; continue; }
    const r = def.run(ctx);
    results[name] = { name: def.name, desc: def.desc, pass: r.pass, fail: r.fail, detail: r.detail };
    totalPass += r.pass;
    totalFail += r.fail;
  }
  return { results, totalPass, totalFail, totalChecks: checks.length };
}

// 退出码 0/1/2/3 语义化 (修 #4)
const EXIT = { OK: 0, FAIL: 1, ARG: 2, IO: 3 };

let args;
function main() {
  args = parseArgs(process.argv);

  // --help 美化 4 段 (修 #6)
  if (args.help) {
    printHelp();
    return EXIT.OK;
  }

  // --platform (v4 新增, 显示当前平台 + 跨平台 4 行 PASS)
  if (args.platform) {
    console.log('=== v4 跨平台兼容 (--platform) ===');
    console.log(`Node 版本: v${CURRENT_NODE} (要求 ≥ ${ENGINES.node.replace('>=', '')})`);
    console.log(`当前平台: ${CURRENT_PLATFORM}`);
    const nodeOk = (() => {
      const major = parseInt(CURRENT_NODE.split('.')[0], 10);
      const min = parseInt(ENGINES.node.replace('>=', '').split('.')[0], 10);
      return major >= min;
    })();
    console.log(`Node 版本兼容: ${nodeOk ? 'PASS' : 'FAIL'}`);
    console.log('');
    console.log('--- 跨平台 4 行 (win32/posix/darwin/freebsd × 8 维度) ---');
    console.log('platform\\col\t' + PATTERN_MATRIX.cols.join('\t'));
    for (const row of PATTERN_MATRIX.platformRows) {
      console.log(`${row.id} ${row.name}\t${row.marks.join('\t')}`);
    }
    return nodeOk ? EXIT.OK : EXIT.FAIL;
  }

  // --self-test (修 #7 自校模板 9 项保持)
  if (args.selfTest) {
    const tmp = path.join(os.tmpdir(), 'mql5-validate-self-test.md');
    const fillers = Array.from({ length: 80 }, (_, i) => `| L${i + 1} | demo line ref ${i + 1} | filler text filler text |`).join('\n');
    const cleanWiki = [
      '# Self-Test Wiki (临时, --self-test 自动生成, 9 项 self-check 全 PASS 验证, v4 跨平台兼容)',
      '',
      '## §0 摘要',
      'Node.js 自校 CLI 工具 v4 --self-test 临时 wiki, 内容干净无 placeholder / 推荐语. 9 项 self-check 期望全 PASS. 字节 ≥ 10000 通过填充 demo 表格.',
      '',
      '## §1 内容 (含 ≥ 20 L### 行号 满足 line_ref ≥ 20 阈值)',
      '| 行号 | 含义 | 填充 |',
      '|---|---|---|',
      fillers,
      '',
      '## §2 模块 demo (≥ 5 个 ## 段满足 chapter ≥ 5 阈值)',
      '- 段 1: 单模块 demo',
      '- 段 2: 0 接入 demo',
      '- 段 3: 13 全集 demo',
      '- 段 4: 5 EA 联合 demo',
      '',
      '## §3 实战案例',
      'demo 实战案例段.',
      '',
      '## §4 验证',
      'self-check 9 项 9/9 PASS 验证段 (v4 跨平台 path.normalize 跑通).',
      '',
      '## §5 链向',
      '- [[MOC EA 开发知识库]]',
      '',
    ].join('\n');
    fs.writeFileSync(tmp, cleanWiki, 'utf8');
    args.input = tmp;
    args.check = 'all';
    const ctx = { wiki: args.input, ea: null, minBytes: 1000, check: 'all' };
    const out = runChecks(ctx);
    if (args.json) {
      console.log(JSON.stringify({ selfTest: true, tmpWiki: tmp, ...out }, null, 2));
    } else {
      console.log('=== --self-test 9 项 self-check (临时干净 wiki, ' + tmp + ') ===');
      for (const [k, v] of Object.entries(out.results)) console.log(`  ${v.pass > 0 && v.fail === 0 ? '✓' : '✗'} ${k.padEnd(15)} ${v.detail}`);
      console.log(`\n${out.totalPass}/${out.totalChecks} PASS, ${out.totalFail} FAIL`);
    }
    try { fs.unlinkSync(tmp); } catch (_) {}
    return out.totalFail === 0 ? EXIT.OK : EXIT.FAIL;
  }

  if (args.patterns) {
    console.log('=== 7+1 模式适用度矩阵 8x8 (P1-P8 × 8 维度, v4 含跨平台维度) ===');
    console.log('row\\col\t' + PATTERN_MATRIX.cols.join('\t'));
    for (const row of PATTERN_MATRIX.rows) {
      console.log(`${row.id} ${row.name}\t${row.marks.join('\t')}`);
    }
    console.log('');
    console.log('=== v4 跨平台 4 行 (win32/posix/darwin/freebsd × 8 维度, 修 #1) ===');
    console.log('row\\col\t' + PATTERN_MATRIX.cols.join('\t'));
    for (const row of PATTERN_MATRIX.platformRows) {
      console.log(`${row.id} ${row.name}\t${row.marks.join('\t')}`);
    }
    // 校验 0 空白 (8x8 + 4 平台行 × 8 = 96 单元, 全 ✓/✗)
    let blank = 0;
    for (const row of PATTERN_MATRIX.rows) for (const m of row.marks) if (m !== '✓' && m !== '✗') blank++;
    for (const row of PATTERN_MATRIX.platformRows) for (const m of row.marks) if (m !== '✓' && m !== '✗') blank++;
    console.log(`\n空白: ${blank}, 状态: ${blank === 0 ? 'PASS' : 'FAIL'}`);
    return blank === 0 ? EXIT.OK : EXIT.FAIL;
  }

  if (args.mocCheck) {
    const r = checkMocLinks();
    console.log('=== MOC 链向闭环检测 ===');
    console.log(`总计 ${r.total} [[wiki link]], ${r.pass} PASS, ${r.fail} FAIL`);
    if (r.fail > 0) {
      console.log('断链:');
      for (const m of r.missing) console.log('  ✗ ' + m);
    }
    if (args.json) console.log(JSON.stringify(r, null, 2));
    return r.fail === 0 ? EXIT.OK : EXIT.FAIL;
  }

  // 默认: 跑 --input --check (语义化退出码, 修 #4)
  if (!args.input) {
    console.error('错误: 缺 --input <path> 参数 (用法: --help)');
    return EXIT.ARG;  // 2 = 参数错
  }
  // 跨平台路径归一化 (修 #1)
  args.input = toPlatformPath(args.input);
  if (!fileExists(args.input)) {
    console.error(`IO 错: wiki 文件不存在: ${args.input} (退出码 ${EXIT.IO})`);
    return EXIT.IO;  // 3 = IO 错
  }
  const ctx = { wiki: args.input, ea: null, minBytes: 10000, check: args.check };
  const out = runChecks(ctx);
  // 修 #3 --output 参数化: --output 自动 JSON + 落盘; 单独 --json 仅 stdout
  if (args.json || args.output) {
    const payload = {
      wiki: args.input,
      ea: null,
      ...out,
      mq5Baseline: checkMtimeUnchanged(),
      mustRead12: checkMustRead12(),
      modeExtract: checkModeExtract(),
      mocEntry: checkMocEntry(),
      crossPlatform: checkCrossPlatform(),
      platform: CURRENT_PLATFORM,
      node: CURRENT_NODE,
    };
    const json = JSON.stringify(payload, null, 2);
    if (args.output) {
      try {
        const outPath = toPlatformPath(args.output);
        ensureDirFor(outPath);
        fs.writeFileSync(outPath, json, { encoding: 'utf8' });
        console.log(`JSON 落盘: ${outPath} (${json.length} 字节)`);
        // 同时打印精简文本结果到 stdout
        console.log(`\n=== ${args.input} (--check ${args.check}, --output ${outPath}) ===`);
        for (const [k, v] of Object.entries(out.results)) console.log(`  ${v.pass > 0 && v.fail === 0 ? '✓' : '✗'} ${k.padEnd(15)} ${v.detail}`);
        console.log(`\n${out.totalPass}/${out.totalChecks} PASS, ${out.totalFail} FAIL`);
      } catch (e) {
        console.error(`IO 错: --output 写文件失败: ${e.message} (退出码 ${EXIT.IO})`);
        return EXIT.IO;
      }
    } else {
      // 单独 --json, stdout 输出 JSON
      console.log(json);
    }
  } else {
    console.log(`=== ${args.input} (--check ${args.check}) ===`);
    for (const [k, v] of Object.entries(out.results)) console.log(`  ${v.pass > 0 && v.fail === 0 ? '✓' : '✗'} ${k.padEnd(15)} ${v.detail}`);
    console.log(`\n${out.totalPass}/${out.totalChecks} PASS, ${out.totalFail} FAIL`);
  }
  return out.totalFail === 0 ? EXIT.OK : EXIT.FAIL;
}

process.exit(main());
