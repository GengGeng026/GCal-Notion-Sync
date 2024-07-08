import os
from pathlib import Path
import pickle
from dotenv import load_dotenv
import requests
from slack_sdk import WebClient
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import urllib.request
import sys
import ssl
import certifi
import re
import logging
import threading
import queue
import time as tm
import time
from datetime import datetime, timedelta
from notion_client import Client
from notion_client.errors import RequestTimeoutError, HTTPResponseError
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from google.auth.exceptions import RefreshError
from googleapiclient.errors import HttpError
import googleapiclient.errors
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from bs4 import BeautifulSoup
import json
import http


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
formatted_right_arrow = format_string(' ▸ ', 'C2', bold=True)
formatted_successful = format_string('Successful', 'C2', bold=True)



stop_event = threading.Event()  # Initialize stop_event
thread = None  # Initialize thread variable

def dynamic_counter_indicator(stop_event, formatted_dot=format_string('.', 'C2', bold=True)):
    dot_counter = 0
    total_dots = 0
    
    while not stop_event.is_set():
        tm.sleep(0.45)
        print(f"{formatted_dot}", end="", flush=True)
        dot_counter += 1
        total_dots += 1

        if dot_counter == 4:
            terminal_width = os.get_terminal_size().columns
            print("\r" + " " * min(len(formatted_dot) * total_dots + 10, terminal_width) + "\r", end="", flush=True)
            dot_counter = 0
            if stop_event.is_set():
                break
    tm.sleep(0.10)


def stop_clear_and_print():
    global stop_event, thread
    if thread is not None:
        stop_event.set()
        thread.join()
    sys.stdout.write("\033[2K")  # 清除整行
    sys.stdout.flush()  # 确保清除命令被立即执行

def start_dynamic_counter_indicator():
    global stop_event, thread
    stop_event = threading.Event()
    thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event, format_string('.', 'C2', bold=True)))
    thread.start()

def format_gradient(text, bold_indices=(0, 0), less_visible_indices=(0, 0)):
    formatted_text = ""
    for i, char in enumerate(text):
        if bold_indices[0] <= i < bold_indices[1]:  # Bold part
            formatted_text += f"{BOLD}{char}{RESET}"
        elif less_visible_indices[0] <= i < less_visible_indices[1]:  # Less visible part
            formatted_text += f"{LESS_VISIBLE}{char}{RESET}"
        else:  # Normal visibility
            formatted_text += char
    return formatted_text

def animate_text_wave(text, repeat=1, sleep_time=0.01):
    length = len(text)
    animation_chars = ['/', '-', '\\', '|']
    for _ in range(repeat):
        for i in range(length + 2):  # 去除不必要的浮點數迭代
            wave_text = ""
            for j in range(length):
                if j >= i - 1 and j < i + 2:
                    wave_text += text[j].upper()
                else:
                    wave_text += text[j].lower()

            current_animation_char = animation_chars[i % len(animation_chars)]
            animated_text = format_gradient(wave_text, bold_indices=(max(0, i - 1), min(length, i + 2)), less_visible_indices=(max(0, i - 3), max(0, i - 1)))

            sys.stdout.write(f"\r{animated_text} {current_animation_char}")
            sys.stdout.flush()
            time.sleep(sleep_time)

        sys.stdout.write(f"\r{text}  ")  # 清除動畫
        sys.stdout.flush()
        time.sleep(sleep_time)

# 添加的全局变量和新函数定义
global_progress = 0

