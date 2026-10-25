import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import base64
import json
import os
import re
import time
import uuid

import requests

from src.config import ACCESS_TOKEN, API_URL, APP_ID, DEFAULT_SPEED_RATIO, PROXIES, ROLE_DISPLAY, VOICE_CONFIG

BASE_DIR = str(Path(__file__).resolve().parents[2])
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "第一章第五段_原文")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.json")
MERGED_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "第一章第五段_原文_英文对白_含旁白.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

SEGMENT_LINES = [
    {
        "id": "原文第五段-1",
        "role": "narrator",
        "text": "At 9:17 p.m., a new message appeared on the screen."
    },
    {
        "id": "原文第五段-2",
        "role": "jiang_che",
        "text": "Coordinates: sixty-two degrees, twelve minutes, fifty-nine seconds south; fifty-eight degrees, fifty-seven minutes, fifty-two seconds west."
    },
    {
        "id": "原文第五段-3",
        "role": "narrator",
        "text": "The point was near the Antarctic Peninsula, about two hundred kilometers from Great Wall Station."
    },
    {
        "id": "原文第五段-4",
        "role": "narrator",
        "text": "More importantly, it was the destination of his parents' last joint expedition ten years ago."
    },
    {
        "id": "原文第五段-5",
        "role": "narrator",
        "text": "They had stayed there for three full months, but they never said what they had done."
    },
    {
        "id": "原文第五段-6",
        "role": "narrator",
        "text": "And now, the answer was calling him."
    },
    {
        "id": "原文第五段-7",
        "role": "narrator",
        "text": "An unread message from An Qi was on his phone."
    },
    {
        "id": "原文第五段-8",
        "role": "an_qi",
        "text": "Tomorrow at three p.m., science club meeting room. Bring all your materials. I have decided to join your project."
    },
    {
        "id": "原文第五段-9",
        "role": "jiang_che",
        "text": "Good."
    },
    {
        "id": "原文第五段-10",
        "role": "narrator",
        "text": "In the dark, the signal continued."
    },
    {
        "id": "原文第五段-11",
        "role": "narrator",
        "text": "Unless you come, the stars will wait forever."
    }
]


def sanitize_filename(text):
    return re.sub(r"[^\w\-]", "_", text)


def synthesize(text, voice_type):
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
            "speed_ratio": DEFAULT_SPEED_RATIO,
            "rate": 24000
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query"
        }
    }

    response = requests.post(
        API_URL,
        headers=HEADERS,
        json=payload,
        proxies=PROXIES,
        timeout=60
    )
    result = response.json()

    if result.get("code") == 3000 and "data" in result:
        return base64.b64decode(result["data"]), None

    return None, result.get("message", f"code={result.get('code')}")


def merge_audio_files(manifest):
    with open(MERGED_OUTPUT_PATH, "wb") as merged_handle:
        for item in manifest:
            if item["status"] != "success":
                continue

            clip_path = os.path.join(OUTPUT_DIR, item["path"])
            with open(clip_path, "rb") as clip_handle:
                merged_handle.write(clip_handle.read())


def main():
    if not APP_ID or not ACCESS_TOKEN:
        raise RuntimeError("Missing VOLC_APP_ID or VOLC_ACCESS_TOKEN in TTS/.env")

    manifest = []

    print("=" * 70)
    print("Generating Chapter 1 Segment 5 Original Dialogue")
    print(f"Output: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Lines: {len(SEGMENT_LINES)} | Speed ratio: {DEFAULT_SPEED_RATIO}")
    print("=" * 70)

    for line in SEGMENT_LINES:
        line_id = line["id"]
        role = line["role"]
        text = line["text"]
        voice_type = VOICE_CONFIG.get(role)

        if not voice_type:
            manifest.append({
                "id": line_id,
                "role": role,
                "display": ROLE_DISPLAY.get(role, role),
                "voice_type": None,
                "text": text,
                "path": None,
                "size": 0,
                "status": "failed",
                "error": f"missing voice config for {role}"
            })
            print(f"[FAIL] {line_id} {ROLE_DISPLAY.get(role, role)}: missing voice config")
            continue

        output_name = f"{sanitize_filename(line_id)}_{role}.mp3"
        output_path = os.path.join(OUTPUT_DIR, output_name)

        if os.path.exists(output_path):
            manifest.append({
                "id": line_id,
                "role": role,
                "display": ROLE_DISPLAY.get(role, role),
                "voice_type": voice_type,
                "text": text,
                "path": output_name,
                "size": os.path.getsize(output_path),
                "status": "success"
            })
            print(f"[SKIP] {line_id} {ROLE_DISPLAY.get(role, role)} -> {output_name}")
            continue

        audio, error = synthesize(text, voice_type)
        if audio:
            with open(output_path, "wb") as handle:
                handle.write(audio)

            manifest.append({
                "id": line_id,
                "role": role,
                "display": ROLE_DISPLAY.get(role, role),
                "voice_type": voice_type,
                "text": text,
                "path": output_name,
                "size": len(audio),
                "status": "success"
            })
            print(f"[OK] {line_id} {ROLE_DISPLAY.get(role, role)} -> {output_name}")
        else:
            manifest.append({
                "id": line_id,
                "role": role,
                "display": ROLE_DISPLAY.get(role, role),
                "voice_type": voice_type,
                "text": text,
                "path": None,
                "size": 0,
                "status": "failed",
                "error": error
            })
            print(f"[FAIL] {line_id} {ROLE_DISPLAY.get(role, role)}: {error}")

        time.sleep(0.3)

    merge_audio_files(manifest)

    with open(MANIFEST_PATH, "w", encoding="utf-8") as handle:
        json.dump(
            {
                "output_dir": os.path.abspath(OUTPUT_DIR),
                "merged_output": os.path.abspath(MERGED_OUTPUT_PATH),
                "speed_ratio": DEFAULT_SPEED_RATIO,
                "count": len(SEGMENT_LINES),
                "manifest": manifest
            },
            handle,
            ensure_ascii=False,
            indent=2
        )

    success_count = sum(1 for item in manifest if item["status"] == "success")
    print("=" * 70)
    print(f"Done. Success: {success_count}/{len(SEGMENT_LINES)}")
    print(f"Merged: {os.path.abspath(MERGED_OUTPUT_PATH)}")
    print(f"Manifest: {os.path.abspath(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
