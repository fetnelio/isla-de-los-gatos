#!/usr/bin/env bash
# Descarga las voces de Piper (Hugging Face: rhasspy/piper-voices) a ./voces
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p voces
for v in es/es_AR/daniela/high/es_AR-daniela-high es/es_MX/claude/high/es_MX-claude-high \
         es/es_MX/ald/medium/es_MX-ald-medium es/es_ES/davefx/medium/es_ES-davefx-medium; do
  n=$(basename "$v")
  for ext in onnx onnx.json; do
    [ -s "voces/$n.$ext" ] || curl -sSfL -o "voces/$n.$ext" "https://huggingface.co/rhasspy/piper-voices/resolve/main/$v.$ext"
  done
  echo "ok $n"
done
