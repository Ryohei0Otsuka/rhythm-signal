# models/project.py
from __future__ import annotations
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional
import json

@dataclass
class Marker:
    t: float
    label: str = ""
    kind: str = "hit"  # or "manual"

@dataclass
class Project:
    audio_path: str
    bpm: float = 120.0
    downbeat_t0: float = 0.0
    markers: List[Marker] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["markers"] = [asdict(m) for m in (self.markers or [])]
        return d

    def save(self, path: Path) -> None:
        path.write_text(json.dumps(self.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")

    @staticmethod
    def load(path: Path) -> "Project":
        data = json.loads(path.read_text(encoding="utf-8"))
        markers = [Marker(**m) for m in data.get("markers", [])]
        return Project(
            audio_path=data["audio_path"],
            bpm=float(data.get("bpm", 120.0)),
            downbeat_t0=float(data.get("downbeat_t0", 0.0)),
            markers=markers,
        )