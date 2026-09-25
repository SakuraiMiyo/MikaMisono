// store.mjs — 向量库读写：manifest.json（文档元数据）+ chunks.json（文本）+ vectors.bin（float32 矩阵）。
import { readFile, writeFile, mkdir, readdir, stat } from 'node:fs/promises';
import { join } from 'node:path';

export async function loadIndex(dir) {
  try {
    const [manifest, chunks] = await Promise.all([
      readFile(join(dir, 'manifest.json'), 'utf8'),
      readFile(join(dir, 'chunks.json'), 'utf8'),
    ]);
    let vectors = null;
    try {
      const buf = await readFile(join(dir, 'vectors.bin'));
      vectors = new Float32Array(buf.buffer, buf.byteOffset, buf.byteLength / 4);
    } catch {
      vectors = null;
    }
    return { manifest: JSON.parse(manifest), chunks: JSON.parse(chunks), vectors };
  } catch {
    return null;
  }
}

export async function saveIndex(dir, { manifest, chunks, vectors }) {
  await mkdir(dir, { recursive: true });
  await writeFile(join(dir, 'manifest.json'), JSON.stringify(manifest, null, 2), 'utf8');
  await writeFile(join(dir, 'chunks.json'), JSON.stringify(chunks, null, 1), 'utf8');
  await writeFile(join(dir, 'vectors.bin'), Buffer.from(vectors.buffer, vectors.byteOffset, vectors.byteLength));
}

/** 归一化点积 = 余弦相似度（所有向量均已 L2 归一化）。返回 top-k 下标。 */
export function topK(queryVec, matrix, dims, k) {
  const n = matrix.length / dims;
  const scores = new Array(n);
  for (let i = 0; i < n; i++) {
    let s = 0;
    const off = i * dims;
    for (let d = 0; d < dims; d++) s += queryVec[d] * matrix[off + d];
    scores[i] = s;
  }
  const idx = scores.map((s, i) => [s, i]).sort((a, b) => b[0] - a[0]).slice(0, k);
  return idx;
}

/** 文档列表 → 分块（卡片 JSON 序列化后参与嵌入）。 */
export async function buildChunks(docs, chunkMarkdownFn) {
  const { readFile } = await import('node:fs/promises');
  const chunks = [];
  for (const doc of docs) {
    const raw = await readFile(doc.file, 'utf8');
    let text = raw;
    let title = doc.title;
    if (doc.source === 'card') {
      try {
        const card = JSON.parse(raw);
        title = card.title || doc.title;
        text = `记忆卡 ${card.date ?? ''}\n${card.summary ?? ''}\n人物：${(card.people ?? []).join('、')}\n地点：${(card.places ?? []).join('、')}\n事件：${(card.events ?? []).join('\n')}\n情绪：${(card.feelings ?? []).join('、')}\n决定：${(card.decisions ?? []).join('\n')}\n后续：${(card.followUps ?? []).join('\n')}`;
      } catch {
        text = raw;
      }
    }
    const parts = chunkMarkdownFn(text);
    parts.forEach((p, i) => {
      chunks.push({
        id: `${doc.docId}#${i}`,
        docId: doc.docId,
        text: p.text,
        meta: { source: doc.source, file: doc.file, title, heading: p.heading },
      });
    });
  }
  return chunks;
}
