# -*- coding: utf-8 -*-
"""检查英文剧本 vs 中文剧本段落数是否相等。"""
import re
from pathlib import Path

EN = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\workespace\03_校园日常\纯英文版.md')
ZH = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\doc\支线\全局完整版\03_校园日常\03_校园日常_完整版.md')

def split_paragraphs(text):
    return [p.strip() for p in re.split(r'\n\s*\n', text) if p.strip() and not p.strip().startswith(('---', '##', '>', 'title:'))]

en_text = EN.read_text(encoding='utf-8')
zh_text = ZH.read_text(encoding='utf-8')

en_paras = split_paragraphs(en_text)
zh_paras = split_paragraphs(zh_text)

print(f'英文段数: {len(en_paras)}')
print(f'中文段数: {len(zh_paras)}')

# 列出前 20 段对比
print('\n前 20 段对比:')
for i, (en, zh) in enumerate(zip(en_paras[:20], zh_paras[:20])):
    en_first = en[:40].replace('\n', ' ')
    zh_first = zh[:40].replace('\n', ' ')
    print(f'{i:3d}. EN: {en_first}')
    print(f'     ZH: {zh_first}')
    print()
