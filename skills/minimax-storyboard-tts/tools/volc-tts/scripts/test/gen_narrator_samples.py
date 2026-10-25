# 生成英文女声旁白样本（V1 HTTP 1.0大模型）
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import requests
import json
import uuid
import base64
import os
import time
import io
from src.config import ACCESS_TOKEN, API_URL, APP_ID, PROXIES

# 输出目录
OUTPUT_DIR = "F:/AA_Company_project/AA_main/Lexi/Media/Append/资产/TTS/samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 测试文本
TEXT = "On an April morning, sunlight shone through the curtains into Jiang Che's room. On the bedside table lay the two of their reservation confirmations and copies of the visa An Qi had printed for them."

# 候选音色：豆包同款 + 已成功的标准英文女声
VOICES = [
    {"name": "Daisy", "voice_type": "en_female_dacey_conversation_wvae_bigtts", "tag": "豆包同款"},
    {"name": "Luna", "voice_type": "en_female_sarah_new_conversation_wvae_bigtts", "tag": "豆包同款"},
    {"name": "Stokie", "voice_type": "en_female_stokie_uranus_bigtts", "tag": "标准英文女声"}
]

# 固定请求头
HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

# 设置 UTF-8 输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8")
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8")


def synthesize(text, voice_type, speed_ratio=0.9):
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
            "speed_ratio": speed_ratio,
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


def main():
    print("=" * 60)
    print("英文女声旁白样本生成 - 第二轮")
    print(f"文本: {TEXT}")
    print(f"输出目录: {OUTPUT_DIR}")
    print("=" * 60)

    results = []
    for v in VOICES:
        print(f"\n生成: {v['name']} ({v['tag']}) - {v['voice_type']}")
        audio, err = synthesize(TEXT, v["voice_type"], speed_ratio=0.9)
        if audio:
            output_path = os.path.join(OUTPUT_DIR, f"narrator_{v['name'].lower()}_sample.mp3")
            with open(output_path, "wb") as f:
                f.write(audio)
            print(f"  [OK] 成功 -> {output_path} ({len(audio)} bytes)")
            results.append({"name": v["name"], "tag": v["tag"], "success": True, "path": output_path, "size": len(audio)})
        else:
            print(f"  [FAIL] 失败: {err}")
            results.append({"name": v["name"], "tag": v["tag"], "success": False, "error": err})
        time.sleep(0.5)

    print("\n" + "=" * 60)
    print("生成结果汇总")
    print("=" * 60)
    for r in results:
        if r["success"]:
            print(f"  [OK] {r['name']:<8} {r['tag']:<12} -> {r['path']}")
        else:
            print(f"  [FAIL] {r['name']:<8} {r['tag']:<12} -> {r.get('error', '未知错误')}")


if __name__ == "__main__":
    main()
