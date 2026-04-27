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

## 手動更新

GitHubの Actions タブ → "Generate morning news" → "Run workflow"
