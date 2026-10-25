# -*- coding: utf-8 -*-
"""确认 SU-09-D3 / SU-10-D2 在 SU 表和 zh_units 里的索引。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from su_table_parser import parse_su_table
from zh_script_parser import parse_zh_script

SU = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\workespace\03_校园日常\故事板\doc\文本语义拆分表.md')
ZH = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\doc\支线\全局完整版\03_校园日常\03_校园日常_完整版.md')

su_list = parse_su_table(SU)
zh_units = parse_zh_script(ZH, ['安琪', '江彻', '英语老师', '数学老师', '科学老师', '历史老师', '图书管理员'])

# 找 SU-09-D3 在 SU 表的索引
for i, su in enumerate(su_list):
    if su['su_id'] in ('SU-09-D2', 'SU-09-D3', 'SU-09-D4', 'SU-10-D2'):
        print(f'SU idx {i}: {su["su_id"]} - {su["fragments"][0][:50]}')

print()
# 找对应 zh_unit 的索引（"你的家庭一定很热闹"）
for i, zh in enumerate(zh_units):
    if '你的家庭' in zh['text_zh'] or '先把数学' in zh['text_zh']:
        print(f'zh idx {i}: {zh["speaker_zh"]} - {zh["text_zh"][:50]}')
