"""Configuración del bot. Todo se puede cambiar desde el archivo .env."""
from __future__ import annotations

import os
from dataclasses import dataclass, field, fields
from pathlib import Path

SOL_MINT = "So11111111111111111111111111111111111111112"
LAMPORTS_PER_SOL = 1_000_000_000


def load_dotenv(path: str | Path = ".env") -> None:
    """Lector mínimo de .env (sin dependencias). No sobreescribe variables ya definidas."""
    p = Path(path)
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        value = value.strip().strip('"').strip("'")
        os.environ.setdefault(key.strip(), value)


@dataclass
class Config:
    # --- Modo de operación ---
    dry_run: bool = True                 # True = simulación (no toca dinero)
    live_confirm: str = ""               # Debe ser "SI_ENTIENDO_EL_RIESGO" para operar en real
    jupiter_api_key: str = ""
    solana_private_key: str = ""         # base58. SOLO en tu .env local. Nunca la compartas.
    rpc_url: str = "https://api.mainnet-beta.solana.com"  # mejor usar un RPC propio (Helius, QuickNode...)
    data_dir: str = "data"

    # --- Ciclo ---
    scan_interval_sec: int = 30
    paper_start_sol: float = 1.0         # saldo inicial de la simulación

    # --- Gestión de riesgo ---
    position_size_sol: float = 0.05      # SOL por operación
    max_open_positions: int = 3
    max_daily_loss_sol: float = 0.15     # si se pierde esto en el día, el bot deja de comprar
    min_sol_reserve: float = 0.02        # SOL que nunca se gasta (para fees)
    cooldown_minutes: int = 120          # no recomprar el mismo token en este tiempo

    # --- Filtros de entrada (momentum) ---
    min_age_minutes: float = 20
    max_age_hours: float = 48
    min_liquidity_usd: float = 20_000
    min_mcap_usd: float = 60_000
    max_mcap_usd: float = 8_000_000
    min_volume_h1_usd: float = 25_000
    min_buys_h1: int = 60
    min_buy_sell_ratio_h1: float = 1.15
    max_buy_sell_ratio_h1: float = 4.0   # demasiadas compras sin ventas suele ser honeypot/bots
    min_change_m5_pct: float = 0.0
    min_change_h1_pct: float = 8.0
    max_change_h1_pct: float = 150.0     # evita entrar en velas ya sobreextendidas
    min_liq_to_mcap: float = 0.05
    min_score: float = 0.45              # puntuación mínima de momentum (0-1)

    # --- Seguridad del token ---
    max_rugcheck_score: float = 30       # score_normalised de RugCheck (más bajo = más seguro)
    max_roundtrip_loss_pct: float = 6.0  # comprar y vender al instante no debe costar más que esto
                                         # (incluye fees, impacto de precio e impuestos ocultos)

    # --- Salidas ---
    stop_loss_pct: float = 25.0
    take_profit_pct: float = 60.0        # vende una parte aquí
    take_profit_sell_fraction: float = 0.5
    trailing_activate_pct: float = 30.0  # el trailing se activa al llegar a esta ganancia
    trailing_stop_pct: float = 20.0      # cae este % desde el máximo -> vende
    max_hold_minutes: float = 360
    liquidity_drop_exit_pct: float = 50.0  # si la liquidez cae esto desde la entrada -> vende todo

    @property
    def is_live(self) -> bool:
        return (not self.dry_run) and self.live_confirm == "SI_ENTIENDO_EL_RIESGO"

    @classmethod
    def from_env(cls, env_file: str | Path = ".env") -> "Config":
        load_dotenv(env_file)
        cfg = cls()
        for f in fields(cls):
            raw = os.environ.get(f.name.upper())
            if raw is None or raw == "":
                continue
            default = getattr(cfg, f.name)
            if isinstance(default, bool):
                val = raw.strip().lower() in ("1", "true", "yes", "si", "sí")
            elif isinstance(default, int):
                val = int(float(raw))
            elif isinstance(default, float):
                val = float(raw)
            else:
                val = raw
            setattr(cfg, f.name, val)
        return cfg

    def public_dict(self) -> dict:
        """Configuración sin secretos, para logs y reportes."""
        d = {f.name: getattr(self, f.name) for f in fields(self)}
        d.pop("solana_private_key", None)
        d.pop("jupiter_api_key", None)
        return d
