# -*- coding: utf-8 -*-
"""测试不同合并策略的组数。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from su_table_parser import parse_su_table
from zh_script_parser import parse_zh_script

SU = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\workespace\03_校园日常\故事板\doc\文本语义拆分表.md')
ZH = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\doc\支线\全局完整版\03_校园日常\03_校园日常_完整版.md')

su_list = parse_su_table(SU)
zh_units = parse_zh_script(ZH, ['安琪', '江彻', '英语老师', '数学老师', '科学老师', '历史老师', '图书管理员'])
print(f'zh_units: {len(zh_units)}')

# 策略 A：按 (type, speaker) 合并
def group_a(su_list):
    groups = []
    cur = None
    for su in su_list:
        key = (su['type'], su['speaker_en'])
        if cur and cur['key'] == key:
            cur['sus'].append(su)
        else:
            if cur: groups.append(cur)
            cur = {'key': key, 'sus': [su]}
    if cur: groups.append(cur)
    return groups

# 策略 B：按 type 合并
def group_b(su_list):
    groups = []
    cur = None
    for su in su_list:
        key = su['type']
        if cur and cur['key'] == key:
            cur['sus'].append(su)
        else:
            if cur: groups.append(cur)
            cur = {'key': key, 'sus': [su]}
    if cur: groups.append(cur)
    return groups

ga = group_a(su_list)
gb = group_b(su_list)
print(f'策略 A (type, speaker): {len(ga)} 组')
print(f'策略 B (type only):     {len(gb)} 组')
print(f'zh_units:               {len(zh_units)}')

# 看策略 B 分组情况
print('\n策略 B 分组:')
for i, g in enumerate(gb[:20]):
    first = g['sus'][0]
    last = g['sus'][-1]
    print(f'组 {i:3d} ({g["key"]}): {first["su_id"]} ~ {last["su_id"]} ({len(g["sus"])} SU) → zh: {zh_units[i]["text_zh"][:40] if i < len(zh_units) else "?"}')
