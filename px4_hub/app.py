"""
Application launcher and Qt lifecycle manager for PX4 Setup Hub.
"""
import sys
import os
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from .ui.main_window import MainWindow
from .comms.connection_manager import ConnectionManager
from .core.database import DatabaseManager


def run_app():
    # Enable High DPI scaling
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )

    app = QApplication(sys.argv)
    app.setApplicationName("PX4 Setup Hub")
    app.setOrganizationName("PX4 Community")

    db_mgr = DatabaseManager()
    conn_mgr = ConnectionManager()

    window = MainWindow(conn_mgr, db_mgr)
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    run_app()
