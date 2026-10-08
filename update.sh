#!/bin/bash
# Roda a cada 5 min no iMac (launchd): baixa código novo do GitHub e reinicia o site se mudou.
cd "$(dirname "$0")" || exit 1
git fetch -q origin main || exit 0
[ "$(git rev-parse HEAD)" = "$(git rev-parse origin/main)" ] && exit 0
OLD_REQ=$(git rev-parse HEAD:requirements.txt 2>/dev/null)
git reset -q --hard origin/main
echo "$(date '+%F %T') atualizado para $(git log -1 --format='%h %s')"
if [ "$OLD_REQ" != "$(git rev-parse HEAD:requirements.txt)" ]; then
  if command -v uv >/dev/null; then uv pip install -q --python .venv/bin/python -r requirements.txt
  else .venv/bin/pip install -q -r requirements.txt; fi
fi
if [ "$(uname)" = "Darwin" ]; then launchctl kickstart -k "gui/$(id -u)/com.despertador.server"
else systemctl --user restart despertador.service; fi
