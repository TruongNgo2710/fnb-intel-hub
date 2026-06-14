"""
F&B Intel Hub — RSS News Fetcher v2
Tự động chạy mỗi 4 giờ qua GitHub Actions
Không cần API key — hoàn toàn miễn phí
Output: news.json + trends.json
"""

import feedparser
import json
import re
import hashlib
from datetime import datetime, timezone, timedelta
from time import mktime
from collections import Counter

# ═══════════════════════════════════════════════
# NGUỒN RSS
# ═══════════════════════════════════════════════
SOURCES = [
    # ── F&B VIỆT NAM ──
    {"url":"https://vnexpress.net/rss/kinh-doanh.rss","name":"VnExpress Kinh doanh","key":"vnexpress","badge":"vnexpress","region":"vietnam","lang":"vi","category":"fnb"},
    {"url":"https://vnexpress.net/rss/thi-truong.rss","name":"VnExpress Thị trường","key":"vnexpress","badge":"vnexpress","region":"vietnam","lang":"vi","category":"fnb"},
    {"url":"https://cafef.vn/hang-hoa-nguyen-lieu.rss","name":"CafeF Hàng hoá","key":"cafebiz","badge":"cafebiz","region":"vietnam","lang":"vi","category":"commodity"},
    {"url":"https://cafebiz.vn/rss/thi-truong.rss","name":"CafeBiz Thị trường","key":"cafebiz","badge":"cafebiz","region":"vietnam","lang":"vi","category":"fnb"},
    # ── F&B QUỐC TẾ ──
    {"url":"https://www.foodnavigator-asia.com/Info/RSS-Feed","name":"Food Navigator Asia","key":"foodnavigator","badge":"foodnavigator","region":"sea","lang":"en","category":"fnb"},
    {"url":"https://www.foodnavigator.com/Info/RSS-Feed","name":"Food Navigator Europe","key":"foodnavigator","badge":"foodnavigator","region":"europe","lang":"en","category":"fnb"},
    {"url":"https://www.foodbusinessnews.net/rss/news","name":"Food Business News","key":"foodbusiness","badge":"foodnavigator","region":"americas","lang":"en","category":"fnb"},
    {"url":"https://nrn.com/rss.xml","name":"Nation's Restaurant News","key":"nrn","badge":"foodnavigator","region":"americas","lang":"en","category":"fnb"},
    # ── CÀ PHÊ CHUYÊN SÂU ──
    {"url":"https://perfectdailygrind.com/feed/","name":"Perfect Daily Grind","key":"pdg","badge":"foodnavigator","region":"global","lang":"en","category":"coffee"},
    {"url":"https://dailycoffeenews.com/feed/","name":"Daily Coffee News","key":"dcn","badge":"foodnavigator","region":"global","lang":"en","category":"coffee"},
    {"url":"https://www.scaa.org/feed/","name":"SCA Coffee","key":"sca","badge":"foodnavigator","region":"global","lang":"en","category":"coffee"},
    # ── AI & CLAUDE ──
    {"url":"https://www.anthropic.com/rss.xml","name":"Anthropic Blog","key":"anthropic","badge":"bloomberg","region":"global","lang":"en","category":"ai"},
    {"url":"https://techcrunch.com/category/artificial-intelligence/feed/","name":"TechCrunch AI","key":"techcrunch","badge":"bloomberg","region":"global","lang":"en","category":"ai"},
    {"url":"https://www.theverge.com/rss/ai-artificial-intelligence/index.xml","name":"The Verge AI","key":"theverge","badge":"bloomberg","region":"global","lang":"en","category":"ai"},
    # ── KINH TẾ VĨ MÔ ──
    {"url":"https://feeds.reuters.com/reuters/businessNews","name":"Reuters Business","key":"reuters","badge":"reuters","region":"global","lang":"en","category":"macro"},
    {"url":"https://asia.nikkei.com/rss/feed/nar","name":"Nikkei Asia","key":"nikkei","badge":"nikkei","region":"sea","lang":"en","category":"macro"},
    {"url":"https://en.vietnamplus.vn/rss/economy.rss","name":"VietnamPlus Economy","key":"vnplus","badge":"vnexpress","region":"vietnam","lang":"en","category":"macro"},
]

