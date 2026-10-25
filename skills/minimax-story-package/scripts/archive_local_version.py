#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地旧版归档脚本

功能：
  在生成新版文件之前，把已存在的旧版文件归档到同目录的 旧版/ 文件夹中。

用法示例：
  python scripts/archive_local_version.py \
    --file "panels/SH-01.png" \
    --reason "人物服装不一致，重新生成"
"""

import argparse
import sys
from pathlib import Path

from _archive import archive_local_file


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="归档本地旧版文件")
    parser.add_argument("--file", required=True, help="要归档的本地文件路径")
    parser.add_argument("--reason", default="", help="归档原因，会写入 旧版/说明.txt")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    target = Path(args.file)

    archived = archive_local_file(target, reason=args.reason)
    if archived is None:
        print(f"文件不存在，无需归档：{target}")
        return 0

    print(f"已归档旧版：{target} -> {archived}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
