# -*- coding: utf-8 -*-
"""步骤 4：生成 ASS 双语字幕文件。

样式默认值（用户指定）：
  - 字幕整体在视频下方
  - 上行英文（大字体 36）+ 下行中文（小字体 26）
  - 字体：仿宋（FangSong）
  - 颜色：白色
  - 英文 MarginV=72 / 中文 MarginV=24（从底部往上算）

输入：
  --workspace     本 skill 工作区（含 subtitle_split.json）
  --output        输出 .ass 路径（默认 {workspace}/subtitle.ass）
  --video-width   视频宽度（默认 768）
  --video-height  视频高度（默认 1344）
  --en-size       英文字号（默认 36）
  --zh-size       中文字号（默认 26）
  --en-margin-v   英文底部边距（默认 72）
  --zh-margin-v   中文底部边距（默认 24）
  --font          字体名（默认 FangSong）

输出：{workspace}/subtitle.ass（utf-8-sig，Windows 播放器兼容）
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from common import read_json, fmt_ass_time, escape_ass_text


def main():
    parser = argparse.ArgumentParser(description='步骤 4：生成 ASS 字幕文件')
    parser.add_argument('--workspace', required=True, help='本 skill 工作区')
    parser.add_argument('--output', default=None, help='输出 .ass 路径（默认 workspace/subtitle.ass）')
    parser.add_argument('--video-width', type=int, default=768, help='视频宽度')
    parser.add_argument('--video-height', type=int, default=1344, help='视频高度')
    parser.add_argument('--en-size', type=int, default=36, help='英文字号')
    parser.add_argument('--zh-size', type=int, default=26, help='中文字号')
    parser.add_argument('--en-margin-v', type=int, default=72, help='英文底部边距')
    parser.add_argument('--zh-margin-v', type=int, default=24, help='中文底部边距')
    parser.add_argument('--font', default='FangSong', help='字体名')
    args = parser.parse_args()

    workspace = Path(args.workspace)
    output = Path(args.output) if args.output else workspace / 'subtitle.ass'
    subs = read_json(workspace / 'subtitle_split.json')

    # ASS 头部
    header = f"""[Script Info]
Title: bilingual_subtitle
ScriptType: v4.00+
PlayResX: {args.video_width}
PlayResY: {args.video_height}
WrapStyle: 0
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: English,{args.font},{args.en_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0.5,0,1,2,1,2,20,20,{args.en_margin_v},1
Style: Chinese,{args.font},{args.zh_size},&H00FFFFFF,&H000000FF,&H00000000,&H64000000,0,0,0,0,100,100,0.5,0,1,2,1,2,20,20,{args.zh_margin_v},1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""

    lines = [header]
    for s in subs:
        start = fmt_ass_time(s['actual_start'])
        end = fmt_ass_time(s['actual_end'])
        en = escape_ass_text(s['text_en'])
        zh = escape_ass_text(s['text_zh'])
        lines.append(f'Dialogue: 0,{start},{end},English,,0,0,0,,{en}\n')
        lines.append(f'Dialogue: 0,{start},{end},Chinese,,0,0,0,,{zh}\n')

    output.write_text(''.join(lines), encoding='utf-8-sig')
    print(f'已生成 {output.name}（{len(subs)} 条字幕 × 2 行）')
    print(f'文件大小：{output.stat().st_size} 字节')


if __name__ == '__main__':
    main()
