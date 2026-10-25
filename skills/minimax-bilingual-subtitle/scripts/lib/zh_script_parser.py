# -*- coding: utf-8 -*-
"""中文剧本解析器：从中文版 .md 提取 zh_units（按 SU 整段）。

格式：
  【旁白】周五下午，学校体育馆gym门口stick着一张鲜红的招募海报。
  "加入体育俱乐部能锻炼体能..."安琪眨眨眼。

支持段落类型：
  - 旁白：以 【旁白】/【Narrator】 开头
  - 对白：以 "..." 包裹，后跟说话人 + 动作描述
  - 元信息段（---、>、##、title:）自动跳过

清洗规则：
  - **中文English** 词汇标注（如 **雾foggy**）：去英文只留中文
  - **English**（如 **pronounce**）：保留英文（是台词实词）
"""
import re
from pathlib import Path


def clean_vocab(s: str) -> str:
    """清洗 **中文English** / **English** 词汇标注。"""
    def strip_in_stars(m):
        inner = m.group(1)
        # 含中文 → **中文English** → 去英文留中文
        has_chinese = bool(re.search(r'[一-鿿]', inner))
        if has_chinese:
            inner = re.sub(r"[A-Za-z][A-Za-z\-\']*", '', inner)
            return inner
        # 纯英文: 看 ** 前一个字符——紧邻中文时是中文的英文注解(如 "一家人**family**"),
        # 应剔除; 仅在前面是空格/标点/开头时视为台词实词保留
        start = m.start()
        if start > 0 and re.search(r'[一-鿿]', m.string[start - 1]):
            return ''
        return inner
    s = re.sub(r'\*\*([^*]+)\*\*', strip_in_stars, s)
    # 去残留的 ** 标记
    s = s.replace('**', '')
    # 压缩空格
    s = re.sub(r'\s+', ' ', s).strip()
    # 去孤立标点前的空格
    s = re.sub(r'\s+([，。！？；：、）」])', r'\1', s)
    s = re.sub(r'([（「])\s+', r'\1', s)
    return s


def parse_zh_script(zh_script_path: Path, characters: list) -> list:
    """解析中文版剧本，返回 zh_units 列表。

    返回：[{"idx": 1, "type": "narration", "speaker_zh": "旁白", "text_zh": "..."}, ...]
    """
    text = zh_script_path.read_text(encoding='utf-8')
    paragraphs = re.split(r'\n\s*\n', text)

    units = []
    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        # 跳过元信息段
        if para.startswith('---') or para.startswith('>') or para.startswith('##') \
           or para.startswith('title:') or para.startswith('#'):
            continue

        # 旁白：【旁白】... 或 【Narrator】...
        m_narr = re.match(r'^【(旁白|Narrator)】\s*(.+)$', para, re.DOTALL)
        if m_narr:
            body = m_narr.group(2).strip()
            units.append({
                'type': 'narration',
                'speaker_zh': '旁白',
                'text_zh': clean_vocab(body),
            })
            continue

        # 对白：含 "..." 的段
        if '"' in para:
            dialogues = re.findall(r'"([^"]+)"', para)
            if dialogues:
                merged = ' '.join(clean_vocab(d) for d in dialogues)
                # 说话人识别：优先从开引号前的动作前缀找，否则查第一个引号闭合后
                first_q = para.find('"')
                prefix = para[:first_q] if first_q > 0 else ''
                first_q_end = para.find('"', first_q + 1)
                tail = para[first_q_end + 1:first_q_end + 30] if first_q_end > 0 else ''
                speaker = '未知'
                for name in characters:
                    if name in prefix:
                        speaker = name
                        break
                if speaker == '未知':
                    for name in characters:
                        if name in tail:
                            speaker = name
                            break
                units.append({
                    'type': 'dialogue',
                    'speaker_zh': speaker,
                    'text_zh': merged,
                })
            continue

    # 分配 idx
    for i, u in enumerate(units, start=1):
        u['idx'] = i
    return units
