import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS WebSocket 测试脚本（正确签名方式）
# 参考: https://www.volcengine.com/docs/6561/79823

import websocket
import hashlib
import hmac
import json
import time
import struct
from datetime import datetime, timezone
from urllib.parse import quote, urlencode
from src.config import SDK_AK, SDK_SK

AK = SDK_AK
SK = SDK_SK

# 服务配置
ENDPOINT = "openspeech.bytedance.com"
RESOURCE_ID = "seed-tts-2.0"
REGION = "cn-beijing"  # 火山引擎区域
SERVICE = "speech_saas_prod"  # 服务名称

# 事件编号
EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 3
EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_TASK_REQUEST = 200

def get_utc_time():
    """获取UTC时间"""
    return datetime.now(timezone.utc)

def hmac_sha256(key, msg):
    """HMAC-SHA256签名"""
    if isinstance(key, str):
        key = key.encode('utf-8')
    if isinstance(msg, str):
        msg = msg.encode('utf-8')
    return hmac.new(key, msg, hashlib.sha256).digest()

def get_signature_key(secret_key, date_stamp, region, service):
    """派生签名密钥"""
    k_date = hmac_sha256(secret_key, date_stamp)
    k_region = hmac_sha256(k_date, region)
    k_service = hmac_sha256(k_region, service)
    k_signing = hmac_sha256(k_service, 'request')
    return k_signing

def hash_sha256(data):
    """SHA256哈希"""
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()

def build_auth_headers():
    """构造签名认证headers"""
    now = get_utc_time()
    amz_date = now.strftime('%Y%m%dT%H%M%SZ')
    date_stamp = now.strftime('%Y%m%d')

    # HTTP方法（WebSocket升级使用GET）
    method = 'GET'
    path = '/api/v3/tts/bidirection'
    host = ENDPOINT

    # Query参数（需要按字母顺序排序）
    query_params = {
        'X-Api-Resource-Id': RESOURCE_ID,
    }
    canonical_querystring = urlencode(sorted(query_params.items()))

    # Canonical Headers（必须按名称排序，小写）
    canonical_headers = f'host:{host}\nx-content-sha256:UNSIGNED-PAYLOAD\n'
    signed_headers = 'host;x-content-sha256'

    # Payload hash（GET请求无body）
    payload_hash = 'UNSIGNED-PAYLOAD'

    # 构造Canonical Request
    canonical_request = f'{method}\n{path}\n{canonical_querystring}\n{canonical_headers}\n{signed_headers}\n{payload_hash}'
    canonical_request_hash = hash_sha256(canonical_request)

    # 构造String to Sign
    algorithm = 'HMAC-SHA256'
    credential_scope = f'{date_stamp}/{REGION}/{SERVICE}/request'
    string_to_sign = f'{algorithm}\n{amz_date}\n{credential_scope}\n{canonical_request_hash}'

    # 计算签名
    signing_key = get_signature_key(SK, date_stamp, REGION, SERVICE)
    signature = hmac.new(signing_key, string_to_sign.encode('utf-8'), hashlib.sha256).hexdigest()

    # 构造Authorization header
    authorization = f'{algorithm} Credential={AK}/{credential_scope}, SignedHeaders={signed_headers}, Signature={signature}'

    headers = {
        'Host': host,
        'Authorization': authorization,
        'X-Date': amz_date,
        'X-Content-Sha256': payload_hash,
        'X-Api-Resource-Id': RESOURCE_ID,
    }

    ws_url = f'wss://{host}{path}?{canonical_querystring}'

    print(f"URL: {ws_url}")
    print(f"Headers: {json.dumps(headers, indent=2)}")
    print(f"Canonical Request:\n{canonical_request}")
    print(f"String to Sign:\n{string_to_sign}")
    print(f"Signature: {signature}")

    return ws_url, headers

# 构造二进制请求帧
def build_request_frame(event_type, session_id=None, payload=None):
    session_id_str = session_id or ''
    session_id_bytes = session_id_str.encode('utf-8')
    payload_str = json.dumps(payload or {})
    payload_bytes = payload_str.encode('utf-8')

    header = bytes([0x11, 0x14, 0x10, 0x00])
    event_bytes = struct.pack('>i', event_type)
    session_size_bytes = struct.pack('>I', len(session_id_bytes))
    payload_size_bytes = struct.pack('>I', len(payload_bytes))

    return header + event_bytes + session_size_bytes + session_id_bytes + payload_size_bytes + payload_bytes

