# 根据 TTS音色总表.md 生成角色样本音频
# 为每个角色生成主选 + 备选音色样本，样本文本来自剧本台词
import argparse
import base64
import json
import os
import re
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

# 让脚本能找到 volc-tts 的 src 模块
SCRIPT_DIR = Path(__file__).resolve().parent
VOLC_TTS_DIR = SCRIPT_DIR / "volc-tts"
sys.path.insert(0, str(VOLC_TTS_DIR))

import requests
from src.config import ACCESS_TOKEN, API_URL, APP_ID, DEFAULT_SPEED_RATIO, PROXIES

HEADERS = {
    "Authorization": f"Bearer;{ACCESS_TOKEN}",
    "Content-Type": "application/json"
}

REFERENCE_MIN_SECONDS = 2.0
REFERENCE_MAX_SECONDS = 15.0


def parse_markdown_table(lines):
    """解析 Markdown 表格，返回表头和数据行。"""
    # 找到表格开始和结束
    start = None
    end = None
    for i, line in enumerate(lines):
        if line.strip().startswith("|") and "---" in line:
            start = i - 1  # 表头行
            continue
        if start is not None and not line.strip().startswith("|"):
            end = i
            break
    if start is None:
        return [], []
    if end is None:
        end = len(lines)

    header_line = lines[start].strip()
    raw_headers = [h.strip() for h in header_line.split("|")[1:-1]]

    # 给重复的表头加序号，例如 voice_type, voice_type_1, voice_type_2
    headers = []
    counts = {}
    for h in raw_headers:
        if h in counts:
            counts[h] += 1
            headers.append(f"{h}_{counts[h]}")
        else:
            counts[h] = 0
            headers.append(h)

    rows = []
    for line in lines[start + 2:end]:
        if not line.strip().startswith("|"):
            continue
        cells = [c.strip() for c in line.split("|")[1:-1]]
        if len(cells) != len(headers):
            continue
        rows.append(dict(zip(headers, cells)))

    return headers, rows


def clean(v):
    """去掉 Markdown 反引号和首尾空白，避免 `voice_type` 这种格式传给 API。"""
    if not v:
        return ""
    return v.strip().strip("`").strip()