def animate_text_wave_with_progress(text, new_text, target_percentage, current_progress=0, sleep_time=0.02, percentage_first=True):
    global global_progress
    if current_progress < global_progress:
        current_progress = global_progress
    length = len(text)
    animation_chars = ['/', '-', '\\', '|']
    total_iterations = 50
    iteration_step = (target_percentage - current_progress) / total_iterations

    start_time = time.time()
    while current_progress < target_percentage:
        elapsed_time = time.time() - start_time
        if elapsed_time > 5:
            break

        wave_text = ""
        for i in range(length):
            wave_text += text[i].upper() if i % 2 == int(current_progress) % 2 else text[i].lower()

        current_animation_char = animation_chars[int(current_progress) % len(animation_chars)]
        if percentage_first:
            display_text = f"{int(current_progress)}%  {new_text}  {current_animation_char}"
        else:
            display_text = f"{new_text}  {current_animation_char}  {int(current_progress)}%"

        animated_text = format_gradient(display_text, bold_indices=(max(0, int(current_progress / 2) - 1), min(length, int(current_progress / 2) + 2)), less_visible_indices=(max(0, int(current_progress / 2) - 3), max(0, int(current_progress / 2) - 1)))

        sys.stdout.write(f"\r{animated_text}")
        sys.stdout.flush()

        current_progress += iteration_step
        time.sleep(sleep_time)

    global_progress = target_percentage
    if percentage_first:
        final_text = f"{target_percentage}%  {new_text}"
    else:
        final_text = f"{new_text}  {target_percentage}%"
    sys.stdout.write(f"\r{final_text}") 
    sys.stdout.flush()

###########################################################################
##### The Set-Up Section. Please follow the comments to understand the code. 
###########################################################################

# Constants
Task_Notion_Name = 'Task Name' 
Date_Notion_Name = 'StartEnd'
Start_Notion_Name = 'Start'
End_Notion_Name = 'End'
Previous_Start_Notion_Name = 'Previous Start'
Previous_End_Notion_Name = 'Previous End'
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


load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_API_KEY") #the secret_something from Notion Integration

# Create an instance of the Notion client
notion = Client(auth=NOTION_TOKEN)

database_id = os.getenv("NOTION_DATABASE_ID") #get the mess of numbers before the "?" on your dashboard URL (no need to split into dashes)

urlRoot = os.getenv("NOTION_DATABASE_URL") #open up a task and then copy the URL root up to the "p="

### MULTIPLE CALENDAR PART:
#  - VERY IMPORTANT: For each 'key' of the dictionary, make sure that you make that EXACT thing in the Notion database first before running the code. You WILL have an error and your dashboard/calendar will be messed up

DEFAULT_CALENDAR_ID = os.getenv("GOOGLE_PRIVATE_CALENDAR_ID") #The GCal calendar id. The format is something like "sldkjfliksedjgodsfhgshglsj@group.calendar.google.com"

DEFAULT_CALENDAR_NAME = 'Life'


#leave the first entry as is
#the structure should be as follows:              WHAT_THE_OPTION_IN_NOTION_IS_CALLED : GCAL_CALENDAR_ID 
calendarDictionary = {
    DEFAULT_CALENDAR_NAME : DEFAULT_CALENDAR_ID, 
    'Life' : os.getenv("GOOGLE_PRIVATE_CALENDAR_ID"),  #just typed some random ids but put the one for your calendars here
    'Soka': os.getenv("GOOGLE_SOKA_CALENDAR_ID"),
    'Work': os.getenv("GOOGLE_WORK_CALENDAR_ID"),
}


#######################################################################################
###               No additional user editing beyond this point is needed            ###
#######################################################################################

# Create a lock
token_lock = threading.Lock()

# Constants
CREDENTIALS_LOCATION = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_LOCATION")
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CALENDAR_CLI_SECRET_FILE")
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']
DEFAULT_CALENDAR_ID = 'primary'  # Replace with your Calendar ID

def event_exists(service, calendar_id, event_id):
    try:
        service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except googleapiclient.errors.HttpError:
        return False

