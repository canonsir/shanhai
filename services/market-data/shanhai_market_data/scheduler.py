"""Scheduled ingestion runner for Market Data Runtime MVP."""

from __future__ import annotations

import argparse
import time
from dataclasses import dataclass
from datetime import datetime, time as day_time

from shanhai_market_data.factory import default_market_store, default_tushare_provider
from shanhai_market_data.sync import AShareCompanySyncService, DEFAULT_A_SHARE_TARGETS


@dataclass(frozen=True)
class ScheduledIngestionConfig:
    run_at: day_time = day_time(hour=18, minute=30)
    poll_seconds: int = 60
    quote_start_date: str | None = None
    quote_end_date: str | None = None


class TushareScheduledIngestion:
    """Daily Tushare ingestion loop.

    The scheduler is process-local and intentionally simple. Production can run
    it under cron/systemd/container scheduler; the code keeps the ingestion
    boundary deterministic and independent from RuntimeKernel / AgentRunner.
    """

    def __init__(
        self,
        service: AShareCompanySyncService,
        config: ScheduledIngestionConfig | None = None,
    ) -> None:
        self._service = service
        self._config = config or ScheduledIngestionConfig()
        self._last_run_date: str | None = None

    def run_once(self) -> dict:
        report = self._service.sync_companies(
            DEFAULT_A_SHARE_TARGETS,
            quote_start_date=self._config.quote_start_date,
            quote_end_date=self._config.quote_end_date,
        )
        self._last_run_date = datetime.now().date().isoformat()
        return report.model_dump(mode="json")

    def run_forever(self) -> None:
        while True:
            now = datetime.now()
            today = now.date().isoformat()
            if (
                self._last_run_date != today
                and now.time() >= self._config.run_at
            ):
                self.run_once()
            time.sleep(self._config.poll_seconds)


def build_default_scheduler() -> TushareScheduledIngestion:
    store = default_market_store()
    provider = default_tushare_provider()
    service = AShareCompanySyncService(provider, store)
    return TushareScheduledIngestion(service)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run ShanHai Tushare scheduled ingestion")
    parser.add_argument("--once", action="store_true", help="run ingestion once and exit")
    args = parser.parse_args()

    scheduler = build_default_scheduler()
    if args.once:
        print(scheduler.run_once())
    else:
        scheduler.run_forever()


if __name__ == "__main__":
    main()
