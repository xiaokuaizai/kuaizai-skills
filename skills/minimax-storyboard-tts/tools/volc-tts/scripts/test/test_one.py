import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 一句话测试
import websocket
import json
import struct
import time
from src.config import ACCESS_TOKEN, APP_ID, RESOURCE_ID

# API配置
ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

audio_chunks = []

def on_open(ws):
    print("WebSocket连接成功")

def on_message(ws, data):
    data = bytes(data)
    print(f"收到数据: {len(data)} bytes")

    # 检查是否有错误
    if b'error' in data:
        err_start = data.find(b'{')
        if err_start >= 0:
            print(f"错误: {data[err_start:].decode('utf-8')}")
        ws.close()
        return

    # 解析响应类型
    if len(data) >= 2:
        msg_type = (data[1] >> 4) & 0x0F
        flags = data[1] & 0x0F

        # 音频数据 (msg_type=11)
        if msg_type == 11:
            # 跳过session_id获取音频
            offset = 8
            sid_size = struct.unpack('>I', data[offset:offset+4])[0]
            offset += 4 + sid_size
            audio_chunks.append(data[offset:])
            print(f"收到音频: {len(data[offset:])} bytes, isLast={flags>=2}")
            if flags >= 2:
                ws.close()

def on_close(ws, *args):
    if audio_chunks:
        total = sum(len(c) for c in audio_chunks)
        with open("output/test.mp3", "wb") as f:
            f.write(b''.join(audio_chunks))
        print(f"✓ 音频保存成功: output/test.mp3 ({total} bytes)")
    else:
        print("× 未收到音频")

def on_error(ws, err):
    print(f"WebSocket错误: {err}")

# 连接并运行
headers = {
    "X-Api-App-Key": APP_ID,
    "X-Api-Access-Key": ACCESS_TOKEN,
    "X-Api-Resource-Id": RESOURCE_ID,
}

print(f"测试参数:")
print(f"  APP ID: {APP_ID}")
print(f"  Resource ID: {RESOURCE_ID}")
print(f"  文本: 'Unless decoded, the plan fails.'")
print(f"  音色: en_male_tim_uranus_bigtts (英文男声)")
print(f"  语速: -18 (慢)")
print()

ws = websocket.WebSocketApp(
    ENDPOINT,
    header=headers,
    on_open=on_open,
    on_message=on_message,
    on_close=on_close,
    on_error=on_error
)

ws.run_forever()
