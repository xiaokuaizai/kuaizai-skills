# -*- coding: utf-8 -*-
"""minimax-bilingual-subtitle skill 的公共工具函数。

所有脚本的共享逻辑：路径解析、文本归一化、JSON 读写、日志。
"""
import json
import re
from pathlib import Path


def norm_text(s: str) -> str:
    """归一化文本用于匹配：小写、去 **、合并空白、strip。

    注意：不能去引号 —— timeline unit 末尾可能是合法的闭引号
    （如 "...challenge"），去掉会导致后续拼接时引号丢失，frag 匹配失败。
    """
    s = s.lower()
    s = re.sub(r'\*\*', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def norm_match(s: str) -> str:
    """模糊匹配用归一化：在 norm_text 基础上去所有中英文标点。

    适用场景：跨数据源字符串包含匹配（SP 表美式引号 ," vs timeline 句号 .）。
    注意：去掉的标点在匹配结果中不可恢复，仅用于相似度计算，不能替代原文。
    """
    s = norm_text(s)
    s = re.sub(r'[.,!?;:"\'"\'、，。！？；：（）()\[\]【】《》«»\-—…·]', '', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def clean_md(s: str) -> str:
    """清理 markdown 强调符号 **，保留内部文字（**xxx** → xxx）。"""
    s = re.sub(r'\*\*([^*]+)\*\*', r'\1', s)
    s = re.sub(r'\s+', ' ', s).strip()
    return s


def read_json(path):
    """读 JSON 文件。"""
    return json.loads(Path(path).read_text(encoding='utf-8'))


def write_json(path, data):
    """写 JSON 文件（utf-8 + indent=2，保留中文）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def ffprobe_duration(video_path: str) -> float:
    """用 ffprobe 获取视频时长（秒）。"""
    import subprocess
    r = subprocess.run(
        ['ffprobe', '-v', 'error', '-show_entries', 'format=duration',
         '-of', 'csv=p=0', str(video_path)],
        capture_output=True, text=True, encoding='utf-8', errors='replace',
    )
    return float(r.stdout.strip())


def fmt_ass_time(sec: float) -> str:
    """秒 → ASS 时间格式 H:MM:SS.cc（厘秒）。"""
    if sec < 0:
        sec = 0
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    cs = int(round((sec - int(sec)) * 100))
    if cs == 100:
        cs = 0
        s += 1
    return f'{h}:{m:02d}:{s:02d}.{cs:02d}'


def escape_ass_text(s: str) -> str:
    """ASS 特殊字符转义：{ } 是格式控制符，需替换。"""
    return s.replace('{', '(').replace('}', ')')
