# 故事板 HTML 制作规范

> 本规范负责把独立生成的单镜头分镜图，按视频段（SEG）组织、排版成可浏览的导演故事板总表。
> 它不负责图像生成本身；图像生成规则详见 `references/storyboard-sketch.md`。
> 配套模板文件：`templates/storyboard_seg_row_template.html`。

## 1. 适用范围与定位

本规范在阶段 E 强制启用。调用完整 `minimax-storyboard` 流程时，HTML 导演总表不是可选项，必须在全部单镜头图通过 QA 后制作并完成浏览器校验。

开始执行时必须满足：

- `Shot List` 与 `Minimax H3 Segments` 已锁定。
- `references/storyboard-sketch.md` 要求的单镜头分镜图已全部生成到 `panels/`。
- 输出可浏览的 HTML 导演总表；长图 PNG 仍可作为附加产物。

**分工**：

- `storyboard-sketch.md`：规定每个镜头如何单独生成一张 9:16 彩色分镜图。
- 本规范：规定如何把多个单镜头图排进 HTML 总表，包括 SEG 行版式、镜头号标签、SVG 站位图、环境声字段位置等。

---

## 2. 强制前置条件

开始 HTML 总表制作、站位图绘制之前，**必须同时满足**以下条件：

1. **`Shot List` 与 `Minimax H3 Segments` 已锁定**，且镜头与 SEG 的对应关系明确。
2. **`panels/` 目录下所有该任务涉及的单镜头分镜图已全部生成完毕**。
3. **所有单镜头图已通过 `references/storyboard-sketch.md` 的 QA 校验**：
   - 每张图只包含一个 9:16 镜头画面；
   - 无多格、无拼接、无分栏、无 storyboard sheet 版式；
   - 画面内容、人物、服装、道具与锁定镜头一致。
4. **`doc/镜头内容检验.md` 已通过**：每个镜头的 `Duration` ≥ `Min Duration`，SEG 总时长 ≤ 15s（建议 ≤ 13s），并已把锁定时长回填到 `doc/镜头设计.md`。
5. **`references/故事板HTML制作规范.md` 与 `templates/storyboard_seg_row_template.html` 已加载到当前任务上下文**。

**任一条件未满足，禁止开始以下操作：**

- 生成 HTML 总表；
- 绘制 SVG 站位图；
- 渲染总表 PNG。

---

## 3. 基本原则

1. **一行一个 SEG**：HTML 总表的每一行对应一个 Minimax H3 视频段（SEG），不是对应单个镜头。
2. **单镜头图直接入表**：左栏不再使用段级拼接图，而是直接引用 `panels/SH-XX.png`，每张图下方带镜头号标签。
3. **文字用真实文字**：镜头号、景别、对白、说明、CAM/FOV 标签等全部用 HTML/SVG 真实文字，不依赖图像模型渲染文字。
4. **固定行高、等宽排版**：每行高度固定并基本占满一屏；每行的左中右三栏比例固定，确保滚动浏览时版式稳定。
5. **环境声字段在右栏**：中栏不再保留「声音」字段，统一放到右栏 SVG 站位图下方，用横线与上方图注分隔。右栏字段标题为「环境声」，内容包括环境描述与动作音效。

---

## 4. HTML 必填字段与占位符清单

HTML 总表不是自由排版文档，以下字段**必须真实填写**，禁止保留任何 `{{...}}` 占位符、示例文本或模板默认值。

### 4.1 顶部全局信息（必填）

| 字段 | 占位符示例 | 填写要求 |
|---|---|---|
| 标题 | `{{EPISODE_TITLE}}` | 真实剧集/任务名称 |
| 总镜头数 | `{{TOTAL_SHOTS}}` | 与 `Shot List` 完全一致 |
| 总时长 | `{{TOTAL_DURATION}}` / `{{TOTAL_SECONDS}}` | 所有 SEG 时长之和 |
| 画幅 | `{{ASPECT_RATIO}}` | 如 `9:16` |
| 人物列表 | `{{CHARACTER_LIST}}` | 本任务全部核心人物 |
| SEG 总数 | `{{SEG_COUNT}}` | 与 `doc/视频分段.md` 一致 |