# ═══════════════════════════════════════════════
# TỪ KHOÁ LỌC F&B
# ═══════════════════════════════════════════════
FNB_KEYWORDS = [
    "cà phê","cafe","nhà hàng","quán ăn","thực phẩm","đồ uống","ẩm thực","f&b",
    "highlands","phúc long","trung nguyên","the coffee house","nguyên liệu","chuỗi",
    "giá gạo","giá đường","giá dầu ăn","giá sữa","bột mì","robusta","arabica",
    "trà","bia","rượu","wine","brunch","thức uống","đồ ăn",
    "coffee","restaurant","food","beverage","chain","food delivery","qsr","fast food",
    "dining","culinary","brewery","hospitality","grocery","starbucks","mcdonald","kfc",
    "chipotle","pizza","domino","commodity","ingredient","supply chain","oat milk",
    "plant-based","vegan","dairy","wheat","sugar","food tech","dark kitchen",
    "ghost kitchen","grabfood","shopeefood","food inflation","menu","barista",
    "espresso","latte","cappuccino","cold brew","specialty coffee","third wave",
    "cafe chain","coffee shop","bubble tea","milk tea","trà sữa",
]

AI_KEYWORDS = [
    "claude","anthropic","chatgpt","openai","gemini","llm","ai model","large language",
    "artificial intelligence","machine learning","generative ai","gpt","bard",
    "ai agent","automation","productivity ai","ai tool","ai assistant",
    "claude opus","claude sonnet","claude haiku",
]

BRAND_MAP = {
    "brand-highlands": ["highlands coffee","highlands"],
    "brand-phuoclong": ["phúc long","phuc long"],
    "brand-thecoffeehouse": ["the coffee house","coffee house"],
    "brand-trungnguyen": ["trung nguyên","trung nguyen","g7 coffee"],
    "brand-starbucks": ["starbucks"],
    "brand-mcdonalds": ["mcdonald"],
    "brand-kfc": ["kfc","yum! brands","yum brands"],
    "brand-grab": ["grabfood","grab food"],
    "brand-phuclong": ["phúc long","phuc long"],
    "brand-claude": ["claude","anthropic"],
    "brand-openai": ["chatgpt","openai","gpt-4","gpt-5"],
}

TOPIC_MAP = {
    "topic-coffee": ["cà phê","coffee","café","robusta","arabica","highlands","phúc long","trung nguyên","barista","espresso","cold brew","specialty coffee","third wave","brew"],
    "topic-qsr": ["kfc","mcdonald","fast food","qsr","quick service","chipotle","pizza","burger","fast-food","domino"],
    "topic-price": ["giá","price","commodity","nguyên liệu","ingredient","supply","cost","inflation","tăng giá","giá tăng","price increase","costly"],
    "topic-delivery": ["delivery","grab food","shopee food","giao hàng","food delivery","dark kitchen","ghost kitchen","grabfood","shopeefood"],
    "topic-plantbased": ["plant-based","vegan","oat milk","thực vật","chay","alternative protein","meatless"],
    "topic-funding": ["gọi vốn","funding","series a","series b","investment","đầu tư","ipo","raise","venture","startup"],
    "topic-brunch": ["brunch","breakfast","sáng","morning","weekend dining"],
    "topic-wine": ["wine","rượu vang","beer","bia","craft beer","brewery","spirits","cocktail"],
    "topic-ai": ["ai","claude","chatgpt","openai","artificial intelligence","machine learning","llm","automation","generative"],
    "topic-macro": ["inflation","lạm phát","gdp","interest rate","fed","lãi suất","kinh tế","economy","recession","growth"],
    "topic-trend": ["trend","xu hướng","consumer","người tiêu dùng","demand","nhu cầu","market research","insight","survey"],
    "topic-supply": ["supply chain","chuỗi cung ứng","logistics","warehouse","kho","vận chuyển","import","export","xuất khẩu"],
}