# Function to refresh token
def refresh_token():
    credentials = None
    stop_event = threading.Event()  # Define stop_event at the beginning
    thread = threading.Thread()  # Initialize thread variable
    if os.path.exists(CREDENTIALS_LOCATION):
        with open(CREDENTIALS_LOCATION, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError:
                os.remove(CREDENTIALS_LOCATION)
                return refresh_token()
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open(CREDENTIALS_LOCATION, 'wb') as token:
            pickle.dump(credentials, token)
        stop_event.set()
        if thread.is_alive():  # Check if thread is alive before joining
            thread.join()
        sys.stdout.write("\033[2K") # 清除整行
        sys.stdout.flush()  # 确保清除命令被立即执行
        print(f"\n{formatted_successful} Authentication / Refresh Token")
        stop_event = threading.Event()
        thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event, "."))
        thread.start()
    return credentials

# Function to obtain calendar
def obtain_calendar(service):
    try:
        calendar = service.calendars().get(calendarId=DEFAULT_CALENDAR_ID).execute()
    except Exception as e:
        # 僅捕獲和記錄必要的錯誤信息
        logging.error('Error obtaining calendar: %s', e)
        # 在發生錯誤時，重新授權並重新初始化服務
        credentials = refresh_token()
        service = build("calendar", "v3", credentials=credentials)
        try:
            calendar = service.calendars().get(calendarId=DEFAULT_CALENDAR_ID).execute()
        except Exception as e:
            # 如果仍然無法獲取日曆，則記錄錯誤並返回 None
            logging.error('Error obtaining calendar after refreshing credentials: %s', e)
            calendar = None
    return calendar

# Main code
try:
    animate_text_wave("initializing", repeat=1)
    print("\r\033[K", end="")
    credentials = refresh_token()
    service = build("calendar", "v3", credentials=credentials)
    calendar = obtain_calendar(service)
finally:
    start_dynamic_counter_indicator()

###########################################################################
##### The Methods that we will use in this scipt are below
###########################################################################

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

jenkins_url = 'http://localhost:8081'
username = 'admin'
password = 'admin'
job_name = 'TimeLinker'
api_url = f'{jenkins_url}/job/{job_name}/api/json'
pipeline_url = f'{jenkins_url}/job/{job_name}/lastBuild/consoleText'

jenkins_job_url = "https://balanced-poorly-shiner.ngrok-free.app/generic-webhook-trigger/invoke?token=generic-webhook-trigger"


# Authenticate and retrieve the build information
def check_last_line_status(text):
    response = requests.get(pipeline_url, auth=(username, password))
    if response.status_code == 200:
        lines = response.text.split('\n')
        status = 'Unknown'
        no_changes = False
        for line in lines:
            if 'Total Pages  : 0' in line or 'No Page Modified' in line:
                no_changes = True
            elif line.startswith('Finished: SUCCESS'):
                status = 'SUCCESS'
            elif line.startswith('Finished: FAILURE'):
                status = 'FAILURE'
        
        if status == 'SUCCESS' and no_changes:
            return 'No Change'
        else:
            return status
    else:
        print(f'Failed to retrieve pipeline status: {response.status_code}')
        return 'Unknown'


modified_pages_count = 0

def extract_number(text):
    pattern = r"Total\s+Pages\s+Modified\s*:\s*(\d+)"
    match = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    if match:
        print(f"匹配到的文本: {match.group(0)}")
        print(f"提取的數字: {match.group(1)}")
        return int(match.group(1))
    else:
        print("未找到匹配的文本")
        return None

