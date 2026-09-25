#!/usr/bin/env node
// search.mjs — 语义检索记忆库与知识库
// 用法：
//   node tools/search.mjs "问题" [--k 5] [--scope knowledge|diary|card|summary|all] [--full]
import { readFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createEmbedder } from './lib/embed.mjs';
import { loadIndex, topK } from './lib/store.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const config = JSON.parse(await readFile(join(root, 'config.json'), 'utf8'));
const indexDir = join(root, config.index.root);

const args = process.argv.slice(2);
const query = args.find((a) => !a.startsWith('-')) ?? '';
const kArg = args.indexOf('--k');
const k = kArg >= 0 ? Number(args[kArg + 1]) || 5 : 5;
const scopeArg = args.indexOf('--scope');
const scope = scopeArg >= 0 ? args[scopeArg + 1] ?? 'all' : 'all';
const full = args.includes('--full');

if (!query) {
  console.error('用法: node tools/search.mjs "问题" [--k 5] [--scope knowledge|diary|card|summary|all]');
  process.exit(1);
}

const idx = await loadIndex(indexDir);
if (!idx) {
  console.error('索引不存在，先运行: node tools/index.mjs');
  process.exit(1);
}

const embedder = await createEmbedder(config, root);
const [qvec] = await embedder.embed([`${config.embedding.queryPrefix ?? ''}${query}`]);
const dims = idx.manifest.dims;
const hits = topK(qvec, idx.vectors, dims, Math.max(k * 3, 20));

const allowed = scope === 'all' ? null : new Set(scope.split(','));
let shown = 0;
console.log(`\n🔍 「${query}」 top-${k}（引擎 ${idx.manifest.engine}，共 ${idx.chunks.length} 块）\n`);
for (const [score, i] of hits) {
  const chunk = idx.chunks[i];
  if (!chunk) continue;
  if (allowed && !allowed.has(chunk.meta.source)) continue;
  if (shown >= k) break;
  shown++;
  const text = full ? chunk.text : chunk.text.slice(0, 160);
  console.log(
    `[${String(score).slice(0, 6)}] ${chunk.meta.source}/${chunk.meta.title}${chunk.meta.heading ? ' · ' + chunk.meta.heading : ''}\n    ${text.replace(/\n/g, ' ')}\n`,
  );
}
if (shown === 0) console.log('（该 scope 下无结果）');
