import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

"""
第三章 TTS 同步脚本。

作用：
1. 从 wiki 中的《第三章英文对白与旁白台本》读取最新台词。
2. 重建 data/chapter3_lines.json 和 output/chapter3/ch3_tts_tasks.*。
3. 核对已有 mp3，能复用就复制，文本或语速不一致就重新生成。
"""
import argparse
import base64
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path

import requests

from src.config import (
    ACCESS_TOKEN,
    API_URL,
    APP_ID,
    DEFAULT_SPEED_RATIO,
    PROXIES,
    VOICE_CONFIG,
)


ROOT = Path(__file__).resolve().parents[4]
TTS_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_MD = ROOT / "wiki-整理/wiki/主线视频计划/第三章/第三章英文对白与旁白台本.md"
DATA_FILE = TTS_ROOT / "data/chapter3_lines.json"
TTS_DIR = TTS_ROOT / "output/chapter3"
AUDIO_DIR = TTS_DIR / "audio"
TASK_JSON = TTS_DIR / "ch3_tts_tasks.json"
TASK_MD = TTS_DIR / "ch3_tts_tasks.md"
MANIFEST_FILE = AUDIO_DIR / "ch3_tts_manifest.json"
LEGACY_AUDIO_DIR = ROOT / "视频/第三章/tts/audio"

ROLE_KEY = {
    "Narrator": "narrator",
    "Email": "email",
    "Jiang Che": "jiang_che",
    "An Qi": "an_qi",
    "Guard": "guard",
    "Doctor": "doctor",
}

ROLE_VOICE_LABEL = {
    "Narrator": "旁白男声/中性低速",
    "Email": "正式电子提示音色",
    "Jiang Che": "少年男声",
    "An Qi": "少女女声",
    "Guard": "成熟男声",
    "Doctor": "成熟女声/男声",
}

VOICE_CONFIG_CH3 = {
    **VOICE_CONFIG,
    "email": "en_male_michael_moon_bigtts",
    "guard": "en_male_glen_emo_v2_mars_bigtts",
    "doctor": "en_female_skye_emo_v2_mars_bigtts",
}

HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json",
}


def slug_role(role_key):
    """把角色 key 转成文件名片段。"""
    return role_key


def normalize_text(text):
    """归一化文本，便于判断旧音频是否可复用。"""
    return re.sub(r"\s+", " ", text.strip())


def parse_table_rows():
    """从 Markdown 台本表格中解析当前正式台词。"""
    rows = []
    for raw in SCRIPT_MD.read_text(encoding="utf-8").splitlines():
      line = raw.strip()
      if not line.startswith("|"):
          continue
      if "英文台词/旁白" in line or line.startswith("|---"):
          continue
      cells = [cell.strip() for cell in line.strip("|").split("|")]
      if len(cells) < 8 or not cells[0].isdigit():
          continue
      seq = int(cells[0])
      section = cells[1]
      role = cells[2]
      role_key = ROLE_KEY.get(role)
      if not role_key:
          raise ValueError(f"未配置角色映射: {role}")
      rows.append({
          "seq": seq,
          "section": section,
          "role_display": role,
          "role": role_key,
          "text": cells[3],
          "text_zh": cells[4],
          "learning_point": cells[5],
          "emotion": cells[6],
          "speed": DEFAULT_SPEED_RATIO,
      })

    rows.sort(key=lambda item: item["seq"])
    for expected, item in enumerate(rows, start=1):
        if item["seq"] != expected:
            raise ValueError(f"台本序号不连续: 期望 {expected}, 实际 {item['seq']}")
    return rows


def build_current_scenes(rows):
    """构建 generate_chapter3.py 可读取的数据结构。"""
    scenes = []
    current = None
    for item in rows:
        section_num = item["section"].replace("S", "").lower()
        line_id = f"ch3_s{section_num}_{slug_role(item['role'])}_{item['seq']:03d}"
        line = {
            "id": line_id,
            "role": item["role"],
            "text": item["text"],
            "speed": item["speed"],
            "emotion": item["emotion"],
        }
        if not current or current["scene"] != item["section"]:
            current = {"scene": item["section"], "lines": []}
            scenes.append(current)
        current["lines"].append(line)
    return scenes


def build_tasks(rows):
    """构建给人看的任务清单。"""
    tasks = []
    for item in rows:
        section_num = item["section"].replace("S", "").lower()
        task_id = f"ch3_s{section_num}_{slug_role(item['role'])}_{item['seq']:03d}"
        tasks.append({
            "task_id": task_id,
            "section": item["section"],
            "role": item["role_display"],
            "voice": ROLE_VOICE_LABEL[item["role_display"]],
            "voice_type": VOICE_CONFIG_CH3[item["role"]],
            "speed": item["speed"],
            "emotion": item["emotion"],
            "text_en": item["text"],
            "text_zh": item["text_zh"],
            "learning_point": item["learning_point"],
            "output_wav": str(AUDIO_DIR / f"{task_id}.mp3").replace("\\", "/"),
            "status": "待核对",
        })
    return tasks


