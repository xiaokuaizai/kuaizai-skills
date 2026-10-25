#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
submit_video_batch.py
提交一批 Minimax H3 视频生成任务。
支持 Minimax 官方平台和秘塔中转站，只有 base_url 和 api_key 不同。
秘塔中转站支持用户配置多个 API Key，每个 key 并发上限为 4。
"""

import argparse
import json
import os
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests
from dotenv import load_dotenv

# 加载 .env 中的 API key
load_dotenv()


# 平台配置：base_url 和对应的环境变量名
# 秘塔支持多 key，通过 --metaso-key 参数指定具体使用哪个环境变量
# 重要：脚本只能使用用户明确选定的 key，禁止自动切换或回退到其他 key
PLATFORM_CONFIG = {
    "official": {
        "base_url": os.getenv("MINIMAX_OFFICIAL_BASE_URL", "https://api.minimaxi.com"),
        "api_key_env": "MINIMAX_OFFICIAL_API_KEY",
    },
    "metaso": {
        "base_url": os.getenv("METASO_BASE_URL", "https://metaso.cn/api/minimax"),
        # 默认 key，可通过参数覆盖
        "api_key_env": "METASO_API_KEY",
    },
}

# 每个 API Key 的最大并发数（秘塔中转站限制）
MAX_CONCURRENCY_PER_KEY = 4


def load_asset_packs(manifest_dir: str, segment_ids: list[str]) -> list[dict]:
    """读取每个 SEG 的 asset pack 文件。"""
    packs = []
    for seg_id in segment_ids:
        path = Path(manifest_dir) / f"{seg_id}_asset_pack.json"
        if not path.exists():
            raise FileNotFoundError(f"找不到 asset pack: {path}")
        with open(path, "r", encoding="utf-8") as f:
            packs.append(json.load(f))
    return packs


def build_request_body(pack: dict) -> dict:
    """根据 asset pack 组装 Minimax 视频生成请求体。"""
    content = [{"type": "text", "text": pack["prompt"]}]

    # 多模态参考图
    ref_images = pack.get("reference_images", [])
    first_frame_url = pack.get("first_frame")

    # 互斥规则：如果已有 reference_image，则不能再出现 first_frame。
    # 把 first_frame 作为最后一张 reference_image 加入，保持 prompt 编号顺序。
    all_images = list(ref_images)
    if first_frame_url:
        all_images.append({
            "type": "image_url",
            "image_url": {"url": first_frame_url},
            "role": "reference_image",
        })

    for img in all_images:
        # 兼容两种字段：url 或 image_url.url
        if "url" in img:
            url = img["url"]
        else:
            url = img.get("image_url", {}).get("url", "")
        content.append({
            "type": "image_url",
            "image_url": {"url": url},
            "role": img.get("role", "reference_image"),
        })

    # 参考音频
    for audio in pack.get("reference_audios", []):
        # 兼容两种字段：url 或 audio_url.url
        if "url" in audio:
            url = audio["url"]
        else:
            url = audio.get("audio_url", {}).get("url", "")
        content.append({
            "type": "audio_url",
            "audio_url": {"url": url},
            "role": audio.get("role", "reference_audio"),
        })

    # 参考视频（如果有）
    for video in pack.get("reference_videos", []):
        # 兼容两种字段：url 或 video_url.url
        if "url" in video:
            url = video["url"]
        else:
            url = video.get("video_url", {}).get("url", "")
        content.append({
            "type": "video_url",
            "video_url": {"url": url},
            "role": video.get("role", "reference_video"),
        })

    body = {
        "model": "MiniMax-H3",
        "content": content,
        "resolution": pack.get("resolution", "2K"),
        "duration": pack.get("duration", 5),
        "ratio": pack.get("ratio", "9:16"),
    }

    # 如果 asset pack 指定了 callback_url，也带上
    if pack.get("callback_url"):
        body["callback_url"] = pack["callback_url"]

    return body


def submit_one(pack: dict, platform: str, api_key_env: str) -> dict:
    """提交单个 SEG 的生成任务。"""
    cfg = PLATFORM_CONFIG[platform]
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"环境变量 {api_key_env} 未设置")

    body = build_request_body(pack)
    url = f"{cfg['base_url'].rstrip('/')}/v2/video_generation"

    response = requests.post(
        url,
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json=body,
        timeout=60,
    )

    # 非 200 时抛出异常，由调用方处理
    response.raise_for_status()
    return response.json()


def submit_one_with_retry(
    pack: dict,
    platform: str,
    api_key_env: str,
    dry_run: bool = False,
) -> dict:
    """提交单个 SEG，带基础错误分类。"""
    seg_id = pack["segment_id"]

    if dry_run:
        body = build_request_body(pack)
        print(f"[dry-run] {seg_id} 请求体:\n{json.dumps(body, ensure_ascii=False, indent=2)}")
        return {
            "segment_id": seg_id,
            "task_id": "dry-run",
            "status": "dry-run",
            "api_key_env": api_key_env,
        }

    try:
        resp = submit_one(pack, platform, api_key_env)
        task_id = resp.get("task_id")
        print(f"{seg_id} 提交成功，task_id: {task_id}")
        return {
            "segment_id": seg_id,
            "task_id": task_id,
            "status": "submitted",
            "api_key_env": api_key_env,
        }
    except requests.HTTPError as e:
        print(f"{seg_id} 提交失败: {e.response.status_code} {e.response.text}")
        return {
            "segment_id": seg_id,
            "task_id": None,
            "status": "failed",
            "api_key_env": api_key_env,
            "error": {
                "http_code": e.response.status_code,
                "body": e.response.text,
            },
        }
    except Exception as e:
        print(f"{seg_id} 提交异常: {e}")
        return {
            "segment_id": seg_id,
            "task_id": None,
            "status": "failed",
            "api_key_env": api_key_env,
            "error": {"message": str(e)},
        }


def submit_batch(
    manifest_dir: str,
    segment_ids: list[str],
    platform: str,
    api_key_env: str,
    output_log: str,
    dry_run: bool = False,
) -> list[dict]:
    """批量提交 SEG 生成任务，按 API Key 控制并发。"""
    packs = load_asset_packs(manifest_dir, segment_ids)
    results = []

    print(f"平台: {platform} | 使用 API Key: {api_key_env}")
    print(f"最大并发数: {MAX_CONCURRENCY_PER_KEY} | 共 {len(packs)} 个 SEG\n")

    # 使用线程池控制同一 key 的并发请求数
    with ThreadPoolExecutor(max_workers=MAX_CONCURRENCY_PER_KEY) as executor:
        futures = {
            executor.submit(
                submit_one_with_retry,
                pack,
                platform,
                api_key_env,
                dry_run,
            ): pack
            for pack in packs
        }

        for future in as_completed(futures):
            result = future.result()
            results.append(result)

    # 保存提交记录
    log_path = Path(output_log)
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"\n提交记录已保存: {output_log}")

    return results


def main():
    parser = argparse.ArgumentParser(description="提交一批 Minimax H3 视频生成任务")
    parser.add_argument("--manifest-dir", required=True, help="asset pack 所在目录")
    parser.add_argument("--segments", required=True, nargs="+", help="要提交的 SEG ID 列表")
    parser.add_argument("--platform", choices=["official", "metaso"], default="official", help="平台")
    parser.add_argument(
        "--metaso-key",
        default="METASO_API_KEY",
        help="秘塔中转站使用的 API Key 环境变量名（例如 METASO_API_KEY_1）",
    )
    parser.add_argument("--output-log", default="00_元数据/清单/video_submission_log.json", help="提交记录保存路径")
    parser.add_argument("--dry-run", action="store_true", help="只组装请求体，不真正提交")

    args = parser.parse_args()

    # 确定实际使用的 API Key 环境变量名
    if args.platform == "official":
        api_key_env = PLATFORM_CONFIG["official"]["api_key_env"]
    else:
        api_key_env = args.metaso_key

    submit_batch(
        manifest_dir=args.manifest_dir,
        segment_ids=args.segments,
        platform=args.platform,
        api_key_env=api_key_env,
        output_log=args.output_log,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
