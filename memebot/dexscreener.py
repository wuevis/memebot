"""Descubrimiento de tokens y datos de mercado usando la API pública de DEX Screener."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import SOL_MINT
from .http import RateLimiter, request_json

log = logging.getLogger(__name__)

BASE = "https://api.dexscreener.com"
_slow = RateLimiter(55)    # endpoints de perfiles/boosts: 60 req/min
_fast = RateLimiter(250)   # endpoints de pares/tokens: 300 req/min

DISCOVERY_ENDPOINTS = [
    "/token-profiles/latest/v1",
    "/token-boosts/latest/v1",
    "/token-boosts/top/v1",
    "/community-takeovers/latest/v1",
]


@dataclass
class PairInfo:
    token: str
    symbol: str
    name: str
    pair_address: str
    dex_id: str
    quote_mint: str
    price_usd: float
    liquidity_usd: float
    mcap_usd: float
    volume_h1: float
    volume_m5: float
    buys_h1: int
    sells_h1: int
    buys_m5: int
    sells_m5: int
    change_m5: float
    change_h1: float
    change_h6: float
    created_at_ms: int | None
    url: str

    @classmethod
    def from_api(cls, p: dict) -> "PairInfo":
        tx = p.get("txns") or {}
        vol = p.get("volume") or {}
        chg = p.get("priceChange") or {}
        liq = p.get("liquidity") or {}

        def f(x, default=0.0):
            try:
                return float(x) if x is not None else default
            except (TypeError, ValueError):
                return default

        return cls(
            token=p["baseToken"]["address"],
            symbol=p["baseToken"].get("symbol") or "?",
            name=p["baseToken"].get("name") or "",
            pair_address=p.get("pairAddress", ""),
            dex_id=p.get("dexId", ""),
            quote_mint=(p.get("quoteToken") or {}).get("address") or "",
            price_usd=f(p.get("priceUsd")),
            liquidity_usd=f(liq.get("usd")),
            mcap_usd=f(p.get("marketCap") or p.get("fdv")),
            volume_h1=f(vol.get("h1")),
            volume_m5=f(vol.get("m5")),
            buys_h1=int((tx.get("h1") or {}).get("buys") or 0),
            sells_h1=int((tx.get("h1") or {}).get("sells") or 0),
            buys_m5=int((tx.get("m5") or {}).get("buys") or 0),
            sells_m5=int((tx.get("m5") or {}).get("sells") or 0),
            change_m5=f(chg.get("m5")),
            change_h1=f(chg.get("h1")),
            change_h6=f(chg.get("h6")),
            created_at_ms=p.get("pairCreatedAt"),
            url=p.get("url", ""),
        )


def discover_candidate_tokens() -> list[str]:
    """Direcciones de tokens de Solana que aparecen en perfiles/boosts recientes."""
    seen: dict[str, None] = {}
    for path in DISCOVERY_ENDPOINTS:
        try:
            data = request_json("GET", BASE + path, limiter=_slow)
        except Exception as e:  # una fuente caída no debe parar el bot
            log.warning("Descubrimiento falló en %s: %s", path, e)
            continue
        items = data if isinstance(data, list) else (data or {}).get("data", []) if isinstance(data, dict) else []
        for it in items:
            if it.get("chainId") == "solana" and it.get("tokenAddress"):
                seen.setdefault(it["tokenAddress"], None)
    return list(seen)


def best_sol_pair(pairs: list[dict]) -> dict | None:
    """Elige el par contra SOL con más liquidez."""
    sol_pairs = [p for p in pairs
                 if p.get("chainId") == "solana"
                 and (p.get("quoteToken") or {}).get("address") == SOL_MINT]
    if not sol_pairs:
        return None
    return max(sol_pairs, key=lambda p: (p.get("liquidity") or {}).get("usd") or 0)


def fetch_pairs(tokens: list[str]) -> dict[str, PairInfo]:
    """Datos del mejor par SOL para cada token (lotes de 30)."""
    out: dict[str, PairInfo] = {}
    for i in range(0, len(tokens), 30):
        chunk = tokens[i:i + 30]
        try:
            data = request_json("GET", f"{BASE}/tokens/v1/solana/{','.join(chunk)}", limiter=_fast)
        except Exception as e:
            log.warning("No se pudieron leer pares: %s", e)
            continue
        by_token: dict[str, list[dict]] = {}
        for p in data or []:
            addr = (p.get("baseToken") or {}).get("address")
            if addr:
                by_token.setdefault(addr, []).append(p)
        for addr, plist in by_token.items():
            best = best_sol_pair(plist)
            if best:
                try:
                    out[addr] = PairInfo.from_api(best)
                except (KeyError, TypeError) as e:
                    log.debug("Par mal formado para %s: %s", addr, e)
    return out
