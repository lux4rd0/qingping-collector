import paho.mqtt.client as mqtt
import logging
import uuid
import time
import json
import signal
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
import config
from enum import Enum


class MessageType(Enum):
    SENSOR_DATA = "17"
    DIAGNOSTIC = "13"


@dataclass
class WifiInfo:
    ap_name: Optional[str] = None
    signal: Optional[float] = None
    channel: Optional[int] = None
    ap_mac: Optional[str] = None

    @classmethod
    def from_string(cls, wifi_info: str) -> "WifiInfo":
        try:
            ap_name, signal, channel, ap_mac = wifi_info.split(",")
            return cls(
                ap_name=ap_name,
                signal=float(signal),
                channel=int(channel),
                ap_mac=ap_mac.replace(":", ""),
            )
        except (ValueError, IndexError) as e:
            logging.warning(f"Failed to parse wifi info: {e}")
            return cls()


class QingpingMQTTCollector:
    def __init__(self):
        self.should_reconnect = True
        self.running = True
        self._setup_logging()
        self._setup_influxdb()
        self._setup_mqtt()

    def _setup_logging(self) -> None:
        """Initialize logging configuration."""
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT
        )
        self.logger = logging.getLogger(__name__)

    def _setup_influxdb(self) -> None:
        """Initialize InfluxDB connection."""
        self.validate_config()
        self.influx_client = InfluxDBClient(
            url=config.INFLUXDB_URL,
            token=config.INFLUXDB_TOKEN,
            org=config.INFLUXDB_ORG,
            enable_gzip=config.INFLUXDB_ENABLE_GZIP,
        )
        self.write_api = self.influx_client.write_api(
            write_options=SYNCHRONOUS,
            batch_size=config.INFLUXDB_BATCH_SIZE,
            flush_interval=config.INFLUXDB_FLUSH_INTERVAL,
        )

    def _setup_mqtt(self) -> None:
        """Initialize MQTT client configuration."""
        unique_id = f"MQTTCollector-{uuid.uuid4()}"
        self.logger.debug(f"Generated unique client ID: {unique_id}")

        self.client = mqtt.Client(
            client_id=unique_id,
            protocol=mqtt.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        # Enable MQTT keepalive monitoring
        self.client.enable_logger()
        self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

        # Set up TLS if configured
        if config.MQTT_USE_TLS:
            self.client.tls_set()

        # Set callbacks
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message

    def validate_config(self) -> None:
        """Validate configuration with detailed error messages."""
        required_config = {
            "MQTT_BROKER_ADDRESS": config.MQTT_BROKER_ADDRESS,
            "MQTT_BROKER_PORT": config.MQTT_BROKER_PORT,
            "MQTT_USERNAME": config.MQTT_USERNAME,
            "MQTT_PASSWORD": config.MQTT_PASSWORD,
            "INFLUXDB_URL": config.INFLUXDB_URL,
            "INFLUXDB_TOKEN": config.INFLUXDB_TOKEN,
            "INFLUXDB_ORG": config.INFLUXDB_ORG,
            "INFLUXDB_BUCKET": config.INFLUXDB_BUCKET,
        }

        missing = [key for key, value in required_config.items() if not value]
        if missing:
            raise EnvironmentError(
                f"Missing required configuration: {', '.join(missing)}"
            )

        self.logger.info("Configuration validated successfully")
        self._log_config(required_config)

    def _log_config(self, config_dict: Dict[str, Any]) -> None:
        """Log configuration values with sensitive data masked."""
        sensitive_fields = {"PASSWORD", "TOKEN"}
        for key, value in config_dict.items():
            if any(field in key for field in sensitive_fields):
                masked_value = f"{str(value)[:4]}..." if value else None
                self.logger.info(f"{key}: {masked_value}")
            else:
                self.logger.info(f"{key}: {value}")

    def process_diagnostic_data(self, mac: str, data: Dict[str, Any]) -> None:
        """Process and store diagnostic data."""
        try:
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
            )

            if wifi_info.signal is not None:
                point.field("wifi_signal", wifi_info.signal)
            if wifi_info.channel is not None:
                point.field("wifi_channel", float(wifi_info.channel))

            point.field("timezone", float(data.get("timezone", 0)))
            point.time(timestamp, write_precision="s")

            self._write_to_influx(point, mac, "diagnostic")

        except Exception as e:
            self.logger.error(f"Error processing diagnostic data for device {mac}: {e}")

    def process_sensor_data(self, mac: str, data: Dict[str, Any]) -> None:
        """Process and store sensor data."""
        try:
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
            self._write_to_influx(point, mac, "sensor")

        except Exception as e:
            self.logger.error(f"Error processing sensor data for device {mac}: {e}")

    def _write_to_influx(self, point: Point, mac: str, data_type: str) -> None:
        """Write data point to InfluxDB with error handling."""
        try:
            self.write_api.write(
                bucket=config.INFLUXDB_BUCKET,
                org=config.INFLUXDB_ORG,
                record=point,
                write_precision="s",
            )
            self.logger.debug(f"Wrote {data_type} data for device {mac}")
        except Exception as e:
            self.logger.error(f"Failed to write {data_type} data for device {mac}: {e}")

    def on_message(self, client, userdata, msg) -> None:
        """Handle incoming MQTT messages."""
        try:
            payload = json.loads(msg.payload.decode())
            self.logger.debug(f"Received message on topic {msg.topic}: {payload}")

            msg_type = payload.get("type")

            if msg_type == MessageType.SENSOR_DATA.value:
                if not "sensorData" in payload:
                    return

                mac = payload.get("wifi_mac") or payload.get("mac")
                if not mac:
                    self.logger.error(
                        f"No MAC address found in sensor data payload: {json.dumps(payload, indent=2)}"
                    )
                    return

                for sensor_data in payload["sensorData"]:
                    self.process_sensor_data(mac, sensor_data)

            elif msg_type == MessageType.DIAGNOSTIC.value:
                mac = payload.get("wifi_mac") or payload.get("mac")
                if not mac:
                    self.logger.error(
                        f"No MAC address found in diagnostic payload: {json.dumps(payload, indent=2)}"
                    )
                    return

                self.process_diagnostic_data(mac, payload)

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message: {e}\nRaw payload: {msg.payload}")
        except Exception as e:
            self.logger.error(
                f"Message processing error: {e}\nPayload: {json.dumps(payload, indent=2)}"
            )

    def on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        """Handle MQTT connection events."""
        if reason_code == mqtt.CONNACK_ACCEPTED:
            self.logger.info("Connected to MQTT Broker")
            client.subscribe(config.MQTT_TOPIC)
            self.logger.info(f"Subscribed to {config.MQTT_TOPIC}")
        else:
            self.logger.error(f"Connection failed: {reason_code}")

    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ) -> None:
        """Handle MQTT disconnection events."""
        if reason_code != 0:
            self.logger.warning(f"Unexpected disconnection: {reason_code}")
            if self.should_reconnect:
                self.reconnect()
        else:
            self.logger.info("Disconnected from MQTT Broker")

    def reconnect(self) -> None:
        """Implement exponential backoff reconnection strategy."""
        backoff = 1
        attempt = 0

        while self.should_reconnect and attempt < config.MAX_RECONNECT_ATTEMPTS:
            try:
                self.logger.info(
                    f"Reconnection attempt {attempt + 1}/{config.MAX_RECONNECT_ATTEMPTS} (backoff: {backoff}s)"
                )
                self.client.reconnect()
                self.logger.info("Reconnected successfully")
                return
            except Exception as e:
                self.logger.error(f"Reconnection failed: {e}")
                attempt += 1
                time.sleep(backoff)
                backoff = min(backoff * 2, config.MAX_RECONNECT_DELAY)

        self.logger.error("Max reconnection attempts reached")
        self.stop()

    def signal_handler(self, signum, frame) -> None:
        """Handle system signals gracefully."""
        self.logger.info(f"Received signal {signum}")
        self.stop()

    def start(self) -> None:
        """Start the collector service."""
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            self.logger.info("Starting MQTT Collector")
            self.client.connect(
                config.MQTT_BROKER_ADDRESS,
                config.MQTT_BROKER_PORT,
                keepalive=config.MQTT_KEEPALIVE,
            )
            self.client.loop_forever()
        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        """Stop the collector service gracefully."""
        self.logger.info("Initiating shutdown...")
        self.should_reconnect = False
        self.running = False

        try:
            if hasattr(self, "write_api"):
                self.logger.info("Closing InfluxDB write API...")
                self.write_api.close()

            if hasattr(self, "influx_client"):
                self.logger.info("Closing InfluxDB client...")
                self.influx_client.close()

            if hasattr(self, "client"):
                self.logger.info("Disconnecting MQTT client...")
                self.client.disconnect()

            self.logger.info("Shutdown complete")

        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")


if __name__ == "__main__":
    collector = None
    try:
        collector = QingpingMQTTCollector()
        collector.start()
    except Exception as e:
        logging.error(f"Fatal error: {e}")
    finally:
        if collector:
            collector.stop()
