**特性开发指导书**

Frontpage 搜索词 \+ Transcriptions 5列并排 \+ Combined Keywords & Sentence（Next.js \+ FastAPI \+ llama.cpp）

日期：2026-02-08

# **1\. 目标与范围**

本指导书描述一个可落地实现的功能：在首页展示可点击的搜索词，并新增转录页（Transcriptions）以最多 5 列并排展示视频转录，同时基于 Meta-Llama-3.1-8B（llama.cpp 部署）抽取并融合关键词与证据句，提升跨视频的内容关联与整合。

## **1.1 目标**

* 首页保持 3 列视频布局不变，在页面右侧展示 Search word（搜索词），支持点击跳转到转录页。  
* 新增 Transcriptions 页面：最多 5 个视频转录并排展示（最多 5 列）。  
* Transcriptions 顶部展示：Search word、从 combined transcription 提取的 5 个 combined keyword tags、以及由关键词所在句子拼接的 combined sentence。  
* 关键词提取使用 Meta-Llama-3.1-8B：LLM 负责语义相关性 Score；程序侧负责 Occurrence Counting（Count）并执行 Score→Count 排序与覆盖补偿。

## **1.2 非目标（本期不做）**

* 不做搜索召回/排序的大改（默认使用现有 Top-N 返回逻辑）。  
* 不做复杂多语言同义词体系（只提供轻量可配置映射）。  
* 不对转录文本进行改写/生成式摘要（combined sentence 只抽取原句并合并）。

# **2\. 用户体验与页面规格**

## **2.1 Frontpage（首页）**

### **布局**

* 视频卡片区：维持 3 列栅格（不变）。  
* 右侧栏：新增 Search word 卡片/侧栏区域。无 query 时可隐藏或显示占位提示。

### **交互**

* Search word 可点击，跳转到 /transcriptions?query={query}。

## **2.2 Transcriptions 页面**

### **顶部信息区**

* 第一行：Search word: {query}  
* 第二行：Combined keywords（5 个 tag）  
* 第三行：Combined sentence（由 5 个 tag 对应句子合并得到，可折叠/展开）

### **主体并排区（最多 5 列）**

* 每列对应一个视频：列头可包含标题/来源；列头下方显示该列 keywords tags（建议 3-5 个）。  
* 列内展示转录文本（可滚动）。  
* 提供下载本列转录按钮（可选：一键下载全部）。

### **响应式建议**

* \>= 1280px：5 列栅格；中等宽度可 2-3 列；窄屏可改为横向滚动或折行。

# **3\. 数据流与系统边界**

建议由后端提供聚合接口：输入 query，输出 Top5 videos \+ transcripts \+ combined/column keywords \+ combined sentence。前端仅负责渲染与下载。

## **3.1 核心数据实体**

* Video: { videoId, title, ... }  
* Transcript: { videoId, text }  
* Keyword: { term, score, count }

## **3.2 流程概览**

1. Frontpage：用户搜索得到 query 与视频列表（3 列展示）。  
2. 用户点击右侧 Search word，跳转到 /transcriptions?query=...  
3. Transcriptions 页面加载后请求后端聚合接口，获取 Top5 视频及转录。  
4. 后端生成 combined transcription（拼接 T1..TN），调用 llama.cpp 抽取候选关键词与 score；程序侧计算 count 与排序。  
5. 执行覆盖补偿（确保每条转录尽量至少命中 1 个 combined keyword；同时保护核心主题词）。  
6. 从 combined transcription 中抽取 5 个关键词所在句子合并为 combined sentence。  
7. 返回前端渲染所需 JSON。

# **4\. 接口设计（FastAPI）**

## **4.1 聚合接口**

GET /api/transcriptions?query={query}\&limit=5

返回结构示例：

