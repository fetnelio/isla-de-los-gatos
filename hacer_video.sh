#!/usr/bin/env bash
# Genera un tablero, su guion, audio y video.
# Uso: ./hacer_video.sh TAMAÑO NIVEL_TACTICA SEMILLA NUMERO_EPISODIO
#   o: ./hacer_video.sh archivo.txt NUMERO_EPISODIO   (tablero ya existente)
set -euo pipefail
cd "$(dirname "$0")"
mkdir -p salida
if [[ -f "${1:-}" ]]; then
  tab="$1"; num="${2:-1}"; base="salida/$(basename "${tab%.txt}")"
  [[ "$(realpath "$tab")" == "$(realpath -m "$base.txt")" ]] || cp "$tab" "$base.txt"
else
  n="$1"; lvl="$2"; seed="$3"; num="${4:-1}"
  base="salida/n${n}_t${lvl}_s${seed}"
  python3 generador.py "$n" "$lvl" "$seed" > "$base.txt"
fi
python3 guion.py "$base.txt" --numero "$num" -o "$base.json"
python3 voz.py "$base.json"
python3 audio.py "$base.json" "$base.wav"
node render/grabar.js "$base.json" "$base.mp4" "$base.wav"
