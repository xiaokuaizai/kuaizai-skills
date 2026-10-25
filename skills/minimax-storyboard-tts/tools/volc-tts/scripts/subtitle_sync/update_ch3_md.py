"""
根据第三章最新 TTS JSON 和 manifest，重新生成 ch3_tts_tasks.md。

路径统一使用 对口型/TTS/output/chapter3，避免再写入旧的视频目录。
"""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[4]
TTS_OUTPUT_DIR = Path(__file__).resolve().parents[2] / "output/chapter3"
TASK_JSON = TTS_OUTPUT_DIR / "ch3_tts_tasks.json"
MANIFEST_JSON = TTS_OUTPUT_DIR / "audio/ch3_tts_manifest.json"
TASK_MD = TTS_OUTPUT_DIR / "ch3_tts_tasks.md"


def main():
    """读取最新清单，并写出给人查看的 Markdown 任务表。"""
    manifest_data = json.loads(MANIFEST_JSON.read_text(encoding="utf-8"))
    task_data = json.loads(TASK_JSON.read_text(encoding="utf-8"))
    size_map = {item["id"]: item.get("size", 0) for item in manifest_data["manifest"]}

    lines = [
        "# 第三章TTS任务清单",
        "",
        f"说明：火山引擎 V1 HTTP 接口生成 mp3，共 {len(task_data['tasks'])} 条，默认语速 1.0x。",
        "",
        "| 任务ID | 分节 | 角色 | 音色 | 语速 | 英文文本 | 输出文件 | 大小 | 状态 |",
        "|---|---|---|---|---:|---|---|---:|---|",
    ]

    for task in task_data["tasks"]:
        task_id = task["task_id"]
        size = size_map.get(task_id, 0)
        size_text = f"{size // 1024}KB" if size else "-"
        output_path = task["output_wav"].replace("G:/draw_long/novel/", "")
        lines.append(
            f"| `{task_id}` | {task['section']} | {task['role']} | {task['voice_type']} | "
            f"{task['speed']} | {task['text_en']} | `{output_path}` | {size_text} | {task['status']} |"
        )

    TASK_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"已更新：{TASK_MD}")


if __name__ == "__main__":
    main()
