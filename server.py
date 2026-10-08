"""Servidor do Relógio Despertador.

Serve o site e gera a fala com vozes neurais (edge-tts), devolvendo MP3.
Uso:  .venv/bin/python server.py   (porta 8000)
"""
import asyncio
import hashlib
import json
import os
import re
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


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=ROOT, **kwargs)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == "/news":
            try:
                body = json.dumps({"text": news_text()}).encode()
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
