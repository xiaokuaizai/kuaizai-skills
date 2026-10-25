# -*- coding: utf-8 -*-
"""检查 SU-09 区域 speaker 分布。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from su_table_parser import parse_su_table

SU = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\workespace\03_校园日常\故事板\doc\文本语义拆分表.md')
su_list = parse_su_table(SU)

# 列出 SU-09 全部
print('SU-09 全部:')
for su in su_list:
    if su['su_id'].startswith('SU-09'):
        print(f'  {su["su_id"]:15s} speaker={su["speaker_en"]:20s} frags={su["fragments"][0][:40]}')

# 列出 SU-10 全部
print('\nSU-10 全部:')
for su in su_list:
    if su['su_id'].startswith('SU-10'):
        print(f'  {su["su_id"]:15s} speaker={su["speaker_en"]:20s} frags={su["fragments"][0][:40]}')

# 所有 speaker
print('\n所有 speaker 类型:')
speakers = set(su['speaker_en'] for su in su_list)
for s in sorted(speakers):
    count = sum(1 for su in su_list if su['speaker_en'] == s)
    print(f'  {s}: {count}')
