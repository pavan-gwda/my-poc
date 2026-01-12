"""Price tracker for Indian stocks, gold, silver."""

import yfinance as yf
import requests
from bs4 import BeautifulSoup
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import threading
import re


@dataclass
class AssetPrice:
    """Asset price data."""
    symbol: str
    name: str
    current_price: float
    change: float
    change_percent: float
    day_high: float
    day_low: float
    volume: int
    market_cap: Optional[float]
    week_52_high: float
    week_52_low: float
    last_updated: datetime


@dataclass
class MetalPrice:
    """Precious metal price data."""
    name: str
    symbol: str
    price_inr: float  # Price in INR (per 10g for gold, per kg for silver)
    price_per_gram: float  # Price per gram in INR
    change: float
    change_percent: float
    day_high: float
    day_low: float
    last_updated: datetime


@dataclass
class CityMetalPrice:
    """City-wise precious metal price."""
    city: str
    metal: str  # Gold or Silver
    price_22k: float  # Per gram for gold
    price_24k: float  # Per gram for gold
    price_per_gram: float  # For silver
    price_per_kg: float  # For silver
    last_updated: datetime


@dataclass
class FDRate:
    """Fixed Deposit rate data."""
    bank_name: str
    tenure: str
    general_rate: float
    senior_rate: float
    last_updated: datetime


