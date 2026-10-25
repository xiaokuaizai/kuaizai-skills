import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS V1 WebSocket协议测试
import websocket
import json
import struct
import time
from src.config import ACCESS_TOKEN, APP_ID

# V1 WebSocket接口地址
WS_URL = "wss://openspeech.bytedance.com/api/v1/tts/ws_binary"

# V1认证格式: Authorization: Bearer;{token}
headers = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}"
}

audio_data = []

def build_v1_frame(payload_dict):
    """V1协议帧 - header(4B) + payload_size(4B) + payload"""
    # Header:
    # Byte 0: version=1(0b0001), header_size=1(0b0001) => 0x11
    # Byte 1: message_type=1(0b0001), flags=0(0b0000) => 0x10
    # Byte 2: serialization=1(JSON), compression=0 => 0x10
    # Byte 3: reserved => 0x00
    header = bytes([0x11, 0x10, 0x10, 0x00])
    payload_bytes = json.dumps(payload_dict).encode('utf-8')
    payload_size = struct.pack('>I', len(payload_bytes))
    return header + payload_size + payload_bytes

def on_open(ws):
    print("WebSocket连接成功")
    # V1协议：直接发送请求，不需要StartConnection
    request = {
        "app": {
            "appid": APP_ID,
            "token": ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {
            "uid": "test_user"
        },
        "audio": {
            "voice_type": "BV504_streaming",  # 活力男声-Jackson
            "encoding": "mp3",
            "speed_ratio": 0.8,  # 慢语速
            "rate": 24000
        },
        "request": {
            "reqid": f"req_{int(time.time()*1000)}",
            "text": "Unless decoded, the plan fails.",
            "operation": "query"
        }
    }
    ws.send(build_v1_frame(request))
    print("发送请求")

def on_message(ws, msg):
    data = bytes(msg)
    print(f"收到: {len(data)}B, hex: {data[:30].hex()}")

    if len(data) < 4:
        return

    msg_type = (data[1] >> 4) & 0x0F

    if msg_type == 15:  # 错误
        idx = data.find(b'{')
        if idx >= 0:
            print(f"错误: {data[idx:].decode('utf-8')}")
        ws.close()
        return

    # Audio-only response (msg_type=11, 即0b1011)
    if msg_type == 11:
        # V1音频响应格式: header(4B) + payload(audio)
        # payload_size在header之后吗？让我检查文档
        # 根据文档，Audio-only response的payload直接是音频数据
        flags = data[1] & 0x0F
        # 跳过header获取音频
        audio_chunk = data[4:]
        audio_data.append(audio_chunk)
        print(f"音频: {len(audio_chunk)}B, flags={flags}")
        if flags >= 2:  # last chunk
            ws.close()
        return

    # 其他类型
    print(f"未知消息类型: {msg_type}")

def on_close(ws, *args):
    if audio_data:
        with open("output/test.mp3", "wb") as f:
            f.write(b''.join(audio_data))
        print(f"✓ 保存: output/test.mp3 ({sum(len(d) for d in audio_data)}B)")
    else:
        print("× 无音频")

def on_error(ws, err):
    print(f"错误: {err}")

print(f"测试配置:")
print(f"  APP ID: {APP_ID}")
print(f"  接口: V1 WebSocket")
print(f"  音色: BV504_streaming (活力男声-Jackson)")
print(f"  语速: 0.8 (慢)")
print()

ws = websocket.WebSocketApp(WS_URL, header=headers, on_open=on_open, on_message=on_message, on_close=on_close, on_error=on_error)
ws.run_forever()
