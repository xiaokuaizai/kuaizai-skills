#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成产物归档脚本

功能：
  把生成后的产物（图片、音频、视频）自动解析路径并上传到 OSS。
  等价于先调用 resolve_asset_paths.py，再调用 upload_assets.py。

用法示例：
  python scripts/register_outputs.py \
    --project 英语项目 \
    --branch 支线1 \
    --asset-type storyboard_panel \
    --files "panels/SH-01.png" "panels/SH-02.png" \
    --upload
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Windows 控制台默认编码可能为 GBK，重定向输出时统一使用 UTF-8 并允许替换不可编码字符
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="归档生成产物到 OSS")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--branch", default="主线", help="支线名称")
    parser.add_argument("--asset-type", required=True, help="资产类型，同 resolve_asset_paths.py")
    parser.add_argument("--files", nargs="+", required=True, help="产物文件路径列表")
    parser.add_argument("--ids", nargs="+", help="产物 ID 列表")
    parser.add_argument("--segment", default="", help="SEG 编号")
    parser.add_argument("--date-desc", default="", help="test 类型描述")
    parser.add_argument("--output-dir", default="00_元数据/清单", help="manifest 输出目录")
    parser.add_argument("--upload", action="store_true", help="真实上传")
    return parser.parse_args()


def run_resolve(args: argparse.Namespace, manifest_path: Path) -> int:
    """调用 resolve_asset_paths.py"""
    script_dir = Path(__file__).resolve().parent
    cmd = [
        sys.executable,
        str(script_dir / "resolve_asset_paths.py"),
        "--project", args.project,
        "--branch", args.branch,
        "--asset-type", args.asset_type,
        "--files", *args.files,
        "--output", str(manifest_path),
    ]
    if args.ids:
        cmd += ["--ids", *args.ids]
    if args.segment:
        cmd += ["--segment", args.segment]
    if args.date_desc:
        cmd += ["--date-desc", args.date_desc]

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def run_upload(manifest_path: Path, do_upload: bool) -> int:
    """调用 upload_assets.py"""
    script_dir = Path(__file__).resolve().parent
    cmd = [
        sys.executable,
        str(script_dir / "upload_assets.py"),
        "--manifest", str(manifest_path),
    ]
    if do_upload:
        cmd.append("--upload")

    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result.returncode


def main() -> int:
    args = parse_args()

    # 生成 manifest 文件名
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_%H%M%S")
    manifest_name = f"{timestamp}_{args.asset_type}_manifest.json"
    manifest_path = Path(args.output_dir) / manifest_name
    manifest_path.parent.mkdir(parents=True, exist_ok=True)

    # 解析路径
    rc = run_resolve(args, manifest_path)
    if rc != 0:
        return rc

    # 上传
    rc = run_upload(manifest_path, args.upload)
    return rc


if __name__ == "__main__":
    sys.exit(main())
