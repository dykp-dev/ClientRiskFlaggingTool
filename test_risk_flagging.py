import pandas as pd

from risk_flagging_tool import RAG_AMBER, RAG_GREEN, RAG_RED, flag_clients


def make_row(**overrides):
    base = {
        "client_id": "CL999999",
        "country": "UK",
        "account_limit": 10_000,
        "current_exposure": 1_000,
        "kyc_verified": True,
        "days_since_last_review": 10,
        "flagged_transactions_90d": 0,
    }
    base.update(overrides)
    return base


def test_clean_account_is_green():
    df = pd.DataFrame([make_row()])
    result = flag_clients(df, exceptions={})
    assert result.loc[0, "status"] == RAG_GREEN


def test_over_limit_is_red():
    df = pd.DataFrame([make_row(current_exposure=12_000)])
    result = flag_clients(df, exceptions={})
    assert result.loc[0, "status"] == RAG_RED
    assert "exceeds the account limit" in result.loc[0, "reason"]


def test_unverified_kyc_is_red():
    df = pd.DataFrame([make_row(kyc_verified=False)])
    result = flag_clients(df, exceptions={})
    assert result.loc[0, "status"] == RAG_RED


def test_near_limit_is_amber():
    df = pd.DataFrame([make_row(current_exposure=8_500)])
    result = flag_clients(df, exceptions={})
    assert result.loc[0, "status"] == RAG_AMBER


def test_exception_waives_the_rule_that_would_have_fired():
    df = pd.DataFrame([make_row(current_exposure=12_000)])
    exceptions = {
        "CL999999": {
            "over_limit": {
                "client_id": "CL999999",
                "rule": "over_limit",
                "reason": "Approved temporary increase.",
            }
        }
    }
    result = flag_clients(df, exceptions=exceptions)
    assert result.loc[0, "status"] == RAG_GREEN
    assert "Waived: over_limit" in result.loc[0, "reason"]


def test_exception_only_waives_the_named_rule_not_others():
    # Over-limit AND unverified KYC both fire; only over_limit is waived,
    # so the account should still come back Red because of KYC.
    df = pd.DataFrame([make_row(current_exposure=12_000, kyc_verified=False)])
    exceptions = {
        "CL999999": {
            "over_limit": {
                "client_id": "CL999999",
                "rule": "over_limit",
                "reason": "Approved temporary increase.",
            }
        }
    }
    result = flag_clients(df, exceptions=exceptions)
    assert result.loc[0, "status"] == RAG_RED
    assert "KYC has not been verified" in result.loc[0, "reason"]
    assert "Waived: over_limit" in result.loc[0, "reason"]
