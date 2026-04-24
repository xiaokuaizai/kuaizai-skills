---
name: md-mindmap-to-pdf
version: 1.0.0
description: |
  将 Markdown 词根/前缀学习页（或任何层级化 markdown 索引）转换为树状思维导图 PDF。
  解析分类、单词、音标、释义和词根拆分，生成带 SVG 连接线的可视化卡片图，
  最终通过 playwright-cli 输出为 PDF。
triggers:
  - md to mindmap pdf
  - markdown mindmap
  - 思维导图 pdf
  - 生成思维导图
  - md 转 pdf 思维导图
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Agent
---

# md-mindmap-to-pdf：Markdown 树状思维导图生成器

把层级化的 markdown 索引（如词根/前缀词汇页）转成带连接线的思维导图 PDF。
支持完整单词卡片（音标+释义）和词根拆分节点。

## 前置检查

```bash
# 1. 检测 playwright-cli
PWCLI=""
if command -v playwright-cli &>/dev/null; then
  PWCLI="playwright-cli"
elif [ -x "F:/nodejs_global/playwright-cli" ]; then
  PWCLI="F:/nodejs_global/playwright-cli"
elif [ -x "$HOME/.claude/skills/gstack/node_modules/.bin/playwright-cli" ]; then
  PWCLI="$HOME/.claude/skills/gstack/node_modules/.bin/playwright-cli"
fi

if [ -n "$PWCLI" ]; then
  echo "PLAYWRIGHT_CLI: $PWCLI"
else
  echo "ERROR: 找不到 playwright-cli。请先安装：npm install -g @anthropic-ai/playwright-cli"
  exit 1
fi

# 2. 检测 Python
if command -v python &>/dev/null || command -v python3 &>/dev/null; then
  echo "PYTHON: OK"
else
  echo "ERROR: 需要 Python 环境"
  exit 1
fi
```

## 工作流程

### 1. 读取并解析 Markdown

读取用户指定的 `.md` 文件。解析规则：
- `# ` 开头的是**根节点标题**（一级标题），标题下方连续的 `> ` 引用块（如核心意象、词源提示）会被提取并合并渲染到根节点内部
- `## ` 开头的是**分类节点**（二级标题）
- `- **单词** /音标/ 词性. 释义` 是**单词卡片**
- 缩进的 `  - → re(回)+turn(转)` 是**词根拆分节点**
- 过滤掉 `关联词网`、`相关页面`、`相关链接` 等非分类尾部区块

**必须保留的字段**：
- 根节点标题 + 核心意象/词源提示（`> ` 引用块）
- 分类标题
- 单词原文
- 音标（`/.../`）
- 词性 + 中文释义
- 词根拆分文本（如果有）

### 2. 生成思维导图 HTML

使用 skill 目录下的模板生成独立 HTML 文件：

```bash
# 复制模板到输出目录
cp ~/.claude/skills/md-mindmap-to-pdf/templates/generate_mindmap.py "$OUTPUT_DIR/"
cp ~/.claude/skills/md-mindmap-to-pdf/templates/export_pdf.js "$OUTPUT_DIR/"
```

然后修改 `generate_mindmap.py` 中的 `MD_PATH` 和 `HTML_PATH`，运行：

```bash
cd "$OUTPUT_DIR" && python generate_mindmap.py
```

### 3. 导出 PDF

**不要**用 `playwright-cli open file://...`（会被拦截）。
**不要**依赖本地 HTTP 服务器（后台进程在本环境存活困难）。

正确做法：使用 `playwright-cli run-code --filename export_pdf.js`

```bash
"$PWCLI" run-code --filename "$OUTPUT_DIR/export_pdf.js"
```

## 核心坑点与解决方案（必读）

### 坑 1：playwright-cli 禁止 `file://` 协议（open 命令）

**现象**：
```
playwright-cli open "file:///G:/.../mindmap.html"
# Error: Access to "file:" protocol is blocked.
```

**解决**：不使用 `open`，改用 `run-code` + Playwright API：
```javascript
// export_pdf.js
async (page) => {
  await page.goto('file:///G:/.../mindmap.html');
  await page.waitForTimeout(1500);
  await page.pdf({ path: '...', printBackground: true });
}
```
`run-code` 中的 `page.goto('file://')` 不受此限制。

---

### 坑 2：本地 HTTP 服务器起不来

**现象**：`python -m http.server &` 后 curl 测试连接失败，后台进程被环境清理。

**解决**：完全放弃 HTTP 服务器方案，全部使用 `file://` + `run-code` 导出。

---

### 坑 3：Inline 代码的引号/转义地狱

**现象**：试图把 Python/JS 代码直接 inline 到 bash `-c "..."` 中，导致引号嵌套崩溃。