# Từ khóa sentiment
POSITIVE_WORDS = [
    "tăng trưởng","tăng","phát triển","thành công","lợi nhuận","doanh thu","mở rộng",
    "growth","increase","success","profit","revenue","expand","launch","innovative",
    "opportunity","positive","surge","boom","record","bullish","breakthrough","approve",
    "gọi vốn","đầu tư thành công","mở thêm","chuỗi mở","ra mắt",
]
NEGATIVE_WORDS = [
    "giảm","đóng cửa","thua lỗ","khó khăn","khủng hoảng","sụt giảm","phá sản",
    "decline","close","loss","struggle","crisis","bankruptcy","fail","cut","layoff",
    "bearish","recession","inflation","costly","shortage","supply chain disruption",
    "thất bại","đóng chi nhánh","cắt giảm",
]

# ═══════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:500]

def is_relevant(title, desc, category):
    text = (title + " " + desc).lower()
    if category in ("coffee", "ai", "macro"):
        return True  # Luôn lấy từ nguồn chuyên biệt
    return any(kw in text for kw in FNB_KEYWORDS)

def detect_topics(title, desc):
    text = (title + " " + desc).lower()
    found = [tag for tag, kws in TOPIC_MAP.items() if any(k in text for k in kws)]
    return found if found else ["topic-general"]

def detect_brands(title, desc):
    text = (title + " " + desc).lower()
    return [tag for tag, kws in BRAND_MAP.items() if any(k in text for k in kws)]

def detect_region(base, title, desc):
    text = (title + " " + desc).lower()
    if any(k in text for k in ["việt nam","vietnam","tp.hcm","hà nội","hanoi","hcmc","viet nam","ho chi minh"]):
        return "region-vietnam"
    if any(k in text for k in ["southeast asia","đông nam á","singapore","thailand","indonesia","malaysia","asean","philippines"]):
        return "region-sea"
    if any(k in text for k in ["europe","châu âu"," eu ","france","germany","uk ","italy","spain","netherlands"]):
        return "region-europe"
    if any(k in text for k in ["america"," us ","usa","united states","châu mỹ","chipotle","mexico","canada","brazil"]):
        return "region-americas"
    return f"region-{base}"

def parse_date(entry):
    try:
        if entry.get("published_parsed"):
            return datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc).isoformat()
    except:
        pass
    return datetime.now(timezone.utc).isoformat()

def time_ago(iso_str):
    try:
        dt = datetime.fromisoformat(iso_str.replace("Z","+00:00"))
        now = datetime.now(timezone.utc)
        diff = int((now - dt).total_seconds())
        if diff < 3600: return f"{diff // 60} phút trước"
        if diff < 86400: return f"{diff // 3600} giờ trước"
        return f"{diff // 86400} ngày trước"
    except:
        return "vừa xong"

def sentiment_score(title, desc):
    text = (title + " " + desc).lower()
    pos = sum(1 for w in POSITIVE_WORDS if w in text)
    neg = sum(1 for w in NEGATIVE_WORDS if w in text)
    if pos > neg: return "positive"
    if neg > pos: return "negative"
    return "neutral"

def extract_keywords(title, desc):
    """Trích xuất từ khoá nổi bật"""
    text = (title + " " + desc).lower()
    important = []
    for kw in ["robusta","arabica","highlands","starbucks","kfc","mcdonald","delivery","plant-based",
               "funding","brunch","wine","beer","inflation","supply chain","claude","chatgpt","ai",
               "phúc long","trung nguyên","the coffee house","cold brew","specialty"]:
        if kw in text:
            important.append(kw)
    return important[:5]

