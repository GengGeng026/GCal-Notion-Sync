import os
import re
from dotenv import load_dotenv
import httpx
from notion_client import Client
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
from collections import defaultdict
from collections import Counter
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from googleapiclient.errors import HttpError
import googleapiclient.errors
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from concurrent.futures import ThreadPoolExecutor, as_completed, CancelledError,TimeoutError
from queue import Queue
import logging
from wcwidth import wcswidth
import traceback
import pprint
import shutil
import functools

###########################################################################
##### The Set-Up Section. Please follow the comments to understand the code. 
###########################################################################

load_dotenv()
NOTION_TOKEN = os.getenv("NOTION_API_KEY") #the secret_something from Notion Integration

# Create an instance of the Notion client
notion = Client(auth=NOTION_TOKEN)

database_id = os.getenv("NOTION_DATABASE_ID") #get the mess of numbers before the "?" on your dashboard URL (no need to split into dashes)

urlRoot = os.getenv("NOTION_DATABASE_URL") #open up a task and then copy the URL root up to the "p="

#GCal Set Up Part
DEFAULT_EVENT_LENGTH = 60 #This is how many minutes the default event length is. Feel free to change it as you please
timezone = 'Asia/Kuala_Lumpur' #Choose your respective time zone: http://www.timezoneconverter.com/cgi-bin/zonehelp.tzc

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
Initiative_Notion_Name = 'Initiative'
ExtraInfo_Notion_Name = 'Notes'
On_GCal_Notion_Name = 'On GCal?'
to_Auto_Sync_Notion_Name = 'to Auto-Sync'
NeedGCalUpdate_Notion_Name = 'NeedGCalUpdate'
GCalEventId_Notion_Name = 'GCal Event Id'
LastUpdatedTime_Notion_Name  = 'Last Updated Time'
Calendar_Notion_Name = 'Calendar'
Current_Calendar_Id_Notion_Name = 'Current Calendar Id'
Delete_Notion_Name = 'Delete from GCal?'
#######################################################################################
###               No additional user editing beyond this point is needed            ###
#######################################################################################

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
        print(f"\nsuccessful Authentication / Refresh Token\n")
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


###########################################################################
##### The Methods that we will use in this scipt are below
###########################################################################

# Main code
credentials = refresh_token()
service = build("calendar", "v3", credentials=credentials)
calendar = obtain_calendar(service)

###########################################################################
##### Part 1: Take Notion Events not on GCal and move them over to GCal
###########################################################################


## Note that we are only querying for events that are today or in the next week so the code can be efficient. 
## If you just want all Notion events to be on GCal, then you'll have to edit the query so it is only checking the 'On GCal?' property
# Get today's date
today = datetime.today()

# Calculate the first day of this month
this_month = datetime(today.year, today.month, 1)

# Format the date to match the format used in your code
this_month_str = this_month.strftime("%Y-%m-%dT%H:%M:%S.%f")

my_page = notion.databases.query(  #this query will return a dictionary that we will parse for information that we want
    **{
        "database_id": database_id, 
        "filter": {
            "and": [
                {
                    "property": On_GCal_Notion_Name, 
                    "checkbox":  {
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
                    "checkbox":  {
                        "equals": False
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

TaskNames = []
start_Dates = []
end_Times = []
Initiatives = []
ExtraInfo = []
URL_list = []
calEventIdList = []
CalendarList = []

no_new_updated = True
no_new_added = True
No_pages_modified = True

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

if len(resultList) > 0:
    # print(len(resultList))
    for i, el in enumerate(resultList):
        # 检查标题列表是否为空
        title_list = el['properties'][Task_Notion_Name]['title']
        # print(title_list)  # 打印 title_list，查看其內容
        
        # 处理 title_list 是空列表的情况
        if not title_list:
            # 如果 title_list 是空的，返回 true
            TaskNames.append("空標題")
            print("true")
            break 

        # 处理 title 列表有内容的情况
        title = title_list[0]['text']['content']
        # print(title)
        if title is None or title.isspace():
            TaskNames.append(title)
            print("true")
        else:
            print("false")
