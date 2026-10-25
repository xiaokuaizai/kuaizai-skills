#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
assemble_scenes.py
按 Scene 拼接 SEG 视频，输出到场次视频目录。
"""

import argparse
import json
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


def load_video_generation_log(log_path: str) -> dict:
    """读取 video_generation_log.json。"""
    with open(log_path, "r", encoding="utf-8") as f:
        return json.load(f)


def parse_scene_mapping(segment_doc_path: str) -> dict:
    """
    从 doc/视频分段.md 中解析 Scene -> SEG 列表映射。
    这里用简单正则匹配表格行，实际格式以文档为准。
    """
    scene_map = {}
    text = Path(segment_doc_path).read_text(encoding="utf-8")
    # 简单匹配：| SEG-XX | Scene-YY | ...
    pattern = re.compile(r"\|\s*(SEG-\d+)\s*\|\s*(Scene-\d+)\s*\|")
    for match in pattern.finditer(text):
        seg_id = match.group(1)
        scene_id = match.group(2)
        scene_map.setdefault(scene_id, []).append(seg_id)

    # 每个 Scene 内的 SEG 按编号排序
    for scene_id in scene_map:
        scene_map[scene_id].sort(key=lambda x: int(re.search(r"\d+", x).group()))

    return scene_map


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


def get_seg_local_path(base_dir: str, branch: str, seg_id: str) -> str:
    """获取 SEG 视频的本地产物路径。"""
    return str(Path(base_dir) / branch / "分段视频" / seg_id / f"{seg_id}.mp4")


def run_ffmpeg_concat(concat_list_path: str, output_path: str) -> None:
    """调用 ffmpeg 拼接视频。"""
    cmd = [
        "ffmpeg",
        "-y",
        "-f", "concat",
        "-safe", "0",
        "-i", concat_list_path,
        "-c", "copy",
        output_path,
    ]
    subprocess.run(cmd, check=True)


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


def assemble_scenes(
    branch: str,
    segment_doc_path: str,
    generation_log_path: str,
    output_base_dir: str,
    output_log_path: str,
) -> dict:
    """按 Scene 拼接 SEG 视频。"""
    log = load_video_generation_log(generation_log_path)
    scene_map = parse_scene_mapping(segment_doc_path)

    # 只取 succeeded 的 SEG
    succeeded_segments = {
        task["segment_id"]: task
        for batch in log.get("batches", [])
        for task in batch.get("tasks", [])
        if task.get("status") == "succeeded"
    }

    scene_results = []

    for scene_id in sorted(scene_map.keys(), key=lambda x: int(re.search(r"\d+", x).group())):
        seg_ids = scene_map[scene_id]
        print(f"\n开始拼接 {scene_id}，包含 SEG: {seg_ids}")

        # 检查所有 SEG 是否成功
        missing = [seg for seg in seg_ids if seg not in succeeded_segments]
        if missing:
            print(f"{scene_id} 跳过，缺失 SEG: {missing}")
            scene_results.append({
                "scene_id": scene_id,
                "segment_ids": seg_ids,
                "status": "skipped",
                "reason": f"缺失 SEG: {missing}",
            })
            continue

        # 获取 SEG 视频路径
        video_paths = [get_seg_local_path(output_base_dir, branch, seg) for seg in seg_ids]
        missing_files = [p for p in video_paths if not Path(p).exists()]
        if missing_files:
            print(f"{scene_id} 跳过，找不到文件: {missing_files}")
            scene_results.append({
                "scene_id": scene_id,
                "segment_ids": seg_ids,
                "status": "skipped",
                "reason": f"找不到文件: {missing_files}",
            })
            continue

        # 输出路径
        scene_output_dir = Path(output_base_dir) / branch / "场次视频"
        scene_output_path = scene_output_dir / f"{scene_id}.mp4"
        scene_output_dir.mkdir(parents=True, exist_ok=True)

        # 单个 SEG 直接复制
        if len(video_paths) == 1:
            archive_existing_file(str(scene_output_path), "重新生成")
            shutil.copy(video_paths[0], str(scene_output_path))
            expected_duration = sum(get_duration(p) for p in video_paths)
            print(f"{scene_id} 只有 1 个 SEG，已复制")
        else:
            # 生成 concat list
            concat_list_path = scene_output_dir / f"{scene_id}_concat.txt"
            with open(concat_list_path, "w", encoding="utf-8") as f:
                for p in video_paths:
                    f.write(f"file '{p}'\n")

            # 归档旧版并拼接
            archive_existing_file(str(scene_output_path), "重新生成")
            run_ffmpeg_concat(str(concat_list_path), str(scene_output_path))
            expected_duration = sum(get_duration(p) for p in video_paths)
            print(f"{scene_id} 拼接完成: {scene_output_path}")

        # 校验时长
        actual_duration = get_duration(str(scene_output_path))
        if abs(actual_duration - expected_duration) > 0.2:
            print(f"警告：{scene_id} 时长校验不通过，期望 {expected_duration}，实际 {actual_duration}")

        scene_results.append({
            "scene_id": scene_id,
            "segment_ids": seg_ids,
            "output_path": str(scene_output_path),
            "duration": actual_duration,
            "status": "succeeded",
        })

    # 保存日志
    assembly_log = {
        "branch": branch,
        "assembled_at": datetime.now().isoformat(),
        "scenes": scene_results,
    }
    Path(output_log_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_log_path, "w", encoding="utf-8") as f:
        json.dump(assembly_log, f, ensure_ascii=False, indent=2)
    print(f"\n拼接日志已保存: {output_log_path}")

    return assembly_log


def main():
    parser = argparse.ArgumentParser(description="按 Scene 拼接 SEG 视频")
    parser.add_argument("--branch", required=True, help="支线名称")
    parser.add_argument("--segment-doc", default="doc/视频分段.md", help="视频分段文档路径")
    parser.add_argument("--generation-log", default="00_元数据/清单/video_generation_log.json", help="生成日志路径")
    parser.add_argument("--output-base-dir", default="04_支线产出/产出", help="输出根目录")
    parser.add_argument("--output-log", default="00_元数据/清单/scene_assembly_log.json", help="拼接日志输出路径")

    args = parser.parse_args()
    assemble_scenes(
        branch=args.branch,
        segment_doc_path=args.segment_doc,
        generation_log_path=args.generation_log,
        output_base_dir=args.output_base_dir,
        output_log_path=args.output_log,
    )


if __name__ == "__main__":
    main()
