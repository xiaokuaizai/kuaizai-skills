# 输出格式

## 输出文件结构

文字产物默认放在任务目录的 `doc/` 文件夹下：

| 文件 | 包含内容 |
|---|---|
| `doc/前提设定.md` | `Assumptions` + `Continuity Bible` |
| `doc/镜头设计.md` | `Beat Map` + `Shot List` |
| `doc/镜头内容检验.md` | 每镜头 `Required Content`、`Min Duration`、锁定时长和通过状态 |
| `doc/文本语义拆分表.md` | 对白/旁白/画外音/内心独白的语义拆分点、拆分理由、片段时长和人工抽查状态 |
| `doc/视频生成内容检验.md` | 每个镜头的画面扩写 + 镜头时间轴 / 运镜路线 |
| `doc/视频分段.md` | `Minimax H3 Segments` + 每条 SEG 的最终提示词 |
| `doc/风险质检.md` | `Continuity Risk Checks` + `Content QA` + `Production Stats` + `Repair Notes` |
| `doc/导演总表.md` | 最终文字版导演总表 |
| `doc/文件地址管理.md` | 所有图片、参考图、音频、任务级脚本等文件路径登记表 |
| `doc/分镜图方案.md` | 全部镜头的 `Storyboard Sketch Briefs`（强制） |

其他产物：

- `panels/`：单镜头分镜图源图。
- `故事板参考图/`：每个 SEG 一张完整三栏故事板参考图（强制）。
- `00_元数据/清单/`：资产 manifest、upload result 和每个 SEG 的 asset pack（强制）。
- `scripts/`：任务级脚本，按需分子目录管理（`capture/`、`upload/`、`convert/`、`qa/`）。
- `*_director_full_table.html`：可浏览导演总表。
- `*_director_full_table.png`：总表静态渲染长图（可选）。

---

## Assumptions

只列出会影响生产的决定：

| 字段 | 值 |
|---|---|
| Aspect ratio | 9:16 或用户指定画幅 |
| Target runtime | 预估总时长 |
| Style | 风格化3D动画动态漫画 / 青春冒险科幻悬疑 |
| Generation model | Minimax_H3 |
| Segment cap | 15 秒硬上限，目标 8-13 秒 |

## Continuity Bible

| 元素 | 锁定细节 |
|---|---|
| Character A | 姓名、外貌、服装、情绪基线 |
| Character B | 姓名、外貌、服装、情绪基线 |
| Location | 空间布局和视觉锚点 |
| Camera axis | 主轴线下谁在画面左侧/右侧 |
| Props | 归属、手别、位置、连续性状态 |

## Beat Map

| Beat ID | 剧本范围 | 戏剧功能 | 必要视觉信息 | 预估时长 |
|---|---|---|---|---:|

## Shot List

| Shot ID | Beat | Duration | Min Duration | Shot Size | Camera | Blocking | Action | Dialogue/Audio | Required Content | Cut Logic | Minimax H3 Segment |
|---|---|---:|---:|---|---|---|---|---|---|---|---|

`Blocking` 必须包含画面方向和纵深，例如：“女主 screen-right foreground，男主 screen-left midground”。

`Required Content` 必须列出该镜头中观众必须看到、听到或理解的所有信息，例如：场景识别、动作完成、情绪变化、道具揭示、台词。

`Min Duration` 根据 `Required Content` 按 `references/镜头内容检验规范.md` 反推得出；`Duration` 必须 **≥ `Min Duration`**。

如果输出 Minimax H3 提示词模式，每个镜头的摄影细节颗粒度必须一致。至少包含：景别、机位角度、焦距或镜头类型、景深、运镜。不要在同一输出里有的镜头写焦距、有的镜头完全不写。

## 视频生成内容检验

| Shot ID | Required Content | Duration | 镜头时间轴 / 运镜路线 | 画面扩写 | 摄影 | 光线 / 氛围 | 人物调度 / 道具状态 | 连续性检查 | 对应分镜图 |
|---|---|---:|---|---|---|---|---|---|---|

规则：