def check_pipeline_status(jenkins_url, username, password, job_name):
    global modified_pages_count
    pipeline_url = f'{jenkins_url}/job/{job_name}/lastBuild/consoleText'
    response = requests.get(pipeline_url, auth=(username, password))
    
    if response.status_code == 200:
        # print("完整的 response.text:")
        # print(response.text)
        # print("------------------------")

        lines = response.text.split('\n')
        status = 'Unknown'
        no_changes = False
        modified_pages_count = None
        
        for line in lines:
            # print(f"處理行: {line}")
            if 'Total Pages Modified : 0' in line:
                no_changes = True
                # print("發現 'Total Pages Modified : 0'")
            elif line.startswith('Finished: SUCCESS') or 'Total Pages' in line:
                status = 'SUCCESS'
                # print("設置 status 為 'SUCCESS'")
            if 'Total Pages Modified' in line:
                # print(f"發現 'Total Pages Modified'，原始行內容: '{line}'")
                parts = line.split(':')
                if len(parts) == 2:
                    # try:
                        modified_pages_count = int(parts[1].strip())
                #         print(f"提取的數字: {modified_pages_count}")
                #     except ValueError:
                #         print(f"無法將 '{parts[1].strip()}' 轉換為整數")
                # else:
                #     print(f"無法分割行: '{line}'")
            elif line.startswith('Finished: FAILURE'):
                status = 'FAILURE'
                # print("設置 status 為 'FAILURE'")
        
        # print(f"最終的 modified_pages_count : {modified_pages_count}")
        
        if status == 'SUCCESS' and no_changes:
            return 'No Change'
        else:
            return status
    else:
        print(f'無法獲取管道狀態: {response.status_code}')
        return 'Unknown', None

updated_tasks = []  # 用于存储在过去5分钟内更新的任务
received_previous_start = False
received_previous_end = False
last_message_was_related = False  # 用於跟踪上一次消息是否與關鍵字相關
waiting_for_confirmation = False  # 用於標記是否正在等待用戶確認
confirmation_message_sent = False  # 用於標記是否已經發送確認消息
last_triggered_keyword = None  # 用於跟踪最後一次觸發的關鍵字
last_message = None

def trigger_jenkins_job():
    response = requests.get(api_url, auth=(username, password))
    if response.status_code == 200:
        build_info = response.json()
        build_number = build_info['lastBuild']['number'] + 1
        current_build_number = f" ` {build_number} ` "
    try:
        response = requests.get(jenkins_job_url, timeout=0.05)
        if response.status_code == 200:
            response_data = response.json()
            jobs = response_data.get('jobs', {})
            end_time = time.time()
            return f" ✦  {', '.join(jobs.keys())}" + f"{current_build_number}"
        else:
            logging.error(f"Failed to trigger Jenkins job. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error triggering Jenkins job: {e}")
    return None

# 新增全局變量
last_trigger_time = 0
COOLDOWN_PERIOD = 16  # 冷卻時間，單位為秒
is_syncing = False

trigger_lock = threading.Lock()
processed_messages = set()


def check_for_updates():
    global message_buffer, updated_tasks
    if not message_buffer:
        return
    channel_id = message_buffer[0]['channel']
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
            task_Name = result["properties"][Task_Notion_Name]["title"][0]["text"]["content"]
            last_edited_time = result["last_edited_time"]
            last_edited_datetime = datetime.fromisoformat(last_edited_time.replace("Z", "+00:00"))
            now = last_edited_datetime <= datetime.now()
                        
            # 获取当前时间的上一分钟
            current_time = datetime.datetime.now()
            previous_minute = current_time - datetime.timedelta(minutes=1)
            start_time = previous_minute - datetime.timedelta(minutes=5)

             # 在过去5分钟内
            if (datetime.now(last_edited_datetime.tzinfo) - last_edited_datetime < timedelta(minutes=5)) or now:
            # if (start_time <= last_edited_datetime < previous_minute:
                updated_tasks.append((task_Name, last_edited_time))  # 添加到列表中

        if updated_tasks:
            print("\r\033[K" + f"Found recent update in Notion", end="")
            for task, time in updated_tasks:
                print(f"{task}")
            return True, updated_tasks
        else:
            print("\r\033[K" + f"No recent updates found in Notion", end="")
            no_change_notified = True
            return False, [], no_change_notified
        pass
    except KeyError as e:
        print(f"Error checking for updates in Notion: {e}")
        # 设置一个错误标志，而不是直接发送消息
        return False
    except Exception as e:
        # 处理其他可能的错误
        print(f"Unexpected error: {e}")
        return False
    # 如果一切正常，返回 True 表示检查更新成功
    return True

