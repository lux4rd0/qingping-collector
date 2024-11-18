import os

# MQTT Broker Configuration
MQTT_BROKER_ADDRESS = os.getenv("MQTT_BROKER_ADDRESS")
MQTT_BROKER_PORT = int(os.getenv("MQTT_BROKER_PORT", "1883"))
MQTT_USERNAME = os.getenv("MQTT_USERNAME")
MQTT_PASSWORD = os.getenv("MQTT_PASSWORD")
MQTT_TOPIC = os.getenv("MQTT_TOPIC", "qingping/#")
MQTT_KEEPALIVE = int(os.getenv("MQTT_KEEPALIVE", "60"))
MQTT_USE_TLS = os.getenv("MQTT_USE_TLS", "false").lower() == "true"
MQTT_CLEAN_START = os.getenv("MQTT_CLEAN_START", "true").lower() == "true"

# Reconnection Configuration
MAX_RECONNECT_DELAY = int(os.getenv("MAX_RECONNECT_DELAY", "60"))
MAX_RECONNECT_ATTEMPTS = int(os.getenv("MAX_RECONNECT_ATTEMPTS", "5"))

# InfluxDB Configuration
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086/")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET")
INFLUXDB_BATCH_SIZE = int(os.getenv("INFLUXDB_BATCH_SIZE", "100"))
INFLUXDB_FLUSH_INTERVAL = int(
    os.getenv("INFLUXDB_FLUSH_INTERVAL", "5000")
)  # milliseconds
INFLUXDB_ENABLE_GZIP = os.getenv("INFLUXDB_ENABLE_GZIP", "true").lower() == "true"

# Logging Configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = os.getenv("LOG_FORMAT", "%(asctime)s - %(levelname)s - %(message)s")

# Validate the configuration on import
def validate_port(port: int) -> bool:
    return isinstance(port, int) and 0 <= port <= 65535


def validate_positive_int(value: int, name: str) -> None:
    if value <= 0:
        raise ValueError(f"{name} must be a positive integer")


# Basic validation of numeric values
try:
    validate_port(MQTT_BROKER_PORT)
    validate_positive_int(MQTT_KEEPALIVE, "MQTT_KEEPALIVE")
    validate_positive_int(MAX_RECONNECT_DELAY, "MAX_RECONNECT_DELAY")
    validate_positive_int(MAX_RECONNECT_ATTEMPTS, "MAX_RECONNECT_ATTEMPTS")
    validate_positive_int(INFLUXDB_BATCH_SIZE, "INFLUXDB_BATCH_SIZE")
    validate_positive_int(INFLUXDB_FLUSH_INTERVAL, "INFLUXDB_FLUSH_INTERVAL")
except ValueError as e:
    raise ValueError(f"Configuration validation failed: {e}")
