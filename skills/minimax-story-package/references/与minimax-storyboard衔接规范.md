# 与 minimax-storyboard 衔接规范

本规范说明 `/minimax-storyboard` 在哪些步骤需要调用 `/minimax-story-package`。

## 调用原则

`/minimax-storyboard` 任何要产生本地文件或引用外部参考图的步骤，都应先咨询 `/minimax-story-package`，确保：
- 本地路径统一
- OSS 路径可预期
- 参考图已有 public URL
- 产物生成后能自动归档

## 具体衔接点

### 1. 人物锚点图生成前

在调用速创APIimage2.0 生成人物三视图/服装衍生图前：

```bash
python scripts/resolve_asset_paths.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type character_costume_view \
  --files "资产/人物锚点/支线1/安琪_支线1_外出超市休闲装.png" \
  --ids "anqi_支线1_外出超市休闲装" \
  --upload
```

将返回的 `public_url` 填入速创 config 的 `character_refs`。

### 2. 场景锚点图生成前

```bash
python scripts/resolve_asset_paths.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type scene_anchor \
  --files "资产/场景锚点/支线1/安琪家门口.png" \
  --ids "anqi_home_entrance" \
  --upload
```

### 3. 物品锚点图生成前

```bash
python scripts/resolve_asset_paths.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type prop_anchor \
  --files "资产/物品锚点/支线1/安琪的包.png" \
  --ids "anqi_bag" \
  --upload
```

### 4. 单镜头分镜图生成后

`panels/SH-XX.png` 生成后，调用产物归档：

```bash
python scripts/register_outputs.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type storyboard_panel \
  --files "panels/SH-01.png" "panels/SH-02.png" \
  --upload
```

### 5. 故事板参考图截图后

`capture_storyboard_refs.py` 截图后：

```bash
python scripts/register_outputs.py \
  --project 英语项目 \
  --branch 支线1 \
  --asset-type storyboard_ref \
  --files "故事板参考图/SEG-01-故事板参考图.png" \
  --upload
```

### 6. Minimax H3 提交包准备时

为某个 SEG 组装参考图包：

```bash
python scripts/build_segment_asset_pack.py \
  --project 英语项目 \
  --branch 支线1 \
  --segment SEG-01 \
  --scene "scene_br1_安琪家门口与邮箱.png" \
  --characters "jiangche_day_visit" "anqi_day_apron"
```

输出包含：
- Image 1：故事板参考图 URL
- Image 2：人物拼接参考图 URL（如需要则提示调用 `minimax-storyboard/scripts/combine_reference_sheets.py`）
- Image 3：场景锚点图 URL
- Image 4：物品锚点图 URL 或风格参考图
- Image 5：首帧分镜图 URL

## 在 SKILL.md 中的插入位置

在 `/minimax-storyboard/SKILL.md` 核心工作流中，以下步骤前插入 `/minimax-story-package` 调用：
- 第 8 步（生成分镜图 panels）前
- 第 10 步（故事板参考图截图）后
- 第 13 步（准备 Minimax H3 提交包）中
