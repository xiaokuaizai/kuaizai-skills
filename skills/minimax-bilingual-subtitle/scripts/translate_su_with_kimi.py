# -*- coding: utf-8 -*-
"""调用 Kimi API 批量翻译 SU 拆分表的所有 fragments。

输入：SU 拆分表（含 fragments 列表）
输出：{workspace}/su_zh.json
  格式：{frag_id: "中文译文"}
        frag_id 是 SU 表的拆分片段 ID，如 "SU-01-N1a"、"SU-01-D1"

每次调用翻译 1 个 fragment，避免长文本返回不稳定。
已存在的翻译会跳过（除非 --force）。
"""
import argparse
import json
import os
import re
import sys
import time
import urllib.request
from pathlib import Path

# 把 lib/ 加入 path
sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from su_table_parser import parse_su_table


def call_kimi(prompt: str, max_retries: int = 3, timeout: int = 60) -> str:
    """调用 Kimi API，返回翻译结果。失败重试。"""
    auth_token = os.environ.get('ANTHROPIC_AUTH_TOKEN')
    base_url = os.environ.get('ANTHROPIC_BASE_URL', 'https://api.kimi.com/coding/')
    model = os.environ.get('ANTHROPIC_MODEL', 'kimi-for-coding')

    if not auth_token:
        raise RuntimeError('环境变量 ANTHROPIC_AUTH_TOKEN 未设置')

    if not base_url.endswith('/'):
        base_url += '/'
    if not base_url.endswith('/v1/'):
        base_url += 'v1/'

    url = base_url + 'messages'

    payload = {
        "model": model,
        "max_tokens": 1024,
        "messages": [
            {"role": "user", "content": prompt}
        ]
    }

    last_err = None
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode('utf-8'),
                headers={
                    'Content-Type': 'application/json',
                    'x-api-key': auth_token,
                    'anthropic-version': '2023-06-01',
                },
                method='POST',
            )
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                # Kimi 会返回 thinking + text 多块，过滤 type == 'text'
                for block in data.get('content', []):
                    if block.get('type') == 'text':
                        return block.get('text', '').strip()
                raise RuntimeError(f'响应中没有 text 块: {data}')
        except Exception as e:
            last_err = e
            wait = 2 ** attempt  # 1, 2, 4 秒
            print(f'  [WARN] 第 {attempt + 1} 次失败: {e}，{wait}s 后重试')
            time.sleep(wait)

    raise RuntimeError(f'调用 Kimi 失败 {max_retries} 次: {last_err}')


def build_prompt(en_text: str, utype: str, speaker_en: str) -> str:
    """构造翻译提示词。utype: narration / dialogue。"""
    if utype == 'narration':
        role_desc = '旁白（narration）'
    else:
        role_desc = f'角色 {speaker_en} 的对白'

    return f"""把下面这句英文{role_desc}翻译成中文，只返回翻译结果，不要任何解释。

要求：
1. 保留原文的语气和标点风格（句末逗号/句号）
2. 直译不要意译
3. 输出纯文本，不要引号、不要前缀、不要 markdown
4. 一行内完成

英文：{en_text}"""


def main():
    parser = argparse.ArgumentParser(description='用 Kimi API 翻译 SU 拆分表')
    parser.add_argument('--su-table', required=True, help='SU 拆分表路径')
    parser.add_argument('--workspace', required=True, help='输出工作区')
    parser.add_argument('--force', action='store_true', help='强制重新翻译（覆盖已有）')
    parser.add_argument('--delay', type=float, default=0.5, help='每次调用间隔秒数（默认 0.5）')
    parser.add_argument('--per-sentence', action='store_true', default=True,
                        help='按英文句子粒度翻译（推荐，避免多句 SU 中文错位）')
    args = parser.parse_args()

    su_table = Path(args.su_table)
    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    # 1. 解析 SU 表
    su_list = parse_su_table(su_table)
    print(f'[INFO] SU 拆分表解析到 {len(su_list)} 个 SU')

    # 2. 收集所有 (frag_id, frag_text, type, speaker_en)
    #    若 --per-sentence，多句 fragment 拆成单句逐条翻译
    sys.path.insert(0, str(Path(__file__).parent / 'lib'))
    from subtitle_splitter import split_en_sentences

    to_translate = []  # [(frag_id, en_text, utype, speaker_en)]
    for su in su_list:
        for frag_id, frag_text in zip(su['frag_ids'], su['fragments']):
            if args.per_sentence:
                # 按英文句末标点拆分
                sents = split_en_sentences(frag_text)
                if len(sents) <= 1:
                    to_translate.append((frag_id, frag_text, su['type'], su['speaker_en']))
                else:
                    # 多句：为每句生成独立 key（frag_id__1, frag_id__2, ...）
                    for i, sent in enumerate(sents, start=1):
                        sub_id = f'{frag_id}__{i}'
                        to_translate.append((sub_id, sent, su['type'], su['speaker_en']))
            else:
                to_translate.append((frag_id, frag_text, su['type'], su['speaker_en']))

    print(f'[INFO] 共 {len(to_translate)} 个翻译单元（含多句拆分）')

    # 3. 加载已有翻译
    out_file = workspace / 'su_zh.json'
    if out_file.exists() and not args.force:
        existing = json.loads(out_file.read_text(encoding='utf-8'))
        print(f'[INFO] 已有 {len(existing)} 条翻译')
    else:
        existing = {}

    # 4. 逐个翻译
    n_new = 0
    n_fail = 0
    for i, (frag_id, en_text, utype, speaker_en) in enumerate(to_translate, start=1):
        if frag_id in existing and existing[frag_id]:
            print(f'  [{i}/{len(to_translate)}] 跳过（已存在）: {frag_id}')
            continue

        prompt = build_prompt(en_text, utype, speaker_en)
        try:
            zh = call_kimi(prompt)
            # 清洗：去引号、去 markdown 标记
            zh = zh.strip().strip('"').strip()
            # 去可能的前缀（如 "译文：" "翻译结果："）
            zh = re.sub(r'^(译文|翻译结果|翻译|中文)[:：]\s*', '', zh).strip()
            existing[frag_id] = zh
            n_new += 1
            print(f'  [{i}/{len(to_translate)}] {frag_id}: {en_text[:40]} → {zh[:40]}')
        except Exception as e:
            n_fail += 1
            print(f'  [{i}/{len(to_translate)}] [FAIL] {frag_id}: {e}')

        # 每次调用后保存进度
        if i % 5 == 0 or i == len(to_translate):
            out_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')

        time.sleep(args.delay)

    # 最终保存
    out_file.write_text(json.dumps(existing, ensure_ascii=False, indent=2), encoding='utf-8')

    print()
    print(f'[完成] 新增 {n_new} 条，失败 {n_fail} 条，共 {len(existing)} 条')
    print(f'[输出] {out_file}')


if __name__ == '__main__':
    main()
