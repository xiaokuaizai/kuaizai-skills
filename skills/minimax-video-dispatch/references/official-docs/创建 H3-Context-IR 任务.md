> ## Documentation Index

> Fetch the complete documentation index at: https://platform.minimaxi.com/docs/llms.txt

> Use this file to discover all available pages before exploring further.



\# 创建 H3-Context-IR 任务



> 深度理解多模态上下文，并生成结构化、语义更丰富的视频提示词。



<Warning>

&#x20; 本接口只返回增强后的视频提示词，不会创建视频生成任务。

</Warning>



H3-Context-IR 对文本、图像、音频和视频等多模态上下文进行深度理解，分析素材之间以及素材与目标生成结果之间的关系，并进行复杂逻辑推理。系统会将理解结果转换为结构化表达，在尽量保持用户原始意图的前提下丰富语义细节。



<Note>

&#x20; H3-Context-IR 是一个复杂系统，暂不提供开源实现；本 API 既可用于验证 Full 2K-Workflow 的官方效果，也可集成到生产工作流中。

</Note>



<Note>

&#x20; 创建成功后，使用\[查询任务](/docs/api-reference/video-generation-v2-query)或\[查询任务列表](/docs/api-reference/video-generation-v2-list)接口查询。H3-Context-IR 任务的 `task\_type` 为 `h3\_context\_ir`；任务成功后，从 `content.prompt` 获取增强提示词。

</Note>





\## OpenAPI



````yaml api-reference/video/generation/api/v2-video-generation.json POST /v2/h3\_context\_ir

openapi: 3.1.0

info:

&#x20; title: MiniMax API

&#x20; description: MiniMax video generation V2 (Hailuo-03) API

&#x20; license:

&#x20;   name: MIT

&#x20; version: 2.0.0

servers:

&#x20; - url: https://api.minimaxi.com

security:

&#x20; - bearerAuth: \[]

paths:

&#x20; /v2/h3\_context\_ir:

&#x20;   post:

&#x20;     tags:

&#x20;       - Video V2

&#x20;     summary: 创建 H3-Context-IR 任务

&#x20;     description: >-

&#x20;       H3-Context-IR

&#x20;       深度理解文本、图像、音频和视频等多模态上下文，分析素材之间以及素材与目标生成结果之间的关系，并进行复杂逻辑推理。系统会将理解结果转换为结构化表达，在尽量保持用户原始意图的前提下丰富语义细节。本接口只返回增强提示词，不创建视频生成任务。





&#x20;       H3-Context-IR 是一个复杂系统，暂不提供开源实现；本 API 既可用于验证 Full 2K-Workflow

&#x20;       的官方效果，也可集成到生产工作流中。

&#x20;     operationId: h3ContextIRV2Create

&#x20;     parameters:

&#x20;       - name: Content-Type

&#x20;         in: header

&#x20;         required: true

&#x20;         description: 请求体的媒介类型，请设置为 `application/json`。

&#x20;         schema:

&#x20;           type: string

&#x20;           enum:

&#x20;             - application/json

&#x20;           default: application/json

&#x20;     requestBody:

&#x20;       content:

&#x20;         application/json:

&#x20;           schema:

&#x20;             $ref: '#/components/schemas/H3ContextIRReq'

&#x20;           examples:

&#x20;             文生视频 (t2va):

&#x20;               value:

&#x20;                 model: MiniMax-H3

&#x20;                 content:

&#x20;                   - type: text

&#x20;                     text: >-

&#x20;                       史诗级太空歌剧院线预告：女舰长独自站在巨大观景窗前，最后一支舰队正在集结并跃迁离去，强光爆闪、舰桥震动，她被留在原地。

&#x20;                 duration: 5

&#x20;                 ratio: '16:9'

&#x20;             图生视频 (i2va):

&#x20;               value:

&#x20;                 model: MiniMax-H3

&#x20;                 content:

&#x20;                   - type: text

&#x20;                     text: >-

&#x20;                       Pull focus to the people in the background and add more

&#x20;                       steam to the ramen bowl.

&#x20;                   - type: image\_url

&#x20;                     image\_url:

&#x20;                       url: >-

