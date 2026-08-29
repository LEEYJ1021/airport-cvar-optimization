from __future__ import annotations

import hashlib
import json
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from sqlalchemy import text

from src.db.engine import DBWriter
from src.models.personalization import PassengerProfile
from src.pipeline.engine import AirportOptimizationEngine, T1FeatureBuilder
from src.settings import CHECKIN_COUNTERS, GATES_T1, CHECKIN_TO_GATE
from src.utils.helpers import compute_cvar, is_gate_open, stable_seed

logger = logging.getLogger("airport.pipeline.experiments")


@dataclass
class PolicyConfig:
    """Configuration for a single policy in an offline experiment."""
    name: str
    policy_version: str
    use_prediction: bool = True
    objective: str = "cvar"  # 'mean', 'quantile', 'cvar'
    enforce_gate_hours: bool = True
    hysteresis_penalty: float = 1.5
    use_risk_score: bool = True
    personalize: bool = True


@dataclass
class ExperimentConfig:
    """Configuration for an entire experiment run."""
    duration_minutes: int = 180
    interval_minutes: int = 5
    users_per_snapshot: int = 8
    epsilon: float = 0.2  # For epsilon-greedy simulation of user choice
    refresh_external_once: bool = True


class PolicyEvaluator:
    """Evaluates different policies on a given snapshot of data."""

    def __init__(self, engine: AirportOptimizationEngine):
        self.engine = engine

    def _get_dist(
        self, gate_id: str, snapshot, df_feat: pd.DataFrame, policy: PolicyConfig
    ) -> Dict[str, float]:
        """Gets the wait time distribution according to the policy's settings."""
        if not policy.use_prediction:
            real_wait = snapshot.gate_wait.get(gate_id, 8.0)
            sigma = max(1.5, 0.2 * real_wait + 2.0)
            return {"mu": real_wait, "sigma": sigma}
        return self.engine._predict_and_blend_dist(gate_id, snapshot, df_feat)

    def evaluate(
        self,
        snapshot,
        df_feat: pd.DataFrame,
        profile: PassengerProfile,
        origin_type: str,
        origin_location: str,
        required_gate_time: datetime,
        policy: PolicyConfig,
        last_recommended_gate: Optional[str],
        allowed_counters: Optional[List[str]] = None,
        parking_occupancy: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """Evaluates all possible routes for a user under a given policy."""
        time_context = self.engine._get_time_context(snapshot.collected_at)
        eff_profile = profile if policy.personalize else PassengerProfile(age_group="adult", mobility="normal", bags=1, companions=0)
        
        candidates = []
        for counter in (allowed_counters or CHECKIN_COUNTERS):
            travel_to_checkin = self.engine.get_travel_time(origin_type, origin_location, counter)
            if origin_type == "parking":
                travel_to_checkin += 2 + 10 * ((parking_occupancy or 0.8) ** 2)
            
            checkin_time = self.engine.optimizer.checkin_model.estimate_time(eff_profile, time_context)

            for gate_id in GATES_T1:
                checkin_to_gate = CHECKIN_TO_GATE.get(gate_id, 10.0)
                dist = self._get_dist(gate_id, snapshot, df_feat, policy)
                feat_row = df_feat[df_feat['gate_id'] == gate_id].iloc[0] if not df_feat[df_feat['gate_id'] == gate_id].empty else {}
                
                score, comps = self.engine.optimizer.score_route(
                    travel_to_checkin, checkin_time, checkin_to_gate, dist, eff_profile, gate_id,
                    snapshot.collected_at, objective=policy.objective,
                    required_gate_time=required_gate_time,
                    last_recommended_gate=last_recommended_gate,
                    hysteresis_penalty=policy.hysteresis_penalty,
                    risk_score=feat_row.get("congestion_risk_score") if policy.use_risk_score else None,
                    enforce_gate_hours=policy.enforce_gate_hours
                )
                
                candidates.append({
                    "gate_id": gate_id, "checkin_counter": counter, "origin": origin_location,
                    "score": score, "components": comps, "gate_wait_dist": dist,
                })
        
        candidates.sort(key=lambda x: x["score"])
        return candidates


class ExperimentRunner:
    """Orchestrates the execution of offline replay experiments."""

    def __init__(self, app_engine: AirportOptimizationEngine, db_engine):
        self.app_engine = app_engine
        self.db_writer = DBWriter(db_engine)
        self.db_engine = db_engine
        self.evaluator = PolicyEvaluator(self.app_engine)
        self.policies = self._define_policies()

    def _define_policies(self) -> List[PolicyConfig]:
        sys_ver = self.app_engine.config["system_version"]
        return [
            PolicyConfig(name="Baseline", policy_version=f"{sys_ver}-baseline", use_prediction=False, objective="mean", enforce_gate_hours=False, hysteresis_penalty=0.0, use_risk_score=False, personalize=False),
            PolicyConfig(name="Hybrid-Mean", policy_version=f"{sys_ver}-hmean", objective="mean", enforce_gate_hours=False, hysteresis_penalty=0.0, use_risk_score=False, personalize=False),
            PolicyConfig(name="Hybrid-CVaR", policy_version=f"{sys_ver}-cvar", objective="cvar", personalize=True),
            PolicyConfig(name="Hybrid-Mean-HardOn", policy_version=f"{sys_ver}-hmean-hardon", objective="mean", enforce_gate_hours=True),
            PolicyConfig(name="Hybrid-CVaR-NoHys", policy_version=f"{sys_ver}-cvar-nohys", objective="cvar", hysteresis_penalty=0.0),
            PolicyConfig(name="Hybrid-CVaR-NoPersonal", policy_version=f"{sys_ver}-cvar-nopers", objective="cvar", personalize=False),
        ]

    def run(self, config: ExperimentConfig) -> str:
        """Main method to run the entire experiment suite."""
        experiment_id = str(uuid.uuid4())
        started_at = datetime.now()
        logger.info(f"Starting experiment run with ID: {experiment_id}")

        self._log_experiment_start(experiment_id, started_at, config)

        if config.refresh_external_once:
            self.app_engine.external.fetch_and_process_metar()
            self.app_engine.last_passenger_t1 = self.app_engine.external.fetch_and_process_passenger_forecast()

        snapshot_stream = self._collect_snapshots(config)
        
        all_logs = self._run_offline_replay(snapshot_stream, config, experiment_id)
        self.db_writer.insert_df("policy_evaluation_log", pd.DataFrame(all_logs))

        metrics = self._compute_and_log_metrics(all_logs, experiment_id)
        self.db_writer.insert_df("experiment_metrics", pd.DataFrame(metrics))

        self._log_experiment_end(experiment_id, datetime.now())
        logger.info(f"✅ Experiment {experiment_id} completed successfully.")
        return experiment_id

    def _collect_snapshots(self, config: ExperimentConfig) -> list:
        """Collects a stream of real-time data snapshots for the replay."""
        total_steps = max(1, config.duration_minutes // config.interval_minutes)
        logger.info(f"Collecting {total_steps} snapshots...")
        stream = []
        for i in range(total_steps):
            logger.debug(f"Collecting snapshot {i+1}/{total_steps}")
            snapshot = self.app_engine.perception.fetch_and_persist_snapshot()
            df_feat = self.app_engine.feature_builder.build_features(
                snapshot, self.app_engine.last_passenger_t1 or pd.DataFrame()
            )
            stream.append((snapshot, df_feat))
        return stream

    def _run_offline_replay(self, stream, config, exp_id) -> List[Dict[str, Any]]:
        """Simulates user decisions for each snapshot and policy."""
        all_logs = []
        # [버그 수정] 기존엔 (policy_version, scenario)만으로 키를 잡아, 서로 다른 승객끼리
        # (Q4의 서로 다른 주차구역까지) hysteresis 상태를 공유하고 있었다.
        # (policy_version, scenario, u, seg[, occupancy])로 키를 잡아 승객별 독립 상태로 분리한다.
        last_gate_state: Dict[tuple, Optional[str]] = {}

        for i, (snapshot, df_feat) in enumerate(stream):
            logger.debug(f"Replaying snapshot {i+1}/{len(stream)}")
            for u in range(config.users_per_snapshot):
                for seg, profile in self._get_user_profiles():
                    scenarios = self._get_scenarios_for_user(u)
                    for scenario_name, scenario_params in scenarios.items():
                        for policy in self.policies:
                            log = self._simulate_one_user_choice(
                                snapshot, df_feat, profile, seg, scenario_name, scenario_params,
                                policy, config, exp_id, u, last_gate_state
                            )
                            if log:
                                all_logs.append(log)
        return all_logs

    def _hyst_key(self, policy_version: str, sc_name: str, user_idx: int, seg: str, occupancy: Optional[float] = None) -> tuple:
        """[버그 수정] hysteresis 상태를 승객 단위로 분리하기 위한 키. Q4는 주차구역(occupancy)까지 포함."""
        if sc_name == "Q4":
            return (policy_version, sc_name, user_idx, seg, occupancy)
        return (policy_version, sc_name, user_idx, seg)

    def _simulate_one_user_choice(self, snapshot, df_feat, profile, seg, sc_name, sc_params, policy, config, exp_id, user_idx, last_gate_state):
        """Simulates a single user-policy interaction."""
        req_time = self._get_required_gate_time(snapshot.collected_at, snapshot.snapshot_id, sc_name, seg, user_idx)
        occ = sc_params.get('occ')
        hkey = self._hyst_key(policy.policy_version, sc_name, user_idx, seg, occupancy=occ)

        candidates = self.evaluator.evaluate(
            snapshot, df_feat, profile, sc_params['type'], sc_params['loc'], req_time, policy,
            last_gate_state.get(hkey), parking_occupancy=occ
        )
        if not candidates: return None

        rec = candidates[0]
        last_gate_state[hkey] = rec["gate_id"]

        seed_key = f"{snapshot.snapshot_id}|{sc_name}|{seg}|{user_idx}|{policy.policy_version}"
        accepted = np.random.default_rng(stable_seed(seed_key, "accept")).random() > config.epsilon
        chosen = rec if accepted else self._choose_alternative(candidates, seed_key)
        
        realized_total = self._simulate_realized_total(chosen, seed_key)
        missed = (snapshot.collected_at + timedelta(minutes=realized_total)) > req_time

        return {
            "ts": snapshot.collected_at, "experiment_id": exp_id, "scenario": sc_name,
            "snapshot_id": snapshot.snapshot_id, "user_segment": seg, "u": user_idx, "occupancy": occ,
            "policy_version": policy.policy_version,
            "recommended_gate": rec["gate_id"], "recommended_score": rec["score"],
            "propensity": self._calculate_propensity(candidates), "accepted": accepted,
            "accepted_gate": chosen["gate_id"], "realized_total": realized_total, "missed": missed
        }

    def _compute_and_log_metrics(self, logs: List[Dict], exp_id: str) -> List[Dict]:
        """Computes summary metrics for each policy and experiment code."""
        df = pd.DataFrame(logs)
        metrics = []
        exp_codes = {"E1": ["baseline", "hmean"], "E2": ["hmean", "cvar"], "E3": ["hmean", "hmean-hardon"],
                     "E4": ["cvar", "cvar-nohys"], "E5": ["cvar", "cvar-nopers"]}
        
        for code, pol_stems in exp_codes.items():
            # [버그 수정] 기존 정규식 f"({stem1}|{stem2})"은 부분일치라서
            # "hmean"이 "hmean-hardon"과, "cvar"가 "cvar-nohys"/"cvar-nopers"와도
            # 걸려서 experiment_metrics에 의도치 않은 policy_version이 잘못된
            # experiment_code로 함께 들어갔다. policy_version은 f"{sys_ver}-{stem}"
            # 형식이므로 접미사 정확매칭(endswith)으로 교체한다.
            mask = df['policy_version'].apply(
                lambda pv, stems=pol_stems: any(pv.endswith(f"-{s}") for s in stems)
            )
            df_exp = df[mask]
            for (policy, scenario), group in df_exp.groupby(['policy_version', 'scenario']):
                realized = group['realized_total'].dropna().tolist()
                if not realized: continue
                n = len(realized)
                metrics.extend([
                    {"metric_name": "APT_mean", "metric_value": np.mean(realized)},
                    {"metric_name": "Q90", "metric_value": np.quantile(realized, 0.9)},
                    {"metric_name": "CVaR_0.9", "metric_value": compute_cvar(realized, 0.9)},
                    {"metric_name": "MissRate", "metric_value": group['missed'].mean()},
                    {"metric_name": "AcceptanceRate", "metric_value": group['accepted'].mean()},
                ])
                for m in metrics[-5:]:
                    m.update({"experiment_id": exp_id, "experiment_code": code, "policy_version": policy, "scenario": scenario, "n": n, "created_at": datetime.now()})
        return metrics

    # Helper methods for simulation
    def _get_user_profiles(self) -> List[Tuple[str, PassengerProfile]]:
        return [("family", PassengerProfile(bags=3, companions=2)), ("senior", PassengerProfile(age_group="senior", mobility="low")),
                ("baggage", PassengerProfile(bags=4)), ("solo", PassengerProfile(bags=0, companions=0))]
    
    def _get_scenarios_for_user(self, user_idx: int) -> Dict:
        return {
            "Q1": {"type": "checkin", "loc": ["A", "D", "H"][user_idx % 3]},
            "Q2": {"type": "railroad", "loc": "인천공항1터미널역"},
            "Q3": {"type": "taxi", "loc": ["3층_1번_정차구역", "3층_7번_정차구역"][user_idx % 2]},
            "Q4": {"type": "parking", "loc": "단기주차장_지하2층_A구역", "occ": [0.6, 0.9][user_idx % 2]}
        }

    def _get_required_gate_time(self, base_time, *seed_parts) -> datetime:
        rng = np.random.default_rng(stable_seed(*seed_parts))
        return base_time + timedelta(minutes=float(rng.uniform(60, 150)))

    def _simulate_realized_total(self, chosen_route: Dict, seed_key: str) -> float:
        rng = np.random.default_rng(stable_seed(seed_key, "realized"))
        base = chosen_route["components"]["base_time"]
        dist = chosen_route["gate_wait_dist"]
        wait = max(0.1, rng.normal(dist["mu"], dist["sigma"]))
        return float(base + wait)

    def _choose_alternative(self, candidates: List[Dict], seed_key: str) -> Dict:
        if len(candidates) <= 1: return candidates[0]
        rng = np.random.default_rng(stable_seed(seed_key, "alt"))
        return candidates[rng.integers(1, len(candidates))]

    def _calculate_propensity(self, candidates: List[Dict]) -> float:
        if not candidates: return 1.0
        scores = np.array([-c["score"] for c in candidates])
        probs = np.exp(scores - np.max(scores)) / np.sum(np.exp(scores - np.max(scores)))
        return probs[0]

    def _log_experiment_start(self, exp_id, ts, config):
        self.db_writer.insert_df("experiment_runs", pd.DataFrame([{
            "experiment_id": exp_id, "started_at": ts, "ended_at": None,
            "config_json": json.dumps(config.__dict__)
        }]))

    def _log_experiment_end(self, exp_id, ts):
        with self.db_engine.begin() as conn:
            conn.execute(text("UPDATE experiment_runs SET ended_at = :ts WHERE experiment_id = :eid"), {"ts": ts, "eid": exp_id})
