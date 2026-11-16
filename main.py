import sys

from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from styles import APP_STYLE, UI_FONT, load_fonts


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("City Network Builder")

    loaded = load_fonts()
    if UI_FONT in loaded:
        app.setFont(QFont(UI_FONT, 11))

    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())