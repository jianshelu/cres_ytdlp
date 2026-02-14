# Combined Keywords 功能（愿景 + 当前交付）

最后更新：2026-02-14

## 1. 产品愿景（目标）

该功能面向“按查询词聚合理解视频内容”的体验，目标是：
- 首页提供查询词入口，并可快速跳转到转录页。
- 转录页集中展示 combined keywords、证据句（key sentences）与分视频转录上下文。
- 关键词由 LLM 做语义打分，程序侧做真实出现次数统计，并进行覆盖补偿。
- 用户可以高效地浏览、跳转和下载转录内容。

## 2. 交付状态（当前基线）

| 能力 | 状态 | 当前实现 |
|---|---|---|
| 查询词 -> 转录页跳转 | 已实现 | 首页 query chip 跳转到 `/transcriptions?query=...&limit=...` |
| Combined 关键词抽取（LLM + count） | 已实现 | FastAPI + `keyword_service` + llama.cpp 回退路径 |
| 覆盖补偿（CORE_KEEP / MAX_REPLACE） | 已实现 | 后端回退流程中执行 |
| Combined sentence + key sentence items | 已实现 | `sentence_service` 生成带来源映射的证据句 |
| Combined 视频播放 | 已实现 | 优先使用服务端 `combined_video_url`，否则前端动态拼接片段 |
| Top 结果转录浏览 | 已实现 | Top-5 采用 carousel + 关键词高亮 + 跳转 |
| 固定并排 5 列转录板 | 规划增强 | 当前基线为 carousel，可增加“5 列模式”切换 |
| 首页右侧 Search word 独立侧栏 | 规划增强 | 当前基线为 query 行视图，后续可叠加侧栏 |

## 3. API 契约（已实现）

### 3.1 接口

- `GET /api/transcriptions?query=<query>&limit=<1..50>`
- `limit` 默认值为 `50`。
- Combined 关键词列表仍为 top-5（`TOPK = 5`）。

### 3.2 返回结构

```json
{
  "query": "...",
  "videos": [
    {
      "videoId": "...",
      "title": "...",
      "transcription": "...",
      "keywords": [{ "term": "...", "score": 0.0, "count": 0 }],
      "videoPath": "...",
      "segments": []
    }
  ],
  "combined": {
    "keywords": [{ "term": "...", "score": 0.0, "count": 0 }],
    "sentence": "...",
    "key_sentences": [
      {
        "id": 0,
        "sentence": "...",
        "keyword": "...",
        "source_index": 0,
        "source_title": "..."
      }
    ],
    "combined_video_url": "...",
    "recombined_sentence": false,
    "sentence_version": ""
  },
  "meta": {
    "llm": "llama.cpp:Meta-Llama-3.1-8B",
    "replaceCount": 0,
    "coverage": [true],
    "cache": "hit"
  }
}
```

## 4. 后端处理流程（已实现）

1. 读取 `web/src/data.json`。
2. 按 `search_query` 做大小写不敏感的精确匹配过滤。
3. 取前 `limit` 条（最大 50）。
4. 并发拉取 transcript payload（`text`、可选 `keywords`、可选 `segments`）。
5. 从 transcript payload 的关键词构造 per-video 初始关键词。
6. Combined 关键词来源：
   - 快路径：优先读取 MinIO 的 combined 输出。
   - 回退路径：调用 llama.cpp 做提取。
7. 做关键词标准化/质量过滤/语言过滤，并统计出现次数。
8. 必要时执行覆盖补偿。
9. 生成 combined sentence 与结构化 key sentence items。
10. 返回响应并写入缓存。

## 5. 关键词与证据句逻辑（已实现）

- 参数：
  - `TOPK = 5`
  - `COL_K = 5`
  - `CORE_KEEP = 2`
  - `MAX_REPLACE = 3`
- 排序：
  - `score DESC`，再 `count DESC`，再 `term ASC`。
- 过滤：
  - 低质量/泛词过滤
  - 按 query 语言做兼容性过滤
- 证据句抽取：
  - 先按标点/换行切句
  - 优先“每条 transcript 至少一句”
  - 不足时全局回填，最多 5 句

## 6. 缓存与超时行为（已实现）

- 前端代理超时（`web/src/app/api/transcriptions/route.ts`）：`90s`。
- 后端路由回退分支中的 LLM 提取超时保护：`3s`。
- 后端内存缓存默认：
  - TTL `600s`
  - 最大项数 `128`
- 启用时支持 MinIO 缓存。
- `meta.cache`：`hit` / `miss` / `disabled`。

## 7. 下一阶段升级路径（不破坏契约）

1. 在保留当前 query 行视图的基础上，增加首页右侧 Search word 面板。
2. 在保留当前 carousel 的基础上，增加“5 列并排”视图切换。
3. 保持 `/api/transcriptions` 契约稳定，避免前后端反复联调成本。

## 8. 事实来源文件

- 后端 API：`src/api/routers/transcriptions.py`
- 关键词逻辑：`src/backend/services/keyword_service.py`
- 证据句逻辑：`src/backend/services/sentence_service.py`
- LLM 客户端：`src/backend/services/llm_llamacpp.py`
- 前端页面：`web/src/app/transcriptions/page.tsx`
- 前端交互：`web/src/app/transcriptions/TranscriptionsClient.tsx`
- 前端 API 代理：`web/src/app/api/transcriptions/route.ts`