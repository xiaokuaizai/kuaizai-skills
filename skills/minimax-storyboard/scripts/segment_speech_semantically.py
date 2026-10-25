#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
segment_speech_semantically.py
对剧本中的对白、旁白、画外音、内心独白按语义规则拆分，并估算时长。

输入：
  - 剧本原文 .md 或 .txt（需配合 --speech-pattern 参数提取台词）
  - 或已结构化的 speech_units.json

输出：
  - speech_segments.json：结构化拆分结果
  - doc/文本语义拆分表.md：供人工抽查的 Markdown 表格

核心规则：
  1. 拆分后的所有片段拼接后必须等于原文。
  2. 优先在句子结尾拆分，其次在完整从句/意群结尾。
  3. 禁止在名词短语、动词短语、完整从句、引号内一句话中间切断。
  4. 先保证语义完整，再校验 SEG 8-13 秒目标区间。
"""

import argparse
import json
import re
from pathlib import Path
from typing import Optional


# 语速配置（与 references/旁白处理与时长预留规范.md 保持一致）
SPEECH_RATES = {
    "zh_normal": 4.0,        # 中文字/秒
    "zh_slow": 3.0,
    "zh_fast": 5.0,
    "en_normal": 0.40,       # 英文秒/词（对应 150 wpm）
    "en_slow": 0.45,
    "en_fast": 0.33,
}

# 句子结尾标点
SENTENCE_END_PUNCT = r"[。！？.!?]"
# 从句/意群结尾标点
CLAUSE_END_PUNCT = r"[，；,;]"

# 默认 SEG 目标区间（秒）
TARGET_MIN = 8.0
TARGET_MAX = 13.0
HARD_CAP = 15.0


def count_chinese_chars(text: str) -> int:
    """统计中文字符数。"""
    return len(re.findall(r"[一-鿿]", text))


def count_english_words(text: str) -> int:
    """统计英文单词数。"""
    return len(re.findall(r"[A-Za-z]+", text))


def estimate_duration(text: str, speech_type: str = "normal", emotion: str = "normal") -> float:
    """估算文本发声时长（秒）。"""
    text = text.strip()
    if not text:
        return 0.0

    zh_chars = count_chinese_chars(text)
    en_words = count_english_words(text)

    # 选择语速
    if emotion in ("slow", "情绪", "缓慢") or speech_type in ("inner_monologue", "narration"):
        zh_rate = SPEECH_RATES["zh_slow"]
        en_rate = SPEECH_RATES["en_slow"]
    elif emotion in ("fast", "快速", "急促"):
        zh_rate = SPEECH_RATES["zh_fast"]
        en_rate = SPEECH_RATES["en_fast"]
    else:
        zh_rate = SPEECH_RATES["zh_normal"]
        en_rate = SPEECH_RATES["en_normal"]

    duration = 0.0
    if zh_chars:
        duration += zh_chars / zh_rate
    if en_words:
        duration += en_words * en_rate

    # 停顿余量
    pauses = len(re.findall(r"[，,。.;；!?！？]", text))
    duration += min(pauses * 0.2, 1.0)

    # 兜底：如果没有任何文字，按最小 0.5 秒算
    return max(0.5, duration)


def find_sentence_breaks(text: str) -> list[int]:
    """返回所有句子结尾后的切分位置索引。"""
    breaks = []
    for m in re.finditer(SENTENCE_END_PUNCT, text):
        pos = m.end()
        # 跳过紧跟的引号、空格
        while pos < len(text) and text[pos] in " \\n\"\"''」』":
            pos += 1
        if pos < len(text):
            breaks.append(pos)
    return breaks


def find_clause_breaks(text: str) -> list[int]:
    """返回所有完整从句/意群结尾的切分位置索引。"""
    breaks = []
    for m in re.finditer(CLAUSE_END_PUNCT, text):
        pos = m.end()
        # 跳过后续空格或引号闭合
        while pos < len(text) and text[pos] in " \\n\"\"''」』":
            pos += 1
        if pos < len(text):
            breaks.append(pos)
    return breaks


def is_semantically_safe_split(left: str, right: str) -> bool:
    """
    启发式判断切分点是否在安全位置。
    简单实现：左侧不能是以「因为/虽然/如果/当」等连词结尾，右侧不能是单独依赖左侧的从句。
    """
    left_stripped = left.rstrip(" ，,；;。！？.!?\\n\"\"''「『")
    right_stripped = right.lstrip(" ，,；;。！？.!?\\n\"\"''」』")

    # 左侧以从属连词结尾，不安全
    dependent_prefixes = (
        "因为", "虽然", "尽管", "如果", "假如", "要是", "当", "在", "随着",
        "即使", "无论", "不管", "由于", "为了", "除了", "正如", "就像",
        "because", "although", "though", "if", "when", "while", "since", "as",
    )
    if any(left_stripped.endswith(p) for p in dependent_prefixes):
        return False

    # 右侧以从属连词开头，可能无法独立成段
    if any(right_stripped.startswith(p) for p in dependent_prefixes):
        return False

    # 右侧过短（少于 3 个字符/词），可能不是完整意群
    if count_chinese_chars(right_stripped) < 3 and count_english_words(right_stripped) < 2:
        return False

    return True


def split_text_semantically(
    text: str,
    target_max: float = TARGET_MAX,
    original_text: Optional[str] = None,
    offset: int = 0,
) -> list[dict]:
    """对单段文本按语义规则拆分。

    返回每个 portion 包含原始完整文本中的 start/end 索引，
    以便 build_speech_segments 精确重建原文（包括英文句间空格）。

    Args:
        text: 当前待拆分的子串。
        target_max: SEG 目标最大时长。
        original_text: 最外层原始完整文本；递归调用时透传。
        offset: text 在 original_text 中的起始索引。
    """
    if original_text is None:
        original_text = text

    stripped = text.strip()
    if not stripped:
        return []

    duration = estimate_duration(stripped)
    if duration <= target_max:
        return [{
            "text": stripped,
            "start": offset + (text.find(stripped) if stripped else 0),
            "end": offset + len(text),
            "duration": round(duration, 2),
            "breakpoint_reason": "无需拆分",
        }]

    # 第一优先级：句子结尾（把后续空白包含进当前 portion，避免重建丢空格）
    breaks = find_sentence_breaks(stripped)
    if breaks:
        portions = []
        start = 0
        base_offset = offset + (text.find(stripped) if text.find(stripped) >= 0 else 0)
        for pos in breaks:
            end_pos = pos
            while end_pos < len(stripped) and stripped[end_pos].isspace():
                end_pos += 1
            portion_text = stripped[start:end_pos].rstrip()
            if portion_text:
                # text 显示时去掉尾部空格，但 end 索引包含后续空白，确保重建精确
                portions.append({
                    "text": portion_text,
                    "start": base_offset + start,
                    "end": base_offset + end_pos,
                    "duration": round(estimate_duration(portion_text), 2),
                    "breakpoint_reason": "句子结尾",
                })
            start = end_pos
        # 最后一段
        last_text = stripped[start:].strip()
        if last_text:
            portions.append({
                "text": last_text,
                "start": base_offset + start,
                "end": offset + len(text),
                "duration": round(estimate_duration(last_text), 2),
                "breakpoint_reason": "句子结尾",
            })

        # 递归检查：如果某段仍然过长，继续拆分（透传 original_text 和正确 offset）
        result = []
        for p in portions:
            if p["duration"] > target_max:
                result.extend(split_text_semantically(
                    p["text"],
                    target_max,
                    original_text=original_text,
                    offset=p["start"],
                ))
            else:
                result.append(p)
        return result

    # 第二优先级：完整从句/意群结尾
    clause_breaks = [
        b for b in find_clause_breaks(stripped)
        if is_semantically_safe_split(stripped[:b], stripped[b:])
    ]
    if clause_breaks:
        best_pos = None
        best_diff = float("inf")
        for pos in clause_breaks:
            left_dur = estimate_duration(stripped[:pos])
            right_dur = estimate_duration(stripped[pos:])
            diff = abs(left_dur - target_max)
            if left_dur <= HARD_CAP and diff < best_diff:
                best_diff = diff
                best_pos = pos

        if best_pos is not None:
            left_text = stripped[:best_pos].strip()
            right_text = stripped[best_pos:].strip()
            base_offset = offset + (text.find(stripped) if text.find(stripped) >= 0 else 0)
            left_p = {
                "text": left_text,
                "start": base_offset + stripped.find(left_text),
                "end": base_offset + stripped.find(left_text) + len(left_text),
                "duration": round(estimate_duration(left_text), 2),
                "breakpoint_reason": "完整从句/意群结尾",
            }
            right_splits = split_text_semantically(
                right_text,
                target_max,
                original_text=original_text,
                offset=base_offset + stripped.find(right_text),
            )
            if left_p["duration"] > target_max:
                left_splits = split_text_semantically(
                    left_text,
                    target_max,
                    original_text=original_text,
                    offset=left_p["start"],
                )
                return left_splits + right_splits
            return [left_p] + right_splits

    # 兜底：无法找到安全语义断点，按字数大致均分并标记为 forced
    chars = count_chinese_chars(stripped)
    words = count_english_words(stripped)
    total_units = max(chars, words)
    if total_units == 0:
        return [{
            "text": stripped,
            "start": offset + (text.find(stripped) if stripped else 0),
            "end": offset + len(text),
            "duration": round(duration, 2),
            "breakpoint_reason": "无法自动拆分（请人工复核）",
        }]

    words_per_sec = total_units / duration
    units_per_portion = max(3, int(target_max * words_per_sec))

    portions = []
    start = 0
    base_offset = offset + (text.find(stripped) if text.find(stripped) >= 0 else 0)
    while start < len(stripped):
        end = min(start + units_per_portion, len(stripped))
        safe_end = end
        while safe_end > start + 3:
            if stripped[safe_end - 1] in " ，,；;。！？.!?":
                if is_semantically_safe_split(stripped[start:safe_end], stripped[safe_end:]):
                    break
            safe_end -= 1
        if safe_end == start + 3:
            safe_end = end
        portion_text = stripped[start:safe_end].strip()
        if portion_text:
            local_start = stripped.find(portion_text, start)
            portions.append({
                "text": portion_text,
                "start": base_offset + local_start,
                "end": base_offset + local_start + len(portion_text),
                "duration": round(estimate_duration(portion_text), 2),
                "breakpoint_reason": "字数均衡拆分（强制，需人工复核）",
            })
        start = safe_end

    return portions


def split_speech_unit(unit: dict, target_max: float = TARGET_MAX) -> list[dict]:
    """对单个 speech unit 做语义拆分。"""
    text = unit.get("text", "").strip()
    if not text:
        return []

    portions = split_text_semantically(text, target_max)

    # 判断说话人是否缺失或需要推断（仅 dialogue 类型需要补全说话人）
    speaker = unit.get("speaker")
    speaker_inferred = unit.get("speaker_inferred", False)
    speaker_inference_note = unit.get("speaker_inference_note", "")
    if unit.get("type") == "dialogue" and not speaker:
        speaker_inference_note = speaker_inference_note or "说话人缺失，需根据上下文推断或人工确认"
    else:
        speaker_inference_note = ""

    # 为每个 portion 分配 ID 和元数据
    result = []
    for idx, p in enumerate(portions, start=1):
        result.append({
            "portion_id": f"{unit.get('unit_id', 'SP-UNKNOWN')}-{chr(64 + idx)}",
            "parent_unit_id": unit.get("unit_id"),
            "type": unit.get("type", "dialogue"),
            "speaker": speaker,
            "speaker_inferred": speaker_inferred,
            "speaker_inference_note": speaker_inference_note,
            "original_text": text,
            "text": p["text"],
            "start": p.get("start", 0),
            "end": p.get("end", len(text)),
            "duration": p["duration"],
            "breakpoint_reason": p["breakpoint_reason"],
            "needs_review": (
                "强制" in p["breakpoint_reason"]
                or "无法自动" in p["breakpoint_reason"]
                or (unit.get("type") == "dialogue" and not speaker)
            ),
        })
    return result


def build_speech_segments(speech_units: list[dict], target_max: float = TARGET_MAX) -> dict:
    """批量处理所有 speech unit。"""
    all_portions = []
    for unit in speech_units:
        portions = split_speech_unit(unit, target_max)
        all_portions.extend(portions)

    # 全局完整性校验：使用原始文本的 start/end 索引精确重建
    original_texts = {}
    reconstructed = {}
    for p in all_portions:
        uid = p["parent_unit_id"]
        if uid not in original_texts:
            original_texts[uid] = p["original_text"]
            reconstructed[uid] = ""
        # 通过原始文本的 start/end 切片，确保空格不丢失
        start = p.get("start", 0)
        end = p.get("end", len(p["original_text"]))
        reconstructed[uid] += p["original_text"][start:end]

    integrity_issues = []
    for uid, original in original_texts.items():
        if reconstructed[uid] != original:
            integrity_issues.append({
                "unit_id": uid,
                "original": original,
                "reconstructed": reconstructed[uid],
            })

    return {
        "target_min": TARGET_MIN,
        "target_max": target_max,
        "hard_cap": HARD_CAP,
        "speech_units": speech_units,
        "portions": all_portions,
        "integrity_issues": integrity_issues,
        "needs_manual_review": any(p.get("needs_review") for p in all_portions) or bool(integrity_issues),
    }


def generate_markdown_table(result: dict) -> str:
    """生成 doc/文本语义拆分表.md 内容。"""
    lines = [
        "# 文本语义拆分表",
        "",
        f"> SEG 目标时长区间：{result['target_min']}s - {result['target_max']}s",
        f"> 硬上限：{result['hard_cap']}s",
        "",
        "## 拆分结果",
        "",
        "| 原 unit | 类型 | 说话人 | 拆分片段 | 时长(s) | 拆分理由 | 需人工复核 | 备注 |",
        "|---|---|---|---|---:|---|---|---|---|",
    ]

    for p in result["portions"]:
        review_flag = "是" if p.get("needs_review") else "否"
        speaker = p.get("speaker") or "-"
        if p.get("speaker_inferred"):
            speaker += " (推断)"
        note = p.get("speaker_inference_note", "")
        lines.append(
            f"| {p['parent_unit_id']} | {p['type']} | {speaker} | {p['text']} | {p['duration']} | {p['breakpoint_reason']} | {review_flag} | {note} |"
        )

    if result["integrity_issues"]:
        lines.extend([
            "",
            "## 完整性校验失败",
            "",
            "以下 unit 拆分后无法还原原文，必须修复：",
            "",
        ])
        for issue in result["integrity_issues"]:
            lines.append(f"- **{issue['unit_id']}**")
            lines.append(f"  - 原文：{issue['original']}")
            lines.append(f"  - 还原：{issue['reconstructed']}")

    # 收集需要补全说话人的 unit
    missing_speakers = set()
    for p in result["portions"]:
        if p.get("type") == "dialogue" and not p.get("speaker"):
            missing_speakers.add(p["parent_unit_id"])
    if missing_speakers:
        lines.extend([
            "",
            "## 说话人待补全",
            "",
            "以下 dialogue unit 未标注说话人，请根据上下文推断并补全：",
            "",
        ])
        for uid in sorted(missing_speakers):
            lines.append(f"- **{uid}**")

    lines.extend([
        "",
        "## 人工抽查确认",
        "",
        "- [ ] 所有拆分点均落在自然语义边界，无句中切断。",
        "- [ ] 拆分后所有片段拼接等于原文，无增删改。",
        "- [ ] 每个片段时长在 SEG 目标区间 8-13s 内，或已标注例外理由。",
        "- [ ] 标记「需人工复核」的片段已确认可接受。",
        "- [ ] 所有 dialogue 的说话人已补全或确认无法推断。",
        "",
        "确认人：__________  日期：__________",
    ])

    return "\n".join(lines) + "\n"


def load_speech_units(path: str) -> list[dict]:
    """加载 speech units。"""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"找不到输入文件: {path}")

    text = p.read_text(encoding="utf-8")

    # 如果是 JSON，直接解析
    if p.suffix.lower() == ".json":
        data = json.loads(text)
        if isinstance(data, dict):
            return data.get("speech_units", [])
        return data

    # 否则按简单格式解析：每行 "[类型:说话人] 文本"
    units = []
    pattern = re.compile(r"^\[(?P<type>[^:\]]+)(?::(?P<speaker>[^\]]+))?\]\s*(?P<text>.+)$")
    for idx, line in enumerate(text.splitlines(), start=1):
        line = line.strip()
        if not line:
            continue
        m = pattern.match(line)
        if m:
            speaker = (m.group("speaker") or "").strip() or None
            units.append({
                "unit_id": f"SP-{idx:03d}",
                "type": m.group("type").strip(),
                "speaker": speaker,
                "speaker_inferred": False,
                "speaker_inference_note": "" if speaker else "说话人缺失，需根据上下文推断或人工确认",
                "text": m.group("text").strip(),
            })
        else:
            # 无标签行默认当作 narration
            units.append({
                "unit_id": f"SP-{idx:03d}",
                "type": "narration",
                "speaker": None,
                "speaker_inferred": False,
                "speaker_inference_note": "",
                "text": line,
            })
    return units


def main():
    parser = argparse.ArgumentParser(description="按语义规则拆分剧本发声文本")
    parser.add_argument("--input", required=True, help="输入文件：speech_units.json 或剧本文本")
    parser.add_argument("--target-max", type=float, default=TARGET_MAX, help=f"SEG 目标最大时长（默认 {TARGET_MAX}s）")
    parser.add_argument("--output-json", default="00_元数据/清单/speech_segments.json", help="JSON 输出路径")
    parser.add_argument("--output-md", default="doc/文本语义拆分表.md", help="Markdown 输出路径")
    parser.add_argument("--dump-units", action="store_true", help="仅输出 speech_units.json 模板后退出")

    args = parser.parse_args()

    if args.dump_units:
        template = [
            {
                "unit_id": "SP-001",
                "type": "dialogue",
                "speaker": "安琪",
                "text": "示例对白文本，用于估算时长和语义拆分。",
            }
        ]
        Path(args.output_json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.output_json, "w", encoding="utf-8") as f:
            json.dump(template, f, ensure_ascii=False, indent=2)
        print(f"speech_units 模板已保存: {args.output_json}")
        return

    units = load_speech_units(args.input)
    result = build_speech_segments(units, args.target_max)

    # 保存 JSON
    json_path = Path(args.output_json)
    json_path.parent.mkdir(parents=True, exist_ok=True)
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f"拆分结果已保存: {json_path}")

    # 保存 Markdown
    md_path = Path(args.output_md)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.write_text(generate_markdown_table(result), encoding="utf-8")
    print(f"语义拆分表已保存: {md_path}")

    if result["needs_manual_review"]:
        print("\n注意：存在需要人工复核的拆分点，请在 doc/文本语义拆分表.md 中确认。")


if __name__ == "__main__":
    main()
