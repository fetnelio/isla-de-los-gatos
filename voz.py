"""
Voz del relator (Piper TTS, natural) y re-timing del guion según la voz.

Marcas en el texto:  [risa] -> "¡Ja, ja, ja, ja!"   ([glitch] se ignora)
Voz: variable de entorno VOZ (nombre del modelo en /home/user/voces), por defecto es_AR-daniela-high.
Velocidad: variable VOZ_VEL (length_scale de Piper; <1 más rápido), por defecto 0.92.

Uso: python3 voz.py video.json   (escribe clips en <base>_voz/ y actualiza el json)
"""
import io
import json
import os
import re
import sys
import wave
import numpy as np
from piper import PiperVoice, SynthesisConfig

SR = 44100
VOCES = os.environ.get("VOCES_DIR", os.path.join(os.path.dirname(os.path.abspath(__file__)), "voces"))
MODELO = os.environ.get("VOZ", "es_AR-daniela-high")
VEL = float(os.environ.get("VOZ_VEL", "0.92"))
RISA = "¡Ja, ja, ja, ja!"

_voice = None


def tts(text, length_scale=None):
    global _voice
    if _voice is None:
        _voice = PiperVoice.load(os.path.join(VOCES, MODELO + ".onnx"))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        _voice.synthesize_wav(text, w, SynthesisConfig(length_scale=length_scale or VEL))
    buf.seek(0)
    with wave.open(buf) as w:
        sr = w.getframerate()
        x = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16).astype(np.float32) / 32768
    t_new = np.arange(int(len(x) * SR / sr)) / SR
    x = np.interp(t_new, np.arange(len(x)) / sr, x)
    nz = np.where(np.abs(x) > 0.01)[0]
    return x[max(0, nz[0] - 200): nz[-1] + 2000] if len(nz) else x


def say(text):
    parts = re.split(r"(\[risa\])", text.replace("[glitch] ", "").replace("[glitch]", ""))
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        if p == "[risa]":
            out += [np.zeros(int(0.12 * SR)), tts(RISA, VEL * 0.85), np.zeros(int(0.2 * SR))]
        else:
            out.append(tts(p))
    return np.concatenate(out) if out else np.zeros(1)


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
