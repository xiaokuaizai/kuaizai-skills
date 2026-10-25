#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
旧版归档工具模块

功能：
  - 本地文件存在时，移动到当前目录的 旧版/ 子文件夹，并添加版本号后缀。
  - OSS 对象存在时，复制到同前缀的 旧版/ 子路径，并添加版本号后缀。
  - 同时写入/追加说明文件，记录归档时间和原因。

用法：
  本模块通常被 upload_assets.py 与 archive_local_version.py 引用，
  不需要直接运行。
"""

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


NOTE_FILENAME = "说明.txt"  # 归档说明文件名


def _next_version(existing_names: list, stem: str, suffix: str) -> int:
    """根据已有旧版文件名计算下一个版本号"""
    # 匹配形如 A_旧版v1.png 的文件名
    pattern = re.compile(re.escape(stem) + r"_旧版v(\d+)" + re.escape(suffix) + "$")
    max_v = 0
    for name in existing_names:
        m = pattern.match(name)
        if m:
            max_v = max(max_v, int(m.group(1)))
    return max_v + 1


def _append_note(note_path: Path, original_name: str, archived_name: str, reason: str) -> None:
    """在本地说明文件末尾追加一条归档记录"""
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    reason_text = reason or "重新生成"
    line = f"{timestamp}  {original_name} -> {archived_name}  原因：{reason_text}\n"

    if note_path.exists():
        content = note_path.read_text(encoding="utf-8")
    else:
        content = "旧版归档记录\n"

    content += line
    note_path.write_text(content, encoding="utf-8")


def archive_local_file(local_path: Path, reason: str = "") -> Optional[Path]:
    """
    把已存在的本地文件归档到同目录的 旧版/ 文件夹中。

    参数：
      local_path: 要归档的本地文件路径
      reason: 归档原因，会写入说明文件

    返回：
      归档后的新路径；如果文件不存在则返回 None
    """
    if not local_path.exists():
        return None

    # 在当前目录下创建 旧版 文件夹
    old_dir = local_path.parent / "旧版"
    old_dir.mkdir(parents=True, exist_ok=True)

    stem = local_path.stem
    suffix = local_path.suffix

    # 计算版本号，例如 A_旧版v1.png
    existing_names = [p.name for p in old_dir.iterdir() if p.is_file()]
    version = _next_version(existing_names, stem, suffix)
    archived_name = f"{stem}_旧版v{version}{suffix}"
    archived_path = old_dir / archived_name

    # 移动旧文件
    local_path.rename(archived_path)

    # 写入说明
    _append_note(old_dir / NOTE_FILENAME, local_path.name, archived_name, reason)

    return archived_path


def _old_oss_dir_key(oss_key: str) -> str:
    """根据 OSS key 计算 旧版 目录的 key 前缀"""
    if "/" in oss_key:
        prefix, _ = oss_key.rsplit("/", 1)
        return f"{prefix}/旧版/"
    return "旧版/"


def _list_oss_object_names(bucket, prefix: str) -> list:
    """列出 OSS 指定前缀下的所有对象文件名"""
    names = []
    marker = ""
    while True:
        result = bucket.list_objects(prefix=prefix, marker=marker, max_keys=1000)
        for obj in result.object_list:
            names.append(obj.key)
        if not result.is_truncated:
            break
        marker = result.next_marker
    return names


def _next_oss_version(bucket, old_dir_key: str, stem: str, suffix: str) -> int:
    """计算 OSS 上该文件的下一个旧版版本号"""
    existing_keys = _list_oss_object_names(bucket, old_dir_key)
    existing_names = [key.rsplit("/", 1)[-1] for key in existing_keys]
    return _next_version(existing_names, stem, suffix)


def _append_oss_note(bucket, old_dir_key: str, original_name: str,
                     archived_name: str, reason: str) -> None:
    """在 OSS 的 旧版 目录中追加/创建说明文件"""
    note_key = f"{old_dir_key}{NOTE_FILENAME}"
    timestamp = datetime.now(timezone.utc).astimezone().strftime("%Y-%m-%d %H:%M:%S")
    reason_text = reason or "重新生成"
    line = f"{timestamp}  {original_name} -> {archived_name}  原因：{reason_text}\n"

    existing = "旧版归档记录\n"
    try:
        existing = bucket.get_object(note_key).read().decode("utf-8")
        if not existing:
            existing = "旧版归档记录\n"
    except Exception:
        pass

    bucket.put_object(note_key, (existing + line).encode("utf-8"))


def archive_oss_object(bucket, oss_key: str, reason: str = "") -> Optional[str]:
    """
    把已存在的 OSS 对象归档到同目录的 旧版/ 前缀下。

    参数：
      bucket: ali-oss Bucket 对象
      oss_key: 要归档的 OSS 对象 key
      reason: 归档原因

    返回：
      归档后的新 key；如果对象不存在则返回 None
    """
    # 检查对象是否存在，不存在则无需归档
    try:
        bucket.head_object(oss_key)
    except Exception:
        return None

    old_dir_key = _old_oss_dir_key(oss_key)
    filename = oss_key.rsplit("/", 1)[-1] if "/" in oss_key else oss_key
    stem = Path(filename).stem
    suffix = Path(filename).suffix

    version = _next_oss_version(bucket, old_dir_key, stem, suffix)
    archived_name = f"{stem}_旧版v{version}{suffix}"
    archived_key = f"{old_dir_key}{archived_name}"

    # 复制旧对象到新 key，然后删除原对象
    bucket.copy_object(bucket.bucket_name, oss_key, archived_key)
    bucket.delete_object(oss_key)

    # 写入说明
    _append_oss_note(bucket, old_dir_key, filename, archived_name, reason)

    return archived_key
