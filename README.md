# Smart Socket Statistics


## Description
Power consumption metering with graphs and calculate electricity costs. Uses tinytuya for local access to the smart device (socket) and the flask framework for a minimal site.

## Installation / How to use
```
pip install -r requirements.txt
```

Using tinytua's wizard, get the required ID, IP and local key of your device:
```
python -m tinytuya wizard
```
The results will be stored in a json. Enter these values in .env

After that, the flask app is ready:
```
python app.py
```

Start logging power consumption information using power_monitor_working.py. You can do this by enabling "Record Statistics" on the flask app.

### Extra
If your logging file gets too big, there is an additional script that compresses older data into 1-minute averages (instead of the original measurements that happen every 5 seconds).
```
python compress_data.py
```

Optionally, you can automate this using a Windows Task Scheduler (or whatever else for other operating systems)
```
@echo off
cd /d "%~dp0"
python compress_data.py 
```


## Current issues
- GPU usage metering works only for NVIDIA GPUs