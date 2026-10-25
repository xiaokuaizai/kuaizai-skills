# -*- coding: utf-8 -*-
"""按"连续同说话人"合并 SU，看是否能对上 zh_units。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from su_table_parser import parse_su_table
from zh_script_parser import parse_zh_script

SU = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\workespace\03_校园日常\故事板\doc\文本语义拆分表.md')
ZH = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\doc\支线\全局完整版\03_校园日常\03_校园日常_完整版.md')

su_list = parse_su_table(SU)
zh_units = parse_zh_script(ZH, ['安琪', '江彻', '英语老师', '数学老师', '科学老师', '历史老师', '图书管理员'])

# 按"连续同说话人"合并 SU
merged = []
cur_group = None
for su in su_list:
    key = (su['type'], su['speaker_en'])
    if cur_group and cur_group['key'] == key:
        cur_group['sus'].append(su)
    else:
        if cur_group:
            merged.append(cur_group)
        cur_group = {'key': key, 'sus': [su]}
if cur_group:
    merged.append(cur_group)

print(f'合并后 SU 组数: {len(merged)}')
print(f'zh_units 数: {len(zh_units)}')
print()

# 对比
for i, (g, zh) in enumerate(zip(merged, zh_units)):
    su_speaker = g['key'][1]
    su_text = ' | '.join(s['su_id'] for s in g['sus'])
    zh_speaker = zh['speaker_zh']
    match = '✓' if su_speaker == zh_speaker or (su_speaker == 'Narrator' and zh_speaker == '旁白') else '✗'
    print(f'{i:3d}. {match} SU={su_speaker:15s} ZH={zh_speaker:10s} | {su_text[:40]}')
