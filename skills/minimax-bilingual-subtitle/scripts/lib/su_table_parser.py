# -*- coding: utf-8 -*-
"""SU 拆分表解析器：从 minimax-storyboard 的 doc/文本语义拆分表.md 提取 SU。

命名兼容：
  - 17 支线：SU-XX / SU-XXa / SU-XXb（嵌套引用式，拆分片段在 - **SU-XXa**：`...`）
  - 03 支线：SU-XX-N1 / SU-XX-D1（含 -N/-D 区分 narration/dialogue，平铺式）
  - 通用：SP-XX / SP-XXa / SP-XXb

内部统一为 SU-XX 处理。

两种表结构：
  1. 嵌套式（17）：父行 "拆分后片段" 列引用子片段 ID，子片段定义在表尾 - **SU-XXa**：`text`
  2. 平铺式（03）：父行 "拆分后片段" 列是 "SU-01-N1a + SU-01-N1b"，
     子片段作为独立行紧跟父行（备注列标 "拆分后片段"）
"""
import re
from pathlib import Path


def extract_spoken(text_en: str, utype: str) -> str:
    """从 SU 原文中提取纯台词，去掉说话人动作描述。

    - narration（旁白）：保留全文
    - dialogue（对白）：只保留 "..." 引号内的台词
    若对白没有引号包裹，fallback 为原文。
    """
    if utype == 'narration':
        return text_en.strip()
    quotes = re.findall(r'"([^"]+)"', text_en)
    if quotes:
        return ' '.join(q.strip() for q in quotes)
    return text_en.strip()


def parse_su_table(su_table_path: Path) -> list:
    """从文本语义拆分表提取 SU 列表（含拆分片段）。

    支持两种表结构：
      1. 嵌套式（17 支线）：SU-XX 父行 + 表尾 - **SU-XXa**：`text`
      2. 平铺式（03 支线）：SU-XX-N1 父行 + SU-XX-N1a/b 子行（独立行）

    返回：[{"su_id": "SU-01", "scene": "SC-01", "type": "narration",
            "speaker_en": "Narrator", "fragments": ["...", "..."]}, ...]
    """
    text = su_table_path.read_text(encoding='utf-8')

    # 判断表结构：17 用 - **SU-XXa**：`...`，03 用 markdown 表格
    is_nested = bool(re.search(r'^- \*\*(?:SU|SP)-\d+[a-z]\*\*[^：`]*：`', text, re.MULTILINE))

    if is_nested:
        return _parse_nested_table(text)
    return _parse_flat_table(text)


def _parse_nested_table(text: str) -> list:
    """17 支线格式：嵌套引用式。"""
    # 抓拆分片段（SU-XXy / SP-XXy → fragment）
    frag_map = {}  # "SU-01a" / "SP-01a" -> "fragment text"
    for m in re.finditer(r'- \*\*((?:SU|SP)-\d+[a-z])\*\*[^：`]*：`([^`]+)`', text):
        frag_map[m.group(1)] = m.group(2)

    # 抓主表 SU/SP 行
    su_list = []
    for m in re.finditer(
        r'\|\s*((?:SU|SP)-\d+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*([\d.]+)\s*\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|',
        text,
    ):
        sp_id, sc, utype_zh, speaker_zh, text_en, _wc, _dur, split_state = m.groups()
        # 统一改名为 SU-XX
        su_id = 'SU-' + sp_id.split('-', 1)[1]
        utype = _map_utype(utype_zh)
        speaker = _map_speaker(speaker_zh)
        # 抓拆分片段 ID
        sub_m = re.search(r'→\s*((?:(?:SU|SP)-\d+[a-z]\s*/\s*)+(?:SU|SP)-\d+[a-z])', split_state)
        fragments = []
        frag_ids = []
        if sub_m:
            for sub_id in re.findall(r'(?:SU|SP)-\d+[a-z]', sub_m.group(1)):
                frag_ids.append('SU-' + sub_id.split('-', 1)[1])
                if sub_id in frag_map:
                    fragments.append(extract_spoken(frag_map[sub_id], utype))
                else:
                    fragments.append('')
        else:
            fragments.append(extract_spoken(text_en.strip(), utype))
            frag_ids.append(su_id)
        su_list.append({
            'su_id': su_id,
            'scene': sc,
            'type': utype,
            'speaker_en': speaker,
            'fragments': fragments,
            'frag_ids': frag_ids,
        })
    return su_list


