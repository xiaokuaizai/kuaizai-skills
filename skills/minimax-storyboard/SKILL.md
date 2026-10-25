---
name: minimax-storyboard
description: 将叙事剧本完整转换成可生产的 AI风格化3D动画动态漫画分镜包、单镜头彩色分镜图、HTML 导演总表、Minimax H3 视频分段提示词和 SEG 资产包。使用本 skill 必须执行 A-G 七阶段完整流程，不得因用户未单独要求而跳过分镜图、HTML 总表、故事板参考图或最终资产包。
---

本 skill 要求同时建立并维护三类锚点：

1. **人物锚点**（Character Anchoring）：身份、服装、情绪基线、画面侧位、人物标准三视图、服装衍生三视图、资产目录与溯源台账。详见 `references/人物锚点.md`。
2. **场景锚点**（Scene Anchoring）：场景边界、连通关系、画面方向、光线、出入口规则，以及场景图生成与一致性校验。详见 `references/场景锚点.md`。
3. **物品锚点**（Prop Anchoring）：关键道具状态、归属、手别、朝向、参考资产与状态版本管理。详见 `references/物品锚点.md`。

设计镜头和写 Minimax H3 视频提示词前，必须先把三类锚点写入 `Continuity Bible`。

此外，所有视觉产出（场景图、道具图、人物图、分镜图）还必须遵循项目目录中的 `references/全局风格.md`。该项目级文件是全项目最高优先级美术基准，优先级高于参考图与单条提示词的风格描述；当参考图风格与全局风格冲突时，以全局风格为准。

注意：本 Skill 自带的 `references/全局风格.md` 只是通用规则与示例库，不是具体项目的成品配置。阶段 A 必须将 `templates/project_global_style.md` 复制到任务目录的 `references/全局风格.md` 并填写真实项目值；不得直接把 Skill 参考文件当作项目配置使用。

# Minimax H3 分镜

## 核心工作流

使用这个 skill，把剧本转换成适合 Minimax H3 生成 AI风格化3D动画动态漫画视频的完整分镜包。

### 七阶段强制编排

本 skill 的唯一有效执行顺序是 A-G 七阶段。下方原有 1-15 步作为各阶段内部细则执行，不再允许从中挑选部分步骤。

| 阶段 | 核心范围 | 输入与前置依赖 | 对应下方细则 | 成本属性 | 阶段主要输出 |
|---|---|---|---|---|---|
| A | 需求、剧本/音频解析、资产盘点、文字版连续性与风格锁定 | 用户任务、源剧本、已有资产；无前序阶段 | 1-3 | C0-C1 | 项目契约、输入清单、资产需求矩阵、项目级 `references/全局风格.md`、`doc/前提设定.md` |
| B | Beat、Shot、时长、SEG、交接和镜头扩写锁定 | 阶段 A 输出、A 阶段 QA 通过、用户确认进入 B | 4-9、14 的生成前校验 | C1-C2 | `doc/镜头设计.md`、`doc/镜头内容检验.md`、`doc/视频生成内容检验.md`、`doc/视频分段.md` |
| C | 人物/场景/道具视觉锚点与 TTS 音色参考资产生成、复用、QA、登记与 OSS 入库 | 阶段 A 资产矩阵、阶段 B Shot/SEG、B 阶段 QA 通过、用户确认进入 C | 2 中的资产动作、三类锚点规范与 TTS 子流程 | C2-C4 | 视觉锚点（含 `scenes/` 目录下的 16:9 线稿布局图、同名 `.md` 文字描述、9:16 渲染图）、已确认 `tts_reference`、manifest、upload result、可用 public URL |
| D | 全部单镜头彩色分镜图 brief、生成、QA、登记与上传 | 阶段 B 锁定镜头、阶段 C 可用资产和 URL、C 阶段 QA 通过、用户确认进入 D | 10 | C2-C4 | `doc/分镜图方案.md`、`panels/`、panel manifest |
| E | HTML 导演总表、SVG 站位图、浏览器 QA、全部 SEG 故事板参考图和上传 | 阶段 B Shot/SEG、阶段 D 全部 QA 通过的 panels、用户确认进入 E | 11-12 | C2-C4 | HTML/Markdown 总表、SVG、`故事板参考图/`、上传结果 |
| F | 最终 H3 提示词、参考图拼接和 SEG 资产包 | 阶段 B `视频分段.md`/`视频生成内容检验.md`、阶段 C-E 全部资产与 manifest、E 阶段 QA 通过、用户确认进入 F | 15 | C1-C4 | 最终提示词、拼接图、`segment_asset_pack.json` |
| G | 内容、时间、连续性、视觉、资产、交付六层最终 QA | 阶段 A-F 全部产物、F 阶段 QA 通过、用户确认进入 G | 13-14 的最终回归校验 | C2-C4 | `doc/风险质检.md`、完整交付清单、`submit_ready` 状态 |