# ═══════════════════════════════════════════════
# FETCH ALL NEWS
# ═══════════════════════════════════════════════
def fetch_all():
    articles = []
    seen = set()

    for src in SOURCES:
        try:
            print(f"⏳ Fetching: {src['name']} ...")
            feed = feedparser.parse(src["url"], request_headers={"User-Agent": "FnBIntelHub/2.0"})
            count = 0
            for entry in feed.entries[:20]:
                url = entry.get("link","")
                if not url or url in seen:
                    continue
                title = entry.get("title","").strip()
                desc = clean_html(entry.get("summary", entry.get("description","")))
                if not title or not is_relevant(title, desc, src.get("category","fnb")):
                    continue
                seen.add(url)
                pub = parse_date(entry)
                topics = detect_topics(title, desc)
                brands = detect_brands(title, desc)
                region = detect_region(src["region"], title, desc)
                sentiment = sentiment_score(title, desc)
                keywords = extract_keywords(title, desc)
                tags = " ".join(set([f"source-{src['key']}", region, f"category-{src.get('category','fnb')}"] + topics + brands))
                is_ai = src.get("category") == "ai" or "topic-ai" in topics
                is_coffee = src.get("category") == "coffee" or "topic-coffee" in topics
                articles.append({
                    "id": hashlib.md5(url.encode()).hexdigest()[:8],
                    "title": title,
                    "url": url,
                    "source_name": src["name"],
                    "source_key": src["key"],
                    "badge": src.get("badge", src["key"]),
                    "region": region,
                    "tags": tags,
                    "topics": topics,
                    "brands": brands,
                    "category": src.get("category","fnb"),
                    "published": pub,
                    "time_ago": time_ago(pub),
                    "summary": desc,
                    "sentiment": sentiment,
                    "keywords": keywords,
                    "is_new": True,
                    "is_hot": len(desc) > 150 or len(topics) >= 2 or sentiment == "positive",
                    "is_ai": is_ai,
                    "is_coffee": is_coffee,
                    "lang": src["lang"],
                })
                count += 1
            print(f"   ✅ {count} articles found")
        except Exception as e:
            print(f"   ❌ Error fetching {src['name']}: {e}")

    articles.sort(key=lambda x: x["published"], reverse=True)
    articles = articles[:80]
    return articles

