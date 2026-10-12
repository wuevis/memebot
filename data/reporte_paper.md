# Reporte del bot

- Operaciones cerradas: **3**
- Win rate: **33%**
- PnL total: **-0.8738 SOL**
- Ganancia media: +0.1332 SOL
- Pérdida media: -0.5035 SOL
- Profit factor: 0.13
- Tiempo medio en posición: 157 min

### Por motivo de salida
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| liquidez | 1 | 0% | -0.8864 | -99.1% |
| stop | 1 | 0% | -0.1206 | -27.7% |
| trailing | 1 | 100% | +0.1332 | +34.1% |

### Por score de momentum
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0.5–0.6 | 2 | 50% | +0.0126 | +3.2% |
| 0.8–0.9 | 1 | 0% | -0.8864 | -99.1% |

### Por edad del token
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0h–1h | 1 | 0% | -0.8864 | -99.1% |
| 1h–3h | 2 | 50% | +0.0126 | +3.2% |

### Por liquidez (USD)
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 100,000–250,000 | 1 | 0% | -0.1206 | -27.7% |
| 25,000–50,000 | 2 | 50% | -0.7533 | -32.5% |

### Por subida en 1h al entrar
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 15%–30% | 1 | 100% | +0.1332 | +34.1% |
| 30%–60% | 1 | 0% | -0.1206 | -27.7% |
| 60%–100% | 1 | 0% | -0.8864 | -99.1% |

### Por ratio compras/ventas
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 1.6–2.0 | 1 | 0% | -0.1206 | -27.7% |
| 2.0–3.0 | 2 | 50% | -0.7533 | -32.5% |

### Mejores y peores
| token | PnL SOL | salida |
|---|---|---|
| GOMODOGE | +0.1332 | trailing stop (máx 66%, ahora 3%) |
| SEAN | -0.1206 | stop loss -27.6% |
| DOGELON | -0.8864 | liquidez cayó 95% |
| GOMODOGE | +0.1332 | trailing stop (máx 66%, ahora 3%) |
| SEAN | -0.1206 | stop loss -27.6% |
| DOGELON | -0.8864 | liquidez cayó 95% |

## Configuración usada
```json
{
  "dry_run": true,
  "live_confirm": "",
  "rpc_url": "https://api.mainnet-beta.solana.com",
  "data_dir": "data",
  "scan_interval_sec": 20,
  "paper_start_sol": 2.686006,
  "position_size_sol": 0.268601,
  "max_open_positions": 8,
  "max_daily_loss_sol": 0.537201,
  "min_sol_reserve": 0.02686,
  "cooldown_minutes": 720,
  "min_age_minutes": 10,
  "max_age_hours": 48,
  "min_liquidity_usd": 15000,
  "min_mcap_usd": 60000,
  "max_mcap_usd": 8000000,
  "min_volume_h1_usd": 15000,
  "min_buys_h1": 40,
  "min_buy_sell_ratio_h1": 1.15,
  "max_buy_sell_ratio_h1": 4.0,
  "min_change_m5_pct": 0.0,
  "min_change_h1_pct": 8.0,
  "max_change_h1_pct": 150.0,
  "min_liq_to_mcap": 0.05,
  "min_score": 0.4,
  "max_rugcheck_score": 30,
  "max_roundtrip_loss_pct": 6.0,
  "stop_loss_pct": 25.0,
  "take_profit_pct": 60.0,
  "take_profit_sell_fraction": 0.5,
  "trailing_activate_pct": 30.0,
  "trailing_stop_pct": 20.0,
  "max_hold_minutes": 360,
  "liquidity_drop_exit_pct": 50.0
}
```