&#x20;                         https://cdn.hailuoai.com/prod/hailuo\_demo/testsets/H3\_AA\_I2VA/gallery/sr\_v17\_variants\_seed42\_43\_20260724/inputs/4a3a90bf9100\_KDmcbkhzYo5sjjxr9FqcVmWVnzb.png

&#x20;                     role: first\_frame

&#x20;                 duration: 5

&#x20;                 ratio: adaptive

&#x20;             多模态参考生视频 (r2va):

&#x20;               value:

&#x20;                 model: MiniMax-H3

&#x20;                 content:

&#x20;                   - type: text

&#x20;                     text: >-

&#x20;                       角色说话：Follow the wind, live free.Leave worries behind,

&#x20;                       enjoy the moment，音色参考音频1

&#x20;                   - type: video\_url

&#x20;                     video\_url:

&#x20;                       url: >-

&#x20;                         https://cdn.hailuoai.com/prod/hailuo\_demo/testsets/h3\_promo\_eval\_ref2va/gallery/sr\_v2p26\_trio\_seed42\_20260724/inputs/297573323635\_00\_%E8%A7%86%E9%A2%911\_YnyRbxEwio\_video\_20260525\_163755\_1927e9d3.mp4

&#x20;                     role: reference\_video

&#x20;                   - type: audio\_url

&#x20;                     audio\_url:

&#x20;                       url: >-

&#x20;                         https://cdn.hailuoai.com/prod/hailuo\_demo/testsets/h3\_promo\_eval\_ref2va/gallery/sr\_v2p26\_trio\_seed42\_20260724/inputs/f463d523c5ce\_01\_%E9%9F%B3%E9%A2%911\_RSLcbpzJPo\_6%E6%9C%885%E6%97%A5(1).mp3

&#x20;                     role: reference\_audio

&#x20;                 duration: 5

&#x20;                 ratio: adaptive

&#x20;       required: true

&#x20;     responses:

&#x20;       '200':

&#x20;         description: >-

&#x20;           创建成功后返回 `task\_id`。使用该 `task\_id`

&#x20;           调用\[查询任务](/api-reference/video-generation-v2-query)接口获取任务状态与结果。任务成功后，从

&#x20;           `content.prompt` 获取增强提示词。





&#x20;           \*\*查询任务成功响应示例\*\*





&#x20;           ```json



&#x20;           {

&#x20;             "task": {

&#x20;               "id": "426586401755526",

&#x20;               "model": "MiniMax-H3",

&#x20;               "status": "succeeded",

&#x20;               "created\_at": 1785702855,

&#x20;               "updated\_at": 1785702884,

&#x20;               "content": {

&#x20;                 "prompt": "integrated\_multimodal\_description: \[Shot 1] Cinematic, wide shot with a slow push in on a female captain standing center frame with her back to the camera. She has a slender build and short, swept-back silver hair, wearing a crisp, dark navy-blue futuristic military uniform adorned with rigid silver epaulets. Before her stretches a colossal, curved glass observation window dominating the dimly lit starship bridge. The interior features sleek metallic consoles on the left and right emitting soft cyan light. Outside the window, a massive fleet of dark-grey, heavily armored dreadnoughts and cruisers is assembling against a backdrop of a swirling deep-purple and magenta nebula. The rear thrusters of the distant ships glow intensely with fiery orange light. \[Shot 2] At 00:02.800, the camera cuts to a medium close-up of the captain from Shot 1 in profile facing right, while the camera shakes strongly. Her facial features are now visible, revealing a woman in her late forties with sharp cheekbones and a stoic expression. A sudden, blinding flash of brilliant cyan and white light bursts through the window as the fleet outside simultaneously jumps into warp, casting harsh, overexposed illumination across her face. The bridge vibrates violently, causing her shoulders to tense and her uniform collar to tremble. The intense light instantly fades into deep shadow, leaving her completely alone against the newly emptied, pitch-black void of space.\\noverall\_soundscape: Deep, resonant low-frequency thrumming of ship engines, overlaid with rhythmic, high-pitched electronic beeps from the consoles, followed by a sudden, deafening sub-bass boom and a loud, sizzling crackle as the warp drives engage. The immense acoustic impact causes a heavy, metallic clattering of the bridge panels, which instantly drops off into a stark, quiet mechanical hum.\\nnon\_diegetic\_music: Symphonic orchestral score, beginning with a slow, rising brass and string crescendo that abruptly cuts off, instantly transitioning into a single, sustained, low-register solo cello note with no dynamic swell."

