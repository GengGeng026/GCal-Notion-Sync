from configparser import NoOptionError
from dis import Positions
import os
import re
from dotenv import load_dotenv
import httpx
from notion_client import APIResponseError, Client
from notion_client.errors import RequestTimeoutError, HTTPResponseError
import pickle
import requests
import pytz
from pytz import timezone as pytz_timezone
from dateutil.parser import parse
from dateutil import parser
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone, time
import time as tm
import time
import sys
import threading
from threading import Lock
from textblob import TextBlob
from fuzzywuzzy import process
import Levenshtein as lev
from collections import defaultdict
from collections import Counter
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from gcsa.google_calendar import GoogleCalendar
from googleapiclient.errors import HttpError
import googleapiclient.errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from concurrent.futures import ThreadPoolExecutor, as_completed, CancelledError,TimeoutError
from queue import Queue
import logging
from wcwidth import wcswidth
import traceback
import pprint
import shutil
import functools

###########################################################################
##### Print Tool Section. Will be used throughoout entire script. 
###########################################################################

# 在脚本开始处或合适的位置定义
immediate_stop_event = threading.Event()

# 模擬終端寬度，如果在非交互式環境（如 Jenkins）中運行
if 'JENKINS_HOME' in os.environ:
    terminal_width = 80  # 或者使用任何你認為合適的預設值
else:
    terminal_width = os.get_terminal_size().columns
print('\n' + '-' * terminal_width + '\n')

# Define ANSI escape codes as constants
BOLD = "\033[1m"
LESS_VISIBLE = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"
TEAL = "\033[34m"
HIGHLIGHT_GREEN = "\033[36m"
LIGHT_GRAY = "\033[37m"  # Light gray color as an example of a lighter color to simulate transparency
RED = "\033[38;5;196m"
BLUE_BG = "\033[48;5;4m"
RESET = "\033[0m"

# Create a dictionary to map color names to ANSI escape codes
COLORS = {
    "C1": TEAL,
    "C2": HIGHLIGHT_GREEN,
    "C3": RED,
    "C4": BLUE_BG,
    # Add more colors as needed
}

