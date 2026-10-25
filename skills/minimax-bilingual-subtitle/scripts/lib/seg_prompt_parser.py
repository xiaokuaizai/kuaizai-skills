# -*- coding: utf-8 -*-
"""SEG 提示词解析器：从 minimax-storyboard 的多种 SEG prompt 提取台词行。

支持三种格式（用 --format 切换）：

  shot（默认）：doc/minimax_h3_prompts/{SEG}_prompt.md（17 支线）
      - 00:00.0–00:07.2（SH-01）：...旁白（Luna）："text"
      说话人在文本前的（角色名）（音色）："..."形式

  seg：doc/最终提示词/{SEG}_final_prompt.md（11 支线）
      ## 时间轴视频描述
      00:00-00:06: [全景] ...描述...
        Audio: Narrator: "..."

  single：doc/H3最终提示词.md（03 支线，单文件含所有 SEG）
      ## SEG-01（10.8s｜...｜镜头 SH-001、SH-002）
      ### 时间轴视频描述
      00:00.0-00:07.8: 描述... 旁白 (V.O.): "..."
      时间码相对全片，每个 SEG 用 ## SEG-XX 分隔
"""
import re
from pathlib import Path

# 默认角色映射（旁白 + 4 主角）
DEFAULT_SPEAKER_MAP = {
    '旁白': ('Narrator', '旁白', 'narration'),
    '安琪': ('An Qi', '安琪', 'dialogue'),
    '江彻': ('Jiang Che', '江彻', 'dialogue'),
    '教练': ('Coach', '教练', 'dialogue'),
    # 03 支线扩展角色
    '英语老师': ('English teacher', '英语老师', 'dialogue'),
    '数学老师': ('Math teacher', '数学老师', 'dialogue'),
    '科学老师': ('Science teacher', '科学老师', 'dialogue'),
    '历史老师': ('History teacher', '历史老师', 'dialogue'),
    '老师': ('Teacher', '老师', 'dialogue'),
    '图书管理员': ('Librarian', '图书管理员', 'dialogue'),
    '同学': ('Classmate', '同学', 'dialogue'),
}

# 默认音色（来自项目 CLAUDE.md TTS 配置）
DEFAULT_VOICE_MAP = {
    'Narrator': 'Luna',
    'An Qi': 'Dacey',
    'Jiang Che': 'Lucas',
}


def parse_seg_prompt_shot(prompt_file: Path, speaker_map: dict) -> list:
    """shot 格式：解析单个 SEG prompt 的台词行（仅含语音段）。

    格式：- 00:00.0–00:07.2（SH-01）：...旁白（Luna）："text"
    返回：[{seg_id, shot_id, seg_start, seg_end, speaker_en, speaker_zh, voice,
            type, is_continuation, text_en}, ...]
    """
    text = prompt_file.read_text(encoding='utf-8')
    m = re.search(r'## 时间轴视频描述\n(.+?)\n## ', text, re.DOTALL)
    if not m:
        return []
    block = m.group(1)

    units = []
    for line in block.splitlines():
        line = line.strip()
        if not line.startswith('- '):
            continue
        # 匹配头部：- 00:00.0–00:07.2（SH-01）：
        head = re.match(r'^- (\d+):(\d+\.\d+)–(\d+):(\d+\.\d+)（(SH-\d+)）：', line)
        if not head:
            continue
        seg_start = int(head.group(1)) * 60 + float(head.group(2))
        seg_end = int(head.group(3)) * 60 + float(head.group(4))
        shot_id = head.group(5)
        rest = line[head.end():]  # 描述 + 说话人 + 文本

        # 在 rest 中查找角色名
        found = None
        for zh_name, (en_name, zh_display, utype) in speaker_map.items():
            pat = re.escape(zh_name) + r'（([^）]+)）(同句前(?:半)|同句后(?:半)|完整|前(?:半)|后(?:半))?[：:]\s*"'
            sm = re.search(pat, rest)
            if sm:
                voice = sm.group(1)
                cont_mark = sm.group(2) or ''
                is_cont = ('后' in cont_mark) and ('半' in cont_mark or cont_mark == '后半')
                text_start = sm.end()
                found = (en_name, zh_display, voice, utype, is_cont, text_start)
                break
        if not found:
            continue  # 无语音行（留白节拍）
        en_name, zh_display, voice, utype, is_cont, text_start = found

        # 提取文本：从 text_start 到行末最后一个 "
        tail = rest[text_start:]
        last_q = tail.rfind('"')
        if last_q <= 0:
            continue
        spoken = tail[:last_q].strip()

        units.append({
            'seg_id': prompt_file.stem.replace('_prompt', ''),
            'shot_id': shot_id,
            'seg_start': seg_start,
            'seg_end': seg_end,
            'speaker_en': en_name,
            'speaker_zh': zh_display,
            'voice': voice,
            'type': utype,
            'is_continuation': is_cont,
            'text_en': spoken,
        })
    return units


