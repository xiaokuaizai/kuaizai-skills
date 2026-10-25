#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
archive_video_outputs.py
下载生成产物并归档旧版文件。
"""

import argparse
import json
import shutil
from datetime import datetime
from pathlib import Path

import requests


def archive_existing_file(file_path: str, reason: str) -> None:
    """
    如果文件已存在，把它归档到同目录的 旧版/ 文件夹。
    """
    path = Path(file_path)
    if not path.exists():
        return

    archive_dir = path.parent / "旧版"
    archive_dir.mkdir(parents=True, exist_ok=True)

    # 计算版本号
    base_name = path.stem
    ext = path.suffix
    version = 1
    while (archive_dir / f"{base_name}_旧版v{version}{ext}").exists():
        version += 1

    archive_path = archive_dir / f"{base_name}_旧版v{version}{ext}"
    shutil.move(str(path), str(archive_path))

    # 记录说明
    note_path = archive_dir / "说明.txt"
    with open(note_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | 原文件: {path.name} | "
                f"归档为: {archive_path.name} | 原因: {reason}\n")

    print(f"已归档旧版: {archive_path}")


def download_file(url: str, save_path: str) -> str:
    """下载文件到本地。"""
    Path(save_path).parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=120) as r:
        r.raise_for_status()
        with open(save_path, "wb") as f:
            for chunk in r.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
    return save_path


def archive_outputs(
    query_log: str,
    output_base_dir: str,
    reason: str = "重新生成",
) -> list[dict]:
    """根据查询日志下载视频并归档旧版。"""
    with open(query_log, "r", encoding="utf-8") as f:
        tasks = json.load(f)

    updated = []
    for task in tasks:
        seg_id = task.get("segment_id")
        status = task.get("status")
        content_url = task.get("content_url")

        if status != "succeeded" or not content_url:
            updated.append(task)
            continue

        # 产物保存路径
        save_path = Path(output_base_dir) / seg_id / f"{seg_id}.mp4"

        # 归档旧版
        archive_existing_file(str(save_path), reason)

        # 下载新版
        try:
            download_file(content_url, str(save_path))
            task["local_path"] = str(save_path)
            print(f"{seg_id} 已下载到 {save_path}")
        except Exception as e:
            task["status"] = "download_failed"
            task["error"] = str(e)
            print(f"{seg_id} 下载失败: {e}")

        updated.append(task)

    # 回写日志
    with open(query_log, "w", encoding="utf-8") as f:
        json.dump(updated, f, ensure_ascii=False, indent=2)

    return updated


def main():
    parser = argparse.ArgumentParser(description="下载并归档视频生成产物")
    parser.add_argument("--query-log", required=True, help="query_video_tasks.py 生成的查询结果")
    parser.add_argument("--output-base-dir", default="04_支线产出/产出", help="产物保存根目录")
    parser.add_argument("--reason", default="重新生成", help="归档原因")

    args = parser.parse_args()
    archive_outputs(
        query_log=args.query_log,
        output_base_dir=args.output_base_dir,
        reason=args.reason,
    )


if __name__ == "__main__":
    main()
