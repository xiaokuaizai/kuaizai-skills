#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""归档故事板流程中的旧输出，避免脚本静默覆盖历史版本。"""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="归档一个或多个旧输出文件")
    parser.add_argument("--project-root", required=True, help="任务目录")
    parser.add_argument("--file", nargs="+", required=True, help="要归档的文件路径")
    parser.add_argument("--archive-dir", help="归档目录，默认原文件目录/_archive")
    return parser.parse_args()


def main() -> int:
    """移动文件到带时间戳的归档目录。"""
    args = parse_args()
    root = Path(args.project_root).resolve()
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    moved = 0
    for raw_path in args.file:
        path = Path(raw_path)
        if not path.is_absolute():
            path = root / path
        path = path.resolve()
        if not path.exists():
            print(f"跳过不存在文件：{path}")
            continue

        archive_dir = Path(args.archive_dir) if args.archive_dir else path.parent / "_archive"
        archive_dir.mkdir(parents=True, exist_ok=True)
        target = archive_dir / f"{path.stem}_{stamp}{path.suffix}"
        index = 2
        while target.exists():
            target = archive_dir / f"{path.stem}_{stamp}_{index}{path.suffix}"
            index += 1
        path.replace(target)
        print(f"已归档：{path} -> {target}")
        moved += 1

    print(f"归档完成，共 {moved} 个文件。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
