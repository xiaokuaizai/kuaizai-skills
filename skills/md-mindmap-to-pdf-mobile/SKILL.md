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
  - notebook 思维导图
  - 深色思维导图
  - 交互式思维导图
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

## 输出模式

本 skill 支持两种输出模式：

### 模式一：移动端竖版 PDF（经典版）
适合在手机 PDF 阅读器中纵向滑动查看。

| 特性 | 桌面版 md-mindmap-to-pdf | 移动端竖版 PDF |
|------|------------------------|----------------|
| 布局方向 | 横向展开（根节点在左，分类向右展开） | 纵向堆叠（根节点在上，分类依次向下） |
| 列数 | 双列/多列 grid（dense 模式） | 单列布局，卡片独占一行 |
| SVG 连线 | 有（根→分类→单词→拆分） | 无（完全取消线条） |
| 拆分卡片 | 独立蓝色 .split-card | 内嵌到单词卡片中（.split-inline） |
| 视口 | 3000x2000（防止 grid 挤压） | 414x800（手机宽度） |
| 用途 | 电脑查看、打印 | 手机查看、微信/钉钉传阅 |

### 模式二：Notebook 风格交互式 HTML（推荐）
模仿 Notebook 视频风格的现代深色主题思维导图，**可点击展开/折叠**，在手机浏览器中打开效果最佳。

| 特性 | 移动端竖版 PDF | Notebook 交互式 HTML |
|------|---------------|---------------------|
| 背景 | 浅灰 #f0f2f5 | 深黑 #0d0d0d |
| 根节点 | 扁平灰 | 深灰圆角卡片 + 阴影 |
| 分类节点 | 统一黄色 | 按语义分配主题色（黄/绿/橙/紫等） |
| 连线 | 无 | 贝塞尔曲线（平滑弧线） |
| 交互 | 无 | 点击分类节点展开/折叠单词卡片 |
| 文件格式 | PDF | HTML（手机浏览器直接打开） |
| 用途 | 传阅、打印 | 交互学习、手机浏览器查看 |

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

### 模式一：移动端竖版 PDF（经典版）

#### 1. 读取并解析 Markdown

解析规则与桌面版一致：
- `# ` 开头的是**根节点标题**（一级标题），标题下方连续的 `> ` 引用块会被提取并渲染到根节点内部
- `## ` 开头的是**分类节点**（二级标题）
- `- **单词** /音标/ 词性. 释义` 是**单词卡片**
- 缩进的 `  - → re(回)+turn(转)` 是**词根拆分**，会被内嵌到单词卡片底部
- 过滤掉 `关联词网`、`相关页面`、`相关链接` 等非分类尾部区块

#### 2. 生成移动端 HTML

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

#### 3. 导出 PDF

使用 `run-code` + Playwright API（同桌面版）：

```bash
"$PWCLI" run-code --filename "$OUTPUT_DIR/export_mobile_pdf.js"
```

### 模式二：Notebook 风格交互式 HTML

#### 1. 批量生成交互式 HTML

使用 `generate_notebook_interactive.py` 模板，它会自动扫描 `wiki/concepts` 目录下的所有 `前缀_*.md` 文件，生成对应的交互式 HTML：

```bash
cp ~/.claude/skills/md-mindmap-to-pdf-mobile/templates/generate_notebook_interactive.py "$OUTPUT_DIR/"
# 修改脚本中的 WIKI_DIR 和 OUTPUT_DIR 路径
python "$OUTPUT_DIR/generate_notebook_interactive.py"
```

#### 2. 在手机浏览器中打开

生成的 `.html` 文件可以直接在手机浏览器中打开（通过文件传输或本地 HTTP 服务器）。

**交互说明**：
- 初始状态只显示根节点和分类标签
- 点击分类标签：该分支下的单词卡片以 `opacity` 淡入动画展开，同时贝塞尔连线动态绘制
- 再次点击：折叠收起，连线同步更新
- 分类标签旁的 `+` / `-` 符号指示展开状态

#### 3. 视觉特征

- **白色背景**：`#ffffff` 干净清爽，打印/截图友好
- **根节点**：`#f0f4f8` 浅灰蓝圆角卡片，带微阴影和 hover 上浮效果，纵向居中于所有分支
- **分类节点**：按语义分配主题色（动作=黄、状态=绿、抽象=橙、空间=紫、情感=粉、时间=青），圆角胶囊形，纵向居中于其单词卡片组
- **单词卡片**：`#ffffff` 白底 + 所属分类颜色的左侧边框高亮 + 浅灰边框，层次分明
- **拆分内嵌**：`#e3f2fd` 浅蓝底 + `#01579b` 文字，嵌在卡片底部
- **贝塞尔连线**：平滑 S 形弧线，根→分类用分类同色粗线（2.5px），分类→单词用蓝灰细线（1.5px）

## Notebook 风格核心坑点与解决方案

