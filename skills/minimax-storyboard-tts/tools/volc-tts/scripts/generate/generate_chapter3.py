import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 第三章完整对话音频生成
# 读取 data/chapter3_lines.json，为每句对白/旁白生成 mp3。
# 输出目录: G:/draw_long/novel/对口型/TTS/output/chapter3/audio/
# 文件名: {task_id}.mp3
import argparse
import base64
import json
import os
import time
import uuid

import requests

from src.config import (
    ACCESS_TOKEN,
    API_URL,
    APP_ID,
    DEFAULT_SPEED_RATIO,
    PROXIES,
    VOICE_CONFIG,
)

# 第三章新增角色音色（不在 config.py 的 VOICE_CONFIG 里，这里扩展）
VOICE_CONFIG_CH3 = {
    **VOICE_CONFIG,
    "email": "en_male_michael_moon_bigtts",    # 正式邮件男声
    "guard": "en_male_glen_emo_v2_mars_bigtts",  # 成熟男声，功能性短句
    "doctor": "en_female_skye_emo_v2_mars_bigtts",  # 成熟女声，专业语气
}

DATA_FILE = "data/chapter3_lines.json"
OUTPUT_BASE = str(Path(__file__).resolve().parents[2] / "output/chapter3/audio")
HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def load_lines():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def validate_ready(scenes):
    """生成前检查：数量、角色、凭证和音色配置"""
    lines = [line for scene in scenes for line in scene["lines"]]
    roles = set(line["role"] for line in lines)
    missing_roles = sorted(roles - set(VOICE_CONFIG_CH3))
    problems = []
    if missing_roles:
        problems.append(f"存在未配置音色的角色: {', '.join(missing_roles)}")
    if not APP_ID:
        problems.append("缺少 VOLC_APP_ID")
    if not ACCESS_TOKEN:
        problems.append("缺少 VOLC_ACCESS_TOKEN")
    return {
        "scene_count": len(scenes),
        "line_count": len(lines),
        "roles": sorted(roles),
        "problems": problems,
    }


def synthesize(text, voice_type, speed):
    """调用 V1 HTTP 接口合成单句"""
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


def generate_all(scenes):
    os.makedirs(OUTPUT_BASE, exist_ok=True)
    manifest = []
    stats = {"success": 0, "failed": 0, "skipped": 0}
    total = sum(len(s["lines"]) for s in scenes)

    print("=" * 70)
    print("第三章 TTS 音频生成")
    print(f"接口: V1 HTTP | 总句数: {total}")
    print(f"输出目录: {OUTPUT_BASE}")
    print("=" * 70)

    for scene in scenes:
        print(f"\n场景: {scene['scene']} ({len(scene['lines'])} 条)")
        for line in scene["lines"]:
            line_id = line["id"]
            role = line["role"]
            text = line["text"]
            speed = line.get("speed", DEFAULT_SPEED_RATIO)
            voice_type = VOICE_CONFIG_CH3.get(role)

            if not voice_type:
                print(f"  [FAIL] 未知角色: {role} ({line_id})")
                manifest.append({"id": line_id, "role": role, "text": text, "status": "failed", "error": "未知角色"})
                stats["failed"] += 1
                continue

            filename = f"{line_id}.mp3"
            output_path = os.path.join(OUTPUT_BASE, filename)

            # 已存在则跳过，方便失败后继续
            if os.path.exists(output_path):
                print(f"  [SKIP] {line_id} 已存在")
                manifest.append({"id": line_id, "role": role, "text": text, "path": filename, "size": os.path.getsize(output_path), "status": "skipped"})
                stats["skipped"] += 1
                continue

            audio, err = synthesize(text, voice_type, speed)
            if audio:
                with open(output_path, "wb") as f:
                    f.write(audio)
                print(f"  [OK] {line_id} ({len(audio)} bytes, speed={speed})")
                manifest.append({"id": line_id, "role": role, "text": text, "voice_type": voice_type, "speed": speed, "path": filename, "size": len(audio), "status": "success"})
                stats["success"] += 1
            else:
                print(f"  [FAIL] {line_id}: {err}")
                manifest.append({"id": line_id, "role": role, "text": text, "status": "failed", "error": err})
                stats["failed"] += 1

            time.sleep(0.3)

    manifest_path = os.path.join(OUTPUT_BASE, "ch3_tts_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({"chapter": 3, "total": sum(stats.values()), "stats": stats, "manifest": manifest}, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"生成完成 | 成功: {stats['success']} | 跳过: {stats['skipped']} | 失败: {stats['failed']}")
    print(f"清单文件: {manifest_path}")


def main():
    parser = argparse.ArgumentParser(description="生成第三章 TTS 音频")
    parser.add_argument("--check-only", action="store_true", help="只做生成前检查，不调用 TTS 接口")
    args = parser.parse_args()

    scenes = load_lines()
    report = validate_ready(scenes)

    print("=" * 70)
    print("第三章 TTS 生成前检查")
    print(f"场景数: {report['scene_count']} | 台词数: {report['line_count']}")
    print(f"角色: {', '.join(report['roles'])}")

    if report["problems"]:
        print("\n[FAIL] 检查未通过:")
        for item in report["problems"]:
            print(f"  - {item}")
        raise SystemExit(1)

    print("\n[OK] 检查通过，可以开始生成。")
    if args.check_only:
        return

    generate_all(scenes)


if __name__ == "__main__":
    main()
