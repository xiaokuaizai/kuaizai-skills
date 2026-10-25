import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS V1协议测试
import websocket
import json
import struct
import time
from src.config import ACCESS_TOKEN, APP_ID, RESOURCE_ID

ENDPOINT = "openspeech.bytedance.com"

EVENT_START_CONNECTION = 1
EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_TASK_REQUEST = 200

def build_frame_v1(event_type, session_id="", payload=None):
    """V1协议帧 - 更简单的格式"""
    sid_bytes = session_id.encode('utf-8')
    payload_bytes = json.dumps(payload or {}).encode('utf-8')

    # V1格式: event_type(4B) + session_id_size(4B) + session_id + payload_size(4B) + payload
    event = struct.pack('>i', event_type)
    sid_size = struct.pack('>I', len(sid_bytes))
    payload_size = struct.pack('>I', len(payload_bytes))

    return event + sid_size + sid_bytes + payload_size + payload_bytes

def test():
    ws_url = f"wss://{ENDPOINT}/api/v1/tts/bidirection"  # 注意: v1路径
    headers = {
        "X-Api-App-Key": APP_ID,
        "X-Api-Access-Key": ACCESS_TOKEN,
        "X-Api-Resource-Id": RESOURCE_ID,
    }

    print(f"URL: {ws_url}")
    print(f"Headers: {headers}")

    audio_data = []
    session_id = f"sess_{int(time.time()*1000)}"

    def on_open(ws):
        print("连接成功")
        # V1 StartConnection
        ws.send(build_frame_v1(EVENT_START_CONNECTION, "", {}))

    def on_message(ws, msg):
        data = bytes(msg)
        print(f"收到 {len(data)} bytes")

        if len(data) < 8:
            return

        event = struct.unpack('>i', data[0:4])[0]
        print(f"事件: {event}")

        off = 4
        sid_sz = struct.unpack('>I', data[off:off+4])[0]
        off += 4 + sid_sz

        if off + 4 <= len(data):
            pl_sz = struct.unpack('>I', data[off:off+4])[0]
            off += 4
            if pl_sz > 0 and off + pl_sz <= len(data):
                content = data[off:off+pl_sz]
                try:
                    jd = json.loads(content.decode('utf-8'))
                    print(f"JSON: {jd}")

                    if event == 50:
                        print("✓ 连接就绪")
                        payload = {
                            "user": {"uid": "test"},
                            "req_params": {
                                "speaker": "en_male_tim_uranus_bigtts",
                                "audio_params": {"format": "mp3", "speech_rate": -18}
                            }
                        }
                        ws.send(build_frame_v1(EVENT_START_SESSION, session_id, payload))

                    elif event == 150:
                        print("✓ 会话就绪")
                        ws.send(build_frame_v1(EVENT_TASK_REQUEST, session_id, {"req_params": {"text": "Unless decoded, the plan fails."}}))
                        ws.send(build_frame_v1(EVENT_FINISH_SESSION, session_id, {}))

                    elif event == 152:
                        print("✓ 结束")
                        ws.close()
                except:
                    # 可能是音频数据
                    audio_data.append(content)
                    print(f"数据块: {len(content)} bytes")

    def on_close(ws, code, msg):
        if audio_data:
            with open("output/test.mp3", "wb") as f:
                f.write(b''.join(audio_data))
            print(f"✓ 保存: output/test.mp3")
        else:
            print("× 无音频")

    def on_error(ws, err):
        print(f"错误: {err}")

    ws = websocket.WebSocketApp(ws_url, header=headers, on_open=on_open, on_message=on_message, on_close=on_close, on_error=on_error)
    ws.run_forever()

if __name__ == "__main__":
    test()
