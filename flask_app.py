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


# Get today's date
today = datetime.today()

# Calculate the first day of this month
this_month = datetime(today.year, today.month, 1)

# Format the date to match the format used in your code
this_month_str = this_month.strftime("%Y-%m-%dT%H:%M:%S.%f")

##Query notion tasks already in Gcal, don't have to be updated, and are today or in the next week
my_page = notion.databases.query( 
    **{
        "database_id": database_id,
        "filter": {
            "and": [
                {
                    "property": NeedGCalUpdate_Notion_Name, 
                    "formula":{
                        "checkbox":  {
                            "equals": False
                        }
                    }
                }, 
                {
                    "property": On_GCal_Notion_Name, 
                    "checkbox":  {
                        "equals": True
                    }
                }, 
                {
                    "property": Date_Notion_Name, 
                    "date": {
                        "on_or_after": this_month_str
                    }
                },
                # {
                #     "or": [
                #     {
                #         "property": Date_Notion_Name, 
                #         "date": {
                #             "equals": todayDate
                #         }
                #     }, 
                #     {
                #         "property": Date_Notion_Name, 
                #         "date": {
                #             "next_week": {}
                #         }
                #     }
                # ]   
                # },
                {
                    "property": Delete_Notion_Name, 
                    "checkbox":  {
                        "equals": False
                    }
                }
            ]
        },
    }
)

resultList = my_page['results']

#Comparison section: 
# We need to see what times between GCal and Notion are not the same, so we are going to convert all of the notion date/times into 
## datetime values and then compare that against the datetime value of the GCal event. If they are not the same, then we change the Notion 
### event as appropriate
notion_IDs_List = []
notion_start_datetimes = []
notion_end_datetimes = []
notion_gCal_IDs = [] #we will be comparing this against the gCal_datetimes
gCal_start_datetimes = []
gCal_end_datetimes = []
notion_gCal_CalIds = [] #going to fill this in from the select option, not the text option. 
notion_gCal_CalNames = []
notion_titles = []
gCal_CalIds = []
gCal_titles = []
events_to_update = []
events_info = []
added_events = []
modified_events = []
added_events_counter = 0
modified_events_counter = 0

for result in resultList:
    notion_IDs_List.append(result['id'])
    notion_start_datetimes.append(result['properties'][Date_Notion_Name]['date']['start'])
    notion_end_datetimes.append(result['properties'][Date_Notion_Name]['date']['end'])
    if result['properties'][GCalEventId_Notion_Name]['rich_text']:
        notion_gCal_IDs.append(result['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content'])
    else:
        pass
    if result['properties'][Task_Notion_Name]['title']:
        notion_titles.append(result['properties'][Task_Notion_Name]['title'][0]['text']['content'])
    else:
        notion_titles.append("Untitled")
    try:
        notion_gCal_CalIds.append(calendarDictionary[result['properties'][Calendar_Notion_Name]['select']['name']])
        notion_gCal_CalNames.append(result['properties'][Calendar_Notion_Name]['select']['name'])
    except: #keyerror occurs when there's nothing put into the calendar in the first place
        notion_gCal_CalIds.append(calendarDictionary[DEFAULT_CALENDAR_NAME])
        notion_gCal_CalNames.append(result['properties'][Calendar_Notion_Name]['select']['name'])


