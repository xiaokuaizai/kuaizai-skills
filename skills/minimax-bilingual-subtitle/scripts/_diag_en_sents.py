# -*- coding: utf-8 -*-
"""按句拆分英文剧本，看句数是否等于 SU 数。"""
import re
from pathlib import Path

EN = Path(r'F:\AA_Company_project\AA_main\Lexi\Media\Append\workespace\03_校园日常\纯英文版.md')
text = EN.read_text(encoding='utf-8')

# 按句拆分（.!? 结尾）
# 先去掉【Narration】等标记
text = re.sub(r'【Narration】', '', text)
text = re.sub(r'【Dialogue】', '', text)
text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)  # 去 ** 标记

# 按句末标点拆分
sentences = re.split(r'(?<=[.!?])\s+(?=[A-Z"【])', text)
sentences = [s.strip() for s in sentences if s.strip() and not s.strip().startswith(('---', '##', '>'))]
print(f'英文剧本按句拆分: {len(sentences)} 句')

# 看前 20 句
for i, s in enumerate(sentences[:20]):
    print(f'{i:3d}. {s[:70]}')
