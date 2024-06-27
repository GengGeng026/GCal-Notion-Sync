import os
from pathlib import Path
from dotenv import load_dotenv
import requests
from slack_sdk import WebClient
from slack_sdk.webhook import WebhookClient
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import re
import logging
import ssl
import certifi
import urllib.request
import threading
import queue
import time as tm
import threading
import datetime

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

https_handler = urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where()))
opener = urllib.request.build_opener(https_handler)
urllib.request.install_opener(opener)
response = urllib.request.urlopen('https://example.com')

load_dotenv()
env_path = '/Users/mac/Documents/pythonProjects/Notion-and-Google-Calendar-2-Way-Sync-main/.env'

# 創建一個日誌處理器，將日誌寫入到文件中
handler = logging.FileHandler('/Users/mac/Desktop/GCal-Notion-Sync/log/app.log')
handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger = logging.getLogger()
logger.addHandler(handler)
logger.info('This is an info message.')
logger.error('This is an error message.')

current_path = os.getcwd()
load_dotenv(env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)
client = WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']
jenkins_pipeline_url = "https://balanced-poorly-shiner.ngrok-free.app/generic-webhook-trigger/invoke?token=generic-webhook-trigger"
last_triggered_time = 0
cooldown_period = 60  # 设置触发冷却时间为60秒

# 在函数外部定义一个字典来存储每个页面的最后状态
timer = None
job_names = None 
message_sent = False
match_multiple_found = False
message_queue = queue.Queue()
message_list = []


@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    
    if BOT_ID != user_id:
        if any(keyword in text for keyword in ["Previous Start", "Previous End", "StarEnd"]):
            client.chat_postMessage(channel=channel_id, text="已更新 ✅ ")
        elif "edited in Tutorial Database" in text:
            trigger_status(user_id, channel_id, text)
        else:
            if text:
                client.chat_postMessage(channel=channel_id, text=text)

def trigger_status(channel_id, text):
    global timer, job_names, message_sent, message_queue, message_list, match_multiple_found

    # 使用正则表达式匹配用户名和对象名
    match_user = re.search(os.environ['USER_NAME'], text)
    match_script = re.search(os.environ['SCRIPT_NAME'], text)
    n = re.search(" and ", text, re.IGNORECASE)
    match_multiple = (match_script and n and match_user) or (match_user and n and match_script)
    action = re.search(" edited in", text)

    message = ""

    # 发送请求触发Jenkins Job
    try:
        response = requests.get(jenkins_pipeline_url)
    except requests.exceptions.RequestException as e:
        print(f"\n\nError: Failed to trigger Jenkins job: {e}")
        return

    # 检查响应状态码
    if response.status_code == 200:
        
        # 解析 JSON 响应
        response_data = response.json()

        # 构建易读的消息
        jobs = response_data.get('jobs', {})
        job_names = ', '.join(jobs.keys())
        triggered_jobs = f"✦ {job_names}"
        
        if match_user and action and message_queue.empty() and not message_sent:
            message = triggered_jobs + "\n更新中。請稍等 · · ·"
            # 只有在消息队列为空时，才添加消息
            if message not in message_list and message not in message_queue.queue:
                message_queue.put(message)
                message_list.append(message)
            if timer is None:
                timer = threading.Timer(7.0, send_message, args=[channel_id])
                timer.start()
                
        if match_script or match_multiple_found:
            message = "N. Database 已更新 ✅ "
            if message not in message_list and message not in message_queue.queue:
                message_queue.put(message)
                message_list.append(message)
            if timer is None:
                timer = threading.Timer(7.0, send_message, args=[channel_id])
                timer.start()


def send_message(channel_id):
    global message_sent, timer, message_queue, message_list, match_multiple_found

    # 如果消息尚未发送，并且队列中有消息，则发送消息
    while not message_queue.empty():
        message = message_queue.get()
        if message in message_list:
            message_list.remove(message)

        # 使用 Slack 客户端发送消息，并打印 chat_postMessage 方法的响应
        client.chat_postMessage(channel=channel_id, text=message)
        message_sent = True

    # 重置定时器和 message_sent 标志
    timer = None
    message_sent = False
    match_multiple_found = False


@app.route('/triggerjob', methods=['POST'])
def triggerjob():
    global last_triggered_time
    
    current_time = tm.time()
    if current_time - last_triggered_time < cooldown_period:
        return "Trigger cooldown in effect", 429  # 返回429状态码，表示请求太频繁

    # 触发 Jenkins Pipeline
    try:
        response = requests.post(jenkins_pipeline_url)
        if response.status_code == 200:
            last_triggered_time = current_time  # 更新最后触发时间
            return "Jenkins Pipeline triggered successfully", 200
        else:
            return f"Failed to trigger Jenkins Pipeline. Status code: {response.status_code}", 500
    except requests.exceptions.RequestException as e:
        return f"Failed to trigger Jenkins Pipeline: {str(e)}", 500

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