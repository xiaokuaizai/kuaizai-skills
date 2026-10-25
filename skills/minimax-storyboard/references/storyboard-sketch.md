# 彩色分镜图 Brief

本文件是 `references/storyboard-workflow.md` 的下游输出规范，用于在 `Shot List` 与 `Minimax H3 Segments` 锁定后生成可视化分镜图。同一场景连续分镜的参考资产调用、场景扩展与连续性执行，需先遵循 `references/导演分镜连续制作行为规范.md`。

分镜图的 HTML 总表排版、段级拼接图生成、SVG 站位图绘制，详见 `references/故事板HTML制作规范.md`。本文件只规定单镜头分镜图的生成。

调用 `minimax-storyboard` 时必须使用本参考。阶段 D 必须为 `Shot List` 中的全部镜头生成独立彩色分镜图 brief 和单镜头 panel，不以用户是否单独提出分镜图要求为触发条件。

## 目的

彩色分镜图是视觉连续性检查，不是重新改写场景。它必须从已锁定的 `Shot List`、`Minimax H3 Segments` 和 `Continuity Bible` 中生成。

用分镜图验证：

- 人物站位和画面方向。
- 道具归属、手别、朝向和状态。
- 景别、机位和运镜意图。
- 重要情绪节拍和揭示。
- 视频段首帧/尾帧的连续性。

## 前置条件

开始制作彩色分镜图前，必须确认三类锚点已经完成：

1. **人物锚点**：已完成 `references/人物锚点.md` 要求的人物实体文件、基础三视图及服装衍生三视图校验。核心人物的身份、服装、情绪基线、画面侧位已锁定。
2. **场景锚点**：已完成 `references/场景锚点.md` 要求的全局户型图、子场景场景图生成与一致性校验。场景边界、连通关系、画面方向、光线、出入口规则已锁定。
3. **物品锚点**：已完成 `references/物品锚点.md` 要求的关键道具识别、三视图资产生成及状态变更版本管理。核心道具的归属、手别、朝向、状态已锁定。

未完成上述三类锚点前，不得进入彩色分镜图生成阶段。任何待生成镜头涉及尚未锚定的人物、场景或道具时，必须回到阶段 C 补充锚点、重新 QA 并取得用户确认，再生成对应分镜图。

## 覆盖规则

- `all-shots` 是唯一标准范围：`Shot List` 中每个镜头必须对应一张独立 9:16 彩色 panel。
- SEG 首帧、关键揭示、关键动作和交接高风险镜头已包含在全镜头范围内，不得以只生成这些镜头替代 `all-shots`。
- 连续性风险较高时，可以额外生成 `handoff-pairs` 交接对照图，但它们是全镜头 panels 之外的补充，不能抵扣任何镜头 panel。
- panel 数量必须与锁定 Shot 数量一致；任何缺失、失败或未通过 QA 的 panel 都会阻断阶段 D 确认和阶段 E HTML 制作。

## 连续分镜的前序 panel 引用

同一场景内连续相邻的 shot，生成 panel 时必须引用前序 panel 作为 continuity reference 与风格参考。

具体规则（可继承信息、使用红线、启用/禁用判断、声明模板、给生图模型的 prompt 写法）全部遵循 `references/导演分镜连续制作行为规范.md` 2.3 ~ 2.5 节与 2.4 节的声明模板。本文件不再重复。

引用方式：

- 将前序 panel 的 OSS public URL 加入当前 shot 的参考图列表。
- 在场景状态备忘中按 `references/导演分镜连续制作行为规范.md` 2.4 节模板完成声明。
- 给生图模型的 prompt 中只保留画面事实和必要的风格连续指令，不写流程声明。

## 导演分镜图格式

每个分镜图必须独立生成，格式要求如下：

- 画幅：`9:16 vertical`。
- 目标分辨率：`4K`，约 `2160x3840` 或更高质量的 9:16。
- 内容：只包含一个镜头的彩色视觉画面，不渲染中文说明、对白、镜头号、表格、`CAM` 标签或关系图。
- 风格：彩色导演分镜，保留清晰色彩与光影，可用克制强调色标出关键道具或效果；避免过度卡通化。

多个分镜图的 HTML 排版、段级拼接、站位图绘制、导演总表生成，详见 `references/故事板HTML制作规范.md`。

## 文字清晰度和版式稳定

图像生成对密集中文和精确版式不可靠。把生成图当作视觉分镜，而不是最终排版文档。

规则：

