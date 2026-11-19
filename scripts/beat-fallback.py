#!/usr/bin/env python3
"""Pure-Python beat tracker used when numpy is not installed.

Mirrors the algorithm in osu-beats.py with the standard library only: a radix-2
FFT over the same 1024-sample window, bass-weighted spectral flux, then the
same autocorrelation and comb over the last six seconds. It is slower than
numpy but keeps the lyric word grid working without a system package.

Run with --selftest to check a synthetic 120 BPM track.
"""
import cmath
import math
import struct
import sys

RATE = 22050
HOP = 512
WIN = 1024
FPS = RATE / HOP
HISTORY = int(6 * FPS)


def fft(a):
    """In-place iterative radix-2 Cooley-Tukey FFT on a list of complex numbers."""
    n = len(a)
    j = 0
    for i in range(1, n):
        bit = n >> 1
        while j & bit:
            j ^= bit
            bit >>= 1
        j ^= bit
        if i < j:
            a[i], a[j] = a[j], a[i]
    length = 2
    while length <= n:
        wlen = cmath.exp(-2j * cmath.pi / length)
        for i in range(0, n, length):
            w = 1 + 0j
            for k in range(i, i + length // 2):
                u = a[k]
                v = a[k + length // 2] * w
                a[k] = u + v
                a[k + length // 2] = u - v
                w *= wlen
        length <<= 1
    return a


def frange(start, stop, step):
    """numpy.arange with a float step, without numpy."""
    n = int(math.ceil((stop - start) / step))
    return [start + i * step for i in range(n)]


def interp_one(xx, n, fp):
    """np.interp for the fixed integer axis 0..n-1 and a left fill of 0."""
    if xx < 0:
        return 0.0
    if xx >= n - 1:
        return fp[-1]
    i = int(xx)
    return fp[i] + (xx - i) * (fp[i + 1] - fp[i])


class Tracker:
    def __init__(self):
        self.window = [0.5 - 0.5 * math.cos(2 * math.pi * n / (WIN - 1)) for n in range(WIN)]
        freqs = [k * RATE / WIN for k in range(WIN // 2 + 1)]
        self.low = [i for i, f in enumerate(freqs) if f < 180]
        self.nlow = max(1, len(self.low))
        self.nall = len(freqs)
        self.prev = None
        self.odf = []
        self.times = []
        self.samples = []
        self.bpm = 0.0
        self.pending = 0.0
        self.quiet_since = None

    def feed(self, mono, t_end):
        """mono samples whose last one was heard at t_end (epoch s)."""
        self.samples.extend(mono)
        n_hops = (len(self.samples) - WIN) // HOP + 1
        if n_hops <= 0:
            return
        for i in range(n_hops):
            frame = [x * w for x, w in zip(self.samples[i * HOP:i * HOP + WIN], self.window)]
            spec = fft([complex(x, 0) for x in frame])[:WIN // 2 + 1]
            mag = [math.log1p(abs(z) * 20) for z in spec]
            if self.prev is None:
                flux = 0.0
            else:
                rise = [max(m - p, 0.0) for m, p in zip(mag, self.prev)]
                flux = sum(rise[k] for k in self.low) / self.nlow * 3 + sum(rise) / self.nall
            self.prev = mag
            left = len(self.samples) - (i * HOP + WIN)
            self.odf.append(flux)
            self.times.append(t_end - left / RATE)
        self.samples = self.samples[n_hops * HOP:]
        if len(self.odf) > HISTORY:
            self.odf = self.odf[-HISTORY:]
            self.times = self.times[-HISTORY:]

    def estimate(self):
        if len(self.odf) < int(3 * FPS):
            return None
        x = [float(v) for v in self.odf]
        n = len(x)
        k = 8
        # np.convolve(x, ones(k)/k, mode='same') with even k: window i-4..i+3
        smooth = [sum(x[j] for j in range(i - (k - 1) // 2, i + k // 2 + 1) if 0 <= j < n) / k
                  for i in range(n)]
        x = [max(v - s, 0.0) for v, s in zip(x, smooth)]
        if not any(x):
            return None
        m = max(x)
        x = [v / m for v in x]
        lo, hi = int(FPS * 60 / 190), int(FPS * 60 / 70) + 1
        ac = [sum(x[t] * x[t + lag] for t in range(n - lag)) for lag in range(lo, hi)]
        lags = list(range(lo, hi))
        bpms = [60 * FPS / lag for lag in lags]
        prior = [math.exp(-0.5 * (math.log2(b / 120.0) / 0.9) ** 2) for b in bpms]
        score = [a * b for a, b in zip(ac, prior)]
        i = max(range(len(score)), key=score.__getitem__)
        a = score[i - 1] if i > 0 else 0
        c = score[i + 1] if i < len(score) - 1 else 0
        b = score[i]
        d = 0.5 * (a - c) / (a - 2 * b + c) if (a - 2 * b + c) else 0
        if i == 0 or i == len(score) - 1:
            d = 0
        lag = lags[i] + d
        bpm = 60 * FPS / lag
        conf = ac[i] / (sum(v * v for v in x) or 1)
        best, best_lag, best_off, best_mean = -1.0, lag, 0.0, 1.0
        for L in frange(lag - 1.2, lag + 1.25, 0.05):
            if L < lo:
                continue
            offs = frange(0, L, 0.5)
            sums = []
            for off in offs:
                s = 0.0
                for step in frange(0, (n - 1) / L, 1):
                    idx = (n - 1) - off - step * L
                    if idx >= 0:
                        s += interp_one(idx, n, x)
                sums.append(s)
            j = max(range(len(sums)), key=sums.__getitem__)
            if sums[j] > best:
                best, best_lag, best_off = sums[j], L, offs[j]
                best_mean = sum(sums) / len(sums)
        bpm = 60 * FPS / best_lag
        beat_idx = int(round(n - 1 - best_off))
        beat_ms = self.times[beat_idx] * 1000 - 20
        if self.bpm and abs(bpm - self.bpm) / self.bpm > 0.04:
            if self.pending and abs(bpm - self.pending) / self.pending < 0.04:
                self.bpm = bpm
                self.pending = 0
            else:
                self.pending = bpm
                bpm = self.bpm
        else:
            self.bpm = bpm if not self.bpm else self.bpm * 0.7 + bpm * 0.3
            bpm = self.bpm
            self.pending = 0
        fit = best / best_mean if best_mean > 0 else 0.0
        return {
            "bpm": round(bpm, 2),
            "beat": round(beat_ms, 1),
            "conf": round(min(1.0, conf * 4), 3),
            "fit": round(fit, 2),
        }


def mono_from_chunk(chunk, channels):
    vals = struct.unpack("<%dh" % (len(chunk) // 2), chunk)
    return [sum(vals[i:i + channels]) / (32768.0 * channels) for i in range(0, len(vals), channels)]


def rms(a):
    return math.sqrt(sum(v * v for v in a) / len(a)) if a else 0.0


def selftest():
    dur = 12.0
    buf = [0.0] * int(RATE * dur)
    for beat in range(int(dur / 0.5)):
        start = int(beat * 0.5 * RATE)
        for i in range(int(0.25 * RATE)):
            env = math.exp(-i / (0.05 * RATE))
            buf[start + i] += 0.8 * env * math.sin(2 * math.pi * 60 * i / RATE)
    t = Tracker()
    t0 = 1_700_000_000.0
    for i in range(0, len(buf), HOP * 8):
        a = buf[i:i + HOP * 8]
        t.feed(a, t0 + (i + len(a)) / RATE)
    est = t.estimate()
    assert est and abs(est["bpm"] - 120) < 2, est
    assert est["conf"] > 0.5 and est["fit"] > 1, est
    print("beat-fallback selftest:", est)


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        selftest()
