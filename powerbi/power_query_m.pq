// =============================================================================
// Credit Fraud Trends & Credit Score Analysis
// Power Query (M) Data Transformation Script for Power BI Desktop
// =============================================================================

let
    // 1. Load Processed Customer Credit & Fraud Risk Profiles
    Source = Csv.Document(
        File.Contents("C:\Projects\credit-fraud-score-analysis\data\processed\customer_risk_profiles.csv"),
        [Delimiter=",", Columns=46, Encoding=65001, QuoteStyle=QuoteStyle.None]
    ),
    PromotedHeaders = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),

    // 2. Enforce Strict Data Types across Financial & Behavioural Fields
    TypedTable = Table.TransformColumnTypes(PromotedHeaders, {
        {"customer_id", type text},
        {"full_name", type text},
        {"age", Int64.Type},
        {"income_gbp", Currency.Type},
        {"employment_status", type text},
        {"home_city", type text},
        {"home_region", type text},
        {"home_lat", type number},
        {"home_lon", type number},
        {"tenure_months", Int64.Type},
        {"account_id", type text},
        {"card_type", type text},
        {"credit_limit", Currency.Type},
        {"current_balance", Currency.Type},
        {"apr_pct", Percentage.Type},
        {"credit_score", Int64.Type},
        {"total_payment_cycles", Int64.Type},
        {"repayment_ratio", type number},
        {"total_transactions", Int64.Type},
        {"total_spend_gbp", Currency.Type},
        {"avg_transaction_gbp", Currency.Type},
        {"fraud_txn_count", Int64.Type},
        {"fraud_exposure_gbp", Currency.Type},
        {"confirmed_fraud_loss_gbp", Currency.Type},
        {"credit_utilisation_pct", type number},
        {"delinquency_rate_pct", type number},
        {"location_consistency_score", type number},
        {"behavioural_risk_index", type number},
        {"credit_risk_tier", type text}
    }),

    // 3. Add Sort Order Column for Credit Risk Tier Visuals
    AddedTierSort = Table.AddColumn(
        TypedTable,
        "RiskTierSortOrder",
        each if [credit_risk_tier] = "Low Risk" then 1
             else if [credit_risk_tier] = "Medium Risk" then 2
             else 3,
        Int64.Type
    )
in
    AddedTierSort
