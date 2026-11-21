"""
Voz del relator y re-timing del guion según la voz.

Motor: Kokoro (ONNX), voces en español: ef_dora (default), em_alex, em_santa.
También acepta una voz Piper si VOZ empieza con "es_" (p.ej. es_MX-ald-medium).

Marcas en el texto:
  [miau]  -> "¡Miau, miau, miau, miáuuu!"   ([risa] es alias)
  [michi] -> "Michi, michi, miau."
  ([glitch] se ignora)

Variables: VOZ (voz), VOZ_VEL (velocidad Kokoro; >1 más rápido; default 1.05),
           VOCES_DIR (carpeta de modelos, default ./voces)

Uso: python3 voz.py video.json   (escribe clips en <base>_voz/ y actualiza el json)
"""
import io
import json
import os
import re
import sys
import wave
import numpy as np

SR = 44100
VOCES = os.environ.get("VOCES_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "voces"))
MODELO = os.environ.get("VOZ", "ef_dora")
VEL = float(os.environ.get("VOZ_VEL", "1.05"))
MARCAS = {
    "[miau]": "¡Miau, miau, miau, miáuuu!",
    "[risa]": "¡Miau, miau, miau, miáuuu!",
    "[michi]": "Michi, michi, miau.",
}

_engine = None


def _resample(x, sr):
    if sr == SR:
        return x
    t_new = np.arange(int(len(x) * SR / sr)) / SR
    return np.interp(t_new, np.arange(len(x)) / sr, x)


def _trim(x):
    nz = np.where(np.abs(x) > 0.01)[0]
    return x[max(0, nz[0] - 200): nz[-1] + 2000] if len(nz) else x


def tts(text, speed=None):
    global _engine
    speed = speed or VEL
    if MODELO.startswith("es_"):  # Piper
        from piper import PiperVoice, SynthesisConfig
        if _engine is None:
            _engine = PiperVoice.load(os.path.join(VOCES, MODELO + ".onnx"))
        buf = io.BytesIO()
        with wave.open(buf, "wb") as w:
            _engine.synthesize_wav(text, w, SynthesisConfig(length_scale=1 / speed))
        buf.seek(0)
        with wave.open(buf) as w:
            sr = w.getframerate()
            x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    else:  # Kokoro
        from kokoro_onnx import Kokoro
        if _engine is None:
            _engine = Kokoro(os.path.join(VOCES, "kokoro-v1.0.onnx"), os.path.join(VOCES, "voices-v1.0.bin"))
        x, sr = _engine.create(text, voice=MODELO, speed=speed, lang="es")
        x = np.asarray(x, dtype=np.float32)
    return _trim(_resample(x, sr))


def say(text):
    text = text.replace("[glitch] ", "").replace("[glitch]", "")
    parts = re.split(r"(\[miau\]|\[risa\]|\[michi\])", text)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p in MARCAS:
            out += [np.zeros(int(0.12 * SR)), tts(MARCAS[p]), np.zeros(int(0.2 * SR))]
        else:
            out.append(tts(p))
    x = np.concatenate(out) if out else np.zeros(1)
    return x / (np.max(np.abs(x)) + 1e-9) * 0.9


def write(path, x):
    x = np.clip(x, -1, 1)
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((x * 32767).astype(np.int16).tobytes())


def main(json_path):
    data = json.load(open(json_path))
    base = os.path.splitext(json_path)[0]
    outdir = base + "_voz"
    os.makedirs(outdir, exist_ok=True)
    t = 0.0
    for i, b in enumerate(data["beats"]):
        d = b["d"]
        if b.get("voz"):
            x = say(b["voz"])
            f = os.path.join(outdir, f"{i:03d}.wav")
            write(f, x)
            vlen = len(x) / SR
            b["voz_file"] = os.path.abspath(f)
            b["voz_len"] = round(vlen, 3)
            new_d = max(d, vlen + b.get("pad", 0.5))
            if "apply" in b and b.get("tag") != "Cascada":
                b["apply"] = round(min(new_d - 0.3, max(0.4, vlen * 0.9)), 3)
            d = new_d
        b["t"] = round(t, 3)
        b["d"] = round(d, 3)
        t += d
    data["duration"] = round(t, 3)
    data["voz"] = MODELO
    json.dump(data, open(json_path, "w"), ensure_ascii=False, indent=1)
    print(f"voz ({MODELO}): {sum(1 for b in data['beats'] if b.get('voz_file'))} clips, duración {t:.1f}s")


if __name__ == "__main__":
    main(sys.argv[1])
