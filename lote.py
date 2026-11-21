"""
Arma un lote de episodios diarios: calendario, tableros y textos para publicar.

  python3 lote.py 2026-11-22 30 4      # fecha de inicio, cantidad, número del primer episodio

Escribe:
  episodios/epN.txt            tablero de cada episodio
  lote/calendario.csv          fecha, episodio, tablero, táctica, estrellas, archivos, texto
  lote/calendario.md           lo mismo, legible
  lote/pendientes.txt          lista de episodios a renderizar (la usa render_lote.sh)

Calendario (día de la semana -> tamaño, táctica objetivo):
  lun 7×7 t2 · mar 8×8 t3 · mié 8×8 t2 · jue 8×8 t3 · vie 8×8 t4 · sáb 9×9 t6 · dom sorteado
"""
import csv
import datetime as dt
import os
import random
import sys

from generador import generate, to_text
from guion import build, ESTRELLAS
from solver import NOMBRE_TACTICA

CALENDARIO = {0: (7, 2), 1: (8, 3), 2: (8, 2), 3: (8, 3), 4: (8, 4), 5: (9, 6)}  # 6 = domingo: sorteo
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
HASHTAGS = "#acertijo #logica #puzzle #juegosdelogica #starbattle #queens #gatos #michis #desafio"


def domingo(fecha):
    rng = random.Random(fecha.isoformat())
    lvl = rng.choice([2, 3, 4, 5, 6])
    n = {2: rng.choice([7, 8]), 3: rng.choice([7, 8]), 4: rng.choice([8, 9])}.get(lvl, 9)
    return n, lvl


def elegir_tablero(n, lvl, base_seed, intentos=20):
    """Entre varios candidatos, el de guion más corto que usa la táctica objetivo 1 o 2 veces."""
    best = None
    for s in range(intentos):
        seed = base_seed + s
        out = generate(n, lvl, seed)
        if not out or not 1 <= out["levels"].count(lvl) <= 2:
            continue
        d = build(out["grid"], 1)["duration"]
        if best is None or d < best[0]:
            best = (d, seed, out)
    return best


def texto(num, lvl, estrellas, dia):
    nueva = NOMBRE_TACTICA[lvl]
    return (f"Nivel {num} {'★' * estrellas}{'☆' * (5 - estrellas)} · ¿Dónde va cada gato?\n"
            f"Un gato por fila, por columna y por isla. Y no se tocan, ni en diagonal.\n"
            f"La clave de hoy: {nueva}.\n"
            f"Pausá y probá antes de ver la solución.\n\n{HASHTAGS}")


def main(inicio, cantidad, primero):
    os.makedirs("lote", exist_ok=True)
    os.makedirs("episodios", exist_ok=True)
    filas = []
    for k in range(cantidad):
        fecha = inicio + dt.timedelta(days=k)
        num = primero + k
        wd = fecha.weekday()
        n, lvl = domingo(fecha) if wd == 6 else CALENDARIO[wd]
        best = elegir_tablero(n, lvl, num * 1000)
        if best is None:
            sys.exit(f"ep{num}: no se encontró tablero {n}x{n} táctica {lvl}")
        dur, seed, out = best
        open(f"episodios/ep{num}.txt", "w").write(to_text(out["grid"]) + "\n")
        est = ESTRELLAS[lvl]
        filas.append({
            "fecha": fecha.isoformat(), "dia": DIAS[wd], "episodio": num,
            "tablero": f"{n}x{n}", "tactica": NOMBRE_TACTICA[lvl], "estrellas": "★" * est,
            "semilla": seed, "reel": f"docs/videos/ep{num}.mp4", "story": f"docs/stories/ep{num}.mp4",
            "texto_reel": texto(num, lvl, est, DIAS[wd]),
        })
        print(f"ep{num} {fecha} {DIAS[wd]:9} {n}x{n} t{lvl} semilla {seed} (guion base {dur:.0f}s)", flush=True)

    with open("lote/calendario.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(filas[0]))
        w.writeheader()
        w.writerows(filas)
    with open("lote/pendientes.txt", "w") as f:
        f.write("\n".join(str(r["episodio"]) for r in filas) + "\n")
    md = ["# Calendario de publicación\n",
          "Cada día: **story** (desafío, a la mañana) y **reel** (solución, unas horas después).\n",
          "| Fecha | Día | Ep. | Tablero | Táctica clave | Dificultad | Reel | Story |",
          "|---|---|---|---|---|---|---|---|"]
    for r in filas:
        md.append(f"| {r['fecha']} | {r['dia']} | {r['episodio']} | {r['tablero']} | {r['tactica']} | "
                  f"{r['estrellas']} | [mp4](../{r['reel']}) | [mp4](../{r['story']}) |")
    md.append("\n## Textos de cada reel\n")
    for r in filas:
        md.append(f"### Ep. {r['episodio']} · {r['dia']} {r['fecha']}\n\n```\n{r['texto_reel']}\n```\n")
    open("lote/calendario.md", "w").write("\n".join(md))


if __name__ == "__main__":
    inicio = dt.date.fromisoformat(sys.argv[1])
    main(inicio, int(sys.argv[2]), int(sys.argv[3]))
