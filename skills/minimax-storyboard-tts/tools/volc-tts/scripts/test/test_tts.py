import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 测试脚本（使用官方SDK）
from volcengine.tts import TtsService
from src.config import SDK_AK, SDK_APP_ID, SDK_INSTANCE_ID, SDK_SK

ak = SDK_AK
sk = SDK_SK

missing = [
    name for name, value in [
        ("VOLC_AK", ak),
        ("VOLC_SK", sk),
        ("VOLC_SDK_APP_ID", SDK_APP_ID),
        ("VOLC_SDK_INSTANCE_ID", SDK_INSTANCE_ID)
    ] if not value
]

if missing:
    raise RuntimeError(f"Missing required settings in TTS/.env: {', '.join(missing)}")

# 实例化客户端
tts_service = TtsService(ak, sk)
tts_service.set_app_id(SDK_APP_ID)

# 测试文本（英文）
test_text = "Unless decoded, the plan fails. This is not ordinary noise."

# 合成参数配置（慢语速 -18）
resp = tts_service.synthesis(
    text=test_text,
    voice_type="en_male_tim_uranus_bigtts",  # Tim - 2.0英文男声
    instance_id=SDK_INSTANCE_ID,
    encoding="mp3",
    speech_rate=-18  # 慢语速
)

# 保存音频文件
output_path = "output/test_sample.mp3"
with open(output_path, "wb") as f:
    f.write(resp.data)

print(f"音频已保存: {output_path} ({len(resp.data)} bytes)")