### 4.2 每个 SEG 必填字段

| 字段 | 占位符示例 | 填写要求 |
|---|---|---|
| SEG 编号 | `SEG-XX` | 与 `doc/视频分段.md` 一致，如 `SEG-01` |
| 风格 | `{{SEG_STYLE}}` | 必须填写，不可省略 |
| 主要内容 | `{{SEG_SUMMARY}}` | 只描述当前 SEG，禁止剧透下一段 |
| 时长 | `{{SEG_DURATION}}` | 与 SEG 标注时长一致 |
| 单镜头图 | `panels/{{SH-XX}}.png` | 每个镜头必须替换为真实文件名 |
| 镜头号标签 | `{{SH-XX}}` | 与图片文件名一致 |
| 景别 | 如 `{{SHOT_SIZE}}` | 真实景别，如全景、中景、特写 |
| 拍摄视角 | 如 `{{CAMERA_ANGLE}}` | 真实视角描述 |
| 镜头时长 | 如 `{{SHOT_DURATION}}` | 与 `Shot List` 一致 |
| 首帧锚点 | `{{FIRST_FRAME_ANCHOR}}` | 开场帧人物位置、朝向、道具、情绪 |
| 尾帧锚点 | `{{LAST_FRAME_ANCHOR}}` | 结束帧姿势、视线、道具状态，不写转场词 |
| 台词/旁白 | `{{DIALOGUE}}` / `{{NARRATION}}` | 实际出现在该 SEG 中的完整文本，不允许省略 |
| 环境声 | `{{ENV_SOUND}}` / `{{ACTION_SOUND}}` | 右栏环境声字段，必须真实填写 |
| SVG 站位图 | `{{BLOCKING_SVG}}` | 角色位置、CAM、FOV、运动方向必须真实绘制 |

### 4.3 占位符检查规则

1. 生成 HTML 后必须全局搜索 `{{` 和 `}}`，任何剩余占位符都视为未完成的 HTML，禁止进入阶段 F。
2. 禁止使用示例文本填充必填字段，例如 `示例风格`、`请填写`、`TODO`、`待定`、`N/A`。
3. 若某项确实不存在（如某 SEG 无台词），应写「无」或「-」，而不是保留占位符。
4. Agent 替换占位符后，必须逐行对照 `Shot List`、`Minimax H3 Segments`、`视频生成内容检验` 复核，确保没有遗漏。

---

## 5. 输出目录结构

一个故事板任务完成后，目录结构如下：

```text
storyboard_output/
├─ doc/                              # 文字产物
│  ├─ 前提设定.md                     # Assumptions + Continuity Bible
│  ├─ 镜头设计.md                     # Beat Map + Shot List
│  ├─ 镜头内容检验.md                 # Required Content + Min Duration + 通过状态
│  ├─ 视频分段.md                     # Minimax H3 Segments + 最终提示词
│  ├─ 风险质检.md                     # 风险 + QA + 统计 + 修复记录
│  ├─ 导演总表.md                     # 最终文字版导演总表
│  └─ 文件地址管理.md                  # 图片、参考图、音频等文件路径登记表
├─ panels/                            # 单镜头源图（由 storyboard-sketch.md 生成）
│  ├─ SH-01.png
│  ├─ SH-02.png
│  └─ ...
├─ *_director_full_table.html         # 可浏览总表（基于 templates/storyboard_seg_row_template.html）
└─ *_director_full_table.png          # 总表静态渲染长图（可选）
```

- `doc/`：所有 Markdown 文字产物统一放在这里。
- `panels/`：每个镜头一张独立 9:16 分镜图，命名保留镜头 ID（如 `SH-01.png`）。
- 模板已弃用 `segments/` 段级拼接图目录；左栏直接引用 `panels/` 单图。

