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
from notion_client import Client

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
##### The Set-Up Section. Please follow the comments to understand the code. 
###########################################################################

# Constants
Task_Notion_Name = 'Task Name' 
Date_Notion_Name = 'StartEnd'
Start_Notion_Name = 'Start'
End_Notion_Name = 'End'
Initiative_Notion_Name = 'Initiative'
ExtraInfo_Notion_Name = 'Notes'
On_GCal_Notion_Name = 'On GCal?'
to_Auto_Sync_Notion_Name = 'to Auto-Sync'
NeedGCalUpdate_Notion_Name = 'NeedGCalUpdate'
GCalEventId_Notion_Name = 'GCal Event Id'
LastUpdatedTime_Notion_Name  = 'Last Updated Time'
LastEditedTime_Notion_Name = 'Last Edited Time'
Calendar_Notion_Name = 'Calendar'
Current_Calendar_Id_Notion_Name = 'Current Calendar Id'
Delete_Notion_Name = 'Delete from GCal?'

###########################################################################
##### The Methods that we will use in this scipt are below
###########################################################################

# 新增配置部分
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

# 初始化 Notion 客戶端
notion = Client(auth=os.environ["NOTION_API_KEY"])

# 設置 Notion 數據庫 ID
NOTION_DATABASE_ID = os.environ["NOTION_DATABASE_ID"]

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)
client = WebClient(token=os.environ['SLACK_TOKEN'])

# 修改消息緩衝區相關變量
message_buffer = []
buffer_lock = threading.Lock()
buffer_timer = None
BUFFER_TIME = 20

# 计算编辑距离的函数
def levenshtein(s1, s2):
    if len(s1) < len(s2):
        return levenshtein(s2, s1)

    if len(s2) == 0:
        return len(s1)

    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


keyword = "sync"
# 使用正则表达式匹配任何由字母组成的字符串，不区分大小写
match = re.match(r'^[a-zA-Z]+$', keyword, re.IGNORECASE)
threshold = 2  # 设置编辑距离的阈值
no_change_notified = False

BOT_ID = client.api_call("auth.test")['user_id']
NOTION_USER_ID = "U072XCLK9L5"
SLACK_USER_ID = "U07309GQP18"
SLACK_BOT_ID = "U073CA7EUCF"

def is_message_from_notion(user_id):
    return user_id == NOTION_USER_ID

def is_message_from_slack_user(user_id):
    return user_id == SLACK_USER_ID

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

def trigger_and_notify(channel_id):
    global no_change_notified
    triggered_jobs = trigger_jenkins_job()
    message = f"{triggered_jobs}\n检查中 · · ·" if triggered_jobs else ""
    client.chat_postMessage(channel=channel_id, text=message)
    no_change_notified = True

@slack_event_adapter.on('message')
def message(payload):
    global no_change_notified, buffer_timer
    no_change_notified = False
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text').lower()  # 转换为小写以便不区分大小写的匹配

    # 分類消息
    previous_messages = [msg for msg in message_buffer if "Previous" in msg['text']]
    other_messages = [msg for msg in message_buffer if "Previous" not in msg['text']]

    # 检查消息是否来自Notion
    if is_message_from_notion(user_id):
        print("\n\nMessage from Notion")           
        with buffer_lock:
            message_buffer.append({'channel': channel_id, 'text': text, 'user_id': user_id})
            
            if buffer_timer is None:
                buffer_timer = threading.Timer(BUFFER_TIME, process_buffer)
                buffer_timer.start()


        if other_messages:
            message = f"{triggered_jobs}\n检查中 · · ·" if triggered_jobs else ""
            client.chat_postMessage(channel=channel_id, text=message)
            triggered_jobs = trigger_jenkins_job()
                
        elif previous_messages:
            print(f"got previous : {previous_messages}")
            client.chat_postMessage(channel=channel_id, text="確認完畢 ✅✅")
        no_change_notified = True
        
    else:
        # 消息来自真实用户的处理逻辑
        if BOT_ID != user_id:  # 确保消息来自用户而非机器人
            with buffer_lock:
                message_buffer.append({'channel': channel_id, 'text': text, 'user_id': user_id})
                
                if buffer_timer is None:
                    buffer_timer = threading.Timer(BUFFER_TIME, process_buffer)
                    buffer_timer.start()

            # 计算编辑距离
            distance = levenshtein(text, keyword)
            
            if text == keyword:  # 直接处理 sync 关键词
                client.chat_postMessage(channel=channel_id, text="⚡️ 成功触发")
                trigger_and_notify(channel_id)
                return Response(), 200
            elif distance <= threshold:
                client.chat_postMessage(channel=channel_id, text=f"是要 `{keyword}` 嗎？  試再輸入一次")
            else:
                if text and not no_change_notified:
                    client.chat_postMessage(channel=channel_id, text=f"Tips：\n\n`{keyword}` = 触发 Jenkins Pipeline")
    return Response(), 200

