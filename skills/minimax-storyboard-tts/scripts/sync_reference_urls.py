#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把 package 的 tts_reference 上传结果回填到 TTS 音色总表。"""

import argparse
import json
import os
import sys
from pathlib import Path


def parse_args():
    """解析 URL 回填参数。"""
    parser = argparse.ArgumentParser(description="回填 TTS 参考音频 public URL")
    parser.add_argument("--selection", required=True, help="tts_reference_selection.json 路径")
    parser.add_argument("--upload-result", required=True, help="真实上传产生的 upload_result.json")
    parser.add_argument("--table", help="TTS音色总表路径，默认读取 selection 中的 voice_table")
    return parser.parse_args()


def load_inputs(selection_path, upload_path):
    """把选择清单和真实上传结果按资产 ID 对齐。"""
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    upload = json.loads(upload_path.read_text(encoding="utf-8"))
    if selection.get("manifest_type") != "tts_reference_selection":
        raise ValueError("selection 类型错误")
    if upload.get("manifest_type") != "upload_result":
        raise ValueError("upload-result 类型错误")
    if upload.get("dry_run"):
        raise ValueError("dry-run 结果不能作为已上传 URL 回填")
    if upload.get("asset_type") != "tts_reference":
        raise ValueError("upload-result 不是 tts_reference 类型")

    uploaded = {
        item.get("id"): item
        for item in upload.get("results", [])
        if item.get("success") and item.get("public_url")
    }
    rows = []
    for asset in selection.get("assets", []):
        result = uploaded.get(asset.get("id"))
        if not result:
            raise ValueError(f"缺少真实上传成功结果：{asset.get('id', '<unknown>')}")
        rows.append({
            "role_key": asset.get("role_key", ""),
            "variant": asset.get("selected_variant", ""),
            "local_path": asset.get("local_path", ""),
            "public_url": result.get("public_url", ""),
        })
    return selection, rows


def replace_confirmation_section(table_path, rows):
    """保留音色总表其他内容，只重写参考音频确认区。"""
    lines = table_path.read_text(encoding="utf-8").splitlines()
    section_start = None
    section_end = len(lines)
    for index, line in enumerate(lines):
        if line.strip() == "## 参考音频确认":
            section_start = index
            continue
        if section_start is not None and index > section_start and line.startswith("## "):
            section_end = index
            break
    if section_start is None:
        raise ValueError("音色总表缺少‘参考音频确认’区，请先运行 select_reference_audio.py")

    section = [
        "## 参考音频确认",
        "",
        "> 人工试听确认；人物和旁白都只绑定音色，不绑定正式台词内容。",
        "",
        "| role_key | 已确认样本 | 参考音频文件 | reference_audio URL | 状态 |",
        "|---|---|---|---|---|",
    ]
    for row in rows:
        rel_path = os.path.relpath(row["local_path"], table_path.parent).replace("\\", "/")
        section.append(
            f"| {row['role_key']} | {row['variant']} | {rel_path} | {row['public_url']} | 已上传 |"
        )
    section.append("")
    new_lines = lines[:section_start] + section + lines[section_end:]
    table_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def main():
    args = parse_args()
    selection_path = Path(args.selection).resolve()
    upload_path = Path(args.upload_result).resolve()
    try:
        selection, rows = load_inputs(selection_path, upload_path)
        table_value = args.table or selection.get("voice_table")
        if not table_value:
            raise ValueError("未提供 TTS 音色总表路径")
        table_path = Path(table_value).resolve()
        if not table_path.exists():
            raise ValueError(f"TTS 音色总表不存在：{table_path}")
        replace_confirmation_section(table_path, rows)
    except (OSError, json.JSONDecodeError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    print(f"已回填 {len(rows)} 条 reference_audio URL：{table_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