def parse_seg_prompt_seg(prompt_file: Path, speaker_map: dict) -> list:
    """seg 格式：解析最终提示词的台词行。

    支线 11 实际格式：
      ## 时间轴视频描述
      00:00-00:06: [全景] ...描述...
        Audio: Narrator: "..."
      00:06-00:08: [近景] ...纯镜头描述，无 Audio 行...
    """
    text = prompt_file.read_text(encoding='utf-8')
    m = re.search(r'## 时间轴视频描述\n(.+?)\n## ', text, re.DOTALL)
    if not m:
        return []
    block = m.group(1)

    # 说话人识别优先级：长名字优先（安琪母亲 > 安妈妈 > 妈妈 > 安琪 > 江彻）
    dialogue_speakers = sorted(
        [(zh_name, en_name, zh_display) for zh_name, (en_name, zh_display, _t) in speaker_map.items()
         if _t == 'dialogue'],
        key=lambda x: -len(x[0]),
    )

    units = []
    lines = block.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].rstrip()
        i += 1
        # 时间码行：00:00-00:06: 或 00:00.0-00:06.5:
        tm = re.match(r'^(\d+):(\d+(?:\.\d+)?)-(\d+):(\d+(?:\.\d+)?)\s*[:：]\s*(.+)$', line)
        if not tm:
            continue
        seg_start = int(tm.group(1)) * 60 + float(tm.group(2))
        seg_end = int(tm.group(3)) * 60 + float(tm.group(4))
        desc = tm.group(5)

        # 看下一行是否是 Audio: 行
        audio_m = None
        if i < len(lines):
            audio_line = lines[i].strip()
            audio_m = re.match(r'^Audio:\s*([^:]+?):\s*"(.+?)"\s*$', audio_line)
            if audio_m:
                i += 1  # 消费 Audio 行

        if not audio_m:
            continue  # 纯镜头描述行，无语音

        speaker_raw = audio_m.group(1).strip()
        spoken = audio_m.group(2).strip()

        # 判断旁白 / 对白
        if speaker_raw in ('旁白', 'Narrator', 'narrator', 'Narration'):
            en_name, zh_display, utype = 'Narrator', '旁白', 'narration'
        else:
            utype = 'dialogue'
            en_name, zh_display = 'Unknown', '未知'
            # 先尝试按中文名匹配
            for zh_name, en, zh_disp in dialogue_speakers:
                if zh_name in speaker_raw or zh_name in desc:
                    en_name, zh_display = en, zh_disp
                    break
            # 否则尝试按英文名匹配
            if en_name == 'Unknown':
                for zh_name, en, zh_disp in dialogue_speakers:
                    if en.lower() in speaker_raw.lower():
                        en_name, zh_display = en, zh_disp
                        break

        units.append({
            'seg_id': prompt_file.stem.replace('_final_prompt', ''),
            'shot_id': '',
            'seg_start': seg_start,
            'seg_end': seg_end,
            'speaker_en': en_name,
            'speaker_zh': zh_display,
            'voice': DEFAULT_VOICE_MAP.get(en_name, ''),
            'type': utype,
            'is_continuation': False,
            'text_en': spoken,
        })

    # 后处理：Unknown speaker 继承同 SEG 上一个 dialogue unit
    for i in range(1, len(units)):
        if units[i]['speaker_en'] == 'Unknown' and units[i-1]['type'] == 'dialogue':
            units[i]['speaker_en'] = units[i-1]['speaker_en']
            units[i]['speaker_zh'] = units[i-1]['speaker_zh']
            units[i]['voice'] = units[i-1]['voice']
    # 首行 Unknown 兜底：取 speaker_map 第一个 dialogue 角色
    for u in units:
        if u['speaker_en'] == 'Unknown':
            first_dial = next(((zh, en, zd) for zh, (en, zd, t) in speaker_map.items() if t == 'dialogue'), None)
            if first_dial:
                u['speaker_en'] = first_dial[1]
                u['speaker_zh'] = first_dial[2]
                u['voice'] = DEFAULT_VOICE_MAP.get(first_dial[1], '')
    return units


