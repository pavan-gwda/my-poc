"""News aggregator with sentiment analysis for market intelligence."""

import feedparser
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
import hashlib


@dataclass
class NewsArticle:
    """News article data."""
    title: str
    summary: str
    url: str
    source: str
    published: datetime
    sentiment: str  # "bullish", "bearish", "neutral"
    sentiment_score: float  # -1 to 1
    tickers_mentioned: List[str]
    keywords: List[str]
    category: str  # "stocks", "gold", "silver", "economy", "fed", "general"


# Sentiment keywords
BULLISH_KEYWORDS = [
    "surge", "soar", "rally", "jump", "gain", "rise", "bullish", "breakout",
    "record high", "beat expectations", "strong earnings", "upgrade", "growth",
    "buy rating", "outperform", "recovery", "optimism", "boom", "profit",
    "exceed", "positive", "upside", "momentum", "buying", "accumulate"
]

BEARISH_KEYWORDS = [
    "plunge", "crash", "tumble", "drop", "fall", "bearish", "breakdown",
    "record low", "miss expectations", "weak earnings", "downgrade", "decline",
    "sell rating", "underperform", "recession", "fear", "warning", "loss",
    "deficit", "negative", "downside", "selling", "correction", "crisis"
]

GOLD_KEYWORDS = ["gold", "bullion", "precious metal", "safe haven", "GLD", "gold price"]
SILVER_KEYWORDS = ["silver", "SLV", "silver price", "white metal"]
FED_KEYWORDS = ["federal reserve", "fed", "interest rate", "powell", "fomc", "monetary policy", "rate hike", "rate cut"]
ECONOMY_KEYWORDS = ["inflation", "cpi", "gdp", "unemployment", "jobs report", "economic", "treasury", "yield"]


