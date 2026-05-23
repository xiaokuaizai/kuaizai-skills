# Word Label Toolkit
# 单词标签批量生成工具包

## 用途

从 Markdown 提示词文件中，批量提取 `[Labels]` 标签列表，生成排版整齐的 HTML 页面，并自动截图成 PNG 图片。

用于解决 GPT 生成图片时中文文字错误的问题——把文字用 HTML 精确渲染后作为参考图。

## 使用步骤

### 1. 安装依赖

```bash
npm install sharp
```

`sharp` 用于截图后自动裁剪空白边缘。

### 2. 配置路径

编辑 `generate-labels-only.js` 和 `batch-screenshot.js` 顶部的路径变量：

```js
const SOURCE_DIR = path.resolve("你的提示词目录");
const OUTPUT_DIR = path.resolve("输出HTML目录");
```

### 3. 生成 HTML

```bash
node generate-labels-only.js
```

会自动解析所有 `.md` 文件中的 `[Labels]` 标签，每个 prompt 生成一个独立的 HTML 文件。

### 4. 截图成 PNG

```bash
node batch-screenshot.js
```

调用系统 Edge 浏览器 headless 模式截图，并用 sharp 自动裁剪空白边缘。

## 目录结构

```
word-label-toolkit/
├── README.md                 # 本说明文档
├── generate-labels-only.js   # 核心：生成纯标签 HTML
├── batch-screenshot.js       # 核心：批量截图 + 裁剪
└── package.json              # 依赖信息
```

## 核心脚本说明

### generate-labels-only.js

- 遍历指定目录下所有 `.md` 文件
- 用正则提取每个 `[PROMPT]` 区块
- 从区块中提取 `Words:` 和 `[Labels] Complete label list:`
- 每个 prompt 生成一个独立 HTML，文件名格式：`类别_序号_标题.html`
- HTML 只包含纯标签网格，无标题、无 footer、无多余内容
- 标签样式：白色圆角矩形 + 2px 彩色边框 + 圆形数字 badge
- 布局：CSS Grid，每行固定 4 列，所有标签宽度一致

### batch-screenshot.js

- 遍历所有 HTML 文件
- **先把文件复制为临时文件**（避免文件名中的 emoji/特殊字符导致 Edge 无法打开）
- 调用 Edge headless 截图（`--headless --screenshot`）
- 用 sharp 的 `.trim()` 自动裁剪空白边缘
- 清理中间 raw 文件

## 遇到的坑 & 解决方案

### 坑 1：Windows bash 中反斜杠被吞

**现象：** Node.js 脚本里写 `G:ooar` 会变成 `G:foobar`，路径完全错乱。

**原因：** Windows bash (Git Bash/MSYS) 把反斜杠当作转义符。

**解决：**
- 脚本文件里用双反斜杠：`"G:\\foo\\bar"`
- 不要在 `node -e` 里直接写带反斜杠的路径，一定写成 `.js` 文件再运行

### 坑 2：文件名含 emoji/特殊字符，Edge 打不开

**现象：** Edge headless 截图时报错或生成"未找到文件"的黑色图片。

**原因：** 文件名中包含 `🚢`、`⚧`、`✈️` 等 emoji，通过 `file:///` URL 传给 Edge 时编码失败。

**解决：** 截图前先把 HTML 文件复制到一个干净的临时文件名（如 `temp_screenshot.html`），截图完立即删除。

### 坑 3：Edge 不支持 `--screenshot-fullpage`

**现象：** 用 `--screenshot-fullpage` 参数，Edge 没有任何输出，也不生成文件。

**原因：** Edge/Chrome 的新版 headless 模式已经移除了 `--screenshot-fullpage` 参数。

**解决：**
1. 先用足够大的 `--window-size=1500,20000` 截图（覆盖完整页面高度）
2. 再用 sharp 的 `.trim()` 自动裁剪掉底部空白

### 坑 4：md 文件的分隔符把内容切散

**现象：** 用 `text.split(/\n={40,}\n/)` 分割后，`[Labels]` 内容和 `[PROMPT]` 标题被分到不同块里，标签提取失败。

**原因：** md 文件中每个 PROMPT 区块内部也有 `====` 分隔符（标题和正文之间）。

**解决：** 不要用 split，改用正则全局匹配完整 PROMPT 块：
```js
const promptRegex = /\[PROMPT\s*\d+\][\s\S]*?(?=\n\[PROMPT\s*\d+\]|$)/g;
```

### 坑 5：标签框大小不一致

**现象：** 用 Flexbox 时，同一行内有的标签长有的标签短。

**原因：** `flex: 1 1 auto` 会让标签按内容自适应宽度。

**解决：** 用 CSS Grid 固定列数：
```css
.labels-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
}
```
所有标签宽度完全一致，最后一行不满时自然留白，不会拉伸。

### 坑 6：文字太长溢出标签框

**现象：** 加了 `white-space: nowrap` 后，长文字溢出边框被截断。

**原因：** 中文释义太长，一行放不下。

**解决：** 去掉 `white-space: nowrap`，允许自动换行。同时用 Grid 保证每列有足够宽度（4列 × ~360px）。

### 坑 7：标签数量少时被拉得很宽

**现象：** 一行只有 2 个标签时，`flex: 1 1 0` 会把它们拉伸到占满整行，变得很丑。

**原因：** Flexbox 的 flex-grow 会让元素填满剩余空间。

**解决：** 用 CSS Grid 的 `repeat(4, 1fr)` 固定 4 列，无论一行有几个标签，宽度都固定为容器的 1/4，不会拉伸。

## 样式参数速查

| 参数 | 值 | 说明 |
|------|-----|------|
| 容器宽度 | 1500px | 截图窗口宽度 |
| 每行列数 | 4 | CSS Grid 固定列数 |
| 标签边框 | 2px solid | 彩色边框 |
| 标签圆角 | 10px | border-radius |
| 标签内边距 | 8px 12px | padding |
| 字体大小 | 14px | label-text |
| badge 大小 | 22px × 22px | 圆形数字 |
| 标签间距 | 10px | gap |

## 配色方案

```js
const COLORS = [
  "#E74C3C", "#3498DB", "#2ECC71", "#F39C12", "#9B59B6",
  "#1ABC9C", "#E67E22", "#34495E", "#D35400", "#27AE60",
  "#2980B9", "#8E44AD", "#C0392B", "#16A085", "#F1C40F",
];
```

按顺序循环使用，每个标签一个颜色。