- 模块宁可少而大，不要多而挤。
- 图中只能放极短文字：模块标题、人物标签、`CAM`、方向箭头、1-2 个说明碎片。
- 清晰度重要时，避免在生成图中放完整句子。
- 不要要求图像模型渲染长制作说明、长对白、表格或精确镜头表。
- 各页模块版式保持一致：标题区、分镜图区、站位图区、说明区都固定。
- 标签词汇保持一致：`CAM`、`镜头方向`、`FOV`、`苏明舒`、`顾灵薇`、`青枝`、`沈昭昭`、`宫人`、`贵女`、`天机匣`。
- 如果中文可读性重要，先让图像模型生成少量标签或空白说明框，再用 HTML/SVG/PPT/图像编辑叠加准确中文标题和说明。不要依赖图像模型做最终文字排版。
- 如果生成图版式不一致或标签模糊，先拆成更多页面，而不是继续提高单图分辨率。

## 单镜头图验证与保存

每个镜头独立生成一张分镜图后，按以下规则验证和保存：

1. 将原始单镜头图保存到 `panels/` 目录，命名保留镜头 ID，例如 `panels/SH-01.png`、`panels/SH-02.png`。
2. 验证每张图只包含一个 9:16 镜头画面。若发现多格、拼接、分栏等异常，重新生成该镜头图。
3. 必要时保留一个 panel-check HTML 页面，仅用于快速检查全部单图，不作为最终导演总表。

推荐图像生成提示词结构（每个镜头单独调用一次）：

```text
Single colored storyboard panel, 9:16 vertical frame, 4K ultra-high-definition. [Shot size and camera angle]. [Character positions using screen-left/center/screen-right and depth]. [Main action or held pose]. [Important prop state]. [Lighting/mood]. No subtitles, no speech bubbles, no title text, no UI overlays, no watermark, no multiple panels, no storyboard sheet layout, no split frames.
```

不要要求图像模型渲染长正文、站位图、机位图或多格排版。每个 prompt 只生成一个镜头的画面。

后续的段级拼接、HTML 总表排版、SVG 站位图绘制，详见 `references/故事板HTML制作规范.md`。

## Brief 格式

除非用户要求其他格式，使用这个表：

| Sketch ID | Source | Panel Type | Composition | Characters | Props  | Camera | Continuity Purpose | Image Prompt |
| --------- | ------ | ---------- | ----------- | ---------- | ------ | ------ | ------------------ | ------------ |
| <br />    | <br /> | <br />     | <br />      | <br />     | <br /> | <br /> | <br />             | <br />       |

字段说明：

- `Sketch ID`：直接使用 `Shot List` 的稳定镜头 ID，例如 `SH-01`、`SH-02`，不再另建另一套编号。
- `Source`：镜头 ID 或视频段 ID，例如 `SHOT-03` 或 `SEG-02 first frame`。
- `Panel Type`：`首帧`、`尾帧`、`关键动作`、`反应`、`道具特写`、`空间重置` 或 `交接对照`。
- `Composition`：screen-left/center/screen-right 加 foreground/midground/background。
- `Characters`：外貌、服装、姿态、视线、情绪状态、相对距离。
- `Props`：归属、手别、位置、朝向、必要的剧情实物文字、状态。
- `Camera`：景别、机位角度、焦距、景深和运镜意图。
- `Continuity Purpose`：这张面板证明或保护什么。
- `Image Prompt`：用于彩色分镜图的简洁 prompt，不是精修剧照 prompt。

## 图像 Prompt 规则

写分镜图 prompt 时：

- 每个 prompt 必须只生成**一个独立镜头画面**。禁止在单张图里生成多个镜头、多格面板、上下分栏或 storyboard sheet。
- 保留源镜头的准确走位、服装、道具和机位。
- 除非用户要求精修概念图，否则要求 `single colored storyboard panel`、`color storyboard illustration`、`loose colored production thumbnail` 或 `simple colored storyboard`。
- 保持最终视频计划的画幅，通常是 `9:16 vertical`。
- 只包含可见视觉事实，不写隐藏动机或剧情解释。
- 避免加入会改变场景设计的装饰性风格词。
- 不引入字幕、对白气泡、标签、UI 叠加、标题卡或解释文字。
- 只有当 Minimax H3 视频提示词已批准且文字真实存在于画面道具上时，才允许剧情世界内的道具文字。
- 如果道具开口、刀刃方向、喷射路径、抛出物或机关经常生成反向，改用反向机位或角色 POV。把镜头放在受影响角色一侧，让“朝向镜头”等于“朝向受影响角色”。在 prompt 中明确说明这一点。

