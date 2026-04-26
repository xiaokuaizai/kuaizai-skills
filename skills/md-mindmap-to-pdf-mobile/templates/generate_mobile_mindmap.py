# -*- coding: utf-8 -*-
"""移动端竖版思维导图 HTML 生成器模板
使用方式：修改 MD_PATH 和 HTML_PATH，然后运行 python generate_mobile_mindmap.py
"""
import re

MD_PATH = r"INPUT_MD_PATH"
HTML_PATH = r"OUTPUT_HTML_PATH"


def parse_md(path):
    """解析 markdown，提取根标题、核心意象/词源提示、分类、单词、词根拆分"""
    with open(path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    root_title = None
    categories = []
    quotes = []
    current = None
    i = 0
    while i < len(lines):
        line = lines[i].rstrip("\n")

        # 一级标题 = 根节点标题，后续读取 > 引用块作为核心意象/词源提示
        if line.startswith("# ") and not line.startswith("## "):
            root_title = line[2:].strip()
            i += 1
            quotes = []
            while i < len(lines):
                qline = lines[i].rstrip("\n")
                if qline.startswith("> "):
                    quotes.append(qline[2:])
                    i += 1
                elif qline.strip() == "" or qline.strip() == "---":
                    i += 1
                else:
                    break
            continue

        # 二级标题 = 分类
        m = re.match(r"##\s+(.+)", line)
        if m:
            title = m.group(1).strip()
            # 过滤尾部非分类区块
            if "关联词网" in title or "相关页面" in title or "相关链接" in title:
                if current:
                    categories.append(current)
                    current = None
                while i + 1 < len(lines) and not re.match(r"##\s+", lines[i + 1]):
                    i += 1
                i += 1
                continue

            if current:
                categories.append(current)
            current = {"title": title, "words": []}
            i += 1
            continue

        # 单词行：- **word** /phonetic/ rest...
        m2 = re.match(r"-\s+\*\*([^*]+)\*\*\s*(.*)", line)
        if m2 and current is not None:
            word_text = m2.group(1).strip()
            rest = m2.group(2).strip()
            full = word_text + (" " + rest if rest else "")
            entry = {"text": full, "split": None}

            # 检查下一行是否是词根拆分
            if i + 1 < len(lines):
                nxt = lines[i + 1].rstrip("\n")
                if (nxt.strip().startswith("→") or "→" in nxt) and lines[i + 1].startswith(" "):
                    # 清理拆分文本前面的 "- " 等脏前缀
                    split_text = nxt.strip()
                    split_text = re.sub(r"^-\s*", "", split_text)
                    entry["split"] = split_text
                    i += 1
            current["words"].append(entry)
            i += 1
            continue

        i += 1

    if current:
        categories.append(current)
    info_text = "\n".join(quotes) if quotes else ""
    return root_title, info_text, categories


def fmt_word(text):
    """把 'return /rɪˈtɜːn/ v.&n. 回来...' 格式化成 HTML 卡片"""
    m = re.search(r'(/[^/]+/)', text)
    if m:
        phonetic = m.group(1)
        parts = text.split(phonetic, 1)
        word = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        # 单词和音标放在 nowrap 容器里，避免被不自然断开
        html = (
            f'<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px;margin-bottom:4px;">'
            f'<strong style="font-size:18px;white-space:nowrap;">{word}</strong>'
            f'<span style="color:#555;font-size:14px;white-space:nowrap;">{phonetic}</span>'
            f'</div>'
        )
        if rest:
            html += f'<div style="color:#444;line-height:1.5;">{rest}</div>'
        return html
    return text


def build_html(root_title, info_text, categories):
    # 拆分根标题为主标题和副标题
    root_main = root_title or "词根"
    root_sub = ""
    if " " in root_main:
        parts = root_main.split(" ", 1)
        root_main = parts[0]
        root_sub = parts[1]

    info_html_block = ('<div class="root-info">' + info_text.replace("\n", "<br>") + '</div>') if info_text else ""

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{root_title or '思维导图'}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    margin: 0 auto;
    padding: 20px 16px;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    background: #f0f2f5;
    max-width: 430px;
}}
.container {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 28px;
    padding-bottom: 40px;
}}
.root {{
    background: #9e9e9e;
    color: #fff;
    padding: 22px 24px;
    border-radius: 16px;
    font-size: 24px;
    font-weight: bold;
    text-align: center;
    line-height: 1.5;
    box-shadow: 0 6px 16px rgba(0,0,0,0.18);
    width: 100%;
}}
.root small {{ font-size: 16px; font-weight: normal; display: block; margin-top: 4px; }}
.root-info {{
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.3);
    font-size: 14px;
    font-weight: normal;
    line-height: 1.6;
    text-align: left;
    color: rgba(255,255,255,0.95);
}}
.branches {{
    display: flex;
    flex-direction: column;
    gap: 28px;
    width: 100%;
}}
.branch {{
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 16px;
    width: 100%;
}}
.cat-node {{
    background: #ffc107;
    color: #333;
    padding: 12px 22px;
    border-radius: 12px;
    font-size: 16px;
    font-weight: bold;
    text-align: center;
    box-shadow: 0 4px 12px rgba(0,0,0,0.14);
    width: auto;
    min-width: 160px;
}}
.word-groups {{
    display: flex;
    flex-direction: column;
    gap: 12px;
    width: 100%;
}}
.word-group {{
    width: 100%;
}}
.word-card {{
    background: #fff3cd;
    color: #333;
    padding: 14px 16px;
    border-radius: 12px;
    font-size: 14px;
    line-height: 1.6;
    border: 1px solid #ffe082;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    width: 100%;
}}
/* 拆分内容内嵌在单词卡片中，使用蓝色底色区分 */
.split-inline {{
    margin-top: 10px;
    padding: 8px 12px;
    background: #b3e5fc;
    color: #01579b;
    border-radius: 8px;
    font-size: 13px;
    line-height: 1.5;
    border: 1px solid #81d4fa;
}}
</style>
</head>
<body>
<div class="container">
<div class="root">{root_main}<small>{root_sub}</small>{info_html_block}</div>
<div class="branches">'''

    for i, cat in enumerate(categories):
        html += f'<div class="branch">\n'
        html += f'<div class="cat-node">{cat["title"]}</div>\n'
        html += f'<div class="word-groups">\n'
        for j, w in enumerate(cat["words"]):
            html += f'<div class="word-group">\n'
            split_html = f'<div class="split-inline">{w["split"]}</div>' if w["split"] else ""
            html += f'<div class="word-card">{fmt_word(w["text"])}{split_html}</div>\n'
            html += '</div>\n'
        html += '</div>\n</div>\n'

    html += '''</div>
</div>
</body>
</html>'''
    return html


def generate():
    root_title, info_text, categories = parse_md(MD_PATH)
    html = build_html(root_title, info_text, categories)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成移动端 HTML: {HTML_PATH}")


if __name__ == "__main__":
    generate()