def read_voice_table(table_path):
    """读取音色总表，解析出角色音色配置和样本文本。"""
    text = Path(table_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    # 找到角色与音色匹配表格
    role_section_idx = None
    sample_section_idx = None
    for i, line in enumerate(lines):
        if "## 角色与音色匹配" in line:
            role_section_idx = i
        elif "## 样本文本" in line:
            sample_section_idx = i

    if role_section_idx is None:
        raise ValueError("未找到 '## 角色与音色匹配' 表格")

    role_headers, role_rows = parse_markdown_table(lines[role_section_idx:])
    sample_headers, sample_rows = [], []
    if sample_section_idx is not None:
        sample_headers, sample_rows = parse_markdown_table(lines[sample_section_idx:])

    # 样本文本也清理首尾引号/反引号
    sample_texts = {clean(row["role_key"]): row["样本文本"].strip().strip('"').strip("'").strip("`").strip()
                    for row in sample_rows if "role_key" in row and "样本文本" in row}

    roles = []
    for row in role_rows:
        if "role_key" not in row or not row["role_key"]:
            continue
        role_key = clean(row["role_key"])
        voices = []
        if "voice_type" in row and row["voice_type"]:
            voices.append({"label": "primary", "voice_type": clean(row["voice_type"])})
        # 备选列可能有多个
        for i in range(1, 4):
            vt_col = f"voice_type_{i}"
            if vt_col in row and row[vt_col]:
                voices.append({"label": f"alt_{i:02d}", "voice_type": clean(row[vt_col])})

        roles.append({
            "role_key": role_key,
            "display": row.get("角色", role_key),
            "sample_text": sample_texts.get(role_key, ""),
            "speed": clean(row.get("语速", "1.0")) or "1.0",
            "voices": voices
        })

    return roles


def synthesize(text, voice_type, speed_ratio=1.0):
    """调用火山引擎 V1 HTTP 接口合成语音。"""
    payload = {
        "app": {
            "appid": APP_ID,
            "token": ACCESS_TOKEN,
            "cluster": "volcano_tts"
        },
        "user": {"uid": "novel_tts_user"},
        "audio": {
            "voice_type": voice_type,
            "encoding": "mp3",
            "speed_ratio": speed_ratio,
            "rate": 24000
        },
        "request": {
            "reqid": str(uuid.uuid4()),
            "text": text,
            "operation": "query"
        }
    }

    try:
        resp = requests.post(API_URL, headers=HEADERS, json=payload, proxies=PROXIES, timeout=60)
        result = resp.json()
    except Exception as e:
        return None, f"请求异常: {e}"

    if result.get("code") == 3000 and "data" in result:
        return base64.b64decode(result["data"]), None
    else:
        # 打印完整响便于排查（resource not granted 等授权类错误）
        msg = result.get("message") or f"code={result.get('code')}"
        full = json.dumps(result, ensure_ascii=False)[:200]
        return None, f"{msg} | full={full}"


def archive_existing(output_path):
    """生成新样本前归档同名旧文件，避免直接覆盖。"""
    if not output_path.exists():
        return True, ""

    archive_script = (
        SCRIPT_DIR.parent.parent
        / "minimax-story-package"
        / "scripts"
        / "archive_local_version.py"
    )
    if not archive_script.exists():
        return False, f"缺少归档脚本: {archive_script}"

    result = subprocess.run(
        [
            sys.executable,
            str(archive_script),
            "--file",
            str(output_path),
            "--reason",
            "重新生成 TTS 音色试听样本",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "未知归档错误"
        return False, message
    return True, result.stdout.strip()


def probe_audio(audio_path):
    """用 ffprobe 读取真实时长，确认生成文件可被音频工具解析。"""
    if audio_path.suffix.lower() not in {".mp3", ".wav"}:
        return None, f"不支持的音频格式: {audio_path.suffix or '<无扩展名>'}"

    try:
        result = subprocess.run(
            [
                "ffprobe",
                "-v",
                "error",
                "-show_entries",
                "format=duration",
                "-of",
                "default=noprint_wrappers=1:nokey=1",
                str(audio_path),
            ],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=30,
        )
    except FileNotFoundError:
        return None, "未找到 ffprobe，请先安装或配置 FFmpeg"
    except subprocess.TimeoutExpired:
        return None, "ffprobe 读取音频超时"

    if result.returncode != 0:
        return None, result.stderr.strip() or "ffprobe 无法解析音频"

    try:
        duration = round(float(result.stdout.strip()), 3)
    except ValueError:
        return None, "ffprobe 返回了无效时长"
    if duration <= 0:
        return None, "音频时长必须大于 0 秒"
    return duration, ""


def update_table_samples(table_path, results):
    """把样本文件路径回填到音色总表的样本文件列。"""
    text = Path(table_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    # 找到角色与音色匹配表格
    section_idx = None
    for i, line in enumerate(lines):
        if "## 角色与音色匹配" in line:
            section_idx = i
            break

    if section_idx is None:
        return

    headers, _ = parse_markdown_table(lines[section_idx:])
    if "样本文件" not in headers:
        return

    sample_col = headers.index("样本文件")

    # 更新表格行
    new_lines = []
    in_table = False
    for i, line in enumerate(lines):
        if i == section_idx:
            in_table = True
        if in_table and i > section_idx and line.strip() and not line.strip().startswith("|"):
            in_table = False

        if in_table and line.strip().startswith("|") and "---" not in line and i > section_idx + 1:
            cells = [c.strip() for c in line.split("|")[1:-1]]
            if len(cells) == len(headers):
                role_key = cells[headers.index("role_key")]
                if role_key in results:
                    sample_files = results[role_key]
                    cells[sample_col] = " <br> ".join(sample_files)
                    line = "| " + " | ".join(cells) + " |"

        new_lines.append(line)

    Path(table_path).write_text("\n".join(new_lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description="根据 TTS音色总表生成角色样本音频")
    parser.add_argument("table", help="TTS音色总表.md 路径")
    parser.add_argument("--result", help="样本生成结果 JSON，默认写到音色表同目录")
    parser.add_argument("--primary-only", action="store_true", help="只生成主选音色样本，跳过备选")
    parser.add_argument("--output-dir", help="样本输出目录，默认写到音色表同目录的 samples/ 子目录")
    args = parser.parse_args()

    table_path = Path(args.table).resolve()
    if not table_path.exists():
        print(f"错误：文件不存在 {table_path}")
        sys.exit(1)

    # 支持自定义输出目录（例如直接写到资产/TTS/samples）
    output_dir = Path(args.output_dir).resolve() if args.output_dir else (table_path.parent / "samples")
    output_dir.mkdir(parents=True, exist_ok=True)

    roles = read_voice_table(table_path)
    if args.primary_only:
        # 只保留 primary 那一条 voice，避免为备选音色付费
        for role in roles:
            role["voices"] = [v for v in role["voices"] if v["label"] == "primary"]
    if not roles:
        print("未解析到任何角色，请检查表格格式。")
        sys.exit(1)

    print(f"输出目录: {output_dir}")
    print(f"共 {len(roles)} 个角色需要生成样本\n")

    all_results = {}
    sample_results = []
    for role in roles:
        role_key = role["role_key"]
        display = role["display"]
        text = role["sample_text"]
        speed = float(role["speed"]) if role["speed"] else 1.0

        if not text:
            print(f"[{role_key}] 没有样本文本，跳过")
            continue

        print(f"\n【{display} ({role_key})】")
        print(f"  文本: {text[:80]}{'...' if len(text) > 80 else ''}")

        role_files = []
        for voice in role["voices"]:
            voice_type = voice["voice_type"]
            label = voice["label"]
            filename = f"{role_key}_{label}.mp3"
            output_path = output_dir / filename

            print(f"  生成 [{label}] {voice_type} ...", end=" ")
            archived, archive_message = archive_existing(output_path)
            if not archived:
                print(f"FAIL: 旧版归档失败: {archive_message}")
                sample_results.append({
                    "role_key": role_key,
                    "role": display,
                    "variant": label,
                    "voice_type": voice_type,
                    "local_path": str(output_path),
                    "success": False,
                    "validation_passed": False,
                    "reference_eligible": False,
                    "error": f"旧版归档失败: {archive_message}",
                })
                continue

            audio, err = synthesize(text, voice_type, speed)
            if audio:
                output_path.write_bytes(audio)
                duration, validation_error = probe_audio(output_path)
                validation_passed = duration is not None
                reference_eligible = bool(
                    validation_passed
                    and REFERENCE_MIN_SECONDS <= duration <= REFERENCE_MAX_SECONDS
                )
                if validation_passed:
                    eligibility = "可作为参考音频" if reference_eligible else "仅可试听"
                    print(f"OK ({duration:.2f}s, {eligibility}) -> {output_path.name}")
                    # 输出目录可能在音色表外部（例如资产/TTS/samples），此时相对路径会失败，退回绝对路径
                    try:
                        rel_path = str(output_path.relative_to(table_path.parent)).replace("\\", "/")
                    except ValueError:
                        rel_path = str(output_path.resolve()).replace("\\", "/")
                    role_files.append(rel_path)
                else:
                    print(f"FAIL: 音频校验失败: {validation_error}")

                sample_results.append({
                    "role_key": role_key,
                    "role": display,
                    "variant": label,
                    "voice_type": voice_type,
                    "sample_text": text,
                    "local_path": str(output_path.resolve()),
                    "relative_path": (str(output_path.relative_to(table_path.parent)).replace("\\", "/")
                                       if output_path.is_relative_to(table_path.parent)
                                       else str(output_path.resolve()).replace("\\", "/")),
                    "format": output_path.suffix.lower().lstrip("."),
                    "duration_seconds": duration,
                    "success": True,
                    "validation_passed": validation_passed,
                    "reference_eligible": reference_eligible,
                    "error": validation_error,
                })
            else:
                print(f"FAIL: {err}")
                sample_results.append({
                    "role_key": role_key,
                    "role": display,
                    "variant": label,
                    "voice_type": voice_type,
                    "local_path": str(output_path),
                    "success": False,
                    "validation_passed": False,
                    "reference_eligible": False,
                    "error": err,
                })

            time.sleep(0.3)

        if role_files:
            all_results[role_key] = role_files

    # 回填样本路径
    update_table_samples(table_path, all_results)

    # 结果清单由 TTS skill 维护，供人工选样脚本读取。
    result_path = Path(args.result).resolve() if args.result else table_path.parent / "sample_generation_result.json"
    result_data = {
        "manifest_type": "tts_sample_generation_result",
        "generated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "voice_table": str(table_path),
        "samples": sample_results,
    }
    result_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.write_text(json.dumps(result_data, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + "=" * 60)
    print("生成完成")
    print(f"输出目录: {output_dir}")
    print(f"成功角色: {len(all_results)}/{len(roles)}")
    print(f"校验结果: {result_path}")

    failed_count = sum(1 for item in sample_results if not item.get("validation_passed"))
    if failed_count:
        print(f"失败或无法解析样本: {failed_count}")
        sys.exit(1)


if __name__ == "__main__":
    main()