成本等级统一定义：C0 为读取和元数据检查；C1 为文本分析与规划；C2 为本地确定性计算、校验、HTML/SVG 和截图；C3 为可能产生费用的图片或音频生成；C4 为 OSS 上传、归档和 manifest 等外部状态；C5 为真实 Minimax H3 视频提交。A-G 标准流程只准备到 `submit_ready`，C5 必须取得单独的明确授权。

阶段 C 的音频部分必须调用 `/minimax-storyboard-tts`：先确认候选音色并取得付费生成授权，再生成和自检人物/旁白主选及备选样本，随后等待人工试听确认，最后由 `/minimax-story-package` 登记上传为 `tts_reference`。这两个 TTS 确认门禁不能被阶段 C 的一次确认替代；未得到已确认参考音频时，只能把对应 SEG 标为缺失或不使用 reference_audio，不能由 agent 擅自选择音色。

### 阶段确认门禁

每个阶段都必须严格执行：

```text
执行本阶段 -> 阶段 QA -> 向用户汇报 -> 停止并等待确认 -> 用户确认后进入下一阶段
```

1. 阶段完成后必须向用户汇报：阶段名称、输入、完成动作、输出文件/数据、成本属性、QA 结果、失败或残余风险、下一阶段将执行的动作。
2. 汇报末尾必须给出唯一明确的确认口令：`确认进入阶段 B/C/D/E/F/G`。阶段 G 汇报使用 `确认完成本次分镜流程`。
3. 未收到用户明确确认前，禁止进入下一阶段，也禁止提前执行下一阶段的图片生成、TTS、OSS 上传、HTML、截图、拼接或资产包动作。
4. 用户确认一次只放行一个阶段，不得把一次确认解释为连续放行后续多个阶段。
5. 用户要求修改当前阶段时，只修订当前阶段及受影响的已有上游数据；修订后重新 QA、重新汇报并再次等待确认，旧确认自动失效。
6. 如果下游发现上游错误，必须回退到产生问题的最低阶段；修复后从该阶段重新经过用户确认，不能沿用旧图片、旧 URL、旧 HTML 或旧资产包。

阶段汇报固定使用以下结构：

```markdown
## 阶段 X 完成汇报
- 输入：本阶段实际使用的源文件、上游数据和资产状态
- 完成动作：本阶段实际执行内容
- 输出：文件路径、数据数量和状态
- 成本：C0-C5 实际涉及等级；是否发生付费调用或外部写入
- QA：通过项、失败项、校验命令和结果
- 风险：残余风险、阻断项和回退位置；没有则写“无”
- 下一阶段：下一阶段将读取什么、生成什么、可能产生什么成本

请回复：确认进入阶段 X
```

其中 `X` 必须替换为下一个实际阶段字母；阶段 G 没有下一阶段，改为 `请回复：确认完成本次分镜流程`。

### 强制完整交付

一旦调用本 skill，以下项目全部属于标准必交付物，不存在“用户要求时才做”或“下游需要时才做”：

- 全镜头 `doc/分镜图方案.md` 和 `panels/` 单镜头彩色分镜图。
- `*_director_full_table.html`、对应 Markdown 导演总表和 SVG 站位图。
- 每个 SEG 的完整三栏故事板参考图及其登记、上传结果。
- 每个 SEG 的最终 Minimax H3 提示词、参考图/音频映射和 asset pack。
- 六层最终 QA 和完整交付清单。

只有 `*_director_full_table.png` 长图和独立拆出的 `blocking/*.svg` 可以作为附加输出；HTML 总表本身、HTML 内嵌 SVG 站位图和 SEG 故事板参考图不能省略。

