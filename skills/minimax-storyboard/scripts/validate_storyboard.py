#!/usr/bin/env python3
"""Minimax H3 分镜 Markdown 轻量校验脚本。

检查项：
- SEG 总时长是否超过 15s 硬上限（建议 ≤13s）。
- Shot List 中每个镜头是否填写 Required Content / Min Duration。
- 镜头分配时长是否 ≥ 最低内容时长。
- 首帧/尾帧锚点是否缺失。
- 文档是否声明 Minimax H3 与 15s 上限。
"""

from __future__ import annotations

import io
import argparse
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

# Windows 控制台默认编码可能不是 UTF-8，强制输出 UTF-8 避免中文乱码
if hasattr(sys.stdout, "buffer"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", line_buffering=True)
if hasattr(sys.stderr, "buffer"):
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", line_buffering=True)


# 匹配 SEG/SH 编号
SEGMENT_RE = re.compile(r"\bSEG[-_ ]?(\d+)\b", re.IGNORECASE)
SHOT_RE = re.compile(r"\bSH[-_ ]?(\d+)\b", re.IGNORECASE)
# 匹配时长，例如 3s、3.5秒、3.0 s
DURATION_RE = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)\s*(?:s|秒)\b", re.IGNORECASE)

# 内容类型关键词与对应最低时长（秒）
CONTENT_RULES = [
    ("场景识别", ["场景", "空间", "识别", "谁在画面", "人物在画面", "画面里", "环境", "地点"], 1.5),
    ("动作完成", ["推门", "转身", "坐下", "站起", "拿起", "放下", "走", "跑", "跳", "进入", "离开",
                 "抬头", "低头", "回头", "握手", "拥抱", "摔", "打", "开门", "关门", "移动", "走近", "退后"], 2.0),
    ("情绪读取", ["表情", "惊讶", "皱眉", "笑", "哭", "眼神", "冷", "怒", "害怕", "紧张", "激动",
                 "兴奋", "悲伤", "痛苦", "眼神变化", "表情变化"], 1.0),
    ("道具揭示", ["道具", "手机", "屏幕", "戒指", "钱", "药", "消息", "照片", "信", "文件", "杯子",
                 "钥匙", "血迹", "文书", "包", "项链", "手表"], 1.0),
    ("反应留白", ["反应", "留白", "缓冲", "余量", "停顿", "静默"], 0.5),
]

# 台词相关关键词与语速
DIALOGUE_KEYWORDS = ["台词", "对白", "旁白", "说", "问道", "回答", "喊", "低声", "大声", "念", "讲", "asked", "replied", "said"]
EMOTIONAL_MARKS = ["！", "!", "？", "?"]
# 快速/急促语气线索，用于对白节奏判断
FAST_DIALOGUE_MARKS = ["快速", "急促", "快", "fast", "quickly", "hurry", "shout", "yell", "scream", "争吵", "angrily"]
DIALOGUE_QUOTES_RE = re.compile(r"「([^」]*)」")
ENGLISH_QUOTES_RE = re.compile(r'"([^"]*)"|“([^”]*)”')
WORD_COUNT_RE = re.compile(r"约?(\d+)\s*[词個个]")

# SEG 时长目标区间（与 references/minimax-h3-continuity.md 保持一致）
SEG_TARGET_MIN = 8.0
SEG_TARGET_MAX = 13.0
SEG_HARD_CAP = 15.0

# 不同阶段只要求当前阶段应该已经存在的文件，避免阶段 B 被后期产物阻塞。
STAGE_DOC_FILES = {
    "A": ["前提设定.md"],
    "B": [
        "前提设定.md",
        "镜头设计.md",
        "镜头内容检验.md",
        "文本语义拆分表.md",
        "视频生成内容检验.md",
        "视频分段.md",
        "文件地址管理.md",
    ],
    "C": [
        "前提设定.md",
        "镜头设计.md",
        "镜头内容检验.md",
        "视频生成内容检验.md",
        "视频分段.md",
        "文件地址管理.md",
    ],
    "D": [
        "前提设定.md",
        "镜头设计.md",
        "镜头内容检验.md",
        "视频生成内容检验.md",
        "视频分段.md",
        "文件地址管理.md",
        "分镜图方案.md",
    ],
    "E": [
        "前提设定.md",
        "镜头设计.md",
        "镜头内容检验.md",
        "视频生成内容检验.md",
        "视频分段.md",
        "文件地址管理.md",
        "分镜图方案.md",
        "导演总表.md",
    ],
    "F": [
        "前提设定.md",
        "镜头设计.md",
        "镜头内容检验.md",
        "视频生成内容检验.md",
        "视频分段.md",
        "文件地址管理.md",
        "分镜图方案.md",
        "导演总表.md",
    ],
    "G": [
        "前提设定.md",
        "镜头设计.md",
        "镜头内容检验.md",
        "视频分段.md",
        "视频生成内容检验.md",
        "风险质检.md",
        "导演总表.md",
        "文件地址管理.md",
        "分镜图方案.md",
    ],
}

# 保留旧常量，避免外部脚本导入时失效。
CORE_DOC_FILES = STAGE_DOC_FILES["G"]

# 阶段排序用于判断哪些视觉交付物应该已经存在。
STAGE_ORDER = {name: index for index, name in enumerate("ABCDEFG", start=1)}


def stage_at_least(stage: str, target: str) -> bool:
    """判断当前阶段是否已经到达目标阶段。"""
    return STAGE_ORDER[stage] >= STAGE_ORDER[target]


