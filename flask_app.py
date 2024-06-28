import os
from pathlib import Path
from dotenv import load_dotenv
import requests
from slack_sdk import WebClient
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import urllib.request
import ssl
import certifi
import re
import logging
import threading
import queue
import time as tm
from datetime import datetime, timedelta

###########################################################################
##### Print Tool Section. Will be used throughoout entire script. 
###########################################################################

# Define ANSI escape codes as constants
BOLD = "\033[1m"
LESS_VISIBLE = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
TEAL = "\033[34m"
HIGHLIGHT_GREEN = "\033[36m"
RED = "\033[38;5;196m"
BLUE_BG = "\033[48;5;4m"
RESET = "\033[0m"

# Create a dictionary to map color names to ANSI escape codes
COLORS = {
    "C1": TEAL,
    "C2": HIGHLIGHT_GREEN,
    "C3": RED,
    # Add more colors as needed
}

def format_string(text, color=None, bold=False, italic=False, less_visible=False):
    return f"{BOLD if bold else ''}{ITALIC if italic else ''}{LESS_VISIBLE if less_visible else ''}{COLORS[color] if color else ''}{text}{RESET}"

formatted_dot = format_string('.', 'C2', bold=True)

def dynamic_counter_indicator(stop_event):
    dot_counter = 0
    total_dots = 0
    
    while not stop_event.is_set():
        tm.sleep(0.45)  # Wait for 0.3 second
        print(f"{formatted_dot}", end="", flush=True)
        dot_counter += 1
        total_dots += 1

        if dot_counter == 4:
            terminal_width = os.get_terminal_size().columns
            print("\r" + " " * min(len(f"") + total_dots + 10, terminal_width) + "\r", end="", flush=True)
            dot_counter = 0
            if stop_event.is_set():
                break
    tm.sleep(0.10)


###########################################################################
##### The Methods that we will use in this scipt are below
###########################################################################

# 新增配置部分
BUFFER_TIME = 20  # 緩衝期時間（秒）
jenkins_job_url = "https://balanced-poorly-shiner.ngrok-free.app/generic-webhook-trigger/invoke?token=generic-webhook-trigger"

# 配置日誌，HTTPS 處理和 Slack 客戶端初始化部分)
logging.basicConfig(filename='app.log', level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
https_handler = urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where()))
opener = urllib.request.build_opener(https_handler)
urllib.request.install_opener(opener)
response = urllib.request.urlopen('https://example.com')
handler = logging.FileHandler('/Users/mac/Desktop/GCal-Notion-Sync/log/app.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
logger.info('This is an info message.')
logger.error('This is an error message.')

current_path = os.getcwd()
env_path = '/Users/mac/Documents/pythonProjects/Notion-and-Google-Calendar-2-Way-Sync-main/.env'
load_dotenv(env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)
client = WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

# 消息緩衝區
message_buffer = []
buffer_lock = threading.Lock()
buffer_timer = None
message_queue = queue.Queue()
message_sent = False
match_multiple_found = False

def process_buffer():
    global message_buffer, buffer_timer, message_sent, match_multiple_found
    with buffer_lock:
        if not message_buffer:
            return

        logging.info(f"Processing {len(message_buffer)} messages from buffer")
        
        # 分類消息
        previous_messages = [msg for msg in message_buffer if "Previous" in msg['text']]
        other_messages = [msg for msg in message_buffer if "Previous" not in msg['text']]

        # 處理非 Previous 消息
        if other_messages:
            channel_id = other_messages[0]['channel']
            triggered_jobs = trigger_jenkins_job()
            if triggered_jobs:
                message = f"{triggered_jobs}\n更新中。請稍等 · · ·"
                client.chat_postMessage(channel=channel_id, text=message)

        # 處理 Previous 消息
        if previous_messages:
            channel_id = previous_messages[0]['channel']
            client.chat_postMessage(channel=channel_id, text="N. Database 已更新 ✅")

        message_buffer.clear()
        buffer_timer = None
        message_sent = False
        match_multiple_found = False


def trigger_jenkins_job():
    try:
        response = requests.get(jenkins_job_url)
        if response.status_code == 200:
            logging.info("Jenkins job triggered successfully")
            response_data = response.json()
            jobs = response_data.get('jobs', {})
            job_names = ', '.join(jobs.keys())
            return f"✦ {job_names}"
        else:
            logging.error(f"Failed to trigger Jenkins job. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error triggering Jenkins job: {e}")
    return None

@slack_event_adapter.on('message')
def message(payload):
    global buffer_timer
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    
    if BOT_ID != user_id:
        with buffer_lock:
            message_buffer.append({'channel': channel_id, 'text': text})
            
            if buffer_timer is None:
                buffer_timer = threading.Timer(BUFFER_TIME, process_buffer)
                buffer_timer.start()

@app.route('/triggerjob', methods=['GET', 'POST'])
def triggerjob():
    if request.method == 'POST':
        data = request.form
    else:
        data = request.args

    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    text = data.get('text')
    
    with buffer_lock:
        message_buffer.append({'channel': channel_id, 'text': text})
        
        if buffer_timer is None:
            buffer_timer = threading.Timer(BUFFER_TIME, process_buffer)
            buffer_timer.start()
    
    return Response(), 200

print("\n")

stop_event = threading.Event()
thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event,))
thread.start()

@app.route('/')
def home():
    return "Flask server is running"


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, port=8080)

stop_event.set()
thread.join()