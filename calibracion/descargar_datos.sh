#!/usr/bin/env bash
# Baja los datasets de calibración (solo para uso interno, no publicar sus niveles).
set -euo pipefail
cd "$(dirname "$0")"; mkdir -p datos; cd datos
[ -d queens-game-linkedin ] || git clone --depth 1 https://github.com/samimsu/queens-game-linkedin.git
[ -d queens-without-backtracking ] || git clone --depth 1 https://github.com/mspiegel/queens-without-backtracking.git
