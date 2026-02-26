from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput


class AudioPlayer:
    def __init__(self) -> None:
        self._player = QMediaPlayer()
        self._audio = QAudioOutput()
        self._player.setAudioOutput(self._audio)
        self._loaded: bool = False
        self._path: Optional[Path] = None

    def load(self, path: Path) -> None:
        if not path.exists():
            raise FileNotFoundError(path)
        self._path = path
        url = QUrl.fromLocalFile(str(path.resolve()))
        self._player.setSource(url)
        self._loaded = True

    def is_loaded(self) -> bool:
        return self._loaded

    def is_playing(self) -> bool:
        return self._player.playbackState() == QMediaPlayer.PlayingState

    def play(self) -> None:
        self._player.play()

    def pause(self) -> None:
        self._player.pause()

    def stop(self) -> None:
        self._player.stop()

    def position_seconds(self) -> float:
        return float(self._player.position()) / 1000.0

    def duration_seconds(self) -> float:
        return float(self._player.duration()) / 1000.0