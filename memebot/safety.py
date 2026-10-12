"""Chequeos anti-rug: RugCheck + lectura directa de la cuenta mint en la blockchain."""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

from .http import RateLimiter, request_json

log = logging.getLogger(__name__)

RUGCHECK = "https://api.rugcheck.xyz/v1/tokens/{mint}/report/summary"
_rc_limiter = RateLimiter(40)
_rpc_limiter = RateLimiter(120)


@dataclass
class SafetyReport:
    ok: bool
    reasons: list[str] = field(default_factory=list)
    rugcheck_score: float | None = None
    lp_locked_pct: float | None = None


def check_mint_authorities(mint: str, rpc_url: str) -> list[str]:
    """Un token con mint authority puede imprimir más; con freeze authority puede congelar tu saldo."""
    body = {"jsonrpc": "2.0", "id": 1, "method": "getAccountInfo",
            "params": [mint, {"encoding": "jsonParsed"}]}
    res = request_json("POST", rpc_url, body=body, limiter=_rpc_limiter)
    value = ((res or {}).get("result") or {}).get("value")
    if not value:
        return ["cuenta mint no encontrada"]
    info = ((value.get("data") or {}).get("parsed") or {}).get("info") or {}
    problems = []
    if info.get("mintAuthority"):
        problems.append("mint authority activa")
    if info.get("freezeAuthority"):
        problems.append("freeze authority activa")
    return problems


def evaluate_rugcheck(summary: dict, max_score: float) -> SafetyReport:
    reasons = []
    score = summary.get("score_normalised")
    if summary.get("error"):
        reasons.append(f"rugcheck error: {summary['error']}")
    if score is not None and score > max_score:
        reasons.append(f"rugcheck score {score} > {max_score}")
    for r in summary.get("risks") or []:
        if (r.get("level") or "").lower() == "danger":
            reasons.append(f"riesgo: {r.get('name')}")
    return SafetyReport(ok=not reasons, reasons=reasons, rugcheck_score=score,
                        lp_locked_pct=summary.get("lpLockedPct"))


def check_token(mint: str, rpc_url: str, max_rugcheck_score: float) -> SafetyReport:
    try:
        summary = request_json("GET", RUGCHECK.format(mint=mint), limiter=_rc_limiter)
        report = evaluate_rugcheck(summary or {}, max_rugcheck_score)
    except Exception as e:
        # Sin datos de seguridad no se compra.
        return SafetyReport(ok=False, reasons=[f"rugcheck no disponible: {e}"])
    try:
        auth = check_mint_authorities(mint, rpc_url)
    except Exception as e:
        auth = [f"RPC no disponible: {e}"]
    if auth:
        report.reasons.extend(auth)
        report.ok = False
    return report
