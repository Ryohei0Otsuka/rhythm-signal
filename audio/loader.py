# audio/loader.py
from __future__ import annotations

import os
import sys
import tempfile
import subprocess
from pathlib import Path
from typing import Tuple

import numpy as np


def _ffmpeg_path() -> str:
    """
    ffmpegの場所を返す。
    - 開発環境: PATH上のffmpeg
    - exe環境: PyInstaller展開先(_MEIPASS)/bin/ffmpeg.exe を優先
    """
    if getattr(sys, "frozen", False):
        base = Path(sys._MEIPASS)  # type: ignore[attr-defined]
        ff = base / "bin" / "ffmpeg.exe"
        if ff.exists():
            return str(ff)
    return "ffmpeg"


def _decode_to_wav_pcm16(src: Path, target_sr: int, mono: bool) -> Path:
    """
    ffmpegで音源をwav(PCM s16le)にデコードして一時ファイルへ。
    """
    ffmpeg = _ffmpeg_path()
    channels = "1" if mono else "2"

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
    tmp_path = Path(tmp.name)
    tmp.close()

    # -y 上書き, -vn 映像無視, -ac/-ar チャンネル/サンプルレート固定, PCM16LE
    cmd = [
        ffmpeg,
        "-y",
        "-vn",
        "-i", str(src),
        "-ac", channels,
        "-ar", str(int(target_sr)),
        "-f", "wav",
        "-acodec", "pcm_s16le",
        str(tmp_path),
    ]

    # コンソールを出さずに実行（失敗時は例外）
    p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if p.returncode != 0 or not tmp_path.exists() or tmp_path.stat().st_size == 0:
        # 失敗時の情報を出す
        raise RuntimeError(f"ffmpeg decode failed:\n{p.stderr[-2000:]}")

    return tmp_path


def _load_with_soundfile(path: Path) -> Tuple[np.ndarray, int]:
    import soundfile as sf
    y, sr = sf.read(str(path), always_2d=False)
    y = y.astype(np.float32)
    return y, sr


def load_audio_for_analysis(
    path: Path,
    target_sr: int = 22050,
    mono: bool = True,
    max_seconds: float = 180.0,
) -> Tuple[np.ndarray, int]:
    """
    解析用に音声をnumpyへロード。
    - wav/ogg/flac: soundfileで直接
    - mp3/m4a/aac等: ffmpegでwavにデコード → soundfileで読む
    """
    if not path.exists():
        raise FileNotFoundError(path)

    ext = path.suffix.lower().lstrip(".")
    tmp_wav: Path | None = None

    try:
        if ext in ("wav", "ogg", "flac"):
            y, sr = _load_with_soundfile(path)
        else:
            # mp3含む「ほとんど全部」をffmpeg経由にする（安定）
            tmp_wav = _decode_to_wav_pcm16(path, target_sr=target_sr, mono=mono)
            y, sr = _load_with_soundfile(tmp_wav)

        # soundfileが2chを返す場合があるので整形
        if y.ndim == 2:
            if mono:
                y = y.mean(axis=1)
            else:
                # stereo -> take as is
                pass

        # trim
        if max_seconds and max_seconds > 0:
            max_n = int(max_seconds * sr)
            if len(y) > max_n:
                y = y[:max_n]

        # normalize
        m = float(np.max(np.abs(y))) if len(y) else 1.0
        if m > 0:
            y = (y / m).astype(np.float32)

        return y.astype(np.float32), int(sr)

    finally:
        if tmp_wav is not None:
            try:
                os.remove(tmp_wav)
            except Exception:
                pass