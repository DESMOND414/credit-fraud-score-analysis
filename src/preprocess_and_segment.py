"""
Preprocess joined relational financial records in Python (Pandas, NumPy, SQLAlchemy) to:
1. Extract holistic customer records by joining the 5 SQL tables (customers, accounts,
   transactions, credit_history, fraud_records).
2. Compute delinquency rates, credit utilisation, spending averages, and location
   consistency metrics using vectorised NumPy/Pandas operations.
3. Categorise customers into credit risk tiers (Low Risk, Medium Risk, High Risk)
   based on repayment behavioural patterns.
4. Export processed analytical tables for Power BI (Power Query / DAX) and dashboarding.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
SQL_DIR = ROOT / "sql"
PROC_DIR = ROOT / "data" / "processed"
DB_PATH = PROC_DIR / "credit_fraud_analytics.db"


def extract_sql_joined_records(engine) -> tuple[pd.DataFrame, pd.DataFrame]:
    sql_file = (SQL_DIR / "02_holistic_financial_joins.sql").read_text()
    queries = [q.strip() for q in sql_file.split(";") if q.strip()]

    with engine.connect() as conn:
        cust_holistic_df = pd.read_sql_query(text(queries[0]), conn)
        txn_enriched_df = pd.read_sql_query(text(queries[1]), conn)

    print(f"[SQL Join] Extracted {len(cust_holistic_df):,} holistic customer records")
    print(f"[SQL Join] Extracted {len(txn_enriched_df):,} enriched transaction records")
    return cust_holistic_df, txn_enriched_df


def compute_metrics_and_risk_tiers(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()

    # 1. Credit Utilisation (%)
    out["credit_utilisation_pct"] = np.round(
        (out["current_balance"] / out["credit_limit"].replace(0, np.nan)) * 100.0, 2
    ).fillna(0.0)

    # 2. Delinquency Rate (%) & Weighted Delinquency Index
    total_late = (
        out["late_payments_30d"]
        + out["late_payments_60d"]
        + out["late_payments_90d_plus"]
    )
    weighted_late = (
        out["late_payments_30d"] * 1.0
        + out["late_payments_60d"] * 2.0
        + out["late_payments_90d_plus"] * 3.5
    )
    cycles = out["total_payment_cycles"].replace(0, 1)

    out["total_delinquent_payments"] = total_late
    out["delinquency_rate_pct"] = np.round((total_late / cycles) * 100.0, 2)
    out["weighted_delinquency_score"] = np.round((weighted_late / cycles) * 100.0, 2)

    # 3. Spending Averages & Velocity Metrics
    out["monthly_spend_avg_gbp"] = np.round(out["total_spend_gbp"] / 12.0, 2)
    out["spend_to_limit_ratio_pct"] = np.round(
        (out["monthly_spend_avg_gbp"] / out["credit_limit"].replace(0, np.nan)) * 100.0, 2
    ).fillna(0.0)

    # 4. Location Consistency Metrics (0 - 100 scale)
    txns = out["total_transactions"].replace(0, 1)
    home_city_share = (out["home_city_txn_count"] / txns) * 100.0
    home_region_share = (out["home_region_txn_count"] / txns) * 100.0
    intl_penalty = (out["international_txn_count"] / txns) * 100.0
    dist_penalty = np.clip(out["avg_distance_from_home_km"] / 5.0, 0, 40)

    out["home_city_consistency_pct"] = np.round(home_city_share, 2)
    out["location_consistency_score"] = np.round(
        np.clip(0.55 * home_city_share + 0.45 * home_region_share - 0.6 * intl_penalty - 0.35 * dist_penalty, 0.0, 100.0),
        2,
    )

    # 5. Composite Repayment Behavioural Risk Index (0 - 100, higher = riskier)
    score_component = np.clip((850 - out["credit_score"]) / 5.3, 0, 100)
    util_component = np.clip(out["credit_utilisation_pct"], 0, 100)
    delinq_component = np.clip(out["weighted_delinquency_score"] * 2.6, 0, 100)
    repay_component = np.clip((1.0 - out["repayment_ratio"]) * 100.0, 0, 100)

    out["behavioural_risk_index"] = np.round(
        0.32 * score_component
        + 0.28 * util_component
        + 0.25 * delinq_component
        + 0.15 * repay_component,
        2,
    )

    # 6. Categorise Customers into Credit Risk Tiers (Low, Medium, High)
    high_cond = (
        (out["credit_score"] < 580)
        | (out["delinquency_rate_pct"] >= 10.0)
        | (out["credit_utilisation_pct"] >= 75.0)
        | (out["defaults_flag"] == 1)
        | (out["behavioural_risk_index"] >= 58.0)
    )
    med_cond = (
        (out["credit_score"].between(580, 699))
        | (out["delinquency_rate_pct"].between(3.5, 9.99))
        | (out["credit_utilisation_pct"].between(38.0, 74.99))
        | (out["behavioural_risk_index"].between(30.0, 57.99))
    )

    out["credit_risk_tier"] = np.select(
        [high_cond, med_cond],
        ["High Risk", "Medium Risk"],
        default="Low Risk",
    )

    out["customer_fraud_rate_pct"] = np.round(
        (out["fraud_txn_count"] / txns) * 100.0, 2
    )

    return out


def run_pipeline() -> None:
    db_url = os.getenv("MYSQL_URL", f"sqlite:///{DB_PATH}")
    engine = create_engine(db_url)

    cust_df, txn_df = extract_sql_joined_records(engine)
    processed_cust = compute_metrics_and_risk_tiers(cust_df)

    # Map risk tier and location consistency back to transaction stream
    tier_map = processed_cust.set_index("customer_id")[
        ["credit_risk_tier", "credit_utilisation_pct", "delinquency_rate_pct", "location_consistency_score", "behavioural_risk_index"]
    ]
    txn_enriched = txn_df.merge(tier_map, on="customer_id", how="left")
    txn_enriched["year_month"] = txn_enriched["txn_timestamp"].str.slice(0, 7)

    # Write processed datasets back to SQL & CSV for Power BI consumption
    with engine.begin() as conn:
        processed_cust.to_sql("customer_risk_profiles", conn, if_exists="replace", index=False)

    processed_cust.to_csv(PROC_DIR / "customer_risk_profiles.csv", index=False)

    # Aggregated tables for fast Power BI / GitHub repo commit
    geo_summary = (
        txn_enriched.groupby(["merchant_region", "merchant_city"], as_index=False)
        .agg(
            lat=("txn_lat", "mean"),
            lon=("txn_lon", "mean"),
            total_transactions=("transaction_id", "count"),
            fraud_transactions=("is_fraud", "sum"),
            total_spend_gbp=("amount_gbp", "sum"),
            fraud_exposure_gbp=("amount_gbp", lambda s: s[txn_enriched.loc[s.index, "is_fraud"] == 1].sum()),
            confirmed_loss_gbp=("confirmed_loss_gbp", "sum"),
            avg_distance_km=("distance_from_home_km", "mean"),
        )
    )
    geo_summary["fraud_rate_pct"] = np.round(
        (geo_summary["fraud_transactions"] / geo_summary["total_transactions"]) * 100.0, 2
    )
    geo_summary.to_csv(PROC_DIR / "geographic_fraud_summary.csv", index=False)

    monthly_trends = (
        txn_enriched.groupby(["year_month", "credit_risk_tier"], as_index=False)
        .agg(
            total_transactions=("transaction_id", "count"),
            fraud_transactions=("is_fraud", "sum"),
            total_spend_gbp=("amount_gbp", "sum"),
            fraud_exposure_gbp=("amount_gbp", lambda s: s[txn_enriched.loc[s.index, "is_fraud"] == 1].sum()),
            confirmed_loss_gbp=("confirmed_loss_gbp", "sum"),
        )
    )
    monthly_trends["fraud_rate_pct"] = np.round(
        (monthly_trends["fraud_transactions"] / monthly_trends["total_transactions"]) * 100.0, 2
    )
    monthly_trends.to_csv(PROC_DIR / "monthly_fraud_trends.csv", index=False)

    # Save 10,000-row sample of enriched transactions for repository portability
    txn_enriched.sample(10000, random_state=42).to_csv(PROC_DIR / "transactions_enriched_sample.csv", index=False)

    # Compute KPI summary JSON
    tier_counts = processed_cust["credit_risk_tier"].value_counts().to_dict()
    summary_kpis = {
        "total_customers": int(len(processed_cust)),
        "total_transactions": int(len(txn_enriched)),
        "total_spend_gbp": round(float(txn_enriched["amount_gbp"].sum()), 2),
        "total_fraud_txns": int(txn_enriched["is_fraud"].sum()),
        "overall_fraud_rate_pct": round(float(txn_enriched["is_fraud"].mean() * 100.0), 2),
        "gross_fraud_exposure_gbp": round(float(txn_enriched.loc[txn_enriched["is_fraud"] == 1, "amount_gbp"].sum()), 2),
        "confirmed_net_loss_gbp": round(float(txn_enriched["confirmed_loss_gbp"].sum()), 2),
        "avg_credit_score": round(float(processed_cust["credit_score"].mean()), 1),
        "avg_utilisation_pct": round(float(processed_cust["credit_utilisation_pct"].mean()), 2),
        "avg_delinquency_rate_pct": round(float(processed_cust["delinquency_rate_pct"].mean()), 2),
        "avg_location_consistency": round(float(processed_cust["location_consistency_score"].mean()), 2),
        "risk_tier_distribution": {k: int(v) for k, v in tier_counts.items()},
    }
    (PROC_DIR / "pipeline_kpi_summary.json").write_text(json.dumps(summary_kpis, indent=2))
    print("[Pipeline Summary]", json.dumps(summary_kpis, indent=2))


if __name__ == "__main__":
    run_pipeline()
