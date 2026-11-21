"""
Galería de episodios para GitHub Pages y README.

  python3 docs/generar_galeria.py

Escribe:
  docs/galeria/epN.jpg   miniatura (cuadro de la story: tablero vacío)
  docs/episodios.html    página con reel + story de cada episodio, texto para copiar y descargas
  README.md              grilla de miniaturas entre <!-- galeria:inicio --> y <!-- galeria:fin -->
"""
import csv
import html
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(RAIZ, "docs")
sys.path.insert(0, RAIZ)
from solver import solve, parse, NOMBRE_TACTICA  # noqa: E402
from guion import ESTRELLAS  # noqa: E402

PAGES = "https://fetnelio.github.io/isla-de-los-gatos/"
DIAS_CORTOS = {"lunes": "lun", "martes": "mar", "miércoles": "mié", "jueves": "jue",
               "viernes": "vie", "sábado": "sáb", "domingo": "dom"}


def duracion(path):
    if not os.path.exists(path):
        return None
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "csv=p=0", path], capture_output=True, text=True).stdout.strip()
    return round(float(out)) if out else None


def episodios():
    eps = {}
    cal = os.path.join(RAIZ, "lote", "calendario.csv")
    if os.path.exists(cal):
        for r in csv.DictReader(open(cal)):
            eps[int(r["episodio"])] = r
    for f in os.listdir(os.path.join(RAIZ, "episodios")):
        m = re.match(r"ep(\d+)\.txt$", f)
        if not m:
            continue
        n = int(m.group(1))
        if n in eps:
            continue
        grid = parse(open(os.path.join(RAIZ, "episodios", f)).read())
        lvl = solve(grid)["maxlevel"]
        eps[n] = {"episodio": n, "fecha": "", "dia": "piloto", "tablero": f"{len(grid)}x{len(grid)}",
                  "tactica": NOMBRE_TACTICA[lvl], "estrellas": "★" * ESTRELLAS[lvl], "texto_reel": ""}
    out = []
    for n in sorted(eps):
        r = dict(eps[n])
        r["reel_rel"] = f"videos/ep{n}.mp4"
        r["story_rel"] = f"stories/ep{n}.mp4"
        r["reel_s"] = duracion(os.path.join(DOCS, r["reel_rel"]))
        r["story_s"] = duracion(os.path.join(DOCS, r["story_rel"]))
        if r["reel_s"] is None:
            continue
        out.append(r)
    return out


def miniatura(r):
    os.makedirs(os.path.join(DOCS, "galeria"), exist_ok=True)
    dst = os.path.join(DOCS, "galeria", f"ep{r['episodio']}.jpg")
    src = os.path.join(DOCS, r["story_rel"] if r["story_s"] else r["reel_rel"])
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", "6", "-i", src, "-frames:v", "1",
                        "-vf", "scale=270:-1", "-q:v", "4", dst], check=True)
    return f"galeria/ep{r['episodio']}.jpg"


def miniatura_reel(r):
    """Portada del reel: cuadro final (tablero resuelto)."""
    dst = os.path.join(DOCS, "galeria", f"ep{r['episodio']}_reel.jpg")
    src = os.path.join(DOCS, r["reel_rel"])
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-ss", str(max(0, r["reel_s"] - 1.5)), "-i", src,
                        "-frames:v", "1", "-vf", "scale=270:-1", "-q:v", "4", dst], check=True)
    return f"galeria/ep{r['episodio']}_reel.jpg"


def etiqueta_fecha(r):
    if not r["fecha"]:
        return "Piloto"
    a, m, d = r["fecha"].split("-")
    return f"{DIAS_CORTOS.get(r['dia'], r['dia'])} {int(d)}/{int(m)}"


