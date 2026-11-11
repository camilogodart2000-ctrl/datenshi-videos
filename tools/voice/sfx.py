"""Sound design original (synthétisé) pour les vidéos voix Datenshi.
Usage : python3 sfx.py events.json durée seed sortie.wav
events.json : liste [{"t": secondes, "k": type, "d": durée optionnelle}] produite par motion.html (events()).
"""
import json, sys
import numpy as np
from scipy.signal import butter, sosfilt
from scipy.io import wavfile

SR = 48000


def lp(x, f, o=4):
    return sosfilt(butter(o, f, 'low', fs=SR, output='sos'), x)


def hp(x, f, o=4):
    return sosfilt(butter(o, f, 'high', fs=SR, output='sos'), x)


def bp(x, a, b, o=4):
    return sosfilt(butter(o, [a, b], 'band', fs=SR, output='sos'), x)


def env(n, a, d):
    t = np.arange(n) / SR
    return np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / d)


def sweep(f0, f1, dur, k=6.0):
    t = np.arange(int(dur * SR)) / SR
    f = f1 + (f0 - f1) * np.exp(-t * k)
    return np.sin(2 * np.pi * np.cumsum(f) / SR)


rng = None


def noise(n):
    return rng.standard_normal(n)


def whoosh():
    n = int(.55 * SR); x = noise(n); out = np.zeros(n)
    for i in range(0, n, 480):  # filtre glissant par blocs
        c = 400 + 5000 * np.sin(np.pi * i / n) ** 2
        out[i:i + 480] = bp(x[max(0, i - 2000):i + 480], c * .6, min(c * 1.6, 20000))[-len(out[i:i + 480]):]
    return out * np.sin(np.linspace(0, np.pi, n)) ** 2 * .5, .33  # pic à 0,33 s


def pop(f=820):
    n = int(.12 * SR); t = np.arange(n) / SR
    return np.sin(2 * np.pi * f * t * (1 + .6 * np.exp(-t * 60))) * env(n, .002, .03) * .5, 0


def pop2():
    a, _ = pop(392); b, _ = pop(311)
    out = np.zeros(int(.2 * SR)); out[:len(a)] += a; out[int(.07 * SR):int(.07 * SR) + len(b)] += b
    return out * .8, 0


def hit():
    n = int(.35 * SR)
    k = sweep(160, 45, .35, 18) * env(n, .001, .12)
    c = hp(noise(n), 2500) * env(n, .0005, .015) * .4
    return (k + c) * .9, 0


def boom():
    n = int(1.6 * SR)
    k = sweep(110, 32, 1.6, 7) * env(n, .002, .45)
    crash = lp(noise(n), 1800) * env(n, .002, .25) * .5
    return (k + crash) * 1.0, 0


def riser(d=1.3):
    n = int(d * SR); t = np.arange(n) / SR
    x = hp(noise(n), 1200) * (t / d) ** 2 * .35
    tone = np.sin(2 * np.pi * np.cumsum(200 + 900 * (t / d) ** 2) / SR) * (t / d) ** 3 * .15
    return x + tone, d


