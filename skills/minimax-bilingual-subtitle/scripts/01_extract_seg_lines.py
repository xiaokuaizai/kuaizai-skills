# -*- coding: utf-8 -*-
"""步骤 1：提取 shots（shot 级台词行）+ fragments（SU 拆分片段级字幕）。

合并了旧版 01+02+03 三步，但保留两层数据结构：

  shots（shot 级，120 行）
    - 来自 SEG prompt 时间轴
    - 每 shot 最多 1 行台词（含 SEG 内时间戳 + 英文 + 说话人）
    - 用于 whisper 按 SEG 对位（步骤 3）

  fragments（SU 拆分片段级，~84 个）
    - 来自 SU 拆分表
    - 每个 fragment 对应一条最终字幕
    - 含独立的中英文 + 覆盖的 shots 引用
    - 时间 = [首 shot actual_start, 末 shot actual_end]（步骤 3 计算）

SU 整段 ↔ shots 用 prefix-safe 顺序贪心匹配（SEG 内文本包含判断）。
SU 整段内拆分片段 ↔ shots 按词数占比分配（不需要文本匹配）。

输入：
  --storyboard-dir  故事板工作区（含 doc/minimax_h3_prompts/ 或 doc/最终提示词/）
  --workspace       本 skill 工作区
  --zh-script       中文版剧本 .md
  --su-table        SU 拆分表路径
  --seg-count       SEG 总数（默认 62）
  --seg-dir         SEG 视频目录（可选，用于 ffprobe 实测时长）
  --format          shot（默认）/ seg（最终提示词）
  --characters      中文角色名列表（逗号分隔）
  --speaker-map-json  自定义角色映射 JSON

输出：
  {workspace}/seg_lines.json     shots（shot 级）
  {workspace}/fragments.json     SU 拆分片段（含 shots 引用 + 中文）
  {workspace}/seg_durations.json 每 SEG 实测时长
"""
import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from common import read_json, write_json, ffprobe_duration, norm_text
from seg_prompt_parser import parse_seg_prompt_shot, parse_seg_prompt_seg, parse_seg_prompt_shot_dash, parse_h3_single_file, DEFAULT_SPEAKER_MAP
from su_table_parser import parse_su_table
from zh_script_parser import parse_zh_script
from subtitle_splitter import split_chinese, count_words


def match_sus_to_shots(su_list: list, shots: list) -> list:
    """按顺序贪心匹配 SU 整段 ↔ shots（文本相似度版）。

    v2：不再用 prefix-safe 严格顺序消费（在 SU 顺序 ≠ shot 顺序时错位），
        改用文本相似度。对每个 shot 找最佳 SU，允许多个 shot → 同 SU。

    算法：
      1. 预计算每个 SU 的 normalized 全文
      2. 对每个 shot（按时间顺序），计算其文本 vs 所有 SU 的相似度
      3. 找相似度最高的 SU（≥0.5），分配给该 SU
      4. 未被分配的 SU 返回空 shot_idxs

    返回：list of [shot_idx, ...]，与 su_list 等长。
    """
    from difflib import SequenceMatcher
    import re as _re

    def _norm(t):
        t = t.lower()
        t = _re.sub(r"[^a-z0-9\s]", ' ', t)
        return _re.sub(r'\s+', ' ', t).strip()

    def _sim(a, b):
        a_n, b_n = _norm(a), _norm(b)
        if not a_n or not b_n:
            return 0.0
        return SequenceMatcher(None, a_n, b_n).ratio()

    # 预计算 SU 全文 + 第一个拆分片段
    su_texts = [' '.join(su['fragments']) for su in su_list]
    su_texts_norm = [_norm(t) for t in su_texts]
    # 短 shot 精确匹配用: 某些 SU 第一个拆分片段极短(如 SU-33a 的 "Yes," 仅 1 词),
    # substring 因 SUBSTR_MIN_LEN 被跳过, SequenceMatcher 相似度也远低于阈值,
    # 需要靠"完全等于第一个 fragment"来精确对位
    su_first_frag_norm = [
        _norm(su['fragments'][0]) if su.get('fragments') else ''
        for su in su_list
    ]

    # 每个 shot 找最佳 SU
    matched = [[] for _ in su_list]
    THRESHOLD = 0.5
    SUBSTR_MIN_LEN = 15  # 子串匹配的最小长度（避免单字误配）
    for si, sh in enumerate(shots):
        shot_norm = _norm(sh['text_en'])
        best_su = -1
        best_score = 0.0
        for ui, su_norm in enumerate(su_texts_norm):
            # 先尝试子串匹配（shot 是 SU 的一部分）
            if len(shot_norm) >= SUBSTR_MIN_LEN and shot_norm in su_norm:
                score = 1.0
            elif 0 < len(shot_norm) < SUBSTR_MIN_LEN and shot_norm == su_first_frag_norm[ui]:
                # 短 shot 完全等于 SU 第一个拆分片段: 视为该 SU 的头部 shot
                score = 1.0
            else:
                score = _sim(sh['text_en'], su_texts[ui])
            if score > best_score:
                best_score = score
                best_su = ui
        if best_su >= 0 and best_score >= THRESHOLD:
            matched[best_su].append(si)

    return matched


