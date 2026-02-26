from __future__ import annotations
from dataclasses import dataclass
from typing import Optional

@dataclass
class BeatGrid:
    bpm: float
    downbeat_t0: float
    beats_per_bar: int = 4

    def beat_seconds(self) -> float:
        bpm = max(30.0, min(300.0, float(self.bpm)))
        return 60.0 / bpm

    def beat_index_at(self, t: float) -> Optional[int]:
        beat_s = self.beat_seconds()
        dt = float(t) - float(self.downbeat_t0)
        if dt < 0:
            return None
        return int(dt // beat_s)