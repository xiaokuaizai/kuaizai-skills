# Minimax-H3-最终提示词撰写规范

> 本规范说明：当成品 `*_director_full_table.html` 已生成、`故事板参考图/` 已截图后，如何整理成最终提交给 Minimax H3 的提示词与参考文件包。
> 它负责把 skill 内已有资产（人物锚点、场景锚点、物品锚点、全局风格、故事板参考图）映射到 Minimax H3 的 reference_image / reference_audio 输入。

---

## 1. 阶段 F 必需输入

撰写最终 Minimax H3 提示词前，必须读取并核对以下全部输入：

| 输入 | 来源 | 用途 |
|---|---|---|
| SEG 结构与时间轴草案 | `doc/视频分段.md` | 确定每个 SEG 的 shots、Duration、首帧/尾帧锚点、连续性交接、提示词时间轴。 |
| 镜头画面扩写 | `doc/视频生成内容检验.md` | 把每个镜头的画面执行细节写入 SEG 提示词时间轴。 |
| 最终导演总表 | `doc/导演总表.md` | 核对镜头顺序、SEG 归属和关键连续性信息。 |
| 分镜图方案 | `doc/分镜图方案.md` | 核对每个 SEG 需要的单镜头分镜图（panels/）和关键帧选择。 |
| 全部资产 public URL | `doc/文件地址管理.md` | 获取人物锚点、场景锚点、物品锚点、panels、故事板参考图、TTS reference_audio 的可访问 URL。 |
| 上传清单 | `00_元数据/清单/*manifest.json`、`*upload_result.json` | 确认资产已真实上传 OSS，避免使用本地路径或无效 URL。 |
| 项目美术基准 | `references/全局风格.md` | 写入提示词风格说明，确保与项目整体美术一致。 |
| 连续性设定 | `doc/前提设定.md` 中的 `Continuity Bible` | 核对人物、场景、道具连续性，避免提示词与设定矛盾。 |
| 参考音频 | `03_TTS/参考音频/` 及已登记的 `tts_reference` | 为有人物对白/旁白的 SEG 选择音色参考，只参考音色不绑定内容。 |

以上输入缺一不可；若任一输入缺失或存在未上传资产，必须暂停阶段 F，回退到对应阶段补齐后再继续。

---

## 2. 提交前限制

- 参考图 ≤5 张；前 5 张免费，超出部分 **0.2 元/张**。
- 参考音频 ≤3 段；每段 2–15 秒，**总时长 ≤15 秒**。
- 输出视频时长：4–15 秒。
- 常见分辨率：2K / 768P。
- 画幅：默认 9:16。

---

## 3. 参考图分配（固定 5 张）

| 标签 | 内容 | 来源 | 作用 | 权重 |
|---|---|---|---|---|
| Image 1 | 故事板参考图 | `故事板参考图/SEG-XX-故事板参考图.png` | 整体构图、站位、机位意图 | 低 |
| Image 2 | 人物拼接参考图 | `scripts/combine_reference_sheets.py --mode character` 竖拼多个人物三视图 sheet | 锁定所有出场角色外貌与服装 | 高 |
| Image 3 | 场景参考图 | `场景锚点` 子活动区成品图 / 机位匹配场景图 | 锁定空间、光影、材质 | 中高 |
| Image 4 | 道具/风格参考图 | `物品锚点` 关键道具三视图；或全局风格参考画面；或本 SEG 需要的其他 panel | 锁定特写道具、风格或关键画面 | 中 |
| Image 5 | 首帧分镜图 / 备用 | `panels/SH-XX.png` 中本 SEG 首帧或其他关键单镜头图 | 精确控制开场画面或关键揭示 | 高 |

如果某 SEG 没有关键道具特写，Image 4 可替换为风格参考图，也可以只传 4 张。

阶段 F 选择参考图时，候选池包括：

- `故事板参考图/`：已截图的 SEG 三栏参考图。
- `refs/`：人物/场景/道具锚点图、拼接参考图。
- `panels/`：阶段 D 生成的单镜头分镜图。

按本 SEG 实际需要从中挑选 ≤5 张，不必填满 5 张，也不得超过 5 张。

---

## 4. 参考图拼接制作方法

skill 已有人物/道具锚点资产。为了把多张图合并成一张 reference_image 以节省额度，使用 `scripts/combine_reference_sheets.py`。

脚本基于 HTML 模板 + Playwright 截图，支持两种模式：

- `character`：人物竖排，左侧名字标签 + 右侧图片
- `prop`：物品 2 列网格，顶部名字标签 + 图片

模板文件位于 `templates/reference_character_sheet.html` 和 `templates/reference_prop_sheet.html`，可直接复制修改。

### 3.1 人物拼接

一个 SEG 需要多个人物时，把各人物的三视图 sheet 竖着拼成一张 Image 2：

```text
Image 2:
├─ 上半：安琪 服装三视图 sheet
└─ 下半：江彻 服装三视图 sheet
```

```bash
python scripts/combine_reference_sheets.py character \
  --input "人物锚点/人物服装三视图/安琪_支线11_休闲旅行装三视图.png" \
          "人物锚点/人物服装三视图/江彻_支线11_休闲旅行装三视图.png" \
  --names "安琪" "江彻" \
  --output "references_for_minimax/SEG-01_characters.png"
```

### 3.2 物品拼接

一个 SEG 有多个关键道具时，把道具三视图拼成一张 Image 4：

```bash
python scripts/combine_reference_sheets.py prop \
  --input "物品锚点/道具三视图/贝壳.png" \
          "物品锚点/道具三视图/安琪的包.png" \
          "物品锚点/道具三视图/江彻的背包.png" \
  --names "贝壳" "安琪的包" "江彻的背包" \
  --output "references_for_minimax/SEG-01_props.png"
```

