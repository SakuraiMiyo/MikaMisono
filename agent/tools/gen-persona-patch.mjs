#!/usr/bin/env node
// gen-persona-patch.mjs — 从 SKILL.md 生成 DSH profile 的全局 persona patch（cordis.patch.yml）。
// 可移植：知识库路径自动取自本项目目录，DSH home / profile 可用参数指定。
// 用法：
//   node tools/gen-persona-patch.mjs                        # 写到 $DSH_HOME/profiles/desktop/cordis.patch.yml
//   node tools/gen-persona-patch.mjs --home "C:\Users\xxx\.dsh"   # 指定 DSH home
//   node tools/gen-persona-patch.mjs --profile web          # 指定 profile 名
//   node tools/gen-persona-patch.mjs --out "path\to\file"   # 指定输出文件
import { readFile, writeFile, copyFile } from 'node:fs/promises';
import { join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';
import { homedir } from 'node:os';
import { existsSync } from 'node:fs';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
const args = process.argv.slice(2);
const argVal = (flag) => {
  const i = args.indexOf(flag);
  return i >= 0 ? args[i + 1] : undefined;
};
const home = argVal('--home') || process.env.DSH_HOME || join(homedir(), '.dsh');
const profile = argVal('--profile') || 'desktop';
const out = argVal('--out') || join(home, 'profiles', profile, 'cordis.patch.yml');

const skillPath = join(root, 'SKILL.md');
const kbBase = join(root, 'knowledge');
const lines = (await readFile(skillPath, 'utf8')).split(/\r?\n/);

// 1) 剥离 YAML frontmatter
let first = -1;
let second = -1;
for (let i = 0; i < lines.length; i++) {
  if (lines[i].trim() === '---') {
    if (first < 0) first = i;
    else if (second < 0) { second = i; break; }
  }
}
if (second < 0) throw new Error('SKILL.md 的 frontmatter 未闭合（缺少第二个 ---）');
const body = lines.slice(second + 1);
while (body.length && body[0].trim() === '') body.shift();
if (body.length && body[0].startsWith('#')) body.shift();
while (body.length && body[0].trim() === '') body.shift();

// 2) 在介绍段末尾插入知识库绝对路径注记
const note = `> （知识库根目录：${kbBase}。下文所有 knowledge/xxx.md 引用均相对此目录，角色扮演细节不确定时优先查阅。）`;
const anchor = body.findIndex((l) => l.includes('请优先查阅对应知识库文件'));
if (anchor >= 0) {
  let end = anchor;
  while (end + 1 < body.length && body[end + 1].trimStart().startsWith('>')) end++;
  body.splice(end + 1, 0, note);
}

// 3) 组装 YAML（persona 块缩进 6 空格，块标量 | 保留换行）
const ind = '      ';
const outLines = [
  '# Global persona: 圣园未花 (Misono Mika) roleplay — generated from',
  `#   ${skillPath} (strip frontmatter).`,
  '# Applies to the whole deployment. Restart DSH Desktop to apply.',
  '- id: system-prompt',
  '  config:',
  '    persona: |',
  ...body.map((l) => ind + l),
  '    includeHarnessIdentity: false',
];
const content = outLines.join('\n') + '\n';

// 4) 备份原文件（仅当尚无备份时），再写入
if (existsSync(out) && !existsSync(`${out}.bak`)) {
  try {
    await copyFile(out, `${out}.bak`);
    console.log(`[gen] 已备份原配置 → ${out}.bak`);
  } catch (e) {
    console.warn(`[gen] 备份失败（继续写入）: ${e.message}`);
  }
}
await writeFile(out, content, 'utf8');
console.log(`[gen] 已生成 → ${out}`);
console.log(`[gen] persona ${body.length} 行 / ${content.length} 字符`);
console.log('[gen] 重启 DSH Desktop 后生效（persona 变更对新会话生效）');