def parse_seg_prompt_shot_dash(prompt_file: Path, speaker_map: dict) -> list:
    """shot_dash 格式：解析 最终提示词/SEG-XX_final_prompt.md 的台词行。

    本项目（09_模拟联合国支线）实际格式：
      #### 6.3 时间轴视频描述
      ```
      0.0–3.5s: LS，24mm 广角... 台词："The morning campus was covered in foggy air."
      3.5–7.5s: MCU，35mm... 台词："Several pupils gathered in front of the bulletin board,"
      7.5–11.5s: CU，35mm... 台词："all looking at the Model United Nations recruitment poster."
      ```

    特点：
      - shot 边界用 " / " 或换行分隔（同一行内可有多 shot）
      - 每个 shot：X.X–Y.Ys: 描述 台词："..."（EN dash 连接时间）
      - 台词用 中文"台词：" 标记 + 英文双引号
      - 说话人需从 shot 描述中推断（An Qi screen-center / Jiang Che / Narrator 等）

    返回：[{seg_id, shot_id, seg_start, seg_end, speaker_en, speaker_zh, voice,
            type, is_continuation, text_en}, ...]
    """
    text = prompt_file.read_text(encoding='utf-8')
    # 匹配 #### 6.3 时间轴视频描述 段（H4 标题，不一定有 ``` 包裹）
    m = re.search(r'####\s*6\.3\s*时间轴视频描述\s*\n+```\s*\n(.+?)\n?```', text, re.DOTALL)
    if not m:
        return []
    block = m.group(1)

    # 按 shot 边界切分：shot 头 = X.X–Y.Ys:
    # 用 lookahead 把 " / " 后面的 shot 头当成新 shot 起点
    shot_head_pat = r'(\d+\.\d+)–(\d+\.\d+)s\s*:'
    parts = re.split(shot_head_pat, block)
    # parts = [前导, start1, end1, body1, start2, end2, body2, ...]

    # 英文角色名映射（出现在 shot 描述里）
    EN_SPEAKER_HINTS = [
        ('An Qi', 'An Qi', '安琪', 'dialogue', 'Dacey'),
        ('Jiang Che', 'Jiang Che', '江彻', 'dialogue', 'Lucas'),
        ('Narrator', 'Narrator', '旁白', 'narration', 'Luna'),
        ('Host', 'Host', '主持人', 'dialogue', ''),
        ('Opposing Delegate', 'Opposing Delegate', '对方代表', 'dialogue', ''),
    ]

    units = []
    seg_id = prompt_file.stem.replace('_final_prompt', '')

    i = 1
    shot_counter = 0
    while i + 2 <= len(parts):
        try:
            seg_start = float(parts[i])
            seg_end = float(parts[i + 1])
        except (ValueError, IndexError):
            i += 1
            continue

        body = parts[i + 2]
        # 去掉尾部的 " /"（shot 分隔符残留）
        body = body.rstrip()
        if body.endswith('/'):
            body = body[:-1].rstrip()

        # 提取台词："..."（可能跨段到 shot 末尾）
        dm = re.search(r'台词\s*[:：]\s*"([^"]+)"', body)
        if not dm:
            i += 3
            continue  # 该 shot 无语音
        spoken = dm.group(1).strip()

        # 去掉台词部分，剩下的作为描述用于说话人推断
        desc = body[:dm.start()].strip()

        # 推断说话人：优先匹配英文名（按长度降序，避免 Jiang 误匹配 Jiang Che）
        speaker_en, speaker_zh, utype, voice = 'Narrator', '旁白', 'narration', 'Luna'
        sorted_hints = sorted(EN_SPEAKER_HINTS, key=lambda x: -len(x[0]))
        for en_name, sp_en, sp_zh, ut, v in sorted_hints:
            if en_name in desc:
                speaker_en, speaker_zh, utype, voice = sp_en, sp_zh, ut, v
                break

        shot_counter += 1
        units.append({
            'seg_id': seg_id,
            'shot_id': f'SH-{shot_counter:02d}',
            'seg_start': seg_start,
            'seg_end': seg_end,
            'speaker_en': speaker_en,
            'speaker_zh': speaker_zh,
            'voice': voice,
            'type': utype,
            'is_continuation': False,
            'text_en': spoken,
        })
        i += 3

    return units


