#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assemble_full_branch.py
按 Scene 顺序拼接所有场次视频，生成完整支线视频。
"""

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def get_duration(video_path: str) -> float:
    """获取视频时长。"""
    cmd = [
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "csv=p=0",
        video_path,
    ]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
    return float(result.stdout.strip())


def archive_existing_file(file_path: str, reason: str) -> None:
    """如果文件已存在，归档到 旧版/ 文件夹。"""
    path = Path(file_path)
    if not path.exists():
        return

    archive_dir = path.parent / "旧版"
    archive_dir.mkdir(parents=True, exist_ok=True)

    base_name = path.stem
    ext = path.suffix
    version = 1
    while (archive_dir / f"{base_name}_旧版v{version}{ext}").exists():
        version += 1

    archive_path = archive_dir / f"{base_name}_旧版v{version}{ext}"
    shutil.move(str(path), str(archive_path))

    note_path = archive_dir / "说明.txt"
    with open(note_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat()} | 原文件: {path.name} | "
                f"归档为: {archive_path.name} | 原因: {reason}\n")


def assemble_full_branch(
    branch: str,
    scene_assembly_log_path: str,
    output_base_dir: str,
) -> dict:
    """按 Scene 顺序拼接完整支线视频。"""
    with open(scene_assembly_log_path, "r", encoding="utf-8") as f:
        log = json.load(f)

    # 只取成功的 Scene
    succeeded_scenes = [
        s for s in log.get("scenes", [])
        if s.get("status") == "succeeded"
    ]

    if not succeeded_scenes:
        raise ValueError("没有可用的 Scene 视频，无法拼接完整支线视频")

    # 按 Scene 编号排序
    succeeded_scenes.sort(key=lambda s: int(re.search(r"\d+", s["scene_id"]).group()))

    # 检查是否有 Scene 失败
    all_scenes = log.get("scenes", [])
    failed_scenes = [s["scene_id"] for s in all_scenes if s.get("status") != "succeeded"]
    if failed_scenes:
        raise ValueError(f"以下 Scene 未成功拼接，不能生成完整视频: {failed_scenes}")

    scene_paths = [s["output_path"] for s in succeeded_scenes]
    expected_duration = sum(get_duration(p) for p in scene_paths)

    # 输出目录
    full_video_dir = Path(output_base_dir) / branch / "完整视频"
    full_video_dir.mkdir(parents=True, exist_ok=True)
    output_path = full_video_dir / f"{branch}_完整版.mp4"

    # 生成 concat list
    concat_list_path = full_video_dir / f"{branch}_concat.txt"
    with open(concat_list_path, "w", encoding="utf-8") as f:
        for p in scene_paths:
            f.write(f"file '{p}'\n")

    # 归档旧版并拼接
    archive_existing_file(str(output_path), "重新生成")
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", str(concat_list_path),
        "-c", "copy",
        str(output_path),
    ]
    subprocess.run(cmd, check=True)

    actual_duration = get_duration(str(output_path))
    if abs(actual_duration - expected_duration) > 0.2:
        print(f"警告：完整视频时长校验不通过，期望 {expected_duration}，实际 {actual_duration}")

    result = {
        "branch": branch,
        "output_path": str(output_path),
        "duration": actual_duration,
        "scene_ids": [s["scene_id"] for s in succeeded_scenes],
        "assembled_at": datetime.now().isoformat(),
        "status": "succeeded",
    }

    # 更新 scene_assembly_log.json
    log["full_video"] = result
    with open(scene_assembly_log_path, "w", encoding="utf-8") as f:
        json.dump(log, f, ensure_ascii=False, indent=2)

    print(f"完整支线视频已生成: {output_path}")
    return result


def main():
    parser = argparse.ArgumentParser(description="拼接完整支线视频")
    parser.add_argument("--branch", required=True, help="支线名称")
    parser.add_argument("--scene-assembly-log", default="00_元数据/清单/scene_assembly_log.json", help="Scene 拼接日志路径")
    parser.add_argument("--output-base-dir", default="04_支线产出/产出", help="输出根目录")

    args = parser.parse_args()
    assemble_full_branch(
        branch=args.branch,
        scene_assembly_log_path=args.scene_assembly_log,
        output_base_dir=args.output_base_dir,
    )


if __name__ == "__main__":
    main()
