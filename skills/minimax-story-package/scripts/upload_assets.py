#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
资产上传脚本

功能：
  读取 resolve_asset_paths.py 生成的 manifest，将本地文件上传到 OSS。
  支持 --dry-run 只检查不上传。

依赖：
  pip install oss2

用法示例：
  python scripts/upload_assets.py \
    --manifest "清单/2026-08-24_asset_manifest.json" \
    --output "清单/2026-08-24_upload_result.json" \
    --upload
"""

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from _archive import archive_oss_object
from _config import check_credentials, get_oss_config


def parse_args() -> argparse.Namespace:
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description="上传资产到 OSS")
    parser.add_argument("--manifest", required=True, help="asset_manifest.json 文件路径")
    parser.add_argument("--output", help="上传结果输出路径，默认覆盖为 manifest 同名 _upload_result.json")
    parser.add_argument("--upload", action="store_true", help="真实上传；未指定则只执行 dry-run")
    parser.add_argument("--no-archive-old", dest="archive_old", action="store_false", default=True,
                        help="如果 OSS 上已存在同名对象，默认会归档旧版；指定此参数则跳过归档")
    return parser.parse_args()


def create_oss_client():
    """创建 OSS 客户端"""
    import oss2
    cfg = get_oss_config()
    auth = oss2.Auth(cfg["access_key_id"], cfg["access_key_secret"])
    endpoint = f"https://{cfg['region']}.aliyuncs.com"
    return oss2.Bucket(auth, endpoint, cfg["bucket"])


def upload_manifest(manifest_path: Path, do_upload: bool, archive_old: bool = True) -> dict:
    """读取 manifest 并执行上传或 dry-run"""
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

    if manifest.get("manifest_type") != "asset_manifest":
        raise ValueError(f"manifest 类型错误：{manifest.get('manifest_type')}")

    assets = manifest.get("assets", [])
    results = []
    success_count = 0
    failed_count = 0

    bucket = None
    if do_upload:
        check_credentials()
        bucket = create_oss_client()

    for item in assets:
        local_path = Path(item["local_path"])
        oss_key = item["oss_key"]
        result = {
            "id": item["id"],
            "type": item.get("type", manifest.get("asset_type", "")),
            "local_path": str(local_path),
            "oss_key": oss_key,
            "public_url": item["public_url"],
            "success": False,
            "size": 0,
            "message": "",
            "archived_oss_key": "",
        }
        # 保留参考音频的 TTS 自检元数据，供后续 SEG 资产包复核。
        for key in ("duration_seconds", "format", "purpose", "content_binding"):
            if key in item:
                result[key] = item[key]

        if not local_path.exists():
            result["message"] = "本地文件不存在"
            results.append(result)
            failed_count += 1
            continue

        result["size"] = local_path.stat().st_size

        if not do_upload:
            result["success"] = True
            result["message"] = "dry-run 通过"
            results.append(result)
            success_count += 1
            continue

        try:
            # 如果 OSS 上已有同名对象，先归档旧版
            if archive_old:
                archived_key = archive_oss_object(bucket, oss_key, reason="重新生成")
                if archived_key:
                    result["archived_oss_key"] = archived_key
                    print(f"[ARCHIVE] {item['id']} 旧版已归档 -> {archived_key}")
            # 实际上传，设置不缓存
            bucket.put_object_from_file(oss_key, str(local_path), headers={"Cache-Control": "no-cache"})
            result["success"] = True
            result["message"] = "上传成功"
            success_count += 1
            print(f"[OK] {item['id']} -> {oss_key}")
        except Exception as e:
            result["message"] = f"上传失败：{e}"
            failed_count += 1
            print(f"[FAIL] {item['id']}: {e}", file=sys.stderr)

        results.append(result)

    return {
        "manifest_type": "upload_result",
        "uploaded_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "dry_run": not do_upload,
        "project": manifest.get("project", ""),
        "branch": manifest.get("branch", ""),
        "asset_type": manifest.get("asset_type", ""),
        "uploaded_count": success_count,
        "failed_count": failed_count,
        "results": results,
    }


def main() -> int:
    args = parse_args()
    manifest_path = Path(args.manifest)
    if not manifest_path.exists():
        print(f"错误：manifest 文件不存在：{manifest_path}", file=sys.stderr)
        return 1

    if not args.upload:
        print("【dry-run 模式】只检查文件，不上传")

    result = upload_manifest(manifest_path, args.upload, archive_old=args.archive_old)

    # 确定输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = manifest_path.parent / f"{manifest_path.stem}_upload_result.json"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"上传结果已写入：{output_path.resolve()}")

    if args.upload and result["failed_count"] > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
