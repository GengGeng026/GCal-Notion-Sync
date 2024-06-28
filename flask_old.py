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

# Create a HTTPS handler with certifi's bundle of certificate authorities
https_handler = urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where()))

# Create an opener that will use this handler
opener = urllib.request.build_opener(https_handler)

# Install the opener
urllib.request.install_opener(opener)

# Now, when you use urllib.request.urlopen, it will use the opener with certifi's bundle of certificate authorities
response = urllib.request.urlopen('https://example.com')

load_dotenv()

# 創建一個日誌處理器，將日誌寫入到文件中
handler = logging.FileHandler('/Users/mac/Desktop/GCal-Notion-Sync/log/app.log')
handler.setLevel(logging.INFO)

# 創建一個日誌格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 獲取 root logger，並添加我們剛剛創建的處理器
logger = logging.getLogger()
logger.addHandler(handler)

# 現在，你可以使用 logger.info() 和 logger.error() 來寫入日誌
logger.info('This is an info message.')
logger.error('This is an error message.')

# 獲取當前工作目錄
current_path = os.getcwd()

# .env 文件的絕對路徑
env_path = '/Users/mac/Documents/pythonProjects/Notion-and-Google-Calendar-2-Way-Sync-main/.env'


# 加載 .env 文件
load_dotenv(env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events', app)
print("\n")

client = WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    
    if BOT_ID != user_id:
        if any(keyword in text for keyword in ["Previous Start", "Previous End", "StarEnd"]):
            client.chat_postMessage(channel=channel_id, text="已更新 ✅ ")
        elif "edited in Tutorial Database" in text:  # 检查消息文本是否包含 "edited in Tutorial Database"
            trigger_status(user_id, channel_id, text)  # 调用触发Job的函数
        else:
            if text:  # 检查 text 变量是否不是空的
                client.chat_postMessage(channel=channel_id, text=text)


@app.route('/triggerjob', methods=['GET', 'POST'])
def triggerjob():
    if request.method == 'POST':
        data = request.form
    else:
        data = request.args

    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    client.chat_postMessage(channel=channel_id, text="I got the command")
    text = data.get('text')
    
    # Trigger the Jenkins job
    trigger_status(user_id, channel_id, text) 
    return Response(), 200

# 在函数外部定义一个字典来存储每个页面的最后状态
timer = None
job_names = None 
message_sent = False  # 新增的全局变量
message_list = []  # New list to keep track of messages in the queue
match_multiple_found = False

# 创建一个队列来存储待发送的消息
message_queue = queue.Queue()

def trigger_status(user_id, channel_id, text):
    global timer, job_names, message_sent, message_queue, message_list, match_multiple_found
    
    message = ""
    
    # 构建Jenkins Job的触发URL
    jenkins_job_url = "https://balanced-poorly-shiner.ngrok-free.app/generic-webhook-trigger/invoke?token=generic-webhook-trigger"

    # 发送请求触发Jenkins Job
    try:
        response = requests.get(jenkins_job_url)
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

        # 使用正则表达式匹配用户名和对象名
        match_user = re.search(os.environ['USER_NAME'], text)
        match_script = re.search(os.environ['SCRIPT_NAME'], text)
        n = re.search(" and ", text, re.IGNORECASE)
        match_multiple = (match_script and n and match_user) or (match_user and n and match_script)
        action = re.search(" edited in| added in", text, re.IGNORECASE)
        
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

# Use the function to format text
formatted_dot = format_string('.', 'C2', bold=True)

# Define a function to print the "Printing" message and dots
def dynamic_counter_indicator(stop_event):
    dot_counter = 0
    total_dots = 0  # New variable to keep track of the total number of dots
    
    while not stop_event.is_set():
        tm.sleep(0.45)  # Wait for 0.3 second
        print(f"{formatted_dot}", end="", flush=True)  # Print the colored dot
        dot_counter += 1
        total_dots += 1  # Increment the total number of dots

        # If the counter reaches 4, reset it and erase the dots
        if dot_counter == 4:
            terminal_width = os.get_terminal_size().columns  # Get the width of the terminal
            print("\r" + " " * min(len(f"") + total_dots + 10, terminal_width) + "\r", end="", flush=True)  # Clear the line and print spaces
            dot_counter = 0
            if stop_event.is_set():  # Check if stop_event is set immediately after resetting the dot_counter
                break
    tm.sleep(0.10)  # Add a small delay
    
# Create a stop event
stop_event = threading.Event()

# Start the separate thread
thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event,))
thread.start()


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

@app.route('/')
def home():
    return "Flask server is running"


if __name__ == '__main__':
    app.run(debug=False, use_reloader=False, port=8080)
    
# Signal the dynamic_counter_indicator function to stop
stop_event.set()

# Wait for the separate thread to finish
thread.join()