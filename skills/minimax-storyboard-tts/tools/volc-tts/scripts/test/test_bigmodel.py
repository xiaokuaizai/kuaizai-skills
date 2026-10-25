import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 大模型 V3 WebSocket测试
import websocket
import json
import struct
import time
from src.config import ACCESS_KEY, APP_ID

# V3 WebSocket接口
WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
RESOURCE_ID = "seed-tts-1.0"  # 大模型1.0

# Headers（旧版控制台格式）
headers = {
    "X-Api-App-Id": APP_ID,
    "X-Api-Access-Key": ACCESS_KEY,
    "X-Api-Resource-Id": RESOURCE_ID,
}

audio_data = []
session_id = f"sess_{int(time.time()*1000)}"

def build_frame(event, sid="", payload="{}"):
    """V3协议帧"""
    header = bytes([0x11, 0x14, 0x10, 0x00])
    sid_bytes = sid.encode('utf-8')
    payload_bytes = payload.encode('utf-8')
    return header + struct.pack('>i', event) + struct.pack('>I', len(sid_bytes)) + sid_bytes + struct.pack('>I', len(payload_bytes)) + payload_bytes

def on_open(ws):
    print("连接成功")
    ws.send(build_frame(1, "", "{}"))

def on_message(ws, msg):
    data = bytes(msg)
    print(f"收到: {len(data)}B")

    if len(data) < 4:
        return

    msg_type = (data[1] >> 4) & 0x0F

    if msg_type == 15:
        idx = data.find(b'{')
        if idx >= 0:
            print(f"错误: {data[idx:].decode('utf-8')}")
        ws.close()
        return

    if len(data) < 12:
        return

    event = struct.unpack('>i', data[4:8])[0]
    off = 8
    sid_sz = struct.unpack('>I', data[off:off+4])[0]
    off += 4 + sid_sz

    print(f"事件: {event}")

    if msg_type == 9:
        if off + 4 <= len(data):
            jsz = struct.unpack('>I', data[off:off+4])[0]
            off += 4
            if jsz > 0 and off + jsz <= len(data):
                jd = json.loads(data[off:off+jsz].decode('utf-8'))
                print(f"JSON: {jd}")

                if event == 50:
                    print("✓ 连接就绪")
                    payload = json.dumps({
                        "user": {"uid": "test"},
                        "req_params": {
                            "speaker": "en_male_michael_moon_bigtts",  # 1.0英文男声
                            "audio_params": {
                                "format": "mp3",
                                "sample_rate": 24000,
                                "speech_rate": -18
                            }
                        }
                    })
                    ws.send(build_frame(100, session_id, payload))

                elif event == 150:
                    print("✓ 会话就绪")
                    ws.send(build_frame(200, session_id, json.dumps({"req_params": {"text": "Unless decoded, the plan fails."}})))
                    ws.send(build_frame(102, session_id, "{}"))

                elif event == 152:
                    print("✓ 结束")
                    ws.close()

    elif msg_type == 11:
        audio_data.append(data[off:])
        print(f"音频: {len(data[off:])}B")

def on_close(ws, *args):
    if audio_data:
        with open("output/test.mp3", "wb") as f:
            f.write(b''.join(audio_data))
        print(f"✓ 保存成功: {sum(len(d) for d in audio_data)}B")
    else:
        print("× 无音频")

def on_error(ws, err):
    print(f"错误: {err}")

print(f"测试: en_male_michael_moon_bigtts (李老师音色)")
print(f"Resource: {RESOURCE_ID}")
print()

ws = websocket.WebSocketApp(WS_URL, header=headers, on_open=on_open, on_message=on_message, on_close=on_close, on_error=on_error)
ws.run_forever()
