from influxdb_client import Point
import logging
import time
import config
from typing import Dict, Any
from models.wifi_info import WifiInfo
from services.influx_service import InfluxService


class DataProcessor:
    def __init__(self, influx_service: InfluxService):
        self.logger = logging.getLogger(__name__)
        self.influx_service = influx_service

    def process_diagnostic_data(self, mac: str, data: Dict[str, Any]) -> None:
        try:
            if config.USE_CURRENT_TIME:
                timestamp = int(time.time())
                self.logger.debug(
                    f"Using current time for diagnostic data from device {mac}."
                )
            else:
                timestamp = int(data["timestamp"])

            wifi_info = WifiInfo.from_string(data["wifi_info"])

            point = (
                Point("diagnostic")
                .tag("device_mac", mac)
                .tag("sw_version", data.get("sw_version", ""))
                .tag("module_version", data.get("module_version", ""))
                .tag("hw_version", data.get("hw_version", ""))
                .tag("wifi_ap_name", wifi_info.ap_name)
                .tag("wifi_ap_mac", wifi_info.ap_mac)
                .field("timezone", float(data.get("timezone", 0)))
                .time(timestamp, write_precision="s")
            )

            if wifi_info.signal is not None:
                point.field("wifi_signal", wifi_info.signal)
            if wifi_info.channel is not None:
                point.field("wifi_channel", float(wifi_info.channel))

            self.influx_service.write_point(point, mac, "diagnostic")

        except Exception as e:
            self.logger.error(f"Error processing diagnostic data for device {mac}: {e}")

    def process_sensor_data(self, mac: str, data: Dict[str, Any]) -> None:
        try:
            if config.USE_CURRENT_TIME:
                timestamp = int(time.time())
                self.logger.debug(
                    f"Using current time for device {mac} due to configuration."
                )
            else:
                timestamp = int(data["timestamp"]["value"])

            point = Point("sensor").tag("device_mac", mac)
            metrics = ["temperature", "humidity", "co2", "pm25", "pm10", "battery"]

            for metric in metrics:
                if metric in data:
                    try:
                        value = float(data[metric]["value"])
                        point.field(metric, value)
                    except (TypeError, ValueError) as e:
                        self.logger.warning(
                            f"Invalid {metric} value for device {mac}: {e}"
                        )

            point.time(timestamp, write_precision="s")
            self.influx_service.write_point(point, mac, "sensor")

        except Exception as e:
            self.logger.error(f"Error processing sensor data for device {mac}: {e}")