---

## 6. HTML 总表生成方式

HTML 导演总表可通过以下方式生成，任选其一但同一任务内保持一致：

### 方式一：使用脚本生成（推荐）

使用本 skill 自带的 `scripts/build_director_table.py`，从结构化 JSON 直接生成 HTML 和 Markdown 总表：

```bash
python scripts/build_director_table.py \
  --input "00_元数据/清单/director_table_input.json" \
  --output-html "*_director_full_table.html" \
  --output-md "doc/导演总表.md"
```

输入 JSON 需包含 `episode_title`、`aspect_ratio`、`characters`、`segments` 等字段，每个 segment 包含 `shots` 列表及首帧/尾帧锚点、台词、环境声等信息。该脚本会同时校验 SEG ID 格式、镜头数 ≥2、时长 0-15 秒。

### 方式二：基于模板手动拼装

如需精细控制版式，可基于 `templates/storyboard_seg_row_template.html` 手动替换占位符并拼装。无论哪种方式，最终版式必须满足本章以下各节的排版规则。

---

## 7. 左栏：单镜头图网格

### 7.1 基本规则

- 左栏直接展示该 SEG 包含的所有单镜头图，每张图下方显示镜头号标签（如 `SH-01`）。
- 镜头号标签必须在图外，**禁止压在画面上**。
- 单图保持 9:16 比例，等比例缩放，不裁剪、不变形。
- 使用 CSS Grid 排列，按阅读顺序：从左到右、从上到下。

### 7.2 按镜头数量排布

按一个 SEG 内的镜头数量 N 排布。**每个 SEG 至少 2 个镜头，N=1 不再出现。**

| 镜头数 N | grid-template-columns | grid-template-rows | 说明 |
|---------|----------------------|-------------------|------|
| 2 | `repeat(2, 1fr)` | 1 行 | 横向排列 |
| 3 | `repeat(2, 1fr)` | `repeat(2, 1fr)` | 2×2，第 4 格空白（`visibility: hidden`） |
| 4 | `repeat(2, 1fr)` | `repeat(2, 1fr)` | 2×2 满格 |
| 5 | `repeat(3, 1fr)` | `repeat(2, 1fr)` | 2×3，第 6 格空白 |
| 6 | `repeat(3, 1fr)` | `repeat(2, 1fr)` | 2×3 满格 |
| 7-8 | `repeat(4, 1fr)` | `repeat(2, 1fr)` | 末尾留白 |
| 9+ | 优先 3 列或 4 列 | 按需 | 若过密，拆分为多个 SEG |


## 8. 三栏布局与排版

### 8.1 行高与宽度

- 每行使用固定高度，`min-height: 95vh`。
- 行宽 = 容器宽度（通常为浏览器可视宽度）。
- 内容超出时允许内部滚动，但不增加行高。

### 8.2 标题栏

- 标题栏固定高度 76px，底部一条横线。
- 标题栏内容：`SEG-XX` 编号 + `风格：{{SEG_STYLE}}｜主要内容：{{SEG_SUMMARY}}` + 时长 badge。
- **标题必须包含「风格」字段**，不可省略。
- **「主要内容」仅描述当前 SEG 的内容**，禁止出现下一段 SEG 的情节、信息或剧透。
- 标题字号较大、加粗。
- 横线下方三栏内容必须紧贴横线，无额外空隙。

### 8.3 三栏比例

每行使用 CSS Grid 分为三栏：

| 左栏 | 中栏 | 右栏 |
|------|------|------|
| 约 60% | 约 25% | 约 15% |
| 单镜头图网格 | 导演分镜表信息 | SVG 站位图 + 环境声 |

Grid 参考：
```css
grid-template-columns: minmax(760px, 1.35fr) minmax(460px, .9fr) minmax(360px, 430px);
grid-template-rows: 76px 1fr;
```

### 8.4 中栏：导演分镜表信息

每个 SEG 对应的中栏内容：

