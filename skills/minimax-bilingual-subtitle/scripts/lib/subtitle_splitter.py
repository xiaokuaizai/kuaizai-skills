# -*- coding: utf-8 -*-
"""字幕拆分器：把超长字幕按规则拆分（Netflix/YouTube 惯例）。

拆分规则：
  - 英文 > 20 词 或 中文 > 30 字 或 时长 > 10s → 必须拆
  - 优先级：英文句末标点 → 词数硬切 → 中文标点 → 中文硬切（避 ASCII 词）

时间分配：
  - 拆分片段的 [start, end] 在原子标题的 actual 时间范围内按比例切分
"""
import re


def count_words(text: str) -> int:
    return len([w for w in re.split(r'\s+', text.strip()) if w])


def count_zh_chars(text: str) -> int:
    """中文字符 + 中文标点计数（ASCII 字母/数字不计）。"""
    return len(re.findall(r'[一-鿿　-〿＀-￯]', text))


def split_en_sentences(text: str) -> list:
    """按英文句末标点（. ! ?）拆分，保留标点。"""
    parts = re.split(r'(?<=[.!?])\s+(?=[A-Z])', text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_chinese(zh: str, ratios: list) -> list:
    """按 ratios 切分中文，优先在标点处断。

    ratios: [0.38, 0.21, 0.41] 表示每段占比
    返回：[seg1, seg2, ...] 长度 = len(ratios)
    """
    n = len(zh)
    if len(ratios) == 1:
        return [zh]
    boundaries = []
    cum = 0.0
    for r in ratios[:-1]:
        cum += r
        target = int(n * cum)
        # 在 target ±10 内找最近的中文标点
        best = None
        for delta in range(0, 10):
            for cand in [target + delta, target - delta]:
                if 1 <= cand < n and zh[cand - 1] in '，。！？；：、':
                    best = cand
                    break
            if best is not None:
                break
        boundaries.append(best if best is not None else target)
    segs = []
    prev = 0
    for b in boundaries:
        segs.append(zh[prev:b].strip())
        prev = b
    segs.append(zh[prev:].strip())
    return segs


def find_safe_cut_zh(zh: str, mid: int) -> int:
    """在 zh 中找安全切分点：避开 ASCII 字母单词内部。

    中英混排（如 "路口的信箱mailbox上贴着..."）硬切时，mid 可能落在
    "mailbox" 单词中间。向前/后扫描找最近的不是 ASCII 字母的位置。
    """
    n = len(zh)
    for delta in range(0, n):
        for cand in [mid + delta, mid - delta]:
            if 1 <= cand < n:
                prev_c = zh[cand - 1]
                next_c = zh[cand]
                in_word = (prev_c.isascii() and prev_c.isalpha()
                           and next_c.isascii() and next_c.isalpha())
                if not in_word:
                    return cand
    return mid


def force_split_subtitle(sub: dict, max_words: int = 20, max_chars: int = 30,
                         max_dur: float = 10.0) -> list:
    """递归强制拆分单条字幕，直到每段都满足长度限制。

    返回：拆分后的 subtitle 列表（与原 sub 同结构，su_id 加 a/b/c 后缀）。
    """
    n_words = count_words(sub['text_en'])
    n_zh = count_zh_chars(sub['text_zh'])
    dur = sub['actual_end'] - sub['actual_start']

    if n_words <= max_words and n_zh <= max_chars and dur <= max_dur:
        return [sub]

    en_sents = split_en_sentences(sub['text_en'])

    if len(en_sents) >= 2:
        # 有句末标点：按比例拆中文
        sent_wcs = [count_words(s) for s in en_sents]
        total_wc = sum(sent_wcs)
        ratios = [wc / total_wc for wc in sent_wcs]
        zh_segs = split_chinese(sub['text_zh'], ratios)
    else:
        words = sub['text_en'].split()
        if len(words) > max_words:
            # 英文词数超：硬切词，中文按字符占比同步拆
            mid = len(words) // 2
            en_sents = [' '.join(words[:mid]), ' '.join(words[mid:])]
            ratios = [0.5, 0.5]
            zh_segs = split_chinese(sub['text_zh'], ratios)
        else:
            # 英文词数不超，只是中文超 / 时长超
            # 按中点最近的中文标点硬切 2 段（避免按所有标点拆导致段数过多）
            zh = sub['text_zh']
            mid = len(zh) // 2
            best = None
            for delta in range(0, 15):
                for cand in [mid + delta, mid - delta]:
                    if 1 <= cand < len(zh) and zh[cand - 1] in '，。！？；：、':
                        best = cand
                        break
                if best:
                    break
            if best is None:
                best = find_safe_cut_zh(zh, mid)
            zh_segs_raw = [zh[:best].strip(), zh[best:].strip()]
            n = 2
            # 英文按字符占比同步拆（避免第一段独吞全部英文）
            zh_lens = [len(z) for z in zh_segs_raw]
            zh_total = sum(zh_lens)
            en_segs = []
            word_start = 0
            for i, _zlen in enumerate(zh_lens):
                if i == n - 1:
                    en_segs.append(' '.join(words[word_start:]))
                else:
                    word_end = int(len(words) * sum(zh_lens[:i+1]) / zh_total)
                    word_end = max(word_end, word_start)
                    en_segs.append(' '.join(words[word_start:word_end]))
                    word_start = word_end
            en_sents = en_segs
            zh_segs = zh_segs_raw
            ratios = [count_zh_chars(z) / max(sum(count_zh_chars(zz) for zz in zh_segs), 1)
                      for z in zh_segs]

    # 分配时间
    su_start = sub['actual_start']
    su_end = sub['actual_end']
    su_dur = su_end - su_start

    out = []
    cum = 0.0
    real_idx = 0
    for i, (en, zh) in enumerate(zip(en_sents, zh_segs)):
        if not en and not zh:
            continue
        seg_dur = su_dur * ratios[i]
        seg_start = su_start + cum
        seg_end = seg_start + seg_dur
        cum += seg_dur
        suffix = chr(97 + real_idx)
        new_sub = {
            **sub,
            'idx': 0,
            'su_id': f"{sub['su_id']}{suffix}",
            'parent_su': sub.get('parent_su', sub['su_id']),
            'actual_start': round(seg_start, 3),
            'actual_end': round(seg_end, 3),
            'abs_start': round(seg_start, 3),
            'abs_end': round(seg_end, 3),
            'text_en': en,
            'text_zh': zh,
            'word_count': count_words(en),
            'zh_chars': count_zh_chars(zh),
        }
        real_idx += 1
        # 递归：仍超长则继续拆
        out.extend(force_split_subtitle(new_sub, max_words, max_chars, max_dur))
    return out
