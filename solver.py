"""
Solver explicador por tácticas.

Aplica siempre la táctica de menor nivel disponible y registra cada paso con
su evidencia (qué grupo, qué casillas, por qué), para poder narrarlo.

Niveles:
  1 único candidato       (grupo con una sola casilla libre -> gato)
  2 encierro simple       (isla en una línea / línea en una isla)
  3 ataque común          (todas las candidatas de un grupo atacan una casilla)
  4 encierro k=2
  5 encierro k>=3
  6 contradicción en cadena (supongo gato, se fuerzan gatos (nivel 1), un grupo queda vacío)
  7 contradicción larga   (igual, pero propagando con niveles 1..5)
El "barrido" (nivel 0) va incluido en cada gato colocado.
"""
from itertools import combinations

NOMBRE_TACTICA = {
    1: "Único lugar",
    2: "Encierro en una línea",
    3: "Ataque común",
    4: "Encierro doble",
    5: "Encierro múltiple",
    6: "¿Y si...? (contradicción)",
    7: "¿Y si...? (contradicción larga)",
}


def bits(m):
    out = []
    while m:
        low = m & -m
        out.append(low.bit_length() - 1)
        m ^= low
    return out


def popcount(m):
    return bin(m).count("1")


class Board:
    """Geometría fija del tablero: grupos y ataques precomputados como bitmasks."""

    def __init__(self, grid):
        self.grid = grid
        self.n = n = len(grid)
        self.groups = []  # (tipo, indice, mask)
        self.row = [0] * n
        self.col = [0] * n
        self.isl = [0] * n
        for r in range(n):
            for c in range(n):
                b = 1 << (r * n + c)
                self.row[r] |= b
                self.col[c] |= b
                self.isl[grid[r][c]] |= b
        for i in range(n):
            self.groups.append(("fila", i, self.row[i]))
        for i in range(n):
            self.groups.append(("columna", i, self.col[i]))
        for i in range(n):
            self.groups.append(("isla", i, self.isl[i]))
        self.attack = []
        for r in range(n):
            for c in range(n):
                m = self.row[r] | self.col[c] | self.isl[grid[r][c]]
                for dr in (-1, 0, 1):
                    for dc in (-1, 0, 1):
                        rr, cc = r + dr, c + dc
                        if 0 <= rr < n and 0 <= cc < n:
                            m |= 1 << (rr * n + cc)
                m &= ~(1 << (r * n + c))
                self.attack.append(m)
        self.full = (1 << (n * n)) - 1

    def rc(self, i):
        return divmod(i, self.n)


class State:
    __slots__ = ("cand", "cats")

    def __init__(self, cand, cats):
        self.cand = cand
        self.cats = cats

    def copy(self):
        return State(self.cand, self.cats)


def place(B, S, i):
    """Coloca gato en i, devuelve las casillas tachadas por el barrido."""
    removed = S.cand & B.attack[i]
    S.cats |= 1 << i
    S.cand &= ~B.attack[i]
    S.cand &= ~(1 << i)
    return removed


def open_groups(B, S):
    return [g for g in B.groups if not (g[2] & S.cats)]


def empty_group(B, S):
    for g in B.groups:
        if not (g[2] & S.cats) and not (g[2] & S.cand):
            return g
    return None


# ---------------------------------------------------------------- tácticas

def t_single(B, S):
    # preferimos islas (más narrable), luego filas y columnas
    for g in sorted(open_groups(B, S), key=lambda g: g[0] != "isla"):
        m = g[2] & S.cand
        if m and not (m & (m - 1)):
            i = m.bit_length() - 1
            return {"level": 1, "kind": "cat", "cell": i, "group": g[:2]}
    return None


