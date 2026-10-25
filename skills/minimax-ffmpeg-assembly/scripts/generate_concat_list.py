#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
generate_concat_list.py
生成 ffmpeg concat demuxer 所需的 list 文件。
"""

import argparse
from pathlib import Path


def generate_concat_list(video_paths: list[str], output_path: str) -> str:
    """根据视频路径列表生成 concat list 文件。"""
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        for path in video_paths:
            # ffmpeg concat 需要单引号包裹路径
            f.write(f"file '{path}'\n")
    return output_path


def main():
    parser = argparse.ArgumentParser(description="生成 ffmpeg concat list")
    parser.add_argument("--inputs", nargs="+", required=True, help="输入视频路径列表")
    parser.add_argument("--output", required=True, help="输出 list 文件路径")

    args = parser.parse_args()
    path = generate_concat_list(args.inputs, args.output)
    print(f"concat list 已生成: {path}")


if __name__ == "__main__":
    main()
