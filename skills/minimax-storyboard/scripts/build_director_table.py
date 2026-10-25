#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""根据结构化 JSON 生成导演总表 HTML、Markdown 和内嵌 SVG 站位图。

Agent 负责决定剧情与镜头内容，本脚本只负责稳定排版，避免手工复制模板残留示例。
"""

from __future__ import annotations

import argparse
import html
import json
from pathlib import Path


CSS = """
*{box-sizing:border-box}body{margin:0;background:#ece8e1;color:#202020;font-family:Arial,"Microsoft YaHei",sans-serif}.shell{width:98vw;max-width:2400px;margin:0 auto;padding:24px}.hero,.seg-row{background:#fffdf8;border:1px solid #d7ccbd;border-radius:8px}.hero{padding:22px;margin-bottom:18px}.hero h1{margin:0 0 12px;font-size:30px}.meta{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:8px;color:#51493f}.stats{margin-top:10px;font-weight:700;color:#7a4c20}.seg-row{display:grid;grid-template-columns:minmax(640px,1.35fr) minmax(420px,.9fr) minmax(300px,.55fr);grid-template-rows:64px 1fr;gap:0 16px;min-height:720px;margin:18px 0;padding:14px;break-inside:avoid}.seg-head{grid-column:1/-1;display:grid;grid-template-columns:auto 1fr auto;align-items:center;gap:12px;border-bottom:1px solid #d7ccbd}.seg-id{font-size:28px;font-weight:900;color:#7a4c20}.seg-title{font-size:21px;font-weight:800}.badge{background:#f0e7d8;border:1px solid #dbcbb5;border-radius:999px;padding:6px 12px;white-space:nowrap}.panel-grid{display:grid;gap:10px;align-content:start}.panel-cell{text-align:center}.panel-img{width:100%;aspect-ratio:9/16;object-fit:contain;background:#e9e5dd;border:1px solid #c9c1b8;border-radius:5px;display:block}.panel-label{display:inline-block;margin-top:5px;padding:3px 10px;background:#f0e7d8;border:1px solid #dbcbb5;border-radius:999px;font-weight:800}.notes{overflow:auto}.field{border-bottom:1px dashed #ded4c7;padding:8px 0}.label{font-size:16px;color:#8a6a35;font-weight:900;margin-bottom:4px}.value{line-height:1.45}.shot-table{width:100%;border-collapse:collapse}.shot-table th,.shot-table td{border:1px solid #d7ccbd;padding:5px;text-align:left;vertical-align:top}.shot-table th{background:#f0e7d8}.blocking{background:#fbfaf7;border:1px solid #c9c1b8;border-radius:6px;padding:8px;overflow:hidden}.blocking svg{width:100%;height:auto}.sound{color:#666}@media(max-width:1500px){.seg-row{grid-template-columns:1fr 1fr}.blocking{grid-column:1/-1}}@media(max-width:900px){.seg-row{grid-template-columns:1fr}.blocking{grid-column:auto}.meta{grid-template-columns:1fr}}
"""


def parse_args() -> argparse.Namespace:
    """解析命令行参数。"""
    parser = argparse.ArgumentParser(description="从 storyboard.json 生成导演总表")
    parser.add_argument("--input", required=True, help="结构化 JSON")
    parser.add_argument("--output-html", required=True, help="HTML 输出路径")
    parser.add_argument("--output-md", help="可选：Markdown 总表输出路径")
    return parser.parse_args()


def grid_columns(count: int) -> str:
    """根据镜头数量选择稳定网格列数。"""
    if count <= 2:
        return "repeat(2,1fr)"
    if count <= 4:
        return "repeat(2,1fr)"
    return "repeat(3,1fr)"


def blocking_svg(segment: dict) -> str:
    """生成简单、确定性的 CAM/FOV SVG。"""
    svg = segment.get("svg", {})
    character_a = html.escape(str(svg.get("character_a", "角色 A")))
    character_b = html.escape(str(svg.get("character_b", "角色 B")))
    scene = html.escape(str(svg.get("scene", "场景")))
    camera = html.escape(str(svg.get("camera", "正面机位")))
    return f'''<svg viewBox="0 0 360 360" role="img" aria-label="站位图"><rect x="10" y="10" width="340" height="340" rx="16" fill="#fbfaf7" stroke="#c9c1b8"/><rect x="60" y="42" width="240" height="62" rx="10" fill="#ece6dc" stroke="#d4c6b6"/><text x="180" y="78" text-anchor="middle" fill="#6d655d">{scene}</text><path d="M180 330 L118 132 L242 132 Z" fill="#7aa0c4" opacity=".16" stroke="#7aa0c4" stroke-width="2"/><line x1="180" y1="330" x2="180" y2="170" stroke="#426d9b" stroke-width="4"/><text x="180" y="372" text-anchor="middle" fill="#426d9b" font-weight="900">CAM</text><text x="310" y="330" text-anchor="end" fill="#6d655d">{camera} / FOV</text><circle cx="120" cy="120" r="22" fill="#60a5fa" stroke="#333" stroke-width="2"/><text x="120" y="163" text-anchor="middle" fill="#222">{character_a}</text><circle cx="240" cy="120" r="22" fill="#f472b6" stroke="#333" stroke-width="2"/><text x="240" y="163" text-anchor="middle" fill="#222">{character_b}</text></svg>'''


def render_segment(segment: dict) -> str:
    """渲染单个 SEG 行。"""
    seg_id = html.escape(str(segment["id"]))
    shots = segment.get("shots", [])
    panels = []
    rows = []
    for shot in shots:
        shot_id = html.escape(str(shot["id"]))
        image = html.escape(str(shot["image"]))
        panels.append(f'<div class="panel-cell"><img class="panel-img" src="{image}" alt="{shot_id}"><div class="panel-label">{shot_id}</div></div>')
        rows.append(f"<tr><td>{shot_id}</td><td>{html.escape(str(shot.get('shot_size', '-')))}</td><td>{html.escape(str(shot.get('camera', '-')))}</td><td>{html.escape(str(shot.get('duration', '-')))} s</td></tr>")
    summary = html.escape(str(segment.get("summary", "")))
    style = html.escape(str(segment.get("style", "")))
    dialogue = html.escape(str(segment.get("dialogue", "无"))).replace("\n", "<br>")
    sound = html.escape(str(segment.get("sound", "无"))).replace("\n", "<br>")
    cols = grid_columns(len(shots))
    return f'''<article class="seg-row"><div class="seg-head"><div class="seg-id">{seg_id}</div><div class="seg-title">风格：{style}｜主要内容：{summary}</div><div class="badge">{html.escape(str(segment.get("duration", "-")))} s</div></div><div class="panel-grid" style="grid-template-columns:{cols}">{''.join(panels)}</div><div class="notes"><div class="field"><div class="label">镜头列表</div><table class="shot-table"><thead><tr><th>镜头号</th><th>景别</th><th>拍摄视角</th><th>时长</th></tr></thead><tbody>{''.join(rows)}</tbody></table></div><div class="field"><div class="label">首帧锚点</div><div class="value">{html.escape(str(segment.get("first_frame", "")))}</div></div><div class="field"><div class="label">尾帧锚点</div><div class="value">{html.escape(str(segment.get("last_frame", "")))}</div></div><div class="field"><div class="label">台词 / 旁白</div><div class="value">{dialogue}</div></div></div><div class="blocking">{blocking_svg(segment)}<div class="field"><div class="label">环境声 / 动作音效</div><div class="sound">{sound}</div></div></div></article>'''


def render_markdown(data: dict) -> str:
    """生成便于审阅的 Markdown 总表。"""
    lines = [f"# {data.get('episode_title', '导演总表')}", "", "## SEG 列表", "", "| SEG | 时长 | 镜头 | 主要内容 |", "|---|---:|---|---|"]
    for segment in data.get("segments", []):
        shot_ids = ", ".join(str(shot["id"]) for shot in segment.get("shots", []))
        lines.append(f"| {segment['id']} | {segment.get('duration', '-')} s | {shot_ids} | {segment.get('summary', '')} |")
    return "\n".join(lines) + "\n"


def main() -> int:
    """读取 JSON 并输出 HTML/Markdown。"""
    args = parse_args()
    input_path = Path(args.input)
    data = json.loads(input_path.read_text(encoding="utf-8"))
    segments = data.get("segments", [])
    if not segments:
        raise SystemExit("输入 JSON 缺少 segments")
    ids = [str(segment.get("id", "")) for segment in segments]
    if len(ids) != len(set(ids)) or any(not item.startswith("SEG-") for item in ids):
        raise SystemExit("SEG ID 必须唯一且使用 SEG-XX 格式")
    for segment in segments:
        shots = segment.get("shots", [])
        if len(shots) < 1:
            raise SystemExit(f"{segment.get('id', '<unknown>')} 至少需要 1 个镜头")
        if len(shots) < 2:
            print(f"[WARN] {segment.get('id', '<unknown>')} 只有 {len(shots)} 个镜头（单镜头 SEG 例外）")
        try:
            duration = float(segment.get("duration", 0))
        except (TypeError, ValueError):
            raise SystemExit(f"{segment.get('id', '<unknown>')} 缺少有效时长") from None
        if duration <= 0 or duration > 15:
            raise SystemExit(f"{segment.get('id', '<unknown>')} 时长必须在 0-15 秒内")

    html_parts = ["<!doctype html><html lang=\"zh-CN\"><head><meta charset=\"utf-8\"><title>", html.escape(str(data.get("episode_title", "导演总表"))), "</title><style>", CSS, "</style></head><body><div class=\"shell\">"]
    html_parts.append(f"<section class=\"hero\"><h1>{html.escape(str(data.get('episode_title', '导演总表')))}｜导演分镜总表</h1><div class=\"meta\"><div>画幅：{html.escape(str(data.get('aspect_ratio', '9:16')))}</div><div>生成模型：Minimax H3</div><div>出场人物：{html.escape(str(data.get('characters', '')))}</div></div><div class=\"stats\">SEG 数：{len(segments)}　镜头数：{sum(len(s.get('shots', [])) for s in segments)}</div></section>")
    html_parts.extend(render_segment(segment) for segment in segments)
    html_parts.append("</div></body></html>")

    output_html = Path(args.output_html)
    output_html.parent.mkdir(parents=True, exist_ok=True)
    output_html.write_text("".join(html_parts), encoding="utf-8")
    if args.output_md:
        output_md = Path(args.output_md)
        output_md.parent.mkdir(parents=True, exist_ok=True)
        output_md.write_text(render_markdown(data), encoding="utf-8")
    print(f"已生成 HTML：{output_html.resolve()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
