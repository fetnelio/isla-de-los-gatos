#!/usr/bin/env bash
# Descarga los modelos de voz a ./voces
#   Kokoro (default): GitHub thewh1teagle/kokoro-onnx
#   Piper (opcional): Hugging Face rhasspy/piper-voices  ->  ./descargar_voces.sh --piper
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p voces
K=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
for f in kokoro-v1.0.onnx voices-v1.0.bin; do
  [ -s "voces/$f" ] || curl -sSfL -o "voces/$f" "$K/$f"
done
echo "ok kokoro"
if [[ "${1:-}" == "--piper" ]]; then
  for v in es/es_MX/ald/medium/es_MX-ald-medium es/es_ES/davefx/medium/es_ES-davefx-medium \
           es/es_MX/claude/high/es_MX-claude-high es/es_AR/daniela/high/es_AR-daniela-high; do
    n=$(basename "$v")
    for ext in onnx onnx.json; do
      [ -s "voces/$n.$ext" ] || curl -sSfL -o "voces/$n.$ext" "https://huggingface.co/rhasspy/piper-voices/resolve/main/$v.$ext"
    done
    echo "ok $n"
  done
fi
