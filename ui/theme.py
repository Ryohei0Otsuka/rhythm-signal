from dataclasses import dataclass

@dataclass(frozen=True)
class Theme:
    bg: str = "#0B0F14"
    fg: str = "#D7DEE7"
    grid: str = "#263241"
    grid_strong: str = "#3B4D63"
    accent: str = "#4CC3FF"
    hit: str = "#44FFAA"
    playhead: str = "#FF4C6A"
    monitor_off: str = "#2A3442"
    monitor_on: str = "#FF2E2E"

APP_QSS = """
QMainWindow { background: #0B0F14; }
QLabel, QGroupBox { color: #D7DEE7; }
QPushButton, QToolButton {
    background: #111826;
    color: #D7DEE7;
    border: 1px solid #263241;
    padding: 6px 10px;
    border-radius: 10px;
}
QPushButton:hover, QToolButton:hover { border-color: #3B4D63; }
QPushButton:pressed { background: #0F1520; }
QLineEdit, QSpinBox, QDoubleSpinBox {
    background: #0F1520;
    color: #D7DEE7;
    border: 1px solid #263241;
    padding: 4px 8px;
    border-radius: 10px;
}
QStatusBar { color: #9FB0C3; }
QMenuBar { background: #0B0F14; color: #D7DEE7; }
QMenuBar::item:selected { background: #111826; }
QMenu { background: #0B0F14; color: #D7DEE7; border: 1px solid #263241; }
QMenu::item:selected { background: #111826; }
"""