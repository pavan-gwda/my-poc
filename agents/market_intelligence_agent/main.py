#!/usr/bin/env python3
"""Market Intelligence Agent - Entry Point."""

import sys
import signal
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import Qt


def main():
    """Main entry point for Market Intelligence Agent."""
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    app = QApplication(sys.argv)
    app.setApplicationName("Market Intelligence Agent")
    app.setOrganizationName("MarketIntel")
    app.setStyle("Fusion")

    from ui.dashboard import MarketDashboard

    dashboard = MarketDashboard()
    dashboard.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