class PriceTracker:
    """Tracks prices for Indian stocks and precious metals."""

    # Indian Market Indices
    NIFTY_50 = "^NSEI"  # NIFTY 50
    SENSEX = "^BSESN"  # BSE SENSEX
    NIFTY_BANK = "^NSEBANK"  # NIFTY Bank
    NIFTY_IT = "^CNXIT"  # NIFTY IT
    INDIA_VIX = "^INDIAVIX"  # India VIX

    # Headers for web requests
    HEADERS = {
        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
    }

    def __init__(self):
        self._cache: Dict[str, AssetPrice] = {}
        self._cache_time: Dict[str, datetime] = {}
        self._cache_ttl = timedelta(seconds=30)
        self._lock = threading.Lock()

    def get_stock_price(self, symbol: str) -> Optional[AssetPrice]:
        """Get current stock price."""
        try:
            with self._lock:
                # Check cache
                if symbol in self._cache:
                    if datetime.now() - self._cache_time[symbol] < self._cache_ttl:
                        return self._cache[symbol]

            ticker = yf.Ticker(symbol)
            info = ticker.info
            hist = ticker.history(period="1d")

            if hist.empty:
                return None

            current = hist['Close'].iloc[-1]
            prev_close = info.get('previousClose', current)
            change = current - prev_close
            change_pct = (change / prev_close * 100) if prev_close else 0

            asset = AssetPrice(
                symbol=symbol,
                name=info.get('shortName', symbol),
                current_price=current,
                change=change,
                change_percent=change_pct,
                day_high=info.get('dayHigh', hist['High'].iloc[-1]),
                day_low=info.get('dayLow', hist['Low'].iloc[-1]),
                volume=int(info.get('volume', hist['Volume'].iloc[-1])),
                market_cap=info.get('marketCap'),
                week_52_high=info.get('fiftyTwoWeekHigh', 0),
                week_52_low=info.get('fiftyTwoWeekLow', 0),
                last_updated=datetime.now()
            )

            with self._lock:
                self._cache[symbol] = asset
                self._cache_time[symbol] = datetime.now()

            return asset

        except Exception as e:
            print(f"Error fetching {symbol}: {e}")
            return None

    def get_gold_price(self) -> Optional[MetalPrice]:
        """Get current gold price in INR from Indian sources (per 10 grams, 24K)."""
        try:
            # Fetch from GoodReturns - reliable Indian gold prices
            url = "https://www.goodreturns.in/gold-rates/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find prices in gold per gram range (Rs 10,000-15,000)
                # 24K is highest, 22K is middle, 18K is lowest
                prices = []
                for elem in soup.find_all(string=re.compile(r'₹[\d,]+')):
                    match = re.search(r'₹([\d,]+)', elem)
                    if match:
                        price = float(match.group(1).replace(',', ''))
                        if 12000 < price < 15000:  # 24K gold per gram range
                            prices.append(price)

                if prices:
                    # Take the most common price (24K appears multiple times)
                    from collections import Counter
                    price_per_gram = Counter(prices).most_common(1)[0][0]
                    price_inr = price_per_gram * 10  # Per 10g

                    return MetalPrice(
                        name="Gold",
                        symbol="24K",
                        price_inr=price_inr,
                        price_per_gram=price_per_gram,
                        change=0,
                        change_percent=0,
                        day_high=price_inr,
                        day_low=price_inr,
                        last_updated=datetime.now()
                    )

        except Exception as e:
            print(f"Error fetching gold price: {e}")

        return None

    def get_silver_price(self) -> Optional[MetalPrice]:
        """Get current silver price in INR from Indian sources (per kg)."""
        try:
            # Fetch from GoodReturns
            url = "https://www.goodreturns.in/silver-rates/"
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            }
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Look for silver price per kg (format: ₹ X,XX,XXX/kg)
                for elem in soup.find_all(string=re.compile(r'₹\s*[\d,]+/kg')):
                    match = re.search(r'₹\s*([\d,]+)/kg', elem)
                    if match:
                        price_per_kg = float(match.group(1).replace(',', ''))
                        if 50000 < price_per_kg < 500000:  # Valid silver per kg range
                            price_per_gram = price_per_kg / 1000

                            return MetalPrice(
                                name="Silver",
                                symbol="999",
                                price_inr=price_per_kg,
                                price_per_gram=price_per_gram,
                                change=0,
                                change_percent=0,
                                day_high=price_per_kg,
                                day_low=price_per_kg,
                                last_updated=datetime.now()
                            )

        except Exception as e:
            print(f"Error fetching silver price: {e}")

        return None

    def get_multiple_prices(self, symbols: List[str]) -> Dict[str, AssetPrice]:
        """Get prices for multiple symbols efficiently."""
        results = {}

        # Use yfinance download for batch fetching
        try:
            data = yf.download(symbols, period="1d", group_by='ticker', progress=False, auto_adjust=True)

            for symbol in symbols:
                try:
                    if len(symbols) == 1:
                        ticker_data = data
                    else:
                        ticker_data = data[symbol]

                    if ticker_data.empty:
                        continue

                    ticker = yf.Ticker(symbol)
                    info = ticker.info

                    current = ticker_data['Close'].iloc[-1]
                    prev_close = info.get('previousClose', current)
                    change = current - prev_close
                    change_pct = (change / prev_close * 100) if prev_close else 0

                    results[symbol] = AssetPrice(
                        symbol=symbol,
                        name=info.get('shortName', symbol),
                        current_price=current,
                        change=change,
                        change_percent=change_pct,
                        day_high=ticker_data['High'].iloc[-1],
                        day_low=ticker_data['Low'].iloc[-1],
                        volume=int(ticker_data['Volume'].iloc[-1]),
                        market_cap=info.get('marketCap'),
                        week_52_high=info.get('fiftyTwoWeekHigh', 0),
                        week_52_low=info.get('fiftyTwoWeekLow', 0),
                        last_updated=datetime.now()
                    )
                except Exception as e:
                    print(f"Error processing {symbol}: {e}")
                    continue

        except Exception as e:
            print(f"Error batch fetching: {e}")

        return results

    def get_market_indices(self) -> Dict[str, AssetPrice]:
        """Get major Indian market indices."""
        indices = [
            self.NIFTY_50,      # NIFTY 50
            self.SENSEX,        # BSE SENSEX
            self.NIFTY_BANK,    # NIFTY Bank
            self.INDIA_VIX,     # India VIX
        ]
        return self.get_multiple_prices(indices)

    def get_stock_fundamentals(self, symbol: str) -> Optional[Dict]:
        """Get stock fundamentals for analysis."""
        try:
            ticker = yf.Ticker(symbol)
            info = ticker.info

            return {
                "symbol": symbol,
                "name": info.get('shortName'),
                "sector": info.get('sector'),
                "industry": info.get('industry'),
                "market_cap": info.get('marketCap'),
                "pe_ratio": info.get('trailingPE'),
                "forward_pe": info.get('forwardPE'),
                "peg_ratio": info.get('pegRatio'),
                "price_to_book": info.get('priceToBook'),
                "debt_to_equity": info.get('debtToEquity'),
                "revenue_growth": info.get('revenueGrowth'),
                "earnings_growth": info.get('earningsGrowth'),
                "profit_margin": info.get('profitMargins'),
                "analyst_rating": info.get('recommendationMean'),
                "target_price": info.get('targetMeanPrice'),
                "dividend_yield": info.get('dividendYield'),
                "beta": info.get('beta'),
                "52w_high": info.get('fiftyTwoWeekHigh'),
                "52w_low": info.get('fiftyTwoWeekLow'),
            }
        except Exception as e:
            print(f"Error getting fundamentals for {symbol}: {e}")
            return None

    def get_price_history(self, symbol: str, period: str = "1mo") -> Optional[Dict]:
        """Get historical price data."""
        try:
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=period)

            if hist.empty:
                return None

            return {
                "dates": hist.index.tolist(),
                "open": hist['Open'].tolist(),
                "high": hist['High'].tolist(),
                "low": hist['Low'].tolist(),
                "close": hist['Close'].tolist(),
                "volume": hist['Volume'].tolist(),
            }
        except Exception as e:
            print(f"Error getting history for {symbol}: {e}")
            return None

    # Major Indian cities for gold/silver prices
    CITIES = ['delhi', 'mumbai', 'chennai', 'bangalore', 'hyderabad']
    CITY_DISPLAY_NAMES = {
        'delhi': 'Delhi',
        'mumbai': 'Mumbai',
        'chennai': 'Chennai',
        'bangalore': 'Bangalore',
        'hyderabad': 'Hyderabad'
    }

    def get_city_gold_prices(self) -> List[CityMetalPrice]:
        """Get gold prices for major Indian cities."""
        results = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        for city in self.CITIES:
            try:
                url = f"https://www.goodreturns.in/gold-rates/{city}.html"
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Find prices - look for 22K and 24K gold per gram
                    prices_22k = []
                    prices_24k = []

                    for elem in soup.find_all(string=re.compile(r'₹[\d,]+')):
                        match = re.search(r'₹([\d,]+)', elem)
                        if match:
                            price = float(match.group(1).replace(',', ''))
                            # 24K: Rs 12,000-15,000/gram, 22K: Rs 11,000-14,000/gram
                            if 12000 < price < 15000:
                                prices_24k.append(price)
                            elif 11000 < price < 13000:
                                prices_22k.append(price)

                    if prices_24k or prices_22k:
                        from collections import Counter
                        price_24k = Counter(prices_24k).most_common(1)[0][0] if prices_24k else 0
                        price_22k = Counter(prices_22k).most_common(1)[0][0] if prices_22k else 0

                        results.append(CityMetalPrice(
                            city=self.CITY_DISPLAY_NAMES.get(city, city.title()),
                            metal="Gold",
                            price_22k=price_22k,
                            price_24k=price_24k,
                            price_per_gram=0,
                            price_per_kg=0,
                            last_updated=datetime.now()
                        ))

            except Exception as e:
                print(f"Error fetching gold price for {city}: {e}")

        return results

    def get_city_silver_prices(self) -> List[CityMetalPrice]:
        """Get silver prices for major Indian cities."""
        results = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        for city in self.CITIES:
            try:
                url = f"https://www.goodreturns.in/silver-rates/{city}.html"
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200:
                    soup = BeautifulSoup(response.text, 'html.parser')

                    # Look for silver price per kg (format: ₹ X,XX,XXX/kg)
                    for elem in soup.find_all(string=re.compile(r'₹\s*[\d,]+/kg')):
                        match = re.search(r'₹\s*([\d,]+)/kg', elem)
                        if match:
                            price_per_kg = float(match.group(1).replace(',', ''))
                            if 50000 < price_per_kg < 500000:
                                price_per_gram = price_per_kg / 1000

                                results.append(CityMetalPrice(
                                    city=self.CITY_DISPLAY_NAMES.get(city, city.title()),
                                    metal="Silver",
                                    price_22k=0,
                                    price_24k=0,
                                    price_per_gram=price_per_gram,
                                    price_per_kg=price_per_kg,
                                    last_updated=datetime.now()
                                ))
                                break

            except Exception as e:
                print(f"Error fetching silver price for {city}: {e}")

        return results

    def get_fd_rates(self) -> List[FDRate]:
        """Get FD rates from major banks."""
        results = []
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        }

        try:
            url = "https://www.goodreturns.in/fixed-deposit-interest-rates.html"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find FD rate tables
                tables = soup.find_all('table')

                # Known bank FD rates (fallback with typical rates)
                bank_rates = {
                    'SBI': {'1 Year': (6.80, 7.30), '2 Years': (7.00, 7.50), '3 Years': (6.75, 7.25)},
                    'HDFC Bank': {'1 Year': (6.60, 7.10), '2 Years': (7.00, 7.50), '3 Years': (7.00, 7.50)},
                    'ICICI Bank': {'1 Year': (6.70, 7.20), '2 Years': (7.00, 7.50), '3 Years': (7.00, 7.50)},
                    'Axis Bank': {'1 Year': (6.70, 7.20), '2 Years': (7.10, 7.60), '3 Years': (7.10, 7.60)},
                    'Kotak Bank': {'1 Year': (6.50, 7.00), '2 Years': (6.75, 7.25), '3 Years': (6.75, 7.25)},
                }

                # Try to extract from tables
                for table in tables:
                    rows = table.find_all('tr')
                    for row in rows:
                        cells = row.find_all(['td', 'th'])
                        if len(cells) >= 3:
                            text = ' '.join(c.get_text(strip=True) for c in cells)
                            # Look for bank names and rates
                            for bank in bank_rates.keys():
                                if bank.lower() in text.lower():
                                    # Try to extract rates
                                    rate_matches = re.findall(r'(\d+\.?\d*)%', text)
                                    if len(rate_matches) >= 2:
                                        gen_rate = float(rate_matches[0])
                                        sen_rate = float(rate_matches[1])
                                        if 5 < gen_rate < 10 and 5 < sen_rate < 10:
                                            results.append(FDRate(
                                                bank_name=bank,
                                                tenure="1 Year",
                                                general_rate=gen_rate,
                                                senior_rate=sen_rate,
                                                last_updated=datetime.now()
                                            ))

                # If scraping didn't work well, use fallback data
                if len(results) < 3:
                    results = []
                    for bank, tenures in bank_rates.items():
                        for tenure, (gen, sen) in tenures.items():
                            results.append(FDRate(
                                bank_name=bank,
                                tenure=tenure,
                                general_rate=gen,
                                senior_rate=sen,
                                last_updated=datetime.now()
                            ))

        except Exception as e:
            print(f"Error fetching FD rates: {e}")
            # Return fallback data on error
            bank_rates = {
                'SBI': (6.80, 7.30),
                'HDFC Bank': (6.60, 7.10),
                'ICICI Bank': (6.70, 7.20),
                'Axis Bank': (6.70, 7.20),
                'Kotak Bank': (6.50, 7.00),
            }
            for bank, (gen, sen) in bank_rates.items():
                results.append(FDRate(
                    bank_name=bank,
                    tenure="1 Year",
                    general_rate=gen,
                    senior_rate=sen,
                    last_updated=datetime.now()
                ))

        return results
