"""Main dashboard UI for Market Intelligence Agent."""

import sys
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTabWidget, QTableWidget, QTableWidgetItem,
    QGroupBox, QScrollArea, QFrame, QHeaderView, QSplitter,
    QProgressBar, QTextEdit
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread
from PyQt6.QtGui import QFont, QColor
from typing import Dict, List, Optional
from datetime import datetime
import threading


class DataFetchWorker(QThread):
    """Background worker for fetching data."""
    data_ready = pyqtSignal(dict)
    error = pyqtSignal(str)

    def __init__(self, fetch_func, name: str):
        super().__init__()
        self.fetch_func = fetch_func
        self.name = name

    def run(self):
        try:
            result = self.fetch_func()
            self.data_ready.emit({"name": self.name, "data": result})
        except Exception as e:
            self.error.emit(f"{self.name}: {str(e)}")


class PriceCard(QFrame):
    """Card widget for displaying asset price."""

    def __init__(self, title: str, currency: str = "₹", parent=None):
        super().__init__(parent)
        self.title = title
        self.currency = currency
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)

        # Title
        self.title_label = QLabel(self.title)
        self.title_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(self.title_label)

        # Price
        self.price_label = QLabel("--")
        self.price_label.setStyleSheet("color: #fff; font-size: 24px; font-weight: bold;")
        layout.addWidget(self.price_label)

        # Change
        self.change_label = QLabel("--")
        self.change_label.setStyleSheet("font-size: 14px;")
        layout.addWidget(self.change_label)

    def update_price(self, price: float, change: float, change_pct: float):
        self.price_label.setText(f"{self.currency}{price:,.2f}")

        color = "#4CAF50" if change >= 0 else "#f44336"
        arrow = "▲" if change >= 0 else "▼"
        self.change_label.setText(f"{arrow} {self.currency}{abs(change):.2f} ({change_pct:+.2f}%)")
        self.change_label.setStyleSheet(f"color: {color}; font-size: 14px;")


