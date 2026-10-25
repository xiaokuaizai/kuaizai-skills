# -*- coding: utf-8 -*-
"""步骤 5：用 ffmpeg 把 ASS 字幕烧录到视频。

输入：
  --video    原始完整视频路径
  --ass      ASS 字幕文件路径
  --output   输出视频路径（默认 {workspace}/{name}_双语字幕.mp4）
  --duration 仅烧前 N 秒（用于生成样品；默认 None 全量）

输出：烧录后的 mp4（视频重新编码 + 音频 copy）

注意：
  - ffmpeg subtitles 滤镜在 Windows 下要用相对路径（避免 F: 盘符被识别为滤镜选项）
  - 本脚本会自动 cd 到 ASS 所在目录
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='步骤 5：ffmpeg 烧录字幕')
    parser.add_argument('--video', required=True, help='原始完整视频路径')
    parser.add_argument('--ass', required=True, help='ASS 字幕文件路径')
    parser.add_argument('--output', default=None, help='输出视频路径')
    parser.add_argument('--duration', type=float, default=None, help='仅烧前 N 秒（用于样品）')
    args = parser.parse_args()

    video = Path(args.video)
    ass = Path(args.ass)

    if args.output:
        output = Path(args.output)
    else:
        output = ass.parent / f'{video.stem}_双语字幕.mp4'

    # 切到 ASS 所在目录，让 subtitles 滤镜用相对路径
    cwd = ass.parent
    ass_rel = ass.name

    cmd = [
        'ffmpeg', '-y', '-v', 'warning', '-stats_period', '60',
        '-i', str(video),
    ]
    if args.duration:
        cmd.extend(['-t', str(args.duration)])
    cmd.extend([
        '-vf', f'subtitles={ass_rel}',
        '-c:a', 'copy',
        str(output),
    ])

    print(f'运行: {" ".join(cmd)}')
    print(f'cwd: {cwd}')
    r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print(f'[FAIL] ffmpeg 退出码 {r.returncode}')
        print(r.stderr[-2000:])
        sys.exit(1)

    # 校验时长
    probe = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'default=noprint_wrappers=1:nokey=1', str(output)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    duration = float(probe.stdout.strip())
    size_mb = output.stat().st_size / 1024 / 1024
    print(f'[OK] {output.name}')
    print(f'  时长: {duration:.2f}s / 大小: {size_mb:.1f} MB')


if __name__ == '__main__':
    main()
