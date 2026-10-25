# Minimax Video Dispatch

## 核心作用

本 skill 是 `/minimax-storyboard` 的下游调度层，负责把导演总表和 SEG 资产包提交给视频生成平台（Minimax 官方 或 秘塔中转站），并按批次控制风险。

## 触发条件

- `/minimax-storyboard` 阶段 F 已完成，导演总表和 SEG asset pack 已锁定。
- 用户要求"开始生成视频"、"提交 Minimax H3 生成"或"生成 SEG 视频"。

## 使用前必须先拿到

1. **平台选择**：Minimax 官方 / 秘塔中转站。
2. **生成模式**：t2va / i2va / r2va / regeneration / h3_context_ir。
3. **分辨率**：2K / 768P。
4. **比例**：9:16 / 16:9 / adaptive 等。
5. **SEG 范围**：先生成哪几个 SEG。

## 固定执行流程

```text
1. 读取 asset pack 和导演总表。
2. 询问用户是否需要重新查询 Minimax 官方最新价格。
   - 需要 → 调用 WebSearch 查询并更新 references/平台配置与价格.md。
   - 不需要 → 使用本地记录的价格。
3. 向用户展示两个平台的价格明细。
4. 询问用户使用哪个平台。
5. 如果选择秘塔中转站，向用户确认使用哪一个 API Key（用户可能提供多个 key）。**选定后本次任务全程只能使用该 key，禁止私自切换。**
6. 询问生成分辨率、比例、模式。
7. 计算总 SEG 数、预估费用、预计总时长。
8. 第一批：生成 ≤4 个 SEG。
9. 轮询任务状态，下载产物到本地。
10. 向用户展示第一批结果，等待确认。
11. 第二批：再生成 10 个 SEG。
12. 等待用户确认。
13. 询问用户：全量生成剩余 / 继续分批生成 N 个 / 停止。
```

## 并发控制

- **秘塔中转站**：每个 API Key 的并发上限为 **4**。提交脚本必须保证同一 key 同时进行的任务数不超过 4。
- **Minimax 官方**：按官方文档的默认限流处理，本 skill 保持相邻任务间隔 1 秒。
- 当批次大小超过 key 的并发上限时，脚本内部自动排队，先提交前 4 个，有任务进入 running/queued 后再提交下一个。
- **严禁自动切换 key**：无论遇到 429、key 失效还是余额不足，都只能暂停并通知用户，由用户决定是否换 key。脚本不得在未获授权的情况下切换到 `METASO_API_KEY_2` 等其他 key。

## 支持的平台

| 平台 | Base URL | 鉴权方式 |
|---|---|---|
| Minimax 官方 | `https://api.minimaxi.com` | `Authorization: Bearer {MINIMAX_OFFICIAL_API_KEY}` |
| 秘塔中转站 | `https://metaso.cn/api/minimax` | `Authorization: Bearer {METASO_API_KEY}` |

## 支持的模式

详见 `references/生成模式说明.md`。

## 产物管理

详见 `references/产物管理规范.md`。

本 skill 只负责把生成产物下载到本地预定目录。产物上传 OSS、更新 manifest、登记 `doc/文件地址管理.md` 等资产管理操作，统一交给 `/minimax-story-package` 处理。生成后必须调用 `/minimax-story-package` 的 `scripts/register_outputs.py` 完成归档。

## 核心脚本

- `scripts/submit_video_batch.py`：提交一批视频生成任务。支持 `--metaso-key` 指定具体使用哪个秘塔 API Key。
- `scripts/query_video_tasks.py`：批量查询任务状态并下载产物。需与提交时使用相同的 `--metaso-key`。
- `scripts/build_video_prompts.py`：从 storyboard 产物组装 prompt 和 content 数组。
- `scripts/estimate_cost.py`：根据批次和参数估算费用。
- `scripts/archive_video_outputs.py`：下载并归档生成产物。

### 秘塔多 Key 调用示例

```bash
# 使用第 1 个秘塔 key 提交前 4 个 SEG
python scripts/submit_video_batch.py \
  --manifest-dir "00_元数据/清单" \
  --segments SEG-01 SEG-02 SEG-03 SEG-04 \
  --platform metaso \
  --metaso-key METASO_API_KEY_1 \
  --output-log "00_元数据/清单/video_submission_log.json"

# 使用同一个 key 查询
python scripts/query_video_tasks.py \
  --submission-log "00_元数据/清单/video_submission_log.json" \
  --platform metaso \
  --metaso-key METASO_API_KEY_1
```

## 参考文档

- `references/平台配置与价格.md`
- `references/生成模式说明.md`
- `references/官方文档/`（原始 Minimax H3 API 文档，含创建任务、查询、取消等）
- `references/分批生成策略.md`
- `references/产物管理规范.md`
- `references/错误处理与重试.md`
- `references/与minimax-storyboard衔接.md`