脚本会自动：
1. 读取 HTML 模板并填入图片与名称；
2. 用 Playwright 无头截图；
3. 输出 2x 分辨率 PNG（默认 1024px 页面宽度，输出 2048px）。

---

## 5. 参考音频规则

- **人物与旁白使用同一套规则**：都从用户确认并以 `tts_reference` 上传的 TTS 样本中选择。
- reference_audio 只用于模仿音色、语速或气质，不参考其中的具体台词，也不与 SEG 的正式台词时间轴绑定。
- 人物对白和旁白的正式内容都必须逐字写入 prompt 时间轴，由 Minimax H3 在生成视频时完成；不得把 TTS 样本当作正式音轨，也不做 FFmpeg 后期旁白叠加。
- 每个 SEG 最多 3 段参考音频，每段 2–15 秒，格式为 mp3/wav，所有参考音频总时长 ≤15 秒；超过时必须重新选择或截取代表性片段。
- 提交前必须通过 asset pack 的格式、数量、单段时长和总时长校验。参考音频内容与正式台词不同不属于错误。

---

## 6. 提示词结构

最终提示词至少包含以下三个标题：

### 6.1 参考内容说明

逐条说明 Image/Audio/Video 的身份、位置、使用方式和不用于什么。

#### 素材编号规则（重要）

prompt 中所有素材引用必须严格对应 `content` 数组中同类型素材的出现顺序：

| 素材类型 | content 出现顺序 | prompt 引用名 |
|---|---|---|
| reference_image | 第 1 张 | `Image 1` |
| reference_image | 第 2 张 | `Image 2` |
| reference_image | 第 3 张 | `Image 3` |
| reference_image | 第 4 张 | `Image 4` |
| reference_image | 第 5 张 | `Image 5` |
| reference_audio | 第 1 段 | `Reference Audio 1` |
| reference_audio | 第 2 段 | `Reference Audio 2` |
| reference_audio | 第 3 段 | `Reference Audio 3` |
| reference_video | 第 1 段 | `Reference Video 1` |
| reference_video | 第 2 段 | `Reference Video 2` |

规则：

1. **编号只按同类型素材顺序计算**，不按整个 `content` 数组的全局位置计算。
2. **prompt 中的编号必须与 content 顺序严格对应**。例如 `Image 1` 必须指代 `content` 中第 1 个 `reference_image`。
3. **调整 content 顺序时，prompt 必须同步调整编号**。把人物图从第 2 位调到第 1 位，prompt 里的 `Image 2` 就要改成 `Image 1`。
4. 这是提示词工程实践，让模型清楚区分多素材分工，不是 API 强制校验字段，但必须保持内部一致。

#### 示例

```text
Image 1: SEG-01 故事板参考图。仅用于理解本段整体构图、人物站位和机位意图，不作为首帧、风格或人物外观的直接参考。
Image 2: 人物拼接参考图。上半为 A，中间为 B，下半为 C。用于锁定三位角色的外貌与服装，不用于场景风格。
Image 3: 场景参考图。机场航站楼值机区，用于保持空间、光影、材质一致。
Image 4: 道具参考图。用于锁定关键道具外观。
Image 5: 首帧分镜图。用于精确控制开场画面构图。
Reference Audio 1: A 的声线参考，只参考音色与语速，不参考台词内容。
Reference Audio 2: 旁白参考，只参考音色与节奏，具体旁白以本提示词文字为准。
Reference Video 1: 人物动作参考，用于保持角色动作范式。
Reference Video 2: 镜头运镜参考，用于保持运镜节奏。
```

### 6.2 风格说明

直接引用 `references/全局风格.md`：

```text
Style: AI风格化3D动画 / 青春冒险科幻悬疑。
Global baseline: 卡通渲染，电影级4K质感，柔和漫反射光影，低饱和莫兰迪色系。
This scene: 机场航站楼，冷灰疏离，顶光平光，明亮通透，低饱和克制。
```

### 6.3 时间轴视频描述

从 `00:00` 开始，按镜头写：

```text
00:00-00:03: 中景，A 站在画面右侧前景，B 站在画面左侧中景。A 对 B 说："我们得走了"。环境音：机场广播。
00:03-00:07: 近景 A，视线看向画面左侧 B，表情紧张。手中机票微微捏紧。...
```

每条时间块只写一个主动作 + 情绪，并包含：景别、机位、人物位置、对白、声音。

---

## 7. 避免项

```text
避免项：
固定避免项：不要生成对白字幕、标题字、解释字、旁白字卡、水印；对白只作为角色语音出现；已指定的道具文字可以保留。
本段特殊避免项：不要交换 A/B 站位；不要改变服装发型；不要增加额外人物；不要越轴。
```

---

## 8. 提交参数

```text
model: MiniMax-H3
duration: Xs (4-15)
resolution: 2K / 768P
aspect ratio: 9:16
```

---

## 9. 与相关文件的引用关系

- `references/全局风格.md`：风格说明来源。
- `references/人物锚点.md`：人物三视图 sheet 来源。
- `references/场景锚点.md`：场景参考图来源。
- `references/物品锚点.md`：道具参考图来源。
- `references/导演分镜表到故事板参考图.md`：故事板参考图生成方式。
- `references/output-format.md`：SEG 字段与编号规则。
- `scripts/combine_reference_sheets.py`：人物/物品参考图拼接脚本。
- `templates/reference_character_sheet.html`：人物拼接 HTML 模板。
- `templates/reference_prop_sheet.html`：物品拼接 HTML 模板。
