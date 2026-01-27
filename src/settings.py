from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

# Base directory of the project
BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables from .env file
ENV_PATH = BASE_DIR.parent / ".env"
if ENV_PATH.exists():
    load_dotenv(dotenv_path=ENV_PATH)
    print(f"Loaded environment variables from {ENV_PATH}")
else:
    print("Warning: .env file not found. Using default or system environment variables.")


@lru_cache(maxsize=1)
def get_config() -> Dict[str, Any]:
    """
    Loads configuration from environment variables and provides it as a dictionary.
    The result is cached for performance.

    Returns:
        A dictionary containing all configuration parameters.
    """
    return {
        # Database
        "mysql_host": os.getenv("MYSQL_HOST", "localhost"),
        "mysql_port": int(os.getenv("MYSQL_PORT", 3306)),
        "mysql_db": os.getenv("MYSQL_DB", "icn_airport_analysis"),
        "mysql_user": os.getenv("MYSQL_USER", "airport_user"),
        "mysql_password": os.getenv("MYSQL_PASSWORD", "changeme"),

        # API Keys
        "service_key": os.getenv("SERVICE_KEY"),
        "kma_service_key": os.getenv("KMA_SERVICE_KEY"),

        # System & Model Versioning
        "system_version": os.getenv("SYSTEM_VERSION", "v2.1.0"),
        "transform_version": os.getenv("TRANSFORM_VERSION", "t2026.01.16-r3"),

        # General Settings
        "log_level": os.getenv("LOG_LEVEL", "INFO"),
        "random_seed": int(os.getenv("RANDOM_SEED", 42)),
    }


def get_service_key(key_type: str = "default") -> str:
    """
    Retrieves a specific API service key from the configuration.

    Args:
        key_type: The type of key to retrieve ('default' for B551177, 'kma' for KMA).

    Returns:
        The requested API service key.

    Raises:
        ValueError: If the requested key is not found in the configuration.
    """
    cfg = get_config()
    key = None
    if key_type == "kma":
        key = cfg.get("kma_service_key") or cfg.get("service_key")
    else: # 'default'
        key = cfg.get("service_key")

    if not key:
        raise ValueError(f"Service key for '{key_type}' not found. Please check your .env file.")
    return key


