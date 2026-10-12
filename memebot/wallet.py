"""Wallet local. La clave privada se lee de tu .env y nunca sale de tu computadora."""
from __future__ import annotations

import base64

from .http import RateLimiter, request_json

_rpc = RateLimiter(120)


class Wallet:
    def __init__(self, private_key_b58: str, rpc_url: str):
        try:
            from solders.keypair import Keypair
        except ImportError as e:  # pragma: no cover
            raise SystemExit("Para operar en real instala solders:  pip install solders") from e
        if not private_key_b58:
            raise SystemExit("Falta SOLANA_PRIVATE_KEY en tu .env")
        self._kp = Keypair.from_base58_string(private_key_b58.strip())
        self.address = str(self._kp.pubkey())
        self.rpc_url = rpc_url

    # --- Firma ---
    def sign_b64(self, tx_b64: str) -> str:
        """Firma parcial: pone nuestra firma en su posición y deja las demás
        (JupiterZ añade la del market maker en /execute)."""
        from solders.message import to_bytes_versioned
        from solders.transaction import VersionedTransaction

        tx = VersionedTransaction.from_bytes(base64.b64decode(tx_b64))
        msg = tx.message
        n = msg.header.num_required_signatures
        signers = list(msg.account_keys[:n])
        me = self._kp.pubkey()
        if me not in signers:
            raise ValueError("La transacción no requiere la firma de esta wallet; no se firma.")
        sigs = list(tx.signatures)
        sigs[signers.index(me)] = self._kp.sign_message(to_bytes_versioned(msg))
        return base64.b64encode(bytes(VersionedTransaction.populate(msg, sigs))).decode()

    # --- Saldos ---
    def _rpc(self, method: str, params: list):
        res = request_json("POST", self.rpc_url, limiter=_rpc,
                           body={"jsonrpc": "2.0", "id": 1, "method": method, "params": params})
        if "error" in (res or {}):
            raise RuntimeError(f"RPC {method}: {res['error']}")
        return res["result"]

    def sol_balance_lamports(self) -> int:
        return int(self._rpc("getBalance", [self.address])["value"])

    def token_balance_raw(self, mint: str) -> int:
        r = self._rpc("getTokenAccountsByOwner",
                      [self.address, {"mint": mint}, {"encoding": "jsonParsed"}])
        total = 0
        for acc in r.get("value", []):
            info = acc["account"]["data"]["parsed"]["info"]
            total += int(info["tokenAmount"]["amount"])
        return total
