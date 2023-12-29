# Kanyon Dashboard Script
# To run as service, providing local network access to port 5000 of this Pi's IP address to view and interact
# with telemetry data from a webpage.

import time
import ntplib
from flask import Flask, render_template, jsonify
from flask import request
import board
import busio
import adafruit_ina260
import smbus
from w1thermsensor import W1ThermSensor, Unit  # Added import
from datetime import datetime
import RPi.GPIO as GPIO
import threading
import signal
from threading import Thread, Lock
import adafruit_max1704x

# Configurable variable for threshold voltage
threshold_voltage_lipo = 6.3  # Change this value for LiPo battery
threshold_voltage_nimh = 5.6  # Change this value for NiMH battery

#********** CHANGE THIS VALUE!!!!!!!!!

#********** Choose the appropriate threshold voltage based on the battery type
threshold_voltage = threshold_voltage_lipo  # Change this assignment based on your battery type

#**********

# Variable for battery chemistry based on the threshold voltage
battery_chemistry = "Lithium Polymer" if threshold_voltage == threshold_voltage_lipo else "Nickel Metal Hydride"

# Initialize cumulative energy consumption from the file on script startup
cumulative_energy_consumption_file_path = 'energy_consumption.txt'

# Function to load initial cumulative energy consumption from the file
def load_initial_energy_consumption():
    try:
        with open(cumulative_energy_consumption_file_path, "r") as energy_file:
            return float(energy_file.read())
    except FileNotFoundError:
        return 0.0
    except Exception as e:
        # Handle the exception (e.g., log it) and return a default value
        log_exception("Error loading initial energy consumption", e)
        return 0.0
    
def log_exception(message, exception):
    timestamp = datetime.now().replace(microsecond=0)
    log_entry = f"{timestamp} - ERROR: {message} - {str(exception)}"
    with open("app_log.txt", "a") as log_file:
        log_file.write(log_entry + "\n")
    
cumulative_energy_consumption = load_initial_energy_consumption()

# Attempt to get NTP time synchronisation
def wait_for_ntp_time(timeout=30):
    """
    Wait for NTP time synchronization.

    :param timeout: Maximum time (in seconds) to wait for synchronization.
    """
    print("Checking NTP time synchronization...")
    
    # Initialize NTP client
    client = ntplib.NTPClient()

    start_time = time.time()
    while True:
        try:
            # Query an NTP server
            response = client.request('pool.ntp.org', version=3)
            
            # Check if the response has a valid timestamp
            if response.tx_time:
                ntp_time = response.tx_time
                end_time = time.time()
                duration = end_time - start_time
                print(f"NTP time synchronized in {duration:.2f} seconds!")
                
                # Log the synchronization message with NTP-synchronized time
                log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ntp_time))} - NTP time synchronized in {duration:.2f} seconds!"
                with open("app_log.txt", "a") as log_file:
                    log_file.write(log_entry + "\n")
                
                return ntp_time
        except Exception as e:
            # Log the exception or print an error message if needed
            error_message = f"Error checking NTP time synchronization: {e}"
            print(error_message)
            
            # Log the error message with system time
            log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {error_message}"
            with open("app_log.txt", "a") as log_file:
                log_file.write(log_entry + "\n")

        # Check the timeout
        elapsed_time = time.time() - start_time
        if elapsed_time >= timeout:
            print(f"Unable to synchronize time within {timeout} seconds. Continuing with the script.")
            
            # Log the timeout message with system time
            log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S')} - Unable to synchronize time within {timeout} seconds. Continuing with the script."
            with open("app_log.txt", "a") as log_file:
                log_file.write(log_entry + "\n")
                
            return

        # Wait before retrying
        time.sleep(1)

# Call the function to wait for NTP synchronization
ntp_time_value = wait_for_ntp_time()

# Create a lock for thread-safe access to shared variables
lock = threading.Lock()

# Set up GPIO for pin 27 - DC-DC Converter
GPIO.setmode(GPIO.BCM)
GPIO.setup(27, GPIO.OUT)

# Drive GPIO 27 low (initial ON state for the DC-DC Converter)
GPIO.output(27, GPIO.HIGH)

# Set up GPIO for pin 26 - Battery Heater
GPIO.setmode(GPIO.BCM)
GPIO.setup(26, GPIO.OUT)

