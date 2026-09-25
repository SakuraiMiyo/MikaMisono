// chunk.mjs — Markdown 分块：按标题分层 + 段落长度上限 + 重叠。
import { readFile, readdir, stat } from 'node:fs/promises';
import { join, basename, extname } from 'node:path';
import { createHash } from 'node:crypto';

export function chunkMarkdown(text, { maxChars = 600, overlapChars = 80 } = {}) {
  const lines = String(text).split(/\r?\n/);
  const chunks = [];
  let current = '';
  let heading = '';

  const flush = () => {
    const t = current.trim();
    if (t) chunks.push({ text: t, heading: heading || '' });
    current = '';
  };

  for (const line of lines) {
    const h = /^(#{1,4})\s+(.*)$/.exec(line);
    if (h) {
      flush();
      heading = line.trim();
      current = `${line}\n`;
      continue;
    }
    if (current.trim() && current.length + line.length + 1 > maxChars) flush();
    current += `${line}\n`;
  }
  flush();
  return chunks;
}

export function sha1(text) {
  return createHash('sha1').update(String(text)).digest('hex');
}

/**
 * 扫描一个来源目录下的文档。
 * @returns {Promise<Array<{docId, file, source, title, mtime, hash}>>}
 */
export async function scanDir(root, source) {
  const out = [];
  let entries = [];
  try {
    entries = await readdir(root, { withFileTypes: true });
  } catch {
    return out;
  }
  for (const entry of entries) {
    if (!entry.isFile()) continue;
    const ext = extname(entry.name);
    if (ext !== '.md' && ext !== '.json') continue;
    const file = join(root, entry.name);
    const content = await readFile(file, 'utf8');
    out.push({
      docId: `${source}|${entry.name}`,
      file,
      source,
      title: basename(entry.name, ext),
      mtime: (await stat(file)).mtimeMs,
      hash: sha1(content),
    });
  }
  return out;
}
