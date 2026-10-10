"""Original 124 BPM track for the promo reel (pure numpy, no samples). Usage: music.py <beats> <out.wav>
Sections (in beats): intro 0-12, build 12-24, drop 24-(end-6), outro tail."""
import sys, wave, numpy as np
SR = 44100; BPM = 124; B = 60 / BPM
NB = int(sys.argv[1]); OUT = sys.argv[2]
N = int((NB * B + 2.5) * SR); mix = np.zeros((N, 2))
rng = np.random.default_rng(7)
def put(sig, t, pan=0.0, g=1.0):
    i = int(t * SR); j = min(N, i + len(sig)); s = sig[: j - i] * g
    mix[i:j, 0] += s * (1 - max(0, pan)); mix[i:j, 1] += s * (1 + min(0, pan))
def env(n, a, r): e = np.ones(n); na = int(a * SR); e[:na] = np.linspace(0, 1, na) if na else 1; e *= np.exp(-np.arange(n) / (r * SR)); return e
def saw(f, d, h=12, det=0.0):
    t = np.arange(int(d * SR)) / SR; s = np.zeros_like(t)
    for k in range(1, h + 1):
        if f * k > 9000: break
        s += np.sin(2 * np.pi * f * k * t * (1 + det)) / k
    return s * 0.6
def note(m): return 440 * 2 ** ((m - 69) / 12)
def kick(): d = 0.45; t = np.arange(int(d * SR)) / SR; f = 45 + 110 * np.exp(-t * 30); return np.sin(2 * np.pi * np.cumsum(f) / SR) * np.exp(-t * 7) * 1.0
def clap():
    d = 0.25; n = rng.standard_normal(int(d * SR)); t = np.arange(len(n)) / SR
    n = n - np.convolve(n, np.ones(6) / 6, "same"); e = np.exp(-t * 18)
    for o in (0.0, 0.012, 0.024): e += np.exp(-np.maximum(0, t - o) * 120) * (t >= o) * 0.6
    return n * e * 0.35
def hat(open_=False):
    d = 0.22 if open_ else 0.05; n = rng.standard_normal(int(d * SR)); n = n - np.convolve(n, np.ones(3) / 3, "same")
    return n * np.exp(-np.arange(len(n)) / SR * (12 if open_ else 70)) * (0.16 if open_ else 0.12)
def reverb(x, sec=2.2, wet=0.3):
    L = int(sec * SR); ir = rng.standard_normal(L) * np.exp(-np.arange(L) / SR * 3.2); ir /= np.sqrt((ir ** 2).sum())
    n = 1 << int(np.ceil(np.log2(len(x) + L)))
    y = np.fft.irfft(np.fft.rfft(x, n) * np.fft.rfft(ir, n), n)[: len(x)]
    return x + y * wet
CH = [(57, [57, 60, 64]), (53, [53, 57, 60]), (48, [48, 52, 55]), (55, [55, 59, 62])]  # Am F C G
I0, D0 = 12, 24; DROP_END = NB - 6
pad = np.zeros(N)
for bar in range(0, NB + 4, 4):
    root, ch = CH[(bar // 4) % 4]; d = 4 * B + 0.4
    for m in ch:
        for det in (-0.004, 0.004):
            s = saw(note(m + 12), d, h=6, det=det) * env(int(d * SR), 0.35, 3.0) * 0.07
            i = int(bar * B * SR); j = min(N, i + len(s)); pad[i:j] += s[: j - i]
for b in range(NB + 4):
    t = b * B; sec = "i" if b < I0 else "b" if b < D0 else "d" if b < DROP_END else "o"
    root = CH[(b // 4) % 4][0]
    if sec in "bd" or (sec == "o" and b < DROP_END + 1): pass
    if sec == "d":
        put(kick(), t, g=0.95)
        if b % 2 == 1: put(clap(), t, g=0.9)
        put(hat(True), t + B / 2, pan=0.2)
        for q in (0.25, 0.75): put(hat(), t + q * B, pan=-0.3)
        bs = saw(note(root - 12), B / 2 * 0.9, h=8) * env(int(B / 2 * 0.9 * SR), 0.005, 0.18)
        put(bs, t + B / 2, g=0.55); put(np.sin(2 * np.pi * note(root - 24) * np.arange(int(B * SR)) / SR) * env(int(B * SR), 0.01, 0.25), t, g=0.35)
        arp = CH[(b // 4) % 4][1]
        for q in range(4):
            m = arp[(b * 4 + q) % 3] + 24; dd = B / 4
            put(saw(note(m), dd * 1.6, h=5) * env(int(dd * 1.6 * SR), 0.002, 0.08), t + q * dd, pan=(-0.4 if q % 2 else 0.4), g=0.16)
    elif sec == "b":
        put(kick(), t, g=0.6 if b < 20 else 0.0)
        k = 1 if b < 18 else 2 if b < 22 else 4
        for q in range(k): put(clap(), t + q * B / k, g=0.25 + 0.5 * (b - I0) / 12)
        put(hat(), t + B / 2, g=1.0)
        put(np.sin(2 * np.pi * note(root - 24) * np.arange(int(B * SR)) / SR) * env(int(B * SR), 0.01, 0.3), t, g=0.3)
    elif sec == "i":
        if b % 4 == 0: put(np.sin(2 * np.pi * note(root - 24) * np.arange(int(4 * B * SR)) / SR) * env(int(4 * B * SR), 0.6, 2.5), t, g=0.4)
        if b % 2 == 1: put(hat(), t + B / 2, g=0.5)
# riser into the drop + impact
rl = 12 * B; n = rng.standard_normal(int(rl * SR)); n = n - np.convolve(n, np.ones(4) / 4, "same")
put(n * np.linspace(0, 1, len(n)) ** 2.5 * 0.25, I0 * B)
tt = np.arange(int(rl * SR)) / SR; put(np.sin(2 * np.pi * np.cumsum(200 + 1600 * (tt / rl) ** 2) / SR) * (tt / rl) ** 3 * 0.08, I0 * B)
imp = kick() * 1.3; put(imp, D0 * B); put(np.pad(imp, (0, SR))[: SR] * 0, D0 * B)
put(rng.standard_normal(int(1.8 * SR)) * np.exp(-np.arange(int(1.8 * SR)) / SR * 2.5) * 0.18, D0 * B)
put(rng.standard_normal(int(1.8 * SR)) * np.exp(-np.arange(int(1.8 * SR)) / SR * 2.5) * 0.12, DROP_END * B)
pad_g = np.ones(N); pad_g[int(D0 * B * SR):int(DROP_END * B * SR)] = 0.55
mix[:, 0] += pad * pad_g; mix[:, 1] += pad * pad_g
for c in range(2): mix[:, c] = reverb(mix[:, c], wet=0.22)
# sidechain-ish pump on drop
t = np.arange(N) / SR; ph = (t % B) / B; pump = np.where((t >= D0 * B) & (t < DROP_END * B), 0.55 + 0.45 * np.minimum(1, ph * 4), 1)
mix *= pump[:, None]
end = NB * B; fade = np.clip((end + 2.2 - t) / 2.2, 0, 1); fade[t < end] = 1; mix *= fade[:, None]
mix = np.tanh(mix * 1.4) ; mix /= np.abs(mix).max() / 0.89
w = wave.open(OUT, "wb"); w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes((mix * 32767).astype("<i2").tobytes()); w.close()
print("wav", N / SR)
