"""
根据第三章 TTS 任务和实际 mp3 时长生成双语 SRT。

说明：
- 英文台词来自 ch3_tts_tasks.json。
- 时间轴来自 ffprobe 读取的真实 mp3 时长。
- 每条之间默认留 0.35 秒间隔，方便后期剪辑。
"""
import json
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
TTS_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output/chapter3"
TASK_JSON = TTS_OUTPUT_DIR / "ch3_tts_tasks.json"
SRT_PATH = TTS_OUTPUT_DIR / "subtitles/ch3_full_zh_en.srt"
GAP_SECONDS = 0.35


def format_time(seconds):
    """把秒数转换成 SRT 需要的 00:00:00,000 格式。"""
    total_ms = round(seconds * 1000)
    ms = total_ms % 1000
    total_seconds = total_ms // 1000
    sec = total_seconds % 60
    total_minutes = total_seconds // 60
    minute = total_minutes % 60
    hour = total_minutes // 60
    return f"{hour:02d}:{minute:02d}:{sec:02d},{ms:03d}"


def duration_seconds(path):
    """用 ffprobe 读取单个 mp3 的实际时长。"""
    result = subprocess.run(
        [
            "ffprobe",
            "-v",
            "error",
            "-show_entries",
            "format=duration",
            "-of",
            "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="ignore",
        check=False,
    )
    return float((result.stdout or "0").strip() or 0)


def main():
    data = json.loads(TASK_JSON.read_text(encoding="utf-8"))
    tasks = data["tasks"]
    SRT_PATH.parent.mkdir(parents=True, exist_ok=True)

    current = 0.0
    lines = ["NOTE: 第三章 TTS 对齐版，时间轴按 2026-07-27 mp3 实际时长生成。"]
    for index, task in enumerate(tasks, start=1):
        audio_path = Path(task["output_wav"])
        if not audio_path.exists():
            raise FileNotFoundError(f"缺少音频：{audio_path}")
        duration = duration_seconds(audio_path)
        if duration <= 0:
            raise ValueError(f"无法读取时长：{audio_path}")
        start = current
        end = start + duration
        lines.extend([
            "",
            str(index),
            f"{format_time(start)} --> {format_time(end)}",
            task["text_en"],
            task["text_zh"],
        ])
        current = end + GAP_SECONDS

    lines.append("")
    SRT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"生成完成：{SRT_PATH}")
    print(f"字幕条数：{len(tasks)}")
    print(f"含间隔总时长：{format_time(max(current - GAP_SECONDS, 0))}")


if __name__ == "__main__":
    main()
