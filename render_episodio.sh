#!/usr/bin/env bash
# Renderiza reel + story de un episodio ya elegido (episodios/epN.txt).
# Uso: ./render_episodio.sh N        |  en lote: xargs -P 3 -n 1 ./render_episodio.sh < lote/pendientes.txt
set -euo pipefail
cd "$(dirname "$0")"
n="$1"
mkdir -p salida docs/videos docs/stories
tab="episodios/ep$n.txt"

# reel (solución completa)
b="salida/ep$n"
python3 guion.py "$tab" --numero "$n" -o "$b.json" > /dev/null
python3 voz.py "$b.json" > /dev/null
python3 audio.py "$b.json" "$b.wav" > /dev/null
node render/grabar.js "$b.json" "$b.mp4" "$b.wav" > /dev/null 2>&1

# story (desafío)
s="salida/ep${n}_story"
python3 guion.py "$tab" --numero "$n" --story -o "$s.json" > /dev/null
python3 voz.py "$s.json" > /dev/null
python3 audio.py "$s.json" "$s.wav" > /dev/null
node render/grabar.js "$s.json" "$s.mp4" "$s.wav" > /dev/null 2>&1

# recién con los dos completos se mueven al sitio
mv "$b.mp4" "docs/videos/ep$n.mp4"
mv "$s.mp4" "docs/stories/ep$n.mp4"

dur=$(python3 -c "import json;print(round(json.load(open('$b.json'))['duration']))")
echo "ep$n listo (reel ${dur}s)"