1. 阅读源剧本，识别剧情节拍、场景边界、发言轮次、情绪反转、道具、地点，以及必须被观众看见的视觉信息。若源剧本包含对白、旁白、画外音或内心独白，先按 `references/旁白处理与时长预留规范.md` 提取 speech unit；**对白未标注说话人时必须依据上下文推断并补全，无法唯一推断则标记待确认**。再估算提示词中正式文本的发声时长；**对超长文本按语义规则拆分，生成 `doc/文本语义拆分表.md`，经人工抽查后再作为第一约束拆分镜头与视频段**；不得使用 TTS 参考样本的实际时长代替正式文本估算。
2. 设计镜头前，先建立文字版连续性设定：人物身份、服装、道具、空间地理、画面方向、视线、镜头轴线、起止站位，并在阶段 A 形成 `Continuity Bible` 和资产需求矩阵。人物三视图、场景图、道具图等视觉锚点资产在阶段 B 的 Shot/SEG 需求锁定并经用户确认后，于阶段 C 按实际需求生成或复用；未完成视觉锚点 QA 和准备前不得进入阶段 D 的单镜头画面生成。场景锚点必须遵循 `references/场景锚点.md` 的两级流程：先生成 16:9 线稿布局图（模式A为全局户型图，模式B为场景单元布局图）及同名 `.md` 文字描述，通过 QA 后再生成对应子场景/子活动区的 9:16 渲染图。任何生成或收到的参考图、音频都必须立即登记到 `doc/文件地址管理.md`；作为 Image 2.0 或 Minimax H3 输入的资产必须在调用前经 `/minimax-story-package` 上传并确认 public URL。
3. 阶段 A 复制并填写 `templates/project_global_style.md`，生成项目级 `references/全局风格.md`。锁定 `Continuity Bible` 前，必须按 Skill 通用规范 `references/全局风格.md` 第五章的冲突防控规则，填写项目配置第四、五章的分场景风格和过渡检查结果，并解决所有冲突项。配置缺失、仍有占位符或冲突未解决前不得进入镜头设计。
4. 按当前 AI风格化3D动画动态漫画节奏设计镜头：优先保证情绪清楚、动作可读、连续性稳定，而不是追求花哨覆盖。
5. 生成 `镜头内容检验`：为每个镜头列出 `Required Content`，按 `references/镜头内容检验规范.md` 反推 `Min Duration`。若 `Duration < Min Duration`，优先拆分镜头或延长时长，不要压缩关键信息。**如果镜头包含对白、旁白、画外音或内心独白，必须先完成语义拆分和时长估算，再填充 Required Content；禁止直接切分或修改原文。** 校验通过后再进入下一步。
6. 将镜头组合成 Minimax H3 视频段。每段 15 秒是硬上限；**目标区间 8-13 秒**；除非节拍确实需要，优先使用 8-13 秒。**每个 SEG 必须至少包含 2 个镜头**，以保证剪辑节奏和段级拼接图的信息量；不再允许单镜头 SEG。
7. 为每个视频段写连续性交接并锁定 SEG 结构：首帧锚点、尾帧锚点、延续道具、身体位置、视线方向、镜头关系和转场逻辑。
8. 生成 `视频生成内容检验`：在镜头和 SEG 结构锁定后，按 `references/视频生成内容检验规范.md` 为每个镜头做**画面扩写**与**镜头时间轴 / 运镜路线**。**画面扩写必须像人工分镜师一样逐镜头、逐时间块完成，不能一次性批量生成；这是一个缓慢但关键的过程，不得跳过或压缩。** 扩写必须在原 `Duration`、对白/旁白时间、剧情事实、核心动作和连续性不变的前提下，增加同一动作内部过程、摄影机运动、焦点/景别、人物细微表演、道具细节、空间纵深、光影和视觉节奏，解决画面静态、干巴的问题；禁止新增剧情事件、角色、道具、台词或改变动作结果。扩写结果回填到 `doc/视频分段.md` 的 SEG 提示词时间轴和 `doc/分镜图方案.md`。
9. 镜头方案内部一致后，在阶段 B 形成 Minimax H3 时间轴描述草案；最终提示词必须等阶段 E 的 HTML 和故事板参考图完成并经用户确认后，统一在阶段 F 写入实际参考资产和 public URL。
10. 阶段 D 必须为全部镜头创建彩色分镜图 brief 并生成单镜头图。生成前先确认阶段 C 的人物/场景/道具参考资产已经 `/minimax-story-package` 上传并拿到 public URL。阶段 D 按 **Scene ID 分组生成**，并在每组内部按「依赖关系」决定串并行：
    - **可并行**：同一场景内不依赖前序 panel 的镜头，包括首镜、场景切换/空间重置镜、三级特写镜、以及经判断无需继承前序人物状态/站位的独立镜头。
    - **必须串行**：同一场景内需要引用前序 panel 作为 continuity reference 的连续相邻镜头；每生成一张 panel 后必须立即调用 `/minimax-story-package` 上传并获得 public URL，下一张 shot 的 `prev_frame_url` 必须指向前一张已上传 panel 的 public URL。
    - 不同场景之间始终可并行。
    Agent 必须在生成前为每个 shot 判定依赖关系，输出 `panel_generation_config.json` 并标注 `parallel_group` 与 `depends_on`，禁止把有依赖关系的镜头放入同一并行批次。分镜图必须以锁定后的镜头方案和分段锚点为准；不要新增走位、道具、服装或机位。每个镜头独立调用一次 Image 2.0，生成一张 9:16 彩色视觉画面，禁止一次生成多格分镜图。生成时遵守 `references/场景锚点.md` 和 `references/导演分镜连续制作行为规范.md`；**同一场景内连续相邻的 shot，必须引用前序 panel 作为中低权重 continuity reference**（仅继承人物外形、服装、姿态和相对位置；不得约束场景透视、机位、取景范围）。**每次调用参考图（含前序 panel）都须先说明参考图身份、调用目的、使用方式与不用于什么**。所有单镜头图保存到 `panels/`，覆盖前先归档旧版，每张图生成并上传后立即登记；通过 `references/storyboard-sketch.md` QA 后，再进入下一张或下一阶段。
