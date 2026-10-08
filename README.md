# Relógio Despertador

Relógio com despertadores que falam a mensagem com voz natural (pt-BR) e podem ler as principais notícias do dia.
Feito para rodar num computador da casa e ser aberto no iPad (funciona em iPads antigos, iOS 9+).

## Instalar no Mac (uma vez)

```bash
curl -fsSL https://raw.githubusercontent.com/guiavicar/despertador/main/install-mac.sh | bash
```

Isso deixa o site sempre ligado (inclusive depois de reiniciar) e verifica atualizações no GitHub a cada 5 minutos.
Logs em `~/despertador/logs/`.

## Rodar manualmente

Dois cliques em `iniciar.command` (Mac) ou `./iniciar.command`. Abra `http://IP-DO-COMPUTADOR:8000`.

## Desinstalar do Mac

```bash
launchctl bootout gui/$(id -u)/com.despertador.server; launchctl bootout gui/$(id -u)/com.despertador.update
rm ~/Library/LaunchAgents/com.despertador.*.plist; rm -rf ~/despertador
```