def find_project_html_files(dir_path: Path) -> list[Path]:
    """查找任务目录下的导演总表 HTML，排除临时文件。"""
    return sorted(
        path
        for path in dir_path.glob("*_director_full_table.html")
        if path.is_file() and not path.name.startswith("_")
    )


def extract_ids(text: str, pattern: re.Pattern[str]) -> set[str]:
    """提取并统一 ID，便于检查图片、SEG 和文档数量是否匹配。"""
    return {re.sub(r"[-_ ]+", "-", match.group(0).upper()) for match in pattern.finditer(text)}


def normalize_id(value: str) -> str:
    """统一 SH/SEG 编号中的大小写、空格、下划线和连字符。"""
    return re.sub(r"[-_ ]+", "-", value.upper()).strip()


def split_markdown_row(line: str) -> list[str]:
    """把 Markdown 表格的一行拆成单元格列表。"""
    return [cell.strip() for cell in line.strip().strip("|").split("|")]


def is_separator_row(cells: list[str]) -> bool:
    """判断是否为 Markdown 表格的分隔行（|---|---|）。"""
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.strip()) for cell in cells)


def find_column(headers: list[str], terms: tuple[str, ...]) -> int | None:
    """根据关键字在表头中找到列索引。"""
    normalized = [header.lower().replace(" ", "").replace("-", "") for header in headers]
    for index, header in enumerate(normalized):
        if any(term.lower().replace(" ", "").replace("-", "") in header for term in terms):
            return index
    return None


def blank_cell(value: str) -> bool:
    """判断单元格是否为空或占位符。"""
    return value.strip() in {"", "-", "—", "N/A", "n/a", "无", "待定"}


def extract_tables(text: str) -> list[list[list[str]]]:
    """从 Markdown 文本中提取所有表格。"""
    tables: list[list[list[str]]] = []
    current: list[str] = []
    for line in text.splitlines():
        if "|" in line:
            current.append(line)
        else:
            if len(current) >= 2:
                tables.append([split_markdown_row(ln) for ln in current])
            current = []
    if len(current) >= 2:
        tables.append([split_markdown_row(ln) for ln in current])
    return tables


def find_table_by_header(tables: list[list[list[str]]], terms: tuple[str, ...]) -> list[list[str]] | None:
    """根据表头关键字定位表格。"""
    for rows in tables:
        if not rows:
            continue
        headers = rows[0]
        norm = [h.lower().replace(" ", "").replace("-", "") for h in headers]
        for term in terms:
            target = term.lower().replace(" ", "").replace("-", "")
            if any(target in h for h in norm):
                return rows
    return None


def parse_duration_cell(value: str) -> float | None:
    """从单元格文本中解析秒数。"""
    value = value.strip().replace("秒", "s")
    # 优先匹配显式带 s/秒 的数字
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:s|秒)", value, re.IGNORECASE)
    if m:
        return float(m.group(1))
    # 兜底：提取第一个数字
    m = re.search(r"(\d+(?:\.\d+)?)", value)
    if m:
        return float(m.group(1))
    return None


def split_content_items(content: str) -> list[str]:
    """把 Required Content 单元格拆成独立内容项。

    引号内的分隔符不切分，避免英文台词中的逗号把一句话截断。
    """
    items: list[str] = []
    buf: list[str] = []
    in_quote: str | None = None
    i = 0
    while i < len(content):
        ch = content[i]
        # 处理引号状态切换（支持中文/英文弯引号与直角引号）
        if ch in ('"', '“', '”', '「', '」'):
            if in_quote is None:
                in_quote = ch
            elif (in_quote, ch) in [('“', '”'), ('「', '」'), ('"', '"')]:
                in_quote = None
            buf.append(ch)
            i += 1
            continue
        # 引号外的分隔符才切分
        if in_quote is None and ch in ("、", "，", ",", "；", ";"):
            item = "".join(buf).strip().strip("-*•")
            if item:
                items.append(item)
            buf = []
            i += 1
            continue
        buf.append(ch)
        i += 1
    item = "".join(buf).strip().strip("-*•")
    if item:
        items.append(item)
    return items


def count_chinese_chars(text: str) -> int:
    """统计中文字符数。"""
    return len(re.findall(r"[一-鿿]", text))


def count_english_words(text: str) -> int:
    """统计英文单词数（按连续字母计）。"""
    return len(re.findall(r"[A-Za-z]+", text))


def _pause_bonus(text: str) -> float:
    """根据标点数量增加少量停顿余量，对齐旁白/台词规范中的停顿规则。"""
    pauses = len(re.findall(r"[，,。.;；!?！？]", text))
    return min(pauses * 0.2, 1.0)


