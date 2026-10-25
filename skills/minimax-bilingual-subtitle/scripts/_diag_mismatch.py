# -*- coding: utf-8 -*-
"""诊断 SU 表 vs zh_units 差异。

SU 表 96 个，zh_units 81 个，差 15 个。
需要找出：哪些 SU 在表里但不在剧本里？
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from su_table_parser import parse_su_table
from zh_script_parser import parse_zh_script

SU = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\workespace\03_校园日常\故事板\doc\文本语义拆分表.md')
ZH = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\doc\支线\全局完整版\03_校园日常\03_校园日常_完整版.md')

su_list = parse_su_table(SU)
zh_units = parse_zh_script(ZH, ['安琪', '江彻', '英语老师', '数学老师', '科学老师', '历史老师', '图书管理员'])

print(f'SU 整段: {len(su_list)}')
print(f'zh_units: {len(zh_units)}')
print(f'差: {len(su_list) - len(zh_units)}')

# 列出所有 SU ID 和类型
print('\n=== SU 表（按序）===')
for i, su in enumerate(su_list):
    frag_summary = f"frags={len(su['fragments'])}" if len(su['fragments']) > 1 else 'single'
    print(f'{i:3d}. {su["su_id"]:15s} {su["type"]:10s} {frag_summary}  {su["fragments"][0][:50]}')

print('\n=== zh_units（按序）===')
for i, zh in enumerate(zh_units):
    print(f'{i:3d}. {zh["speaker_zh"]:10s}  {zh["text_zh"][:50]}')
