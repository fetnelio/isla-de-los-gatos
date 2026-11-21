"""
Guion del relator: convierte los pasos del solver en una línea de tiempo narrada.

Cada "beat" tiene: tiempo, duración, textos, resaltados y efectos sobre el tablero.
Uso: python3 guion.py tablero.txt --numero 12 -o video.json
"""
import json
import random
import re
import sys
from solver import solve, parse, NOMBRE_TACTICA

# invitaciones a la acción del cierre (rotan por episodio)
CTAS = [
    "Si lo sacaste antes que yo, dejá un miau en los comentarios.",
    "Mandáselo a quien siempre te gana en estos juegos.",
    "Guardalo y probalo sin mirar la solución.",
    "Mañana, otra isla. Seguime para no perdértela.",
]

# paleta propia (nombre para el relator, color)
PALETA = [
    ("roja", "#E8716D"), ("naranja", "#F2A65A"), ("amarilla", "#EFD26B"),
    ("verde", "#7CC47F"), ("turquesa", "#45B5AA"), ("celeste", "#86C5E8"),
    ("azul", "#5A78C8"), ("violeta", "#9C7AD1"), ("rosa", "#EE92C2"),
    ("marrón", "#A47454"), ("lima", "#C3DB6C"), ("gris", "#9FA8B3"),
]
ESTRELLAS = {0: 1, 1: 1, 2: 2, 3: 3, 4: 4, 5: 4, 6: 5, 7: 5}
COLS = "ABCDEFGHIJKL"