def trigger_and_notify(channel_id):
    global no_change_notified, is_syncing, confirmation_message_sent, updated_tasks, modified_pages_count
    
    try:
        # 觸發 Jenkins 作業
        response = requests.get(api_url, auth=(username, password))
        if response.status_code == 200:
            build_info = response.json()
            build_number = build_info['lastBuild']['number'] + 1
            current_build_number = f" ` {build_number} ` "
        
        triggered_jobs = trigger_jenkins_job()
        message = f"{triggered_jobs}\n檢查中 · · ·" if triggered_jobs is not None else f"✦  TimeLinker {current_build_number}\n檢查中 · · ·"
        client.chat_postMessage(channel=channel_id, text=message)
        
        # 等待 Jenkins 作業完成
        while True:
            time.sleep(10)
            result = check_pipeline_status(jenkins_url, username, password, job_name)
            if result == 'SUCCESS':
                if modified_pages_count is not None:
                    client.chat_postMessage(channel=channel_id, text=f"# `{modified_pages_count}` 件同步完成")
                    confirmation_message_sent = True
                    no_change_notified = True
                    process_buffer()  # 添加這行
                    break
            elif result == 'No Change':
                client.chat_postMessage(channel=channel_id, text="Notion 暫無變更 🥕")
                confirmation_message_sent = True
                no_change_notified = True
                break
    
    finally:
        is_syncing = False
        return no_change_notified, confirmation_message_sent


# def trigger_and_notify(channel_id):
#     global no_change_notified, is_syncing, confirmation_message_sent
#     response = requests.get(api_url, auth=(username, password))
#     if response.status_code == 200:
#         build_info = response.json()
#         build_number = build_info['lastBuild']['number'] + 1
#         current_build_number = f" `{build_number}` "
#     triggered_jobs = trigger_jenkins_job()
#     message = f"{triggered_jobs}\n檢查中 · · ·" if triggered_jobs is not None else f"✦ TimeLinker {current_build_number}\n檢查中 · · ·"
#     client.chat_postMessage(channel=channel_id, text=message)
#     threading.Timer(BUFFER_TIME, check_and_confirm, [channel_id]).start()
#     try:
#         while True:
#             result = check_pipeline_status(jenkins_url, username, password, job_name)
#             time.sleep(20)
#             if result == 'No Change':
#                 check_for_updates()
#                 if not updated_tasks:
#                     client.chat_postMessage(channel=channel_id, text="Notion 暫無變更 🥕")
#                     no_change_notified = True
#                     confirmation_message_sent = True
#                 break
#             elif result == 'SUCCESS':
#                 check_for_updates()
#                 if updated_tasks:
#                     updates_count = len(updated_tasks)  # 计算已修改的 Notion 事件总数
#                     client.chat_postMessage(channel=channel_id, text=f" `{updates_count}`  件同步完成 ✅")
#                     confirmation_message_sent = True
#                     break
#     finally:
#         is_syncing = False
#         return no_change_notified, confirmation_message_sent

def extract_text_from_blocks(blocks):
    all_text = []
    for block in blocks:
        if block['type'] == 'context':
            for element in block['elements']:
                if element['type'] == 'mrkdwn':
                    all_text.append(element['text'])
        elif block['type'] == 'section':
            for field in block['fields']:
                all_text.append(field['text'])
    return '\n'.join(all_text)

