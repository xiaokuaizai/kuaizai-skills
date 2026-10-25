# 从剧本生成 TTS音色总表.md
# 识别旁白和对话角色，自动推荐音色并挑选样本文本
import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path

# 内置音色推荐库
VOICE_RECOMMENDATIONS = {
    "en_teen_boy": {
        "primary": ("Lucas", "zh_male_M100_conversation_wvae_bigtts"),
        "alternatives": [
            ("Brayan", "zh_male_shaonianzixin_moon_bigtts"),
            ("Alvin", "zh_male_wennuanahu_moon_bigtts"),
        ]
    },
    "en_teen_girl": {
        "primary": ("Dacey", "en_female_dacey_uranus_bigtts"),
        "alternatives": [
            ("Shiny", "zh_female_cancan_mars_bigtts"),
            ("Stokie", "en_female_stokie_uranus_bigtts"),
        ]
    },
    "en_adult_male": {
        "primary": ("Sylus", "en_male_sylus_emo_v2_mars_bigtts"),
        "alternatives": [
            ("Bruce", "en_male_bruce_moon_bigtts"),
            ("Michael", "en_male_michael_moon_bigtts"),
        ]
    },
    "en_adult_female": {
        "primary": ("Skye", "en_female_skye_emo_v2_mars_bigtts"),
        "alternatives": [
            ("Nadia", "en_female_nadia_tips_emo_v2_mars_bigtts"),
            ("Dacey", "en_female_dacey_uranus_bigtts"),
        ]
    },
    "en_narrator_male": {
        "primary": ("Tim", "en_male_tim_uranus_bigtts"),
        "alternatives": [
            ("Corey", "en_male_corey_emo_v2_mars_bigtts"),
            ("Michael", "en_male_michael_moon_bigtts"),
        ]
    },
    "zh_teen_boy": {
        "primary": ("少年梓辛/Brayan", "zh_male_shaonianzixin_moon_bigtts"),
        "alternatives": [
            ("Lucas", "zh_male_M100_conversation_wvae_bigtts"),
            ("温暖阿虎/Alvin", "zh_male_wennuanahu_moon_bigtts"),
        ]
    },
    "zh_teen_girl": {
        "primary": ("知性灿灿", "zh_female_cancan_mars_bigtts"),
        "alternatives": [
            ("邻家女孩", "zh_female_linjianvhai_uranus_bigtts"),
            ("萌丫头/Cutey", "zh_female_mengyatou_uranus_bigtts"),
        ]
    },
    "zh_adult_male": {
        "primary": ("云舟", "zh_male_m191_uranus_bigtts"),
        "alternatives": [
            ("儒雅逸辰", "zh_male_ruyayichen_uranus_bigtts"),
            ("刘飞", "zh_male_liufei_uranus_bigtts"),
        ]
    },
    "zh_adult_female": {
        "primary": ("温柔妈妈", "zh_female_wenroumama_uranus_bigtts"),
        "alternatives": [
            ("魅力苏菲", "zh_female_sophie_uranus_bigtts"),
            ("甜美小源", "zh_female_tianmeixiaoyuan_uranus_bigtts"),
        ]
    },
    "zh_narrator_male": {
        "primary": ("解说小明", "zh_male_jieshuoxiaoming_uranus_bigtts"),
        "alternatives": [
            ("霸气青叔", "zh_male_baqiqingshu_uranus_bigtts"),
            ("悬疑解说", "zh_male_xuanyijieshuo_uranus_bigtts"),
        ]
    },
}

# 常见英文名性别映射（简化版）
MALE_NAMES = {"jiang", "che", "father", "teacher", "li", "director", "chen", "staff", "boy", "narrator", "tim", "michael", "bruce", "sylus", "glen", "corey", "lucas", "alvin"}
FEMALE_NAMES = {"an", "qi", "mother", "girl", "skye", "nadia", "dacey", "stokie", "shiny"}


def is_english_text(text):
    """判断文本是否为英文剧本（按英文字母比例）。"""
    letters = len(re.findall(r"[a-zA-Z]", text))
    total = len(re.sub(r"\s", "", text))
    if total == 0:
        return True
    return letters / total > 0.5


