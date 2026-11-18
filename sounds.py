"""Tiny sound helper. Usage:

    from sounds import Sounds
    self.sounds = Sounds()          # create once, e.g. in MainWindow.__init__
    self.sounds.play("city_add")    # call wherever the action happens
"""
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QSoundEffect

SFX_DIR = Path(__file__).resolve().parent / "assets" / "sfx"
NAMES = ("city_add", "city_remove", "road_add", "road_remove", "clear", "error")


class Sounds:
    def __init__(self, volume: float = 0.6, enabled: bool = True) -> None:
        self.enabled = enabled
        self._effects: dict[str, QSoundEffect] = {}
        for name in NAMES:
            path = SFX_DIR / f"{name}.wav"
            if not path.exists():
                continue
            effect = QSoundEffect()
            effect.setSource(QUrl.fromLocalFile(str(path)))
            effect.setVolume(volume)
            self._effects[name] = effect

    def play(self, name: str) -> None:
        effect = self._effects.get(name)
        if self.enabled and effect is not None:
            effect.play()
