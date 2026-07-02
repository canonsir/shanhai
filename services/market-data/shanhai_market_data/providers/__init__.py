"""Public (free) market data providers — M3.2 Data Acquisition Foundation.

Each module here is a peer implementation of ``PublicMarketDataProvider``.
ShanHai does not bind to any single vendor: EastMoney and CNInfo are the first
free, no-token adapters; commercial adapters (Tushare / Wind / JoinQuant) sit at
the same level and are optional.
"""

from shanhai_market_data.providers.cninfo import CninfoAnnouncementProvider
from shanhai_market_data.providers.eastmoney import EastMoneyProvider

__all__ = [
    "CninfoAnnouncementProvider",
    "EastMoneyProvider",
]
