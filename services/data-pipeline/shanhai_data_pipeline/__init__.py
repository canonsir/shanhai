"""ShanHai Data Pipeline。

未来接入：财报 / 公告 / 新闻 / 政策 / 行情数据。
Phase 0 仅定义 Source 抽象骨架，不实现具体采集逻辑。
"""

from shanhai_data_pipeline.source import DataSource

__all__ = ["DataSource"]
