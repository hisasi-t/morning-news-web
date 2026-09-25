#!/usr/bin/env python3
"""朝刊エージェント Web版 — モノトーン・要約付き・レスポンシブ"""

import os
import re
import sys
import time
import json
import datetime
import urllib.request
import html as html_module

import feedparser

from feeds import FEEDS, MAX_ITEMS_PER_FEED, MAX_ITEMS_PER_CATEGORY
from keywords import KEYWORDS, EXCLUDE_KEYWORDS

OUTPUT_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "docs")
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "index.html")
LINKS_FILE = os.path.join(OUTPUT_DIR, "links.json")

# 見出しを押したときに本文を取ってくる Worker（morning-news-cron の /read）
READER_URL = "https://morning-news-cron.hisasi-t.workers.dev/read"
TRANSLATE_URL = "https://morning-news-cron.hisasi-t.workers.dev/translate"

KEYWORDS_LOWER = {
    cat: [kw.lower() for kw in kws]
    for cat, kws in KEYWORDS.items()
}
EXCLUDE_LOWER = {
    cat: [kw.lower() for kw in kws]
    for cat, kws in EXCLUDE_KEYWORDS.items()
}


def matching_categories(text: str) -> list:
    t = text.lower()
    return [cat for cat, kws in KEYWORDS_LOWER.items() if any(kw in t for kw in kws)]


def is_excluded(cat: str, title: str) -> bool:
    t = title.lower()
    return any(kw in t for kw in EXCLUDE_LOWER.get(cat, []))


