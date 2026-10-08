#!/bin/bash
# Instala o Relógio Despertador no Mac: site sempre ligado + atualização automática pelo GitHub.
# Uso (no Terminal do iMac):
#   curl -fsSL https://raw.githubusercontent.com/guiavicar/despertador/main/install-mac.sh | bash
set -e
REPO="https://github.com/guiavicar/despertador.git"
DIR="$HOME/despertador"
AGENTS="$HOME/Library/LaunchAgents"

if ! xcode-select -p >/dev/null 2>&1; then
  echo "Falta instalar as Ferramentas de Linha de Comando da Apple (git e python)."
  echo "Vai abrir uma janela: clique em Instalar e, quando terminar, rode este comando de novo."
  xcode-select --install || true
  exit 1
fi

if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q "$REPO" "$DIR"; fi
cd "$DIR"
mkdir -p logs "$AGENTS"
echo "Instalando as vozes naturais..."
[ -x .venv/bin/python ] || python3 -m venv .venv
.venv/bin/pip install -q --upgrade pip >/dev/null 2>&1 || true
.venv/bin/pip install -q -r requirements.txt
chmod +x update.sh iniciar.command

cat > "$AGENTS/com.despertador.server.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.despertador.server</string>
  <key>ProgramArguments</key><array><string>$DIR/.venv/bin/python</string><string>$DIR/server.py</string></array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>StandardOutPath</key><string>$DIR/logs/server.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/server.log</string>
</dict></plist>
PLIST

cat > "$AGENTS/com.despertador.update.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.despertador.update</string>
  <key>ProgramArguments</key><array><string>/bin/bash</string><string>$DIR/update.sh</string></array>
  <key>StartInterval</key><integer>300</integer>
  <key>RunAtLoad</key><true/>
  <key>StandardOutPath</key><string>$DIR/logs/update.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/update.log</string>
</dict></plist>
PLIST

for s in server update; do
  launchctl bootout "gui/$(id -u)/com.despertador.$s" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$AGENTS/com.despertador.$s.plist"
done

IP=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "IP-DO-IMAC")
echo ""
echo "Pronto! O Relógio Despertador está rodando e se atualiza sozinho a cada 5 minutos."
echo "No iPad, abra:  http://$IP:8000"
echo "(Se o Mac perguntar se o Python pode aceitar conexões de rede, clique em Permitir.)"
