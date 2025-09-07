# File: app/main.py

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from pathlib import Path

# Import the main window from our new structure
from app.main_window import MainWindow


def main():
    """
    The main entry point for the application.
    Initializes the QApplication and the MainWindow, then starts the event loop.
    """
    # High DPI scaling attributes for better rendering on modern displays
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)

    # Load a global stylesheet (keeps styling separate from code)
    qss_path = Path(__file__).with_name("styles.qss")
    if qss_path.is_file():
        app.setStyleSheet(qss_path.read_text(encoding="utf-8"))

    # Instantiate and show the main window
    win = MainWindow()
    win.show()

    # Start the application's event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()