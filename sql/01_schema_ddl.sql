-- =============================================================================
-- Credit Fraud Trends & Credit Score Analysis
-- MySQL Relational Database Schema (5 Core Tables)
-- =============================================================================

CREATE DATABASE IF NOT EXISTS credit_fraud_analytics;
USE credit_fraud_analytics;

DROP TABLE IF EXISTS fraud_records;
DROP TABLE IF EXISTS transactions;
DROP TABLE IF EXISTS credit_history;
DROP TABLE IF EXISTS accounts;
DROP TABLE IF EXISTS customers;

-- 1. Customers Table
CREATE TABLE customers (
    customer_id VARCHAR(16) PRIMARY KEY,
    full_name VARCHAR(100) NOT NULL,
    age INT NOT NULL,
    income_gbp DECIMAL(12, 2) NOT NULL,
    employment_status VARCHAR(40) NOT NULL,
    home_city VARCHAR(60) NOT NULL,
    home_region VARCHAR(60) NOT NULL,
    home_lat DECIMAL(9, 6) NOT NULL,
    home_lon DECIMAL(9, 6) NOT NULL,
    tenure_months INT NOT NULL,
    created_at DATE NOT NULL,
    INDEX idx_cust_region (home_region),
    INDEX idx_cust_city (home_city)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 2. Accounts Table
CREATE TABLE accounts (
    account_id VARCHAR(16) PRIMARY KEY,
    customer_id VARCHAR(16) NOT NULL,
    card_type VARCHAR(30) NOT NULL,
    credit_limit DECIMAL(12, 2) NOT NULL,
    current_balance DECIMAL(12, 2) NOT NULL,
    account_status VARCHAR(20) NOT NULL,
    opened_date DATE NOT NULL,
    apr_pct DECIMAL(5, 2) NOT NULL,
    CONSTRAINT fk_acc_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    INDEX idx_acc_customer (customer_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 3. Credit History Table
CREATE TABLE credit_history (
    history_id VARCHAR(20) PRIMARY KEY,
    customer_id VARCHAR(16) NOT NULL,
    credit_score INT NOT NULL,
    total_credit_lines INT NOT NULL,
    open_credit_lines INT NOT NULL,
    total_payment_cycles INT NOT NULL,
    late_payments_30d INT NOT NULL,
    late_payments_60d INT NOT NULL,
    late_payments_90d_plus INT NOT NULL,
    defaults_flag TINYINT(1) NOT NULL DEFAULT 0,
    hard_inquiries_12m INT NOT NULL,
    repayment_ratio DECIMAL(6, 4) NOT NULL,
    last_updated DATE NOT NULL,
    CONSTRAINT fk_ch_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    INDEX idx_ch_customer (customer_id),
    INDEX idx_ch_score (credit_score)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 4. Card Transactions Table
CREATE TABLE transactions (
    transaction_id VARCHAR(20) PRIMARY KEY,
    account_id VARCHAR(16) NOT NULL,
    customer_id VARCHAR(16) NOT NULL,
    txn_timestamp DATETIME NOT NULL,
    amount_gbp DECIMAL(10, 2) NOT NULL,
    merchant_category VARCHAR(50) NOT NULL,
    merchant_city VARCHAR(60) NOT NULL,
    merchant_region VARCHAR(60) NOT NULL,
    txn_lat DECIMAL(9, 6) NOT NULL,
    txn_lon DECIMAL(9, 6) NOT NULL,
    distance_from_home_km DECIMAL(8, 2) NOT NULL,
    channel VARCHAR(25) NOT NULL,
    is_international TINYINT(1) NOT NULL DEFAULT 0,
    CONSTRAINT fk_txn_account FOREIGN KEY (account_id) REFERENCES accounts(account_id),
    CONSTRAINT fk_txn_customer FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
    INDEX idx_txn_customer (customer_id),
    INDEX idx_txn_account (account_id),
    INDEX idx_txn_timestamp (txn_timestamp),
    INDEX idx_txn_region (merchant_region)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- 5. Fraud Records Table
CREATE TABLE fraud_records (
    fraud_id VARCHAR(20) PRIMARY KEY,
    transaction_id VARCHAR(20) NOT NULL UNIQUE,
    is_fraud TINYINT(1) NOT NULL DEFAULT 0,
    fraud_type VARCHAR(50) NOT NULL,
    risk_rule_score DECIMAL(5, 2) NOT NULL,
    detection_method VARCHAR(50) NOT NULL,
    confirmed_loss_gbp DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
    reported_timestamp DATETIME NULL,
    resolution_status VARCHAR(30) NOT NULL,
    CONSTRAINT fk_fraud_txn FOREIGN KEY (transaction_id) REFERENCES transactions(transaction_id),
    INDEX idx_fraud_flag (is_fraud),
    INDEX idx_fraud_type (fraud_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
