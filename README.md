# Qingping MQTT to InfluxDB Collector

## Features
- Collects data from Qingping sensors via MQTT
- Supports sensor data collection, including:
  - Temperature
  - Humidity
  - CO2 levels
  - PM2.5 and PM10 particulate matter
  - Battery level
- Collects diagnostic data including:
  - WiFi signal strength
  - WiFi channel
  - WiFi access point details
  - Software and hardware versions
  - Timezone settings
- Stores all data in InfluxDB for time-series analysis
- Robust error handling and reconnection logic
- Configurable logging levels
- Support for MQTT v5 protocol
- TLS support for secure MQTT connections
- Batched writes to InfluxDB for better performance

## How It Works

### Message Processing
1. Connects to an MQTT broker and subscribes to the configured topic (default: `qingping/#`)
2. Processes two types of messages:
   - Type 17: Sensor data messages containing environmental readings
   - Type 13: Diagnostic messages containing device status information
3. Extracts device MAC address and relevant data from messages
4. Formats data into InfluxDB points with appropriate tags and fields
5. Writes data to InfluxDB with timestamps

### Data Structure
- **Sensor Data Points**:
  - Tags: device_mac
  - Fields: temperature, humidity, co2, pm25, pm10, battery
  - Measurement name: "sensor"

- **Diagnostic Data Points**:
  - Tags: device_mac, sw_version, module_version, hw_version, wifi_ap_name, wifi_ap_mac
  - Fields: wifi_signal, wifi_channel, timezone
  - Measurement name: "diagnostic"

# Configuration Parameters

| Parameter | Description | Default | Required | Example |
|-----------|-------------|---------|----------|---------|
| **MQTT Settings** |
| `MQTT_BROKER_ADDRESS` | Hostname or IP of MQTT broker | - | Yes | `mqtt.example.com` |
| `MQTT_BROKER_PORT` | Port number for MQTT broker | `1883` | No | `1883` |
| `MQTT_USERNAME` | Username for MQTT authentication | - | Yes | `mqttuser` |
| `MQTT_PASSWORD` | Password for MQTT authentication | - | Yes | `password123` |
| `MQTT_TOPIC` | MQTT topic to subscribe to | `qingping/#` | No | `qingping/#` |
| `MQTT_KEEPALIVE` | Keepalive interval in seconds | `60` | No | `60` |
| `MQTT_USE_TLS` | Enable TLS encryption | `false` | No | `true` |
| **InfluxDB Settings** |
| `INFLUXDB_URL` | URL of InfluxDB server | `http://localhost:8086/` | Yes | `http://influxdb:8086/` |
| `INFLUXDB_TOKEN` | Authentication token for InfluxDB | - | Yes | `your-token-here` |
| `INFLUXDB_ORG` | Organization name in InfluxDB | - | Yes | `myorg` |
| `INFLUXDB_BUCKET` | Bucket name for data storage | - | Yes | `qingping` |
| `INFLUXDB_BATCH_SIZE` | Number of points to batch | `100` | No | `100` |
| `INFLUXDB_FLUSH_INTERVAL` | Flush interval in milliseconds | `5000` | No | `5000` |
| `INFLUXDB_ENABLE_GZIP` | Enable GZIP compression | `true` | No | `true` |
| **General Settings** |
| `LOG_LEVEL` | Logging verbosity level | `INFO` | No | `DEBUG` |
| `MAX_RECONNECT_DELAY` | Max reconnection backoff in seconds | `60` | No | `60` |
| `TZ` | Container timezone | - | No | `America/Chicago` |

## Notes:
- Required parameters must be set for the application to function
- Default values are used if optional parameters are not specified
- Values marked with `-` in the Default column have no default and must be provided if required
- The MQTT topic should match your Qingping device configuration
- Log levels available: DEBUG, INFO, WARNING, ERROR, CRITICAL
- TLS is disabled by default for MQTT connections

## Deployment

### Docker Compose Deployment
1. Create a `compose.yaml` file:
```yaml
name: qingping-collector
services:
  qingping_collector:
    command:
      - python
      - main.py
    container_name: qingping_collector
    environment:
      INFLUXDB_BUCKET: qingping
      INFLUXDB_ORG: YourOrg
      INFLUXDB_TOKEN: your-influxdb-token
      INFLUXDB_URL: http://your-influxdb-server:8086/
      LOG_LEVEL: INFO
      MAX_RECONNECT_DELAY: "60"
      MQTT_BROKER_ADDRESS: your-mqtt-broker
      MQTT_BROKER_PORT: "1883"
      MQTT_KEEPALIVE: "60"
      MQTT_PASSWORD: your-mqtt-password
      MQTT_TOPIC: qingping/#
      MQTT_USERNAME: your-mqtt-username
      TZ: America/Chicago
    image: lux4rd0/qingping-collector:latest
    restart: always
    networks:
      default: null
networks:
  default:
    name: qingping-collector_default
```

2. Deploy using Docker Compose:
```bash
docker-compose up -d
```

### Requirements
- Docker and Docker Compose
- Access to an MQTT broker
- Access to an InfluxDB v2.x instance
- Network connectivity between collector, MQTT broker, and InfluxDB


Here’s the revised **GitHub summary** with step 4 removed and focused solely on the setup process:

---

## **Setting Up Qingping Devices to Publish to a Local MQTT Broker**

### **Overview**
Qingping devices can be configured to send real-time data to your **local MQTT broker**, allowing for better control and privacy. This guide outlines how to set up your local broker and configure Qingping devices using their web interface.

---

### **Steps to Configure Devices**

#### 1. **Request Private MQTT Access**
- **Contact Qingping** to enable **private MQTT** for your devices. 
- This allows you to redirect data from Qingping’s cloud to your local MQTT broker.
- For more details, refer to:  
  [Private Communication Protocols - MQTT](https://developer.qingping.co/private/communication-protocols/public-mqtt-json)

---

#### 2. **Set Up Your Local MQTT Broker**
- Install and configure an MQTT broker, such as:
  - **Mosquitto**
  - **EMQX**
  - **HiveMQ**

**Basic Setup**:
- **Broker Address**: e.g., `192.168.x.x`
- **Port**: `1883` (non-TLS) or `8883` (TLS for secure connections)
- **Username** and **Password**: (if using broker authentication)

---

#### 3. **Configure Devices via Qingping Web Interface**
To direct Qingping devices to your local broker:

1. **Log into Qingping’s Device Management Portal**.
   - URL provided by Qingping upon enabling private MQTT access.

2. **Locate Your Devices**:
   - Find your devices in the **Device Settings** section.

3. **Update MQTT Settings**:
   - **MQTT Server**: `tcp://<broker_address>:<port>`  
     Example: `tcp://192.168.1.100:1883`
   - **Username/Password**: Credentials for your local MQTT broker (if applicable).

4. **Save and Apply Changes**:
   - The devices will now publish data to your local MQTT broker.

---

### **Additional Resources**
- [Qingping Private Communication Protocols](https://developer.qingping.co/private/communication-protocols/public-mqtt-json)  
- [Device Settings Modification API](https://developer.qingping.co/cloud-to-cloud/open-apis)

---

Following these steps, Qingping devices will publish real-time data to your local MQTT broker, which is ready for further processing by this data collector.


### Monitoring
- Check container logs: `docker logs qingping_collector.dev`
- Monitor InfluxDB for data ingestion
- Set up alerts for disconnections or data gaps

### Maintenance
- Container automatically restarts on failure
- Regular monitoring of logs for any connection issues
- Periodic verification of data in InfluxDB
- Update image version for new releases
