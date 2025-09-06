# File: app/main.py

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt

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

    # Instantiate and show the main window
    win = MainWindow()
    win.show()

    # Start the application's event loop
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()