def flatten_old_lines(path):
    """读取旧 data/chapter3_lines.json，建立旧音频索引。"""
    if not path.exists():
        return []
    try:
        scenes = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return []
    result = []
    for scene in scenes:
        for line in scene.get("lines", []):
            line_id = line.get("id")
            result.append({
                "id": line_id,
                "role": line.get("role"),
                "text": line.get("text"),
                "speed": line.get("speed", DEFAULT_SPEED_RATIO),
                "path": find_existing_audio(line_id),
            })
    return result


def load_json(path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def find_existing_audio(line_id):
    """优先找新目录，找不到再兼容旧错放目录。"""
    if not line_id:
        return None
    current = AUDIO_DIR / f"{line_id}.mp3"
    if current.exists():
        return current
    legacy = LEGACY_AUDIO_DIR / f"{line_id}.mp3"
    if legacy.exists():
        return legacy
    return current


def collect_reusable_audio(old_lines):
    """收集可复用的旧音频：同角色、同文本、同语速才复用。"""
    reusable = {}
    for item in old_lines:
        path = item.get("path")
        if not item.get("text") or not path or not path.exists():
            continue
        key = (item.get("role"), normalize_text(item["text"]), float(item.get("speed", 1.0)))
        reusable.setdefault(key, path)

    old_manifest = load_json(MANIFEST_FILE) or {}
    if not old_manifest:
        old_manifest = load_json(LEGACY_AUDIO_DIR / "ch3_tts_manifest.json") or {}
    for item in old_manifest.get("manifest", []):
        raw_path = item.get("path") or ""
        path = Path(raw_path) if raw_path else find_existing_audio(item.get("id"))
        role_key = ROLE_KEY.get(item.get("role"), item.get("role"))
        if not item.get("text") or not path.exists():
            continue
        key = (role_key, normalize_text(item["text"]), float(item.get("speed", 1.0)))
        reusable.setdefault(key, path)
    return reusable


def synthesize(text, voice_type, speed):
    """调用火山 V1 HTTP 接口合成单句。"""
    payload = {
        "app": {"appid": APP_ID, "token": ACCESS_TOKEN, "cluster": "volcano_tts"},
        "user": {"uid": "novel_tts_user"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": speed,
            "rate": 24000,
        },
        "request": {"reqid": str(uuid.uuid4()), "text": text, "operation": "query"},
    }
    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, proxies=PROXIES, timeout=60)
        result = resp.json()
    except Exception as exc:
        return None, f"请求异常: {exc}"
    if result.get("code") == 3000 and "data" in result:
        return base64.b64decode(result["data"]), None
    return None, result.get("message", f"code={result.get('code')}")


def backup_existing(path, backup_dir):
    """覆盖前备份旧音频，不丢历史输出。"""
    if not path.exists():
        return None
    backup_dir.mkdir(parents=True, exist_ok=True)
    target = backup_dir / path.name
    if target.exists():
        target = backup_dir / f"{path.stem}_{int(time.time())}{path.suffix}"
    shutil.copy2(path, target)
    return target


