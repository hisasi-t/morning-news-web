# 朝刊エージェント Web版

毎朝6:30 JSTにGitHub Actionsで自動更新されるRSS朝刊。

## 公開URL

GitHub PagesでホスティングされたURL（リポジトリのSettings → Pagesで確認）

## 仕組み

- `news.py` がRSSフィードを取得して `docs/index.html` を生成
- GitHub Actions が毎朝6:30 JSTに実行
- 生成された `docs/index.html` をリポジトリにcommit
- GitHub Pages が `docs/` を公開

## カスタマイズ

- フィード追加: `feeds.py` の `FEEDS`
- 注目キーワード: `keywords.py` の `KEYWORDS`
- 載せたくない記事: `keywords.py` の `EXCLUDE_KEYWORDS`（タイトルに含まれたら除外）

## 記事を読む画面・翻訳

見出しを押すと、Cloudflare Worker `morning-news-cron`（別フォルダ）の `/read` が
本文を取り出し、朝刊の中に大きな字で表示する。英語記事の翻訳も同じWorkerが行う。
翻訳には Secrets の `TRANSLATE_KEY` が必要（Worker側にも同じ値を登録済み）。

## 手動更新

GitHubの Actions タブ → "Generate morning news" → "Run workflow"
