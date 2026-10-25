# -*- coding: utf-8 -*-
"""检查合并后的 SU-09-D3 在哪个索引。"""
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
merged_su_list = []
cur_group = None
for su in su_list:
    key = (su['type'], su['speaker_en'])
    if cur_group and cur_group['key'] == key:
        cur_group['sus'].append(su)
    else:
        if cur_group:
            merged_su_list.append(cur_group)
        cur_group = {'key': key, 'sus': [su]}
if cur_group:
    merged_su_list.append(cur_group)

# 找 SU-09-D3 在哪个组
for gi, g in enumerate(merged_su_list):
    for su in g['sus']:
        if su['su_id'] in ('SU-09-D3', 'SU-09-D5'):
            print(f'组 {gi}: SU={su["su_id"]} speaker={su["speaker_en"]}')
            print(f'  本组所有 SU: {[s["su_id"] for s in g["sus"]]}')
            print(f'  对应 zh_unit: {zh_units[gi]["text_zh"][:50]}')
            print()
