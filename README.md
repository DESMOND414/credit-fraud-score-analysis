# Credit Fraud Trends & Credit Score Analysis

**End-to-End Customer Credit Risk Segmentation & Fraud Monitoring Pipeline**  
*Tools & Technologies:* **Python** (`Pandas`, `NumPy`, `SQLAlchemy`), **SQL** (`MySQL`), **Power BI** (`Power Query`, `DAX`)

---

## Executive Objective

To evaluate customer credit histories and card transactions across relational financial tables, extract holistic financial profiles, segment customers into behavioural credit risk tiers (**Low**, **Medium**, **High**), and track fraudulent transaction trends across geography and time.

**Result:** Delivered an automated monitoring and reporting solution across **5,000 customer accounts** and **60,000 card transactions (£6.02M spend)**, providing clear visibility into customer creditworthiness (mean score **705**) and fraudulent transaction velocity (**2,889 fraud events / £1.20M gross exposure**, with **£683.5K** prevented via real-time velocity rules).

---

## Executive Dashboard & Visual Analytics

### 1. Full Power BI Executive Monitor Overview
![Executive Dashboard Overview](dashboard/images/executive_dashboard_overview.png)

### 2. Credit Utilisation vs. Delinquency & Behavioural Risk Segmentation
![Credit Utilisation vs Delinquency](dashboard/images/utilisation_vs_delinquency.png)

### 3. Geographic Fraud Heatmap & Location Consistency Analysis
![Geographic Fraud Heatmap](dashboard/images/geographic_fraud_heatmap.png)

### 4. Time-Series Fraud Velocity & Monthly Loss Recovery Trends
![Time-Series Fraud Trends](dashboard/images/timeseries_fraud_trends.png)

> **Interactive Companion Dashboard:** Open [`dashboard/interactive_dashboard.html`](dashboard/interactive_dashboard.html) in any browser to explore interactive hover tooltips, zoomable UK geographic maps, and risk-tier filtering.

---

## Architecture & Pipeline Workflow

1. **Relational SQL Schema & Holistic Table Joins (`sql/`)**
   - Normalised 5-table MySQL relational schema ([`sql/01_schema_ddl.sql`](sql/01_schema_ddl.sql)):
     - `customers`: Demographics, annual income (£), tenure, and home geo-coordinates (`home_lat`, `home_lon`).
     - `accounts`: Card product types, credit limits (£), current revolving balances (£), and APR (%).
     - `credit_history`: Bureau credit scores (300–850), total/open credit lines, 30d/60d/90d+ delinquency buckets, defaults, hard inquiries, and repayment ratios.
     - `transactions`: 60,000 timestamped card transactions across 15 UK cities, merchant categories, payment channels, and Haversine distance from home (`distance_from_home_km`).
     - `fraud_records`: Fraud flags (`is_fraud`), fraud typology (CNP, Account Takeover, Cross-Border Velocity, Skimming), rule scores, and confirmed net losses.
   - Multi-table SQL join queries ([`sql/02_holistic_financial_joins.sql`](sql/02_holistic_financial_joins.sql) & [`sql/03_risk_and_fraud_analytics.sql`](sql/03_risk_and_fraud_analytics.sql)) aggregate customer-level and transaction-level financial records.

2. **Python Feature Engineering & Credit Risk Segmentation (`src/preprocess_and_segment.py`)**
   - **Credit Utilisation Ratio (%):** $\text{Current Balance} / \text{Credit Limit} \times 100$ (Portfolio mean: **38.04%**).
   - **Delinquency Rate (%):** Total 30d/60d/90d+ late payments divided by total payment cycles, plus severity-weighted delinquency scoring (Portfolio mean: **6.47%**).
   - **Spending Averages & Velocity:** Monthly average spend (£) and spend-to-limit ratios.
   - **Location Consistency Score (0–100):** Combines home-city transaction share, home-region share, cross-border frequency, and Haversine distance-from-home penalties (Portfolio mean: **70.73**).
   - **Credit Risk Tier Categorisation:** Vectorised segmentation into **Low Risk** (2,512 customers, mean score 805), **Medium Risk** (1,268 customers, mean score 702), and **High Risk** (1,220 customers, mean score 499).

