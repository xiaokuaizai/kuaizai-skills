---
name: minimax-storyboard-tts
description: 从剧本中提取旁白和对话角色，自动推荐火山引擎 TTS 音色并生成音色总表；用户确认后生成主选+备选试听样本，并将选定样本作为 Minimax H3 音色参考。TTS 不生成正式台词音轨。
---

> **安全提示**：本 skill 目录下的 `tools/volc-tts/.env` 包含火山引擎 API 密钥，仅限本地个人使用。禁止将本 skill 目录上传 Git、网盘或分享给他人。

# Minimax Storyboard TTS

## 核心作用

把剧本转换成 Minimax H3 可用的音色参考资产规划：

1. 读取用户提供的剧本文件（Markdown）。
2. 识别旁白（`【Narration】`）和对话角色。
3. 根据角色类型自动推荐主选 + 2-3 个备选音色。
4. 生成 `TTS音色总表.md` 草案。
5. 用户确认候选音色表后，实际调用 TTS 为每个人物和旁白生成主选 + 备选试听音频。
6. 生成后读取真实时长并检查格式、可解析性及是否满足 reference_audio 单段 2-15 秒限制。
7. 用户试听并确认最终音色后，生成 `tts_reference_selection.json`，再交给 `/minimax-story-package` 上传。

人物和旁白遵循同一契约：TTS 样本只用于试听和提供音色参考；人物对白、旁白的正式内容均由 Minimax H3 根据 storyboard prompt 生成。样本文本不承担正式台词内容，不需要与任何 SEG 或正式时间轴一致。

## 触发条件

当用户请求以下任一内容时启用本 skill：

- "给这个剧本做 TTS 音色表"
- "生成旁白/对话的音色总表"
- "选一下这个角色用什么音色"
- "生成 TTS 样本"
- 用户提供剧本文件路径，并提到 TTS、音色、配音、旁白等关键词

## 必须先拿到两个输入

1. **剧本文件路径**：例如 `11_机场旅行/纯英文版.md`（相对工作空间）或绝对路径。
2. **资产目录路径**：例如 `F:/AA_Company_project/AA_main/Lexi/Media/Append/资产`。所有输出（音色表、样本音频）都放在这里。

如果用户只给了一个路径，询问另一个是哪个。

## 输出目录结构

假设资产目录为 `资产/`，剧本为 `11_机场旅行/纯英文版.md`：

```text
资产/
└── 11_机场旅行/
    └── TTS/
        ├── TTS音色总表.md
        └── samples/
            ├── jiang_che_primary.mp3
            ├── jiang_che_alt_01.mp3
            ├── jiang_che_alt_02.mp3
            ├── an_qi_primary.mp3
            └── ...
```

音色总表中记录的路径统一使用**资产目录相对路径**，例如：

```text
11_机场旅行/TTS/samples/jiang_che_primary.mp3
```

## 工作流

### 阶段一：生成音色总表草案

1. 读取剧本，识别所有 `【Narration】` 段落，统一归为 `narrator` 角色。
2. 读取剧本中的对话，通过 `"..." X said/asked/replied` 等模式推断角色名。
3. 如果某句对话无法推断角色，列出存疑列表询问用户，不要瞎猜。
4. 根据角色性别、年龄、语言推断角色类型（详见 `references/TTS音色选择规范.md`）。
5. 从内置推荐表中为每个角色挑选 1 个主选 + 2-3 个备选音色。
6. 为每个角色从剧本中挑选一句 7-8 秒以内的台词作为样本文本。
   - 优先选最长但不超过 20 个英文单词（或约 25 个汉字）的一句。
   - 太长时在语义断点截断；太短时拼接 2-3 句连续台词。
7. 生成 `TTS音色总表.md` 到 `资产/{场次名}/TTS/` 下。
8. 展示表格给用户，等待确认或修改。

### 阶段二：确认候选音色并授权生成

- 用户可以直接修改 `TTS音色总表.md` 文件，然后回复 "确认"。
- 也可以回复 "把 Jiang Che 改成 XXX 音色" 之类的指令，由 skill 代为修改。
- **实际 TTS 调用会产生费用，必须得到用户明确确认后，才能进入阶段三。**

### 阶段三：生成样本音频

1. 读取确认后的 `TTS音色总表.md`。
2. 对表中每个角色，依次生成：
   - 主选音色样本：`{role_key}_primary.mp3`
   - 备选音色1：`{role_key}_alt_01.mp3`
   - 备选音色2：`{role_key}_alt_02.mp3`
   - 如有备选3：`{role_key}_alt_03.mp3`
   生成每个样本前，若目标文件已存在，先调用 `/minimax-story-package/scripts/archive_local_version.py` 按 `../minimax-story-package/references/旧版归档规则.md` 归档旧版。
3. 每个样本调用 `tools/volc-tts/src/config.py` 中的火山引擎 V1 HTTP 接口。
4. 每个样本生成后立即用 ffprobe 读取实际时长，记录格式、时长、解析状态和 `reference_eligible`；2-15 秒且可正常解析的样本才可进入人工确认。
5. 把样本路径回填到音色总表的「样本文件」列，并写出 `sample_generation_result.json`。试听样本如需远程试听，可调用 `/minimax-story-package` 以 `tts_preview` 类型上传。
6. 汇总生成结果：成功数、失败数、实际时长、可作为参考音频的样本数和输出目录。

