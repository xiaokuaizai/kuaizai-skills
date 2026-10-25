# -*- coding: utf-8 -*-
"""一键跑完 7 步字幕生成流程。

用法：
  python run_all.py \
    --workspace "F:/path/to/工作区" \
    --video "F:/path/to/完整版.mp4" \
    --storyboard-dir "F:/path/to/故事板工作区" \
    --seg-dir "F:/path/to/分段视频" \
    --seg-count 62

可选参数：
  --format              SEG 提示词格式：shot（默认）/ seg / shot_dash / single
  --skip-translate      跳过 Kimi 翻译（如果 su_zh.json 已存在）
  --skip-transcribe     跳过 whisper 识别（如果 whisper_by_seg.json 已存在）
  --sample-duration N   只烧前 N 秒（用于验证）
"""
import argparse
import subprocess
import sys
from pathlib import Path

SCRIPTS_DIR = Path(__file__).parent


def run(script_name: str, args: list):
    """跑一个子脚本，失败则退出。"""
    cmd = [sys.executable, str(SCRIPTS_DIR / script_name)] + args
    print(f'\n=== 运行 {script_name} ===')
    print(f'{" ".join(cmd)}')
    r = subprocess.run(cmd, capture_output=False, text=True,
                       encoding='utf-8', errors='replace')
    if r.returncode != 0:
        print(f'\n[FAIL] {script_name} 退出码 {r.returncode}')
        sys.exit(r.returncode)


def main():
    parser = argparse.ArgumentParser(description='一键跑完 7 步双语字幕流程')
    parser.add_argument('--workspace', required=True)
    parser.add_argument('--video', required=True)
    parser.add_argument('--storyboard-dir', required=True)
    parser.add_argument('--seg-dir', required=True)
    parser.add_argument('--seg-count', type=int, required=True)
    parser.add_argument('--format', choices=['shot', 'seg', 'shot_dash', 'single'], default='shot',
                        help='SEG 提示词格式：shot=minimax_h3_prompts（默认）/ seg=最终提示词 / shot_dash / single=H3最终提示词.md')
    parser.add_argument('--characters', default='安琪,江彻,教练')
    parser.add_argument('--video-width', type=int, default=768)
    parser.add_argument('--video-height', type=int, default=1344)
    parser.add_argument('--model', default='base')
    parser.add_argument('--skip-translate', action='store_true',
                        help='跳过 Kimi 翻译（如果 su_zh.json 已存在）')
    parser.add_argument('--force-translate', action='store_true',
                        help='强制重新翻译（覆盖已有 su_zh.json）')
    parser.add_argument('--skip-transcribe', action='store_true',
                        help='跳过 whisper 识别（如果 whisper_by_seg.json 已存在）')
    parser.add_argument('--sample-duration', type=float, default=None,
                        help='只烧前 N 秒（用于验证）')
    args = parser.parse_args()

    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)

    su_table = Path(args.storyboard_dir) / 'doc' / '文本语义拆分表.md'
    if not su_table.exists():
        raise SystemExit(f'[错误] SU 拆分表不存在: {su_table}')

    # 步骤 1：Kimi 翻译（生成 su_zh.json）
    su_zh_file = workspace / 'su_zh.json'
    if args.skip_translate and su_zh_file.exists():
        print(f'\n=== 跳过 translate_su_with_kimi.py（已存在 {su_zh_file}）===')
    else:
        translate_args = [
            '--su-table', str(su_table),
            '--workspace', str(workspace),
        ]
        if args.force_translate:
            translate_args.append('--force')
        run('translate_su_with_kimi.py', translate_args)

    # 步骤 2：提取 seg_lines + fragments（含中文配对）
    run('01_extract_seg_lines.py', [
        '--storyboard-dir', args.storyboard_dir,
        '--workspace', str(workspace),
        '--su-table', str(su_table),
        '--seg-count', str(args.seg_count),
        '--seg-dir', args.seg_dir,
        '--format', args.format,
        '--characters', args.characters,
    ])

    # 步骤 3（可选跳过 whisper 识别）
    whisper_file = workspace / 'whisper_by_seg.json'
    if args.skip_transcribe and whisper_file.exists():
        print(f'\n=== 跳过 02_transcribe_by_seg.py（已存在 {whisper_file}）===')
    else:
        # 模型预检：未下载则先触发下载
        print('\n=== 预检 whisper 模型 ===')
        from faster_whisper import WhisperModel
        try:
            WhisperModel(args.model, device='cpu', compute_type='int8')
            print('模型已就绪')
        except Exception:
            print(f'模型 {args.model} 未下载，先下载...')
            run('00_download_whisper_model.py', ['--model', args.model])

        run('02_transcribe_by_seg.py', [
            '--seg-dir', args.seg_dir,
            '--seg-count', str(args.seg_count),
            '--workspace', str(workspace),
            '--model', args.model,
        ])

    # 步骤 4：按 SEG 对位
    run('03_align_by_order.py', ['--workspace', str(workspace)])

    # 步骤 5：生成 ASS
    run('04_generate_ass.py', [
        '--workspace', str(workspace),
        '--video-width', str(args.video_width),
        '--video-height', str(args.video_height),
    ])

    # 步骤 6：烧录
    burn_args = [
        '--video', args.video,
        '--ass', str(workspace / 'subtitle.ass'),
    ]
    if args.sample_duration:
        burn_args.extend(['--duration', str(args.sample_duration)])
    run('05_burn_subtitles.py', burn_args)

    print('\n=== 全部完成 ===')
    print(f'产物目录: {workspace}')


if __name__ == '__main__':
    main()
