import tinytuya
from dotenv import dotenv_values
from time import sleep
from time import strftime
import json
import os
import subprocess
import re

config = dotenv_values(".env")

DEVICE_ID = config["DEVICE_ID"]
DEVICE_IP = config["DEVICE_IP"]
DEVICE_KEY = config["DEVICE_KEY"]

DATA_FILE = "power_data.json"
CONFIG_FILE = "data_config.json"

# Default columns configuration
DEFAULT_COLUMNS = {
    'timestamp': 'str',
    'current_ma': 'float',
    'power_w': 'float',
    'voltage_v': 'float',
    'gpu_usage': 'float'
}

def get_gpu_usage():
    try:
        # Using nvidia-smi to get GPU usage
        result = subprocess.check_output(
            ['nvidia-smi', '--query-gpu=utilization.gpu', '--format=csv,noheader,nounits'],
            encoding='utf-8'
        )
        return float(result.strip())
    except:
        return None

def load_column_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return DEFAULT_COLUMNS

def save_column_config(config):
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=4)

def ensure_data_structure():
    if not os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'w') as f:
            json.dump([], f)
        save_column_config(DEFAULT_COLUMNS)

def save_data(timestamp, current, power, voltage, gpu_usage):
    try:
        # Read existing data
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
        
        # Create new entry with only non-None values
        new_entry = {'timestamp': timestamp}
        if current is not None:
            new_entry['current_ma'] = current
        if power is not None:
            new_entry['power_w'] = power
        if voltage is not None:
            new_entry['voltage_v'] = voltage
        if gpu_usage is not None:
            new_entry['gpu_usage'] = gpu_usage
        
        # Add new entry
        data.append(new_entry)
        
        # Keep only last 1000 entries to prevent file from growing too large
        if len(data) > 1000:
            data = data[-1000:]
        
        # Write back to file
        with open(DATA_FILE, 'w') as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving data: {e}")

# Connect to Device
device = tinytuya.OutletDevice(
    dev_id=DEVICE_ID,
    address=DEVICE_IP,      # Or set to 'Auto' to auto-discover IP address
    local_key=DEVICE_KEY, 
    version=3.4)

def main():
    try:
        ensure_data_structure()
        while True:
            try:
                # without these it needs an active phone to poll
                device.set_socketPersistent(True)
                device.updatedps()

                # Get Status
                data = device.status() 
                print('%r' % data)
                current_time = strftime("%Y-%m-%d %H:%M:%S")

                # https://github.com/jasonacox/tinytuya?tab=readme-ov-file#version-33---plug-switch-power-strip-type
                raw_Current = data['dps'].get('18')  # Current in mA
                raw_W = data['dps'].get('19')  # Power in W*10
                raw_V = data['dps'].get('20')  # Voltage in V*10
                gpu_usage = get_gpu_usage()

                # Convert values if they exist
                current = float(raw_Current) if raw_Current is not None else None
                power = float(raw_W)/10 if raw_W is not None else None
                voltage = float(raw_V)/10 if raw_V is not None else None

                # Save data to JSON
                save_data(current_time, current, power, voltage, gpu_usage)

                print(f'Time: {current_time}')
                if current is not None:
                    print(f'Current: {current}mA')
                if power is not None:
                    print(f'Power: {power}W')
                if voltage is not None:
                    print(f'Voltage: {voltage}V')
                if gpu_usage is not None:
                    print(f'GPU Usage: {gpu_usage}%')
                
                sleep(5)

            except OSError:
                print("[OSError] Error reading Tuya power meter")
                sleep(5)
                continue
            except ValueError:
                print("[ValueError] Error reading Tuya power meter")
                sleep(5)
                continue
            except KeyError:
                print("[KeyError] Error reading Tuya power meter")
                print("[KeyError] Data:", data)
                sleep(5)
                continue
            except TypeError:
                print("[TypeError] Error reading Tuya power meter")
                print("[TypeError] Data:", data)
                sleep(5)
                continue
    except KeyboardInterrupt:
        print("KeyboardInterrupt")
        return None

if __name__ == "__main__":
    main()