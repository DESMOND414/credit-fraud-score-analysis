-- =============================================================================
-- Credit Fraud Trends & Credit Score Analysis
-- Holistic Financial Records Extraction (Joining 5 Relational Tables)
-- =============================================================================

-- 1. Holistic Customer Financial & Fraud Profile Extraction
-- Joins customers, accounts, credit_history, transactions, and fraud_records
SELECT 
    c.customer_id,
    c.full_name,
    c.age,
    c.income_gbp,
    c.employment_status,
    c.home_city,
    c.home_region,
    c.home_lat,
    c.home_lon,
    c.tenure_months,
    a.account_id,
    a.card_type,
    a.credit_limit,
    a.current_balance,
    a.apr_pct,
    ch.credit_score,
    ch.total_credit_lines,
    ch.open_credit_lines,
    ch.total_payment_cycles,
    ch.late_payments_30d,
    ch.late_payments_60d,
    ch.late_payments_90d_plus,
    ch.defaults_flag,
    ch.hard_inquiries_12m,
    ch.repayment_ratio,
    COUNT(t.transaction_id) AS total_transactions,
    ROUND(COALESCE(SUM(t.amount_gbp), 0), 2) AS total_spend_gbp,
    ROUND(COALESCE(AVG(t.amount_gbp), 0), 2) AS avg_transaction_gbp,
    ROUND(COALESCE(MAX(t.amount_gbp), 0), 2) AS max_transaction_gbp,
    ROUND(COALESCE(AVG(t.distance_from_home_km), 0), 2) AS avg_distance_from_home_km,
    ROUND(COALESCE(MAX(t.distance_from_home_km), 0), 2) AS max_distance_from_home_km,
    SUM(CASE WHEN t.merchant_city = c.home_city THEN 1 ELSE 0 END) AS home_city_txn_count,
    SUM(CASE WHEN t.merchant_region = c.home_region THEN 1 ELSE 0 END) AS home_region_txn_count,
    SUM(CASE WHEN t.is_international = 1 THEN 1 ELSE 0 END) AS international_txn_count,
    SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) AS fraud_txn_count,
    ROUND(COALESCE(SUM(CASE WHEN fr.is_fraud = 1 THEN t.amount_gbp ELSE 0 END), 0), 2) AS fraud_exposure_gbp,
    ROUND(COALESCE(SUM(fr.confirmed_loss_gbp), 0), 2) AS confirmed_fraud_loss_gbp,
    ROUND(COALESCE(AVG(fr.risk_rule_score), 0), 2) AS avg_risk_rule_score
FROM customers c
INNER JOIN accounts a 
    ON c.customer_id = a.customer_id
INNER JOIN credit_history ch 
    ON c.customer_id = ch.customer_id
LEFT JOIN transactions t 
    ON a.account_id = t.account_id AND c.customer_id = t.customer_id
LEFT JOIN fraud_records fr 
    ON t.transaction_id = fr.transaction_id
GROUP BY 
    c.customer_id, c.full_name, c.age, c.income_gbp, c.employment_status,
    c.home_city, c.home_region, c.home_lat, c.home_lon, c.tenure_months,
    a.account_id, a.card_type, a.credit_limit, a.current_balance, a.apr_pct,
    ch.credit_score, ch.total_credit_lines, ch.open_credit_lines,
    ch.total_payment_cycles, ch.late_payments_30d, ch.late_payments_60d,
    ch.late_payments_90d_plus, ch.defaults_flag, ch.hard_inquiries_12m,
    ch.repayment_ratio
ORDER BY fraud_exposure_gbp DESC, ch.credit_score ASC;

-- 2. Enriched Transaction-Level Stream for Fraud Heatmaps & Time-Series Trends
SELECT 
    t.transaction_id,
    t.txn_timestamp,
    t.customer_id,
    t.account_id,
    c.home_city,
    c.home_region,
    a.card_type,
    a.credit_limit,
    a.current_balance,
    ch.credit_score,
    t.amount_gbp,
    t.merchant_category,
    t.merchant_city,
    t.merchant_region,
    t.txn_lat,
    t.txn_lon,
    t.distance_from_home_km,
    t.channel,
    t.is_international,
    fr.is_fraud,
    fr.fraud_type,
    fr.risk_rule_score,
    fr.detection_method,
    fr.confirmed_loss_gbp,
    fr.resolution_status
FROM transactions t
INNER JOIN accounts a ON t.account_id = a.account_id
INNER JOIN customers c ON t.customer_id = c.customer_id
INNER JOIN credit_history ch ON t.customer_id = ch.customer_id
INNER JOIN fraud_records fr ON t.transaction_id = fr.transaction_id;