# Set the GPIO pin for the fan control
fan_control_pin = 22

# Set up the GPIO pin as an output
GPIO.setup(fan_control_pin, GPIO.OUT)

# Turn the fan off
GPIO.output(fan_control_pin, GPIO.LOW)

# Drive GPIO 26 low (initial OFF state for the battery heater)
GPIO.output(26, GPIO.LOW)

low_voltage_logged = False  # Variable to track whether low voltage has been logged
very_low_voltage_logged = False  # Variable to track whether very low voltage has been logged

app = Flask(__name__)

# Set the new I2C address
try:
    ina260_i2c_address = 0x41
except Exception as e:
    log_exception("Error setting INA260 I2C address at 0x41.", e)

# Create I2C object for INA260 sensor
try:
    ina260_i2c = busio.I2C(board.SCL, board.SDA)
    ina260_sensor = adafruit_ina260.INA260(ina260_i2c, address=ina260_i2c_address)
except Exception as e:
    log_exception("Error creating INA260 I2C object.", e)

# Create I2C object for LV battery
try:
    lv_battery_i2c_address = 0x10
    lv_battery_bus = smbus.SMBus(1)
except Exception as e:
    log_exception("Error creating I2C object for DFRobot MAX17048 sensor at 0x10.", e)

# Create W1ThermSensor instance
try:
    sensor = W1ThermSensor()
except Exception as e:
    log_exception("Error creating W1ThermSensor instance.", e)

# Set up MAX17048 sensor
try:
    MAX17048_i2c = board.I2C()  # uses board.SCL and board.SDA
    max17 = adafruit_max1704x.MAX17048(MAX17048_i2c)
except:
    log_exception("Error creating Adafruit MAX17048 sensor I2C object at 0x36. Remember to connect power from battery!", e)

# Introduce a delay to allow voltage to stabilise.
time.sleep(3)

# Read initial HV voltage
initial_hv_voltage = ina260_sensor.voltage

# Check if initial HV voltage is above threshold voltage for selected battery type.
try:
    if initial_hv_voltage > threshold_voltage:
        # Drive GPIO 27 high (ENABLE DC-DC Converter)
        GPIO.output(27, GPIO.HIGH)
        print(f"Self-test OK - Batt Chem: {battery_chemistry} - HV voltage above threshold, printing confirmation message to log file.")
        log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ntp_time_value))} - Initialization and self test: OK. Battery chemistry selected: {battery_chemistry}. HV battery above selected threshold voltage ({threshold_voltage}): ({initial_hv_voltage}V), enabling DC-DC converter."
    else:
        # Drive GPIO 27 low and log the message
        GPIO.output(27, GPIO.LOW)
        print(f"Self-test FAILED - Batt Chem: {battery_chemistry} - HV voltage below threshold, printing confirmation message to log file.")
        log_entry = f"{time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(ntp_time_value))} - Initialization and self test: FAILED. SUGGEST IMMEDIATE SHUTDOWN. Battery chemistry selected: {battery_chemistry}. HV battery voltage too low ({initial_hv_voltage}V, below selected threshold voltage: {threshold_voltage}), disabling DC-DC converter."

    # Log the initial status
    with open("app_log.txt", "a") as log_file:
        log_file.write(log_entry + "\n")

except Exception as e:
    # Log the exception
    print(f"Exception during self-test: {str(e)}")

@app.route("/toggle_gpio_27", methods=["POST"])
def toggle_gpio_27():
    try:
        # Toggle the state of GPIO 27 - DC-DC Converter
        current_status = GPIO.input(27)
        new_status = not current_status
        GPIO.output(27, new_status)

        # Get the updated GPIO status
        gpio_status = 'Active' if new_status == GPIO.HIGH else 'OFF'

        return jsonify({'gpio_status': gpio_status})

    except Exception as e:
        # Log the exception
        log_exception("Error toggling GPIO 27", e)
        return jsonify({'error': 'Error toggling GPIO 27'}), 500
    