def build(grid, numero=1, titulo="¿Dónde va cada gato?"):
    n = len(grid)
    res = solve(grid)
    if not res["solved"]:
        raise SystemExit("El solver no pudo resolver este tablero")
    steps = res["steps"]
    maxlevel = res["maxlevel"]

    def gname(g):
        tipo, i = g[0], g[1]
        if tipo == "isla":
            return f"la isla {PALETA[i][0]}"
        if tipo == "fila":
            return f"la fila {i + 1}"
        return f"la columna {COLS[i]}"

    def gcells(g):
        tipo, i = g[0], g[1]
        if tipo == "isla":
            return [r * n + c for r in range(n) for c in range(n) if grid[r][c] == i]
        if tipo == "fila":
            return [i * n + c for c in range(n)]
        return [r * n + i for r in range(n)]

    def cname(i):
        r, c = divmod(i, n)
        return f"{COLS[c]}{r + 1}"

    def cap(s):
        return s[0].upper() + s[1:]

    # cascada: racha final de pasos nivel 1
    cascade_from = len(steps)
    while cascade_from > 0 and steps[cascade_from - 1]["level"] == 1:
        cascade_from -= 1
    if len(steps) - cascade_from < 3:
        cascade_from = len(steps)

    rng = random.Random(str(grid))
    pick = rng.choice
    seen_levels = set()
    prev_level = None
    beats = []
    t = 0.0

    def add(d, **kw):
        nonlocal t
        kw["t"] = round(t, 3)
        kw["d"] = d
        beats.append(kw)
        t += d

    add(3.0, kind="intro", caption=titulo,
        sub="1 gato por fila, columna e isla. Los gatos no se tocan, ni en diagonal.",
        voz=f"Nivel {numero}. Un gato por fila, por columna y por isla. Y no se tocan. Ni en diagonal.")
    add(2.5, kind="pause", caption="Pausá y probá.", sub="¿Por dónde empezarías?",
        voz=pick(["Pausá el video y probá. Yo te espero.",
                  "Dale, pausá y probá vos primero.",
                  "Pausá. Pensalo un rato. Acá te espero."]), pad=1.2)

    for idx, s in enumerate(steps):
        lvl = s["level"]
        first = lvl not in seen_levels
        key = lvl >= 2 and first
        seen_levels.add(lvl)
        corta = pick(["Acá vuelvo.", "Acá lo mismo.", "Esto ya sabemos cómo sale.",
                      "Misma táctica.", "Ya lo vimos.", "Otra vez, lo mismo."])
        repeat = (lvl == prev_level)
        prev_level = lvl
        tag = NOMBRE_TACTICA[lvl]

        if idx >= cascade_from:
            if idx == cascade_from:
                frase = pick(["Y ahora... cae todo solo.", "Y ahora, la parte satisfactoria.",
                              "Ahora miren. Cae todo solo."])
                add(1.6, kind="say", caption=frase, tag="Cascada", voz=frase)
            add(0.45, kind="step", tag="Cascada", apply=0.05,
                cat=s["cell"], swept=s["swept"], focus=gcells(s["group"]))
            continue

        if lvl == 1:
            add(1.8 if first else 0.9, kind="step", level=1, tag=tag,
                caption=f"A {gname(s['group'])} le queda un solo lugar." if first else "",
                focus=gcells(s["group"]), apply=0.4, cat=s["cell"], swept=s["swept"],
                voz=f"A {gname(s['group'])} le queda un solo lugar." if first else None)
            continue

        q = None
        if lvl == 2:
            g = s["group"]
            if s["dir"] == "isla->linea":
                q = f"Miren {gname(g)}. ¿Dónde puede estar su gato?"
                lt, lv = s["line"]
                line = f"la fila {lv + 1}" if lt == "fila" else f"la columna {COLS[lv]}"
                exp = f"El gato de {gname(g)} solo puede estar en {line}. Así que {line} es suya: el resto se tacha."
                focus = gcells(g)
                area = gcells(s["line"])
            else:
                q = f"Miren {gname(g)}. ¿En qué isla caen sus lugares libres?"
                isla = gname(s["line"])
                exp = f"Todos caen en {isla}. Su gato está en {gname(g)}: el resto de la isla se tacha."
                focus = gcells(g)
                area = gcells(s["line"])
            body = dict(focus=focus, area=area, cands=s["cands"])
        elif lvl == 3:
            g = s["group"]
            q = f"Miren {gname(g)}. ¿Qué casillas ataca, pase lo que pase?"
            exp = (f"Esté donde esté el gato de {gname(g)}, "
                   f"{'esta casilla queda atacada' if len(s['cells']) == 1 else 'estas casillas quedan atacadas'}. "
                   f"Se tacha{'n' if len(s['cells']) > 1 else ''}.")
            body = dict(focus=gcells(g), cands=s["cands"])
        elif lvl in (4, 5):
            gs = s["groups"]
            k = s["k"]
            into = s["into"]
            tipo_u = {"fila": "filas", "columna": "columnas", "isla": "islas"}[into[0][0]]
            q = f"¿Ven {k} grupos encerrados en solo {k} {tipo_u}?"
            nombres = ", ".join(gname(g) for g in gs[:-1]) + " y " + gname(gs[-1])
            dest = ", ".join(gname(u) for u in into[:-1]) + " y " + gname(into[-1])
            exp = f"{cap(nombres)} solo caben en {dest}. Esos lugares son suyos: lo demás se tacha."
            focus = sorted({c for g in gs for c in gcells(g)})
            area = sorted({c for u in into for c in gcells(u)})
            body = dict(focus=focus, area=area)
        else:  # 6, 7 contradicción
            h = s["hyp"]
            q = f"¿Qué pasaría si ponemos un gato en {cname(h)}?"
            chain = s["chain"]
            cadena = ", ".join(cname(c) for c in chain)
            exp = (f"Si va en {cname(h)}, se fuerza{'n' if len(chain) > 1 else ''} "
                   f"{'gatos' if len(chain) > 1 else 'un gato'} en {cadena}... "
                   f"y {gname(s['empty'])} se queda sin lugar. ¡Imposible! [miau] Entonces {cname(h)} es X.")
            body = dict(hyp=h, chain=chain, empty=gcells(s["empty"]), focus=[h])

        if key:
            add(3.0, kind="question", level=lvl, tag="¿Qué ves?", caption=q,
                sub="Pausá. ¿Qué táctica usarías?", pad=1.8,
                voz=q + " " + pick(["¿Qué ven?", "¿Qué táctica usarían?", "Piénsenlo.", "Los escucho."]), **{k: v for k, v in body.items() if k in ("focus", "area", "cands")})
            dur = 4.5 if lvl >= 6 else 3.5
        else:
            dur = 2.4 if lvl >= 6 else 1.5
        if key:
            voz, caption = exp, exp
        else:
            voz, caption = corta, corta
        add(dur, kind="step", level=lvl, tag=tag, caption=caption, voz=voz,
            x=s["cells"], apply=dur * (0.8 if lvl >= 6 else 0.6), **body)

    cta = CTAS[(numero - 1) % len(CTAS)]
    add(3.0, kind="outro", caption="Cada gato en su isla...\ny cada isla con su gato.",
        sub=cta, voz=f"Cada gato en su isla... y cada isla con su gato. [michi] {cta}")

    for b in beats:
        for k in ("caption", "sub"):
            if b.get(k):
                b[k] = re.sub(r"\[(glitch|risa|miau|michi)\] ?", "", b[k])
    return {
        "n": n, "grid": grid, "numero": numero,
        "colors": [PALETA[k][1] for k in range(n)],
        "stars": ESTRELLAS[maxlevel], "maxlevel": maxlevel,
        "duration": round(t, 3), "beats": beats,
    }


if __name__ == "__main__":
    args = sys.argv[1:]
    out = "video.json"
    numero = 1
    if "-o" in args:
        out = args[args.index("-o") + 1]
    if "--numero" in args:
        numero = int(args[args.index("--numero") + 1])
    grid = parse(open(args[0]).read())
    data = build(grid, numero)
    json.dump(data, open(out, "w"), ensure_ascii=False, indent=1)
    print(f"{out}: {len(data['beats'])} beats, {data['duration']:.1f}s, nivel máx {data['maxlevel']}")