11. 单镜头图全部生成并验证通过后，必须进入 HTML 总表制作：基于 `templates/storyboard_seg_row_template.html`，按 `references/故事板HTML制作规范.md` 排版单镜头图、SVG 站位图与声音字段，并组装成 `*_director_full_table.html`。文字、站位图、机位图在 HTML/SVG 中确定性绘制，固定遵守 `references/storyboard-sketch.md` 的“固定交付格式：单镜头独立生成”和 `references/故事板HTML制作规范.md` 的总表排版规则。SVG 站位图生成后立即登记到 `doc/文件地址管理.md`。
12. HTML 总表通过浏览器 QA 后，必须运行 `scripts/capture_storyboard_refs.py` 将每个 SEG 行单独截图，输出到 `故事板参考图/`。命名格式为 `SEG-XX-故事板参考图.png`，必须包含完整三栏。若目标截图文件已存在，先归档旧版。截图完成后立即登记，再以 `storyboard_ref` 类型上传 OSS，获得 public URL 并记录。任何 SEG 缺少故事板参考图都不得进入阶段 F。
13. 定稿前，对照源剧本做内容 QA。检查剧情忠实度、因果逻辑、空间连续性、人物行为、提示词可生成性、分镜图可用性，以及 Minimax H3 幻觉风险。
14. Markdown 分镜是强制输出，因此阶段 B 生成前校验必须运行 `scripts/validate_storyboard.py <file_or_project_dir> --stage B`，阶段 G 最终回归校验必须运行 `scripts/validate_storyboard.py <file_or_project_dir> --stage G`，并修复脚本提示的时长或锚点问题。阶段 B 未通过不得进入阶段 C；阶段 G 未通过不得标记 `submit_ready`。Windows 下若路径包含空格，先将项目目录路径整体用双引号包住。
15. 准备 Minimax H3 提交包。进入阶段 F 前，必须先读取并核对以下全部输入：
    - `doc/视频分段.md`：锁定的 SEG 结构、每个 SEG 的 shots、Duration、首帧/尾帧锚点、连续性交接、Minimax H3 提示词时间轴草案。
    - `doc/视频生成内容检验.md`：每个镜头的画面扩写、镜头时间轴 / 运镜路线、摄影、光线、人物调度 / 道具状态。
    - `doc/导演总表.md`：最终文字版导演总表，用于核对镜头顺序和 SEG 归属。
    - `doc/分镜图方案.md`：全部镜头的 Storyboard Sketch Briefs 和对应分镜图规划。
    - `doc/文件地址管理.md`：全部已上传资产的 public URL，包括人物锚点、场景锚点、物品锚点、单镜头分镜图（panels/）、SEG 故事板参考图、TTS reference_audio 等。
    - `00_元数据/清单/` 下的 manifest 与 upload result：确认哪些资产已真实上传 OSS 并获得 public URL。
    - `references/Minimax-H3-最终提示词撰写规范.md`：最终提示词结构与参考图/音频使用规则。
    - `references/全局风格.md`：项目级美术基准，写入提示词时必须引用。
    - `doc/前提设定.md`：Continuity Bible，用于核对人物、场景、道具连续性。
    然后按 `references/Minimax-H3-最终提示词撰写规范.md` 选择本 SEG 需要的参考图，使用 `scripts/combine_reference_sheets.py`（`character` 模式拼人物，`prop` 模式拼道具）生成参考图拼接文件，若拼接输出文件已存在，先调用 `/minimax-story-package/scripts/archive_local_version.py` 归档旧版。撰写最终 Minimax H3 提示词（参考内容说明、风格说明、时间轴描述），并核对参考图 ≤5 张、参考音频 ≤3 段且总时长 ≤15 秒。选择参考图前必须先查看 `doc/文件地址管理.md`；生成拼接文件后，也要登记到 `doc/文件地址管理.md`。然后使用 `/minimax-story-package/scripts/build_segment_asset_pack.py` 读取已上传资产的 manifest，为每个 SEG 组装 reference_image / reference_audio URL 包。人物对白和旁白的正式内容都写在提示词时间轴中并由 Minimax H3 生成；reference_audio 只能从用户确认后的 `tts_reference` 中选择，只用于模仿音色、语速或气质，不与正式台词内容或 SEG 时间轴绑定。

