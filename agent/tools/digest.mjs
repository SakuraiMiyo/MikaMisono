#!/usr/bin/env node
// digest.mjs — 长期记忆摘要：把日记逐篇提炼成结构化「记忆卡」（调用 DeepSeek API）
// 用法：
//   node tools/digest.mjs              为所有还没有记忆卡的日记生成卡片
//   node tools/digest.mjs --date 2026-08-24  只为指定日期生成
//   node tools/digest.mjs --list       列出缺卡片的日记
import { readFile, writeFile, readdir, mkdir } from 'node:fs/promises';
import { join, dirname, basename, extname } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const config = JSON.parse(await readFile(join(root, 'config.json'), 'utf8'));
const diaryDir = join(root, config.sources.diary);
const cardsDir = join(root, config.sources.cards);
const summariesDir = join(root, config.sources.summaries);

const DATE_RE = /^(\d{4}-\d{2}-\d{2})$/;

async function readApiKey() {
  // 凭据路径：config.digest.credentialsFile 或 $DSH_HOME/.credentials.yaml（跨设备可移植）
  const { homedir } = await import('node:os');
  const credFile = config.digest.credentialsFile
    || join(process.env.DSH_HOME || join(homedir(), '.dsh'), '.credentials.yaml');
  const text = await readFile(credFile, 'utf8');
  // 支持两种形态：
  //   DEEPSEEK_API_KEY: sk-xxx          （同行）
  //   DEEPSEEK_API_KEY:                  （下一行）secret: sk-xxx
  const lines = text.split(/\r?\n/);
  for (let i = 0; i < lines.length; i++) {
    const m = /^\s*DEEPSEEK_API_KEY\s*:\s*(\S+)\s*$/.exec(lines[i]);
    if (m) return m[1];
    if (/^\s*DEEPSEEK_API_KEY\s*:\s*$/.test(lines[i])) {
      for (let j = i + 1; j < Math.min(i + 4, lines.length); j++) {
        const s = /^\s*secret\s*:\s*(\S+)\s*$/.exec(lines[j]);
        if (s) return s[1];
      }
    }
  }
  return null;
}

async function callDeepSeek(apiKey, diaryText, date) {
  const prompt = `你是未花记忆管家。请把下面这则《圣园未花日记》提炼成一张结构化记忆卡（JSON 对象，不要输出其他内容）：
{
  "date": "${date}",
  "title": "一句话标题",
  "summary": "80字以内的核心经过",
  "people": ["出现的人物"],
  "places": ["地点"],
  "events": ["关键事件，每件一句话"],
  "feelings": ["主要情绪"],
  "decisions": ["做出的决定/承诺"],
  "quotes": ["值得记住的原话，没有则空数组"],
  "followUps": ["待办/下次要做的事，没有则空数组"]
}
日记内容：
"""
${diaryText}
"""`;
  const body = {
    model: config.digest.model,
    messages: [
      { role: 'system', content: '你只输出合法的 JSON 对象。' },
      { role: 'user', content: prompt },
    ],
    temperature: 0.4,
    max_tokens: 900,
  };
  const res = await fetch(config.digest.apiBase, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${apiKey}` },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`DeepSeek API ${res.status}: ${(await res.text()).slice(0, 300)}`);
  const data = await res.json();
  const content = data.choices?.[0]?.message?.content ?? '';
  const m = content.match(/\{[\s\S]*\}/);
  if (!m) throw new Error('API 未返回 JSON');
  return JSON.parse(m[0]);
}

async function main() {
  const entries = (await readdir(diaryDir, { withFileTypes: true })).filter((e) => e.isFile() && e.name.endsWith('.md'));
  const cards = new Set((await readdir(cardsDir).catch(() => [])).map((n) => basename(n, extname(n))));

  const dateArg = process.argv.indexOf('--date');
  const onlyDate = dateArg >= 0 ? process.argv[dateArg + 1] : null;
  if (process.argv.includes('--list')) {
    console.log('缺记忆卡的日记：');
    for (const e of entries) {
      const date = basename(e.name, '.md');
      if (!cards.has(date)) console.log(`  ${date}`);
    }
    process.exit(0);
  }

  const todo = entries.filter((e) => {
    const date = basename(e.name, '.md');
    if (!DATE_RE.test(date)) return false;
    if (onlyDate && date !== onlyDate) return false;
    return !cards.has(date);
  });

  if (todo.length === 0) {
    console.log('所有日记都已有记忆卡 ✓');
    process.exit(0);
  }
  console.log(`待生成记忆卡: ${todo.length} 篇`);

  const apiKey = await readApiKey();
  if (!apiKey) {
    console.error('未找到 DEEPSEEK_API_KEY（.credentials.yaml）');
    process.exit(1);
  }

  await mkdir(cardsDir, { recursive: true });
  await mkdir(summariesDir, { recursive: true });
  const summaryLines = [];
  let ok = 0;
  for (const e of todo) {
    const date = basename(e.name, '.md');
    const diaryText = await readFile(join(diaryDir, e.name), 'utf8');
    try {
      const card = await callDeepSeek(apiKey, diaryText, date);
      await writeFile(join(cardsDir, `${date}.json`), JSON.stringify(card, null, 2), 'utf8');
      summaryLines.push(`- ${date} ${card.title}｜${card.summary}`);
      console.log(`  ✓ ${date} → ${card.title}`);
      ok++;
    } catch (err) {
      console.error(`  ✗ ${date}: ${err.message}`);
    }
  }

  if (summaryLines.length > 0) {
    const memFile = join(summariesDir, 'memory.md');
    const prev = await readFile(memFile, 'utf8').catch(() => '');
    const head = prev ? `${prev.replace(/\s+$/, '')}\n` : '# 未花长期记忆（滚动摘要）\n\n';
    await writeFile(memFile, head + summaryLines.join('\n') + '\n', 'utf8');
  }
  console.log(`\n完成 ${ok}/${todo.length} 篇。\n下一步：运行 node tools/index.mjs 把新记忆卡纳入向量库。`);
}

main().catch((e) => {
  console.error(e);
  process.exit(1);
});
