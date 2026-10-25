#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产路径解析脚本

功能：
  根据项目名、支线名、资产类型和本地文件，生成对应的 OSS key 和 public URL。
  支持中文路径，输出 JSON manifest。

依赖：
  pip install ali-oss  # 仅在上传时需要，解析本身不需要

用法示例：
  python scripts/resolve_asset_paths.py \
    --project 英语项目 \
    --branch 支线1 \
    --asset-type character_costume_view \
    --files "资产/人物锚点/支线1/安琪_支线1_外出超市休闲装.png" \
    --ids "anqi_支线1_外出超市休闲装" \
    --output "清单/2026-08-24_asset_manifest.json"
"""

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from _config import get_oss_config


# 资产类型到 OSS 目录模板的映射
# 模板中可用变量：{project}, {branch}, {character}, {segment}, {filename}
ASSET_TYPE_DIRS = {
    # 人物锚点
    "character_base_view": "video_workspace/{project}/02_参考/支线/{branch}/人物锚点/人物三视图/{filename}",
    "character_costume_view": "video_workspace/{project}/02_参考/支线/{branch}/人物锚点/人物服装三视图/{filename}",
    # 场景/物品锚点
    "scene_anchor": "video_workspace/{project}/02_参考/支线/{branch}/场景锚点/{filename}",
    "prop_anchor": "video_workspace/{project}/02_参考/支线/{branch}/物品锚点/{filename}",
    # 分镜相关
    "storyboard_panel": "video_workspace/{project}/02_参考/支线/{branch}/分镜图/{filename}",
    "storyboard_ref": "video_workspace/{project}/02_参考/支线/{branch}/故事板参考图/{filename}",
    # 风格参考（默认放主线）
    "style_ref": "video_workspace/{project}/02_参考/主线/风格参考/{filename}",
    # TTS
    "tts_preview": "video_workspace/{project}/03_TTS/试听音频/{filename}",
    "tts_reference": "video_workspace/{project}/03_TTS/参考音频/{filename}",
    # 最终产出
    "output_full_video": "video_workspace/{project}/04_支线产出/产出/{branch}/完整视频/{filename}",
    "output_segment_video": "video_workspace/{project}/04_支线产出/产出/{branch}/分段视频/{segment}/{filename}",
    "output_shot_video": "video_workspace/{project}/04_支线产出/产出/{branch}/分段视频/{segment}/镜头视频/{filename}",
    # 测试
    "test": "video_workspace/TEST/{date_desc}/{filename}",
}


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="解析资产路径，生成 OSS key 和 public URL")
    parser.add_argument("--project", required=True, help="项目名称，例如：英语项目")
    parser.add_argument("--branch", default="主线", help="支线名称，例如：支线1；主线可省略或写'主线'")
    parser.add_argument("--asset-type", required=True, choices=list(ASSET_TYPE_DIRS.keys()), help="资产类型")
    parser.add_argument("--files", nargs="+", required=True, help="本地文件路径列表")
    parser.add_argument("--ids", nargs="+", help="每个资产的ID，未提供时使用原文件名")
    parser.add_argument("--segment", default="", help="分段视频时的 SEG 编号，例如：SEG-01")
    parser.add_argument("--date-desc", default="", help="test 类型时的目录描述，例如：2026-08-24_测试")
    parser.add_argument("--output", help="输出 manifest 文件路径，默认输出到 stdout")
    parser.add_argument("--dry-run", action="store_true", help="只检查文件是否存在，不实际上传")
    return parser.parse_args()


def build_oss_key(asset_type: str, project: str, branch: str, filename: str,
                  segment: str = "", date_desc: str = "") -> str:
    """根据资产类型和参数生成 OSS key"""
    template = ASSET_TYPE_DIRS[asset_type]

    # 主线特殊处理：把"支线/{branch}"替换为"主线"
    if branch == "主线":
        template = template.replace("支线/{branch}/", "主线/")
        template = template.replace("支线/{branch}", "主线")

    # OSS 规范要求所有正式对象位于 lexilearnoss/ 前缀下。
    return "lexilearnoss/" + template.format(
        project=project,
        branch=branch,
        segment=segment or "未命名分段",
        filename=filename,
        date_desc=date_desc or datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d_未命名"),
    )


def build_public_url(base_url: str, oss_key: str) -> str:
    """把 OSS key 转换成可公开访问的 URL（对中文字符做 URL 编码）"""
    # 去掉末尾斜杠，确保 base_url 和 key 之间只有一个 /
    base_url = base_url.rstrip("/")
    # 对 key 中的非安全字符做编码，保留 /
    encoded_key = quote(oss_key, safe="/")
    # oss_key 已包含 lexilearnoss 前缀，公共 URL 直接拼接整个对象 key。
    return f"{base_url}/{encoded_key}"


def probe_reference_audio(path: Path) -> tuple[float, str]:
    """登记参考音频时复核格式和真实时长，生成层仍由 TTS skill 负责。"""
    audio_format = path.suffix.lower().lstrip(".")
    if audio_format not in {"mp3", "wav"}:
        raise ValueError(f"tts_reference 只支持 mp3/wav：{path}")
    if not path.exists():
        raise ValueError(f"tts_reference 文件不存在：{path}")

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except FileNotFoundError as error:
        raise ValueError("未找到 ffprobe，无法登记 tts_reference") from error
    except subprocess.TimeoutExpired as error:
        raise ValueError(f"ffprobe 读取参考音频超时：{path}") from error

    if result.returncode != 0:
        raise ValueError(f"参考音频无法解析：{path}；{result.stderr.strip()}")
    try:
        duration = round(float(result.stdout.strip()), 3)
    except ValueError as error:
        raise ValueError(f"参考音频时长无效：{path}") from error
    if not 2.0 <= duration <= 15.0:
        raise ValueError(f"参考音频必须为 2-15 秒：{path}（{duration}s）")
    return duration, audio_format


def resolve_assets(args: argparse.Namespace) -> dict:
    """解析所有资产，返回 manifest 字典"""
    cfg = get_oss_config()
    base_url = cfg["public_base_url"]

    input_paths = [Path(p) for p in args.files]
    ids = args.ids or []

    # 补齐 ids
    for i, p in enumerate(input_paths):
        if i >= len(ids):
            ids.append(p.name)
    ids = ids[:len(input_paths)]

    assets = []
    for p, asset_id in zip(input_paths, ids):
        if not p.exists():
            print(f"警告：文件不存在：{p}", file=sys.stderr)

        # 优先使用用户指定的 id 作为文件名主干，保留扩展名
        if asset_id != p.name:
            filename = f"{asset_id}{p.suffix}"
        else:
            filename = p.name

        oss_key = build_oss_key(
            args.asset_type,
            args.project,
            args.branch,
            filename,
            segment=args.segment,
            date_desc=args.date_desc,
        )
        public_url = build_public_url(base_url, oss_key)

        asset = {
            "id": asset_id,
            "type": args.asset_type,
            "local_path": str(p.resolve()),
            "filename": filename,
            "oss_key": oss_key,
            "public_url": public_url,
            "uploaded": False,
            "uploaded_at": None,
        }
        if args.asset_type == "tts_reference":
            duration, audio_format = probe_reference_audio(p)
            asset.update({
                "duration_seconds": duration,
                "format": audio_format,
                "purpose": "voice_only",
                "content_binding": False,
            })
        assets.append(asset)

    return {
        "manifest_type": "asset_manifest",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "project": args.project,
        "branch": args.branch,
        "asset_type": args.asset_type,
        "assets": assets,
    }


def main() -> int:
    args = parse_args()

    if args.dry_run:
        print("【dry-run 模式】只解析路径，不上传")

    try:
        manifest = resolve_assets(args)
    except ValueError as error:
        print(f"错误：{error}", file=sys.stderr)
        return 1

    # 输出
    output_text = json.dumps(manifest, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
        print(f"manifest 已写入：{output_path.resolve()}")
    else:
        print(output_text)

    return 0


if __name__ == "__main__":
    sys.exit(main())
