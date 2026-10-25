# Minimax Bilingual Subtitle

## 核心作用

本 skill 为已有的**完整视频**自动添加**中英双语字幕**。前提是同一份剧本有英文版（SU 拆分表即完整英文剧本逐句拆分），视频里的语音是英文（faster_whisper 识别英文时间戳）。

**中文翻译**：调 Kimi API 把 SU 表的每个英文 fragment 直译成中文，存成 `su_zh.json` 复用。

字幕样式固定：
- 位置：视频下方
- 上行英文（大字体）+ 下行中文（小字体）
- 字体：仿宋（FangSong）
- 颜色：白色

## 触发条件

- 已有完整支线视频（来自 `/minimax-ffmpeg-assembly` 或手工拼接）
- 有 SU 拆分表（含完整英文台词）
- 用户要求"加双语字幕"、"烧字幕"或"做双语字幕视频"

## 前置条件

开始前必须明确：

1. **工作区**：一个独立的输出目录（本 skill 所有产物都放这里）
2. **SU 拆分表**：minimax-storyboard 的 `doc/文本语义拆分表.md`（含完整英文台词）
3. **完整视频**：`.mp4` 路径
4. **minimax-storyboard 二次产物目录**：含 `doc/minimax_h3_prompts/`（或 `doc/最终提示词/` 或 `doc/H3最终提示词.md`）和 `04_支线产出/视频/SEG-XX/SEG-XX.mp4`
5. **Kimi API 环境变量**（用于中文翻译）：
   - `ANTHROPIC_AUTH_TOKEN`
   - `ANTHROPIC_BASE_URL`（默认 `https://api.kimi.com/coding/`）
   - `ANTHROPIC_MODEL`（默认 `kimi-for-coding`）

若上游没有 minimax-storyboard 二次产物，本 skill 不可用（seg_lines 提取依赖 SEG prompt）。

## 工作流程（7 步固定）

| 步骤 | 脚本 | 输入 | 输出 | 成本 |
|---|---|---|---|---|
| 0 | `00_download_whisper_model.py` | （可选）模型大小 | 本机缓存 | 一次性 |
| 1 | `translate_su_with_kimi.py` | SU 拆分表 | `su_zh.json` | Kimi API |
| 2 | `01_extract_seg_lines.py` | storyboard 工作区 + SU 拆分表 + su_zh.json | `seg_lines.json` + `fragments.json` | C0 |
| 3 | `02_transcribe_by_seg.py` | SEG 视频目录 | `whisper_by_seg.json` | C2（CPU） |
| 4 | `03_align_by_order.py` | seg_lines + whisper_by_seg | `subtitle_split.json` | C0 |
| 5 | `04_generate_ass.py` | subtitle_split + 样式配置 | `subtitle.ass` | C0 |
| 6 | `05_burn_subtitles.py` | 完整视频 + subtitle.ass | `{name}_双语字幕.mp4` | C2（CPU） |

每个步骤都是独立 Python 脚本，可通过 CLI 单独调用，便于调试。

## 环境准备（首次运行必做）

**1. 安装 Python 依赖**

```bash
pip install faster-whisper
```

**2. 设置 Kimi API 环境变量**

```powershell
$env:ANTHROPIC_AUTH_TOKEN="sk-kimi-..."
$env:ANTHROPIC_BASE_URL="https://api.kimi.com/coding/"
$env:ANTHROPIC_MODEL="kimi-for-coding"
```

或持久化到系统环境变量。

**3. 下载 whisper 模型（一次性，所有项目共享缓存）**

```bash
python scripts/00_download_whisper_model.py                  # 默认 base（约 145MB）
python scripts/00_download_whisper_model.py --model small    # 更精准但慢 2-3 倍
python scripts/00_download_whisper_model.py --list           # 查看所有可选模型 + 缓存状态
```

模型默认从 `https://hf-mirror.com` 下载（国内可直连），缓存在：
```
C:\Users\{用户名}\.cache\huggingface\hub\models--Systran--faster-whisper-{模型名}\
```

**缓存机制**：
- 缓存是**系统级**的，跟会话、工作区、项目都无关
- 下载一次后，**所有 faster_whisper 项目共用**（包括其他 skill、其他工作区）
- `00_download_whisper_model.py` 会先检查缓存，已存在则直接跳过，不会重复下载
- 即使新开一个 Claude 会话，只要调用 `02_transcribe_by_seg.py`，faster_whisper 库也会自动复用此缓存

若 hf-mirror 不可达，可设置 `HF_ENDPOINT` 环境变量切换镜像。

**4. 确认 ffmpeg 已安装并在 PATH 中**

```bash
ffmpeg -version
```

## 核心原则

