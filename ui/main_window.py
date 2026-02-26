from __future__ import annotations

from pathlib import Path
from typing import Optional

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QFileDialog,
    QPushButton, QDoubleSpinBox, QLabel, QMessageBox
)

from ui.theme import Theme, APP_QSS
from ui.timeline_widget import TimelineWidget, HitEvent

from audio.player import AudioPlayer
from audio.loader import load_audio_for_analysis
from core.grid import BeatGrid
from core.tempo import estimate_bpm_librosa_optional
from core.detector import detect_hits_peakish


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Rhythm Signal")
        self.resize(1100, 700)

        self.theme = Theme()
        self.setStyleSheet(APP_QSS)

        self.player = AudioPlayer()
        self.grid = BeatGrid(bpm=120.0, downbeat_t0=0.0, beats_per_bar=4)

        self.current_file: Optional[Path] = None
        self._last_beat_index: Optional[int] = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(12, 12, 12, 12)
        root.setSpacing(10)

        self.timeline = TimelineWidget(self.theme)
        root.addWidget(self.timeline, 1)

        controls = QHBoxLayout()
        controls.setSpacing(10)

        self.btn_open = QPushButton("Open")
        self.btn_play = QPushButton("Play / Pause (Space)")
        self.btn_set_downbeat = QPushButton("Set 1st Beat Here")
        self.btn_auto_bpm = QPushButton("Auto BPM")
        controls.addWidget(self.btn_open)
        controls.addWidget(self.btn_play)
        controls.addWidget(self.btn_set_downbeat)
        controls.addWidget(self.btn_auto_bpm)

        controls.addSpacing(20)

        controls.addWidget(QLabel("BPM"))
        self.bpm = QDoubleSpinBox()
        self.bpm.setRange(30.0, 300.0)
        self.bpm.setDecimals(1)
        self.bpm.setSingleStep(0.5)
        self.bpm.setValue(120.0)
        controls.addWidget(self.bpm)

        controls.addStretch(1)
        root.addLayout(controls)

        self._make_menu()

        self.btn_open.clicked.connect(self.open_file_dialog)
        self.btn_play.clicked.connect(self.toggle_play)
        self.btn_set_downbeat.clicked.connect(self.set_downbeat_here)
        self.btn_auto_bpm.clicked.connect(self.auto_bpm)

        self.bpm.valueChanged.connect(self.on_bpm_changed)

        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self.on_tick)
        self.timer.start()

        act_space = QAction(self)
        act_space.setShortcut(QKeySequence(Qt.Key_Space))
        act_space.triggered.connect(self.toggle_play)
        self.addAction(act_space)

        self.statusBar().showMessage("Ready.")

    def _make_menu(self) -> None:
        file_menu = self.menuBar().addMenu("File")

        act_open = QAction("Open...", self)
        act_open.setShortcut(QKeySequence.Open)
        act_open.triggered.connect(self.open_file_dialog)

        act_quit = QAction("Quit", self)
        act_quit.setShortcut(QKeySequence.Quit)
        act_quit.triggered.connect(self.close)

        file_menu.addAction(act_open)
        file_menu.addSeparator()
        file_menu.addAction(act_quit)

    def open_file_dialog(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Audio",
            "",
            "Audio Files (*.mp3 *.wav *.ogg *.flac);;All Files (*)",
        )
        if not path:
            return
        self.load_audio(Path(path))

    def load_audio(self, path: Path) -> None:
        try:
            self.player.load(path)
            dur = self.player.duration_seconds()
            self.timeline.set_duration(dur)

            self.current_file = path
            self.statusBar().showMessage(f"Loaded: {path.name} ({dur:0.1f}s)")

            self.grid.downbeat_t0 = 0.0
            self.timeline.set_downbeat_t0(0.0)
            self._last_beat_index = None

            y, sr = load_audio_for_analysis(path, target_sr=22050, mono=True, max_seconds=180.0)
            hits = detect_hits_peakish(y, sr, hop_ms=10.0, min_gap_ms=90.0)
            self.timeline.set_hits([HitEvent(t=h[0], strength=h[1]) for h in hits])

        except Exception as e:
            QMessageBox.critical(self, "Load Error", f"Failed to load audio:\n{e}")

    def toggle_play(self) -> None:
        if not self.player.is_loaded():
            self.open_file_dialog()
            return
        if self.player.is_playing():
            self.player.pause()
            self.statusBar().showMessage("Paused.")
        else:
            self.player.play()
            self.statusBar().showMessage("Playing...")

    def on_bpm_changed(self, bpm: float) -> None:
        self.grid.bpm = float(bpm)
        self.timeline.set_bpm(float(bpm))
        self._last_beat_index = None

    def set_downbeat_here(self) -> None:
        if not self.player.is_loaded():
            return
        t = self.player.position_seconds()
        self.grid.downbeat_t0 = t
        self.timeline.set_downbeat_t0(t)
        self._last_beat_index = None
        self.statusBar().showMessage(f"Downbeat set to t={t:0.3f}s")

    def auto_bpm(self) -> None:
        if not self.current_file:
            return
        try:
            y, sr = load_audio_for_analysis(self.current_file, target_sr=22050, mono=True, max_seconds=120.0)
            bpm = estimate_bpm_librosa_optional(y, sr)
            if bpm is None:
                QMessageBox.information(
                    self,
                    "Auto BPM",
                    "librosaが未インストール、または推定に失敗しました。\nrequirementsに librosa を追加して再試行できます。"
                )
                return
            self.bpm.setValue(float(bpm))
            self.statusBar().showMessage(f"Auto BPM: {bpm:0.1f}")
        except Exception as e:
            QMessageBox.warning(self, "Auto BPM Error", str(e))

    def on_tick(self) -> None:
        if not self.player.is_loaded():
            return

        t = self.player.position_seconds()
        self.timeline.update_transport(t)

        beat_index = self.grid.beat_index_at(t)
        if beat_index is not None:
            if self._last_beat_index is None:
                self._last_beat_index = beat_index
            elif beat_index != self._last_beat_index:
                self._last_beat_index = beat_index
                self.flash_beat()

    def flash_beat(self) -> None:
        self.timeline.monitor.set_on(True)
        QTimer.singleShot(90, lambda: self.timeline.monitor.set_on(False))