def assign_shots_to_frags(su: dict, shot_idxs: list, shots: list) -> list:
    """在 SU 整段内，把 shots 按词数占比分配给拆分片段。

    每个拆分片段消费 shots 直到覆盖其词数。

    返回：list of [shot_idx, ...]，与 su['fragments'] 等长。
    """
    frag_wcs = [count_words(f) for f in su['fragments']]
    shot_wcs = [count_words(shots[i]['text_en']) for i in shot_idxs]

    result = []
    shot_pos = 0
    for frag_wc in frag_wcs:
        accumulated = 0
        frag_shots = []
        while shot_pos < len(shot_idxs) and accumulated < frag_wc:
            frag_shots.append(shot_idxs[shot_pos])
            accumulated += shot_wcs[shot_pos]
            shot_pos += 1
        result.append(frag_shots)
    # 兜底：最后一个拆分片段消费剩余 shots
    if shot_pos < len(shot_idxs):
        result[-1].extend(shot_idxs[shot_pos:])
    return result


def load_su_zh(workspace: Path, su_list: list) -> dict:
    """从 su_zh.json 加载每个 SU fragment 的中文翻译。

    su_zh.json 格式: {frag_id: "中文译文"} 或 {frag_id__N: "第 N 句中文"}
    frag_id 与 SU 表的 frag_ids 一一对应（如 SU-01-N1a、SU-01-D1）。
    若 frag_id 不存在，尝试 frag_id__1, frag_id__2, ... 拼接（按句拆分翻译）。

    返回：{su_id: (text_zh_joined, speaker_zh, frag_zh_list)}
    text_zh_joined：所有 fragments 用空格拼接的整段中文。
    frag_zh_list：逐 fragment 的中文（按 frag_ids 顺序），可能含空字符串。
    """
    # 主角英文名 → 中文名
    EN_TO_ZH = {
        'An Qi': '安琪',
        'Jiang Che': '江彻',
        'Narrator': '旁白',
    }

    su_zh_file = workspace / 'su_zh.json'
    if not su_zh_file.exists():
        raise SystemExit(
            f'[错误] 找不到 {su_zh_file}\n'
            f'请先用 translate_su_with_kimi.py 生成翻译:\n'
            f'  python translate_su_with_kimi.py --su-table <SU表> --workspace <工作区>'
        )

    frag_zh_map = json.loads(su_zh_file.read_text(encoding='utf-8'))
    print(f'[INFO] 从 {su_zh_file.name} 加载 {len(frag_zh_map)} 条翻译')

    def get_frag_zh(frag_id: str) -> str:
        """取单个 fragment 的中文，支持 __N 拆分形式。"""
        if frag_id in frag_zh_map:
            return frag_zh_map[frag_id]
        # 尝试 __N 形式
        parts = []
        for i in range(1, 20):
            key = f'{frag_id}__{i}'
            if key in frag_zh_map:
                parts.append(frag_zh_map[key])
            else:
                break
        return ' '.join(parts)

    result = {}
    n_missing = 0
    for su in su_list:
        frag_zhs = []
        for fid in su['frag_ids']:
            zh = get_frag_zh(fid)
            if not zh:
                n_missing += 1
                if n_missing <= 5:
                    print(f'  [WARN] {su["su_id"]} 的 fragment {fid} 无中文翻译')
            frag_zhs.append(zh)
        # 多 fragment 用空格拼接（保留完整语义）
        zh_joined = ' '.join(z for z in frag_zhs if z).strip()
        speaker_zh = EN_TO_ZH.get(su['speaker_en'], su['speaker_en'])
        result[su['su_id']] = (zh_joined, speaker_zh, frag_zhs)

    if n_missing:
        print(f'[WARN] 共 {n_missing} 个 fragment 缺中文翻译')

    return result