1. **按 SEG 对齐，不做跨 SEG 文本匹配**：SEG 内的行与 whisper 段按"时间重叠最大"配对，避免了 normalize/引号/前缀 bug 一整类问题。
2. **不能修改原文**：SU 拆分表是锁定文档，字幕英文逐字符引用，不能压缩、改写、漏字。
3. **中文用 Kimi API 直译**：不调 zh_units 配对（容易错位）；直接对 SU 表的每个英文 fragment 调 Kimi 直译，保留原文语气和标点。
4. **whisper 必须按 SEG 识别**：一次性处理长视频会有时间戳漂移（mean -3s，max -7.5s）。必须按 SEG 单独识别。
5. **首字时间戳优先**：whisper 识别到的当句话首字时间戳优先采用；与理论时间差 ≤0.3s 时采用 whisper，否则回退理论时间。
6. **长字幕必须拆**：单条字幕英文 ≤20 词 / 中文 ≤30 字 / 时长 ≤10s；优先用 SU 拆分表的人工审核边界，兜底按句子边界强制拆。
7. **样式固定**：英文 36px + 中文 26px + 仿宋 + 白色 + MarginV（英 72 / 中 24）。可通过 `--style` 覆盖。
8. **数据保留**：所有中间 JSON 都保留在工作区，可复查。
9. **源文件不能改**：SU 拆分表、上游视频都不能改。

## 关键算法：时间对位（`03_align_by_order.py`）

 whisper 识别出的语音段与 shot 理论时间**经常不一致**，需要复杂的对位逻辑：

### 同时间多 shot（同帧多说话人）

**现象**：minimax-storyboard 的 prompt 常把两人对话写在同一时间（如 `0:04.0–0:09.0` 江彻+安琪各一句）。

**修复**：把时间完全相同的 shot 分到一组（按 `seg_start, seg_end` 完全相等），视为"同帧多说话人"。whisper 段在该组内**按 shot 顺序轮流分配**。

### 1 个 whisper 段跨越多个 shot

**现象**：whisper 把 2~3 句识别成 1 段（如 "A little, but I will not weep."），但 SU 表拆成了 2 个 shot。

**修复**：把 whisper 段按**时间重叠占比**切分到不同的 shot 组。每个 shot 分到的片段用 `synthetic: True` 标记。

### 组内 whisper 段数 vs shot 数不一致

- 段数 == shot 数 → 一一对应
- 段数 > shot 数 → 相邻合并，多余段给最后一个 shot
- 段数 < shot 数 → 按 shot 顺序均分 whisper 段时间

### 实现

见 `scripts/03_align_by_order.py` 的 `align_seg_shots()` 函数。

## 标准调用示例

```bash
# 步骤 1：翻译 SU 表（首次必做，生成 su_zh.json）
python scripts/translate_su_with_kimi.py \
  --su-table "F:/path/to/文本语义拆分表.md" \
  --workspace "F:/path/to/工作区"

# 步骤 2-6：完整流程（一键跑完）
python scripts/run_all.py \
  --workspace "F:/path/to/工作区" \
  --su-table "F:/path/to/文本语义拆分表.md" \
  --video "F:/path/to/完整版.mp4" \
  --storyboard-dir "F:/path/to/故事板工作区" \
  --seg-dir "F:/path/to/分段视频" \
  --seg-count 62 \
  --format single

# 或者单步调用
python scripts/01_extract_seg_lines.py \
  --storyboard-dir "F:/path/to/故事板工作区" \
  --workspace "F:/path/to/工作区" \
  --su-table "F:/path/to/文本语义拆分表.md" \
  --seg-dir "F:/path/to/分段视频" \
  --seg-count 62 \
  --format single
```

## 输出结构

```text
{workspace}/
├── su_zh.json                    # 步骤 1：SU fragment → 中文翻译（可复用）
├── seg_durations.json            # 每 SEG 实测时长
├── seg_lines.json                # 步骤 2：SEG 内台词行 + 英文
├── fragments.json                # 步骤 2：SU 拆分片段（含 shots 引用 + 中文）
├── whisper_by_seg.json           # 步骤 3：whisper 识别结果
├── subtitle_split.json           # 步骤 4：对位后字幕（最终数据）
├── subtitle.ass                  # 步骤 5：ASS 字幕文件
├── {name}_双语字幕.mp4           # 步骤 6：最终烧录产物
└── preview/                      # 抽帧验证
    ├── frame_*.png
    └── _test.png
```

## SEG prompt 格式（--format）

| 格式 | 路径 | 说明 |
|---|---|---|
| `shot`（默认） | `doc/minimax_h3_prompts/SEG-XX_prompt.md` | 每 SEG 一个文件 |
| `seg` | `doc/最终提示词/SEG-XX_final_prompt.md` | 每 SEG 一个文件 |
| `single` | `doc/H3最终提示词.md` | 所有 SEG 在一个文件（03 支线格式） |

**判断方法**：看故事板 `doc/` 下哪个存在。

## 参考文档

- `references/输入要求.md`：环境准备、参数说明、SU 拆分表格式
- `references/时间戳对齐算法.md`：时间重叠最大配对 + whisper 校正的详细说明
- `references/字幕样式规范.md`：ASS 样式参数说明
- `references/常见问题与调试.md`：已知 bug、调优参数
- `references/支线输入预处理.md`：非标准 SU 表 / SEG prompt 的预处理方案（06 支线实测）
