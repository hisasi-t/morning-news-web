FEEDS = {
    "A": {
        "name": "大工・建築",
        "sources": {
            # 建築知識ビルダーズ: 要確認 (404のため除外)
        },
    },
    "B": {
        "name": "AI・Claude",
        "sources": {
            "ITmedia AI+": "https://rss.itmedia.co.jp/rss/2.0/aiplus.xml",
            "Publickey": "https://www.publickey1.jp/atom.xml",
        },
    },
    "C": {
        "name": "個人開発",
        "sources": {
            "Zenn": "https://zenn.dev/feed",
            "Qiita": "https://qiita.com/popular-items/feed",
        },
    },
    "D": {
        "name": "知的生産・Obsidian",
        "sources": {
            "ライフハッカー": "https://www.lifehacker.jp/feed/index.xml",
        },
    },
    "E": {
        "name": "相棒AIカルチャー",
        "sources": {
            "GIGAZINE": "https://gigazine.net/news/rss_2.0/",
        },
    },
}

MAX_ITEMS_PER_FEED = 5
MAX_ITEMS_PER_CATEGORY = 10
