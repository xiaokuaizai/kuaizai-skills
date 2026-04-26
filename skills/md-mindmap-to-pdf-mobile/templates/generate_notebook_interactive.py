# -*- coding: utf-8 -*-
"""批量生成 Notebook 风格交互式思维导图 HTML
深色主题 + 圆角节点 + 贝塞尔曲线 + 点击展开/折叠动画
"""
import os, re, json, glob

WIKI_DIR = r"G:\draw_long\单词划分\wiki\wiki\concepts"
OUTPUT_DIR = r"G:\draw_long\单词划分\逻辑式组成\output\mindmaps\notebook_html"

# 扫描所有前缀文件
all_files = sorted(glob.glob(os.path.join(WIKI_DIR, "前缀_*.md")))


# 语义颜色分配表
CAT_COLOR_MAP = {
    "动作": "#ffc107",   # 黄
    "行为": "#ffc107",
    "动态": "#ffc107",
    "操作": "#ffc107",
    "执行": "#ffc107",
    "进行": "#ffc107",
    "移动": "#ffc107",
    "变化": "#ffc107",
    "转变": "#ffc107",
    "转换": "#ffc107",
    "转化": "#ffc107",
    "过渡": "#ffc107",
    "传递": "#ffc107",
    "传输": "#ffc107",
    "传送": "#ffc107",
    "传播": "#ffc107",
    "状态": "#4caf50",   # 绿
    "性质": "#4caf50",
    "特征": "#4caf50",
    "特点": "#4caf50",
    "属性": "#4caf50",
    "状况": "#4caf50",
    "情形": "#4caf50",
    "情况": "#4caf50",
    "条件": "#4caf50",
    "环境": "#4caf50",
    "情境": "#4caf50",
    "心态": "#4caf50",
    "姿态": "#4caf50",
    "形态": "#4caf50",
    "形式": "#4caf50",
    "方式": "#4caf50",
    "方法": "#4caf50",
    "手段": "#4caf50",
    "途径": "#4caf50",
    "模式": "#4caf50",
    "模型": "#4caf50",
    "样式": "#4caf50",
    "格式": "#4caf50",
    "结构": "#4caf50",
    "构造": "#4caf50",
    "组成": "#4caf50",
    "构成": "#4caf50",
    "组织": "#4caf50",
    "安排": "#4caf50",
    "配置": "#4caf50",
    "布局": "#4caf50",
    "分布": "#4caf50",
    "排列": "#4caf50",
    "排序": "#4caf50",
    "分类": "#4caf50",
    "类别": "#4caf50",
    "种类": "#4caf50",
    "类型": "#4caf50",
    "抽象": "#ff9800",   # 橙
    "概念": "#ff9800",
    "理念": "#ff9800",
    "观念": "#ff9800",
    "思想": "#ff9800",
    "意识": "#ff9800",
    "认识": "#ff9800",
    "认知": "#ff9800",
    "理解": "#ff9800",
    "了解": "#ff9800",
    "知道": "#ff9800",
    "明白": "#ff9800",
    "清楚": "#ff9800",
    "明确": "#ff9800",
    "确定": "#ff9800",
    "肯定": "#ff9800",
    "否定": "#ff9800",
    "否认": "#ff9800",
    "拒绝": "#ff9800",
    "接受": "#ff9800",
    "同意": "#ff9800",
    "赞成": "#ff9800",
    "支持": "#ff9800",
    "反对": "#ff9800",
    "空间": "#9c27b0",   # 紫
    "位置": "#9c27b0",
    "方位": "#9c27b0",
    "方向": "#9c27b0",
    "地点": "#9c27b0",
    "场所": "#9c27b0",
    "区域": "#9c27b0",
    "领域": "#9c27b0",
    "范围": "#9c27b0",
    "界限": "#9c27b0",
    "边界": "#9c27b0",
    "边缘": "#9c27b0",
    "中心": "#9c27b0",
    "中央": "#9c27b0",
    "中间": "#9c27b0",
    "内部": "#9c27b0",
    "外部": "#9c27b0",
    "表面": "#9c27b0",
    "上面": "#9c27b0",
    "下面": "#9c27b0",
    "前面": "#9c27b0",
    "后面": "#9c27b0",
    "左面": "#9c27b0",
    "右面": "#9c27b0",
    "之间": "#9c27b0",
    "之内": "#9c27b0",
    "之外": "#9c27b0",
    "情感": "#e91e63",   # 粉
    "情绪": "#e91e63",
    "心情": "#e91e63",
    "感受": "#e91e63",
    "感觉": "#e91e63",
    "体验": "#e91e63",
    "体会": "#e91e63",
    "心理": "#e91e63",
    "精神": "#e91e63",
    "心灵": "#e91e63",
    "灵魂": "#e91e63",
    "意志": "#e91e63",
    "意愿": "#e91e63",
    "愿望": "#e91e63",
    "期望": "#e91e63",
    "希望": "#e91e63",
    "渴望": "#e91e63",
    "欲望": "#e91e63",
    "需要": "#e91e63",
    "需求": "#e91e63",
    "要求": "#e91e63",
    "请求": "#e91e63",
    "时间": "#00bcd4",   # 青
    "时刻": "#00bcd4",
    "时期": "#00bcd4",
    "期间": "#00bcd4",
    "阶段": "#00bcd4",
    "时代": "#00bcd4",
    "年代": "#00bcd4",
    "年份": "#00bcd4",
    "月份": "#00bcd4",
    "日期": "#00bcd4",
    "天数": "#00bcd4",
    "小时": "#00bcd4",
    "分钟": "#00bcd4",
    "秒钟": "#00bcd4",
    "先后": "#00bcd4",
    "前后": "#00bcd4",
    "开始": "#00bcd4",
    "结束": "#00bcd4",
    "持续": "#00bcd4",
    "延续": "#00bcd4",
    "连续": "#00bcd4",
    "继续": "#00bcd4",
    "中断": "#00bcd4",
    "停止": "#00bcd4",
    "暂停": "#00bcd4",
    "恢复": "#00bcd4",
    "重复": "#00bcd4",
    "再次": "#00bcd4",
    "重新": "#00bcd4",
    "频率": "#00bcd4",
    "次数": "#00bcd4",
    "数量": "#00bcd4",
    "程度": "#00bcd4",
    "水平": "#00bcd4",
    "标准": "#00bcd4",
    "等级": "#00bcd4",
    "级别": "#00bcd4",
    "层次": "#00bcd4",
    "高低": "#00bcd4",
    "大小": "#00bcd4",
    "多少": "#00bcd4",
    "数量": "#00bcd4",
    "质量": "#00bcd4",
    "品质": "#00bcd4",
}

