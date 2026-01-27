from __future__ import annotations

import logging
import random

import typer

from src.db import get_engine, run_migrations
from src.db.feature_store import FeatureStore
from src.models.personalization import PassengerProfile
from src.pipeline.engine import AirportOptimizationEngine
from src.pipeline.experiments import ExperimentConfig, ExperimentRunner
from src.settings import BUS_TO_CHECKIN, CHECKIN_COUNTERS, PARKING_TO_CHECKIN, RAILROAD_TO_CHECKIN, TAXI_TO_CHECKIN
from src.utils.helpers import parse_time_hhmm, print_recommendations

logger = logging.getLogger("airport.cli")
app = typer.Typer(help="Airport CVaR Optimization CLI")


def get_engine_and_run_migrations():
    """Initializes DB engine and runs migrations."""
    try:
        engine = get_engine()
        run_migrations()
        return engine
    except Exception as e:
        logger.critical(f"Database setup failed: {e}")
        raise typer.Exit(code=1)


@app.command(name="interactive")
def run_interactive():
    """Run the system in interactive mode for live recommendations."""
    engine = get_engine_and_run_migrations()
    fs = FeatureStore(engine)
    app_engine = AirportOptimizationEngine(engine, fs)
    logger.info("Starting interactive mode...")

    while True:
        typer.secho("\n--- Airport Departure Optimization System ---", fg=typer.colors.CYAN)
        choice = typer.prompt(
            "Select Mode:\n"
            "1. Q1: From Check-in\n"
            "2. Q2: From Railroad\n"
            "3. Q3: From Bus/Taxi\n"
            "4. Q4: From Parking\n"
            "9. Refresh External Data\n"
            "0. Exit\n"
            "Choice"
        )
        if choice == "0":
            break
        if choice == "9":
            app_engine.external.fetch_and_process_metar()
            app_engine.last_passenger_t1 = app_engine.external.fetch_and_process_passenger_forecast()
            typer.secho("External data refreshed.", fg=typer.colors.GREEN)
            continue

        profile = _prompt_profile()
        req_time = _prompt_required_gate_time()
        
        result = None
        if choice == "1":
            counter = typer.prompt("Current check-in counter (A-N)", default=random.choice(CHECKIN_COUNTERS))
            result = app_engine.recommend_route(profile, "checkin", counter, req_time)
        elif choice == "2":
            station = list(RAILROAD_TO_CHECKIN.keys())[0]
            result = app_engine.recommend_route(profile, "railroad", station, req_time)
        elif choice == "3":
            mode = typer.prompt("Mode (bus/taxi)", default="taxi")
            loc = random.choice(list(BUS_TO_CHECKIN.keys()) if mode == "bus" else list(TAXI_TO_CHECKIN.keys()))
            result = app_engine.recommend_route(profile, mode, loc, req_time)
        elif choice == "4":
            loc = random.choice(list(PARKING_TO_CHECKIN.keys()))
            occ = typer.prompt("Parking occupancy (0-1, blank=random)", default="", show_default=False)
            result = app_engine.recommend_route(profile, "parking", loc, req_time, parking_occupancy=float(occ) if occ else None)

        if result:
            print_recommendations(f"Top 3 Routes (Mode: Q{choice})", result)


@app.command(name="experiments")
def run_experiments_command(
    duration: int = typer.Option(180, help="Duration of the experiment in minutes."),
    interval: int = typer.Option(5, help="Interval between snapshots in minutes."),
    users: int = typer.Option(8, help="Number of simulated users per snapshot."),
    epsilon: float = typer.Option(0.2, help="Epsilon for user choice simulation (1-epsilon = acceptance)."),
):
    """Run the automated offline replay experiments (E1-E6)."""
    engine = get_engine_and_run_migrations()
    fs = FeatureStore(engine)
    app_engine = AirportOptimizationEngine(engine, fs)
    runner = ExperimentRunner(app_engine, engine)
    config = ExperimentConfig(
        duration_minutes=duration,
        interval_minutes=interval,
        users_per_snapshot=users,
        epsilon=epsilon,
    )
    typer.secho(f"Starting experiments with config: {config}", fg=typer.colors.YELLOW)
    exp_id = runner.run(config)
    typer.secho(f"✅ Experiments complete. Experiment ID: {exp_id}", fg=typer.colors.GREEN)


def _prompt_profile() -> PassengerProfile:
    typer.secho("\n[Passenger Profile]", fg=typer.colors.MAGENTA)
    age = typer.prompt("Age (child/adult/senior) [blank=impute]", default="", show_default=False)
    mobility = typer.prompt("Mobility (normal/low) [blank=impute]", default="", show_default=False)
    bags = typer.prompt("Bags (number) [blank=impute]", default="", show_default=False)
    companions = typer.prompt("Companions (number) [blank=impute]", default="", show_default=False)
    return PassengerProfile(
        age_group=age or None, mobility=mobility or None,
        bags=int(bags) if bags else None, companions=int(companions) if companions else None
    )

def _prompt_required_gate_time():
    typer.secho("\n[Flight Timing]", fg=typer.colors.MAGENTA)
    time_str = typer.prompt("Boarding time HH:MM [blank=unknown]", default="", show_default=False)
    return parse_time_hhmm(time_str)


if __name__ == "__main__":
    app()