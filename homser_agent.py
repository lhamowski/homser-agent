import os
import time
import yaml
import psutil
import socketio
import logging
import threading

from flask import Flask, request

with open('config.yaml') as f:
    config = yaml.safe_load(f)

sio = socketio.Client()

app = Flask(__name__)

@app.route('/turn-off', methods=['PUT'])
def turn_off():
    try:
        def shutdown():
            time.sleep(1)
            os.system('sudo shutdown now')

        sio.disconnect()
        threading.Thread(target=shutdown).start()
        return 'Turned off successfully', 200
    except Exception as e:
        return f'Error turning off: {str(e)}', 500

def send_info():
    try:
        cpu_usage = psutil.cpu_percent()
        cpu_temp = round(psutil.sensors_temperatures()['k10temp'][0].current)

        ram = psutil.virtual_memory()
        ram_usage = f"{round(ram.used / (1024**3), 1):.1f}/{round(ram.total / (1024**3), 1):.1f}"

        agent_id = config['agent_id']

        sio.emit('RemoteServerMetrics', {
            'id': agent_id,
            'cpuUsage': cpu_usage,
            'cpuTemp': cpu_temp,
            'ramUsage': ram_usage
        })

        logging.info(f"Agent {agent_id} - CPU: {cpu_usage}%, Temp: {cpu_temp}°C, RAM: {ram_usage}GB")
    except Exception as e:
        logging.error(f"Error sending info: {str(e)}")

connected = False

@sio.event
def connect():
    global connected
    connected = True
    print('Connected to server')
    while connected:
        send_info()
        time.sleep(config['send_interval'])

@sio.event
def disconnect():
    global connected
    connected = False
    print('Disconnected from server')

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    logging.info('Starting agent server_url=%s', config['server_url'])

    threading.Thread(target=app.run, kwargs={'host': config['host'], 'port': config['port']}).start()
    
    while True:
        try:
            sio.connect(config['server_url'])
            break
        except Exception as e:
            logging.error(f"Error connecting to server: {str(e)}")
            time.sleep(5)

    sio.wait()