"""Default source registry seeded into SQLite on init-db.

These are well-known public RSS/Atom feeds and public APIs. URLs should be
validated on first fetch; if a feed is unreachable it is marked with an error
and skipped, rather than crashing the run. No paywalled or private feeds.
"""

from __future__ import annotations

# source_type: rss | api | arxiv | github | html
# reliability_tier: 1 = primary/official, 2 = reputable, 3 = aggregator
DEFAULT_SOURCES: list[dict] = [
    # ---- Global AI (official / primary) ----
    {"name": "OpenAI Blog", "url": "https://openai.com/blog/rss.xml",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 9, "reliability_tier": 1},
    {"name": "Google DeepMind Blog", "url": "https://deepmind.google/blog/rss.xml",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 9, "reliability_tier": 1},
    {"name": "Hugging Face Blog", "url": "https://huggingface.co/blog/feed.xml",
     "category": "ai_engineering", "region": "global", "source_type": "rss",
     "priority": 8, "reliability_tier": 1},
    {"name": "NVIDIA Technical Blog", "url": "https://developer.nvidia.com/blog/feed",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 1},
    {"name": "Microsoft Source Blog", "url": "https://news.microsoft.com/source/feed/",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 1},

    # ---- AI engineering / agents / frameworks ----
    {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/",
     "category": "ai_engineering", "region": "global", "source_type": "rss",
     "priority": 9, "reliability_tier": 1},
    {"name": "BAIR Blog (Berkeley AI)", "url": "https://bair.berkeley.edu/blog/feed.xml",
     "category": "research", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 1},

    # ---- Research (arXiv) ----
    {"name": "arXiv cs.AI", "url": "http://export.arxiv.org/rss/cs.AI",
     "category": "research", "region": "global", "source_type": "arxiv",
     "priority": 8, "reliability_tier": 1},
    {"name": "arXiv cs.LG", "url": "http://export.arxiv.org/rss/cs.LG",
     "category": "research", "region": "global", "source_type": "arxiv",
     "priority": 8, "reliability_tier": 1},
    {"name": "arXiv cs.CL", "url": "http://export.arxiv.org/rss/cs.CL",
     "category": "research", "region": "global", "source_type": "arxiv",
     "priority": 7, "reliability_tier": 1},

    # ---- Software engineering ----
    {"name": "Python Insider", "url": "https://blog.python.org/feeds/posts/default",
     "category": "software", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 1},
    {"name": "GitHub Blog", "url": "https://github.blog/feed/",
     "category": "software", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 1},
    {"name": "Node.js Blog", "url": "https://nodejs.org/en/feed/blog.xml",
     "category": "software", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 1},
    {"name": "Vercel Blog", "url": "https://vercel.com/atom",
     "category": "software", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 2},

    # ---- Indian technology / AI ecosystem ----
    {"name": "Inc42", "url": "https://inc42.com/feed/",
     "category": "indian_tech", "region": "india", "source_type": "rss",
     "priority": 7, "reliability_tier": 2},
    {"name": "YourStory", "url": "https://yourstory.com/feed",
     "category": "indian_tech", "region": "india", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},
    {"name": "Analytics India Magazine", "url": "https://analyticsindiamag.com/feed/",
     "category": "indian_tech", "region": "india", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},
    {"name": "The Hindu Sci-Tech", "url": "https://www.thehindu.com/sci-tech/technology/feeder/default.rss",
     "category": "indian_tech", "region": "india", "source_type": "rss",
     "priority": 5, "reliability_tier": 2},

    # ---- Broad tech press (aggregators) ----
    {"name": "TechCrunch AI", "url": "https://techcrunch.com/category/artificial-intelligence/feed/",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 3},
    {"name": "VentureBeat AI", "url": "https://venturebeat.com/category/ai/feed/",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 3},
    {"name": "The Verge AI", "url": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 3},
    {"name": "Ars Technica", "url": "https://feeds.arstechnica.com/arstechnica/index",
     "category": "software", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 3},

    # ---- AI news & articles (dedicated AI press) ----
    {"name": "MIT Technology Review - AI",
     "url": "https://www.technologyreview.com/topic/artificial-intelligence/feed/",
     "category": "ai_news", "region": "global", "source_type": "rss",
     "priority": 8, "reliability_tier": 2},
    {"name": "The Decoder", "url": "https://the-decoder.com/feed/",
     "category": "ai_news", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},
    {"name": "MarkTechPost", "url": "https://www.marktechpost.com/feed/",
     "category": "ai_news", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 3},
    {"name": "Google Blog - AI", "url": "https://blog.google/technology/ai/rss/",
     "category": "ai_news", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 1},
    {"name": "AWS Machine Learning Blog",
     "url": "https://aws.amazon.com/blogs/machine-learning/feed/",
     "category": "ai_news", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 1},

    # ---- World tech news ----
    {"name": "TechCrunch", "url": "https://techcrunch.com/feed/",
     "category": "tech_news", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 3},
    {"name": "The Verge", "url": "https://www.theverge.com/rss/index.xml",
     "category": "tech_news", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 3},
    {"name": "Wired", "url": "https://www.wired.com/feed/rss",
     "category": "tech_news", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},
    {"name": "Engadget", "url": "https://www.engadget.com/rss.xml",
     "category": "tech_news", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 3},
    {"name": "Hacker News (front page)", "url": "https://hnrss.org/frontpage",
     "category": "trending_tech", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 3},
    {"name": "TechRadar", "url": "https://www.techradar.com/rss",
     "category": "tech_news", "region": "global", "source_type": "rss",
     "priority": 4, "reliability_tier": 3},

    # ---- Business news ----
    {"name": "CNBC Business", "url": "https://www.cnbc.com/id/10001147/device/rss/rss.html",
     "category": "business", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},
    {"name": "CNBC Technology", "url": "https://www.cnbc.com/id/19854910/device/rss/rss.html",
     "category": "business", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},
    {"name": "BBC Business", "url": "https://feeds.bbci.co.uk/news/business/rss.xml",
     "category": "business", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 1},
    {"name": "Fortune", "url": "https://fortune.com/feed/",
     "category": "business", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 2},
    {"name": "Business Insider", "url": "https://www.businessinsider.com/rss",
     "category": "business", "region": "global", "source_type": "rss",
     "priority": 4, "reliability_tier": 3},

    # ---- Deals / funding / M&A (AI + business deals) ----
    {"name": "TechCrunch Venture", "url": "https://techcrunch.com/category/venture/feed/",
     "category": "deals", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 3},
    {"name": "TechCrunch Startups", "url": "https://techcrunch.com/category/startups/feed/",
     "category": "deals", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 3},
    {"name": "Crunchbase News", "url": "https://news.crunchbase.com/feed/",
     "category": "deals", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},

    # ---- Geopolitics / world affairs ----
    {"name": "BBC World", "url": "https://feeds.bbci.co.uk/news/world/rss.xml",
     "category": "geopolitics", "region": "global", "source_type": "rss",
     "priority": 6, "reliability_tier": 1},
    {"name": "Al Jazeera", "url": "https://www.aljazeera.com/xml/rss/all.xml",
     "category": "geopolitics", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 2},
    {"name": "The Guardian World", "url": "https://www.theguardian.com/world/rss",
     "category": "geopolitics", "region": "global", "source_type": "rss",
     "priority": 5, "reliability_tier": 2},
    {"name": "Reuters World (Google News)",
     "url": "https://news.google.com/rss/search?q=when:1d+geopolitics+technology&hl=en-US&gl=US&ceid=US:en",
     "category": "geopolitics", "region": "global", "source_type": "rss",
     "priority": 4, "reliability_tier": 3},

    # ---- Devices / gadgets / consumer tech ----
    {"name": "9to5Google", "url": "https://9to5google.com/feed/",
     "category": "devices", "region": "global", "source_type": "rss",
     "priority": 4, "reliability_tier": 3},
    {"name": "9to5Mac", "url": "https://9to5mac.com/feed/",
     "category": "devices", "region": "global", "source_type": "rss",
     "priority": 4, "reliability_tier": 3},
    {"name": "GSMArena", "url": "https://www.gsmarena.com/rss-news-reviews.php3",
     "category": "devices", "region": "global", "source_type": "rss",
     "priority": 4, "reliability_tier": 3},

    # ---- More Indian business / tech ----
    {"name": "ETtech (Economic Times)",
     "url": "https://economictimes.indiatimes.com/tech/rssfeeds/13357270.cms",
     "category": "indian_tech", "region": "india", "source_type": "rss",
     "priority": 6, "reliability_tier": 2},
    {"name": "Livemint Technology", "url": "https://www.livemint.com/rss/technology",
     "category": "indian_tech", "region": "india", "source_type": "rss",
     "priority": 5, "reliability_tier": 2},
]
