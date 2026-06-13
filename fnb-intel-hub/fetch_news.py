"""
F&B Intel Hub — RSS News Fetcher
Tự động chạy mỗi 4 giờ qua GitHub Actions
Không cần API key — hoàn toàn miễn phí
"""

import feedparser
import json
import re
import hashlib
from datetime import datetime, timezone
from time import mktime

# ═══════════════════════════════════════════════
# NGUỒN RSS (thêm/bỏ tuỳ ý)
# ═══════════════════════════════════════════════
SOURCES = [
    {
        "url": "https://vnexpress.net/rss/kinh-doanh.rss",
        "name": "VnExpress Kinh doanh",
        "key": "vnexpress",
        "badge": "vnexpress",
        "region": "vietnam",
        "lang": "vi"
    },
    {
        "url": "https://vnexpress.net/rss/thi-truong.rss",
        "name": "VnExpress Thị trường",
        "key": "vnexpress",
        "badge": "vnexpress",
        "region": "vietnam",
        "lang": "vi"
    },
    {
        "url": "https://cafef.vn/hang-hoa-nguyen-lieu.rss",
        "name": "CafeF Hàng hoá",
        "key": "cafebiz",
        "badge": "cafebiz",
        "region": "vietnam",
        "lang": "vi"
    },
    {
        "url": "https://cafebiz.vn/rss/thi-truong.rss",
        "name": "CafeBiz Thị trường",
        "key": "cafebiz",
        "badge": "cafebiz",
        "region": "vietnam",
        "lang": "vi"
    },
    {
        "url": "https://www.foodnavigator-asia.com/Info/RSS-Feed",
        "name": "Food Navigator Asia",
        "key": "foodnavigator",
        "badge": "foodnavigator",
        "region": "sea",
        "lang": "en"
    },
    {
        "url": "https://www.foodnavigator.com/Info/RSS-Feed",
        "name": "Food Navigator Europe",
        "key": "foodnavigator",
        "badge": "foodnavigator",
        "region": "europe",
        "lang": "en"
    },
    {
        "url": "https://feeds.reuters.com/reuters/businessNews",
        "name": "Reuters Business",
        "key": "reuters",
        "badge": "reuters",
        "region": "global",
        "lang": "en"
    },
    {
        "url": "https://asia.nikkei.com/rss/feed/nar",
        "name": "Nikkei Asia",
        "key": "nikkei",
        "badge": "nikkei",
        "region": "sea",
        "lang": "en"
    },
]

# ═══════════════════════════════════════════════
# TỪ KHOÁ LỌC F&B
# ═══════════════════════════════════════════════
KEYWORDS = [
    # Tiếng Việt
    "cà phê", "cafe", "nhà hàng", "quán ăn", "thực phẩm", "đồ uống",
    "ẩm thực", "f&b", "highlands", "phúc long", "trung nguyên",
    "the coffee house", "nguyên liệu", "chuỗi", "giá gạo", "giá đường",
    "giá dầu ăn", "giá sữa", "bột mì", "robusta", "arabica",
    "trà", "bia", "rượu", "wine", "brunch", "thức uống", "đồ ăn",
    # Tiếng Anh
    "coffee", "restaurant", "food", "beverage", "cafe", "chain",
    "food delivery", "qsr", "fast food", "dining", "culinary",
    "brewery", "wine", "beer", "hospitality", "grocery",
    "starbucks", "mcdonald", "kfc", "chipotle", "pizza", "domino",
    "robusta", "arabica", "commodity", "ingredient", "supply chain",
    "oat milk", "plant-based", "vegan", "dairy", "wheat", "sugar",
    "food tech", "dark kitchen", "ghost kitchen", "grabfood",
    "shopeefood", "food inflation", "menu", "barista",
]

BRAND_MAP = {
    "brand-highlands": ["highlands coffee", "highlands"],
    "brand-phuoclong": ["phúc long", "phuc long"],
    "brand-thecoffeehouse": ["the coffee house", "coffee house"],
    "brand-trungnguyen": ["trung nguyên", "trung nguyen", "g7 coffee"],
    "brand-starbucks": ["starbucks"],
    "brand-mcdonalds": ["mcdonald"],
    "brand-kfc": ["kfc", "yum! brands", "yum brands"],
    "brand-grab": ["grabfood", "grab food"],
}

