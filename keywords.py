KEYWORDS = {
    "A": [
        "大工", "木造", "建築", "古民家", "リノベーション",
        "工務店", "DIY", "木材", "在来工法", "棟上げ", "墨付け",
        "木材価格", "建設業界", "住宅着工", "建材", "資材高騰",
        "ウッドショック", "新築", "戸建", "ゼネコン", "公共工事",
        "断熱", "断熱材", "省エネ基準", "気密",
    ],
    "B": [
        "Claude", "Anthropic", "ChatGPT", "OpenAI", "Gemini",
        "LLM", "生成AI", "AI", "MCP", "プロンプト", "Claude Code",
    ],
    "C": [
        "Python", "tkinter", "個人開発", "自作アプリ",
        "Raspberry Pi", "Arduino", "ローカルLLM", "Ollama",
        "Roland", "ステカ", "カッティング",
    ],
    "F": [
        "insulation", "thermal", "airtight", "passive house",
        "retrofit", "energy efficiency", "heat pump", "R-value", "U-value",
        "mineral wool", "cellulose", "wood fiber", "hempcrete", "aerogel",
        "mass timber", "CLT", "cross-laminated", "timber", "embodied carbon",
    ],
    "E": [
        "ナイトライダー", "KITT", "アイアンマン", "ジャービス",
        "AIエージェント", "音声アシスタント", "スマートホーム",
        "ロボット", "自動化", "エージェント",
    ],
}

# タイトルにこの言葉が入っている記事はそのカテゴリに載せない（大文字小文字は区別しない）
EXCLUDE_KEYWORDS = {
    "A": [
        # 「断熱」で拾ってしまう服・日用品
        "ファッション", "SPUR", "コーデ", "ワークマン", "作業服", "断熱服",
        "着る断熱", "ウェア", "アウター", "ジャケット",
        "水筒", "ボトル", "タンブラー", "魔法瓶", "クーラーボックス", "寝袋",
        # 中身の無い市場調査の宣伝
        "世界市場", "市場予測", "市場規模", "市場の未来", "成長見通し", "市場調査",
    ],
    "F": [
        "Market Forecast", "Market Size", "Market Report", "Market Share",
        "Market Growth", "Market Analysis", "IndexBox", "openPR",
        "Subsea", "Battery", "Lithium",
    ],
}
