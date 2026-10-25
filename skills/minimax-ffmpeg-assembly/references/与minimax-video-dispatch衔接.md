# 与 minimax-video-dispatch 衔接

> 本文件说明 `/minimax-ffmpeg-assembly` 如何从 `/minimax-video-dispatch` 的产物中读取输入。

## 上游产物

进入 `/minimax-ffmpeg-assembly` 前，`/minimax-video-dispatch` 必须已完成：

1. `00_元数据/清单/video_generation_log.json`：记录所有 SEG 的生成状态。
2. `04_支线产出/产出/{branch}/分段视频/{segment}/SEG-XX.mp4`：SEG 视频文件。

## 读取顺序

```text
1. 读取 00_元数据/清单/video_generation_log.json。
2. 过滤出 status == "succeeded" 且有 local_path 的 SEG。
3. 读取 doc/视频分段.md，建立 Scene → [SEG-XX] 映射。
4. 检查每个 SEG 的本地视频是否存在。
```

## 失败 SEG 处理

如果某个 SEG 状态不是 `succeeded` 或本地视频不存在：

1. 记录到失败列表。
2. 如果该 SEG 属于某个 Scene，该 Scene 标记为不可拼接。
3. 向用户汇报缺失 SEG，等待用户决定是否继续（跳过失败 Scene）。

## 状态流转

```text
minimax-video-dispatch
        │
        ▼
video_generation_log.json（succeeded）
        │
        ▼
minimax-ffmpeg-assembly
        │
        ├── 按 Scene 拼接 ──> 场次视频/
        │
        └── 按 Scene 顺序拼接 ──> 完整视频/
        │
        ▼
  用户确认
        │
        ▼
minimax-story-package（上传 OSS）
```

## 不处理的职责

`/minimax-ffmpeg-assembly` **不处理**：

- SEG 视频生成失败后的重试（属于 `/minimax-video-dispatch`）。
- 字幕生成与压制（属于现有的 `Tool/ffmpeg` skill 或字幕工作流）。
- 视频转码、调色、加转场等后期效果。
- OSS 上传与资产登记（属于 `/minimax-story-package`）。
