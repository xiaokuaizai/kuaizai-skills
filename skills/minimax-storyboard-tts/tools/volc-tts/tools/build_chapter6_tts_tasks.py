# 从第六章正式 TTS Markdown 导出机器可用的任务清单。
# 这个脚本只写 JSON/Markdown，不调用 TTS 接口，不产生付费请求。
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[3]
SOURCE_MD = ROOT / "wiki-整理/wiki/主线视频计划/第六章/第六章TTS语音文本.md"
DATA_FILE = Path(__file__).resolve().parents[1] / "data/chapter6_lines.json"
OUTPUT_DIR = Path(__file__).resolve().parents[1] / "output/chapter6"
TASK_FILE = OUTPUT_DIR / "ch6_tts_tasks.json"
TASK_MD_FILE = OUTPUT_DIR / "ch6_tts_tasks.md"
STATUS_FILE = OUTPUT_DIR / "tasks/第六章TTS准备状态.md"

VOICE_META = {
    "Narrator": {
        "slug": "narrator",
        "voice": "旁白男声/中性低速",
        "voice_type": "en_male_tim_uranus_bigtts",
    },
    "An Qi": {
        "slug": "an_qi",
        "voice": "少女女声",
        "voice_type": "en_female_dacey_uranus_bigtts",
    },
    "Jiang Che": {
        "slug": "jiang_che",
        "voice": "少年男声",
        "voice_type": "zh_male_M100_conversation_wvae_bigtts",
    },
    "Chen Zongjian": {
        "slug": "chen_zongjian",
        "voice": "中年男声 / Sylus",
        "voice_type": "en_male_sylus_emo_v2_mars_bigtts",
    },
    "Chen Recording": {
        "slug": "chen_recording",
        "voice": "陈总监录音质感 / Sylus",
        "voice_type": "en_male_sylus_emo_v2_mars_bigtts",
    },
    "Maria": {
        "slug": "maria",
        "voice": "中年女声 / Skye",
        "voice_type": "en_female_skye_emo_v2_mars_bigtts",
    },
    "Jiang Mingyuan": {
        "slug": "jiang_mingyuan",
        "voice": "父亲类成熟男声 / Sylus",
        "voice_type": "en_male_sylus_emo_v2_mars_bigtts",
    },
    "Lin Xue": {
        "slug": "lin_xue",
        "voice": "母亲类成熟女声 / Skye",
        "voice_type": "en_female_skye_emo_v2_mars_bigtts",
    },
}


def parse_source():
    """按当前 Markdown 结构读取 S01-S08 下的角色、英文、中文。"""
    text = SOURCE_MD.read_text(encoding="utf-8")
    in_export = False
    current_section = None
    current_role = None
    pending_text = []
    records = []

    def flush_record():
        nonlocal pending_text
        if not current_section or not current_role or not pending_text:
            pending_text = []
            return
        block = "\n".join(pending_text).strip()
        zh_match = re.search(r"中文：(.+)", block)
        text_en = re.sub(r"中文：.+", "", block, flags=re.S).strip()
        text_en = re.sub(r"\s+", " ", text_en)
        text_zh = zh_match.group(1).strip() if zh_match else ""
        records.append({
            "section": current_section,
            "role": current_role,
            "text_en": text_en,
            "text_zh": text_zh,
        })
        pending_text = []

    for raw in text.splitlines():
        line = raw.strip()
        if line == "## 按分节导出":
            in_export = True
            continue
        if in_export and line.startswith("## ") and line != "## 按分节导出":
            flush_record()
            break
        if not in_export:
            continue
        section_match = re.match(r"^###\s+(S\d{2})$", line)
        role_match = re.match(r"^####\s+(.+)$", line)
        if section_match:
            flush_record()
            current_section = section_match.group(1)
            current_role = None
            continue
        if role_match:
            flush_record()
            current_role = role_match.group(1).strip()
            continue
        if current_section and current_role and line:
            pending_text.append(line)

    return records


