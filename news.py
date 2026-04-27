#!/usr/bin/env python3
"""朝刊エージェント Web版 — モノトーン・要約付き・レスポンシブ"""

import os
import re
import sys
import datetime
import html as html_module

import feedparser

from feeds import FEEDS, MAX_ITEMS_PER_FEED, MAX_ITEMS_PER_CATEGORY
from keywords import KEYWORDS

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")

KEYWORDS_LOWER = {
    cat: [kw.lower() for kw in kws]
    for cat, kws in KEYWORDS.items()
}


def matching_categories(text: str) -> list:
    t = text.lower()
    return [cat for cat, kws in KEYWORDS_LOWER.items() if any(kw in t for kw in kws)]


def fetch_articles() -> dict:
    result = {cat: [] for cat in FEEDS}

    for primary_cat, cat_info in FEEDS.items():
        for source_name, url in cat_info["sources"].items():
            try:
                feed = feedparser.parse(url)
                entries = feed.entries[:MAX_ITEMS_PER_FEED]
            except Exception as e:
                print(f"[SKIP] {source_name}: {e}", file=sys.stderr)
                continue

            for entry in entries:
                title = getattr(entry, "title", "(タイトルなし)")
                link  = getattr(entry, "link",  "#")
                summary_raw = getattr(entry, "summary",
                              getattr(entry, "description", ""))
                summary = re.sub(r"<[^>]+>", "", summary_raw)[:200]

                combined = title + " " + summary
                matched_cats = matching_categories(combined)
                highlight = primary_cat in matched_cats

                article = {
                    "source":    source_name,
                    "title":     title,
                    "link":      link,
                    "summary":   summary,
                    "highlight": highlight,
                }
                result[primary_cat].append(article)

    for cat in result:
        articles = result[cat]
        highlighted = [a for a in articles if a["highlight"]]
        normal      = [a for a in articles if not a["highlight"]]
        result[cat] = (highlighted + normal)[:MAX_ITEMS_PER_CATEGORY]

    return result


# ---- HTML生成 --------------------------------------------------------

def card_html(article: dict) -> str:
    title_t   = html_module.escape(article["title"])
    source_t  = html_module.escape(article["source"])
    summary_t = html_module.escape(article["summary"])
    link_t    = html_module.escape(article["link"])
    cls = "card highlight" if article["highlight"] else "card"
    summary_block = f'<p class="summary">{summary_t}</p>' if summary_t else ""
    return f"""
    <article class="{cls}">
      <div class="source">{source_t}</div>
      <a class="title" href="{link_t}" target="_blank" rel="noopener">{title_t}</a>
      {summary_block}
    </article>"""


def section_html(cat_id: str, articles: list) -> str:
    info  = FEEDS[cat_id]
    name  = info["name"]
    count = len(articles)

    if not info["sources"]:
        body = '<p class="empty">フィード未登録</p>'
    elif count == 0:
        body = '<p class="empty">今日は新着なし</p>'
    else:
        body = '<div class="cards">' + "".join(card_html(a) for a in articles) + '</div>'

    return f"""
  <section class="category">
    <h2 class="cat-title">
      <span class="cat-name">{name}</span>
      <span class="cat-count">{count}</span>
    </h2>
    {body}
  </section>"""


def build_html(articles_by_cat: dict) -> str:
    now      = datetime.datetime.now()
    date_str = now.strftime("%Y年%m月%d日")
    time_str = now.strftime("%H:%M")
    total = sum(len(a) for a in articles_by_cat.values())

    sections = "".join(
        section_html(cat, arts) for cat, arts in articles_by_cat.items()
    )

    return f"""<!DOCTYPE html>
<html lang="ja">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>朝刊 {date_str}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ -webkit-text-size-adjust: 100%; }}
    body {{
      background: #ffffff;
      color: #1a1a1a;
      font-family: -apple-system, "Helvetica Neue", "Hiragino Sans", sans-serif;
      line-height: 1.6;
      padding: 16px;
    }}
    header {{
      border-bottom: 1px solid #1a1a1a;
      padding-bottom: 12px;
      margin-bottom: 24px;
    }}
    header h1 {{
      font-size: 1.1rem;
      font-weight: 600;
      letter-spacing: 0.05em;
    }}
    header .meta {{
      font-size: 0.8rem;
      color: #777;
      margin-top: 4px;
    }}
    .category {{ margin-bottom: 28px; }}
    .cat-title {{
      font-size: 0.95rem;
      font-weight: 600;
      color: #333;
      padding-bottom: 4px;
      margin-bottom: 12px;
      border-bottom: 1px solid #d0d0d0;
      display: flex;
      align-items: baseline;
      gap: 8px;
    }}
    .cat-count {{
      font-size: 0.7rem;
      font-weight: 400;
      color: #999;
      margin-left: auto;
    }}
    .cards {{ display: grid; gap: 12px; grid-template-columns: 1fr; }}
    .card {{
      padding: 10px 0;
      border-bottom: 1px solid #eee;
    }}
    .card:last-child {{ border-bottom: none; }}
    .card.highlight .title::before {{
      content: "★ ";
      color: #1a1a1a;
    }}
    .source {{
      font-size: 0.7rem;
      color: #888;
      margin-bottom: 3px;
      letter-spacing: 0.03em;
    }}
    a.title {{
      display: block;
      font-size: 0.95rem;
      font-weight: 600;
      color: #1a1a1a;
      text-decoration: none;
      margin-bottom: 4px;
      line-height: 1.45;
    }}
    a.title:hover {{ text-decoration: underline; }}
    .summary {{
      font-size: 0.8rem;
      color: #555;
      line-height: 1.65;
    }}
    .empty {{ color: #aaa; font-size: 0.85rem; padding: 4px 0; }}

    /* タブレット以上: コンテンツ幅制限 */
    @media (min-width: 640px) {{
      body {{ max-width: 720px; margin: 0 auto; padding: 32px 24px; }}
      header h1 {{ font-size: 1.25rem; }}
    }}

    /* PC: 2カラム配置 */
    @media (min-width: 1024px) {{
      body {{ max-width: 1100px; padding: 40px 32px; }}
      .cards {{ grid-template-columns: 1fr 1fr; gap: 16px 32px; }}
      .card {{ padding: 12px 0; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>朝刊</h1>
    <div class="meta">{date_str} {time_str} 配信 / 計{total}件</div>
  </header>
  {sections}
</body>
</html>"""


def main():
    print("記事を収集中...", flush=True)
    articles_by_cat = fetch_articles()

    for cat, arts in articles_by_cat.items():
        info = FEEDS[cat]
        print(f"  {cat} {info['name']}: {len(arts)}件")

    html = build_html(articles_by_cat)
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"\nHTML生成完了: {OUTPUT_FILE}")


if __name__ == "__main__":
    main()
