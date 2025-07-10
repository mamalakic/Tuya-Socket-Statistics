from flask import Flask, render_template, jsonify, request
import json
from datetime import datetime
import os
import subprocess
import psutil
from collections import defaultdict

app = Flask(__name__)

# Global variable to store the power monitor process
power_monitor_process = None

def format_timestamp(timestamp_str):
    try:
        dt = datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        return dt.strftime("%b %d %H:%M")
    except:
        return timestamp_str

def load_column_config():
    config_file = "data_config.json"
    if os.path.exists(config_file):
        with open(config_file, 'r') as f:
            return json.load(f)
    return {
        'timestamp': 'str',
        'current_ma': 'float',
        'power_w': 'float',
        'voltage_v': 'float',
        'gpu_usage': 'float'
    }

def read_power_data(avg='5s'):
    columns = load_column_config()
    data = {col: [] for col in columns.keys()}
    try:
        with open('power_data.json', 'r') as f:
            json_data = json.load(f)
            if avg == '1m':
                # TODO:
                # Group by minute
                grouped = defaultdict(list)
                for entry in json_data:
                    ts = entry.get('timestamp')
                    if ts:
                        minute = ts[:16]  # 'YYYY-MM-DD HH:MM'
                        grouped[minute].append(entry)
                for minute, entries in grouped.items():
                    avg_entry = {'timestamp': minute + ':00'}
                    for col in columns.keys():
                        if col == 'timestamp':
                            continue
                        values = [float(e.get(col)) for e in entries if e.get(col) is not None]
                        avg_entry[col] = sum(values)/len(values) if values else None
                    for col in columns.keys():
                        data[col].append(avg_entry.get(col) if col != 'timestamp' else avg_entry['timestamp'])
            else:
                for entry in json_data:
                    # Format timestamp
                    if 'timestamp' in entry:
                        data['timestamp'].append(format_timestamp(entry['timestamp']))
                    # Convert numeric values
                    for col in columns.keys():
                        if col != 'timestamp':
                            value = entry.get(col)
                            if value is not None:
                                try:
                                    data[col].append(float(value))
                                except (ValueError, TypeError):
                                    data[col].append(None)
                            else:
                                data[col].append(None)
    except FileNotFoundError:
        pass
    return data

def calculate_costs():
    try:
        with open('power_data.json', 'r') as f:
            data = json.load(f)
            
        if not data:
            return {
                'day': 0,
                'week': 0,
                'month': 0,
                'year': 0
            }
            
        # Read cost and usage from config
        with open('config.json', 'r') as f:
            config = json.load(f)
            cost_per_kwh = config.get('electricity_cost_per_kwh', 0)
            usage_hours = config.get('usage_hours', 24)
            
        # Calculate average power in kW
        power_values = [float(entry['power_w']) for entry in data if 'power_w' in entry and entry['power_w'] is not None]
        if not power_values:
            return {
                'day': 0,
                'week': 0,
                'month': 0,
                'year': 0
            }
            
        total_power = sum(power_values) / len(power_values)
        avg_power_kw = total_power / 1000  # Convert W to kW
        
        # Calculate costs based on usage hours
        day_cost = avg_power_kw * usage_hours * cost_per_kwh
        week_cost = day_cost * 7
        month_cost = day_cost * 30
        year_cost = day_cost * 365
        
        return {
            'day': round(day_cost, 2),
            'week': round(week_cost, 2),
            'month': round(month_cost, 2),
            'year': round(year_cost, 2)
        }
    except Exception as e:
        print(f"Error calculating costs: {e}")
        return {
            'day': 0,
            'week': 0,
            'month': 0,
            'year': 0
        }

