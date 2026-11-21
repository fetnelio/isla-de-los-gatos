import glob, re, sys, json, collections, os
os.chdir(os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos"))
import os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from solver import solve
from backtracking import solve as bt

# --- oficiales: estadísticas de Spiegel
dist = collections.Counter(); bysize = collections.defaultdict(collections.Counter)
for f in glob.glob("queens-without-backtracking/solutions/*.txt"):
    txt = open(f).read()
    n = sum(1 for l in txt.splitlines() if l and set(l) <= set(".♛"))
    st = dict((k.strip(), int(v)) for k, v in re.findall(r"^(.+?):\s*(\d+)$", txt, re.M))
    poly = sum(v for k, v in st.items() if k.startswith("polyomino"))
    if st.get("Placement-forces-contradiction"): lv = "6 contradicción"
    elif st.get("N-regions-in-N-lines"): lv = "4-5 encierro k≥2"
    elif poly: lv = "3 ataque común"
    elif st.get("Region-confined-to-line") or st.get("Line-confined-to-region"): lv = "2 encierro línea"
    else: lv = "1 único lugar"
    dist[lv] += 1; bysize[n][lv] += 1
print("OFICIALES LinkedIn (667), táctica máxima necesaria:")
for k in sorted(dist): print(f"  {k:20} {dist[k]:4}  {100*dist[k]/sum(dist.values()):.0f}%")
print("  tamaños:", dict(sorted((n, sum(c.values())) for n, c in bysize.items())))

# --- comunitarios: nuestro solver
res = collections.Counter(); multi = 0; stuck = []; sizes = collections.Counter(); recs = []
for f in glob.glob("queens-game-linkedin/src/utils/community-levels/level*.ts"):
    txt = open(f).read()
    rows = re.findall(r"\[((?:\s*\"[A-Z]\",?\s*)+)\]", txt)
    grid = [re.findall(r"\"([A-Z])\"", r) for r in rows]
    n = len(grid)
    if not n or any(len(r) != n for r in grid): continue
    labels = sorted({c for r in grid for c in r})
    if len(labels) != n: continue
    g = [[labels.index(c) for c in r] for r in grid]
    if len(bt(g, 2)) != 1: multi += 1; continue
    r = solve(g); sizes[n] += 1
    if not r["solved"]: stuck.append(f); res["sin resolver"] += 1; continue
    res[r["maxlevel"]] += 1
    recs.append({"file": f.split("/")[-1], "n": n, "max": r["maxlevel"], "levels": r["levels"]})
print("\nCOMUNITARIOS (únicos):", sum(sizes.values()), " descartados por solución múltiple:", multi)
for k in sorted(res, key=str): print(f"  nivel {k}: {res[k]}")
print("  tamaños:", dict(sorted(sizes.items())))
json.dump(recs, open(os.path.join(os.path.dirname(__file__), "calibracion_comunitarios.json"), "w"))
