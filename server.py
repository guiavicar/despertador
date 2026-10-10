"""Servidor do Relógio Despertador.

Serve o site e gera a fala com vozes neurais (edge-tts), devolvendo MP3.
Uso:  .venv/bin/python server.py   (porta 8000)
"""
import asyncio
import hashlib
import json
import os
import re
import datetime
import time
import urllib.request
import xml.etree.ElementTree as ET
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import edge_tts

ROOT = os.path.dirname(os.path.abspath(__file__))
CACHE = os.path.join(ROOT, "cache")
PORT = int(os.environ.get("PORT", "8000"))
VOICES = {"pt-BR-FranciscaNeural", "pt-BR-AntonioNeural", "pt-BR-ThalitaMultilingualNeural"}
NEWS_URL = "https://news.google.com/rss?hl=pt-BR&gl=BR&ceid=BR:pt-419"
NEWS_COUNT = 5
STARTED = str(int(time.time()))  # muda a cada reinício (ou seja, a cada atualização)
# Agenda do Notion: banco "✅ task" (THE PURSUIT). A chave fica em .env (fora do Git): NOTION_TOKEN=ntn_...
NOTION_DATA_SOURCE = "db75f277-731f-42be-a8c4-4037b8c8a40b"
UPCOMING_COUNT = 3  # quantas próximas tarefas citar
os.makedirs(CACHE, exist_ok=True)


def synthesize(text, voice):
    key = hashlib.sha1((voice + "|" + text).encode()).hexdigest()
    path = os.path.join(CACHE, key + ".mp3")
    if not os.path.exists(path):
        tmp = path + ".tmp"
        asyncio.run(edge_tts.Communicate(text, voice, rate="-5%").save(tmp))
        os.replace(tmp, path)
    return path


_news = {"at": 0, "text": ""}


def news_text():
    """Principais manchetes do Google Notícias Brasil, prontas para serem lidas (cache de 15 min)."""
    if time.time() - _news["at"] < 15 * 60:
        return _news["text"]
    req = urllib.request.Request(NEWS_URL, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=15) as r:
        root = ET.fromstring(r.read())
    titles = []
    for item in root.iter("item"):
        title = re.sub(r"\s+-\s+[^-]+$", "", item.findtext("title") or "").strip()  # tira " - Fonte"
        if title:
            titles.append(title.rstrip(".") + ".")
        if len(titles) == NEWS_COUNT:
            break
    text = "Agora, as principais notícias do dia. " + " ".join(
        f"{n}: {t}" for n, t in zip(["Primeira", "Segunda", "Terceira", "Quarta", "Quinta", "Sexta"], titles)
    ) + " Essas foram as notícias. Tenha um ótimo dia!"
    _news.update(at=time.time(), text=text)
    return text


def notion_token():
    if os.environ.get("NOTION_TOKEN"):
        return os.environ["NOTION_TOKEN"]
    try:
        with open(os.path.join(ROOT, ".env")) as f:
            for line in f:
                k, _, v = line.strip().partition("=")
                if k == "NOTION_TOKEN":
                    return v.strip().strip('"')
    except FileNotFoundError:
        pass
    return None


