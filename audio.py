"""
Pista de audio sintetizada a partir del guion (video.json -> audio.wav).
  - fondo: acordes suaves tipo piano eléctrico (ii-V-I-vi en Fa), loop
  - gato: nota "pluck"; en la cascada las notas suben por la escala pentatónica
  - X: tic suave
  - pregunta: campanita
Uso: python3 audio.py video.json audio.wav
"""
import json
import sys
import wave
import numpy as np

SR = 44100


def note(midi):
    return 440.0 * 2 ** ((midi - 69) / 12)


def env(n, attack, decay):
    t = np.arange(n) / SR
    a = np.clip(t / attack, 0, 1)
    return a * np.exp(-t / decay)


def epiano(freq, dur, vol):
    n = int(dur * SR)
    t = np.arange(n) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.25 * np.sin(2 * np.pi * 2 * freq * t) * np.exp(-t * 3)
    return vol * w * env(n, 0.01, dur * 0.45)


def pluck(freq, vol):
    n = int(0.7 * SR)
    t = np.arange(n) / SR
    w = np.sin(2 * np.pi * freq * t) + 0.3 * np.sin(2 * np.pi * 3 * freq * t) * np.exp(-t * 18)
    return vol * w * env(n, 0.004, 0.18)


def tick(vol):
    n = int(0.05 * SR)
    rng = np.random.default_rng(0)
    w = rng.standard_normal(n)
    w = np.convolve(w, np.ones(8) / 8, mode="same")
    return vol * w * env(n, 0.001, 0.012)


def chime(vol):
    out = np.zeros(int(1.5 * SR))
    for m, d in ((84, 0.0), (88, 0.08), (91, 0.16)):
        s = int(d * SR)
        n = len(out) - s
        t = np.arange(n) / SR
        out[s:] += np.sin(2 * np.pi * note(m) * t) * env(n, 0.005, 0.5)
    return vol * out


def mix(buf, sig, at):
    s = int(at * SR)
    if s >= len(buf):
        return
    e = min(len(buf), s + len(sig))
    buf[s:e] += sig[: e - s]


def build(data):
    dur = data["duration"] + 0.5
    buf = np.zeros(int(dur * SR))
    # fondo: Gm7 - C7 - Fmaj7 - Dm7, 2.4 s por acorde
    chords = [[55, 58, 62, 65], [48, 58, 64, 67], [53, 57, 60, 64], [50, 57, 60, 65]]
    t, k = 0.0, 0
    while t < dur:
        for m in chords[k % 4]:
            mix(buf, epiano(note(m), 2.8, 0.035), t)
        mix(buf, epiano(note(chords[k % 4][0] - 12), 2.8, 0.05), t)
        t += 2.4
        k += 1
    penta = [65, 67, 69, 72, 74, 77, 79, 81, 84, 86, 89]
    casc = 0
    for b in data["beats"]:
        if b["kind"] == "question":
            mix(buf, chime(0.12), b["t"])
        if "apply" not in b:
            continue
        at = b["t"] + b["apply"]
        if b.get("cat") is not None:
            if b.get("tag") == "Cascada":
                m = penta[min(casc, len(penta) - 1)]
                casc += 1
            else:
                m = 72
            mix(buf, pluck(note(m), 0.22), at)
        if b.get("x") or b.get("swept"):
            mix(buf, tick(0.25), at)
    # voz encima, con la música atenuada mientras habla
    import wave as _w
    duck = np.ones(len(buf))
    voice = np.zeros(len(buf))
    for b in data["beats"]:
        if not b.get("voz_file"):
            continue
        with _w.open(b["voz_file"]) as w:
            v = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
        s0 = int((b["t"] + 0.1) * SR)
        e = min(len(buf), s0 + len(v))
        voice[s0:e] += v[: e - s0]
        duck[max(0, s0 - 2000):e + 4000] = 0.45
    duck = np.convolve(duck, np.ones(4000) / 4000, mode="same")
    buf = buf * duck + 0.55 * voice
    peak = np.max(np.abs(buf)) or 1
    buf = buf / max(peak, 1.0) * 0.9
    return (buf * 32767).astype(np.int16)


if __name__ == "__main__":
    data = json.load(open(sys.argv[1]))
    pcm = build(data)
    with wave.open(sys.argv[2], "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes(pcm.tobytes())
    print("audio:", sys.argv[2], f"{len(pcm) / SR:.1f}s")
