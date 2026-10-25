# Minimax FFmpeg Assembly

## 核心作用

本 skill 是 `/minimax-video-dispatch` 的下游拼接层，负责把生成好的 SEG 视频：

1. **按 Scene 分组拼接**成场次视频。
2. **再按 Scene 顺序拼接**成完整支线视频。

使用 FFmpeg 的 `concat demuxer` + `-c copy` 硬切，保持原始规格。

## 触发条件

- `/minimax-video-dispatch` 已完成，所有 SEG 视频已成功下载到本地。
- 用户要求"拼接 Scene 视频"、"拼完整视频"或"开始后期拼接"。

## 前置条件

开始拼接前必须满足：

1. `doc/视频分段.md` 已存在，且 SEG 与 Scene 的对应关系明确。
2. `00_元数据/清单/video_generation_log.json` 已存在，所有待拼接 SEG 状态为 `succeeded`。
3. 每个 SEG 的本地视频文件存在：`04_支线产出/产出/{branch}/分段视频/{segment}/SEG-XX.mp4`。
4. 本机已安装 FFmpeg 并在 PATH 中可用。

任一条件不满足，禁止开始拼接。

## 拼接原则

1. **先 Scene，后完整**：必须先完成所有 Scene 视频，再拼完整支线视频。
2. **硬切过渡**：SEG 之间、Scene 之间均使用 `-c copy` 硬切，不加转场。
3. **原始规格**：保持 SEG 原始分辨率、码率、编码参数。
4. **严格模式**：如果 SEG 视频编码参数不一致，`-c copy` 会失败。此时停止拼接，向用户报告不一致的 SEG，不自动转码。
5. **先本地，后上传**：拼接产物先保留本地，等用户确认后再调用 `/minimax-story-package` 上传 OSS。

## 输出目录

```text
04_支线产出/
└── 产出/
    └── {branch}/
        ├── 分段视频/                    # 上游输入
        ├── 场次视频/                    # 本 skill 输出
        │   ├── Scene-01.mp4
        │   ├── Scene-02.mp4
        │   └── ...
        └── 完整视频/                    # 本 skill 输出
            └── {branch}_完整版.mp4
```

## 固定执行流程

```text
1. 读取 doc/视频分段.md，建立 Scene → [SEG-XX] 映射。
2. 读取 video_generation_log.json，确认所有 SEG 状态为 succeeded。
3. 检查每个 SEG 本地视频文件是否存在。
4. 检查所有 SEG 视频编码参数是否一致（分辨率、码率、编码器、像素格式）。
   - 不一致 → 停止，向用户报告。
5. 对每个 Scene 生成 concat list。
6. 调用 ffmpeg -f concat -safe 0 -i list.txt -c copy 拼接 Scene-XX.mp4。
7. 校验 Scene 视频时长是否等于各 SEG 时长之和。
8. 按 Scene 顺序生成完整支线视频 concat list。
9. 调用 ffmpeg 拼接完整支线视频。
10. 校验完整视频时长是否等于所有 SEG 时长之和。
11. 更新 scene_assembly_log.json 和 doc/文件地址管理.md。
12. 等待用户确认后，再调用 /minimax-story-package 上传。
```

## 核心脚本

- `scripts/generate_concat_list.py`：生成 ffmpeg concat list 文件。
- `scripts/assemble_scenes.py`：按 Scene 拼接。
- `scripts/assemble_full_branch.py`：拼完整支线视频。
- `scripts/validate_assembly.py`：校验输出视频时长和编码一致性。

## 参考文档

- `references/拼接规则.md`
- `references/场景与完整视频拼接.md`
- `references/产物管理规范.md`
- `references/与minimax-video-dispatch衔接.md`