TOPIC_MAP = {
    "topic-coffee": ["cà phê", "coffee", "café", "robusta", "arabica",
                     "highlands", "phúc long", "trung nguyên", "barista"],
    "topic-qsr": ["kfc", "mcdonald", "fast food", "qsr", "quick service",
                  "chipotle", "pizza", "burger", "fast-food"],
    "topic-price": ["giá", "price", "commodity", "nguyên liệu",
                    "ingredient", "supply", "cost", "inflation", "tăng giá"],
    "topic-delivery": ["delivery", "grab food", "shopee food",
                       "giao hàng", "food delivery", "dark kitchen"],
    "topic-plantbased": ["plant-based", "vegan", "oat milk",
                         "thực vật", "chay", "alternative protein"],
    "topic-funding": ["gọi vốn", "funding", "series a", "series b",
                      "investment", "đầu tư", "ipo", "raise"],
    "topic-brunch": ["brunch", "breakfast", "sáng", "morning"],
    "topic-wine": ["wine", "rượu vang", "beer", "bia", "craft beer", "brewery"],
}

# ═══════════════════════════════════════════════
# HELPER FUNCTIONS
# ═══════════════════════════════════════════════
def clean_html(text):
    if not text:
        return ""
    text = re.sub(r'<[^>]+>', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text[:400]

def is_fnb(title, desc):
    text = (title + " " + desc).lower()
    return any(kw in text for kw in KEYWORDS)

def detect_topics(title, desc):
    text = (title + " " + desc).lower()
    found = [tag for tag, kws in TOPIC_MAP.items() if any(k in text for k in kws)]
    return found if found else ["topic-general"]

def detect_brands(title, desc):
    text = (title + " " + desc).lower()
    return [tag for tag, kws in BRAND_MAP.items() if any(k in text for k in kws)]

def detect_region(base, title, desc):
    text = (title + " " + desc).lower()
    if any(k in text for k in ["việt nam", "vietnam", "tp.hcm", "hà nội", "hanoi", "hcmc", "viet nam"]):
        return "region-vietnam"
    if any(k in text for k in ["southeast asia", "đông nam á", "singapore", "thailand", "indonesia", "malaysia", "asean"]):
        return "region-sea"
    if any(k in text for k in ["europe", "châu âu", " eu ", "france", "germany", "uk ", "italy", "spain"]):
        return "region-europe"
    if any(k in text for k in ["america", " us ", "usa", "united states", "châu mỹ", "chipotle", "mexico"]):
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
        dt = datetime.fromisoformat(iso_str.replace("Z", "+00:00"))
        now = datetime.now(timezone.utc)
        diff = int((now - dt).total_seconds())
        if diff < 3600:
            return f"{diff // 60} phút trước"
        if diff < 86400:
            return f"{diff // 3600} giờ trước"
        return f"{diff // 86400} ngày trước"
    except:
        return "vừa xong"

# ═══════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════
def fetch_all():
    articles = []
    seen = set()

    for src in SOURCES:
        try:
            print(f"⏳ Fetching: {src['name']} ...")
            feed = feedparser.parse(src["url"], request_headers={"User-Agent": "FnBIntelHub/1.0"})
            count = 0
            for entry in feed.entries[:25]:
                url = entry.get("link", "")
                if not url or url in seen:
                    continue
                title = entry.get("title", "").strip()
                desc = clean_html(entry.get("summary", entry.get("description", "")))
                if not title or not is_fnb(title, desc):
                    continue
                seen.add(url)
                pub = parse_date(entry)
                topics = detect_topics(title, desc)
                brands = detect_brands(title, desc)
                region = detect_region(src["region"], title, desc)
                # build data-tags string for frontend filtering
                tags = " ".join(set([f"source-{src['key']}", region] + topics + brands))
                articles.append({
                    "id": hashlib.md5(url.encode()).hexdigest()[:8],
                    "title": title,
                    "url": url,
                    "source_name": src["name"],
                    "source_key": src["key"],
                    "badge": src["badge"],
                    "region": region,
                    "tags": tags,
                    "topics": topics,
                    "brands": brands,
                    "published": pub,
                    "time_ago": time_ago(pub),
                    "summary": desc,
                    "is_new": True,
                    "is_hot": len(desc) > 200 or len(topics) >= 2,
                    "lang": src["lang"],
                })
                count += 1
            print(f"   ✅ {count} F&B articles found")
        except Exception as e:
            print(f"   ❌ Error: {e}")

    articles.sort(key=lambda x: x["published"], reverse=True)
    articles = articles[:60]

    output = {
        "updated": datetime.now(timezone.utc).isoformat(),
        "count": len(articles),
        "articles": articles,
    }

    with open("news.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"\n🎉 Done! {len(articles)} articles saved to news.json")

if __name__ == "__main__":
    fetch_all()
