"""End-to-end test of both fetchers (headless Chromium and requests) against a local web server that
serves the sample pages the way Wiktionary does (/wiki/<title>?action=raw, 404 for missing pages).

Run from the project folder:  python -m tests.test_fetchers_local
"""
import threading
import urllib.parse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import crawler.wiktionary_crawler as wc
from tests.test_crawler import PAGES


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = urllib.parse.urlparse(self.path)
        title = urllib.parse.unquote(url.path.removeprefix("/wiki/")).replace("_", " ")
        body = PAGES.get(title)
        self.send_response(200 if body else 404)
        self.send_header("Content-Type", "text/x-wiki; charset=UTF-8")
        self.end_headers()
        self.wfile.write((body or "").encode("utf-8"))

    def log_message(self, *args):
        pass


def run():
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    wc.BASE = f"http://127.0.0.1:{server.server_port}/wiki/"
    try:
        for backend in (wc.RequestsFetcher, wc.PlaywrightFetcher):
            fetcher = backend(wc.DEFAULT_UA, delay=0)
            try:
                status, chain = wc.crawl_word("harpoon", fetcher)
                assert status == "ok", status
                assert [c["term"] for c in chain] == ["harpon", "harpon", "harper", "*harpā"], chain
                assert fetcher.fetch("no such page") is None
                print(f"passed: {backend.__name__} -> harpoon <- " + " <- ".join(
                    f"{c['lang']}:{c['term']}" for c in chain))
            finally:
                fetcher.close()
    finally:
        server.shutdown()


if __name__ == "__main__":
    run()