def calculate_power_statistics():
    try:
        with open('power_data.json', 'r') as f:
            data = json.load(f)
            
        if not data:
            return {
                'total_kwh': 0,
                'total_hours': 0,
                'avg_kwh_per_day': 0,
                'peak_power': 0,
                'median_power': 0,
                'min_power': 0,
                'total_samples': 0
            }
            
        # Convert timestamps to datetime objects
        timestamps = [datetime.strptime(entry['timestamp'], "%Y-%m-%d %H:%M:%S") for entry in data if 'timestamp' in entry]
        
        if not timestamps:
            return {
                'total_kwh': 0,
                'total_hours': 0,
                'avg_kwh_per_day': 0,
                'peak_power': 0,
                'median_power': 0,
                'min_power': 0,
                'total_samples': 0
            }
            
        # Calculate time span
        start_time = min(timestamps)
        end_time = max(timestamps)
        total_hours = (end_time - start_time).total_seconds() / 3600
        
        # Calculate power statistics
        power_values = [float(entry['power_w']) for entry in data if 'power_w' in entry and entry['power_w'] is not None]
        
        if not power_values:
            return {
                'total_kwh': 0,
                'total_hours': 0,
                'avg_kwh_per_day': 0,
                'peak_power': 0,
                'median_power': 0,
                'min_power': 0,
                'total_samples': 0
            }
            
        # Calculate total kWh (assuming 5-second intervals between measurements)
        total_kwh = sum(power_values) * (5/3600) / 1000  # Convert W to kW and multiply by hours
        
        # Calculate average kWh per day
        days_recorded = total_hours / 24
        avg_kwh_per_day = total_kwh / days_recorded if days_recorded > 0 else 0
        
        # Calculate median power
        sorted_power = sorted(power_values)
        n = len(sorted_power)
        if n % 2 == 0:
            median_power = (sorted_power[n//2 - 1] + sorted_power[n//2]) / 2
        else:
            median_power = sorted_power[n//2]
        
        return {
            'total_kwh': round(total_kwh, 2),
            'total_hours': round(total_hours, 1),
            'avg_kwh_per_day': round(avg_kwh_per_day, 2),
            'peak_power': round(max(power_values), 1),
            'median_power': round(median_power, 1),
            'min_power': round(min(power_values), 1),
            'total_samples': len(power_values)
        }
    except Exception as e:
        print(f"Error calculating power statistics: {e}")
        return {
            'total_kwh': 0,
            'total_hours': 0,
            'avg_kwh_per_day': 0,
            'peak_power': 0,
            'median_power': 0,
            'min_power': 0,
            'total_samples': 0
        }

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data')
def get_data():
    avg = request.args.get('avg', '5s')
    return jsonify(read_power_data(avg=avg))

@app.route('/costs')
def get_costs():
    return jsonify(calculate_costs())

@app.route('/update_cost', methods=['POST'])
def update_cost():
    try:
        data = request.json
        cost = float(data.get('cost', 0))
        usage_hours = float(data.get('usage_hours', 24))
        
        # Validate usage hours
        if not 0 <= usage_hours <= 24:
            return jsonify({'success': False, 'error': 'Usage hours must be between 0 and 24'})
            
        with open('config.json', 'w') as f:
            json.dump({
                'electricity_cost_per_kwh': cost,
                'usage_hours': usage_hours
            }, f)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/toggle_recording', methods=['POST'])
def toggle_recording():
    global power_monitor_process
    try:
        data = request.json
        should_record = data.get('record', False)
        
        if should_record:
            # Start the power monitor script if it's not already running
            if power_monitor_process is None or power_monitor_process.poll() is not None:
                power_monitor_process = subprocess.Popen(['python', 'power_monitor_working.py'])
                return jsonify({'success': True, 'status': 'started'})
        else:
            # Stop the power monitor script if it's running
            if power_monitor_process is not None and power_monitor_process.poll() is None:
                # Find all child processes
                parent = psutil.Process(power_monitor_process.pid)
                children = parent.children(recursive=True)
                
                # Terminate child processes first
                for child in children:
                    child.terminate()
                
                # Terminate the main process
                power_monitor_process.terminate()
                power_monitor_process = None
                return jsonify({'success': True, 'status': 'stopped'})
        
        return jsonify({'success': True, 'status': 'unchanged'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/recording_status')
def recording_status():
    global power_monitor_process
    is_running = power_monitor_process is not None and power_monitor_process.poll() is None
    return jsonify({'is_recording': is_running})

@app.route('/statistics')
def get_statistics():
    return jsonify(calculate_power_statistics())

@app.route('/config')
def get_config():
    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
            return jsonify({
                'electricity_cost_per_kwh': config.get('electricity_cost_per_kwh', 0),
                'usage_hours': config.get('usage_hours', 24)
            })
    except Exception as e:
        return jsonify({'electricity_cost_per_kwh': 0, 'usage_hours': 24, 'error': str(e)})

if __name__ == '__main__':
    app.run(debug=True) 