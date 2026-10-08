# Relógio Despertador

Relógio com despertadores que falam a mensagem com voz natural (pt-BR) e podem ler as principais notícias do dia.
Feito para rodar num computador da casa e ser aberto no iPad (funciona em iPads antigos, iOS 9+).

## Instalar no Mac (uma vez)

```bash
curl -fsSL https://raw.githubusercontent.com/guiavicar/despertador/main/install-mac.sh | bash
```

Isso deixa o site sempre ligado (inclusive depois de reiniciar) e verifica atualizações no GitHub a cada 5 minutos.
Logs em `~/despertador/logs/`.

## Instalar no Linux (uma vez, sem sudo)

```bash
curl -fsSL https://raw.githubusercontent.com/guiavicar/despertador/main/install-linux.sh | bash
```

Usa serviços do systemd do usuário (`despertador.service` e `despertador-update.timer`).
Ver o log: `journalctl --user -u despertador -f`.

## Agenda do Notion

O despertador pode ler os itens de hoje do banco "✅ task" (THE PURSUIT) que ainda não têm check, e avisar quantos estão atrasados.
Ele consulta o Notion na hora em que o alarme toca.

1. Crie uma integração interna em https://www.notion.so/profile/integrations e copie a chave (começa com `ntn_`).
2. No Notion, abra o banco "✅ task" → `•••` → Conexões → adicione a integração.
3. No computador do servidor, crie o arquivo `~/despertador/.env` com a linha `NOTION_TOKEN=sua_chave` e reinicie:
   `systemctl --user restart despertador` (Linux).

O `.env` fica fora do Git, então as atualizações automáticas não apagam a chave.

## Rodar manualmente

Dois cliques em `iniciar.command` (Mac) ou `./iniciar.command`. Abra `http://IP-DO-COMPUTADOR:8000`.

## Desinstalar do Linux

```bash
systemctl --user disable --now despertador.service despertador-update.timer
rm ~/.config/systemd/user/despertador*; rm -rf ~/despertador
```

## Desinstalar do Mac

```bash
launchctl bootout gui/$(id -u)/com.despertador.server; launchctl bootout gui/$(id -u)/com.despertador.update
rm ~/Library/LaunchAgents/com.despertador.*.plist; rm -rf ~/despertador
```
