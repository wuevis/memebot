"""Aprendizaje: el bot aprende de lo que pasó con cada meme coin que evaluó.

1. Etiqueta: 1-6 h después de evaluar un token, mira su precio real y anota cuánto subió o bajó.
2. Entrena: ajusta una regresión logística que estima la probabilidad de que un token
   suba más de WIN_PCT% (ganancia que cubre comisiones), a partir de sus datos de entrada.
3. El bot usa esa probabilidad para descartar entradas malas y decidir cuánto invertir.
"""
from __future__ import annotations

import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

WIN_PCT = 15.0          # subida que cuenta como "acierto"
MIN_AGE_H, MAX_AGE_H = 1.0, 6.0
MIN_SAMPLES = 60        # con menos ejemplos el modelo no se usa
FEATURES = ["score", "buy_sell_ratio", "change_m5", "change_h1", "change_h6",
            "log_liq", "log_mcap", "log_age", "turnover", "liq_mcap"]


def _f(x, d=0.0):
    try:
        return float(x)
    except (TypeError, ValueError):
        return d


def vectorize(r: dict) -> list[float]:
    liq, mcap, vol = _f(r.get("liquidity_usd")), _f(r.get("mcap_usd")), _f(r.get("volume_h1"))
    clip = lambda v, lo, hi: max(lo, min(hi, v))
    return [
        _f(r.get("score")),
        clip(_f(r.get("buy_sell_ratio"), 1), 0, 6),
        clip(_f(r.get("change_m5")), -50, 100),
        clip(_f(r.get("change_h1")), -90, 500),
        clip(_f(r.get("change_h6")), -95, 2000),
        math.log10(liq + 1),
        math.log10(mcap + 1),
        math.log10(_f(r.get("age_min"), 60) + 1),
        clip(vol / max(liq, 1), 0, 20),
        clip(liq / max(mcap, 1), 0, 1),
    ]


def _ts(s: str) -> float:
    return datetime.fromisoformat(s).timestamp()


# ------------------------------------------------------------------ etiquetado
def label(data_dir: str, mode: str = "paper", max_tokens: int = 150) -> int:
    from .dexscreener import fetch_pairs

    d = Path(data_dir)
    cand, train = d / f"candidates_{mode}.jsonl", d / "training.jsonl"
    if not cand.exists():
        return 0
    done = set()
    if train.exists():
        for line in train.open(encoding="utf-8"):
            try:
                done.add(json.loads(line)["key"])
            except (json.JSONDecodeError, KeyError):
                pass
    now = time.time()
    todo: dict[str, dict] = {}
    for line in cand.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not r.get("price_usd") or not r.get("time"):
            continue
        age_h = (now - _ts(r["time"])) / 3600
        key = f"{r['token']}|{int(_ts(r['time']) // 7200)}"   # 1 ejemplo por token cada 2 h
        if MIN_AGE_H <= age_h <= MAX_AGE_H and key not in done and r["token"] not in todo:
            todo[r["token"]] = {**r, "key": key}
    todo_list = list(todo.values())[:max_tokens]
    if not todo_list:
        return 0
    prices = fetch_pairs([r["token"] for r in todo_list])
    with train.open("a", encoding="utf-8") as f:
        for r in todo_list:
            p = prices.get(r["token"])
            # Sin par/precio: el token murió o perdió la liquidez -> se cuenta como pérdida grande.
            ret = (p.price_usd / r["price_usd"] - 1) * 100 if p and p.price_usd else -90.0
            f.write(json.dumps({"key": r["key"], "token": r["token"], "symbol": r.get("symbol"),
                                "x": vectorize(r), "ret": round(ret, 2),
                                "decision": r.get("decision")}) + "\n")
    return len(todo_list)