# ═══════════════════════════════════════════════
# GENERATE TRENDS ANALYSIS
# ═══════════════════════════════════════════════
def generate_trends(articles):
    now = datetime.now(timezone.utc)
    last_24h = [a for a in articles if (now - datetime.fromisoformat(a["published"].replace("Z","+00:00"))).total_seconds() < 86400]
    last_7d = articles  # already sorted

    # ── Topic counts ──
    topic_counts = Counter()
    topic_24h = Counter()
    for a in articles:
        for t in a["topics"]:
            topic_counts[t] += 1
    for a in last_24h:
        for t in a["topics"]:
            topic_24h[t] += 1

    trending_topics = []
    topic_labels = {
        "topic-coffee":"#ChuỗiCàPhê","topic-price":"#GiáNguyênLiệu",
        "topic-delivery":"#FoodDelivery","topic-qsr":"#QSR",
        "topic-ai":"#AI&Claude","topic-funding":"#GọiVốn",
        "topic-wine":"#Wine&Beer","topic-brunch":"#Brunch",
        "topic-plantbased":"#PlantBased","topic-macro":"#KinhTếVĩMô",
        "topic-trend":"#XuHướng","topic-supply":"#ChuỗiCungỨng",
    }
    for tag, label in topic_labels.items():
        cnt = topic_counts.get(tag, 0)
        cnt_24h = topic_24h.get(tag, 0)
        if cnt > 0:
            trending_topics.append({
                "tag": tag,
                "label": label,
                "count": cnt,
                "count_24h": cnt_24h,
                "trend": "hot" if cnt_24h >= 3 else "up" if cnt_24h >= 1 else "stable",
            })
    trending_topics.sort(key=lambda x: x["count"], reverse=True)

    # ── Brand counts ──
    brand_counts = Counter()
    for a in articles:
        for b in a["brands"]:
            brand_counts[b] += 1
    brand_labels = {
        "brand-highlands":"Highlands Coffee","brand-phuoclong":"Phúc Long",
        "brand-thecoffeehouse":"The Coffee House","brand-trungnguyen":"Trung Nguyên",
        "brand-starbucks":"Starbucks","brand-mcdonalds":"McDonald's",
        "brand-kfc":"KFC/Yum!","brand-grab":"GrabFood",
        "brand-claude":"Claude/Anthropic","brand-openai":"ChatGPT/OpenAI",
    }
    trending_brands = [{"tag":k,"name":brand_labels.get(k,k),"count":v,"trend":"hot" if v>=3 else "up"} for k,v in brand_counts.most_common(8) if v > 0]

    # ── Sentiment analysis ──
    sentiments = Counter(a["sentiment"] for a in articles)
    total = len(articles) or 1
    sentiment_score_val = round((sentiments["positive"] - sentiments["negative"]) / total * 100)

    # ── Keyword frequency ──
    all_keywords = []
    for a in articles:
        all_keywords.extend(a.get("keywords",[]))
    hot_keywords = [{"word":k,"count":v} for k,v in Counter(all_keywords).most_common(15) if v > 1]

    # ── Coffee deep analysis ──
    coffee_articles = [a for a in articles if a.get("is_coffee") or "topic-coffee" in a.get("topics",[])]
    coffee_price_up = sum(1 for a in coffee_articles if any(w in (a["title"]+a["summary"]).lower() for w in ["tăng","increase","surge","high","đỉnh","record"]))
    coffee_price_down = sum(1 for a in coffee_articles if any(w in (a["title"]+a["summary"]).lower() for w in ["giảm","decrease","drop","fall","low"]))

    coffee_trends = {
        "total_articles": len(coffee_articles),
        "price_direction": "up" if coffee_price_up > coffee_price_down else "down" if coffee_price_down > coffee_price_up else "stable",
        "price_up_signals": coffee_price_up,
        "price_down_signals": coffee_price_down,
        "top_articles": [{"title":a["title"],"url":a["url"],"source":a["source_name"],"time":a["time_ago"]} for a in coffee_articles[:5]],
        "consumer_demand": "high" if len(coffee_articles) >= 5 else "moderate" if len(coffee_articles) >= 2 else "low",
        "insight": _coffee_insight(coffee_articles, coffee_price_up, coffee_price_down),
    }

    # ── AI/Claude news ──
    ai_articles = [a for a in articles if a.get("is_ai") or "topic-ai" in a.get("topics",[])]
    ai_trends = {
        "total_articles": len(ai_articles),
        "top_articles": [{"title":a["title"],"url":a["url"],"source":a["source_name"],"time":a["time_ago"]} for a in ai_articles[:5]],
        "insight": _ai_insight(ai_articles),
    }

    # ── Regional breakdown ──
    region_counts = Counter(a["region"] for a in articles)

    # ── Price signals từ text ──
    price_signals = {
        "robusta": _price_signal(articles, ["robusta","cà phê","coffee price"]),
        "wheat": _price_signal(articles, ["lúa mì","wheat","flour"]),
        "sugar": _price_signal(articles, ["đường","sugar"]),
        "dairy": _price_signal(articles, ["sữa","dairy","milk"]),
    }

    return {
        "updated": now.isoformat(),
        "period": "7 ngày gần nhất",
        "total_articles": len(articles),
        "articles_24h": len(last_24h),
        "trending_topics": trending_topics[:10],
        "trending_brands": trending_brands,
        "sentiment": {
            "positive": sentiments["positive"],
            "negative": sentiments["negative"],
            "neutral": sentiments["neutral"],
            "score": sentiment_score_val,
            "label": "Tích cực" if sentiment_score_val > 20 else "Tiêu cực" if sentiment_score_val < -20 else "Trung tính",
        },
        "hot_keywords": hot_keywords,
        "coffee_trends": coffee_trends,
        "ai_trends": ai_trends,
        "price_signals": price_signals,
        "regional_breakdown": dict(region_counts),
    }