{

  "query": "Gemini",

  "videos": \[

    {

      "videoId": "v1",

      "title": "...",

      "transcription": "...",

      "keywords": \[

        {"term":"gemini","score":0.92,"count":8}

      \]

    }

  \],

  "combined": {

    "keywords": \[

      {"term":"gemini","score":0.92,"count":22}

    \],

    "sentence": "..."

  },

  "meta": {

    "llm": "llama.cpp:Meta-Llama-3.1-8B",

    "replaceCount": 1,

    "coverage": \[true,true,true,true,true\]

  }

}

# **5\. LLM（Meta-Llama-3.1-8B）关键词提取规范**

## **5.1 输出约束（强制 JSON）**

* LLM 仅输出 term 与 score；count 由程序侧计算（避免幻觉）。  
* term：小写、无标点，英文短语 1-5 词（中文 2-8 字/词组），避免泛词。  
* 输出必须是纯 JSON（不含 markdown / 解释文字），便于可靠解析。  
* 候选数量：combined 50；单条 30（后续再筛 Top5 / TopK）。

## **5.2 Prompt 模板（通用）**

You are an information extraction system.

Task: Extract candidate keywords/phrases that are highly relevant to the search query.

Rules:

\- Output MUST be valid JSON only. No markdown, no extra text.

\- Provide exactly {K} candidate keywords/phrases.

\- Each keyword is 1-5 words, lowercase, no punctuation.

\- Prefer specific entities/concepts; avoid generic words (video, today, people, thing).

\- Score is semantic relevance to the query on \[0,1\]. Higher is more relevant.

\- Do NOT include counts.

\- Do NOT include duplicates (same meaning).

Query: "{QUERY}"

Transcript:

"""

{TEXT}

"""

Return JSON:

{

  "query": "{QUERY}",

  "keywords": \[

    {"term":"...", "score":0.0}

  \]

}

# **6\. 程序侧算法：Count、排序、覆盖补偿、证据句**

## **6.1 基本参数（建议默认值）**

| 参数 | 默认值/说明 |
| :---- | :---- |
| TOPK | 5（combined keywords 数量） |
| COL\_K | 5（每列显示 keywords 数量，建议 3-5） |
| CORE\_KEEP | 2（保护 combined 最强前 2 个词不被替换，防止主题漂移） |
| MAX\_REPLACE | 3（最多替换次数，避免 Top5 完全碎片化） |

## **6.2 关键原则**

* Score 由 LLM 提供，Count 由程序侧在原文中真实计数。  
* 统一排序：Score DESC → Count DESC → term ASC。  
* 过滤掉 count=0 的关键词（LLM 可能产出文本中未出现的词）。  
* 覆盖补偿目标：尽量让每条转录至少命中 1 个 combined keyword，同时保留全局核心主题。

## **6.3 伪代码（核心流程）**

CONST TOPK \= 5

CONST CORE\_KEEP \= 2

CONST MAX\_REPLACE \= 3

CONST COL\_K \= 5

\# 输入：query, transcripts\[\<=5\]

\# 输出：combinedTop5, perColumnKeywords, combinedSentence

1\) perKw\[i\] \= LLM.extract\_keywords(query, Ti, K=30)

2\) combinedKw \= LLM.extract\_keywords(query, Tc=concat(T1..Tn), K=50)

3\) 对 perKw\[i\] 与 combinedKw：

   \- normalize term（lowercase、去标点、同义映射）

   \- merge duplicate terms（score 取 max，count 后算）

   \- count \= occurrence(term in text)

   \- filter count==0

   \- sort by (score desc, count desc)

4\) combinedTop \= top5(combinedKw)

5\) 覆盖补偿（最多 MAX\_REPLACE 次）:

   while replaceCount \< MAX\_REPLACE:

       找到第一条未覆盖的 Ti（combinedTop 中没有任何 term 在 Ti 出现）

       若不存在：break

       candidate \= Ti 中排序最高且不在 combinedTop 的 term

       removeIdx \= 在 combinedTop 中选择“最该被删”的 term（idx \< CORE\_KEEP 不可删）

           删除优先级：coverageCount asc, score asc, count asc

       combinedTop.remove(removeIdx)

       combinedTop.add(candidate)

       combinedTop \= sort(combinedTop)

       replaceCount \+= 1