def shimmer():
    n = int(2.2 * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for f, a in [(1760, .3), (2637, .22), (3520, .16), (5274, .1)]:
        out += np.sin(2 * np.pi * f * t + f) * a * env(n, .01, .7) * (1 + .3 * np.sin(2 * np.pi * 6 * t))
    return out * .35, 0


def rip():
    n = int(.4 * SR); x = bp(noise(n), 1500, 6000)
    am = (rng.random(n // 240 + 1) > .35).repeat(240)[:n]
    return x * am * env(n, .003, .12) * .6, 0


def tick():
    n = int(.04 * SR)
    return hp(noise(n), 3000) * env(n, .0003, .006) * .5 + np.sin(2 * np.pi * 1900 * np.arange(n) / SR) * env(n, .0005, .01) * .25, 0


def bell(f=660, dur=2.4, amp=.4):
    n = int(dur * SR); t = np.arange(n) / SR; out = np.zeros(n)
    for m, a, dcy in [(1, 1, .9), (2.01, .5, .6), (3.0, .3, .4), (4.2, .2, .3), (5.4, .12, .2)]:
        out += np.sin(2 * np.pi * f * m * t) * a * env(n, .003, dcy)
    return out * amp, 0


def roll(d):
    out = np.zeros(int((d + .1) * SR)); tk, _ = tick(); tt = 0.0; k = 0
    while tt < d:
        i = int(tt * SR); out[i:i + len(tk)] += tk * .8
        k += 1; tt += .045 + .05 * (tt / max(d, .01)) ** 2
    return out, 0


def reverb(x, sec=1.1):
    n = int(sec * SR)
    ir = noise(n) * np.exp(-np.arange(n) / SR / (sec / 5))
    ir = lp(ir, 5000); ir /= np.abs(ir).sum() / 6
    return np.convolve(x, ir)[:len(x)]


def bed(dur, seed):
    n = int(dur * SR); t = np.arange(n) / SR
    root = [49.0, 55.0, 46.25, 51.91][seed % 4]
    x = np.zeros(n)
    for m, a in [(1, .5), (1.5, .25), (2, .2), (3, .06)]:
        x += np.sin(2 * np.pi * root * m * t + m) * a * (1 + .25 * np.sin(2 * np.pi * .13 * m * t))
    air = lp(noise(n), 700) * .08 * (1 + .5 * np.sin(2 * np.pi * .09 * t))
    beat = 60 / (84 + seed % 12)  # battement de cœur discret
    hb = np.zeros(n); k, _ = hit()
    for b0 in np.arange(.0, dur, beat * 2):
        for off, g in [(0, .35), (.22, .2)]:
            i = int((b0 + off) * SR)
            if i < n: hb[i:i + len(k)] += lp(k, 140)[:n - i] * g
    fade = np.minimum(1, t / 1.2) * np.minimum(1, (dur - t) / .8)
    return (x * .22 + air + hb) * fade


def main():
    global rng
    ev = json.load(open(sys.argv[1])); dur = float(sys.argv[2]); seed = int(sys.argv[3]); out = sys.argv[4]
    rng = np.random.default_rng(seed)
    n = int(dur * SR) + SR; dry = np.zeros(n); wet = np.zeros(n)
    for e in ev:
        k = e['k']; t = e['t']; send = 0
        if k == 'whoosh': s, a = whoosh()
        elif k == 'pop': s, a = pop(760 + 160 * rng.random())
        elif k == 'pop2': s, a = pop2()
        elif k == 'hit': s, a = hit(); send = .2
        elif k == 'boom': s, a = boom(); send = .5
        elif k == 'riser_end': s, a = riser()
        elif k == 'shimmer': s, a = shimmer(); send = .6
        elif k == 'rip': s, a = rip()
        elif k == 'tick': s, a = tick()
        elif k == 'roll': s, a = roll(e.get('d', .8))
        elif k == 'ding': s, a = bell(1320, 1.6, .3); send = .4
        elif k == 'bell': s, a = bell(523.25, 2.6, .35); send = .6
        else: continue
        i = int((t - a) * SR)
        if i < 0: s = s[-i:]; i = 0
        m = min(len(s), n - i)
        dry[i:i + m] += s[:m]; wet[i:i + m] += s[:m] * send
    mix = dry + reverb(wet) + np.pad(bed(dur, seed), (0, n - int(dur * SR)))
    mix = mix[:int(dur * SR)]
    mix = mix / (np.abs(mix).max() + 1e-9) * .5  # crête à -6 dBFS
    st = np.stack([mix, np.roll(mix, 240) * .96], 1)  # léger élargissement stéréo
    wavfile.write(out, SR, (st * 32767).astype(np.int16))


if __name__ == '__main__':
    main()
