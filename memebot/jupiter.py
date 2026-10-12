"""Cotizaciones y swaps con Jupiter Swap API v2 (/order + /execute)."""
from __future__ import annotations

import base64
import logging
from dataclasses import dataclass

from .http import HttpError, RateLimiter, request_json

log = logging.getLogger(__name__)

BASE = "https://api.jup.ag/swap/v2"
_limiter = RateLimiter(50)


@dataclass
class Quote:
    in_amount: int
    out_amount: int
    price_impact_pct: float
    router: str
    fee_bps: int
    request_id: str = ""
    transaction: str | None = None


@dataclass
class SwapResult:
    ok: bool
    signature: str
    in_amount: int
    out_amount: int
    error: str = ""


class Jupiter:
    def __init__(self, api_key: str = ""):
        self.headers = {"x-api-key": api_key} if api_key else {}

    def order(self, input_mint: str, output_mint: str, amount: int, taker: str | None = None) -> Quote:
        params = {"inputMint": input_mint, "outputMint": output_mint,
                  "amount": str(int(amount)), "taker": taker}
        d = request_json("GET", f"{BASE}/order", params=params, headers=self.headers, limiter=_limiter)
        if taker and d.get("transaction") == "":
            raise RuntimeError(f"Jupiter no pudo armar la transacción [{d.get('router')}] "
                               f"{d.get('errorCode')}: {d.get('errorMessage')}")
        # Solo informativo: el filtro real de costo es la prueba de ida y vuelta (ver strategy.py).
        try:
            impact = abs(float(d.get("priceImpactPct", d.get("priceImpact", 0)) or 0))
        except (TypeError, ValueError):
            impact = 0.0
        return Quote(
            in_amount=int(d.get("inAmount") or amount),
            out_amount=int(d.get("outAmount") or 0),
            price_impact_pct=impact,
            router=d.get("router", ""),
            fee_bps=int(d.get("feeBps") or 0),
            request_id=d.get("requestId", ""),
            transaction=d.get("transaction"),
        )

    def quote(self, input_mint: str, output_mint: str, amount: int) -> Quote:
        """Solo precio (sin taker): sirve para simulación y para valorar posiciones."""
        return self.order(input_mint, output_mint, amount, taker=None)

    def swap(self, wallet, input_mint: str, output_mint: str, amount: int) -> SwapResult:
        """Swap real: pide la orden, firma localmente y la ejecuta. `wallet` es memebot.wallet.Wallet."""
        q = self.order(input_mint, output_mint, amount, taker=wallet.address)
        if not q.transaction:
            return SwapResult(False, "", amount, 0, "orden sin transacción")
        signed_b64 = wallet.sign_b64(q.transaction)
        try:
            r = request_json("POST", f"{BASE}/execute", headers=self.headers, limiter=_limiter,
                             body={"signedTransaction": signed_b64, "requestId": q.request_id},
                             retries=1, timeout=60)
        except HttpError as e:
            return SwapResult(False, "", amount, 0, str(e))
        ok = r.get("status") == "Success"
        return SwapResult(
            ok=ok,
            signature=r.get("signature", ""),
            in_amount=int(r.get("totalInputAmount") or r.get("inputAmountResult") or 0),
            out_amount=int(r.get("totalOutputAmount") or r.get("outputAmountResult") or 0),
            error="" if ok else f"code {r.get('code')}: {r.get('error', '')}",
        )
