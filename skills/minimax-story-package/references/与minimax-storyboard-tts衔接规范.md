# 与 minimax-storyboard-tts 衔接规范

本规范定义 TTS 音色资产进入 OSS 和 Minimax H3 资产包时的边界。

## 职责边界

- `/minimax-storyboard-tts`：识别人物与旁白、推荐音色、实际生成主选/备选音频、读取真实时长、人工确认最终样本。
- `/minimax-story-package`：登记、归档、上传已生成的音频，并在 SEG 打包时复核 Minimax 接口限制。
- `/minimax-storyboard`：估算正式对白/旁白文本时长，编写提示词时间轴，并指定每个声音身份使用哪个参考音频。

`/minimax-story-package` 不调用 TTS 接口，不选择音色，也不生成逐句正式对白或旁白音轨。

## 1. 试听音频

TTS 生成并自检候选样本后，如需远程试听，可上传为 `tts_preview`：

```bash
python scripts/register_outputs.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type tts_preview \
  --files "资产/支线1/TTS/samples/jiang_che_primary.mp3" \
          "资产/支线1/TTS/samples/narrator_alt_01.mp3" \
  --upload
```

`tts_preview` 只表示候选试听状态，不能直接进入 SEG 资产包。

## 2. 已确认参考音频

用户试听后，由 `minimax-storyboard-tts/scripts/select_reference_audio.py` 输出
`tts_reference_selection.json`。使用专用脚本直接消费该清单，避免手工抄写文件与 ID：

```bash
python scripts/register_tts_references.py \
  --selection "资产/支线1/TTS/tts_reference_selection.json" \
  --project 英语项目 \
  --branch 支线1 \
  --output-dir "00_元数据/清单" \
  --upload
```

登记 `tts_reference` 时会再次读取真实时长，并写入：

```json
{
  "duration_seconds": 7.2,
  "format": "mp3",
  "purpose": "voice_only",
  "content_binding": false
}
```

这一步是资产边界复核，不替代 TTS skill 的生成后自检。

## 3. SEG 资产包

`/minimax-storyboard` 根据该 SEG 出现的声音身份选择参考音频 ID：

```bash
python scripts/build_segment_asset_pack.py \
  --project 英语项目 \
  --branch 支线1 \
  --segment SEG-01 \
  --manifest-dir "00_元数据/清单" \
  --scene "airport_checkin" \
  --characters "jiang_che" "an_qi" \
  --first-frame-panel "SH-01" \
  --voice-refs "jiang_che_voice_ref" "narrator_voice_ref" \
  --output "00_元数据/清单/SEG-01_asset_pack.json"
```

打包脚本只接受真实上传成功的 `tts_reference`，并复核：

- 最多 3 段；
- 每段 2-15 秒；
- 总时长不超过 15 秒；
- 格式为 mp3/wav；
- public URL 存在；
- 固定标记 `purpose: voice_only`、`content_binding: false`。

参考样本不与 SEG 正式台词逐字匹配，也不与正式时间轴一一对应。人物对白和旁白的正式内容均由 Minimax H3 根据 prompt 生成。
