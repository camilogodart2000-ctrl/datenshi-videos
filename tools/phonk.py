"""Original phonk-style beat synthesizer (cowbell melody, distorted 808, hats, claps).
Everything is synthesized from scratch, so the result is free to use.
Usage: python3 phonk.py <seed> <duration_s> <bpm> <out.wav>
"""
import sys
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 44100


def env(n, attack=0.002, decay=0.2):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    return a * np.exp(-t / decay)


def bp(x, lo, hi):
    return sosfilt(butter(2, [lo, hi], btype="band", fs=SR, output="sos"), x)


def hp(x, f):
    return sosfilt(butter(2, f, btype="high", fs=SR, output="sos"), x)


def lp(x, f):
    return sosfilt(butter(2, f, btype="low", fs=SR, output="sos"), x)


def square(f, t):
    return np.tanh(6 * np.sin(2 * np.pi * f * t))


def cowbell(freq, length=0.35):
    n = int(length * SR)
    t = np.arange(n) / SR
    s = square(freq, t) + 0.7 * square(freq * 1.4836, t)
    s = bp(s, freq * 0.8, min(freq * 4.5, 15000))
    return 0.55 * s * env(n, 0.001, 0.11)


def bass808(freq, length=0.6, drive=4.0):
    n = int(length * SR)
    t = np.arange(n) / SR
    f = freq * (1 + 1.6 * np.exp(-t / 0.018))
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = np.sin(ph) * env(n, 0.001, length * 0.55)
    s = np.tanh(drive * s) / np.tanh(drive)
    return 0.75 * lp(s, 2500)


def clap(rng, length=0.25):
    n = int(length * SR)
    noise = rng.standard_normal(n)
    e = np.zeros(n)
    for d in (0, 0.009, 0.018):
        k = int(d * SR)
        e[k:] += env(n - k, 0.0005, 0.012)
    e += 0.6 * env(n, 0.002, 0.08)
    return 0.45 * bp(noise, 900, 6000) * e


def hat(rng, length=0.05, open_=False):
    n = int((0.18 if open_ else length) * SR)
    s = hp(rng.standard_normal(n), 7000)
    return 0.16 * s * env(n, 0.0005, 0.06 if open_ else 0.015)


def place(buf, snd, pos):
    i = int(pos * SR)
    if i >= len(buf):
        return
    j = min(len(buf), i + len(snd))
    buf[i:j] += snd[: j - i]


def make(seed, dur, bpm):
    rng = np.random.default_rng(seed)
    step = 60 / bpm / 4  # 16th note
    n_steps = int(dur / step) + 1
    buf = np.zeros(int((dur + 1) * SR))

    root_midi = int(rng.choice([45, 46, 47, 48, 49, 50]))  # A2..D3
    phrygian = [0, 1, 3, 5, 7, 8, 10]
    midi = lambda m: 440 * 2 ** ((m - 69) / 12)

    # cowbell melody: 32-step pattern (2 bars), dense on-beat hits
    rhythm_bank = [
        [1,0,0,1, 0,0,1,0, 1,0,0,1, 0,0,1,0],
        [1,0,1,0, 0,1,0,1, 1,0,1,0, 0,1,1,0],
        [1,0,0,1, 0,1,0,0, 1,0,0,1, 0,1,0,1],
        [1,1,0,1, 0,0,1,0, 1,0,1,1, 0,0,1,0],
    ]
    r1 = rhythm_bank[rng.integers(len(rhythm_bank))]
    r2 = rhythm_bank[rng.integers(len(rhythm_bank))]
    rhythm = r1 + r2
    degrees = []
    d = 0
    for _ in range(32):
        d = int(np.clip(d + rng.choice([-2, -1, 0, 1, 1, 2, 3]), 0, 9))
        degrees.append(d)
    melody = [root_midi + 24 + phrygian[k % 7] + 12 * (k // 7) for k in degrees]

    # 808 line per bar (follows root with a fall)
    bass_notes = [root_midi - 12, root_midi - 12, root_midi - 12 + phrygian[rng.integers(1, 4)], root_midi - 12]

    intro_steps = 0 if rng.random() < 0.5 else 4
    for s in range(n_steps):
        t0 = s * step
        bar_pos = s % 16
        bar = s // 16
        # cowbell
        if rhythm[s % 32]:
            place(buf, cowbell(midi(melody[s % 32])), t0)
        if s < intro_steps:
            continue
        # kick + 808
        if bar_pos in (0, 10) or (bar_pos == 7 and bar % 2):
            place(buf, bass808(midi(bass_notes[bar % 4]), 0.55 if bar_pos else 0.75), t0)
        # clap on 2 and 4
        if bar_pos in (4, 12):
            place(buf, clap(rng), t0)
        # hats: 8ths with rolls
        if bar_pos % 2 == 0:
            place(buf, hat(rng), t0)
        if bar_pos in (14, 15) and bar % 2:
            for k in range(3):
                place(buf, hat(rng) * 0.8, t0 + k * step / 3)
        if bar_pos == 6:
            place(buf, hat(rng, open_=True), t0)

    buf = buf[: int(dur * SR)]
    # master: glue + saturation + fades
    buf = np.tanh(1.6 * buf) * 0.85
    fade = int(0.6 * SR)
    buf[-fade:] *= np.linspace(1, 0, fade)
    buf[: int(0.01 * SR)] *= np.linspace(0, 1, int(0.01 * SR))
    peak = np.max(np.abs(buf)) or 1
    buf = buf / peak * 0.89
    stereo = np.stack([buf, np.roll(buf, 90) * 0.98], axis=1)
    return (stereo * 32767).astype(np.int16)


if __name__ == "__main__":
    seed, dur, bpm, out = int(sys.argv[1]), float(sys.argv[2]), float(sys.argv[3]), sys.argv[4]
    wavfile.write(out, SR, make(seed, dur, bpm))
