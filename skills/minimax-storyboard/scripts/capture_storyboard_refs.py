#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
导演分镜总表按 SEG 截图脚本

功能：
  打开已生成的 *_director_full_table.html，把每一个 .seg-row 单独截图，
  保存为 故事板参考图/SEG-XX-故事板参考图.png。

依赖安装：
  pip install playwright
  playwright install chromium

用法示例：
  python scripts/capture_storyboard_refs.py episode_director_full_table.html
  python scripts/capture_storyboard_refs.py episode_director_full_table.html --output-dir 故事板参考图
"""

import argparse
import json
import os
import sys
from datetime import datetime
from pathlib import Path

from playwright.sync_api import sync_playwright


def file_url(path: str) -> str:
    """把本地路径转成可访问 URL，兼容 Windows

    优先使用 HTTP 服务（避免 file:// 下相对路径加载失败），
    若环境变量 STORYBOARD_HTTP_URL 存在则直接用它作为 base。
    """
    http_base = os.environ.get("STORYBOARD_HTTP_URL")
    if http_base:
        # 用文件名拼接到 HTTP base 后
        return http_base.rstrip("/") + "/" + Path(path).name
    # 否则退回 file:// 协议（相对路径在 file:// 下通常失败，不推荐）
    return Path(path).resolve().as_uri()


def archive_existing(path: Path, archive_dir: Path) -> Path | None:
    """截图前归档旧文件，避免静默覆盖历史交付物。"""
    if not path.exists():
        return None
    archive_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archived = archive_dir / f"{path.stem}_{stamp}{path.suffix}"
    path.replace(archived)
    return archived


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="将导演分镜总表 HTML 按 SEG 截图，输出为故事板参考图。"
    )
    parser.add_argument("html", help="HTML 总表文件路径，例如 episode_director_full_table.html")
    parser.add_argument(
        "--output-dir",
        default="故事板参考图",
        help="截图输出文件夹，默认：故事板参考图",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1920,
        help="浏览器视口宽度，默认 1920",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=1080,
        help="浏览器视口高度，默认 1080",
    )
    parser.add_argument(
        "--scale-factor",
        type=int,
        default=1,
        help="屏幕缩放因子（1=普通，2=2x 高清），默认 1",
    )
    parser.add_argument(
        "--wait-ms",
        type=int,
        default=300,
        help="截图前等待毫秒数，默认 300",
    )
    parser.add_argument(
        "--expected-segments",
        type=int,
        help="预期 SEG 数量；不一致时失败",
    )
    parser.add_argument(
        "--archive-dir",
        help="旧截图归档目录，默认输出目录/_archive",
    )
    parser.add_argument(
        "--manifest",
        help="可选：写出截图清单 JSON",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    # 检查 HTML 文件是否存在
    html_path = Path(args.html)
    if not html_path.exists():
        print(f"错误：HTML 文件不存在：{html_path}", file=sys.stderr)
        return 1

    # 创建输出文件夹
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = Path(args.archive_dir) if args.archive_dir else out_dir / "_archive"
    print(f"输出目录：{out_dir.resolve()}")

    with sync_playwright() as p:
        # 启动 Chromium，无头模式
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={
                "width": args.viewport_width,
                "height": args.viewport_height,
            },
            device_scale_factor=args.scale_factor,
        )

        # 打开 HTML，等待网络空闲确保资源加载完
        page.goto(file_url(str(html_path)), wait_until="networkidle")

        # 查找所有 SEG 行
        rows = page.locator(".seg-row")
        count = rows.count()
        if count == 0:
            print("错误：HTML 中没有找到 .seg-row，请检查总表结构。", file=sys.stderr)
            browser.close()
            return 1
        if args.expected_segments is not None and count != args.expected_segments:
            print(
                f"错误：HTML 中有 {count} 个 SEG，预期 {args.expected_segments} 个。",
                file=sys.stderr,
            )
            browser.close()
            return 1

        # 先检查浏览器能否加载所有图片，避免截图成功但得到裂图。
        broken_images = page.locator("img").evaluate_all(
            "(imgs) => imgs.filter(img => !img.complete || img.naturalWidth === 0).map(img => img.src)"
        )
        if broken_images:
            print(f"错误：HTML 中有 {len(broken_images)} 张图片加载失败。", file=sys.stderr)
            browser.close()
            return 1

        print(f"共找到 {count} 个 SEG 行，开始截图...")

        records = []
        seen_ids = set()
        for i in range(count):
            row = rows.nth(i)

            # 滚动到该行，确保完整渲染
            row.scroll_into_view_if_needed()
            if args.wait_ms > 0:
                page.wait_for_timeout(args.wait_ms)

            # 尝试读取 SEG 编号作为文件名
            try:
                seg_id = row.locator(".seg-id").inner_text(timeout=2000).strip()
            except Exception:
                seg_id = ""

            # 兜底命名：如果读不到 seg-id，就用序号
            if not seg_id:
                seg_id = f"SEG-{i + 1:02d}"
            normalized_id = seg_id.upper().replace(" ", "-")
            if normalized_id in seen_ids:
                print(f"错误：发现重复 SEG ID：{seg_id}", file=sys.stderr)
                browser.close()
                return 1
            seen_ids.add(normalized_id)

            out_name = f"{seg_id}-故事板参考图.png"
            out_path = out_dir / out_name

            archived = archive_existing(out_path, archive_dir)
            # 元素级截图：只截这一行
            row.screenshot(path=str(out_path))
            print(f"  [OK] {out_name}")
            records.append(
                {
                    "seg_id": seg_id,
                    "path": out_path.as_posix(),
                    "archived": archived.as_posix() if archived else None,
                }
            )

        browser.close()

    print(f"截图完成，共 {count} 张。")
    if args.manifest:
        manifest_path = Path(args.manifest)
        manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest_path.write_text(
            json.dumps({"count": count, "items": records}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(f"清单已写入：{manifest_path.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