def parse_script(script_path):
    """解析剧本，返回旁白列表和对话列表。"""
    text = Path(script_path).read_text(encoding="utf-8")
    lines = text.splitlines()

    narrations = []
    dialogues = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 旁白标记
        if line.startswith("【Narration】"):
            narrations.append(line.replace("【Narration】", "").strip())
            continue

        # 对话：以双引号开头和结尾的段落
        # 先处理一行一句的简单情况
        matches = re.findall(r'"([^"]+)"', line)
        for m in matches:
            # 清理嵌入引语时产生的末尾逗号
            cleaned = m.rstrip(",").strip()
            # 推断角色：找引号后面 said/asked/replied/called 前面的词
            # 例如："Yes." Jiang Che said.
            role = infer_role_from_line(line, m)
            dialogues.append({"text": cleaned, "role": role})

    return narrations, dialogues


def infer_role_from_line(line, quote_text):
    """从一行文本中推断说话角色。"""
    # 模式："..." Role said/asked/replied/called/add...
    pattern = r'"' + re.escape(quote_text) + r'"\s*([A-Za-z\s]+?)(?:\s+said|\s+asked|\s+replied|\s+called|\s+added|\s+answered|\s+shouted|\s+whispered|\s+laughed)'
    m = re.search(pattern, line, re.IGNORECASE)
    if m:
        role = m.group(1).strip()
        # 清理可能的多余词，例如 "Jiang Che pulled..." 里的动作
        role = re.split(r'\s+(?:pulled|looked|waved|pointed|turned|opened|took|smiled|nodded)', role, flags=re.IGNORECASE)[0]
        role = role.strip()
        # 去掉孤立的冠词 a/the（an 太可能是名字的一部分，如 An Qi，不处理）
        role = re.sub(r'^(a|the)\s+', '', role, flags=re.IGNORECASE)
        if role.lower() in EXCLUDED_ROLES:
            return "unknown"
        return role

    # 中文模式："..." 角色说/问/答/喊道
    pattern_zh = r'"' + re.escape(quote_text) + r'"\s*([^"\s，。！？]+?)(?:说|问道|回答|喊道|笑着|点点头|问)'
    m = re.search(pattern_zh, line)
    if m:
        role = m.group(1).strip()
        role = re.sub(r'^(一个|一位|一名|那个|这个)\s*', '', role)
        if role.lower() in EXCLUDED_ROLES:
            return "unknown"
        return role

    return "unknown"


# 需要排除的代词和无效角色名
EXCLUDED_ROLES = {"he", "she", "they", "it", "we", "you", "i", "him", "her", "them", "us", "me", "someone", "somebody", "everyone", "everybody", "nobody", "anyone"}


def normalize_role_key(role_name):
    """把角色名转成 role_key（小写、下划线连接）。"""
    key = role_name.lower()
    key = re.sub(r"[^a-z0-9一-鿿]+", "_", key)
    key = key.strip("_")
    return key or "unknown"


def classify_role(role_name, role_texts, is_english):
    """推断角色类型。"""
    key = role_name.lower()

    # 旁白
    if key in {"narrator", "narration", "旁白"}:
        return "en_narrator_male" if is_english else "zh_narrator_male"

    # 年龄判断
    is_child = any(w in key for w in ["boy", "girl", "kid", "child", "男孩", "女孩", "小孩"])
    is_teen = any(w in key for w in ["teen", "student", "少年", "少女", "jiang", "qi", "che"])
    is_adult = any(w in key for w in ["father", "mother", "teacher", "director", "doctor", "staff", "父亲", "母亲", "老师", "总监", "医生", "人员"])

    # 性别判断
    is_male = any(w in key for w in MALE_NAMES)
    is_female = any(w in key for w in FEMALE_NAMES)

    # 从文本中的代词辅助判断
    all_text = " ".join(role_texts).lower()
    if not is_male and not is_female:
        if re.search(r"\b(he|his|him)\b", all_text):
            is_male = True
        elif re.search(r"\b(she|her|hers)\b", all_text):
            is_female = True

    # 组合类型
    if is_english:
        if is_child:
            return "en_teen_boy" if is_male else "en_teen_girl"
        if is_teen:
            return "en_teen_boy" if is_male else "en_teen_girl"
        if is_adult or True:  # 默认成年
            return "en_adult_male" if is_male else "en_adult_female"
    else:
        if is_child:
            return "zh_teen_boy" if is_male else "zh_teen_girl"
        if is_teen:
            return "zh_teen_boy" if is_male else "zh_teen_girl"
        return "zh_adult_male" if is_male else "zh_adult_female"


