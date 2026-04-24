# kuaizai-skills

小快哉的 skills 库，存放 [Claude Code](https://claude.ai/code) 自定义 Skills，方便在不同设备或会话间复用。

## 目录结构

```
kuaizai-skills/
├── README.md
└── skills/
    └── md-mindmap-to-pdf/      # Markdown 树状思维导图生成器
```

## Skills 列表

### md-mindmap-to-pdf

将 Markdown 词根/前缀学习页（或任何层级化 markdown 索引）转换为树状思维导图 PDF。

**核心功能：**
- 解析 `# ` 根节点标题及 `> ` 引用块（核心意象 / 词源提示）
- 解析 `## ` 分类节点、`- **单词**` 单词卡片、词根拆分节点
- 生成带 SVG 连接线的可视化卡片图（灰色根节点 → 黄色分类 → 米色单词 → 蓝色拆分）
- 单词过多时自动启用 CSS Grid 多列布局
- 通过 Playwright 动态测量页面尺寸后导出 PDF，避免内容裁切

**文件位置：** `skills/md-mindmap-to-pdf/`