def pagina(eps):
    tarjetas = []
    for r in eps:
        n = r["episodio"]
        thumb = miniatura(r)
        story = ""
        if r["story_s"]:
            story = f"""
        <figure><video src="{r['story_rel']}" poster="{thumb}" controls playsinline preload="none"></video>
          <figcaption>Story · {r['story_s']} s · <a href="{r['story_rel']}" download>descargar</a></figcaption></figure>"""
        texto = ""
        if r.get("texto_reel"):
            texto = f"""
      <details><summary>Texto para el reel</summary>
        <pre id="t{n}">{html.escape(r['texto_reel'])}</pre>
        <button type="button" data-copy="t{n}">Copiar texto</button></details>"""
        largo = ' <span class="aviso">largo</span>' if r["reel_s"] and r["reel_s"] > 60 else ""
        tarjetas.append(f"""
    <article class="ep" id="ep{n}">
      <header><h2>Ep. {n}</h2><span class="fecha">{etiqueta_fecha(r)}</span></header>
      <p class="meta"><span class="estrellas">{r['estrellas']}</span> · {r['tablero']} · {html.escape(r['tactica'])}</p>
      <div class="videos">
        <figure><video src="{r['reel_rel']}" poster="{miniatura_reel(r)}" controls playsinline preload="none"></video>
          <figcaption>Reel · {r['reel_s']} s{largo} · <a href="{r['reel_rel']}" download>descargar</a></figcaption></figure>{story}
      </div>{texto}
    </article>""")
    return f"""<!doctype html>
<html lang="es">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Episodios · La Isla de los Gatos</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Nunito:wght@600;800;900&display=swap" rel="stylesheet">
<style>
  :root {{ --bg1:#16213B; --bg2:#24345A; --card:#1D2B4A; --ink:#FFF; --muted:#AFC0E0; --accent:#FFD36E; --line:#2E4170; --warn:#FF8A80; }}
  * {{ box-sizing: border-box; }}
  body {{ margin:0; color:var(--ink); font-family:Nunito,system-ui,sans-serif; line-height:1.45;
         background: radial-gradient(ellipse at 50% 0%, var(--bg2), var(--bg1) 60%) fixed, var(--bg1); }}
  main {{ max-width:1200px; margin:0 auto; padding:40px 16px 80px; }}
  .top {{ text-align:center; margin-bottom:32px; }}
  .marca {{ letter-spacing:.35em; color:var(--muted); font-weight:800; font-size:14px; }}
  h1 {{ font-size:clamp(32px,6vw,52px); font-weight:900; margin:6px 0; }}
  .top p {{ color:var(--muted); margin:0; }}
  .top a {{ color:var(--accent); }}
  .grilla {{ display:grid; grid-template-columns:repeat(auto-fill,minmax(340px,1fr)); gap:20px; }}
  .ep {{ background:var(--card); border:1px solid var(--line); border-radius:18px; padding:16px; scroll-margin-top:16px; }}
  .ep:target {{ outline:3px solid var(--accent); }}
  .ep header {{ display:flex; justify-content:space-between; align-items:baseline; }}
  .ep h2 {{ margin:0; font-size:22px; font-weight:900; }}
  .fecha {{ color:var(--accent); font-weight:800; }}
  .meta {{ margin:4px 0 12px; color:var(--muted); font-size:15px; }}
  .estrellas {{ color:var(--accent); letter-spacing:1px; }}
  .videos {{ display:grid; grid-template-columns:1fr 1fr; gap:10px; }}
  figure {{ margin:0; }}
  video {{ width:100%; aspect-ratio:9/16; border-radius:10px; background:#0B1020; display:block; }}
  figcaption {{ font-size:13px; color:var(--muted); margin-top:6px; }}
  figcaption a {{ color:var(--accent); }}
  .aviso {{ color:var(--warn); font-weight:800; }}
  details {{ margin-top:12px; }}
  summary {{ cursor:pointer; font-weight:800; color:var(--muted); }}
  pre {{ white-space:pre-wrap; background:#121B33; border-radius:10px; padding:12px; font:14px/1.4 Nunito,system-ui,sans-serif; color:var(--ink); }}
  button {{ background:var(--accent); color:#2A2340; border:0; border-radius:20px; padding:8px 16px; font:800 14px Nunito,system-ui,sans-serif; cursor:pointer; }}
  @media (max-width:420px) {{ .grilla {{ grid-template-columns:1fr; }} }}
</style>
</head>
<body>
<main>
  <div class="top">
    <div class="marca">LA ISLA DE LOS GATOS</div>
    <h1>Todos los episodios</h1>
    <p>{len(eps)} episodios · reel (solución) + story (desafío) · <a href="./">volver al inicio</a></p>
  </div>
  <section class="grilla">{''.join(tarjetas)}
  </section>
</main>
<script>
  // un solo video sonando a la vez
  document.addEventListener("play", e => {{
    document.querySelectorAll("video").forEach(v => {{ if (v !== e.target) v.pause(); }});
  }}, true);
  document.querySelectorAll("button[data-copy]").forEach(b => b.addEventListener("click", async () => {{
    const t = document.getElementById(b.dataset.copy).textContent;
    try {{ await navigator.clipboard.writeText(t); b.textContent = "¡Copiado!"; }}
    catch (e) {{ b.textContent = "Seleccioná y copiá a mano"; }}
    setTimeout(() => b.textContent = "Copiar texto", 1800);
  }}));
</script>
</body>
</html>
"""


def readme(eps):
    filas, fila = [], []
    for r in eps:
        n = r["episodio"]
        fila.append(f'<td align="center"><a href="{PAGES}episodios.html#ep{n}">'
                    f'<img src="docs/galeria/ep{n}.jpg" width="120" alt="Episodio {n}"></a><br>'
                    f'<sub><b>Ep. {n}</b> · {etiqueta_fecha(r)}<br>{r["estrellas"]} · {r["reel_s"]} s</sub></td>')
        if len(fila) == 6:
            filas.append("<tr>" + "".join(fila) + "</tr>")
            fila = []
    if fila:
        filas.append("<tr>" + "".join(fila) + "</tr>")
    bloque = ("<!-- galeria:inicio -->\n"
              f"**[▶ Ver todos los episodios con reel y story]({PAGES}episodios.html)**\n\n"
              "<table>\n" + "\n".join(filas) + "\n</table>\n<!-- galeria:fin -->")
    path = os.path.join(RAIZ, "README.md")
    s = open(path).read()
    if "<!-- galeria:inicio -->" in s:
        s = re.sub(r"<!-- galeria:inicio -->.*?<!-- galeria:fin -->", lambda m: bloque, s, flags=re.S)
    else:
        s = s.replace("## El puzzle", "## Episodios\n\n" + bloque + "\n\n---\n\n## El puzzle", 1)
    open(path, "w").write(s)


if __name__ == "__main__":
    eps = episodios()
    open(os.path.join(DOCS, "episodios.html"), "w").write(pagina(eps))
    readme(eps)
    print(f"{len(eps)} episodios en la galería")
