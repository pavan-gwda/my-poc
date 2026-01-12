"""Signal generator combining all data sources for market predictions."""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime
from .price_tracker import PriceTracker
from .news_aggregator import NewsAggregator
from .economic_calendar import EconomicCalendar


@dataclass
class MarketSignal:
    """Market signal/prediction."""
    asset: str
    asset_type: str  # "stock", "gold", "silver", "index"
    signal: str  # "strong_buy", "buy", "hold", "sell", "strong_sell"
    confidence: float  # 0-100
    price: float
    target_price: Optional[float]
    stop_loss: Optional[float]
    timeframe: str  # "short_term", "medium_term", "long_term"
    reasons: List[str]
    risks: List[str]
    generated_at: datetime


class SignalGenerator:
    """Generates trading signals based on multiple data sources."""

    def __init__(self):
        self.price_tracker = PriceTracker()
        self.news_aggregator = NewsAggregator()
        self.economic_calendar = EconomicCalendar()

    def generate_gold_signal(self) -> MarketSignal:
        """Generate signal for gold (INR)."""
        gold = self.price_tracker.get_gold_price()
        sentiment = self.news_aggregator.get_market_sentiment()
        gold_news = self.news_aggregator.get_gold_silver_news()["gold"]
        rbi_events = self.economic_calendar.get_fed_calendar()  # Uses RBI calendar now

        reasons = []
        risks = []
        score = 50  # Neutral starting point

        if not gold:
            return self._create_neutral_signal("Gold", "gold", 0)

        # Price momentum
        if gold.change_percent > 1:
            score += 10
            reasons.append(f"Positive momentum: +{gold.change_percent:.1f}% today")
        elif gold.change_percent < -1:
            score -= 10
            risks.append(f"Negative momentum: {gold.change_percent:.1f}% today")

        # News sentiment for gold
        if gold_news:
            gold_sentiment = sum(1 for n in gold_news if n.sentiment == "bullish")
            gold_bearish = sum(1 for n in gold_news if n.sentiment == "bearish")
            if gold_sentiment > gold_bearish:
                score += 15
                reasons.append(f"Bullish news sentiment ({gold_sentiment} positive articles)")
            elif gold_bearish > gold_sentiment:
                score -= 10
                risks.append(f"Bearish news sentiment ({gold_bearish} negative articles)")

        # Market uncertainty (usually good for gold)
        if sentiment.get("sentiment") == "bearish":
            score += 10
            reasons.append("Safe haven demand: Market sentiment is bearish")

        # RBI policy impact
        if rbi_events:
            next_rbi = rbi_events[0]
            days_to_rbi = next_rbi["days_until"]
            if days_to_rbi <= 7:
                risks.append(f"RBI MPC meeting in {days_to_rbi} days - volatility expected")
                score -= 5  # Uncertainty

        # Economic factors
        econ_news = self.news_aggregator.get_fed_economic_news()
        rate_cut_mentions = sum(1 for n in econ_news if "rate cut" in n.title.lower())
        rate_hike_mentions = sum(1 for n in econ_news if "rate hike" in n.title.lower())

        if rate_cut_mentions > rate_hike_mentions:
            score += 15
            reasons.append("Rate cut expectations (bullish for gold)")
        elif rate_hike_mentions > rate_cut_mentions:
            score -= 10
            risks.append("Rate hike concerns (bearish for gold)")

        # Generate signal
        signal = self._score_to_signal(score)
        target = gold.price_inr * 1.05 if score > 60 else gold.price_inr * 0.98
        stop_loss = gold.price_inr * 0.97 if score > 60 else None

        return MarketSignal(
            asset="Gold",
            asset_type="gold",
            signal=signal,
            confidence=min(100, max(0, abs(score - 50) * 2)),
            price=gold.price_inr,
            target_price=target,
            stop_loss=stop_loss,
            timeframe="short_term",
            reasons=reasons if reasons else ["No strong signals"],
            risks=risks if risks else ["Normal market conditions"],
            generated_at=datetime.now()
        )

    def generate_silver_signal(self) -> MarketSignal:
        """Generate signal for silver (INR)."""
        silver = self.price_tracker.get_silver_price()
        gold = self.price_tracker.get_gold_price()
        sentiment = self.news_aggregator.get_market_sentiment()
        silver_news = self.news_aggregator.get_gold_silver_news()["silver"]

        reasons = []
        risks = []
        score = 50

        if not silver:
            return self._create_neutral_signal("Silver", "silver", 0)

        # Price momentum
        if silver.change_percent > 1.5:
            score += 12
            reasons.append(f"Strong momentum: +{silver.change_percent:.1f}% today")
        elif silver.change_percent < -1.5:
            score -= 12
            risks.append(f"Weak momentum: {silver.change_percent:.1f}% today")

        # Gold/Silver ratio analysis (using per-gram prices)
        if gold and silver.price_per_gram > 0:
            gs_ratio = gold.price_per_gram / silver.price_per_gram
            if gs_ratio > 80:
                score += 10
                reasons.append(f"Gold/Silver ratio high ({gs_ratio:.0f}) - silver undervalued")
            elif gs_ratio < 60:
                score -= 5
                risks.append(f"Gold/Silver ratio low ({gs_ratio:.0f}) - silver may be overvalued")

        # Industrial demand sentiment
        if sentiment.get("sentiment") == "bullish":
            score += 8
            reasons.append("Industrial demand outlook positive (bullish market)")

        # News sentiment
        if silver_news:
            bullish = sum(1 for n in silver_news if n.sentiment == "bullish")
            bearish = sum(1 for n in silver_news if n.sentiment == "bearish")
            if bullish > bearish:
                score += 10
                reasons.append(f"Positive silver news ({bullish} articles)")

        signal = self._score_to_signal(score)
        target = silver.price_inr * 1.07 if score > 60 else silver.price_inr * 0.97
        stop_loss = silver.price_inr * 0.95 if score > 60 else None

        return MarketSignal(
            asset="Silver",
            asset_type="silver",
            signal=signal,
            confidence=min(100, max(0, abs(score - 50) * 2)),
            price=silver.price_inr,
            target_price=target,
            stop_loss=stop_loss,
            timeframe="short_term",
            reasons=reasons if reasons else ["No strong signals"],
            risks=risks if risks else ["Normal market conditions"],
            generated_at=datetime.now()
        )

    def generate_market_signal(self) -> MarketSignal:
        """Generate overall market signal (NIFTY 50)."""
        indices = self.price_tracker.get_market_indices()
        sentiment = self.news_aggregator.get_market_sentiment()
        rbi_events = self.economic_calendar.get_fed_calendar()

        nifty = indices.get("^NSEI")
        india_vix = indices.get("^INDIAVIX")

        reasons = []
        risks = []
        score = 50

        if not nifty:
            return self._create_neutral_signal("NIFTY 50", "index", 0)

        # Price action
        if nifty.change_percent > 0.5:
            score += 10
            reasons.append(f"Positive price action: +{nifty.change_percent:.1f}%")
        elif nifty.change_percent < -0.5:
            score -= 10
            risks.append(f"Negative price action: {nifty.change_percent:.1f}%")

        # India VIX (fear indicator)
        if india_vix:
            if india_vix.current_price < 12:
                score += 5
                reasons.append(f"Low volatility (India VIX: {india_vix.current_price:.1f})")
            elif india_vix.current_price > 20:
                score -= 15
                risks.append(f"High fear (India VIX: {india_vix.current_price:.1f})")
            elif india_vix.current_price > 15:
                score -= 5
                risks.append(f"Elevated volatility (India VIX: {india_vix.current_price:.1f})")

        # News sentiment
        if sentiment.get("sentiment") == "bullish":
            score += 10
            reasons.append(f"Bullish news sentiment ({sentiment.get('bullish_percent', 0):.0f}% positive)")
        elif sentiment.get("sentiment") == "bearish":
            score -= 10
            risks.append(f"Bearish news sentiment ({sentiment.get('bearish_percent', 0):.0f}% negative)")

        # 52-week position
        if nifty.week_52_high > 0:
            position = (nifty.current_price - nifty.week_52_low) / (nifty.week_52_high - nifty.week_52_low) * 100
            if position > 90:
                risks.append("Near 52-week high - potential resistance")
                score -= 5
            elif position < 20:
                reasons.append("Near 52-week low - potential value")
                score += 10

        signal = self._score_to_signal(score)

        return MarketSignal(
            asset="NIFTY 50",
            asset_type="index",
            signal=signal,
            confidence=min(100, max(0, abs(score - 50) * 2)),
            price=nifty.current_price,
            target_price=nifty.current_price * 1.03 if score > 60 else nifty.current_price * 0.98,
            stop_loss=nifty.current_price * 0.97 if score > 60 else None,
            timeframe="short_term",
            reasons=reasons if reasons else ["No strong signals"],
            risks=risks if risks else ["Normal market conditions"],
            generated_at=datetime.now()
        )

    def generate_all_signals(self) -> Dict[str, MarketSignal]:
        """Generate signals for all tracked assets."""
        return {
            "gold": self.generate_gold_signal(),
            "silver": self.generate_silver_signal(),
            "market": self.generate_market_signal(),
        }

    def get_daily_briefing(self) -> Dict:
        """Generate comprehensive daily market briefing."""
        signals = self.generate_all_signals()
        sentiment = self.news_aggregator.get_market_sentiment()
        market_status = self.economic_calendar.get_market_hours_status()
        week_preview = self.economic_calendar.get_week_preview()

        # Get breaking news
        breaking = self.news_aggregator.get_breaking_news(hours=4)

        return {
            "generated_at": datetime.now().isoformat(),
            "market_status": market_status,
            "overall_sentiment": sentiment,
            "signals": {
                name: {
                    "signal": sig.signal,
                    "confidence": sig.confidence,
                    "price": sig.price,
                    "reasons": sig.reasons,
                    "risks": sig.risks,
                }
                for name, sig in signals.items()
            },
            "upcoming_events": week_preview,
            "breaking_news": [
                {"title": n.title, "source": n.source, "sentiment": n.sentiment}
                for n in breaking[:5]
            ],
            "key_levels": self._get_key_levels(),
        }

    def _get_key_levels(self) -> Dict:
        """Get key support/resistance levels."""
        gold = self.price_tracker.get_gold_price()
        silver = self.price_tracker.get_silver_price()
        indices = self.price_tracker.get_market_indices()

        levels = {}

        if gold:
            levels["gold"] = {
                "current": gold.price_usd,
                "support": round(gold.day_low * 0.99, 2),
                "resistance": round(gold.day_high * 1.01, 2),
            }

        if silver:
            levels["silver"] = {
                "current": silver.price_usd,
                "support": round(silver.day_low * 0.99, 2),
                "resistance": round(silver.day_high * 1.01, 2),
            }

        sp500 = indices.get("^GSPC")
        if sp500:
            levels["sp500"] = {
                "current": sp500.current_price,
                "support": round(sp500.day_low * 0.995, 2),
                "resistance": round(sp500.day_high * 1.005, 2),
                "52w_high": sp500.week_52_high,
                "52w_low": sp500.week_52_low,
            }

        return levels

    def _score_to_signal(self, score: int) -> str:
        """Convert numeric score to signal."""
        if score >= 75:
            return "strong_buy"
        elif score >= 60:
            return "buy"
        elif score >= 40:
            return "hold"
        elif score >= 25:
            return "sell"
        else:
            return "strong_sell"

    def _create_neutral_signal(self, asset: str, asset_type: str, price: float) -> MarketSignal:
        """Create a neutral signal when data is unavailable."""
        return MarketSignal(
            asset=asset,
            asset_type=asset_type,
            signal="hold",
            confidence=0,
            price=price,
            target_price=None,
            stop_loss=None,
            timeframe="short_term",
            reasons=["Insufficient data for analysis"],
            risks=["Unable to fetch current data"],
            generated_at=datetime.now()
        )
