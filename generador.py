"""
Generador de tableros resolubles por tácticas.

1. Elige una solución (N gatos, uno por fila/columna, sin tocarse).
2. Cada gato es semilla de su isla; las islas crecen de forma compacta.
3. Búsqueda local: mueve casillas de borde entre islas vecinas hasta que el
   solver por tácticas (con tope `nivel`) lo resuelva usando el nivel objetivo.

Uso: python3 generador.py N NIVEL [semilla] [--min-isla K]
"""
import random
import sys
import json
from solver import solve

D4 = ((1, 0), (-1, 0), (0, 1), (0, -1))


def random_solution(n, rng):
    while True:
        cols, used = [], set()

        def bt(r):
            if r == n:
                return True
            opts = [c for c in range(n) if c not in used and (r == 0 or abs(cols[-1] - c) > 1)]
            rng.shuffle(opts)
            for c in opts:
                cols.append(c); used.add(c)
                if bt(r + 1):
                    return True
                cols.pop(); used.discard(c)
            return False

        if bt(0):
            return cols


def grow(n, sol, rng):
    g = [[-1] * n for _ in range(n)]
    for r, c in enumerate(sol):
        g[r][c] = r
    left = n * n - n
    # pesos de crecimiento distintos por isla -> tamaños variados
    weight = [rng.uniform(0.5, 2.0) for _ in range(n)]
    while left:
        frontier = []
        for r in range(n):
            for c in range(n):
                if g[r][c] != -1:
                    continue
                nb = {}
                for dr, dc in D4:
                    rr, cc = r + dr, c + dc
                    if 0 <= rr < n and 0 <= cc < n and g[rr][cc] != -1:
                        nb[g[rr][cc]] = nb.get(g[rr][cc], 0) + 1
                for k, cnt in nb.items():
                    # cnt alto = más compacto
                    frontier.append(((r, c), k, weight[k] * cnt ** 2))
        tot = sum(w for _, _, w in frontier)
        x = rng.uniform(0, tot)
        for (r, c), k, w in frontier:
            x -= w
            if x <= 0:
                break
        g[r][c] = k
        left -= 1
    return g


def connected(g, k, n, without):
    cells = [(r, c) for r in range(n) for c in range(n) if g[r][c] == k and (r, c) != without]
    if not cells:
        return False
    seen = {cells[0]}
    st = [cells[0]]
    cs = set(cells)
    while st:
        r, c = st.pop()
        for dr, dc in D4:
            p = (r + dr, c + dc)
            if p in cs and p not in seen:
                seen.add(p); st.append(p)
    return len(seen) == len(cells)


def sizes(g, n):
    s = [0] * n
    for row in g:
        for k in row:
            s[k] += 1
    return s


def perimeter(g, n):
    p = 0
    for r in range(n):
        for c in range(n):
            for dr, dc in ((1, 0), (0, 1)):
                rr, cc = r + dr, c + dc
                if rr < n and cc < n and g[rr][cc] != g[r][c]:
                    p += 1
    return p


def score(g, n, nivel):
    res = solve(g, maxlevel=nivel)
    if not res["solved"]:
        s = res["progress"]
    else:
        lv = res["levels"]
        s = 1.0 + (1.0 if res["maxlevel"] == nivel else res["maxlevel"] / 10)
        s += 0.02 * sum(1 for x in lv if x == nivel)   # más usos del nivel objetivo
        s += 0.002 * sum(x * x for x in lv)
    s -= 0.004 * perimeter(g, n)  # compacidad (islas "naturales")
    s -= 0.003 * sum((x - n) ** 2 for x in sizes(g, n)) / n  # tamaños parejos
    return s, res


def mutate(g, n, seeds, min_isla, rng):
    sz = sizes(g, n)
    for _ in range(200):
        r, c = rng.randrange(n), rng.randrange(n)
        if (r, c) in seeds:
            continue
        k = g[r][c]
        nbs = {g[r + dr][c + dc] for dr, dc in D4
               if 0 <= r + dr < n and 0 <= c + dc < n and g[r + dr][c + dc] != k}
        if not nbs or sz[k] <= min_isla:
            continue
        if not connected(g, k, n, (r, c)):
            continue
        h = [row[:] for row in g]
        h[r][c] = rng.choice(sorted(nbs))
        return h
    return None


def generate(n, nivel, seed=None, min_isla=None, iters=3000, restarts=20, log=False):
    rng = random.Random(seed)
    if min_isla is None:
        min_isla = 1 if nivel <= 2 else 3
    for rs in range(restarts):
        sol = random_solution(n, rng)
        seeds = {(r, c) for r, c in enumerate(sol)}
        g = grow(n, sol, rng)
        if min(sizes(g, n)) < min_isla:
            continue
        cur, res = score(g, n, nivel)
        T = 0.05
        for it in range(iters):
            if res["solved"] and res["maxlevel"] == nivel:
                if log:
                    print(f"  ok reinicio={rs} iter={it}", file=sys.stderr)
                return {"grid": g, "solution": sol, "nivel": nivel, "seed": seed,
                        "levels": res["levels"]}
            h = mutate(g, n, seeds, min_isla, rng)
            if h is None:
                break
            s, r2 = score(h, n, nivel)
            if s >= cur or rng.random() < pow(2.718, (s - cur) / T):
                g, cur, res = h, s, r2
            T = max(0.002, T * 0.998)
        if log:
            print(f"  reinicio {rs}: sin éxito (prog={res['progress']:.2f}, max={res['maxlevel']})",
                  file=sys.stderr)
    return None


def to_text(g):
    abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
    return "\n".join("".join(abc[k] for k in row) for row in g)


if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    n, nivel = int(args[0]), int(args[1])
    seed = int(args[2]) if len(args) > 2 else None
    mi = None
    if "--min-isla" in sys.argv:
        mi = int(sys.argv[sys.argv.index("--min-isla") + 1])
    out = generate(n, nivel, seed, mi, log=True)
    if not out:
        sys.exit("No se encontró tablero")
    print(to_text(out["grid"]))
    print("niveles usados:", out["levels"], file=sys.stderr)
