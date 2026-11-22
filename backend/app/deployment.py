"""The sole production startup path: validate -> migrate -> one API process."""

import logging
from logging.config import dictConfig
import os
from pathlib import Path
import argparse
from zoneinfo import ZoneInfo

from alembic import command
from alembic.config import Config
import uvicorn

from app.core.config import get_settings
from app.core.logging import production_log_config


def main(*, check_only: bool = False) -> None:
    log_config = production_log_config()
    dictConfig(log_config)
    logger = logging.getLogger(__name__)
    try:
        settings = get_settings()
        if settings.app_env != "production":
            raise ValueError("Production startup requires APP_ENV=production")
        port = int(os.environ.get("PORT", "8000"))
        if not 1 <= port <= 65535:
            raise ValueError("Invalid PORT")
        trusted = os.environ.get("FORWARDED_ALLOW_IPS", "127.0.0.1")
        if "*" in trusted:
            raise ValueError("Explicit trusted proxy addresses are required")
        ZoneInfo(settings.timezone)
        if check_only:
            return
        # Config without a logging ini preserves the safe production handlers.
        config = Config()
        config.set_main_option("script_location", str(Path(__file__).resolve().parents[1] / "alembic"))
        command.upgrade(config, "head")
    except Exception:
        logger.exception("production_startup_failed")
        raise SystemExit(1) from None
    uvicorn.run(
        "app.main:app", host="0.0.0.0", port=port, workers=1, reload=False,
        proxy_headers=True, forwarded_allow_ips=trusted, access_log=False,
        log_config=log_config,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Validate config without migration or startup")
    main(check_only=parser.parse_args().check)
