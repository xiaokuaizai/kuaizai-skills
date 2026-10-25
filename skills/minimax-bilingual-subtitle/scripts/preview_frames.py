# -*- coding: utf-8 -*-
"""抽帧验证：从烧录后的视频抽若干帧带字幕预览图。

输入：
  --video     原始完整视频路径（用于抽帧 + 叠加 ASS 字幕）
  --ass       ASS 字幕文件路径
  --times     抽帧时间点（逗号分隔，秒）
              默认：2,32,600
  --output    输出目录（默认 {workspace}/preview/）

输出：frame_t{N}s.png 多张
"""
import argparse
import subprocess
import sys
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description='抽帧验证：带字幕的预览帧')
    parser.add_argument('--video', required=True, help='原始完整视频路径')
    parser.add_argument('--ass', required=True, help='ASS 字幕文件路径')
    parser.add_argument('--times', default='2,32,600', help='抽帧时间点（逗号分隔，秒）')
    parser.add_argument('--output-dir', default=None, help='输出目录（默认 ASS 所在目录的 preview/）')
    args = parser.parse_args()

    video = Path(args.video)
    ass = Path(args.ass)
    out_dir = Path(args.output_dir) if args.output_dir else ass.parent / 'preview'
    out_dir.mkdir(parents=True, exist_ok=True)

    # 切到 ASS 所在目录，让 subtitles 滤镜用相对路径
    cwd = ass.parent
    ass_rel = ass.name

    times = [float(t.strip()) for t in args.times.split(',') if t.strip()]
    for t in times:
        out = out_dir / f'frame_t{int(t)}s.png'
        cmd = [
            'ffmpeg', '-y', '-v', 'error',
            '-ss', str(t), '-copyts', '-i', str(video),  # -copyts 保留原始时间戳让 ASS 时钟对齐
            '-vf', f'subtitles={ass_rel}',
            '-frames:v', '1',
            str(out),
        ]
        r = subprocess.run(cmd, cwd=str(cwd), capture_output=True, text=True,
                           encoding='utf-8', errors='replace')
        if r.returncode != 0:
            print(f'[FAIL] t={t}s: {r.stderr[:300]}')
        else:
            print(f'[OK] {out.name}')


if __name__ == '__main__':
    main()