@app.route("/toggle_gpio_26", methods=["POST"])
def toggle_gpio_26():
    global last_heater_on_time

    try:
        # Check HV voltage before allowing the heater to be toggled ON
        hv_voltage = ina260_sensor.voltage
        if hv_voltage < threshold_voltage:
            return jsonify({'error': f'HV voltage ({hv_voltage}V) is below the threshold ({threshold_voltage}V). Heater cannot be turned ON.'}), 400

        # Toggle the state of GPIO 26 - BATTERY HEATER
        current_status = GPIO.input(26)
        new_status = not current_status
        GPIO.output(26, new_status)

        # Get the updated GPIO status
        gpio_26_status = 'High' if new_status == GPIO.HIGH else 'Low'

        # Update the last heater on time when turning it on
        if new_status == GPIO.HIGH:
            last_heater_on_time = time.time()

        # Log the operation
        log_entry = f"{datetime.now().replace(microsecond=0)} - Battery Heater turned {gpio_26_status}. Current HV voltage: {hv_voltage}V"
        with open("app_log.txt", "a") as log_file:
            log_file.write(log_entry + "\n")

        return jsonify({'gpio_26_status': gpio_26_status})

    except Exception as e:
        # Log the exception
        log_exception("Error toggling GPIO 26", e)
        return jsonify({'error': 'Error toggling GPIO 26'}), 500


def calculate_hv_soc():
    try:
        hv_soc = max17.cell_percent
    except Exception as e:
        hv_soc = "Unavailable"
        log_exception("Error reading HV SoC", e)

    return hv_soc
    
def calculate_hv_cond(temp_C):
    if not isinstance(temp_C, (int, float)):
        return "Unknown"
    elif temp_C >= 23:
        return "Cool"
    elif temp_C <= 10:
        return "Heat"
    else:
        return "Not Required"

@app.route("/")
def index():
    try:
        # INA260 sensor data (HV Battery)
        try:
            hv_voltage = ina260_sensor.voltage
        except Exception as e:
            hv_voltage = "Unavailable"
            log_exception("Error reading HV voltage", e)

        try:
            hv_current = ina260_sensor.current
        except Exception as e:
            hv_current = "Unavailable"
            log_exception("Error reading HV current", e)

        try:
            hv_power = ina260_sensor.power
        except Exception as e:
            hv_power = "Unavailable"
            log_exception("Error reading HV power", e)

        # HV SoC
        hv_soc = calculate_hv_soc

        # Contactor state
        try:
            contactor_state = "Closed"  # Replace with the actual function to get contactor state
        except Exception as e:
            contactor_state = "Unknown"
            log_exception("Error reading contactor state", e)

        # LV Battery data
        try:
            lv_voltage, lv_soc = read_battery_data()
        except Exception as e:
            lv_voltage, lv_soc = "Unavailable", "Unavailable"
            log_exception("Error reading LV battery data", e)

        # Temperature data
        try:
            temp_C = sensor.get_temperature(Unit.DEGREES_C)
        except Exception as e:
            temp_C = "Unavailable"
            log_exception("Error reading temperature", e)

        # Determine if HV Conditioning is Required
        try:
            hv_cond_req = calculate_hv_cond(temp_C)
        except Exception as e:
            hv_cond_req = "Unknown"
            log_exception("Error calculating hv_cond_req", e)

        # Read the current state of GPIO 26 (battery heater)
        try:
            battery_heater_state = GPIO.input(26) == GPIO.HIGH  # True if HIGH, False if LOW
        except Exception as e:
            battery_heater_state = "Unavailable"
            log_exception("Error reading battery heater state", e)

    except Exception as e:
        # Log the exception
        log_exception("Error in sensor readings for the index route", e)
        # Set default values or handle the error as needed
        hv_voltage, hv_current, hv_power, lv_voltage, lv_soc, temp_C, battery_heater_state, hv_cond_req, = None, None, None, None, None, None, None

    return render_template(
        "dashboard.html",
        hv_voltage=hv_voltage,
        hv_soc=hv_soc,
        hv_current=hv_current,
        hv_power=hv_power,
        lv_voltage=lv_voltage,
        lv_soc=lv_soc,
        temp_C=temp_C,
        battery_heater_state=battery_heater_state,
        battery_chemistry=battery_chemistry,
        contactor_state=contactor_state,
        hv_cond_req=hv_cond_req,
    )


