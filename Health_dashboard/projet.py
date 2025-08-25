import math
import paho.mqtt.client as mqtt
import logging
import pymysql  # MySQL client library

# MQTT Configuration
mqtt_server = "broker.emqx.io"
mqtt_port = 1883
client_id = "python_subscriber"

# MQTT Topics
topic_temperature_ds18b20 = "topic_sensor_temperature_ds18b20"
topic_temperature_ntc = "topic_sensor_temperature_ntc"
topic_accel = "topic_sensor_acceleration"
topic_ds18b20_alert = "alert/ds18b20_temperature"
topic_ntc_alert = "alert/ntc_temperature"
topic_accel_alert = "alert/acceleration"
topic_blue_led = "control/blue_led"

# Thresholds for alerts
ds18b20_threshold = 30.0
ntc_threshold = 30.0
accel_vector_threshold = 9.0  # Threshold for acceleration vector magnitude

# Database Configuration
db_config = {
    "host": "localhost",
    "user": "root",
    "password": "root1234",
    "database": "iot_health_monitor",
}

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Callback for when the client connects to the broker
def on_connect(client, userdata, flags, rc):
    if rc == 0:
        logging.info("Connected to MQTT Broker!")
        # Subscribe to relevant topics
        client.subscribe([(topic_temperature_ds18b20, 0),
                          (topic_temperature_ntc, 0),
                          (topic_accel, 0),
                          (topic_blue_led, 0)])
        # Fetch and publish blue LED status on connect
        fetch_and_publish_led_status(client)
    else:
        logging.error(f"Failed to connect, return code {rc}")

# Fetch the latest blue LED status from the database
def fetch_and_publish_led_status(client):
    try:
        # Connect to the database
        connection = pymysql.connect(**db_config)
        cursor = connection.cursor()

        # Query to get the latest blue LED status
        query = "SELECT color FROM rgb_led_status ORDER BY id DESC LIMIT 1"
        cursor.execute(query)
        result = cursor.fetchone()

        if result:
            led_status = result[0]
            led_state = "on" if led_status == "blue_on" else "off"

            # Publish the LED status to the MQTT topic
            payload = {"led": "blue", "state": led_state}
            client.publish(topic_blue_led, str(payload))
            logging.info(f"Published LED status: {payload} to topic: {topic_blue_led}")
        else:
            logging.warning("No LED status found in the database.")

        # Close database connection
        cursor.close()
        connection.close()
    except Exception as e:
        logging.error(f"Error fetching LED status from database: {e}")

# Callback for when a message is received
def on_message(client, userdata, msg):
    topic = msg.topic
    payload = msg.payload.decode("utf-8")
    logging.info(f"Message received on topic '{topic}': {payload}")

    try:
        if topic == topic_temperature_ds18b20:
            temperature = float(payload)
            logging.info(f"DS18B20 Temperature: {temperature}°C")
            if temperature > ds18b20_threshold:
                client.publish(topic_ds18b20_alert, "1")
                logging.warning(f"Alert: DS18B20 temperature exceeded threshold ({ds18b20_threshold}°C)!")
        elif topic == topic_temperature_ntc:
            temperature = float(payload)
            logging.info(f"NTC Temperature: {temperature}°C")
            if temperature > ntc_threshold:
                client.publish(topic_ntc_alert, "1")
                logging.warning(f"Alert: NTC temperature exceeded threshold ({ntc_threshold}°C)!")
        elif topic == topic_accel:
            # Example payload: "X:1.2 Y:0.8 Z:0.5"
            accel_data = payload.split()
            accel_values = {axis.split(":")[0]: float(axis.split(":")[1]) for axis in accel_data}
            magnitude = math.sqrt(sum(val**2 for val in accel_values.values()))
            logging.info(f"Acceleration - X: {accel_values['X']}, Y: {accel_values['Y']}, Z: {accel_values['Z']}, Magnitude: {magnitude}")
            if magnitude > accel_vector_threshold:
                client.publish(topic_accel_alert, "1")
                logging.warning(f"Alert: Acceleration magnitude exceeded threshold ({accel_vector_threshold})!")
        elif topic == topic_blue_led:
            logging.info(f"Blue LED state changed: {payload}")
    except Exception as e:
        logging.error(f"Error processing message: {e}")

# Callback for subscription acknowledgment
def on_subscribe(client, userdata, mid, granted_qos):
    logging.info("Subscription successful")

# Create MQTT client instance
client = mqtt.Client(client_id)
client.on_connect = on_connect
client.on_message = on_message
client.on_subscribe = on_subscribe

# Enable debugging logs
client.enable_logger()

try:
    logging.info("Connecting to MQTT Broker...")
    client.connect(mqtt_server, mqtt_port, 60)
    client.loop_start()  # Non-blocking loop
    while True:
        pass  # Keep the script running
except KeyboardInterrupt:
    logging.info("Exiting...")
    client.loop_stop()
    client.disconnect()
except Exception as e:
    logging.error(f"An error occurred: {e}")