def estimate_min_duration(content: str) -> float:
    """根据 Required Content 文本估算最低时长。

    实现 `references/镜头内容检验规范.md` 第 4.2 节：
    - 台词/旁白独占一个内容项时，按字数估时长；
    - 台词与画面内容并发时（同一镜头内），取主导项（通常是台词），不重复相加；
    - 纯画面多项顺序发生时，仍按各项相加。
    """
    items = split_content_items(content)
    dialogue_total = 0.0
    visual_total = 0.0
    has_dialogue = False
    for item in items:
        item = item.strip()
        if not item:
            continue

        # 判断是否为台词/对白/旁白
        is_dialogue = (
            any(kw in item for kw in DIALOGUE_KEYWORDS)
            or "「" in item
            or '"' in item
            or "“" in item
            or "'" in item
        )
        if is_dialogue:
            # 先尝试统计引号内的中文
            chars = 0
            for quoted in DIALOGUE_QUOTES_RE.findall(item):
                chars += count_chinese_chars(quoted)
            if chars > 0:
                rate = 3.0 if any(m in item for m in EMOTIONAL_MARKS) else 4.0
                duration = max(0.5, chars / rate)
                duration += _pause_bonus(item)
                dialogue_total = max(dialogue_total, duration)
                has_dialogue = True
                continue

            # 没有中文时，按英文词数估算（项目使用英文对白/旁白）
            words = 0
            for quoted in ENGLISH_QUOTES_RE.findall(item):
                # findall 返回元组，取非空组拼接
                text_in_quotes = "".join(g for g in quoted if g)
                words += count_english_words(text_in_quotes)
            if words == 0:
                m = WORD_COUNT_RE.search(item)
                if m:
                    words = int(m.group(1))
                else:
                    words = count_english_words(item)
            if words > 0:
                # 对齐旁白/台词规范：常规 ≈150 wpm(0.40 s/词)，情绪 ≈133 wpm(0.45 s/词)，快速 ≈180 wpm(0.33 s/词)
                if any(m in item for m in EMOTIONAL_MARKS):
                    rate = 0.45
                elif any(m in item for m in FAST_DIALOGUE_MARKS):
                    rate = 0.33
                else:
                    rate = 0.40
                duration = max(0.5, words * rate)
                duration += _pause_bonus(item)
                dialogue_total = max(dialogue_total, duration)
                has_dialogue = True
                continue
            # 引号内没有任何可统计文本时按视觉项继续向下匹配
        # 画面内容项按规范表累加（顺序发生）
        visual_matched = False
        for _label, keywords, seconds in CONTENT_RULES:
            if any(kw in item for kw in keywords):
                visual_total += seconds
                visual_matched = True
                break
        if not visual_matched:
            visual_total += 1.0
    if has_dialogue:
        # 台词与画面并发：取主导项（通常是台词时长），不重复相加
        return max(dialogue_total, visual_total)
    return visual_total


def validate_visual_expansion(text: str, source: str, issues: list[str]) -> None:
    """校验视频生成内容检验中的镜头时间轴是否连续覆盖 Duration。"""
    tables = extract_tables(text)
    table = find_table_by_header(
        tables,
        ("视频生成内容检验", "镜头时间轴", "运镜路线", "shot id", "画面扩写"),
    )
    if not table:
        return

    headers = table[0]
    rows = table[1:]
    shot_col = find_column(headers, ("shot id", "镜头号", "shot"))
    duration_col = find_column(headers, ("duration", "时长"))
    axis_col = find_column(headers, ("镜头时间轴", "运镜路线", "时间轴"))
    if shot_col is None or duration_col is None or axis_col is None:
        return

    interval_re = re.compile(r"(\d+(?:\.\d+)?)\s*[–\-~]\s*(\d+(?:\.\d+)?)\s*(?:s|秒)?", re.IGNORECASE)

    for row in rows:
        if not row:
            continue
        shot_id = row[shot_col].strip()
        if not SHOT_RE.search(shot_id):
            continue

        duration = parse_duration_cell(row[duration_col]) if duration_col is not None else None
        axis_text = row[axis_col].strip() if axis_col is not None else ""
        if duration is None:
            issues.append(f"{source}: {shot_id}: 视频生成内容检验缺少 Duration，无法校验时间轴")
            continue

        intervals = []
        for match in interval_re.finditer(axis_text):
            intervals.append((float(match.group(1)), float(match.group(2))))
        if not intervals:
            issues.append(f"{source}: {shot_id}: 镜头时间轴未解析到有效时间段")
            continue

        intervals.sort()

        # 检查是否从 0 开始
        if intervals[0][0] > 0.05:
            issues.append(f"{source}: {shot_id}: 镜头时间轴未从 0s 开始")

        # 检查终点是否等于 Duration
        if abs(intervals[-1][1] - duration) > 0.05:
            issues.append(
                f"{source}: {shot_id}: 镜头时间轴终点 {intervals[-1][1]:g}s 与 Duration {duration:g}s 不一致"
            )

        # 检查重叠与空隙
        for idx in range(1, len(intervals)):
            prev_end = intervals[idx - 1][1]
            curr_start = intervals[idx][0]
            if curr_start < prev_end - 0.05:
                issues.append(f"{source}: {shot_id}: 镜头时间轴存在重叠 {curr_start:g}s < {prev_end:g}s")
            elif curr_start > prev_end + 0.1:
                issues.append(f"{source}: {shot_id}: 镜头时间轴存在空隙 {prev_end:g}s ~ {curr_start:g}s")

        # 检查是否超出 Duration
        for start, end in intervals:
            if end > duration + 0.05:
                issues.append(
                    f"{source}: {shot_id}: 镜头时间轴片段 {start:g}-{end:g}s 超出 Duration {duration:g}s"
                )


