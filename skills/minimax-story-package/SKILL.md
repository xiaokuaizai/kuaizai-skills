---
name: minimax-story-package
description: 管理 /minimax-storyboard 与 /minimax-storyboard-tts 生成资产的 OSS 路径解析、上传与归档。在生成前提供统一的本地路径 + OSS key + public URL，在生成后将产物归档到 oss://getwallet/lexilearnoss/video_workspace/ 的固定目录结构中。
---

# Minimax Story Package

## 核心作用

本 skill 是 `/minimax-storyboard` 与 `/minimax-storyboard-tts` 的**资产管理中间层**：

1. **生成前**：为参考图/音频解析本地路径、OSS key、public URL。
2. **生成中**：被其他 skill 阅读或调用，确保所有产物都有预定的存放位置。
3. **生成后**：把产物上传到 OSS，更新清单，为 Minimax H3 提交包组装 reference_image / reference_audio。

音频生成、音色推荐和人工选样属于 `/minimax-storyboard-tts`；本 skill 不调用 TTS 接口，只接收已经生成并确认的音频文件。

## 触发条件

以下任一情况启用本 skill：

- `/minimax-storyboard` 需要调用 速创APIimage2.0 生成分镜图、场景图、人物图前。
- `/minimax-storyboard-tts` 生成试听样本或确认 reference_audio 后。
- 用户要求"把产物归档到 OSS"、"生成 OSS 资产包"、"准备 Minimax H3 提交包"。
- 用户要求统一管理视频工作区的 OSS 目录。

## 必须先拿到四个输入

1. **项目名称**：例如 `英语项目`、`南极星`。
2. **支线名称**：例如 `支线1`、`主线`。
3. **资产类型**：见下方支持的类型。
4. **本地文件路径**：要上传或解析的本地文件。

## 支持的资产类型

| 类型 | OSS 目录 | 说明 |
|---|---|---|
| `character_base_view` | `02_参考/支线/{branch}/人物锚点/人物三视图/` | 人物标准三视图 |
| `character_costume_view` | `02_参考/支线/{branch}/人物锚点/人物服装三视图/` | 人物服装衍生图 |
| `scene_anchor` | `02_参考/支线/{branch}/场景锚点/` | 场景锚点图 |
| `prop_anchor` | `02_参考/支线/{branch}/物品锚点/` | 物品锚点图 |
| `storyboard_panel` | `02_参考/支线/{branch}/分镜图/` | 单镜头分镜图 |
| `storyboard_ref` | `02_参考/支线/{branch}/故事板参考图/` | SEG 故事板参考图 |
| `style_ref` | `02_参考/主线/风格参考/` | 全局风格参考图 |
| `tts_preview` | `03_TTS/试听音频/` | 试听样本音频 |
| `tts_reference` | `03_TTS/参考音频/` | 人物/旁白统一使用的 reference_audio，只参考音色，不绑定内容 |
| `output_full_video` | `04_支线产出/产出/{branch}/完整视频/` | 支线完整视频 |
| `output_segment_video` | `04_支线产出/产出/{branch}/分段视频/{segment}/` | SEG 完整视频 |
| `output_shot_video` | `04_支线产出/产出/{branch}/分段视频/{segment}/镜头视频/` | 分段内镜头视频 |
| `test` | `TEST/{date_desc}/` | 测试/无关碎片 |

## 核心脚本

### 1. resolve_asset_paths.py

解析本地文件对应的 OSS 路径和 public URL。

```bash
python scripts/resolve_asset_paths.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type character_costume_view \
  --files "资产/人物锚点/支线1/安琪_支线1_外出超市休闲装.png" \
  --ids "anqi_支线1_外出超市休闲装" \
  --output "00_元数据/清单/2026-08-24_asset_manifest.json"
```

### 2. upload_assets.py

读取 manifest，上传文件到 OSS。

```bash
# 先 dry-run 检查
python scripts/upload_assets.py \
  --manifest "00_元数据/清单/2026-08-24_asset_manifest.json"

# 真实上传
python scripts/upload_assets.py \
  --manifest "00_元数据/清单/2026-08-24_asset_manifest.json" \
  --upload
```

### 3. register_outputs.py

一步完成产物解析 + 上传。

