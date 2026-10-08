#!/bin/bash
# Instala o Relógio Despertador no Linux (sem sudo): site sempre ligado + atualização automática pelo GitHub.
# Uso:  curl -fsSL https://raw.githubusercontent.com/guiavicar/despertador/main/install-linux.sh | bash
set -e
REPO="https://github.com/guiavicar/despertador.git"
DIR="$HOME/despertador"
UNITS="$HOME/.config/systemd/user"
export PATH="$HOME/.local/bin:$PATH"

command -v git >/dev/null || { echo "Instale o git:  sudo apt install git"; exit 1; }
# uv cria o ambiente Python sem precisar do pacote python3-venv (que exige sudo)
command -v uv >/dev/null || curl -LsSf https://astral.sh/uv/install.sh | sh

if [ -d "$DIR/.git" ]; then git -C "$DIR" pull -q; else git clone -q "$REPO" "$DIR"; fi
cd "$DIR"
mkdir -p logs "$UNITS"
echo "Instalando as vozes naturais..."
[ -x .venv/bin/python ] || uv venv -q .venv
uv pip install -q --python .venv/bin/python -r requirements.txt
chmod +x update.sh iniciar.command

cat > "$UNITS/despertador.service" <<UNIT
[Unit]
Description=Relógio Despertador
After=network-online.target

[Service]
WorkingDirectory=$DIR
ExecStart=$DIR/.venv/bin/python $DIR/server.py
Restart=always
RestartSec=5

[Install]
WantedBy=default.target
UNIT

cat > "$UNITS/despertador-update.service" <<UNIT
[Unit]
Description=Atualiza o Relógio Despertador pelo GitHub

[Service]
Type=oneshot
Environment=PATH=$HOME/.local/bin:/usr/local/bin:/usr/bin:/bin
ExecStart=/bin/bash $DIR/update.sh
UNIT

cat > "$UNITS/despertador-update.timer" <<UNIT
[Unit]
Description=Verifica atualizações do Relógio Despertador a cada 5 minutos

[Timer]
OnBootSec=1min
OnUnitActiveSec=5min

[Install]
WantedBy=timers.target
UNIT

systemctl --user daemon-reload
systemctl --user enable -q --now despertador.service despertador-update.timer
systemctl --user restart despertador.service
# mantém rodando mesmo sem ninguém logado (pode pedir senha se ainda não estiver ativo)
[ "$(loginctl show-user "$USER" -p Linger --value)" = "yes" ] || loginctl enable-linger "$USER" || true

IP=$(hostname -I | awk '{print $1}')
echo ""
echo "Pronto! O Relógio Despertador está rodando e se atualiza sozinho a cada 5 minutos."
echo "No iPad, abra:  http://$IP:8000"
