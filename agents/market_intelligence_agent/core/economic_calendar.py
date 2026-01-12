"""Economic calendar for Indian market-moving events."""

import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta
import json


@dataclass
class EconomicEvent:
    """Economic event data."""
    name: str
    date: datetime
    time: str
    country: str
    importance: str  # "high", "medium", "low"
    previous: str
    forecast: str
    actual: str
    impact: str  # "bullish", "bearish", "neutral", "pending"
    description: str


class EconomicCalendar:
    """Tracks economic events that affect Indian markets."""

    # Major Indian market-moving events
    HIGH_IMPACT_EVENTS = [
        "RBI Interest Rate Decision",
        "RBI Monetary Policy Statement",
        "RBI MPC Meeting",
        "India CPI",
        "India WPI",
        "India GDP",
        "India IIP",
        "India Trade Balance",
        "India PMI Manufacturing",
        "India PMI Services",
        "India Forex Reserves",
        "India Current Account",
        "GST Collections",
        "FII/FPI Data",
        "Auto Sales Data",
    ]

    # RBI MPC Meeting dates for 2024
    RBI_MEETINGS_2024 = [
        datetime(2024, 2, 8),
        datetime(2024, 4, 5),
        datetime(2024, 6, 7),
        datetime(2024, 8, 8),
        datetime(2024, 10, 9),
        datetime(2024, 12, 6),
    ]

    # RBI MPC Meeting dates for 2025
    RBI_MEETINGS_2025 = [
        datetime(2025, 2, 7),
        datetime(2025, 4, 9),
        datetime(2025, 6, 6),
        datetime(2025, 8, 8),
        datetime(2025, 10, 8),
        datetime(2025, 12, 5),
    ]

    def __init__(self):
        self._cache = None
        self._cache_time = None
        self._cache_ttl = timedelta(hours=1)

    def get_upcoming_events(self, days: int = 7) -> List[EconomicEvent]:
        """Get economic events for the next N days."""
        events = []

        # Add RBI meetings
        events.extend(self._get_rbi_meetings(days))

        # Try to fetch from investing.com calendar (filtered for India)
        try:
            events.extend(self._fetch_investing_calendar(days))
        except Exception as e:
            print(f"Error fetching investing.com calendar: {e}")

        # Sort by date
        events.sort(key=lambda x: x.date)

        return events

    def _get_rbi_meetings(self, days: int) -> List[EconomicEvent]:
        """Get upcoming RBI MPC meetings."""
        events = []
        now = datetime.now()
        end_date = now + timedelta(days=days)

        all_meetings = self.RBI_MEETINGS_2024 + self.RBI_MEETINGS_2025

        for meeting_date in all_meetings:
            if now <= meeting_date <= end_date:
                days_until = (meeting_date - now).days

                events.append(EconomicEvent(
                    name="RBI MPC Interest Rate Decision",
                    date=meeting_date,
                    time="10:00 IST",
                    country="India",
                    importance="high",
                    previous="",
                    forecast="",
                    actual="",
                    impact="pending",
                    description=f"RBI Monetary Policy Committee interest rate decision. {days_until} days away."
                ))

        return events

    def _fetch_investing_calendar(self, days: int) -> List[EconomicEvent]:
        """Fetch economic calendar from investing.com."""
        events = []

        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36',
                'X-Requested-With': 'XMLHttpRequest',
            }

            # Investing.com economic calendar
            url = "https://www.investing.com/economic-calendar/"
            response = requests.get(url, headers=headers, timeout=10)

            if response.status_code == 200:
                soup = BeautifulSoup(response.text, 'html.parser')

                # Find event rows
                rows = soup.find_all('tr', class_='js-event-item')

                for row in rows[:50]:  # Limit to 50 events
                    try:
                        # Extract data
                        event_name = row.find('td', class_='event')
                        if event_name:
                            event_name = event_name.get_text(strip=True)
                        else:
                            continue

                        # Check importance
                        importance = "low"
                        bulls = row.find_all('i', class_='grayFullBullishIcon')
                        if len(bulls) >= 3:
                            importance = "high"
                        elif len(bulls) >= 2:
                            importance = "medium"

                        # Skip low importance
                        if importance == "low":
                            continue

                        # Get date/time
                        time_cell = row.find('td', class_='time')
                        time_str = time_cell.get_text(strip=True) if time_cell else ""

                        # Get country
                        country_span = row.find('span', class_='ceFlags')
                        country = country_span.get('title', 'Unknown') if country_span else "Unknown"

                        # Get values
                        actual = row.find('td', class_='act')
                        actual = actual.get_text(strip=True) if actual else ""

                        forecast = row.find('td', class_='fore')
                        forecast = forecast.get_text(strip=True) if forecast else ""

                        previous = row.find('td', class_='prev')
                        previous = previous.get_text(strip=True) if previous else ""

                        # Determine impact
                        impact = "pending"
                        if actual and forecast:
                            try:
                                actual_val = float(actual.replace('%', '').replace(',', ''))
                                forecast_val = float(forecast.replace('%', '').replace(',', ''))
                                if actual_val > forecast_val:
                                    impact = "bullish"
                                elif actual_val < forecast_val:
                                    impact = "bearish"
                                else:
                                    impact = "neutral"
                            except:
                                pass

                        events.append(EconomicEvent(
                            name=event_name,
                            date=datetime.now(),  # Simplified - would need proper date parsing
                            time=time_str,
                            country=country,
                            importance=importance,
                            previous=previous,
                            forecast=forecast,
                            actual=actual,
                            impact=impact,
                            description=""
                        ))

                    except Exception as e:
                        continue

        except Exception as e:
            print(f"Error fetching calendar: {e}")

        return events

    def get_todays_events(self) -> List[EconomicEvent]:
        """Get economic events for today."""
        return self.get_upcoming_events(days=1)

    def get_high_impact_events(self, days: int = 14) -> List[EconomicEvent]:
        """Get only high impact events."""
        events = self.get_upcoming_events(days)
        return [e for e in events if e.importance == "high"]

    def get_fed_calendar(self) -> List[Dict]:
        """Get all RBI MPC meeting dates with analysis (alias for backward compatibility)."""
        return self.get_rbi_calendar()

    def get_rbi_calendar(self) -> List[Dict]:
        """Get all RBI MPC meeting dates with analysis."""
        now = datetime.now()
        rbi_events = []

        all_meetings = self.RBI_MEETINGS_2024 + self.RBI_MEETINGS_2025

        for meeting_date in all_meetings:
            if meeting_date >= now:
                days_until = (meeting_date - now).days

                status = "upcoming"
                if days_until == 0:
                    status = "today"
                elif days_until <= 7:
                    status = "this_week"
                elif days_until <= 30:
                    status = "this_month"

                rbi_events.append({
                    "date": meeting_date.strftime("%Y-%m-%d"),
                    "day": meeting_date.strftime("%A"),
                    "days_until": days_until,
                    "status": status,
                    "description": "RBI MPC Interest Rate Decision",
                    "expected_time": "10:00 AM IST"
                })

        return rbi_events[:6]  # Next 6 meetings

    def get_earnings_calendar(self, symbols: List[str] = None) -> List[Dict]:
        """Get earnings dates for watched stocks."""
        import yfinance as yf

        earnings = []

        if not symbols:
            symbols = ["AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA"]

        for symbol in symbols:
            try:
                ticker = yf.Ticker(symbol)
                info = ticker.info

                next_earnings = info.get('earningsDate')
                if next_earnings:
                    earnings.append({
                        "symbol": symbol,
                        "name": info.get('shortName', symbol),
                        "earnings_date": str(next_earnings),
                        "eps_estimate": info.get('epsForward'),
                        "revenue_estimate": info.get('revenueForward'),
                    })
            except:
                continue

        return earnings

    def get_market_hours_status(self) -> Dict:
        """Get current Indian market hours status (NSE/BSE)."""
        now = datetime.now()
        weekday = now.weekday()
        hour = now.hour
        minute = now.minute
        current_time = hour * 60 + minute  # Minutes since midnight

        # Indian market times in IST (minutes since midnight)
        PRE_MARKET_START = 9 * 60  # 9:00 AM IST
        MARKET_OPEN = 9 * 60 + 15  # 9:15 AM IST
        MARKET_CLOSE = 15 * 60 + 30  # 3:30 PM IST
        POST_MARKET_END = 16 * 60  # 4:00 PM IST

        status = "closed"
        next_event = ""
        time_until = ""

        if weekday >= 5:  # Weekend
            status = "closed"
            days_until_monday = (7 - weekday) % 7 or 7
            next_event = "Market opens Monday"
            time_until = f"{days_until_monday} days"
        elif current_time < PRE_MARKET_START:
            status = "closed"
            next_event = "Pre-market opens"
            mins = PRE_MARKET_START - current_time
            time_until = f"{mins // 60}h {mins % 60}m"
        elif current_time < MARKET_OPEN:
            status = "pre_market"
            next_event = "Market opens"
            mins = MARKET_OPEN - current_time
            time_until = f"{mins // 60}h {mins % 60}m"
        elif current_time < MARKET_CLOSE:
            status = "open"
            next_event = "Market closes"
            mins = MARKET_CLOSE - current_time
            time_until = f"{mins // 60}h {mins % 60}m"
        elif current_time < POST_MARKET_END:
            status = "post_market"
            next_event = "Post-market ends"
            mins = POST_MARKET_END - current_time
            time_until = f"{mins // 60}h {mins % 60}m"
        else:
            status = "closed"
            next_event = "Market opens tomorrow"
            time_until = "~17 hours"

        return {
            "status": status,
            "next_event": next_event,
            "time_until": time_until,
            "current_time": now.strftime("%H:%M IST"),
            "is_trading": status == "open",
            "is_extended_hours": status in ("pre_market", "post_market"),
        }

    def get_week_preview(self) -> Dict:
        """Get preview of the week's important events."""
        events = self.get_upcoming_events(days=7)
        high_impact = [e for e in events if e.importance == "high"]

        return {
            "total_events": len(events),
            "high_impact_count": len(high_impact),
            "high_impact_events": [
                {
                    "name": e.name,
                    "date": e.date.strftime("%Y-%m-%d") if isinstance(e.date, datetime) else str(e.date),
                    "time": e.time,
                    "country": e.country,
                }
                for e in high_impact
            ],
            "market_status": self.get_market_hours_status(),
        }
