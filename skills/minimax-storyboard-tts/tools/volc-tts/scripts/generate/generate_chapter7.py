import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 第七章完整对话音频生成。
# 读取 output/chapter7/ch7_tts_tasks.json，逐句生成 mp3，并写入真实 manifest。
import argparse
import base64
import json
import os
import time
import uuid
from collections import Counter
from datetime import datetime
from pathlib import Path

import requests

from src.config import ACCESS_TOKEN, API_URL, APP_ID, DEFAULT_SPEED_RATIO, PROXIES


TASK_FILE = Path("output/chapter7/ch7_tts_tasks.json")
OUTPUT_DIR = Path("output/chapter7/audio")
MANIFEST_DIR = Path("output/chapter7/manifests")
MANIFEST_FILE = MANIFEST_DIR / "ch7_tts_manifest.json"
EXPECTED_COUNT = 40
HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def load_tasks():
    """读取第七章 TTS 任务清单。"""
    with TASK_FILE.open("r", encoding="utf-8") as f:
        data = json.load(f)
    return data, data.get("tasks", [])


def validate_ready(tasks):
    """生成前检查：避免数量、ID、音色、文本和凭证出错。"""
    problems = []
    task_ids = [task.get("task_id") for task in tasks]
    duplicate_ids = [
        task_id
        for task_id, count in Counter(task_ids).items()
        if task_id and count > 1
    ]
    empty_id_tasks = [index + 1 for index, task in enumerate(tasks) if not task.get("task_id")]
    empty_text_ids = [task.get("task_id", f"第{index + 1}条") for index, task in enumerate(tasks) if not task.get("text_en")]
    empty_voice_ids = [task.get("task_id", f"第{index + 1}条") for index, task in enumerate(tasks) if not task.get("voice_type")]

    if len(tasks) != EXPECTED_COUNT:
        problems.append(f"第七章任务数应为 {EXPECTED_COUNT}，当前为 {len(tasks)}")
    if duplicate_ids:
        problems.append(f"存在重复任务 ID: {', '.join(duplicate_ids)}")
    if empty_id_tasks:
        problems.append(f"存在空任务 ID: {', '.join(map(str, empty_id_tasks))}")
    if empty_text_ids:
        problems.append(f"存在空英文文本: {', '.join(empty_text_ids)}")
    if empty_voice_ids:
        problems.append(f"存在空 voice_type: {', '.join(empty_voice_ids)}")
    if not APP_ID:
        problems.append("缺少 VOLC_APP_ID")
    if not ACCESS_TOKEN:
        problems.append("缺少 VOLC_ACCESS_TOKEN")

    return {
        "line_count": len(tasks),
        "role_counts": dict(Counter(task.get("role", "UNKNOWN") for task in tasks)),
        "voice_counts": dict(Counter(task.get("voice_type", "UNKNOWN") for task in tasks)),
        "problems": problems,
    }


def print_ready_report(report):
    """打印检查报告，方便生成前确认。"""
    print("=" * 70)
    print("第七章 TTS 生成前检查")
    print(f"任务数: {report['line_count']}")
    print("角色统计:")
    for role, count in sorted(report["role_counts"].items()):
        print(f"  {role}: {count}")
    print("音色统计:")
    for voice_type, count in sorted(report["voice_counts"].items()):
        print(f"  {voice_type}: {count}")

    if report["problems"]:
        print("\n[FAIL] 检查未通过:")
        for problem in report["problems"]:
            print(f"  - {problem}")
    else:
        print("\n[OK] 检查通过，可以开始生成。")


def synthesize(text, voice_type, speed):
    """调用 V1 HTTP 接口合成单句 mp3。"""
    payload = {
        "app": {"appid": APP_ID, "token": ACCESS_TOKEN, "cluster": "volcano_tts"},
        "user": {"uid": "novel_tts_user"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": speed,
            "rate": 24000,
        },
        "request": {"reqid": str(uuid.uuid4()), "text": text, "operation": "query"},
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, proxies=PROXIES, timeout=60)
        result = resp.json()
    except Exception as e:
        return None, f"请求异常: {e}"

    if result.get("code") == 3000 and "data" in result:
        return base64.b64decode(result["data"]), None

    return None, result.get("message", f"code={result.get('code')}")