def validate_text(text: str, source: str = "document", require_shot_list: bool = False) -> int:
    """对一段 Markdown 文本执行校验。"""
    issues: list[str] = []
    current_headers: list[str] = []

    # 1. 老逻辑：逐行扫描 SEG 时长与首帧/尾帧锚点
    for number, line in enumerate(text.splitlines(), start=1):
        if "|" in line:
            cells = split_markdown_row(line)
            if is_separator_row(cells):
                continue
            if any("segment" in cell.lower() or "首帧" in cell or "尾帧" in cell for cell in cells):
                current_headers = cells

        if not SEGMENT_RE.search(line):
            continue

        # 只检查包含 Duration/时长 关键词的行，跳过时间轴等含 SEG 引用但非时长定义的行
        if not any(kw in line.lower() for kw in ["duration", "时长"]):
            continue

        durations = [float(match.group(1)) for match in DURATION_RE.finditer(line)]
        for duration in durations:
            if duration > SEG_HARD_CAP:
                issues.append(f"{source} line {number}: segment duration {duration:g}s exceeds Minimax H3 {SEG_HARD_CAP:g}s cap")
            elif duration > SEG_TARGET_MAX:
                issues.append(f"{source} line {number}: segment duration {duration:g}s exceeds target range {SEG_TARGET_MIN:g}-{SEG_TARGET_MAX:g}s")

        if "|" in line and current_headers:
            cells = split_markdown_row(line)
            first_index = find_column(current_headers, ("firstframe", "first-frame", "首帧", "开场帧"))
            last_index = find_column(current_headers, ("lastframe", "last-frame", "尾帧", "结束帧"))
            if first_index is not None and first_index < len(cells) and blank_cell(cells[first_index]):
                issues.append(f"{source} line {number}: segment row is missing a first-frame anchor")
            if last_index is not None and last_index < len(cells) and blank_cell(cells[last_index]):
                issues.append(f"{source} line {number}: segment row is missing a last-frame anchor")

    # 2. 解析表格做更精确的校验
    tables = extract_tables(text)

    # 2.1 Shot List 校验
    shot_table = find_table_by_header(tables, ("shot id", "shot", "镜头号", "镜头"))
    if shot_table is None and require_shot_list:
        issues.append(f"{source}: 缺少 Shot List 表格，无法执行镜头时长和 SEG 校验")
    if shot_table:
        headers = shot_table[0]
        rows = shot_table[1:]
        duration_col = find_column(headers, ("duration", "时长", "分配时长"))
        min_duration_col = find_column(headers, ("minduration", "min duration", "最低时长", "最少时长"))
        required_col = find_column(
            headers,
            ("requiredcontent", "required content", "必须内容", "必须出现的内容", "内容清单", "requiredcontent"),
        )
        segment_col = find_column(headers, ("minimax h3 segment", "segment", "所属seg", "视频段"))

        missing_columns = []
        if duration_col is None:
            missing_columns.append("Duration")
        if min_duration_col is None:
            missing_columns.append("Min Duration")
        if required_col is None:
            missing_columns.append("Required Content")
        if segment_col is None:
            missing_columns.append("Minimax H3 Segment")
        if missing_columns and require_shot_list:
            issues.append(f"{source}: Shot List 缺少关键列: {', '.join(missing_columns)}")

        # 累计每个 SEG 的时长与镜头数
        segment_durations: dict[str, float] = defaultdict(float)
        segment_shot_counts: dict[str, int] = defaultdict(int)

        for row in rows:
            if not row:
                continue
            shot_id = row[0].strip()
            if not SHOT_RE.search(shot_id):
                continue

            duration = parse_duration_cell(row[duration_col]) if duration_col is not None else None
            min_duration = parse_duration_cell(row[min_duration_col]) if min_duration_col is not None else None
            required = row[required_col].strip() if required_col is not None else ""
            seg_cell = row[segment_col].strip() if segment_col is not None else ""

            # 检查 Required Content
            if blank_cell(required):
                issues.append(f"{source}: {shot_id}: Required Content 为空，必须填写镜头必须出现的内容")
            else:
                estimated = estimate_min_duration(required)
                if min_duration is None:
                    issues.append(
                        f"{source}: {shot_id}: Min Duration 缺失，根据 Required Content 估算最低时长为 {estimated:g}s，请补填"
                    )
                    min_duration = estimated
                elif abs(min_duration - estimated) > 1.0:
                    issues.append(
                        f"{source}: {shot_id}: Min Duration {min_duration:g}s 与 Required Content 估算 {estimated:g}s 差距过大，请核对"
                    )

            # 检查分配时长是否足够
            if duration is not None and min_duration is not None and duration + 0.05 < min_duration:
                issues.append(
                    f"{source}: {shot_id}: 分配时长 {duration:g}s < 最低内容时长 {min_duration:g}s，需要延长或拆分镜头"
                )

            # 累计 SEG 时长与镜头数
            if duration is not None:
                for seg_id in SEGMENT_RE.findall(seg_cell):
                    segment_durations[seg_id.upper()] += duration
            for seg_id in SEGMENT_RE.findall(seg_cell):
                segment_shot_counts[seg_id.upper()] += 1

        # 检查 SEG 累计时长
        for seg_id, total in sorted(segment_durations.items()):
            if total > SEG_HARD_CAP:
                issues.append(f"{source}: {seg_id}: 所属镜头累计时长 {total:g}s 超过 {SEG_HARD_CAP:g}s 硬上限")
            elif total > SEG_TARGET_MAX:
                issues.append(f"{source}: {seg_id}: 所属镜头累计时长 {total:g}s 超过目标区间 {SEG_TARGET_MIN:g}-{SEG_TARGET_MAX:g}s，建议拆分或压缩")
            elif total < SEG_TARGET_MIN:
                issues.append(f"{source}: {seg_id}: 所属镜头累计时长 {total:g}s 低于目标区间 {SEG_TARGET_MIN:g}-{SEG_TARGET_MAX:g}s，建议检查是否信息过短")

        # 检查每个 SEG 至少 2 个镜头
        for seg_id, count in sorted(segment_shot_counts.items()):
            if count < 2:
                issues.append(f"{source}: {seg_id}: 仅包含 {count} 个镜头，每个 SEG 必须至少包含 2 个镜头")

    # 2.2 Minimax H3 Segments 表格校验
    segment_table = find_table_by_header(tables, ("segment id", "segment", "视频段", "seg"))
    if segment_table:
        headers = segment_table[0]
        rows = segment_table[1:]
        duration_col = find_column(headers, ("duration", "时长"))
        for row in rows:
            if not row:
                continue
            seg_id = row[0].strip()
            if not SEGMENT_RE.search(seg_id):
                continue
            duration = parse_duration_cell(row[duration_col]) if duration_col is not None else None
            if duration is not None and duration > SEG_HARD_CAP:
                issues.append(f"{source}: {seg_id}: 视频段标注时长 {duration:g}s 超过 {SEG_HARD_CAP:g}s 硬上限")
            elif duration is not None and duration > SEG_TARGET_MAX:
                issues.append(f"{source}: {seg_id}: 视频段标注时长 {duration:g}s 超过目标区间 {SEG_TARGET_MIN:g}-{SEG_TARGET_MAX:g}s")

    # 3. 视频生成内容检验时间轴校验
    validate_visual_expansion(text, source, issues)

    # 4. 文档级检查
    if "Minimax H3" not in text and "minimax h3" not in text:
        issues.append(f"{source}: document does not mention Minimax H3; confirm the output is a Minimax H3 segment plan")

    if not re.search(r"15\s*(?:s|秒|seconds?)", text, re.IGNORECASE):
        issues.append(f"{source}: document does not state the {SEG_HARD_CAP:g}s segment cap")

    if issues:
        print("Storyboard validation found issues:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    print("Storyboard validation passed.")
    return 0


def validate(path: Path) -> int:
    """校验单个 Markdown 文件。"""
    text = path.read_text(encoding="utf-8")
    return validate_text(text, source=str(path))


def validate_speech_segments(dir_path: Path) -> list[str]:
    """校验 speech_segments.json 的语义拆分完整性。"""
    issues: list[str] = []
    seg_path = dir_path / "00_元数据" / "清单" / "speech_segments.json"
    if not seg_path.exists():
        return issues

    try:
        data = json.loads(seg_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        issues.append(f"speech_segments.json 无法读取: {error}")
        return issues

    # 检查完整性
    integrity = data.get("integrity_issues", [])
    if integrity:
        for item in integrity:
            uid = item.get("unit_id", "未知")
            issues.append(f"语义拆分完整性校验失败: {uid} 拆分后无法还原原文")

    # 检查 dialogue 类型是否缺少说话人
    for p in portions:
        if p.get("type") == "dialogue" and not p.get("speaker"):
            pid = p.get("portion_id", "未知")
            issues.append(f"dialogue 缺少说话人: {pid}，需根据上下文推断并补全")

    # 检查是否需要人工复核
    if data.get("needs_manual_review"):
        issues.append("speech_segments.json 标记需要人工复核，请在 doc/文本语义拆分表.md 中确认")

    # 检查每个 portion 是否都能还原 original_text
    portions = data.get("portions", [])
    reconstructed: dict[str, list[str]] = defaultdict(list)
    originals: dict[str, str] = {}
    for p in portions:
        uid = p.get("parent_unit_id")
        if not uid:
            continue
        reconstructed[uid].append(p.get("text", ""))
        originals[uid] = p.get("original_text", "")

    for uid, parts in reconstructed.items():
        joined = "".join(parts)
        original = originals.get(uid, "")
        if joined != original:
            issues.append(f"文本拼接不一致: {uid}")

    # 检查非法断点：片段以从属连词开头/结尾
    dependent_words = (
        "因为", "虽然", "尽管", "如果", "假如", "要是", "当", "在", "随着",
        "即使", "无论", "不管", "由于", "为了", "除了", "正如", "就像",
        "because", "although", "though", "if", "when", "while", "since", "as",
    )
    for p in portions:
        text = p.get("text", "").strip()
        reason = p.get("breakpoint_reason", "")
        # 只有自动拆分的才检查，人工确认的例外
        if "人工" in reason or "句子结尾" in reason:
            continue
        left = text.lstrip(" ，,；;。！？.!?\"\"''「『")
        if any(left.startswith(w) for w in dependent_words):
            pid = p.get("portion_id", "未知")
            issues.append(f"语义拆分可疑: {pid} 以从属连词开头，可能切断了从句")

    return issues


def validate_directory(dir_path: Path, stage: str = "G", strict: bool = False) -> int:
    """校验任务目录：按阶段检查文档、视觉产物和交付合同。"""
    doc_dir = dir_path / "doc"
    if not doc_dir.exists():
        print(f"doc/ directory not found in {dir_path}", file=sys.stderr)
        return 2

    required_docs = STAGE_DOC_FILES[stage]
    missing = [name for name in required_docs if not (doc_dir / name).exists()]
    if missing:
        print(f"doc/ 下缺少文件: {', '.join(missing)}", file=sys.stderr)
        return 1

    # 只合并当前阶段已有文件，避免后期文档内容提前影响阶段 B 校验。
    combined = ""
    for name in required_docs:
        combined += (doc_dir / name).read_text(encoding="utf-8") + "\n\n"

    result = validate_text(
        combined,
        source="doc",
        require_shot_list=stage_at_least(stage, "B"),
    )

    # 阶段 B 起检查语义拆分完整性（如果存在 speech_segments.json）
    if stage_at_least(stage, "B"):
        speech_issues = validate_speech_segments(dir_path)
        if speech_issues:
            print("语义拆分校验发现以下问题:", file=sys.stderr)
            for issue in speech_issues:
                print(f"- {issue}", file=sys.stderr)
            result = 1

    # 检查 HTML 占位符，防止模板示例或 {{...}} 残留进入截图阶段。
    if stage_at_least(stage, "E"):
        html_files = find_project_html_files(dir_path)
        if not html_files:
            print("交付合同错误：缺少 *_director_full_table.html", file=sys.stderr)
            result = 1
        for html_path in html_files:
            html_text = html_path.read_text(encoding="utf-8")
            if "{{" in html_text or "}}" in html_text:
                print(f"交付合同错误：{html_path.name} 仍包含模板占位符", file=sys.stderr)
                result = 1
            # 检查常见示例文本残留
            example_patterns = [
                "{{EPISODE_TITLE}}", "{{TOTAL_SHOTS}}", "{{TOTAL_DURATION}}",
                "{{ASPECT_RATIO}}", "{{CHARACTER_LIST}}", "{{SEG_COUNT}}",
                "{{TOTAL_SECONDS}}", "{{SEG_STYLE}}", "{{SEG_SUMMARY}}",
                "{{SEG_DURATION}}", "{{FIRST_FRAME_ANCHOR}}", "{{LAST_FRAME_ANCHOR}}",
                "{{DIALOGUE}}", "{{NARRATION}}", "{{ENV_SOUND}}", "{{ACTION_SOUND}}",
                "{{BLOCKING_SVG}}", "示例风格", "请填写", "待定", "TODO", "N/A",
            ]
            for pattern in example_patterns:
                if pattern in html_text:
                    print(f"交付合同错误：{html_path.name} 仍包含示例/占位文本 '{pattern}'", file=sys.stderr)
                    result = 1
                    break
            if html_text.count('class="seg-row"') == 0:
                print(f"交付合同错误：{html_path.name} 没有 .seg-row", file=sys.stderr)
                result = 1

    # D 阶段起必须做到 Shot 与 panel 一一对应，不能只放一张示例图。
    if stage_at_least(stage, "D"):
        panels_dir = dir_path / "panels"
        panel_files = sorted(
            path for path in panels_dir.glob("*")
            if path.is_file() and path.suffix.lower() in {".png", ".jpg", ".jpeg", ".webp"}
        ) if panels_dir.exists() else []
        if not panel_files:
            print("交付合同错误：panels/ 下没有可用图片", file=sys.stderr)
            result = 1
        else:
            # 从已锁定文档提取 SH-XX，并核对每个图片文件名是否只对应一个镜头。
            expected_shots = extract_ids(combined, SHOT_RE)
            panel_ids: list[str] = []
            invalid_panel_names: list[str] = []
            for panel_path in panel_files:
                matches = list(SHOT_RE.finditer(panel_path.stem))
                if len(matches) != 1:
                    invalid_panel_names.append(panel_path.name)
                    continue
                panel_ids.append(normalize_id(matches[0].group(0)))

            if not expected_shots:
                print("交付合同错误：无法从阶段文档提取任何 SH-XX，不能核对 panels/ 覆盖范围", file=sys.stderr)
                result = 1
            if invalid_panel_names:
                print(
                    f"交付合同错误：panel 文件名必须包含且只能包含一个 SH-XX: {', '.join(invalid_panel_names)}",
                    file=sys.stderr,
                )
                result = 1

            duplicate_panel_ids = sorted(
                panel_id for panel_id in set(panel_ids) if panel_ids.count(panel_id) > 1
            )
            if duplicate_panel_ids:
                print(
                    f"交付合同错误：同一 Shot 存在多个 panel 文件: {', '.join(duplicate_panel_ids)}",
                    file=sys.stderr,
                )
                result = 1

            actual_shots = set(panel_ids)
            missing_panels = sorted(expected_shots - actual_shots)
            extra_panels = sorted(actual_shots - expected_shots)
            if missing_panels:
                print(f"交付合同错误：缺少 Shot panel: {', '.join(missing_panels)}", file=sys.stderr)
                result = 1
            if extra_panels:
                print(f"交付合同错误：存在未在 Shot List 中声明的 panel: {', '.join(extra_panels)}", file=sys.stderr)
                result = 1

    # E 阶段起必须做到 SEG 与故事板参考图一一对应。
    if stage_at_least(stage, "E"):
        refs_dir = dir_path / "故事板参考图"
        ref_files = sorted(refs_dir.glob("*.png")) if refs_dir.exists() else []
        if not ref_files:
            print("交付合同错误：故事板参考图/ 下没有 PNG", file=sys.stderr)
            result = 1
        expected_segments = extract_ids(combined, SEGMENT_RE)
        ref_ids: list[str] = []
        invalid_refs: list[str] = []
        for ref_path in ref_files:
            matches = list(SEGMENT_RE.finditer(ref_path.stem))
            if len(matches) != 1:
                invalid_refs.append(ref_path.name)
                continue
            ref_ids.append(normalize_id(matches[0].group(0)))
        if invalid_refs:
            print(
                f"交付合同错误：故事板参考图文件名必须包含且只能包含一个 SEG 编号: {', '.join(invalid_refs)}",
                file=sys.stderr,
            )
            result = 1
        if not expected_segments:
            print("交付合同错误：无法从阶段文档提取任何 SEG，不能核对故事板参考图覆盖范围", file=sys.stderr)
            result = 1

        duplicate_ref_ids = sorted(ref_id for ref_id in set(ref_ids) if ref_ids.count(ref_id) > 1)
        if duplicate_ref_ids:
            print(
                f"交付合同错误：同一 SEG 存在多张故事板参考图: {', '.join(duplicate_ref_ids)}",
                file=sys.stderr,
            )
            result = 1

        actual_segments = set(ref_ids)
        missing_refs = sorted(expected_segments - actual_segments)
        extra_refs = sorted(actual_segments - expected_segments)
        if missing_refs:
            print(f"交付合同错误：缺少 SEG 故事板参考图: {', '.join(missing_refs)}", file=sys.stderr)
            result = 1
        if extra_refs:
            print(f"交付合同错误：存在未在文档中声明的 SEG 故事板参考图: {', '.join(extra_refs)}", file=sys.stderr)
            result = 1

    # F/G 阶段检查资产包目录；允许项目使用不同目录名，但不能完全缺失。
    if stage_at_least(stage, "F"):
        metadata_dir = dir_path / "00_元数据" / "清单"
        if not metadata_dir.exists():
            print("交付合同错误：缺少 00_元数据/清单/ 目录", file=sys.stderr)
            result = 1
        else:
            asset_packs = list(metadata_dir.glob("*segment*asset*pack*.json"))
            # 兼容命名为 SEG-XX_asset_pack.json 的任务产物
            if not asset_packs:
                asset_packs = list(metadata_dir.glob("SEG-*_asset_pack.json"))
            if not asset_packs:
                print("交付合同错误：清单目录中缺少 segment asset pack JSON", file=sys.stderr)
                result = 1
            else:
                expected_segments = extract_ids(combined, SEGMENT_RE)
                pack_segments: list[str] = []
                # Minimax H3 只能读取可访问的公网 HTTP(S) 地址，禁止 asset:// 等内部占位符。
                valid_url_re = re.compile(r"^https?://\S+$", re.IGNORECASE)
                for pack_path in asset_packs:
                    try:
                        pack = json.loads(pack_path.read_text(encoding="utf-8"))
                    except (OSError, json.JSONDecodeError) as error:
                        print(f"交付合同错误：资产包 JSON 无法读取: {pack_path.name} ({error})", file=sys.stderr)
                        result = 1
                        continue

                    if pack.get("manifest_type") != "segment_asset_pack":
                        print(f"交付合同错误：{pack_path.name} 不是 segment_asset_pack", file=sys.stderr)
                        result = 1
                    segment_id = normalize_id(str(pack.get("segment", "")))
                    if not SEGMENT_RE.search(segment_id):
                        print(f"交付合同错误：{pack_path.name} 缺少有效 segment ID", file=sys.stderr)
                        result = 1
                    else:
                        pack_segments.append(segment_id)

                    images = pack.get("reference_images")
                    # 规范允许按需使用参考图，但不能超过 Minimax H3 的 5 张上限。
                    if not isinstance(images, list) or not 1 <= len(images) <= 5:
                        print(
                            f"交付合同错误：{pack_path.name} reference_images 必须包含 1-5 张",
                            file=sys.stderr,
                        )
                        result = 1
                    else:
                        # 图片槽位必须从 1 开始连续编号；4 张时合法槽位为 1-4。
                        slots = {
                            item.get("slot")
                            for item in images
                            if isinstance(item, dict)
                        }
                        expected_slots = set(range(1, len(images) + 1))
                        if slots != expected_slots:
                            slot_text = f"1-{len(images)}"
                            print(
                                f"交付合同错误：{pack_path.name} reference_images 槽位必须为 {slot_text}",
                                file=sys.stderr,
                            )
                            result = 1
                        for item in images:
                            url = item.get("public_url", "") if isinstance(item, dict) else ""
                            if not isinstance(url, str) or not valid_url_re.match(url):
                                label = item.get("label", "未知") if isinstance(item, dict) else "未知"
                                print(f"交付合同错误：{pack_path.name} 的 {label} 缺少有效 public URL", file=sys.stderr)
                                result = 1

                    audios = pack.get("reference_audios", [])
                    if not isinstance(audios, list) or len(audios) > 3:
                        print(f"交付合同错误：{pack_path.name} reference_audios 超过 3 段", file=sys.stderr)
                        result = 1
                    total_audio = 0.0
                    for audio in audios if isinstance(audios, list) else []:
                        duration = audio.get("duration_seconds") if isinstance(audio, dict) else None
                        url = audio.get("public_url", "") if isinstance(audio, dict) else ""
                        try:
                            duration_value = float(duration)
                        except (TypeError, ValueError):
                            duration_value = -1
                        if not 2.0 <= duration_value <= 15.0 or not isinstance(url, str) or not valid_url_re.match(url):
                            print(f"交付合同错误：{pack_path.name} 存在无效 reference_audio", file=sys.stderr)
                            result = 1
                        total_audio += max(duration_value, 0)
                    if total_audio > 15.0:
                        print(f"交付合同错误：{pack_path.name} reference_audio 总时长超过 15 秒", file=sys.stderr)
                        result = 1

                duplicate_pack_segments = sorted(segment_id for segment_id in set(pack_segments) if pack_segments.count(segment_id) > 1)
                if duplicate_pack_segments:
                    print(f"交付合同错误：同一 SEG 存在多个资产包: {', '.join(duplicate_pack_segments)}", file=sys.stderr)
                    result = 1
                missing_pack_segments = sorted(expected_segments - set(pack_segments))
                extra_pack_segments = sorted(set(pack_segments) - expected_segments)
                if missing_pack_segments:
                    print(f"交付合同错误：缺少 SEG 资产包: {', '.join(missing_pack_segments)}", file=sys.stderr)
                    result = 1
                if extra_pack_segments:
                    print(f"交付合同错误：存在未在文档中声明的 SEG 资产包: {', '.join(extra_pack_segments)}", file=sys.stderr)
                    result = 1

    # G 阶段要求风险质检明确给出交付状态，不能只靠文件存在判断。
    if stage == "G":
        risk_path = doc_dir / "风险质检.md"
        risk_text = risk_path.read_text(encoding="utf-8")
        submit_ready_match = re.search(
            r"(?im)^\s*(?:[-*]\s*)?`?submit_ready`?\s*[:：=]\s*(true|false)\s*$",
            risk_text,
        )
        if not submit_ready_match:
            print("交付合同错误：风险质检.md 未明确声明 submit_ready: true/false", file=sys.stderr)
            result = 1
        elif submit_ready_match.group(1).lower() != "true":
            print("交付合同错误：风险质检.md 的 submit_ready 不是 true", file=sys.stderr)
            result = 1

    # 全局风格是阶段 A 的正式输出，A 阶段 QA 就必须检查项目级配置。
    if stage_at_least(stage, "A"):
        style_path = dir_path / "references" / "全局风格.md"
        if style_path.exists():
            style_text = style_path.read_text(encoding="utf-8")
            placeholder_patterns = [
                r"\[如：",
                r"例：删除本行后填写",
                r"(?m)^\s*-\s*\[\s\]\s+",
            ]
            # Skill 自带规范含有示例库，不能误当作项目级实际配置。
            generic_style_markers = [
                "# 全局风格规范.md",
                "## 七、项目配置文件",
            ]
            if all(marker in style_text for marker in generic_style_markers):
                print(
                    f"交付合同错误：{style_path} 看起来仍是 Skill 通用规范，必须改为项目级风格配置",
                    file=sys.stderr,
                )
                result = 1
            required_style_fields = [
                "项目唯一 ID",
                "项目名称",
                "版本",
                "最后更新",
                "主风格品类",
                "渲染类型",
                "画面精度",
                "镜头语言基调",
                "构图逻辑",
                "统一美术元素",
                "统一布光逻辑",
                "统一光影软硬",
                "统一阴影属性",
                "统一色域基调",
                "统一色彩逻辑",
                "统一对比度与曝光",
                "统一材质表现",
                "统一画面肌理",
            ]
            # 每个必填字段必须在项目文件中有真实的非空值。
            missing_style_fields = [
                field for field in required_style_fields
                if not re.search(rf"(?m)^\s*-\s*{re.escape(field)}\s*[:：]\s*\S+", style_text)
            ]
            if missing_style_fields:
                print(
                    f"交付合同错误：全局风格缺少已填写的必填字段: {', '.join(missing_style_fields)}",
                    file=sys.stderr,
                )
                result = 1
            remaining = [pattern for pattern in placeholder_patterns if re.search(pattern, style_text, re.MULTILINE)]
            if remaining:
                print(
                    f"交付合同错误：全局风格仍包含未填写的模板占位内容: {style_path}",
                    file=sys.stderr,
                )
                result = 1
        else:
            # 全局风格是阶段 B 之后所有视觉产出的硬性输入，缺失时必须阻断流程。
            print(f"交付合同错误：项目缺少必需的 references/全局风格.md: {style_path}", file=sys.stderr)
            result = 1

    # 轻量检查：panels/ 下的图片是否在文件地址管理表中登记
    file_mgmt_path = doc_dir / "文件地址管理.md"
    panels_dir = dir_path / "panels"
    if file_mgmt_path.exists() and panels_dir.exists():
        mgmt_text = file_mgmt_path.read_text(encoding="utf-8")
        unregistered = [
            img.name for img in panels_dir.iterdir()
            if img.is_file() and img.name not in mgmt_text
        ]
        if unregistered:
            print("File address management warnings:")
            for name in unregistered:
                print(f"- panels/{name} 未在 doc/文件地址管理.md 中登记")
            # 文件登记是交付合同的强制项；无论是否传入兼容参数都必须失败。
            result = 1

    # 轻量检查：scripts/ 下的任务级脚本是否已登记
    scripts_dir = dir_path / "scripts"
    if file_mgmt_path.exists() and scripts_dir.exists():
        mgmt_text = file_mgmt_path.read_text(encoding="utf-8")
        unregistered_scripts = []
        for script_path in scripts_dir.rglob("*"):
            if script_path.is_file() and script_path.name not in mgmt_text:
                unregistered_scripts.append(script_path.relative_to(dir_path).as_posix())
        if unregistered_scripts:
            print("File address management warnings:")
            for rel_path in unregistered_scripts:
                print(f"- {rel_path} 未在 doc/文件地址管理.md 中登记")
            # 文件登记是交付合同的强制项；无论是否传入兼容参数都必须失败。
            result = 1

    return result


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description="按阶段校验 Minimax H3 分镜项目")
    parser.add_argument("path", help="Markdown 文件或项目目录")
    parser.add_argument(
        "--stage",
        choices=list(STAGE_DOC_FILES),
        default="G",
        help="项目校验阶段，默认 G；单文件模式仅执行文档校验",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="兼容旧命令的参数；文件登记现在默认就是硬门禁，传入与否结果相同",
    )
    args = parser.parse_args(argv[1:])

    path = Path(args.path)
    if not path.exists():
        print(f"File or directory not found: {path}", file=sys.stderr)
        return 2

    if path.is_dir():
        return validate_directory(path, stage=args.stage, strict=args.strict)
    return validate(path)


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
