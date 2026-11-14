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
    {"name": "Microsoft AI Blog", "url": "https://blogs.microsoft.com/ai/feed/",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 1},
    {"name": "Meta AI Blog", "url": "https://ai.meta.com/blog/rss/",
     "category": "global_ai", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 1},

    # ---- AI engineering / agents / frameworks ----
    {"name": "LangChain Blog", "url": "https://blog.langchain.dev/rss/",
     "category": "ai_engineering", "region": "global", "source_type": "rss",
     "priority": 9, "reliability_tier": 1},
    {"name": "Hugging Face Papers", "url": "https://huggingface.co/papers/feed",
     "category": "research", "region": "global", "source_type": "rss",
     "priority": 7, "reliability_tier": 2},

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
]