def parse_h3_single_file(prompt_file: Path, speaker_map: dict) -> dict:
    """解析单文件 H3 最终提示词（03 支线格式），返回 {seg_id: [units]}。

    格式特点：
      - 一个 .md 文件含所有 SEG，用 `## SEG-XX（10.8s｜...）` 分隔
      - 每 SEG 内 `### 时间轴视频描述` 段是 shot 列表
      - shot 行：`00:00.0-00:07.8: 描述... 旁白 (V.O.): "..."` 或 `... 安琪: "..."`
      - 时间码相对全片（不是 SEG 内），需减去 SEG 起始偏移

    说话人标记：
      - 旁白 (V.O.): "..."
      - 安琪: "..." / 江彻: "..." / 英语老师: "..." 等

    返回：{seg_id: [unit, ...]}，unit 结构与其他 parse_* 函数一致。
    """
    text = prompt_file.read_text(encoding='utf-8')

    # 按 ## SEG-XX 切分整个文件
    seg_blocks = re.split(r'^## (SEG-\d+)\b', text, flags=re.MULTILINE)
    # seg_blocks = [前导, seg_id_1, body_1, seg_id_2, body_2, ...]

    # 说话人识别：长名字优先（英语老师 > 安琪）
    dialogue_speakers = sorted(
        [(zh_name, en_name, zh_display) for zh_name, (en_name, zh_display, _t) in speaker_map.items()
         if _t == 'dialogue'],
        key=lambda x: -len(x[0]),
    )

    result = {}
    i = 1
    while i + 1 < len(seg_blocks):
        seg_id = seg_blocks[i].strip()
        body = seg_blocks[i + 1]
        i += 2

        # 找该 SEG 的时间轴视频描述段
        m = re.search(r'###\s*时间轴视频描述\s*\n(.+?)(?=\n###\s|\n##\s|\Z)', body, re.DOTALL)
        if not m:
            continue
        block = m.group(1)

        # 计算该 SEG 的起始偏移（用于把全片时间转成 SEG 内时间）
        # 取第一时间码作为偏移
        first_tm = re.search(r'^(\d+):(\d+(?:\.\d+)?)-', block, re.MULTILINE)
        if not first_tm:
            continue
        seg_offset_min = int(first_tm.group(1))
        seg_offset_sec = float(first_tm.group(2))
        seg_offset = seg_offset_min * 60 + seg_offset_sec

        units = []
        shot_counter = 0
        for line in block.splitlines():
            line = line.strip()
            if not line:
                continue
            # shot 行：00:00.0-00:07.8: 描述...
            tm = re.match(r'^(\d+):(\d+(?:\.\d+)?)-(\d+):(\d+(?:\.\d+)?)\s*[:：]\s*(.+)$', line)
            if not tm:
                continue
            abs_start = int(tm.group(1)) * 60 + float(tm.group(2))
            abs_end = int(tm.group(3)) * 60 + float(tm.group(4))
            rest = tm.group(5)

            # 转 SEG 内相对时间
            seg_start = round(abs_start - seg_offset, 3)
            seg_end = round(abs_end - seg_offset, 3)

            # 提取说话人 + 台词
            # 优先匹配 "名字 (V.O.): " 或 "名字: "
            speaker_m = re.search(
                r'([一-鿿A-Za-z ]+?)\s*(?:\(V\.O\.\))?\s*[:：]\s*"([^"]+)"',
                rest,
            )
            if not speaker_m:
                continue  # 该 shot 无语音（纯镜头描述）

            speaker_raw = speaker_m.group(1).strip()
            spoken = speaker_m.group(2).strip()

            # 判断旁白 / 对白
            if speaker_raw in ('旁白', 'Narrator', 'narrator', 'Narration') or '(V.O.)' in rest:
                en_name, zh_display, utype = 'Narrator', '旁白', 'narration'
            else:
                utype = 'dialogue'
                en_name, zh_display = 'Unknown', '未知'
                # 按中文名匹配
                for zh_name, en, zh_disp in dialogue_speakers:
                    if zh_name in speaker_raw:
                        en_name, zh_display = en, zh_disp
                        break
                # 兜底：按英文名匹配
                if en_name == 'Unknown':
                    for zh_name, en, zh_disp in dialogue_speakers:
                        if en.lower() in speaker_raw.lower():
                            en_name, zh_display = en, zh_disp
                            break
                # 再兜底：直接保留 speaker_raw（如 "English teacher"）
                if en_name == 'Unknown' and re.match(r'^[A-Za-z ]+$', speaker_raw):
                    en_name = speaker_raw
                    zh_display = speaker_raw

            shot_counter += 1
            units.append({
                'seg_id': seg_id,
                'shot_id': f'SH-{shot_counter:02d}',
                'seg_start': max(seg_start, 0.0),
                'seg_end': seg_end,
                'speaker_en': en_name,
                'speaker_zh': zh_display,
                'voice': DEFAULT_VOICE_MAP.get(en_name, ''),
                'type': utype,
                'is_continuation': False,
                'text_en': spoken,
            })

        # 后处理：Unknown speaker 继承同 SEG 上一个 dialogue unit
        for j in range(1, len(units)):
            if units[j]['speaker_en'] == 'Unknown' and units[j-1]['type'] == 'dialogue':
                units[j]['speaker_en'] = units[j-1]['speaker_en']
                units[j]['speaker_zh'] = units[j-1]['speaker_zh']
                units[j]['voice'] = units[j-1]['voice']

        if units:
            result[seg_id] = units

    return result
