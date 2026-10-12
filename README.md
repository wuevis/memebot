# MemeBot — bot de momentum para meme coins en Solana

Busca meme coins que ya tienen tracción (unos minutos u horas de vida, volumen y compradores reales).
Descarta las peligrosas y opera con stop-loss, take-profit parcial y trailing stop.
**Arranca en modo simulación**: usa precios reales de Jupiter pero no toca dinero.

> ⚠️ La mayoría de las meme coins terminan en cero o son estafas. Este bot reduce riesgos, pero no
> los elimina, y puede perder todo lo que le des. No es asesoría financiera. Opera solo con dinero que
> puedas perder entero.

## Cómo decide

1. **Descubre** tokens de Solana en DEX Screener: perfiles nuevos, boosts y community takeovers.
2. **Filtra por momentum**. Revisa la edad del par, la liquidez, el market cap, el volumen y las
   compras de la última hora, el ratio compras/ventas y la subida en 5m y 1h. Los tokens que ya
   subieron demasiado quedan fuera.
3. **Puntúa** de 0 a 1. Cuenta la presión compradora, la aceleración de los últimos 5 minutos y la
   rotación del volumen sobre la liquidez.
4. **Chequeo anti-rug** de los 5 mejores:
   - RugCheck: score y riesgos de nivel "danger".
   - Lectura directa en la blockchain: rechaza tokens con *mint authority* o *freeze authority* activa.
   - **Prueba de ida y vuelta**: cotiza comprar y vender al instante. Si se pierde más de 6%, lo
     descarta. Así detecta honeypots, impuestos ocultos y poca liquidez real.
5. **Compra** con Jupiter (mejor precio entre varios routers).
6. **Vigila** cada posición en cada ciclo. Valora la posición con una cotización real de venta, que
   incluye el slippage. Sale según estas reglas:
   - Stop loss: −25%.
   - Take profit parcial: vende 50% al +60%.
   - Trailing stop: se activa al +30% y vende si cae 20% desde el máximo.
   - Salida si la liquidez cae 50% (señal de rug).
   - Salida por tiempo máximo: 6h.

**Protecciones de cuenta:** tamaño fijo por operación, máximo de posiciones abiertas, límite de
pérdida diaria (al llegar, el bot deja de comprar), reserva mínima de SOL para fees y un cooldown
antes de volver a comprar el mismo token.

## Instalación

Necesitas Python 3.10 o superior.

```bash
cd memebot
cp .env.example .env          # en Windows: copy .env.example .env
```

El modo simulación **no necesita instalar nada más**. Para el modo real:

```bash
pip install -r requirements.txt
```

Una API key gratis de Jupiter es recomendable: https://developers.jup.ag/portal

## 1) Simulación (empieza aquí)

```bash
python -m memebot            # corre en bucle; Ctrl+C para detenerlo
python -m memebot --once     # un solo ciclo, útil para probar
```

Todo se guarda en `data/`:
- `trades_paper.csv`: cada compra y venta con sus datos.
- `candidates_paper.jsonl`: cada token evaluado y por qué se compró o rechazó.
- `state_paper.json`: posiciones y saldo simulado.
- `bot.log`: el registro completo.

Déjalo correr **varios días** para tener al menos unas 30 operaciones cerradas antes de sacar
conclusiones.

## 2) Perfeccionarlo juntos

```bash
python -m memebot.analyze --followup
```

Esto genera `data/reporte_paper.md` con:
- Win rate, PnL y profit factor.
- Resultados por motivo de salida, score, edad, liquidez, subida previa y ratio compras/ventas.
- **Seguimiento de rechazados**: cuánto subieron después los tokens que el bot descartó, para saber
  si algún filtro es demasiado estricto.
- La configuración usada (sin claves).

**Pégame ese reporte en el chat** y te digo qué parámetros cambiar en tu `.env`, o modifico el código.
Repite el ciclo: correr, analizar, ajustar.

## 3) Pasar a real (solo si la simulación es rentable de forma consistente)

1. Crea una **wallet nueva** solo para el bot (por ejemplo en Phantom) y deposita poco.
2. Exporta su clave privada y pégala en `.env` como `SOLANA_PRIVATE_KEY`. **Nunca la compartas con
   nadie, ni conmigo, ni en ningún chat.**
3. Usa un RPC propio en `RPC_URL`. Helius o QuickNode tienen planes gratis.
4. Verifica la wallet. Este comando firma una orden de prueba **sin enviarla**:
   ```bash
   python -m memebot --check-wallet
   ```
5. Activa el modo real en `.env`:
   ```
   DRY_RUN=false
   LIVE_CONFIRM=SI_ENTIENDO_EL_RIESGO
   ```
6. Empieza con `POSITION_SIZE_SOL` pequeño.

Botón de pánico, para vender todo de inmediato:

```bash
python -m memebot --sell-all
```

## Pruebas

```bash
python -m unittest discover tests
```

## Estructura

| Archivo | Qué hace |
|---|---|
| `memebot/config.py` | Todos los parámetros (se cambian desde `.env`) |
| `memebot/dexscreener.py` | Descubrimiento de tokens y datos de mercado |
| `memebot/safety.py` | RugCheck y chequeo de mint/freeze authority |
| `memebot/strategy.py` | Filtros, score y reglas de salida (aquí se ajusta la estrategia) |
| `memebot/jupiter.py` | Cotizaciones y swaps (Jupiter Swap API v2) |
| `memebot/wallet.py` | Firma local y lectura de saldos |
| `memebot/executor.py` | Ejecutor simulado y real con la misma interfaz |
| `memebot/portfolio.py` | Estado, límites de riesgo y registros |
| `memebot/bot.py` | Bucle principal |
| `memebot/analyze.py` | Reporte de rendimiento |