def skip_in_jenkins(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        if 'JENKINS_HOME' in os.environ:
            return ''  # Return an empty string instead of None
        return func(*args, **kwargs)
    return wrapper

def format_string(text, color=None, bold=False, italic=False, less_visible=False, underline=False, light_color=False):
    text = str(text)  # 確保text為字符串
    color_code = COLORS.get(color, '')  # 使用get來避免KeyError，如果color不在COLORS中，則返回空字符串
    return f"{BOLD if bold else ''}{ITALIC if italic else ''}{LESS_VISIBLE if less_visible else ''}{UNDERLINE if underline else ''}{LIGHT_GRAY if light_color else ''}{color_code}{text}{RESET}" if not 'JENKINS_HOME' in os.environ else text

# Use the function to format text
formatted_dot = format_string('.', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else '.'
formatted_BOLD_italic = format_string('{}', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else '{}'
formatted_right_arrow = format_string(' ▸ ', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else ' ▸ '
formatted_indicator = format_string('{}', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else '{}'
formatted_successful = format_string('Successful', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Successful'
formatted_added = format_string('Added', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Added'
formatted_updated = format_string('Updated', 'C2', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'Updated'
formatted_failed = format_string('Failed', 'C3', bold=True) if not 'JENKINS_HOME' in os.environ else 'Failed'
formatted_deleted = format_string('Deleted', 'C3', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'Deleted'
formatted_title = format_string('Title', bold=True) if not 'JENKINS_HOME' in os.environ else 'Title'
formatted_start = format_string('Start', bold=True) if not 'JENKINS_HOME' in os.environ else 'Start'
formatted_end = format_string('End', bold=True) if not 'JENKINS_HOME' in os.environ else 'End'
formatted_startend = format_string('StartEnd', bold=True) if not 'JENKINS_HOME' in os.environ else 'StartEnd'
formatted_condition_met = format_string('Condition Met', bold=True) if not 'JENKINS_HOME' in os.environ else 'Condition Met'
formatted_no = format_string('No', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'No'
formatted_has_time = format_string('has time', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'has time'
formatted_is_changed = format_string('have been Changed', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'have been Changed'
formatted_count = format_string('{}', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else '{}'
formatted_plus = format_string('+', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else '+'
formatted_slash = format_string('/', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else '/'
formatted_colon = format_string(':', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else ':'
formatted_semicolon = format_string(';', 'C1', bold=True) if not 'JENKINS_HOME' in os.environ else ';'
formatted_reset_default_setting = format_string('RESET accordingly Default Setting', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'RESET accordingly Default Setting'
formatted_default_time = format_string('Default Time Range', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Default Time Range'
formatted_time_range = format_string('Time Range', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Time Range'
formatted_explicitly_set = format_string('Explicitly Set', bold=True) if not 'JENKINS_HOME' in os.environ else 'Explicitly Set'
formatted_explicitly_set_0000 = format_string('Explicitly set to 00:00', bold=True) if not 'JENKINS_HOME' in os.environ else 'Explicitly set to 00:00'
formatted_alldayevent = format_string('All-Day-Event', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'All-Day-Event'
formatted_alternate_alldayevent = format_string('Alternate All-Day-Event', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Alternate All-Day-Event'
formatted_have_time = format_string('have Time', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'have Time'
formatted_have_single_date = format_string('have Single-Date', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'have Single-Date'
formatted_no_time = format_string('No Time', 'C1', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'No Time'
formatted_is_filled_accordingly = format_string('is Filled accordingly', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'is Filled accordingly'
formatted_is_filled_single_date = format_string('is Filled Single-Date', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'is Filled Single-Date'
formatted_overwritten = format_string('Overwritten', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Overwritten'
formatted_done = format_string('Done', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Done'
formatted_Printing = format_string('Printing', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Printing'
formatted_error = format_string('error', 'C3', bold=True) if not 'JENKINS_HOME' in os.environ else 'error'
formatted_plain_none = format_string('None', italic=True, less_visible=True) if not 'JENKINS_HOME' in os.environ else 'None'
formatted_plain_previous = format_string('Previous', italic=True, less_visible=True) if not 'JENKINS_HOME' in os.environ else 'Previous'
formatted_AFTER = format_string('AFTER', 'C1', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'AFTER'
formatted_none = format_string('None', 'C1', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'None'
formatted_nothing = format_string('Nothing', bold=True) if not 'JENKINS_HOME' in os.environ else 'Nothing'
formatted_all_none = format_string('All None', 'C1', bold=True, italic=True) if not 'JENKINS_HOME' in os.environ else 'All None'
formatted_modified = format_string('Modified', 'C2', bold=True) if not 'JENKINS_HOME' in os.environ else 'Modified'


# Global variable to track progress
global_progress = 0
stop_event = threading.Event()
thread = None

def get_console_width():
    # 返回一个固定的宽度值，这里我们使用150，它足够大以覆盖大多数控制台窗口的宽度
    return 150
    # return shutil.get_terminal_size().columns

@skip_in_jenkins
def clear_line():
    print("\r\033[K", end="")

@skip_in_jenkins
def dynamic_counter_indicator(stop_event, message, timeout=20):
    start_time = time.time()
    dot_counter = 0
    total_dots = 0
    console_width = get_console_width()
    while not stop_event.is_set() and not immediate_stop_event.is_set():  # 增加对 immediate_stop_event 的检查
        current_time = time.time()
        elapsed_time = current_time - start_time
        if elapsed_time > timeout:
            print("\r" + " " * (len(progress_and_message) + total_dots) + "\r", end="")
            break
        current_progress_str = f"{global_progress}%"
        progress_and_message = f"{BOLD}{COLORS['C2']}{current_progress_str} " + format_gradient(f"{message}", bold_indices=(0, len(current_progress_str)), less_visible_indices=(len(current_progress_str) + 1, len(current_progress_str) + 1 + len(message)))
        if dot_counter == 4:
            print("\r" + " " * (len(progress_and_message) + total_dots + 5) + "\r", end="", flush=True)
            dot_counter = 0
            total_dots = 0
        else:
            tm.sleep(0.002)
            if len(progress_and_message) + total_dots < console_width:
                print(f"\r{progress_and_message}" + "." * total_dots, end="", flush=True)
            else:
                print(f"\r{progress_and_message}", end="", flush=True)
                total_dots = 0
            dot_counter += 1
            total_dots += 1
        sys.stdout.flush()
    clear_line()

@skip_in_jenkins
def stop_clear_and_print():
    global stop_event, thread
    if thread is not None:
        stop_event.set()
        thread.join()
    sys.stdout.write("\033[2K")  # 清除整行
    sys.stdout.flush()  # 确保清除命令被立即执行

@skip_in_jenkins
def start_dynamic_counter_indicator():
    global stop_event, thread
    stop_event = threading.Event()
    thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event, "."))
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

@skip_in_jenkins
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

@skip_in_jenkins
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

clear_line()

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_API_KEY") #the secret_something from Notion Integration

# Create an instance of the Notion client
notion = Client(auth=NOTION_TOKEN)

database_id = os.getenv("NOTION_DATABASE_ID") #get the mess of numbers before the "?" on your dashboard URL (no need to split into dashes)

urlRoot = os.getenv("NOTION_DATABASE_URL") #open up a task and then copy the URL root up to the "p="

#GCal Set Up Part
DEFAULT_EVENT_LENGTH = 60 #This is how many minutes the default event length is. Feel free to change it as you please
timezone = 'Asia/Kuala_Lumpur' #Choose your respective time zone: http://www.timezoneconverter.com/cgi-bin/zonehelp.tzc
local_tz = pytz.timezone(timezone)

def notion_time():
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S+08:00") #Change the last 5 characters to be representative of your timezone
     #^^ has to be adjusted for when daylight savings is different if your area observes it
    
def DateTimeIntoNotionFormat(dateTimeValue):
    return dateTimeValue.strftime("%Y-%m-%dT%H:%M:%S+08:00")  #Change the last 5 characters to be representative of your timezone
     #^^ has to be adjusted for when daylight savings is different if your area observes it


def googleQuery():
    # Get today's date
    today = datetime.now()

    # Calculate the first day of the current month
    first_day_of_month = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Return the date and time in ISO 8601 format with timezone offset
    return first_day_of_month.strftime("%Y-%m-%dT%H:%M:%S")+"+08:00" # Adjust the timezone offset as needed


DEFAULT_EVENT_START = 8 #8 would be 8 am. 16 would be 4 pm. Only whole numbers 

AllDayEventOption = 0 #0 if you want dates on your Notion dashboard to be treated as an all-day event
#^^ 1 if you want dates on your Notion dashboard to be created at whatever hour you defined in the DEFAULT_EVENT_START variable



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
    'Ideal': os.getenv("GOOGLE_IDEAL_CALENDAR_ID")
}

## doesn't delete the Notion task (yet), I'm waiting for the Python API to be updated to allow deleting tasks
DELETE_OPTION = 0 
#set at 0 if you want the delete column being checked off to mean that the gCal event and the Notion Event will be checked off. 
#set at 1 if you want nothing deleted


##### DATABASE SPECIFIC EDITS

# There needs to be a few properties on the Notion Database for this to work. Replace the values of each variable with the string of what the variable is called on your Notion dashboard
# The Last Edited Time column is a property of the notion pages themselves, you just have to make it a column
# The NeedGCalUpdate column is a formula column that works as such "if(prop("Last Edited Time") > prop("Last Updated Time"), true, false)"
#Please refer to the Template if you are confused: https://www.notion.so/akarri/2583098dfd32472ab6ca1ff2a8b2866d?v=3a1adf60f15748f08ed925a2eca88421

# Constants
Task_Notion_Name = 'Task Name' 
Date_Notion_Name = 'StartEnd'
Start_Notion_Name = 'Start'
End_Notion_Name = 'End'
Frequency_Notion_Name = 'Frequency'
First_Day_of_Week_Notion_Name = 'First Day of Week'
Recur_Until_Notion_Name = 'Recur Until'
Recur_Count_Notion_Name = 'Recur Count'
Recur_Interval_Notion_Name = 'Recur Interval'
Days_Notion_Name = 'Days'
Days_of_Month_Notion_Name = 'Days of Month'
Days_of_Year_Notion_Name = 'Days of Year'
Week_Numbers_of_Year_Notion_Name = 'Week Numbers of Year'
Months_Notion_Name = 'Months'
ExtraInfo_Notion_Name = 'Notes'
On_GCal_Notion_Name = 'On GCal?'
to_Auto_Sync_Notion_Name = 'to Auto-Sync'
AutoRename_Notion_Name = 'AutoRename'
NeedGCalUpdate_Notion_Name = 'NeedGCalUpdate'
GCalEventId_Notion_Name = 'GCal Event Id'
LastUpdatedTime_Notion_Name  = 'Last Updated Time'
Calendar_Notion_Name = 'Calendar'
Current_Calendar_Id_Notion_Name = 'Current Calendar Id'
Delete_Notion_Name = 'Delete from GCal?'

#######################################################################################
###               No additional user editing beyond this point is needed            ###
#######################################################################################

start_dynamic_counter_indicator()

# Set up logging
# 在正式部署前，將日誌級別設置為 INFO 或更高，這樣可以減少細節的輸出
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Create a lock
token_lock = threading.Lock()

# Constants
CREDENTIALS_LOCATION = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_LOCATION")
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CALENDAR_CLI_SECRET_FILE")
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']
DEFAULT_CALENDAR_ID = 'primary'  # Replace with your Calendar ID

# 從環境變數中讀取 Google Calendar 憑證路徑
credentials_path = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_LOCATION")

if credentials_path:
    with open(credentials_path, 'rb') as token:
        creds = pickle.load(token)

    # 初始化 Google Calendar 客戶端
    from googleapiclient.discovery import build
    gc = build('calendar', 'v3', credentials=creds)
else:
    print("憑證路徑不存在")

def event_exists(service, calendar_id, event_id):
    try:
        service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        return True
    except HttpError as e:
        if e.resp.status == 404:
            return False
        else:
            raise

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
        print(f"\n{formatted_successful} Authentication / Refresh Token\n")
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
    clear_line()
    credentials = refresh_token()
    service = build("calendar", "v3", credentials=credentials)
    calendar = obtain_calendar(service)
finally:
    stop_clear_and_print()
    animate_text_wave_with_progress(text="Loading", new_text="initialized", target_percentage=3, current_progress=global_progress, sleep_time=0.005, percentage_first=True)
    start_dynamic_counter_indicator()


###########################################################################
##### The Methods that we will use in this scipt are below
###########################################################################

######################################################################
#METHOD TO FORMAT DATE AND TIME

def parse_date(date_str):
    return parse(date_str)


# Define a function to format the date and time
def format_date_time(start, end):
    if start.year != end.year:
        return start.strftime('%b %-d, %Y %-H:%M'), end.strftime('%b %-d, %Y %-H:%M')
    elif start.month != end.month:
        return start.strftime('%-m/%d'), end.strftime('%-m/%d ｜ %-H:%M')
    elif start.day != end.day:
        return start.strftime('%b %-d, %-H:%M'), end.strftime('%b %-d, %-H:%M')
    else:
        return start.strftime('%b %-d, %-H:%M'), end.strftime('%-H:%M')


######################################################################
#METHOD TO MAKE A CALENDAR EVENT DESCRIPTION

#This method can be edited as wanted. Whatever is returned from this method will be in the GCal event description 
#Whatever you change up, be sure to return a string 

def makeEventDescription(Frequency, info):
    if Frequency == '' and info == '':
        return ''
    elif info == "":
        return Frequency
    elif Frequency == '':
        return info
    else:
        return f'Frequency: {Frequency} \n{info}'


######################################################################
#METHOD TO MAKE A TASK'S URL
#To make a url for the notion task, we have to take the id of the task and take away the hyphens from the string

def makeTaskURL(ending, urlRoot):
    # urlId = ending[0:8] + ending[9:13] + ending[14:18] + ending[19:23] + ending[24:]  #<--- super inefficient way to do things lol
    return urlRoot + ending


######################################################################
#METHOD TO MAKE A CALENDAR EVENT

def makeCalEvent(eventName, eventDescription, eventStartTime, sourceURL, eventEndTime, calId, all_day=False, frequency=None, interval=None, byDay=None, byMonth=None, byMonthDay=None, byYearDay=None, byWeekNum=None, until=None, count=None):
    # 確保在處理之前 eventEndTime 不是 None
    if eventEndTime is None:
        eventEndTime = eventStartTime

    # 生成 recurrence 相關規則
    recurrence_rules = []

    # 檢查頻率是否有效
    if frequency:
        if frequency.upper() not in ['DAILY', 'WEEKLY', 'MONTHLY', 'YEARLY']:
            raise ValueError(f"Invalid frequency: {frequency}")

        rule = f"RRULE:FREQ={frequency.upper()}"
        if interval:
            rule += f";INTERVAL={interval}"
        if byDay:
            rule += f";BYDAY={byDay}"
        if byMonth:
            rule += f";BYMONTH={byMonth}"
        if byMonthDay:
            rule += f";BYMONTHDAY={byMonthDay}"
        if byYearDay:
            rule += f";BYYEARDAY={byYearDay}"
        if byWeekNum:
            rule += f";BYWEEKNO={byWeekNum}"
        if until:
            if isinstance(until, datetime):
                # 將until的時間設置為該天的23:59:59
                until = until.replace(hour=23, minute=59, second=59, microsecond=0).astimezone(eventStartTime.tzinfo)
                rule += f";UNTIL={until.strftime('%Y%m%dT%H%M%SZ')}"
            else:
                print(f"警告: 'until' 參數不是有效的 datetime 對象: {until}")
        if count:
            if until:
                raise ValueError("Cannot specify both COUNT and UNTIL in the recurrence rule.")
            rule += f";COUNT={count}"

        recurrence_rules.append(rule)

    # 處理全天事件
    if all_day or (eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime == eventStartTime):
        event = {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'date': eventStartTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'end': {
                'date': eventEndTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            },
            'recurrence': recurrence_rules if recurrence_rules else None  # 設置 recurrence
        }
    else:
        # 非全天事件的處理邏輯
        event = {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'dateTime': eventStartTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': eventEndTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            },
            'recurrence': recurrence_rules if recurrence_rules else None  # 設置 recurrence
        }

    try:
        x = service.events().insert(calendarId=calId, body=event).execute()
        return x['id']
    except Exception as e:
        print(f"Failed to create calendar event: {e}")


######################################################################
#METHOD TO UPDATE A CALENDAR EVENT

def parse_recurrence(recurrence_list): 
    if not recurrence_list:
        return None
    
    for rule in recurrence_list:
        if rule.startswith('RRULE:'):
            params = rule[len('RRULE:'):].split(';')
            recurrence_info = {}

            # 解析每个参数
            for param in params:
                if '=' in param:
                    key, value = param.split('=', 1)  # 只分割一次
                    recurrence_info[key] = value

            # 将频率信息单独提取出来，并添加到 recurrence_info
            frequency = recurrence_info.get('FREQ', None)
            interval = recurrence_info.get('INTERVAL', '1')
            until = recurrence_info.get('UNTIL', None)
            count = recurrence_info.get('COUNT', None)
            byday = recurrence_info.get('BYDAY', None)

            # 返回一个包含所有解析结果的字典
            return {
                'frequency': frequency,
                'interval': interval,
                'until': until,
                'count': count,
                'byday': byday
            }

    return None

def validate_rrule(rrule_str):
    until_value = None
    try:
        if 'UNTIL' in rrule_str:
            match = re.search(r"UNTIL=(\d{8}T\d{6}Z)", rrule_str)
            if match:
                until_value = match.group(1)
                if not re.match(r"\d{8}T\d{6}Z", until_value):
                    raise ValueError(f"Invalid UNTIL format: {until_value}")
            else:
                raise ValueError("UNTIL is missing or has an invalid format.")

        
        # if until_value is not None:
        #     print(f"Checking UNTIL value: {until_value}")
        # else:
        #     print("UNTIL value is not defined.")

        return True
    except Exception as e:
        print(f"RRULE validation failed: {e}")
        return False

def format_until_date(until: str) -> str:
    try:
        dt = datetime.fromisoformat(until[:-1] + '+00:00') if until.endswith('Z') else datetime.fromisoformat(until)
        return dt.strftime('%Y%m%dT%H%M%SZ')
    except ValueError as e:
        raise ValueError(f"Invalid UNTIL format: {until}") from e

def extract_recurrence_info(service, calendar_id, event, el):
    recurring_event_id = event.get('recurringEventId')
    if 'recurrence' in event and event['recurrence']:
        # print("Recurrence found:", event['recurrence'])
        return parse_recurrence(event['recurrence'])

    Frequency_name = ""
    interval = '1'
    until = None
    count = None
    byday = None

    if el is not None and isinstance(el, dict) and 'properties' in el:
        properties = el['properties']
        
        if Frequency_Notion_Name in properties and properties[Frequency_Notion_Name]:
            select_field = properties[Frequency_Notion_Name].get('select')
            if select_field and isinstance(select_field, dict):
                Frequency_name = select_field.get('name', "")
        
        interval = properties.get(Recur_Interval_Notion_Name, {}).get('number', '1')

        # 假設 until_property 是從 event 中提取的某個屬性
        until_property = event.get('recurrence', {}).get('until', None)  # 根據實際結構獲取 until_property

        # 確保 until_property 不是 None
        if until_property is None:
            logging.warning("until_property is None, returning default value.")
            return {
                "until": None,
                # 可以根據需要返回其他的默認值
            }

        # 繼續處理 until_property
        until = until_property.get('date', {}).get('start', None) if until_property else None
        
        count = properties.get(Recur_Count_Notion_Name, {}).get('number', None)
        byday = properties.get(Days_Notion_Name, {}).get('multi_select', [])

        # 轉換 until 的格式
        until = format_until_date(until) if until else None

        if Frequency_name:
            rrule = f"RRULE:FREQ={Frequency_name.upper()};INTERVAL={interval}"
            if until:
                rrule += f";UNTIL={until}"
            if count:
                rrule += f";COUNT={count}"
            if byday:
                days = ','.join([day['name'] for day in byday])
                rrule += f";BYDAY={days}"

            if validate_rrule(rrule):
                return [rrule]
            else:
                print("Invalid RRULE")
                return None
            
    if 'recurringEventId' in event:
        try:
            original_event = service.events().get(calendarId=calendar_id, eventId=recurring_event_id).execute()
            return parse_recurrence(original_event.get('recurrence', [])), recurring_event_id
        except googleapiclient.errors.HttpError as e:
            logging.error(f"Failed to fetch original event: {e}")

    return None, None

# Define recurrence rules only if recurrence_info is provided
def generate_recurrence_rules(frequency, interval, byDay, byMonth, byMonthDay, byYearDay, byWeekNum, until, count):
    recurrence_rules = []
    print(f"generating recurrence rules ...")
    rule = f"RRULE:FREQ={frequency.upper()}"
    
    if interval and interval != '1':
        rule += f";INTERVAL={interval}"
    if byMonth:
        rule += f";BYMONTH={byMonth}"
    if byMonthDay:
        rule += f";BYMONTHDAY={byMonthDay}"
    if until and count is None:
        # 將字符串格式的日期轉換為日期物件
        try:
            until_date = datetime.fromisoformat(until.replace("Z", "+00:00"))
            rule += f";UNTIL={until_date.strftime('%Y%m%dT%H%M%SZ')}"
        except ValueError as e:
            print(f"Invalid `until` date format: {e}")
            return None
    elif count:
        rule += f";COUNT={count}"
    if byDay:
        rule += f";BYDAY={byDay}"  # `byDay` 應該已經是逗號分隔的格式，如 `WE,FR,SA`
        
    recurrence_rules.append(rule)
    print(f"recurrence_rules: {recurrence_rules}")
    return recurrence_rules

def is_rule_identical(existing_rules, new_rules):
    # 忽略順序進行集合比較
    existing_rules_set = set([rule.strip() for rule in existing_rules if rule.startswith('RRULE')])
    new_rules_set = set([rule.strip() for rule in new_rules if rule.startswith('RRULE')])
    return existing_rules_set == new_rules_set

number = 0
new_titles = []
got_new_update = False

def upDateCalEvent(eventName, autoRename,eventDescription, eventStartTime, sourceURL, eventId, eventEndTime, currentCalId, CalId, thread, recurrence_info=None):

    # 設置初始值
    x = None
    recurrence_rules = None
    got_new_update = False
    updated_event_id = None

    stop_clear_and_print()
    animate_text_wave("updating", repeat=1)

    # print(f"Initial values - eventName: {eventName}, eventId: {eventId}, currentCalId: {currentCalId}, CalId: {CalId}")

    # 檢查已存在的事件
    existing_events = service.events().list(calendarId=CalId, q=eventName).execute().get('items', [])
    existing_event_ids = [event['id'] for event in existing_events]
    # print(f"Existing events in target calendar: {existing_event_ids}")
    
    # 檢查當前事件是否已存在於目標日曆
    if eventId in existing_event_ids:
        # print(f"Event ID {eventId} already exists in calendar {CalId}. Skipping update.")
        return None

    try:
        try:
            if currentCalId == CalId:
                # print(f"Updating event {eventId} directly in the same calendar {CalId}.")
                x = service.events().update(calendarId=CalId, eventId=eventId, body=event).execute()
                if x:
                    # print("Event updated successfully.")
                    got_new_update = True
                else:
                    print("Failed to update event.")
            else:
                # print(f"Moving event {eventId} from calendar {currentCalId} to {CalId}.\n")
                x = service.events().move(calendarId=currentCalId, eventId=eventId, destination=CalId).execute()
                if x:
                    # print("Event moved successfully.")
                    
                    # 反转calendarDictionary字典並獲取日曆名稱
                    # print(f"calendarDictionary: {calendarDictionary}")
                    id_to_calendar_name = {v: k for k, v in calendarDictionary.items()}
                    currentCalName = id_to_calendar_name.get(currentCalId, "Unknown Calendar")
                    CalName = id_to_calendar_name.get(CalId, "Unknown Calendar")

                    # 打印事件信息
                    print(format_string(eventName, bold=True))  # 打印事件标题
                    
                    formattedCurrentCalName = format_string(currentCalName, less_visible=True)
                    formattedCalName = format_string(CalName, italic=True, light_color=True)
                    print(f'{formattedCurrentCalName} {formatted_right_arrow} {formattedCalName}\n')
                    got_new_update = True

                else:
                    print("Failed to move event.")
            
            # 驗證是否成功移動/更新
            if x:
                moved_event_id = x.get('id', eventId)
                event = service.events().get(calendarId=CalId, eventId=moved_event_id).execute()
                if moved_event_id in existing_event_ids:
                    # print(f"Moved event ID {moved_event_id} already exists in calendar {CalId}. Skipping further update.")
                    return None
                else:
                    # print(f"\nMoved event to {CalId}, attempting to update with new info.")
                    x = service.events().update(calendarId=CalId, eventId=moved_event_id, body=event).execute()
                    if x:
                        # print("Update after move successful.")
                        got_new_update = True
                    else:
                        print("Update after move failed.")
            else:
                print("No response after move attempt.")
                
            # print(f"got_new_update status: {got_new_update}")
            return got_new_update

        except googleapiclient.errors.HttpError as e:
            print(f"Google API HttpError: {e}")
            if e.resp.status == 400 and 'cannotChangeOrganizer' in str(e):
                print("Organizer cannot be changed, creating a new event instead.")
                # 嘗試創建新的事件
                try:
                    new_event = {
                        'summary': eventName,
                        'description': eventDescription,
                        'start': eventStartTime,
                        'end': eventEndTime,
                        'recurrence': recurrence_info,
                        'source': event.get('source', {}),
                    }
                    new_event_response = service.events().insert(calendarId=CalId, body=new_event).execute()
                    new_event_id = new_event_response.get('id')
                    print(f"New event created with ID: {new_event_id}. Attempting to delete old event.")
                    
                    # 刪除舊事件
                    try:
                        service.events().delete(calendarId=currentCalId, eventId=eventId).execute()
                        print("Old event deleted successfully.")
                    except googleapiclient.errors.HttpError as delete_error:
                        print(f"Failed to delete old event: {delete_error}")
                        
                except Exception as ex:
                    print(f"Error creating or deleting event: {ex}")
                    raise

        # Generate recurrence rules only if valid recurrence_info is provided
        recurrence_rules = None

        # 提取重複信息
        recurrence_info = extract_recurrence_info(service, CalId, event, el)
        if recurrence_info:
            recurrence_rules = generate_recurrence_rules(
                recurrence_info.get('Frequency_Notion_Name'),
                recurrence_info.get('Recur_Interval_Notion_Name', '1'),
                recurrence_info.get('Days_Notion_Name'),
                recurrence_info.get('Months_Notion_Name'),
                recurrence_info.get('Days_of_Month_Notion_Name'),
                recurrence_info.get('Days_of_Year_Notion_Name'),
                recurrence_info.get('Week_Numbers_of_Year_Notion_Name'),
                recurrence_info.get('Recur_Until_Notion_Name'),
                recurrence_info.get('Recur_Count_Notion_Name')
            )
            
        print(f"生成的重複規則: {recurrence_rules}")

        # 獲取當前事件狀態
        current_event = service.events().get(calendarId=CalId, eventId=eventId).execute()
        current_recurrence = current_event.get('recurrence', [])
        print(f"current event recurrence: {current_event.get('recurrence')}")

        # Check if the event should be renamed, handle update or move
        print(f"AutoRename_Notion_Name: {AutoRenames}")
        if AutoRenames:
            eventName = generate_unique_title(CurrentCalList, task_name, new_titles, number, resultList, current_page=el)
            # print(f"生成的新標題: {eventName}")
        
        if recurrence_rules is not None and not is_rule_identical(current_recurrence, recurrence_rules):
            if eventStartTime == eventEndTime:
                event_body = {
                    'summary': eventName if eventName else current_event.get('summary', 'Unnamed Event'),
                    'description': eventDescription if eventDescription else current_event.get('description', ''),
                    'recurrence': recurrence_rules,
                    'start': {
                        'date': eventStartTime.date().isoformat(),
                    },
                    'end': {
                        'date': eventEndTime.date().isoformat(),
                    }
                }
                try:
                    x = service.events().update(calendarId=CalId, eventId=eventId, body=event_body).execute()
                    got_new_update = True
                except HttpError as e:
                    print(e)
                    got_new_update = False
            else:
                got_new_update = False
        else:
            got_new_update = False    


        # 判斷事件類型
        if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime.hour == 0 and eventEndTime.minute == 0 and eventStartTime != eventEndTime:            
            if AllDayEventOption == 1:                    
                eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(hours=DEFAULT_EVENT_START) 
                eventEndTime = eventStartTime + timedelta(minutes=DEFAULT_EVENT_LENGTH)
                event = create_event_body(eventName, eventDescription, eventStartTime, eventEndTime, sourceURL, False, recurrence_rules=recurrence_rules)
            else:
                eventEndTime += timedelta(days=1)
                event = create_event_body(eventName, eventDescription, eventStartTime, eventEndTime, sourceURL, True, recurrence_rules=recurrence_rules)

        elif eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime.hour == 0 and eventEndTime.minute == 0 and eventStartTime != eventEndTime:  # 多天事件
            eventEndTime += timedelta(days=1)  
            event = create_event_body(eventName, eventDescription, eventStartTime, eventEndTime, sourceURL, True, recurrence_rules=recurrence_rules)

        else:  # 处理具体的开始时间和结束时间
            # 具體時間事件
            event_body = {
                'summary': eventName if eventName else current_event.get('summary', 'Unnamed Event'),
                'description': eventDescription if eventDescription else current_event.get('description', ''),
                'recurrence': recurrence_rules,
                'start': {
                    'dateTime': eventStartTime.isoformat(),  # 使用 dateTime 格式
                    'timeZone': timezone,
                },
                'end': {
                    'dateTime': eventEndTime.isoformat(),  # 使用 dateTime 格式
                    'timeZone': timezone,
                }
            }
            event = create_event_body(eventName, eventDescription, eventStartTime, eventEndTime, sourceURL, False, recurrence_rules=recurrence_rules)


        # Build event with recurrence rules if applicable
        event = create_event_body(eventName, eventDescription, eventStartTime, eventEndTime, sourceURL, all_day=True, recurrence_rules=recurrence_rules)

        # print(f"Final got_new_update status: {got_new_update}")
    except Exception as ex:
        print(f"Error updating event after move: {ex}")
    finally:
        # 最後檢查 x
        if x and 'id' in x:
            return got_new_update
        else:
            print("Event ID was not found in the response.")
            return got_new_update  # 或者根據需要返回一個其他值


def create_event_body(eventName, eventDescription, startTime, endTime, sourceURL, isAllDay, recurrence_rules):
    if isAllDay:
        return {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'date': startTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'end': {
                'date': endTime.strftime("%Y-%m-%d"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            },
            'recurrence': recurrence_rules
        }
    else:
        return {
            'summary': eventName,
            'description': eventDescription,
            'start': {
                'dateTime': startTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'end': {
                'dateTime': endTime.strftime("%Y-%m-%dT%H:%M:%S"),
                'timeZone': timezone,
            },
            'source': {
                'title': 'Notion Link',
                'url': sourceURL,
            },
            'recurrence': recurrence_rules
        }

def handle_http_error(e, currentCalId, eventId, event, recurrence_info):
    logging.error(f"Google API HttpError: {e}")

    if e.resp.status == 400 and 'cannotChangeOrganizer' in str(e):
        try:
            logging.warning("Organizer cannot be changed, creating a new event.")
            new_event = {
                'summary': event['summary'],
                'description': event['description'],
                'start': event['start'],
                'end': event['end'],
                'recurrence': recurrence_info if recurrence_info else [],
                'source': event.get('source', {}),
            }
            new_event_response = service.events().insert(calendarId=calId, body=new_event).execute()
            logging.info(f"New event created with ID: {new_event_response.get('id')}.")

            service.events().delete(calendarId=currentCalId, eventId=eventId).execute()
        except Exception as ex:
            logging.error(f"Error creating or deleting event: {ex}")
            raise
    else:
        logging.error(f"Unhandled Google API error: {e}")
        raise

###########################################################################
##### Part 1: Take Notion Events not on GCal and move them over to GCal
###########################################################################

start_dynamic_counter_indicator()

## Note that we are only querying for events that are today or in the next week so the code can be efficient. 
## If you just want all Notion events to be on GCal, then you'll have to edit the query so it is only checking the 'On GCal?' property
# Get today's date
today = datetime.today()

# Calculate the first day of this month
this_month = datetime(today.year, today.month, 1)

# Format the date to match the format used in your code
this_month_str = this_month.strftime("%Y-%m-%dT%H:%M:%S.%f")

max_retries = 5
retry_delay = 2  # seconds

for attempt in range(max_retries):
    try:
        my_page = notion.databases.query(
            database_id=database_id,
            filter={
                "and": [
                    {
                        "property": On_GCal_Notion_Name,
                        "checkbox": {
                            "equals": False
                        }
                    },
                    {
                        "property": Date_Notion_Name,
                        "date": {
                            "on_or_after": this_month_str
                        }
                    },
                    {
                        "property": Delete_Notion_Name,
                        "checkbox": {
                            "equals": False
                        }
                    }
                ]
            }
        )
        resultList = my_page['results']
        break  # 成功後退出循環
    except APIResponseError as e:
        print(f"Error: {e}. Retrying in {retry_delay} seconds...")
        time.sleep(retry_delay)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        break  # 遇到其他錯誤則退出

animate_text_wave_with_progress(text="Loading", new_text="Checked 1", target_percentage=5, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

TaskNames = []
start_Dates = []
end_Times = []
First_Days = []
Frequencies = []
Recur_Intervals = []
Recur_Days = []
Recur_Months = []
byMonthDays = []
byYearDays = []
byWeekNumbers = []
Recur_Untils = []
Recur_Counts = []
ExtraInfo = []
URL_list = []
calEventIdList = []
CalendarList = []

no_new_updated = True
no_new_added = True
No_pages_modified = True

# 定义一些正确的拼写选项和保護詞
correct_terms = ["Untitled", "Physiotherapy", "General Physiotherapy", "Soka", "RUKA", "UMMC", "Sync"]
protected_terms = ["Daily", "Weekly", "Monthly", "Yearly", "JC", "Appt.", "【Appt.】", "【Appt】", "Untitled", "JOKER", "Folie À Deux", "Movie", "Yeux", "Police", "RE"]

# 判断是否为专业术语或保護詞
def is_special_term(term):
    # 如果 term 是保護詞則直接返回 True
    if term in protected_terms:
        return True
    # 如果 term 與專業詞列表中的某詞匹配，則返回 True
    for correct_term in correct_terms:
        if correct_term.lower().startswith(term.lower()):
            return True
    # 正則表達式匹配多單詞保護詞
    for protected in protected_terms:
        if re.search(r'\b' + re.escape(protected) + r'\b', term, re.IGNORECASE):
            return True
    return False

# 判定是否拼寫接近正確
def is_spelling_close_enough(term, correct_terms):
    best_match = process.extractOne(term, correct_terms)
    return best_match and best_match[1] > 60

# 判定是否為嚴重錯誤（使用 Levenshtein 距離）
def is_severe_typo(term, correct_terms, threshold=3):
    best_match = process.extractOne(term, correct_terms)
    if best_match:
        distance = lev.distance(term.lower(), best_match[0].lower())
        return distance > threshold  # 阈值越高，判定越寬鬆
    return False

def contains_chinese(s):
    """檢查字串是否包含中文字符"""
    return bool(re.search(r'[\u4e00-\u9fff]', s))

def correct_spelling(term):
    # 優先判定保護詞和特殊字符
    if is_special_term(term):
        return term
    if contains_chinese(term):
        return term

    # 檢查詞長度，若小於3個字母則直接返回
    if len(term) < 3:
        return term
    
    # 檢查是否全大寫，若是則直接返回
    if term.isupper():
        return term

    # 判定拼寫接近正確，則不做糾正
    if is_spelling_close_enough(term, correct_terms):
        return term
    
    # 嚴重錯誤才執行糾正
    if is_severe_typo(term, correct_terms):
        blob = TextBlob(term)
        corrected_term = str(blob.correct())
        
        # 確保糾正後的結果符合專業詞語
        best_match = process.extractOne(corrected_term, correct_terms)
        if best_match and best_match[1] > 90:  # 增加相似度閾值
            return best_match[0]
        return corrected_term
    
    return term


def get_existing_titles_from_gcal(service, calendar_id, time_min):
    # 确保 time_min 是 UTC 时间，并且格式正确
    if isinstance(time_min, str):
        time_min = datetime.strptime(time_min, "%Y-%m-%dT%H:%M:%S.%f")
    
    # 将时间转换为 UTC
    time_min = time_min.astimezone(pytz.UTC)
    
    # 格式化时间为 RFC3339 格式
    time_min_str = time_min.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

    try:
        events_result = service.events().list(
            calendarId=calendar_id, 
            timeMin=time_min_str, 
            singleEvents=True, 
            orderBy='startTime',
            maxResults=2500  # 限制结果数量，避免请求过大
        ).execute()
        events = events_result.get('items', [])
        return [event['summary'] for event in events if 'summary' in event]
    
    except HttpError as error:
        print(f"An error occurred: {error}")
        return []

# 獲取過去 2 個月的事件
n_months_ago = datetime.now(pytz.UTC) - timedelta(days=61)
existing_titles = {}
for calendar_id in calendarDictionary.values():
    existing_titles[calendar_id] = get_existing_titles_from_gcal(service, calendar_id, n_months_ago)

def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def extract_number_and_position(title):
    matches = re.finditer(r'\b(\d+)(st|nd|rd|th)\b', title)
    for match in matches:
        return int(match.group(1)), match.start(), match.end()
    return None, None, None

def contains_latin_or_numbers_or_chinese(s):
    """檢查字串是否包含任何羅馬字母、數字或中文字符"""
    return bool(re.search(r'[A-Za-z0-9\u4e00-\u9fff]', s))

notion_data = {}

def generate_unique_title(existing_titles, base_title, new_titles, number, resultList, current_page):
    new_title = base_title  # Initialize new_title with a default value
    # 將空標題處理為 Untitled
    if not base_title.strip():
        base_title = "Untitled"
    all_titles = existing_titles + new_titles

    # 确保 number 在有效范围内
    if number < 0 or number >= len(resultList):
        # print(f"Invalid number: {number}. Adjusting to {len(resultList) - 1}.")
        number = max(0, len(resultList) - 1)  # 调整 number

    # 获取当前页面的 AutoRename 值
    auto_rename_notion_name_value = None
    if 'properties' in current_page:
        if 'AutoRename' in current_page['properties']:
            if 'formula' in current_page['properties']['AutoRename']:
                if 'string' in current_page['properties']['AutoRename']['formula']:
                    auto_rename_notion_name_value = current_page['properties']['AutoRename']['formula']['string']
                    # print(f"auto_rename_notion_name_value: {auto_rename_notion_name_value}")

    # 如果成功获取了 AutoRename 值
    if auto_rename_notion_name_value and contains_latin_or_numbers_or_chinese(auto_rename_notion_name_value):
        AutoRename_Notion_Name = auto_rename_notion_name_value
    else:
        AutoRename_Notion_Name = None

    # 确保不会错误覆盖原始标题
    if AutoRename_Notion_Name:
        # 使用正则表达式检查是否与其他字符同时存在
        if re.search(r'\bUntitled\b', AutoRename_Notion_Name) and len(AutoRename_Notion_Name.split()) > 1:
            # 如果 "Untitled" 与其他单词同时存在，替换为 ""
            AutoRename_Notion_Name = re.sub(r'\bUntitled\b', '', AutoRename_Notion_Name).strip()
            new_title = AutoRename_Notion_Name
        else:
            new_title = base_title

        # print(f"New title after processing AutoRename: {new_title}")
        # print(f"Existing titles: {existing_titles}")
        if new_title in existing_titles:
            # print(f"New title '{new_title}' already exists in existing titles. Returning base title.")
            return base_title  # 或使用其他逻辑处理重复

        # 检查 base_title 是否已存在于 existing_titles 中
        if base_title in all_titles:
            # print(f"Base title '{base_title}' already exists. Keeping original title.")
            return base_title  # 如果原始标题存在，直接返回
        
        # print(f"Returning AutoRename title: {AutoRename_Notion_Name}")
        return AutoRename_Notion_Name  # 返回提取的标题

    # print("AutoRename_Notion_Name is None. Proceeding with base title logic...")
    # 此处可以添加更多代码逻辑来处理 base_title 的生成

    # 去除空白字符并转换为小写
    base_title_clean = base_title.strip().lower()

    # 对基础标题进行拼写校正，先 TextBlob 后 fuzzywuzzy
    base_title = correct_spelling(base_title)

    # 特殊处理 "Untitled" 标题
    if base_title == "Untitled":
        untitled_exists = any(title.strip() == "Untitled" for title in all_titles)
        untitled_numbers = [0]  # 用于存储 "Untitled" 后的数字，0 表示仅 "Untitled"

        for title in all_titles:
            if title.startswith("Untitled"):
                try:
                    # 尝试提取序号，忽略无序号的 "Untitled"
                    num = int(title.split(" ")[-1])
                    untitled_numbers.append(num)
                except ValueError:
                    continue

        if untitled_exists:
            next_number = 2  # 如果存在 "Untitled"，从 "Untitled 2" 开始
            while next_number in untitled_numbers:
                next_number += 1
            return f"{base_title} {next_number}"
        else:
            return "Untitled"  # 如果不存在 "Untitled"，直接返回

    # Function to check if a title is relevant to the base_title
    def is_relevant_title(title, base):
        return base.lower() in title.lower()

    # Filter relevant titles
    relevant_titles = [title for title in all_titles if is_relevant_title(title, base_title)]

    if not relevant_titles:
        return base_title  # If no relevant titles found, return the original base_title

    # Pattern to match ordinal numbers and surrounding text
    pattern = re.compile(r'(.*?)(\d+)(st|nd|rd|th)\s*(.*?)((?:\s*F\/up|\s*Follow[\s-]up)?)', re.IGNORECASE)

    matching_titles = []
    numbers = []

    for title in relevant_titles:
        match = pattern.search(title)
        if match:
            prefix, num, _, suffix, followup = match.groups()
            numbers.append(int(num))
            matching_titles.append((prefix.strip(), suffix.strip(), followup.strip()))

    if not matching_titles:
        return base_title  # If no matching structure found in relevant titles

    # Determine the next number
    next_number = max(numbers) + 1 if numbers else 1

    # Find the most common prefix and suffix combination
    common_parts = Counter(matching_titles).most_common(1)[0][0]

    # Construct the new title
    new_title = f"{common_parts[0].strip()} {ordinal(next_number)} {common_parts[1].strip()}"
    if common_parts[2]:  # If there's a F/up or Follow-up
        new_title += f"{common_parts[2].strip()}"

    # 处理 "visit" 类型的标题
    if base_title.lower().startswith("visit"):
        visit_pattern = re.compile(r'(\d+)(st|nd|rd|th)\s*(visit\s*\w*)', re.IGNORECASE)
        numbers = []
        full_visit_titles = []

        for title in all_titles:
            match = visit_pattern.search(title)
            if match:
                num = int(match.group(1))
                numbers.append(num)
                full_visit_titles.append(match.group(3))

        if numbers:
            next_number = max(numbers) + 1
        else:
            next_number = 1

        # 使用最常见的完整 "visit" 标题
        if full_visit_titles:
            most_common_visit = max(set(full_visit_titles), key=full_visit_titles.count)
        else:
            most_common_visit = "visit"

        return f"{ordinal(next_number)} {most_common_visit}"

    # 确保 "JC" 标题保持 "visit"
    if base_title.lower() == "jc":
        visit_pattern = re.compile(r'(\d+)(st|nd|rd|th)\s*(visit\s*\w*)', re.IGNORECASE)
        visit_titles = [title for title in all_titles if visit_pattern.search(title)]

        if visit_titles:
            numbers = [int(visit_pattern.search(title).group(1)) for title in visit_titles]
            next_number = max(numbers) + 1 if numbers else 1
            return f"{ordinal(next_number)} visit {base_title}"

    # 保留原有逻辑处理其他带序数词的标题
    # 处理其他带基础标题的情况
    for title in all_titles:
        if base_title in title:
            number, start_pos, end_pos = extract_number_and_position(title)
            if number is not None:
                numbers.append(number)

    if not numbers:
        next_number = 1
    else:
        next_number = max(numbers) + 1

    return new_title.strip()

animate_text_wave_with_progress(text="Loading", new_text="Checked 1", target_percentage=6, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

# 初始化计数器
untitled_counter = 1

# 初始化计数器
untitled_counter = 1

def make_aware(dt, timezone):
    """將 naive datetime 轉換為指定時區的 aware datetime"""
    if dt.tzinfo is None:
        return timezone.localize(dt)  # 將 naive datetime 加上時區
    return dt.astimezone(timezone)  # 將 aware datetime 轉換為指定時區

def process_date(date_str, local_tz=None):
    if not date_str:
        return None
    if isinstance(date_str, datetime):
        return make_aware(date_str, local_tz) if local_tz else date_str  # 如果是 datetime 對象，轉換為 aware
    try:
        parsed_date = parser.parse(date_str)
        return make_aware(parsed_date, local_tz) if local_tz else parsed_date
    except Exception as e:
        print(f"無法解析日期 {date_str}: {e}")
        return None

def auto_set_recur_days(start_date, until_date=None):
    """根据开始日期和结束日期范围返回所有对应的星期几"""
    # print(f"start_date: {start_date}, until_date: {until_date}")

    # 确保 start_date 是 aware datetime
    if start_date.tzinfo is None:
        raise ValueError("start_date 必须是 aware datetime")

    # 如果 until_date 为 None，返回 start_date 的星期
    if until_date is None:
        day_of_week = start_date.strftime('%A').upper()  # 获取对应的星期几
        return [day_of_week[:2]]  # 例如 'MO'，只返回 start_date 的星期

    if until_date.tzinfo is None:
        raise ValueError("until_date 必须是 aware datetime")

    days = []
    current_date = start_date
    while current_date <= until_date:
        day_of_week = current_date.strftime('%A').upper()
        days.append(day_of_week[:2])  # 例如 'SA', 'SU'
        current_date += timedelta(days=1)
    return days


# 如果 multi_select 沒有值，則使用自動生成的 days_list
local_tz = pytz.timezone(timezone)

Recur_Days = []

if len(resultList) > 0:
    for i, el in enumerate(resultList):
        # 檢查標題列表是否為空
        if el['properties'][Task_Notion_Name].get('title') and el['properties'][Task_Notion_Name]['title'][0]['text']['content']:
            TaskNames.append(el['properties'][Task_Notion_Name]['title'][0]['text']['content'])
        else:
            # 生成唯一的標題
            while True:
                new_title = f"Untitled {untitled_counter}"
                if new_title not in TaskNames:
                    TaskNames.append(new_title)
                    untitled_counter += 1
                    break
                untitled_counter += 1

        # 解析開始和結束日期
        start_date_str = el['properties'][Date_Notion_Name]['date']['start']
        end_date_str = el['properties'][Date_Notion_Name]['date']['end'] if el['properties'][Date_Notion_Name]['date']['end'] else start_date_str

        local_tz = pytz.timezone(timezone)

        # 在這裡使用 process_date 函數
        start_date_dt = process_date(start_date_str, local_tz)
        end_date_dt = process_date(end_date_str, local_tz)


        # 檢查日期對象的類型
        if not isinstance(start_date_dt, datetime):
            # print(f"警告: 開始日期 '{start_date_str}' 轉換為 datetime 失敗")
            continue

        if not isinstance(end_date_dt, datetime):
            # print(f"警告: 結束日期 '{end_date_str}' 轉換為 datetime 失敗")
            end_date_dt = start_date_dt + timedelta(hours=1)  # 設置默認結束日期

        is_all_day_event = len(start_date_str) <= 10 and len(end_date_str) <= 10
        if is_all_day_event:
            # 確保使用 datetime 對象
            if isinstance(start_date_dt, datetime) and isinstance(end_date_dt, datetime):
                notion_start_date_str = start_date_dt.strftime("%Y-%m-%d")
                notion_end_date_str = end_date_dt.strftime("%Y-%m-%d")
            else:
                print(f"錯誤: 開始或結束日期不是有效的 datetime 對象。")
                continue

            # 對於 Google Calendar，結束日期需要加一天
            gcal_end_date_dt = end_date_dt + timedelta(days=1)
            gcal_end_date_str = gcal_end_date_dt.strftime("%Y-%m-%d")

            if notion_start_date_str == notion_end_date_str:
                my_page = notion.pages.update(
                    **{
                        "page_id": el['id'], 
                        "properties": {
                            Date_Notion_Name: {
                                "date":{
                                    'start': notion_start_date_str,
                                    'end': None,
                                }
                            },
                        },
                    },
                )
            else:
                my_page = notion.pages.update(
                    **{
                        "page_id": el['id'], 
                        "properties": {
                            Date_Notion_Name: {
                                "date":{
                                    'start': notion_start_date_str,
                                    'end': notion_end_date_str,
                                }
                            },
                        },
                    },
                )
        else:
            # 非全天事件保持不變
            notion_start_date_str = start_date_str
            notion_end_date_str = end_date_str
            gcal_end_date_str = end_date_str
        
        # 更新start_Dates和end_Times列表
        start_Dates.append(notion_start_date_str)
        end_Times.append(notion_end_date_str)

        # 如果 start_Dates 有日期和時間但沒有對應的 end_Times，則跳過當前迭代
        if 'T' in start_Dates[i] and start_Dates[i] == end_Times[i]:
            continue
        
        # 處理其他屬性...
        try:
            First_Days.append(el['properties'][First_Day_of_Week_Notion_Name]['select']['name'])
        except:
            First_Days.append("")
        
        try:
            Frequencies.append(el['properties'][Frequency_Notion_Name]['select']['name'])
        except:
            Frequencies.append("")
        
        try:
            Recur_Intervals.append(el['properties'][Recur_Interval_Notion_Name]['number'])
        except:
            Recur_Intervals.append("")

        try:
            Recur_Counts.append(el['properties'][Recur_Count_Notion_Name]['number'])
        except:
            Recur_Counts.append("")
            
        if 'date' in el['properties'][Recur_Until_Notion_Name] and el['properties'][Recur_Until_Notion_Name]['date']:
            recur_until = el['properties'][Recur_Until_Notion_Name]['date']['start']
            recur_until_dt = process_date(recur_until, local_tz)  # 添加 timezone

            # 檢查是否為單日事件，且時間為開始時間
            if recur_until_dt and recur_until_dt.time() == datetime.min.time():  
                recur_until_dt = recur_until_dt.replace(hour=23, minute=59, second=59)  # 調整為當天的最後一刻

                # 轉換為當地時區的時間
                local_recur_until_dt = recur_until_dt.astimezone(local_tz)

                pageId = el['id']
                notion.pages.update(
                    **{
                        "page_id": pageId, 
                        "properties": {
                            Recur_Until_Notion_Name: {
                                "date":{
                                    'start': local_recur_until_dt.strftime("%Y-%m-%d %H:%M:%S%z"),
                                    'end': None,
                                }
                            }
                        },
                    },
                )

                Recur_Untils.append(local_recur_until_dt.strftime("%Y-%m-%d %H:%M:%S"))  # 存儲調整後的日期
            else:
                Recur_Untils.append(recur_until_dt)
        else:

            # 在调用之前检查 recur_until_dt 是否定义
            if 'recur_until_dt' not in locals():
                recur_until_dt = None  # 或者设置为其他默认值，例如 datetime.now()


            # 調用 auto_set_recur_days 並檢查返回值
            days_list = auto_set_recur_days(start_date_dt, recur_until_dt)
            # print(f"Returned days_list from auto_set_recur_days: {days_list}")

            # 更新 Notion 中的 Days_Notion_Name 属性
            notion_days = [{"name": day} for day in days_list]
            page_id = el['id']
            notion.pages.update(
                **{
                    "page_id": page_id,
                    "properties": {
                        Days_Notion_Name: {
                            "multi_select": notion_days
                        }
                    },
                },
            )

            # 将生成的 days_list 加入 Recur_Days
            if days_list:
                Recur_Days.append(days_list)
            else:
                Recur_Days.append([])  # 确保结构一致，即使 days_list 为空
                
            Recur_Untils.append("")
                    
        
        
        # 檢查 Days_Notion_Name 的 multi_select 是否有值，並確保鍵存在
        if 'multi_select' in el['properties'][Days_Notion_Name] and el['properties'][Days_Notion_Name]['multi_select']:
            # 如果 multi_select 有值，則提取選項並更新 Recur_Days
            selected_days = el['properties'][Days_Notion_Name]['multi_select']
            Recur_Days.append([day['name'] for day in selected_days])
            # print(f"Recur_Days after appending selected days: {Recur_Days}")
        else:
            start_date_dt = make_aware(start_date_dt, local_tz)
            if not end_date_dt:
                end_date_dt = start_date_dt + timedelta(hours=1)  # 預設結束日期為開始日期的下一小時
            else:
                end_date_dt = make_aware(end_date_dt, local_tz)  # 確保結束日期是 aware
            
            # print(f"Before auto_set_recur_days: start_date_dt = {start_date_dt}, recur_until_dt = {recur_until_dt}")

            # 在调用之前检查 recur_until_dt 是否定义
            if 'recur_until_dt' not in locals():
                recur_until_dt = None  # 或者设置为其他默认值，例如 datetime.now()

            # 調用 auto_set_recur_days 並檢查返回值
            days_list = auto_set_recur_days(start_date_dt, recur_until_dt)
            # print(f"Returned days_list from auto_set_recur_days: {days_list}")
            
            # 更新 Notion 中的 Days_Notion_Name 屬性
            notion_days = [{"name": day} for day in days_list]
            page_id = el['id']
            notion.pages.update(
                **{
                    "page_id": page_id,
                    "properties": {
                        Days_Notion_Name: {
                            "multi_select": notion_days
                        }
                    },
                },
            )
            
            # 將生成的 days_list 加入 Recur_Days
            if days_list:
                Recur_Days.append(days_list)
            else:
                Recur_Days.append([])  # 確保結構一致，即使 days_list 為空
            # print(f"Updated Recur_Days: {Recur_Days}")
        
        try:
            Recur_Months.append(el['properties'][Months_Notion_Name]['multi_select'][0]['name'])
        except:
            Recur_Months.append("")
        
        try:
            byMonthDays.append(el['properties'][Days_of_Month_Notion_Name]['number'])
        except:
            byMonthDays.append("")
        
        try:
            byYearDays.append(el['properties'][Days_of_Year_Notion_Name]['number'])
        except:
            byYearDays.append("")
        
        try:
            byWeekNumbers.append(el['properties'][Week_Numbers_of_Year_Notion_Name]['number'])
        except:
            byWeekNumbers.append("")
        
        try: 
            ExtraInfo.append(el['properties'][ExtraInfo_Notion_Name]['rich_text'][0]['text']['content'])
        except:
            ExtraInfo.append("")

        URL_list.append(makeTaskURL(el['id'], urlRoot))
        
        try:
            CalendarList.append(calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']])
        except:
            CalendarList.append(calendarDictionary[DEFAULT_CALENDAR_NAME])

        pageId = el['id']
        notion.pages.update(
            **{
                "page_id": pageId, 
                "properties": {
                    On_GCal_Notion_Name: {
                        "checkbox": True 
                    },
                    LastUpdatedTime_Notion_Name: {
                        "date":{
                            'start': notion_time(),
                            'end': None,
                        }
                    },
                },
            },
        )

        # 創建日曆事件
        calendar_id = CalendarList[i]
        unique_title = generate_unique_title(existing_titles[calendar_id], TaskNames[i], [], 1, resultList, current_page=el)
        TaskNames[i] = unique_title
        existing_titles[calendar_id].append(unique_title)

        # 用於確保 Recur_Until 時間部分正確的方法
        def adjust_until_date(until_date):
            if not until_date:
                return None
            if until_date.time() == datetime.min.time():  # 如果時間是 00:00，則設置為 23:59:59
                return until_date.replace(hour=23, minute=59, second=59)
            return until_date  # 若已包含時間，則直接返回

        if i < len(Recur_Untils) and Recur_Untils[i]:
            # 在呼叫 makeCalEvent 前進行調整
            until_adjusted = adjust_until_date(process_date(Recur_Untils[i]))
        else:
            until_adjusted = None

        if i < len(Recur_Days):
            byDay = ",".join(Recur_Days[i])  # 生成用逗號分隔的字符串
        else:
            # print(f"警告: Recur_Days 列表長度不足，當前索引: {i}")
            byDay = ""
        
        if i < len(TaskNames) and i < len(Recur_Days):
            calEventId = makeCalEvent(TaskNames[i], 
                                    makeEventDescription(Frequencies[i], ExtraInfo[i]), 
                                    start_date_dt, 
                                    URL_list[i], 
                                    gcal_end_date_dt if is_all_day_event else end_date_dt, 
                                    CalendarList[i], 
                                    all_day=is_all_day_event, 
                                    frequency=Frequencies[i], 
                                    interval=Recur_Intervals[i], 
                                    byDay=byDay,  # 使用格式化後的 Recur_Days
                                    byMonth=Recur_Months[i], 
                                    byMonthDay=byMonthDays[i], 
                                    byYearDay=byYearDays[i], 
                                    byWeekNum=byWeekNumbers[i], 
                                    until=until_adjusted,  # 確保這裡是 datetime 對象
                                    count=Recur_Counts[i])

        if calEventId:
            calEventIdList.append(calEventId)
            # 更新 Notion 頁面
            notion.pages.update(
                **{
                    "page_id": pageId,
                    "properties": {
                        Task_Notion_Name: {"title": [{"text": {"content": unique_title}}]},
                        GCalEventId_Notion_Name: {"rich_text": [{"text": {"content": calEventId}}]},
                        Current_Calendar_Id_Notion_Name: {"rich_text": [{"text": {"content": CalendarList[i]}}]}
                    },
                }
            )

    # 在使用 calEventIdList 之前檢查其長度
    if calEventIdList:
        for i, pageId in enumerate(resultList):
            if i < len(calEventIdList):
                if CalendarList[i] == calendarDictionary[DEFAULT_CALENDAR_NAME]:
                    notion.pages.update(
                        **{
                            "page_id": pageId['id'], 
                            "properties": {
                                GCalEventId_Notion_Name: {
                                    "rich_text": [{
                                        'text': {
                                            'content': calEventIdList[i]
                                        }
                                    }]
                                },
                                Current_Calendar_Id_Notion_Name: {
                                    "rich_text": [{
                                        'text': {
                                            'content': CalendarList[i]
                                        }
                                    }]
                                },
                                Calendar_Notion_Name:  { 
                                    'select': {
                                        "name": DEFAULT_CALENDAR_NAME
                                    },
                                },
                            },
                        },
                    )
                else:
                    notion.pages.update(
                        **{
                            "page_id": pageId['id'], 
                            "properties": {
                                GCalEventId_Notion_Name: {
                                    "rich_text": [{
                                        'text': {
                                            'content': calEventIdList[i]
                                        }
                                    }]
                                },
                                Current_Calendar_Id_Notion_Name: {
                                    "rich_text": [{
                                        'text': {
                                            'content': CalendarList[i]
                                        }
                                    }]
                                }
                            },
                        },
                    )
    else:
        print("警告: 沒有成功創建任何日曆事件")

animate_text_wave_with_progress(text="Loading", new_text="Checked 1", target_percentage=7, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

processedEvents = set()  # Initialize the set outside the loop
totalEventsProcessed = 0  # 在循环开始之前初始化计数器
event_added_yet_modified = False
total_added_count_to_print = False

for i, eventId in enumerate(calEventIdList, start=1):
    
    if eventId in processedEvents:
        continue

    if i-1 < len(CalendarList):
        stop_clear_and_print()
        animate_text_wave("addin", repeat=1)
        start_dynamic_counter_indicator()
        calendarId = CalendarList[i-1]
        try:
            event = service.events().get(calendarId=calendarId, eventId=eventId).execute()
        except googleapiclient.errors.HttpError as e:
            if e.resp.status == 404:
                print(f"Error: Event with ID '{eventId}' not found in calendar '{calendarId}'.")
            else:
                print(f"Unexpected error occurred: {e}")
        eventName = event['summary']
        processedEvents.add(eventId)

        # 在这里增加 totalEventsProcessed 的值
        totalEventsProcessed += 1
    else:
        pass

    eventStartTime = datetime.strptime(event['start']['dateTime'], "%Y-%m-%dT%H:%M:%S%z") if 'dateTime' in event['start'] else datetime.strptime(event['start']['date'], "%Y-%m-%d")
    eventEndTime = datetime.strptime(event['end']['dateTime'], "%Y-%m-%dT%H:%M:%S%z") if 'dateTime' in event['end'] else datetime.strptime(event['end']['date'], "%Y-%m-%d")

    start_time_formatted = eventStartTime.strftime("%d %b, %Y %H:%M")
    end_time_formatted = eventEndTime.strftime("%H:%M")
    
    # 使用 totalEventsProcessed 而不是 processedEvents 来进行比较
    if totalEventsProcessed > 0:
        stop_clear_and_print()
        if i == 1:
            print("\r\033[K", end="\n") # 在第一个 {i} 打印之前添加一个新行
            
        print(f"{format_string(f'{i}', bold=True, italic=True)}" + formatted_dot + "  " + f"{format_string(eventName, bold=True)}")
        stop_clear_and_print()


if totalEventsProcessed > 0:
    stop_clear_and_print()
    print(f"\nTotal {formatted_added} New N.Event : {format_string(totalEventsProcessed, "C2", bold=True)}\n\n\n")
    start_dynamic_counter_indicator()
    no_new_updated = False
    No_pages_modified = False
    

animate_text_wave_with_progress(text="Loading", new_text="Checked 1", target_percentage=10, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

###########################################################################
##### Part 2: Updating GCal Events that Need To Be Updated (Changed on Notion but need to be changed on GCal)
###########################################################################

#Just gotta put a fail-safe in here in case people deleted the Calendar Variable
#this queries items in the next week where the Calendar select thing is empty

# Get today's date
today = datetime.today()

# Calculate the first day of this month
this_month = datetime(today.year, today.month, 1)

# Format the date to match the format used in your code
this_month_str = this_month.strftime("%Y-%m-%dT%H:%M:%S.%f")

my_page = notion.databases.query(  
    **{
        "database_id": database_id, 
        "filter": {
            "and": [
                {
                    "property": Calendar_Notion_Name, 
                    "select":  {
                        "is_empty": True
                    }
                }, 
                {
                    "property": Date_Notion_Name, 
                    "date": {
                        "on_or_after": this_month_str
                    }
                },
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

for i, el in enumerate(resultList):
    pageId = el['id']
    # 檢查 `title` 屬性是否存在並且列表不為空
    task_property = el['properties'].get(Task_Notion_Name, {}).get('title', [])
    if task_property and 'text' in task_property[0]:
        task_name = task_property[0]['text']['content']

        # 更新 Notion 頁面
        my_page = notion.pages.update( 
            **{
                "page_id": pageId, 
                "properties": {
                    Calendar_Notion_Name:  { 
                        'select': {
                            "name": DEFAULT_CALENDAR_NAME
                        },
                    },
                    LastUpdatedTime_Notion_Name: {
                        "date": {
                            'start': notion_time(),
                            'end': None,
                        }
                    }, 
                },
            },
        )

    else:
        continue


## Filter events that have been updated since the GCal event has been made

#this query will return a dictionary that we will parse for information that we want
#look for events that are today or in current month
my_page = notion.databases.query(  
    **{
        "database_id": database_id, 
        "filter": {
            "and": [
                {
                    "property": NeedGCalUpdate_Notion_Name, 
                    "checkbox":  {
                        "equals": True
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


animate_text_wave_with_progress(text="Loading", new_text="Checked 1.5", target_percentage=20, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()


updatingNotionPageIds = []
updatingCalEventIds = []

for result in resultList:
    pageId = result['id']
    updatingNotionPageIds.append(pageId)
    try:
        calId = result['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content']
    except:
        calId = DEFAULT_CALENDAR_ID
    updatingCalEventIds.append(calId)

TaskNames = []
AutoRenames = []
start_Dates = []
end_Times = []
Frequencies = []
ExtraInfo = []
URL_list = []
CalendarList = []
CurrentCalList = []
updated_tasks = []
tasks_by_calendar = {}

updated_events_counter = 0

created_single_day_events = set()

if len(resultList) > 0:
    
    for i, el in enumerate(resultList):
        # print(f"Processing {i+1} of {len(resultList)}")
            
        calendar_name = el['properties'][Calendar_Notion_Name]['select']['name']
        # print(f"calendar_name: {calendar_name}")
        
        task_name = el['properties'][Task_Notion_Name]['title'][0]['text']['content']
        # print(f"task name: {task_name}")
        
        new_title = el['properties'][AutoRename_Notion_Name]['formula']['string']
        AutoRenames.append(new_title)

        # If the calendar name is not in the dictionary, add it with an empty list
        if calendar_name not in tasks_by_calendar:
            tasks_by_calendar[calendar_name] = []

        # Append the task name to the list of tasks for this calendar
        tasks_by_calendar[calendar_name].append(task_name)
        
        TaskNames.append(el['properties'][Task_Notion_Name]['title'][0]['text']['content'])
        start_Dates.append(el['properties'][Date_Notion_Name]['date']['start'])

        if el['properties'][GCalEventId_Notion_Name]['rich_text']:
            GCalEventId = el['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content']
            # print(f"GCal Event ID: {GCalEventId}")
        else:
            GCalEventId = DEFAULT_CALENDAR_ID

        if el['properties'][Date_Notion_Name]['date']['end'] != None:
            end_Times.append(el['properties'][Date_Notion_Name]['date']['end'])
        else:
            end_Times.append(el['properties'][Date_Notion_Name]['date']['start'])

        try:
            First_Days.append(el['properties'][First_Day_of_Week_Notion_Name]['select']['name'])
        except:
            First_Days.append("")
        
        try:
            Frequencies.append(el['properties'][Frequency_Notion_Name]['select']['name'])
        except:
            Frequencies.append("")
        
        try:
            Recur_Intervals.append(el['properties'][Recur_Interval_Notion_Name]['number'])
        except:
            Recur_Intervals.append("")

        try:
            Recur_Counts.append(el['properties'][Recur_Count_Notion_Name]['number'])
        except:
            Recur_Counts.append("")

        try:
            Recur_Untils.append(el['properties'][Recur_Until_Notion_Name]['date']['start'])
        except:
            Recur_Untils.append("")

        try:
            # 將所有選擇的天數提取到一個列表中，並使用逗號連接
            days = [day['name'] for day in el['properties'][Days_Notion_Name]['multi_select']]
            Recur_Days.append(",".join(days))
        except:
            Recur_Days.append("")
            
        try:
            Recur_Months.append(el['properties'][Months_Notion_Name]['multi_select'][0]['name'])
        except:
            Recur_Months.append("")
        
        try:
            byMonthDays.append(el['properties'][Days_of_Month_Notion_Name]['number'])
        except:
            byMonthDays.append("")
        
        try:
            byYearDays.append(el['properties'][Days_of_Year_Notion_Name]['number'])
        except:
            byYearDays.append("")
        
        try:
            byWeekNumbers.append(el['properties'][Week_Numbers_of_Year_Notion_Name]['number'])
        except:
            byWeekNumbers.append("")

        try: 
            ExtraInfo.append(el['properties'][ExtraInfo_Notion_Name]['rich_text'][0]['text']['content'])
        except:
            ExtraInfo.append("")
            
        URL_list.append(makeTaskURL(el['id'], urlRoot))

        # CalendarList.append(calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']])
        try:
            CalendarList.append(calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']])
            # print(f"CalendarList: {CalendarList}")
        except: #keyerror occurs when there's nothing put into the calendar in the first place
            CalendarList.append(calendarDictionary[DEFAULT_CALENDAR_NAME])

        if el['properties'][Current_Calendar_Id_Notion_Name]['rich_text']:
            CurrentCalList.append(el['properties'][Current_Calendar_Id_Notion_Name]['rich_text'][0]['text']['content'])
            # print(f"CurrentCalList: {CurrentCalList}")
        else:
            continue

        pageId = el['id']

        try:
            # 先尝试使用所有参数调用 upDateCalEvent
            # print(f"got_new_update: {got_new_update}")
            got_new_update = upDateCalEvent(
                task_name,
                AutoRenames[i],
                makeEventDescription(Frequencies[i], ExtraInfo[i]),
                parse_date(start_Dates[i]),
                URL_list[i],
                updatingCalEventIds[i],
                parse_date(end_Times[i]),
                CurrentCalList[i],
                CalendarList[i],
                thread,
                {
                    "Frequency_Notion_Name": Frequencies[i],
                    "First_Day_of_Week_Notion_Name": First_Days[i],
                    "Recur_Interval_Notion_Name": Recur_Intervals[i],
                    "Recur_Count_Notion_Name": Recur_Counts[i],
                    "Recur_Until_Notion_Name": Recur_Untils[i],
                    "Days_Notion_Name": Recur_Days[i],
                    "Months_Notion_Name": Recur_Months[i],
                    "Days_of_Month_Notion_Name": byMonthDays[i],
                    "Days_of_Year_Notion_Name": byYearDays[i],
                    "Week_Numbers_of_Year_Notion_Name": byWeekNumbers[i],
                },
            )
            # print(f"got_new_update: {got_new_update}")
            if got_new_update is True:
                updated_events_counter += 1
                updated_tasks.append((GCalEventId, task_name))  # 將 GCalEventId 和 task_name 作為元組添加到列表中
                created_single_day_events.add(updatingCalEventIds[i])  # 标记为已创建
                No_pages_modified = False
                no_new_updated = False
        except Exception as e:
            # 处理异常情况
            print(f"Error updating calendar event: {e}")
            # 这里可以选择重试或记录详细的错误信息
        

        calendar_id_to_name = {v: k for k, v in calendarDictionary.items()}
        calendar_name = calendar_id_to_name[CalendarList[i]]
        
        my_page = notion.pages.update( ##### This updates the last time that the page in Notion was updated by the code
            **{
                "page_id": pageId, 
                "properties": {
                    LastUpdatedTime_Notion_Name: {
                        "date":{
                            'start': notion_time(), #has to be adjusted for when daylight savings is different
                            'end': None,
                        }
                    },
                    Current_Calendar_Id_Notion_Name: {
                        "rich_text": [{
                            'text': {
                                'content': CalendarList[i]
                            }
                        }]
                    },
                    Calendar_Notion_Name:  {
                        'select': {
                            "name": calendar_name
                        },
                    }
                },
            },
        )

# After the loop, calculate the visual width of the longest title
max_width = 0
if updated_tasks:
    widths = [wcswidth(task[1]) for task in updated_tasks]
    if widths:
        max_width = max(widths)

# After the loop, convert updated_tasks to a set to remove duplicates
unique_updated_tasks = [{id: name} for id, name in updated_tasks]

# Count occurrences of each task title
task_counts = {}
for task in unique_updated_tasks:
    task_name = ','.join(AutoRenames) if isinstance(AutoRenames, list) else AutoRenames or list(task.items())[0][1]
    task_counts[task_name] = task_counts.get(task_name, 0) + 1


# Calculate total count of all added tasks
total_count = sum(task_counts.values())

# Initialize a set to keep track of printed titles
printed_titles = set()

# This will track the correct sequential number for printed tasks
printed_index = 1

# Check if there are any new tasks added
if unique_updated_tasks:
    stop_clear_and_print()
    print("\n")
    start_dynamic_counter_indicator()
    
    # Sort tasks by their IDs (or any other specified key)
    sorted_tasks = sorted(unique_updated_tasks, key=lambda x: list(x.keys())[0])
        
    for task in sorted_tasks:
        stop_clear_and_print()
        animate_text_wave("Updatin'", repeat=1)
        start_dynamic_counter_indicator()
        
        if AutoRenames and len(AutoRenames) == 2:
            id, task_name = AutoRenames
        else:
            item = list(task.items())[0]
            if len(item) == 2:
                id, task_name = item
            else:
                # 提供預設值或其他處理方式以避免 ValueError
                id, task_name = None, item[0] if item else (None, None)

        current_title = task_name if task_name else id

        if current_title in printed_titles:
            continue
        printed_titles.add(current_title)

        title_count = task_counts.get(current_title, 0)
        title_with_count = f"{current_title} (x{title_count})" if title_count > 1 else current_title

        spaces_to_add = max_width - wcswidth(title_with_count)
        title_with_count += ' ' * spaces_to_add

        stop_clear_and_print()
        print(f"{format_string(f'{printed_index}', bold=True, italic=True)}{formatted_dot} {format_string(title_with_count, italic=True)}  ")

        printed_index += 1

if updated_events_counter > 0:
    formatted_updated_counter = format_string(updated_events_counter, "C2") 
    print(f"\nTotal {formatted_updated} G.Event : {formatted_updated_counter}\n\n")
    start_dynamic_counter_indicator()
    No_pages_modified = False
    no_new_updated = False

todayDate = datetime.today().strftime("%Y-%m-%d")

animate_text_wave_with_progress(text="Loading", new_text="Checked 2", target_percentage=30, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

###########################################################################
##### Part 3: Sync GCal event updates for events already in Notion back to Notion!
###########################################################################

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


animate_text_wave_with_progress(text="Loading", new_text="Checked 2.1", target_percentage=35, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

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

animate_text_wave_with_progress(text="Loading", new_text="Checked 2.2", target_percentage=40, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

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


animate_text_wave_with_progress(text="Loading", new_text="Checked 2.3", target_percentage=40, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

# 更新 Notion 中的事件
def update_notion_event_with_recurrence(notion_event, recurrence_info):
    """
    更新 Notion 事件以包含重複信息。

    :param notion_event: Notion 中的事件對象
    :param recurrence_info: 從 Google Calendar 提取的重複信息
    """
    
    notion.pages.update(
        page_id=notion_event['id'],
        properties={
            Frequency_Notion_Name: {
                'select': {
                    'name': recurrence_info  # 將重複信息存儲到 Initiative_Notion_Name
                }
            }
        }
    )

def is_valid_uuid(uuid_to_test, version=4):
    regex = re.compile(
        r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}\Z', re.I
    )
    match = regex.match(uuid_to_test)
    return bool(match)

##We use the gCalId from the Notion dashboard to get retrieve the start Time from the gCal event
value = ''
exitVar = ''


for i, gCalId in enumerate(notion_gCal_IDs):
    # print(f"\nProcessing gCalId: {gCalId} (Index: {i})")
    try:
        # 確認 gCalId 是否有效
        if not is_valid_uuid(gCalId):
            valid_page_id = None
            for result in resultList:
                if result['properties'][GCalEventId_Notion_Name]['rich_text']:
                    if result['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content'] == gCalId:
                        valid_page_id = result['id']
                        break

            if valid_page_id:
                if valid_page_id not in notion_IDs_List:
                    notion_IDs_List.append(valid_page_id)
                if i < len(notion_gCal_IDs):
                    notion_gCal_IDs[i] = valid_page_id
                else:
                    notion_gCal_IDs.append(valid_page_id)
            else:
                continue

        # 確保索引範圍內，並且 gCalId 在 notion_gCal_IDs 中
        gCalId_to_check = valid_page_id if valid_page_id else gCalId
        if gCalId_to_check in notion_gCal_IDs:
            notion_index = notion_gCal_IDs.index(gCalId_to_check)
            notion_ID = notion_IDs_List[notion_index]
        else:
            continue

        # 繼續處理有效的 gCalId
        event_found = False
        for calendarID in calendarDictionary.keys():
            try:
                x = service.events().get(calendarId=calendarDictionary[calendarID], eventId=gCalId).execute()
                # print("calendarDictionary contents:", calendarDictionary)

            except HttpError:
                continue

            event_found = True

            if x['status'] == 'confirmed':
                value = x
                currentCalId = notion_gCal_CalNames[notion_index]
                newCalId = calendarID
                eventName = x['summary']
                # print(f"eventName: {eventName}", "newCalId: ", newCalId, "currentCalId: ", currentCalId)
                
                gCal_titles.append(eventName)
                gCal_CalIds.append(calendarID)

                # 提取重複事件信息
                el = x.get('recurrence')
                recurrence_info = extract_recurrence_info(gc, calendarID, x, el)
                # if recurrence_info:
                #     print(f"Recurrence info extracted: {recurrence_info}")

                # 更新日曆信息
                if currentCalId != newCalId:
                    
                    calendar_name_to_id = {v: k for k, v in calendarDictionary.items()}
                    # print("Reversed dictionary:", calendar_name_to_id)
                    
                    calendar_email = calendarDictionary.get(newCalId)

                    formattedCurrentCalName = format_string(currentCalId, less_visible=True)
                    formattedCalName = format_string(newCalId, italic=True, light_color=True)
                    print(f"{eventName}")
                    print(f'{formattedCurrentCalName} {formatted_right_arrow} {formattedCalName}\n')
                    modified_events_counter += 1
                    try:
                        notion.pages.update(
                            page_id=notion_ID, 
                            properties={
                                Calendar_Notion_Name: {
                                    'select': {
                                        'name': newCalId
                                        }
                                    },
                                Current_Calendar_Id_Notion_Name: {
                                    "rich_text": [{
                                        'text': {
                                            'content': calendar_email
                                        }
                                    }]
                                },
                                LastUpdatedTime_Notion_Name: {
                                    "date":{
                                        'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                        'end': None,
                                    }
                                },
                                }
                            )
                    except APIResponseError as e:
                        print(f"Failed to update Notion page with ID {notion_ID}: {e}")

                # 更新事件的開始和結束時間
                if 'start' in value:
                    if 'dateTime' in value['start']:
                        new_start_time = datetime.strptime(value['start']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S")
                        new_end_time = datetime.strptime(value['end']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S")
                    elif 'date' in value['start']:
                        date = datetime.strptime(value['start']['date'], "%Y-%m-%d")
                        new_start_time = datetime(date.year, date.month, date.day, 0, 0, 0)
                        new_end_time = datetime(date.year, date.month, date.day, 23, 59, 59)

                    # 檢查單日事件是否需要更新
                    if (not recurrence_info and 
                        (new_start_time != notion_start_datetimes[notion_index] or 
                         new_end_time != notion_end_datetimes[notion_index] or 
                         x['summary'] != notion_titles[notion_index])):

                        # 更新 Notion 頁面
                        try:
                            notion.pages.update(
                                page_id=notion_ID,
                                properties={
                                    "Event Start": {
                                        "date": {"start": new_start_time.isoformat(), "end": new_end_time.isoformat()}
                                    },
                                    "Event Title": {"title": [{"text": {"content": x['summary']}}]},
                                LastUpdatedTime_Notion_Name: {
                                    "date":{
                                        'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                        'end': None,
                                    }
                                },
                                }
                            )
                            # print(f"Notion page {notion_ID} updated successfully with new start/end time and title.")
                        except APIResponseError as e:
                            print(f"Failed to update Notion page with ID {notion_ID}: {e}")
                    # else:
                    #     print(f"Event {gCalId} is already up-to-date in Notion.")
            # else:
            #     print(f"Event {gCalId} is not confirmed; skipping.")
    except (HttpError, ValueError, IndexError) as e:
        print(f"Error occurred for event ID {gCalId}: {e}")
    except IndexError as e:
        print(f"Index error: {e}. Current index: {i}. Length of notion_IDs_List: {len(notion_IDs_List)}")


# 在循環後打印列表狀態
# print("Final states:")
# print(f"notion_IDs_List: {notion_IDs_List}")
# print(f"notion_gCal_IDs: {notion_gCal_IDs}")


animate_text_wave_with_progress(text="Loading", new_text="Checked 2.4", target_percentage=45, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

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
        # print(f"Title for Notion page ID {notion_IDs_List[i]} changed to {new_notion_titles[i]}")
        if new_notion_titles[i] != '':
            # 更新 Notion 的標題
            try:
                page_id = notion_IDs_List[i]
                notion.pages.update(
                    page_id=page_id, 
                    properties={
                        Task_Notion_Name: {
                            'title': [
                                {'text': {
                                    'content': new_notion_titles[i]
                                    }}
                                ]
                            },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        }
                    )
            except Exception as e:
                print(f"Failed to update title for Notion page ID {page_id}: {e}")
    else:
        new_notion_titles[i] = notion_titles[i]  # If gCal_titles[i] is empty, keep the original Notion title

# Ensure that any remaining titles in notion_titles are handled if notion_titles is longer than gCal_titles
for i in range(loop_length_titles, len(notion_titles)):
    new_notion_titles[i] = notion_titles[i]  # 如果 gCal_titles[i] 是空值，則保持原始的 Notion 標題


animate_text_wave_with_progress(text="Loading", new_text="Checked 2.5", target_percentage=50, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

@skip_in_jenkins
def format_time(time):
    if time is None:
        # 可以选择不进行任何操作，或者设置一个默认值
        return ""
    # Use the provided remove_leading_zero function to format time without leading zeros
    return remove_leading_zero(time.strftime('%H:%M'))

@skip_in_jenkins
def remove_leading_zero(time_str):
    parts = time_str.split(':')
    if len(parts) == 2:
        hour = str(int(parts[0]))  # 移除小时的前导零
        minute = parts[1]  # 分钟部分不变
        return f"{hour}:{minute}"
    return time_str

@skip_in_jenkins
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

@skip_in_jenkins
def format_date(date):
    if date is None:
        return " " * 12  # 返回固定长度的空字符串，以保持对齐
    # 格式化日期，确保日和月份始终占用两个字符位置（对于日，通过在单数前添加空格实现）
    day = date.strftime('%d').lstrip('0').rjust(2, ' ')
    month = date.strftime('%b')
    year = date.strftime('%Y')
    return f"{day} {month}, {year}"

@skip_in_jenkins
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

# 修改循环，收集事件信息而不是直接打印
for i in range(len(notion_gCal_IDs)):
    
    # 檢查索引是否在範圍內
    if (i >= len(notion_IDs_List) or 
        i >= len(notion_titles) or 
        i >= len(new_notion_titles) or 
        i >= len(notion_start_datetimes) or 
        i >= len(notion_end_datetimes)):
        # print(f"Index {i} is out of range for one of the lists.")
        continue  # 跳過這次迴圈，避免 IndexError

    notion_ID = notion_IDs_List[i]
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
            'is_added': event_added_yet_modified,
            'is_modified': not event_added_yet_modified,
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

# Sort events by start time
modified_events.sort(key=lambda x: x['start_time'] if x['start_time'] is not None else datetime.max)

if modified_events_counter > 0:
    stop_clear_and_print()
    formatted_modified_counter = format_string(modified_events_counter, "C2") 
    print(f"\nTotal {formatted_modified} New N.Event : {formatted_modified_counter}\n\n")
    start_dynamic_counter_indicator()
    No_pages_modified = False
    no_new_updated = False
    

animate_text_wave_with_progress(text="Loading", new_text="Checked 2.7", target_percentage=60, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

def update_notion_page_with_retry(page_id, updates, max_retries=5):
    retry_count = 0
    backoff_factor = 1  # Initial backoff duration in seconds
    while retry_count < max_retries:
        try:
            # Increase timeout for the request
            with httpx.Client() as client:
                notion.pages.update(page_id=page_id, **updates, http_client=client)
            return
        except HTTPResponseError as e:
            if e.status == 502:
                # Handle 502 Bad Gateway specifically, if needed
                print(f"Retry {retry_count + 1}/{max_retries}: Server error {e.status}. Retrying after {backoff_factor} seconds...")
            else:
                # Handle other HTTP errors
                print(f"Retry {retry_count + 1}/{max_retries}: Failed with status {e.status}. Retrying after {backoff_factor} seconds...")
            time.sleep(backoff_factor)
            backoff_factor *= 2  # Exponential backoff
            retry_count += 1
    print("Failed to update Notion page after maximum retries.")

CalNames = list(calendarDictionary.keys())
CalIds = list(calendarDictionary.values())

for i in range(len(new_notion_start_datetimes)):
    if new_notion_start_datetimes[i]  != '' and new_notion_end_datetimes[i] != '': #both start and end time need to be updated
        start = new_notion_start_datetimes[i]
        end = new_notion_end_datetimes[i]
 
        if start.hour == 0 and start.minute == 0 and start == end: #you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = notion.pages.update( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i], 
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': start.strftime("%Y-%m-%d"),
                                'end': None,
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
        elif start.hour == 0 and start.minute == 0 and end.hour == 0 and end.minute == 0: #you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = update_notion_page_with_retry( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],  
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': start.strftime("%Y-%m-%d"),
                                'end': end.strftime("%Y-%m-%d"),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalIds[CalNames.index(gCalId)]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCalId 
                            },
                        },
                    },
                },
            )
        else: #update Notin using datetime format 
            my_page = notion.pages.update( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': DateTimeIntoNotionFormat(start),
                                'end': DateTimeIntoNotionFormat(end),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        }
                    },
                },
            )
    elif new_notion_start_datetimes[i]  != '': #only start time need to be updated
        start = new_notion_start_datetimes[i]
        end = notion_end_datetimes[i]
 
        if start.hour == 0 and start.minute == 0 and start == end: #you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = update_notion_page_with_retry( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': start.strftime("%Y-%m-%d"),
                                'end': None,
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalIds[CalNames.index(gCalId)]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCalId 
                            },
                        },
                    },
                },
            )
        elif start.hour == 0 and start.minute == 0 and end.hour == 0 and end.minute == 0: #you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = update_notion_page_with_retry( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': start.strftime("%Y-%m-%d"),
                                'end': end.strftime("%Y-%m-%d"),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalIds[CalNames.index(gCalId)]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCalId 
                            },
                        },
                    },
                },
            )
        else: #update Notin using datetime format 
            # print("calendarDictionary:", calendarDictionary)
            # print("gCalId:", gCalId)
            my_page = update_notion_page_with_retry( #update the notion dashboard with the new datetime and update the last updated time
                page_id=notion_IDs_List[i],
                updates={
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': DateTimeIntoNotionFormat(start),
                                'end': DateTimeIntoNotionFormat(end),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': gCalId
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCalId 
                            },
                        },
                    },
                },
            )
    elif new_notion_end_datetimes[i] != '': #only end time needs to be updated
        start = notion_start_datetimes[i]
        end = new_notion_end_datetimes[i]

        if start.hour == 0 and start.minute == 0 and start == end: #you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = update_notion_page_with_retry( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': start.strftime("%Y-%m-%d"),
                                'end': None,
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalIds[CalNames.index(gCalId)]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCalId 
                            },
                        },
                    },
                },
            )
        elif start.hour == 0 and start.minute == 0 and end.hour == 0 and end.minute == 0: #you're given 12 am dateTimes so you want to enter them as dates (not datetimes) into Notion
            my_page = update_notion_page_with_retry( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': start.strftime("%Y-%m-%d"),
                                'end': end.strftime("%Y-%m-%d"),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalIds[CalNames.index(gCalId)]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCalId 
                            },
                        },
                    },
                },
            )
        else: #update Notin using datetime format 
            my_page = notion.pages.update( #update the notion dashboard with the new datetime and update the last updated time
                **{
                    "page_id": notion_IDs_List[i],
                    "properties": {
                        "title": {
                            "title": [
                                {
                                    "text": {
                                        "content": new_notion_titles[i]
                                    }
                                }
                            ]
                        },
                        Date_Notion_Name: {
                            "date":{
                                'start': DateTimeIntoNotionFormat(start),
                                'end': DateTimeIntoNotionFormat(end),
                            }
                        },
                        LastUpdatedTime_Notion_Name: {
                            "date":{
                                'start': notion_time(), #has to be adjsuted for when daylight savings is different
                                'end': None,
                            }
                        },
                        Current_Calendar_Id_Notion_Name: {
                            "rich_text": [{
                                'text': {
                                    'content': CalIds[CalNames.index(gCalId)]
                                }
                            }]
                        },
                        Calendar_Notion_Name: {
                            'select': {
                                "name": gCalId 
                            },
                        }
                    },
                },
            )
    else: #nothing needs to be updated here
        continue 
    
animate_text_wave_with_progress(text="Loading", new_text="Checked 3", target_percentage=70, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

###########################################################################
##### Part 4: Bring events (not in Notion) from GCal to Notion
###########################################################################


##First, we get a list of all of the GCal Event Ids from the Notion Dashboard.
# Retrieve all pages from the database
pages = notion.databases.query(database_id=database_id)

# Filter the pages by GCalEventId_Notion_Name and Delete_Notion_Name
filtered_pages = [page for page in pages['results'] 
                  if page['properties'][GCalEventId_Notion_Name]['rich_text'] 
                  and page['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content'] != '' 
                  and not page['properties'][Delete_Notion_Name]['checkbox']]

# Now filtered_pages contains only the pages where GCalEventId_Notion_Name is not empty and Delete_Notion_Name is not checked
ALL_notion_gCal_Ids =[]

for page in filtered_pages:
    ALL_notion_gCal_Ids.append(page['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content'])
    # print("ALL_notion_gCal_Ids:", ALL_notion_gCal_Ids)

start_dynamic_counter_indicator()

animate_text_wave_with_progress(text="Loading", new_text="Checked 3.1", target_percentage=72, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

##Get the GCal Ids and other Event Info from Google Calendar 
events = []
for el in calendarDictionary.keys(): #get all the events from all calendars of interest
    x = service.events().list(calendarId=calendarDictionary[el],
                            maxResults=2000,
                            timeMin=googleQuery(),
                            singleEvents=True,
                            orderBy='startTime').execute()    
    events.extend(x['items'])

# calItems = events['items']
calItems = events

calName = [item['summary'] if 'summary' in item else 'Untitled' for item in calItems]

gCal_calendarId = [item['organizer']['email'] for item in calItems] #this is to get all of the calendarIds for each event

CalNames = list(calendarDictionary.keys())
CalIds = list(calendarDictionary.values())
gCal_calendarName = [ CalNames[CalIds.index(x)] for x in gCal_calendarId]

calStartDates = []
calEndDates = []
for el in calItems:
    try:
        calStartDates.append(datetime.strptime(el['start']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(el['start']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0)
        # gCal_start_datetimes.append(datetime.strptime(x, "%Y-%m-%dT%H:%M:%S"))
        calStartDates.append(x)
    try:
        calEndDates.append(datetime.strptime(el['end']['dateTime'][:-6], "%Y-%m-%dT%H:%M:%S"))
    except:
        date = datetime.strptime(el['end']['date'], "%Y-%m-%d")
        x = datetime(date.year, date.month, date.day, 0, 0, 0) 
        # gCal_end_datetimes.append(datetime.strptime(value['end']['date'][:-6], "%Y-%m-%dT%H:%M:%S"))
        calEndDates.append(x)

    # 檢查開始和結束日期是否相同
    if calStartDates[-1] == calEndDates[-1]:
        # 對於全天事件，可以選擇不添加結束日期或將結束日期設置為開始日期
        # 這裡選擇不添加結束日期到calEndDates列表來避免將單一日期視為日期範圍
        pass
    # 如果开始和结束日期不相同，则已经在之前的逻辑中添加了结束日期，无需再次添加

calIds = [item['id'] for item in calItems]
# print("GCal IDs:", calIds)

# calDescriptions = [item['description'] for item in calItems]
calDescriptions = []
for item in calItems:
    try: 
        calDescriptions.append(item['description'])
    except:
        calDescriptions.append(' ')


animate_text_wave_with_progress(text="Loading", new_text="Checked 3.5", target_percentage=78, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

#Now, we compare the Ids from Notion and Ids from GCal. If the Id from GCal is not in the list from Notion, then 
## we know that the event does not exist in Notion yet, so we should bring that over. 
delete_flags_dict = {page['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content']: 
                     page['properties'][Delete_Notion_Name]['checkbox'] 
                     for page in pages['results'] 
                     if page['properties'][GCalEventId_Notion_Name]['rich_text']}

# Create a new list to store the 'Delete from GCal?' property values
delete_notion_flags = [delete_flags_dict.get(id, False) for id in calIds]
# print("Delete Notion Flags:", delete_notion_flags)


# Create an empty list to store the names of the tasks that are added
added_tasks = []

n_months_ago = 3

# Append False to delete_notion_flags for every missing element
for i in range(len(calIds)):
    if i >= len(delete_notion_flags):
        delete_notion_flags.insert(i, False)

# # 判断是否为专业术语或保護詞
# def is_special_term(term):
#     # 保護大小写和词形的保護词匹配
#     if term in protected_terms or term.lower() in [t.lower() for t in protected_terms]:
#         return True
#     # 检查是否是拼写选项中的专业术语
#     for correct_term in correct_terms:
#         if correct_term.lower().startswith(term.lower()):
#             return True
#     return False


# # 判断是否为常见的拼写错误（如重复字母、少字母等）
# def is_simple_typo(term):
#     # 常见拼写错误的简单规则，比如单词太短不作校正或只有一个字母不同
#     if len(term) < 6:
#         return True  # 字符太少，可能是普通拼写错误
#     # 检查是否有明显的错字，如重复字符、漏字等
#     return False  # 复杂的词汇，认为不是简单的拼写错误

# 进行拼写校正
# def correct_spelling(term):
#     # 如果是 "Untitled" 或者空格，直接返回，不進行校正
#     if term.lower().startswith("untitled") or re.match(r'^\s+$', term):
#         return "Untitled"
    
#     # 如果是保护词汇，跳过拼写校正
#     if protected_terms and term.lower() in [t.lower() for t in protected_terms]:
#         return term

#     # 仅对可能的常见拼写错误进行校正
#     if is_simple_typo(term):
#         # 使用 TextBlob 进行拼写校正
#         blob = TextBlob(term)
#         corrected_term = str(blob.correct())

#         # 使用 fuzzywuzzy 模糊匹配进一步校正
#         best_match = process.extractOne(corrected_term, correct_terms)
#         if best_match and best_match[1] > 60:  # 如果 fuzzywuzzy 相似度较高
#             return best_match[0]
        
#         return corrected_term  # 否则返回 TextBlob 校正结果
    
#     # 如果不是简单拼写错误，直接返回原词
#     return term

def get_existing_titles(service, n_months_ago, calendar_id):
    # Include time in the start_date in RFC3339 format
    start_date = (datetime.now(pytz.UTC) - timedelta(days=30*n_months_ago)).isoformat()

    try:
        events_result = service.events().list(calendarId=calendar_id,
                                              timeMin=start_date,
                                              singleEvents=True,
                                              orderBy='startTime').execute()
        events = events_result.get('items', [])
        titles = [event['summary'] for event in events if 'summary' in event]
        return titles
    except Exception as e:
        print(f"An error occurred: {e}")
        return []

def ordinal(n):
    if 10 <= n % 100 <= 20:
        suffix = 'th'
    else:
        suffix = {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th')
    return f"{n}{suffix}"

def extract_number_and_position(title):
    matches = re.finditer(r'\b(\d+)(st|nd|rd|th)\b', title)
    for match in matches:
        return int(match.group(1)), match.start(), match.end()
    return None, None, None

def create_page(calName, calStartDates, calEndDates, calDescriptions, calIds, gCal_calendarId, gCal_calendarName, i, end=None, recurring_event_id=None):

    # Convert dates to local timezone
    calStartDates[i] = calStartDates[i].astimezone(local_tz)
    if end:
        end = end.astimezone(local_tz)
    else:
        calEndDates[i] = calEndDates[i].astimezone(local_tz)

    # Handle all-day events
    if isinstance(calStartDates[i], datetime) and calStartDates[i].hour == 0 and calStartDates[i].minute == 0:
        # This is an all-day event
        start_date = calStartDates[i].date()  # Only keep the date part
        if calEndDates[i].date() > start_date + timedelta(days=1):  # Check if the event spans more than one day
            end_date = calEndDates[i].date() - timedelta(days=1)  # Set the end date to the end of the event, minus one day
        else:
            end_date = None  # No end date for single-day or next-day midnight events
    else:
        # This is a timed event
        start_date = calStartDates[i]
        end_date = calEndDates[i]  # Set the end time

    # Format dates for Notion
    start_date_str = start_date.isoformat() if isinstance(start_date, datetime) else start_date.strftime('%Y-%m-%d')
    end_date_str = None if end_date is None else (end_date.isoformat() if isinstance(end_date, datetime) else end_date.strftime('%Y-%m-%d'))

    # 提取重複事件信息
    event = calItems[i]
    recurrence_info, found_recurring_event_id = extract_recurrence_info(service, gCal_calendarId[i], event, el)

    # Create a page in Notion
    # print("Creating page with title:", calName[i])
    unique_id = found_recurring_event_id if found_recurring_event_id else calIds[i]
    properties = {
        Task_Notion_Name: {
            "type": 'title',
            "title": [
                {
                    "type": 'text',
                    "text": {
                        "content": calName[i],
                    },
                },
            ],
        },
        Date_Notion_Name: {
            "type": 'date',
            'date': {
                'start': start_date_str,
                'end': end_date_str,
            }
        },
        LastUpdatedTime_Notion_Name: {
            "type": 'date',
            'date': {
                'start': notion_time(),
                'end': None,
            }
        },
        ExtraInfo_Notion_Name:  {
            "type": 'rich_text',
            "rich_text": [{
                'text': {
                    'content': calDescriptions[i]
                }
            }]
        },
        GCalEventId_Notion_Name: {
            "type": "rich_text",
            "rich_text": [{
                'text': {
                    'content': unique_id
                }
            }]
        },
        On_GCal_Notion_Name: {
            "type": "checkbox",
            "checkbox": True
        },
        Current_Calendar_Id_Notion_Name: {
            "rich_text": [{
                'text': {
                    'content': gCal_calendarId[i]
                }
            }]
        },
        Calendar_Notion_Name: {
            'select': {
                "name": gCal_calendarName[i]
            },
        }
    }

    # 同步 recurrence 信息到 Notion
    if recurrence_info:
        # print(f"recurrence_info: {recurrence_info}")
        properties[Frequency_Notion_Name] = {
            "select": {
                "name": recurrence_info.get('frequency', 'Unknown')
            }
        }
        properties[Recur_Interval_Notion_Name] = {
            "number": int(recurrence_info.get('interval', 1))
        }

        # 如果存在 `until`，则优先同步 `until`，否则同步 `count`
        if recurrence_info.get('until'):
            properties[Recur_Until_Notion_Name] = {
                "date": {
                    'start': recurrence_info['until'],
                    'end': None
                }
            }
        elif recurrence_info.get('count'):
            properties[Recur_Count_Notion_Name] = {
                "number": int(recurrence_info['count'])
            }

        # 处理 byday 信息
        if recurrence_info.get('byday'):
            properties[Days_Notion_Name] = {
                "multi_select": [{'name': day} for day in recurrence_info['byday'].split(',')]
            }

    # Create the page in Notion
    page = notion.pages.create(
        **{
            "parent": {
                "database_id": database_id,
            },
            "properties": properties,  # Dynamically updated properties
        },
    )
    
    # Update the event title in Google Calendar if it's "Untitled"
    if calName[i] == 'Untitled':
        update_google_calendar_event_title(service, gCal_calendarId[i], calIds[i], 'Untitled')
    
    return page

def update_google_calendar_event_title(service, calendar_id, event_id, new_title):
    try:        
        event = service.events().get(calendarId=calendar_id, eventId=event_id).execute()
        # print(event.get('recurrence', 'No recurrence info available'))
        event['summary'] = new_title
        updated_event = service.events().update(calendarId=calendar_id, eventId=event_id, body=event).execute()
        print(updated_event.get('recurrence'))
        # print(f"Updating event ID: {event_id} with title: {new_title}")
    except HttpError as error:
        print(f"An error occurred: {error}")

# 在脚本开始处初始化一个集合用于跟踪已处理的 recurringEventId
processed_recurring_ids = set()

# Initialize a list to track added tasks
unique_added_tasks = []

# 新集合來追踪已創建的單日事件
created_single_day_events = set()

for i, calId in enumerate(calIds):

    # 檢查是否超出任何列表範圍，以防止 IndexError
    if i >= len(calItems) or i >= len(gCal_calendarId) or i >= len(calName) or i >= len(calStartDates) or i >= len(calEndDates) or i >= len(delete_notion_flags):
        print(f"Index {i} is out of range for one or more lists.")
        continue  # 跳過該次迭代

    # 提取事件的重复信息
    event = calItems[i]  # 假设 calItems[i] 是当前事件
    recurrence_info, found_recurring_event_id = extract_recurrence_info(service, gCal_calendarId[i], event, el)

    # 檢查是否已處理此事件
    unique_id = found_recurring_event_id if found_recurring_event_id else calIds[i]
    if unique_id in processed_recurring_ids:
        continue

    # 確保同一 recurringEventId 只被處理一次
    if found_recurring_event_id in processed_recurring_ids:
        continue  # 跳過已處理的重複事件

    # 檢查是否需要創建新的事件
    if unique_id not in ALL_notion_gCal_Ids and not delete_notion_flags[i]:

        # 處理標題生成邏輯
        if i < len(calName):
            title = calName[i].strip() if calName[i] else 'Untitled'  # 默認未命名標題
            existing_titles = get_existing_titles(service, n_months_ago, gCal_calendarId[i])
            default_number = 1
            new_title = generate_unique_title(existing_titles, title, new_titles, default_number, resultList, current_page=event)

            calName[i] = new_title  # 更新標題
            new_titles.append(new_title)
            update_google_calendar_event_title(service, gCal_calendarId[i], calId, new_title)
        else:
            print(f"Index {i} is out of range for the list calName")

        # 添加到已處理的重複事件集合
        if found_recurring_event_id:
            processed_recurring_ids.add(found_recurring_event_id)

        # 創建 Notion 頁面的邏輯
        # 單日事件
        if calStartDates[i] == calEndDates[i] - timedelta(days=1):
            end = calEndDates[i] - timedelta(days=1)
            if title in created_single_day_events:
                # print(f"Event '{title}' already created. Skipping.")
                continue
            else:
                my_page = create_page(calName, calStartDates, calEndDates, calDescriptions, calIds, gCal_calendarId, gCal_calendarName, i, end, found_recurring_event_id)
                created_single_day_events.add(title)  # 添加到追踪集合

        # 日期格式
        elif calStartDates[i].hour == 0 and calStartDates[i].minute == 0 and calEndDates[i].hour == 0 and calEndDates[i].minute == 0:
            end = calEndDates[i] - timedelta(days=1)
            if calIds[i] in created_single_day_events:
                # print(f"Event '{title}' already created. Skipping.")
                continue
            else:
                my_page = create_page(calName, calStartDates, calEndDates, calDescriptions, calIds, gCal_calendarId, gCal_calendarName, i, end, found_recurring_event_id)
                created_single_day_events.add(calIds[i])

        # 常規日期時間
        else:
            if calIds[i] in created_single_day_events:
                # print(f"Event '{title}' already created. Skipping.")
                continue
            else:
                my_page = create_page(calName, calStartDates, calEndDates, calDescriptions, calIds, gCal_calendarId, gCal_calendarName, i, calEndDates[i], found_recurring_event_id)
                created_single_day_events.add(calIds[i])

        # 確保事件只添加一次
        if calIds[i] not in created_single_day_events:
            created_single_day_events.add(calIds[i])

        added_tasks.append((calId, title))  # 添加到已處理任務列表

# 打印已处理的 recurringEventId
# print(f"Processed recurring event IDs: {processed_recurring_ids}")

animate_text_wave_with_progress(text="Loading", new_text="Checked 3.7", target_percentage=80, current_progress=global_progress, sleep_time=0.005, percentage_first=True)

clear_line()

# After the loop, calculate the visual width of the longest title
max_width = 0
if added_tasks:
    widths = [wcswidth(task[1]) for task in added_tasks]
    if widths:
        max_width = max(widths)

# After the loop, convert added_tasks to a set to remove duplicates
unique_added_tasks = [{id: name} for id, name in added_tasks]

# Count occurrences of each task title
task_counts = {}
for task in unique_added_tasks:
    _, title = list(task.items())[0]
    task_counts[title] = task_counts.get(title, 0) + 1

# Calculate total count of all added tasks
total_count = sum(task_counts.values())

# Initialize a set to keep track of printed titles
printed_titles = set()

# This will track the correct sequential number for printed tasks
printed_index = 1

# Check if there are any new tasks added
if unique_added_tasks:
    stop_clear_and_print()
    print("\n")
    start_dynamic_counter_indicator()
    
    # Sort tasks by their IDs (or any other specified key)
    sorted_tasks = sorted(unique_added_tasks, key=lambda x: list(x.keys())[0])
        
    for task in sorted_tasks:
        stop_clear_and_print()
        animate_text_wave("re/adding", repeat=1)
        start_dynamic_counter_indicator()
        
        id, title = list(task.items())[0]

        # 使用 `new_title` 如果它存在，否則使用 `title`
        current_title = new_title if new_title else title

        # 跳過已經打印的標題
        if current_title in printed_titles:
            continue
        printed_titles.add(current_title)

        # 使用 `.get()` 方法，設置默認值以避免 KeyError
        title_count = task_counts.get(current_title, 0)
        title_with_count = f"{current_title} (x{title_count})" if title_count > 1 else current_title

        # 計算空間並格式化輸出
        spaces_to_add = max_width - wcswidth(title_with_count)
        title_with_count += ' ' * spaces_to_add

        stop_clear_and_print()
        print(f"{format_string(f'{printed_index}', bold=True, italic=True)}{formatted_dot} {format_string(title_with_count, italic=True)}  ")
        start_dynamic_counter_indicator()

        # 增加 printed_index 以便處理下一個標題
        printed_index += 1

# Adjust the total count output
if total_count > 0:
    stop_clear_and_print()
    formatted_unique_added_counter = format_string(total_count, "C2", bold=True)
    print(f"\nTotal " +  format_string('re/', less_visible=True, italic=True) + f"{formatted_added} New G.Event(s) : {formatted_unique_added_counter}\n\n")
    start_dynamic_counter_indicator()
    no_new_added = False
    no_new_updated = False

animate_text_wave_with_progress(text="Loading", new_text="Checked 4", target_percentage=90, current_progress=global_progress, sleep_time=0.005, percentage_first=True)
clear_line()

###########################################################################
##### Part 5: Deletion Sync -- If marked Done in Notion, 
##### then it will delete the GCal event 
##### (and the Notion event once Python API updates)
###########################################################################

# Retrieve all pages from the database
pages = notion.databases.query(database_id=database_id)

# Filter the pages by GCalEventId_Notion_Name, On_GCal_Notion_Name, and Delete_Notion_Name
filtered_pages = [page for page in pages['results'] 
                  if page['properties'][GCalEventId_Notion_Name]['rich_text'] 
                  and page['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content'] != '' 
                  and page['properties'][On_GCal_Notion_Name]['checkbox'] 
                  and page['properties'][Delete_Notion_Name]['checkbox']]  # Only include pages where Delete from GCal? is checked

# Now filtered_pages contains only the pages where GCalEventId_Notion_Name is not empty, On_GCal_Notion_Name is checked, and Delete_Notion_Name is checked

resultList = filtered_pages

events_by_calendar = {}

# 步驟 1 & 2：收集數據並處理
for el in resultList:
    calendar_name = el['properties'][Calendar_Notion_Name]['select']['name']
    task_title = el['properties'][Task_Notion_Name]['title'][0]['text']['content']
    
    if calendar_name not in events_by_calendar:
        events_by_calendar[calendar_name] = {}
    if task_title not in events_by_calendar[calendar_name]:
        events_by_calendar[calendar_name][task_title] = 1
    else:
        events_by_calendar[calendar_name][task_title] += 1

animate_text_wave_with_progress(text="Loading", new_text="Checked 4.5", target_percentage=94, current_progress=global_progress, sleep_time=0.005, percentage_first=True)
clear_line()

# 添加重试机制的辅助函数
def delete_notion_task(notion, page_id, task_title, max_retries=3):
    retries = 0
    while retries < max_retries:
        try:
            response = notion.pages.update(
                **{
                    "page_id": page_id,
                    "archived": True,  # 将任务存档而非物理删除
                    "properties": {}
                },
            )
            # print(f"Notion task '{task_title}' archived successfully.")
            return response
        except Exception as e:
            retries += 1
            print(f"Error deleting Notion task '{task_title}' (attempt {retries}/{max_retries}): {e}")
            if retries >= max_retries:
                print(f"Failed to delete Notion task '{task_title}' after {max_retries} attempts.")
                return None
            time.sleep(2)  # 重试前等待2秒

if DELETE_OPTION == 0 and len(resultList) > 0: #delete gCal event (and Notion task once the Python API is updated)
    stop_clear_and_print()
    print("\n")
    start_dynamic_counter_indicator()
    
    CalendarList = [] 
    CurrentCalList = [] 
    printed_calendars = set() 
    printed_titles = set()  # 用于跟踪已打印的标题
    
    # 在删除操作前初始化用于跟踪成功删除的事件的结构
    successful_deletions = {}

    # 初始化总删除事件数
    total_deleted_events = 0

    for i, el in enumerate(resultList):
        
        calendar_name = el['properties'][Calendar_Notion_Name]['select']['name']
        task_title = el['properties'][Task_Notion_Name]['title'][0]['text']['content']
        calendarID = calendarDictionary[el['properties'][Calendar_Notion_Name]['select']['name']]
        eventId = el['properties'][GCalEventId_Notion_Name]['rich_text'][0]['text']['content']
        pageId = el['id']

        # 删除 Google Calendar 事件
        try:
            service.events().delete(calendarId=calendarID, eventId=eventId).execute()
            # print(f"Google Calendar event {eventId} deleted successfully.")
        except Exception as e:
            if e.resp.status == 410:
                # 事件已經在 GCal 刪除，繼續處理 Notion 事件
                print(f"Event {eventId} was already deleted on GCal.")
            else:
                stop_clear_and_print()
                print("Error deleting GCal event:", e)
                start_dynamic_counter_indicator()

        # 无论 Google Calendar 刪除是否成功，删除 Notion 任务（带重试机制）
        response = delete_notion_task(notion, pageId, task_title)
        
        # 如果删除成功，记录删除状态
        if response:
            if calendar_name not in successful_deletions:
                successful_deletions[calendar_name] = {}
            if task_title not in successful_deletions[calendar_name]:
                successful_deletions[calendar_name][task_title] = 1
            else:
                successful_deletions[calendar_name][task_title] += 1

    total_deleted_events = sum(count for tasks in successful_deletions.values() for count in tasks.values())
    
    task_counter = 1  # 初始化任务计数器

    # 所有删除操作完成后，根据successful_deletions打印成功删除的事件
    for calendar_name, tasks in successful_deletions.items():
        stop_clear_and_print()
        animate_text_wave("deletin", repeat=1)
        start_dynamic_counter_indicator()
        for task_title, count in tasks.items():
            count = events_by_calendar[calendar_name][task_title] if calendar_name and task_title in events_by_calendar[calendar_name] else 1
            if count > 1:
                stop_clear_and_print()
                print(f"{task_counter}. {task_title} (x{count})")
                start_dynamic_counter_indicator()
            else:
                stop_clear_and_print()
                clear_line()
                print(f"{task_counter}. {task_title}")
                start_dynamic_counter_indicator()
            task_counter += 1  # 更新任务计数器

    ps_word = format_string("(s)", bold=True)
    page_word = "Page" if total_deleted_events == 1 else "Page" + ps_word
    stop_clear_and_print()
    print(f"\nTotal {formatted_deleted} {page_word} : ", format_string(total_deleted_events, bold=True)+f"\n\n")
    start_dynamic_counter_indicator()
    no_new_updated = False
    No_pages_modified = False

stop_clear_and_print()
animate_text_wave("FINAL checked", repeat=1)
start_dynamic_counter_indicator()

animate_text_wave_with_progress(text="Loading", new_text="Checked 5", target_percentage=100, current_progress=global_progress, sleep_time=0.005, percentage_first=True)
clear_line()

printed_no_new_added = False
printed_no_new_updated = False

# Modify the calls to format_string to ensure None is handled
formatted_page_added = format_string("Page Added") or "Page Added"
formatted_page_updated = format_string("Page Updated") or "Page Updated"
formatted_fr = format_string("fr.", italic=True, less_visible=True) or 'fr.'
formatted_notion = format_string(" Notion", less_visible=True) or ' Notion'

# Apply the modified variables in the print statements
if no_new_added:
    stop_clear_and_print()
    print(f"\n{formatted_no}" + ' ' + formatted_page_added + '  ' + formatted_fr + formatted_notion)
    start_dynamic_counter_indicator()
    printed_no_new_added = True

if no_new_updated:
    if printed_no_new_added != True:
        stop_clear_and_print()
        print(f"\n\n{formatted_no}" + ' ' + formatted_page_updated + '  ' + formatted_fr + formatted_notion)
        start_dynamic_counter_indicator()
    else:
        stop_clear_and_print()
        print(f"{formatted_no}" + ' ' + formatted_page_updated + '  ' + formatted_fr + formatted_notion)
        start_dynamic_counter_indicator()
    printed_no_new_updated = True

if No_pages_modified:
    modified_string = formatted_modified
    count_string = format_string(str(len(events_to_update)), bold=True)
    event_string = "Event" if len(events_to_update) < 2 else "Event" + '' + format_string("(", bold=True) + format_string(str('s'), bold=True) + format_string(")", bold=True)
    if not No_pages_modified:
        if printed_no_new_added or printed_no_new_updated:
            stop_clear_and_print()
            print(f"{modified_string}" + '  ' + f"{count_string}" + '  ' + f"{event_string}{formatted_dot}\n", end="", flush=True)
        else:
            stop_clear_and_print()
            print(f"\n{modified_string}" + '  ' + f"{count_string}" + '  ' + f"{event_string}{formatted_dot}\n", end="", flush=True)
    else:
        if printed_no_new_added or printed_no_new_updated:
            stop_clear_and_print()
            print(f"{formatted_no}" + ' ' + f"Page Modified\n", end="", flush=True)
        else:
            stop_clear_and_print()
            print(f"\n{formatted_no}" + ' ' + f"Page Modified\n", end="", flush=True)
        
if no_new_added or no_new_updated or No_pages_modified:
    stop_clear_and_print()
    print("\n\n" + '-' * terminal_width + "\n" + "End of Script".center(terminal_width) + "\n" + '-' * terminal_width)
else:
    stop_clear_and_print()
    print('-' * terminal_width + "\n" + "End of Script".center(terminal_width) + "\n" + '-' * terminal_width)

# 在脚本结束或其他需要立即停止打印的地方
immediate_stop_event.set()