def _parse_flat_table(text: str) -> list:
    """平铺式 markdown 表格，父子都在主表里。

    支持三种列结构：
      - 03 支线（10 列）：
        | SU ID | 场景 | 类型 | 说话人 | 原始文本 | 词数 | 估算时长 | 是否拆分 | 拆分后片段 | 备注 |
      - 04 支线（8 列）：
        | SP-XX | 场景 | 类型 | 说话人 | 原始文本 | 预估时长 | 是否拆分 | 拆分建议 |
        其中"是否拆分"是 "否" 或 "**建议拆分**"，"拆分建议"是文字描述
        （拆分点 A：after "loud."），不是 frag_id 列表
      - 11 支线（7 列）：
        | S1-U01 | narration | Narrator | text | 31 | 12.5s | 否 |
        拆分片段定义在文件末尾 - S3-U04-A："..." 形式

    返回：[{su_id, scene, type, speaker_en, fragments, frag_ids}, ...]（仅父行）
    """
    # 先抓文件末尾的拆分片段定义（11 支线格式）：- S3-U04-A："text"（...）
    frag_map = {}
    for m in re.finditer(r'-\s+(S\d+-U\d+-[A-Z])："([^"]+)"', text):
        frag_map[m.group(1)] = m.group(2)

    rows = []
    for line in text.splitlines():
        line = line.strip()
        # 只认 SU/SP/SN-UNN 开头的表格行
        # 支线 11 用 S1-U01（场景-Unit），支线 17 用 SU-01，支线 03 用 SU-01-N1
        if not line.startswith('|'):
            continue
        if not re.match(r'^\|\s*(?:(?:SU|SP)-\d+|S\d+-U\d+)', line):
            continue
        # 跳过分隔行 |---|---|
        if re.match(r'^\|[\s\-|]+\|$', line):
            continue
        # 按 | 切分，去首尾空元素
        parts = [p.strip() for p in line.split('|')]
        # parts[0] 是空（行首 |），parts[-1] 是空（行末 |）
        parts = [p for p in parts if p]
        # 11 支线（7 列）比 03/04/09 少一列，最低 7
        if len(parts) < 7:
            continue
        # 区分 11 支线（S1-U01，无场景列）vs 其他支线（SU-XX/SP-XX，有场景列）
        if re.match(r'^S\d+-U\d+', parts[0]):
            # 11 支线：| S1-U01 | narration | Narrator | text | 31 | 12.5s | 否 |
            su_id_full, utype_zh, speaker_zh, text_en = parts[0], parts[1], parts[2], parts[3]
            sc = ''
        elif len(parts) == 7 and re.match(r'^(?:SU|SP)-\d+$', parts[0]) and not re.match(r'^(?:Scene|SC|S\d+)', parts[1], re.IGNORECASE):
            # 14 支线：| SU-01 | Narrator | text | 19 | 8.4s | SPL-01-a | 备注 |
            # 特点：SU ID 是纯数字（无 -N/-D 后缀），第 2 列是说话人（不是场景），7 列
            su_id_full = parts[0]
            sc = ''
            speaker_zh = parts[1]
            text_en = parts[2]
            # 推断类型：speaker 是 Narrator → narration，否则 dialogue
            utype_zh = '旁白' if speaker_zh.strip().lower() in ('narrator', '旁白') else '对白'
        else:
            # 03/04/09 支线：| SU-01 | Scene One | 旁白 | Narrator | text | ... |
            su_id_full, sc, utype_zh, speaker_zh, text_en = parts[0], parts[1], parts[2], parts[3], parts[4]
        # 03/09 (10列): split_state=parts[7], frag_refs=parts[8]
        # 04 (8列):  split_state=parts[6], frag_refs=parts[7]
        # 11 (7列):  split_state=parts[6], frag_refs=''
        # 14 (7列):  split_state=parts[5]（拆分标记），frag_refs=''（无引用）
        if re.match(r'^(?:SU|SP)-\d+$', parts[0]) and not re.match(r'^(?:Scene|SC|S\d+)', parts[1], re.IGNORECASE) and len(parts) == 7:
            # 14 支线：拆分标记在 parts[5]，备注在 parts[6]，无 frag_refs
            split_state = parts[5]
            frag_refs = ''
        elif len(parts) >= 10:
            split_state = parts[7]
            frag_refs = parts[8]
        elif len(parts) >= 9:
            # 09 支线：8 列数据（含场景）+ 1 列备注 = 9 列
            split_state = parts[6]
            frag_refs = parts[7]
        elif len(parts) >= 8:
            split_state = parts[6]
            frag_refs = parts[7]
        else:  # 11 支线 7 列
            split_state = parts[6] if len(parts) > 6 else ''
            frag_refs = ''

        rows.append({
            'su_id_full': su_id_full,
            'scene': sc,
            'type': _map_utype(utype_zh),
            'speaker': _map_speaker(speaker_zh),
            'text_en': text_en,
            'split_state': split_state,
            'frag_refs': frag_refs,
        })

    if not rows:
        return []

    # 区分父子：以字母结尾的是子（SU-01-N1a），否则是父（SU-01-N1）
    def is_child(r):
        return bool(re.search(r'[a-z]$', r['su_id_full']))

    by_id = {r['su_id_full']: r for r in rows}

    su_list = []
    for r in rows:
        if is_child(r):
            continue  # 子片段行由父行引用

        # 提取拆分片段 ID 列表
        frag_ids = re.findall(r'(?:SU|SP)-\d+(?:-[A-Z]\d+)?[a-z]', r['frag_refs'])
        # 也匹配 11 支线末尾定义的 S3-U04-A 形式（在备注/拆分后片段列里没有，需从全局 frag_map 找）
        if not frag_ids and r['su_id_full'] in [fid.rsplit('-', 1)[0] for fid in frag_map]:
            # 找 S{X}-U{NN}-A/B/C 顺序
            prefix = r['su_id_full']
            matched = sorted([fid for fid in frag_map if fid.startswith(prefix + '-')])
            frag_ids = matched
        fragments = []
        if frag_ids:
            # 平铺式：从 by_id 取子片段的 text_en
            for fid in frag_ids:
                # 11 支线：frag_map 里有
                if fid in frag_map:
                    fragments.append(extract_spoken(frag_map[fid], r['type']))
                    continue
                child = by_id.get(fid)
                if child:
                    fragments.append(extract_spoken(child['text_en'], r['type']))
                else:
                    fragments.append('')
        else:
            # 未拆分：整段作为单 fragment
            fragments.append(extract_spoken(r['text_en'], r['type']))
            frag_ids = [r['su_id_full']]

        su_list.append({
            'su_id': r['su_id_full'],
            'scene': r['scene'],
            'type': r['type'],
            'speaker_en': r['speaker'],
            'fragments': fragments,
            'frag_ids': frag_ids,
        })

    return su_list


def _map_utype(utype_zh: str) -> str:
    """类型列映射到 narration / dialogue。"""
    utype_zh_clean = utype_zh.strip()
    if utype_zh_clean in ('旁白', 'Narration', 'narration'):
        return 'narration'
    elif utype_zh_clean in ('对白', 'Dialogue', 'dialogue'):
        return 'dialogue'
    return 'narration'


def _map_speaker(speaker: str) -> str:
    """说话人列映射到英文 ID。"""
    speaker = speaker.strip()
    if speaker in ('旁白', '—', '-', ''):
        return 'Narrator'
    # 去掉"（推断）"等中文括号后缀（如 "Teacher Wang (推断)" → "Teacher Wang"）
    speaker = re.sub(r'[（(][^）)]*[)）]', '', speaker).strip()
    return speaker
