FEEDS = {
    "A": {
        "name": "木材価格・建設業界",
        "sources": {
            "Google News 木材価格": "https://news.google.com/rss/search?q=%E6%9C%A8%E6%9D%90%E4%BE%A1%E6%A0%BC&hl=ja&gl=JP&ceid=JP:ja",
            "Google News 建設業界": "https://news.google.com/rss/search?q=%E5%BB%BA%E8%A8%AD%E6%A5%AD%E7%95%8C&hl=ja&gl=JP&ceid=JP:ja",
            "Google News 住宅着工": "https://news.google.com/rss/search?q=%E4%BD%8F%E5%AE%85%E7%9D%80%E5%B7%A5&hl=ja&gl=JP&ceid=JP:ja",
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
