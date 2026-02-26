from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Tuple

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

from ui.theme import Theme

@dataclass
class HitEvent:
    t: float          # seconds
    strength: float   # 0..1

class BeatMonitor(QLabel):
    def __init__(self, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme = theme
        self.setAlignment(Qt.AlignCenter)
        self.setFixedHeight(42)
        self.setText("BEAT")
        self._on = False
        self._apply()

    def set_on(self, on: bool) -> None:
        self._on = on
        self._apply()

    def _apply(self) -> None:
        bg = self._theme.monitor_on if self._on else self._theme.monitor_off
        self.setStyleSheet(
            f"QLabel {{ background:{bg}; color:{self._theme.fg}; "
            "border: 1px solid #263241; border-radius: 12px; font-weight: 700; }}"
        )

class TimelineWidget(QWidget):
    """
    2小節固定表示のタイムライン:
    - beat grid（拍線 + 1拍目強調）
    - ヒット（縦バー）
    - 再生ヘッド
    """
    def __init__(self, theme: Theme, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._theme = theme

        self._bpm: float = 120.0
        self._t0_downbeat: float = 0.0  # 1拍目(小節頭)の基準時刻(sec)
        self._time_sig: Tuple[int, int] = (4, 4)  # 4/4のみ（MVP）
        self._window_bars: int = 2  # 2小節表示固定
        self._hits: List[HitEvent] = []

        self._current_t: float = 0.0
        self._duration_s: float = 0.0

        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        layout.setSpacing(8)

        self.monitor = BeatMonitor(theme)
        layout.addWidget(self.monitor)

        pg.setConfigOptions(antialias=True)
        self.plot = pg.PlotWidget()
        self.plot.setBackground(theme.bg)
        self.plot.showGrid(x=False, y=False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.hideButtons()
        self.plot.setMenuEnabled(False)

        self.plot.getAxis("left").setStyle(showValues=False)
        self.plot.getAxis("left").setPen(pg.mkPen(theme.grid))
        self.plot.getAxis("bottom").setPen(pg.mkPen(theme.grid))
        self.plot.getAxis("bottom").setTextPen(pg.mkPen(theme.fg))
        self.plot.setYRange(0, 1.0, padding=0.05)

        layout.addWidget(self.plot, 1)

        self._grid_items: List[pg.GraphicsObject] = []
        self._hit_item: Optional[pg.BarGraphItem] = None
        self._playhead_line = pg.InfiniteLine(pos=0.0, angle=90, pen=pg.mkPen(theme.playhead, width=2))
        self.plot.addItem(self._playhead_line)

        self._info = QLabel("")
        self._info.setStyleSheet("color: #9FB0C3;")
        layout.addWidget(self._info)

        self._redraw_all()

    # ---------- Public API ----------
    def set_bpm(self, bpm: float) -> None:
        self._bpm = max(30.0, min(300.0, float(bpm)))
        self._redraw_all()

    def set_downbeat_t0(self, t0: float) -> None:
        self._t0_downbeat = max(0.0, float(t0))
        self._redraw_all()

    def set_duration(self, duration_s: float) -> None:
        self._duration_s = max(0.0, float(duration_s))
        self._redraw_all()

    def set_hits(self, hits: List[HitEvent]) -> None:
        self._hits = hits
        self._redraw_hits()

    def update_transport(self, current_t: float) -> None:
        self._current_t = max(0.0, float(current_t))
        self._update_view_and_playhead()

    # ---------- Internals ----------
    def _bars_window_seconds(self) -> float:
        beats_per_bar = self._time_sig[0]
        beat_s = 60.0 / self._bpm
        return self._window_bars * beats_per_bar * beat_s

    def _current_window(self) -> Tuple[float, float]:
        w = self._bars_window_seconds()
        start = self._current_t - w * 0.25
        start = max(0.0, start)
        end = start + w
        if self._duration_s > 0.0:
            end = min(self._duration_s, end)
            start = max(0.0, end - w)
        return start, end

    def _clear_grid(self) -> None:
        for it in self._grid_items:
            self.plot.removeItem(it)
        self._grid_items.clear()

    def _redraw_grid(self) -> None:
        self._clear_grid()
        start, end = self._current_window()
        beats_per_bar = self._time_sig[0]
        beat_s = 60.0 / self._bpm
        if beat_s <= 0:
            return

        k0 = int(np.floor((start - self._t0_downbeat) / beat_s))
        if self._t0_downbeat + k0 * beat_s < start:
            k0 += 1

        k = k0
        while True:
            t = self._t0_downbeat + k * beat_s
            if t > end:
                break

            is_bar_head = (k % beats_per_bar) == 0
            pen = pg.mkPen(self._theme.grid_strong if is_bar_head else self._theme.grid, width=2 if is_bar_head else 1)
            line = pg.InfiniteLine(pos=t, angle=90, pen=pen)
            self.plot.addItem(line)
            self._grid_items.append(line)

            beat_num = (k % beats_per_bar) + 1
            text = pg.TextItem(text=str(beat_num), anchor=(0.5, 1.2), color=self._theme.fg)
            text.setPos(t, 0.0)
            self.plot.addItem(text)
            self._grid_items.append(text)

            k += 1

        self.plot.setXRange(start, end, padding=0.0)

    def _redraw_hits(self) -> None:
        if self._hit_item is not None:
            self.plot.removeItem(self._hit_item)
            self._hit_item = None

        if not self._hits:
            return

        start, end = self._current_window()
        xs = []
        hs = []
        width = 0.01
        for h in self._hits:
            if start <= h.t <= end:
                xs.append(h.t)
                hs.append(max(0.02, min(1.0, h.strength)))

        if not xs:
            return

        self._hit_item = pg.BarGraphItem(
            x=np.array(xs),
            height=np.array(hs),
            width=width,
            y0=0.0,
            brush=pg.mkBrush(self._theme.hit),
            pen=pg.mkPen(None),
        )
        self.plot.addItem(self._hit_item)

    def _update_view_and_playhead(self) -> None:
        start, end = self._current_window()
        self.plot.setXRange(start, end, padding=0.0)
        self._playhead_line.setPos(self._current_t)

        self._info.setText(
            f"t={self._current_t:0.3f}s | BPM={self._bpm:0.1f} | downbeat(t0)={self._t0_downbeat:0.3f}s"
        )

        self._redraw_grid()
        self._redraw_hits()

    def _redraw_all(self) -> None:
        self._update_view_and_playhead()