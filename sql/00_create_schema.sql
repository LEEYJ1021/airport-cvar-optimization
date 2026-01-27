-- This script contains the initial table creation statements.
-- It is designed to be idempotent using `CREATE TABLE IF NOT EXISTS`.

-- Raw data from real-time congestion API
CREATE TABLE IF NOT EXISTS `congestion_data` (
  `terminal_id` VARCHAR(10),
  `terminal_name` VARCHAR(20),
  `gate_id` VARCHAR(10),
  `wait_time` FLOAT,
  `wait_length` INT,
  `occur_time` DATETIME,
  `hour_of_day` INT,
  `day_of_week` INT,
  `collected_at` DATETIME,
  `model_version` VARCHAR(20),
  `transform_version` VARCHAR(30),
  `snapshot_id` VARCHAR(50),
  `quality_pred_based` FLOAT,
  `fallback_level` INT,
  `hour_of_week` INT,
  `is_holiday` INT,
  `schedule_density` INT,
  `weather_temp` FLOAT,
  `weather_rain` FLOAT
);

-- Raw METAR weather reports
CREATE TABLE IF NOT EXISTS `metar_raw` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `icao` VARCHAR(10),
  `metar_msg` TEXT,
  `temp` FLOAT,
  `rain_flag` INT,
  `rain_mm` FLOAT,
  `raw_json` TEXT,
  `collected_at` DATETIME
);

-- Raw passenger forecast data
CREATE TABLE IF NOT EXISTS `passenger_forecast_raw` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `adate` VARCHAR(20),
  `atime` VARCHAR(20),
  `raw_json` TEXT,
  `collected_at` DATETIME
);

-- Transformed passenger forecast for Terminal 1
CREATE TABLE IF NOT EXISTS `passenger_forecast_t1` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `date` VARCHAR(20),
  `time_slot` VARCHAR(10),
  `departure_gate` VARCHAR(10),
  `expected_passenger_load` FLOAT,
  `collected_at` DATETIME
);

-- Fused features for Terminal 1 congestion analysis
CREATE TABLE IF NOT EXISTS `congestion_features_t1` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `snapshot_id` VARCHAR(50),
  `gate_id` VARCHAR(10),
  `date` VARCHAR(20),
  `time_slot` VARCHAR(10),
  `expected_passenger_load` FLOAT,
  `gate_processing_capacity` FLOAT,
  `load_to_capacity_ratio` FLOAT,
  `queue_pressure_index` FLOAT,
  `congestion_state` VARCHAR(20),
  `data_reliability_score` FLOAT,
  `is_prediction_only` INT,
  `congestion_risk_score` FLOAT,
  `schedule_density` FLOAT,
  `weather_temp` FLOAT,
  `weather_rain_flag` INT,
  `weather_rain_mm` FLOAT,
  `model_version` VARCHAR(20),
  `transform_version` VARCHAR(30),
  `collected_at` DATETIME
);

-- Log for offline policy evaluation and A/B testing
CREATE TABLE IF NOT EXISTS `policy_evaluation_log` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `ts` DATETIME,
  `experiment_id` VARCHAR(50),
  `scenario` VARCHAR(10),
  `snapshot_id` VARCHAR(50),
  `user_segment` VARCHAR(50),
  `policy_version` VARCHAR(50),
  `recommended_gate` VARCHAR(10),
  `recommended_score` FLOAT,
  `propensity` FLOAT,
  `accepted` BOOLEAN,
  `accepted_gate` VARCHAR(10),
  `realized_total` FLOAT,
  `missed` BOOLEAN
);

-- Metadata for each experiment run
CREATE TABLE IF NOT EXISTS `experiment_runs` (
  `experiment_id` VARCHAR(50) PRIMARY KEY,
  `started_at` DATETIME,
  `ended_at` DATETIME,
  `config_json` TEXT
);

-- Aggregated metrics from experiments
CREATE TABLE IF NOT EXISTS `experiment_metrics` (
  `id` BIGINT AUTO_INCREMENT PRIMARY KEY,
  `experiment_id` VARCHAR(50),
  `experiment_code` VARCHAR(10),
  `policy_version` VARCHAR(50),
  `scenario` VARCHAR(10),
  `metric_name` VARCHAR(50),
  `metric_value` FLOAT,
  `n` INT,
  `details_json` TEXT,
  `created_at` DATETIME
);