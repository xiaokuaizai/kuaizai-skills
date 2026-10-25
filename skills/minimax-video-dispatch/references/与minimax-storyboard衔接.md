# 与 minimax-storyboard 衔接

> 本文件说明 `/minimax-video-dispatch` 如何从 `/minimax-storyboard` 和 `/minimax-story-package` 的产物中读取输入。

## 上游产物

进入 `/minimax-video-dispatch` 前，必须已经完成以下产物：

1. `doc/视频分段.md`：SEG 列表、每个 SEG 的时长、镜头归属。
2. `doc/视频生成内容检验.md`：每个 SEG 的画面扩写、时间轴、摄影与光线细节。
3. `*_director_full_table.html` 和 `doc/导演总表.md`：导演总表。
4. `00_元数据/清单/SEG-XX_asset_pack.json`：由 `/minimax-story-package` 的 `build_segment_asset_pack.py` 生成。
5. `references/全局风格.md`：项目级美术基准。

## 读取顺序

```text
1. 读取 doc/视频分段.md，获取 SEG 总数和顺序。
2. 读取 doc/导演总表.md，获取每个 SEG 的 prompt、首帧/尾帧锚点、台词、环境声。
3. 读取 00_元数据/清单/SEG-XX_asset_pack.json，获取 reference_image / reference_audio 的 public URL。
4. 按 SEG 组装 content 数组和请求体。
```

## asset pack 字段映射

`SEG-XX_asset_pack.json` 示例：

```json
{
  "project": "英语项目",
  "branch": "支线1",
  "segment_id": "SEG-01",
  "mode": "r2va",
  "duration": 5,
  "ratio": "9:16",
  "resolution": "2K",
  "prompt": "00:00-00:02: ...",
  "reference_images": [
    {"url": "https://...", "role": "reference_image", "description": "故事板参考图"},
    {"url": "https://...", "role": "reference_image", "description": "人物拼接参考图"},
    {"url": "https://...", "role": "reference_image", "description": "场景参考图"},
    {"url": "https://...", "role": "reference_image", "description": "道具参考图"},
    {"url": "https://...", "role": "reference_image", "description": "首帧分镜图"}
  ],
  "reference_audios": [
    {"url": "https://...", "role": "reference_audio", "description": "角色A音色", "duration": 6}
  ],
  "first_frame": "https://...",
  "last_frame": null
}
```

映射到 Minimax 请求体：

| asset pack 字段 | Minimax 请求体字段 |
|---|---|
| `prompt` | `content[0].text` |
| `reference_images` | `content[i].image_url` + `role=reference_image` |
| `reference_audios` | `content[i].audio_url` + `role=reference_audio` |
| `first_frame` | `content[i].image_url` + `role=first_frame` |
| `last_frame` | `content[i].image_url` + `role=last_frame` |
| `duration` | `duration` |
| `ratio` | `ratio` |
| `resolution` | `resolution` |
| `model` | 固定 `MiniMax-H3` |

## 模式推断

如果 asset pack 中没有 `first_frame`、`last_frame`、`reference_images`、`reference_audios`，则使用 `t2va`。

如果只有 `first_frame` 或 `last_frame`，则使用 `i2va`。

如果有 `reference_images`、`reference_audios` 或 reference_video，则使用 `r2va`。

## 首帧/尾帧来源

- `first_frame` 通常取 SEG 内第一个 shot 的 panel：`panels/SH-XX.png`。
- `last_frame` 通常取 SEG 内最后一个 shot 的 panel：`panels/SH-XX.png`。

## prompt 组装规则

1. 读取 `doc/导演总表.md` 中该 SEG 的时间轴描述。
2. 在开头追加 `references/全局风格.md` 中的风格说明。
3. 追加参考内容说明（Image/Audio 的身份、用途、不用于什么）。
4. 最终 prompt 作为 `content[0].text`。

## 输出回写

生成完成后，把结果回写到：

- `00_元数据/清单/video_generation_log.json`
- `doc/文件地址管理.md`
- `04_支线产出/产出/{branch}/分段视频/{segment}/`
