#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
build_video_prompts.py
从 minimax-storyboard 的产物中组装 Minimax H3 视频生成所需的 prompt 和 content。
"""

import argparse
import json
import re
from pathlib import Path


def load_json(path: str) -> dict:
    """读取 JSON 文件。"""
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_text(path: str) -> str:
    """读取文本文件。"""
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


def parse_director_table(md_path: str) -> dict:
    """
    从导演总表 Markdown 中提取每个 SEG 的信息。
    这里只做了简单的解析示例，实际格式以 doc/导演总表.md 为准。
    """
    text = load_text(md_path)
    segments = {}
    # 简单示例：按 SEG-XX 分段
    pattern = re.compile(r"## (SEG-\d+).*?(?=## SEG-\d+|\Z)", re.S)
    for match in pattern.finditer(text):
        seg_id = match.group(1)
        segments[seg_id] = match.group(0)
    return segments


def extract_segment_prompt(seg_text: str) -> str:
    """从 SEG 文本中提取时间轴视频描述。"""
    lines = []
    in_prompt = False
    for line in seg_text.splitlines():
        if "时间轴" in line or "视频描述" in line:
            in_prompt = True
            continue
        if in_prompt:
            if line.startswith("##") or line.strip() == "":
                continue
            lines.append(line.strip())
    return "\n".join(lines)


def build_asset_pack(
    project: str,
    branch: str,
    segment_id: str,
    director_table_path: str,
    manifest_dir: str,
    style_path: str,
    output_path: str,
) -> dict:
    """
    为单个 SEG 构建 asset pack。
    实际使用时应根据已有产物（导演总表、全局风格、参考图 URL）组装。
    """
    segments = parse_director_table(director_table_path)
    seg_text = segments.get(segment_id, "")
    timeline_prompt = extract_segment_prompt(seg_text)

    style_text = ""
    if Path(style_path).exists():
        style_text = load_text(style_path)

    # 组装最终 prompt
    prompt_parts = []
    if style_text:
        prompt_parts.append(f"Style:\n{style_text}")
    prompt_parts.append(timeline_prompt)
    final_prompt = "\n\n".join(prompt_parts)

    pack = {
        "project": project,
        "branch": branch,
        "segment_id": segment_id,
        "mode": "r2va",  # 默认多模态参考；实际应根据输入推断
        "model": "MiniMax-H3",
        "resolution": "2K",
        "duration": 5,
        "ratio": "9:16",
        "prompt": final_prompt,
        "reference_images": [],
        "reference_audios": [],
        "reference_videos": [],
        "first_frame": None,
        "last_frame": None,
    }

    # 这里可以读取 minimax-story-package 生成的参考图清单
    # 示例：从 manifest 中挑选前 5 张 reference_image
    # 实际应根据 build_segment_asset_pack.py 的输出

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(pack, f, ensure_ascii=False, indent=2)
    print(f"asset pack 已生成: {output_path}")
    return pack


def main():
    parser = argparse.ArgumentParser(description="组装 Minimax H3 视频生成 asset pack")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--branch", required=True, help="支线名称")
    parser.add_argument("--segment-id", required=True, help="SEG ID")
    parser.add_argument("--director-table", default="doc/导演总表.md", help="导演总表路径")
    parser.add_argument("--manifest-dir", default="00_元数据/清单", help="清单目录")
    parser.add_argument("--style", default="references/全局风格.md", help="全局风格文件路径")
    parser.add_argument("--output", help="输出 asset pack 路径")

    args = parser.parse_args()
    output = args.output or f"{args.manifest_dir}/{args.segment_id}_asset_pack.json"
    build_asset_pack(
        project=args.project,
        branch=args.branch,
        segment_id=args.segment_id,
        director_table_path=args.director_table,
        manifest_dir=args.manifest_dir,
        style_path=args.style,
        output_path=output,
    )


if __name__ == "__main__":
    main()