def parse_notion_message(blocks):
    message_info = {
        'title': '',
        'start': '',
        'end': '',
        'start_end': '',
        'previous_start': '',
        'previous_end': '',
        'last_updated_time': '',
        'calendar': '',
        'on_gcal': ''
    }

    for block in blocks:
        if block['type'] == 'context' and 'elements' in block:
            for element in block['elements']:
                if element['type'] == 'mrkdwn':
                    text = element['text']
                    if 'edited in' in text:
                        message_info['title'] = text
                    elif 'Calendar' in text:
                        calendar_info = text.split('*Calendar*')[-1].split('*On GCal?*')
                        message_info['calendar'] = calendar_info[0].strip()
                        message_info['on_gcal'] = calendar_info[1].strip() if len(calendar_info) > 1 else ''
        elif block['type'] == 'section' and 'fields' in block:
            for field in block['fields']:
                text = field['text']
                if 'Start' in text and 'StartEnd' not in text:
                    if '~' in text:  # Check for strikethrough text
                        message_info['previous_start'] = text.split('~')[1]
                        message_info['start'] = text.split('→')[-1].strip()
                    else:
                        message_info['start'] = text.split('\n')[-1]
                elif 'End' in text and 'StartEnd' not in text:
                    if '~' in text:  # Check for strikethrough text
                        message_info['previous_end'] = text.split('~')[1]
                        message_info['end'] = text.split('→')[-1].strip()
                    else:
                        message_info['end'] = text.split('\n')[-1]
                elif 'StartEnd' in text:
                    message_info['start_end'] = text.split('\n')[-1]
                elif 'Last Updated Time' in text:
                    if '~' in text:  # Check for strikethrough text
                        message_info['last_updated_time'] = text.split('→')[-1].strip()
                    else:
                        message_info['last_updated_time'] = text.split('\n')[-1]

    return message_info

# 修改消息緩衝區相關變量
message_buffer = []
buffer_lock = threading.Lock()
buffer_timer = None
BUFFER_TIME = 20
previous_messages = []
other_messages = []

