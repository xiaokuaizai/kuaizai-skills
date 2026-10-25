import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 1.0模型 HTTP接口测试（简单版）
import requests
import json
import uuid
import base64
from src.config import ACCESS_TOKEN, API_URL, APP_ID, PROXIES

# 请求参数
payload = {
    "app": {
        "appid": APP_ID,
        "token": ACCESS_TOKEN,
        "cluster": "volcano_tts"
    },
    "user": {
        "uid": "test_user"
    },
    "audio": {
        "voice_type": "BV504_streaming",  # 活力男声-Jackson（美式英语）
        "encoding": "mp3",
        "speed_ratio": 0.8,  # 慢语速（小于1变慢）
        "rate": 24000
    },
    "request": {
        "reqid": str(uuid.uuid4()),
        "text": "Unless decoded, the plan fails.",
        "operation": "query"
    }
}

# 发送请求
headers = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

print("测试参数:")
print(f"  APP ID: {APP_ID}")
print(f"  音色: BV504_streaming (活力男声-Jackson)")
print(f"  文本: 'Unless decoded, the plan fails.'")
print(f"  语速: 0.8 (慢)")
print()

response = requests.post(API_URL, headers=headers, json=payload, proxies=PROXIES, timeout=60)

print(f"状态码: {response.status_code}")
result = response.json()
print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

# 如果成功，保存音频
if result.get("code") == 3000 and "data" in result:
    audio_data = base64.b64decode(result["data"])
    with open("output/test.mp3", "wb") as f:
        f.write(audio_data)
    print(f"\n✓ 音频保存成功: output/test.mp3 ({len(audio_data)} bytes)")
else:
    print(f"\n× 合成失败: {result.get('message', '未知错误')}")
