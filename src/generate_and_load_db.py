"""
Generate realistic relational financial datasets for Credit Fraud Trends & Credit Score Analysis
and load them into SQL via SQLAlchemy (supports MySQL and local SQLite mirror).

Tables created & populated:
1. customers (5,000 customers across 15 UK cities / 10 regions)
2. accounts (5,000 credit card accounts with credit limits, balances, APRs)
3. credit_history (5,000 credit bureau histories with FICO/Experian-style scores & delinquency buckets)
4. transactions (60,000 card transactions across 12 months with geo-coordinates & channels)
5. fraud_records (60,000 transaction fraud assessments with fraud types, rule scores & losses)
"""

from __future__ import annotations

import os
from pathlib import Path
import numpy as np
import pandas as pd
from sqlalchemy import create_engine, text

ROOT = Path(__file__).resolve().parents[1]
RAW_DIR = ROOT / "data" / "raw"
PROC_DIR = ROOT / "data" / "processed"
DB_PATH = PROC_DIR / "credit_fraud_analytics.db"

UK_LOCATIONS = [
    ("London", "Greater London", 51.5074, -0.1278, 0.24),
    ("Manchester", "North West", 53.4808, -2.2426, 0.11),
    ("Birmingham", "West Midlands", 52.4862, -1.8904, 0.10),
    ("Leeds", "Yorkshire & Humber", 53.8008, -1.5491, 0.08),
    ("Glasgow", "Scotland", 55.8642, -4.2518, 0.07),
    ("Edinburgh", "Scotland", 55.9533, -3.1883, 0.06),
    ("Bristol", "South West", 51.4545, -2.5879, 0.06),
    ("Liverpool", "North West", 53.4084, -2.9916, 0.05),
    ("Sheffield", "Yorkshire & Humber", 53.3811, -1.4701, 0.04),
    ("Newcastle", "North East", 54.9783, -1.6178, 0.04),
    ("Nottingham", "East Midlands", 52.9548, -1.1581, 0.04),
    ("Cardiff", "Wales", 51.4816, -3.1791, 0.03),
    ("Belfast", "Northern Ireland", 54.5973, -5.9301, 0.03),
    ("Cambridge", "East of England", 52.2053, 0.1218, 0.03),
    ("Southampton", "South East", 50.9097, -1.4044, 0.02),
]

FIRST_NAMES = [
    "Oliver", "George", "Noah", "Arthur", "Harry", "Leo", "Muhammad", "Jack",
    "Charlie", "Oscar", "Amelia", "Olivia", "Isla", "Ava", "Freya", "Mia",
    "Willow", "Evie", "Lily", "Grace", "Liam", "Ethan", "Mason", "Lucas",
    "Sophie", "Chloe", "Ella", "Poppy", "Phoebe", "Sienna"
]
LAST_NAMES = [
    "Smith", "Jones", "Taylor", "Brown", "Williams", "Wilson", "Johnson",
    "Davies", "Robinson", "Wright", "Thompson", "Evans", "Walker", "White",
    "Roberts", "Green", "Hall", "Wood", "Jackson", "Clarke", "Patel", "Khan",
    "Murphy", "O'Connor", "Walsh", "Kelly", "Campbell", "Stewart", "Hughes"
]


def haversine_km(lat1: np.ndarray, lon1: np.ndarray, lat2: np.ndarray, lon2: np.ndarray) -> np.ndarray:
    r = 6371.0
    phi1, phi2 = np.radians(lat1), np.radians(lat2)
    dphi = np.radians(lat2 - lat1)
    dlambda = np.radians(lon2 - lon1)
    a = np.sin(dphi / 2.0) ** 2 + np.cos(phi1) * np.cos(phi2) * np.sin(dlambda / 2.0) ** 2
    return 2.0 * r * np.arcsin(np.sqrt(a))


