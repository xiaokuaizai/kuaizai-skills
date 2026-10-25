# 火山引擎 TTS 公共配置
# 所有生成脚本共享的凭证、代理和音色配置
import os
from pathlib import Path


def load_env(env_path):
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key, value)


ENV_PATH = Path(__file__).resolve().parents[1] / ".env"
load_env(ENV_PATH)

APP_ID = os.getenv("VOLC_APP_ID", "")
ACCESS_TOKEN = os.getenv("VOLC_ACCESS_TOKEN", "")
ACCESS_KEY = ACCESS_TOKEN
SECRET_KEY = os.getenv("VOLC_SECRET_KEY", "")
ARK_API_KEY = os.getenv("ARK_API_KEY", os.getenv("VOLC_TTS_API_KEY", ""))
SDK_AK = os.getenv("VOLC_AK", "")
SDK_SK = os.getenv("VOLC_SK", "")
SDK_APP_ID = os.getenv("VOLC_SDK_APP_ID", "")
SDK_INSTANCE_ID = os.getenv("VOLC_SDK_INSTANCE_ID", "")
RESOURCE_ID = os.getenv("VOLC_TTS_RESOURCE_ID", "seed-tts-2.0")
TTS_ENDPOINT = os.getenv("VOLC_TTS_ENDPOINT", "wss://openspeech.bytedance.com/api/v3/tts/bidirection")

PROXY_URL = os.getenv("PROXY_URL", "http://127.0.0.1:7898")
PROXIES = {
    "http": PROXY_URL,
    "https": PROXY_URL
} if PROXY_URL else None

# V1 HTTP 非流式接口
API_URL = "https://openspeech.bytedance.com/api/v1/tts"

# 已确认和暂定的角色音色配置
# 第二章新增角色先使用主选音色，小样确认后再批量生成全章音频。
VOICE_CONFIG = {
    "jiang_che": "zh_male_M100_conversation_wvae_bigtts",
    "an_qi": "en_female_dacey_uranus_bigtts",
    "father": "en_male_sylus_emo_v2_mars_bigtts",
    "mother": "en_female_skye_emo_v2_mars_bigtts",
    "teacher_li": "en_male_michael_moon_bigtts",
    "narrator": "en_male_tim_uranus_bigtts",
    "director_chen": "en_male_bruce_moon_bigtts",
    "legal_staff": "en_male_glen_emo_v2_mars_bigtts",
    "diary": "en_male_tim_uranus_bigtts",
    "boy": "zh_male_shaonianzixin_moon_bigtts"
}

# 第二章待确认角色的主选/备选音色
# 小样脚本会先试主选音色，失败时再试备选音色。
VOICE_OPTIONS_CHAPTER2 = {
    "director_chen": {
        "primary": "en_male_bruce_moon_bigtts",
        "fallback": "en_male_sylus_emo_v2_mars_bigtts"
    },
    "legal_staff": {
        "primary": "en_male_glen_emo_v2_mars_bigtts",
        "fallback": "en_male_michael_moon_bigtts"
    },
    "diary": {
        "primary": "en_male_tim_uranus_bigtts",
        "fallback": "en_female_skye_emo_v2_mars_bigtts"
    },
    "boy": {
        "primary": "zh_male_shaonianzixin_moon_bigtts",
        "fallback": "zh_male_M100_conversation_wvae_bigtts"
    }
}

# 角色中文名
ROLE_DISPLAY = {
    "jiang_che": "江彻",
    "an_qi": "安琪",
    "father": "父亲",
    "mother": "母亲",
    "teacher_li": "李老师",
    "narrator": "旁白",
    "director_chen": "陈总监",
    "legal_staff": "法务人员",
    "diary": "南极手记",
    "boy": "男孩"
}

# 默认语速（1.0 = 正常语速）
DEFAULT_SPEED_RATIO = 1.0
