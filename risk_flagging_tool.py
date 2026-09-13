"""
risk_flagging_tool.py

A small rules engine that reads a client dataset (CSV or Excel), evaluates
each account against a set of risk rules, and writes back a Red/Amber/Green
status plus a human-readable reason for that status.

Supports a JSON "exceptions" file so specific rules can be waived for
specific clients (e.g. after a manual review or a client request), each with
its own reason and an optional expiry date, so overrides don't linger
silently.

This is a portfolio/demo project built on fully synthetic data — see
generate_sample_data.py. It is not connected to any real client system.

Usage:
    python risk_flagging_tool.py \
        --input data/clients.csv \
        --exceptions data/exceptions.json \
        --output output/clients_flagged.xlsx
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from typing import Callable

import numpy as np
import pandas as pd

RAG_RED = "Red"
RAG_AMBER = "Amber"
RAG_GREEN = "Green"


@dataclass(frozen=True)
class Rule:
    """A single risk rule: a name, a predicate over a row, a RAG level it
    triggers, and the reason text to record when it fires."""

    name: str
    level: str
    reason: str
    predicate: Callable[[pd.Series], bool]


def build_rules() -> list[Rule]:
    """Define the risk rules for the demo. In a real system these would
    likely come from a config file or a rules database rather than code."""
    return [
        Rule(
            name="unverified_kyc",
            level=RAG_RED,
            reason="KYC has not been verified for this account.",
            predicate=lambda row: not row["kyc_verified"],
        ),
        Rule(
            name="over_limit",
            level=RAG_RED,
            reason="Current exposure exceeds the account limit.",
            predicate=lambda row: row["current_exposure"] > row["account_limit"],
        ),
        Rule(
            name="high_risk_jurisdiction_near_limit",
            level=RAG_RED,
            reason="Account is based in a higher-risk jurisdiction and exposure is above 90% of its limit.",
            predicate=lambda row: (
                row["country"] in {"Cyprus", "Panama", "UAE"}
                and row["current_exposure"] > 0.9 * row["account_limit"]
            ),
        ),
        Rule(
            name="near_limit",
            level=RAG_AMBER,
            reason="Exposure is above 80% of the account limit.",
            predicate=lambda row: 0.8 * row["account_limit"] < row["current_exposure"] <= row["account_limit"],
        ),
        Rule(
            name="stale_review",
            level=RAG_AMBER,
            reason="Account has not been reviewed in over a year.",
            predicate=lambda row: row["days_since_last_review"] > 365,
        ),
        Rule(
            name="recent_flags",
            level=RAG_AMBER,
            reason="Account has had flagged transactions in the last 90 days.",
            predicate=lambda row: row["flagged_transactions_90d"] > 0,
        ),
    ]


RAG_SEVERITY = {RAG_GREEN: 0, RAG_AMBER: 1, RAG_RED: 2}


def load_exceptions(path: str | None) -> dict[str, dict[str, dict]]:
    """Load the exceptions file into {client_id: {rule_name: entry}}.
    Expired exceptions (based on today's date) are dropped."""
    if not path:
        return {}

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    today = date.today()
    by_client: dict[str, dict[str, dict]] = {}
    for entry in raw.get("exceptions", []):
        expires = entry.get("expires")
        if expires:
            expiry_date = datetime.strptime(expires, "%Y-%m-%d").date()
            if expiry_date < today:
                continue  # expired — treat as if it didn't exist
        by_client.setdefault(entry["client_id"], {})[entry["rule"]] = entry
    return by_client


def evaluate_row(row: pd.Series, rules: list[Rule], exceptions: dict[str, dict]) -> tuple[str, str]:
    """Run every rule against one row, apply any client-specific exceptions,
    and return the worst remaining (status, reason)."""
    client_exceptions = exceptions.get(row["client_id"], {})

    fired: list[Rule] = []
    waived_reasons: list[str] = []
    for rule in rules:
        if not rule.predicate(row):
            continue
        override = client_exceptions.get(rule.name)
        if override:
            waived_reasons.append(f"[Waived: {rule.name}] {override['reason']}")
            continue
        fired.append(rule)

    if not fired:
        if waived_reasons:
            return RAG_GREEN, " | ".join(waived_reasons)
        return RAG_GREEN, "No risk conditions triggered."

    worst = max(fired, key=lambda r: RAG_SEVERITY[r.level])
    reasons = [r.reason for r in fired]
    if waived_reasons:
        reasons.extend(waived_reasons)
    return worst.level, " | ".join(reasons)


def flag_clients(df: pd.DataFrame, exceptions: dict[str, dict]) -> pd.DataFrame:
    """Add 'status' and 'reason' columns to the client dataframe."""
    rules = build_rules()
    results = df.apply(lambda row: evaluate_row(row, rules, exceptions), axis=1)
    df = df.copy()
    df["status"] = [r[0] for r in results]
    df["reason"] = [r[1] for r in results]
    return df


def read_clients(path: str) -> pd.DataFrame:
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    return pd.read_csv(path)


def write_clients(df: pd.DataFrame, path: str) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if path.lower().endswith((".xlsx", ".xls")):
        df.to_excel(path, index=False)
    else:
        df.to_csv(path, index=False)


def main() -> None:
    parser = argparse.ArgumentParser(description="Flag client risk status (RAG) with exception handling.")
    parser.add_argument("--input", required=True, help="Path to input CSV/XLSX of clients.")
    parser.add_argument("--exceptions", default=None, help="Path to exceptions JSON file (optional).")
    parser.add_argument("--output", required=True, help="Path to write the flagged CSV/XLSX.")
    args = parser.parse_args()

    df = read_clients(args.input)
    exceptions = load_exceptions(args.exceptions)
    flagged = flag_clients(df, exceptions)
    write_clients(flagged, args.output)

    counts = flagged["status"].value_counts().to_dict()
    print(f"Flagged {len(flagged)} clients -> {args.output}")
    print(f"Status breakdown: {counts}")


if __name__ == "__main__":
    main()
