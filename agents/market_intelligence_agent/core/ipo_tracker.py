"""IPO tracker for upcoming and recent IPOs."""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import yfinance as yf


@dataclass
class IPO:
    """IPO data."""
    company: str
    symbol: str
    exchange: str
    price_range: str
    shares_offered: str
    expected_date: str
    status: str  # "upcoming", "priced", "trading"
    current_price: Optional[float]
    change_from_ipo: Optional[float]
    sector: str
    lead_underwriter: str


class IPOTracker:
    """Tracks upcoming and recent IPOs."""

    def __init__(self):
        self._cache = {}
        self._cache_time = None
        self._cache_ttl = timedelta(hours=1)

    def get_upcoming_ipos(self) -> List[IPO]:
        """Get upcoming IPOs from various sources."""
        ipos = []

        # Try to fetch from Nasdaq IPO calendar
        try:
            ipos.extend(self._fetch_nasdaq_ipos())
        except Exception as e:
            print(f"Error fetching Nasdaq IPOs: {e}")

        # Try to fetch from MarketWatch
        try:
            ipos.extend(self._fetch_marketwatch_ipos())
        except Exception as e:
            print(f"Error fetching MarketWatch IPOs: {e}")

        # Remove duplicates by symbol
        seen = set()
        unique_ipos = []
        for ipo in ipos:
            if ipo.symbol not in seen:
                seen.add(ipo.symbol)
                unique_ipos.append(ipo)

        return unique_ipos

    def _fetch_nasdaq_ipos(self) -> List[IPO]:
        """Fetch IPOs from Nasdaq calendar."""
        ipos = []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            # Upcoming IPOs
            url = "https://api.nasdaq.com/api/ipo/calendar"
            params = {"date": datetime.now().strftime("%Y-%m")}

            response = requests.get(url, headers=headers, params=params, timeout=10)

            if response.status_code == 200:
                data = response.json()

                if data.get('data', {}).get('upcoming', {}).get('upcomingTable', {}).get('rows'):
                    for row in data['data']['upcoming']['upcomingTable']['rows']:
                        ipos.append(IPO(
                            company=row.get('companyName', ''),
                            symbol=row.get('proposedTickerSymbol', ''),
                            exchange=row.get('proposedExchange', 'NASDAQ'),
                            price_range=row.get('proposedSharePrice', 'TBD'),
                            shares_offered=row.get('sharesOffered', ''),
                            expected_date=row.get('expectedPriceDate', 'TBD'),
                            status="upcoming",
                            current_price=None,
                            change_from_ipo=None,
                            sector=row.get('dollarValueOfSharesOffered', ''),
                            lead_underwriter=row.get('leadUnderwriters', '')
                        ))

                # Recent/Priced IPOs
                if data.get('data', {}).get('priced', {}).get('pricedTable', {}).get('rows'):
                    for row in data['data']['priced']['pricedTable']['rows']:
                        symbol = row.get('proposedTickerSymbol', '')
                        current_price = None
                        change = None

                        # Try to get current price
                        if symbol:
                            try:
                                ticker = yf.Ticker(symbol)
                                hist = ticker.history(period="1d")
                                if not hist.empty:
                                    current_price = hist['Close'].iloc[-1]
                                    ipo_price_str = row.get('pricedDate', '').split('$')[-1] if '$' in str(row.get('pricedDate', '')) else None
                                    if ipo_price_str:
                                        try:
                                            ipo_price = float(ipo_price_str.replace(',', ''))
                                            change = ((current_price - ipo_price) / ipo_price * 100)
                                        except:
                                            pass
                            except:
                                pass

                        ipos.append(IPO(
                            company=row.get('companyName', ''),
                            symbol=symbol,
                            exchange=row.get('proposedExchange', 'NASDAQ'),
                            price_range=row.get('proposedSharePrice', ''),
                            shares_offered=row.get('sharesOffered', ''),
                            expected_date=row.get('pricedDate', ''),
                            status="priced",
                            current_price=current_price,
                            change_from_ipo=change,
                            sector='',
                            lead_underwriter=row.get('leadUnderwriters', '')
                        ))

        except Exception as e:
            print(f"Nasdaq API error: {e}")

        return ipos

    def _fetch_marketwatch_ipos(self) -> List[IPO]:
        """Fetch IPOs from MarketWatch."""
        ipos = []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
            }

            url = "https://www.marketwatch.com/tools/ipo-calendar"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find IPO tables
                tables = soup.find_all('table', class_='table')

                for table in tables[:2]:  # First 2 tables usually have upcoming/recent
                    rows = table.find_all('tr')[1:]  # Skip header

                    for row in rows[:10]:  # Limit to 10 per table
                        cols = row.find_all('td')
                        if len(cols) >= 4:
                            company = cols[0].get_text(strip=True)
                            symbol = cols[1].get_text(strip=True) if len(cols) > 1 else ''
                            price = cols[2].get_text(strip=True) if len(cols) > 2 else ''
                            date = cols[3].get_text(strip=True) if len(cols) > 3 else ''

                            if company and symbol:
                                ipos.append(IPO(
                                    company=company,
                                    symbol=symbol,
                                    exchange="",
                                    price_range=price,
                                    shares_offered="",
                                    expected_date=date,
                                    status="upcoming",
                                    current_price=None,
                                    change_from_ipo=None,
                                    sector="",
                                    lead_underwriter=""
                                ))

        except Exception as e:
            print(f"MarketWatch error: {e}")

        return ipos

    def get_recent_ipo_performance(self, days: int = 30) -> List[Dict]:
        """Get performance of IPOs from the last N days."""
        performances = []

        # Get recently IPO'd stocks (simplified approach)
        recent_ipos = [
            # Add known recent IPOs here, or fetch from API
        ]

        for symbol in recent_ipos:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info
                hist = ticker.history(period="1mo")

                if hist.empty:
                    continue

                ipo_price = hist['Open'].iloc[0]
                current_price = hist['Close'].iloc[-1]
                change = ((current_price - ipo_price) / ipo_price * 100)

                performances.append({
                    "symbol": symbol,
                    "name": info.get('shortName', symbol),
                    "ipo_price": ipo_price,
                    "current_price": current_price,
                    "change_percent": change,
                    "volume": info.get('volume', 0),
                    "market_cap": info.get('marketCap', 0),
                })
            except Exception as e:
                continue

        return sorted(performances, key=lambda x: x['change_percent'], reverse=True)

    def analyze_ipo_potential(self, symbol: str) -> Optional[Dict]:
        """Analyze an IPO stock's potential."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="3mo")

            if hist.empty:
                return None

            current_price = hist['Close'].iloc[-1]
            ipo_price = hist['Open'].iloc[0]
            volume = int(hist['Volume'].iloc[-1])
            avg_volume = int(hist['Volume'].mean())

            # Calculate metrics
            change_from_ipo = ((current_price - ipo_price) / ipo_price * 100)
            volatility = hist['Close'].std() / hist['Close'].mean() * 100

            # Determine signal
            signal = "neutral"
            if change_from_ipo > 20 and volume > avg_volume:
                signal = "strong_buy"
            elif change_from_ipo > 0 and volume > avg_volume * 0.8:
                signal = "buy"
            elif change_from_ipo < -20:
                signal = "risky"

            return {
                "symbol": symbol,
                "name": info.get('shortName', symbol),
                "sector": info.get('sector', ''),
                "ipo_price": ipo_price,
                "current_price": current_price,
                "change_from_ipo": change_from_ipo,
                "day_high": hist['High'].iloc[-1],
                "day_low": hist['Low'].iloc[-1],
                "volume": volume,
                "avg_volume": avg_volume,
                "volatility": volatility,
                "market_cap": info.get('marketCap'),
                "signal": signal,
                "pe_ratio": info.get('trailingPE'),
                "analyst_rating": info.get('recommendationMean'),
            }

        except Exception as e:
            print(f"Error analyzing {symbol}: {e}")
            return None

    def get_hot_ipos(self) -> List[Dict]:
        """Get IPOs that are showing strong performance."""
        # Manually curated list of recent IPOs to track
        recent_symbols = ["ARM", "CART", "KVYO", "BIRK", "VIK"]  # Add more as they IPO

        hot = []
        for symbol in recent_symbols:
            analysis = self.analyze_ipo_potential(symbol)
            if analysis and analysis.get('change_from_ipo', 0) > 10:
                hot.append(analysis)

        return sorted(hot, key=lambda x: x.get('change_from_ipo', 0), reverse=True)