@app.route("/data")
def get_data():
    global cumulative_energy_consumption
    try:
        # INA260 sensor data (HV Battery)
        try:
            hv_voltage = ina260_sensor.voltage
        except Exception as e:
            hv_voltage = "Unavailable"
            log_exception("Error reading HV voltage", e)

        try:
            hv_current = ina260_sensor.current
        except Exception as e:
            hv_current = "Unavailable"
            log_exception("Error reading HV current", e)

        try:
            hv_power = ina260_sensor.power
        except Exception as e:
            hv_power = "Unavailable"
            log_exception("Error reading HV power", e)

        # HV SoC
        hv_soc = calculate_hv_soc()

        # Contactor state
        try:
            contactor_state = "Closed"  # Replace with the actual function to get contactor state
        except Exception as e:
            contactor_state = "Unknown"
            log_exception("Error reading contactor state", e)

        # LV Battery data
        try:
            lv_voltage, lv_soc = read_battery_data()
        except Exception as e:
            lv_voltage, lv_soc = "Unavailable", "Unavailable"
            log_exception("Error reading LV battery data", e)

        # Temperature data
        try:
            temp_C = sensor.get_temperature(Unit.DEGREES_C)
        except Exception as e:
            temp_C = "Unavailable"
            log_exception("Error reading temperature", e)

        # Determine if HV Conditioning is Required
        try:
            hv_cond_req = calculate_hv_cond(temp_C)
        except Exception as e:
            hv_cond_req = "Unknown"
            log_exception("Error calculating hv_cond_req", e)

        # Check and log low HV voltage
        check_and_log_low_voltage()

        # Calculate energy consumption
        energy_consumption = hv_power / 3600000.0  # Convert from mW to W

        # Update cumulative energy consumption
        cumulative_energy_consumption += energy_consumption

        # Read the current GPIO 27 status - DC-DC Converter
        gpio_status = GPIO.input(27)

        # Convert GPIO status to a human-readable format
        gpio_status_text = 'Active' if gpio_status == GPIO.HIGH else 'OFF'

    except Exception as e:
        # Log the exception
        log_exception("Error in sensor readings for the data route", e)
        # Set default values or handle the error as needed
        hv_voltage, hv_current, hv_power, lv_voltage, lv_soc, temp_C = None, None, None, None, None, None
        gpio_status_text = 'Unknown'  # Set status to 'Unknown' in the event of an error.

    return jsonify(
        hv_voltage=hv_voltage,
        hv_soc=hv_soc,
        hv_current=hv_current,
        hv_power=hv_power,
        lv_voltage=lv_voltage,
        lv_soc=lv_soc,
        temp_C=temp_C,
        gpio_status=gpio_status_text,
        cumulative_energy_consumption=cumulative_energy_consumption,
        contactor_state=contactor_state,
        hv_cond_req=hv_cond_req,
    )

def update_energy_consumption():
    global cumulative_energy_consumption

    while True:
        try:
            # INA260 sensor data (HV Battery)
            hv_power = ina260_sensor.power

            # Calculate energy consumption
            energy_consumption = hv_power / 3600000.0  # Convert from mW to Wh

            # Update cumulative energy consumption
            with lock:
                cumulative_energy_consumption += energy_consumption
        except Exception as e:
            # Log the exception
            log_exception("Error in continuous energy consumption update", e)

        time.sleep(1)  # Update every second, adjust as needed

def save_energy_to_file():
    while True:
        with lock:
            # Write the cumulative energy consumption to the file
            with open(cumulative_energy_consumption_file_path, 'w') as file:
                file.write(str(cumulative_energy_consumption))

        # Sleep for 60 seconds before writing again
        time.sleep(60)

# Start the energy consumption update in a separate thread
energy_consumption_thread = Thread(target=update_energy_consumption)
energy_consumption_thread.start()

# Start the file writing in a separate thread
file_writing_thread = Thread(target=save_energy_to_file)
file_writing_thread.start()

@app.route("/log")
def get_log():
    try:
        # Read the log file content
        with open("app_log.txt", "r") as log_file:
            log_content = log_file.readlines()

    except Exception as e:
        # Log the exception
        log_exception("Error reading the log file", e)
        # Set default log content or handle the error as needed
        log_content = ["Error reading the log file"]

    # Return the log content as plain text
    return "\n".join(log_content)

