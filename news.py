#!/usr/bin/env python3
"""朝刊エージェント Web版 — モノトーン・要約付き・レスポンシブ"""

import os
import re
import sys
import time
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

                # 日時取得（published優先、なければupdated、なければNone）
                pub_struct = (getattr(entry, "published_parsed", None)
                              or getattr(entry, "updated_parsed", None))
                pub_ts = time.mktime(pub_struct) if pub_struct else 0

                combined = title + " " + summary
                matched_cats = matching_categories(combined)
                highlight = primary_cat in matched_cats

                article = {
                    "source":    source_name,
                    "title":     title,
                    "link":      link,
                    "summary":   summary,
                    "highlight": highlight,
                    "pub_ts":    pub_ts,
                }
                result[primary_cat].append(article)

    # 各カテゴリ: 新しい順 → highlight優先 → 上限
    for cat in result:
        articles = sorted(result[cat], key=lambda a: a["pub_ts"], reverse=True)
        highlighted = [a for a in articles if a["highlight"]]
        normal      = [a for a in articles if not a["highlight"]]
        result[cat] = (highlighted + normal)[:MAX_ITEMS_PER_CATEGORY]

    return result


def relative_time(pub_ts: float) -> str:
    """配信時刻を「3時間前」「昨日 14:30」「2日前」みたいに整形"""
    if not pub_ts:
        return ""
    now = time.time()
    diff = now - pub_ts
    if diff < 60:
        return "たった今"
    if diff < 3600:
        return f"{int(diff // 60)}分前"
    if diff < 86400:
        return f"{int(diff // 3600)}時間前"
    if diff < 86400 * 2:
        return f"昨日 {datetime.datetime.fromtimestamp(pub_ts).strftime('%H:%M')}"
    days = int(diff // 86400)
    if days < 7:
        return f"{days}日前"
    return datetime.datetime.fromtimestamp(pub_ts).strftime("%-m月%-d日")


# ---- HTML生成 --------------------------------------------------------

def card_html(article: dict) -> str:
    title_t   = html_module.escape(article["title"])
    source_t  = html_module.escape(article["source"])
    summary_t = html_module.escape(article["summary"])
    link_t    = html_module.escape(article["link"])
    when_t    = html_module.escape(relative_time(article.get("pub_ts", 0)))
    cls = "card highlight" if article["highlight"] else "card"
    summary_block = f'<p class="summary">{summary_t}</p>' if summary_t else ""
    when_block = f'<span class="when">{when_t}</span>' if when_t else ""
    return f"""
    <article class="{cls}">
      <div class="meta-line"><span class="source">{source_t}</span>{when_block}</div>
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
    # GitHub Actions はUTCで動くので、必ずJSTに変換してから日付を出す
    JST = datetime.timezone(datetime.timedelta(hours=9))
    now      = datetime.datetime.now(JST)
    date_str = now.strftime("%Y年%m月%d日")
    time_str = now.strftime("%H:%M")
    build_ts = int(now.timestamp())  # JS側で経過時間を判定するため
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
  <!-- ホーム画面アプリで古いキャッシュを掴まないようにする -->
  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">
  <meta http-equiv="Pragma" content="no-cache">
  <meta http-equiv="Expires" content="0">
  <meta name="apple-mobile-web-app-capable" content="yes">
  <meta name="apple-mobile-web-app-title" content="朝刊">
  <title>朝刊 {date_str}</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    html {{ -webkit-text-size-adjust: 100%; }}
    body {{
      background: #ffffff;
      color: #1a1a1a;
      font-family: -apple-system, "Helvetica Neue", "Hiragino Sans", sans-serif;
      font-size: 18px;
      line-height: 1.65;
      padding: 18px;
    }}
    header {{
      border-bottom: 1px solid #1a1a1a;
      padding-bottom: 14px;
      margin-bottom: 28px;
    }}
    header h1 {{
      font-size: 1.4rem;
      font-weight: 600;
      letter-spacing: 0.05em;
    }}
    header .meta {{
      font-size: 0.95rem;
      color: #777;
      margin-top: 6px;
      display: flex;
      align-items: center;
      gap: 12px;
    }}
    #refresh-btn {{
      margin-left: auto;
      background: #1a1a1a;
      color: #fff;
      border: none;
      padding: 6px 14px;
      font-size: 0.85rem;
      border-radius: 4px;
      cursor: pointer;
      font-family: inherit;
    }}
    #refresh-btn:active {{ opacity: 0.7; }}
    header .tip {{
      font-size: 0.8rem;
      color: #999;
      margin-top: 8px;
      padding: 6px 10px;
      background: #f7f7f7;
      border-radius: 4px;
      line-height: 1.5;
    }}
    header .tip b {{ color: #1a1a1a; }}
    .category {{ margin-bottom: 36px; }}
    .cat-title {{
      font-size: 1.2rem;
      font-weight: 600;
      color: #333;
      padding-bottom: 6px;
      margin-bottom: 16px;
      border-bottom: 1px solid #d0d0d0;
      display: flex;
      align-items: baseline;
      gap: 8px;
    }}
    .cat-count {{
      font-size: 0.85rem;
      font-weight: 400;
      color: #999;
      margin-left: auto;
    }}
    .cards {{ display: grid; gap: 16px; grid-template-columns: 1fr; }}
    .card {{
      padding: 14px 0;
      border-bottom: 1px solid #eee;
    }}
    .card:last-child {{ border-bottom: none; }}
    .card.highlight .title::before {{
      content: "★ ";
      color: #1a1a1a;
    }}
    .meta-line {{
      display: flex;
      justify-content: space-between;
      align-items: baseline;
      margin-bottom: 5px;
      gap: 8px;
    }}
    .source {{
      font-size: 0.85rem;
      color: #888;
      letter-spacing: 0.03em;
    }}
    .when {{
      font-size: 0.78rem;
      color: #aaa;
      flex-shrink: 0;
    }}
    a.title {{
      display: block;
      font-size: 1.15rem;
      font-weight: 600;
      color: #1a1a1a;
      text-decoration: none;
      margin-bottom: 6px;
      line-height: 1.5;
    }}
    a.title:hover {{ text-decoration: underline; }}
    .summary {{
      font-size: 1rem;
      color: #555;
      line-height: 1.7;
    }}
    .empty {{ color: #aaa; font-size: 1rem; padding: 4px 0; }}

    /* タブレット以上: コンテンツ幅制限 */
    @media (min-width: 640px) {{
      body {{ max-width: 760px; margin: 0 auto; padding: 36px 28px; font-size: 17px; }}
      header h1 {{ font-size: 1.5rem; }}
    }}

    /* PC: 2カラム配置 */
    @media (min-width: 1024px) {{
      body {{ max-width: 1180px; padding: 44px 36px; }}
      .cards {{ grid-template-columns: 1fr 1fr; gap: 20px 40px; }}
      .card {{ padding: 14px 0; }}
    }}
  </style>
</head>
<body>
  <header>
    <h1>朝刊</h1>
    <div class="meta">
      <span>{date_str} {time_str} 配信 / 計{total}件</span>
      <button id="refresh-btn" type="button">更新</button>
    </div>
    <div class="tip">読みづらいリンク先は、Safariの「<b>あA</b>」→「<b>Webサイトを表示</b>」または「<b>リーダーを表示</b>」で整います</div>
  </header>
  {sections}

  <script>
    // この朝刊が生成された時刻（UNIXタイムスタンプ）
    const BUILD_TS = {build_ts};

    // 強制再読み込み（キャッシュ無視）
    function hardReload() {{
      const url = new URL(window.location.href);
      url.searchParams.set('_t', Date.now());
      window.location.href = url.toString();
    }}

    // 「更新」ボタン
    document.getElementById('refresh-btn').addEventListener('click', hardReload);

    // ホーム画面アプリで戻ってきた時、ページが30分以上古ければ自動更新
    document.addEventListener('visibilitychange', () => {{
      if (document.visibilityState === 'visible') {{
        const ageMin = (Date.now() / 1000 - BUILD_TS) / 60;
        if (ageMin > 30) hardReload();
      }}
    }});

    // pageshow（戻る/進むキャッシュからの復元時）でも判定
    window.addEventListener('pageshow', (e) => {{
      if (e.persisted) {{
        const ageMin = (Date.now() / 1000 - BUILD_TS) / 60;
        if (ageMin > 30) hardReload();
      }}
    }});
  </script>
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