**禁止写法（会导致多格图）**：

- `multiple panels`、`3 panels`、`vertical stack`、`split into sections`、`storyboard sheet`、`comic page layout`
- `a sequence of frames`、`top/middle/bottom panels`
- 任何暗示一张图包含多个连续镜头的描述

推荐 prompt 形状：

```text
Single colored storyboard panel, 9:16 vertical frame. [Shot size and camera angle]. [Character positions using screen-left/center/screen-right and depth]. [Main action or held pose]. [Important prop state]. [Lighting/mood]. No subtitles, no speech bubbles, no title text, no UI overlays, no watermark, no multiple panels, no storyboard sheet layout.
```

## 反向机位修正

当图像模型在普通措辞后仍反复生成错误方向时，使用这个修正。

例子：

- 盒口必须朝向受害者，但模型总是让盒口朝向观众。
- 陷阱必须喷向脸，但模型把机关指向外侧。
- 刀刃、箭、飞纸、粉末喷射或视线方向指向了错误人物。

流程：

1. 把镜头移动到受影响角色一侧：过肩、肩后或近 POV。
2. 说明观众站在该角色一侧。
3. 用镜头逻辑定义方向：`盒口朝镜头 = 盒口朝顾灵薇`，因为镜头在顾灵薇身后。
4. 把另一个角色放在远处背景或对侧，以证明道具不是对准他们。
5. 当道具方向比完整展示物体更重要时，避免正面展示式镜头。

对于 `SH-06` 类型的机关盒节拍，优先使用：

```text
Camera is behind Gu Lingwei's shoulder, almost Gu Lingwei POV. Viewer stands on Gu Lingwei's side of the box. The box opening faces the viewer, therefore it faces Gu Lingwei. Su Mingshu stands opposite in the background, holding chestnuts and not touching the box. The hidden mechanism points from the box interior back toward Gu Lingwei/camera, not toward Su Mingshu.
```

## 分镜图 QA

交付分镜图 brief 前检查：

- 每张分镜图的来源都存在于镜头表或 Minimax H3 视频段列表中。
- 每张分镜图都是独立单镜头画面，没有多格、分栏、拼接或 storyboard sheet 版式。
- 分镜图没有改变人物画面侧位、距离、服装或道具归属。
- 如果道具是该面板存在的原因，关键道具必须可见。
- 每张站位图都包含镜头位置、镜头方向和近似 FOV；如果镜头运动，图中要显示运动方向。
- 对方向性道具或机关，镜头侧逻辑能证明道具朝向或目标是谁。
- 面板数量与声明范围一致。
- 图像 prompt 避免字幕和非剧情文字，且明确禁止多格版式。
- 同场景连续分镜按 `references/导演分镜连续制作行为规范.md` 2.2/2.5 节引用了前序 panel；首镜、场景切换/空间重置镜、三级特写镜的 `prev_frame_url` 为 `null`。
- `panel_generation_config.json` 中 `parallel_group` 与 `depends_on` 标注正确，不存在相互依赖的镜头被放入同一并行批次。
- 场景状态备忘中的五项声明（身份、目的、方式、位置、不用于什么）完整。
- 生图 prompt 中没有混入流程声明（如「参考图身份」「调用目的」「中低权重」等），也没有出现「沿用风格」「继承构图」等越界表述。
- 所有参考图（含前序 panel）的 public URL 已在 `doc/文件地址管理.md` 中登记。

如果分镜图暴露连续性问题，先修复镜头/视频段，再更新分镜图 brief。

## 阶段 D 生成配置字段

### 输入来源

阶段 D 读取以下已锁定文件生成 panel：

- `doc/镜头设计.md`：Shot List（`Shot ID`、`Scene`、`Duration`、`Shot Size`、`Camera`、`Blocking`、`Action`、`Props` 等）。
- `doc/视频分段.md`：SEG 结构与 shot 归属。
- `doc/视频生成内容检验.md`：每个 shot 的画面扩写、镜头时间轴、摄影与光线细节。
- `doc/文件地址管理.md`：人物/场景/道具参考图、前序 panel 的 public URL。
- `references/全局风格.md`：项目级美术基准。

### 输出配置

阶段 D 生成 panel 前，必须输出一份结构化生成配置，建议保存为：

```text
00_元数据/清单/panel_generation_config.json
```

配置为数组，每个 shot 一个对象，供调用 Image 2.0 的脚本读取。阶段 D 按 **Scene ID 分组生成**，每组内部再根据 shot 间的依赖关系划分**可并行批次**与**必须串行链**：

