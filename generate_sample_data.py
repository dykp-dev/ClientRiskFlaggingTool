"""
generate_sample_data.py

Creates a synthetic dataset of trading-client accounts so the risk-flagging
tool can be demoed without any real client information. Every field here is
randomly generated and does not correspond to any real person or account.

Usage:
    python generate_sample_data.py --rows 250 --out data/clients.csv
"""

import argparse
import numpy as np
import pandas as pd

RNG_SEED = 42
COUNTRIES = ["UK", "USA", "Germany", "France", "Cyprus", "Panama", "UAE", "Singapore"]
HIGH_RISK_COUNTRIES = {"Cyprus", "Panama", "UAE"}


def generate_clients(n_rows: int, seed: int = RNG_SEED) -> pd.DataFrame:
    """Build a synthetic client book with account limits, exposure, and KYC flags."""
    rng = np.random.default_rng(seed)

    client_ids = [f"CL{100000 + i}" for i in range(n_rows)]
    account_limit = rng.choice([10_000, 25_000, 50_000, 100_000, 250_000], size=n_rows)

    # Exposure is usually well inside the limit, but a meaningful slice of
    # accounts are deliberately generated near or over the limit so the
    # rules below have real cases to flag.
    exposure_ratio = rng.beta(a=2.0, b=3.0, size=n_rows) * 1.3
    current_exposure = np.round(account_limit * exposure_ratio, 2)

    kyc_verified = rng.choice([True, False], size=n_rows, p=[0.9, 0.1])
    country = rng.choice(COUNTRIES, size=n_rows)
    days_since_last_review = rng.integers(1, 400, size=n_rows)
    flagged_transactions_90d = rng.poisson(lam=0.4, size=n_rows)

    df = pd.DataFrame(
        {
            "client_id": client_ids,
            "country": country,
            "account_limit": account_limit,
            "current_exposure": current_exposure,
            "kyc_verified": kyc_verified,
            "days_since_last_review": days_since_last_review,
            "flagged_transactions_90d": flagged_transactions_90d,
        }
    )
    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic client data.")
    parser.add_argument("--rows", type=int, default=250, help="Number of client rows to generate.")
    parser.add_argument("--out", type=str, default="data/clients.csv", help="Output CSV path.")
    parser.add_argument("--seed", type=int, default=RNG_SEED, help="Random seed for reproducibility.")
    args = parser.parse_args()

    df = generate_clients(args.rows, seed=args.seed)
    df.to_csv(args.out, index=False)
    print(f"Wrote {len(df)} synthetic client rows to {args.out}")


if __name__ == "__main__":
    main()