def t_line(B, S):
    n = B.n
    for g in open_groups(B, S):
        if g[0] != "isla":
            continue
        cs = bits(g[2] & S.cand)
        rows = {c // n for c in cs}
        cols = {c % n for c in cs}
        for kind, vals, masks in (("fila", rows, B.row), ("columna", cols, B.col)):
            if len(vals) == 1:
                v = next(iter(vals))
                elim = masks[v] & S.cand & ~g[2]
                if elim:
                    return {"level": 2, "kind": "x", "cells": bits(elim),
                            "group": g[:2], "line": (kind, v), "dir": "isla->linea",
                            "cands": cs}
    for g in open_groups(B, S):
        if g[0] == "isla":
            continue
        cs = bits(g[2] & S.cand)
        isl = {B.grid[c // n][c % n] for c in cs}
        if len(isl) == 1:
            k = next(iter(isl))
            elim = B.isl[k] & S.cand & ~g[2]
            if elim:
                return {"level": 2, "kind": "x", "cells": bits(elim),
                        "group": g[:2], "line": ("isla", k), "dir": "linea->isla",
                        "cands": cs}
    return None


def t_common(B, S):
    gs = []
    for g in open_groups(B, S):
        m = g[2] & S.cand
        if m:
            gs.append((popcount(m), g, m))
    gs.sort(key=lambda x: (x[0], x[1][0] != "isla"))
    for k, g, m in gs:
        common = B.full
        for c in bits(m):
            common &= B.attack[c]
        elim = common & S.cand
        if elim:
            return {"level": 3, "kind": "x", "cells": bits(elim), "group": g[:2],
                    "cands": bits(m), "k": k}
    return None


def t_confine(B, S, kmin, kmax, level):
    n = B.n
    types = ("isla", "fila", "columna")
    for k in range(kmin, kmax + 1):
        for T in types:
            gT = [g for g in open_groups(B, S) if g[0] == T]
            if len(gT) <= k:
                continue
            for U in types:
                if U == T:
                    continue
                masksU = {"fila": B.row, "columna": B.col, "isla": B.isl}[U]

                def u_of(c):
                    r, cc = divmod(c, n)
                    return {"fila": r, "columna": cc, "isla": B.grid[r][cc]}[U]

                gidx = []
                for g in gT:
                    us = {u_of(c) for c in bits(g[2] & S.cand)}
                    if len(us) <= k:
                        gidx.append((g, us))
                for combo in combinations(gidx, k):
                    us = set().union(*(x[1] for x in combo))
                    if len(us) != k:
                        continue
                    inner = 0
                    for g, _ in combo:
                        inner |= g[2]
                    outer = 0
                    for u in us:
                        outer |= masksU[u]
                    elim = outer & S.cand & ~inner
                    if elim:
                        return {"level": level, "kind": "x", "cells": bits(elim),
                                "groups": [g[:2] for g, _ in combo],
                                "into": [(U, u) for u in sorted(us)], "k": k}
    return None


def t_confine2(B, S):
    return t_confine(B, S, 2, 2, 4)


def t_confineK(B, S):
    return t_confine(B, S, 3, max(3, B.n // 2), 5)


def propagate(B, S, maxlevel):
    """Aplica tácticas hasta maxlevel (sin contradicción). Devuelve (cadena de gatos, grupo vacío o None)."""
    chain = []
    while True:
        g = empty_group(B, S)
        if g:
            return chain, g
        if S.cats.bit_count() == B.n:
            return chain, None
        step = None
        for lvl, f in TACTICS:
            if lvl > maxlevel:
                break
            step = f(B, S)
            if step:
                break
        if not step:
            return chain, None
        if step["kind"] == "cat":
            place(B, S, step["cell"])
            chain.append(step["cell"])
        else:
            for c in step["cells"]:
                S.cand &= ~(1 << c)


def t_contra(B, S, level, inner):
    best = None
    for x in bits(S.cand):
        T = S.copy()
        place(B, T, x)
        chain, g = propagate(B, T, inner)
        if g and chain and (best is None or len(chain) < len(best[1])):
            best = (x, chain, g)
            if len(chain) == 1:
                break
    if best:
        x, chain, g = best
        return {"level": level, "kind": "x", "cells": [x], "hyp": x,
                "chain": chain, "empty": g[:2]}
    return None


def t_contra6(B, S):
    return t_contra(B, S, 6, 1)


def t_contra7(B, S):
    return t_contra(B, S, 7, 5)


TACTICS = [(1, t_single), (2, t_line), (3, t_common), (4, t_confine2),
           (5, t_confineK), (6, t_contra6), (7, t_contra7)]


def solve(grid, maxlevel=7):
    """Devuelve dict con pasos, si se resolvió, y estadísticas."""
    B = Board(grid)
    S = State(B.full, 0)
    steps = []
    while S.cats.bit_count() < B.n:
        if empty_group(B, S):
            return {"solved": False, "steps": steps, "broken": True}
        step = None
        for lvl, f in TACTICS:
            if lvl > maxlevel:
                break
            step = f(B, S)
            if step:
                break
        if not step:
            break
        if step["kind"] == "cat":
            step["swept"] = bits(place(B, S, step["cell"]))
        else:
            for c in step["cells"]:
                S.cand &= ~(1 << c)
        steps.append(step)
    solved = S.cats.bit_count() == B.n
    decided = B.n * B.n - popcount(S.cand)
    levels = [s["level"] for s in steps]
    return {
        "solved": solved,
        "steps": steps,
        "progress": decided / (B.n * B.n),
        "maxlevel": max(levels) if levels else 0,
        "levels": levels,
        "cats": bits(S.cats),
    }


def parse(text):
    rows = [l.strip().replace(" ", "") for l in text.splitlines() if l.strip()]
    labels = sorted({ch for r in rows for ch in r})
    idx = {ch: k for k, ch in enumerate(labels)}
    return [[idx[ch] for ch in r] for r in rows]


if __name__ == "__main__":
    import sys
    from collections import Counter
    for path in sys.argv[1:]:
        res = solve(parse(open(path).read()))
        c = Counter(res["levels"])
        print(f"{path}: resuelto={res['solved']} nivel máx={res['maxlevel']} "
              f"pasos={len(res['steps'])} uso={dict(sorted(c.items()))}")
