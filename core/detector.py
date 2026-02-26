from __future__ import annotations
from typing import List, Tuple
import numpy as np

def detect_hits_peakish(
    y: np.ndarray,
    sr: int,
    hop_ms: float = 10.0,
    min_gap_ms: float = 90.0,
) -> List[Tuple[float, float]]:
    if y is None or len(y) == 0:
        return []

    y = y.astype(np.float32)
    hop = max(1, int(sr * hop_ms / 1000.0))

    n = len(y)
    m = (n + hop - 1) // hop
    env = np.zeros(m, dtype=np.float32)

    for i in range(m):
        a = i * hop
        b = min(n, a + hop)
        env[i] = float(np.max(np.abs(y[a:b]))) if b > a else 0.0

    k = 3
    if m >= k:
        kernel = np.ones(k, dtype=np.float32) / k
        env_s = np.convolve(env, kernel, mode="same")
    else:
        env_s = env

    d = np.diff(env_s, prepend=env_s[0])
    d[d < 0] = 0.0

    score = 0.6 * env_s + 0.4 * d

    thr = float(np.percentile(score, 92.0))
    thr = max(thr, 0.08)

    min_gap = int(max(1, (min_gap_ms / hop_ms)))
    hits: List[Tuple[float, float]] = []
    last_i = -10**9

    for i in range(1, m - 1):
        if score[i] < thr:
            continue
        if not (score[i] >= score[i - 1] and score[i] >= score[i + 1]):
            continue

        if i - last_i < min_gap:
            if hits and score[i] > hits[-1][1]:
                hits[-1] = (hits[-1][0], float(score[i]))
                last_i = i
            continue

        t = (i * hop) / float(sr)
        hits.append((t, float(score[i])))
        last_i = i

    if hits:
        s = np.array([h[1] for h in hits], dtype=np.float32)
        smin, smax = float(s.min()), float(s.max())
        out = []
        for (t, v) in hits:
            vv = (v - smin) / (smax - smin) if smax > smin else 1.0
            out.append((t, float(vv)))
        return out

    return []