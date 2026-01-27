"""
Airport CVaR Optimization Package.

This package contains the complete source code for the real-time, tail-risk-aware
airport departure optimization system.
"""
import logging.config
from pathlib import Path
import yaml

# Setup logging
LOG_CONFIG_PATH = Path(__file__).parent.parent / 'config' / 'logging.yaml'
LOG_DIR = Path(__file__).parent.parent / 'logs'
LOG_DIR.mkdir(exist_ok=True)

if LOG_CONFIG_PATH.exists():
    with open(LOG_CONFIG_PATH, 'rt') as f:
        config = yaml.safe_load(f.read())
    logging.config.dictConfig(config)
else:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("airport")
logger.info("Airport Optimization package initialized.")