FALLBACK_COLORS = ["#ffc107", "#4caf50", "#ff9800", "#9c27b0", "#e91e63", "#00bcd4", "#ff5722", "#3f51b5"]


def get_cat_color(title):
    """根据分类标题的语义关键词分配颜色"""
    for keyword, color in CAT_COLOR_MAP.items():
        if keyword in title:
            return color
    # 无匹配时用稳定哈希取色（确保同一标题始终得到同一颜色）
    idx = sum(ord(c) for c in title) % len(FALLBACK_COLORS)
    return FALLBACK_COLORS[idx]


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
            if any(k in title for k in ["关联词网", "相关页面", "相关链接"]):
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
    """把 'return /rɪˈtɜːn/ v.&n. 回来...' 格式化成 HTML 卡片（深色主题版）"""
    m = re.search(r'(/[^/]+/)', text)
    if m:
        phonetic = m.group(1)
        parts = text.split(phonetic, 1)
        word = parts[0].strip()
        rest = parts[1].strip() if len(parts) > 1 else ""
        html = (
            f'<div style="display:flex;flex-wrap:wrap;align-items:baseline;gap:6px;margin-bottom:4px;">'
            f'<strong style="font-size:13px;white-space:nowrap;color:#fff;">{word}</strong>'
            f'<span style="color:#aaa;font-size:12px;white-space:nowrap;">{phonetic}</span>'
            f'</div>'
        )
        if rest:
            html += f'<div style="color:#ccc;font-size:12px;line-height:1.5;">{rest}</div>'
        return html
    return f'<span style="color:#fff;">{text}</span>'