- `Duration` 必须复制 `Shot List` 中的锁定时长，**本阶段禁止修改**。
- `镜头时间轴 / 运镜路线` 必须连续覆盖 `0.0s` 到 `Duration`，不能有空隙、重叠或超出。
- 每个时间块可以丰富既定动作内部过程、摄影机运动、焦点/景别、人物细微反应、已有道具细节、空间和光影变化；**禁止新增剧情事件、角色、台词、道具、独立动作或改变核心动作结果**。
- 若镜头包含旁白/台词，时间轴要与音频时间点对齐。
- 扩写内容回填到 `doc/视频分段.md` 的 SEG 提示词时间轴，以及 `doc/分镜图方案.md` 的分镜图 brief。

---

## Minimax H3 Segments

| Segment ID | Duration | Shots | First-frame Anchor | Last-frame Anchor | Continuity Handoff | Minimax H3 Prompt | 避免项 |
|---|---:|---|---|---|---|---|---|

规则：

- 每个视频段时长必须 `<=15s`。
- 每个视频段时长目标区间为 `8-13s`；只有连续表演节拍、慢揭示或拆开会破坏动作的段落，才允许 12-15s，并必须在备注中说明理由。
- **每个 SEG 必须至少包含 2 个镜头，禁止单镜头 SEG。**
- Segment ID 应稳定，例如 `SEG-01`、`SEG-02`。
- 列出 SEG 内部所有 Shot ID。
- `Minimax H3 Prompt` 应是生产提示词，不是分析文字。
- 使用中文字段名 `避免项`，不要混用 `Avoid/避免`。
- `避免项` 始终使用这个结构：`固定避免项：不要生成对白字幕、标题字、解释字、旁白字卡、水印；对白只作为角色语音出现；已指定的道具文字可以保留。本段特殊避免项：...`
- `本段特殊避免项` 应写具体连续性风险，例如人物站位交换、道具归属变化、手别错误、道具朝向错误、增加额外人物、镜头轴线跳变。
- 如果视频段内部用时间块写镜头，每个时间块都必须包含统一摄影细节：`景别 / 机位角度 / 焦距 / 景深 / 运镜`。
- 音效时间用自然语言，不用符号式标记。使用 `镜头开头`、`镜头中段`、`镜头末尾`、`第X秒` 等；不要在音效后写 `@00:14`、`@XS` 等时间码。

## Continuity Risk Checks

| 风险 | 位置 | 修复方式 |
|---|---|---|

包括轴线跳变、缺少交接锚点、单段动作过多、视频段超长、道具归属不清、人物站位交换等问题。

## Content QA

最终交付前使用 `references/content-qa.md`。包含：

| Severity | Issue | Where | Why It Matters | Fix |
|---|---|---|---|---|

优先检查内容和提示词风险，而不是表面格式。如果没有严重问题，写：

```text
Content QA: 未发现 P0/P1 内容问题；剩余风险为 Minimax H3 生成时可能产生的表情/群演随机性。
```

## Storyboard Sketch Briefs

完整流程必须包含本节，并使用 `references/storyboard-sketch.md`。用户无需另行提出分镜图要求。

固定范围：`Shot List` 中每个镜头一张独立 9:16 彩色分镜图；交接对照图可以追加，但不能替代任何镜头图。

| Sketch ID | Source | Panel Type | Composition | Characters | Props | Camera | Continuity Purpose | Image Prompt |
|---|---|---|---|---|---|---|---|---|

规则：

- 分镜图 brief 必须从已有镜头、视频段和连续性锚点推导。
- 不要新增走位、服装、道具、光线或机位。
- 使用 `Shot List` 的稳定镜头 ID，例如 `SH-01`、`SH-02`，不另建第二套分镜图编号。
- 除非用户要求精修概念图，`Image Prompt` 应要求 colored storyboard panel / 彩色分镜图。
- 保持最终视频画幅，通常是 `9:16 vertical`。
- 禁字幕/禁叠加文字规则要与 Minimax H3 视频段提示词一致。

## Production Stats

每份 Minimax H3 提示词输出末尾放置：

| 场次 | 视频编号 | 时长 | 镜头数 | 主要内容 |
|---|---|---:|---:|---|

然后补充：

```text
合计：共 X 条视频，总时长 X 秒，约 X 分 X 秒，合计 X 个镜头。
```

使用计划中的视频段时长，不要猜最终剪辑时长。如果视频段包含内部计时镜头，则汇总这些时间块。