# Static constants for the airport layout
RAILROAD_TO_CHECKIN = {
    "인천공항1터미널역": {
        "A": 15.33, "B": 14.33, "C": 13.33, "D": 12.33, "E": 11.33, "F": 10.33,
        "G": 9.33,  "H": 10.33, "J": 11.33, "K": 12.33, "L": 13.33, "M": 14.33, "N": 15.33
    }
}
BUS_TO_CHECKIN = {
    "3층_1번_정차구역": {"A": 4.23, "B": 3.42, "C": 4.23, "D": 5.05, "E": 5.87, "F": 6.68, "G": 7.5, "H": 8.97, "J": 9.78, "K": 10.6, "L": 11.42, "M": 12.23, "N": 13.05},
    "3층_2번_정차구역": {"A": 3.57, "B": 2.75, "C": 3.57, "D": 4.38, "E": 5.2, "F": 6.02, "G": 6.83, "H": 8.3, "J": 9.12, "K": 9.93, "L": 10.75, "M": 11.57, "N": 12.38},
    "3층_3번_정차구역": {"A": 4.38, "B": 3.57, "C": 2.75, "D": 3.57, "E": 4.38, "F": 5.2, "G": 6.02, "H": 7.48, "J": 8.3, "K": 9.12, "L": 9.93, "M": 10.75, "N": 11.57},
    "3층_4번_정차구역": {"A": 5.05, "B": 4.23, "C": 3.4, "D": 4.32, "E": 3.42, "F": 4.23, "G": 5.05, "H": 6.52, "J": 7.17, "K": 8.15, "L": 8.97, "M": 9.78, "N": 10.6},
    "3층_5번_정차구역": {"A": 6.02, "B": 5.2, "C": 4.38, "D": 3.57, "E": 2.75, "F": 3.57, "G": 4.38, "H": 5.85, "J": 6.67, "K": 7.48, "L": 8.3, "M": 9.12, "N": 9.93},
    "3층_6번_정차구역": {"A": 6.83, "B": 6.02, "C": 5.2, "D": 4.38, "E": 3.57, "F": 2.75, "G": 3.57, "H": 5.03, "J": 5.85, "K": 6.67, "L": 7.48, "M": 8.3, "N": 9.12},
    "3층_7번_정차구역": {"A": 7.65, "B": 6.83, "C": 6.02, "D": 5.2, "E": 4.38, "F": 3.57, "G": 2.75, "H": 4.22, "J": 5.03, "K": 5.85, "L": 6.67, "M": 7.48, "N": 8.3},
    "3층_8번_정차구역": {"A": 8.48, "B": 7.67, "C": 6.85, "D": 6.03, "E": 5.22, "F": 4.4, "G": 3.58, "H": 3.38, "J": 4.2, "K": 5.02, "L": 5.83, "M": 6.65, "N": 7.47},
    "3층_9번_정차구역": {"A": 9.15, "B": 8.33, "C": 7.52, "D": 6.7, "E": 5.88, "F": 5.07, "G": 4.25, "H": 4.23, "J": 3.42, "K": 4.23, "L": 5.05, "M": 5.87, "N": 6.68},
    "3층_10번_정차구역": {"A": 9.93, "B": 9.12, "C": 8.3, "D": 7.48, "E": 6.67, "F": 5.85, "G": 5.03, "H": 3.57, "J": 2.75, "K": 3.57, "L": 4.38, "M": 5.2, "N": 6.02},
    "3층_11번_정차구역": {"A": 10.6, "B": 9.78, "C": 8.97, "D": 8.15, "E": 7.33, "F": 6.52, "G": 5.7, "H": 4.23, "J": 3.42, "K": 4.23, "L": 5.05, "M": 5.87, "N": 6.68},
    "3층_12번_정차구역": {"A": 11.57, "B": 10.75, "C": 9.93, "D": 9.12, "E": 8.3, "F": 7.48, "G": 6.67, "H": 5.2, "J": 2.75, "K": 3.57, "L": 4.38, "M": 5.2, "N": 6.02},
    "3층_13번_정차구역": {"A": 12.38, "B": 11.57, "C": 10.75, "D": 9.93, "E": 9.12, "F": 8.3, "G": 7.48, "H": 6.02, "J": 5.2, "K": 4.38, "L": 3.57, "M": 2.75, "N": 3.57},
    "3층_14번_정차구역": {"A": 13.05, "B": 12.23, "C": 11.42, "D": 10.6, "E": 9.78, "F": 8.97, "G": 8.15, "H": 6.68, "J": 5.87, "K": 5.05, "L": 4.23, "M": 3.42, "N": 4.23}
}
TAXI_TO_CHECKIN = {
    "3층_1번_정차구역": {"A": 3.23, "B": 2.42, "C": 3.23, "D": 4.05, "E": 4.87, "F": 5.68, "G": 6.5, "H": 7.97, "J": 8.78, "K": 9.6, "L": 10.42, "M": 11.23, "N": 12.05},
    "3층_2번_정차구역": {"A": 2.57, "B": 1.75, "C": 2.57, "D": 3.38, "E": 4.2, "F": 5.02, "G": 5.83, "H": 7.3, "J": 8.12, "K": 8.93, "L": 9.75, "M": 10.57, "N": 11.38},
    "3층_3번_정차구역": {"A": 3.38, "B": 2.57, "C": 1.75, "D": 2.57, "E": 3.38, "F": 4.2, "G": 5.02, "H": 6.48, "J": 7.3, "K": 8.12, "L": 8.93, "M": 9.75, "N": 10.57},
    "3층_4번_정차구역": {"A": 4.05, "B": 3.23, "C": 2.4, "D": 3.32, "E": 2.42, "F": 3.23, "G": 4.05, "H": 5.52, "J": 6.17, "K": 7.15, "L": 7.97, "M": 8.78, "N": 9.6},
    "3층_5번_정차구역": {"A": 5.02, "B": 4.2, "C": 3.38, "D": 2.57, "E": 1.75, "F": 2.57, "G": 3.38, "H": 4.85, "J": 5.67, "K": 6.48, "L": 7.3, "M": 8.12, "N": 8.93},
    "3층_6번_정차구역": {"A": 5.83, "B": 5.02, "C": 4.2, "D": 3.38, "E": 2.57, "F": 1.75, "G": 2.57, "H": 4.03, "J": 4.85, "K": 5.67, "L": 6.48, "M": 7.3, "N": 8.12},
    "3층_7번_정차구역": {"A": 6.65, "B": 5.83, "C": 5.02, "D": 4.2, "E": 3.38, "F": 2.57, "G": 1.75, "H": 3.22, "J": 4.03, "K": 4.85, "L": 5.67, "M": 6.48, "N": 7.3},
    "3층_8번_정차구역": {"A": 7.48, "B": 6.67, "C": 5.85, "D": 5.03, "E": 4.22, "F": 3.4, "G": 2.58, "H": 2.38, "J": 3.2, "K": 4.02, "L": 4.83, "M": 5.65, "N": 6.47},
    "3층_9번_정차구역": {"A": 8.15, "B": 7.33, "C": 6.52, "D": 5.7, "E": 4.88, "F": 4.07, "G": 3.25, "H": 3.23, "J": 2.42, "K": 3.23, "L": 4.05, "M": 4.87, "N": 5.68},
    "3층_10번_정차구역": {"A": 8.93, "B": 8.12, "C": 7.3, "D": 6.48, "E": 5.67, "F": 4.85, "G": 4.03, "H": 2.57, "J": 1.75, "K": 2.57, "L": 3.38, "M": 4.2, "N": 5.02},
    "3층_11번_정차구역": {"A": 9.6, "B": 8.78, "C": 7.97, "D": 7.15, "E": 6.33, "F": 5.52, "G": 4.7, "H": 3.23, "J": 2.42, "K": 3.23, "L": 4.05, "M": 4.87, "N": 5.68},
    "3층_12번_정차구역": {"A": 10.57, "B": 9.75, "C": 8.93, "D": 8.12, "E": 7.3, "F": 6.48, "G": 5.67, "H": 4.2, "J": 1.75, "K": 2.57, "L": 3.38, "M": 4.2, "N": 5.02},
    "3층_13번_정차구역": {"A": 11.38, "B": 10.57, "C": 9.75, "D": 8.93, "E": 8.12, "F": 7.3, "G": 6.48, "H": 5.02, "J": 4.2, "K": 3.38, "L": 2.57, "M": 1.75, "N": 2.57},
    "3층_14번_정차구역": {"A": 12.05, "B": 11.23, "C": 10.42, "D": 9.6, "E": 8.78, "F": 7.97, "G": 7.15, "H": 5.68, "J": 4.87, "K": 4.05, "L": 3.23, "M": 2.42, "N": 3.23}
}
PARKING_TO_CHECKIN = {
    "단기주차장_지하2층_A구역": {"A": 8.03, "B": 6.15, "C": 7.02, "D": 7.05, "E": 5.02, "F": 5.08, "G": 6.05, "H": 7.12, "J": 8.07, "K": 8.13, "L": 9.1, "M": 10.07, "N": 11.0},
    "단기주차장_지하2층_H구역": {"A": 11.13, "B": 11.03, "C": 10.08, "D": 9.13, "E": 9.03, "F": 8.08, "G": 7.13, "H": 6.08, "J": 5.13, "K": 3.1, "L": 4.15, "M": 5.08, "N": 5.13}
}
CHECKIN_TO_GATE = {
    "DG1_W": 10, "DG1_E": 10, "DG2_W": 9,  "DG2_E": 9, "DG3_W": 8,  "DG3_E": 7,
    "DG4_W": 6,  "DG4_E": 6, "DG5_W": 6,  "DG5_E": 6, "DG6_W": 9,  "DG6_E": 10
}
GATE_OPERATING_HOURS = {
    "DG1_W": "24시간", "DG1_E": "24시간", "DG2_W": "06:00-20:00", "DG2_E": "06:00-20:00",
    "DG3_W": "00:00-24:00", "DG3_E": "00:00-24:00", "DG4_W": "06:30-20:00", "DG4_E": "06:30-20:00",
    "DG5_W": "05:00-22:00", "DG5_E": "05:00-22:00", "DG6_W": "24시간", "DG6_E": "24시간"
}
GATES_T1 = list(CHECKIN_TO_GATE.keys())
CHECKIN_COUNTERS = ["A", "B", "C", "D", "E", "F", "G", "H", "J", "K", "L", "M", "N"]
TERMINAL_ID = "P01"
TERMINAL_NAME = "제1터미널"