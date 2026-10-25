#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
参考图拼接脚本（HTML + Playwright）

功能：
  把多张人物或物品参考图拼成一张 PNG，作为 Minimax H3 的 reference_image 上传。
  支持两种布局：
    - character：左侧名字标签 + 右侧图片，竖向堆叠（适合人物三视图 sheet）
    - prop：2 列网格卡片，顶部名字标签 + 图片（适合道具/物品三视图）

依赖安装：
  pip install playwright
  playwright install chromium

用法示例：
  # 人物拼接
  python scripts/combine_reference_sheets.py character \
    --input "人物锚点/A.png" "人物锚点/B.png" \
    --names "安琪" "江彻" \
    --output "refs_for_minimax/SEG-01_characters.png"

  # 物品拼接
  python scripts/combine_reference_sheets.py prop \
    --input "物品锚点/贝壳.png" "物品锚点/包.png" "物品锚点/背包.png" \
    --names "贝壳" "安琪的包" "江彻的背包" \
    --output "refs_for_minimax/SEG-01_props.png"
"""

import argparse
import html
import json
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


# 模板位于脚本同级目录的 templates/ 下
TEMPLATE_DIR = Path(__file__).resolve().parent.parent / "templates"


def file_url(path: Path) -> str:
    """把本地路径转成 file:// URL"""
    # Path.as_uri 会正确处理空格、中文和 Windows 盘符。
    return path.resolve().as_uri()


def archive_existing(path: Path, archive_dir: Path) -> Path | None:
    """输出覆盖前先归档旧拼接图。"""
    if not path.exists():
        return None
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived = archive_dir / f"{path.stem}_{stamp}{path.suffix}"
    path.replace(archived)
    return archived


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="拼接参考图为单张 PNG")
    parser.add_argument(
        "mode",
        choices=["character", "prop"],
        help="拼接模式：character 为人物竖排，prop 为物品 2 列网格",
    )
    parser.add_argument(
        "--input",
        nargs="+",
        required=True,
        help="输入图片路径列表",
    )
    parser.add_argument(
        "--names",
        nargs="+",
        help="每张图对应的名称，未提供时使用文件名",
    )
    parser.add_argument(
        "--output",
        required=True,
        help="输出 PNG 路径",
    )
    parser.add_argument(
        "--width",
        type=int,
        default=1024,
        help="HTML 页面宽度，默认 1024",
    )
    parser.add_argument(
        "--scale",
        type=int,
        default=2,
        help="Playwright 缩放因子，默认 2（输出 2x 分辨率）",
    )
    parser.add_argument(
        "--keep-html",
        action="store_true",
        help="保留临时生成的 HTML 文件",
    )
    parser.add_argument(
        "--title",
        default="Minimax 参考图拼接",
        help="HTML 页面标题",
    )
    parser.add_argument(
        "--desc",
        default="",
        help="HTML 页面副标题",
    )
    parser.add_argument(
        "--archive-dir",
        help="旧输出归档目录，默认输出目录/_archive",
    )
    parser.add_argument(
        "--manifest",
        help="可选：写出拼接结果 JSON 清单",
    )
    return parser.parse_args()


def build_character_items(inputs: list[Path], names: list[str]) -> str:
    """生成人物模式下的条目 HTML"""
    items = []
    for i, (p, name) in enumerate(zip(inputs, names)):
        tone = (i % 5) + 1
        url = file_url(p)
        items.append(
            f'<div class="ref-item">'
            f'<div class="label tone-{tone}"><div class="label-text">{html.escape(name)}</div></div>'
            f'<div class="image-wrap"><img src="{url}" alt="{html.escape(name)}"></div>'
            f'</div>'
        )
    return "\n".join(items)


def build_prop_items(inputs: list[Path], names: list[str]) -> str:
    """生成物品模式下的卡片 HTML"""
    items = []
    for i, (p, name) in enumerate(zip(inputs, names)):
        tone = (i % 5) + 1
        url = file_url(p)
        items.append(
            f'<div class="item-card">'
            f'<div class="item-label tone-{tone}">{html.escape(name)}</div>'
            f'<div class="item-image"><img src="{url}" alt="{html.escape(name)}"></div>'
            f'</div>'
        )
    return "\n".join(items)


def main() -> int:
    args = parse_args()

    # 检查输入文件
    input_paths = [Path(p) for p in args.input]
    for p in input_paths:
        if not p.exists():
            print(f"错误：文件不存在：{p}", file=sys.stderr)
            return 1

    # 补齐名称
    names = args.names or [p.stem for p in input_paths]
    if len(names) != len(input_paths):
        print("错误：--names 数量必须与 --input 数量完全一致。", file=sys.stderr)
        return 1

    # 选择模板与布局
    if args.mode == "character":
        template_name = "reference_character_sheet.html"
        items_html = build_character_items(input_paths, names)
    else:
        template_name = "reference_prop_sheet.html"
        items_html = build_prop_items(input_paths, names)

    template_path = TEMPLATE_DIR / template_name
    if not template_path.exists():
        print(f"错误：找不到模板文件：{template_path}", file=sys.stderr)
        return 1

    # 渲染 HTML
    html = template_path.read_text(encoding="utf-8")
    html = html.replace("{{WIDTH}}", str(args.width))
    html = html.replace("{{TITLE}}", args.title)
    html = html.replace("{{DESC}}", args.desc)
    html = html.replace("{{ITEMS}}", items_html)

    # 输出路径与临时 HTML
    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    archive_dir = Path(args.archive_dir) if args.archive_dir else output_path.parent / "_archive"
    archived = archive_existing(output_path, archive_dir)
    temp_html = output_path.parent / f"_{output_path.stem}.html"
    temp_html.write_text(html, encoding="utf-8")

    # Playwright 截图
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": args.width, "height": 1080},
            device_scale_factor=args.scale,
        )
        page.goto(file_url(temp_html), wait_until="networkidle")
        broken_images = page.locator("img").evaluate_all(
            "(imgs) => imgs.filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src)"
        )
        if broken_images:
            browser.close()
            if temp_html.exists() and not args.keep_html:
                temp_html.unlink()
            print(f"错误：有 {len(broken_images)} 张输入图片加载失败。", file=sys.stderr)
            return 1
        page.screenshot(path=str(output_path), full_page=True)
        browser.close()

    # 默认删除临时 HTML
    if not args.keep_html:
        temp_html.unlink()

    print(f"已生成：{output_path.resolve()}")
    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps(
                {
                    "mode": args.mode,
                    "output": output_path.as_posix(),
                    "inputs": [p.as_posix() for p in input_paths],
                    "names": names,
                    "archived": archived.as_posix() if archived else None,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"清单已写入：{manifest_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
