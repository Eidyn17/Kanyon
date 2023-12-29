#!/usr/bin/python3

import time
import paho.mqtt.client as paho
from paho import mqtt
import board
import busio
import adafruit_ina260
import smbus
from w1thermsensor import W1ThermSensor, Unit
from datetime import datetime
import threading
import signal
from threading import Thread, Lock
import RPi.GPIO as GPIO
import adafruit_max1704x

# setting callbacks for different events to see if it works, print the message etc.
def on_connect(client, userdata, flags, rc, properties=None):
    print("CONNACK received with code %s." % rc)
    # Subscribe to topic
    client.subscribe("Kanyon/mqtt_request", qos=1)

# with this callback you can see if your publish was successful
def on_publish(client, userdata, mid, properties=None):
    print("mid: " + str(mid))

# print which topic was subscribed to
def on_subscribe(client, userdata, mid, granted_qos, properties=None):
    print("Subscribed: " + str(mid) + " " + str(granted_qos))

# print message, useful for checking if it was successful
def on_message(client, userdata, msg):
    print(msg.topic + " " + str(msg.qos) + " " + str(msg.payload))

    #Get INA260 data - HV Voltage, DC-DC Current and DC-DC Input Power
    try:
        hv_voltage = ina260_sensor.voltage
    except Exception as e:
        print(f"Exception during sensor reading: {str(e)}")
        hv_voltage = "Unknown"

    try:
        hv_current = ina260_sensor.current
    except Exception as e:
        print(f"Exception during sensor reading: {str(e)}")
        hv_current = "Unknown"

    try:
        hv_power = ina260_sensor.power
    except Exception as e:
        print(f"Exception during sensor reading: {str(e)}")
        hv_power = "Unknown"

    # Get HV SOC
    try:
        hv_soc = max17.cell_percent
    except Exception as e:
        hv_soc = "Unknown"
        print(f"Exception during sensor reading: {str(e)}")

    #Get LV Battery Details LV_voltage and LV_soc
    try:
        addr = 0x10  # LV Battery I2C address
        vcellH = lv_battery_bus.read_byte_data(addr, 0x03)
        vcellL = lv_battery_bus.read_byte_data(addr, 0x04)
        socH = lv_battery_bus.read_byte_data(addr, 0x05)
        socL = lv_battery_bus.read_byte_data(addr, 0x06)

        LV_voltage = (((vcellH & 0x0F) << 8) + vcellL) * 1.25  # Voltage in mV
        LV_soc = ((socH << 8) + socL) * 0.003906  # SoC percentage

    except Exception as e:
        # Log the exception
        print(f"Error in I2C communication for LV Battery: {str(e)}")
        # Set default values or handle the error as needed
        LV_voltage, LV_soc = "Unknown", "Unknown"

    #Get temperature data
    try:
        temp_C = sensor.get_temperature(Unit.DEGREES_C)
    except Exception as e:
        print(f"Error in getting temperature data: {str(e)}")
        temp_C = "Unknown"

    #Get GPIO state for DC-DC Converter - GPIO 27
    try:
        gpio27_status = GPIO.input(27)
        dcdc_status = 'Active' if gpio27_status == GPIO.HIGH else 'OFF'
    except Exception as e:
        print(f"Error in getting gpio 27 status (DC-DC): {str(e)}")
        dcdc_status = "Unknown"

    #Get GPIO state for Battery Heater - GPIO 26
    try:
        gpio26_status = GPIO.input(26)
        heater_status = 'ON' if gpio26_status == GPIO.HIGH else 'OFF'
    except Exception as e:
        print(f"Error in getting gpio 26 status (Heater): {str(e)}")
        heater_status = "Unknown"

    #Publish values to relevant topics

    client.publish("Kanyon/HV_Voltage", payload=hv_voltage, qos=0)
    print("Message posted to Kanyon/HV_Voltage.")

    client.publish("Kanyon/HV_SOC", payload=hv_soc, qos=0)
    print("Message posted to Kanyon/HV_SOC.")

    client.publish("Kanyon/DC-DC_Current", payload=hv_current, qos=0)
    print("Message posted to Kanyon/DC-DC_Current.")

    client.publish("Kanyon/DC-DC_Power", payload=hv_power, qos=0)
    print("Message posted to Kanyon/DC-DC_Power.")

    client.publish("Kanyon/LV_Voltage", payload=LV_voltage, qos=0)
    print("Message posted to Kanyon/LV_Voltage.")

    client.publish("Kanyon/LV_soc", payload=LV_soc, qos=0)
    print("Message posted to Kanyon/LV_soc.")

    client.publish("Kanyon/Temp", payload=temp_C, qos=0)
    print("Message posted to Kanyon/Temp.")

    client.publish("Kanyon/DC-DC_Status", payload=dcdc_status, qos=0)
    print("Message posted to Kanyon/DC-DC_Status.")

    client.publish("Kanyon/Heater_Status", payload=heater_status, qos=0)
    print("Message posted to Kanyon/Heater_Status.")

# using MQTT version 5 here, for 3.1.1: MQTTv311, 3.1: MQTTv31
# userdata is user defined data of any type, updated by user_data_set()
# client_id is the given name of the client
client = paho.Client(client_id="", userdata=None, protocol=paho.MQTTv5)
client.on_connect = on_connect

# enable TLS for secure connection
client.tls_set(tls_version=mqtt.client.ssl.PROTOCOL_TLS)
# set username and password
client.username_pw_set("Eidyn", "Mqtt1111")
# connect to HiveMQ Cloud on port 8883 (default for MQTT)
client.connect("95ea70d6edb34e4a956c8f346ae8fba8.s1.eu.hivemq.cloud", 8883)

# setting callbacks, use separate functions like above for better visibility
client.on_subscribe = on_subscribe
client.on_message = on_message
client.on_publish = on_publish

# Set the I2C address for INA260
try:
    ina260_i2c_address = 0x41
except Exception as e:
    print(f"Error in setting I2C address for INA260 on 0x41 {str(e)}")

# Create I2C object for INA260 sensor
try:
    ina260_i2c = busio.I2C(board.SCL, board.SDA)
    ina260_sensor = adafruit_ina260.INA260(ina260_i2c, address=ina260_i2c_address)
except Exception as e:
    print(f"Error in creating I2C object for INA260 on 0x41 {str(e)}")

# Create I2C object for LV battery (MAX17048)
try:
    lv_battery_i2c_address = 0x10
    lv_battery_bus = smbus.SMBus(1)
except Exception as e:
    print(f"Error in creating I2C object for DFRobot UPS MAX17048 on 0x10 {str(e)}")

# Create W1ThermSensor instance
try:
    sensor = W1ThermSensor()
except Exception as e:
    print(f"Error in creating W1ThermSensor instance {str(e)}")

# Set up MAX17048 sensor
try:
    MAX17048_i2c = board.I2C()  # uses board.SCL and board.SDA
    max17 = adafruit_max1704x.MAX17048(MAX17048_i2c)
except Exception as e:
    print(f"Error in creating Adafruit MAX17048 instance. Remember to connect power from battery! {str(e)}")

# Set up GPIO for pin 27 - DC-DC Converter
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)

# Set up GPIO for pin 26 - Battery Heater
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)

try:
    client.loop_forever()
except KeyboardInterrupt:
    print("Script terminated by user.")
    client.disconnect()
    client.loop_stop()

# a single publish, this can also be done in loops, etc.
#client.publish("encyclopedia/temperature", payload="hot", qos=1)

# loop_forever for simplicity, here you need to stop the loop manually
# you can also use loop_start and loop_stop
#client.loop_forever()