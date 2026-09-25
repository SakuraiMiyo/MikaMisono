#!/usr/bin/env node
// index.mjs — 构建/增量更新向量库
// 用法：
//   node tools/index.mjs            增量（只重嵌入变更的文档）
//   node tools/index.mjs --rebuild  全量重建
import { readFile } from 'node:fs/promises';
import { join, dirname, basename } from 'node:path';
import { fileURLToPath } from 'node:url';
import { createEmbedder } from './lib/embed.mjs';
import { chunkMarkdown, scanDir, sha1 } from './lib/chunk.mjs';
import { loadIndex, saveIndex, buildChunks } from './lib/store.mjs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const config = JSON.parse(await readFile(join(root, 'config.json'), 'utf8'));
const indexDir = join(root, config.index.root);
const sources = config.sources;

// 1) 收集全部文档
// sources.exclude 里的文件名不进索引——用于排除「存疑/待核」这类
// 明确标注了「不要当设定用」的文件，避免它们被检索回来当事实用。
const exclude = new Set((sources.exclude ?? []).map((s) => String(s).toLowerCase()));
const docs = [
  ...(await scanDir(join(root, sources.knowledge), 'knowledge')),
  ...(await scanDir(join(root, sources.diary), 'diary')),
  ...(await scanDir(join(root, sources.cards), 'card')),
  ...(await scanDir(join(root, sources.summaries), 'summary')),
].filter((d) => !exclude.has(basename(d.file).toLowerCase()));
console.log(`[index] 扫描到 ${docs.length} 个文档（排除规则 ${exclude.size} 条）`);

// 2) 增量判定
const force = process.argv.includes('--rebuild');
const prev = force ? null : await loadIndex(indexDir);
const prevManifest = prev?.manifest ?? { docs: {} };
const changed = docs.filter((d) => {
  const old = prevManifest.docs[d.docId];
  return !old || old.hash !== d.hash;
});
const removed = new Set(
  Object.keys(prevManifest.docs).filter((id) => !docs.some((d) => d.docId === id)),
);
console.log(`[index] 变更 ${changed.length}，删除 ${removed.size}，未变 ${docs.length - changed.length}`);

if (changed.length === 0 && removed.size === 0) {
  console.log('[index] 无需更新');
  process.exit(0);
}

// 3) 嵌入引擎
const embedder = await createEmbedder(config, root);
console.log(`[index] 嵌入引擎: ${embedder.engine} (${embedder.model}, ${embedder.dims} 维)`);

// 4) 全量分块 + 嵌入（个人规模小，直接全量重算最稳妥）
const chunks = await buildChunks(docs, (t) => chunkMarkdown(t, config.index));
const passagePrefix = config.embedding.passagePrefix ?? '';
const texts = chunks.map((c) => `${passagePrefix}${c.text}`);
const vectors = await embedder.embed(texts);
console.log(`[index] 分块 ${chunks.length} 条，向量 ${vectors.length} 条`);

// 5) 落盘
const dims = embedder.dims;
const flat = new Float32Array(chunks.length * dims);
vectors.forEach((v, i) => {
  for (let d = 0; d < dims; d++) flat[i * dims + d] = v[d];
});
const manifest = {
  version: 1,
  engine: embedder.engine,
  model: embedder.model,
  dims,
  updatedAt: new Date().toISOString(),
  docs: Object.fromEntries(docs.map((d) => [d.docId, { file: d.file, source: d.source, title: d.title, mtime: d.mtime, hash: d.hash }])),
};
await saveIndex(indexDir, { manifest, chunks, vectors: flat });
console.log(`[index] 完成 → ${indexDir}`);