## 参考文档加载

只加载当前任务需要的参考文档：

- `references/全局风格.md`：项目级全局美术配置，必须由 `templates/project_global_style.md` 复制并填写；规定本项目的核心风格、光影/色彩/材质体系、分场景适配和风格过渡结果。所有画面生成提示词必须强制引用，冲突未解决前禁止进入生成环节。
- `references/storyboard-workflow.md`：从剧本到镜头表、生成包的端到端转换流程。
- `references/minimax-h3-continuity.md`：Minimax H3 分段规则、15 秒上限、提示词连续性和跨段交接。
- `references/ai-drama-pacing.md`：AI风格化3D动画动态漫画的镜头数量、镜头时长、景别逻辑、镜头默认值和节奏建议。
- `references/sample-insights.md`：从用户历史示例和提示词中提炼的经验；用作校准，不要当成固定模板照抄。
- `references/content-qa.md`：生成后的内容层面检查；阶段 G 最终交付前必须加载并执行。
- `references/output-format.md`：要求的输出表格和字段名，包括 `Shot List` 的 `Required Content`、`Min Duration` 与 SEG 时长约束。
- `references/镜头内容检验规范.md`：镜头内容清单与最低时长反推规范，用于生成独立的 `doc/镜头内容检验.md` 阶段 B 门禁文件。
- `references/视频生成内容检验规范.md`：把锁定后的镜头转换为带时间轴的画面扩写方案，回填到 SEG 提示词与分镜图生成流程。
- `references/文件地址管理规范.md`：图片、参考图、音频等文件地址的登记规范。要求每生成或收到一个文件，立即更新 `doc/文件地址管理.md`。
- `references/storyboard-sketch.md`：强制彩色分镜图 brief 工作流，用于把全部锁定镜头转换成**单镜头**分镜面板提示词；阶段 D 必须加载并执行。内含同场景连续相邻分镜必须引用前序 panel 的规则。
- `references/故事板HTML制作规范.md`：导演故事板 HTML 总表的制作规范，包含单镜头图网格、行版式、SVG 站位图、声音字段位置、交付文件清单与 QA。配套模板见 `templates/storyboard_seg_row_template.html`。
- `references/transition-guide.md`：SEG 之间转场信息的填写规范，规定转场不是必需字段、应简短、不提前描述下一段内容；转场只写在 Markdown SEG 的 `Continuity Handoff` 字段中，HTML 尾帧只保留画面状态。
- `references/导演分镜表到故事板参考图.md`：HTML 总表定稿后，按 SEG 导出故事板参考图的命名、截图要求与 Playwright 脚本使用规范。
- `references/Minimax-H3-最终提示词撰写规范.md`：把 skill 已有资产（故事板参考图、人物/场景/物品锚点、全局风格）整理成 Minimax H3 最终提示词与参考文件包的规范，含 5 张参考图分配、人物拼接脚本、参考音频规则、提示词结构与示例。
- `../minimax-story-package/references/旧版归档规则.md`：图片、音频、拼接文件重制前的旧版归档规则。
- `references/场景锚点.md`：场景锚点规则与场景图生成规范，包含全局户型图、场景生成顺序、参考图调用、提示词约束、一致性校验及输出格式。
- `references/物品锚点.md`：物品锚点规则，包含关键道具识别、三视图资产生成、状态变更版本管理与调用规则。
- `references/人物锚点.md`：人物锚点与三视图资产管理规范，强制管理人物基础三视图、服装衍生版本、资产目录、实体文件与总台账。触发条件满足时必须执行，未完成前不得进入单镜头画面生成。
- `references/导演分镜连续制作行为规范.md`：同一场景连续导演分镜的参考资产权责、人物/场景参考调用红线及 Agent 固定执行步骤；**2.3 节规定同一场景连续相邻分镜必须引用前序 panel**。用于生成导演分镜图或连续分镜面板时保持人物、空间、机位一致性。
- `references/旁白处理与时长预留规范.md`：正式对白/旁白文本时长、语义拆分规则、SEG 切分，以及 TTS reference_audio 的职责边界。输入含人物发声或旁白时启用。
- `examples/storyboard_seg_examples.html`：独立的 SEG HTML 示例片段目录；仅用于复制结构和字段，不得直接作为生产总表或截图输入。

