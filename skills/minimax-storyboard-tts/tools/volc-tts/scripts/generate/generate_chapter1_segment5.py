import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import base64
import json
import os
import re
import time
import uuid
import shutil

import requests

from src.config import ACCESS_TOKEN, API_URL, APP_ID, DEFAULT_SPEED_RATIO, PROXIES, ROLE_DISPLAY, VOICE_CONFIG

BASE_DIR = str(Path(__file__).resolve().parents[2])
SEGMENT_SCENE = "4.6 Coordinate Night: An Qi Joins"
DATA_FILE = os.path.join(BASE_DIR, "data", "chapter1_lines.json")
OUTPUT_DIR = os.path.join(BASE_DIR, "output", "第一章第五段")
RAW_DIR = os.path.join(OUTPUT_DIR, "逐句素材")
MANIFEST_PATH = os.path.join(OUTPUT_DIR, "manifest.json")
MERGED_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "第一章第五段_英文对白_含旁白.mp3")

os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}


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


def load_segment_lines():
    with open(DATA_FILE, "r", encoding="utf-8") as handle:
        scenes = json.load(handle)

    for scene in scenes:
        if scene.get("scene") == SEGMENT_SCENE:
            return scene["lines"]

    raise RuntimeError(f"Scene not found: {SEGMENT_SCENE}")


def ensure_raw_path(filename):
    raw_path = os.path.join(RAW_DIR, filename)
    legacy_path = os.path.join(OUTPUT_DIR, filename)

    if os.path.exists(legacy_path) and not os.path.exists(raw_path):
        try:
            shutil.copy2(legacy_path, raw_path)
        except PermissionError:
            return legacy_path

    return raw_path


def merge_audio_files(manifest):
    with open(MERGED_OUTPUT_PATH, "wb") as merged_handle:
        for item in manifest:
            if item["status"] != "success":
                continue

            clip_path = os.path.join(OUTPUT_DIR, item["path"])
            if not os.path.exists(clip_path):
                clip_path = os.path.join(OUTPUT_DIR, os.path.basename(item["path"]))
            with open(clip_path, "rb") as clip_handle:
                merged_handle.write(clip_handle.read())


def main():
    if not APP_ID or not ACCESS_TOKEN:
        raise RuntimeError("Missing VOLC_APP_ID or VOLC_ACCESS_TOKEN in TTS/.env")

    lines = load_segment_lines()
    manifest = []

    print("=" * 70)
    print("Generating Chapter 1 Segment 5 English dialogue")
    print(f"Scene: {SEGMENT_SCENE}")
    print(f"Output: {os.path.abspath(OUTPUT_DIR)}")
    print(f"Lines: {len(lines)} | Speed ratio: {DEFAULT_SPEED_RATIO}")
    print("=" * 70)

    for line in lines:
        line_id = line["id"]
        role = line["role"]
        text = line["text"]
        voice_type = VOICE_CONFIG.get(role)

        if not voice_type:
            print(f"[FAIL] Missing voice config for {role} ({line_id})")
            manifest.append({
                "id": line_id,
                "role": role,
                "display": ROLE_DISPLAY.get(role, role),
                "voice_type": None,
                "text": text,
                "path": None,
                "status": "failed",
                "error": f"missing voice config for {role}"
            })
            continue

        output_name = f"{sanitize_filename(line_id)}_{role}.mp3"
        output_path = ensure_raw_path(output_name)
        relative_path = os.path.relpath(output_path, OUTPUT_DIR).replace("\\", "/")

        if os.path.exists(output_path):
            audio_size = os.path.getsize(output_path)
            manifest.append({
                "id": line_id,
                "role": role,
                "display": ROLE_DISPLAY.get(role, role),
                "voice_type": voice_type,
                "text": text,
                "path": relative_path,
                "size": audio_size,
                "status": "success"
            })
            print(f"[SKIP] {line_id} {ROLE_DISPLAY.get(role, role)} -> {relative_path}")
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
                "path": os.path.relpath(output_path, OUTPUT_DIR).replace("\\", "/"),
                "size": len(audio),
                "status": "success"
            })
            print(f"[OK] {line_id} {ROLE_DISPLAY.get(role, role)} -> {os.path.relpath(output_path, OUTPUT_DIR).replace('\\', '/')}")
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
                "scene": SEGMENT_SCENE,
                "output_dir": os.path.abspath(OUTPUT_DIR),
                "raw_dir": os.path.abspath(RAW_DIR),
                "merged_output": os.path.abspath(MERGED_OUTPUT_PATH),
                "speed_ratio": DEFAULT_SPEED_RATIO,
                "count": len(lines),
                "manifest": manifest
            },
            handle,
            ensure_ascii=False,
            indent=2
        )

    success_count = sum(1 for item in manifest if item["status"] == "success")
    print("=" * 70)
    print(f"Done. Success: {success_count}/{len(lines)}")
    print(f"Merged: {os.path.abspath(MERGED_OUTPUT_PATH)}")
    print(f"Manifest: {os.path.abspath(MANIFEST_PATH)}")


if __name__ == "__main__":
    main()