- **镜头列表**：按顺序列出该 SEG 内的所有镜头：
  - `镜头号`
  - `景别`
  - `拍摄视角`
  - `时长`
- **首帧锚点**：该 SEG 开场帧中的准确人物位置、身体朝向、景别、主要道具和情绪状态。
- **尾帧锚点**：该 SEG 结束帧中的准确姿势、视线、道具状态、镜头关系和运动终点。**尾帧锚点不写转场词，不写括号补充。**转场信息由导演在后续流程中单独决定，不在 HTML 总表内标注。
- **台词 / 旁白**：只写实际出现在该 SEG 中的对白或旁白，**内容必须完整，不允许省略或只写片段**。

**注意**：中栏不设置「环境声」字段；环境声已迁移到右栏。

### 8.5 右栏：SVG 站位图 + 环境声

右栏从上到下依次为：

1. **标题**：`人物关系位置图 / CAM + FOV`
2. **SVG 站位图**：矢量绘制，不生成位图。必须包含：
   - 角色位置圆点（用角色名标签）。
   - 关键场景元素或道具。
   - `CAM` 位置与镜头方向箭头。
   - 浅色 `FOV` 扇形表示视角范围。
   - 若镜头有运动，用虚线箭头表示推/拉/跟/摇方向。
3. **图注说明**：`圆点为人物/空间锚点；蓝色为镜头视角，红色虚线为推/拉/跟/摇方向。`
4. **横线分隔**：一条水平线，与上方图注保持足够间距（约 24px）。
5. **环境声**：
   - 字段标题为「环境声」。
   - `环境：{{环境声描述}}`
   - `动作：{{动作音效描述}}`
   - 字号 18px，清晰可读。

---

## 9. HTML/CSS 技术要求

1. **固定布局优先**：使用 `display: grid`，三栏比例固定，不因窗口宽度变化而换行。
2. **图片引用**：所有 `<img>` 标签引用相对路径文件 `panels/SH-XX.png`，不内嵌 base64（除非交付单文件）。
3. **字体**：中文字体使用系统默认无衬线字体栈，如 `font-family: "Microsoft YaHei", "Noto Sans SC", Arial, sans-serif;`。
4. **配色**：背景浅色（如 `#fffdf8`），文字深色（如 `#202020`），边框细灰（如 `#d7ccbd`）。
5. **打印/渲染友好**：避免使用 sticky、fixed 定位，确保总表渲染为 PNG 时内容完整。
6. **移动端不做优先适配**：本规范面向桌面审阅，优先保证宽屏可读性。

---

## 10. 推荐实现流程

必须按以下顺序执行，不可跳过、不可并行：

1. **生成单镜头图**：按 `storyboard-sketch.md` 生成 `panels/SH-XX.png`。
2. **单镜头 QA 通过**：确认所有单镜头图符合 9:16、无多格、无拼接。
3. **复制模板**：将 `templates/storyboard_seg_row_template.html` 复制到任务目录。
4. **替换占位符**：
   - 顶部信息：`{{EPISODE_TITLE}}`、`{{TOTAL_SHOTS}}`、`{{TOTAL_DURATION}}`、`{{ASPECT_RATIO}}`、`{{CHARACTER_LIST}}`、`{{SEG_COUNT}}`、`{{TOTAL_SECONDS}}`。
   - 每个 SEG 的 `SEG-XX` 编号、`{{SEG_STYLE}}`、`{{SEG_SUMMARY}}`、`{{SEG_DURATION}}`。
   - 每个镜头的 `{{SH-XX}}`、景别、视角、时长。
   - 首帧/尾帧锚点、台词/旁白、环境声内容。
   - SVG 站位图中的角色位置、CAM 方向、FOV 扇形、运动方向。
   - 替换时必须对照第 4 节「HTML 必填字段与占位符清单」逐项勾选，禁止凭记忆遗漏。