**解决**：**永远写独立文件**。先 `Write` 生成 `.py` 或 `.js` 文件，再执行：
```bash
python generate_mindmap.py
playwright-cli run-code --filename export_pdf.js
```

---

### 坑 4：PDF 固定尺寸导致内容裁切

**现象**：设置 `width: '1920px', height: '1080px'` 后，下方内容被截断。

**解决**：在 `run-code` 中动态测量页面尺寸：
```javascript
const dims = await page.evaluate(() => {
  const el = document.getElementById('page') || document.body;
  return {
    width: el.scrollWidth + 80,
    height: el.scrollHeight + 80
  };
});
await page.pdf({
  path: 'output.pdf',
  width: dims.width + 'px',
  height: dims.height + 'px',
  printBackground: true,
  margin: { top: '0', right: '0', bottom: '0', left: '0' }
});
```

---

### 坑 5：中文字体和渲染

**解决**：CSS 中始终指定中文字体栈：
```css
font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
```
`printBackground: true` 必须开启，否则背景色丢失。

---

### 坑 6：单词过多导致图纵向爆炸

**现象**：某分类下有 70+ 个单词，单列纵向排列后高度超过 4000px，PDF 变成长条。

**解决**：当分类下单词数超过阈值（如 15 个）时，单词区域使用 CSS Grid 多列布局：
```css
.word-groups.dense {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
}
```
同时该分类下的 `.word-group` 改为纵向排列（卡片在上，拆分在下）。

---

### 坑 7：MD 尾部非分类区块混进导图

**现象**：`## 关联词网`、`## 相关页面` 等尾部区块被误识别为分类，生成多余节点。

**解决**：解析时遇到这些标题关键字直接跳过，并清空当前分类上下文。

---

### 坑 8：playwright-cli 路径不统一

**现象**：用户本机的 playwright-cli 可能装在：
- `F:\nodejs_global\playwright-cli`（npm 全局自定义 prefix）
- `~/.claude/skills/gstack/node_modules/.bin/playwright-cli`（gstack 自带）
- 或其他 npm 全局路径

**解决**：skill 启动时按优先级探测多个常见路径，找到可用的即可。

---

### 坑 9：JS 画线时机

**现象**：SVG 连接线位置错乱或没画出来。

**解决**：
1. 所有连线代码放在 `window.onload` 中
2. `run-code` 导出前加 `await page.waitForTimeout(1500)` 确保 JS 执行完毕
3. SVG 尺寸在 onload 中根据 `page.scrollWidth / scrollHeight` 设置

---

### 坑 10：根节点遗漏核心意象/词源提示

**现象**：Markdown 中 `# ` 标题下方的 `> ` 引用块（核心意象、词源提示）没有被渲染到思维导图中，导致词根页缺少关键记忆线索。

**解决**：
1. 解析阶段：遇到 `# ` 标题后，继续读取后续连续的 `> ` 引用块，合并为 `info_text`
2. 渲染阶段：将 `info_text` 以 `.root-info` 子元素的形式嵌入 `.root` 灰色根节点内部，用半透明白线（`border-top: 1px solid rgba(255,255,255,0.3)`）与标题分隔
3. 样式保持根节点统一灰色背景，提示文字使用较小字号（`14px`）和左对齐，不另起独立卡片

---

## 节点配色规范（参考图风格）

| 节点类型 | 背景色 | 文字色 | 用途 |
|---------|--------|--------|------|
| 根节点 | `#9e9e9e` | `#fff` | 词根/前缀主题 |
| 分类节点 | `#ffc107` | `#333` | 语义分类（二级标题） |
| 单词卡片 | `#fff3cd` | `#333` | 单词+音标+释义 |
| 拆分卡片 | `#b3e5fc` | `#01579b` | 词根拆分说明 |
| 连接线（根→分类）| `#2196f3` | - | 粗线 3px |
| 连接线（分类→单词）| `#64b5f6` | - | 细线 2px |
| 连接线（单词→拆分）| `#4fc3f7` | - | 细线 2px |

## 调试指南

- **PDF 文字模糊**：检查 `printBackground: true` 是否开启；截图测试时用 `page.setViewportSize({width:1920, height:1080})`
- **内容被截断**：检查是否使用了动态尺寸（坑 4）
- **连线缺失**：检查 `window.onload` 是否触发；检查 SVG 容器尺寸
- **第五类单词太密**：调大 `grid-template-columns: repeat(4, 1fr)` 或减小 `.word-card` 的 `font-size`
- **中文字显示为方框**：添加 `"Microsoft YaHei"` 字体回退

## 输出约定

- HTML 临时文件：与输出 PDF 同目录，后缀 `.html`
- PDF 文件：按用户指定路径交付
- 截图预览（可选）：导出前用 `$PWCLI screenshot --filename preview.png` 预览效果