def translate_ja(texts: list) -> list:
    """英文をまとめて日本語へ訳す（Worker の Cloudflare AI 翻訳。失敗したら原文のまま返す）。
    Googleの無料翻訳はGitHub Actionsからだと自動アクセス扱いで断られるため使わない"""
    key = os.environ.get("TRANSLATE_KEY")
    if not key:
        print("[translate SKIP] TRANSLATE_KEY 未設定", file=sys.stderr)
        return texts
    req = urllib.request.Request(
        TRANSLATE_URL,
        data=json.dumps({"texts": texts}).encode("utf-8"),
        # Python標準のUser-AgentはCloudflareに弾かれる（error 1010）ので名乗りを付ける
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}",
                 "User-Agent": "morning-news-web"},
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as res:
            out = json.load(res)["texts"]
        return [o or t for o, t in zip(out, texts)]
    except Exception as e:
        print(f"[translate SKIP] {e}", file=sys.stderr)
        return texts


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
                title = html_module.unescape(getattr(entry, "title", "(タイトルなし)"))
                link  = getattr(entry, "link",  "#")
                if is_excluded(primary_cat, title):
                    print(f"  除外: {title[:50]}", flush=True)
                    continue
                summary_raw = getattr(entry, "summary",
                              getattr(entry, "description", ""))
                summary = re.sub(r"<[^>]+>", "", summary_raw)
                summary = html_module.unescape(summary).strip()[:200]

                # 日時取得（published優先、なければupdated、なければNone）
                pub_struct = (getattr(entry, "published_parsed", None)
                              or getattr(entry, "updated_parsed", None))
                pub_ts = time.mktime(pub_struct) if pub_struct else 0

                combined = title + " " + summary
                matched_cats = matching_categories(combined)
                highlight = primary_cat in matched_cats

                # Google News等はタイトルと同じ文を要約として返す。重複なら要約を省く
                title_norm   = re.sub(r"\s+", "", title)[:25]
                summary_norm = re.sub(r"\s+", "", summary)
                if title_norm and summary_norm.startswith(title_norm):
                    summary = ""

                article = {
                    "source":    source_name,
                    "title":     title,
                    "link":      link,
                    "summary":   summary,
                    "highlight": highlight,
                    "pub_ts":    pub_ts,
                }
                result[primary_cat].append(article)

    # 各カテゴリ: 重複除去 → 新しい順 → highlight優先 → 上限
    for cat in result:
        articles = sorted(result[cat], key=lambda a: a["pub_ts"], reverse=True)
        # 同じ記事を複数の検索が拾った場合の重複除去（タイトル先頭40字で判定）
        seen = set()
        deduped = []
        for a in articles:
            key = a["title"].lower()[:40]
            if key in seen:
                continue
            seen.add(key)
            deduped.append(a)
        highlighted = [a for a in deduped if a["highlight"]]
        normal      = [a for a in deduped if not a["highlight"]]
        result[cat] = (highlighted + normal)[:MAX_ITEMS_PER_CATEGORY]

    # 翻訳指定カテゴリ: 上限で絞った後にタイトル・要約を日本語化（キーワード判定は原文で済み）
    for cat, cat_info in FEEDS.items():
        if not cat_info.get("translate"):
            continue
        arts = result[cat]
        print(f"  翻訳中: {cat_info['name']} {len(arts)}件", flush=True)
        done = translate_ja([a["title"] for a in arts] + [a["summary"] for a in arts])
        for i, a in enumerate(arts):
            a["title"], a["summary"] = done[i], done[len(arts) + i]

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
    attr = " data-translate" if info.get("translate") else ""

    return f"""
  <section class="category"{attr}>
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
    html {{ -webkit-text-size-adjust: 100%; font-size: 20px; }}
    /* タッチ端末（スマホ）: 文字サイズを「画面幅の5.5%」で決める。
       Safariの「デスクトップ用サイト表示」でもモバイル表示でも実寸が同じになり、
       拡大操作なしで読める。大きさ調整はこの 5.5vw の数字ひとつ */
    @media (hover: none) and (pointer: coarse) {{
      html {{ font-size: 5.5vw; }}
    }}
    body {{
      background: #ffffff;
      color: #1a1a1a;
      font-family: -apple-system, "Helvetica Neue", "Hiragino Sans", sans-serif;
      font-size: 1rem;
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
      font-size: 1.25rem;
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

    /* 記事を読む画面（一覧と同じ rem 基準なので、一覧と同じ大きさで読める） */
    body.reading > header, body.reading > .category {{ display: none; }}
    #reader {{ max-width: 760px; margin: 0 auto; }}
    .reader-bar {{ margin-bottom: 18px; }}
    .reader-back {{
      background: #1a1a1a;
      color: #fff;
      border: none;
      padding: 8px 18px;
      font-size: 1rem;
      border-radius: 4px;
      font-family: inherit;
      cursor: pointer;
    }}
    .reader-source {{ font-size: 0.85rem; color: #888; margin-bottom: 6px; }}
    .reader-title {{
      font-size: 1.35rem;
      font-weight: 600;
      line-height: 1.5;
      padding-bottom: 14px;
      margin-bottom: 18px;
      border-bottom: 1px solid #1a1a1a;
    }}
    .reader-body p {{ font-size: 1.1rem; line-height: 1.9; margin-bottom: 1.1em; }}
    .reader-body p.reader-msg {{ font-size: 0.95rem; color: #888; }}
    .reader-foot {{
      margin-top: 30px;
      padding-top: 18px;
      border-top: 1px solid #d0d0d0;
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
    }}
    .reader-orig {{ font-size: 1rem; color: #1a1a1a; }}

    /* タブレット以上: コンテンツ幅制限 */
    @media (min-width: 640px) {{
      body {{ max-width: 760px; margin: 0 auto; padding: 36px 28px; }}
      header h1 {{ font-size: 1.5rem; }}
    }}
    /* マウス操作のPCだけ従来の文字サイズ */
    @media (min-width: 640px) and (hover: hover) and (pointer: fine) {{
      html {{ font-size: 16px; }}
      body {{ font-size: 17px; }}
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
  </header>
  {sections}

  <div id="reader" hidden>
    <div class="reader-bar"><button type="button" class="reader-back">← 戻る</button></div>
    <div class="reader-source"></div>
    <h1 class="reader-title"></h1>
    <div class="reader-body"></div>
    <div class="reader-foot">
      <a class="reader-orig" target="_blank" rel="noopener">元の記事を開く</a>
      <button type="button" class="reader-back">← 戻る</button>
    </div>
  </div>

  <script>
    // 見出しを押したら、記事本文をこの朝刊の中に同じ大きさの文字で表示する
    const READER_URL = {json.dumps(READER_URL)};
    const reader = document.getElementById('reader');
    let savedScroll = 0;
    // 戻ったときの位置はこちらで戻す（ブラウザ任せだと先頭に飛ぶ）
    if ('scrollRestoration' in history) history.scrollRestoration = 'manual';

    function showReader(link, title, source, translate) {{
      savedScroll = window.scrollY;
      reader.querySelector('.reader-source').textContent = source;
      reader.querySelector('.reader-title').textContent = title;
      reader.querySelector('.reader-orig').href = link;
      const body = reader.querySelector('.reader-body');
      body.innerHTML = '<p class="reader-msg">' + (translate
        ? '英語の記事を日本語に訳しています。10秒ほどお待ちください…'
        : '本文を読み込み中…') + '</p>';
      document.body.classList.add('reading');
      reader.hidden = false;
      window.scrollTo(0, 0);
      fetch(READER_URL + '?u=' + encodeURIComponent(link))
        .then(r => r.ok ? r.json() : Promise.reject(r.status))
        .then(d => {{
          if (!d.paragraphs || !d.paragraphs.length) throw 'empty';
          body.innerHTML = '';
          for (const p of d.paragraphs) {{
            const el = document.createElement('p');
            el.textContent = p;
            body.appendChild(el);
          }}
          if (d.translated) {{
            const n = document.createElement('p');
            n.className = 'reader-msg';
            n.textContent = '（英語の記事を自動で日本語に訳しています）';
            body.prepend(n);
          }}
        }})
        .catch(() => {{
          body.innerHTML = '<p class="reader-msg">このサイトは本文を取り出せませんでした。下の「元の記事を開く」で読んでください。</p>';
        }});
    }}

    function hideReader() {{
      reader.hidden = true;
      document.body.classList.remove('reading');
      window.scrollTo(0, savedScroll);
      setTimeout(() => window.scrollTo(0, savedScroll), 50);
    }}

    document.querySelectorAll('a.title').forEach(a => {{
      a.addEventListener('click', e => {{
        e.preventDefault();
        const card = a.closest('.card');
        showReader(a.href, a.textContent, card.querySelector('.source').textContent,
                   a.closest('.category').hasAttribute('data-translate'));
        history.pushState({{ reader: true }}, '');
      }});
    }});
    reader.querySelectorAll('.reader-back').forEach(b => b.addEventListener('click', () => history.back()));
    window.addEventListener('popstate', () => {{ if (!reader.hidden) hideReader(); }});

    // この朝刊が生成された時刻（UNIXタイムスタンプ）
    const BUILD_TS = {build_ts};

    // version.json を毎回fetchし、サーバー側が新しければ確実に再読込する
    // （HTMLはPWAで強くキャッシュされるが、別ファイル＋no-store＋クエリ付きなら最新が取れる）
    async function checkForUpdates() {{
      try {{
        const res = await fetch('./version.json?t=' + Date.now(), {{ cache: 'no-store' }});
        if (!res.ok) return;
        const v = await res.json();
        if (v.build_ts && v.build_ts > BUILD_TS) {{
          // サーバーに新しい朝刊あり → 新しいBUILD_TSをURLに付けて遷移（iOSは別URL扱い）
          const url = new URL(window.location.href);
          url.searchParams.set('v', v.build_ts);
          window.location.href = url.toString();
        }}
      }} catch (e) {{ /* オフライン等は無視 */ }}
    }}

    // 手動「更新」ボタン: 強制リロード
    document.getElementById('refresh-btn').addEventListener('click', () => {{
      const url = new URL(window.location.href);
      url.searchParams.set('_t', Date.now());
      window.location.href = url.toString();
    }});

    // 初回表示時にチェック
    checkForUpdates();

    // ホーム画面アプリで戻ってきた時にチェック
    document.addEventListener('visibilitychange', () => {{
      if (document.visibilityState === 'visible') checkForUpdates();
    }});

    // ブラウザ戻る/進むキャッシュからの復元時にもチェック
    window.addEventListener('pageshow', () => checkForUpdates());
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

    # 本文取り出しWorkerは、ここに載っているURLしか読みに行かない
    links = [a["link"] for arts in articles_by_cat.values() for a in arts]
    with open(LINKS_FILE, "w", encoding="utf-8") as f:
        json.dump(links, f, ensure_ascii=False)

    # PWAキャッシュ突破用：JS側から fetch して最新かどうかを判定する小さなファイル
    JST = datetime.timezone(datetime.timedelta(hours=9))
    now = datetime.datetime.now(JST)
    version_path = os.path.join(OUTPUT_DIR, "version.json")
    with open(version_path, "w", encoding="utf-8") as f:
        json.dump({
            "build_ts": int(now.timestamp()),
            "date":     now.strftime("%Y-%m-%d"),
            "time":     now.strftime("%H:%M"),
        }, f, ensure_ascii=False)
    print(f"version.json生成完了: {version_path}")


if __name__ == "__main__":
    main()
