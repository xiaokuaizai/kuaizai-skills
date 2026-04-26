# -*- coding: utf-8 -*-
"""Markdown 树状思维导图 HTML 生成器模板
使用方式：修改 MD_PATH 和 HTML_PATH，然后运行 python generate_mindmap.py
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
                    entry["split"] = nxt.strip()
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
        html = f'<strong style="font-size:14px;">{word}</strong> <span style="color:#555;">{phonetic}</span>'
        if rest:
            html += f'<br><span style="color:#444;">{rest}</span>'
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
<title>{root_title or '思维导图'}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    margin: 0;
    padding: 24px;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    background: #f0f2f5;
}}
.page {{
    position: relative;
    display: inline-block;
    padding-right: 40px;
}}
.container {{
    display: flex;
    align-items: flex-start;
    gap: 40px;
    position: relative;
    z-index: 1;
    padding-bottom: 24px;
}}
.root {{
    background: #9e9e9e;
    color: #fff;
    padding: 24px 28px;
    border-radius: 16px;
    font-size: 24px;
    font-weight: bold;
    text-align: center;
    line-height: 1.5;
    box-shadow: 0 6px 16px rgba(0,0,0,0.18);
    flex-shrink: 0;
    margin-top: 32px;
}}
.root small {{ font-size: 16px; font-weight: normal; display: block; margin-top: 6px; }}
.root-info {{
    margin-top: 10px;
    padding-top: 8px;
    border-top: 1px solid rgba(255,255,255,0.3);
    font-size: 13px;
    font-weight: normal;
    line-height: 1.5;
    text-align: left;
    color: rgba(255,255,255,0.95);
}}
.branches {{
    display: flex;
    flex-direction: column;
    gap: 28px;
}}
.branch {{
    display: flex;
    align-items: flex-start;
    gap: 30px;
}}
.cat-node {{
    background: #ffc107;
    color: #333;
    padding: 14px 20px;
    border-radius: 12px;
    font-size: 17px;
    font-weight: bold;
    white-space: nowrap;
    box-shadow: 0 4px 12px rgba(0,0,0,0.14);
    flex-shrink: 0;
    margin-top: 8px;
}}
.word-groups {{
    display: flex;
    flex-direction: column;
    gap: 12px;
}}
.word-groups.dense {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 10px;
    align-items: start;
    padding-left: 20px;
}}
.word-groups.dense-4 {{
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 10px;
    align-items: start;
    padding-left: 20px;
}}
.word-groups.dense-5 {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    align-items: start;
    padding-left: 20px;
}}
.word-group {{
    display: flex;
    align-items: flex-start;
    gap: 24px;
}}
.word-groups.dense .word-group,
.word-groups.dense-4 .word-group,
.word-groups.dense-5 .word-group {{
    flex-direction: column;
    gap: 6px;
}}
.word-card {{
    background: #fff3cd;
    color: #333;
    padding: 10px 14px;
    border-radius: 10px;
    font-size: 13px;
    line-height: 1.6;
    border: 1px solid #ffe082;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    min-width: 170px;
    max-width: 240px;
}}
.word-groups.dense .word-card,
.word-groups.dense-4 .word-card,
.word-groups.dense-5 .word-card {{
    width: 100%;
    max-width: none;
}}
.split-card {{
    background: #b3e5fc;
    color: #01579b;
    padding: 8px 12px;
    border-radius: 10px;
    font-size: 12px;
    line-height: 1.5;
    border: 1px solid #81d4fa;
    box-shadow: 0 3px 10px rgba(0,0,0,0.1);
    min-width: 170px;
    max-width: 240px;
}}
.word-groups.dense .split-card,
.word-groups.dense-4 .split-card,
.word-groups.dense-5 .split-card {{
    width: 100%;
    max-width: none;
}}
svg.lines {{
    position: absolute;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    z-index: 0;
    pointer-events: none;
    overflow: visible;
}}
</style>
</head>
<body>
<div class="page" id="page">
<svg class="lines" id="svg" xmlns="http://www.w3.org/2000/svg"></svg>
<div class="container" id="container">
<div class="root" id="root">{root_main}<small>{root_sub}</small>{info_html_block}</div>
<div class="branches">'''

    for i, cat in enumerate(categories):
        word_count = len(cat["words"])
        if word_count > 40:
            dense_cls = ' dense-5'
        elif word_count > 24:
            dense_cls = ' dense-4'
        elif word_count > 15:
            dense_cls = ' dense'
        else:
            dense_cls = ''
        html += f'<div class="branch" id="branch-{i}">\n'
        html += f'<div class="cat-node" id="cat-{i}">{cat["title"]}</div>\n'
        html += f'<div class="word-groups{dense_cls}" id="wgs-{i}">\n'
        for j, w in enumerate(cat["words"]):
            html += f'<div class="word-group" id="wg-{i}-{j}">\n'
            html += f'<div class="word-card" id="word-{i}-{j}">{fmt_word(w["text"])}</div>\n'
            if w["split"]:
                html += f'<div class="split-card" id="split-{i}-{j}">{w["split"]}</div>\n'
            html += '</div>\n'
        html += '</div>\n</div>\n'

    html += '''</div>
</div>
</div>
<script>
function getBox(el, container) {
    const er = el.getBoundingClientRect();
    const cr = container.getBoundingClientRect();
    return {
        left: er.left - cr.left,
        right: er.right - cr.left,
        top: er.top - cr.top,
        bottom: er.bottom - cr.top,
        cx: er.left - cr.left + er.width / 2,
        cy: er.top - cr.top + er.height / 2
    };
}
function drawLine(x1, y1, x2, y2, color, width) {
    const p = document.createElementNS("http://www.w3.org/2000/svg", "line");
    p.setAttribute("x1", x1);
    p.setAttribute("y1", y1);
    p.setAttribute("x2", x2);
    p.setAttribute("y2", y2);
    p.setAttribute("stroke", color);
    p.setAttribute("stroke-width", width);
    p.setAttribute("fill", "none");
    p.setAttribute("stroke-linecap", "round");
    return p;
}
function drawPath(x1, y1, x2, y2, color, width) {
    const mx = (x1 + x2) / 2;
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", `M ${x1} ${y1} L ${mx} ${y1} L ${mx} ${y2} L ${x2} ${y2}`);
    p.setAttribute("stroke", color);
    p.setAttribute("stroke-width", width);
    p.setAttribute("fill", "none");
    p.setAttribute("stroke-linejoin", "round");
    p.setAttribute("stroke-linecap", "round");
    return p;
}
function drawPathFixed(x1, y1, x2, y2, color, width) {
    // 固定折点：在起点右侧 40px 处（确保落在 gap/padding 空白区，不戳进卡片）
    const mx = x1 + 40;
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", `M ${x1} ${y1} L ${mx} ${y1} L ${mx} ${y2} L ${x2} ${y2}`);
    p.setAttribute("stroke", color);
    p.setAttribute("stroke-width", width);
    p.setAttribute("fill", "none");
    p.setAttribute("stroke-linejoin", "round");
    p.setAttribute("stroke-linecap", "round");
    return p;
}
window.onload = function() {
    const page = document.getElementById("page");
    const svg = document.getElementById("svg");
    svg.setAttribute("width", page.scrollWidth);
    svg.setAttribute("height", page.scrollHeight);

    const root = document.getElementById("root");
    const rc = getBox(root, page);

    document.querySelectorAll(".branch").forEach(function(branch) {
        const cat = branch.querySelector(".cat-node");
        const cc = getBox(cat, page);
        svg.appendChild(drawPath(rc.right, rc.cy, cc.left, cc.cy, "#2196f3", 3));

        const wgs = branch.querySelector(".word-groups");
        const isDense = wgs.classList.contains("dense") || wgs.classList.contains("dense-4") || wgs.classList.contains("dense-5");

        if (isDense) {
            // dense 模式：每个 word-card 独立 Manhattan 折线
            // 折点固定在分类节点右侧 40px，确保垂直段落在 gap/padding 空白区
            branch.querySelectorAll(".word-card").forEach(function(wc) {
                const wb = getBox(wc, page);
                svg.appendChild(drawPathFixed(cc.right, cc.cy, wb.left, wb.cy, "#64b5f6", 2));
            });
        } else {
            // 非 dense：分类节点逐个连到每个 word-card
            branch.querySelectorAll(".word-card").forEach(function(wc) {
                const wb = getBox(wc, page);
                svg.appendChild(drawPath(cc.right, cc.cy, wb.left, wb.cy, "#64b5f6", 2));
            });
        }

        // 单词卡片 → 拆分卡片
        branch.querySelectorAll(".word-card").forEach(function(wc) {
            const group = wc.parentElement;
            const split = group.querySelector(".split-card");
            if (split) {
                const wb = getBox(wc, page);
                const sb = getBox(split, page);
                if (isDense) {
                    // dense 模式：上下排列，强制垂直连线
                    svg.appendChild(drawLine(wb.cx, wb.bottom, wb.cx, sb.top, "#4fc3f7", 2));
                } else {
                    // 非 dense：左右排列，横向连线
                    svg.appendChild(drawLine(wb.right, wb.cy, sb.left, sb.cy, "#4fc3f7", 2));
                }
            }
        });
    });
};
</script>
</body>
</html>'''
    return html


def generate():
    root_title, info_text, categories = parse_md(MD_PATH)
    html = build_html(root_title, info_text, categories)
    with open(HTML_PATH, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"已生成: {HTML_PATH}")


if __name__ == "__main__":
    generate()
