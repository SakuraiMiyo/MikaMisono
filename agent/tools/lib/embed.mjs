// embed.mjs — 嵌入引擎：本地 ONNX 语义嵌入（transformers.js）为主，
// 纯 JS 哈希 n-gram 嵌入为离线降级。两者都产出 L2 归一化向量。
import { pipeline, env } from '@huggingface/transformers';
import { join } from 'node:path';

/**
 * 创建嵌入器。
 * @param {object} config - config.json 的 embedding 段
 * @param {string} projectRoot - 项目根目录（agent\，模型缓存在此目录的 .cache）
 */
export async function createEmbedder(config, projectRoot) {
  try {
    env.cacheDir = join(projectRoot, '.cache');
    env.allowLocalModels = false;
    if (config.embedding.remoteHost) env.remoteHost = config.embedding.remoteHost;
    const extractor = await pipeline('feature-extraction', config.embedding.model, { dtype: 'q8' });
    const embed = async (texts) => {
      const out = await extractor(texts, { pooling: 'mean', normalize: true });
      return out.tolist(); // number[][]
    };
    return {
      engine: 'transformers',
      model: config.embedding.model,
      dims: config.embedding.dims,
      embed,
    };
  } catch (err) {
    console.warn(`[embed] transformers.js 不可用（${err?.message ?? err}），降级为哈希 n-gram 嵌入`);
    if (process.env.DEBUG_EMBED === '1') console.warn(err?.stack);
    return createHashEmbedder();
  }
}

/** 零依赖降级：字符 1-3 gram 哈希 → 512 维稀疏向量（L2 归一化）。中文场景够用。 */
function createHashEmbedder() {
  const dims = 512;
  const hash = (str, seed) => {
    let h = (2166136261 ^ seed) >>> 0;
    for (let i = 0; i < str.length; i++) {
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }
    return (h >>> 0) % dims;
  };
  const vec = (text) => {
    const v = new Float32Array(dims);
    const t = String(text).replace(/\s+/g, '');
    for (let n = 1; n <= 3; n++) {
      for (let i = 0; i + n <= t.length; i++) {
        v[hash(t.slice(i, i + n), n * 31)] += 1;
      }
    }
    let s = 0;
    for (const x of v) s += x * x;
    s = Math.sqrt(s) || 1;
    for (let i = 0; i < dims; i++) v[i] /= s;
    return Array.from(v);
  };
  return {
    engine: 'hashing-ngram',
    model: 'none',
    dims,
    embed: async (texts) => texts.map(vec),
  };
}
