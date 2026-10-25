import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS - 纯V1格式
import websocket
import struct
import time
from src.config import ACCESS_TOKEN, APP_ID, RESOURCE_ID, TTS_ENDPOINT

ws_url = TTS_ENDPOINT
headers = {"X-Api-App-Key": APP_ID, "X-Api-Access-Key": ACCESS_TOKEN, "X-Api-Resource-Id": RESOURCE_ID}

def frame(event, sid=b"", payload=b""):
    # 纯V1: event(4) + sid_size(4) + sid + payload_size(4) + payload
    return struct.pack('>i', event) + struct.pack('>I', len(sid)) + sid + struct.pack('>I', len(payload)) + payload

def on_open(ws):
    print("连接")
    ws.send(frame(1))  # StartConnection

def on_msg(ws, m):
    d = bytes(m)
    print(f"收到{len(d)}B: {d.hex()}")
    if b'error' in d:
        print(d.decode('utf-8', errors='ignore'))
    ws.close()

ws = websocket.WebSocketApp(ws_url, header=headers, on_open=on_open, on_message=on_msg)
ws.run_forever()