- **可并行**：同一场景内不依赖前序 panel 的镜头，包括首镜、场景切换/空间重置镜、三级特写镜、以及经判断无需继承前序人物状态/站位的独立镜头。这些 shot 可放入同一 `parallel_group` 同时调用生图模型。
- **必须串行**：需要引用前序 panel 作为 continuity reference 的连续相邻镜头。这类 shot 的 `depends_on` 必须填写前序 shot ID，且只有在前序 panel 已生成并上传 OSS、拿到 public URL 后，才能开始生成。
- 不同场景之间始终可并行。

配置至少包含以下字段：

```json
{
  "project": "项目名称",
  "scene_id": "SC-01",
  "shot_id": "SH-01",
  "shot_grade": "一级/二级/三级",
  "parallel_group": 1,
  "depends_on": null,
  "character_refs": [
    "人物三视图/服装三视图 OSS public URL"
  ],
  "scene_refs": [
    "基准场景图 OSS public URL"
  ],
  "prop_refs": [
    "道具图 OSS public URL"
  ],
  "prev_frame_url": "前序 panel 的 OSS public URL（同场景连续相邻时必填，用于人物连续性与美术风格一致性；首镜、场景切换/空间重置镜、三级特写镜设为 null）"
}
```

规则：

- `shot_grade` 按 `references/导演分镜连续制作行为规范.md` 第三章「镜头分级与场景参考动态匹配策略」判定，用于决定场景参考权重和是否触发场景扩展。
- `scene_refs`、`prop_refs`、`character_refs` 必须分开，不得全部塞进 `character_refs`。
- `parallel_group` 为同一批次可并行的整数编号；不同 `parallel_group` 之间必须等前一批全部完成上传并拿到 public URL 后，才能开始下一批。
- `depends_on` 填写本 shot 直接依赖的前序 shot ID（如 `SH-01`）；无依赖时设为 `null`。若 `depends_on` 不为 `null`，该 shot 不得与依赖目标放入同一 `parallel_group`。
- 生成脚本必须按 `parallel_group` 分批调度：同组内可并发调用生图模型，组间必须等待前序组完成上传并更新 `prev_frame_url`。
- `prev_frame_url` 在同场景连续相邻时必须填写前序 panel 的 **OSS public URL**；该 URL 必须已经真实上传并可访问。首镜、场景切换/空间重置镜、三级特写镜设为 `null`。
- 每生成一张 panel 后，必须立即上传 OSS、登记到 `doc/文件地址管理.md`、通过 QA，再进入下一批。
- 生成脚本必须能识别 `prev_frame_url` 字段，并将其作为中低权重 continuity reference 与风格参考传入。具体继承范围、红线、prompt 写法见 `references/导演分镜连续制作行为规范.md` 2.3 ~ 2.5 节与 2.4 节声明模板。

## 固定交付格式：单镜头独立生成

完整流程始终严格使用以下图像生成方式，不以用户是否额外指定版式为条件：

1. 按镜头表逐个独立生成彩色分镜图：每个镜头调用一次 Image 2.0，生成一张 9:16 单镜头图。禁止一张图生成多个镜头面板。
2. 将独立分镜图保存到 `panels/` 目录，命名保留镜头 ID，例如 `panels/SH-01.png`。
3. 同步输出 `*_director_full_table.md` 文字版镜头表。

后续的段级拼接图生成、HTML/SVG 导演总表排版、站位图绘制，严格按 `references/故事板HTML制作规范.md` 执行。

## Image 2.0 分镜图固定质量提示词

使用 Codex Image 2.0 生成分镜图时，必须把图像模型限制为“只生成单个镜头的视觉分镜画面”：不要要求模型生成中文说明、对白、镜头号、表格、`CAM` 标签、关系图或多格排版。所有文字、站位图、机位图都在 HTML/SVG 中确定性绘制。

每条 Image 2.0 分镜图 prompt 末尾固定追加以下质量约束：

```text
4K ultra-high-definition, clean and noise-free, no color spots or pixel artifacts, smooth and uniform texture, crisp and complete details, balanced colors, stable composition, sharp and well-defined subject, distinct background layers, natural and complete materials, smooth edges, no blur or distortion, no pixel corruption, no cracks or collapse, no excessive sharpening, normal emoji rendering, pure and flawless image quality.
```

同时在 prompt 中继续明确 `single colored storyboard panel`、`no text`、`no captions`、`no watermark`、`no speech bubbles`、`no multiple panels`、`no storyboard sheet layout`。
