import paho.mqtt.client as mqtt
import logging
import uuid
import json
import time
import config
from typing import Optional, Callable, Dict, Any


class MQTTService:
    def __init__(self, on_message_callback: Callable):
        self.logger = logging.getLogger(__name__)
        self.should_reconnect = True
        self.on_message_callback = on_message_callback
        self._setup_client()

    def _setup_client(self) -> None:
        unique_id = f"MQTTCollector-{uuid.uuid4()}"
        self.logger.debug(f"Generated unique client ID: {unique_id}")

        self.client = mqtt.Client(
            client_id=unique_id,
            protocol=mqtt.MQTTv5,
            callback_api_version=mqtt.CallbackAPIVersion.VERSION2,
        )

        self.client.enable_logger()
        self.client.username_pw_set(config.MQTT_USERNAME, config.MQTT_PASSWORD)

        if config.MQTT_USE_TLS:
            self.client.tls_set()

        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect
        self.client.on_message = self.on_message_callback

    def connect(self) -> None:
        self.client.connect(
            config.MQTT_BROKER_ADDRESS,
            config.MQTT_BROKER_PORT,
            keepalive=config.MQTT_KEEPALIVE,
        )
        self.client.loop_start()

    def disconnect(self) -> None:
        self.should_reconnect = False
        if hasattr(self, "client"):
            self.logger.info("Disconnecting MQTT client...")
            self.client.disconnect()

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        try:
            self.client.publish(topic, json.dumps(payload))
            self.logger.info(f"Published to {topic}: {payload}")
        except Exception as e:
            self.logger.error(f"Failed to publish to {topic}: {e}")

    def on_connect(self, client, userdata, flags, reason_code, properties) -> None:
        if reason_code == mqtt.CONNACK_ACCEPTED:
            self.logger.info("Connected to MQTT Broker")
            client.subscribe(config.MQTT_TOPIC)
            self.logger.info(f"Subscribed to {config.MQTT_TOPIC}")
        else:
            self.logger.error(f"Connection failed: {reason_code}")

    def on_disconnect(
        self, client, userdata, disconnect_flags, reason_code, properties
    ) -> None:
        if reason_code != 0:
            self.logger.warning(f"Unexpected disconnection: {reason_code}")
            if self.should_reconnect:
                self.reconnect()
        else:
            self.logger.info("Disconnected from MQTT Broker")

    def reconnect(self) -> None:
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
