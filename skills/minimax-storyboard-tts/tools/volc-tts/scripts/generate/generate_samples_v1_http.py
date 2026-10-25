import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# 火山引擎 TTS 批量生成角色语音样本（V1 HTTP 1.0大模型）
# 使用V1 HTTP非流式接口，自动在主选音色失败时尝试备选音色
import requests
import json
import uuid
import base64
import os
import time
from src.config import ACCESS_TOKEN, API_URL, APP_ID, DEFAULT_SPEED_RATIO, PROXIES

OUTPUT_DIR = "output/samples"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 每个角色的样本文本（自我介绍/代表台词）
SAMPLE_TEXTS = {
    "jiang_che": "Unless decoded, the plan fails. This is not ordinary noise.",
    "an_qi": "I will join. Do not investigate this alone.",
    "father": "That is not a joke. It is a test signal we left ten years ago.",
    "mother": "Record everything first. Do not explain it too soon.",
    "teacher_li": "From the frequency, structure, and coordinate logic, it looks like a scientific test signal.",
    "narrator": "At 2:17 a.m., the old radio in the garage suddenly came alive."
}

# 角色音色配置：主选音色 + 1.0大模型备选音色
VOICE_CONFIG = {
    "jiang_che": {
        "primary": "zh_male_M100_conversation_wvae_bigtts",
        "fallback": "zh_male_shaonianzixin_moon_bigtts",
        "display": "江彻"
    },
    "an_qi": {
        "primary": "en_female_dacey_uranus_bigtts",
        "fallback": "zh_female_cancan_mars_bigtts",
        "display": "安琪"
    },
    "father": {
        "primary": "en_male_sylus_emo_v2_mars_bigtts",
        "fallback": "en_male_bruce_moon_bigtts",
        "display": "父亲"
    },
    "mother": {
        "primary": "en_female_skye_emo_v2_mars_bigtts",
        "fallback": "en_female_nadia_tips_emo_v2_mars_bigtts",
        "display": "母亲"
    },
    "teacher_li": {
        "primary": "en_male_michael_moon_bigtts",
        "fallback": "en_male_glen_emo_v2_mars_bigtts",
        "display": "李老师"
    },
    "narrator": {
        "primary": "en_male_tim_uranus_bigtts",
        "fallback": "en_male_corey_emo_v2_mars_bigtts",
        "display": "旁白"
    }
}

# 固定请求头
HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}


def synthesize(text, voice_type):
    """调用V1 HTTP接口合成单句语音，返回音频二进制数据或错误信息"""
    payload = {
        "app": {
            "appid": APP_ID,
            "token": ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {"uid": "novel_tts_user"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": DEFAULT_SPEED_RATIO,  # 使用公共默认语速
            "rate": 24000
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query"
        }
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, proxies=PROXIES, timeout=60)
        result = resp.json()
    except Exception as e:
        return None, f"请求异常: {e}"

    if result.get("code") == 3000 and "data" in result:
        return base64.b64decode(result["data"]), None
    else:
        return None, result.get("message", f"code={result.get('code')}")


def generate_role_sample(role):
    """生成单个角色的样本，主选失败则尝试备选"""
    cfg = VOICE_CONFIG[role]
    text = SAMPLE_TEXTS[role]
    display = cfg["display"]

    print(f"\n【{display}】")
    print(f"  文本: {text}")

    # 先尝试主选音色
    for voice_key in ["primary", "fallback"]:
        voice_type = cfg[voice_key]
        label = "主选" if voice_key == "primary" else "备选"
        print(f"  尝试{label}音色: {voice_type}")

        audio, err = synthesize(text, voice_type)
        if audio:
            output_path = os.path.join(OUTPUT_DIR, f"{role}_sample.mp3")
            with open(output_path, "wb") as f:
                f.write(audio)
            print(f"  [OK] 成功 [{label}] -> {output_path} ({len(audio)} bytes)")
            return {
                "role": role,
                "display": display,
                "voice_type": voice_type,
                "voice_source": label,
                "path": output_path,
                "size": len(audio),
                "success": True
            }
        else:
            print(f"  [FAIL] {label}失败: {err}")

    return {
        "role": role,
        "display": display,
        "voice_type": None,
        "voice_source": None,
        "path": None,
        "size": 0,
        "success": False
    }


def main():
    print("=" * 60)
    print("火山引擎 TTS 角色语音样本生成")
    print(f"接口: V1 HTTP 非流式 | 模型: 1.0大模型 | 语速: {DEFAULT_SPEED_RATIO}")
    print("=" * 60)

    results = []
    for role in SAMPLE_TEXTS.keys():
        res = generate_role_sample(role)
        results.append(res)
        time.sleep(0.5)  # 避免请求过快

    # 汇总
    print("\n" + "=" * 60)
    print("生成结果汇总")
    print("=" * 60)
    success_count = 0
    for r in results:
        status = "[OK] 成功" if r["success"] else "[FAIL] 失败"
        voice = r["voice_type"] or "无"
        source = r["voice_source"] or "-"
        print(f"  {r['display']:<6} {status:<6} [{source}] {voice}")
        if r["success"]:
            success_count += 1

    print(f"\n成功: {success_count}/{len(results)}")

    # 输出最终音色配置表
    print("\n最终使用音色配置:")
    print("-" * 60)
    for r in results:
        if r["success"]:
            print(f"{r['display']:<6} | {r['voice_source']:<4} | {r['voice_type']}")


if __name__ == "__main__":
    main()