def write_task_files(tasks):
    TASK_JSON.parent.mkdir(parents=True, exist_ok=True)
    TASK_JSON.write_text(json.dumps({"chapter": "03", "tasks": tasks}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    lines = [
        "# 第三章TTS任务清单",
        "",
        f"说明：按 2026-07-27 学习台本同步，共 {len(tasks)} 条，默认语速 1.0x。",
        "",
        "| 任务ID | 分节 | 角色 | 音色 | 语速 | 英文文本 | 状态 |",
        "|---|---|---|---|---:|---|---|",
    ]
    for task in tasks:
        lines.append(
            f"| `{task['task_id']}` | {task['section']} | {task['role']} | "
            f"{task['voice_type']} | {task['speed']} | {task['text_en']} | {task['status']} |"
        )
    TASK_MD.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="同步第三章 TTS 文本与音频")
    parser.add_argument("--check-only", action="store_true", help="只核对，不写文件、不生成音频")
    parser.add_argument("--no-generate", action="store_true", help="只写清单，不调用 TTS 接口")
    args = parser.parse_args()

    rows = parse_table_rows()
    scenes = build_current_scenes(rows)
    tasks = build_tasks(rows)
    old_lines = flatten_old_lines(DATA_FILE)
    reusable = collect_reusable_audio(old_lines)

    problems = []
    roles = {task["role"] for task in tasks}
    missing_roles = sorted({ROLE_KEY[role] for role in roles} - set(VOICE_CONFIG_CH3))
    if missing_roles:
        problems.append(f"缺少音色: {', '.join(missing_roles)}")
    if not APP_ID:
        problems.append("缺少 VOLC_APP_ID")
    if not ACCESS_TOKEN:
        problems.append("缺少 VOLC_ACCESS_TOKEN")

    actions = []
    exact_old = {(item["id"], item["role"], normalize_text(item["text"]), float(item.get("speed", 1.0))) for item in old_lines if item.get("id")}
    for task in tasks:
        path = AUDIO_DIR / f"{task['task_id']}.mp3"
        role_key = ROLE_KEY[task["role"]]
        text_key = normalize_text(task["text_en"])
        speed = float(task["speed"])
        exact_key = (task["task_id"], role_key, text_key, speed)
        reuse_key = (role_key, text_key, speed)

        if path.exists() and exact_key in exact_old:
            task["status"] = "已存在-一致"
            task["file_size"] = path.stat().st_size
            actions.append(("skip", task, path, None))
        elif reuse_key in reusable and reusable[reuse_key] != path:
            task["status"] = "可复用旧音频"
            actions.append(("copy", task, path, reusable[reuse_key]))
        else:
            task["status"] = "需生成"
            actions.append(("generate", task, path, None))

    print("=" * 70)
    print("第三章 TTS 核对")
    print(f"最新台词: {len(tasks)} 条 | 分节: {len(scenes)} 个 | 角色: {', '.join(sorted(roles))}")
    print(f"跳过: {sum(1 for a in actions if a[0] == 'skip')} | 复用: {sum(1 for a in actions if a[0] == 'copy')} | 需生成: {sum(1 for a in actions if a[0] == 'generate')}")
    if problems:
        print("[FAIL] 检查问题:")
        for problem in problems:
            print(f"  - {problem}")
        raise SystemExit(1)
    if args.check_only:
        return

    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(json.dumps(scenes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    AUDIO_DIR.mkdir(parents=True, exist_ok=True)
    backup_dir = AUDIO_DIR / "_backup_before_20260727_sync"

    manifest = []
    stats = {"skipped": 0, "copied": 0, "generated": 0, "failed": 0}
    for action, task, path, source in actions:
        path.parent.mkdir(parents=True, exist_ok=True)
        if action == "skip":
            stats["skipped"] += 1
            status = "skipped"
        elif action == "copy":
            backup_existing(path, backup_dir)
            shutil.copy2(source, path)
            task["status"] = "已复用"
            task["file_size"] = path.stat().st_size
            stats["copied"] += 1
            status = "copied"
            print(f"[COPY] {task['task_id']} <= {source.name}")
        else:
            if args.no_generate:
                task["status"] = "待生成"
                stats["failed"] += 1
                status = "pending"
            else:
                backup_existing(path, backup_dir)
                audio, err = synthesize(task["text_en"], task["voice_type"], task["speed"])
                if audio:
                    path.write_bytes(audio)
                    task["status"] = "已生成"
                    task["file_size"] = len(audio)
                    stats["generated"] += 1
                    status = "generated"
                    print(f"[OK] {task['task_id']} ({len(audio)} bytes)")
                    time.sleep(0.3)
                else:
                    task["status"] = "生成失败"
                    task["error"] = err
                    stats["failed"] += 1
                    status = "failed"
                    print(f"[FAIL] {task['task_id']}: {err}")

        manifest.append({
            "id": task["task_id"],
            "role": task["role"],
            "role_key": ROLE_KEY[task["role"]],
            "section": task["section"],
            "text": task["text_en"],
            "voice_type": task["voice_type"],
            "speed": task["speed"],
            "path": str(path).replace("\\", "/"),
            "size": path.stat().st_size if path.exists() else 0,
            "status": status,
        })

    write_task_files(tasks)
    obsolete = []
    current_names = {f"{task['task_id']}.mp3" for task in tasks}
    for old_mp3 in sorted(AUDIO_DIR.glob("*.mp3")):
        if old_mp3.name not in current_names:
            obsolete.append(old_mp3.name)

    MANIFEST_FILE.write_text(json.dumps({
        "chapter": 3,
        "source_script": str(SCRIPT_MD).replace("\\", "/"),
        "total": len(manifest),
        "stats": stats,
        "obsolete_audio_files": obsolete,
        "manifest": manifest,
    }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    print("=" * 70)
    print(f"完成 | 跳过 {stats['skipped']} | 复用 {stats['copied']} | 新生成 {stats['generated']} | 失败 {stats['failed']}")
    print(f"清单: {MANIFEST_FILE}")


if __name__ == "__main__":
    main()