updated_tasks = []  # 用于存储在过去5分钟内更新的任务
def check_for_updates():
    try:
        # 获取数据库中最近更新的页面
        response = notion.databases.query(
            database_id=NOTION_DATABASE_ID,
            sorts=[
                {
                    "property": Task_Notion_Name,
                    "direction": "descending"
                },
                {
                    "property": LastEditedTime_Notion_Name,
                    "direction": "descending"
                }]
            # 移除page_size=1以获取所有结果
        )

        for result in response["results"]:
            task_Name = result["properties"]["Task Name"]["title"][0]["text"]["content"]
            last_edited_time = result["last_edited_time"]
            last_edited_datetime = datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))
            
            # 检查最后编辑时间是否在过去5分钟内
            if datetime.now(last_edited_datetime.tzinfo) - last_edited_datetime < timedelta(minutes=5):
                updated_tasks.append((task_Name, last_edited_time))  # 添加到列表中

        if updated_tasks:
            for task, time in updated_tasks:
                print(f"\nFound recent update in Notion :")
                print(f"{task}   {time}")
            return True, updated_tasks
        else:
            print("\nNo recent updates found in Notion")
            return False, []

    except Exception as e:
        print(f"\nError checking for updates in Notion: {e}")
        return False, []

received_previous_start = False
received_previous_end = False

def process_buffer():
    global message_buffer, buffer_timer, updated_tasks
    channel_id = message_buffer[0]['channel']
    with buffer_lock:
        # Copy and clear the buffer at the beginning
        current_buffer = message_buffer.copy()
        message_buffer.clear()
        if not current_buffer:
            return

        print(f"\n\nProcessing {len(current_buffer)} message from buffer")
        
        # 分类消息
        previous_start_messages = [msg for msg in current_buffer if "Previous Start" in msg['text']]
        previous_end_messages = [msg for msg in current_buffer if "Previous End" in msg['text']]

        # Start a timer on receiving the first "Previous" message
        if previous_start_messages or previous_end_messages:
            received_previous_start = True if previous_start_messages else False
            received_previous_end = True if previous_end_messages else False
            print(f"got previous : {previous_start_messages} {previous_end_messages}")
            threading.Timer(BUFFER_TIME, check_and_confirm, [channel_id]).start()

        # 检查是否有任何更新
        check_for_updates()
        if updated_tasks:
            updates_count = len(updated_tasks)  # 计算已修改的 Notion 事件总数
            client.chat_postMessage(channel=channel_id, text=f"{updates_count}  件同步完成 ✅")
        else:
            client.chat_postMessage(channel=channel_id, text="Notion 暫無變更 🥕")
        
        buffer_timer = None
    return response, 200


def check_and_confirm(channel_id):
    if received_previous_start and received_previous_end:
        client.chat_postMessage(channel=channel_id, text="確認完畢 ✅✅")
    else:
        print("Did not receive all notifications within the time limit.")

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