# -*- coding: utf-8 -*-
"""
共享配置读取模块

功能：
  从 .env 文件读取 OSS 凭证和配置，供多个脚本复用。
"""

import os
from pathlib import Path


# skill 根目录：本文件上级目录
SKILL_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = SKILL_DIR / ".env"


def load_env(env_path: Path = ENV_PATH) -> dict:
    """读取 .env 文件，返回配置字典"""
    config = {}
    if not env_path.exists():
        return config

    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        # 跳过空行和注释
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        config[key] = value
    return config


def get_oss_config() -> dict:
    """获取 OSS 配置，优先 .env，其次环境变量"""
    env_config = load_env()
    return {
        "access_key_id": env_config.get("OSS_ACCESS_KEY_ID") or os.getenv("OSS_ACCESS_KEY_ID", ""),
        "access_key_secret": env_config.get("OSS_ACCESS_KEY_SECRET") or os.getenv("OSS_ACCESS_KEY_SECRET", ""),
        "region": env_config.get("OSS_REGION") or os.getenv("OSS_REGION", "oss-cn-shenzhen"),
        "bucket": env_config.get("OSS_BUCKET") or os.getenv("OSS_BUCKET", "getwallet"),
        "public_base_url": env_config.get("PUBLIC_BASE_URL") or os.getenv(
            "PUBLIC_BASE_URL", "https://getwallet.oss-cn-shenzhen.aliyuncs.com"
        ),
    }


def check_credentials() -> None:
    """检查 OSS 凭证是否完整，不完整则抛异常"""
    cfg = get_oss_config()
    if not cfg["access_key_id"] or not cfg["access_key_secret"]:
        raise RuntimeError("缺少 OSS 凭证，请检查 .env 文件中的 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET")
