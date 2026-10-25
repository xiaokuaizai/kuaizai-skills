import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 1.0模型 WebSocket测试（正确的旧版控制台headers）
import websocket
import json
import struct
import time
from src.config import ACCESS_KEY, APP_ID

# API配置 - 使用V3接口和1.0模型
WS_URL = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"
RESOURCE_ID = "seed-tts-1.0"  # 1.0模型

# 正确的headers格式（旧版控制台）
headers = {
    "X-Api-App-Id": APP_ID,
    "X-Api-Access-Key": ACCESS_KEY,
    "X-Api-Resource-Id": RESOURCE_ID,
}

audio_data = []
session_id = f"sess_{int(time.time()*1000)}"

def build_frame(event, sid="", payload_str="{}"):
    """V3协议帧 - payload_str是JSON字符串"""
    header = bytes([0x11, 0x14, 0x10, 0x00])
    event_bytes = struct.pack('>i', event)
    sid_bytes = sid.encode('utf-8')
    payload_bytes = payload_str.encode('utf-8')
    return header + event_bytes + struct.pack('>I', len(sid_bytes)) + sid_bytes + struct.pack('>I', len(payload_bytes)) + payload_bytes

def on_open(ws):
    print("WebSocket连接成功")
    ws.send(build_frame(1, "", "{}"))  # StartConnection - payload必须是"{}"

def on_message(ws, msg):
    data = bytes(msg)
    print(f"收到: {len(data)}B, hex: {data[:20].hex()}")

    if len(data) < 4:
        return

    msg_type = (data[1] >> 4) & 0x0F

    if msg_type == 15:  # 错误
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

    if msg_type == 9:  # JSON
        if off + 4 <= len(data):
            jsz = struct.unpack('>I', data[off:off+4])[0]
            off += 4
            if jsz > 0 and off + jsz <= len(data):
                jd = json.loads(data[off:off+jsz].decode('utf-8'))
                print(f"JSON: {jd}")

                if event == 50:  # ConnectionStarted
                    print("✓ 连接就绪")
                    # 1.0模型的英文音色
                    payload = {
                        "user": {"uid": "test"},
                        "req_params": {
                            "speaker": "BV504_streaming",  # 活力男声-Jackson
                            "audio_params": {
                                "format": "mp3",
                                "sample_rate": 24000,
                                "speed_ratio": 0.8  # 慢语速
                            }
                        }
                    }
                    ws.send(build_frame(100, session_id, json.dumps(payload)))
                    print(f"发送StartSession: {session_id}")

                elif event == 150:  # SessionStarted
                    print("✓ 会话就绪")
                    ws.send(build_frame(200, session_id, json.dumps({"req_params": {"text": "Unless decoded, the plan fails."}})))
                    ws.send(build_frame(102, session_id, "{}"))

                elif event == 152:  # SessionFinished
                    print("✓ 会话结束")
                    ws.close()

    elif msg_type == 11:  # 音频
        audio_data.append(data[off:])
        is_last = (data[1] & 0x0F) >= 2
        print(f"音频: {len(data[off:])}B, 最后: {is_last}")

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
print(f"  Resource ID: {RESOURCE_ID}")
print(f"  音色: BV504_streaming (活力男声-Jackson)")
print(f"  语速: 0.8 (慢)")
print()

ws = websocket.WebSocketApp(WS_URL, header=headers, on_open=on_open, on_message=on_message, on_close=on_close, on_error=on_error)
ws.run_forever()