### 阶段四：人工试听并确认 reference_audio

1. 用户试听人物和旁白的主选/备选样本，并明确每个声音身份采用哪个样本；未确认不得自动选主选。
2. 运行 `scripts/select_reference_audio.py`，从 `sample_generation_result.json` 中选择已通过自检的样本，生成 `tts_reference_selection.json` 并回填音色总表。
3. 每个声音身份只能确认一个参考样本。项目可确认多个声音身份，但单个 SEG 最终选择的 reference_audio 数量和总时长由 `/minimax-story-package` 在打包时复核。

### 阶段五：登记并上传参考音频

1. 根据 `tts_reference_selection.json`，调用 `/minimax-story-package/scripts/register_tts_references.py`，以 `tts_reference` 类型登记并上传人物和旁白参考样本；不要手工重抄文件与 ID。
2. 上传前若本地或 OSS 上已存在同名参考音频，按 `../minimax-story-package/references/旧版归档规则.md` 归档旧版。
3. 运行 `scripts/sync_reference_urls.py`，把真实上传结果中的 public URL 回填到 `TTS音色总表.md`，并同步登记到 `doc/文件地址管理.md`；始终标记“只参考音色，不绑定内容”。
4. 本 skill 到 `tts_reference` 交接完成即结束，不生成逐句人物或旁白正式音轨；正式对白和旁白由 Minimax H3 根据提示词生成。

## 样本长度控制

- 目标：7-8 秒以内。
- 估算：英文 10 词约 4 秒；中文 10 字约 2.2 秒。
- 超过上限时优先截断到完整句子末尾；仍过长则截断到语义断点（逗号、分号）。
- 不超过下限不强制补齐，自然长度即可。
- 少于 2 秒的样本仍可用于试听，但脚本会标记为不能直接用作 Minimax reference_audio。

## 路径约定

- 所有写入文件的路径使用**资产目录相对路径**。
- 脚本内部使用绝对路径操作文件，但写入 Markdown 时转换为相对路径。
- `tools/volc-tts/` 内部路径保持其原有约定，skill 通过调用其 `src/config.py` 复用凭证。

## 参考文档

按当前任务需要加载：

- `references/旁白处理与时长预留规范.md`：TTS 音色样本与 storyboard 正式文本时长的职责边界。
- `references/TTS音色选择规范.md`：角色类型、默认音色推荐、语速建议。
- `references/TTS音色总表模板.md`：输出文件模板。
- `tools/volc-tts/doc/音色列表.md`：完整火山引擎音色列表（候选库）。
- `../minimax-story-package/references/旧版归档规则.md`：试听样本、参考音频重制前的旧版归档规则。

## 常用命令

生成音色总表（阶段一），假设当前目录为工作空间根目录：

```bash
cd ".claude/skills/minimax-storyboard-tts"
python scripts/build_voice_table.py \
  --script "11_机场旅行/纯英文版.md" \
  --assets "../../资产" \
  --workspace "../.."
```

生成样本音频（阶段三）：

```bash
cd ".claude/skills/minimax-storyboard-tts"
python tools/generate_samples_from_table.py \
  "../../资产/11_机场旅行/TTS/TTS音色总表.md"
```

人工试听后确认参考音频（阶段四）：

```bash
python scripts/select_reference_audio.py \
  --result "../../资产/11_机场旅行/TTS/sample_generation_result.json" \
  --select "jiang_che=primary" \
  --select "narrator=alt_01"
```

真实上传后回填 URL（阶段五）：

```bash
python scripts/sync_reference_urls.py \
  --selection "../../资产/11_机场旅行/TTS/tts_reference_selection.json" \
  --upload-result "../../00_元数据/清单/tts_reference_upload_result.json"
```

> 路径可根据实际工作空间结构调整。`--workspace` 用于计算音色表中的相对路径；`--skill-root` 用于生成使用说明中的命令。

## 输出约定

默认返回：

1. `角色识别结果`：识别出的旁白和对话角色清单。
2. `TTS音色总表.md`：已写入文件的路径。
3. 用户授权生成后：`sample_generation_result.json`（成功/失败、实际时长、是否可作为 reference_audio）。
4. 用户试听确认后：`tts_reference_selection.json`（人物/旁白与已确认样本的映射）。
5. 上传后：参考音频 OSS public URL。

## 限制与注意事项

1. 本 skill 只处理 Markdown 剧本。其他格式请先转换为 Markdown。
2. 角色识别依赖 `X said/asked/replied` 等英文标签或中文对话格式。如果剧本没有这些标签，需要用户手动补充角色名。
3. 实际调用 TTS 会产生 API 费用。生成样本前必须得到用户确认。
4. 如果某个音色生成失败（例如账号无权限），记录失败原因并继续生成其他样本。
5. 样本音频不会自动复制到其他位置，统一放在 `资产/{场次名}/TTS/samples/` 下。
