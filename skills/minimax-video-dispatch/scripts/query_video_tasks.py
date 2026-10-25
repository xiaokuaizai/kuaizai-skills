#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
query_video_tasks.py
批量查询 Minimax H3 视频生成任务状态，并下载成功的产物。
支持通过 --metaso-key 指定秘塔中转站使用的具体 API Key 环境变量名。
"""

import argparse
import json
import os
import time
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv()


PLATFORM_CONFIG = {
    "official": {
        "base_url": os.getenv("MINIMAX_OFFICIAL_BASE_URL", "https://api.minimaxi.com"),
        "api_key_env": "MINIMAX_OFFICIAL_API_KEY",
    },
    "metaso": {
        "base_url": os.getenv("METASO_BASE_URL", "https://metaso.cn/api/minimax"),
        # 默认 key，可通过 --metaso-key 参数指定；禁止自动切换到其他 key
        "api_key_env": "METASO_API_KEY",
    },
}


def query_task(task_id: str, platform: str, api_key_env: str) -> dict:
    """查询单个任务状态。"""
    cfg = PLATFORM_CONFIG[platform]
    api_key = os.getenv(api_key_env)
    if not api_key:
        raise ValueError(f"环境变量 {api_key_env} 未设置")

    url = f"{cfg['base_url'].rstrip('/')}/v2/query/video_generation/{task_id}"
    response = requests.get(
        url,
        headers={"Authorization": f"Bearer {api_key}"},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def download_video(url: str, save_path: str) -> str:
    """从 URL 下载视频到本地。"""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return save_path


def poll_tasks(
    submission_log: str,
    platform: str,
    api_key_env: str,
    output_dir: str,
    output_log: str,
    poll_interval: int = 10,
    max_poll_time: int = 1800,
) -> list[dict]:
    """轮询所有任务到终态，并下载成功产物。"""
    with open(submission_log, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    pending = [t for t in tasks if t.get("status") == "submitted" and t.get("task_id")]
    results = [t for t in tasks if t not in pending]
    start_time = time.time()

    while pending and (time.time() - start_time) < max_poll_time:
        still_pending = []
        for task in pending:
            seg_id = task["segment_id"]
            task_id = task["task_id"]
            try:
                resp = query_task(task_id, platform, api_key_env)
                task_info = resp.get("task", {})
                status = task_info.get("status")

                result = {
                    "segment_id": seg_id,
                    "task_id": task_id,
                    "status": status,
                    "resolution": task_info.get("resolution"),
                    "duration": task_info.get("duration"),
                    "ratio": task_info.get("ratio"),
                    "api_key_env": api_key_env,
                }

                if status == "succeeded":
                    video_url = task_info.get("content", {}).get("url")
                    result["content_url"] = video_url
                    # 下载视频
                    save_path = Path(output_dir) / seg_id / f"{seg_id}.mp4"
                    try:
                        download_video(video_url, str(save_path))
                        result["local_path"] = str(save_path)
                        print(f"{seg_id} 成功，已下载到 {save_path}")
                    except Exception as e:
                        result["status"] = "download_failed"
                        result["error"] = str(e)
                        print(f"{seg_id} 下载失败: {e}")
                elif status == "failed":
                    error = task_info.get("error", {})
                    result["error"] = error
                    print(f"{seg_id} 失败: {error}")
                else:
                    # queued / running，继续轮询
                    still_pending.append(task)
                    print(f"{seg_id} 状态: {status}，继续等待...")

                if status in ("succeeded", "failed", "cancelled"):
                    results.append(result)
            except requests.HTTPError as e:
                print(f"{seg_id} 查询失败: {e.response.status_code} {e.response.text}")
                still_pending.append(task)
            except Exception as e:
                print(f"{seg_id} 查询异常: {e}")
                still_pending.append(task)

            time.sleep(0.5)

        pending = still_pending
        if pending:
            time.sleep(poll_interval)

    # 超时的任务
    for task in pending:
        results.append({
            "segment_id": task["segment_id"],
            "task_id": task["task_id"],
            "status": "timeout",
            "api_key_env": api_key_env,
        })
        print(f"{task['segment_id']} 轮询超时")

    # 保存结果
    Path(output_log).parent.mkdir(parents=True, exist_ok=True)
    with open(output_log, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f"查询结果已保存: {output_log}")

    return results


def main():
    parser = argparse.ArgumentParser(description="批量查询 Minimax H3 视频生成任务")
    parser.add_argument("--submission-log", required=True, help="submit_video_batch.py 生成的提交记录")
    parser.add_argument("--platform", choices=["official", "metaso"], default="official", help="平台")
    parser.add_argument(
        "--metaso-key",
        default="METASO_API_KEY",
        help="秘塔中转站使用的 API Key 环境变量名（例如 METASO_API_KEY_1）",
    )
    parser.add_argument("--output-dir", default="04_支线产出/产出", help="视频下载目录")
    parser.add_argument("--output-log", default="00_元数据/清单/video_query_log.json", help="查询结果保存路径")
    parser.add_argument("--poll-interval", type=int, default=10, help="轮询间隔（秒）")
    parser.add_argument("--max-poll-time", type=int, default=1800, help="最大轮询时间（秒）")

    args = parser.parse_args()

    if args.platform == "official":
        api_key_env = PLATFORM_CONFIG["official"]["api_key_env"]
    else:
        api_key_env = args.metaso_key

    poll_tasks(
        submission_log=args.submission_log,
        platform=args.platform,
        api_key_env=api_key_env,
        output_dir=args.output_dir,
        output_log=args.output_log,
        poll_interval=args.poll_interval,
        max_poll_time=args.max_poll_time,
    )


if __name__ == "__main__":
    main()
