from __future__ import annotations
from typing import Optional
import numpy as np

def estimate_bpm_librosa_optional(y: np.ndarray, sr: int) -> Optional[float]:
    try:
        import librosa
        oenv = librosa.onset.onset_strength(y=y, sr=sr)
        tempo = librosa.feature.tempo(onset_envelope=oenv, sr=sr)
        bpm = float(tempo[0]) if len(tempo) else None
        if bpm and (30.0 <= bpm <= 300.0):
            return bpm
        return None
    except Exception:
        return None