def build_html(root_title, info_text, categories):
    """生成 Notebook 风格交互式 HTML"""
    root_main = root_title or "词根"
    root_sub = ""
    if " " in root_main:
        parts = root_main.split(" ", 1)
        root_main = parts[0]
        root_sub = parts[1]

    info_html_block = ('<div class="root-info">' + info_text.replace("\n", "<br>") + '</div>') if info_text else ""

    # 预分配分类颜色
    cat_colors = [get_cat_color(cat["title"]) for cat in categories]

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{root_title or '思维导图'}</title>
<style>
* {{ box-sizing: border-box; margin: 0; padding: 0; }}
body {{
    margin: 0;
    padding: 24px;
    font-family: "Segoe UI", "Microsoft YaHei", "PingFang SC", sans-serif;
    background: #0d0d0d;
    color: #e0e0e0;
    min-height: 100vh;
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
/* 根节点 */
.root {{
    background: #2d2d3a;
    color: #fff;
    padding: 20px 24px;
    border-radius: 16px;
    font-size: 18px;
    font-weight: bold;
    text-align: center;
    line-height: 1.5;
    flex-shrink: 0;
    margin-top: 32px;
    box-shadow: 0 4px 20px rgba(0,0,0,0.4);
    border: 1px solid #3a3a4a;
    min-width: 140px;
    max-width: 220px;
    cursor: default;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
}}
.root:hover {{
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(0,0,0,0.5);
}}
.root small {{
    font-size: 14px;
    font-weight: normal;
    display: block;
    margin-top: 6px;
    color: rgba(255,255,255,0.7);
}}
.root-info {{
    margin-top: 12px;
    padding-top: 10px;
    border-top: 1px solid rgba(255,255,255,0.15);
    font-size: 12px;
    font-weight: normal;
    line-height: 1.5;
    text-align: left;
    color: rgba(255,255,255,0.75);
}}
/* 分支区域 */
.branches {{
    display: flex;
    flex-direction: column;
    gap: 20px;
}}
.branch {{
    display: flex;
    align-items: flex-start;
    gap: 24px;
}}
/* 分类节点 */
.cat-node {{
    padding: 10px 18px;
    border-radius: 20px;
    font-size: 13px;
    font-weight: bold;
    white-space: nowrap;
    flex-shrink: 0;
    margin-top: 8px;
    cursor: pointer;
    user-select: none;
    box-shadow: 0 3px 12px rgba(0,0,0,0.35);
    border: 1px solid rgba(255,255,255,0.1);
    transition: transform 0.2s ease, box-shadow 0.2s ease, filter 0.2s ease;
    position: relative;
}}
.cat-node:hover {{
    transform: translateY(-2px) scale(1.03);
    box-shadow: 0 5px 16px rgba(0,0,0,0.45);
    filter: brightness(1.1);
}}
.cat-node.collapsed::after {{
    content: " +";
    opacity: 0.7;
}}
.cat-node.expanded::after {{
    content: " -";
    opacity: 0.7;
}}
/* 单词组区域 */
.word-groups {{
    display: none;
    flex-direction: column;
    gap: 10px;
    opacity: 0;
    transition: opacity 0.3s ease;
}}
.word-groups.expanded {{
    display: flex;
    opacity: 1;
}}
.word-group {{
    display: flex;
    align-items: flex-start;
    gap: 14px;
}}
/* 单词卡片 */
.word-card {{
    background: #1e1e2e;
    color: #e0e0e0;
    padding: 10px 14px;
    border-radius: 12px;
    font-size: 12px;
    line-height: 1.5;
    border: 1px solid #2a2a3a;
    min-width: 140px;
    max-width: 200px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.25);
    transition: transform 0.2s ease, border-color 0.2s ease;
}}
.word-card:hover {{
    transform: translateY(-1px);
    border-color: #3a3a5a;
}}
/* 拆分内嵌 */
.split-inline {{
    margin-top: 8px;
    padding: 6px 10px;
    background: rgba(79, 195, 247, 0.1);
    color: #4fc3f7;
    border-radius: 8px;
    font-size: 11px;
    line-height: 1.4;
    border: 1px solid rgba(79, 195, 247, 0.2);
}}
/* SVG 连线 */
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
        color = cat_colors[i]
        html += f'<div class="branch" id="branch-{i}" data-cat-idx="{i}">\n'
        html += f'<div class="cat-node collapsed" id="cat-{i}" style="background:{color};color:#111;" onclick="toggleBranch({i})">{cat["title"]}</div>\n'
        html += f'<div class="word-groups" id="wgs-{i}" style="display:none;">\n'
        for j, w in enumerate(cat["words"]):
            html += f'<div class="word-group" id="wg-{i}-{j}">\n'
            split_html = f'<div class="split-inline">{w["split"]}</div>' if w["split"] else ""
            html += f'<div class="word-card" id="word-{i}-{j}" style="border-left:3px solid {color};">{fmt_word(w["text"])}{split_html}</div>\n'
            html += '</div>\n'
        html += '</div>\n</div>\n'

    html += '''</div>
</div>
</div>
<script>
// 贝塞尔曲线绘制
function drawBezier(x1, y1, x2, y2, color, width) {
    const dx = x2 - x1;
    const c1x = x1 + dx * 0.5;
    const c1y = y1;
    const c2x = x1 + dx * 0.5;
    const c2y = y2;
    const p = document.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", `M ${x1} ${y1} C ${c1x} ${c1y}, ${c2x} ${c2y}, ${x2} ${y2}`);
    p.setAttribute("stroke", color);
    p.setAttribute("stroke-width", width);
    p.setAttribute("fill", "none");
    p.setAttribute("stroke-linecap", "round");
    return p;
}

// 计算元素相对 page 的包围盒
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

const page = document.getElementById("page");
const svg = document.getElementById("svg");
const root = document.getElementById("root");
const rc = getBox(root, page);

// 存储所有连线以便动态更新
const lines = [];

function clearLines() {
    while (svg.firstChild) svg.removeChild(svg.firstChild);
    lines.length = 0;
}

function redrawAll() {
    clearLines();
    svg.setAttribute("width", page.scrollWidth);
    svg.setAttribute("height", page.scrollHeight);

    document.querySelectorAll(".branch").forEach(function(branch) {
        const idx = parseInt(branch.getAttribute("data-cat-idx"));
        const cat = branch.querySelector(".cat-node");
        const cc = getBox(cat, page);
        const catColor = cat.style.background || "#ffc107";

        // 根 → 分类（始终显示）
        svg.appendChild(drawBezier(rc.right, rc.cy, cc.left, cc.cy, catColor, 2.5));

        const wgs = branch.querySelector(".word-groups");
        if (wgs.classList.contains("expanded")) {
            // 分类 → 单词（仅在展开时显示）
            branch.querySelectorAll(".word-card").forEach(function(wc) {
                const wb = getBox(wc, page);
                svg.appendChild(drawBezier(cc.right, cc.cy, wb.left, wb.cy, "#64b5f6", 1.5));
            });
        }
    });
}

// 切换分支展开/折叠
function toggleBranch(idx) {
    const wgs = document.getElementById("wgs-" + idx);
    const cat = document.getElementById("cat-" + idx);
    if (wgs.style.display === "none" || !wgs.classList.contains("expanded")) {
        // 展开：先设置 display:flex 让元素参与布局，下一帧再添加 expanded 触发动画
        wgs.style.display = "flex";
        cat.classList.remove("collapsed");
        cat.classList.add("expanded");
        requestAnimationFrame(function() {
            wgs.classList.add("expanded");
            redrawAll();
        });
    } else {
        // 折叠：先移除 expanded 触发 opacity 过渡，0.3s 后再隐藏 display
        wgs.classList.remove("expanded");
        cat.classList.remove("expanded");
        cat.classList.add("collapsed");
        setTimeout(function() {
            if (!wgs.classList.contains("expanded")) {
                wgs.style.display = "none";
            }
            redrawAll();
        }, 300);
    }
}

// 初始化
window.onload = function() {
    redrawAll();
};

// 窗口大小变化时重绘连线
window.addEventListener("resize", redrawAll);
</script>
</body>
</html>'''
    return html


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    for fpath in all_files:
        fname = os.path.basename(fpath)
        base = os.path.splitext(fname)[0]
        html_path = os.path.join(OUTPUT_DIR, base + ".html")

        root_title, info_text, categories = parse_md(fpath)
        html = build_html(root_title, info_text, categories)
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML: {base}.html ({len(categories)} 分类)")

    print(f"\n生成完成: {len(all_files)} 个交互式 HTML，输出目录: {OUTPUT_DIR}")


if __name__ == "__main__":
    main()
