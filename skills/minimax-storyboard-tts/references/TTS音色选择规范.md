# TTS 音色选择规范

> 本规范用于 `minimax-storyboard-tts` skill 自动为剧本角色推荐火山引擎 TTS 音色。
> 完整音色列表参考 `tools/volc-tts/doc/音色列表.md`。
> 最终音色以用户确认为准，skill 仅提供初选建议。

## 1. 角色类型定义

根据剧本中角色的性别、年龄、语言，先划分角色类型：

| 角色类型 | 特征 | 示例 |
|---|---|---|
| `en_teen_boy` | 英文，少年/青年男性 | Jiang Che |
| `en_teen_girl` | 英文，少年/青年女性 | An Qi |
| `en_adult_male` | 英文，成年男性 | Father, Teacher Li |
| `en_adult_female` | 英文，成年女性 | Mother |
| `en_narrator_male` | 英文，旁白/叙述男声 | Narrator |
| `zh_teen_boy` | 中文，少年/青年男性 | - |
| `zh_teen_girl` | 中文，少年/青年女性 | - |
| `zh_adult_male` | 中文，成年男性 | - |
| `zh_adult_female` | 中文，成年女性 | - |
| `zh_narrator_male` | 中文，旁白/解说男声 | - |

## 2. 默认音色推荐表

每个角色类型给出 1 个主选 + 2-3 个备选。备选应尽可能与主选在音色质感上有差异，方便用户试听比较。

### 英文角色

| 角色类型 | 主选音色 | voice_type | 备选1 | voice_type | 备选2 | voice_type |
|---|---|---|---|---|---|---|
| `en_teen_boy` | Lucas | `zh_male_M100_conversation_wvae_bigtts` | Brayan | `zh_male_shaonianzixin_moon_bigtts` | Alvin | `zh_male_wennuanahu_moon_bigtts` |
| `en_teen_girl` | Dacey | `en_female_dacey_uranus_bigtts` | Shiny | `zh_female_cancan_mars_bigtts` | Stokie | `en_female_stokie_uranus_bigtts` |
| `en_adult_male` | Sylus | `en_male_sylus_emo_v2_mars_bigtts` | Bruce | `en_male_bruce_moon_bigtts` | Michael | `en_male_michael_moon_bigtts` |
| `en_adult_female` | Skye | `en_female_skye_emo_v2_mars_bigtts` | Nadia | `en_female_nadia_tips_emo_v2_mars_bigtts` | Dacey | `en_female_dacey_uranus_bigtts` |
| `en_narrator_male` | Tim | `en_male_tim_uranus_bigtts` | Corey | `en_male_corey_emo_v2_mars_bigtts` | Michael | `en_male_michael_moon_bigtts` |

### 中文角色

| 角色类型 | 主选音色 | voice_type | 备选1 | voice_type | 备选2 | voice_type |
|---|---|---|---|---|---|---|
| `zh_teen_boy` | 少年梓辛/Brayan | `zh_male_shaonianzixin_moon_bigtts` | Lucas | `zh_male_M100_conversation_wvae_bigtts` | 温暖阿虎/Alvin | `zh_male_wennuanahu_moon_bigtts` |
| `zh_teen_girl` | 知性灿灿 | `zh_female_cancan_mars_bigtts` | 邻家女孩 | `zh_female_linjianvhai_uranus_bigtts` | 萌丫头/Cutey | `zh_female_mengyatou_uranus_bigtts` |
| `zh_adult_male` | 云舟 | `zh_male_m191_uranus_bigtts` | 儒雅逸辰 | `zh_male_ruyayichen_uranus_bigtts` | 刘飞 | `zh_male_liufei_uranus_bigtts` |
| `zh_adult_female` | 温柔妈妈 | `zh_female_wenroumama_uranus_bigtts` | 魅力苏菲 | `zh_female_sophie_uranus_bigtts` | 甜美小源 | `zh_female_tianmeixiaoyuan_uranus_bigtts` |
| `zh_narrator_male` | 解说小明 | `zh_male_jieshuoxiaoming_uranus_bigtts` | 霸气青叔 | `zh_male_baqiqingshu_uranus_bigtts` | 悬疑解说 | `zh_male_xuanyijieshuo_uranus_bigtts` |

## 3. 角色类型推断规则

从剧本中识别角色后，按以下规则推断角色类型：

1. **语言判断**：
   - 如果剧本标题或正文明显为英文（例如 `Airport Travel`、`English Version`），默认所有角色为英文类型。
   - 如果剧本为中文，默认所有角色为中文类型。
   - 旁白和对话语言不一致时，分别判断。

2. **年龄判断**：
   - 角色名包含 `boy`、`girl`、`kid`、`child`、`小男孩`、`小女孩` 等 → 儿童类型。
   - 角色名包含 `teenager`、`student`、`少年`、`少女`、`Jiang Che`、`An Qi` 等明确学生身份 → 青少年类型。
   - 角色名包含 `father`、`mother`、`teacher`、`director`、`doctor`、`staff`、`adult`、`父亲`、`母亲`、`老师`、`总监`、`医生` 等 → 成年类型。
   - 无法判断时，默认成年类型。

3. **性别判断**：
   - 角色名为常见男性名、或文本中有 `he/his/himself` 指代 → 男性。
   - 角色名为常见女性名、或文本中有 `she/her/herself` 指代 → 女性。
   - 无法判断时，根据角色类型默认选择（旁白默认男性，其他按上下文推断）。

4. **旁白**：
   - 标记为 `【Narration】` 或 `Narrator` 的文本统一归到 `*_narrator_male`。
   - 如果用户明确说旁白要用女声，改为 `en_narrator_female` 或 `zh_narrator_female`。

## 4. 语速建议

| 场景 | 语速参数 `speed_ratio` | 说明 |
|---|---|---|
| 正常对话 | `1.0` | 默认 |
| 紧张/急促对话 | `1.1` | 不超过 1.2 |
| 慢速旁白/情感核心句 | `0.9` | 不低于 0.8 |
| 儿童角色 | `1.0` | 可略快，但不超过 1.1 |

最终语速由用户在 `TTS音色总表.md` 中确认。

## 5. 用户覆盖规则

自动推荐只是草案。用户可以在 `TTS音色总表.md` 中直接修改：

- `主选音色` / `voice_type`
- `备选音色` / `voice_type`
- `语速`
- `英文表演方向`

修改后，重新运行样本生成命令即可按新表生成。

## 6. 样本生成约束

- 每个角色生成 **主选 + 2-3 个备选** 样本。
- 样本音频长度控制在 **7-8 秒以内**。
- 样本文本从剧本中该角色的实际台词选取。
- 输出格式：`{role_key}_primary.mp3`、`{role_key}_alt_01.mp3`、`{role_key}_alt_02.mp3`。

## 7. 跨作品音色一致性

如果同一角色在多个剧本/场次中出现，建议复用已确认的音色。skill 在生成草案时会优先检查资产目录中是否已有该角色的音色记录，有则推荐复用。
