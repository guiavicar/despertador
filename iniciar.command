#!/bin/bash
# Inicia o Relógio Despertador. No Mac, dá para abrir com dois cliques.
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ] || ! .venv/bin/python -c "import edge_tts" 2>/dev/null; then
  echo "Primeira vez: instalando as vozes naturais..."
  rm -rf .venv
  python3 -m venv .venv && .venv/bin/pip install -q edge-tts || exit 1
fi
IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || hostname -I 2>/dev/null | awk '{print $1}')
echo "No iPad, abra:  http://$IP:8000"
exec .venv/bin/python server.py