# ------------------------------------------------------------------ entrenamiento
def train(data_dir: str, epochs: int = 400, lr: float = 0.1, l2: float = 0.01) -> dict | None:
    d = Path(data_dir)
    path = d / "training.jsonl"
    if not path.exists():
        return None
    X, y = [], []
    for line in path.open(encoding="utf-8"):
        try:
            r = json.loads(line)
        except json.JSONDecodeError:
            continue
        X.append(r["x"])
        y.append(1.0 if r["ret"] >= WIN_PCT else 0.0)
    n = len(X)
    if n < MIN_SAMPLES or sum(y) < 5 or sum(y) > n - 5:
        info = {"ready": False, "n": n, "wins": int(sum(y))}
        (d / "model.json").write_text(json.dumps(info, indent=2))
        return info
    k = len(X[0])
    mu = [sum(r[j] for r in X) / n for j in range(k)]
    sd = [math.sqrt(sum((r[j] - mu[j]) ** 2 for r in X) / n) or 1.0 for j in range(k)]
    Z = [[(r[j] - mu[j]) / sd[j] for j in range(k)] for r in X]
    # Validación: entrena con el 80% más antiguo, prueba con el 20% más reciente.
    cut = int(n * 0.8)
    w, b = _fit(Z[:cut], y[:cut], k, epochs, lr, l2)
    base_rate = sum(y[cut:]) / max(len(y[cut:]), 1)
    top = sorted(zip((_sig(_dot(w, z) + b) for z in Z[cut:]), y[cut:]), reverse=True)
    top_q = top[: max(1, len(top) // 4)]
    top_rate = sum(t[1] for t in top_q) / len(top_q)
    w, b = _fit(Z, y, k, epochs, lr, l2)   # modelo final con todos los datos
    info = {
        "ready": True, "n": n, "wins": int(sum(y)), "win_pct": WIN_PCT,
        "features": FEATURES, "mu": mu, "sd": sd, "w": w, "b": b,
        "base_rate": round(sum(y) / n, 3),
        "test_base_rate": round(base_rate, 3), "test_top25_rate": round(top_rate, 3),
        "useful": top_rate > base_rate * 1.2,   # ¿el 25% mejor puntuado gana claramente más?
        "trained_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }
    (d / "model.json").write_text(json.dumps(info, indent=2))
    return info


def _sig(z):
    return 1 / (1 + math.exp(-max(-30, min(30, z))))


def _dot(a, b):
    return sum(x * y for x, y in zip(a, b))


def _fit(Z, y, k, epochs, lr, l2):
    w, b, n = [0.0] * k, 0.0, len(Z)
    pos = sum(y) or 1
    wpos = (n - pos) / pos           # compensa que los aciertos son pocos
    for _ in range(epochs):
        gw, gb = [0.0] * k, 0.0
        for z, t in zip(Z, y):
            e = (_sig(_dot(w, z) + b) - t) * (wpos if t else 1.0)
            for j in range(k):
                gw[j] += e * z[j]
            gb += e
        w = [w[j] - lr * (gw[j] / n + l2 * w[j]) for j in range(k)]
        b -= lr * gb / n
    return w, b


# ------------------------------------------------------------------ uso
class Model:
    def __init__(self, data_dir: str):
        p = Path(data_dir) / "model.json"
        self.m = json.loads(p.read_text()) if p.exists() else {}

    @property
    def active(self) -> bool:
        return bool(self.m.get("ready") and self.m.get("useful"))

    def prob(self, feats: dict) -> float | None:
        if not self.active:
            return None
        x = vectorize(feats)
        z = [(x[j] - self.m["mu"][j]) / self.m["sd"][j] for j in range(len(x))]
        return _sig(_dot(self.m["w"], z) + self.m["b"])


def main() -> None:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default="data")
    a = ap.parse_args()
    n = label(a.data)
    info = train(a.data)
    msg = f"{datetime.now().strftime('%H:%M:%S')} IA       {n} ejemplos nuevos etiquetados"
    if info:
        msg += f" | total {info['n']} ({info['wins']} subieron +{WIN_PCT:.0f}%)"
        if info.get("ready"):
            msg += (f" | modelo {'ACTIVO' if info['useful'] else 'aún no confiable'}"
                    f" (prueba: top 25% gana {info['test_top25_rate']:.0%} vs {info['test_base_rate']:.0%} promedio)")
        else:
            msg += f" | necesita {MIN_SAMPLES} para entrenar"
    print(msg)
    with (Path(a.data) / "bot.log").open("a", encoding="utf-8") as f:
        f.write(msg + "\n")


if __name__ == "__main__":
    main()