### 坑 1：`max-height` 动画导致 flex 子项宽度塌陷

**现象**：使用 `max-height: 0 → scrollHeight` 过渡展开单词卡片时，所有卡片被压缩成一条垂直线，宽度为 0。

**原因**：Chromium 在 `max-height` 动画期间对 `overflow: hidden` 的 flex 容器内部宽度计算有 bug。

**解决**：放弃 `max-height` 动画，改用 `display: none → flex` 切换 + `opacity` 淡入淡出：
- 展开：先 `display: flex`，下一帧再添加 `.expanded` 类触发 `opacity` 过渡
- 折叠：先移除 `.expanded` 触发 `opacity` 淡出，300ms 后再 `display: none`
- SVG 连线在 `requestAnimationFrame` 中重绘，确保布局稳定后计算正确位置

### 坑 2：Python `hash()` 不稳定导致分类颜色每次运行不同

**现象**：同一分类标题在不同运行中得到不同颜色。

**解决**：使用稳定哈希替代 `hash(title)`：
```python
idx = sum(ord(c) for c in title) % len(FALLBACK_COLORS)
```

### 坑 3：`display: none` 元素无法计算 bounding box

**现象**：折叠状态下 SVG 连线指向错误位置。

**解决**：`redrawAll()` 只绘制已展开分支的连线（`wgs.classList.contains("expanded")`），折叠分支的单词卡片不参与布局，不绘制连线。

---

## 移动端竖版 PDF 坑点

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

### Notebook 白色主题（交互式 HTML）

| 节点类型 | 背景色 | 文字色 | 边框/高亮 | 用途 |
|---------|--------|--------|----------|------|
| 页面背景 | `#ffffff` | `#333333` | - | 白底 |
| 根节点 | `#f0f4f8` | `#1a1a2e` | `#d0d8e0` | 词根/前缀主题 |
| 分类-动作 | `#ffc107` | `#111` | - | 动作/行为/动态相关 |
| 分类-状态 | `#4caf50` | `#111` | - | 状态/性质/特征相关 |
| 分类-抽象 | `#ff9800` | `#111` | - | 抽象/概念/思想相关 |
| 分类-空间 | `#9c27b0` | `#fff` | - | 空间/位置/方向相关 |
| 分类-情感 | `#e91e63` | `#fff` | - | 情感/心理/感受相关 |
| 分类-时间 | `#00bcd4` | `#111` | - | 时间/频率/程度相关 |
| 单词卡片 | `#ffffff` | `#333333` | 分类色左边框 + `#e0e0e0` | 单词+音标+释义 |
| 拆分内嵌 | `#e3f2fd` | `#01579b` | `#90caf9` | 词根拆分说明 |
| 连线-根到分类 | 分类同色 | - | - | 粗线 2.5px 贝塞尔 |
| 连线-分类到单词 | `#64b5f6` | - | - | 细线 1.5px 贝塞尔 |

### 移动端竖版 PDF（经典版）

| 节点类型 | 背景色 | 文字色 | 用途 |
|---------|--------|--------|------|
| 根节点 | `#9e9e9e` | `#fff` | 词根/前缀主题 |
| 分类节点 | `#ffc107` | `#333` | 语义分类（二级标题） |
| 单词卡片 | `#fff3cd` | `#333` | 单词+音标+释义 |
| 拆分内嵌 | `#b3e5fc` | `#01579b` | 词根拆分说明（嵌在卡片内） |

## 调试指南

### Notebook 交互式 HTML
- **点击分类后单词卡片不显示**：检查是否使用了 `display:flex + opacity` 动画方案，避免 `max-height` 动画
- **连线位置错位**：检查 `redrawAll()` 是否在 `requestAnimationFrame` 中调用，确保布局稳定
- **分类颜色每次运行不同**：检查是否使用了 `sum(ord(c) for c in title)` 稳定哈希
- **折叠后页面仍有大量空白**：检查折叠后是否设置了 `display: none` 释放空间

### 移动端竖版 PDF
- **PDF 在手机上显示太宽**：检查 `page.setViewportSize({width: 414, height: 800})` 是否设置
- **音标还是被截断**：检查 `fmt_word` 中 flex 容器的 `white-space: nowrap`
- **拆分块前面有 "-"**：检查 `clean_split` 正则是否生效
- **内容被截断**：检查动态尺寸测量 `el.scrollHeight + 40`

## 输出约定

### Notebook 交互式 HTML
- HTML 文件：按用户指定路径交付，后缀 `.html`
- 用途：手机浏览器直接打开，支持点击展开/折叠
- 无需 Playwright 导出，纯静态 HTML 文件

### 移动端竖版 PDF
- HTML 临时文件：与输出 PDF 同目录，后缀 `.html`
- PDF 文件：按用户指定路径交付，建议后缀 `_mobile.pdf`
- 视口宽度：固定 414px（iPhone 14 Pro Max 逻辑宽度）

