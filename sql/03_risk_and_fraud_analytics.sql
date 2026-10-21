-- =============================================================================
-- Credit Fraud Trends & Credit Score Analysis
-- Analytical SQL Queries: Risk Segmentation, Geographic Fraud & Time-Series Trends
-- =============================================================================

-- Query 1: Credit Risk Tier Summary & Repayment Behavioural Breakdown
SELECT 
    CASE 
        WHEN ch.credit_score < 580 
             OR (ch.late_payments_30d + ch.late_payments_60d * 2 + ch.late_payments_90d_plus * 3) * 1.0 / ch.total_payment_cycles >= 0.12
             OR (a.current_balance / a.credit_limit) >= 0.75
             OR ch.defaults_flag = 1 THEN 'High Risk'
        WHEN ch.credit_score BETWEEN 580 AND 699 
             OR (ch.late_payments_30d + ch.late_payments_60d * 2 + ch.late_payments_90d_plus * 3) * 1.0 / ch.total_payment_cycles >= 0.04
             OR (a.current_balance / a.credit_limit) >= 0.40 THEN 'Medium Risk'
        ELSE 'Low Risk'
    END AS credit_risk_tier,
    COUNT(DISTINCT c.customer_id) AS customer_count,
    ROUND(AVG(ch.credit_score), 1) AS avg_credit_score,
    ROUND(AVG((a.current_balance / a.credit_limit) * 100), 2) AS avg_credit_utilisation_pct,
    ROUND(AVG(((ch.late_payments_30d + ch.late_payments_60d + ch.late_payments_90d_plus) * 100.0) / ch.total_payment_cycles), 2) AS avg_delinquency_rate_pct,
    ROUND(AVG(ch.repayment_ratio * 100), 2) AS avg_repayment_ratio_pct,
    SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) AS total_fraud_incidents,
    ROUND(SUM(CASE WHEN fr.is_fraud = 1 THEN t.amount_gbp ELSE 0 END), 2) AS total_fraud_amount_gbp
FROM customers c
JOIN accounts a ON c.customer_id = a.customer_id
JOIN credit_history ch ON c.customer_id = ch.customer_id
LEFT JOIN transactions t ON a.account_id = t.account_id
LEFT JOIN fraud_records fr ON t.transaction_id = fr.transaction_id
GROUP BY credit_risk_tier
ORDER BY avg_credit_score ASC;

-- Query 2: Geographic Fraud Heatmap Aggregation by Region and City
SELECT 
    t.merchant_region,
    t.merchant_city,
    ROUND(AVG(t.txn_lat), 4) AS lat,
    ROUND(AVG(t.txn_lon), 4) AS lon,
    COUNT(t.transaction_id) AS total_txns,
    SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) AS fraud_txns,
    ROUND(SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(t.transaction_id), 2) AS fraud_rate_pct,
    ROUND(SUM(CASE WHEN fr.is_fraud = 1 THEN t.amount_gbp ELSE 0 END), 2) AS fraud_volume_gbp,
    ROUND(AVG(t.distance_from_home_km), 2) AS avg_distance_km
FROM transactions t
JOIN fraud_records fr ON t.transaction_id = fr.transaction_id
GROUP BY t.merchant_region, t.merchant_city
HAVING COUNT(t.transaction_id) >= 20
ORDER BY fraud_volume_gbp DESC;

-- Query 3: Time-Series Monthly Fraud Velocity & Loss Recovery Rate
SELECT 
    SUBSTR(t.txn_timestamp, 1, 7) AS year_month,
    COUNT(t.transaction_id) AS total_transactions,
    SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) AS fraud_transactions,
    ROUND(SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(t.transaction_id), 3) AS fraud_incidence_rate_pct,
    ROUND(SUM(t.amount_gbp), 2) AS total_spend_gbp,
    ROUND(SUM(CASE WHEN fr.is_fraud = 1 THEN t.amount_gbp ELSE 0 END), 2) AS gross_fraud_exposure_gbp,
    ROUND(SUM(fr.confirmed_loss_gbp), 2) AS net_confirmed_loss_gbp
FROM transactions t
JOIN fraud_records fr ON t.transaction_id = fr.transaction_id
GROUP BY SUBSTR(t.txn_timestamp, 1, 7)
ORDER BY year_month ASC;

-- Query 4: Merchant Category & Channel Vulnerability Matrix
SELECT 
    t.merchant_category,
    t.channel,
    COUNT(t.transaction_id) AS total_txns,
    SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) AS fraud_count,
    ROUND(SUM(CASE WHEN fr.is_fraud = 1 THEN 1 ELSE 0 END) * 100.0 / COUNT(t.transaction_id), 2) AS category_fraud_rate_pct,
    ROUND(AVG(CASE WHEN fr.is_fraud = 1 THEN t.amount_gbp END), 2) AS avg_fraud_ticket_gbp,
    ROUND(AVG(CASE WHEN fr.is_fraud = 0 THEN t.amount_gbp END), 2) AS avg_legit_ticket_gbp
FROM transactions t
JOIN fraud_records fr ON t.transaction_id = fr.transaction_id
GROUP BY t.merchant_category, t.channel
ORDER BY category_fraud_rate_pct DESC, fraud_count DESC;
