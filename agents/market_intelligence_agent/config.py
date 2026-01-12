"""Configuration for Market Intelligence Agent."""

CONFIG = {
    # Watchlist - assets to track
    "watchlist": {
        "indices": ["^GSPC", "^DJI", "^IXIC", "^VIX"],  # S&P500, Dow, Nasdaq, VIX
        "metals": ["GC=F", "SI=F", "GLD", "SLV"],  # Gold futures, Silver futures, ETFs
        "stocks": [],  # User's custom stocks
    },

    # Penny stock criteria
    "penny_stock": {
        "max_price": 5.0,  # Max price to be considered penny stock
        "min_volume": 500000,  # Minimum daily volume
        "min_change_percent": 5.0,  # Minimum % change to flag
    },

    # Dip buying criteria
    "dip_criteria": {
        "drop_percent": -10.0,  # Consider if dropped more than this from 52w high
        "min_market_cap": 1_000_000_000,  # Min $1B market cap (avoid junk)
        "max_pe_ratio": 30,  # Reasonable valuation
    },

    # Potential risers criteria
    "potential_risers": {
        "min_analyst_rating": 3.5,  # Out of 5
        "min_revenue_growth": 10,  # % YoY
        "max_debt_equity": 1.5,
    },

    # News sources (RSS feeds)
    "news_feeds": [
        {"name": "Reuters Business", "url": "https://feeds.reuters.com/reuters/businessNews"},
        {"name": "CNBC Top News", "url": "https://search.cnbc.com/rs/search/combinedcms/view.xml?partnerId=wrss01&id=100003114"},
        {"name": "MarketWatch", "url": "https://feeds.marketwatch.com/marketwatch/topstories"},
        {"name": "Yahoo Finance", "url": "https://finance.yahoo.com/news/rssindex"},
        {"name": "Investing.com", "url": "https://www.investing.com/rss/news.rss"},
    ],

    # API Keys (free tiers)
    "api_keys": {
        "finnhub": "",  # Get free key at finnhub.io
        "alpha_vantage": "",  # Get free key at alphavantage.co
        "newsapi": "",  # Get free key at newsapi.org
    },

    # UI Settings
    "ui": {
        "refresh_interval_seconds": 60,  # Price refresh interval
        "news_refresh_minutes": 15,
        "theme": "dark",
    },

    # Market hours (EST)
    "market_hours": {
        "pre_market_start": "04:00",
        "market_open": "09:30",
        "market_close": "16:00",
        "after_hours_end": "20:00",
    },
}

# Sectors for screening
SECTORS = [
    "Technology", "Healthcare", "Financial", "Consumer Cyclical",
    "Communication Services", "Industrials", "Consumer Defensive",
    "Energy", "Utilities", "Real Estate", "Basic Materials"
]

# Key economic events that move markets
MARKET_MOVING_EVENTS = [
    "Federal Reserve Interest Rate Decision",
    "FOMC Meeting Minutes",
    "Consumer Price Index (CPI)",
    "Producer Price Index (PPI)",
    "Non-Farm Payrolls",
    "Unemployment Rate",
    "GDP Growth Rate",
    "Retail Sales",
    "ISM Manufacturing PMI",
    "ISM Services PMI",
    "Consumer Confidence",
    "Housing Starts",
    "Existing Home Sales",
    "Durable Goods Orders",
    "Trade Balance",
    "Treasury Yield Auction",
]

# Sentiment keywords for news analysis
BULLISH_KEYWORDS = [
    "surge", "soar", "rally", "jump", "gain", "rise", "bullish", "breakout",
    "record high", "beat expectations", "strong earnings", "upgrade",
    "buy rating", "outperform", "growth", "recovery", "optimism"
]

BEARISH_KEYWORDS = [
    "plunge", "crash", "tumble", "drop", "fall", "bearish", "breakdown",
    "record low", "miss expectations", "weak earnings", "downgrade",
    "sell rating", "underperform", "decline", "recession", "fear", "warning"
]
