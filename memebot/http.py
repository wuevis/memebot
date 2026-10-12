"""Cliente HTTP mínimo con reintentos y limitador de velocidad (solo librería estándar)."""
from __future__ import annotations

import json
import logging
import threading
import time
import urllib.error
import urllib.parse
import urllib.request

log = logging.getLogger(__name__)


class HttpError(Exception):
    def __init__(self, status: int, body: str, url: str):
        super().__init__(f"HTTP {status} en {url}: {body[:300]}")
        self.status = status
        self.body = body


class RateLimiter:
    def __init__(self, per_minute: int):
        self.min_interval = 60.0 / per_minute
        self._last = 0.0
        self._lock = threading.Lock()

    def wait(self) -> None:
        with self._lock:
            now = time.monotonic()
            delay = self._last + self.min_interval - now
            if delay > 0:
                time.sleep(delay)
            self._last = time.monotonic()


def request_json(method: str, url: str, *, params: dict | None = None, body: dict | None = None,
                 headers: dict | None = None, limiter: RateLimiter | None = None,
                 retries: int = 3, timeout: float = 15.0):
    if params:
        url = f"{url}?{urllib.parse.urlencode({k: v for k, v in params.items() if v is not None})}"
    data = json.dumps(body).encode() if body is not None else None
    hdrs = {"Accept": "application/json", "User-Agent": "memebot/1.0"}
    if data is not None:
        hdrs["Content-Type"] = "application/json"
    hdrs.update(headers or {})

    last_exc: Exception | None = None
    for attempt in range(retries):
        if limiter:
            limiter.wait()
        req = urllib.request.Request(url, data=data, headers=hdrs, method=method)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else None
        except urllib.error.HTTPError as e:
            text = e.read().decode("utf-8", errors="replace")
            last_exc = HttpError(e.code, text, url)
            # 429 / 5xx -> reintentar con espera; 4xx -> no tiene sentido reintentar
            if e.code == 429 or e.code >= 500:
                time.sleep(1.5 * (attempt + 1) ** 2)
                continue
            raise last_exc
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            last_exc = e
            time.sleep(1.5 * (attempt + 1))
    assert last_exc is not None
    raise last_exc
