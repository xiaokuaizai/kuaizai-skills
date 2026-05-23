// 从 Markdown 提示词文件中提取 Labels，生成纯标签网格 HTML
// 用法: node generate-labels-only.js

const fs = require('fs');
const path = require('path');

// ==================== 配置区域 ====================
// 修改以下路径为你的实际目录
const SOURCE_DIRS = [
  path.resolve("G:\\draw_long\\GPT-image-2.0\\prompt\\提示词2.0\\infographic"),
  path.resolve("G:\\draw_long\\GPT-image-2.0\\prompt\\提示词2.0\\photo"),
];
const OUTPUT_DIR = path.resolve("G:\\draw_long\\GPT-image-2.0\\batches\\参考\\label_only_html");
// =================================================

const COLORS = [
  "#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
  "#1ABC9C", "#E67E22", "#34495E", "#D35400", "#27AE60",
  "#2980B9", "#8E44AD", "#C0392B", "#16A085", "#F1C40F",
];

function parseMdFile(filepath) {
  const text = fs.readFileSync(filepath, 'utf-8');
  const prompts = [];
  // 坑点：不要用 split 按分隔符切，会切散内容。用正则匹配完整 PROMPT 块
  const promptRegex = /\[PROMPT\s*\d+\][\s\S]*?(?=\n\[PROMPT\s*\d+\]|$)/g;
  let m;
  while ((m = promptRegex.exec(text)) !== null) {
    const trimmed = m[0].trim();
    if (!trimmed) continue;

    const titleMatch = trimmed.match(/\[PROMPT\s*\d+\]\s*(.+)/);
    const title = titleMatch ? titleMatch[1].trim() : 'Untitled';

    const wordsMatch = trimmed.match(/Words:\s*(.+)/);
    const words = wordsMatch ? wordsMatch[1].trim() : '';

    const labels = [];
    const labelSectionMatch = trimmed.match(
      /\[Labels\][\s\S]*?Complete label list:([\s\S]*?)(?=CRITICAL TEXT RENDERING|={20,}|$)/
    );
    if (labelSectionMatch) {
      const labelText = labelSectionMatch[1];
      const lines = labelText.split('\n');
      for (const line of lines) {
        const l = line.trim();
        if (l.startsWith('-')) {
          const label = l.slice(1).trim().replace(/^"|"$/g, '');
          if (label) labels.push(label);
        }
      }
    }

    if (labels.length > 0) {
      prompts.push({ title, words, labels });
    }
  }
  return prompts;
}

function generateLabelsOnlyHtml(categoryName, prompt, promptIndex) {
  let labelsHtml = '';
  for (let li = 0; li < prompt.labels.length; li++) {
    const color = COLORS[li % COLORS.length];
    const label = escapeHtml(prompt.labels[li]);
    labelsHtml += `
        <div class="label-box" style="border-color: ${color};">
          <div class="badge" style="background: ${color};">${li + 1}</div>
          <div class="label-text">${label}</div>
        </div>`;
  }

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<style>
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", "Noto Sans SC", sans-serif;
  background: #ffffff;
  padding: 16px;
  min-width: 1400px;
}
.labels-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
.label-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: #fff;
  border: 2px solid;
  border-radius: 10px;
  padding: 8px 12px;
  font-size: 14px;
  line-height: 1.3;
}
.badge {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  font-weight: 700;
  font-size: 11px;
  flex-shrink: 0;
}
.label-text {
  font-weight: 600;
  letter-spacing: 0.02em;
  color: #222;
}
</style>
</head>
<body>
<div class="labels-grid">
${labelsHtml}
</div>
</body>
</html>`;
}

function escapeHtml(text) {
  if (!text) return '';
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function sanitizeFilename(name) {
  return name.replace(/[\\/:*?"<>|]/g, '_').replace(/\s+/g, '_');
}

function main() {
  if (!fs.existsSync(OUTPUT_DIR)) {
    fs.mkdirSync(OUTPUT_DIR, { recursive: true });
  }

  let total = 0;

  for (const dir of SOURCE_DIRS) {
    if (!fs.existsSync(dir)) continue;

    const files = fs.readdirSync(dir).filter(f => f.endsWith('.md')).sort();
    for (const file of files) {
      const filepath = path.join(dir, file);
      const categoryName = path.basename(file, '.md');
      const prompts = parseMdFile(filepath);

      for (let i = 0; i < prompts.length; i++) {
        const prompt = prompts[i];
        const htmlContent = generateLabelsOnlyHtml(categoryName, prompt, i);
        const idx = String(i + 1).padStart(2, '0');
        const safeTitle = sanitizeFilename(prompt.title).slice(0, 30);
        const outName = `${sanitizeFilename(categoryName)}_${idx}_${safeTitle}.html`;
        const outPath = path.join(OUTPUT_DIR, outName);
        fs.writeFileSync(outPath, htmlContent, 'utf-8');
        total++;
      }
      console.log(`✅ ${categoryName}: ${prompts.length} 个 prompts`);
    }
  }

  console.log(`\n🎉 共生成 ${total} 个纯标签 HTML，保存在:\n   ${OUTPUT_DIR}`);
}

main();