def main():
    parser = argparse.ArgumentParser(description='步骤 1：提取 shots + fragments')
    parser.add_argument('--storyboard-dir', required=True, help='故事板工作区根目录')
    parser.add_argument('--workspace', required=True, help='本 skill 工作区')
    parser.add_argument('--zh-script', default=None, help='中文版剧本 .md（已废弃，中文改用 su_zh.json）')
    parser.add_argument('--su-table', required=True, help='SU 拆分表路径')
    parser.add_argument('--seg-count', type=int, default=62, help='SEG 总数（默认 62）')
    parser.add_argument('--seg-dir', default=None, help='SEG 视频目录（可选）')
    parser.add_argument('--format', choices=['shot', 'seg', 'shot_dash', 'single'], default='shot',
                        help='SEG 提示词格式：shot=minimax_h3_prompts（默认）/ seg=最终提示词 / shot_dash=X.X–Y.Ys: 台词："..."（EN dash）/ single=H3最终提示词.md 单文件')
    parser.add_argument('--characters', default='安琪,江彻,教练',
                        help='中文角色名列表（逗号分隔）')
    parser.add_argument('--speaker-map-json', default=None,
                        help='自定义角色映射 JSON 路径')
    args = parser.parse_args()

    storyboard_dir = Path(args.storyboard_dir)
    workspace = Path(args.workspace)

    # 选 SEG prompt 目录 + 解析函数
    if args.format == 'single':
        # 03 支线格式：doc/H3最终提示词.md 单文件含所有 SEG
        prompt_file = storyboard_dir / 'doc' / 'H3最终提示词.md'
        if not prompt_file.exists():
            raise SystemExit(f'[错误] 单文件 H3 最终提示词不存在: {prompt_file}')
        parse_fn = None  # single 格式走特殊路径
        prompt_dir = None
    elif args.format == 'seg':
        prompt_dir = storyboard_dir / 'doc' / '最终提示词'
        parse_fn = parse_seg_prompt_seg
    elif args.format == 'shot_dash':
        # shot_dash：单一文件 doc/最终提示词.md 切分后的目录
        prompt_dir = storyboard_dir / 'doc' / '最终提示词'
        parse_fn = parse_seg_prompt_shot_dash
    else:
        prompt_dir = storyboard_dir / 'doc' / '最终提示词'
        if not prompt_dir.exists():
            prompt_dir = storyboard_dir / 'doc' / 'minimax_h3_prompts'
        parse_fn = parse_seg_prompt_shot

    speaker_map = read_json(args.speaker_map_json) if args.speaker_map_json else DEFAULT_SPEAKER_MAP

    # 收集 SEG 实测时长
    seg_durations = {}
    if args.seg_dir:
        seg_dir = Path(args.seg_dir)
        for i in range(1, args.seg_count + 1):
            seg_id = f'SEG-{i:02d}'
            mp4 = seg_dir / seg_id / f'{seg_id}.mp4'
            if mp4.exists():
                seg_durations[seg_id] = ffprobe_duration(str(mp4))
            else:
                seg_durations[seg_id] = None

    # 1. 解析所有 SEG prompt → shots（含 SEG 内时间戳）
    shots = []
    seg_offset = 0.0

    if args.format == 'single':
        # 单文件格式：一次解析所有 SEG，再按 SEG 累加偏移
        seg_to_units = parse_h3_single_file(prompt_file, speaker_map)
        for i in range(1, args.seg_count + 1):
            seg_id = f'SEG-{i:02d}'
            lines = seg_to_units.get(seg_id, [])
            # 决定本 SEG 时长
            if seg_durations.get(seg_id) is None:
                if lines:
                    seg_durations[seg_id] = max(l['seg_end'] for l in lines)
                else:
                    seg_durations[seg_id] = 0.0
            # 计算绝对理论时间
            for l in lines:
                l['abs_start'] = round(seg_offset + l['seg_start'], 3)
                l['abs_end'] = round(seg_offset + l['seg_end'], 3)
            shots.extend(lines)
            seg_offset += seg_durations[seg_id]
    else:
        for i in range(1, args.seg_count + 1):
            seg_id = f'SEG-{i:02d}'
            # 兼容多种后缀
            prompt_file = None
            for suffix in ['_final_prompt.md', '_最终提示词.md', '_prompt.md']:
                candidate = prompt_dir / f'{seg_id}{suffix}'
                if candidate.exists():
                    prompt_file = candidate
                    break
            if prompt_file is None:
                print(f'[WARN] {seg_id} prompt 不存在，跳过')
                continue

            lines = parse_fn(prompt_file, speaker_map)
            # 决定本 SEG 时长
            if seg_durations.get(seg_id) is None:
                if lines:
                    seg_durations[seg_id] = max(l['seg_end'] for l in lines)
                else:
                    seg_durations[seg_id] = 0.0

            # 计算绝对理论时间
            for l in lines:
                l['abs_start'] = round(seg_offset + l['seg_start'], 3)
                l['abs_end'] = round(seg_offset + l['seg_end'], 3)
            shots.extend(lines)
            seg_offset += seg_durations[seg_id]

    if not shots:
        raise SystemExit('[错误] 没有解析到任何 SEG 台词行，请检查 --storyboard-dir / --format')

    # 分配 line_idx（shot 级）
    for idx, sh in enumerate(shots, start=1):
        sh['line_idx'] = idx

    # 2. 解析 SU 拆分表
    su_list = parse_su_table(Path(args.su_table))
    if not su_list:
        raise SystemExit(f'[错误] SU 拆分表为空: {args.su_table}')

    # 3. 从 su_zh.json 加载中文翻译（Kimi API 生成）
    su_zh_map = load_su_zh(workspace, su_list)

    # 4. SU 整段 ↔ shots 匹配（文本相似度）
    #    不再合并 SU，直接用 SU 表整段
    matched = match_sus_to_shots(su_list, shots)

    # 诊断：每 SU 匹配状态
    n_incomplete = 0
    for su, shot_idxs in zip(su_list, matched):
        su_norm = norm_text(' '.join(su['fragments']))
        if shot_idxs:
            consumed = norm_text(' '.join(shots[i]['text_en'] for i in shot_idxs))
            if su_norm not in consumed:
                n_incomplete += 1
                if n_incomplete <= 3:
                    print(f'[WARN] {su["su_id"]} INCOMPLETE（未完整覆盖）')
    if n_incomplete:
        print(f'[WARN] 共 {n_incomplete}/{len(su_list)} 个 SU INCOMPLETE')

    # 诊断：未被任何 SU 覆盖的 shots
    matched_shot_idxs = {i for idxs in matched for i in idxs}
    unmatched_shots = [i for i in range(len(shots)) if i not in matched_shot_idxs]
    if unmatched_shots:
        print(f'[WARN] {len(unmatched_shots)} 个 shot 未被 SU 覆盖: '
              f'{[shots[i]["shot_id"] or shots[i]["seg_id"] for i in unmatched_shots[:5]]}')

    # 6. 生成 fragments（shot 级，每个 shot 一个 fragment）
    # 注：SU 表的拆分片段边界与 shot 边界不对应，且 SU 顺序 ≠ shot 顺序。
    #     最稳的做法：fragment = shot，中文按 SU 的 fragments 词数占比拆。
    fragments = []
    for ui, idxs in enumerate(matched):
        if not idxs:
            continue
        su = su_list[ui]
        zh_full, speaker_zh, frag_zh_list = su_zh_map.get(su['su_id'], ('', su['speaker_en'], []))

        # 按 SU fragments 词数占比拆中文
        frag_en_texts = su['fragments']  # e.g., ["This MUN...", "Even students..."]
        n_frags = len(frag_en_texts)
        n_shots = len(idxs)

        if n_frags == n_shots and n_frags == len(frag_zh_list) and all(frag_zh_list):
            # 1:1 且每个 fragment 都有中文：直接用逐条翻译，避免 split_chinese 错位
            frag_zhs = frag_zh_list
        elif n_frags == n_shots:
            frag_zhs = split_chinese(zh_full, [count_words(f) / max(sum(count_words(ff) for ff in frag_en_texts), 1) for f in frag_en_texts])
        else:
            # 不均分时按 shot 英文词数占比拆中文（更准确）
            shot_ens = [shots[i]['text_en'] for i in idxs]
            shot_wcs = [count_words(t) for t in shot_ens]
            total_wc = sum(shot_wcs)
            if total_wc > 0:
                ratios = [wc / total_wc for wc in shot_wcs]
            else:
                ratios = [1.0 / n_shots] * n_shots
            frag_zhs = split_chinese(zh_full, ratios)

        for shot_pos_in_su, si in enumerate(idxs):
            sh = shots[si]
            # 取对应位置的 fragment 文本
            if shot_pos_in_su < len(frag_zhs):
                zh_seg = frag_zhs[shot_pos_in_su]
            else:
                zh_seg = ''

            # 英文：如果有多个 fragments，用对应 fragment 的英文；否则用 shot 原文
            if n_frags == n_shots and shot_pos_in_su < len(frag_en_texts):
                en_seg = re.sub(r'\*\*', '', frag_en_texts[shot_pos_in_su]).strip()
            else:
                en_seg = sh['text_en']

            frag_id = f'{su["su_id"]}_s{shot_pos_in_su+1}' if n_shots > 1 else su['su_id']

            fragments.append({
                'frag_id': frag_id,
                'parent_su': su['su_id'],
                'scene': su['scene'],
                'type': su['type'],
                'speaker_en': su['speaker_en'],
                'speaker_zh': speaker_zh,
                'text_en': en_seg,
                'text_zh': zh_seg,
                'line_idxs': [sh['line_idx']],
                'seg_id': sh['seg_id'],
                'abs_start': sh['abs_start'],
                'abs_end': sh['abs_end'],
            })

    # 保存
    write_json(workspace / 'seg_durations.json', seg_durations)
    write_json(workspace / 'seg_lines.json', shots)
    write_json(workspace / 'fragments.json', fragments)

    print()
    print(f'共解析 {len(shots)} 个 shot → {len(fragments)} 个 SU 拆分片段')
    print(f'SU 整段 {len(su_list)} / 已分配中文 {len(su_zh_map)}')
    print(f'视频总时长（按 SEG 累加）：{seg_offset:.2f}s')
    narration = sum(1 for f in fragments if f['type'] == 'narration')
    dialogue = sum(1 for f in fragments if f['type'] == 'dialogue')
    print(f'旁白 {narration} / 对白 {dialogue}')


if __name__ == '__main__':
    main()
