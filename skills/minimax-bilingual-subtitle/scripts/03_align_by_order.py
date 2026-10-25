# -*- coding: utf-8 -*-
"""步骤 3：shots 与 whisper 按 SEG 对位，再聚合成 fragments（最终字幕）。

两层数据结构：
  shots（shot 级，~120 行）
    - 与 whisper 段按"时间重叠最大"对位
    - 每 shot 得到 actual_start / actual_end

  fragments（SU 拆分片段级，~84 个）
    - 聚合其覆盖的 shots 的 actual 时间
    - 每 fragment 的 actual = [首 shot actual_start, 末 shot actual_end]
    - 输出为 subtitle_split.json

为什么"时间重叠最大"可行？
  - whisper 按 SEG 识别（8-14s 短视频），时间戳漂移 < 0.3s
  - SEG 内 shot 理论时间与 whisper 实际时间重叠度高
  - 不需要文本匹配，避免了 normalize/引号/前缀 bug 一整类问题

输入：
  --workspace  本 skill 工作区（含 seg_lines.json + fragments.json + whisper_by_seg.json + seg_durations.json）
  --gap        相邻 shot 间隔（默认 0.05s）
  --max-words  英文词数上限（默认 20）
  --max-chars  中文字数上限（默认 30）
  --max-dur    时长上限秒（默认 10.0）

输出：{workspace}/subtitle_split.json
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from common import read_json, write_json
from subtitle_splitter import force_split_subtitle, count_words, count_zh_chars


def align_seg_shots(shots: list, wsegs: list, seg_offset: float) -> list:
    """对单 SEG 内的 shots 与 whisper 段做时间对齐。

    原则：
      1. 把时间完全相同的 shot 分到一组（同帧多说话人）
      2. 每个 whisper 段按时间重叠分配给 shot 组
      3. 若 whisper 段数 == 组内 shot 数 → 一一对应轮流分配
         若 whisper 段数 < 组内 shot 数 → 切分最长的 whisper 段
         若 whisper 段数 > 组内 shot 数 → 相邻 shot 合并接收
      4. 对 1 个 whisper 段跨越多个不同时间的 shot 组的情况，
         按 shot 理论时间占比切分 whisper 段

    参数：
      shots: seg_lines 中属于该 SEG 的 shots（已按 seg_start 排序）
      wsegs: whisper 识别的该 SEG 语音段 [{rel_start, rel_end, text, ...}]
      seg_offset: 该 SEG 在整段视频里的起始偏移（秒）

    返回：[(actual_start, actual_end, align_source), ...] 与 shots 等长
    """
    if not wsegs:
        # 该 SEG 没识别出语音 → 全用理论时间
        return [(sh['abs_start'], sh['abs_end'], 'theory') for sh in shots]

    # whisper 段按 rel_start 排序
    wsegs = sorted(wsegs, key=lambda x: x['rel_start'])

    # 按 (seg_start, seg_end) 分组 shots，同时间的 shot 视为"同帧多说话人"
    from collections import defaultdict
    time_to_shots = defaultdict(list)
    for si, sh in enumerate(shots):
        key = (round(sh['seg_start'], 3), round(sh['seg_end'], 3))
        time_to_shots[key].append(si)

    # 把 whisper 段分配给 shot 组（基于时间重叠）
    # 注意：一个 whisper 段可能跨越多个组，按占比切分
    group_wsegs = defaultdict(list)  # 组 key → [{'rel_start', 'rel_end', ...}]

    for w in wsegs:
        w_start, w_end = w['rel_start'], w['rel_end']

        # 计算该 whisper 段对每个组的重叠
        overlaps = []  # [(key, overlap_dur), ...]
        for key in sorted(time_to_shots.keys()):
            g_start, g_end = key
            overlap = max(0.0, min(w_end, g_end) - max(w_start, g_start))
            if overlap > 0.1:
                overlaps.append((key, overlap))

        if not overlaps:
            continue

        if len(overlaps) == 1:
            # 只覆盖 1 个组，直接分配
            group_wsegs[overlaps[0][0]].append(w)
        else:
            # 跨越多个组：按占比切分
            total_overlap = sum(o for _, o in overlaps)
            cum = 0.0
            for key, ovl in overlaps:
                ratio = ovl / total_overlap
                sub_start = w_start + (w_end - w_start) * cum
                cum += ratio
                sub_end = w_start + (w_end - w_start) * cum
                group_wsegs[key].append({
                    'rel_start': sub_start,
                    'rel_end': sub_end,
                    'text': w.get('text', ''),
                    'synthetic': True,
                })

    # 给每组内的 shot 分配 whisper 段
    shot_assignments = {i: [] for i in range(len(shots))}

    for key, sis in time_to_shots.items():
        wlist = sorted(group_wsegs.get(key, []), key=lambda x: x['rel_start'])
        n_shots = len(sis)
        n_wsegs = len(wlist)

        if n_wsegs == 0:
            continue

        if n_wsegs == n_shots:
            # 一一对应
            for si, w in zip(sis, wlist):
                shot_assignments[si].append(w)
        elif n_wsegs > n_shots:
            # whisper 段多 → 相邻合并，多余的给最后一个
            for i, si in enumerate(sis):
                shot_assignments[si].append(wlist[i])
            for w in wlist[n_shots:]:
                shot_assignments[sis[-1]].append(w)
        else:
            # whisper 段少 → 按 shot 顺序均分时间
            total_start = min(w['rel_start'] for w in wlist)
            total_end = max(w['rel_end'] for w in wlist)
            total_dur = total_end - total_start
            avg_dur = total_dur / n_shots
            for i, si in enumerate(sis):
                w_start = total_start + i * avg_dur
                w_end = total_start + (i + 1) * avg_dur
                shot_assignments[si].append({
                    'rel_start': w_start,
                    'rel_end': w_end,
                    'text': '',
                    'synthetic': True,
                })

    # 合成每 shot 的实际时间
    out = []
    for si, sh in enumerate(shots):
        assigned = shot_assignments[si]
        if assigned:
            a_start = seg_offset + min(w['rel_start'] for w in assigned)
            a_end = seg_offset + max(w['rel_end'] for w in assigned)
            out.append((round(a_start, 3), round(a_end, 3), 'whisper'))
        else:
            out.append((sh['abs_start'], sh['abs_end'], 'theory'))
    return out


def main():
    parser = argparse.ArgumentParser(description='步骤 3：shots 与 whisper 对位，聚合成 fragments')
    parser.add_argument('--workspace', required=True, help='本 skill 工作区')
    parser.add_argument('--gap', type=float, default=0.05, help='相邻 shot 间隔（默认 0.05s）')
    parser.add_argument('--max-words', type=int, default=20, help='英文词数上限（默认 20）')
    parser.add_argument('--max-chars', type=int, default=30, help='中文字数上限（默认 30）')
    parser.add_argument('--max-dur', type=float, default=10.0, help='时长上限秒（默认 10.0）')
    args = parser.parse_args()

    workspace = Path(args.workspace)
    shots = read_json(workspace / 'seg_lines.json')
    fragments = read_json(workspace / 'fragments.json')
    whisper = read_json(workspace / 'whisper_by_seg.json')
    seg_durations = read_json(workspace / 'seg_durations.json')

    if not shots:
        raise SystemExit('[错误] seg_lines.json 为空')
    if not fragments:
        raise SystemExit('[错误] fragments.json 为空')

    # 计算每 SEG 的起始偏移
    seg_offsets = {}
    offset = 0.0
    for seg_id in sorted(seg_durations.keys()):
        seg_offsets[seg_id] = offset
        offset += seg_durations[seg_id]

    # 按 SEG 分组 shots
    by_seg = defaultdict(list)
    for sh in shots:
        by_seg[sh['seg_id']].append(sh)
    for seg_id in by_seg:
        by_seg[seg_id].sort(key=lambda x: x['seg_start'])

    # 对每 SEG 对齐
    shot_actuals = {}  # line_idx → (actual_start, actual_end, align_source)
    for seg_id in sorted(by_seg.keys()):
        seg_shots = by_seg[seg_id]
        wsegs = whisper.get(seg_id, [])
        seg_offset = seg_offsets.get(seg_id, 0.0)
        aligned = align_seg_shots(seg_shots, wsegs, seg_offset)
        for sh, (a_start, a_end, src) in zip(seg_shots, aligned):
            shot_actuals[sh['line_idx']] = (a_start, a_end, src)

    # 全局按 abs_start 排序所有 shots（保证跨 SEG 顺序正确）
    shots_sorted = sorted(shots, key=lambda x: x['abs_start'])

    # 校正 end ≤ 下一 shot start - gap
    for i in range(len(shots_sorted) - 1):
        cur = shots_sorted[i]
        nxt = shots_sorted[i + 1]
        cur_a = shot_actuals[cur['line_idx']]
        nxt_a = shot_actuals[nxt['line_idx']]
        if nxt_a[0] - args.gap < cur_a[1]:
            new_end = round(nxt_a[0] - args.gap, 3)
            new_end = max(new_end, round(cur_a[0] + 0.1, 3))
            shot_actuals[cur['line_idx']] = (cur_a[0], new_end, cur_a[2])

    # 聚合成 fragments
    final_subs = []
    n_whisper = 0
    n_theory = 0
    for frag in fragments:
        # 该 fragment 覆盖的 shots 的 actual 时间
        f_actuals = [shot_actuals[lidx] for lidx in frag['line_idxs']
                     if lidx in shot_actuals]
        if not f_actuals:
            print(f"[WARN] {frag['frag_id']} 未找到对应 shot 的 actual 时间，跳过")
            continue
        a_start = min(a[0] for a in f_actuals)
        a_end = max(a[1] for a in f_actuals)
        src = 'whisper' if any(a[2] == 'whisper' for a in f_actuals) else 'theory'
        if src == 'whisper':
            n_whisper += 1
        else:
            n_theory += 1

        sub = {
            'idx': 0,  # 待会重编
            'su_id': frag['frag_id'],
            'parent_su': frag['parent_su'],
            'scene': frag['scene'],
            'seg_id': frag['seg_id'],
            'type': frag['type'],
            'speaker_en': frag['speaker_en'],
            'speaker_zh': frag['speaker_zh'],
            'abs_start': frag['abs_start'],
            'abs_end': frag['abs_end'],
            'actual_start': a_start,
            'actual_end': a_end,
            'text_en': frag['text_en'],
            'text_zh': frag['text_zh'],
            'align_source': src,
            'word_count': count_words(frag['text_en']),
            'zh_chars': count_zh_chars(frag['text_zh']),
        }
        final_subs.extend(force_split_subtitle(
            sub, args.max_words, args.max_chars, args.max_dur))

    # 重编 idx
    for i, s in enumerate(final_subs, start=1):
        s['idx'] = i

    write_json(workspace / 'subtitle_split.json', final_subs)

    print(f'共 {len(final_subs)} 条字幕')
    print(f'  whisper 校正 {n_whisper} / 理论时间 {n_theory}')
    total_dur = sum(s['actual_end'] - s['actual_start'] for s in final_subs)
    print(f'  总时长 {total_dur:.1f}s')

    # 诊断超长
    long_subs = [s for s in final_subs
                 if s.get('word_count', 0) > args.max_words
                 or s.get('zh_chars', 0) > args.max_chars]
    if long_subs:
        print(f'\n[警告] 仍有 {len(long_subs)} 条超长：')
        for s in long_subs[:5]:
            print(f"  {s['su_id']} ({s.get('word_count')}词/{s.get('zh_chars')}字): {s['text_en'][:60]}")

    # 诊断无中文
    no_zh = [s for s in final_subs if not s.get('text_zh')]
    if no_zh:
        print(f'\n[警告] {len(no_zh)} 条无中文：')
        for s in no_zh[:5]:
            print(f"  {s['su_id']}: {s['text_en'][:60]}")


if __name__ == '__main__':
    main()
