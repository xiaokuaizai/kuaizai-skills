#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""记录人工确认的 TTS 音色样本，生成 reference_audio 交接清单。"""

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args():
    """解析人工选样参数。"""
    parser = argparse.ArgumentParser(description="选择人物/旁白的 Minimax H3 参考音频")
    parser.add_argument("--result", required=True, help="sample_generation_result.json 路径")
    parser.add_argument(
        "--select",
        action="append",
        required=True,
        metavar="ROLE=VARIANT",
        help="人工确认项，可重复，例如 jiang_che=primary、narrator=alt_01",
    )
    parser.add_argument("--table", help="TTS音色总表路径；默认读取生成结果中的 voice_table")
    parser.add_argument("--output", help="输出清单路径，默认写到生成结果同目录")
    return parser.parse_args()


def parse_selections(values):
    """把 role=variant 参数转换为唯一的角色选择。"""
    selections = {}
    for value in values:
        if "=" not in value:
            raise ValueError(f"选择格式错误：{value}，应为 ROLE=VARIANT")
        role_key, variant = (part.strip() for part in value.split("=", 1))
        if not role_key or not variant:
            raise ValueError(f"选择格式错误：{value}，角色和样本均不能为空")
        if role_key in selections:
            raise ValueError(f"角色 {role_key} 被重复选择")
        selections[role_key] = variant
    return selections


def select_assets(result_data, selections):
    """只接受已经通过 TTS 自检且满足 reference_audio 单段限制的样本。"""
    samples = result_data.get("samples", [])
    assets = []
    for role_key, variant in selections.items():
        matches = [
            item for item in samples
            if item.get("role_key") == role_key and item.get("variant") == variant
        ]
        if not matches:
            raise ValueError(f"没有找到样本：{role_key}={variant}")

        item = matches[0]
        if not item.get("validation_passed"):
            raise ValueError(f"样本未通过音频解析校验：{role_key}={variant}")
        if not item.get("reference_eligible"):
            duration = item.get("duration_seconds")
            raise ValueError(
                f"样本不满足 reference_audio 单段 2-15 秒限制："
                f"{role_key}={variant} ({duration}s)"
            )

        local_path = Path(item.get("local_path", ""))
        if not local_path.exists():
            raise ValueError(f"样本文件不存在：{local_path}")

        assets.append({
            "id": f"{role_key}_voice_ref",
            "role_key": role_key,
            "role": item.get("role", role_key),
            "selected_variant": variant,
            "voice_type": item.get("voice_type", ""),
            "local_path": str(local_path.resolve()),
            "format": item.get("format", local_path.suffix.lower().lstrip(".")),
            "duration_seconds": item.get("duration_seconds"),
            "purpose": "voice_only",
            "content_binding": False,
            "status": "confirmed_pending_upload",
        })
    return assets


def update_voice_table(table_path, assets):
    """把人工确认结果写回音色总表，URL 留给上传步骤回填。"""
    if not table_path or not table_path.exists():
        return

    original = table_path.read_text(encoding="utf-8")
    lines = original.splitlines()
    section_start = None
    section_end = len(lines)
    for index, line in enumerate(lines):
        if line.strip() == "## 参考音频确认":
            section_start = index
            continue
        if section_start is not None and index > section_start and line.startswith("## "):
            section_end = index
            break

    section = [
        "## 参考音频确认",
        "",
        "> 人工试听确认；人物和旁白都只绑定音色，不绑定正式台词内容。",
        "",
        "| role_key | 已确认样本 | 参考音频文件 | reference_audio URL | 状态 |",
        "|---|---|---|---|---|",
    ]
    for item in assets:
        rel_path = os.path.relpath(item["local_path"], table_path.parent).replace("\\", "/")
        section.append(
            f"| {item['role_key']} | {item['selected_variant']} | {rel_path} |  | 已确认，待上传 |"
        )
    section.append("")

    if section_start is None:
        new_lines = lines + [""] + section
    else:
        new_lines = lines[:section_start] + section + lines[section_end:]
    table_path.write_text("\n".join(new_lines).rstrip() + "\n", encoding="utf-8")


def main():
    args = parse_args()
    result_path = Path(args.result).resolve()
    if not result_path.exists():
        print(f"错误：生成结果不存在：{result_path}", file=sys.stderr)
        return 1

    try:
        result_data = json.loads(result_path.read_text(encoding="utf-8"))
        if result_data.get("manifest_type") != "tts_sample_generation_result":
            raise ValueError("输入文件不是 tts_sample_generation_result")
        selections = parse_selections(args.select)
        assets = select_assets(result_data, selections)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    table_value = args.table or result_data.get("voice_table")
    table_path = Path(table_value).resolve() if table_value else None
    update_voice_table(table_path, assets)

    output_path = (
        Path(args.output).resolve()
        if args.output
        else result_path.parent / "tts_reference_selection.json"
    )
    output_data = {
        "manifest_type": "tts_reference_selection",
        "confirmed_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "source_result": str(result_path),
        "voice_table": str(table_path) if table_path else "",
        "assets": assets,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(output_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"已确认 {len(assets)} 个声音身份的参考音频")
    print(f"交接清单：{output_path}")
    if table_path:
        print(f"已更新音色总表：{table_path}")
    print("下一步：由 minimax-story-package 以 tts_reference 类型登记并上传这些文件")
    return 0


if __name__ == "__main__":
    sys.exit(main())
