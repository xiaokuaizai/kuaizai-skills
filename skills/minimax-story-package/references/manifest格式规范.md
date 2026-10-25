# Manifest 格式规范

本规范定义 `/minimax-story-package` 生成的清单文件格式。

## 清单类型

| 文件名 | 用途 |
|---|---|
| `asset_manifest.json` | 记录某次解析/上传涉及的所有资产 |
| `upload_result.json` | 记录实际上传结果 |
| `segment_asset_pack.json` | 记录某个 SEG 的 Minimax H3 reference_image / reference_audio 包 |

## asset_manifest.json

```json
{
  "manifest_type": "asset_manifest",
  "generated_at": "2026-08-24T12:00:00+08:00",
  "project": "英语项目",
  "branch": "支线1",
  "assets": [
    {
      "id": "anqi_支线1_外出超市休闲装",
      "type": "character_costume_view",
      "local_path": "F:/AA_Company_project/.../安琪_支线1_外出超市休闲装.png",
      "filename": "安琪_支线1_外出超市休闲装.png",
      "oss_key": "video_workspace/英语项目/02_参考/支线/支线1/人物锚点/人物服装三视图/安琪_支线1_外出超市休闲装.png",
      "public_url": "https://getwallet.oss-cn-shenzhen.aliyuncs.com/lexilearnoss/video_workspace/英语项目/02_参考/支线/支线1/人物锚点/人物服装三视图/安琪_支线1_外出超市休闲装.png",
      "uploaded": false,
      "uploaded_at": null
    }
  ]
}
```

## upload_result.json

```json
{
  "manifest_type": "upload_result",
  "uploaded_at": "2026-08-24T12:05:00+08:00",
  "dry_run": false,
  "project": "英语项目",
  "branch": "支线1",
  "uploaded_count": 2,
  "failed_count": 0,
  "results": [
    {
      "id": "anqi_支线1_外出超市休闲装",
      "success": true,
      "local_path": "F:/...",
      "oss_key": "video_workspace/英语项目/...",
      "public_url": "https://getwallet.oss-cn-shenzhen.aliyuncs.com/...",
      "size": 1234567
    }
  ]
}
```

## segment_asset_pack.json

```json
{
  "manifest_type": "segment_asset_pack",
  "project": "英语项目",
  "branch": "支线1",
  "segment": "SEG-01",
  "built_at": "2026-08-24T12:10:00+08:00",
  "reference_images": [
    {
      "slot": 1,
      "label": "故事板参考图",
      "id": "SEG-01-storyboard-ref",
      "public_url": "https://getwallet.oss-cn-shenzhen.aliyuncs.com/..."
    },
    {
      "slot": 2,
      "label": "人物拼接参考图",
      "id": "SEG-01-characters",
      "public_url": "https://getwallet.oss-cn-shenzhen.aliyuncs.com/...",
      "note": "如需拼接多个人物，先运行 minimax-storyboard/scripts/combine_reference_sheets.py"
    },
    {
      "slot": 3,
      "label": "场景参考图",
      "id": "scene_br1_安琪家门口与邮箱",
      "public_url": "https://getwallet.oss-cn-shenzhen.aliyuncs.com/..."
    }
  ],
  "reference_audios": [
    {
      "slot": 1,
      "id": "jiangche_voice_ref",
      "public_url": "https://getwallet.oss-cn-shenzhen.aliyuncs.com/...",
      "duration_seconds": 7.2,
      "format": "mp3",
      "purpose": "voice_only",
      "content_binding": false
    }
  ],
  "reference_audio_validation": {
    "count": 1,
    "total_duration_seconds": 7.2,
    "status": "passed",
    "rules": "最多3段；每段2-15秒；总时长不超过15秒；仅参考音色"
  }
}
```

## 字段说明

| 字段 | 说明 |
|---|---|
| `id` | 资产唯一标识，建议用英文 slug 或中文原名 |
| `type` | 资产类型，见 `resolve_asset_paths.py` 支持的类型 |
| `oss_key` | OSS 对象键，不含 bucket 前缀 |
| `public_url` | 可直接作为图床 URL 使用的完整地址 |
| `slot` | Minimax H3 reference_image 的编号 1–5 |
| `uploaded` | 是否已完成 OSS 上传 |
| `duration_seconds` | reference_audio 的真实时长，由 ffprobe 在登记时读取 |
| `purpose` | 固定为 `voice_only`，表示只用于模仿音色、语速或气质 |
| `content_binding` | 固定为 `false`，表示参考样本内容不与正式台词或时间轴绑定 |

## 存储位置

清单文件统一存放到：

```
{本地项目目录}/00_元数据/清单/
```

或 OSS 上：

```
oss://getwallet/lexilearnoss/video_workspace/{项目名}/00_元数据/清单/
```