&#x20;               },

&#x20;               "duration": 5,

&#x20;               "usage": {

&#x20;                 "total\_tokens": 9090,

&#x20;                 "prompt\_tokens": 5664,

&#x20;                 "completion\_tokens": 3426

&#x20;               },

&#x20;               "ratio": "16:9",

&#x20;               "task\_type": "h3\_context\_ir",

&#x20;               "modality": "text"

&#x20;             }

&#x20;           }



&#x20;           ```

&#x20;         content:

&#x20;           application/json:

&#x20;             schema:

&#x20;               $ref: '#/components/schemas/VideoGenerationV2Resp'

&#x20;       '400':

&#x20;         $ref: '#/components/responses/Err400'

&#x20;       '401':

&#x20;         $ref: '#/components/responses/Err401'

&#x20;       '402':

&#x20;         $ref: '#/components/responses/Err402'

&#x20;       '422':

&#x20;         $ref: '#/components/responses/Err422'

&#x20;       '429':

&#x20;         $ref: '#/components/responses/Err429'

&#x20;       '500':

&#x20;         $ref: '#/components/responses/Err500'

components:

&#x20; schemas:

&#x20;   H3ContextIRReq:

&#x20;     type: object

&#x20;     description: 创建 H3-Context-IR 任务的请求参数。

&#x20;     required:

&#x20;       - model

&#x20;       - content

&#x20;       - duration

&#x20;     properties:

&#x20;       model:

&#x20;         type: string

&#x20;         description: 模型名称。当前可用值：`MiniMax-H3`。

&#x20;         enum:

&#x20;           - MiniMax-H3

&#x20;       content:

&#x20;         type: array

&#x20;         description: >-

&#x20;           多模态上下文输入数组，用于描述目标视频及各类素材之间的关系。每个元素通过 `type` 区分类型（`text` /

&#x20;           `image\_url` / `video\_url` / `audio\_url`），并可通过 `role` 标注用途。





&#x20;           \*\*每次请求必须包含一个非空 `text` 项（prompt 必填）\*\*；缺失会返回参数错误。





&#x20;           支持的输入组合（对应不同生成场景）：



&#x20;           - \*\*文生视频\*\*：仅一个 `text` 元素。



&#x20;           - \*\*图生视频-首帧\*\*：`text` + 1 张 `image\_url`（`role=first\_frame` 或不填）。



&#x20;           - \*\*图生视频-尾帧\*\*：`text` + 1 张 `image\_url`（`role=last\_frame`）。



&#x20;           - \*\*图生视频-首尾帧\*\*：`text` + 2 张 `image\_url`（`role` 分别为

&#x20;           `first\_frame`、`last\_frame`）。



&#x20;           - \*\*多模态参考生视频\*\*：`text` + 参考图片（`role=reference\_image`）+

&#x20;           参考视频（`role=reference\_video`）+ 参考音频（`role=reference\_audio`）的组合。





&#x20;           > \*\*图生视频与多模态参考生视频互斥\*\*：content 中出现 `reference\_image` /

&#x20;           `reference\_video` / `reference\_audio` 任一 role，就不能再出现 `first\_frame` /

&#x20;           `last\_frame`（反之亦然），二者不可混用。





&#x20;           ---





&#x20;           \*\*输入媒体限制\*\*（请求体总大小 ≤ 64 MB，大文件请用公网 URL，勿用 Base64）





&#x20;           图片 `image\_url`：





&#x20;           | 项 | 限制 |



&#x20;           | :--- | :--- |



&#x20;           | 格式 | JPG、JPEG、PNG、WEBP、HEIC、HEIF |



&#x20;           | 单文件大小 | ≤ 30 MB |



&#x20;           | 宽高范围 | \[256, 5760] px |



&#x20;           | 长宽比（宽/高） | \[0.4, 2.5] |



&#x20;           | 数量 | 首帧 ≤ 1、尾帧 ≤ 1、参考图 ≤ 9 |





&#x20;           视频 `video\_url`（仅多模态参考场景）：