5. **全局占位符检查**：替换完成后必须全局搜索 `{{` 和 `}}`，确认 HTML 中不存在任何未替换占位符；同时检查无 `TODO`、`N/A`、`待定`、`示例` 等示例文本残留。任何残留都视为 HTML 未完成，禁止进入阶段 F。
6. **验证排版**：启动本地 HTTP 服务，用浏览器打开验证每一行布局；重点检查标题横线是否紧贴三栏、环境声字段是否在右栏、单镜头图是否正确排列。
7. **渲染 PNG（可选）**：用浏览器无头渲染或截图工具生成 `*_director_full_table.png`。
8. **输出文字表**：同步生成 `*_director_full_table.md`。

---

## 11. 本地验证方法

模板使用占位符 `{{SH-XX}}`，直接双击 HTML 文件会导致图片路径含花括号而加载失败。验证时必须通过本地 HTTP 服务访问：

```bash
python -m http.server 8765 --directory <项目目录>
```

然后访问：

```
http://127.0.0.1:8765/<文件名>.html
```

若需独立验证某个 SEG，可复制一份 HTML，在 `<head>` 中加入脚本隐藏其他 SEG：

```html
<script>
document.addEventListener('DOMContentLoaded', function() {
  document.querySelectorAll('.seg-row').forEach(function(row) {
    var id = row.querySelector('.seg-id');
    if (!id || id.textContent.trim() !== 'SEG-XX') {
      row.style.display = 'none';
    }
  });
});
</script>
```

---

## 12. 交付文件清单

必须输出：

- `*_director_full_table.html`
- `*_director_full_table.md`
- `panels/` 目录（单镜头源图）

可选输出：

- `*_director_full_table.png`
- `blocking/` 目录（独立 SVG 站位图）

---

## 13. QA 检查项

交付前检查：

- [ ] HTML 制作开始前，已确认 `panels/` 目录完整且所有单镜头图通过 QA（9:16、无多格、无拼接）。
- [ ] 每行对应一个 SEG，不是单个镜头。
- [ ] 每行标题必须包含「风格」字段。
- [ ] 每行「主要内容」仅描述当前 SEG，不出现下一段内容。
- [ ] 左栏直接引用 `panels/SH-XX.png`，每张图下方有镜头号标签，标签不压图。
- [ ] 单镜头图排列符合第 7.2 节规则，单图保持 9:16 比例。
- [ ] 中栏信息来自已锁定的 `Shot List` 和 `Minimax H3 Segments`，无新增走位/道具/服装。
- [ ] 中栏不保留「环境声」字段；环境声字段在右栏 SVG 下方。
- [ ] 右栏站位图为 SVG，包含 `CAM`、方向箭头和 `FOV` 扇形。
- [ ] 右栏图注在横线上方，环境声在横线下方，横线与上方图注有足够间距。
- [ ] 总表无 BGM 字段；音频只写角色语音、环境声和动作音效。
- [ ] 文字清晰可读，无依赖图像模型生成的模糊文字。
- [ ] **HTML 中不存在任何 `{{...}}` 占位符；已全局搜索 `{{` 和 `}}` 确认。**
- [ ] **所有必填字段已按第 4 节清单真实填写，无示例文本、无 `TODO`、无 `N/A`、无 `待定`。**
- [ ] **Agent 已逐 SEG 对照 `Shot List`、`视频分段.md`、`视频生成内容检验.md` 复核占位符替换，无遗漏。**
- [ ] 通过本地 HTTP 服务验证时，所有图片正常加载，无裂图。

---

## 14. 与相关文件的引用关系

- `templates/storyboard_seg_row_template.html`：可直接复制的 HTML 模板。
- `references/storyboard-sketch.md`：单镜头分镜图生成规范。
- `references/场景锚点.md`：场景参考与空间一致性规则。
- `references/导演分镜连续制作行为规范.md`：连续分镜的人物/空间/机位一致性规则。
- `references/output-format.md`：输出表格字段规范。
- `references/transition-guide.md`：SEG 之间转场信息的填写规范（供导演参考，不写入 HTML 总表尾帧锚点）。
