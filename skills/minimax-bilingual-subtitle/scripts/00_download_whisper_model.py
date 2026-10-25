# -*- coding: utf-8 -*-
"""步骤 0（预备）：预下载 faster_whisper 模型，避免首次运行 04_transcribe_by_seg.py 时卡在下载。

用法：
  python 00_download_whisper_model.py                     # 下载 base 模型（默认）
  python 00_download_whisper_model.py --model small       # 下载 small 模型
  python 00_download_whisper_model.py --list              # 列出可用模型

模型大小对比：
  tiny    ~39 MB    速度最快，识别精度低（仅适合快速测试）
  base    ~145 MB   速度与精度平衡（默认，支线 17 实测够用）
  small   ~461 MB   精度更高，CPU 上慢 2-3 倍
  medium  ~1.5 GB   精度高，CPU 上明显慢
  large-v3 ~2.9 GB  最高精度，CPU 上很慢，建议 cuda

下载源：
  默认从 https://hf-mirror.com 下载（国内可直连，无需代理）。
  若 hf-mirror 也失败，可设置环境变量 HF_ENDPOINT 切换到其他镜像。

缓存位置：
  Windows: C:\\Users\\{用户名}\\.cache\\huggingface\\hub\\
  所有 faster_whisper 项目共享此缓存，下载一次即可。
"""
import argparse
import os
import sys
from pathlib import Path

# 必须在 import faster_whisper 之前设置镜像源
os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

MODEL_SIZES = {
    'tiny': '~39 MB',
    'base': '~145 MB',
    'small': '~461 MB',
    'medium': '~1.5 GB',
    'large-v3': '~2.9 GB',
}


def check_model_cached(model_name: str) -> bool:
    """检查模型是否已在 Hugging Face 缓存中。

    faster-whisper 的模型由 Systran/faster-whisper-{model_name} 提供，
    缓存在 ~/.cache/huggingface/hub/models--Systran--faster-whisper-{model_name}/。
    只要 snapshots 目录非空就说明已下载。
    """
    cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub' / f'models--Systran--faster-whisper-{model_name}' / 'snapshots'
    if not cache_dir.exists():
        return False
    # snapshots 下有内容（SHA 子目录）才算真缓存了
    return any(cache_dir.iterdir())


def main():
    parser = argparse.ArgumentParser(description='预下载 faster_whisper 模型')
    parser.add_argument('--model', default='base', help='模型大小（默认 base）')
    parser.add_argument('--list', action='store_true', help='列出可用模型')
    parser.add_argument('--device', default='cpu', help='cpu / cuda（默认 cpu）')
    parser.add_argument('--compute-type', default='int8', help='int8 / float16 / float32')
    parser.add_argument('--force', action='store_true', help='强制重新下载（即使已缓存）')
    args = parser.parse_args()

    if args.list:
        print('可用模型大小：')
        for name, size in MODEL_SIZES.items():
            default_mark = '（默认）' if name == 'base' else ''
            cached_mark = '（已缓存）' if check_model_cached(name) else ''
            print(f'  {name:10s} {size:10s}{default_mark}{cached_mark}')
        return

    if args.model not in MODEL_SIZES:
        print(f'[错误] 未知模型 "{args.model}"，可选：{list(MODEL_SIZES.keys())}')
        sys.exit(1)

    # 显式缓存检查：已存在则跳过下载
    if not args.force and check_model_cached(args.model):
        cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
        print(f'[OK] 模型 {args.model} 已缓存，跳过下载')
        print(f'  缓存目录: {cache_dir}\\models--Systran--faster-whisper-{args.model}')
        print()
        print('所有 faster_whisper 项目共享此缓存，无需重复下载')
        return

    print(f'下载 faster-whisper 模型: {args.model} ({MODEL_SIZES[args.model]})')
    print(f'镜像源: {os.environ["HF_ENDPOINT"]}')
    print()

    # 导入并触发下载（faster_whisper 在首次 WhisperModel() 时下载）
    from faster_whisper import WhisperModel
    print('开始下载（首次较慢，请耐心等待）...')
    model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)

    # 缓存目录
    cache_dir = Path.home() / '.cache' / 'huggingface' / 'hub'
    print()
    print(f'[OK] 模型已就绪')
    print(f'  缓存目录: {cache_dir}')
    print()
    print('现在可以运行 04_transcribe_by_seg.py 了')


if __name__ == '__main__':
    main()
