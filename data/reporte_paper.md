# Reporte del bot

- Operaciones cerradas: **9**
- Win rate: **33%**
- PnL total: **-1.5785 SOL**
- Ganancia media: +0.3605 SOL
- Pérdida media: -0.4433 SOL
- Profit factor: 0.41
- Tiempo medio en posición: 129 min

### Por motivo de salida
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| liquidez | 2 | 0% | -1.6024 | -98.2% |
| stop | 4 | 0% | -1.0576 | -45.8% |
| tiempo | 1 | 100% | +0.1881 | +45.8% |
| trailing | 2 | 100% | +0.8934 | +102.1% |

### Por score de momentum
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0.5–0.6 | 5 | 60% | +0.6079 | +30.3% |
| 0.6–0.7 | 1 | 0% | -0.2250 | -43.0% |
| 0.7–0.8 | 1 | 0% | -0.7160 | -97.3% |
| 0.8–0.9 | 2 | 0% | -1.2455 | -70.6% |

### Por edad del token
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0h–1h | 4 | 25% | -0.7103 | -3.5% |
| 1h–3h | 5 | 40% | -0.8682 | -23.2% |

### Por liquidez (USD)
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 0–25,000 | 3 | 0% | -0.9370 | -51.9% |
| 100,000–250,000 | 1 | 0% | -0.1206 | -27.7% |
| 25,000–50,000 | 5 | 60% | -0.5209 | +10.7% |

### Por subida en 1h al entrar
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 100%–150% | 1 | 100% | +0.7602 | +170.1% |
| 15%–30% | 2 | 50% | -0.5828 | -31.6% |
| 30%–60% | 1 | 0% | -0.1206 | -27.7% |
| 60%–100% | 5 | 20% | -1.6353 | -41.8% |

### Por ratio compras/ventas
| grupo | trades | win rate | PnL SOL | PnL medio % |
|---|---|---|---|---|
| 1.0–1.3 | 1 | 100% | +0.7602 | +170.1% |
| 1.3–1.6 | 3 | 0% | -0.9370 | -51.9% |
| 1.6–2.0 | 3 | 33% | -0.6484 | -26.4% |
| 2.0–3.0 | 2 | 50% | -0.7533 | -32.5% |

### Mejores y peores
| token | PnL SOL | salida |
|---|---|---|
| Eikon | +0.7602 | trailing stop (máx 370%, ahora 208%) |
| FIGHT | +0.1881 | tiempo máximo (361m) |
| GOMODOGE | +0.1332 | trailing stop (máx 66%, ahora 3%) |
| SEAN | -0.1206 | stop loss -27.6% |
| PSI | -0.2250 | stop loss -41.9% |
| PSI | -0.2250 | stop loss -41.9% |
| LURK | -0.3530 | stop loss -70.6% |
| ROAD | -0.3591 | stop loss -41.9% |
| FEED | -0.7160 | liquidez cayó 89% |
| DOGELON | -0.8864 | liquidez cayó 95% |

## Configuración usada
```json
{
  "dry_run": true,
  "live_confirm": "",
  "rpc_url": "https://api.mainnet-beta.solana.com",
  "data_dir": "data",
  "scan_interval_sec": 20,
  "paper_start_sol": 2.805049,
  "position_size_sol": 0.280505,
  "max_open_positions": 8,
  "max_daily_loss_sol": 0.56101,
  "min_sol_reserve": 0.02805,
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
