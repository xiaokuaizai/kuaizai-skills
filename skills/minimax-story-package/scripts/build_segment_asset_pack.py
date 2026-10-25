#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
SEG 资产包组装脚本

功能：
  读取已上传资产的 manifest，为指定 SEG 组装 Minimax H3 可用的
  reference_image / reference_audio 包。

用法示例：
  python scripts/build_segment_asset_pack.py \
    --project 英语项目 \
    --branch 支线1 \
    --segment SEG-01 \
    --manifest-dir "00_元数据/清单" \
    --scene "scene_br1_安琪家门口与邮箱.png" \
    --characters "jiangche_day_visit" "anqi_day_apron" \
    --voice-refs "jiang_che_voice_ref" "narrator_voice_ref" \
    --first-frame-panel "SH-01" \
    --output "00_元数据/清单/SEG-01_asset_pack.json"
"""

import argparse
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="组装 SEG 的 Minimax H3 资产包")
    parser.add_argument("--project", required=True, help="项目名称")
    parser.add_argument("--branch", default="支线1", help="支线名称")
    parser.add_argument("--segment", required=True, help="SEG 编号，例如 SEG-01")
    parser.add_argument("--manifest-dir", required=True, help="存放 asset_manifest/upload_result 的目录")
    parser.add_argument("--scene", required=True, help="场景锚点文件名或 ID")
    parser.add_argument("--characters", nargs="+", required=True, help="人物资产 ID 列表")
    parser.add_argument("--props", nargs="*", default=[], help="物品资产 ID 列表（可选）")
    parser.add_argument("--first-frame-panel", required=True, help="首帧分镜图 ID，例如 SH-01")
    parser.add_argument("--style-ref", help="风格参考图 ID（可选）")
    parser.add_argument(
        "--voice-refs",
        nargs="*",
        default=[],
        help="已确认并上传为 tts_reference 的人物/旁白音频 ID，最多 3 个",
    )
    parser.add_argument("--output", help="输出文件路径，默认输出到 stdout")
    return parser.parse_args()


def load_all_assets(manifest_dir: Path) -> list:
    """合并 asset_manifest 与真实 upload_result，得到可提交资产状态。"""
    if not manifest_dir.exists():
        return []

    documents = []
    for file_path in sorted(manifest_dir.glob("*.json")):
        try:
            documents.append(json.loads(file_path.read_text(encoding="utf-8")))
        except Exception:
            continue

    # 先加载资产定义，再用真实上传结果覆盖 uploaded 状态。
    asset_index = {}
    for data in documents:
        if data.get("manifest_type") != "asset_manifest":
            continue
        for item in data.get("assets", []):
            key = (item.get("id", ""), item.get("type", ""))
            asset_index[key] = dict(item)

    for data in documents:
        if data.get("manifest_type") != "upload_result" or data.get("dry_run"):
            continue
        asset_type = data.get("asset_type", "")
        for result in data.get("results", []):
            if not result.get("success"):
                continue
            result_type = result.get("type", asset_type)
            key = (result.get("id", ""), result_type)
            item = asset_index.get(key, {
                "id": result.get("id", ""),
                "type": result_type,
                "filename": Path(result.get("local_path", "")).name,
            })
            item.update({
                "local_path": result.get("local_path", item.get("local_path", "")),
                "oss_key": result.get("oss_key", item.get("oss_key", "")),
                "public_url": result.get("public_url", item.get("public_url", "")),
                "uploaded": True,
            })
            for field in ("duration_seconds", "format", "purpose", "content_binding"):
                if field in result:
                    item[field] = result[field]
            asset_index[key] = item
    return list(asset_index.values())


def find_asset(assets: list, asset_type: str, identifier: str) -> dict:
    """按类型和 ID/文件名查找资产"""
    for item in assets:
        if asset_type and item.get("type") != asset_type:
            continue
        item_id = item.get("id", "")
        filename = item.get("filename", "")
        # ID 匹配或文件名匹配
        if identifier == item_id or identifier == filename or filename.startswith(identifier):
            return item
    return {}


def require_uploaded_reference(item: dict, label: str) -> dict:
    """确保图片资产已真实上传并且有可供下游调用的 public URL。"""
    if not item:
        raise ValueError(f"未找到必需的参考资产：{label}")
    if not item.get("uploaded"):
        raise ValueError(f"参考资产尚未真实上传：{label}")
    public_url = item.get("public_url", "")
    if not isinstance(public_url, str) or not re.fullmatch(r"https?://\S+", public_url, re.IGNORECASE):
        raise ValueError(f"参考资产缺少有效公网 HTTP(S) URL：{label}")
    return item


def build_reference_audios(assets: list, identifiers: list[str]) -> tuple[list, dict]:
    """复核某个 SEG 实际使用的已确认音色参考，不检查样本文本内容。"""
    if not identifiers:
        return [], {
            "count": 0,
            "total_duration_seconds": 0,
            "status": "not_requested",
            "rules": "最多3段；每段2-15秒；总时长不超过15秒；仅参考音色",
        }
    if len(identifiers) > 3:
        raise ValueError(f"reference_audio 最多 3 段，当前选择了 {len(identifiers)} 段")
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("reference_audio ID 存在重复")

    reference_audios = []
    total_duration = 0.0
    for slot, identifier in enumerate(identifiers, start=1):
        item = find_asset(assets, "tts_reference", identifier)
        if not item:
            raise ValueError(f"未找到 tts_reference：{identifier}")
        if not item.get("uploaded"):
            raise ValueError(f"tts_reference 尚未真实上传：{identifier}")
        public_url = item.get("public_url", "")
        if not isinstance(public_url, str) or not re.fullmatch(r"https?://\S+", public_url, re.IGNORECASE):
            raise ValueError(f"tts_reference 缺少有效公网 HTTP(S) URL：{identifier}")

        audio_format = str(item.get("format", "")).lower()
        if audio_format not in {"mp3", "wav"}:
            raise ValueError(f"tts_reference 格式缺失或不支持：{identifier}")
        try:
            duration = float(item.get("duration_seconds"))
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"tts_reference 缺少真实时长，请用当前 resolve_asset_paths.py 重新登记：{identifier}"
            ) from error
        if not 2.0 <= duration <= 15.0:
            raise ValueError(f"tts_reference 必须为 2-15 秒：{identifier}（{duration:g}s）")

        total_duration += duration
        reference_audios.append({
            "slot": slot,
            "id": item.get("id", identifier),
            "public_url": item.get("public_url", ""),
            "duration_seconds": round(duration, 3),
            "format": audio_format,
            "purpose": "voice_only",
            "content_binding": False,
        })

    if total_duration > 15.0:
        raise ValueError(f"reference_audio 总时长不得超过 15 秒，当前为 {total_duration:.3f} 秒")
    return reference_audios, {
        "count": len(reference_audios),
        "total_duration_seconds": round(total_duration, 3),
        "status": "passed",
        "rules": "最多3段；每段2-15秒；总时长不超过15秒；仅参考音色",
    }


def build_pack(args: argparse.Namespace) -> dict:
    """组装 SEG 资产包"""
    manifest_dir = Path(args.manifest_dir)
    assets = load_all_assets(manifest_dir)

    if not assets:
        raise ValueError(f"在 {manifest_dir} 下未找到任何已上传资产")

    # 1. 故事板参考图
    storyboard_ref = find_asset(assets, "storyboard_ref", args.segment)

    # 2. 人物参考图：所有命令行指定的人物都必须能解析到已上传资产。
    character_items = []
    missing_characters = []
    for cid in args.characters:
        item = find_asset(assets, "character_costume_view", cid)
        if not item:
            item = find_asset(assets, "character_base_view", cid)
        if item:
            character_items.append(item)
        else:
            missing_characters.append(cid)
    if missing_characters:
        raise ValueError(f"未找到人物参考资产：{', '.join(missing_characters)}")
    for item in character_items:
        require_uploaded_reference(item, f"人物 {item.get('id', item.get('filename', ''))}")

    # 3. 场景参考图
    scene_item = find_asset(assets, "scene_anchor", args.scene)
    require_uploaded_reference(scene_item, f"场景 {args.scene}")

    # 4. 道具/风格参考图（可选；无道具/风格资产时可不传第 4 张）
    prop_item = {}
    for pid in args.props:
        prop_item = find_asset(assets, "prop_anchor", pid)
        if prop_item:
            break
    if not prop_item and args.style_ref:
        prop_item = find_asset(assets, "style_ref", args.style_ref)
    if prop_item:
        require_uploaded_reference(prop_item, "道具或风格参考图")

    # 5. 首帧分镜图
    first_frame = find_asset(assets, "storyboard_panel", args.first_frame_panel)
    require_uploaded_reference(first_frame, f"首帧分镜图 {args.first_frame_panel}")

    # 故事板参考图必须与当前 SEG 对应，不能用空 URL 继续生成资产包。
    require_uploaded_reference(storyboard_ref, f"故事板参考图 {args.segment}")

    reference_images = [
        {
            "slot": 1,
            "label": "故事板参考图",
            "id": storyboard_ref.get("id", ""),
            "public_url": storyboard_ref.get("public_url", ""),
        },
        {
            "slot": 2,
            "label": "人物拼接参考图",
            "id": ", ".join([c.get("id", "") for c in character_items]),
            "public_url": character_items[0].get("public_url", "") if character_items else "",
            "character_items": [{"id": c.get("id"), "public_url": c.get("public_url")} for c in character_items],
            "note": "如有多个人物，先运行 minimax-storyboard/scripts/combine_reference_sheets.py 拼接",
        },
        {
            "slot": 3,
            "label": "场景参考图",
            "id": scene_item.get("id", ""),
            "public_url": scene_item.get("public_url", ""),
        },
    ]
    if prop_item:
        reference_images.append({
            "slot": 4,
            "label": "道具/风格参考图",
            "id": prop_item.get("id", ""),
            "public_url": prop_item.get("public_url", ""),
        })
    reference_images.append({
        "slot": 5 if prop_item else 4,
        "label": "首帧分镜图",
        "id": first_frame.get("id", ""),
        "public_url": first_frame.get("public_url", ""),
    })

    reference_audios, audio_validation = build_reference_audios(assets, args.voice_refs)

    return {
        "manifest_type": "segment_asset_pack",
        "project": args.project,
        "branch": args.branch,
        "segment": args.segment,
        "built_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "reference_images": reference_images,
        "reference_audios": reference_audios,
        "reference_audio_validation": audio_validation,
    }


def main() -> int:
    args = parse_args()
    try:
        pack = build_pack(args)
    except ValueError as e:
        print(f"错误：{e}", file=sys.stderr)
        return 1

    output_text = json.dumps(pack, ensure_ascii=False, indent=2)
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(output_text, encoding="utf-8")
        print(f"SEG 资产包已写入：{output_path.resolve()}")
    else:
        print(output_text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
