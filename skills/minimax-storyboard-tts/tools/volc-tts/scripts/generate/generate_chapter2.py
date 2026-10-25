import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 第二章完整对话音频生成
# 读取 data/chapter2_lines.json，为每句对白生成 mp3。
import argparse
import base64
import json
import os
import re
import time
import uuid
from collections import Counter

import requests

from src.config import (
    ACCESS_TOKEN,
    API_URL,
    APP_ID,
    DEFAULT_SPEED_RATIO,
    PROXIES,
    ROLE_DISPLAY,
    VOICE_CONFIG,
)

DATA_FILE = "data/chapter2_lines.json"
OUTPUT_BASE = "output/chapter2"
HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json",
}
SPEED_RATIO = DEFAULT_SPEED_RATIO


def sanitize_dirname(name):
    """把中文段落名转成合法且稳定的文件夹名"""
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    return name[:80]


def load_lines():
    """读取第二章台词数据"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def iter_lines(scenes):
    """按场景顺序遍历全部台词"""
    for scene in scenes:
        for line in scene["lines"]:
            yield scene, line


def validate_ready(scenes):
    """生成前检查：数量、角色、凭证和音色配置"""
    lines = [line for _, line in iter_lines(scenes)]
    role_counts = Counter(line["role"] for line in lines)
    missing_roles = sorted(set(role_counts) - set(VOICE_CONFIG))
    duplicate_ids = [
        line_id
        for line_id, count in Counter(line["id"] for line in lines).items()
        if count > 1
    ]
    empty_text_ids = [line["id"] for line in lines if not line.get("text")]
    problems = []

    if len(scenes) != 6:
        problems.append(f"场景数应为 6，当前为 {len(scenes)}")
    if len(lines) != 82:
        problems.append(f"台词数应为 82，当前为 {len(lines)}")
    if missing_roles:
        problems.append(f"存在未配置音色的角色: {', '.join(missing_roles)}")
    if duplicate_ids:
        problems.append(f"存在重复台词 ID: {', '.join(duplicate_ids)}")
    if empty_text_ids:
        problems.append(f"存在空台词: {', '.join(empty_text_ids)}")
    if not APP_ID:
        problems.append("缺少 VOLC_APP_ID")
    if not ACCESS_TOKEN:
        problems.append("缺少 VOLC_ACCESS_TOKEN")

    return {
        "scene_count": len(scenes),
        "line_count": len(lines),
        "role_counts": dict(role_counts),
        "speed_ratio": SPEED_RATIO,
        "output_base": OUTPUT_BASE,
        "problems": problems,
    }


def print_ready_report(report):
    """打印生成前检查报告"""
    print("=" * 70)
    print("第二章 TTS 生成前检查")
    print(f"场景数: {report['scene_count']} | 台词数: {report['line_count']}")
    print(f"语速: {report['speed_ratio']} | 输出目录: {report['output_base']}")
    print("角色统计:")
    for role, count in sorted(report["role_counts"].items()):
        print(f"  {ROLE_DISPLAY.get(role, role)} ({role}): {count}")

    if report["problems"]:
        print("\n[FAIL] 检查未通过:")
        for item in report["problems"]:
            print(f"  - {item}")
    else:
        print("\n[OK] 检查通过，可以开始生成。")


def synthesize(text, voice_type):
    """调用V1 HTTP接口合成单句"""
    payload = {
        "app": {
            "appid": APP_ID,
            "token": ACCESS_TOKEN,
            "cluster": "volcano_tts",
        },
        "user": {"uid": "novel_tts_user"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": SPEED_RATIO,
            "rate": 24000,
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query",
        },
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, proxies=PROXIES, timeout=60)
        result = resp.json()
    except Exception as e:
        return None, f"请求异常: {e}"

    if result.get("code") == 3000 and "data" in result:
        return base64.b64decode(result["data"]), None

    return None, result.get("message", f"code={result.get('code')}")


def generate_all(scenes):
    """生成第二章全部对白音频"""
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    manifest = []
    stats = {"success": 0, "failed": 0, "skipped": 0}
    total_lines = sum(len(scene["lines"]) for scene in scenes)

    print("=" * 70)
    print("第二章完整对话音频生成")
    print(f"接口: V1 HTTP | 语速: {SPEED_RATIO} | 总句数: {total_lines}")
    print("=" * 70)

    for scene in scenes:
        scene_name = scene["scene"]
        scene_dir = sanitize_dirname(scene_name)
        scene_path = os.path.join(OUTPUT_BASE, scene_dir)
        os.makedirs(scene_path, exist_ok=True)

        print(f"\n场景: {scene_name}")

        for line in scene["lines"]:
            line_id = line["id"]
            role = line["role"]
            text = line["text"]
            voice_type = VOICE_CONFIG.get(role)
            display = ROLE_DISPLAY.get(role, role)

            if not voice_type:
                print(f"  [FAIL] 未知角色: {role} ({line_id})")
                manifest.append({
                    "id": line_id,
                    "role": role,
                    "display": display,
                    "voice_type": None,
                    "text": text,
                    "path": None,
                    "size": 0,
                    "status": "failed",
                    "error": "未知角色",
                })
                stats["failed"] += 1
                continue

            safe_id = re.sub(r"[^\w\-]", "_", line_id)
            filename = f"{safe_id}_{role}.mp3"
            output_path = os.path.join(scene_path, filename)
            rel_path = os.path.relpath(output_path, OUTPUT_BASE).replace("\\", "/")

            # 已存在则跳过，方便失败后继续生成。
            if os.path.exists(output_path):
                print(f"  [SKIP] {line_id} 已存在")
                manifest.append({
                    "id": line_id,
                    "role": role,
                    "display": display,
                    "voice_type": voice_type,
                    "text": text,
                    "path": rel_path,
                    "size": os.path.getsize(output_path),
                    "status": "skipped",
                })
                stats["skipped"] += 1
                continue

            audio, err = synthesize(text, voice_type)
            if audio:
                with open(output_path, "wb") as f:
                    f.write(audio)
                print(f"  [OK] {line_id} {display} ({len(audio)} bytes)")
                manifest.append({
                    "id": line_id,
                    "role": role,
                    "display": display,
                    "voice_type": voice_type,
                    "text": text,
                    "path": rel_path,
                    "size": len(audio),
                    "status": "success",
                })
                stats["success"] += 1
            else:
                print(f"  [FAIL] {line_id} {display}: {err}")
                manifest.append({
                    "id": line_id,
                    "role": role,
                    "display": display,
                    "voice_type": voice_type,
                    "text": text,
                    "path": None,
                    "size": 0,
                    "status": "failed",
                    "error": err,
                })
                stats["failed"] += 1

            time.sleep(0.3)  # 控制请求频率，避免连续请求过快。

    manifest_path = os.path.join(OUTPUT_BASE, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "chapter": 2,
            "speed_ratio": SPEED_RATIO,
            "total": sum(stats.values()),
            "stats": stats,
            "manifest": manifest,
        }, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("生成完成")
    print(f"成功: {stats['success']} | 跳过: {stats['skipped']} | 失败: {stats['failed']}")
    print(f"清单文件: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="生成第二章 TTS 音频")
    parser.add_argument(
        "--check-only",
        action="store_true",
        help="只做生成前检查，不调用 TTS 接口",
    )
    args = parser.parse_args()

    scenes = load_lines()
    report = validate_ready(scenes)

    if args.check_only:
        print_ready_report(report)
        raise SystemExit(1 if report["problems"] else 0)

    if report["problems"]:
        print_ready_report(report)
        raise SystemExit(1)

    generate_all(scenes)


if __name__ == "__main__":
    main()
