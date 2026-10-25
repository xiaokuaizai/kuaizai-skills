import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 第一章完整对话音频生成
# 读取 data/chapter1_lines.json，为每句对白生成 mp3
import requests
import json
import uuid
import base64
import os
import time
import re
from src.config import ACCESS_TOKEN, API_URL, APP_ID, DEFAULT_SPEED_RATIO, PROXIES, ROLE_DISPLAY, VOICE_CONFIG

DATA_FILE = "data/chapter1_lines.json"
OUTPUT_BASE = "output/chapter1"
os.makedirs(OUTPUT_BASE, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

SPEED_RATIO = DEFAULT_SPEED_RATIO


def sanitize_dirname(name):
    """把场景名转成合法的文件夹名"""
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"\s+", "_", name).strip("_")
    return name[:80]


def synthesize(text, voice_type):
    """调用V1 HTTP接口合成单句"""
    payload = {
        "app": {
            "appid": APP_ID,
            "token": ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {"uid": "novel_tts_user"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": SPEED_RATIO,
            "rate": 24000
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query"
        }
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, proxies=PROXIES, timeout=60)
        result = resp.json()
    except Exception as e:
        return None, f"请求异常: {e}"

    if result.get("code") == 3000 and "data" in result:
        return base64.b64decode(result["data"]), None
    else:
        return None, result.get("message", f"code={result.get('code')}")


def load_lines():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def main():
    scenes = load_lines()
    manifest = []
    stats = {"success": 0, "failed": 0, "skipped": 0}

    print("=" * 70)
    print("第一章完整对话音频生成")
    print(f"接口: V1 HTTP | 语速: {SPEED_RATIO} | 总句数: {sum(len(s['lines']) for s in scenes)}")
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

            if not voice_type:
                print(f"  [FAIL] 未知角色: {role} ({line_id})")
                stats["failed"] += 1
                continue

            safe_id = re.sub(r"[^\w\-]", "_", line_id)
            filename = f"{safe_id}_{role}.mp3"
            output_path = os.path.join(scene_path, filename)
            rel_path = os.path.relpath(output_path, "output/chapter1").replace("\\", "/")

            # 已存在则跳过（断点续传）
            if os.path.exists(output_path):
                print(f"  [SKIP] {line_id} 已存在")
                manifest.append({
                    "id": line_id,
                    "role": role,
                    "display": ROLE_DISPLAY.get(role, role),
                    "voice_type": voice_type,
                    "text": text,
                    "path": rel_path,
                    "size": os.path.getsize(output_path),
                    "status": "skipped"
                })
                stats["skipped"] += 1
                continue

            audio, err = synthesize(text, voice_type)
            if audio:
                with open(output_path, "wb") as f:
                    f.write(audio)
                print(f"  [OK] {line_id} {ROLE_DISPLAY.get(role)} ({len(audio)} bytes)")
                manifest.append({
                    "id": line_id,
                    "role": role,
                    "display": ROLE_DISPLAY.get(role, role),
                    "voice_type": voice_type,
                    "text": text,
                    "path": rel_path,
                    "size": len(audio),
                    "status": "success"
                })
                stats["success"] += 1
            else:
                print(f"  [FAIL] {line_id} {ROLE_DISPLAY.get(role)}: {err}")
                manifest.append({
                    "id": line_id,
                    "role": role,
                    "display": ROLE_DISPLAY.get(role, role),
                    "voice_type": voice_type,
                    "text": text,
                    "path": None,
                    "size": 0,
                    "status": "failed",
                    "error": err
                })
                stats["failed"] += 1

            time.sleep(0.3)  # 控制请求频率

    # 保存清单
    manifest_path = os.path.join(OUTPUT_BASE, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "speed_ratio": SPEED_RATIO,
            "total": sum(stats.values()),
            "stats": stats,
            "manifest": manifest
        }, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("生成完成")
    print(f"成功: {stats['success']} | 跳过: {stats['skipped']} | 失败: {stats['failed']}")
    print(f"清单文件: {manifest_path}")


if __name__ == "__main__":
    main()