class SignalCard(QFrame):
    """Card widget for displaying market signal."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self._setup_ui()

    def _setup_ui(self):
        self.setFrameStyle(QFrame.Shape.Box | QFrame.Shadow.Raised)
        self.setStyleSheet("""
            QFrame {
                background-color: #1e1e1e;
                border-radius: 8px;
                padding: 10px;
            }
        """)

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel(self.title)
        title_label.setStyleSheet("color: #888; font-size: 12px;")
        layout.addWidget(title_label)

        # Signal
        self.signal_label = QLabel("--")
        self.signal_label.setStyleSheet("font-size: 18px; font-weight: bold;")
        layout.addWidget(self.signal_label)

        # Confidence
        self.confidence_bar = QProgressBar()
        self.confidence_bar.setMaximum(100)
        self.confidence_bar.setTextVisible(True)
        self.confidence_bar.setFormat("Confidence: %p%")
        self.confidence_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                background-color: #333;
                border-radius: 4px;
                height: 20px;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        layout.addWidget(self.confidence_bar)

        # Reasons
        self.reasons_label = QLabel("")
        self.reasons_label.setStyleSheet("color: #aaa; font-size: 11px;")
        self.reasons_label.setWordWrap(True)
        layout.addWidget(self.reasons_label)

    def update_signal(self, signal: str, confidence: float, reasons: List[str]):
        signal_colors = {
            "strong_buy": ("#4CAF50", "STRONG BUY"),
            "buy": ("#8BC34A", "BUY"),
            "hold": ("#FFC107", "HOLD"),
            "sell": ("#FF9800", "SELL"),
            "strong_sell": ("#f44336", "STRONG SELL"),
        }

        color, text = signal_colors.get(signal, ("#888", signal.upper()))
        self.signal_label.setText(text)
        self.signal_label.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")

        self.confidence_bar.setValue(int(confidence))

        reasons_text = " • ".join(reasons[:3]) if reasons else "No signals"
        self.reasons_label.setText(reasons_text)


class MarketDashboard(QMainWindow):
    """Main dashboard window."""

    # Signals for thread-safe UI updates
    update_status = pyqtSignal(str)
    update_last_refresh = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Market Intelligence Agent")
        self.setMinimumSize(1400, 900)

        # Initialize data modules (lazy loading)
        self.price_tracker = None
        self.signal_generator = None
        self.news_aggregator = None
        self.stock_screener = None
        self.economic_calendar = None

        self._setup_ui()
        self._setup_timers()

        # Connect signals
        self.update_status.connect(self._set_status)
        self.update_last_refresh.connect(self._set_last_refresh)

        # Initial data load
        QTimer.singleShot(100, self._initial_load)

    def _set_status(self, text):
        self.status_label.setText(text)

    def _set_last_refresh(self, text):
        self.last_update.setText(text)

    def _setup_ui(self):
        """Setup the main UI."""
        central = QWidget()
        self.setCentralWidget(central)

        main_layout = QVBoxLayout(central)
        main_layout.setSpacing(10)

        # Header
        header = self._create_header()
        main_layout.addWidget(header)

        # Main content with tabs
        tabs = QTabWidget()
        tabs.setStyleSheet("""
            QTabWidget::pane {
                border: 1px solid #333;
                background-color: #1a1a1a;
            }
            QTabBar::tab {
                background-color: #2d2d2d;
                color: #888;
                padding: 10px 20px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #1a1a1a;
                color: #fff;
            }
        """)

        # Overview tab
        overview_tab = self._create_overview_tab()
        tabs.addTab(overview_tab, "Overview")

        # Stock Screener tab
        screener_tab = self._create_screener_tab()
        tabs.addTab(screener_tab, "Stock Screener")

        # News tab
        news_tab = self._create_news_tab()
        tabs.addTab(news_tab, "News & Sentiment")

        # Calendar tab
        calendar_tab = self._create_calendar_tab()
        tabs.addTab(calendar_tab, "Economic Calendar")

        main_layout.addWidget(tabs)

        # Status bar
        self.status_label = QLabel("Loading...")
        self.status_label.setStyleSheet("color: #888; font-size: 11px; padding: 5px;")
        main_layout.addWidget(self.status_label)

        # Dark theme
        self.setStyleSheet("""
            QMainWindow, QWidget {
                background-color: #121212;
                color: #ffffff;
            }
            QLabel {
                color: #ffffff;
            }
            QGroupBox {
                color: #6bff8a;
                font-weight: bold;
                border: 1px solid #333;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #fff;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
            QTableWidget {
                background-color: #1e1e1e;
                border: none;
                gridline-color: #333;
            }
            QTableWidget::item {
                padding: 8px;
            }
            QHeaderView::section {
                background-color: #2d2d2d;
                color: #fff;
                padding: 8px;
                border: none;
            }
        """)

    def _create_header(self) -> QWidget:
        """Create header with market status and refresh button."""
        header = QWidget()
        layout = QHBoxLayout(header)

        # Market status
        self.market_status = QLabel("Market: --")
        self.market_status.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.market_status)

        layout.addStretch()

        # Last update
        self.last_update = QLabel("Last update: --")
        self.last_update.setStyleSheet("color: #888;")
        layout.addWidget(self.last_update)

        # Refresh button
        refresh_btn = QPushButton("Refresh All")
        refresh_btn.clicked.connect(self._refresh_all)
        layout.addWidget(refresh_btn)

        return header

    def _create_overview_tab(self) -> QWidget:
        """Create overview tab with prices and signals."""
        tab = QWidget()
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("QScrollArea { border: none; }")

        content = QWidget()
        layout = QVBoxLayout(content)

        # Price cards row
        prices_group = QGroupBox("Live Prices")
        prices_layout = QHBoxLayout(prices_group)

        self.gold_card = PriceCard("Gold (per 10g)", "₹")
        prices_layout.addWidget(self.gold_card)

        self.silver_card = PriceCard("Silver (per kg)", "₹")
        prices_layout.addWidget(self.silver_card)

        self.nifty_card = PriceCard("NIFTY 50", "")
        prices_layout.addWidget(self.nifty_card)

        self.sensex_card = PriceCard("SENSEX", "")
        prices_layout.addWidget(self.sensex_card)

        layout.addWidget(prices_group)

        # City-wise Gold & Silver prices row
        city_prices_layout = QHBoxLayout()

        # City Gold Prices
        gold_city_group = QGroupBox("Gold Prices by City (per gram)")
        gold_city_layout = QVBoxLayout(gold_city_group)

        self.city_gold_table = QTableWidget()
        self.city_gold_table.setColumnCount(3)
        self.city_gold_table.setHorizontalHeaderLabels(["City", "22K", "24K"])
        self.city_gold_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.city_gold_table.setMaximumHeight(200)
        gold_city_layout.addWidget(self.city_gold_table)
        city_prices_layout.addWidget(gold_city_group)

        # City Silver Prices
        silver_city_group = QGroupBox("Silver Prices by City")
        silver_city_layout = QVBoxLayout(silver_city_group)

        self.city_silver_table = QTableWidget()
        self.city_silver_table.setColumnCount(3)
        self.city_silver_table.setHorizontalHeaderLabels(["City", "Per Gram", "Per Kg"])
        self.city_silver_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.city_silver_table.setMaximumHeight(200)
        silver_city_layout.addWidget(self.city_silver_table)
        city_prices_layout.addWidget(silver_city_group)

        layout.addLayout(city_prices_layout)

        # Signals and FD Rates row
        signals_fd_layout = QHBoxLayout()

        # Signals
        signals_group = QGroupBox("Market Signals")
        signals_layout = QVBoxLayout(signals_group)
        signals_inner = QHBoxLayout()

        self.gold_signal = SignalCard("Gold Signal")
        signals_inner.addWidget(self.gold_signal)

        self.silver_signal = SignalCard("Silver Signal")
        signals_inner.addWidget(self.silver_signal)

        self.market_signal = SignalCard("Market Signal")
        signals_inner.addWidget(self.market_signal)

        signals_layout.addLayout(signals_inner)
        signals_fd_layout.addWidget(signals_group, stretch=2)

        # FD Rates
        fd_group = QGroupBox("Best FD Rates (1 Year)")
        fd_layout = QVBoxLayout(fd_group)

        self.fd_table = QTableWidget()
        self.fd_table.setColumnCount(3)
        self.fd_table.setHorizontalHeaderLabels(["Bank", "General", "Senior"])
        self.fd_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.fd_table.setMaximumHeight(200)
        fd_layout.addWidget(self.fd_table)
        signals_fd_layout.addWidget(fd_group, stretch=1)

        layout.addLayout(signals_fd_layout)

        # Daily briefing
        briefing_group = QGroupBox("Daily Briefing")
        briefing_layout = QVBoxLayout(briefing_group)

        self.briefing_text = QTextEdit()
        self.briefing_text.setReadOnly(True)
        self.briefing_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                border: none;
                color: #ddd;
                font-size: 13px;
            }
        """)
        self.briefing_text.setPlainText("Loading daily briefing...")
        self.briefing_text.setMaximumHeight(200)
        briefing_layout.addWidget(self.briefing_text)

        layout.addWidget(briefing_group)

        scroll.setWidget(content)

        tab_layout = QVBoxLayout(tab)
        tab_layout.setContentsMargins(0, 0, 0, 0)
        tab_layout.addWidget(scroll)

        return tab

    def _create_screener_tab(self) -> QWidget:
        """Create stock screener tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Scan buttons
        btn_layout = QHBoxLayout()

        penny_btn = QPushButton("Scan Penny Stocks")
        penny_btn.clicked.connect(lambda: self._run_scan("penny"))
        btn_layout.addWidget(penny_btn)

        dip_btn = QPushButton("Find Dip Opportunities")
        dip_btn.clicked.connect(lambda: self._run_scan("dip"))
        btn_layout.addWidget(dip_btn)

        momentum_btn = QPushButton("Momentum Stocks")
        momentum_btn.clicked.connect(lambda: self._run_scan("momentum"))
        btn_layout.addWidget(momentum_btn)

        breakout_btn = QPushButton("Breakout Stocks")
        breakout_btn.clicked.connect(lambda: self._run_scan("breakout"))
        btn_layout.addWidget(breakout_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        # Results table
        self.screener_table = QTableWidget()
        self.screener_table.setColumnCount(7)
        self.screener_table.setHorizontalHeaderLabels([
            "Symbol", "Name", "Price", "Change %", "Volume", "Signal", "Reason"
        ])
        self.screener_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.screener_table.setAlternatingRowColors(True)
        layout.addWidget(self.screener_table)

        return tab

    def _create_news_tab(self) -> QWidget:
        """Create news and sentiment tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # Sentiment summary
        sentiment_group = QGroupBox("Market Sentiment")
        sentiment_layout = QHBoxLayout(sentiment_group)

        self.sentiment_label = QLabel("Overall: --")
        self.sentiment_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        sentiment_layout.addWidget(self.sentiment_label)

        self.bullish_label = QLabel("Bullish: --%")
        self.bullish_label.setStyleSheet("color: #4CAF50;")
        sentiment_layout.addWidget(self.bullish_label)

        self.bearish_label = QLabel("Bearish: --%")
        self.bearish_label.setStyleSheet("color: #f44336;")
        sentiment_layout.addWidget(self.bearish_label)

        sentiment_layout.addStretch()
        layout.addWidget(sentiment_group)

        # News table
        self.news_table = QTableWidget()
        self.news_table.setColumnCount(5)
        self.news_table.setHorizontalHeaderLabels([
            "Time", "Source", "Title", "Sentiment", "Category"
        ])
        self.news_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.news_table.setAlternatingRowColors(True)
        layout.addWidget(self.news_table)

        return tab

    def _create_calendar_tab(self) -> QWidget:
        """Create economic calendar tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        # RBI MPC meetings
        rbi_group = QGroupBox("Upcoming RBI MPC Meetings")
        rbi_layout = QVBoxLayout(rbi_group)

        self.fed_table = QTableWidget()  # Keep variable name for compatibility
        self.fed_table.setColumnCount(4)
        self.fed_table.setHorizontalHeaderLabels(["Date", "Day", "Days Until", "Status"])
        self.fed_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        rbi_layout.addWidget(self.fed_table)

        layout.addWidget(rbi_group)

        # Economic events
        events_group = QGroupBox("Economic Events This Week")
        events_layout = QVBoxLayout(events_group)

        self.events_table = QTableWidget()
        self.events_table.setColumnCount(5)
        self.events_table.setHorizontalHeaderLabels([
            "Event", "Time", "Country", "Importance", "Impact"
        ])
        self.events_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        events_layout.addWidget(self.events_table)

        layout.addWidget(events_group)

        return tab

    def _setup_timers(self):
        """Setup refresh timers."""
        # Price refresh every 60 seconds
        self.price_timer = QTimer()
        self.price_timer.timeout.connect(self._refresh_prices)
        self.price_timer.start(60000)

        # News refresh every 15 minutes
        self.news_timer = QTimer()
        self.news_timer.timeout.connect(self._refresh_news)
        self.news_timer.start(900000)

    def _initial_load(self):
        """Initial data load."""
        self._load_modules()
        self._refresh_all()

    def _load_modules(self):
        """Lazy load data modules."""
        from core import (
            PriceTracker, SignalGenerator, NewsAggregator,
            StockScreener, EconomicCalendar
        )

        self.price_tracker = PriceTracker()
        self.signal_generator = SignalGenerator()
        self.news_aggregator = NewsAggregator()
        self.stock_screener = StockScreener()
        self.economic_calendar = EconomicCalendar()

    def _refresh_all(self):
        """Refresh all data."""
        self.update_status.emit("Refreshing...")
        threading.Thread(target=self._do_refresh_all, daemon=True).start()

    def _do_refresh_all(self):
        """Background refresh."""
        try:
            self._refresh_prices()
        except Exception as e:
            print(f"Error refreshing prices: {e}")

        try:
            self._refresh_signals()
        except Exception as e:
            print(f"Error refreshing signals: {e}")

        try:
            self._refresh_news()
        except Exception as e:
            print(f"Error refreshing news: {e}")

        try:
            self._refresh_calendar()
        except Exception as e:
            print(f"Error refreshing calendar: {e}")

        try:
            self._refresh_briefing()
        except Exception as e:
            print(f"Error refreshing briefing: {e}")

        self.update_last_refresh.emit(f"Last update: {datetime.now().strftime('%H:%M:%S')}")
        self.update_status.emit("Ready")

    def _refresh_prices(self):
        """Refresh price cards."""
        if not self.price_tracker:
            return

        try:
            # Gold (INR per 10 grams)
            gold = self.price_tracker.get_gold_price()
            if gold:
                QTimer.singleShot(0, lambda g=gold: self.gold_card.update_price(g.price_inr, g.change, g.change_percent))

            # Silver (INR per kg)
            silver = self.price_tracker.get_silver_price()
            if silver:
                QTimer.singleShot(0, lambda s=silver: self.silver_card.update_price(s.price_inr, s.change, s.change_percent))

            # Indian Indices
            indices = self.price_tracker.get_market_indices()

            nifty = indices.get("^NSEI")
            if nifty:
                QTimer.singleShot(0, lambda n=nifty: self.nifty_card.update_price(n.current_price, n.change, n.change_percent))

            sensex = indices.get("^BSESN")
            if sensex:
                QTimer.singleShot(0, lambda s=sensex: self.sensex_card.update_price(s.current_price, s.change, s.change_percent))

            # Market status (IST)
            status = self.economic_calendar.get_market_hours_status()
            status_text = status.get("status", "").replace("_", " ").title()
            QTimer.singleShot(0, lambda t=status_text: self.market_status.setText(f"NSE/BSE: {t}"))

            # City-wise Gold prices
            city_gold = self.price_tracker.get_city_gold_prices()
            if city_gold:
                QTimer.singleShot(0, lambda cg=city_gold: self._populate_city_gold_table(cg))

            # City-wise Silver prices
            city_silver = self.price_tracker.get_city_silver_prices()
            if city_silver:
                QTimer.singleShot(0, lambda cs=city_silver: self._populate_city_silver_table(cs))

            # FD Rates
            fd_rates = self.price_tracker.get_fd_rates()
            if fd_rates:
                QTimer.singleShot(0, lambda fd=fd_rates: self._populate_fd_table(fd))

        except Exception as e:
            print(f"Error refreshing prices: {e}")

    def _populate_city_gold_table(self, city_gold):
        """Populate city gold prices table."""
        self.city_gold_table.setRowCount(len(city_gold))
        for i, item in enumerate(city_gold):
            self.city_gold_table.setItem(i, 0, QTableWidgetItem(item.city))
            self.city_gold_table.setItem(i, 1, QTableWidgetItem(f"₹{item.price_22k:,.0f}"))
            self.city_gold_table.setItem(i, 2, QTableWidgetItem(f"₹{item.price_24k:,.0f}"))

    def _populate_city_silver_table(self, city_silver):
        """Populate city silver prices table."""
        self.city_silver_table.setRowCount(len(city_silver))
        for i, item in enumerate(city_silver):
            self.city_silver_table.setItem(i, 0, QTableWidgetItem(item.city))
            self.city_silver_table.setItem(i, 1, QTableWidgetItem(f"₹{item.price_per_gram:,.0f}"))
            self.city_silver_table.setItem(i, 2, QTableWidgetItem(f"₹{item.price_per_kg:,.0f}"))

    def _populate_fd_table(self, fd_rates):
        """Populate FD rates table."""
        # Get unique banks (1 Year tenure only)
        seen_banks = set()
        unique_rates = []
        for fd in fd_rates:
            if fd.tenure == "1 Year" and fd.bank_name not in seen_banks:
                seen_banks.add(fd.bank_name)
                unique_rates.append(fd)

        # Sort by general rate descending
        unique_rates.sort(key=lambda x: x.general_rate, reverse=True)

        self.fd_table.setRowCount(len(unique_rates))
        for i, fd in enumerate(unique_rates):
            self.fd_table.setItem(i, 0, QTableWidgetItem(fd.bank_name))

            gen_item = QTableWidgetItem(f"{fd.general_rate:.2f}%")
            gen_item.setForeground(QColor("#4CAF50"))
            self.fd_table.setItem(i, 1, gen_item)

            sen_item = QTableWidgetItem(f"{fd.senior_rate:.2f}%")
            sen_item.setForeground(QColor("#8BC34A"))
            self.fd_table.setItem(i, 2, sen_item)

    def _refresh_signals(self):
        """Refresh signal cards."""
        if not self.signal_generator:
            return

        try:
            signals = self.signal_generator.generate_all_signals()

            gold_sig = signals.get("gold")
            if gold_sig:
                QTimer.singleShot(0, lambda s=gold_sig: self.gold_signal.update_signal(s.signal, s.confidence, s.reasons))

            silver_sig = signals.get("silver")
            if silver_sig:
                QTimer.singleShot(0, lambda s=silver_sig: self.silver_signal.update_signal(s.signal, s.confidence, s.reasons))

            market_sig = signals.get("market")
            if market_sig:
                QTimer.singleShot(0, lambda s=market_sig: self.market_signal.update_signal(s.signal, s.confidence, s.reasons))

        except Exception as e:
            print(f"Error refreshing signals: {e}")

    def _refresh_news(self):
        """Refresh news and sentiment."""
        if not self.news_aggregator:
            return

        try:
            # Sentiment
            sentiment = self.news_aggregator.get_market_sentiment()
            QTimer.singleShot(0, lambda: self.sentiment_label.setText(f"Overall: {sentiment.get('sentiment', '--').upper()}"))
            QTimer.singleShot(0, lambda: self.bullish_label.setText(f"Bullish: {sentiment.get('bullish_percent', 0):.0f}%"))
            QTimer.singleShot(0, lambda: self.bearish_label.setText(f"Bearish: {sentiment.get('bearish_percent', 0):.0f}%"))

            # News table
            news = self.news_aggregator.fetch_all_news(max_per_source=5)
            QTimer.singleShot(0, lambda n=news: self._populate_news_table(n))

        except Exception as e:
            print(f"Error refreshing news: {e}")

    def _populate_news_table(self, news):
        """Populate news table (must run on main thread)."""
        self.news_table.setRowCount(len(news[:30]))
        for i, article in enumerate(news[:30]):
            self.news_table.setItem(i, 0, QTableWidgetItem(
                article.published.strftime("%H:%M") if article.published else "--"
            ))
            self.news_table.setItem(i, 1, QTableWidgetItem(article.source))
            self.news_table.setItem(i, 2, QTableWidgetItem(article.title[:100]))

            sentiment_item = QTableWidgetItem(article.sentiment.upper())
            if article.sentiment == "bullish":
                sentiment_item.setForeground(QColor("#4CAF50"))
            elif article.sentiment == "bearish":
                sentiment_item.setForeground(QColor("#f44336"))
            self.news_table.setItem(i, 3, sentiment_item)

            self.news_table.setItem(i, 4, QTableWidgetItem(article.category))

    def _refresh_calendar(self):
        """Refresh economic calendar."""
        if not self.economic_calendar:
            return

        try:
            # RBI meetings
            rbi = self.economic_calendar.get_fed_calendar()
            events = self.economic_calendar.get_high_impact_events()
            QTimer.singleShot(0, lambda r=rbi, e=events: self._populate_calendar(r, e))

        except Exception as e:
            print(f"Error refreshing calendar: {e}")

    def _populate_calendar(self, rbi, events):
        """Populate calendar tables (must run on main thread)."""
        self.fed_table.setRowCount(len(rbi))
        for i, meeting in enumerate(rbi):
            self.fed_table.setItem(i, 0, QTableWidgetItem(meeting["date"]))
            self.fed_table.setItem(i, 1, QTableWidgetItem(meeting["day"]))
            self.fed_table.setItem(i, 2, QTableWidgetItem(str(meeting["days_until"])))
            self.fed_table.setItem(i, 3, QTableWidgetItem(meeting["status"]))

        self.events_table.setRowCount(len(events))
        for i, event in enumerate(events):
            self.events_table.setItem(i, 0, QTableWidgetItem(event.name))
            self.events_table.setItem(i, 1, QTableWidgetItem(event.time))
            self.events_table.setItem(i, 2, QTableWidgetItem(event.country))
            self.events_table.setItem(i, 3, QTableWidgetItem(event.importance.upper()))
            self.events_table.setItem(i, 4, QTableWidgetItem(event.impact.upper()))

    def _refresh_briefing(self):
        """Refresh daily briefing."""
        if not self.signal_generator:
            return

        try:
            briefing = self.signal_generator.get_daily_briefing()

            text = "=== DAILY MARKET BRIEFING ===\n\n"

            # Market status
            status = briefing.get("market_status", {})
            text += f"Market Status: {status.get('status', 'Unknown').upper()}\n"
            text += f"Next: {status.get('next_event', '')} ({status.get('time_until', '')})\n\n"

            # Signals
            text += "=== SIGNALS ===\n"
            for name, sig in briefing.get("signals", {}).items():
                text += f"{name.upper()}: {sig.get('signal', 'N/A').upper()} "
                text += f"(Confidence: {sig.get('confidence', 0):.0f}%)\n"
                if sig.get("reasons"):
                    text += f"  Reasons: {', '.join(sig['reasons'][:2])}\n"
            text += "\n"

            # Key levels
            text += "=== KEY LEVELS ===\n"
            for asset, levels in briefing.get("key_levels", {}).items():
                text += f"{asset.upper()}: Rs {levels.get('current', 0):,.2f} "
                text += f"(S: Rs {levels.get('support', 0):,.2f} / R: Rs {levels.get('resistance', 0):,.2f})\n"
            text += "\n"

            # Breaking news
            text += "=== BREAKING NEWS ===\n"
            for news in briefing.get("breaking_news", [])[:3]:
                text += f"• [{news.get('sentiment', '').upper()}] {news.get('title', '')}\n"

            QTimer.singleShot(0, lambda t=text: self.briefing_text.setPlainText(t))

        except Exception as e:
            print(f"Error refreshing briefing: {e}")

    def _run_scan(self, scan_type: str):
        """Run stock screener scan."""
        if not self.stock_screener:
            return

        self.update_status.emit(f"Running {scan_type} scan...")

        def do_scan():
            try:
                if scan_type == "penny":
                    results = self.stock_screener.scan_penny_stocks()
                elif scan_type == "dip":
                    results = self.stock_screener.scan_dip_opportunities()
                elif scan_type == "momentum":
                    results = self.stock_screener.scan_momentum_stocks()
                elif scan_type == "breakout":
                    results = self.stock_screener.scan_breakout_stocks()
                else:
                    results = []

                # Use QTimer to update UI from main thread
                QTimer.singleShot(0, lambda: self._update_screener_table(results))
                self.update_status.emit(f"Found {len(results)} opportunities")

            except Exception as e:
                print(f"Scan error: {e}")
                self.update_status.emit(f"Scan error: {e}")

        threading.Thread(target=do_scan, daemon=True).start()

    def _update_screener_table(self, results):
        """Update screener results table."""
        self.screener_table.setRowCount(len(results))

        for i, stock in enumerate(results):
            self.screener_table.setItem(i, 0, QTableWidgetItem(stock.symbol))
            self.screener_table.setItem(i, 1, QTableWidgetItem(stock.name[:30]))
            self.screener_table.setItem(i, 2, QTableWidgetItem(f"₹{stock.current_price:.2f}"))

            change_item = QTableWidgetItem(f"{stock.change_percent:+.1f}%")
            if stock.change_percent > 0:
                change_item.setForeground(QColor("#4CAF50"))
            else:
                change_item.setForeground(QColor("#f44336"))
            self.screener_table.setItem(i, 3, change_item)

            self.screener_table.setItem(i, 4, QTableWidgetItem(f"{stock.volume:,}"))
            self.screener_table.setItem(i, 5, QTableWidgetItem(f"{stock.signal_strength:.0f}"))
            self.screener_table.setItem(i, 6, QTableWidgetItem(stock.reason[:50]))


def main():
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    window = MarketDashboard()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
