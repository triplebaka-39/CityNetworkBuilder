"""Generates the app's sound effects as tiny WAV files (pure sine beeps).
Run from the project root:  python tools/make_sfx.py
"""
import math
import struct
import wave
from pathlib import Path

RATE = 44100
OUT = Path(__file__).resolve().parent.parent / "assets" / "sfx"


def tone(freq: float, ms: int, volume: float = 0.35) -> list[float]:
    n = int(RATE * ms / 1000)
    fade = max(1, int(RATE * 0.008))  # 8 ms fade in/out removes clicks
    samples = []
    for i in range(n):
        env = min(1.0, i / fade, (n - i) / fade)
        samples.append(math.sin(2 * math.pi * freq * i / RATE) * volume * env)
    return samples


def save(name: str, parts: list[list[float]]) -> None:
    data = [s for part in parts for s in part]
    OUT.mkdir(parents=True, exist_ok=True)
    with wave.open(str(OUT / f"{name}.wav"), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(b"".join(struct.pack("<h", int(s * 32767)) for s in data))


# Higher pitch = adding, lower pitch = removing. Cities are single notes,
# roads are two quick notes.
save("city_add",    [tone(660, 90)])
save("city_remove", [tone(330, 110)])
save("road_add",    [tone(520, 60), tone(780, 80)])
save("road_remove", [tone(780, 60), tone(520, 80)])
save("clear",       [tone(440, 70), tone(330, 70), tone(220, 110)])
save("error",       [tone(180, 140)])
print("Wrote sounds to", OUT)
