import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 小男孩候选音色生成
# 只针对第二章 CH2-068 生成少量候选，方便横向试听。
import requests
import json
import uuid
import base64
import os
import time
from src.config import ACCESS_TOKEN, API_URL, APP_ID, DEFAULT_SPEED_RATIO, PROXIES

OUTPUT_DIR = r"G:\draw_long\novel\wiki-整理\raw\声音参考"
os.makedirs(OUTPUT_DIR, exist_ok=True)

SAMPLE_LINE = {
    "id": "CH2-068",
    "role": "boy",
    "text": "How did you make the floor respond?"
}

# 候选顺序按“更像小男孩/少年好奇感”优先排列。
VOICE_CANDIDATES = [
    {
        "key": "01_bryan",
        "display": "少年梓辛_Brayan",
        "voice_type": "zh_male_shaonianzixin_moon_bigtts",
        "note": "当前版本，少年感明显，作为基准对照"
    },
    {
        "key": "02_alvin",
        "display": "温暖阿虎_Alvin",
        "voice_type": "zh_male_wennuanahu_moon_bigtts",
        "note": "支持美式英语，声音更温暖，可能更像观展小朋友"
    },
    {
        "key": "03_lucas",
        "display": "Lucas",
        "voice_type": "zh_male_M100_conversation_wvae_bigtts",
        "note": "英语自然度较稳，但容易和江彻音色接近"
    },
    {
        "key": "04_neighbor_boy",
        "display": "邻家男孩",
        "voice_type": "zh_male_linjiananhai_moon_bigtts",
        "note": "少年感候选，需重点听英文发音是否自然"
    }
]

HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}


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
            "speed_ratio": DEFAULT_SPEED_RATIO,
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


def main():
    print("=" * 70)
    print("第二章小男孩候选音色生成")
    print(f"台词: {SAMPLE_LINE['text']}")
    print(f"语速: {DEFAULT_SPEED_RATIO}")
    print("=" * 70)

    results = []
    for item in VOICE_CANDIDATES:
        print(f"\n【{item['key']} {item['display']}】")
        print(f"  voice_type: {item['voice_type']}")
        print(f"  说明: {item['note']}")

        audio, err = synthesize(SAMPLE_LINE["text"], item["voice_type"])
        if audio:
            output_name = f"男孩声音参考_{item['key']}_{item['display']}.mp3"
            output_path = os.path.join(OUTPUT_DIR, output_name)
            with open(output_path, "wb") as f:
                f.write(audio)

            print(f"  [OK] -> {output_path} ({len(audio)} bytes)")
            results.append({
                **item,
                "line_id": SAMPLE_LINE["id"],
                "text": SAMPLE_LINE["text"],
                "path": output_path,
                "size": len(audio),
                "success": True
            })
        else:
            print(f"  [FAIL] {err}")
            results.append({
                **item,
                "line_id": SAMPLE_LINE["id"],
                "text": SAMPLE_LINE["text"],
                "path": None,
                "size": 0,
                "success": False,
                "error": err
            })

        time.sleep(0.5)  # 控制请求频率，避免连续请求过快。

    manifest_path = os.path.join(OUTPUT_DIR, "男孩音色候选_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump({
            "speed_ratio": DEFAULT_SPEED_RATIO,
            "line": SAMPLE_LINE,
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print("\n" + "=" * 70)
    print(f"候选生成完成，清单文件: {manifest_path}")


if __name__ == "__main__":
    main()