&#x20;           | 项 | 限制 |



&#x20;           | :--- | :--- |



&#x20;           | 容器 / 格式 | MP4（`.mp4`）、MOV（`.mov`） |



&#x20;           | 编码 | 视频 H.264/AVC、H.265/HEVC；音频 AAC、MP3 |



&#x20;           | 单文件大小 | ≤ 50 MB |



&#x20;           | 个数 | ≤ 3 |



&#x20;           | 单段时长 | \[2, 15] s；总时长 ≤ 15 s |



&#x20;           | 宽高范围 | \[256, 5760] px |



&#x20;           | 长宽比（宽/高） | \[0.4, 2.5] |



&#x20;           | 帧率 | \[23.976, 60] |





&#x20;           音频 `audio\_url`（仅多模态参考场景）：





&#x20;           | 项 | 限制 |



&#x20;           | :--- | :--- |



&#x20;           | 格式 | WAV、MP3 |



&#x20;           | 单文件大小 | ≤ 15 MB |



&#x20;           | 个数 | ≤ 3 |



&#x20;           | 单段时长 | \[2, 15] s；总时长 ≤ 15 s |

&#x20;         items:

&#x20;           $ref: '#/components/schemas/ContentItem'

&#x20;       duration:

&#x20;         type: integer

&#x20;         description: 目标视频时长（秒），必选，整数。可用值：`4`\~`15`。

&#x20;         enum:

&#x20;           - 4

&#x20;           - 5

&#x20;           - 6

&#x20;           - 7

&#x20;           - 8

&#x20;           - 9

&#x20;           - 10

&#x20;           - 11

&#x20;           - 12

&#x20;           - 13

&#x20;           - 14

&#x20;           - 15

&#x20;       ratio:

&#x20;         type: string

&#x20;         description: >-

&#x20;           目标视频的宽高比，默认

&#x20;           `adaptive`。可用值：`adaptive`、`21:9`、`16:9`、`4:3`、`1:1`、`3:4`、`9:16`。





&#x20;           \*\*文生视频（t2va，content 仅含 `text`）\*\*：`ratio` 必填，且不能为 `adaptive`；可用值

&#x20;           `21:9`、`16:9`、`4:3`、`1:1`、`3:4`、`9:16`。





&#x20;           \*\*图生视频（i2va，content 含 `first\_frame` / `last\_frame`

&#x20;           图片）\*\*：宽高比由输入图片决定，`ratio` 恒为 `adaptive`；传入其他合理值不会报错，但会被忽略并按

&#x20;           `adaptive` 处理。





&#x20;           \*\*多模态参考生视频（r2va，content 含 `reference\_image` / `reference\_video` /

&#x20;           `reference\_audio`）\*\*：`ratio` 可选，默认 `adaptive`；也可显式指定上述任一具体比例。

&#x20;         enum:

&#x20;           - adaptive

&#x20;           - '21:9'

&#x20;           - '16:9'

&#x20;           - '4:3'

&#x20;           - '1:1'

&#x20;           - '3:4'

&#x20;           - '9:16'

&#x20;       callback\_url:

&#x20;         type: string

&#x20;         description: >-

&#x20;           任务状态变更的回调通知地址。配置后 MiniMax 服务器会先发送含 `challenge` 字段的验证请求（需 3 秒内原样返回

&#x20;           `challenge` 完成验证），验证成功后每当任务状态变更即向该地址 POST

&#x20;           推送，推送体结构与\[查询任务](/api-reference/video-generation-v2-query)接口的响应一致。





&#x20;           回调 `status`

&#x20;           取值：`queued`（排队中）、`running`（运行中）、`succeeded`（成功）、`failed`（失败）、`cancelled`（已取消）。

&#x20;     example:

&#x20;       model: MiniMax-H3

&#x20;       content:

&#x20;         - type: text

&#x20;           text: 一个男孩在海边打篮球

&#x20;       duration: 5

&#x20;       ratio: '16:9'

&#x20;   VideoGenerationV2Resp:

&#x20;     type: object

&#x20;     properties:

&#x20;       task\_id:

&#x20;         type: string

&#x20;         description: 任务 ID，用于后续查询任务状态与结果。