当用户提供样例剧本或样例分镜时，先检查样例，并阅读 `references/sample-insights.md`。推断临时风格画像：镜头密度、平均镜头时长、对白与动作比例、摄影词汇、分段结构。应用该风格时，仍必须遵守 Minimax H3 约束。

## 必须先做的决定

写最终分镜前，决定并说明会影响连续性的假设：

- 单集形式：竖屏短剧、横屏剧、广告、预告片或其他。
- 画幅和目标时长，如果用户没有提供。
- 主要人物和稳定视觉识别点。
- 场景地理和画面方向。
- 完整分镜包的任务目录、资产目录和 OSS 项目/支线映射；不得选择“只输出分镜表”或跳过最终提示词。
- 分镜图固定覆盖全部镜头；每个镜头必须有一张独立 9:16 彩色 panel。

如果信息缺失，做保守假设并放到 `Assumptions` 中，不要因此卡住。

## 连续性规则

维护稳定的空间模型：

- 追踪人物在画面中的 screen-left、center、screen-right，以及 foreground、midground、background。
- 除非有明确动机重建空间关系，否则保持 180 度轴线。
- 跨剪辑延续视线方向、身体朝向、手中道具、坐站状态、人物距离。
- 每个视频段的首帧和尾帧都要写到足够清楚，让 Minimax H3 只凭文字也能重建连续性。
- 避免让 Minimax H3 在同一段中完成太多同步变化；复杂动作拆成相邻视频段。

## 输出约定

除非用户要求其他格式，默认把文字产物输出到任务目录的 `doc/` 文件夹下：

1. `doc/前提设定.md`：`Assumptions` + `Continuity Bible`（人物/场景/道具锚点）。
2. `doc/镜头设计.md`：`Beat Map` + `Shot List`。
3. `doc/镜头内容检验.md`：每个镜头的 `Required Content`、`Min Duration`、锁定时长和通过状态。
4. `doc/文本语义拆分表.md`：对白/旁白/画外音/内心独白的语义拆分点、拆分理由、片段时长和人工抽查状态。
5. `doc/视频生成内容检验.md`：每个镜头的**画面扩写** + **镜头时间轴 / 运镜路线**，作为 Minimax H3 提示词时间轴和分镜图生成的依据。
6. `doc/视频分段.md`：`Minimax H3 Segments` + 每条 SEG 的最终提示词。
7. `doc/风险质检.md`：`Continuity Risk Checks` + `Content QA` + `Production Stats` + `Repair Notes`。
8. `doc/导演总表.md`：最终文字版导演总表。
9. `doc/文件地址管理.md`：图片、参考图、音频、站位图、故事板参考图、任务级脚本等文件路径登记表。每生成或收到一个文件，立即追加记录。
10. `doc/分镜图方案.md`：全部镜头的 `Storyboard Sketch Briefs`，强制输出。

项目级参考配置：

- `references/全局风格.md`：由阶段 A 从 `templates/project_global_style.md` 复制并填写的项目实际风格配置；后续所有视觉提示词必须引用此文件。

`doc/` 以外的产物：

- `panels/`：单镜头分镜图源图。
- `故事板参考图/`：每个 SEG 一张完整三栏故事板参考图，强制输出。
- `00_元数据/清单/`：资产 manifest、upload result 和每个 SEG 的 asset pack。
- `scripts/`：任务级脚本，按需分子目录管理（`capture/`、`upload/`、`convert/`、`qa/`）。
- `*_director_full_table.html`：可浏览导演总表。
- `*_director_full_table.png`：总表静态渲染长图（可选）。

最终输出要保持生产导向。除非用户询问，不解释基础影视术语。
