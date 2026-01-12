"""Stock screener for finding opportunities in Indian markets (NSE/BSE)."""

import yfinance as yf
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed


@dataclass
class StockOpportunity:
    """Stock opportunity data."""
    symbol: str
    name: str
    current_price: float  # Price in INR
    change_percent: float
    volume: int
    market_cap: Optional[float]
    signal_type: str  # "penny", "dip", "momentum", "breakout"
    signal_strength: float  # 0-100
    reason: str
    sector: str
    last_updated: datetime


class StockScreener:
    """Screens Indian stocks (NSE) for various opportunities."""

    # NIFTY 50 & Popular NSE stocks (.NS suffix for Yahoo Finance)
    POPULAR_TICKERS = [
        # NIFTY 50 - IT
        "TCS.NS", "INFY.NS", "WIPRO.NS", "HCLTECH.NS", "TECHM.NS", "LTIM.NS",
        # NIFTY 50 - Banks
        "HDFCBANK.NS", "ICICIBANK.NS", "KOTAKBANK.NS", "AXISBANK.NS", "SBIN.NS", "INDUSINDBK.NS",
        # NIFTY 50 - Finance
        "BAJFINANCE.NS", "BAJAJFINSV.NS", "SBILIFE.NS", "HDFCLIFE.NS",
        # NIFTY 50 - Auto
        "TATAMOTORS.NS", "MARUTI.NS", "M&M.NS", "HEROMOTOCO.NS", "BAJAJ-AUTO.NS", "EICHERMOT.NS",
        # NIFTY 50 - Pharma
        "SUNPHARMA.NS", "DRREDDY.NS", "CIPLA.NS", "DIVISLAB.NS", "APOLLOHOSP.NS",
        # NIFTY 50 - Energy & Oil
        "RELIANCE.NS", "ONGC.NS", "BPCL.NS", "IOC.NS", "NTPC.NS", "POWERGRID.NS",
        # NIFTY 50 - Metals & Mining
        "TATASTEEL.NS", "HINDALCO.NS", "JSWSTEEL.NS", "COALINDIA.NS", "VEDL.NS",
        # NIFTY 50 - FMCG
        "HINDUNILVR.NS", "ITC.NS", "NESTLEIND.NS", "BRITANNIA.NS", "DABUR.NS",
        # NIFTY 50 - Others
        "ASIANPAINT.NS", "ULTRACEMCO.NS", "TITAN.NS", "ADANIENT.NS", "ADANIPORTS.NS",
        "BHARTIARTL.NS", "GRASIM.NS", "HINDZINC.NS", "UPL.NS", "TATACONSUM.NS",
    ]

    # Small-cap & Mid-cap Indian stocks with potential
    PENNY_CANDIDATES = [
        # Small-cap IT
        "RATEGAIN.NS", "ROUTE.NS", "TANLA.NS", "HAPPSTMNDS.NS",
        # Small-cap Finance
        "IIFL.NS", "POONAWALLA.NS", "UJJIVANSFB.NS", "EQUITASBNK.NS",
        # Small-cap Pharma
        "GRANULES.NS", "LAURUSLABS.NS", "AUROPHARMA.NS", "ALKEM.NS",
        # Small-cap Auto
        "TVSMOTOR.NS", "MOTHERSON.NS", "BALKRISIND.NS", "EXIDEIND.NS",
        # PSU & Infra
        "IRCTC.NS", "IRFC.NS", "RVNL.NS", "NHPC.NS", "SJVN.NS",
        # Banks
        "YESBANK.NS", "BANDHANBNK.NS", "IDFCFIRSTB.NS",
        "PNB.NS", "BANKBARODA.NS", "CANBK.NS",
        # New-age Tech
        "DELHIVERY.NS", "POLICYBZR.NS",
        # Others
        "TRENT.NS", "PERSISTENT.NS", "COFORGE.NS", "MPHASIS.NS",
    ]

    def __init__(self):
        self._cache = {}
        self._lock = threading.Lock()

    def scan_penny_stocks(self, max_price: float = 500.0, min_volume: int = 100000) -> List[StockOpportunity]:
        """Find small-cap stocks with high volume and momentum (INR)."""
        opportunities = []

        def check_stock(symbol):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="5d")

                if hist.empty:
                    return None

                price = hist['Close'].iloc[-1]
                volume = int(hist['Volume'].iloc[-1])

                # Filter criteria (INR prices)
                if price > max_price or price < 1:
                    return None
                if volume < min_volume:
                    return None

                # Calculate momentum
                prev_price = hist['Close'].iloc[0]
                change_pct = ((price - prev_price) / prev_price * 100) if prev_price else 0

                # Signal strength based on volume and momentum
                vol_score = min(50, (volume / min_volume) * 10)
                mom_score = min(50, abs(change_pct) * 5) if change_pct > 0 else 0
                signal = vol_score + mom_score

                if signal < 20:
                    return None

                reason = f"Rs {price:.2f}, Vol {volume:,}, "
                if change_pct > 5:
                    reason += f"UP {change_pct:.1f}% in 5 days"
                elif change_pct > 0:
                    reason += f"up {change_pct:.1f}% in 5 days"
                else:
                    reason += f"down {change_pct:.1f}% (potential reversal)"

                return StockOpportunity(
                    symbol=symbol.replace('.NS', ''),  # Remove suffix for display
                    name=info.get('shortName', symbol),
                    current_price=price,
                    change_percent=change_pct,
                    volume=volume,
                    market_cap=info.get('marketCap'),
                    signal_type="penny",
                    signal_strength=signal,
                    reason=reason,
                    sector=info.get('sector', 'Unknown'),
                    last_updated=datetime.now()
                )
            except Exception as e:
                return None

        # Use thread pool for faster scanning
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_stock, sym): sym for sym in self.PENNY_CANDIDATES}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    opportunities.append(result)

        return sorted(opportunities, key=lambda x: x.signal_strength, reverse=True)

    def scan_dip_opportunities(self, drop_percent: float = -15.0, min_market_cap: float = 1e10) -> List[StockOpportunity]:
        """Find quality Indian stocks that have dropped significantly from 52-week high."""
        opportunities = []

        def check_stock(symbol):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1d")

                if hist.empty:
                    return None

                price = hist['Close'].iloc[-1]
                high_52w = info.get('fiftyTwoWeekHigh', 0)
                market_cap = info.get('marketCap', 0)

                if not high_52w or market_cap < min_market_cap:
                    return None

                # Calculate drop from 52w high
                drop_from_high = ((price - high_52w) / high_52w * 100)

                if drop_from_high > drop_percent:  # Not dropped enough
                    return None

                # Check fundamentals for quality
                pe_ratio = info.get('trailingPE', 0)
                profit_margin = info.get('profitMargins', 0)

                # Signal strength based on fundamentals and drop
                signal = 50  # Base score
                signal += min(20, abs(drop_from_high))  # More drop = higher score
                if pe_ratio and 0 < pe_ratio < 25:
                    signal += 15  # Good PE
                if profit_margin and profit_margin > 0.1:
                    signal += 15  # Profitable

                reason = f"Down {drop_from_high:.1f}% from 52w high (Rs {high_52w:.2f})"
                if pe_ratio:
                    reason += f", PE: {pe_ratio:.1f}"

                return StockOpportunity(
                    symbol=symbol.replace('.NS', ''),
                    name=info.get('shortName', symbol),
                    current_price=price,
                    change_percent=drop_from_high,
                    volume=int(info.get('volume', 0)),
                    market_cap=market_cap,
                    signal_type="dip",
                    signal_strength=min(100, signal),
                    reason=reason,
                    sector=info.get('sector', 'Unknown'),
                    last_updated=datetime.now()
                )
            except Exception as e:
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_stock, sym): sym for sym in self.POPULAR_TICKERS}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    opportunities.append(result)

        return sorted(opportunities, key=lambda x: x.signal_strength, reverse=True)

    def scan_momentum_stocks(self, min_change: float = 5.0) -> List[StockOpportunity]:
        """Find stocks with strong upward momentum."""
        opportunities = []

        def check_stock(symbol):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1mo")

                if len(hist) < 5:
                    return None

                price = hist['Close'].iloc[-1]
                price_5d = hist['Close'].iloc[-5]
                price_20d = hist['Close'].iloc[0]
                volume = int(hist['Volume'].iloc[-1])
                avg_volume = int(hist['Volume'].mean())

                # Calculate momentum
                change_5d = ((price - price_5d) / price_5d * 100) if price_5d else 0
                change_20d = ((price - price_20d) / price_20d * 100) if price_20d else 0

                if change_5d < min_change:
                    return None

                # Volume spike indicator
                vol_ratio = volume / avg_volume if avg_volume else 1

                # Signal strength
                signal = 0
                signal += min(30, change_5d * 2)  # 5-day momentum
                signal += min(30, change_20d)  # 20-day momentum
                signal += min(20, vol_ratio * 10)  # Volume spike
                if info.get('recommendationMean', 5) < 2.5:
                    signal += 20  # Analyst buy rating

                reason = f"5d: +{change_5d:.1f}%, 20d: +{change_20d:.1f}%"
                if vol_ratio > 1.5:
                    reason += f", Vol {vol_ratio:.1f}x avg"

                return StockOpportunity(
                    symbol=symbol.replace('.NS', ''),
                    name=info.get('shortName', symbol),
                    current_price=price,
                    change_percent=change_5d,
                    volume=volume,
                    market_cap=info.get('marketCap'),
                    signal_type="momentum",
                    signal_strength=min(100, signal),
                    reason=reason,
                    sector=info.get('sector', 'Unknown'),
                    last_updated=datetime.now()
                )
            except Exception as e:
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            all_tickers = self.POPULAR_TICKERS + self.PENNY_CANDIDATES
            futures = {executor.submit(check_stock, sym): sym for sym in all_tickers}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    opportunities.append(result)

        return sorted(opportunities, key=lambda x: x.signal_strength, reverse=True)[:20]

    def scan_breakout_stocks(self) -> List[StockOpportunity]:
        """Find Indian stocks breaking out of trading ranges."""
        opportunities = []

        def check_stock(symbol):
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="3mo")

                if len(hist) < 20:
                    return None

                price = hist['Close'].iloc[-1]
                high_20d = hist['High'].iloc[-20:].max()
                low_20d = hist['Low'].iloc[-20:].min()
                volume = int(hist['Volume'].iloc[-1])
                avg_volume = int(hist['Volume'].iloc[-20:].mean())

                # Check for breakout above 20-day high
                if price < high_20d * 0.98:  # Not a breakout
                    return None

                # Volume confirmation
                vol_ratio = volume / avg_volume if avg_volume else 1
                if vol_ratio < 1.2:  # Need volume confirmation
                    return None

                # Calculate signal strength
                range_pct = ((high_20d - low_20d) / low_20d * 100) if low_20d else 0
                signal = 50 + min(30, vol_ratio * 10) + min(20, range_pct)

                reason = f"Breaking 20d high Rs {high_20d:.2f}, Vol {vol_ratio:.1f}x avg"

                return StockOpportunity(
                    symbol=symbol.replace('.NS', ''),
                    name=info.get('shortName', symbol),
                    current_price=price,
                    change_percent=((price - low_20d) / low_20d * 100) if low_20d else 0,
                    volume=volume,
                    market_cap=info.get('marketCap'),
                    signal_type="breakout",
                    signal_strength=min(100, signal),
                    reason=reason,
                    sector=info.get('sector', 'Unknown'),
                    last_updated=datetime.now()
                )
            except Exception as e:
                return None

        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_stock, sym): sym for sym in self.POPULAR_TICKERS}
            for future in as_completed(futures):
                result = future.result()
                if result:
                    opportunities.append(result)

        return sorted(opportunities, key=lambda x: x.signal_strength, reverse=True)[:15]

    def get_top_gainers_losers(self) -> Dict[str, List[Dict]]:
        """Get today's top gainers and losers from major indices."""
        try:
            # S&P 500 components (sample)
            sp500_sample = self.POPULAR_TICKERS

            gainers = []
            losers = []

            def check_stock(symbol):
                try:
                    ticker = yf.Ticker(symbol)
                    info = ticker.info
                    return {
                        "symbol": symbol,
                        "name": info.get('shortName', symbol),
                        "price": info.get('currentPrice', 0),
                        "change_percent": info.get('regularMarketChangePercent', 0),
                        "volume": info.get('volume', 0),
                    }
                except:
                    return None

            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = {executor.submit(check_stock, sym): sym for sym in sp500_sample}
                results = []
                for future in as_completed(futures):
                    result = future.result()
                    if result and result['change_percent']:
                        results.append(result)

            # Sort and split
            results.sort(key=lambda x: x['change_percent'], reverse=True)
            gainers = results[:10]
            losers = results[-10:][::-1]

            return {"gainers": gainers, "losers": losers}

        except Exception as e:
            print(f"Error getting gainers/losers: {e}")
            return {"gainers": [], "losers": []}

    def full_scan(self) -> Dict[str, List[StockOpportunity]]:
        """Run full market scan for all opportunity types."""
        return {
            "penny_stocks": self.scan_penny_stocks(),
            "dip_buys": self.scan_dip_opportunities(),
            "momentum": self.scan_momentum_stocks(),
            "breakouts": self.scan_breakout_stocks(),
        }
