# Client Risk Flagging Tool

A small Python (pandas + NumPy) rules engine that reads a client dataset from
CSV/Excel, evaluates each account against a set of risk rules, and writes
back a **Red / Amber / Green** status plus a plain-English reason for that
status. Individual rules can be waived per client via a JSON **exceptions**
file, each with its own reason and optional expiry date, so overrides are
explicit and don't silently persist forever.

> **Note:** All data in this repo is synthetically generated
> (`generate_sample_data.py`). It doesn't correspond to any real person,
> account, or organisation — this project is a demo built to showcase the
> approach, inspired by rule-based data-validation work I did during a
> technology internship.

## What it does

1. **Loads** a client dataset (CSV or Excel) with columns like account
   limit, current exposure, KYC status, and jurisdiction.
2. **Evaluates** every row against a set of rules (over limit, unverified
   KYC, high-risk jurisdiction near its limit, stale review, recent flagged
   transactions, etc.), each mapped to a Red/Amber/Green severity.
3. **Applies exceptions** — a JSON file of per-client, per-rule overrides
   (e.g. "client approved for a temporary limit increase"), each with a
   reason and optional expiry date. Expired exceptions are ignored
   automatically.
4. **Writes back** the dataset with two new columns: `status` and `reason`.

## Project structure

```
client-risk-flagging-tool/
├── generate_sample_data.py   # creates synthetic client data
├── risk_flagging_tool.py     # the rules engine (main script)
├── data/
│   ├── clients.csv           # generated sample data (not committed by default)
│   └── exceptions.json       # example per-client rule overrides
├── output/
│   └── clients_flagged.xlsx  # generated output
├── tests/
│   └── test_risk_flagging.py
└── requirements.txt
```

## Setup

```bash
pip install -r requirements.txt
```

## Usage

Generate a synthetic dataset:

```bash
python generate_sample_data.py --rows 250 --out data/clients.csv
```

Run the risk-flagging tool:

```bash
python risk_flagging_tool.py \
    --input data/clients.csv \
    --exceptions data/exceptions.json \
    --output output/clients_flagged.xlsx
```

This prints a status breakdown and writes the flagged file, e.g.:

```
Flagged 250 clients -> output/clients_flagged.xlsx
Status breakdown: {'Amber': 98, 'Green': 104, 'Red': 48}
```

## Running the tests

```bash
pytest tests/ -v
```

## Adding a new rule

Rules live in `build_rules()` in `risk_flagging_tool.py`. Each `Rule` is a
name, a RAG level, a reason string, and a predicate function over a row:

```python
Rule(
    name="over_limit",
    level=RAG_RED,
    reason="Current exposure exceeds the account limit.",
    predicate=lambda row: row["current_exposure"] > row["account_limit"],
)
```

When more than one rule fires for a client, the tool reports the most
severe status and lists every reason that contributed to it.

## Adding an exception

Exceptions live in `data/exceptions.json`:

```json
{
  "client_id": "CL100004",
  "rule": "over_limit",
  "reason": "Client approved for a temporary 20% exposure increase pending Q3 account review.",
  "expires": "2026-12-31"
}
```

An exception only waives the *named* rule for that client — if other rules
still fire, the account keeps its (still-accurate) status.