6\) perColumnKeywords\[i\] \= top COL\_K from perKw\[i\]

7\) combinedSentence：

   \- split Tc into sentences

   \- for each term in combinedTop: pick first sentence containing term

   \- dedupe sentences

   \- join to one paragraph

## **6.4 删除策略说明（边际贡献最小）**

与“固定删除第 5 名”相比，推荐删除策略为：删除覆盖贡献最小且分数较低的关键词，从而在满足覆盖的同时最大化整合质量。

* coverageCount(term) \= 命中该 term 的转录条数（1..N）  
* 删除优先级：coverageCount 越小越先删；若相同则 score 越低越先删；再比较 count。  
* 保护 combinedTop 排名前 CORE\_KEEP 的核心主题词不被替换。

## **6.5 Combined sentence 生成**

* 句子切分：按 。！？.\!? 与换行切分。  
* 对 combinedTop5 的每个关键词：在 combined transcription 中定位其所在句子，取第一条作为证据句。  
* 对证据句去重后合并展示（不改写、不生成新句子）。

# **7\. 工程实现（Next.js \+ FastAPI \+ llama.cpp）**

## **7.1 后端模块建议**

* routers/transcriptions.py：聚合接口 /api/transcriptions  
* services/search\_service.py：根据 query 拉取 Top5 videos \+ transcripts（复用现有搜索逻辑）  
* services/llm\_llamacpp.py：llama.cpp HTTP 调用（JSON-only \+ 重试）  
* services/keyword\_service.py：count/merge/sort/coverage/combined sentence  
* services/cache.py：缓存（先内存，后续可 Redis）  
* schemas.py：Pydantic 响应模型

## **7.2 llama.cpp 调用要点**

* 使用 llama-server 提供 OpenAI 兼容 /v1/chat/completions 接口，便于 FastAPI 调用。  
* temperature 建议 0.0-0.2；Prompt 强约束 JSON only；解析失败重试 1 次。  
* 并发：一次请求最多 6 次 LLM 调用（combined 1 \+ per transcript 5），建议并发但限流（Semaphore）。

## **7.3 缓存与降级**

* 缓存键建议包含 query 与视频集合（或 query+limit）。常见 query 重复请求收益很高。  
* LLM 超时/失败：降级为纯统计关键词（TF-IDF/RAKE），或返回空 keywords 但页面可用。

## **7.4 前端实现要点（Next.js）**

* Frontpage：维持 3 列视频 grid；右侧 Search word 卡片可点击跳转。  
* Transcriptions：从 URL 读取 query，调用 /api/transcriptions 拉取数据；顶部渲染 combined 区；主体按最多 5 列并排显示。  
* 下载按钮：前端将 transcription 文本生成 Blob（text/plain）触发下载。

# **8\. 验收标准（Acceptance Criteria）**

## **8.1 功能验收**

* 首页：视频仍为 3 列；右侧显示 search word；点击可跳转到转录页并携带 query。  
* 转录页：最多 5 列并排显示；每列顶部显示该列关键词 tags；列内可滚动阅读转录。  
* 顶部 combined 区：显示 query、combined 5 个 tags、combined sentence。  
* 排序规则：Score 优先于 Count；count 必须来自程序侧统计。  
* 覆盖补偿：未覆盖的转录在 MAX\_REPLACE 与 CORE\_KEEP 约束下尽量补齐覆盖。

## **8.2 质量验收**

* combinedTop5 不包含明显泛词（如 video/today/people）。  
* combined sentence 中每个句子都能在原转录中找到（不可凭空生成）。  
* 主题一致时：combinedTop5 应稳定集中在主主题；主题分叉时：能兼顾覆盖并保留核心主题词。