def generate_datasets(n_customers: int = 5000, n_transactions: int = 60000, seed: int = 42) -> dict[str, pd.DataFrame]:
    rng = np.random.default_rng(seed)

    # --- 1. CUSTOMERS ---
    cust_ids = [f"CUST-{i:05d}" for i in range(1, n_customers + 1)]
    fn = rng.choice(FIRST_NAMES, size=n_customers)
    ln = rng.choice(LAST_NAMES, size=n_customers)
    full_names = [f"{f} {l}" for f, l in zip(fn, ln)]

    ages = rng.integers(21, 74, size=n_customers)
    emp_statuses = rng.choice(
        ["Full-Time Employed", "Self-Employed", "Part-Time", "Contractor", "Retired"],
        size=n_customers,
        p=[0.62, 0.14, 0.10, 0.08, 0.06],
    )

    loc_probs = np.array([loc[4] for loc in UK_LOCATIONS])
    loc_probs = loc_probs / loc_probs.sum()
    loc_idx = rng.choice(len(UK_LOCATIONS), size=n_customers, p=loc_probs)

    home_cities = [UK_LOCATIONS[i][0] for i in loc_idx]
    home_regions = [UK_LOCATIONS[i][1] for i in loc_idx]
    home_lats = np.array([UK_LOCATIONS[i][2] for i in loc_idx]) + rng.normal(0, 0.03, size=n_customers)
    home_lons = np.array([UK_LOCATIONS[i][3] for i in loc_idx]) + rng.normal(0, 0.03, size=n_customers)

    # Underlying latent credit risk profile (0 = low risk, 1 = medium risk, 2 = high risk)
    latent_tier = rng.choice([0, 1, 2], size=n_customers, p=[0.52, 0.31, 0.17])

    base_income = np.where(
        latent_tier == 0,
        rng.normal(62000, 18000, size=n_customers),
        np.where(
            latent_tier == 1,
            rng.normal(43000, 13000, size=n_customers),
            rng.normal(31000, 10000, size=n_customers),
        ),
    )
    incomes = np.clip(base_income, 18500, 185000).round(2)
    tenure_months = np.clip(
        np.where(latent_tier == 0, rng.integers(24, 144, size=n_customers), rng.integers(6, 96, size=n_customers)),
        6,
        160,
    )
    created_dates = pd.to_datetime("2025-12-31") - pd.to_timedelta(tenure_months * 30, unit="D")

    customers_df = pd.DataFrame({
        "customer_id": cust_ids,
        "full_name": full_names,
        "age": ages,
        "income_gbp": incomes,
        "employment_status": emp_statuses,
        "home_city": home_cities,
        "home_region": home_regions,
        "home_lat": np.round(home_lats, 6),
        "home_lon": np.round(home_lons, 6),
        "tenure_months": tenure_months,
        "created_at": created_dates.strftime("%Y-%m-%d"),
    })

    # --- 2. ACCOUNTS ---
    acc_ids = [f"ACC-{i:05d}" for i in range(1, n_customers + 1)]
    card_types = np.where(
        incomes > 75000,
        rng.choice(["Platinum Rewards", "Signature Premier", "Gold Cashback"], size=n_customers, p=[0.5, 0.3, 0.2]),
        np.where(
            latent_tier == 2,
            rng.choice(["Classic Builder", "Standard Credit"], size=n_customers, p=[0.6, 0.4]),
            rng.choice(["Standard Credit", "Gold Cashback", "Platinum Rewards"], size=n_customers, p=[0.5, 0.35, 0.15]),
        ),
    )

    credit_limits = np.where(
        latent_tier == 0,
        rng.choice([8000, 10000, 12500, 15000, 20000, 25000], size=n_customers),
        np.where(
            latent_tier == 1,
            rng.choice([4000, 5000, 6500, 8000, 10000], size=n_customers),
            rng.choice([1500, 2000, 2500, 3500, 5000], size=n_customers),
        ),
    ).astype(float)

    # Utilisation ratio linked to latent tier
    util_ratio = np.where(
        latent_tier == 0,
        rng.beta(2.0, 8.5, size=n_customers),      # ~18% mean
        np.where(
            latent_tier == 1,
            rng.beta(4.5, 5.0, size=n_customers),  # ~47% mean
            rng.beta(7.8, 2.0, size=n_customers),  # ~80% mean
        ),
    )
    util_ratio = np.clip(util_ratio, 0.02, 0.99)
    current_balances = np.round(credit_limits * util_ratio, 2)

    apr_pct = np.where(
        latent_tier == 0,
        rng.uniform(14.9, 21.9, size=n_customers),
        np.where(latent_tier == 1, rng.uniform(21.9, 28.9, size=n_customers), rng.uniform(27.9, 36.9, size=n_customers)),
    ).round(2)

    account_status = np.where(
        (latent_tier == 2) & (rng.random(n_customers) < 0.18),
        "Watchlist",
        "Active",
    )

    accounts_df = pd.DataFrame({
        "account_id": acc_ids,
        "customer_id": cust_ids,
        "card_type": card_types,
        "credit_limit": credit_limits,
        "current_balance": current_balances,
        "account_status": account_status,
        "opened_date": created_dates.strftime("%Y-%m-%d"),
        "apr_pct": apr_pct,
    })

    # --- 3. CREDIT HISTORY ---
    hist_ids = [f"CH-{i:05d}" for i in range(1, n_customers + 1)]
    total_cycles = np.clip(tenure_months, 12, 120)

    late_30d = np.where(
        latent_tier == 0,
        rng.poisson(0.25, size=n_customers),
        np.where(latent_tier == 1, rng.poisson(1.8, size=n_customers), rng.poisson(4.5, size=n_customers)),
    )
    late_60d = np.where(
        latent_tier == 0,
        rng.poisson(0.03, size=n_customers),
        np.where(latent_tier == 1, rng.poisson(0.55, size=n_customers), rng.poisson(2.3, size=n_customers)),
    )
    late_90d = np.where(
        latent_tier == 0,
        0,
        np.where(latent_tier == 1, rng.poisson(0.12, size=n_customers), rng.poisson(1.4, size=n_customers)),
    )

    defaults_flag = np.where((latent_tier == 2) & ((late_90d >= 2) | (rng.random(n_customers) < 0.25)), 1, 0)
    hard_inquiries = np.where(
        latent_tier == 0,
        rng.poisson(0.6, size=n_customers),
        np.where(latent_tier == 1, rng.poisson(2.1, size=n_customers), rng.poisson(4.4, size=n_customers)),
    )

    repayment_ratio = np.where(
        latent_tier == 0,
        rng.uniform(0.75, 1.00, size=n_customers),
        np.where(latent_tier == 1, rng.uniform(0.35, 0.78, size=n_customers), rng.uniform(0.08, 0.38, size=n_customers)),
    ).round(4)

    # Calculate realistic credit score (300 - 850) driven by utilisation, delinquency, repayment ratio
    raw_score = (
        815
        - (util_ratio * 195)
        - (late_30d * 14)
        - (late_60d * 28)
        - (late_90d * 45)
        - (defaults_flag * 65)
        - (hard_inquiries * 5)
        + (repayment_ratio * 40)
        + rng.normal(0, 14, size=n_customers)
    )
    credit_scores = np.clip(np.round(raw_score), 320, 850).astype(int)

    total_lines = rng.integers(2, 12, size=n_customers)
    open_lines = np.clip(total_lines - rng.integers(0, 3, size=n_customers), 1, 10)

    credit_history_df = pd.DataFrame({
        "history_id": hist_ids,
        "customer_id": cust_ids,
        "credit_score": credit_scores,
        "total_credit_lines": total_lines,
        "open_credit_lines": open_lines,
        "total_payment_cycles": total_cycles,
        "late_payments_30d": late_30d,
        "late_payments_60d": late_60d,
        "late_payments_90d_plus": late_90d,
        "defaults_flag": defaults_flag,
        "hard_inquiries_12m": hard_inquiries,
        "repayment_ratio": repayment_ratio,
        "last_updated": "2025-12-31",
    })

    # --- 4. TRANSACTIONS & 5. FRAUD RECORDS ---
    txn_cust_indices = rng.integers(0, n_customers, size=n_transactions)
    txn_ids = [f"TXN-{i:06d}" for i in range(1, n_transactions + 1)]
    txn_cust_ids = [cust_ids[i] for i in txn_cust_indices]
    txn_acc_ids = [acc_ids[i] for i in txn_cust_indices]
    txn_tiers = latent_tier[txn_cust_indices]

    # Timestamps across 2025 (with Q4 holiday seasonal uplift)
    months = rng.choice(
        np.arange(1, 13),
        size=n_transactions,
        p=[0.072, 0.070, 0.078, 0.079, 0.082, 0.083, 0.084, 0.083, 0.084, 0.088, 0.098, 0.099],
    )
    days = rng.integers(1, 29, size=n_transactions)
    hours = rng.integers(0, 24, size=n_transactions)
    minutes = rng.integers(0, 60, size=n_transactions)
    seconds = rng.integers(0, 60, size=n_transactions)

    timestamps = pd.to_datetime({
        "year": 2025,
        "month": months,
        "day": days,
        "hour": hours,
        "minute": minutes,
        "second": seconds,
    })

    categories = [
        "Groceries & Supermarkets",
        "Travel & Airlines",
        "Luxury & Jewellery",
        "Electronics & Gaming",
        "Dining & Restaurants",
        "Fuel & Transit",
        "Digital Subscriptions & Crypto",
        "Apparel & Department Stores",
    ]
    cat_probs = [0.24, 0.10, 0.06, 0.12, 0.18, 0.11, 0.07, 0.12]
    txn_cats = rng.choice(categories, size=n_transactions, p=cat_probs)

    channels = rng.choice(
        ["Chip & PIN", "Contactless POS", "Online E-Commerce", "Mobile Wallet", "ATM / Cash Advance"],
        size=n_transactions,
        p=[0.22, 0.34, 0.26, 0.14, 0.04],
    )

    # Determine whether transaction is in customer's home city or another city
    same_city_prob = np.where(txn_tiers == 0, 0.82, np.where(txn_tiers == 1, 0.72, 0.56))
    is_same_city = rng.random(n_transactions) < same_city_prob

    random_loc_idx = rng.choice(len(UK_LOCATIONS), size=n_transactions, p=loc_probs)
    cust_loc_idx = loc_idx[txn_cust_indices]
    final_loc_idx = np.where(is_same_city, cust_loc_idx, random_loc_idx)

    merch_cities = [UK_LOCATIONS[i][0] for i in final_loc_idx]
    merch_regions = [UK_LOCATIONS[i][1] for i in final_loc_idx]
    txn_lats = np.array([UK_LOCATIONS[i][2] for i in final_loc_idx]) + rng.normal(0, 0.04, size=n_transactions)
    txn_lons = np.array([UK_LOCATIONS[i][3] for i in final_loc_idx]) + rng.normal(0, 0.04, size=n_transactions)

    cust_home_lats = home_lats[txn_cust_indices]
    cust_home_lons = home_lons[txn_cust_indices]
    distances_km = np.round(haversine_km(cust_home_lats, cust_home_lons, txn_lats, txn_lons), 2)

    is_intl = np.where(
        ( ~is_same_city ) & (rng.random(n_transactions) < np.where(txn_tiers == 2, 0.18, 0.04)),
        1,
        0,
    )
    # Boost distance for international transactions
    distances_km = np.where(is_intl == 1, distances_km + rng.uniform(450, 2800, size=n_transactions), distances_km).round(2)

    # Base fraud probability driven by risk factors (category, channel, distance, night hour, customer risk tier, Q4)
    fraud_logit = (
        -4.95
        + np.where(txn_tiers == 2, 1.15, np.where(txn_tiers == 1, 0.45, 0.0))
        + np.where(np.isin(txn_cats, ["Luxury & Jewellery", "Electronics & Gaming", "Digital Subscriptions & Crypto"]), 1.25, 0.0)
        + np.where(channels == "Online E-Commerce", 0.95, np.where(channels == "ATM / Cash Advance", 0.80, 0.0))
        + np.where(distances_km > 150, 1.10, 0.0)
        + np.where(is_intl == 1, 1.25, 0.0)
        + np.where((hours >= 0) & (hours <= 4), 0.85, 0.0)
        + np.where(months >= 11, 0.35, 0.0)
    )
    fraud_prob = 1.0 / (1.0 + np.exp(-fraud_logit))
    is_fraud = (rng.random(n_transactions) < fraud_prob).astype(int)

    # Transaction amounts (higher on luxury/electronics and fraudulent spikes)
    base_amt = rng.lognormal(mean=3.55, sigma=0.78, size=n_transactions)
    cat_mult = np.where(
        txn_cats == "Luxury & Jewellery", 4.5,
        np.where(txn_cats == "Travel & Airlines", 3.6,
        np.where(txn_cats == "Electronics & Gaming", 3.1,
        np.where(txn_cats == "Digital Subscriptions & Crypto", 2.2, 1.0)))
    )
    fraud_mult = np.where(is_fraud == 1, rng.uniform(2.4, 5.2, size=n_transactions), 1.0)
    amounts_gbp = np.clip(np.round(base_amt * cat_mult * fraud_mult, 2), 2.50, 9850.00)

    transactions_df = pd.DataFrame({
        "transaction_id": txn_ids,
        "account_id": txn_acc_ids,
        "customer_id": txn_cust_ids,
        "txn_timestamp": timestamps.dt.strftime("%Y-%m-%d %H:%M:%S"),
        "amount_gbp": amounts_gbp,
        "merchant_category": txn_cats,
        "merchant_city": merch_cities,
        "merchant_region": merch_regions,
        "txn_lat": np.round(txn_lats, 6),
        "txn_lon": np.round(txn_lons, 6),
        "distance_from_home_km": distances_km,
        "channel": channels,
        "is_international": is_intl,
    })

    # Fraud Records Table
    fraud_ids = [f"FRD-{i:06d}" for i in range(1, n_transactions + 1)]
    fraud_types_list = [
        "Card-Not-Present (CNP)",
        "Account Takeover (ATO)",
        "Counterfeit / Skimming",
        "Synthetic Identity",
        "Cross-Border Velocity Spike",
    ]
    assigned_fraud_types = np.where(
        is_fraud == 1,
        np.where(
            channels == "Online E-Commerce",
            rng.choice(["Card-Not-Present (CNP)", "Account Takeover (ATO)"], size=n_transactions, p=[0.72, 0.28]),
            np.where(
                is_intl == 1,
                "Cross-Border Velocity Spike",
                rng.choice(fraud_types_list, size=n_transactions, p=[0.35, 0.25, 0.20, 0.10, 0.10]),
            ),
        ),
        "Legitimate",
    )

    risk_rule_scores = np.where(
        is_fraud == 1,
        np.clip(rng.normal(84.5, 9.2, size=n_transactions), 58.0, 99.9),
        np.clip(rng.normal(18.5, 12.0, size=n_transactions), 1.0, 68.0),
    ).round(2)

    detection_methods = np.where(
        is_fraud == 1,
        rng.choice(
            ["Real-Time ML Velocity Rule", "Geo-Distance Anomaly Engine", "Merchant Risk Filter", "Customer Alert"],
            size=n_transactions,
            p=[0.46, 0.28, 0.16, 0.10],
        ),
        "Automated Pass",
    )

    resolution_status = np.where(
        is_fraud == 1,
        rng.choice(
            ["Auto-Blocked & Reversed", "Confirmed Chargeback Loss", "Under Investigation"],
            size=n_transactions,
            p=[0.48, 0.37, 0.15],
        ),
        "Cleared",
    )

    confirmed_loss = np.where(
        (is_fraud == 1) & (resolution_status == "Confirmed Chargeback Loss"),
        amounts_gbp,
        np.where(
            (is_fraud == 1) & (resolution_status == "Under Investigation"),
            np.round(amounts_gbp * 0.45, 2),
            0.00,
        ),
    )

    reported_ts = np.where(
        is_fraud == 1,
        (timestamps + pd.to_timedelta(rng.integers(1, 36, size=n_transactions), unit="h")).dt.strftime("%Y-%m-%d %H:%M:%S"),
        None,
    )

    fraud_records_df = pd.DataFrame({
        "fraud_id": fraud_ids,
        "transaction_id": txn_ids,
        "is_fraud": is_fraud,
        "fraud_type": assigned_fraud_types,
        "risk_rule_score": risk_rule_scores,
        "detection_method": detection_methods,
        "confirmed_loss_gbp": confirmed_loss,
        "reported_timestamp": reported_ts,
        "resolution_status": resolution_status,
    })

    return {
        "customers": customers_df,
        "accounts": accounts_df,
        "credit_history": credit_history_df,
        "transactions": transactions_df,
        "fraud_records": fraud_records_df,
    }


def save_and_load_to_sql(tables: dict[str, pd.DataFrame]) -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)

    # Save raw CSV tables
    for name, df in tables.items():
        csv_path = RAW_DIR / f"{name}.csv"
        df.to_csv(csv_path, index=False)
        print(f"[RAW CSV] Saved {name}.csv ({len(df):,} rows)")

    # Connect via SQLAlchemy (uses MYSQL_URL if configured, otherwise local SQLite mirror)
    db_url = os.getenv("MYSQL_URL", f"sqlite:///{DB_PATH}")
    engine = create_engine(db_url)

    with engine.begin() as conn:
        for name, df in tables.items():
            df.to_sql(name, conn, if_exists="replace", index=False)
        # Create performance indexes
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_cust_id ON customers(customer_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_acc_cust ON accounts(customer_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_ch_cust ON credit_history(customer_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_txn_acc ON transactions(account_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_txn_cust ON transactions(customer_id);"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS idx_frd_txn ON fraud_records(transaction_id);"))

    print(f"[SQLAlchemy] Successfully loaded 5 relational tables into {db_url}")


if __name__ == "__main__":
    datasets = generate_datasets()
    save_and_load_to_sql(datasets)
