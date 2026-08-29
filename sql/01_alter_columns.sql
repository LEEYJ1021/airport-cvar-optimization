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

-- [버그 수정] 승객 개별 궤적을 복원할 수 있도록 식별자 컬럼 추가.
-- 기존 스키마에는 개별 승객을 구분할 방법이 없어, 같은 snapshot 안의
-- 서로 다른 합성 승객이 서로의 hysteresis 상태에 영향을 주고, switch_rate
-- 계산도 "동일 승객의 연속된 추천"이 아니라 "임의의 인접 행"을 세고 있었다.
ALTER TABLE `policy_evaluation_log` ADD COLUMN IF NOT EXISTS `u` INT;
ALTER TABLE `policy_evaluation_log` ADD COLUMN IF NOT EXISTS `occupancy` FLOAT;
