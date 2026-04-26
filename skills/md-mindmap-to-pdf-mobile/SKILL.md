---
name: md-mindmap-to-pdf-mobile
version: 1.0.0
description: |
  将 Markdown 词根/前缀学习页转换为移动端竖版思维导图 PDF。
  采用纵向堆叠布局、单列卡片、无 SVG 线条设计，拆分内容内嵌到单词卡片中，
  适合在手机屏幕上纵向滑动查看。
triggers:
  - mobile mindmap
  - 手机思维导图
  - 移动端思维导图
  - mobile pdf mindmap
  - md 转手机版思维导图
allowed-tools:
  - Bash
  - Read
  - Edit
  - Write
  - Agent
---

# md-mindmap-to-pdf-mobile：Markdown 移动端竖版思维导图生成器

把层级化的 markdown 索引转成**适合手机查看**的竖版思维导图 PDF。
去除了桌面版的复杂连线和横向展开，改用纵向堆叠、单列卡片、内嵌拆分的简洁设计。

## 与桌面版的核心区别

| 特性 | 桌面版 md-mindmap-to-pdf | 移动端 mobile 版 |
|------|------------------------|----------------|
| 布局方向 | 横向展开（根节点在左，分类向右展开） | 纵向堆叠（根节点在上，分类依次向下） |
| 列数 | 双列/多列 grid（dense 模式） | 单列布局，卡片独占一行 |
| SVG 连线 | 有（根→分类→单词→拆分） | 无（完全取消线条） |
| 拆分卡片 | 独立蓝色 .split-card | 内嵌到单词卡片中（.split-inline） |
| 视口 | 3000x2000（防止 grid 挤压） | 414x800（手机宽度） |
| 用途 | 电脑查看、打印 | 手机查看、微信/钉钉传阅 |

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

解析规则与桌面版一致：
- `# ` 开头的是**根节点标题**（一级标题），标题下方连续的 `> ` 引用块会被提取并渲染到根节点内部
- `## ` 开头的是**分类节点**（二级标题）
- `- **单词** /音标/ 词性. 释义` 是**单词卡片**
- 缩进的 `  - → re(回)+turn(转)` 是**词根拆分**，会被内嵌到单词卡片底部
- 过滤掉 `关联词网`、`相关页面`、`相关链接` 等非分类尾部区块

### 2. 生成移动端 HTML

复制模板并修改路径：

```bash
# 复制模板到输出目录
cp ~/.claude/skills/md-mindmap-to-pdf-mobile/templates/generate_mobile_mindmap.py "$OUTPUT_DIR/"
cp ~/.claude/skills/md-mindmap-to-pdf-mobile/templates/export_mobile_pdf.js "$OUTPUT_DIR/"
```

然后修改 `generate_mobile_mindmap.py` 中的 `MD_PATH` 和 `HTML_PATH`，运行：

```bash
cd "$OUTPUT_DIR" && python generate_mobile_mindmap.py
```

### 3. 导出 PDF

使用 `run-code` + Playwright API（同桌面版）：

```bash
"$PWCLI" run-code --filename "$OUTPUT_DIR/export_mobile_pdf.js"
```

## 核心坑点与解决方案

### 坑 1：音标在窄卡片内被不自然断行

**现象**：`involve /ɪnˈvɒlv/` 中音标被截断成两行。

**解决**：单词和音标用 flex 容器包裹，设置 `white-space: nowrap`，让它们作为一个整体在必要时换行，而不是在中间断开：

```html
<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px;">
  <strong style="white-space:nowrap;">involve</strong>
  <span style="white-space:nowrap;">/ɪnˈvɒlv/</span>
</div>
```

### 坑 2：拆分文本带 "- -" 脏前缀

**现象**：原始 markdown 中拆分行以 `  - →` 开头，提取后变成 `- - → ...`。

**解决**：解析阶段用正则清理：

```python
split_text = re.sub(r"^-\s*", "", split_text.strip())
```

### 坑 3：双列布局在 414px 下太挤

**现象**：grid 双列导致卡片宽度不足，内容大量换行。

**解决**：移动端始终使用单列 flex 布局，`width: 100%`，让每张卡片独占一行。

### 坑 4：viewport 过宽导致 PDF 不是手机尺寸

**现象**：默认 1280px 视口下，即使 CSS 写了 `max-width: 414px`，PDF 尺寸也会被拉宽。

**解决**：`run-code` 中设置手机视口：

```javascript
await page.setViewportSize({ width: 414, height: 800 });
```

### 坑 5：拆分卡片独立显示占用空间

**现象**：桌面版中蓝色拆分卡片是独立节点，移动端纵向堆叠后显得冗长。

**解决**：将拆分内容直接内嵌到单词卡片底部，用 `.split-inline` 子元素呈现，蓝色底色与黄色卡片形成层次，不另起独立卡片。

## 节点配色规范

| 节点类型 | 背景色 | 文字色 | 用途 |
|---------|--------|--------|------|
| 根节点 | `#9e9e9e` | `#fff` | 词根/前缀主题 |
| 分类节点 | `#ffc107` | `#333` | 语义分类（二级标题） |
| 单词卡片 | `#fff3cd` | `#333` | 单词+音标+释义 |
| 拆分内嵌 | `#b3e5fc` | `#01579b` | 词根拆分说明（嵌在卡片内） |

## 调试指南

- **PDF 在手机上显示太宽**：检查 `page.setViewportSize({width: 414, height: 800})` 是否设置
- **音标还是被截断**：检查 `fmt_word` 中 flex 容器的 `white-space: nowrap`
- **拆分块前面有 "-"**：检查 `clean_split` 正则是否生效
- **内容被截断**：检查动态尺寸测量 `el.scrollHeight + 40`

## 输出约定

- HTML 临时文件：与输出 PDF 同目录，后缀 `.html`
- PDF 文件：按用户指定路径交付，建议后缀 `_mobile.pdf`
- 视口宽度：固定 414px（iPhone 14 Pro Max 逻辑宽度）

