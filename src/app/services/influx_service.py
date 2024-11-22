from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import logging
import config
from typing import Dict, Any
import time


class InfluxService:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.client = InfluxDBClient(
            url=config.INFLUXDB_URL,
            token=config.INFLUXDB_TOKEN,
            org=config.INFLUXDB_ORG,
            enable_gzip=config.INFLUXDB_ENABLE_GZIP,
        )
        self.write_api = self.client.write_api(
            write_options=SYNCHRONOUS,
            batch_size=config.INFLUXDB_BATCH_SIZE,
            flush_interval=config.INFLUXDB_FLUSH_INTERVAL,
        )

    def write_point(self, point: Point, mac: str, data_type: str) -> None:
        try:
            self.logger.debug(
                f"Preparing to write {data_type} data for device {mac}: {point.to_line_protocol()}"
            )
            self.write_api.write(
                bucket=config.INFLUXDB_BUCKET,
                org=config.INFLUXDB_ORG,
                record=point,
                write_precision="s",
            )
            self.logger.debug(f"Wrote {data_type} data for device {mac}")
        except Exception as e:
            self.logger.error(f"Failed to write {data_type} data for device {mac}: {e}")

    def close(self):
        if hasattr(self, "write_api"):
            self.logger.info("Closing InfluxDB write API...")
            self.write_api.close()
        if hasattr(self, "client"):
            self.logger.info("Closing InfluxDB client...")
            self.client.close()
