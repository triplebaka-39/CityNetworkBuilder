import sys
from pathlib import Path

from PySide6.QtGui import QFont, QIcon
from PySide6.QtWidgets import QApplication

from main_window import MainWindow
from styles import APP_STYLE, UI_FONT, load_fonts


def main() -> int:
    # Ensure Windows taskbar displays the custom icon instead of generic Python/host icon
    if sys.platform == "win32":
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("citynetworkbuilder.mst.app.1")
        except Exception:
            pass

    app = QApplication(sys.argv)
    app.setApplicationName("City Network Builder")

    icon_path = Path(__file__).resolve().parent / "assets" / "app_icon.png"
    if icon_path.exists():
        app.setWindowIcon(QIcon(str(icon_path)))

    loaded = load_fonts()
    if UI_FONT in loaded:
        app.setFont(QFont(UI_FONT, 11))

    app.setStyleSheet(APP_STYLE)

    window = MainWindow()
    if icon_path.exists():
        window.setWindowIcon(QIcon(str(icon_path)))
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