def build_tasks(records):
    """把解析记录补上 task_id、音色和输出路径。"""
    tasks = []
    scenes = []
    by_section = {}

    for index, record in enumerate(records, start=1):
        role = record["role"]
        if role not in VOICE_META:
            raise ValueError(f"未知角色音色: {role}")
        meta = VOICE_META[role]
        section = record["section"]
        task_id = f"ch6_s{section[-2:]}_{meta['slug']}_{index:03d}"
        task = {
            "task_id": task_id,
            "section": f"CH6-SD-{section}",
            "role": role,
            "voice": meta["voice"],
            "voice_type": meta["voice_type"],
            "speed": 1.0,
            "emotion": "chapter6_default",
            "text_en": record["text_en"],
            "text_zh": record["text_zh"],
            "learning_point": "",
            "output_wav": str(OUTPUT_DIR / "audio" / f"{task_id}.mp3").replace("\\", "/"),
            "status": "待生成",
        }
        tasks.append(task)
        by_section.setdefault(section, []).append({
            "seq": index,
            "id": task_id,
            "role": meta["slug"],
            "text": record["text_en"],
            "text_zh": record["text_zh"],
            "speed": 1.0,
            "emotion": "chapter6_default",
        })

    for section, lines in by_section.items():
        scenes.append({"scene": f"CH6-SD-{section}", "lines": lines})
    return scenes, tasks


def main():
    records = parse_source()
    scenes, tasks = build_tasks(records)
    role_counts = Counter(task["role"] for task in tasks)
    voice_counts = Counter(task["voice_type"] for task in tasks)

    if len(tasks) != 38:
        raise SystemExit(f"第六章应为 38 条，当前解析到 {len(tasks)} 条")

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / "tasks").mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(scenes, ensure_ascii=False, indent=2), encoding="utf-8")
    TASK_FILE.write_text(json.dumps({
        "chapter": "06",
        "source": str(SOURCE_MD).replace("\\", "/"),
        "status": "prepared",
        "line_count": len(tasks),
        "tasks": tasks,
    }, ensure_ascii=False, indent=2), encoding="utf-8")

    md = [
        "# 第六章 TTS 任务清单",
        "",
        f"- 来源：`{SOURCE_MD}`",
        f"- 条数：{len(tasks)}",
        "- 语速：1.0x",
        "",
        "## 角色统计",
        "",
        "| 角色 | 条数 |",
        "|---|---:|",
    ]
    for role, count in sorted(role_counts.items()):
        md.append(f"| {role} | {count} |")
    md.extend(["", "## 音色统计", "", "| voice_type | 条数 |", "|---|---:|"])
    for voice_type, count in sorted(voice_counts.items()):
        md.append(f"| `{voice_type}` | {count} |")
    md.extend(["", "## 明细", "", "| 序号 | TTS ID | 角色 | 英文 | 中文 |", "|---:|---|---|---|---|"])
    for index, task in enumerate(tasks, start=1):
        md.append(f"| {index:03d} | `{task['task_id']}` | {task['role']} | {task['text_en']} | {task['text_zh']} |")
    TASK_MD_FILE.write_text("\n".join(md) + "\n", encoding="utf-8")

    STATUS_FILE.write_text(
        "\n".join([
            "# 第六章 TTS 准备状态",
            "",
            "更新时间：2026-07-29",
            "",
            "## 当前状态",
            "",
            "- 已从正式 `第六章TTS语音文本.md` 导出 38 条任务。",
            "- 已建立 `data/chapter6_lines.json`。",
            "- 已建立 `output/chapter6/ch6_tts_tasks.json` 和 Markdown 清单。",
            "- 生成前需运行 `python generate_chapter6.py --check-only` 通过后，再运行 `python generate_chapter6.py`。",
            "",
            "## 注意",
            "",
            "- 本脚本只使用正式 TTS Markdown，不读取旧视频目录。",
            "- Chen Recording 先生成干净音频，录音质感可交给后期处理。",
            "- 第 37、38 段只做音频，不做 MagicHour 基准图。",
        ]) + "\n",
        encoding="utf-8",
    )

    print(f"已导出: {TASK_FILE}")
    print(f"已导出: {DATA_FILE}")
    print(f"line_count={len(tasks)}")


if __name__ == "__main__":
    main()
