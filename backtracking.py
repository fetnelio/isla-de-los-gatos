#!/usr/bin/env python3
"""
Solver de Cool Cat Cove.

Reglas: tablero N×N dividido en N islas. Hay que poner N gatos:
  - uno por fila, uno por columna, uno por isla;
  - dos gatos nunca se tocan (tampoco en diagonal).

Entrada: N líneas de N caracteres; cada carácter identifica una isla
(letras, dígitos, lo que quieras). Espacios y líneas vacías se ignoran.

Uso:
  python3 coolcat_solver.py tablero.txt
  cat tablero.txt | python3 coolcat_solver.py
"""
import sys


def parse(text):
    rows = [l.replace(" ", "").replace("\t", "") for l in text.splitlines()]
    rows = [r for r in rows if r]
    n = len(rows)
    if n == 0:
        raise ValueError("Tablero vacío")
    for i, r in enumerate(rows):
        if len(r) != n:
            raise ValueError(f"La fila {i + 1} tiene {len(r)} casillas, se esperaban {n}")
    labels = sorted({ch for r in rows for ch in r})
    if len(labels) != n:
        raise ValueError(f"Hay {len(labels)} islas pero el tablero es {n}×{n}")
    idx = {ch: k for k, ch in enumerate(labels)}
    return [[idx[ch] for ch in r] for r in rows], labels


def solve(grid, max_solutions=2):
    """Devuelve hasta max_solutions soluciones; cada una es lista col[fila]."""
    n = len(grid)
    # cells[k] = casillas de la isla k
    cells = [[] for _ in range(n)]
    for r in range(n):
        for c in range(n):
            cells[grid[r][c]].append((r, c))

    solutions = []
    cat_col = [-1] * n            # columna del gato en cada fila
    blocked = [[0] * n for _ in range(n)]  # contador de bloqueos por casilla
    used_row = [False] * n
    used_col = [False] * n
    used_reg = [False] * n

    def neighbours_and_lines(r, c):
        for cc in range(n):
            yield r, cc
        for rr in range(n):
            yield rr, c
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                rr, cc = r + dr, c + dc
                if 0 <= rr < n and 0 <= cc < n:
                    yield rr, cc

    def place(r, c, delta):
        for rr, cc in neighbours_and_lines(r, c):
            blocked[rr][cc] += delta

    def free(r, c):
        return blocked[r][c] == 0

    def search():
        if len(solutions) >= max_solutions:
            return
        # Elegir la restricción (fila, columna o isla) con menos candidatos (MRV)
        best = None
        for k in range(n):
            if not used_reg[k]:
                cand = [(r, c) for r, c in cells[k] if free(r, c)]
                if best is None or len(cand) < len(best):
                    best = cand
                    if len(best) <= 1:
                        break
        if best is None:  # todas las islas tienen gato
            solutions.append(cat_col[:])
            return
        if len(best) > 1:
            for r in range(n):
                if not used_row[r]:
                    cand = [(r, c) for c in range(n) if free(r, c)]
                    if len(cand) < len(best):
                        best = cand
            for c in range(n):
                if not used_col[c]:
                    cand = [(r, c) for r in range(n) if free(r, c)]
                    if len(cand) < len(best):
                        best = cand
        for r, c in best:
            k = grid[r][c]
            used_row[r] = used_col[c] = used_reg[k] = True
            cat_col[r] = c
            place(r, c, +1)
            search()
            place(r, c, -1)
            cat_col[r] = -1
            used_row[r] = used_col[c] = used_reg[k] = False
            if len(solutions) >= max_solutions:
                return

    search()
    return solutions


def render(grid, labels, sol):
    n = len(grid)
    out = []
    for r in range(n):
        line = []
        for c in range(n):
            line.append("🐱" if sol[r] == c else f" {labels[grid[r][c]]}")
        out.append(" ".join(line))
    return "\n".join(out)


def main():
    text = open(sys.argv[1]).read() if len(sys.argv) > 1 else sys.stdin.read()
    try:
        grid, labels = parse(text)
    except ValueError as e:
        sys.exit(f"Error: {e}")
    sols = solve(grid)
    if not sols:
        print("Sin solución.")
        return
    sol = sols[0]
    print(render(grid, labels, sol))
    print()
    print("Gatos (fila, columna) 1-indexado:")
    print("  " + "  ".join(f"({r + 1},{c + 1})" for r, c in enumerate(sol)))
    print()
    print("Solución única ✅" if len(sols) == 1 else "⚠️  Hay más de una solución")


if __name__ == "__main__":
    main()
