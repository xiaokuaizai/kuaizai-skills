#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""读取 TTS 人工选样清单，并统一登记/上传 tts_reference。"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args():
    """解析 TTS 参考音频交接参数。"""
    parser = argparse.ArgumentParser(description="登记 minimax-storyboard-tts 已确认的参考音频")
    parser.add_argument("--selection", required=True, help="tts_reference_selection.json 路径")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--branch", default="主线", help="支线名称")
    parser.add_argument("--output-dir", default="00_元数据/清单", help="manifest 输出目录")
    parser.add_argument("--upload", action="store_true", help="真实上传；不指定则只做 dry-run")
    return parser.parse_args()


def read_selection(selection_path):
    """只接受 TTS skill 输出的人工确认清单。"""
    data = json.loads(selection_path.read_text(encoding="utf-8"))
    if data.get("manifest_type") != "tts_reference_selection":
        raise ValueError("输入文件不是 tts_reference_selection")
    assets = data.get("assets", [])
    if not assets:
        raise ValueError("选择清单中没有参考音频")

    ids = []
    files = []
    for item in assets:
        if item.get("status") != "confirmed_pending_upload":
            raise ValueError(f"参考音频尚未处于人工确认状态：{item.get('id', '<unknown>')}")
        if item.get("purpose") != "voice_only" or item.get("content_binding") is not False:
            raise ValueError(f"参考音频用途标记错误：{item.get('id', '<unknown>')}")
        local_path = Path(item.get("local_path", ""))
        if not local_path.exists():
            raise ValueError(f"参考音频文件不存在：{local_path}")
        ids.append(item.get("id", ""))
        files.append(str(local_path))
    if any(not item_id for item_id in ids):
        raise ValueError("选择清单存在空的参考音频 ID")
    if len(set(ids)) != len(ids):
        raise ValueError("选择清单存在重复的参考音频 ID")
    return ids, files


def main():
    args = parse_args()
    selection_path = Path(args.selection).resolve()
    if not selection_path.exists():
        print(f"错误：选择清单不存在：{selection_path}", file=sys.stderr)
        return 1

    try:
        ids, files = read_selection(selection_path)
    except (json.JSONDecodeError, ValueError) as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    script_dir = Path(__file__).resolve().parent
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_%H%M%S")
    output_dir = Path(args.output_dir).resolve()
    manifest_path = output_dir / f"{timestamp}_tts_reference_manifest.json"
    upload_result_path = output_dir / f"{timestamp}_tts_reference_upload_result.json"

    resolve_cmd = [
        sys.executable,
        str(script_dir / "resolve_asset_paths.py"),
        "--project",
        args.project,
        "--branch",
        args.branch,
        "--asset-type",
        "tts_reference",
        "--files",
        *files,
        "--ids",
        *ids,
        "--output",
        str(manifest_path),
    ]
    resolved = subprocess.run(resolve_cmd, capture_output=True, text=True, encoding="utf-8")
    if resolved.stdout:
        print(resolved.stdout.strip())
    if resolved.returncode != 0:
        print(resolved.stderr.strip(), file=sys.stderr)
        return resolved.returncode

    upload_cmd = [
        sys.executable,
        str(script_dir / "upload_assets.py"),
        "--manifest",
        str(manifest_path),
        "--output",
        str(upload_result_path),
    ]
    if args.upload:
        upload_cmd.append("--upload")
    uploaded = subprocess.run(upload_cmd, capture_output=True, text=True, encoding="utf-8")
    if uploaded.stdout:
        print(uploaded.stdout.strip())
    if uploaded.stderr:
        print(uploaded.stderr.strip(), file=sys.stderr)
    if uploaded.returncode != 0:
        return uploaded.returncode

    print(f"TTS 参考音频 manifest：{manifest_path}")
    print(f"TTS 参考音频上传结果：{upload_result_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