@slack_event_adapter.on('message')
def message(payload):
    global no_change_notified, buffer_timer, last_triggered_keyword, last_message_was_related, waiting_for_confirmation, confirmation_message_sent, last_trigger_time, is_syncing
    
    # 重置相關變量
    last_triggered_keyword = None
    last_message_was_related = False
    
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text', '').lower()  # 轉換為小寫以便不區分大小寫的匹配
    blocks = event.get('blocks', [])
    message_id = event.get('ts')
    
    # 檢查消息是否已經處理過
    if message_id in processed_messages:
        return
    
    processed_messages.add(message_id)

    # if blocks:
    #     full_text = extract_text_from_blocks(blocks)
    #     lines = full_text.split('\n')
    #     for line in lines:
    #         print(line)    
    if blocks:
        notion_info = parse_notion_message(blocks)
        
        # 处理第一个 block（标题信息）
        title_block = blocks[0]
        if title_block['type'] == 'context':
            title_text = title_block['elements'][1]['text']
            # print("Title:", title_text)

        # 处理第二个 block（变更详情）
        if len(blocks) > 1:
            details_block = blocks[1]
            if details_block['type'] == 'section':
                for field in details_block['fields']:
                    field_text = field['text']
                    # print(field['text'])

        # 处理第三个 block（额外信息）
        if len(blocks) > 2:
            extra_block = blocks[2]
            if extra_block['type'] == 'context':
                extra_text = extra_block['elements'][0]['text']
                # print("Extra info:", extra_text)
        
        if notion_info['previous_start']:
            previous_messages.append({
                'type': 'previous_start',
                'text': notion_info['previous_start']
            })

        if notion_info['previous_end']:
            previous_messages.append({
                'type': 'previous_end',
                'text': notion_info['previous_end']
            })

        if notion_info['start']:
            other_messages.append({
                'type': 'start',
                'text': notion_info['start']
            })

        if notion_info['end']:
            other_messages.append({
                'type': 'end',
                'text': notion_info['end']
            })
        
        if notion_info['start_end']:
            other_messages.append({
                'type': 'start_end',
                'text': notion_info['start_end']
            })
        
        if notion_info['last_updated_time']:
            other_messages.append({
                'type': 'last_updated_time',
                'text': notion_info['last_updated_time']
            })
        
        if previous_messages:
            Done_checking = True
        elif previous_messages is None:
            Done_checking = False
            
    # 檢查消息是否來自Notion
    if is_message_from_notion(user_id):
        with buffer_lock:
            notion_info = parse_notion_message(blocks)
            message_buffer.append({
                'channel': channel_id,
                'text': text,
                'user_id': user_id,
                'notion_info': notion_info
            })
            
            process_buffer()
                
            if Done_checking is False:
                response = requests.get(api_url, auth=(username, password))
                if response.status_code == 200:
                    build_info = response.json()
                    build_number = build_info['lastBuild']['number'] + 1
                    current_build_number = f" ` {build_number} ` "
                triggered_jobs = trigger_jenkins_job()
                message = f"{triggered_jobs}\n檢查中 · · ·" if triggered_jobs is not None else f" ✦  TimeLinker {current_build_number}  \n檢查中 · · ·"
                client.chat_postMessage(channel=channel_id, text=message)
                last_message.append(message)
                # print("Previous Start:", notion_info['previous_start'])
                # print("Previous End:", notion_info['previous_end'])
                # print("\n")
            elif Done_checking is True:
                # # client.chat_postMessage(channel=channel_id, text="確認完畢 ✅✅")
                print("Previous Start:", notion_info['previous_start'])
                print("Previous End:", notion_info['previous_end'])
                # print("\n")
                pass
            no_change_notified = False
            return previous_messages, other_messages, notion_info, message_buffer
    else:
        # 消息來自真實用戶的處理邏輯
        if is_message_from_slack_user(user_id):  # 確保消息來自用戶而非機器人
            if is_message_from_notion(user_id) or BOT_ID == user_id:
                return
            with buffer_lock:
                message_buffer.append({'channel': channel_id, 'text': text, 'user_id': user_id})
                
                if buffer_timer is None:
                    buffer_timer = threading.Timer(BUFFER_TIME, process_buffer)
                    buffer_timer.start()

            # 計算編輯距離
            distance = levenshtein(text, keyword)

            if waiting_for_confirmation:
                confirmation_message_sent = True
                waiting_for_confirmation = False
                last_message_was_related = False
                last_triggered_keyword = None
                if text in ['y', 'yes', 'yup','是']:  # 用戶確認要執行
                    current_time = time.time()
                    if current_time - last_trigger_time < COOLDOWN_PERIOD:
                        client.chat_postMessage(channel=channel_id, text=f"請稍等，{COOLDOWN_PERIOD}秒內只能觸發一次同步操作。")
                        return
                    
                    if not is_syncing:
                        with trigger_lock:
                            if not is_syncing:  # 雙重檢查
                                is_syncing = True
                                last_trigger_time = current_time
                                # client.chat_postMessage(channel=channel_id, text="⚡️ 成功觸發")
                                threading.Thread(target=trigger_and_notify, args=(channel_id,)).start()
                    else:
                        pass
                        # client.chat_postMessage(channel=channel_id, text="同步操作正在進行中，請稍後再試。")
                    
                    last_triggered_keyword = keyword
                    last_message_was_related = True
                    no_change_notified = True
                    confirmation_message_sent = True
                    waiting_for_confirmation = False
                elif text in ['n', 'no', 'nope','否']:  # 用戶確認不要執行
                    client.chat_postMessage(channel=channel_id, text="確認 CANCEL")
                    no_change_notified = True  # 重置通知標記
                    last_triggered_keyword = "當你準備好了，再讓我知道"  # 重置最後觸發的關鍵字
                    last_message_was_related = False  # 重置上一次消息是否與關鍵字相關
                    waiting_for_confirmation = False
                    confirmation_message_sent = True
                elif confirmation_message_sent is False and text not in ['y', 'yes', 'yup','是','n', 'no', 'nope','否']:  # 用戶輸入錯誤
                    client.chat_postMessage(channel=channel_id, text="當你準備好了，再讓我知道")
                    no_change_notified = True  # 重置通知標記
                    last_triggered_keyword = None  # 重置最後觸發的關鍵字
                    last_message_was_related = False
                    waiting_for_confirmation = True
                    confirmation_message_sent = False
            elif text == keyword:  # 直接處理 sync 關鍵詞
                current_time = time.time()
                if current_time - last_trigger_time < COOLDOWN_PERIOD:
                    client.chat_postMessage(channel=channel_id, text=f"Ops，`{COOLDOWN_PERIOD}`s 內只能觸發 1 次喲")
                    return
                
                if not is_syncing:
                    with trigger_lock:
                        if not is_syncing:  # 雙重檢查
                            is_syncing = True
                            last_trigger_time = current_time
                            # client.chat_postMessage(channel=channel_id, text="⚡️ 成功觸發")
                            threading.Thread(target=trigger_and_notify, args=(channel_id,)).start()
                else:
                    pass
                    # client.chat_postMessage(channel=channel_id, text="同步操作正在進行中，請稍後再試。")
                
                last_triggered_keyword = keyword
                last_message_was_related = True
                waiting_for_confirmation = False
                confirmation_message_sent = True
            elif distance <= threshold:
                last_message_was_related = True
                if last_triggered_keyword is None or last_triggered_keyword == keyword:
                    client.chat_postMessage(channel=channel_id, text=f"是要 `{keyword}` 嗎？   y / n ")
                    no_change_notified = False
                    waiting_for_confirmation = True
                    confirmation_message_sent = False
            elif not no_change_notified and last_triggered_keyword is None and not last_message_was_related and not distance <= threshold:
                if not last_message_was_related:  # 上一次消息與關鍵字相關
                    client.chat_postMessage(channel=channel_id, text=f"TIP: \n`{keyword}` = 觸發 Jenkins Pipeline")
                    last_triggered_keyword = keyword  # 更新最後觸發的關鍵字
                    last_message_was_related = False
                    no_change_notified = True  # 重置通知標記
                        
            no_change_notified = True
    return message_buffer, is_syncing