@app.route("/clear_log", methods=["POST"])
def clear_log():
    try:
        # Clear the log file
        with open("app_log.txt", "w") as log_file:
            log_file.write("")
        return jsonify({'success': True})
    except Exception as e:
        # Log the exception
        log_exception("Error clearing the log file", e)
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route("/check_low_voltage_status")
def check_low_voltage_status():
    try:
        return jsonify(very_low_voltage_logged)
    
    except Exception as e:
        # Log the exception
        log_exception("Error in checking low voltage status", e)
        # Set default value or handle the error as needed
        return jsonify(False)
    
@app.route("/check_gpio_26_status")
def check_gpio_26_status():
    try:
        # Read the current state of GPIO 26 (battery heater)
        battery_heater_state = GPIO.input(26)
        gpio_26_status = 'High' if battery_heater_state == GPIO.HIGH else 'Low'

        return jsonify({'gpio_26_status': gpio_26_status})

    except Exception as e:
        # Log the exception
        log_exception("Error checking GPIO 26 status", e)
        return jsonify({'error': 'Error checking GPIO 26 status'}), 500

@app.route('/reset_energy_consumption', methods=['POST'])
def reset_energy_consumption():
    global cumulative_energy_consumption

    # Reset the cumulative energy consumption to 0
    with lock:
        cumulative_energy_consumption = 0.0

    # Optionally, you can save the reset value to the file if needed

    return jsonify(success=True)

@app.route("/charging_data")
def get_charging_data():
    try:
        # Retrieve charging circuit data
        charging_current = "Unknown"  # Replace with the actual function to get charging current
        charging_power = "Unknown"  # Replace with the actual function to get charging power
        is_charging = "Unknown"    # Replace with the actual function to get charging status

        # Create a dictionary to hold the charging data
        charging_data = {
            'charging_current': charging_current,
            'charging_power': charging_power,
            'is_charging': is_charging,
        }

    except Exception as e:
        # Log the exception
        log_exception("Error in charging circuit data", e)
        # Set default values or handle the error as needed
        charging_data = {'error': 'Error retrieving charging data'}

    # Return the charging data as JSON
    return jsonify(charging_data)

def read_battery_data():
    try:
        addr = 0x10  # LV Battery I2C address
        vcellH = lv_battery_bus.read_byte_data(addr, 0x03)
        vcellL = lv_battery_bus.read_byte_data(addr, 0x04)
        socH = lv_battery_bus.read_byte_data(addr, 0x05)
        socL = lv_battery_bus.read_byte_data(addr, 0x06)

        voltage = (((vcellH & 0x0F) << 8) + vcellL) * 1.25  # Voltage in mV
        soc = ((socH << 8) + socL) * 0.003906  # SoC percentage

    except Exception as e:
        # Log the exception
        log_exception("Error in I2C communication for LV Battery", e)
        # Set default values or handle the error as needed
        voltage, soc = None, None

    # Check and log low LV battery SoC
    check_and_log_low_soc(soc)

    # Check and log critical LV battery SoC
    check_and_log_critical_soc(soc)

    return voltage, soc

def check_and_turn_off_heater():
    global last_heater_on_time

    # Check if the heater is on and it's been more than 5 minutes
    if GPIO.input(26) == GPIO.HIGH and time.time() - last_heater_on_time > 300:
        # Add log entry
        timestamp = datetime.now().replace(microsecond=0)
        log_entry = f"{timestamp} - Battery Heater automatically turned off (5 minutes elapsed)."
        with open("app_log.txt", "a") as log_file:
            log_file.write(log_entry + "\n")

        # Turn off the battery heater
        GPIO.output(26, GPIO.LOW)

def check_and_log_low_soc(soc):
    global low_soc_logged
    timestamp = datetime.now().replace(microsecond=0)  # Seconds precision

    if soc < 50.0 and not low_soc_logged:
        low_soc_log_entry = f"{timestamp} - LV BATTERY LOW SoC (<50%) - ENGAGE HV/DC-DC CONVERTER."
        with open("app_log.txt", "a") as log_file:
            log_file.write(low_soc_log_entry + "\n")
        low_soc_logged = True
    elif soc >= 50.0:
        low_soc_logged = False