def estimate_duration(text, is_english):
    """估算 TTS 试听样本文本的时长，不作为正式台词时长。"""
    if is_english:
        words = len(re.findall(r"[a-zA-Z]+", text))
        return words * 0.4
    else:
        chars = len(re.findall(r"[一-鿿]", text))
        return chars * 0.22


def select_sample_text(texts, is_english, speed=1.0, target_min=6.0, target_max=8.0):
    """为角色选择 7-8 秒以内的样本文本（已考虑语速和音色差异余量）。"""
    # 语速慢则实际时长更长；不同音色朗读速度有差异，预留 15% 安全余量
    effective_max = target_max * speed * 0.85
    effective_min = target_min * speed

    scored = []
    for t in texts:
        d = estimate_duration(t, is_english)
        if effective_min <= d <= effective_max:
            scored.append((t, d, abs(d - 7.0 * speed)))

    if scored:
        scored.sort(key=lambda x: x[2])
        return scored[0][0]

    under_max = [(t, estimate_duration(t, is_english)) for t in texts if estimate_duration(t, is_english) <= effective_max]
    if under_max:
        under_max.sort(key=lambda x: x[1], reverse=True)
        return under_max[0][0]

    shortest = min(texts, key=lambda t: estimate_duration(t, is_english))
    return truncate_text(shortest, is_english, effective_max)


def truncate_text(text, is_english, max_seconds=8.0):
    """在语义断点截断文本，使其不超过 max_seconds。"""
    if estimate_duration(text, is_english) <= max_seconds:
        return text

    if is_english:
        # 按句子截断
        sentences = re.split(r'(?<=[.!?])\s+', text)
        result = ""
        for s in sentences:
            if estimate_duration(result + " " + s if result else s, is_english) <= max_seconds:
                result = (result + " " + s).strip() if result else s
            else:
                break
        return result or text
    else:
        # 中文按逗号/句号截断
        parts = re.split(r'([，。！？；])', text)
        result = ""
        for i in range(0, len(parts), 2):
            chunk = parts[i]
            punct = parts[i + 1] if i + 1 < len(parts) else ""
            candidate = result + chunk + punct
            if estimate_duration(candidate, is_english) <= max_seconds:
                result = candidate
            else:
                break
        return result or text


