import logging
import json
import time
import signal
from typing import Set
import config
from models.message_type import MessageType
from services.mqtt_service import MQTTService
from services.influx_service import InfluxService
from services.data_processor import DataProcessor


class QingpingMQTTCollector:
    def __init__(self):
        self.running = True
        self.detected_devices: Set[str] = set()
        self._setup_logging()
        self._setup_services()

    def _setup_logging(self) -> None:
        logging.basicConfig(
            level=getattr(logging, config.LOG_LEVEL), format=config.LOG_FORMAT
        )
        self.logger = logging.getLogger(__name__)

    def _setup_services(self) -> None:
        self.validate_config()
        self.influx_service = InfluxService()
        self.data_processor = DataProcessor(self.influx_service)
        self.mqtt_service = MQTTService(self.on_message)

    def validate_config(self) -> None:
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
        self.logger.info(f"USE_CURRENT_TIME: {config.USE_CURRENT_TIME}")
        self._log_config(required_config)

    def _log_config(self, config_dict) -> None:
        sensitive_fields = {"PASSWORD", "TOKEN"}
        for key, value in config_dict.items():
            if any(field in key for field in sensitive_fields):
                masked_value = f"{str(value)[:4]}..." if value else None
                self.logger.info(f"{key}: {masked_value}")
            else:
                self.logger.info(f"{key}: {value}")

    def register_new_device(self, mac: str) -> None:
        try:
            self.logger.info(f"Registering new device {mac}")
            payload = {
                "id": 1,
                "need_ack": 1,
                "type": "17",
                "setting": {
                    "report_interval": config.DEFAULT_REPORT_INTERVAL,
                    "collect_interval": config.DEFAULT_COLLECT_INTERVAL,
                },
            }
            topic = f"qingping/{mac}/down"
            self.mqtt_service.publish(topic, payload)
        except Exception as e:
            self.logger.error(f"Failed to register device {mac}: {e}")

    def on_message(self, client, userdata, msg) -> None:
        try:
            payload = json.loads(msg.payload.decode())
            self.logger.debug(f"Received message on topic {msg.topic}: {payload}")

            mac = payload.get("wifi_mac") or payload.get("mac")
            if mac and mac not in self.detected_devices:
                self.logger.info(f"Detected new device: {mac}")
                self.detected_devices.add(mac)
                self.register_new_device(mac)

            msg_type = payload.get("type")

            if msg_type == MessageType.SENSOR_DATA.value:
                if not "sensorData" in payload:
                    return

                if not mac:
                    self.logger.error(
                        f"No MAC address found in sensor data payload: {json.dumps(payload, indent=2)}"
                    )
                    return

                for sensor_data in payload["sensorData"]:
                    self.data_processor.process_sensor_data(mac, sensor_data)

            elif msg_type == MessageType.DIAGNOSTIC.value:
                if not mac:
                    self.logger.error(
                        f"No MAC address found in diagnostic payload: {json.dumps(payload, indent=2)}"
                    )
                    return

                self.data_processor.process_diagnostic_data(mac, payload)

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message: {e}\nRaw payload: {msg.payload}")
        except Exception as e:
            self.logger.error(
                f"Message processing error: {e}\nPayload: {json.dumps(payload, indent=2)}"
            )

    def signal_handler(self, signum, frame) -> None:
        self.logger.info(f"Received signal {signum}")
        self.stop()

    def start(self) -> None:
        try:
            signal.signal(signal.SIGINT, self.signal_handler)
            signal.signal(signal.SIGTERM, self.signal_handler)

            self.logger.info("Starting MQTT Collector")
            self.mqtt_service.connect()

            while self.running:
                time.sleep(1)

        except KeyboardInterrupt:
            self.logger.info("Interrupted by user")
        except Exception as e:
            self.logger.error(f"Fatal error: {e}")
        finally:
            self.stop()

    def stop(self) -> None:
        self.logger.info("Initiating shutdown...")
        self.running = False
        try:
            self.mqtt_service.disconnect()
            self.influx_service.close()
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