def notion_query(token, filt, sorts=None, page_size=100):
    req = urllib.request.Request(
        f"https://api.notion.com/v1/data_sources/{NOTION_DATA_SOURCE}/query",
        data=json.dumps({"filter": filt, "page_size": page_size,
                         **({"sorts": sorts} if sorts else {})}).encode(),
        headers={"Authorization": f"Bearer {token}", "Notion-Version": "2025-09-03",
                 "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as r:
        return json.load(r)["results"]


def task_info(page):
    props = page["properties"]
    title = "".join(t["plain_text"] for t in props["Name"]["title"]).strip() or "sem nome"
    start = ((props["Data"].get("date") or {}).get("start")) or ""
    hour = start[11:16] if len(start) > 10 else ""  # "2026-10-08T14:30:00..." -> "14:30"
    prio = ((props.get("Prioridade") or {}).get("select") or {}).get("name", "")
    return hour, title, prio


WEEKDAYS = ["segunda-feira", "terça-feira", "quarta-feira", "quinta-feira", "sexta-feira", "sábado", "domingo"]
MONTHS = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
          "setembro", "outubro", "novembro", "dezembro"]


def when_day(day, today):
    """'amanhã', 'na sexta-feira, dia 16' (até 6 dias) ou 'dia 21 de outubro'."""
    diff = (day - today).days
    if diff == 1:
        return "amanhã"
    if diff < 7:
        wd = WEEKDAYS[day.weekday()]
        return f"{'no' if day.weekday() >= 5 else 'na'} {wd}, dia {day.day}"
    return f"dia {day.day} de {MONTHS[day.month - 1]}"


def spoken_hour(hour):
    h, _, m = hour.partition(":")
    return f"{int(h)} horas" + (f" e {int(m)}" if int(m) else "")


def agenda_text():
    """Compromissos de hoje e os próximos (não concluídos). Consulta o Notion na hora."""
    token = notion_token()
    if not token:
        raise RuntimeError("Falta a chave do Notion (NOTION_TOKEN no arquivo .env)")
    today = datetime.date.today()
    tomorrow = today + datetime.timedelta(days=1)
    pending = {"property": "check", "checkbox": {"equals": False}}
    todays = notion_query(token, {"and": [
        pending,
        {"property": "Data", "date": {"on_or_after": today.isoformat()}},
        {"property": "Data", "date": {"before": tomorrow.isoformat()}}]})
    upcoming = notion_query(token, {"and": [
        pending, {"property": "Data", "date": {"on_or_after": tomorrow.isoformat()}}]},
        sorts=[{"property": "Data", "direction": "ascending"}], page_size=UPCOMING_COUNT)

    items = sorted(task_info(p) for p in todays)  # com horário primeiro, em ordem
    items.sort(key=lambda i: (i[0] == "", i[0]))
    if not items:
        text = "Você não tem compromissos marcados para hoje na sua agenda."
    else:
        n = len(items)
        parts = []
        for hour, title, prio in items:
            when = f"às {spoken_hour(hour)}, " if hour else ""
            urgent = ", prioridade alta" if prio in ("ALTA", "MÁXIMA") else ""
            parts.append(f"{when}{title}{urgent}.")
        text = (f"Você tem {n} compromisso{'s' if n > 1 else ''} hoje. " if n > 1
                else "Você tem um compromisso hoje. ") + " ".join(parts)
    if upcoming:
        nexts = []
        for p in upcoming:
            hour, title, _ = task_info(p)
            day = datetime.date.fromisoformat(p["properties"]["Data"]["date"]["start"][:10])
            nexts.append(f"{when_day(day, today)}{' às ' + spoken_hour(hour) if hour else ''}, {title}")
        text += " Próximos compromissos: " + "; ".join(nexts) + "."
    return text


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/version":
            body = STARTED.encode()
            self.send_response(200)
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if url.path in ("/news", "/agenda"):
            try:
                body = json.dumps({"text": news_text() if url.path == "/news" else agenda_text()}).encode()
            except Exception as e:
                return self.send_error(502, str(e))
            self.send_response(200)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            return self.wfile.write(body)
        if url.path != "/tts":
            if url.path.startswith(("/.venv", "/cache", "/server.py")):
                return self.send_error(404)
            return super().do_GET()
        q = parse_qs(url.query)
        text = (q.get("text") or [""])[0].strip()[:3000]
        voice = (q.get("voice") or ["pt-BR-FranciscaNeural"])[0]
        if not text or voice not in VOICES:
            return self.send_error(400)
        try:
            path = synthesize(text, voice)
        except Exception as e:  # sem internet, etc.
            return self.send_error(502, str(e))
        with open(path, "rb") as f:
            data = f.read()
        # o Safari do iPad pede o áudio em pedaços (Range) e exige resposta 206
        rng = self.headers.get("Range", "")
        if rng.startswith("bytes="):
            start_s, _, end_s = rng[6:].partition("-")
            start = int(start_s or 0)
            end = min(int(end_s) if end_s else len(data) - 1, len(data) - 1)
            self.send_response(206)
            self.send_header("Content-Range", f"bytes {start}-{end}/{len(data)}")
            data = data[start:end + 1]
        else:
            self.send_response(200)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", "audio/mpeg")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "max-age=31536000")
        self.end_headers()
        self.wfile.write(data)


if __name__ == "__main__":
    print(f"Relógio Despertador em http://localhost:{PORT}")
    ThreadingHTTPServer(("0.0.0.0", PORT), Handler).serve_forever()
