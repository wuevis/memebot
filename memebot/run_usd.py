"""Entrada para GitHub Actions: capital en dólares y tamaño por operación según el potencial.

Cada meme coin recibe entre MIN_TRADE_USD y MAX_TRADE_USD (por defecto $20-$100):
las de mayor puntuación de momentum reciben más; las justas, el mínimo.
"""
from __future__ import annotations

import logging
import os

from . import bot as b

log = logging.getLogger("memebot")

MIN_USD = float(os.environ.get("MIN_TRADE_USD", 20))
MAX_USD = float(os.environ.get("MAX_TRADE_USD", 100))
FULL_SCORE = float(os.environ.get("FULL_SIZE_SCORE", 0.85))   # score con el que se mete el máximo
SOL_USD = float(os.environ.get("SOL_USD", 0) or 0)


def size_usd(score: float, min_score: float) -> float:
    frac = (score - min_score) / max(FULL_SCORE - min_score, 1e-6)
    frac = max(0.0, min(1.0, frac))
    return round(MIN_USD + frac * (MAX_USD - MIN_USD), 2)


class SizedBot(b.Bot):
    def buy(self, p, feats):
        if SOL_USD <= 0:
            return super().buy(p, feats)
        usd = size_usd(feats.get("score", 0), self.cfg.min_score)
        free_usd = (self.ex.available_sol() - self.cfg.min_sol_reserve) * SOL_USD
        usd = min(usd, free_usd)
        if usd < MIN_USD:
            log.info("Sin efectivo suficiente para %s (quedan $%.2f).", p.symbol, free_usd)
            return
        feats["size_usd"] = usd
        log.info("Potencial %.2f -> se invierten $%.2f en %s", feats.get("score", 0), usd, p.symbol)
        base = self.cfg.position_size_sol
        self.cfg.position_size_sol = usd / SOL_USD
        try:
            super().buy(p, feats)
        finally:
            self.cfg.position_size_sol = base

    def can_buy(self) -> bool:
        # Para abrir una nueva basta con tener el mínimo por operación libre.
        base = self.cfg.position_size_sol
        if SOL_USD > 0:
            self.cfg.position_size_sol = MIN_USD / SOL_USD
        try:
            return super().can_buy()
        finally:
            self.cfg.position_size_sol = base


b.MAX_DEEP_CHECKS_PER_CYCLE = int(os.environ.get("MAX_DEEP_CHECKS", 10))
b.Bot = SizedBot

if __name__ == "__main__":
    b.main()