3. **Power BI Modelling (`powerbi/`)**
   - **Power Query (`M`):** [`powerbi/power_query_m.pq`](powerbi/power_query_m.pq) enforces currency, percentage, and integer data types and builds custom risk-tier sort orders.
   - **DAX Measures:** [`powerbi/dax_measures.dax`](powerbi/dax_measures.dax) implements MoM Fraud Velocity Change (%), Fraud Prevention Efficiency (%), High-Risk Portfolio Share (%), and dynamic executive KPI alert narratives.

---

## Key Analytical Findings

| Credit Risk Tier | Customers | Avg Credit Score | Avg Credit Utilisation | Avg Delinquency Rate | Location Consistency | Fraud Incidence Rate |
| :--- | :---: | :---: | :---: | :---: | :---: | :---: |
| **Low Risk** | 2,512 (50.2%) | **805** | 17.7% | 0.4% | 76.2 | 3.0% |
| **Medium Risk** | 1,268 (25.4%) | **702** | 46.8% | 3.8% | 70.1 | 4.5% |
| **High Risk** | 1,220 (24.4%) | **499** | 70.7% | 21.7% | 60.1 | **9.0%** |
| **Portfolio Total / Mean** | **5,000** | **705** | **38.0%** | **6.5%** | **70.7** | **4.81%** |

- **Utilisation vs. Delinquency Inflection:** Accounts exceeding the **75% credit utilisation threshold** exhibit a **5.7x surge** in severe (60d/90d+) delinquency rates compared to accounts below 38% utilisation.
- **Geographic Fraud Concentration:** London (£281.4K), Manchester (£128.3K), Birmingham (£107.8K), and Edinburgh (£94.2K) account for the highest gross fraud volume, while transactions occurring **>150 km from a cardholder's home coordinates** experience a **3.4x higher fraud rate**.
- **Seasonal Q4 Velocity Spike:** Fraudulent transaction volume peaks in November–December (£125.6K and £148.2K gross exposure) driven by `Online E-Commerce` Card-Not-Present (CNP) attacks in `Luxury & Jewellery` and `Electronics & Gaming`.

---

## Repository Structure

```text
credit-fraud-score-analysis/
├── README.md
├── requirements.txt
├── sql/
│   ├── 01_schema_ddl.sql                  # MySQL 5-table relational DDL (customers, accounts, credit_history, transactions, fraud_records)
│   ├── 02_holistic_financial_joins.sql    # Multi-table SQL joins for customer & transaction holistic profiles
│   └── 03_risk_and_fraud_analytics.sql    # Analytical SQL queries for risk tiers, geo heatmaps & monthly velocity
├── src/
│   ├── generate_and_load_db.py            # Generates 5 relational tables & loads into SQL via SQLAlchemy
│   ├── preprocess_and_segment.py          # Computes delinquency, utilisation, location consistency & risk tiers
│   └── build_dashboard.py                 # Builds static PNG dashboard views & interactive Plotly HTML report
├── powerbi/
│   ├── dax_measures.dax                   # DAX KPI formulas, MoM velocity & smart alert narrative
│   └── power_query_m.pq                   # Power Query M script for schema ingestion & type enforcement
├── data/
│   └── processed/
│       ├── customer_risk_profiles.csv     # 5,000 processed customer credit & fraud risk profiles
│       ├── geographic_fraud_summary.csv   # City/region spatial fraud aggregations
│       ├── monthly_fraud_trends.csv       # Monthly time-series fraud & spend metrics by risk tier
│       ├── transactions_enriched_sample.csv # 10,000-row sample of joined transaction records
│       └── pipeline_kpi_summary.json      # Automated pipeline summary metrics
└── dashboard/
    ├── interactive_dashboard.html         # Self-contained interactive HTML dashboard
    └── images/
        ├── executive_dashboard_overview.png
        ├── geographic_fraud_heatmap.png
        ├── timeseries_fraud_trends.png
        └── utilisation_vs_delinquency.png
```

---

## Quick Start & Reproducibility

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Generate the 5 relational tables and load into SQL (MySQL or local SQLite mirror)
# Optional: export MYSQL_URL="mysql+pymysql://user:pass@localhost:3306/credit_fraud_analytics"
python src/generate_and_load_db.py

# 3. Run SQL holistic joins, Python preprocessing & credit risk tier segmentation
python src/preprocess_and_segment.py

# 4. Generate dashboard visuals & interactive HTML report
python src/build_dashboard.py
```
