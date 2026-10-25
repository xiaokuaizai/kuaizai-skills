# -*- coding: utf-8 -*-
"""检查 zh_units 的 speaker 分布。"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from zh_script_parser import parse_zh_script

ZH = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\doc\支线\全局完整版\03_校园日常\03_校园日常_完整版.md')
zh_units = parse_zh_script(ZH, ['安琪', '江彻', '英语老师', '数学老师', '科学老师', '历史老师', '图书管理员'])

from collections import Counter
speakers = Counter(zh['speaker_zh'] for zh in zh_units)
for s, c in speakers.most_common():
    print(f'{s}: {c}')
