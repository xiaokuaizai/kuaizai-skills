import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 第二章新增角色语音小样生成
# 只生成 4 条待确认音色，不批量生成第二章全章音频。
import requests
import json
import uuid
import base64
import os
import time
from src.config import (
    ACCESS_TOKEN,
    API_URL,
    APP_ID,
    DEFAULT_SPEED_RATIO,
    PROXIES,
    ROLE_DISPLAY,
    VOICE_OPTIONS_CHAPTER2,
)

DATA_FILE = "data/chapter2_lines.json"
# 小样直接放到 wiki 的声音参考目录，方便试听和后续复用。
OUTPUT_DIR = r"G:\draw_long\novel\wiki-整理\raw\声音参考"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 固定抽样这 4 句，便于先听第二章新增/不确定角色的声音。
SAMPLE_LINE_IDS = ["CH2-020", "CH2-039", "CH2-045", "CH2-068"]

HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

SPEED_RATIO = DEFAULT_SPEED_RATIO


def load_sample_lines():
    """从第二章台词数据中取出待确认的小样句子"""
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        scenes = json.load(f)

    line_map = {}
    for scene in scenes:
        for line in scene["lines"]:
            line_map[line["id"]] = line

    missing_ids = [line_id for line_id in SAMPLE_LINE_IDS if line_id not in line_map]
    if missing_ids:
        raise ValueError(f"缺少小样台词: {', '.join(missing_ids)}")

    return [line_map[line_id] for line_id in SAMPLE_LINE_IDS]


def synthesize(text, voice_type):
    """调用V1 HTTP接口合成单句语音"""
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

    return None, result.get("message", f"code={result.get('code')}")


def generate_sample(line):
    """生成一条小样，主选失败时自动尝试备选音色"""
    role = line["role"]
    options = VOICE_OPTIONS_CHAPTER2.get(role)
    display = ROLE_DISPLAY.get(role, role)

    if not options:
        return {
            "id": line["id"],
            "role": role,
            "display": display,
            "success": False,
            "error": "未配置第二章待确认音色"
        }

    print(f"\n【{line['id']} {display}】")
    print(f"  文本: {line['text']}")

    for voice_key in ["primary", "fallback"]:
        voice_type = options[voice_key]
        label = "主选" if voice_key == "primary" else "备选"
        print(f"  尝试{label}音色: {voice_type}")

        audio, err = synthesize(line["text"], voice_type)
        if audio:
            output_name = f"{display}声音参考.mp3"
            output_path = os.path.join(OUTPUT_DIR, output_name)
            with open(output_path, "wb") as f:
                f.write(audio)

            print(f"  [OK] 成功 [{label}] -> {output_path} ({len(audio)} bytes)")
            return {
                "id": line["id"],
                "role": role,
                "display": display,
                "voice_type": voice_type,
                "voice_source": label,
                "text": line["text"],
                "path": output_path,
                "size": len(audio),
                "success": True
            }

        print(f"  [FAIL] {label}失败: {err}")

    return {
        "id": line["id"],
        "role": role,
        "display": display,
        "voice_type": None,
        "voice_source": None,
        "text": line["text"],
        "path": None,
        "size": 0,
        "success": False
    }


def main():
    print("=" * 70)
    print("第二章新增角色 TTS 小样生成")
    print(f"接口: V1 HTTP | 语速: {SPEED_RATIO} | 小样数: {len(SAMPLE_LINE_IDS)}")
    print("注意: 运行本脚本会调用火山引擎 TTS 接口。")
    print("=" * 70)

    lines = load_sample_lines()
    results = []
    for line in lines:
        results.append(generate_sample(line))
        time.sleep(0.5)  # 控制请求频率，避免连续请求过快。

    manifest_path = os.path.join(OUTPUT_DIR, "manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "speed_ratio": SPEED_RATIO,
            "sample_line_ids": SAMPLE_LINE_IDS,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print("小样生成完成")
    print(f"清单文件: {manifest_path}")


if __name__ == "__main__":
    main()