def generate_table(roles, script_path, assets_dir, workspace_root, skill_root, is_english):
    """生成 TTS音色总表.md 内容。"""
    scene_name = Path(script_path).parent.name
    table_path = Path(assets_dir) / scene_name / "TTS" / "TTS音色总表.md"

    # 如果有工作空间根目录，用它作为相对路径基准；否则用资产目录
    rel_base = Path(workspace_root) if workspace_root else Path(assets_dir)
    rel_script = os.path.relpath(script_path, rel_base).replace("\\", "/")
    rel_table = os.path.relpath(table_path, rel_base).replace("\\", "/")

    # skill 根目录的相对表示（用于使用说明中的命令）
    if workspace_root and Path(skill_root).is_relative_to(Path(workspace_root)):
        rel_skill = os.path.relpath(skill_root, workspace_root).replace("\\", "/")
    else:
        rel_skill = str(skill_root)

    lines = [
        "# TTS音色总表",
        "",
        "> 本文档记录本场次/本作品的 TTS 音色选择方案。",
        "> 由 `minimax-storyboard-tts` skill 自动生成草案，用户确认后用于样本生成。",
        "",
        "## 源文件",
        "",
        f"- **剧本**: `{rel_script}`",
        f"- **资产目录**: `{assets_dir}`",
        f"- **生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
        "",
        "## 角色与音色匹配",
        "",
        "| 角色 | role_key | 角色类型 | 英文表演方向 | 语速 | 主选音色 | voice_type | 备选音色1 | voice_type | 备选音色2 | voice_type | 匹配理由 | 样本文件 |",
        "|---|---|---|---|---:|---|---|---|---|---|---|---|---|",
    ]

    sample_lines = [
        "",
        "## 样本文本",
        "",
        "| role_key | 样本文本 | 参考样本预估时长 |",
        "|---|---|---:|",
        "",
        "> 样本文本只用于试听音色，不承担 Minimax H3 的正式对白或旁白内容。",
    ]

    for role in roles:
        rec = VOICE_RECOMMENDATIONS.get(role["role_type"], VOICE_RECOMMENDATIONS["en_narrator_male"])
        primary_name, primary_vt = rec["primary"]
        alt1_name, alt1_vt = rec["alternatives"][0] if len(rec["alternatives"]) > 0 else ("", "")
        alt2_name, alt2_vt = rec["alternatives"][1] if len(rec["alternatives"]) > 1 else ("", "")

        sample_text = role["sample_text"]
        duration = estimate_duration(sample_text, is_english)
        speed = "0.9" if role["role_type"].startswith("en_") and "narrator" in role["role_type"] else "1.0"

        direction = role.get("direction", "")
        reason = f"按{role['role_type']}类型自动推荐"

        lines.append(
            f"| {role['display']} | {role['role_key']} | {role['role_type']} | {direction} | {speed} | {primary_name} | {primary_vt} | {alt1_name} | {alt1_vt} | {alt2_name} | {alt2_vt} | {reason} |  |"
        )

        sample_lines.append(f"| {role['role_key']} | {sample_text} | {duration:.1f}s |")

    lines.extend(sample_lines)
    lines.extend([
        "",
        "## 生成记录",
        "",
        "| 时间 | 操作 | 输出目录 | 状态 |",
        "|---|---|---|---|",
        "",
        "---",
        "",
        "## 使用说明",
        "",
        "1. 确认或修改上表中的音色选择。",
        "2. 确认后运行样本生成命令：",
        "   ```bash",
        f"   python \"{rel_skill}/tools/generate_samples_from_table.py\" \"{rel_table}\"",
        "   ```",
        "3. 生成完成后，样本文件路径会自动回填到「样本文件」列。",
        "4. 人工确认的样本可上传为 `tts_reference`；样本文本不承担 Minimax H3 的正式对白或旁白内容。",
        "",
    ])

    return table_path, "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="从剧本生成 TTS音色总表")
    parser.add_argument("--script", required=True, help="剧本文件路径")
    parser.add_argument("--assets", required=True, help="资产目录路径")
    parser.add_argument("--workspace", help="工作空间根目录（用于计算相对路径，可选）")
    parser.add_argument("--skill-root", default=str(Path(__file__).resolve().parents[1]),
                        help="skill 根目录（用于生成使用说明中的命令，可选）")
    args = parser.parse_args()

    script_path = Path(args.script).resolve()
    assets_dir = Path(args.assets).resolve()
    workspace_root = Path(args.workspace).resolve() if args.workspace else None
    skill_root = Path(args.skill_root).resolve()

    if not script_path.exists():
        print(f"错误：剧本不存在 {script_path}")
        sys.exit(1)

    assets_dir.mkdir(parents=True, exist_ok=True)

    print(f"读取剧本: {script_path}")
    narrations, dialogues = parse_script(script_path)
    print(f"  旁白段落: {len(narrations)}")
    print(f"  对话句数: {len(dialogues)}")

    # 判断语言
    sample_text = "\n".join(narrations[:3]) + "\n" + "\n".join([d["text"] for d in dialogues[:5]])
    is_english = is_english_text(sample_text)
    print(f"  判定语言: {'英文' if is_english else '中文'}")

    # 聚合角色
    role_texts = {}
    for d in dialogues:
        role = d["role"]
        if role == "unknown":
            continue
        role_texts.setdefault(role, []).append(d["text"])

    # 旁白角色
    if narrations:
        role_texts["Narrator"] = narrations

    # 生成角色列表
    roles = []
    for role_name, texts in role_texts.items():
        role_key = normalize_role_key(role_name)
        role_type = classify_role(role_name, texts, is_english)
        speed = 0.9 if role_type.startswith("en_") and "narrator" in role_type else 1.0
        sample_text = select_sample_text(texts, is_english, speed=speed)
        roles.append({
            "display": role_name,
            "role_key": role_key,
            "role_type": role_type,
            "sample_text": sample_text,
            "direction": "",
        })

    if not roles:
        print("未识别到任何角色，请检查剧本格式。")
        sys.exit(1)

    # 生成表格
    table_path, content = generate_table(roles, script_path, assets_dir, workspace_root, skill_root, is_english)
    table_path.parent.mkdir(parents=True, exist_ok=True)
    table_path.write_text(content, encoding="utf-8")

    print(f"\n已生成音色总表: {table_path}")
    rel_display = os.path.relpath(table_path, workspace_root if workspace_root else assets_dir).replace(chr(92), '/')
    print(f"相对路径: {rel_display}")
    print(f"\n识别角色:")
    for r in roles:
        print(f"  - {r['display']} ({r['role_key']}) -> {r['role_type']}")


if __name__ == "__main__":
    main()