def _coffee_insight(articles, up, down):
    if not articles:
        return "Chưa đủ dữ liệu phân tích xu hướng cà phê."
    if up > down * 1.5:
        return f"⚠️ Giá nguyên liệu cà phê đang có xu hướng TĂNG ({up} tín hiệu). Cân nhắc lock giá sớm, điều chỉnh menu giá bán."
    if down > up * 1.5:
        return f"✅ Tín hiệu giảm giá xuất hiện ({down} tín hiệu). Có thể chờ thêm trước khi nhập hàng số lượng lớn."
    return f"📊 Giá cà phê đang ổn định (tăng {up} · giảm {down} tín hiệu). Duy trì chiến lược nhập hàng hiện tại."

def _ai_insight(articles):
    if not articles:
        return "Chưa có tin mới từ Anthropic/OpenAI. Theo dõi để cập nhật tính năng AI mới nhất."
    titles = " ".join(a["title"] for a in articles[:3]).lower()
    if "claude" in titles or "anthropic" in titles:
        return f"🤖 Anthropic ra mắt cập nhật mới. {len(articles)} bài về AI trong tuần — xu hướng ứng dụng AI vào F&B đang tăng mạnh."
    return f"🤖 {len(articles)} bài về AI & công nghệ. Các chuỗi F&B lớn đang tích cực ứng dụng AI vào quản lý tồn kho và dự báo nhu cầu."

def _price_signal(articles, keywords):
    relevant = [a for a in articles if any(k in (a["title"]+a["summary"]).lower() for k in keywords)]
    if not relevant:
        return {"direction":"unknown","count":0,"signal":"Chưa đủ dữ liệu"}
    up = sum(1 for a in relevant if any(w in (a["title"]+a["summary"]).lower() for w in ["tăng","increase","surge","high","rise"]))
    down = sum(1 for a in relevant if any(w in (a["title"]+a["summary"]).lower() for w in ["giảm","decrease","drop","fall","low"]))
    if up > down:
        return {"direction":"up","count":len(relevant),"signal":f"⬆️ Tăng ({up} tín hiệu)"}
    elif down > up:
        return {"direction":"down","count":len(relevant),"signal":f"⬇️ Giảm ({down} tín hiệu)"}
    return {"direction":"stable","count":len(relevant),"signal":"➡️ Ổn định"}

# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════
def main():
    print("🚀 F&B Intel Hub v2 — Starting fetch...")
    articles = fetch_all()

    # Save news.json
    news_output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(articles),
        "articles": articles,
    }
    with open("news.json","w",encoding="utf-8") as f:
        json.dump(news_output, f, ensure_ascii=False, indent=2)
    print(f"\n✅ news.json: {len(articles)} articles saved")

    # Generate & save trends.json
    print("\n📊 Generating trends analysis...")
    trends = generate_trends(articles)
    with open("trends.json","w",encoding="utf-8") as f:
        json.dump(trends, f, ensure_ascii=False, indent=2)
    print(f"✅ trends.json saved — {trends['total_articles']} articles analyzed")
    print(f"   Sentiment: {trends['sentiment']['label']} ({trends['sentiment']['score']:+d})")
    print(f"   Top topic: {trends['trending_topics'][0]['label'] if trends['trending_topics'] else 'N/A'}")
    print(f"   Coffee: {trends['coffee_trends']['price_direction']} ({trends['coffee_trends']['total_articles']} articles)")
    print(f"   AI news: {trends['ai_trends']['total_articles']} articles")
    print("\n🎉 Done!")

if __name__ == "__main__":
    main()
