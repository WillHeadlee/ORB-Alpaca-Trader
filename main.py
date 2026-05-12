"""Entry point — load config, bootstrap env, start trading session."""

import asyncio
import os
import sys
from pathlib import Path

import yaml
from dotenv import load_dotenv

from utils.logger import log

BASE_DIR = Path(__file__).resolve().parent


def load_config() -> dict:
    config_path = BASE_DIR / "config.yaml"
    with open(config_path) as f:
        cfg = yaml.safe_load(f)

    # ALPACA_MODE env var overrides config.yaml
    if mode := os.getenv("ALPACA_MODE"):
        cfg["trading"]["mode"] = mode.lower()

    return cfg


def validate_env() -> None:
    missing = [k for k in ("ALPACA_API_KEY", "ALPACA_SECRET_KEY") if not os.getenv(k)]
    if missing:
        print(f"ERROR: missing environment variables: {', '.join(missing)}")
        print("Copy .env.example to .env and fill in your Alpaca API credentials.")
        sys.exit(1)


async def main() -> None:
    load_dotenv(BASE_DIR / ".env")
    validate_env()

    cfg = load_config()
    mode = cfg["trading"]["mode"]

    if mode == "live":
        print("\n" + "!" * 60)
        print("  WARNING: LIVE TRADING MODE — real money at risk!")
        print("!" * 60)
        answer = input("  Type 'yes' to continue with live trading: ").strip().lower()
        if answer != "yes":
            print("Aborted.")
            return
    else:
        log.info("Running in PAPER trading mode — no real money at risk")

    # Import here so env is loaded before alpaca-py makes any network calls
    from trader.session_manager import SessionManager

    session = SessionManager(cfg)
    await session.run()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("Session interrupted by user")
