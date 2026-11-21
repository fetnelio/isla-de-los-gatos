"""
Genera el material visual del README:
  - docs/tacticas/nivelN.png : ejemplo "antes / después" de cada táctica, sacado de un paso real del solver
  - docs/episodios/epN.gif   : vista previa animada de cada episodio

Uso (desde la raíz del repo): python3 docs/generar_docs.py
Requiere node + playwright (usa render/cuadros.js) y ffmpeg.
"""
import json
import os
import subprocess
import sys
import tempfile

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, RAIZ)
from PIL import Image, ImageDraw, ImageFont  # noqa: E402
from guion import build  # noqa: E402
from solver import parse, NOMBRE_TACTICA  # noqa: E402

DOCS = os.path.join(RAIZ, "docs")
FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

# tableros generados (generador.py) donde aparece cada táctica: nivel -> archivo
EJEMPLOS = {L: os.path.join(DOCS, "tableros", f"nivel{L}.txt") for L in range(1, 8)}


def beat_index(beats, L):
    for i, b in enumerate(beats):
        if b["kind"] != "step":
            continue
        if L == 1 and b.get("cat") is not None:
            return i
        if b.get("level") == L:
            return i
    raise ValueError(f"no hay paso de nivel {L}")


def json_ejemplo(data, idx, L):
    """Estado previo aplicado al instante, y el paso idx durando 10 s (se aplica en t=5)."""
    beats = []
    for b in data["beats"][:idx]:
        if "apply" in b:
            beats.append({**b, "t": 0, "d": 0, "apply": 0, "caption": ""})
    cur = dict(data["beats"][idx])
    cur.update(t=0, d=10, apply=5)
    cur["tag"] = NOMBRE_TACTICA[L]
    beats.append(cur)
    return {**data, "beats": beats, "duration": 10}


def snap(js, tiempos, out_prefix):
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as f:
        json.dump(js, f)
    subprocess.run(["node", os.path.join(RAIZ, "render", "cuadros.js"), f.name, out_prefix,
                    *[str(t) for t in tiempos]], check=True)
    os.unlink(f.name)
    return [f"{out_prefix}_{t}.png" for t in tiempos]


def panel(antes, despues, titulo, out):
    box = (40, 425, 1040, 1495)  # pastilla de táctica + tablero
    a = Image.open(antes).crop(box)
    d = Image.open(despues).crop(box)
    w, h = a.size
    pad, head = 30, 70
    img = Image.new("RGB", (w * 2 + pad * 3, h + head + pad), "#16213B")
    img.paste(a, (pad, head))
    img.paste(d, (w + pad * 2, head))
    dr = ImageDraw.Draw(img)
    f = ImageFont.truetype(FONT, 40)
    for x, txt in ((pad, "Antes"), (w + pad * 2, "Después")):
        dr.text((x + w / 2, head / 2 + 4), txt, font=f, fill="#AFC0E0", anchor="mm")
    img = img.resize((img.width // 2, img.height // 2), Image.LANCZOS)
    img.save(out, optimize=True)


def tacticas():
    os.makedirs(os.path.join(DOCS, "tacticas"), exist_ok=True)
    tmp = tempfile.mkdtemp()
    resumen = {}
    for L, path in EJEMPLOS.items():
        data = build(parse(open(path).read()), numero=L)
        idx = beat_index(data["beats"], L)
        js = json_ejemplo(data, idx, L)
        t_antes = 4.2 if L >= 6 else 2.0
        a, d = snap(js, [t_antes, 7], os.path.join(tmp, f"n{L}"))
        out = os.path.join(DOCS, "tacticas", f"nivel{L}.png")
        panel(a, d, NOMBRE_TACTICA[L], out)
        resumen[L] = data["beats"][idx].get("caption") or ""
        print(f"nivel {L}: {out}\n   {resumen[L]}")
    json.dump(resumen, open(os.path.join(DOCS, "tacticas", "explicaciones.json"), "w"),
              ensure_ascii=False, indent=1)


def gifs():
    os.makedirs(os.path.join(DOCS, "episodios"), exist_ok=True)
    for e in (1, 2, 3):
        src = os.path.join(DOCS, "videos", f"ep{e}.mp4")
        out = os.path.join(DOCS, "episodios", f"ep{e}.gif")
        vf = ("setpts=PTS/1.6,fps=8,scale=270:-1:flags=lanczos,split[a][b];"
              "[a]palettegen=max_colors=64[p];[b][p]paletteuse=dither=bayer:bayer_scale=4")
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src, "-vf", vf, out], check=True)
        print(f"gif: {out} ({os.path.getsize(out) // 1024} KB)")


if __name__ == "__main__":
    tacticas()
    gifs()