def generate_session_id():
    return f"sess_{int(time.time() * 1000)}_{hex(int(time.time() * 1000000) % 0xFFFFFF)[2:]}"

def test_tts():
    ws_url, headers = build_auth_headers()

    audio_data = []
    session_id = None

    def on_message(ws, message):
        nonlocal session_id
        data = message if isinstance(message, bytes) else message.encode('utf-8')
        print(f"\n收到数据: {len(data)} bytes")
        print(f"前30字节: {data[:30].hex()}")

        if len(data) < 4:
            return

        byte1 = data[1]
        message_type = (byte1 >> 4) & 0x0F
        flags = byte1 & 0x0F

        # 错误消息 (message type = 15)
        if message_type == 15:
            json_start = data.find(b'{')
            if json_start >= 0:
                try:
                    error_json = json.loads(data[json_start:].decode('utf-8'))
                    print(f"错误: {error_json}")
                except:
                    print(f"错误数据: {data[json_start:].decode('utf-8', errors='ignore')}")
            ws.close()
            return

        if len(data) < 12:
            return

        event_type = struct.unpack('>i', data[4:8])[0]
        offset = 8
        session_id_size = struct.unpack('>I', data[offset:offset+4])[0]
        offset += 4 + session_id_size

        print(f"事件类型: {event_type}, message_type: {message_type}")

        # JSON响应 (message type = 9)
        if message_type == 9:
            if offset + 4 <= len(data):
                json_size = struct.unpack('>I', data[offset:offset+4])[0]
                offset += 4
                if offset + json_size <= len(data):
                    json_str = data[offset:offset+json_size].decode('utf-8')
                    try:
                        json_data = json.loads(json_str)
                        print(f"JSON数据: {json_data}")
                    except:
                        print(f"JSON原始: {json_str}")

                    if event_type == 50:  # ConnectionStarted
                        print("✓ 连接成功！发送StartSession...")
                        session_id = generate_session_id()
                        payload = {
                            "user": {"uid": "user_001"},
                            "req_params": {
                                "speaker": "en_male_tim_uranus_bigtts",
                                "audio_params": {
                                    "format": "mp3",
                                    "sample_rate": 24000,
                                    "speech_rate": -18
                                }
                            }
                        }
                        ws.send(build_request_frame(EVENT_START_SESSION, session_id, payload))
                        print(f"session_id: {session_id}")

                    elif event_type == 150:  # SessionStarted
                        print("✓ 会话启动成功！发送文本...")
                        test_text = "Unless decoded, the plan fails."
                        ws.send(build_request_frame(EVENT_TASK_REQUEST, session_id, {"req_params": {"text": test_text}}))
                        print(f"文本: {test_text}")
                        ws.send(build_request_frame(EVENT_FINISH_SESSION, session_id, {}))
                        print("发送FinishSession")

                    elif event_type == 152:  # SessionFinished
                        print("✓ 会话结束")
                        ws.session_finished = True
            return

        # 音频响应 (message type = 11)
        if message_type == 11:
            audio_chunk = data[offset:]
            audio_data.append(audio_chunk)
            print(f"收到音频: {len(audio_chunk)} bytes, 总计: {sum(len(d) for d in audio_data)} bytes, isLast: {flags >= 2}")
            if flags >= 2:
                ws.audio_complete = True
            return

    def on_error(ws, error):
        print(f"WebSocket错误: {error}")

    def on_close(ws, close_status_code, close_msg):
        print(f"\n连接关闭: code={close_status_code}")
        if audio_data:
            output_path = "output/test_sample.mp3"
            total_size = sum(len(d) for d in audio_data)
            with open(output_path, 'wb') as f:
                f.write(b''.join(audio_data))
            print(f"✓ 音频已保存: {output_path} ({total_size} bytes)")
        else:
            print("× 未收到音频数据")

    def on_open(ws):
        print("WebSocket连接已建立，发送StartConnection...")
        ws.audio_complete = False
        ws.session_finished = False

        # StartConnection帧（无session_id）
        header = bytes([0x11, 0x14, 0x10, 0x00])
        event_bytes = struct.pack('>i', EVENT_START_CONNECTION)
        session_size_bytes = struct.pack('>I', 0)
        payload_bytes = b'{}'
        payload_size_bytes = struct.pack('>I', len(payload_bytes))
        ws.send(header + event_bytes + session_size_bytes + payload_size_bytes + payload_bytes)
        print("已发送StartConnection")

    ws = websocket.WebSocketApp(
        ws_url,
        header=headers,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close
    )

    ws.run_forever()

if __name__ == "__main__":
    test_tts()
