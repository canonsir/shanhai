#!/usr/bin/env node
/*
 * ShanHai Design Guard
 * ---------------------
 * 机械化执行「前端必须走 Design System token，不得 AI coding 自己发挥」铁律。
 * 文档约束不够 —— 本脚本扫描所有前端源码，命中即非零退出（可接 CI / pre-commit）。
 *
 * 拦截：
 *   1. 业务代码里写死的十六进制色值（#fff / #0065fd ...）
 *   2. Tailwind 调色板魔法类（text-red-600 / bg-blue-50 / border-gray-200 ...）
 *      —— 这些绕过了语义 token，是「自己发挥」的典型形态。
 *
 * 允许（事实来源 / 设计系统自身）：
 *   - design-system/**            （token 与 preview 本身就是定义色值的地方）
 *   - apps/<app>/src/app/globals.css 的 :root / @theme 区块（token 定义入口）
 *
 * 用法：
 *   node tools/design-guard/check.mjs            # 扫描默认前端目录
 *   node tools/design-guard/check.mjs apps/console
 */

import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, relative, extname } from "node:path";
import { fileURLToPath } from "node:url";

const REPO_ROOT = join(fileURLToPath(new URL(".", import.meta.url)), "..", "..");
const DEFAULT_TARGETS = ["apps"];
const SCAN_EXT = new Set([".ts", ".tsx", ".jsx", ".js", ".css"]);

// 调色板名单：Tailwind 默认色板，出现 `<util>-<palette>-<step>` 即违规。
const PALETTE =
  "red|orange|amber|yellow|lime|green|emerald|teal|cyan|sky|blue|indigo|violet|purple|fuchsia|pink|rose|slate|gray|grey|zinc|neutral|stone";
const PALETTE_CLASS = new RegExp(
  `\\b(?:text|bg|border|ring|fill|stroke|from|via|to|decoration|outline|divide|placeholder|caret|accent|shadow)-(?:${PALETTE})-\\d{2,3}\\b`,
  "g",
);
const HEX_COLOR = /#[0-9a-fA-F]{3,8}\b/g;

// token 定义入口：globals.css 里 :root{} 与 @theme{} 内的色值是合法来源。
function isTokenDefinitionFile(relPath) {
  return /(^|\/)globals\.css$/.test(relPath);
}
function isDesignSystemFile(relPath) {
  return relPath.startsWith("design-system/");
}

function walk(dir, out) {
  let entries;
  try {
    entries = readdirSync(dir);
  } catch {
    return out;
  }
  for (const name of entries) {
    if (name === "node_modules" || name === ".next" || name === "dist") continue;
    const full = join(dir, name);
    const st = statSync(full);
    if (st.isDirectory()) walk(full, out);
    else if (SCAN_EXT.has(extname(name))) out.push(full);
  }
  return out;
}

const targets = process.argv.slice(2).length
  ? process.argv.slice(2)
  : DEFAULT_TARGETS;

const files = [];
for (const t of targets) walk(join(REPO_ROOT, t), files);

const violations = [];
for (const file of files) {
  const relPath = relative(REPO_ROOT, file);
  if (isDesignSystemFile(relPath)) continue;
  const tokenFile = isTokenDefinitionFile(relPath);
  const lines = readFileSync(file, "utf8").split("\n");

  lines.forEach((line, i) => {
    for (const m of line.matchAll(PALETTE_CLASS)) {
      violations.push({ relPath, line: i + 1, kind: "palette-class", text: m[0] });
    }
    if (!tokenFile) {
      for (const m of line.matchAll(HEX_COLOR)) {
        violations.push({ relPath, line: i + 1, kind: "hardcoded-hex", text: m[0] });
      }
    }
  });
}

if (violations.length === 0) {
  console.log("design-guard: OK — 未发现硬编码色值或调色板魔法类。");
  process.exit(0);
}

console.error(`design-guard: 发现 ${violations.length} 处违规（必须走 Design System token）\n`);
for (const v of violations) {
  const hint =
    v.kind === "palette-class"
      ? "用语义类（text-foreground / bg-muted / text-destructive ...）替代"
      : "改用 var(--token) 或语义 Tailwind 类，色值只允许定义在 token 层";
  console.error(`  ${v.relPath}:${v.line}  [${v.kind}] ${v.text}  -> ${hint}`);
}
console.error(
  "\n参考：docs/frontend-guideline.md · design-system/tokens/。token 是唯一色源，AI/人都不得在业务代码自定义颜色。",
);
process.exit(1);
