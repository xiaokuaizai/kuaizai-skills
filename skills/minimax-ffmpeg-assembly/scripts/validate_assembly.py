#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
validate_assembly.py
校验视频编码一致性和拼接输出时长。
"""

import argparse
import json
import subprocess
from pathlib import Path


def run_ffprobe(video_path: str, args: list[str]) -> str:
    """调用 ffprobe 获取视频信息。"""
    cmd = ["ffprobe", "-v", "error"] + args + [video_path]
    result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffprobe 失败: {result.stderr.strip()}")
    return result.stdout.strip()


def get_video_info(video_path: str) -> dict:
    """获取视频的编码参数信息。"""
    info = {}
    info["width"] = int(run_ffprobe(video_path, ["-select_streams", "v:0", "-show_entries", "stream=width", "-of", "csv=s=x:p=0"]))
    info["height"] = int(run_ffprobe(video_path, ["-select_streams", "v:0", "-show_entries", "stream=height", "-of", "csv=s=x:p=0"]))
    info["video_codec"] = run_ffprobe(video_path, ["-select_streams", "v:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0"])
    info["pix_fmt"] = run_ffprobe(video_path, ["-select_streams", "v:0", "-show_entries", "stream=pix_fmt", "-of", "csv=p=0"])
    info["frame_rate"] = run_ffprobe(video_path, ["-select_streams", "v:0", "-show_entries", "stream=r_frame_rate", "-of", "csv=p=0"])
    info["audio_codec"] = run_ffprobe(video_path, ["-select_streams", "a:0", "-show_entries", "stream=codec_name", "-of", "csv=p=0"])
    info["sample_rate"] = run_ffprobe(video_path, ["-select_streams", "a:0", "-show_entries", "stream=sample_rate", "-of", "csv=p=0"])

    return info


def get_duration(video_path: str) -> float:
    """获取视频时长（秒）。"""
    duration_str = run_ffprobe(video_path, ["-show_entries", "format=duration", "-of", "csv=p=0"])
    return float(duration_str)


def check_consistency(video_paths: list[str]) -> dict:
    """检查所有视频编码参数是否一致。"""
    if not video_paths:
        return {"consistent": True, "differences": []}

    baseline = get_video_info(video_paths[0])
    differences = []

    for path in video_paths[1:]:
        info = get_video_info(path)
        diff = {}
        for key in baseline:
            if baseline[key] != info[key]:
                diff[key] = {"expected": baseline[key], "actual": info[key]}
        if diff:
            differences.append({"file": path, "diff": diff})

    return {
        "consistent": len(differences) == 0,
        "baseline_file": video_paths[0],
        "baseline": baseline,
        "differences": differences,
    }


def validate_output(output_path: str, expected_duration: float, tolerance: float = 0.2) -> dict:
    """校验输出视频时长。"""
    actual_duration = get_duration(output_path)
    diff = abs(actual_duration - expected_duration)
    return {
        "valid": diff <= tolerance,
        "expected_duration": expected_duration,
        "actual_duration": actual_duration,
        "diff": diff,
    }


def main():
    parser = argparse.ArgumentParser(description="校验视频编码一致性和拼接输出时长")
    parser.add_argument("--inputs", nargs="+", required=True, help="输入视频路径列表")
    parser.add_argument("--output", help="输出视频路径（可选，校验时长用）")
    parser.add_argument("--expected-duration", type=float, help="期望的输出时长（秒）")
    parser.add_argument("--output-json", help="输出 JSON 报告路径")

    args = parser.parse_args()

    report = {
        "consistency": check_consistency(args.inputs),
    }

    if args.output and args.expected_duration:
        report["duration_validation"] = validate_output(args.output, args.expected_duration)

    if args.output_json:
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"校验报告已保存: {args.output_json}")

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
