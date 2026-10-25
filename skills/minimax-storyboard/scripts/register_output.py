#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""把生成的文件追加登记到 doc/文件地址管理.md。

该脚本只修改本地登记表，不上传文件，也不触发任何付费接口。
"""

from __future__ import annotations

import argparse
import re
from datetime import datetime
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="登记故事板流程输出文件")
    parser.add_argument("--project-root", required=True, help="任务目录")
    parser.add_argument("--file", required=True, help="文件路径，可为项目相对路径")
    parser.add_argument("--type", required=True, help="文件类型")
    parser.add_argument("--purpose", required=True, help="文件用途")
    parser.add_argument("--object", required=True, dest="related_object", help="关联对象")
    parser.add_argument("--status", default="已生成", help="状态/备注")
    return parser.parse_args()


def relative_path(project_root: Path, file_path: Path) -> str:
    """优先写项目相对路径，项目外文件保留绝对路径。"""
    try:
        return file_path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return str(file_path.resolve())


def ensure_table(text: str) -> str:
    """确保登记表存在，旧文件没有表格时自动补齐。"""
    if "| 文件名 | 类型 | 用途 | 关联对象 | 路径 | 状态/备注 |" in text:
        return text
    suffix = "\n\n## 文件登记表\n\n| 文件名 | 类型 | 用途 | 关联对象 | 路径 | 状态/备注 |\n|---|---|---|---|---|---|\n"
    return text.rstrip() + suffix


def main() -> int:
    """执行登记。"""
    args = parse_args()
    root = Path(args.project_root).resolve()
    file_path = Path(args.file)
    if not file_path.is_absolute():
        file_path = root / file_path
    if not file_path.exists():
        raise SystemExit(f"文件不存在：{file_path}")

    doc_dir = root / "doc"
    doc_dir.mkdir(parents=True, exist_ok=True)
    mgmt_path = doc_dir / "文件地址管理.md"
    text = mgmt_path.read_text(encoding="utf-8") if mgmt_path.exists() else "# 文件地址管理\n"
    text = ensure_table(text)

    rel = relative_path(root, file_path)
    # 用路径列去重，避免重复登记同一个物理文件。
    escaped_rel = re.escape(rel)
    if re.search(rf"\|\s*{escaped_rel}\s*\|", text):
        print(f"已存在登记：{rel}")
        return 0

    filename = file_path.name.replace("|", "\\|")
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    row = (
        f"| {filename} | {args.type} | {args.purpose} | {args.related_object} | "
        f"{rel} | {args.status}；登记时间 {now} |\n"
    )
    mgmt_path.write_text(text.rstrip() + "\n" + row, encoding="utf-8")
    print(f"已登记：{rel}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