```bash
python scripts/register_outputs.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type storyboard_panel \
  --files "panels/SH-01.png" "panels/SH-02.png" \
  --upload
```

### 4. register_tts_references.py

只消费 `/minimax-storyboard-tts` 人工确认后的 `tts_reference_selection.json`，自动提取人物/旁白参考文件和 ID，避免手工抄写映射：

```bash
python scripts/register_tts_references.py \
  --selection "资产/支线1/TTS/tts_reference_selection.json" \
  --project 英语项目 \
  --branch 支线1 \
  --output-dir "00_元数据/清单" \
  --upload
```

### 5. archive_local_version.py

在生成新版文件之前，把已存在的旧版文件归档到同目录的 `旧版/` 文件夹，并添加版本号与说明。

```bash
python scripts/archive_local_version.py \
  --file "panels/SH-01.png" \
  --reason "人物服装不一致，重新生成"
```

### 6. build_segment_asset_pack.py

为某个 SEG 组装 Minimax H3 的 reference_image / reference_audio 包。`--voice-refs` 只接受已确认并真实上传的 `tts_reference` ID；脚本复核最多 3 段、单段 2-15 秒和总时长不超过 15 秒，不检查样本内容是否等于正式台词。

```bash
python scripts/build_segment_asset_pack.py \
  --project 英语项目 \
  --branch 支线1 \
  --segment SEG-01 \
  --manifest-dir "00_元数据/清单" \
  --scene "scene_br1_安琪家门口与邮箱.png" \
  --characters "jiangche_day_visit" "anqi_day_apron" \
  --voice-refs "jiangche_voice_ref" "narrator_voice_ref" \
  --first-frame-panel "SH-01" \
  --output "00_元数据/清单/SEG-01_asset_pack.json"
```

## 旧版归档规则

重新生成某张图片/音频时，旧版本按以下规则归档：

1. **本地归档**：在旧文件所在目录创建 `旧版/` 文件夹，把旧文件移入并改名为 `{原文件名}_旧版v{N}.{扩展名}`。
2. **OSS 归档**：`upload_assets.py` 上传时若检测到同名对象已存在，会自动将其复制到同前缀的 `旧版/` 路径，并改名为 `{原文件名}_旧版v{N}.{扩展名}`，然后删除原对象。
3. **说明文件**：本地与 OSS 的 `旧版/` 目录中都会维护一个 `说明.txt`，记录每次归档的时间、原文件名、新版本文件名和归档原因。
4. **版本号**：从 v1 开始递增，已存在 `v1` 时新归档为 `v2`，以此类推。
5. **调用时机**：生成新版之前先调用 `archive_local_version.py` 归档本地旧版；上传时由 `upload_assets.py` 自动处理 OSS 旧版。

## 凭证配置

本 skill 统一从 `.env` 读取 OSS 凭证：

```bash
cp .env.example .env
# 编辑 .env 填写真实值
```

```text
OSS_ACCESS_KEY_ID=your_access_key_id
OSS_ACCESS_KEY_SECRET=your_access_key_secret
OSS_REGION=oss-cn-shenzhen
OSS_BUCKET=getwallet
PUBLIC_BASE_URL=https://getwallet.oss-cn-shenzhen.aliyuncs.com
```

**安全提示**：`.env` 文件禁止上传 Git、网盘或分享给他人。

## 与相关 skill 的协作

- `/minimax-storyboard`：在生成分镜图、故事板参考图、准备 Minimax H3 提交包时调用本 skill。
- `/minimax-storyboard-tts`：在生成试听样本、确认并上传人物/旁白参考音频后调用本 skill 归档。
- `/minimax-storyboard` 的 `scripts/combine_reference_sheets.py`：用于把多个人物参考图拼接成一张 Image 2。

## 输出约定

默认返回：

1. `asset_manifest.json`：本次解析的资产清单。
2. `upload_result.json`：实际上传结果。
3. `segment_asset_pack.json`：某个 SEG 的 reference_image 建议包。

所有清单默认保存到本地 `00_元数据/清单/` 目录。

## 参考文档

- `references/oss目录结构规范.md`
- `references/资产生命周期规范.md`
- `references/旧版归档规则.md`
- `references/与minimax-storyboard衔接规范.md`
- `references/与minimax-storyboard-tts衔接规范.md`
- `references/manifest格式规范.md`