#the reason we take off the last 6 characters is so we can focus in on just the date and time instead of any extra info
for  i in range(len(notion_start_datetimes)):    
    try:
        notion_start_datetimes[i] = datetime.strptime(notion_start_datetimes[i], "%Y-%m-%d")
    except:
        try:
            notion_start_datetimes[i] = datetime.strptime(notion_start_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.000")
        except:
            notion_start_datetimes[i] = datetime.strptime(notion_start_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.%f")

for  i in range(len(notion_end_datetimes)):    
    if notion_end_datetimes[i] != None:
        try:
            notion_end_datetimes[i] = datetime.strptime(notion_end_datetimes[i], "%Y-%m-%d")
        except:
            try:
                notion_end_datetimes[i] = datetime.strptime(notion_end_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.000")
            except:
                notion_end_datetimes[i] = datetime.strptime(notion_end_datetimes[i][:-6], "%Y-%m-%dT%H:%M:%S.%f")
    else:
        notion_end_datetimes[i] = notion_start_datetimes[i] #the reason we're doing this weird ass thing is because when we put the end time into the update or make GCal event, it'll be representative of the date

##We use the gCalId from the Notion dashboard to get retrieve the start Time from the gCal event
value =''
exitVar = ''
for gCalId in notion_gCal_IDs:  
    
    for calendarID in calendarDictionary.keys(): #just check all of the calendars of interest for info about the event
        try:
            x = service.events().get(calendarId=calendarDictionary[calendarID], eventId = gCalId).execute()
        except:
            x = {'status': 'unconfirmed'}
        if x['status'] == 'confirmed':
            value = x     
            gCal_titles.append(value['summary'])
            gCal_CalIds.append(calendarID)   
        else:
            continue
        
    try:
        gCal_start_datetimes.append(datetime.strptime(value['start']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(value['start']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0)
        gCal_start_datetimes.append(x)
    try:
        gCal_end_datetimes.append(datetime.strptime(value['end']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(value['end']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0) - timedelta(days=1)
        gCal_end_datetimes.append(x)

#Now we iterate and compare the time on the Notion Dashboard and the start time of the GCal event
#If the datetimes don't match up,  then the Notion  Dashboard must be updated
new_notion_start_datetimes = ['']*len(notion_start_datetimes)
new_notion_end_datetimes = ['']*len(notion_end_datetimes)
new_notion_titles = ['']*len(notion_titles)

# Determine the length of the shorter list
loop_length = min(len(notion_start_datetimes), len(gCal_start_datetimes))

# Use loop_length to limit the range of the loop
for i in range(loop_length):
    if isinstance(notion_start_datetimes[i], datetime) and isinstance(gCal_start_datetimes[i], datetime):
        if notion_start_datetimes[i] != gCal_start_datetimes[i]:
            new_notion_start_datetimes[i] = gCal_start_datetimes[i]
            # Additional logic here
    else:
        print(f"Error: Type mismatch at index {i}.")
        # Handle the type mismatch error

    if notion_end_datetimes[i] != gCal_end_datetimes[i]:
        new_notion_end_datetimes[i] = gCal_end_datetimes[i]
        # Additional logic here

# Determine the length of the shorter list
loop_length_titles = min(len(notion_titles), len(gCal_titles))

# Use loop_length_titles to limit the range of the loop for titles comparison
for i in range(loop_length_titles):
    if notion_titles[i] != gCal_titles[i] and gCal_titles[i] != '':
        new_notion_titles[i] = gCal_titles[i]
    else:
        new_notion_titles[i] = notion_titles[i]  # If gCal_titles[i] is empty, keep the original Notion title

# Ensure that any remaining titles in notion_titles are handled if notion_titles is longer than gCal_titles
for i in range(loop_length_titles, len(notion_titles)):
    new_notion_titles[i] = notion_titles[i]  # 如果 gCal_titles[i] 是空值，則保持原始的 Notion 標題


def remove_leading_zero(time_str):
    parts = time_str.split(':')
    if len(parts) == 2:
        hour = str(int(parts[0]))  # 移除小时的前导零
        minute = parts[1]  # 分钟部分不变
        return f"{hour}:{minute}"
    return time_str

def format_date(date):
    if date is None:
        return " " * 12  # 返回固定长度的空字符串，以保持对齐
    # 格式化日期，确保日和月份始终占用两个字符位置（对于日，通过在单数前添加空格实现）
    day = date.strftime('%d').lstrip('0').rjust(2, ' ')
    month = date.strftime('%b')
    year = date.strftime('%Y')
    return f"{day} {month}, {year}"

def format_time(time):
    if time is None:
        # 可以选择不进行任何操作，或者设置一个默认值
        return ""
    # Use the provided remove_leading_zero function to format time without leading zeros
    return remove_leading_zero(time.strftime('%H:%M'))

def print_date_change(label, old_date, new_date, max_label_length):
    old_date_str = old_date.strftime('%d %b, %Y')
    new_date_str = new_date.strftime('%d %b, %Y')
    
    if old_date.hour != 0 or old_date.minute != 0:
        old_date_str += '  ' + remove_leading_zero(old_date.strftime('%H:%M'))
    
    if new_date.hour != 0 or new_date.minute != 0:
        new_date_str += '  ' + remove_leading_zero(new_date.strftime('%H:%M'))

    print(f"{label:<{max_label_length}} :" + "  " + f" {format_string(old_date_str, less_visible=True)} " + formatted_right_arrow + f" {new_date_str}")

labels = ['Title', 'Start', 'End', 'StartEnd']
max_label_length = max(len(label) for label in labels) + 2  # 考虑到空格的数量

def print_modification(notion_ID, before_title, after_title, old_start_date, new_start_date, old_end_date, new_end_date, max_label_length, notion_IDs_List):
    
    title_changed = before_title != after_title
    # Modify the condition to account for None values
    start_date_changed = old_start_date != new_start_date if new_start_date is not None else False
    end_date_changed = old_end_date != new_end_date if new_end_date is not None else False
    event_changed = title_changed or start_date_changed or end_date_changed
    
    try:
        event_index = notion_IDs_List.index(notion_ID)
    except ValueError:
        print(f"Event {notion_ID} not found in the list of Notion IDs.")
        return
    
    notion_ID = notion_IDs_List[event_index]
    
    if event_changed:
        animate_text_wave("modifyin", repeat=1)

    if title_changed:
        stop_clear_and_print()
        print(f"{'Before':<{max_label_length}} :" + "  " + f" {format_string(before_title, less_visible=True)}")
        print(f"{'After':<{max_label_length}} :" + "  " + f" {format_string(after_title, bold=True)}\n")
        start_dynamic_counter_indicator()
    else:
        stop_clear_and_print()
        print(f"{'Title':<{max_label_length}} :" + "  " + f" {format_string(notion_titles[i], bold=True)}")
        start_dynamic_counter_indicator()
            
    if start_date_changed:
        if new_start_date is not None:
            if new_start_date.hour != 0 or new_start_date.minute != 0:
                print_date_change('Start', old_start_date, new_start_date, max_label_length)
            else:
                stop_clear_and_print()
                print(f"{'Start':<{max_label_length}} :" + "   " + format_string(format_date(old_start_date), less_visible=True) + (f"  {format_time(old_start_date)}" if old_start_date.hour != 0 or old_start_date.minute != 0 else "") + '  ' + formatted_right_arrow + f" {format_date(new_start_date)}")
                start_dynamic_counter_indicator()
        else:  # Handle case when new_start_date is None
            stop_clear_and_print()
            print(f"{'Start':<{max_label_length}} :" + "   " + format_string(format_date(old_start_date), less_visible=True) + (f"  {format_time(old_start_date)}" if old_start_date.hour != 0 or old_start_date.minute != 0 else ""))
            start_dynamic_counter_indicator()
    else:
        stop_clear_and_print()
        print(f"{'Start':<{max_label_length}} :" + "   " + format_string(format_date(old_start_date), less_visible=True))
        start_dynamic_counter_indicator()

    if end_date_changed:
        if new_end_date is not None:
            if new_end_date.hour != 0 or new_end_date.minute != 0:
                print_date_change('End', old_end_date, new_end_date, max_label_length)
            else:
                stop_clear_and_print()
                print(f"{'End':<{max_label_length}} :" + "   " + format_string(format_date(old_end_date), less_visible=True) + (f"  {format_time(old_end_date)}" if old_end_date.hour != 0 or old_end_date.minute != 0 else "") + '  ' + formatted_right_arrow + f" {format_date(new_end_date)}")
                start_dynamic_counter_indicator()
        else:  # Handle case when new_end_date is None
            stop_clear_and_print()
            print(f"{'End':<{max_label_length}} :" + "   " + format_string(format_date(old_end_date), less_visible=True) + (f"  {format_time(old_end_date)}" if old_end_date.hour != 0 or old_end_date.minute != 0 else ""))
            start_dynamic_counter_indicator()
    else:
        stop_clear_and_print()
        print(f"{'End':<{max_label_length}} :" + "   " + format_string(format_date(old_end_date), less_visible=True))
        start_dynamic_counter_indicator()

    # Check if date has changed
    if start_date_changed or end_date_changed:
        # Determine the date to use for start and end (fallback to old if new is None)
        final_start_date = new_start_date if new_start_date is not None else old_start_date
        final_end_date = new_end_date if new_end_date is not None else old_end_date

        # Non-all-day event
        if (final_start_date.hour != 0 or final_start_date.minute != 0) or (final_end_date.hour != 0 or final_end_date.minute != 0):
            if final_start_date.day == final_end_date.day:
                stop_clear_and_print()
                print(f"{'StartEnd':<{max_label_length}} :" + "  " + f" {format_date(final_start_date)}  {format_time(final_start_date)}  ─  {format_time(final_end_date)}\n")
                start_dynamic_counter_indicator()
            else:
                stop_clear_and_print()
                print(f"{'StartEnd':<{max_label_length}} :" + "  " + f" {format_date(final_start_date)}  {format_time(final_start_date)}  ─  {format_date(final_end_date)}  {format_time(final_end_date)}\n")
                start_dynamic_counter_indicator()
        # All-day event or Multi-days event
        else:
            if final_start_date.year == final_end_date.year:
                if final_start_date.month == final_end_date.month:
                    if final_start_date.day == final_end_date.day:
                        stop_clear_and_print()
                        print(f"{'StartEnd':<{max_label_length}} :" + "  " + f" {format_date(final_start_date)}\n")
                        start_dynamic_counter_indicator()
                    else:
                        stop_clear_and_print()
                        # For Multi-days events within the same month
                        print(f"{'StartEnd':<{max_label_length}} :" + "  " + f" {final_start_date.strftime('%-d')} ─ {format_date(final_end_date)}\n")
                        start_dynamic_counter_indicator()
                else:
                    stop_clear_and_print()
                    # For events spanning different months in the same year
                    print(f"{'StartEnd':<{max_label_length}} :" + "  " + f" {final_start_date.strftime('%-d %B')} ── {final_end_date.strftime('%-d %B')}\n")
                    start_dynamic_counter_indicator()
            else:
                stop_clear_and_print()
                # For events spanning different years
                print(f"{'StartEnd':<{max_label_length}} :" + "  " + f" {format_date(final_start_date)} ─ {format_date(final_end_date)}\n")
                start_dynamic_counter_indicator()
    else:
        stop_clear_and_print()
        print(f"{'StartEnd':<{max_label_length}} :" + "  " + f" {format_date(old_start_date)}  ─  {format_date(new_end_date)}\n")
        start_dynamic_counter_indicator()


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

# Authenticate and retrieve the build information
response = requests.get(api_url, auth=(username, password))
if response.status_code == 200:
    build_info = response.json()
    build_number = build_info['lastBuild']['number']
    print(f'Latest build number for {job_name}: {build_number}')
else:
    print(f'Failed to retrieve build information: {response.status_code}')
                
def check_pipeline_status(jenkins_url, username, password, job_name):
    pipeline_url = f'{jenkins_url}/job/{job_name}/lastBuild/consoleText'
    response = requests.get(pipeline_url, auth=(username, password))
    
    if response.status_code == 200:
        lines = response.text.split('\n')
        status = 'Unknown'
        no_changes = False
        
        for line in lines:
            if ': 0' in line or 'Page Modified' in line:
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

result = check_pipeline_status(jenkins_url, username, password, job_name)
print("Pipeline Status:", result)


# def check_pipeline_status(jenkins_url, username, password, job_name):
#     pipeline_url = f'{jenkins_url}/job/{job_name}/lastBuild/consoleText'
#     response = requests.get(pipeline_url, auth=(username, password))
#     if response.status_code == 200:
#         build_info = response.json()
#         build_number = build_info['lastBuild']['number']
#         print(f"Pipeline status: {check_pipeline_status(jenkins_url, username, password, job_name)}")
#         print(f'Latest build number for {job_name}: {build_number}')
#         print(f"Last line status: {check_last_line_status(response.text)}")
#         return build_info, build_number
#     else:
#         print(f'Failed to retrieve build information: {response.status_code}')
    

def trigger_jenkins_job():
    start_time = time.time()
    try:
        print("Triggering Jenkins job...")
        response = requests.get(jenkins_job_url, timeout=0.05)
        if response.status_code == 200:
            response_data = response.json()
            jobs = response_data.get('jobs', {})
            end_time = time.time()
            return f"✦ {', '.join(jobs.keys())}"
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
    while True:
        result = check_pipeline_status(jenkins_url, username, password, job_name)
        time.sleep(23)
        if result == 'No Change':
            print("\n\n\n" + result + "\n\n\n")
            check_for_updates()
            if not updated_tasks:
                client.chat_postMessage(channel=channel_id, text="Notion 暫無變更 🥕")
                no_change_notified = True
        elif result == 'SUCCESS':
            print("\n\n\n" + result + "\n\n\n")
        return no_change_notified

updated_tasks = []  # 用于存储在过去5分钟内更新的任务
received_previous_start = False
received_previous_end = False
last_message_was_related = False  # 用於跟踪上一次消息是否與關鍵字相關
waiting_for_confirmation = False  # 用於標記是否正在等待用戶確認
confirmation_message_sent = False  # 用於標記是否已經發送確認消息
last_triggered_keyword = None  # 用於跟踪最後一次觸發的關鍵字
last_message = None

@slack_event_adapter.on('message')
def message(payload):
    global no_change_notified, buffer_timer, last_triggered_keyword, last_message_was_related, waiting_for_confirmation, confirmation_message_sent
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text').lower()  # 转换为小写以便不区分大小写的匹配

    # 重置 last_triggered_keyword 和 last_message_was_related 的值
    last_triggered_keyword = None
    last_message_was_related = False

    # 分類消息
    previous_messages = [msg for msg in message_buffer if "Previous" in msg['text']]
    other_messages = [msg for msg in message_buffer if "Previous" not in msg['text']]

    # 检查消息是否来自Notion
    if is_message_from_notion(user_id):
        print("Message from Notion")           
        with buffer_lock:
            message_buffer.append({'channel': channel_id, 'text': text, 'user_id': user_id})
            
            if buffer_timer is None:
                buffer_timer = threading.Timer(BUFFER_TIME, process_buffer)
                buffer_timer.start()


        if other_messages:
            message = f"{triggered_jobs}\n检查中 · · ·" if triggered_jobs else ""
            client.chat_postMessage(channel=channel_id, text=message)
            triggered_jobs = trigger_jenkins_job()
            last_message.append(message)
                
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

            # 計算編輯距離
            distance = levenshtein(text, keyword)


            if waiting_for_confirmation:
                confirmation_message_sent = True
                waiting_for_confirmation = False
                last_message_was_related = False
                last_triggered_keyword = None
                if text in ['y', 'yes', 'yup','是']:  # 用戶確認要執行
                    client.chat_postMessage(channel=channel_id, text="⚡️ 成功觸發")
                    trigger_and_notify(channel_id)
                    last_triggered_keyword = keyword
                    last_message_was_related = True
                    no_change_notified = True
                    confirmation_message_sent = True
                    return no_change_notified
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
                    pass

            # 判斷是否與關鍵字相關
            if not no_change_notified and text == keyword:  # 直接處理 sync 關鍵詞
                client.chat_postMessage(channel=channel_id, text="⚡️ 成功觸發")
                trigger_and_notify(channel_id)
                check_for_updates()
                last_triggered_keyword = keyword
                last_message_was_related = True
            elif distance <= threshold:
                last_message_was_related = True
                if last_triggered_keyword is None or last_triggered_keyword == keyword:
                    client.chat_postMessage(channel=channel_id, text=f"是要 `{keyword}` 嗎？ (yes／no)")
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

def check_for_updates():
    global message_buffer
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
            
            # 检查最后编辑时间是否在过去5分钟内
            if datetime.now(last_edited_datetime.tzinfo) - last_edited_datetime < timedelta(minutes=5):
                updated_tasks.append((task_Name, last_edited_time))  # 添加到列表中

        if updated_tasks:
            for task, time in updated_tasks:
                print(f"Found recent update in Notion :")
                print(f"{task}   {time}\n")
            return True, updated_tasks
        else:
            print("\r\033[K" + f"No recent updates found in Notion", end="")
            client.chat_postMessage(channel=channel_id, text="Notion 暫無變更 🥕")
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

def process_buffer():
    global message_buffer, buffer_timer, updated_tasks, no_change_notified, received_previous_start, received_previous_end, last_triggered_keyword, last_message_was_related, waiting_for_confirmation, confirmation_message_sent, last_message
    if not message_buffer:
        return
    channel_id = message_buffer[0]['channel']
    with buffer_lock:
        # Copy and clear the buffer at the beginning
        current_buffer = message_buffer.copy()
        message_buffer.clear()
        if not current_buffer:
            return

        print("\r\033[K" + f"Processing {len(current_buffer)} message from buffer", end="")
        
        # 分类消息
        previous_start_messages = [msg for msg in current_buffer if "Previous Start" in msg['text']]
        previous_end_messages = [msg for msg in current_buffer if "Previous End" in msg['text']]

        # Start a timer on receiving the first "Previous" message
        if previous_start_messages or previous_end_messages:
            received_previous_start = True if previous_start_messages else False
            received_previous_end = True if previous_end_messages else False
            print(f"\r\033[Kgot previous : {previous_start_messages} {previous_end_messages}")
            threading.Timer(BUFFER_TIME, check_and_confirm, [channel_id]).start()

        if not received_previous_start and not received_previous_end:
            if not no_change_notified:
                if check_for_updates():
                    if updated_tasks:
                        # 如果有更新，发送相应的消息
                        updates_count = len(updated_tasks)  # 计算已修改的 Notion 事件总数
                        client.chat_postMessage(channel=channel_id, text=f"{updates_count}  件同步完成 ✅\n\n")
                        pass
                    else:
                        client.chat_postMessage(channel=channel_id, text="Notion 暫無變更 🥕")
                        no_change_notified = True
                        return Response(), 200, no_change_notified
                    pass
        
        buffer_timer = None
    return response, 200

for i in range(len(notion_gCal_IDs)):
    notion_ID = notion_IDs_List[i]  # Define notion_ID at the start of the loop iteration
    title_changed = notion_titles[i] != new_notion_titles[i]
    new_start_date = new_notion_start_datetimes[i] or None
    new_end_date = new_notion_end_datetimes[i] or None
    start_date_changed = new_start_date and notion_start_datetimes[i] != new_start_date
    end_date_changed = new_end_date and notion_end_datetimes[i] != new_end_date
    event_changed = title_changed or start_date_changed or end_date_changed

   # 如果事件没有改变，则跳过后续代码
    if not event_changed:
        continue  # Skip the rest of the code for this iteration if no changes are detected
    
    if event_changed:
        event_info = {
            'title': new_notion_titles[i],
            'start_time': new_start_date,
            'end_time': new_end_date,
            'start_time_formatted': new_start_date.strftime('%d %b, %Y %H:%M') if new_start_date else None,
            'end_time_formatted': new_end_date.strftime('%d %b, %Y %H:%M') if new_end_date else None
        }

        if event_info['is_added']:
            added_events.append(event_info)
        elif event_info['is_modified']:
            modified_events.append(event_info)

        events_to_update.append(notion_gCal_IDs[i])
        added_events_counter += 1
        modified_events_counter += 1
        print_modification(notion_IDs_List[i], notion_titles[i], new_notion_titles[i], notion_start_datetimes[i], new_start_date, notion_end_datetimes[i], new_end_date, max_label_length, notion_IDs_List)


def check_and_confirm(channel_id):
    if received_previous_start and received_previous_end:
        client.chat_postMessage(channel=channel_id, text="確認完畢 ✅✅")
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