&#x20;     example:

&#x20;       task\_id: '424010985738629'

&#x20;   ContentItem:

&#x20;     type: object

&#x20;     required:

&#x20;       - type

&#x20;     properties:

&#x20;       type:

&#x20;         type: string

&#x20;         description: 输入内容的类型。

&#x20;         enum:

&#x20;           - text

&#x20;           - image\_url

&#x20;           - video\_url

&#x20;           - audio\_url

&#x20;       text:

&#x20;         type: string

&#x20;         description: >-

&#x20;           文本提示词（prompt），\*\*必填\*\*：所有场景都需包含一个非空 `text`，描述期望生成的视频。按字符数计算长度，单个

&#x20;           `text` 最多 7000 个字符。

&#x20;       image\_url:

&#x20;         type: object

&#x20;         description: 当 `type=image\_url` 时的图片对象（格式 / 大小 / 尺寸 / 数量限制见上方 content 说明）。

&#x20;         required:

&#x20;           - url

&#x20;         properties:

&#x20;           url:

&#x20;             type: string

&#x20;             description: >-

&#x20;               图片地址,支持:公网 URL;`mm\_file://{file\_id}`(引用平台已有文件,如上传或历史产物的

&#x20;               file\_id);`data:image/<格式>;base64,<Base64>` data URI(`<格式>` 小写)。

&#x20;       video\_url:

&#x20;         type: object

&#x20;         description: >-

&#x20;           当 `type=video\_url` 时的视频对象（参考视频，仅多模态参考场景；格式 / 大小 / 时长限制见上方 content

&#x20;           说明）。

&#x20;         required:

&#x20;           - url

&#x20;         properties:

&#x20;           url:

&#x20;             type: string

&#x20;             description: >-

&#x20;               视频地址,支持:公网 URL;`mm\_file://{file\_id}`(引用平台已有文件的

&#x20;               file\_id);`data:video/mp4;base64,<Base64>` data URI。注意请求体总大小 ≤ 64

&#x20;               MB、Base64 会放大约 33%,大视频请用公网 URL 或 mm\_file://。

&#x20;       audio\_url:

&#x20;         type: object

&#x20;         description: >-

&#x20;           当 `type=audio\_url` 时的音频对象（参考音频，仅多模态参考场景；格式 / 大小 / 时长限制见上方 content

&#x20;           说明）。

&#x20;         required:

&#x20;           - url

&#x20;         properties:

&#x20;           url:

&#x20;             type: string

&#x20;             description: >-

&#x20;               音频地址,支持:公网 URL;`mm\_file://{file\_id}`(引用平台已有文件的

&#x20;               file\_id);`data:audio/<格式>;base64,<Base64>` data URI(`<格式>` 小写)。

&#x20;       role:

&#x20;         type: string

&#x20;         description: |-

&#x20;           内容的位置或用途，条件必填：

&#x20;           - `first\_frame`：首帧图片（图生视频；仅一张图且不填 role 时默认按 first\_frame 处理）。

&#x20;           - `last\_frame`：尾帧图片（图生视频-首尾帧，需与 first\_frame 成对）。

&#x20;           - `reference\_image`：参考图片（多模态参考生视频）。

&#x20;           - `reference\_video`：参考视频（多模态参考生视频）。

&#x20;           - `reference\_audio`：参考音频（多模态参考生视频）。

&#x20;         enum:

&#x20;           - first\_frame

&#x20;           - last\_frame

&#x20;           - reference\_image

&#x20;           - reference\_video

&#x20;           - reference\_audio

&#x20;   OaiError:

&#x20;     type: object

&#x20;     description: OpenAI 风格错误响应。出错时 HTTP 状态码为真实错误码(401/400/429/402/422/500…),响应体为该结构。

&#x20;     properties:

&#x20;       type:

&#x20;         type: string

&#x20;         description: 固定为 `error`。

&#x20;         example: error

&#x20;       error:

&#x20;         $ref: '#/components/schemas/OaiErrorDetail'

&#x20;       request\_id:

&#x20;         type: string

&#x20;         description: 请求追踪 ID(便于排查)。

&#x20;   OaiErrorDetail:

&#x20;     type: object

&#x20;     properties:

&#x20;       type:

