#!/usr/bin/env python3
"""
End-to-end test driver:
1) Query Google News (Chinese or English AI news).
2) Extract top N keywords from headlines.
3) Trigger backend /batch for each keyword with max_duration_minutes <= 10.
4) Save a JSON report for auditing.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import pathlib
import re
import sys
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from typing import Any

import requests


GOOGLE_NEWS_RSS = "https://news.google.com/rss/search"
DEFAULT_SEED_QUERY = "中国 人工智能 大模型 科技 新闻"
DEFAULT_EN_SEED_QUERY = "AI technology news"

# Keep this list small and practical. It removes high-frequency function words.
ZH_STOPWORDS = {
    "我们",
    "你们",
    "他们",
    "这个",
    "那个",
    "以及",
    "因为",
    "所以",
    "可以",
    "一个",
    "没有",
    "如何",
    "正在",
    "已经",
    "最新",
    "发布",
    "宣布",
    "报道",
    "新闻",
    "视频",
    "中国",
}

FALLBACK_AI_KEYWORDS = [
    "人工智能",
    "大模型",
    "智能体",
    "算力",
    "芯片",
    "机器学习",
    "深度学习",
    "生成式AI",
    "多模态",
    "科技新闻",
]

EN_STOPWORDS = {
    "the", "and", "for", "that", "with", "from", "this", "will", "into", "after",
    "over", "about", "more", "than", "news", "today", "latest", "update", "updates",
    "says", "say", "new", "how", "why", "what", "when", "where", "their", "they",
    "you", "your", "our", "its", "are", "was", "were", "has", "have", "had", "been",
    "but", "not", "can", "could", "would", "should", "tech", "technology",
}

FALLBACK_EN_AI_KEYWORDS = [
    "artificial intelligence",
    "machine learning",
    "generative ai",
    "ai agents",
    "llm",
    "openai",
    "google ai",
    "microsoft ai",
]


@dataclass
class NewsItem:
    title: str
    link: str
    published: str


def _now_utc_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _safe_print(msg: str) -> None:
    try:
        print(msg)
    except UnicodeEncodeError:
        encoded = msg.encode("utf-8", errors="replace").decode("utf-8", errors="replace")
        print(encoded)


def fetch_google_news(
    seed_query: str,
    max_items: int,
    timeout: float,
    language: str,
) -> list[NewsItem]:
    language = (language or "zh").lower()
    if language == "en":
        hl = "en-US"
        gl = "US"
        ceid = "US:en"
    else:
        hl = "zh-CN"
        gl = "US"
        ceid = "US:zh-Hans"

    params = {
        "q": seed_query,
        "hl": hl,
        "gl": gl,
        "ceid": ceid,
    }
    resp = requests.get(GOOGLE_NEWS_RSS, params=params, timeout=timeout)
    resp.raise_for_status()

    root = ET.fromstring(resp.text)
    items: list[NewsItem] = []
    for item in root.findall("./channel/item"):
        title = (item.findtext("title") or "").strip()
        link = (item.findtext("link") or "").strip()
        pub = (item.findtext("pubDate") or "").strip()
        if not title:
            continue
        # RSS titles usually end with " - SourceName"
        title = re.sub(r"\s+-\s+[^-]+$", "", title).strip()
        items.append(NewsItem(title=title, link=link, published=pub))
        if len(items) >= max_items:
            break
    return items


def extract_keywords_from_titles(titles: list[str], top_n: int) -> list[str]:
    # score = 2 * frequency + title_coverage
    freq: dict[str, int] = {}
    cover: dict[str, int] = {}

    for title in titles:
        tokens = re.findall(r"[\u4e00-\u9fff]{2,6}", title)
        seen_in_title = set()
        for t in tokens:
            token = t.strip()
            if not token:
                continue
            if token in ZH_STOPWORDS:
                continue
            if "的" in token and len(token) >= 5:
                continue
            if len(token) < 2:
                continue
            freq[token] = freq.get(token, 0) + 1
            if token not in seen_in_title:
                cover[token] = cover.get(token, 0) + 1
                seen_in_title.add(token)

    ranked = sorted(
        freq.keys(),
        key=lambda k: (-(2 * freq.get(k, 0) + cover.get(k, 0)), -freq.get(k, 0), k),
    )

    # Bias toward AI-related terms if available.
    ai_terms = [
        "人工智能",
        "大模型",
        "模型",
        "算力",
        "芯片",
        "智能体",
        "千问",
        "文心",
        "腾讯",
        "阿里",
        "百度",
        "华为",
    ]
    prioritized = [k for k in ranked if any(t in k or k in t for t in ai_terms)]
    merged: list[str] = []
    for k in prioritized + ranked:
        if k not in merged:
            merged.append(k)
        if len(merged) >= top_n:
            break

    for fb in FALLBACK_AI_KEYWORDS:
        if fb not in merged:
            merged.append(fb)
        if len(merged) >= top_n:
            break

    return merged[:top_n]


def extract_english_keywords_from_titles(titles: list[str], top_n: int) -> list[str]:
    freq: dict[str, int] = {}
    cover: dict[str, int] = {}
    for title in titles:
        tokens = re.findall(r"[A-Za-z][A-Za-z0-9\-]{2,24}", title)
        seen_in_title = set()
        for t in tokens:
            token = t.lower().strip("-")
            if not token or token in EN_STOPWORDS:
                continue
            if token.isdigit():
                continue
            freq[token] = freq.get(token, 0) + 1
            if token not in seen_in_title:
                cover[token] = cover.get(token, 0) + 1
                seen_in_title.add(token)

    ranked = sorted(
        freq.keys(),
        key=lambda k: (-(2 * freq.get(k, 0) + cover.get(k, 0)), -freq.get(k, 0), k),
    )

    ai_hints = [
        "ai",
        "artificial",
        "intelligence",
        "machine",
        "learning",
        "agent",
        "agents",
        "llm",
        "openai",
        "google",
        "microsoft",
        "nvidia",
        "chip",
        "chips",
        "model",
        "models",
    ]
    prioritized = [k for k in ranked if any(h in k for h in ai_hints)]

    merged: list[str] = []
    for k in prioritized + ranked:
        if k not in merged:
            merged.append(k)
        if len(merged) >= top_n:
            break

    for fb in FALLBACK_EN_AI_KEYWORDS:
        if fb not in merged:
            merged.append(fb)
        if len(merged) >= top_n:
            break

    return merged[:top_n]


def trigger_batch(
    api_base: str,
    query: str,
    limit: int,
    max_duration_minutes: int,
    parallelism: int | None,
    timeout: float,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "query": query,
        "limit": limit,
        "max_duration_minutes": max_duration_minutes,
    }
    if parallelism is not None:
        payload["parallelism"] = parallelism

    r = requests.post(f"{api_base.rstrip('/')}/batch", json=payload, timeout=timeout)
    body: Any
    try:
        body = r.json()
    except Exception:
        body = {"raw": r.text}
    return {"status_code": r.status_code, "ok": r.ok, "response": body}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Google->Keywords->YouTube(<10min)->Batch pipeline test driver"
    )
    parser.add_argument("--api-base", default="http://localhost:8000", help="FastAPI base URL")
    parser.add_argument("--seed-query", default=DEFAULT_SEED_QUERY, help="Google news query")
    parser.add_argument(
        "--keyword-language",
        choices=["zh", "en"],
        default="zh",
        help="Keyword extraction language",
    )
    parser.add_argument("--news-count", type=int, default=30, help="How many news items to sample")
    parser.add_argument("--keyword-count", type=int, default=10, help="How many keywords to dispatch")
    parser.add_argument("--per-keyword-limit", type=int, default=3, help="YouTube videos per keyword")
    parser.add_argument(
        "--max-total-videos",
        type=int,
        default=30,
        help="Hard cap for total requested videos (keyword_count * per_keyword_limit)",
    )
    parser.add_argument(
        "--max-duration-minutes",
        type=int,
        default=10,
        help="Maximum YouTube duration for each batch request",
    )
    parser.add_argument(
        "--parallelism",
        type=int,
        default=None,
        help="Optional batch parallelism override (1..4 in backend)",
    )
    parser.add_argument("--dispatch-delay-seconds", type=float, default=0.15, help="Delay between dispatches")
    parser.add_argument("--timeout-seconds", type=float, default=20.0, help="HTTP timeout")
    parser.add_argument(
        "--report-path",
        default=".agent/artifacts/google_ai_pipeline_report.json",
        help="Where to save report JSON",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Only fetch news and extract keywords; do not call /batch",
    )

    args = parser.parse_args()
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    except Exception:
        pass

    if args.max_duration_minutes > 10:
        print("max_duration_minutes > 10 is not allowed for this test; forcing to 10.")
        args.max_duration_minutes = 10
    if args.max_duration_minutes < 1:
        print("max_duration_minutes must be >= 1; forcing to 1.")
        args.max_duration_minutes = 1

    if args.max_total_videos < 1:
        print("max_total_videos must be >= 1; forcing to 1.")
        args.max_total_videos = 1

    requested_total = max(1, args.keyword_count) * max(1, args.per_keyword_limit)
    if requested_total > args.max_total_videos:
        adjusted_keyword_count = max(1, args.max_total_videos // max(1, args.per_keyword_limit))
        print(
            f"requested total videos {requested_total} exceeds cap {args.max_total_videos}; "
            f"adjust keyword_count to {adjusted_keyword_count}"
        )
        args.keyword_count = adjusted_keyword_count

    report: dict[str, Any] = {
        "started_at_utc": _now_utc_iso(),
        "seed_query": args.seed_query,
        "news_count": args.news_count,
        "keyword_count": args.keyword_count,
        "per_keyword_limit": args.per_keyword_limit,
        "max_total_videos": args.max_total_videos,
        "max_duration_minutes": args.max_duration_minutes,
        "api_base": args.api_base,
        "dry_run": args.dry_run,
    }

    try:
        news_items = fetch_google_news(
            args.seed_query,
            args.news_count,
            args.timeout_seconds,
            args.keyword_language,
        )
    except Exception as e:
        report["error"] = f"Failed to fetch Google News: {e}"
        _write_report(args.report_path, report)
        _safe_print(report["error"])
        return 2

    titles = [n.title for n in news_items]
    if args.keyword_language == "en":
        keywords = extract_english_keywords_from_titles(titles, args.keyword_count)
    else:
        keywords = extract_keywords_from_titles(titles, args.keyword_count)

    report["news_items"] = [
        {"title": n.title, "link": n.link, "published": n.published} for n in news_items
    ]
    report["keywords"] = keywords
    report["dispatches"] = []

    _safe_print(f"Fetched news items: {len(news_items)}")
    _safe_print(f"Extracted keywords ({len(keywords)}): {', '.join(keywords)}")

    if args.dry_run:
        report["finished_at_utc"] = _now_utc_iso()
        _write_report(args.report_path, report)
        _safe_print(f"Dry run complete. Report written: {args.report_path}")
        return 0

    for i, kw in enumerate(keywords, start=1):
        result = trigger_batch(
            api_base=args.api_base,
            query=kw,
            limit=args.per_keyword_limit,
            max_duration_minutes=args.max_duration_minutes,
            parallelism=args.parallelism,
            timeout=args.timeout_seconds,
        )
        result["query"] = kw
        report["dispatches"].append(result)
        status = "OK" if result["ok"] else "FAIL"
        _safe_print(f"[{i}/{len(keywords)}] {kw}: {status} ({result['status_code']})")
        time.sleep(max(0.0, args.dispatch_delay_seconds))

    ok_count = sum(1 for d in report["dispatches"] if d.get("ok"))
    report["accepted_count"] = ok_count
    report["failed_count"] = len(report["dispatches"]) - ok_count
    report["finished_at_utc"] = _now_utc_iso()
    _write_report(args.report_path, report)

    _safe_print(
        f"Done. accepted={report['accepted_count']}, failed={report['failed_count']}, "
        f"report={args.report_path}"
    )
    return 0 if report["failed_count"] == 0 else 1


def _write_report(path: str, payload: dict[str, Any]) -> None:
    p = pathlib.Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    raise SystemExit(main())
