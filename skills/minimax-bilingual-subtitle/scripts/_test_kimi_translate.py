# -*- coding: utf-8 -*-
"""测试 Kimi API 连通性 + 翻译效果。"""
import os
import sys
import urllib.request
import json

# 从环境变量读 Kimi 配置
AUTH_TOKEN = os.environ.get('ANTHROPIC_AUTH_TOKEN')
BASE_URL = os.environ.get('ANTHROPIC_BASE_URL', 'https://api.kimi.com/coding/')
MODEL = os.environ.get('ANTHROPIC_MODEL', 'kimi-for-coding')

if not AUTH_TOKEN:
    print('[错误] 环境变量 ANTHROPIC_AUTH_TOKEN 未设置')
    sys.exit(1)

# 规范化 base_url
if not BASE_URL.endswith('/'):
    BASE_URL += '/'
if not BASE_URL.endswith('/v1/'):
    BASE_URL += 'v1/'

url = BASE_URL + 'messages'
print(f'[INFO] API URL: {url}')
print(f'[INFO] Model: {MODEL}')

# 测试翻译一条
test_en = "Good morning, my friend,"

payload = {
    "model": MODEL,
    "max_tokens": 1024,
    "messages": [
        {
            "role": "user",
            "content": f"""把下面这句英文台词翻译成中文，只返回翻译结果，不要任何解释。

要求：
1. 保留原文的语气和标点风格
2. 不要意译，要直译
3. 输出纯文本，不要引号、不要前缀

英文：{test_en}"""
        }
    ]
}

req = urllib.request.Request(
    url,
    data=json.dumps(payload).encode('utf-8'),
    headers={
        'Content-Type': 'application/json',
        'x-api-key': AUTH_TOKEN,
        'anthropic-version': '2023-06-01',
    },
    method='POST',
)

try:
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode('utf-8'))
        print()
        print('[成功] API 响应：')
        print(json.dumps(data, ensure_ascii=False, indent=2)[:500])
        # 提取翻译结果（Kimi 会返回 thinking + text 多块，要过滤 type == 'text'）
        if 'content' in data:
            for block in data['content']:
                if block.get('type') == 'text':
                    zh = block.get('text', '').strip()
                    print()
                    print(f'原文: {test_en}')
                    print(f'译文: {zh}')
                    break
except Exception as e:
    print(f'[错误] {type(e).__name__}: {e}')
    if hasattr(e, 'read'):
        try:
            err_body = e.read().decode('utf-8')
            print(f'响应体: {err_body[:500]}')
        except Exception:
            pass
