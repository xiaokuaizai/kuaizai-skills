# -*- coding: utf-8 -*-
"""步骤 2：按 SEG 分别用 faster_whisper 识别，避免长音频时间戳漂移。

问题背景：
  对完整视频一次性 transcribe + VAD，faster_whisper 在长音频上会出现
  时间戳漂移（前 15s 误差 -0.3 ~ -1s，累积可达几秒）。
  按 SEG（8-14s）单独识别，时间戳精度高 1 个量级。

输入：
  --seg-dir     SEG 视频目录（每 SEG 一个子目录 SEG-XX/SEG-XX.mp4）
  --seg-count   SEG 总数
  --workspace   本 skill 工作区

输出：{workspace}/whisper_by_seg.json
  {"SEG-01": [{"rel_start": 0.42, "rel_end": 6.85, "abs_start": 0.42,
               "abs_end": 6.85, "text": "...", "avg_logprob": -0.12}, ...], ...}
"""
import argparse
import json
import os
import sys
import time
from pathlib import Path

os.environ.setdefault('HF_ENDPOINT', 'https://hf-mirror.com')

sys.path.insert(0, str(Path(__file__).parent / 'lib'))
from common import read_json, write_json

from faster_whisper import WhisperModel


def main():
    parser = argparse.ArgumentParser(description='步骤 2：按 SEG whisper 识别')
    parser.add_argument('--seg-dir', required=True, help='SEG 视频目录')
    parser.add_argument('--seg-count', type=int, required=True, help='SEG 总数')
    parser.add_argument('--workspace', required=True, help='本 skill 工作区')
    parser.add_argument('--model', default='base', help='whisper 模型（默认 base）')
    parser.add_argument('--device', default='cpu', help='cpu / cuda（默认 cpu）')
    parser.add_argument('--compute-type', default='int8', help='int8 / float16 / float32')
    parser.add_argument('--start-seg', type=int, default=1, help='从第 N 个 SEG 开始（含）')
    parser.add_argument('--end-seg', type=int, default=None, help='到第 N 个 SEG 结束（含），默认 = seg-count')
    parser.add_argument('--out-name', default='whisper_by_seg.json', help='输出 JSON 文件名')
    args = parser.parse_args()

    # 限制 BLAS/MKL 线程，避免 mkl_malloc OOM
    os.environ.setdefault('OMP_NUM_THREADS', '2')
    os.environ.setdefault('MKL_NUM_THREADS', '2')
    os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')

    seg_dir = Path(args.seg_dir)
    workspace = Path(args.workspace)
    seg_durations = read_json(workspace / 'seg_durations.json')

    end_seg = args.end_seg or args.seg_count
    # 计算本批之前的累计偏移
    seg_offset = sum(seg_durations.get(f'SEG-{i:02d}', 0.0) for i in range(1, args.start_seg))

    print(f'加载模型 {args.model} ({args.device}/{args.compute_type})...')
    try:
        model = WhisperModel(args.model, device=args.device, compute_type=args.compute_type)
    except Exception as e:
        print(f'\n[错误] 模型加载失败: {e}')
        print(f'\n如果是首次运行，需要先下载模型：')
        print(f'  python 00_download_whisper_model.py --model {args.model}')
        print(f'\n或者检查镜像源是否可达（默认 https://hf-mirror.com）：')
        print(f'  set HF_ENDPOINT=https://hf-mirror.com')
        sys.exit(1)

    results = {}
    total_segs_identified = 0
    t0 = time.time()

    for i in range(args.start_seg, end_seg + 1):
        seg_id = f'SEG-{i:02d}'
        mp4 = seg_dir / seg_id / f'{seg_id}.mp4'
        if not mp4.exists():
            print(f'[MISS] {seg_id} 不存在，跳过')
            continue

        segments, info = model.transcribe(
            str(mp4),
            language='en',
            beam_size=5,
            vad_filter=True,
            vad_parameters=dict(threshold=0.35, min_silence_duration_ms=300, speech_pad_ms=200),
        )
        segs = []
        for s in segments:
            segs.append({
                'rel_start': round(s.start, 3),
                'rel_end': round(s.end, 3),
                'abs_start': round(seg_offset + s.start, 3),
                'abs_end': round(seg_offset + s.end, 3),
                'text': s.text.strip(),
                'avg_logprob': round(s.avg_logprob, 3),
            })
        results[seg_id] = segs
        total_segs_identified += len(segs)
        seg_offset += seg_durations[seg_id]

        if (i - args.start_seg + 1) % 10 == 0:
            print(f'  已识别 {i}/{end_seg} SEG, 累计 {total_segs_identified} 段, {time.time()-t0:.1f}s', flush=True)

    write_json(workspace / args.out_name, results)
    print(f'\n共识别 {total_segs_identified} 段，耗时 {time.time()-t0:.1f}s')
    print(f'输出: {workspace / args.out_name}')


if __name__ == '__main__':
    main()
