"""Ejecutores: simulación (paper) y real (live). Misma interfaz para que el bot no cambie."""
from __future__ import annotations

import logging
from dataclasses import dataclass

from .config import LAMPORTS_PER_SOL, SOL_MINT, Config
from .jupiter import Jupiter
from .portfolio import Portfolio

log = logging.getLogger(__name__)

PAPER_TX_FEE_SOL = 0.0003   # estimación de fee de red + prioridad por transacción en simulación


@dataclass
class Fill:
    ok: bool
    sol: float          # SOL gastados (compra) o recibidos (venta)
    token_raw: int
    signature: str = ""
    error: str = ""


class PaperExecutor:
    mode = "paper"

    def __init__(self, jup: Jupiter, portfolio: Portfolio):
        self.jup = jup
        self.pf = portfolio

    def available_sol(self) -> float:
        return self.pf.state.paper_sol

    def value_sol(self, token: str, raw: int) -> float:
        if raw <= 0:
            return 0.0
        q = self.jup.quote(token, SOL_MINT, raw)
        return q.out_amount / LAMPORTS_PER_SOL

    def buy(self, token: str, sol: float) -> Fill:
        q = self.jup.quote(SOL_MINT, token, int(sol * LAMPORTS_PER_SOL))
        if q.out_amount <= 0:
            return Fill(False, 0, 0, error="cotización vacía")
        spent = sol + PAPER_TX_FEE_SOL
        self.pf.state.paper_sol -= spent
        return Fill(True, spent, q.out_amount, signature="paper")

    def sell(self, token: str, raw: int) -> Fill:
        q = self.jup.quote(token, SOL_MINT, raw)
        got = q.out_amount / LAMPORTS_PER_SOL - PAPER_TX_FEE_SOL
        self.pf.state.paper_sol += got
        return Fill(True, got, raw, signature="paper")

    def held_raw(self, token: str, tracked: int) -> int:
        return tracked


class LiveExecutor:
    mode = "live"

    def __init__(self, jup: Jupiter, cfg: Config):
        from .wallet import Wallet
        self.jup = jup
        self.wallet = Wallet(cfg.solana_private_key, cfg.rpc_url)
        log.warning("MODO REAL activo. Wallet: %s", self.wallet.address)

    def available_sol(self) -> float:
        return self.wallet.sol_balance_lamports() / LAMPORTS_PER_SOL

    def value_sol(self, token: str, raw: int) -> float:
        if raw <= 0:
            return 0.0
        return self.jup.quote(token, SOL_MINT, raw).out_amount / LAMPORTS_PER_SOL

    def held_raw(self, token: str, tracked: int) -> int:
        try:
            return self.wallet.token_balance_raw(token)
        except Exception as e:
            log.warning("No se pudo leer saldo de %s, uso el registrado: %s", token, e)
            return tracked

    def buy(self, token: str, sol: float) -> Fill:
        before = self.available_sol()
        r = self.jup.swap(self.wallet, SOL_MINT, token, int(sol * LAMPORTS_PER_SOL))
        if not r.ok:
            return Fill(False, 0, 0, r.signature, r.error)
        raw = r.out_amount or self.held_raw(token, 0)
        try:
            spent = max(before - self.available_sol(), r.in_amount / LAMPORTS_PER_SOL)
        except Exception:
            spent = r.in_amount / LAMPORTS_PER_SOL
        return Fill(True, spent, raw, r.signature)

    def sell(self, token: str, raw: int) -> Fill:
        r = self.jup.swap(self.wallet, token, SOL_MINT, raw)
        if not r.ok:
            return Fill(False, 0, 0, r.signature, r.error)
        return Fill(True, r.out_amount / LAMPORTS_PER_SOL, r.in_amount or raw, r.signature)
