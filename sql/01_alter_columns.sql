-- This script contains idempotent ALTER TABLE statements to add columns
-- to existing tables, ensuring backward compatibility.

-- Add specific gate forecast columns to the raw passenger forecast table
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t1dg1` FLOAT;
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t1dg2` FLOAT;
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t1dg3` FLOAT;
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t1dg4` FLOAT;
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t1dg5` FLOAT;
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t1dg6` FLOAT;
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t2dg1` FLOAT;
ALTER TABLE `passenger_forecast_raw` ADD COLUMN IF NOT EXISTS `t2dg2` FLOAT;

-- Add extended columns to the policy evaluation log for detailed analysis
ALTER TABLE `policy_evaluation_log` ADD COLUMN IF NOT EXISTS `experiment_id` VARCHAR(50);
ALTER TABLE `policy_evaluation_log` ADD COLUMN IF NOT EXISTS `scenario` VARCHAR(10);
ALTER TABLE `policy_evaluation_log` ADD COLUMN IF NOT EXISTS `snapshot_id` VARCHAR(50);
ALTER TABLE `policy_evaluation_log` ADD COLUMN IF NOT EXISTS `recommended_score` FLOAT;
ALTER TABLE `policy_evaluation_log` ADD COLUMN IF NOT EXISTS `accepted_gate` VARCHAR(10);