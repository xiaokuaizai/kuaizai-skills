import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 1.0大模型 HTTP接口测试（单句）
# 使用V1 HTTP非流式接口，比V3 WebSocket二进制协议更简单稳定
import requests
import json
import uuid
import base64
import os
from src.config import ACCESS_TOKEN, API_URL, APP_ID, PROXIES

# 请求参数
payload = {
    "app": {
        "appid": APP_ID,
        "token": ACCESS_TOKEN,  # token无实际鉴权作用，可传任意非空字符串
        "cluster": "volcano_tts"  # 必须
    },
    "user": {
        "uid": "test_user"
    },
    "audio": {
        "voice_type": "en_male_michael_moon_bigtts",  # 李老师音色，1.0大模型
        "encoding": "mp3",
        "speed_ratio": 0.9,  # 慢语速，范围[0.1, 2]
        "rate": 24000
    },
    "request": {
        "reqid": str(uuid.uuid4()),  # 每次必须唯一
        "text": "Unless decoded, the plan fails.",
        "operation": "query"
    }
}

# 认证头：Bearer和token用分号分隔
headers = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

print("测试参数:")
print(f"  APP ID: {APP_ID}")
print(f"  音色: en_male_michael_moon_bigtts (李老师音色，1.0大模型)")
print(f"  文本: 'Unless decoded, the plan fails.'")
print(f"  语速: 0.8 (慢)")
print()

try:
    response = requests.post(
        API_URL,
        headers=headers,
        json=payload,
        proxies=PROXIES,
        timeout=60
    )

    print(f"状态码: {response.status_code}")
    result = response.json()
    print(f"响应: {json.dumps(result, indent=2, ensure_ascii=False)}")

    # 成功码3000
    if result.get("code") == 3000 and "data" in result:
        audio_data = base64.b64decode(result["data"])
        os.makedirs("output", exist_ok=True)
        with open("output/test_michael.mp3", "wb") as f:
            f.write(audio_data)
        print(f"\n✓ 音频保存成功: output/test_michael.mp3 ({len(audio_data)} bytes)")
    else:
        print(f"\n× 合成失败: {result.get('message', '未知错误')}")

except Exception as e:
    print(f"\n× 请求异常: {e}")