def check_and_log_critical_soc(soc):
    global critical_soc_logged
    timestamp = datetime.now().replace(microsecond=0)  # Seconds precision

    if soc < 20.0 and not critical_soc_logged:
        critical_soc_log_entry = f"{timestamp} - LV BATTERY CRITICAL SoC (<20%) - SHUTDOWN IMMINENT."
        with open("app_log.txt", "a") as log_file:
            log_file.write(critical_soc_log_entry + "\n")
        critical_soc_logged = True
    elif soc >= 20.0:
        critical_soc_logged = False



def check_and_log_low_voltage():
    global low_voltage_logged, very_low_voltage_logged
    hv_voltage = ina260_sensor.voltage

    timestamp = datetime.now().replace(microsecond=0)  # Seconds precision

    if hv_voltage < 7.0 and not low_voltage_logged:
        low_voltage_log_entry = f"{timestamp} - LOW HV VOLTAGE (<7v): {hv_voltage}V"
        with open("app_log.txt", "a") as log_file:
            log_file.write(low_voltage_log_entry + "\n")
        low_voltage_logged = True
    elif hv_voltage >= 7.0:
        low_voltage_logged = False

    if hv_voltage < 6.5 and not very_low_voltage_logged:
        very_low_voltage_log_entry = f"{timestamp} - VERY LOW HV VOLTAGE (<6.5v) - DC-DC WILL SHUT DOWN AT {threshold_voltage}: {hv_voltage}V"
        with open("app_log.txt", "a") as log_file:
            log_file.write(very_low_voltage_log_entry + "\n")
        very_low_voltage_logged = True
    elif hv_voltage >= 6.5:
        very_low_voltage_logged = False

def check_and_control_relay():
    try:
        hv_voltage = ina260_sensor.voltage

        # Check if HV voltage is below threshold voltage
        if hv_voltage < threshold_voltage:
            # If below threshold, turn off both DC-DC and Battery Heater.
            with lock:
                GPIO.output(27, GPIO.LOW)
                GPIO.output(26, GPIO.LOW)
                log_exception(f"HV battery voltage below specified threshold ({threshold_voltage}). Turning off DC-DC and Heater. SCRIPT MUST BE MANUALLY RESTARTED TO RE-ENABLE DC-DC CONVERTER.", None)

    except Exception as e:
        # Log the exception
        log_exception("Error in checking and controlling relay", e)

    try:
        temp_C = sensor.get_temperature(Unit.DEGREES_C)
        hv_cond_req = calculate_hv_cond(temp_C)
        if hv_cond_req == "Cool":
            # Enable fan
            log_exception(f"Temp above 23C, enabling fan.", None)
            GPIO.output(fan_control_pin, GPIO.HIGH)
        else:
            # Disable fan
            log_exception(f"Temp below 23C or unknown, disabling fan.", None)
            GPIO.output(fan_control_pin, GPIO.LOW)
    except Exception as e:
        log_exception("Error in thermal management logic.", e)


def periodic_task():
    while True:
        check_and_control_relay()
        check_and_turn_off_heater()  # Check and turn off the heater after 5 minutes
        time.sleep(60)

def run_flask_app():
    try:
        app.run(debug=True, host='0.0.0.0', port=5000, use_reloader=False)
    except Exception as e:
        log_exception("Error during Flask app execution", e)

def cleanup_handler(signum, frame):
    try:
        print("Received SIGHUP. Cleaning up GPIO...")
        GPIO.setmode(GPIO.BCM)  # Set GPIO numbering mode before cleanup
        GPIO.output(27, GPIO.LOW)
        GPIO.output(26, GPIO.LOW)
        GPIO.cleanup()
        print("GPIO cleanup complete.")
    except Exception as e:
        print(f"Error during GPIO cleanup: {str(e)}")
    finally:
        sys.exit(0)

if __name__ == "__main__":
    try:
        # Set up SIGHUP handler
        signal.signal(signal.SIGHUP, cleanup_handler)

        # Start the Flask app in a separate thread
        flask_thread = threading.Thread(target=run_flask_app)
        flask_thread.start()

        # Start the periodic task in the main thread
        periodic_task()

    except KeyboardInterrupt:
        # Handle Ctrl+C
        pass
    finally:
        # Clean up GPIO on script exit
        GPIO.output(27, GPIO.LOW)  # Set GPIO 27 to low (OFF) - DC-DC Converter
        GPIO.output(26, GPIO.LOW)  # Set GPIO 26 to low (OFF) - Battery Heater
        GPIO.cleanup()
