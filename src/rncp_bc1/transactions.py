"""Contrat transactionnel PaySim, indépendant des moteurs de stockage."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
import hashlib
import re
from typing import Mapping, Any

from rncp_bc1.dataset import TYPES, DECIMAL_FIELDS, EXCLUDED_FEATURES

MONEY_LIMIT = Decimal("9999999999999999.99")
ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]{1,80}$")


def parse_utc(value: str) -> datetime:
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset() != timedelta(0):
        raise ValueError("Un horodatage UTC explicite est requis.")
    return parsed


def money(value: str) -> str:
    try:
        number = Decimal(value)
        if not number.is_finite() or number < 0 or number > MONEY_LIMIT:
            raise ValueError("Montant hors limites Decimal(18,2).")
        if number != number.quantize(Decimal("0.01")):
            raise ValueError("Plus de deux décimales significatives.")
        return format(number.quantize(Decimal("0.01")), ".2f")
    except InvalidOperation as error:
        raise ValueError("Montant décimal invalide.") from error


@dataclass(frozen=True)
class ReplayContext:
    dataset_sha256: str
    run_id: str
    epoch_utc: str = "2000-01-01T00:00:00+00:00"

    def __post_init__(self):
        if not re.fullmatch(r"[0-9a-f]{64}", self.dataset_sha256):
            raise ValueError("Empreinte SHA-256 invalide.")
        if not ID_PATTERN.fullmatch(self.run_id):
            raise ValueError("run_id : 1–80 lettres, chiffres, tirets ou underscores.")
        parse_utc(self.epoch_utc)


def envelope(row: Mapping[str, str], source_row: int, context: ReplayContext,
             emitted_at: str | None = None) -> dict[str, Any]:
    if not isinstance(source_row, int) or isinstance(source_row, bool) or source_row < 1:
        raise ValueError("source_row doit être strictement positif.")
    try:
        raw_step = row["step"]
        if not raw_step.isascii() or not raw_step.isdigit() or int(raw_step) < 1:
            raise ValueError("step entier positif requis.")
        step = int(raw_step)
        if row["type"] not in TYPES:
            raise ValueError("Type de transaction inconnu.")
        for key in ["nameOrig", "nameDest"]:
            if not row[key] or len(row[key]) > 128 or not row[key].isascii() or not row[key].isalnum():
                raise ValueError(f"Identifiant de compte invalide : {key}.")
        payload: dict[str, Any] = {"step": step, "type": row["type"],
                                   "nameOrig": row["nameOrig"], "nameDest": row["nameDest"]}
        for key in DECIMAL_FIELDS:
            payload[key] = money(row[key])
        for key in ["isFraud", "isFlaggedFraud"]:
            if row[key] not in {"0", "1"}:
                raise ValueError(f"Label binaire invalide : {key}.")
            payload[key] = int(row[key])
        event_time = parse_utc(context.epoch_utc) + timedelta(hours=step - 1)
    except (KeyError, TypeError, OverflowError) as error:
        raise ValueError("Transaction incomplète ou hors limites temporelles.") from error
    emitted = parse_utc(emitted_at) if emitted_at else datetime.now(timezone.utc)
    identity = hashlib.sha256(f"{context.dataset_sha256}:{source_row}".encode()).hexdigest()
    return {"schema_version": 1, "dataset_id": f"paysim-v2:{context.dataset_sha256}",
            "source_row": source_row, "transaction_id": identity, "replay_run_id": context.run_id,
            "event_time": event_time.isoformat(), "event_time_synthetic": True,
            "emitted_at": emitted.isoformat(), "payload": payload}


def predictive_values(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Liste positive : aucun solde, label, ni identifiant de compte comme prédicteur."""
    values = {key: payload[key] for key in ["step", "type", "amount"]}
    assert not set(values).intersection(EXCLUDED_FEATURES)
    return values