&#x20;         type: string

&#x20;         description: >-

&#x20;           错误类型:`authorized\_error`(401)/`bad\_request\_error`(400)/`rate\_limit\_error`(429)/`insufficient\_balance\_error`(402)/`unprocessable\_entity\_error`(422)/`overloaded\_error`(529)/`server\_error`(500)

&#x20;           等。

&#x20;       message:

&#x20;         type: string

&#x20;         description: 错误详情,结尾括号内为内部错误码(如 `... (1004)`)。

&#x20;       http\_code:

&#x20;         type: string

&#x20;         description: HTTP 状态码字符串,如 `401`。

&#x20; responses:

&#x20;   Err400:

&#x20;     description: 参数错误

&#x20;     content:

&#x20;       application/json:

&#x20;         schema:

&#x20;           $ref: '#/components/schemas/OaiError'

&#x20;         example:

&#x20;           type: error

&#x20;           error:

&#x20;             type: bad\_request\_error

&#x20;             message: >-

&#x20;               invalid params, content must include a non-empty text item

&#x20;               (prompt is required) (2013)

&#x20;             http\_code: '400'

&#x20;           request\_id: 021785229015510a2c883cf675b9804d

&#x20;   Err401:

&#x20;     description: 鉴权失败

&#x20;     content:

&#x20;       application/json:

&#x20;         schema:

&#x20;           $ref: '#/components/schemas/OaiError'

&#x20;         example:

&#x20;           type: error

&#x20;           error:

&#x20;             type: authorized\_error

&#x20;             message: >-

&#x20;               login fail: Please carry the API secret key in the

&#x20;               'Authorization' field of the request header (1004)

&#x20;             http\_code: '401'

&#x20;           request\_id: 021785229015510a2c883cf675b9804d

&#x20;   Err402:

&#x20;     description: 余额/额度不足

&#x20;     content:

&#x20;       application/json:

&#x20;         schema:

&#x20;           $ref: '#/components/schemas/OaiError'

&#x20;         example:

&#x20;           type: error

&#x20;           error:

&#x20;             type: insufficient\_balance\_error

&#x20;             message: insufficient balance (1008)

&#x20;             http\_code: '402'

&#x20;           request\_id: 021785229015510a2c883cf675b9804d

&#x20;   Err422:

&#x20;     description: 输入涉及敏感内容

&#x20;     content:

&#x20;       application/json:

&#x20;         schema:

&#x20;           $ref: '#/components/schemas/OaiError'

&#x20;         example:

&#x20;           type: error

&#x20;           error:

&#x20;             type: unprocessable\_entity\_error

&#x20;             message: video description contains sensitive content (1026)

&#x20;             http\_code: '422'

&#x20;           request\_id: 021785229015510a2c883cf675b9804d

&#x20;   Err429:

&#x20;     description: 触发限流

&#x20;     content:

&#x20;       application/json:

&#x20;         schema:

&#x20;           $ref: '#/components/schemas/OaiError'

&#x20;         example:

&#x20;           type: error

&#x20;           error:

&#x20;             type: rate\_limit\_error

&#x20;             message: rate limit, please retry later (1002)

&#x20;             http\_code: '429'

&#x20;           request\_id: 021785229015510a2c883cf675b9804d

&#x20;   Err500:

&#x20;     description: 服务端错误

&#x20;     content:

&#x20;       application/json:

&#x20;         schema:

&#x20;           $ref: '#/components/schemas/OaiError'

&#x20;         example:

&#x20;           type: error

&#x20;           error:

&#x20;             type: server\_error

&#x20;             message: internal error (1000)

&#x20;             http\_code: '500'

&#x20;           request\_id: 021785229015510a2c883cf675b9804d

&#x20; securitySchemes:

&#x20;   bearerAuth:

&#x20;     type: http

&#x20;     scheme: bearer

&#x20;     bearerFormat: JWT

&#x20;     description: |-

&#x20;       `HTTP: Bearer Auth`

&#x20;        - Security Scheme Type: http

&#x20;        - HTTP Authorization Scheme: Bearer API\_key，用于验证账户信息，可在 \[账户管理>接口密钥](https://platform.minimaxi.com/user-center/basic-information/interface-key) 中查看。



````

