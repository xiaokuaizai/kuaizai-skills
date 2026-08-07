# kuaizai-skills

小快哉的 skills 库，存放 [Claude Code](https://claude.ai/code) 自定义 Skills，方便在不同设备或会话间复用。

## 目录结构

```
kuaizai-skills/
├── README.md
└── skills/
    ├── md-mindmap-to-pdf/                    # 静态树状思维导图 PDF 生成器
    ├── md-mindmap-to-pdf-mobile/             # Notebook 风格交互式思维导图
    └── syncing-directories-with-junction/    # Windows 目录联接实时双向同步
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

### md-mindmap-to-pdf-mobile

将 Markdown 词根/前缀学习页转换为 **Notebook 风格交互式思维导图 HTML**，适合在手机浏览器查看。

**核心功能：**
- 白色背景 + 圆角卡片设计，语义化配色（动作/状态/抽象/空间/情感/时间）
- 根节点固定在左侧垂直居中，分类节点以彩色胶囊标签向右展开
- 点击分类节点可展开/折叠单词卡片，带 opacity 过渡动画
- 单词卡片与节点之间使用 SVG 贝塞尔曲线平滑连线
- 根据单词数量自动分栏：>20 词三列、>8 词两列、≤8 词单列
- 完整保留音标、释义、词根拆分等学习信息

**文件位置：** `skills/md-mindmap-to-pdf-mobile/`

### syncing-directories-with-junction

用 Windows 目录联接（Junction）让两个本地路径指向同一份物理数据，实现零延迟、零冲突的实时双向同步。适用于一个路径已有 git/云同步（如 Obsidian vault、xkz_note 等）、另一个路径是日常工作入口的场景。

**核心功能：**
- 三种方案对比（Junction / robocopy 定时 / Syncthing），帮助选型
- 4 项执行前检查（程序占用、git 跟踪、同步机制、文件差异对比）
- 5 步标准化流程（双向 robocopy 合并 → 一致性验证 → 删 B → 建 Junction → 双向通透验证）
- 每步固定命令模板 + 验证条件 + 退出码检查
- Red Flags 清单（6 种必须停下询问的情况）
- Safe Removal 规则（区分"删联接"和"删内容"，避免误删真实数据）
- 术语辨析（Junction / Symbolic Link / Hard Link）

**文件位置：** `skills/syncing-directories-with-junction/`
