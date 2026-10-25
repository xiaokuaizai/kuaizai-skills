# TTS音色总表

> 本文档记录本场次/本作品的 TTS 音色选择方案。
> 由 `minimax-storyboard-tts` skill 自动生成草案，用户确认后用于样本生成。

## 源文件

- **剧本**: `{relative_script_path}`
- **资产目录**: `{relative_assets_dir}`
- **生成时间**: `{generation_time}`

## 角色与音色匹配

| 角色 | role_key | 角色类型 | 英文表演方向 | 语速 | 主选音色 | voice_type | 备选音色1 | voice_type | 备选音色2 | voice_type | 匹配理由 | 样本文件 |
|---|---|---|---|---:|---|---|---|---|---|---|---|---|

## 样本文本

每个角色用于生成样本的台词：

| role_key | 样本文本 | 参考样本预估时长 |
|---|---|---:|

> 样本文本只用于试听音色，不承担 Minimax H3 的正式对白或旁白内容。

## 参考音频确认

人工试听后填写；人物和旁白使用相同规则。

| role_key | 已确认样本 | 参考音频文件 | reference_audio URL | 状态 |
|---|---|---|---|---|

## 生成记录

| 时间 | 操作 | 输出目录 | 状态 |
|---|---|---|---|

---

## 使用说明

1. 确认或修改上表中的音色选择。
2. 确认后运行样本生成命令：
   ```bash
   cd "{rel_skill_root}"
   python tools/generate_samples_from_table.py "{absolute_table_path}"
   ```
3. 生成完成后，样本文件路径会自动回填到「样本文件」列，并输出实际时长校验结果。
4. 人工试听后运行 `select_reference_audio.py` 记录选中的人物/旁白音色；样本内容不与正式台词绑定。
