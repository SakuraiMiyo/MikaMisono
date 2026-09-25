#!/usr/bin/env node
// auto.mjs — 一键自动化：为未处理日记生成记忆卡 + 增量重建向量索引 + 汇报状态
// 用法：
//   node tools/auto.mjs            全流程（digest → index）
//   node tools/auto.mjs --no-digest  只重建索引（不动 API）
//   node tools/auto.mjs --status    只汇报状态，不执行
import { readFile, readdir, stat } from 'node:fs/promises';
import { join, dirname, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const config = JSON.parse(await readFile(join(root, 'config.json'), 'utf8'));
const tool = (name) => join(root, 'tools', name);
const args = process.argv.slice(2);

const diaryDir = join(root, config.sources.diary);
const cardsDir = join(root, config.sources.cards);

async function pendingCount() {
  const entries = await readdir(diaryDir, { withFileTypes: true }).catch(() => []);
  const cards = new Set((await readdir(cardsDir).catch(() => [])).map((n) => basename(n, extname(n))));
  return entries.filter((e) => e.isFile() && e.name.endsWith('.md') && !cards.has(basename(e.name, '.md'))).length;
}

async function indexStats() {
  try {
    const m = JSON.parse(await readFile(join(root, config.index.root, 'manifest.json'), 'utf8'));
    return { docs: Object.keys(m.docs).length, engine: m.engine, updatedAt: m.updatedAt };
  } catch {
    return null;
  }
}

const pending = await pendingCount();
const stats = await indexStats();

if (args.includes('--status')) {
  console.log(`待生成记忆卡: ${pending}`);
  console.log(`索引: ${stats ? `${stats.docs} 个文档 · ${stats.engine} · ${stats.updatedAt}` : '尚未构建'}`);
  process.exit(0);
}

if (pending > 0 && !args.includes('--no-digest')) {
  console.log(`[auto] 生成 ${pending} 张记忆卡…`);
  const r = spawnSync(process.execPath, [tool('digest.mjs')], { stdio: 'inherit', cwd: root });
  if (r.status !== 0) console.warn('[auto] digest 部分失败，继续索引');
} else if (pending === 0) {
  console.log('[auto] 无待处理日记');
}

console.log('[auto] 重建索引…');
const r2 = spawnSync(process.execPath, [tool('index.mjs')], { stdio: 'inherit', cwd: root });
process.exit(r2.status ?? 1);
