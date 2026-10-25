#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
estimate_cost.py
根据 SEG 列表、分辨率、时长和参考素材估算视频生成费用。
"""

import argparse
import json
from pathlib import Path


# 价格表（人民币），与 references/平台配置与价格.md 保持一致
PRICE_TABLE_CNY = {
    "official": {
        "768P": 0.08 * 7.2,   # 美元换算成人民币（汇率可按实际调整）
        "2K": 0.13 * 7.2,
        "regen_768P_to_2K": 0.05 * 7.2,
        "image_over_5": 0.04 * 7.2,
        "audio": 0.0,
        "reference_video_2K": 0.13 * 7.2,
        "reference_video_768P": 0.08 * 7.2,
        "h3_context_ir_input": 0.90 * 7.2 / 1_000_000,
        "h3_context_ir_output": 3.60 * 7.2 / 1_000_000,
    },
    "metaso": {
        "768P": 0.09,
        "2K": 0.15,
        "regen_768P_to_2K": 0.06,
        "image_over_5": 0.05,
        "audio": 0.0,
        "reference_video_2K": 0.15,
        "reference_video_768P": 0.09,
        "h3_context_ir": 0.05,
    },
}


def load_asset_pack(manifest_dir: str, segment_id: str) -> dict:
    """读取单个 SEG 的 asset pack。"""
    path = Path(manifest_dir) / f"{segment_id}_asset_pack.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def estimate_segment_cost(pack: dict, platform: str) -> dict:
    """估算单个 SEG 的费用。"""
    price = PRICE_TABLE_CNY[platform]
    resolution = pack.get("resolution", "2K")
    duration = pack.get("duration", 5)

    # 输出视频费用
    output_cost = duration * price[resolution]

    # 参考图费用（前 5 张免费）
    ref_images = pack.get("reference_images", [])
    image_cost = max(0, len(ref_images) - 5) * price["image_over_5"]

    # 参考视频费用
    ref_videos = pack.get("reference_videos", [])
    video_cost = 0.0
    for v in ref_videos:
        v_duration = v.get("duration", 5)
        # 参考视频按输出分辨率计费
        video_cost += v_duration * price.get(f"reference_video_{resolution}", price[resolution])

    # 参考音频免费
    audio_cost = 0.0

    # H3-Context-IR 费用
    ir_cost = 0.0
    if pack.get("use_h3_context_ir"):
        if platform == "metaso":
            ir_cost = price["h3_context_ir"]
        else:
            # 官方按 token 计费，这里粗略估算
            ir_cost = (price["h3_context_ir_input"] * 5000 +
                       price["h3_context_ir_output"] * 3000)

    total = output_cost + image_cost + video_cost + audio_cost + ir_cost

    return {
        "segment_id": pack.get("segment_id"),
        "output_cost": round(output_cost, 4),
        "image_cost": round(image_cost, 4),
        "video_cost": round(video_cost, 4),
        "audio_cost": round(audio_cost, 4),
        "ir_cost": round(ir_cost, 4),
        "total_cost": round(total, 4),
        "currency": "CNY",
    }


def estimate_batch_cost(
    manifest_dir: str,
    segment_ids: list[str],
    platform: str,
) -> dict:
    """估算一批 SEG 的总费用。"""
    details = []
    total = 0.0
    for seg_id in segment_ids:
        pack = load_asset_pack(manifest_dir, seg_id)
        cost = estimate_segment_cost(pack, platform)
        details.append(cost)
        total += cost["total_cost"]

    return {
        "platform": platform,
        "segment_ids": segment_ids,
        "segment_count": len(segment_ids),
        "total_cost": round(total, 4),
        "currency": "CNY",
        "details": details,
    }


def main():
    parser = argparse.ArgumentParser(description="估算视频生成费用")
    parser.add_argument("--manifest-dir", required=True, help="asset pack 所在目录")
    parser.add_argument("--segments", required=True, nargs="+", help="SEG ID 列表")
    parser.add_argument("--platform", choices=["official", "metaso"], default="official", help="平台")
    parser.add_argument("--output", default="00_元数据/清单/cost_estimate.json", help="输出路径")

    args = parser.parse_args()
    result = estimate_batch_cost(
        manifest_dir=args.manifest_dir,
        segment_ids=args.segments,
        platform=args.platform,
    )

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"预估费用：{result['total_cost']} {result['currency']}")
    print(f"结果已保存: {args.output}")


if __name__ == "__main__":
    main()