def task_output_path(task):
    """根据任务中的 output_wav 字段确定输出路径。"""
    configured_path = task.get("output_wav")
    if configured_path:
        return Path(configured_path)
    return OUTPUT_DIR / f"{task['task_id']}.mp3"


def generate_all(data, tasks, force=False):
    """生成第七章全部 TTS 音频，并写入 manifest。"""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
    manifest = []
    stats = {"success": 0, "failed": 0, "skipped": 0}

    print("=" * 70)
    print("第七章 TTS 音频生成")
    print(f"接口: V1 HTTP | 总句数: {len(tasks)}")
    print(f"输出目录: {OUTPUT_DIR.resolve()}")
    print("=" * 70)

    for task in tasks:
        task_id = task["task_id"]
        role = task["role"]
        text = task["text_en"]
        voice_type = task["voice_type"]
        speed = task.get("speed", DEFAULT_SPEED_RATIO)
        output_path = task_output_path(task)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if output_path.exists() and not force:
            size = os.path.getsize(output_path)
            print(f"  [SKIP] {task_id} 已存在 ({size} bytes)")
            manifest.append({
                "id": task_id,
                "section": task.get("section"),
                "role": role,
                "voice_type": voice_type,
                "speed": speed,
                "text": text,
                "path": str(output_path).replace("\\", "/"),
                "size": size,
                "status": "skipped",
            })
            stats["skipped"] += 1
            continue

        audio, err = synthesize(text, voice_type, speed)
        if audio:
            with output_path.open("wb") as f:
                f.write(audio)
            print(f"  [OK] {task_id} {role} ({len(audio)} bytes, speed={speed})")
            manifest.append({
                "id": task_id,
                "section": task.get("section"),
                "role": role,
                "voice_type": voice_type,
                "speed": speed,
                "text": text,
                "path": str(output_path).replace("\\", "/"),
                "size": len(audio),
                "status": "success",
            })
            stats["success"] += 1
        else:
            print(f"  [FAIL] {task_id} {role}: {err}")
            manifest.append({
                "id": task_id,
                "section": task.get("section"),
                "role": role,
                "voice_type": voice_type,
                "speed": speed,
                "text": text,
                "path": None,
                "size": 0,
                "status": "failed",
                "error": err,
            })
            stats["failed"] += 1

        time.sleep(0.3)  # 控制请求频率，避免连续请求过快。

    with MANIFEST_FILE.open("w", encoding="utf-8") as f:
        json.dump({
            "chapter": data.get("chapter", "07"),
            "source": data.get("source"),
            "generated_at": datetime.now().isoformat(timespec="seconds"),
            "total": sum(stats.values()),
            "stats": stats,
            "manifest": manifest,
        }, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("生成完成")
    print(f"成功: {stats['success']} | 跳过: {stats['skipped']} | 失败: {stats['failed']}")
    print(f"清单文件: {MANIFEST_FILE.resolve()}")
    return stats


def main():
    parser = argparse.ArgumentParser(description="生成第七章 TTS 音频")
    parser.add_argument("--check-only", action="store_true", help="只做生成前检查，不调用 TTS 接口")
    parser.add_argument("--force", action="store_true", help="强制重新生成已存在的音频")
    args = parser.parse_args()

    data, tasks = load_tasks()
    report = validate_ready(tasks)
    print_ready_report(report)

    if report["problems"]:
        raise SystemExit(1)
    if args.check_only:
        return

    stats = generate_all(data, tasks, force=args.force)
    raise SystemExit(1 if stats["failed"] else 0)


if __name__ == "__main__":
    main()
