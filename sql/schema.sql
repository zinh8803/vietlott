-- Schema MySQL 8.4 cho Vietlott AI Prediction System
-- Theo thiết kế trong docs.txt

CREATE DATABASE IF NOT EXISTS vietlott_ml
  CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

USE vietlott_ml;

CREATE TABLE IF NOT EXISTS draws (
    draw_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(32) NOT NULL,
    draw_no BIGINT UNSIGNED NOT NULL,
    draw_date DATE NOT NULL,
    open_time DATETIME NULL,
    n1 TINYINT UNSIGNED NOT NULL,
    n2 TINYINT UNSIGNED NOT NULL,
    n3 TINYINT UNSIGNED NOT NULL,
    n4 TINYINT UNSIGNED NOT NULL,
    n5 TINYINT UNSIGNED NOT NULL,
    n6 TINYINT UNSIGNED NOT NULL,
    bonus_number TINYINT UNSIGNED NULL,
    source_url VARCHAR(512) NULL,
    raw_payload JSON NULL,
    ingested_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_draw_product_no (product_code, draw_no),
    KEY idx_draw_product_date (product_code, draw_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS features (
    feature_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(32) NOT NULL,
    target_draw_id BIGINT UNSIGNED NOT NULL,
    candidate_no TINYINT UNSIGNED NOT NULL,
    window_size SMALLINT UNSIGNED NOT NULL,
    feature_version VARCHAR(64) NOT NULL,
    dataset_role VARCHAR(16) NOT NULL,
    feature_json JSON NULL,
    feature_uri VARCHAR(512) NULL,
    label TINYINT(1) NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY uk_feature_sample (product_code, target_draw_id, candidate_no, window_size, feature_version),
    KEY idx_feature_lookup (product_code, feature_version, dataset_role),
    CONSTRAINT fk_features_draw
        FOREIGN KEY (target_draw_id) REFERENCES draws(draw_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS models (
    model_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    model_name VARCHAR(128) NOT NULL,
    algorithm VARCHAR(32) NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    task_type VARCHAR(32) NOT NULL,
    feature_version VARCHAR(64) NOT NULL,
    window_size SMALLINT UNSIGNED NOT NULL,
    train_from_draw_id BIGINT UNSIGNED NOT NULL,
    train_to_draw_id BIGINT UNSIGNED NOT NULL,
    valid_from_draw_id BIGINT UNSIGNED NULL,
    valid_to_draw_id BIGINT UNSIGNED NULL,
    hyperparams_json JSON NOT NULL,
    metrics_summary_json JSON NULL,
    artifact_uri VARCHAR(512) NOT NULL,
    model_checksum CHAR(64) NULL,
    framework_versions_json JSON NULL,
    status VARCHAR(16) NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    promoted_at DATETIME(6) NULL,
    KEY idx_model_product_status (product_code, status),
    KEY idx_model_algo (algorithm)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS predictions (
    prediction_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    model_id BIGINT UNSIGNED NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    as_of_draw_id BIGINT UNSIGNED NOT NULL,
    predicted_draw_no BIGINT UNSIGNED NOT NULL,
    predicted_draw_date DATE NOT NULL,
    probabilities_json JSON NOT NULL,
    top6_json JSON NOT NULL,
    actual_top6_json JSON NULL,
    actual_bonus_number TINYINT UNSIGNED NULL,
    hit_count_main TINYINT UNSIGNED NULL,
    hit_bonus TINYINT(1) NULL,
    request_type VARCHAR(16) NOT NULL,
    status VARCHAR(16) NOT NULL,
    generated_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    reconciled_at DATETIME(6) NULL,
    UNIQUE KEY uk_prediction_once (model_id, product_code, predicted_draw_no, request_type),
    KEY idx_prediction_pending (product_code, status, predicted_draw_date),
    CONSTRAINT fk_predictions_model
        FOREIGN KEY (model_id) REFERENCES models(model_id),
    CONSTRAINT fk_predictions_asof_draw
        FOREIGN KEY (as_of_draw_id) REFERENCES draws(draw_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS app_users (
    user_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(64) NOT NULL UNIQUE,
    display_name VARCHAR(128) NOT NULL,
    password_hash VARCHAR(256) NULL,
    role VARCHAR(16) NOT NULL DEFAULT 'user',
    daily_ticket_limit INT NOT NULL DEFAULT 3,
    lock_date DATE NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_app_user_role (role)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS user_tickets (
    ticket_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    user_id BIGINT UNSIGNED NOT NULL,
    prediction_id BIGINT UNSIGNED NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    predicted_draw_no BIGINT UNSIGNED NOT NULL,
    numbers_json JSON NOT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_ticket_user_date (user_id, created_at),
    KEY idx_ticket_product_draw (product_code, predicted_draw_no),
    CONSTRAINT fk_user_tickets_user
        FOREIGN KEY (user_id) REFERENCES app_users(user_id),
    CONSTRAINT fk_user_tickets_prediction
        FOREIGN KEY (prediction_id) REFERENCES predictions(prediction_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS metrics (
    metric_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    model_id BIGINT UNSIGNED NOT NULL,
    product_code VARCHAR(32) NOT NULL,
    eval_scope VARCHAR(32) NOT NULL,
    fold_no SMALLINT UNSIGNED NULL,
    period_from_draw_id BIGINT UNSIGNED NULL,
    period_to_draw_id BIGINT UNSIGNED NULL,
    precision_at_6 DECIMAL(10,6) NULL,
    top_k_accuracy DECIMAL(10,6) NULL,
    log_loss DECIMAL(14,8) NULL,
    brier_score DECIMAL(14,8) NULL,
    metric_json JSON NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_metrics_model_scope (model_id, eval_scope),
    CONSTRAINT fk_metrics_model
        FOREIGN KEY (model_id) REFERENCES models(model_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

CREATE TABLE IF NOT EXISTS retrain_jobs (
    job_id BIGINT UNSIGNED NOT NULL AUTO_INCREMENT PRIMARY KEY,
    product_code VARCHAR(32) NOT NULL,
    trigger_reason VARCHAR(128) NOT NULL,
    request_payload_json JSON NULL,
    status VARCHAR(16) NOT NULL,
    started_at DATETIME(6) NULL,
    finished_at DATETIME(6) NULL,
    best_model_id BIGINT UNSIGNED NULL,
    log_uri VARCHAR(512) NULL,
    error_message TEXT NULL,
    created_at DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY idx_retrain_status (product_code, status, created_at),
    CONSTRAINT fk_retrain_best_model
        FOREIGN KEY (best_model_id) REFERENCES models(model_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