def process_buffer():
    global message_buffer, buffer_timer, modified_pages_count, updated_tasks
    
    with buffer_lock:
        if not message_buffer:
            return
    
        channel_id = message_buffer[0]['channel']
        notion_messages = [msg for msg in message_buffer if is_message_from_notion(msg['user_id'])]
        current_buffer = message_buffer.copy()
        message_buffer.clear()
        if not current_buffer:
            return

        print("\r\033[K" + f"Processing {len(current_buffer)} message from buffer", end="")


        if notion_messages:
            # 處理 Notion 消息
            for msg in notion_messages:

                # 檢查是否有包含 "Previous" 的消息
                has_previous = any(
                    'previous' in msg['notion_info'] or 'Previous' in msg['notion_info']
                    for msg in notion_messages
                )
                modified_pages_count =+ 1

                # 處理 Notion 消息
                if has_previous:
                    client.chat_postMessage(channel=channel_id, text=f"確認 `{len(modified_pages_count)}` 件完畢\n\n")

        # 清空緩衝區
        message_buffer.clear()
        buffer_timer = None

def check_and_confirm(channel_id):
    global received_previous_start, received_previous_end, buffer_timer
    with buffer_lock:
        # Copy and clear the buffer at the beginning
        current_buffer = message_buffer.copy()
        message_buffer.clear()
        if not current_buffer:
            return
        if received_previous_start or received_previous_end:
            client.chat_postMessage(channel=channel_id, text="確認完畢")
        else:
            print("Did not receive all notifications within the time limit.")

print("\n")

start_dynamic_counter_indicator()

@app.route('/')
def home():
    return "Flask server is running"

def run_flask_app():
    app.run(debug=False, use_reloader=False, port=8080)

if __name__ == '__main__':
    print("\r\033[K", end="")
    flask_thread = threading.Thread(target=run_flask_app)
    flask_thread.start()
    print("\r\033[K", end="")

    time.sleep(1)  # 等待确保Flask启动信息已经打印
    print("\r\033[K", end="")
    print("\n")  # 打印新行作为分隔

    start_dynamic_counter_indicator()

    try:
        flask_thread.join()
    except KeyboardInterrupt:
        stop_clear_and_print()
        
stop_clear_and_print()