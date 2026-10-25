#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""故事板项目合同校验兼容入口。

历史流程使用本文件名执行项目合同校验。现在统一转发到
validate_storyboard.py，避免两个脚本维护两套不一致的硬门禁规则。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from validate_storyboard import STAGE_DOC_FILES, validate_directory


def parse_args() -> argparse.Namespace:
    """解析旧入口仍支持的命令行参数。"""
    parser = argparse.ArgumentParser(description="校验故事板项目交付合同（统一校验入口）")
    parser.add_argument("project", help="项目目录")
    parser.add_argument("--stage", choices=list(STAGE_DOC_FILES), default="G", help="当前阶段，默认 G")
    parser.add_argument("--json", dest="json_path", help="可选：输出 JSON 报告")
    return parser.parse_args()


def main() -> int:
    """调用主校验器并保留旧命令的 JSON 报告能力。"""
    args = parse_args()
    root = Path(args.project)
    if not root.exists() or not root.is_dir():
        print(f"项目目录不存在：{root}", file=sys.stderr)
        return 2

    # 统一执行主校验器，确保风格、资产包、登记和 submit_ready 规则一致。
    result = validate_directory(root, stage=args.stage, strict=False)
    if args.json_path:
        report_path = Path(args.json_path)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(
                {
                    "project": str(root.resolve()),
                    "stage": args.stage,
                    "status": "passed" if result == 0 else "failed",
                    "validator": "validate_storyboard.py",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return result


if __name__ == "__main__":
    raise SystemExit(main())