class NewsAggregator:
    """Aggregates news from multiple sources with sentiment analysis."""

    RSS_FEEDS = [
        {"name": "Reuters Business", "url": "https://feeds.reuters.com/reuters/businessNews", "category": "general"},
        {"name": "CNBC", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114", "category": "general"},
        {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories", "category": "stocks"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex", "category": "stocks"},
        {"name": "Investing.com", "url": "https://www.investing.com/rss/news.rss", "category": "general"},
        {"name": "Bloomberg Markets", "url": "https://feeds.bloomberg.com/markets/news.rss", "category": "stocks"},
        {"name": "WSJ Markets", "url": "https://feeds.wsj.com/xml/rss/3_7031.xml", "category": "stocks"},
    ]

    def __init__(self):
        self._cache: Dict[str, NewsArticle] = {}
        self._cache_time = None
        self._cache_ttl = timedelta(minutes=15)

    def fetch_all_news(self, max_per_source: int = 10) -> List[NewsArticle]:
        """Fetch news from all RSS feeds."""
        all_news = []

        def fetch_feed(feed_info):
            try:
                return self._parse_rss_feed(
                    feed_info["url"],
                    feed_info["name"],
                    feed_info.get("category", "general"),
                    max_per_source
                )
            except Exception as e:
                print(f"Error fetching {feed_info['name']}: {e}")
                return []

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {executor.submit(fetch_feed, feed): feed for feed in self.RSS_FEEDS}
            for future in as_completed(futures):
                result = future.result()
                all_news.extend(result)

        # Sort by date
        all_news.sort(key=lambda x: x.published, reverse=True)

        # Remove duplicates by title similarity
        seen_titles = set()
        unique_news = []
        for article in all_news:
            title_hash = hashlib.md5(article.title.lower()[:50].encode()).hexdigest()
            if title_hash not in seen_titles:
                seen_titles.add(title_hash)
                unique_news.append(article)

        return unique_news

    def _parse_rss_feed(self, url: str, source: str, category: str, max_items: int) -> List[NewsArticle]:
        """Parse an RSS feed."""
        articles = []

        try:
            feed = feedparser.parse(url)

            for entry in feed.entries[:max_items]:
                title = entry.get('title', '')
                summary = entry.get('summary', entry.get('description', ''))

                # Clean HTML from summary
                if summary:
                    summary = BeautifulSoup(summary, 'html.parser').get_text()
                    summary = summary[:500]  # Truncate

                # Parse date
                published = datetime.now()
                if hasattr(entry, 'published_parsed') and entry.published_parsed:
                    try:
                        published = datetime(*entry.published_parsed[:6])
                    except:
                        pass

                # Analyze sentiment
                text = f"{title} {summary}"
                sentiment, score = self._analyze_sentiment(text)

                # Extract tickers
                tickers = self._extract_tickers(text)

                # Determine category
                article_category = self._categorize_article(text, category)

                # Extract keywords
                keywords = self._extract_keywords(text)

                articles.append(NewsArticle(
                    title=title,
                    summary=summary,
                    url=entry.get('link', ''),
                    source=source,
                    published=published,
                    sentiment=sentiment,
                    sentiment_score=score,
                    tickers_mentioned=tickers,
                    keywords=keywords,
                    category=article_category
                ))

        except Exception as e:
            print(f"Error parsing feed {url}: {e}")

        return articles

    def _analyze_sentiment(self, text: str) -> tuple[str, float]:
        """Analyze sentiment of text."""
        text_lower = text.lower()

        bullish_count = sum(1 for word in BULLISH_KEYWORDS if word in text_lower)
        bearish_count = sum(1 for word in BEARISH_KEYWORDS if word in text_lower)

        total = bullish_count + bearish_count
        if total == 0:
            return "neutral", 0.0

        score = (bullish_count - bearish_count) / total

        if score > 0.3:
            return "bullish", score
        elif score < -0.3:
            return "bearish", score
        else:
            return "neutral", score

    def _extract_tickers(self, text: str) -> List[str]:
        """Extract stock tickers from text."""
        # Common pattern: $AAPL or (AAPL) or ticker AAPL
        patterns = [
            r'\$([A-Z]{1,5})\b',  # $AAPL
            r'\(([A-Z]{1,5})\)',  # (AAPL)
            r'\b([A-Z]{2,5})\s+(?:stock|shares|ticker)',  # AAPL stock
        ]

        tickers = set()
        for pattern in patterns:
            matches = re.findall(pattern, text)
            tickers.update(matches)

        # Filter out common non-ticker words
        non_tickers = {"CEO", "IPO", "ETF", "GDP", "CPI", "FDA", "SEC", "NYSE", "NASDAQ", "USA", "USD", "THE", "FOR"}
        tickers = [t for t in tickers if t not in non_tickers]

        return list(tickers)[:5]  # Max 5 tickers

    def _categorize_article(self, text: str, default_category: str) -> str:
        """Categorize article based on content."""
        text_lower = text.lower()

        if any(kw in text_lower for kw in GOLD_KEYWORDS):
            return "gold"
        elif any(kw in text_lower for kw in SILVER_KEYWORDS):
            return "silver"
        elif any(kw in text_lower for kw in FED_KEYWORDS):
            return "fed"
        elif any(kw in text_lower for kw in ECONOMY_KEYWORDS):
            return "economy"
        else:
            return default_category

    def _extract_keywords(self, text: str) -> List[str]:
        """Extract important keywords from text."""
        text_lower = text.lower()
        keywords = []

        all_keywords = BULLISH_KEYWORDS + BEARISH_KEYWORDS + GOLD_KEYWORDS + SILVER_KEYWORDS + FED_KEYWORDS + ECONOMY_KEYWORDS

        for kw in all_keywords:
            if kw in text_lower:
                keywords.append(kw)

        return keywords[:10]

    def get_news_by_category(self, category: str) -> List[NewsArticle]:
        """Get news filtered by category."""
        all_news = self.fetch_all_news()
        return [n for n in all_news if n.category == category]

    def get_news_by_ticker(self, ticker: str) -> List[NewsArticle]:
        """Get news mentioning a specific ticker."""
        all_news = self.fetch_all_news()
        ticker_upper = ticker.upper()
        return [n for n in all_news if ticker_upper in n.tickers_mentioned or ticker_upper in n.title.upper()]

    def get_market_sentiment(self) -> Dict:
        """Get overall market sentiment from recent news."""
        news = self.fetch_all_news(max_per_source=20)

        if not news:
            return {"sentiment": "neutral", "score": 0, "bullish_count": 0, "bearish_count": 0}

        bullish = sum(1 for n in news if n.sentiment == "bullish")
        bearish = sum(1 for n in news if n.sentiment == "bearish")
        neutral = sum(1 for n in news if n.sentiment == "neutral")
        total = len(news)

        avg_score = sum(n.sentiment_score for n in news) / total if total else 0

        if avg_score > 0.2:
            overall = "bullish"
        elif avg_score < -0.2:
            overall = "bearish"
        else:
            overall = "neutral"

        return {
            "sentiment": overall,
            "score": avg_score,
            "bullish_count": bullish,
            "bearish_count": bearish,
            "neutral_count": neutral,
            "total_articles": total,
            "bullish_percent": (bullish / total * 100) if total else 0,
            "bearish_percent": (bearish / total * 100) if total else 0,
        }

    def get_gold_silver_news(self) -> Dict[str, List[NewsArticle]]:
        """Get news specifically about gold and silver."""
        all_news = self.fetch_all_news()

        return {
            "gold": [n for n in all_news if n.category == "gold" or any(kw in n.title.lower() for kw in GOLD_KEYWORDS)],
            "silver": [n for n in all_news if n.category == "silver" or any(kw in n.title.lower() for kw in SILVER_KEYWORDS)],
        }

    def get_fed_economic_news(self) -> List[NewsArticle]:
        """Get Fed and economic news that affects markets."""
        all_news = self.fetch_all_news()
        return [n for n in all_news if n.category in ("fed", "economy")]

    def get_breaking_news(self, hours: int = 2) -> List[NewsArticle]:
        """Get breaking news from the last N hours."""
        all_news = self.fetch_all_news()
        cutoff = datetime.now() - timedelta(hours=hours)
        return [n for n in all_news if n.published > cutoff]

    def get_sentiment_summary(self) -> Dict:
        """Get sentiment summary by category."""
        all_news = self.fetch_all_news()

        categories = ["stocks", "gold", "silver", "fed", "economy", "general"]
        summary = {}

        for cat in categories:
            cat_news = [n for n in all_news if n.category == cat]
            if cat_news:
                avg_score = sum(n.sentiment_score for n in cat_news) / len(cat_news)
                summary[cat] = {
                    "count": len(cat_news),
                    "avg_sentiment": avg_score,
                    "sentiment_label": "bullish" if avg_score > 0.2 else "bearish" if avg_score < -0.2 else "neutral"
                }

        return summary
