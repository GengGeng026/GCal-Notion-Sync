import os
from dotenv import load_dotenv
from notion_client import Client
import pickle
import requests
import pytz
from pytz import timezone as pytz_timezone
from dateutil.parser import parse
from dateutil.tz import gettz, tzutc
from datetime import datetime, date, timedelta, timezone, time
from datetime import time as dt_time
import datetime as dt
import time as tm
import threading
from threading import Lock
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow
from oauthlib.oauth2 import BackendApplicationClient
from requests_oauthlib import OAuth2Session
from google.auth.exceptions import RefreshError
from google.auth.transport.requests import Request
from concurrent.futures import ThreadPoolExecutor, as_completed, CancelledError,TimeoutError
from queue import Queue
import logging
from collections import defaultdict
import copy
import traceback
import re


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
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")+"-04:00" #Change the last 5 characters to be representative of your timezone
     #^^ has to be adjusted for when daylight savings is different if your area observes it


DEFAULT_EVENT_START = 8 #8 would be 8 am. 16 would be 4 pm. Only whole numbers 

AllDayEventOption = 1 #0 if you want dates on your Notion dashboard to be treated as an all-day event
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
StartEnd_to_Overwrite_All_Notion_Name = 'StartEnd_to_Overwrite_All'
GCalEventId_Notion_Name = 'GCal Event Id'
LastUpdatedTime_Notion_Name  = 'Last Updated Time'
Calendar_Notion_Name = 'Calendar'
Current_Calendar_Id_Notion_Name = 'Current Calendar Id'
Delete_Notion_Name = 'Delete from GCal?'


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
formatted_left_parenthesis = format_string(' (', 'C2', bold=True)
formatted_right_parenthesis = format_string(')', 'C2', bold=True)
formatted_BOLD_italic = format_string('{}', bold=True, italic=True)
formatted_right_arrow = format_string(' ▸ ', 'C2', bold=True)
formatted_indicator = format_string('{}', 'C2', bold=True)
formatted_successful = format_string('Successful', 'C2', bold=True)
formatted_failed = format_string('Failed', 'C3', bold=True)
formatted_page_title = format_string('page_title', 'C1', bold=True)
formatted_start = format_string('Start', bold=True)
formatted_end = format_string('End', bold=True)
formatted_startend = format_string('StartEnd', bold=True)
formatted_condition_met = format_string('Condition Met', bold=True)
formatted_no = format_string('No', bold=True, italic=True)
formatted_has_time = format_string('has time', bold=True, italic=True)
formatted_changed = format_string('Changed', bold=True, italic=True)
formatted_initially_modified = format_string('initially Modified', bold=True, italic=True)
formatted_count = format_string('{}', 'C2', bold=True)
formatted_slash = format_string('/', 'C2', bold=True)
formatted_colon = format_string(':', 'C2', bold=True)
formatted_semicolon = format_string(';', 'C1', bold=True)
formatted_or = format_string('or', bold=True)
formatted_and = format_string('and', bold=True)
formatted_as = format_string('as', bold=True)
formatted_is = format_string('is', bold=True)
formatted_are = format_string('are', bold=True)
formatted_s = format_string('(s)', bold=True)
formatted_reset_default_setting = format_string('RESET accordingly Default Setting', 'C2', bold=True)
formatted_default_time = format_string('Default Time', 'C2', bold=True)
formatted_time_range = format_string('Time-Range', 'C2', bold=True)
formatted_explicitly_set = format_string('Explicitly Set', bold=True)
formatted_explicitly_set_0000 = format_string('Explicitly set to 00:00', bold=True)
formatted_alldaysevent = format_string('All', bold=True) + '-' + format_string('Day', bold=True) + format_string('(s)', 'C2', bold=True) + '-' + format_string('Event', bold=True)
formatted_alldayevent = format_string('All-Day-Event', bold=True)
formatted_daterange = format_string('Date', 'C2', bold=True) + '-' + format_string('Range', 'C2', bold=True)
formatted_alternate_alldayevent = format_string('Alternate All-Day-Event', 'C2', bold=True)
formatted_have_time = format_string('got Time', bold=True, italic=True)
formatted_have_single_date = format_string('got Single-Date', bold=True, italic=True)
formatted_single_date = format_string('Single-Date', 'C2', bold=True, italic=True)
formatted_no_time = format_string('No Time', 'C1', bold=True, italic=True)
formatted_is_filled_accordingly = format_string('is Filled accordingly', 'C2', bold=True)
formatted_is_filled_single_date = format_string('is Filled Single-Date', 'C2', bold=True)
formatted_overwritten = format_string('Overwritten', 'C2', bold=True)
formatted_done = format_string('Done', 'C2', bold=True)
formatted_Printing = format_string('Printing', 'C2', bold=True)
formatted_error = format_string('error', 'C3', bold=True)
formatted_plain_none = format_string('None', italic=True, less_visible=True)
formatted_plain_previous = format_string('Previous', italic=True, less_visible=True)
formatted_AFTER = format_string('AFTER', 'C1', bold=True, italic=True)
formatted_none = format_string('None', 'C1', bold=True, italic=True)
formatted_all_none = format_string('All None', 'C1', bold=True, italic=True)
formatted_modified = format_string('Modified', 'C2', bold=True)

#######################################################################################
###               No additional user editing beyond this point is needed            ###
#######################################################################################




# Declare total_dots as a global variable at the top of your script
total_dots = 0

def dynamic_counter_indicator(stop_event, message):
    dot_counter = 0
    total_dots = 0
    print(f"{BOLD}{COLORS['C2']}{message}{RESET}", end="", flush=True)
    while not stop_event.is_set():
        if dot_counter == 4:
            print("\r" + " " * (len(message) + total_dots + 15) + "\r", end="", flush=True)
            dot_counter = 0
        else:
            tm.sleep(0.15)
            print(".", end="", flush=True)
            dot_counter += 1
            total_dots += 1

stop_event = threading.Event()
thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event, "."))
thread.start()


# Set up logging
# 在正式部署前，將日誌級別設置為 INFO 或更高，這樣可以減少細節的輸出
logging.basicConfig(filename='app.log', filemode='w', format='%(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# Create a lock
token_lock = threading.Lock()

# Constants
GOOGLE_CALENDAR_CREDENTIALS_LOCATION = os.getenv("GOOGLE_CALENDAR_CREDENTIALS_LOCATION")
CLIENT_SECRET_FILE = os.getenv("GOOGLE_CALENDAR_CLI_SECRET_FILE")
SCOPES = ['https://www.googleapis.com/auth/calendar.readonly', 'https://www.googleapis.com/auth/calendar.events']
DEFAULT_CALENDAR_ID = 'primary'  # Replace with your Calendar ID

# Function to refresh token
def refresh_token():
    credentials = None
    if os.path.exists(GOOGLE_CALENDAR_CREDENTIALS_LOCATION):
        with open(GOOGLE_CALENDAR_CREDENTIALS_LOCATION, 'rb') as token:
            credentials = pickle.load(token)
    if not credentials or not credentials.valid:
        if credentials and credentials.expired and credentials.refresh_token:
            try:
                credentials.refresh(Request())
            except RefreshError:
                os.remove(GOOGLE_CALENDAR_CREDENTIALS_LOCATION)
                return refresh_token()
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRET_FILE, SCOPES)
            credentials = flow.run_local_server(port=0)
        with open(GOOGLE_CALENDAR_CREDENTIALS_LOCATION, 'wb') as token:
            pickle.dump(credentials, token)
        print(f"\n{formatted_successful} Authentication / Refresh Token\n")
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
    credentials = refresh_token()
    service = build("calendar", "v3", credentials=credentials)
    calendar = obtain_calendar(service)
finally:
    stop_event.set()
    thread.join()



###########################################################################
##### The Methods that we will use in this scipt are below
###########################################################################


######################################################################
#METHOD TO MAKE A CALENDAR EVENT DESCRIPTION

#This method can be edited as wanted. Whatever is returned from this method will be in the GCal event description 
#Whatever you change up, be sure to return a string 

def makeEventDescription(initiative, info):
    if initiative == '' and info == '':
        return ''
    elif info == "":
        return initiative
    elif initiative == '':
        return info
    else:
        return f'Initiative: {initiative} \n{info}'


######################################################################
#METHOD TO MAKE A TASK'S URL
#To make a url for the notion task, we have to take the id of the task and take away the hyphens from the string

def makeTaskURL(ending, urlRoot):
    # urlId = ending[0:8] + ending[9:13] + ending[14:18] + ending[19:23] + ending[24:]  #<--- super inefficient way to do things lol
    urlId = ending.replace('-', '')
    return urlRoot + urlId


######################################################################
#METHOD TO MAKE A CALENDAR EVENT


def makeCalEvent(eventName, eventDescription, eventStartTime, sourceURL, eventEndTime, calId):
 
    if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime == eventStartTime: #only startTime is given from the Notion Dashboard
        if AllDayEventOption == 1:
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(hours=DEFAULT_EVENT_START) ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes= DEFAULT_EVENT_LENGTH)
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
                }
            }
        else:
            eventEndTime = eventEndTime + timedelta(days=1) #gotta make it to 12AM the day after
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
                }
            }
    elif eventStartTime.hour == 0 and eventStartTime.minute ==  0 and eventEndTime.hour == 0 and eventEndTime.minute == 0 and eventStartTime != eventEndTime:
        
        eventEndTime = eventEndTime + timedelta(days=1) #gotta make it to 12AM the day after
        
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
            }
        }
    
    else: #just 2 datetimes passed in from the method call that are not at 12 AM
        if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime != eventStartTime: #Start on Notion is 12 am and end is also given on Notion 
            eventStartTime = eventStartTime #start will be 12 am
            eventEndTime = eventEndTime #end will be whenever specified
        elif eventStartTime.hour == 0 and eventStartTime.minute == 0: #if the datetime fed into this is only a date or is at 12 AM, then the event will fall under here
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(hours=DEFAULT_EVENT_START) ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes= DEFAULT_EVENT_LENGTH)  
        elif eventEndTime == eventStartTime: #this would meant that only 1 datetime was actually on the notion dashboard 
            eventStartTime = eventStartTime
            eventEndTime = eventStartTime + timedelta(minutes= DEFAULT_EVENT_LENGTH) 
        else: #if you give a specific start time to the event
            eventStartTime = eventStartTime
            eventEndTime = eventEndTime
        
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
            }
        }    
    print('Adding this event to calendar: ', eventName)

    print(event)
    x = service.events().insert(calendarId=calId, body=event).execute()
    return x['id']


######################################################################
#METHOD TO UPDATE A CALENDAR EVENT

def upDateCalEvent(eventName, eventDescription, eventStartTime, sourceURL, eventId, eventEndTime, currentCalId, CalId):

    if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime == eventStartTime:  #you're given a single date
        if AllDayEventOption == 1:
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(hours=DEFAULT_EVENT_START) ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes= DEFAULT_EVENT_LENGTH)
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
                }
            }
        else:
            eventEndTime = eventEndTime + timedelta(days=1) #gotta make it to 12AM the day after
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
                }
            }
    elif eventStartTime.hour == 0 and eventStartTime.minute ==  0 and eventEndTime.hour == 0 and eventEndTime.minute == 0 and eventStartTime != eventEndTime: #it's a multiple day event
        
        eventEndTime = eventEndTime + timedelta(days=1) #gotta make it to 12AM the day after
        
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
            }
        }
    
    else: #just 2 datetimes passed in 
        if eventStartTime.hour == 0 and eventStartTime.minute == 0 and eventEndTime != eventStartTime: #Start on Notion is 12 am and end is also given on Notion 
            eventStartTime = eventStartTime #start will be 12 am
            eventEndTime = eventEndTime #end will be whenever specified
        elif eventStartTime.hour == 0 and eventStartTime.minute == 0: #if the datetime fed into this is only a date or is at 12 AM, then the event will fall under here
            eventStartTime = datetime.combine(eventStartTime, datetime.min.time()) + timedelta(hours=DEFAULT_EVENT_START) ##make the events pop up at 8 am instead of 12 am
            eventEndTime = eventStartTime + timedelta(minutes= DEFAULT_EVENT_LENGTH)  
        elif eventEndTime == eventStartTime: #this would meant that only 1 datetime was actually on the notion dashboard 
            eventStartTime = eventStartTime
            eventEndTime = eventStartTime + timedelta(minutes= DEFAULT_EVENT_LENGTH) 
        else: #if you give a specific start time to the event
            eventStartTime = eventStartTime
            eventEndTime = eventEndTime 
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
            }
        }    
    print('Updating this event to calendar: ', eventName)

    if currentCalId == CalId:
        x = service.events().update(calendarId=CalId, eventId = eventId, body=event).execute()

    else: #When we have to move the event to a new calendar. We must move the event over to the new calendar and then update the information on the event
        print('Event ' + eventId)
        print('CurrentCal ' + currentCalId)
        print('NewCal ' + CalId)
        x= service.events().move(calendarId= currentCalId , eventId= eventId, destination=CalId).execute()
        print('New event id: ' + x['id'])
        x = service.events().update(calendarId=CalId, eventId = eventId, body=event).execute()

    return x['id']


###########################################################################
##### Part 0.5: Synchronize Date Properties in the Same Notion Database
###########################################################################

###################################################################################################

# Initialize a flag to False
no_pages_operated_A = False
no_pages_operated_B = False

# Print new line at the beginning of logging
print("\n")

# Section A
# Filter Only Pages where 'to Auto-Sync’ is Checked and within current month
# Create a thread-local variable
local_data = threading.local()

# Create a lock for no_pages_operated_A
no_pages_operated_A_lock = threading.Lock()


formatted_italic = f"{ITALIC}{{}}{RESET}"
formatted_task = f"{BOLD}Task{RESET}"
formatted_to_auto_sync = f"{BOLD}{COLORS['C2']}to Auto-Sync{RESET}"
formatted_count = f"{BOLD}{COLORS['C2']}{{}}{RESET}"
formatted_within_current_month = f"{BOLD}{ITALIC}within current month{RESET}"
formatted_colon = f"{BOLD}{COLORS['C2']}:{RESET}"

# Get the current month and year
now = datetime.now()
current_month = now.month
current_year = now.year

# Calculate date range
start_date = datetime(current_year, current_month, 1).isoformat()
end_date = datetime(current_year, current_month + 1, 1).isoformat() if current_month < 12 else datetime(current_year + 1, 1, 1).isoformat()

# Define query parameters
query_params = {
    "database_id": database_id, 
    "filter": {
        "and": [
            {
                "property": "to Auto-Sync",
                "checkbox":  {
                    "equals": True
                }
            },
            {
                "property": "Created",
                "date": {
                    "after": start_date,
                    "before": end_date
                }
            }
        ]
    }
}

# Query the pages
my_page = notion.databases.query(**query_params)

# Store the results in a variable
filtered_pages = my_page['results']

# Sort the pages by group and ID
filtered_pages.sort(key=lambda page: (page.get('group', ''), page['properties']['Task Name']['title'][0]['text']['content']))

# Print the Task_Notion_Name and ID of the pages where 'to Auto-Sync' is checked and 'Created' is within current month
for page in filtered_pages:
    page['group'] = page['properties']['Task Name']['title'][0]['text']['content']
    print(f"{formatted_task} {formatted_colon} {formatted_italic.format(page['properties']['Task Name']['title'][0]['text']['content'])}")

if len(filtered_pages) > 0:
    print(f"\nTotal Pages set to {formatted_to_auto_sync} {formatted_within_current_month} {formatted_colon} {formatted_count.format(len(filtered_pages))}\n")

print('\n' + '-' * 70 + '\n\n')

# You can now use the 'filtered_pages' variable in the next section of your code


###################################################################################################
# Section B
# Definitions

# Re-initialize the flag to False before Section B
no_pages_operated_B = False

# Define a function to print the "Printing" message and dots
def dynamic_counter_indicator(stop_event):
    dot_counter = 0
    total_dots = 0  # New variable to keep track of the total number of dots
    formatted_Printing = f"{BOLD}{COLORS['C2']}Printing{RESET}"
    
    print(f"{formatted_Printing}", end="", flush=True)
    while not stop_event.is_set():
        tm.sleep(0.1)  # Wait for 0.3 second
        print(f"{formatted_dot}", end="", flush=True)  # Print the colored dot
        dot_counter += 1
        total_dots += 1  # Increment the total number of dots

        # If the counter reaches 4, reset it and erase the dots
        if dot_counter == 4:
            terminal_width = os.get_terminal_size().columns  # Get the width of the terminal
            print("\r" + " " * min(len(f"{formatted_Printing}") + total_dots + 10, terminal_width) + "\r", end="", flush=True)  # Clear the line and print spaces
            dot_counter = 0
            if stop_event.is_set():  # Check if stop_event is set immediately after resetting the dot_counter
                break
    tm.sleep(0.1)  # Add a small delay
    
# Create a stop event
stop_event = threading.Event()

# Start the separate thread
thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event,))
thread.start()


def handle_none(value):
    return None if value is None else value

def handle_list(value):
    return value[0] if isinstance(value, list) else value

def format_datetime(dateTimeValue, time_format='24'):
    if isinstance(dateTimeValue, str):
        dateTimeValue = parse_datetime(dateTimeValue)
    if time_format == '24':
        formatted_time = dateTimeValue.strftime('%H:%M')
        if formatted_time[:2] != '00':
            formatted_time = formatted_time.lstrip('0')
    else:
        formatted_time = dateTimeValue.strftime('%I:%M')
        if formatted_time[:2] != '00':
            formatted_time = formatted_time.lstrip('0')
    return dateTimeValue.strftime('%b %d, %Y  ').replace(' 0', ' ') + formatted_time

def format_time(old_value, new_value):
    # Convert old_value and new_value to datetime objects if they are strings
    if isinstance(old_value, str):
        old_value = parse_datetime(old_value)
    if isinstance(new_value, str):
        new_value = parse_datetime(new_value)

    # Check if old_value and new_value are not None
    if old_value is not None and new_value is not None:
        # Always use format_datetime for the old_value
        old_format = format_datetime(old_value)
        
        # If the date is the same, only format the time for the new_value
        if old_value.date() == new_value.date():
            new_format = new_value.strftime('%I:%M').lstrip('0')
        else:
            new_format = format_datetime(new_value)
    else:
        old_format = new_format = 'None'

    return old_format, new_format

def parse_datetime(value):
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):  # Handle datetime.date objects
        return datetime.combine(value, datetime.min.time())
    if isinstance(value, tuple):
        return tuple(parse_datetime(v) for v in value)
    try:
        return datetime.strptime(value, '%b %d, %Y')
    except ValueError:
        return datetime.fromisoformat(value)

# Specific tool in a toolbox, designed for a specific task
# Only deals with time objects, not full datetime objects
# if you have a time (like "23:59:59") and you want to format it into a specific string format that Notion can understand
def TimeIntoNotionFormat(dateTimeValue, date_for_comparison=None):
    originalDateTimeValue = dateTimeValue  # Store the original value

    dateTimeValue = handle_none(dateTimeValue)
    dateTimeValue = handle_list(dateTimeValue)

    if isinstance(dateTimeValue, str):
        dateTimeValue = parse_datetime(dateTimeValue)
    if isinstance(dateTimeValue, tuple):
        return tuple(TimeIntoNotionFormat(v, date_for_comparison) for v in dateTimeValue)

    if date_for_comparison is not None:
        if isinstance(date_for_comparison, str):
            date_for_comparison = parse_datetime(date_for_comparison)

        if dateTimeValue.date() == date_for_comparison.date():
            _, new_format = format_time(originalDateTimeValue, dateTimeValue)
            return new_format

    return format_datetime(dateTimeValue)

# This function's like a Swiss Army knife
# If you have a full date and time (like "2022-12-31 23:59:59") and you want to format it into a specific string format that Notion can understand
def DateTimeIntoNotionFormat(dateTimeValue, isEndDate=False, startDate=None, for_notion=False, oldDateTimeValue=None, isOldFormat=False, date_only=False, plus_time=False, time_format='24', show_midnight=False):
    dateTimeValue = handle_none(dateTimeValue)
    startDate = handle_none(startDate)
    oldDateTimeValue = handle_none(oldDateTimeValue)
    
    dateTimeValue = handle_list(dateTimeValue)
    startDate = handle_list(startDate)
    oldDateTimeValue = handle_list(oldDateTimeValue)

    if not dateTimeValue or dateTimeValue == "None":
        return 'None'
    if not isinstance(dateTimeValue, datetime):
        dateTimeValue = parse_datetime(dateTimeValue)
    if isinstance(dateTimeValue, tuple):
        return tuple(DateTimeIntoNotionFormat(v, isEndDate, startDate, for_notion, oldDateTimeValue, isOldFormat, date_only, plus_time) for v in dateTimeValue)

    # Format the day separately to add an extra space before single-digit days.
    day = str(dateTimeValue.day)
    formatted_date = dateTimeValue.strftime('%b') + ' ' + day + dateTimeValue.strftime(', %Y')

    if date_only or (dateTimeValue.time() == time(0) and not show_midnight):  # If time part is midnight
        return formatted_date
    
    if plus_time:
        if time_format == '24':
            formatted_time = dateTimeValue.strftime('%H:%M')
            if formatted_time != '00:00':
                formatted_time = ' ' + formatted_time.lstrip('0') if 1 <= dateTimeValue.hour < 10 else formatted_time
            return formatted_date + '  ' + formatted_time
        else:
            formatted_time = dateTimeValue.strftime('%I:%M %p')
            formatted_time = ' ' + formatted_time.lstrip('0') if 1 <= dateTimeValue.hour < 10 else formatted_time
            return formatted_date + '  ' + formatted_time
    if for_notion:
        return dateTimeValue.isoformat()
    elif isEndDate and startDate:
        if dateTimeValue.date() == startDate.date() and (oldDateTimeValue is None or dateTimeValue.date() == oldDateTimeValue.date()):
            return format_datetime(dateTimeValue, time_format)
        else:
            return format_datetime(dateTimeValue, time_format)
    else:
        return format_datetime(dateTimeValue, time_format)

def parse_date(date_string, formats):
    if isinstance(date_string, datetime):
        return date_string
    for fmt in formats:
        try:
            return datetime.strptime(date_string, fmt)
        except ValueError:
            pass
    raise ValueError(f"No valid date format found for {date_string}")

def format_date(date, as_date=False, for_notion=False, remove_zero_time=False):
    if not date:
        return None
    if as_date:
        return date.strftime('%Y-%m-%d')
    if for_notion:
        return DateTimeIntoNotionFormat(date, for_notion=True)
    formatted_date = date.strftime('%Y-%m-%dT%H:%M:%S%z')
    if remove_zero_time and formatted_date.endswith('T00:00:00+0000'):
        formatted_date = formatted_date[:-15]  # Remove the time part if it's 'T00:00:00+0000'
    return formatted_date

# This function's like a calendar
# Only deals with dates, not times or full datetime objects
# If you have a date (like "2022-12-31") and you want to format it into a specific string format that Notion can understand
def DateIntoNotionFormat(date_string):
    date_string = handle_none(date_string)
    date_string = handle_list(date_string)

    if date_string == "None":
        return date_string

    date = parse_date(date_string, ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%d'])
    return format_date(date)

def apply_date_rules(page):
    for prop in ['Previous Start', 'Previous End', 'Start', 'End', 'StartEnd', 'Last Updated Time']:
        if prop in page:
            page[prop] = convert_to_timezone(page[prop], timezone)

    if 'Start' in page:
        page['Start'] = handle_list(page['Start'])
        page['Start'] = set_default_time_range(page)
    if 'End' in page:
        page['End'] = handle_list(page['End'])
        page['End'] = set_default_time_range(page)

    if 'StartEnd' in page and (isinstance(page['StartEnd'], datetime) or (isinstance(page['StartEnd'], list) and not page['StartEnd'][0].time())):
        page['StartEnd'] = 'All-Day-Event'

    if 'Start' in page and 'Previous Start' in page:
        page['Previous Start'] = page['Start']
    if 'End' in page and 'Previous End' in page:
        page['Previous End'] = page['End']

    return page

def has_time(date_string):
    return 'T' in date_string



def get_default_times():
    today = datetime.now()
    default_start_time = today.replace(hour=DEFAULT_EVENT_START, minute=0)
    default_end_time = today.replace(hour=DEFAULT_EVENT_START + 1, minute=0)
    return default_start_time, default_end_time

def set_default_time_range(page, timezone):
    if all(page.get(key) is None for key in ['start', 'end', 'start_end']):
        start = datetime.now(pytz_timezone(timezone)).replace(hour=DEFAULT_EVENT_START, minute=0, second=0, microsecond=0)
        end = start + timedelta(minutes=DEFAULT_EVENT_LENGTH)
        page.update({'start': start, 'end': end, 'start_end': (start, end)})

    page['start'], page['end'], page['start_end'] = convert_times(page['start'], page['end'], page['start_end'], lambda dt: dt.astimezone(pytz_timezone(timezone)))
    page['start'], page['end'], page['start_end'] = convert_times(page['start'], page['end'], page['start_end'], lambda dt: dt.isoformat())

    # Convert start and end back to datetime objects
    for key in ['start', 'end']:
        if isinstance(page[key], list):
            page[key] = page[key][0]  # take the first element of the list
        if isinstance(page[key], str):
            page[key] = parse(page[key])

    update_page(page, page['start'], page['end'], page['start_end'])

    return page

def handle_single_date(page):
    start, end, start_end = parse_times(page)

    # Situation 1
    if start and not end and not start_end:
        end = start + timedelta(hours=1)
        start_end = (start, end)
    elif end and not start and not start_end:
        start = end - timedelta(hours=1)
        start_end = (start, end)
    elif start_end and not start and not end and start_end[0].time() != time(0, 0):
        end = start_end[0] + timedelta(hours=1)
        start_end = (start_end[0], end)

    # Situation 2
    if (start and not start.time() and not start_end) or (end and not end.time() and not start_end):
        start = start.replace(hour=8, minute=0) if start else None
        end = end.replace(hour=9, minute=0) if end else None
        start_end = (start, end)

    # Situation 3
    if start_end and not start_end[0].time() and not start and not end:
        start = start_end[0]
        end = start_end[1]

    start, end, start_end = convert_times(start, end, start_end, lambda dt: dt.astimezone(pytz_timezone(timezone)))
    start, end, start_end = convert_times(start, end, start_end, lambda dt: dt.isoformat())
    update_page(page, start, end, start_end)

def handle_date_range(page):
    start, end, start_end = parse_times(page)

    # Situation 4
    if start_end and start_end[0].time() != time(0, 0) and start_end[1].time() != time(0, 0) and not start and not end:
        start_end = (start_end[0].replace(hour=8, minute=0), start_end[1].replace(hour=9, minute=0))

    # Requirement c
    if start_end and start_end[0].time() == time(0, 0) and start_end[1].time() == time(0, 0):
        start = start_end[0]
        end = start_end[1]

    start, end, start_end = convert_times(start, end, start_end, lambda dt: dt.astimezone(pytz_timezone(timezone)))
    start, end, start_end = convert_times(start, end, start_end, lambda dt: dt.isoformat())
    update_page(page, start, end, start_end)

def set_default_setting(page):
    # Get default start and end times
    default_start_time, default_end_time = get_default_times()

    # Get the start, end, and start_end times using get_date function
    start, end, start_end = parse_times(page)

    # a. When Date Property is Empty, Set to Default Time and Time Range:
    if start is None and end is None and start_end is None:
        start = default_start_time
        end = default_end_time
        start_end = (default_start_time, default_end_time)

    # b. When Date Property has Single-Date with or without Time, Set to Default Time or Date Range or Time Range:
    handle_single_date(page)

    # c. When Date Property has Date-Range with or without Time, Set to Default Time or Date Range or Time Range:
    handle_date_range(page)

    # Convert the datetime objects to the 'Asia/Kuala_Lumpur' timezone
    start, end, start_end = convert_times(start, end, start_end, lambda dt: dt.astimezone(pytz_timezone(timezone)))

    # Convert the datetime objects back to strings in the correct format
    start, end, start_end = convert_times(start, end, start_end, lambda dt: dt.isoformat())

    # Update the page dictionary
    update_page(page, start, end, start_end)


# Initialize an empty set to keep track of processed pages
processed_pages = set()

# Create a thread-local variable
local_data = threading.local()

# Initialize your lock
lock = Lock()

# Create a lock for no_pages_operated_B
no_pages_operated_B_lock = threading.Lock()

# Create a Queue to store the return values
return_values = Queue()

def convert_to_timezone(dt, tz):
    tz = pytz_timezone(tz)
    return dt.astimezone(tz) if dt else datetime.now(tz)

def convert_times(start, end, start_end, convert_func):
    convert = lambda dt: convert_func(dt)
    start = convert(start)
    end = convert(end)
    start_end = tuple(convert(dt) for dt in start_end) if start_end else None
    return start, end, start_end

def get_page_title(page):
    return page['properties']['Task Name']['title'][0]['text']['content']

def parse_datetime_with_optional_fractional_seconds(date_string):
    dt = parse(date_string)
    if dt.tzinfo is None:
        dt = dt.replace(hour=DEFAULT_EVENT_START)
        dt = timezone(timezone).localize(dt)
    return dt

def print_time_message(date, time_set, property_name, page_id):
    time = date.time() if date else '00:00'
    status = "Explicitly set" if time_set else "not set, Defaulting to"
    print(f"The time for {property_name} of page {page_id} was {status} {time}")

def parse_times(page):
    start, start_time_set = get_date_from_page(page, 'Start')
    end, end_time_set = get_date_from_page(page, 'End')
    start_end_prop = page['properties'].get('StartEnd') if page and 'properties' in page else None
    start_end = (get_date_from_page(page, 'StartEnd[0]'), get_date_from_page(page, 'StartEnd[1]')) if start_end_prop else None
    for date, time_set, property_name in [(start, start_time_set, 'Start'), (end, end_time_set, 'End')]:
        print_time_message(date, time_set, property_name, page['id'])
    return start, end, start_end

def update_page_properties(notion, page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=False, single_date=False, update_all=True, keep_midnight=False, remove_start_end_midnight=False):
    # Convert 'start' and 'end' into datetime objects if they are not already
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, datetime.min.time())
    if end is not None and isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, datetime.min.time())

    # Convert 'start_end' into a list of datetime objects if it is not already
    if isinstance(start_end, (list, tuple)) and len(start_end) == 2:
        start_end = [datetime.combine(d, datetime.min.time()) if isinstance(d, date) and not isinstance(d, datetime) else d for d in start_end]
        if start_end[1] is None:
            start_end[1] = start_end[0]

    # Check if start_end is a list of one datetime object, if so, duplicate it
    if isinstance(start_end, (list, tuple)) and len(start_end) == 1 and isinstance(start_end[0], datetime):
        start_end.append(start_end[0])

    # Check if start and end are datetime objects
    if not isinstance(start, datetime) or not isinstance(end, datetime):
        print(f"Error: start or end is not a datetime object. They are: {start}, {end}")
        return

    # Check if start_end is a list or tuple of two datetime objects
    if not isinstance(start_end, (list, tuple)) or len(start_end) != 2 or not all(isinstance(date, datetime) for date in start_end):
        print(f"Error: start_end is not a list or tuple of two datetime objects. It is: {start_end}")
        return

    def format_date_time(date, keep_midnight=False, remove_midnight=False):
        if isinstance(date, datetime) and date.time() != time(0):  # If time part is not midnight
            return date.isoformat()  # Format as datetime string with time and timezone
        elif isinstance(date, datetime):  # If time part is midnight
            if keep_midnight and not remove_midnight:  # If keep_midnight is True and remove_midnight is False
                return date.isoformat()  # Format as datetime string with time and timezone
            else:  # If keep_midnight is False or remove_midnight is True
                return date.date().isoformat()  # Format as date string without time and timezone
        else:
            return date  # Return the date object as is
        
    # If the start and end dates are the same, set 'StartEnd' as a single date
    if start_end[0] == start_end[1]:
        start_end = (start_end[0], None)

    # Check if only start or end is overwritten by start_end_start or start_end_end respectively
    keep_start_midnight = start.time() == time(0, 0) and end.time() != time(0, 0)
    keep_end_midnight = end.time() == time(0, 0) and start.time() != time(0, 0)

    start_date = format_date_time(start, keep_midnight=keep_start_midnight, remove_midnight=remove_start_end_midnight)
    end_date = format_date_time(end, keep_midnight=keep_end_midnight, remove_midnight=remove_start_end_midnight)

    start_end_start_date = format_date_time(start_end[0])
    start_end_end_date = format_date_time(start_end[1]) if start_end[1] is not None else None

    # Prepare the properties to update
    properties_to_update = {
        Date_Notion_Name: {
            'date': {
                'start': start_end_start_date,
                'end': start_end_end_date
            }
        }
    }

    if update_all:
        properties_to_update.update({
            Start_Notion_Name: {
                'date': {
                    'start': start_date,
                    'end': None
                }
            },
            End_Notion_Name: {
                'date': {
                    'start': end_date,
                    'end': None
                }
            }
        })

    notion.pages.update(
        page_id=page['id'],
        properties=properties_to_update
    )

def update_previous_dates(page, start, end, start_end, as_date=False, keep_midnight=False):
    # Convert 'start' and 'end' into datetime objects if they are not already
    if isinstance(start, date) and not isinstance(start, datetime):
        start = datetime.combine(start, datetime.min.time())
    if end is not None and isinstance(end, date) and not isinstance(end, datetime):
        end = datetime.combine(end, datetime.min.time())

    # Parse 'start' and 'end' values of start_end into datetime objects
    if isinstance(start_end, dict):
        start_end = [parse(start_end['start']), parse(start_end['end'])]
    elif isinstance(start_end, tuple):
        if all(isinstance(date, datetime) for date in start_end):
            start_end = [start_end[0], start_end[1]]
        else:
            temp_start_end = []
            if start_end[0] is not None:
                temp_start_end.append(parse(str(start_end[0])))
            else:
                temp_start_end.append(None)  # or any default value you want to assign

            if len(start_end) > 1 and start_end[1] is not None:
                temp_start_end.append(parse(str(start_end[1])))
            else:
                temp_start_end.append(temp_start_end[0])  # default to the first value

            start_end = temp_start_end

    # If end is None, assign it the value of start
    if end is None:
        end = start

    # Check if start, end, and start_end are datetime objects
    if not isinstance(start, datetime) or not isinstance(end, datetime) or not isinstance(start_end, (list, tuple)) or len(start_end) != 2 or not all(isinstance(date, datetime) for date in start_end):
        print(f"Error: start, end, or start_end is not a datetime object. They are: {start}, {end}, {start_end}")
        return

    # Function to format datetime objects
    def format_date_time(date, keep_midnight=False):
        if date.time() != time(0):  # If time part is not midnight
            return date.isoformat()  # Format as datetime string with time and timezone
        else:  # If time part is midnight
            if keep_midnight:  # If keep_midnight is True
                return date.isoformat()  # Format as datetime string with time and timezone
            else:  # If keep_midnight is False
                return date.strftime('%Y-%m-%d')  # Format as date string without time and timezone

    # Check if only start or end is overwritten by start_end_start or start_end_end respectively
    keep_start_midnight = start.time() != time(0, 0) or (start.time() == time(0, 0) and end.time() != time(0, 0))
    keep_end_midnight = end.time() != time(0, 0) or (end.time() == time(0, 0) and start.time() != time(0, 0))

    # Format the datetime objects
    start_str = format_date_time(start, keep_midnight=keep_start_midnight)
    end_str = format_date_time(end, keep_midnight=keep_end_midnight) if end is not None else None

    properties = {
        'Previous Start': {
            'date': {
                'start': start_str,
            }
        },
        'Previous End': {
            'date': {
                'start': end_str,
            }
        }
    }


    # Check if start and end are different dates and either start or end is not midnight, and start_end is a different time range
    if start.date() != end.date() and (start.time() != datetime.min.time() or end.time() != datetime.min.time()):
        # Overwrite start_end with start and end
        start_end = [start, end]

        # Update 'Previous Start' and 'Previous End' properties
        properties['Previous Start']['date']['start'] = format_date_time(start, keep_midnight=True)
        properties['Previous End']['date']['start'] = format_date_time(end, keep_midnight=True) if end is not None else None

    notion.pages.update(
        page_id=page['id'],
        properties=properties
    )

def update_page(page, start, end, start_end):
    # Check the type of 'start_end'
    if isinstance(start_end, dict):
        # If 'start_end' is a dictionary, access its elements using the keys 'start' and 'end'
        start_end_start = start_end['start']
        start_end_end = start_end['end']
    elif isinstance(start_end, (list, tuple)) and len(start_end) == 2:
        # If 'start_end' is a list or tuple, access its elements using indices
        start_end_start = start_end[0]
        start_end_end = start_end[1]
    else:
        # If 'start_end' is neither a dictionary nor a list/tuple of length 2, raise an error
        raise ValueError("'start_end' must be a dictionary with keys 'start' and 'end', or a list/tuple of length 2")

def update_result(result, page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value=None, new_end_value=None):
    result.update({
        'page_id': page['id'],
        'page_title': page_title,
        'original_start': original_start,
        'original_end': original_end,
        'start': start,
        'end': end,
        'start_end': start_end,
        'prev_start': prev_start,
        'prev_end': prev_end,
        'prev_start_value': prev_start_value,
        'prev_end_value': prev_end_value,
        'new_start_value': new_start_value,
        'new_end_value': new_end_value,
    })
    return result

def get_date_from_page(page, property_name, parse_func=None):
    # Retrieve the property
    prop = page['properties'].get(property_name) if page and 'properties' in page else None

    # Retrieve the date if the property and its 'date' sub-property exist
    date_string = prop and prop.get('date') and prop.get('date').get('start')

    # Convert the date string into a datetime object
    if date_string:
        date = parse_func(date_string) if parse_func else parse(date_string)
        time_set = has_time(date_string)
    else:
        date = None
        time_set = False

    return date, time_set


def check_list(lst):
    return tuple(lst) if isinstance(lst, list) and len(lst) >= 2 else (None, None)


def update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight=False, keep_end_midnight=False, keep_midnight=False):
    
    if prev_start is not None and prev_end is not None:
        prev_start = prev_start.strftime('%Y-%m-%d %H:%M:%S%z')
        prev_end = prev_end.strftime('%Y-%m-%d %H:%M:%S%z')

    start_end = check_list([start, end])

    if not isinstance(start_end, tuple) or len(start_end) != 2:
        start_end = (start, end)
    if start_end == (None, None):
        raise ValueError("Invalid start and end dates")

    with lock:
        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)

    if start_end is not None:
        with lock:
            counts['count_alldayevent'] += 1
            result['total_pages_modified'] = calculate_total(counts)

    with lock:
        update_page(local_data.page, start, end, start_end)

    with lock:
        update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=True, single_date=True, keep_midnight=keep_midnight)
        
    if start is not None and end is not None:
        with lock:
            update_previous_dates(local_data.page, start.date(), end.date(), start_end, as_date=True)
    elif start is not None and end is None:
        with lock:
            update_previous_dates(local_data.page, start.date(), None, start_end, as_date=True)

    if start_end_value is None:
        with lock:
            result['details']['set_alldayevent_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], start_end_value, result['start_end'])

    details['prev_start'] = prev_start
    details['prev_end'] = prev_end

    # Update the start and end values in the result dictionary
    result['start'] = start
    result['end'] = end

    return result, details, start, end


def process_pages_condition_A(page, counts, details, lock, processed_pages, return_values):

    # Initialize your result dictionary
    result = {
        'counts': {
            'count_default_time_range': 0,
            'count_auto_default_setting': 0,
            'count_alternate_alldayevent_start': 0,
            'count_alldayevent': 0,
            'count_pages_filled': 0,
            'count_pages_single_dates': 0,
            'count_pages_overwritten': 0,
            # Add more counts here as needed
        },
        'details':{
            'set_Default_details': {},
            'auto_default_setting_details': {},
            'set_Alternate_alldayevent_start_details': {},
            'set_alldayevent_details': {},
            'pages_filled_details': {},
            'pages_overwritten_details': {},
            'pages_single_dates_details': {},
        },
        'page_id': None,
        'page_title': None,
        'original_start': None,
        'original_end': None,
        'start': None,
        'end': None,
        'start_end': None,
        'prev_start': None,
        'prev_end': None,
        'prev_start_value': None,
        'prev_end_value': None,
        'new_start_value': None,
        'new_end_value': None,
        'total_pages_modified': 0
    }
    
    # Each thread will have its own 'page' dictionary
    local_data.page = dict(page)  # Create a new 'page' dictionary for each iteration
    
    # Retrieve the page id
    page_id = local_data.page['id']
    result['page_id'] = page_id  # Add this line
    
    with lock:
        if page_id in processed_pages:
            # If the page has already been processed, skip it
            return result, processed_pages
        else:
            # If the page has not been processed, add it to the set of processed pages
            processed_pages.add(page_id)

    with no_pages_operated_B_lock:
        global no_pages_operated_B
    
    # Retrieve the page id
    page_id = local_data.page['id']

    # Add the page_id to the result dictionary
    result['page_id'] = page_id
    
    # Retrieve the previous start and end properties
    prev_start, _ = get_date_from_page(local_data.page, 'Previous Start')

    prev_end, _ = get_date_from_page(local_data.page, 'Previous End')

    # Retrieve the page title
    page_title = local_data.page['properties']['Task Name']['title'][0]['text']['content']

    # Retrieve the 'Need GCal Update' property
    try:
        StartEnd_to_Overwrite_All = local_data.page['properties'][StartEnd_to_Overwrite_All_Notion_Name]['formula']['boolean']
    except KeyError:
        print(f"The property {StartEnd_to_Overwrite_All_Notion_Name} does not exist or is not a boolean formula.")
        StartEnd_to_Overwrite_All = None

    # Reset the 'start', 'end', and 'start_end' fields of the 'page' dictionary
    local_data.page['start'] = None
    local_data.page['end'] = None
    local_data.page['start_end'] = None

    # Initialize original_start and original_end
    original_start, original_end = None, None

    # Initialize 'start_end_value' at the start of the loop
    start_end_value = None

    # Initialize prev_start_value, prev_end_value, new_start_value, and new_end_value
    prev_start_value = None
    prev_end_value = None
    new_start_value = None
    new_end_value = None

    # Retrieve the start, end, and start_end properties
    start, _ = get_date_from_page(local_data.page, 'Start')
    end, _ = get_date_from_page(local_data.page, 'End')
    start_end, _ = get_date_from_page(local_data.page, 'StartEnd')


    # Convert 'start' and 'end' values to Kuala Lumpur timezone
    if isinstance(start, datetime):
        start = start.astimezone(pytz.timezone('Asia/Kuala_Lumpur'))
        # Update 'start' value in the page dictionary
        local_data.page['start'] = start.isoformat()

    if isinstance(end, datetime):
        end = end.astimezone(pytz.timezone('Asia/Kuala_Lumpur'))
        # Update 'end' value in the page dictionary
        local_data.page['end'] = end.isoformat()
    
    # Use a re-entrant lock
    lock = threading.RLock()
    
    # MASTER CONDITION A : StartEnd is always None
    if start_end is None:
        
        # Sub-condition 1 under MASTER CONDITION A
        # Defaulting All from None to 8:00 AM to 9:00 AM
        if start is None and end is None:
            
            # Store the original values of 'start' and 'end'
            original_start, original_end = start, end
            page = set_default_time_range(local_data.page, timezone)

            # Get the new values of 'start' and 'end'
            with lock:
                if local_data.page is not None:
                    start = local_data.page.get('start')
                else:
                    start = None  # or some default value
                if local_data.page is not None:
                    end = local_data.page.get('end')
                else:
                    end = None  # or some default value
                if local_data.page is not None:
                    start_end = local_data.page.get('start_end')
                else:
                    start_end = None  # or some default value

            # Assuming start and end are defined somewhere else in your code
            start_end = check_list([start, end])


            # Update 'start', 'end', and 'start_end' in the 'result' dictionary
            result = update_result(result, local_data.page, page_title, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)

            # Increment the count of pages set to default time range
            if start_end is not None:
                with lock:
                    counts['count_default_time_range'] += 1
                

            # Only add details to the list if 'StartEnd' was None before the update
            if start_end_value is None:
                with lock:
                    result['details']['set_Default_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], start_end_value, result['start_end'])
                

            # Update the page in the Notion database
            if start <= end:
                with lock:
                    update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end)
                    update_previous_dates(local_data.page, start, end, start_end)

                    # Increment the count of pages set to default time range
                    counts['count_default_time_range'] += 1
                    
                    # Increment total_pages_modified whenever a page is modified
                    result['total_pages_modified'] = calculate_total(counts)
                    
                return result, counts, details, processed_pages, page['id']
            
            else:
                print(f"Skipping page '{local_data.page['properties']['Task Name']['title'][0]['plain_text']}' because the start date is {formatted_AFTER} the end date")

        # Sub-condition 2 under MASTER CONDITION A
        # Alternative to create All-Day-Event from Notion
        elif start is not None and end is None:

            # Store the original values of 'start' and 'end'
            original_start = start
            original_end = end

            # Check if 'Start' and 'End' have a Single-Date without a time component
            if has_time(local_data.page['properties']['Start']['date']['start']):

                if start.time() == datetime.min.time():
                    end = start = start

                    # Assuming start and end are defined somewhere else in your code
                    start_end = check_list([start, end])

                    # Ensure start_end is a tuple of two datetime objects
                    if not isinstance(start_end, tuple) or len(start_end) != 2:
                        start_end = (start, start)
                    if start_end == (None, None):
                        raise ValueError("Invalid start and end dates")
                    
                    with lock:
                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)
                        
                    if start_end is not None:
                        with lock:
                            counts['count_alternate_alldayevent_start'] += 1
                            result['total_pages_modified'] = calculate_total(counts)

                    with lock:
                        update_page(local_data.page, start, end, start_end)

                    with lock:
                        update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=True, single_date=True)

                    if start is not None and end is not None:
                        with lock:
                            update_previous_dates(local_data.page, start.date(), end.date(), start_end, as_date=True)
                    elif start is not None and end is None:
                        with lock:
                            update_previous_dates(local_data.page, start.date(), None, start_end, as_date=True)

                    if start_end_value is None:
                        with lock:
                            result['details']['set_Alternate_alldayevent_start_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], start_end_value, result['start_end'])

            else:
                original_start = copy.deepcopy(start)
                original_end = copy.deepcopy(end)
                original_start_end = copy.deepcopy(start_end)
                
                gmt8 = pytz.timezone('Asia/Kuala_Lumpur')
                start = datetime.now(gmt8)
                end = start + timedelta(hours=1)

                # Ensure start_end is a tuple of two datetime objects
                if not isinstance(start_end, tuple) or len(start_end) != 2:
                    start_end = (start, end)
                if start_end == (None, None):
                    raise ValueError("Invalid start and end dates")

                # Update 'start', 'end', and 'start_end' in the 'result' dictionary
                result = update_result(result, local_data.page, page_title, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)

                # Increment the count of pages set to All-Day-Event
                if start_end is not None:
                    with lock:
                        counts['count_auto_default_setting'] += 1
                        result['total_pages_modified'] = calculate_total(counts)

                # Update the page object
                with lock:
                    update_page(local_data.page, start, end, start_end)

                # Update the page properties in the Notion database
                with lock:
                    update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end)
                
                if start is not None and end is not None:
                    with lock:
                        update_previous_dates(local_data.page, start, end, start_end)
                elif start is not None and end is None:
                    with lock:
                        update_previous_dates(local_data.page, start, None, start_end)           

                # Only add details to the list if 'StartEnd' was None before the update
                if start_end_value is None:
                    with lock:
                        result['details']['auto_default_setting_details'][result['page_id']] = (result['page_title'], start, end, start_end, original_start, original_end)
                        
            return result, counts, details, processed_pages, page['id'], original_start


        # Sub-condition 3 under MASTER CONDITION A
        # Filling StartEnd
        elif has_time(local_data.page['properties']['Start']['date']['start']) and start.time() != time(0) and has_time(local_data.page['properties']['End']['date']['start']) and end.time() != time(0):
            
            # Save the original values of 'start', 'end', and 'start_end'
            original_start = start
            original_end = end
            original_start_end = start_end

            # Save the original value of 'start_end'
            start_end_value = start_end

            # Ensure start_end is a tuple of two datetime objects
            if not isinstance(start_end, tuple) or len(start_end) != 2:
                start_end = (start, end)
                
            # Assign the current value of start_end to updated_start_end
            updated_start_end = start_end
            
            if start_end == (None, None):
                raise ValueError("Invalid start and end dates")

            # Update 'start_end' in the 'result' dictionary
            result = update_result(result, local_data.page, page_title, start, end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)

            # Increment the count of pages filled
            if start_end is not None:
                with lock:
                    counts['count_pages_filled'] += 1
                    result['total_pages_modified'] = calculate_total(counts)

            # Update the page object
            with lock:
                update_page(local_data.page, start, end, start_end)
                
            # Update the 'StartEnd' property in the Notion database
            update_page_properties(notion, page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, start_end, as_date=False, single_date=False, update_all=True, keep_midnight=False, remove_start_end_midnight=True)
            
            # Update the 'Previous Start' and 'Previous End' properties
            update_previous_dates(local_data.page, start, end, start_end, as_date=False)

            # Only add details to the list if 'StartEnd' was None before the update
            if start_end_value is None:
                with lock:
                    with lock:
                        result['details']['pages_filled_details'][result['page_id']] = (result['page_title'], original_start, original_end, result.get('prev_start_value', None), result.get('prev_end_value', None), original_start_end, updated_start_end)

            return result, counts, details, processed_pages, page['id']

        # Sub-condition 4 under MASTER CONDITION A
        # Single-Dates
        elif start is not None and end is not None:
            
            # Check if 'Start' and 'End' have a Single-Date without a time component
            if (not has_time(local_data.page['properties']['Start']['date']['start']) and not has_time(local_data.page['properties']['End']['date']['start'])) or ((has_time(local_data.page['properties']['Start']['date']['start']) and start.time() == time(0)) or has_time(local_data.page['properties']['End']['date']['start']) and end.time() == time(0)):

                if prev_start is not None and prev_end is not None:
                    prev_start = prev_start.strftime('%Y-%m-%d')
                    prev_end = prev_end.strftime('%Y-%m-%d')

                # Save the original values of 'start' and 'end'
                original_start = start.strftime('%Y-%m-%d')
                original_end = end.strftime('%Y-%m-%d')

                # Format the datetime object for the Notion API
                new_start_value = start.strftime('%Y-%m-%d')
                new_end_value = end.strftime('%Y-%m-%d')

                # Update 'start_end' in the 'result' dictionary
                result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, (start, end), prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)

                # Increment the count of pages filled
                if start_end is not None:
                    with lock:
                        counts['count_pages_single_dates'] += 1
                        result['total_pages_modified'] = calculate_total(counts)

                # Update the page object
                with lock:
                    update_page(local_data.page, start, end, (start, end))
                    
                # Update 'start_end'
                start_end = (start, end)

                # Update the 'Previous Start' and 'Previous End' properties
                update_previous_dates(local_data.page, start, end, start_end, as_date=True)

                # Update the 'StartEnd' property in the Notion database
                update_page_properties(notion, local_data.page, Start_Notion_Name, End_Notion_Name, Date_Notion_Name, start, end, (start, end), as_date=True, single_date=True, update_all=True)

                # Only add details to the list if 'StartEnd' was None before the update
                if start_end_value is None:
                    with lock:
                        result['details']['pages_single_dates_details'][result['page_id']] = (result['page_title'], result['original_start'], result['original_end'], result['new_start_value'], result['new_end_value'])
                        
                
                details['prev_start'] = prev_start
                details['prev_end'] = prev_end
                
                return result, counts, details, processed_pages, page['id']

    # MASTER CONDITION B :  ‘End’ is always None
    if end is None:
        
        # Sub-condition 1 under MASTER CONDITION B
        # FILLING 'End' from None to 'StartEnd' existing value
        if start is not None and start_end is not None:

            if StartEnd_to_Overwrite_All == True:

                # Convert 'start_end', 'start', and 'end' to naive datetime objects
                # 确保处理时区信息时的正确性
                if isinstance(start_end, datetime):
                    start_end_naive = start_end.replace(tzinfo=None) if start_end.tzinfo is not None else start_end
                else:
                    start_end_naive = start_end

                if isinstance(start, datetime):
                    start_naive = start.replace(tzinfo=None) if start.tzinfo is not None else start
                else:
                    start_naive = start

                # 更新end时，确保不会错误地将时间设置为00:00
                if start_end_naive != start_naive:
                    original_start_end = start_end
                    original_start = start
                    original_end = end

                    start_end_prop = local_data.page['properties']['StartEnd']['date']
                    if start_end_prop:
                        new_start = parse(start_end_prop['start']) if start_end_prop['start'] is not None else None
                        new_end = parse(start_end_prop['end']) if start_end_prop['end'] is not None else None

                        # 检查并保留时间部分
                        if new_start and new_start.time() != dt_time(0, 0):
                            new_start = new_start
                        if new_end and new_end.time() != dt_time(0, 0):
                            new_end = new_end

                    # 更新start和end
                    if new_start != start:
                        start = new_start
                    if new_end != end:
                        end = new_end

                    start_end = (new_start, new_end)
                    updated_start_end = start_end

                    # Only print details and increment count if 'Start' and 'End' were actually overwritten
                    if start != original_start or end != original_end:

                        # Save the current values of 'Start' and 'End'
                        prev_start = original_start
                        prev_end = original_end

                        # Update the page in the Notion database
                        with lock:
                            start_end_list = []
                            if start_end_prop['start'] is not None:
                                start_end_list.append(parse(start_end_prop['start']))
                            else:
                                start_end_list.append(None)  # or any default value you want to assign

                            if start_end_prop['end'] is not None:
                                start_end_list.append(parse(start_end_prop['end']))
                            else:
                                start_end_list.append(None)  # or any default value you want to assign
                            update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_list)


                        # Update the 'Previous Start' and 'Previous End' properties
                        with lock:
                            update_previous_dates(local_data.page, start, end, start_end)

                        # Update the page object
                        with lock:
                            update_page(local_data.page, start, end, start_end_prop)

                        # Update the 'result' dictionary
                        with lock:
                            result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, original_start, original_end, original_start_end, updated_start_end)

                        # Increment the count of pages filled
                        with lock:
                            counts['count_pages_filled'] += 1
                            result['total_pages_modified'] = calculate_total(counts)

                        # Only add details to the list if 'StartEnd' was None before the update
                        with lock:
                            result['details']['pages_filled_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'], updated_start_end)

            else:
                # If not overwriting all, ensure we keep the end as None
                updated_start_end = None
                
                start_end_prop = local_data.page['properties']['StartEnd']['date']
                if start_end_prop:
                    original_start_end = start_end  # Capture the original start_end

                    if start_end != start:
                        start_end = start

                        with lock:
                            start_end_list = []
                            # Check and update start date
                            if start_end_prop.get('start') is not None:
                                if not isinstance(start, datetime):
                                    start = parse(start)
                                start_end_list.append(start)
                            else:
                                start_end_list.append(None)  # Default value assignment

                            # Ensure end remains None
                            start_end_list.append(None)

                            update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_list)

                        # Update the 'Previous Start' and 'Previous End' properties
                        with lock:
                            update_previous_dates(local_data.page, start, end, start_end)

                        # Update the page object
                        with lock:
                            update_page(local_data.page, start, end, start_end_prop)

                        # Update the 'result' dictionary
                        with lock:
                            result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, original_start, original_end, original_start_end, updated_start_end)

                        # Increment the count of pages filled
                        with lock:
                            counts['count_pages_filled'] += 1
                            result['total_pages_modified'] = calculate_total(counts)

                        # Only add details to the list if 'StartEnd' was None before the update
                        with lock:
                            result['details']['pages_filled_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'], updated_start_end)
                    

        # Sub-condition 2 under MASTER CONDITION B
        # FILLING 'Start' AND 'End' from None to 'StartEnd' existing value
        if start is None and start_end is not None:

            if StartEnd_to_Overwrite_All == True:
                
                # Convert 'start_end' to naive datetime object
                if isinstance(start_end, datetime):
                    start_end_naive = start_end.replace(tzinfo=None)
                else:
                    start_end_naive = start_end

                # If 'Start' or 'End' have a Single-Date WITH a time component
                if isinstance(start_end, datetime) and start is None and end is None:

                    # Store the original values of 'start' and 'end' before they are overwritten
                    original_start_end = start_end

                    # Update 'Start' and 'End' according to 'StartEnd' existing value
                    start_end_prop = local_data.page['properties']['StartEnd']['date']
                    new_start = None
                    new_end = None
                    if start_end_prop:
                        if start_end_prop['start']:
                            new_start = parse(start_end_prop['start'])
                        if start_end_prop['end']:
                            new_end = parse(start_end_prop['end'])

                    # If 'new_end' is still None, set it to 'new_start'
                    if new_end is None:
                        new_end = new_start

                    # Only update 'start' and 'end' if the new values are different
                    if new_start is not None and new_start != start:
                        start = new_start

                    if new_end is not None and new_end != end:
                        end = new_end

                    # Only update 'start' and 'end' if the new values are different
                    if new_start != start:
                        start = new_start

                    if new_end != end:
                        end = new_end
                        
                    # Update 'start_end' and 'updated_start_end'
                    start_end = (new_start, new_end)
                    updated_start_end = start_end

                    # Only print details and increment count if 'Start' and 'End' were actually overwritten
                    if start != original_start or end != original_end:

                        # Save the current values of 'Start' and 'End'
                        prev_start = original_start
                        prev_end = original_end

                        # Update the page in the Notion database
                        with lock:
                            start_end_list = []
                            if start_end_prop['start']:
                                start_end_list.append(parse(start_end_prop['start']))
                            if start_end_prop['end']:
                                start_end_list.append(parse(start_end_prop['end']))
                            update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end, start_end_list)

                        # Update the 'Previous Start' and 'Previous End' properties
                        with lock:
                            update_previous_dates(local_data.page, start, end, start_end)

                        # Update the page object
                        with lock:
                            update_page(local_data.page, start, end, start_end_prop)

                        # Update the 'result' dictionary
                        with lock:
                            result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, original_start, original_end, original_start_end, updated_start_end)

                        # Increment the count of pages filled
                        with lock:
                            counts['count_pages_filled'] += 1
                            result['total_pages_modified'] = calculate_total(counts)

                        # Only add details to the list if 'StartEnd' was None before the update
                        with lock:
                            result['details']['pages_filled_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'], updated_start_end)


        return result, counts, details, processed_pages, page['id']


    # MASTER CONDITION C :  ‘Start’ is always None
    if start is None:
        
        # Sub-condition 1 under MASTER CONDITION C
        # FILLING 'Start' from None to 'StartEnd' existing value
        if end is not None and start_end is not None:

            if StartEnd_to_Overwrite_All == True:

                # Convert 'start_end', 'start', and 'end' to naive datetime objects
                if isinstance(start_end, datetime):
                    start_end_naive = start_end.replace(tzinfo=None)
                else:
                    start_end_naive = start_end

                if isinstance(start, datetime):
                    start_naive = start.replace(tzinfo=None)
                else:
                    start_naive = start

                if isinstance(end, datetime):
                    end_naive = end.replace(tzinfo=None)
                else:
                    end_naive = end

                # If 'Start' or 'End' have a Single-Date WITH a time component
                if start_end_naive != start_naive or start_end_naive != end_naive:

                    # Store the original values of 'start' and 'end' before they are overwritten
                    original_start_end = start_end

                    if StartEnd_to_Overwrite_All == True:
                        if isinstance(start, datetime):
                            original_start = datetime.combine(start.date(), time()) if start.time() == time() else start
                        else:
                            original_start = start

                        if isinstance(end, datetime):
                            original_end = datetime.combine(end.date(), time()) if end.time() == time() else end
                        else:
                            original_end = end
                            
                        # Update 'Start' and 'End' according to 'StartEnd' existing value
                        start_end_prop = local_data.page['properties']['StartEnd']['date']
                        
                        if start_end_prop['start'] is not None:
                            new_start = parse(start_end_prop['start'])
                        else:
                            new_start = start_end[0] if start_end else None
                                                    
                        if start_end_prop['end'] is not None:
                            new_end = parse(start_end_prop['end'])
                        else:
                            if isinstance(start_end, datetime):
                                new_end = start_end
                            elif isinstance(start_end, (list, tuple)) and len(start_end) > 1:
                                new_end = start_end[1]
                            else:
                                new_end = None                         

                        # Update start and end with new_start and new_end
                        start = new_start
                        end = new_end

                        # Check if the start and end dates have a time component
                        if new_end is not None:
                            new_end = new_end.replace(tzinfo=None)
                        
                        # Only update 'start' and 'end' if the new values are different
                        if new_start != start:
                            start = new_start
                            start_value = start  # Define start_value as the updated variable for start

                        if new_end != end:
                            end = new_end
                            end_value = end  # Define end_value as the updated variable for end

                        if start is None and start_end is not None:
                            start = start_end.date()
                            start_value = start  # Define end_value as the updated variable for end
                        elif start_end != start:
                            start = new_start
                            start_value = start  # Define end_value as the updated variable for end
                            
                        print(f"\nAFTER Update:\n")
                        print(f"original_start: {original_start}")
                        print(f"New Start: {start}")
                        print(f"original_end: {original_end}")
                        print(f"New End: {end}\n")
                        
                            
                        # Update 'start_end' and 'updated_start_end'
                        start_end = (new_start, new_end)
                        updated_start_end = start_end

                        # Only print details and increment count if 'Start' and 'End' were actually overwritten
                        if start != original_start or end != original_end:

                            # Save the current values of 'Start' and 'End'
                            prev_start = original_start
                            prev_end = original_end

                            # Update the page in the Notion database
                            with lock:
                                start_end_list = []
                                if start_end_prop['start']:
                                    start_end_list.append(parse(start_end_prop['start']))
                                if start_end_prop['end']:
                                    start_end_list.append(parse(start_end_prop['end']))
                                update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_list)

                            # Update the 'Previous Start' and 'Previous End' properties
                            with lock:
                                update_previous_dates(local_data.page, start, end, start_end)

                            # Update the page object
                            with lock:
                                update_page(local_data.page, start, end, start_end_prop)

                            # Update the 'result' dictionary
                            with lock:
                                result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, original_start, original_end, original_start_end, updated_start_end)

                            # Increment the count of pages filled
                            with lock:
                                counts['count_pages_filled'] += 1
                                result['total_pages_modified'] = calculate_total(counts)

                            # Only add details to the list if 'StartEnd' was None before the update
                            with lock:
                                result['details']['pages_filled_details'][result['page_id']] = (result['page_title'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'], updated_start_end)


        return result, counts, details, processed_pages, page['id']

    # MASTER CONDITION D :  ‘Start’, End’ and ‘StarEnd’ Date Property are ALL PRESENT
    # OVERWRITE
    elif start_end is not None and start is not None and end is not None:


        # Initialize a dictionary to keep track of the pages modified by each sub-condition
        pages_modified = {
            'sub_condition_1': set(),
            'sub_condition_2': set(),
            'sub_condition_3': set(),
            'sub_condition_4': set(),
        }


        # Sub-Condition 1 under MASTER CONDITION D
        # Overwrite StartEnd accordingly 'Start' and 'End' existing dates and times
        # If 'Start' and 'End' have a Single-Date WITH a time component
        if has_time(local_data.page['properties']['Start']['date']['start']) and has_time(local_data.page['properties']['End']['date']['start']):

            # Check if Start or End are explicitly set 00:00
            if start.time() != datetime.min.time() or end.time() != datetime.min.time():

                # Store the original start and end values
                original_start = prev_start
                original_end = prev_end

                # Define start_value as the updated variable for start
                start_value = start

                # Define end_value as the updated variable for end
                end_value = end

                # Store the previous values of 'start' and 'end' at the beginning of the function
                prev_start_value = prev_start
                prev_end_value = prev_end

                # Check if start and end are set to 00:00 and start_end is empty
                if start.time() == dt.time(0, 0) or end.time() == dt.time(0, 0) and start_end == (None, None):
                    # Overwrite start_end with start and end by removing 00:00
                    start_end = (start.date(), end.date())
                    # Overwrite start and end by removing 00:00
                    start = start.date()
                    end = end.date()                    

                # Only print details and increment count if 'Start' and 'End' were actually overwritten
                if start_value != prev_start_value or end_value != prev_end_value:

                    # Update 'StartEnd' as Time-Range accordingly 'Start' and 'End' existing dates and times
                    start_end_prop = (start_value, end_value)

                    # Save the current values of 'Start' and 'End'
                    prev_start = prev_start_value
                    prev_end = prev_end_value

                    # Update the 'start' and 'end' variables
                    start = start_end_prop[0]
                    end = start_end_prop[1]

                    # Update the page in the Notion database
                    with lock:
                        update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_prop)

                    # Update the 'Previous Start' and 'Previous End' properties
                    with lock:
                        update_previous_dates(local_data.page, start, end, start_end_prop)

                    # Update the page object
                    with lock:
                        update_page(local_data.page, start, end, start_end_prop)

                    # Update the 'result' dictionary
                    with lock:
                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, prev_start_value, prev_end_value)

                    # Increment the count of pages filled
                    with lock:
                        counts['count_pages_overwritten'] += 1
                        result['total_pages_modified'] = calculate_total(counts)

                    # Only add details to the list if 'StartEnd' was None before the update
                    with lock:
                        result['details']['pages_overwritten_details'][result['page_id']] = (result['page_title'], result['original_start'], result['original_end'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'])


        # Sub-Condition 2 under MASTER CONDITION D
        # Overwrite Start or End
        # If 'Start' or 'End' have a Single-Date WITH a time component
        
        # Ensure 'start' and 'end' are datetime objects
        if not isinstance(start, datetime):
            start = pytz.timezone('Asia/Kuala_Lumpur').localize(datetime.combine(start, time()))
        if not isinstance(end, datetime):
            end = pytz.timezone('Asia/Kuala_Lumpur').localize(datetime.combine(end, time()))

        # Parse 'StartEnd' dates and ensure they are datetime objects with timezone
        start_end_prop = local_data.page['properties']['StartEnd']['date']
        if start_end_prop:
            start_end_start = parse(start_end_prop['start']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'start' in start_end_prop and start_end_prop['start'] is not None else None
            start_end_end = parse(start_end_prop['end']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'end' in start_end_prop and start_end_prop['end'] is not None else None

        if (end.time() != time(0, 0) or start.time() != time(0, 0)) or (end.time() == time(0, 0) and start.time() == time(0, 0)):
            
            sub_condition_2_modified = False

            if StartEnd_to_Overwrite_All == True:

                # Store the original values of 'start' and 'end' before they are overwritten
                original_start = start if isinstance(start, datetime) else start
                original_end = end if isinstance(end, datetime) else end

                # Update 'Start' and 'End' according to 'StartEnd' existing value
                start_end_prop = local_data.page['properties']['StartEnd']['date']
                if start_end_prop:
                    # Parse the dates from 'start_end_prop' and convert timezone
                    start_end_start = parse(start_end_prop['start']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'start' in start_end_prop and start_end_prop['start'] is not None else None
                    start_end_end = parse(start_end_prop['end']).astimezone(pytz.timezone('Asia/Kuala_Lumpur')) if 'end' in start_end_prop and start_end_prop['end'] is not None else None
                
                # Check if 'StartEnd' is a Time-Range where start date is same or different from 'start' and end date is same or different from 'end'
                # And also check if Start and End are at midnight (but not set explicitly), and they are the same as the StartEnd date range, while only StartEnd has a time component set explicitly that differs from Start and End
                if start_end_end is not None and ((start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0)) and
                    (start.date() == start_end_start.date() or (start_end_end is not None and end.date() == start_end_end.date()))) or \
                    ((start.time() == time(0, 0) and end.time() == time(0, 0) and start.date() != end.date()) and 
                    (start.date() == start_end_start.date() and (start_end_end is not None and end.date() == start_end_end.date()) and 
                    (start_end_start.time() != start.time() or (start_end_end is not None and start_end_end.time() != end.time())))):

                    # Extract date part from 'start_end_prop' and update 'Start' and 'End' with the same date
                    start_date = start_end_start.date()
                    end_date = start_end_end.date()
                    
                    # Preserve timezone information from 'StartEnd Start' and 'StartEnd End'
                    start_tz = start_end_start.tzinfo
                    end_tz = start_end_end.tzinfo

                    # Update 'Start' and 'End' with the new date part while preserving the original time and timezone
                    start = datetime.combine(start_date, start_end_start.time(), tzinfo=start_tz)
                    end = datetime.combine(end_date, start_end_end.time(), tzinfo=end_tz)  # Update 'end' with the time from 'start_end_end'

                    # Only update 'start' and 'end' if the new values are different
                    if start != original_start:
                        start_value = start  # Define start_value as the updated variable for start

                    if end != original_end:
                        end_value = end  # Define end_value as the updated variable for end

                # Only print details and increment count if 'Start' and 'End' were actually overwritten
                if start != original_start or end != original_end:
                    sub_condition_2_modified = True

                    # Save the current values of 'Start' and 'End'
                    prev_start = original_start
                    prev_end = original_end

                    # Update the page in the Notion database
                    with lock:
                        start_end_list = [parse(start_end_prop['start']), parse(start_end_prop['end'])]
                        update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_list)

                    # Update the 'Previous Start' and 'Previous End' properties
                    with lock:
                        update_previous_dates(local_data.page, start, end, start_end_prop)

                    # Update the page object
                    with lock:
                        update_page(local_data.page, start, end, start_end_prop)

                    # Update the 'result' dictionary
                    with lock:
                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, original_start, original_end)

                    # Increment the count of pages filled
                    with lock:
                        counts['count_pages_overwritten'] += 1
                        result['total_pages_modified'] = calculate_total(counts)

                    # Only add details to the list if 'StartEnd' was None before the update
                    with lock:
                        result['details']['pages_overwritten_details'][result['page_id']] = (result['page_title'], result['original_start'], result['original_end'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'])

                    pages_modified['sub_condition_2'].add(page['id'])
                    print(f"Page {page_title} has been modified")

        if not sub_condition_2_modified and page['id'] not in pages_modified['sub_condition_2']:

            # Initialize the flag
            is_modified = False

            # Sub Condition 3 under MASTER CONDITION D
            # Event Overwritten
            # Overwrite StartEnd accordingly Start and End
            # Start and End are having Single-Date WITHOUT time component 00:00 set explicitly while StartEnd is having different date or time range from Start and End.
            # If 'Start' and 'End' have a Single-Date
            start_end = page['properties']['StartEnd']['date']
            
            if StartEnd_to_Overwrite_All == False:
                
                # Convert 'start' and 'end' in start_end to datetime objects
                if start_end['start'] is not None or start_end['end'] is not None:
                    start_end_start = None
                    start_end_end = None

                    if start_end['start'] is not None:
                        start_end_start = parse(start_end['start']).replace(tzinfo=start.tzinfo)

                    if start_end['end'] is not None:
                        start_end_end = parse(start_end['end']).replace(tzinfo=end.tzinfo)

                        processed_sub_condtion_3 = True

                        #if start.time() != time(0, 0) and end.time() == time(0, 0) and start.date() == start_end_start.date() and end.date() == start_end_end.date():
                            #processed_sub_condtion_3 = False

                        if processed_sub_condtion_3:
                            # Check if start and end have time set to 00:00:00
                            if not (start.time() != datetime.min.time() and end.time() != datetime.min.time() and start_end_start.time() == datetime.min.time() and start_end_end.time() == datetime.min.time()) and \
                                not (start.date() == end.date() == start_end_start.date() and start.time() == end.time() == start_end_start.time() == time(0, 0)) and \
                                ((start.time() != datetime.min.time() and start.date() != start_end_start.date() and end.date() == start_end_end.date()) or
                                (end.time() != datetime.min.time() and end.date() != start_end_end.date() and start.date() == start_end_start.date())) and \
                                ((start_end_start is not None and start.date() == start_end_start.date() and start.time() != time(0, 0)) or
                                (start_end_end is not None and end.date() == start_end_end.date() and end.time() != time(0, 0)) or
                                ((start_end_start is not None and start.date() == start_end_start.date() and start.time() != start_end_start.time() and start.time() != time(0, 0)) or
                                (start_end_end is not None and end.date() == start_end_end.date() and end.time() != start_end_end.time() and end.time() != time(0, 0)))) and \
                                not ((start.time() != time(0, 0) and end.time() == time(0, 0) and start.time() != end.time()) or (start.time() == time(0, 0) and end.time() != time(0, 0) and start.time() != end.time())) and start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0) and \
                                not ((start.time() != datetime.min.time() and end.time() == datetime.min.time()) or (start.time() == datetime.min.time() and end.time() != datetime.min.time())) or \
                                ((start.time() != time(0, 0) and end.time() == time(0, 0)) or (start.time() == time(0, 0) and end.time() != time(0, 0))) and start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0):

                                # Define start_value as the updated variable for start
                                start_value = start

                                # Define end_value as the updated variable for end
                                end_value = end

                                # Store the previous values of 'start' and 'end' at the beginning of the function
                                prev_start_value = prev_start
                                prev_end_value = prev_end
                                
                                # Only print details and increment count if 'Start' and 'End' were actually overwritten
                                if start_value != prev_start_value or end_value != prev_end_value:
                                    is_modified = True
                                    print(f"is_modified: {is_modified}")
                                    
                                    # Update 'StartEnd' as Time-Range accordingly 'Start' and 'End' existing dates and times
                                    start_end_prop = (start_value, end_value)

                                    # Save the current values of 'Start' and 'End'
                                    prev_start = prev_start_value
                                    prev_end = prev_end_value

                                    # Update the 'start' and 'end' variables
                                    start = start_end_prop[0]
                                    end = start_end_prop[1]

                                    # Update the page in the Notion database
                                    with lock:
                                        update_page_properties(notion, local_data.page, 'Start', 'End', 'StartEnd', start, end, start_end_prop)

                                    # Update the 'Previous Start' and 'Previous End' properties
                                    with lock:
                                        update_previous_dates(local_data.page, start, end, start_end_prop)

                                    # Update the page object
                                    with lock:
                                        update_page(local_data.page, start, end, start_end_prop)

                                    # Update the 'result' dictionary
                                    with lock:
                                        result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end_prop, prev_start, prev_end, prev_start_value, prev_end_value)


                                    # Increment the count of pages filled
                                    with lock:
                                        counts['count_pages_overwritten'] += 1
                                        result['total_pages_modified'] = calculate_total(counts)

                                    # Only add details to the list if 'StartEnd' was None before the update
                                    with lock:
                                        result['details']['pages_overwritten_details'][result['page_id']] = (result['page_title'], result['original_start'], result['original_end'], result['start'], result['end'], result['prev_start_value'], result['prev_end_value'], result['start_end'])


                                pages_modified['sub_condition_3'].add(page['id'])
                                print(f"Page {page_title} has been modified")
                        
                        
            
            if not sub_condition_2_modified and page['id'] not in pages_modified['sub_condition_2'] and not is_modified and page['id'] not in pages_modified['sub_condition_3']:

                # SUb-Sub Condition 4 under MASTER CONDITION D
                # All-Days-Event
                # Start and End are having Single-Date WITH time component 00:00 set explicitly while StartEnd is having different date or time range from Start and End.
                # If 'Start' and 'End' have a Single-Date
                    
                start_end = page['properties']['StartEnd']['date']

                if start_end['start'] is not None:
                    start_end_start = parse(start_end['start']).replace(tzinfo=start.tzinfo)
                    start_end_end = start_end['end']
                    if start_end_end is not None:
                        start_end_end = parse(start_end_end).replace(tzinfo=end.tzinfo)
                    else:
                        start_end_end = None

                    
                    # Sub-Condition 1
                    if StartEnd_to_Overwrite_All == True:
                        if start_end_start is not None and start is not None and end is not None:
                            if start_end_end is None and start_end_start.time() == time(0, 0):
                                start = start_end_start
                                end = start_end_start
                                result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_midnight=True)
                            elif start_end_end is not None and start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0) and (start.time() != start_end_start.time() or end.time() != start_end_end.time()):
                                # Check if only start or end is overwritten by start_end_start or start_end_end respectively
                                keep_start_midnight = start.time() == time(0, 0) and end.time() != time(0, 0)
                                keep_end_midnight = end.time() == time(0, 0) and start.time() != time(0, 0)
                                start = start_end_start
                                end = start_end_end
                                result, details , start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight=keep_start_midnight)
                            elif not ((start.time() == time(0, 0) and end.time() == time(0, 0) and start.date() != end.date()) and 
                                ((start.date() == start_end_start.date() or end.date() == start_end_end.date()) and 
                                (start.date() != start_end_start.date() or end.date() != start_end_end.date())) and
                                (start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0))) and not (start.time() != time(0, 0) and end.time() == time(0, 0) and start.date() == start_end_start.date() and end.date() == start_end_end.date()):
                                start = start_end_start
                                end = start_end_end
                                result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                        # New sub-condition
                        elif start_end_start is not None and start_end_end is not None and start is not None and end is not None:
                            if start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0) and start.time() != end.time():
                                start = start_end_start
                                end = start_end_end
                                result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)


                    # Sub-Condition 2
                    if StartEnd_to_Overwrite_All == False:
                        if start is not None and end is not None and start_end is not None:
                            if start_end_start is not None and start is not None and end is not None:                        
                                if not (start.date() == end.date() == start_end_start.date() and start.time() == end.time() == start_end_start.time() == time(0, 0)) or \
                                (start_end_end is not None and start.date() == end.date() == start_end_start.date() and start_end_end.date() != start.date()):
                                    if start_end_end is None and start_end_start.time() == time(0, 0):
                                        keep_start_midnight = False
                                        keep_end_midnight = False
                                        start_end['start'] = start.isoformat()
                                        start_end['end'] = end.isoformat()
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight, keep_end_midnight)
                                    # if start and end are not the same, but start_end_start and start_end_end are the same
                                    if start != end and start_end_start == start_end_end and start.date() != start_end_start.date() and end.date() != start_end_end.date():
                                        # Overwrite start_end as new time-range accordingly start and end
                                        start_end['start'] = start.isoformat()
                                        start_end['end'] = end.isoformat()
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details, keep_start_midnight, keep_end_midnight)
                                    # start and end have a time component 00:00, start_end is having different dates and times from either start and end
                                    if start_end_end is not None and start.time() == time(0, 0) and end.time() == time(0, 0) and \
                                        (start.date() != start_end_start.date() or end.date() != start_end_end.date() or start.time() != start_end_start.time() or end.time() != start_end_end.time()) and \
                                        not (start.date() == start_end_start.date() and end.date() == start_end_end.date() and start_end_end.time() != time(0, 0)):
                                        # Overwrite start_end with start and end
                                        start_end['start'] = start.isoformat()
                                        start_end['end'] = end.isoformat()
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                                    if (start.time() == time(0, 0) and end.time() == time(0, 0) and (start == end)) and (start_end_start.time() == time(0, 0) and start_end_end.time() == time(0, 0)) and (start.date() != start_end_start.date() or end.date() != start_end_end.date()):
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                                    if start_end_end is not None and start.date() == start_end_start.date() and end.date() == start_end_end.date() and start_end_start != start_end_end and \
                                        (start.time() == time(0, 0) and end.time() == time(0, 0)) and \
                                        (start_end_start.time() != time(0, 0) or start_end_end.time() != time(0, 0)):
                                        # Update start_end_start and start_end_end
                                        start_end_start = start
                                        start_end_end = end
                                        result, details, start, end = update_all_data(start, end, start_end, prev_start, prev_end, result, local_data, page_title, original_start, original_end, prev_start_value, prev_end_value, new_start_value, new_end_value, counts, start_end_value, details)
                                    
                                
                    pages_modified['sub_condition_4'].add(page['id'])
        
        return result, counts, details, processed_pages, page['id']
        

    # Update the result dictionary
    result = update_result(result, local_data.page, page_title, original_start, original_end, start, end, start_end, prev_start, prev_end, prev_start_value, prev_end_value, new_start_value, new_end_value)
    
    # Add the result to the return_values queue
    return_values.put(result)
    
    return result, counts, details, processed_pages, page['id'], original_start


def calculate_total(counts):
    return sum(counts.values())

result = {
    'counts': {
        'count_default_time_range': 0,
        'count_auto_default_setting': 0,
        'count_alternate_alldayevent_start': 0,
        'count_alldayevent': 0,
        'count_pages_filled': 0,
        'count_pages_single_dates': 0,
        'count_pages_overwritten': 0,
        # Add more counts here as needed
    },
    'details':{
        'set_Default_details': {},
        'auto_default_setting_details': {},
        'set_Alternate_alldayevent_start_details': {},
        'set_alldayevent_details': {},
        'pages_filled_details': {},
        'pages_overwritten_details': {},
        'pages_single_dates_details': {},
    },
    'page_id': None,
    'page_title': None,
    'original_start': None,
    'original_end': None,
    'start': None,
    'end': None,
    'start_end': None,
    'prev_start': None,
    'prev_end': None,
    'prev_start_value': None,
    'prev_end_value': None,
    'new_start_value': None,
    'new_end_value': None,
    'total_pages_modified': 0
    }

original_start = None
original_end = None
start = None
end = None
start_end = None

# Initialize a list to store the tasks
tasks = []

# Create a list to store the futures
futures = []

# Innitialize Lock
lock = Lock()

# Create a queue and add the pages to it
page_queue = Queue()
for page in filtered_pages:
    page_queue.put(page)

# Initialize the total count variable
total_count_default_time_range = 0
total_count_auto_default_setting = 0
total_count_alternate_alldayevent_start = 0
total_count_alldayevent = 0
total_count_pages_filled = 0
total_count_pages_single_dates = 0
total_count_pages_overwritten = 0

# Initialize the dictionary
unique_set_Default_details = {}
unique_auto_default_setting_details = {}
unique_set_Alternate_alldayevent_start_details = {}
unique_set_alldayevent_details = {}
unique_pages_filled_details = {}
unique_pages_single_dates_details = {}
unique_pages_overwritten_details = {}

# Initialize a set to store the page_titles
processed_page_ids = set()

processed_pages = set()

# Initialize a set to keep track of the unique pages that have been modified
modified_pages = set()

no_pages_operated_B = False

printed_pages = set()

default_time_range_details = []
auto_default_setting_details = []
alternate_alldayevent_start_details = []
alldayevent_details = []
pages_filled_details = []
pages_single_dates_details = []
pages_overwritten_details = []

summary_messages = Queue()
current_group = None

# Create a dictionary that maps each group to its pages
group_to_pages = defaultdict(list)
for page in filtered_pages:
    if 'group' in page:
        group_to_pages[page['group']].append(page)

# Sort the pages in each group by 'id'
for pages in group_to_pages.values():
    pages.sort(key=lambda page: page['id'])

# Get the last page id for each group
last_page_ids = {group: pages[-1]['id'] for group, pages in group_to_pages.items()}

printed_groups = set()

filtered_pages.sort(key=lambda page: (page.get('group', ''), page['id']))

original_start1_before_loop = page.get('start')

with ThreadPoolExecutor(max_workers=3) as executor:
    # Create a list to store the futures in the order they were created
    ordered_futures = []
    futures = {}
    for page in filtered_pages:
        if page['id'] not in processed_pages:
            future = executor.submit(process_pages_condition_A, page, result['counts'], result['details'], lock, processed_pages, return_values)
            futures[future] = page
            ordered_futures.append(future)

    # Extract the 'group' value from each page in filtered_pages
    group_values = [page['group'] for page in filtered_pages if 'group' in page]

    # Remove duplicates by converting the list to a set, then convert it back to a list
    groups = list(set(page['group'] for page in filtered_pages))

    last_page_ids = {group: pages[-1]['id'] for group, pages in group_to_pages.items()}
    
    current_group_condition = None
    # Iterate over the ordered list of futures
    for future in ordered_futures:
        page = futures[future]
        try:
            result = future.result(timeout=15.0)
            if len(result) == 6:
                future_result, future_counts, details, processed_pages, page_id, original_start = result
                original_start1_before_loop = original_start 
                result = {'future_result': future_result, 'future_counts': future_counts, 'details': details, 'processed_pages': processed_pages, 'page_id': page_id, 'original_start': original_start}
            elif len(result) == 5:
                future_result, future_counts, details, processed_pages, page_id = result
                original_start = None  # or some other default value
                result = {'future_result': future_result, 'future_counts': future_counts, 'details': details, 'processed_pages': processed_pages, 'page_id': page_id, 'original_start': original_start}
            else:
                raise ValueError("Unexpected number of values in result")

            if 'prev_start' in details and 'prev_end' in details:
                page['previous_start'] = details['prev_start']
                page['previous_end'] = details['prev_end']
            
            result['total_pages_modified'] = len(modified_pages)
            original_start1 = original_start
            processed_pages.add(page['id'])
            
            # Check if 'original_start' is in result before assigning its value to original_start1
            if 'original_start' in result:
                original_start1 = result['original_start']
            else:
                original_start1 = None
            
            result.update(future_result)
            future_dict = {}
            future_dict.update(future_result)
            future_dict['counts'].update(future_counts)
            page_title = future_result.get('page_title')
            page['start'] = page.get('start', None)
            page['end'] = page.get('end', None)
            original_end1 = page.get('end')
            original_start_end1 = page.get('start_end')
            page = set_default_time_range(page,timezone)
            future_dict['start'] = page.get('start')
            future_dict['end'] = page.get('end')
            future_dict['start_end'] = page.get('start_end')
            result['counts'].update(future_counts)

            if 'page_id' in future_result:
                page_id = future_result['page_id']
            else:
                print(f"Future result doesn't have a 'page_id' key: {future_result}")
                continue

            page_id = future_result['page_id']

            if 'set_Default_details' in result['details']:
                result['details']['set_Default_details'] = dict(result['details']['set_Default_details'])

            for page_id, details in result['details']['set_Default_details'].items():
                if page_id not in unique_set_Default_details:
                    unique_set_Default_details[page_id] = details

            # Initialize current_page_id before the for loop
            current_page_id = None
            page_printed = False
            previous_page_id = None
            
            current_page_condition = (page.get('start'), page.get('end'), page.get('start_end'))

            printed_default_time_range = False

            for page_id, details in unique_set_Default_details.items():
                
                current_page_id = page_id
                # If this is a new group, reset printed_default_time_range
                if current_page_id != previous_page_id:
                    printed_default_time_range = False
                
                if current_page_id == page_id:
                    start_time, end_time, unknown_value, start_end = details[1:]
                    printed_default_time_range = True
                    if printed_default_time_range:
                        default_time_range_details.append((formatted_task, formatted_start, formatted_end, formatted_startend, page_title))

            if printed_default_time_range:
                total_count_default_time_range += 1
                with lock:
                    modified_pages.add(page_id)
            with lock:
                unique_set_Default_details.clear()


            printed_default_setting = False

            prev_start = page.get('previous_start')
            prev_end = page.get('previous_end')

            for page_id, details in result['details'].get('auto_default_setting_details', {}).items():
                task, start, end, start_end, original_start, original_end, *extra = list(details)

                # Convert prev_start and prev_end to datetime objects
                prev_start = datetime.strptime(prev_start, '%Y-%m-%d %H:%M:%S%z') if prev_start is not None else None
                prev_end = datetime.strptime(prev_end, '%Y-%m-%d %H:%M:%S%z') if prev_end is not None else None

                with lock:
                    unique_auto_default_setting_details[page_id] = (task, start, end, start_end, original_start, original_end)

            for page_id, details in unique_auto_default_setting_details.items():
                task, start, end, start_end, original_start, original_end = details

                if prev_start is not None:
                    formatted_prev_start = prev_start.strftime('%b %-d, %Y')
                else:
                    formatted_prev_start = formatted_plain_none
                if prev_end is not None:
                    formatted_prev_end = prev_end.strftime('%b %-d, %Y')
                else:
                    formatted_prev_end = formatted_plain_none

                printed_default_setting = True

                auto_default_setting_details.append((formatted_task, formatted_start, formatted_end, formatted_startend, page_title, start, end, start_end, original_start, original_end))

            if printed_default_setting:
                total_count_auto_default_setting += 1
                with lock:
                    modified_pages.add(page_id)
            with lock:
                unique_auto_default_setting_details.clear()


            printed_alldayevent_start = False

            for page_id, details in result['details'].get('set_Alternate_alldayevent_start_details', {}).items():
                details = list(details)
                task, start_alt, end_alt, original_end, start_end = details
                details.append(original_start1_before_loop)
                details.append(start_alt)
                details.append(end_alt)
                task, start_alt, end_alt, original_end, start_end, original_start1_before_loop, start_new, end_new = details

                with lock:
                    unique_set_Alternate_alldayevent_start_details[page_id] = (task, start_alt, end_alt, original_start1_before_loop, original_end, start_end, start_new, end_new)
            
            for page_id, details in unique_set_Alternate_alldayevent_start_details.items():
                task, start, end, original_end, start_end, original_start1_before_loop, start_new, end_new = details

                printed_alldayevent_start = True
                
                if printed_alldayevent_start:
                    alternate_alldayevent_start_details.append((formatted_task, formatted_start, formatted_end, formatted_startend, page_title, original_start1_before_loop, start_alt, end_alt))

            if printed_alldayevent_start:
                total_count_alternate_alldayevent_start += 1
                with lock:
                    modified_pages.add(page_id)
            with lock:
                unique_set_Alternate_alldayevent_start_details.clear()



            printed_alldayevent = False
            
            prev_start = page.get('previous_start')
            prev_end = page.get('previous_end')
            
            for page_id, details in result['details'].get('set_alldayevent_details', {}).items():
                details = list(details)
                task, start_alt, end_alt, original_end, start_end, *extra = details
                details.append(original_start1_before_loop)
                details.append(start_alt)
                details.append(end_alt)
                task, start_alt, end_alt, original_end, start_end, start_new, end_new, *extra = details

                # Convert prev_start and prev_end to datetime objects
                try:
                    prev_start = datetime.strptime(prev_start, '%Y-%m-%d %H:%M:%S%z') if prev_start is not None else None
                except ValueError:
                    prev_start = datetime.strptime(prev_start, '%Y-%m-%d %H:%M:%S') if prev_start is not None else None

                try:
                    prev_end = datetime.strptime(prev_end, '%Y-%m-%d %H:%M:%S%z') if prev_end is not None else None
                except ValueError:
                    prev_end = datetime.strptime(prev_end, '%Y-%m-%d %H:%M:%S') if prev_end is not None else None

                with lock:
                    unique_set_alldayevent_details[page_id] = (task, start_alt, end_alt, original_end, start_end, start_new, end_new)
            
            for page_id, details in unique_set_alldayevent_details.items():
                task, start, end, original_end, start_end, start_new, end_new = details

                if prev_start is not None:
                    formatted_prev_start = prev_start.strftime('%b %-d, %Y')
                else:
                    formatted_prev_start = formatted_plain_none
                if prev_end is not None:
                    formatted_prev_end = prev_end.strftime('%b %-d, %Y')
                else:
                    formatted_prev_end = formatted_plain_none

                printed_alldayevent = True
                
                if printed_alldayevent:
                    alldayevent_details.append((formatted_task, formatted_start, formatted_end, formatted_startend, page_title, start_alt, end_alt, prev_start, prev_end))

            if printed_alldayevent:
                total_count_alldayevent += 1
                with lock:
                    modified_pages.add(page_id)
            with lock:
                unique_set_alldayevent_details.clear()


            printed_filled_pages = False

            for page_id, details in result['details'].get('pages_filled_details', {}).items():
                task, start, end, original_start, original_end, extra, start_end = details
                
                # Update start and end
                start_new = start  # Replace with your updated start value
                end_new = end  # Replace with your updated end value
                
                # Update start_end and updated_start_end
                start_end = (start_new, end_new)
                updated_start_end = start_end

                # Then append the original and updated values to a new list
                updated_details = details + (start_new, end_new)

                with lock:
                    unique_pages_filled_details[page_id] = updated_details

            for page_id, updated_details in unique_pages_filled_details.items():
                if len(updated_details) >= 8:
                    task, start, end, original_start_end, original_end, extra, start_new, end_new, updated_start_end = updated_details

                    printed_filled_pages = True
                
                    if printed_filled_pages:
                        pages_filled_details.append((task, start, end, original_start_end, original_end, extra, start_new, end_new, updated_start_end))

            if printed_filled_pages:
                total_count_pages_filled += 1
                with lock:
                    modified_pages.add(page_id)
            with lock:
                unique_pages_filled_details.clear()

            printed_single_dates_pages = False

            prev_start = page.get('previous_start')
            prev_end = page.get('previous_end')

            for page_id, details in result['details']['pages_single_dates_details'].items():
                task, original_start, original_end, new_start_value, new_end_value, *rest = details

                # Convert prev_start and prev_end to datetime objects
                try:
                    prev_start = datetime.strptime(prev_start, '%Y-%m-%d %H:%M:%S') if prev_start is not None else None
                except ValueError:
                    prev_start = datetime.strptime(prev_start, '%Y-%m-%d %H:%M:%S%z') if prev_start is not None else None
                prev_end = datetime.strptime(prev_end, '%Y-%m-%d %H:%M:%S') if prev_end is not None else None
                
                original_start_date = original_start.split('T')[0]
                original_end_date = original_end.split('T')[0]

                original_start = datetime.strptime(original_start_date, '%Y-%m-%d')
                original_end = datetime.strptime(original_end_date, '%Y-%m-%d')
                
                new_start_value = datetime.strptime(new_start_value, '%Y-%m-%d')
                new_end_value = datetime.strptime(new_end_value, '%Y-%m-%d')

                if original_start is not None or original_end is not None:
                    start_end = [original_start, original_end]
                else:
                    start_end = [None, None]

                start_end_tuple = tuple(start_end)

                with lock:
                    unique_pages_single_dates_details[page_id] = (task, original_start, original_end, start_end_tuple, new_start_value, new_end_value)

            for page_id, details in unique_pages_single_dates_details.items():
                task, original_start, original_end, start_end, new_start_value, new_end_value = details

                if prev_start is not None:
                    formatted_prev_start = prev_start.strftime('%b %-d, %Y')
                else:
                    formatted_prev_start = formatted_plain_none
                if prev_end is not None:
                    formatted_prev_end = prev_end.strftime('%b %-d, %Y')
                else:
                    formatted_prev_end = formatted_plain_none
                
                formatted_original_start = original_start.strftime('%b %-d, %Y')
                formatted_original_end = original_end.strftime('%b %-d, %Y')

                start_end = check_list([new_start_value, new_end_value])

                if not isinstance(start_end, tuple) or len(start_end) != 2:
                    start_end = (start, start)

                if start_end[0].date() == start_end[1].date():
                    start_end_formatted = start_end[0].strftime('%b %-d, %Y')
                else:
                    start_end_formatted = f"{start_end[0].strftime('%b %-d, %Y')} - {start_end[1].strftime('%b %-d, %Y')}"

                result['StartEnd'] = start_end_formatted

                printed_single_dates_pages = True

                if printed_single_dates_pages:
                    pages_single_dates_details.append((formatted_task, formatted_prev_start, formatted_prev_end, formatted_original_start, formatted_original_end, start_end_formatted, page_title, new_start_value, new_end_value, prev_start, prev_end))

            if printed_single_dates_pages:
                total_count_pages_single_dates += 1
                with lock:
                    modified_pages.add(page_id)
            with lock:
                unique_pages_single_dates_details.clear()

            
            # Initialize the flag and dictionary
            printed_pages_overwritten = False
            unique_pages_overwritten_details = {}

            # Loop through the pages_overwritten_details
            for page_id, details in result['details'].get('pages_overwritten_details', {}).items():
                task,original_start, original_end,  start_value, end_value, prev_start_value, prev_end_value, start_end = details

                # Create a tuple for start_end
                start_end_tuple = tuple(start_end)

                # Add the details to the dictionary
                with lock:
                    unique_pages_overwritten_details[page_id] = (task,original_start, original_end, start_value, end_value, prev_start_value, prev_end_value, start_end_tuple)

            # Loop through the unique_pages_overwritten_details
            for page_id, details in unique_pages_overwritten_details.items():
                task,original_start, original_end, start_value, end_value, prev_start_value, prev_end_value, start_end, *extra = details

                # Set the flag to True
                printed_pages_overwritten = True

                # If the flag is True, append the details to the list
                if printed_pages_overwritten:
                    pages_overwritten_details.append((formatted_task, formatted_start, formatted_end, formatted_startend, page_title,original_start, original_end, start_value, end_value, prev_start_value, prev_end_value))

            # If the flag is True, increment the total count and add the page_id to the set
            if printed_pages_overwritten:
                total_count_pages_overwritten += 1
                with lock:
                    modified_pages.add(page_id)

            # Clear the dictionary for the next iteration
            with lock:
                unique_pages_overwritten_details.clear()

        except Exception as e:
            print(f"An error occurred: {type(e).__name__}, {e}")
            traceback.print_exc()
        
    no_pages_operated_B = False
    
    # After the loop, print the details and summary message for each condition
    for details in default_time_range_details:
        print(f"{details[0]}     {formatted_colon}  {formatted_BOLD_italic.format(details[4])}")
        
        start_value = page.get('start', None)
        end_value = page.get('end', None)

        print(f"{details[1]}    {formatted_colon}  {formatted_plain_none if original_start_end1 is None else DateTimeIntoNotionFormat(original_start1)} {formatted_right_arrow} {DateTimeIntoNotionFormat(future_dict['start'])}")
        print(f"{details[2]}      {formatted_colon}  {formatted_plain_none if original_end1 is None else DateTimeIntoNotionFormat(original_end1)} {formatted_right_arrow} {DateTimeIntoNotionFormat(future_dict['end'])}")
        
        start_end_value = future_dict.get('start_end', [None, None])
        start_end_value = start_end_value if isinstance(start_end_value, list) else [None, None]

        start_end_value = original_start_end1 if isinstance(original_start_end1, list) else [None, None]
        
        print(f"{details[3]} {formatted_colon}  {formatted_plain_none if start_end_value[0] is None and start_end_value[1] is None else f'{DateTimeIntoNotionFormat(start_end_value[0])} — {DateTimeIntoNotionFormat(start_end_value[1])}'} {formatted_right_arrow} {DateTimeIntoNotionFormat(future_dict['start_end'][0])} — {TimeIntoNotionFormat(future_dict['start_end'][1], future_dict['start_end'][0])}\n")
        
    if total_count_default_time_range > 0 and not no_pages_operated_B:
        print(f"\n{formatted_condition_met} {formatted_colon} '{formatted_italic.format('Start')}', '{formatted_italic.format('End')}' and '{formatted_italic.format('StartEnd')}' are {formatted_all_none}")
        print(f"\nTotal Pages set {formatted_default_time} / {formatted_time_range} : {formatted_count.format(total_count_default_time_range)}\n\n\n")
        page_printed = True


    for details in auto_default_setting_details:
        formatted_task, formatted_start, formatted_end, formatted_startend, page_title, start, end, start_end, original_start, original_end = details
        print(f"{formatted_task}     {formatted_colon}  {formatted_BOLD_italic.format(page_title)}")
        original_start_str = (formatted_plain_none if original_start is None else DateTimeIntoNotionFormat(original_start, date_only=True)).strip()
        start_str = (formatted_plain_none if start is None else DateTimeIntoNotionFormat(start, plus_time=True, time_format='24')).strip()
        print(f"{formatted_start}    {formatted_colon}  {original_start_str} {formatted_right_arrow} {start_str}")
        print(f"{formatted_end}      {formatted_colon}  {formatted_plain_none if original_end is None else DateTimeIntoNotionFormat(original_end, plus_time=True, time_format='24')} {formatted_right_arrow} {DateTimeIntoNotionFormat(end, plus_time=True, time_format='24').lstrip('0')}")  
        end_date = end.strftime('%Y-%m-%d')
        start_date = start.strftime('%Y-%m-%d')
        
        if end_date == start_date:
            if end.strftime('%H:%M') == '00:00':
                end_time_formatted = end.strftime('%H:%M')
            else:
                end_time_formatted = end.strftime('%H:%M').lstrip('0')
        else:
            if end.strftime('%H:%M') == '00:00':
                end_time_formatted = end.strftime('%b %d, %Y  %H:%M')
            else:
                end_time_formatted = end.strftime('%b %d, %Y  %H:%M').lstrip('0')

        if start_end is not None and future_dict['start_end'] is not None:
            print(f"{formatted_startend} {formatted_colon}  {formatted_plain_none} {formatted_right_arrow} {DateTimeIntoNotionFormat(start, plus_time=True, time_format='24')} — {end_time_formatted}\n")
        elif start_end is not None:
            print(f"{formatted_startend} {formatted_colon}  {formatted_plain_none} {formatted_right_arrow} {DateTimeIntoNotionFormat(start, plus_time=True, time_format='24')} — {end_time_formatted}\n")
        else:
            print(f"{formatted_startend} {formatted_colon}  {formatted_plain_none} {formatted_right_arrow} None\n")
        page_printed = True
    if total_count_auto_default_setting > 0 and not no_pages_operated_B:
        print(f"\n{formatted_condition_met} {formatted_colon} '{formatted_italic.format('End')}' and '{formatted_italic.format('StartEnd')}' are {formatted_all_none} {formatted_semicolon}")
        print(f"                '{formatted_italic.format('Start')}' {formatted_have_single_date} with {formatted_no_time}")
        print(f"\nTotal Pages {formatted_reset_default_setting} : {formatted_count.format(total_count_auto_default_setting)}\n\n\n")


    for details in alternate_alldayevent_start_details:
        formatted_task, formatted_start, formatted_end, formatted_startend, page_title, original_start1_before_loop, start_alt, end_alt = details
        print(f"{formatted_task}     {formatted_colon}  {formatted_BOLD_italic.format(page_title)}")
        original_start1_before_loop = DateTimeIntoNotionFormat(original_start1_before_loop[0], plus_time=True) if original_start1_before_loop[0] is not None else formatted_plain_none
        print(f"{formatted_start}    {formatted_colon}  {formatted_plain_none if original_start1_before_loop is None else DateTimeIntoNotionFormat(original_start1_before_loop, date_only=False, plus_time=True, show_midnight=True)} {formatted_right_arrow} {DateTimeIntoNotionFormat(start_alt, date_only=True)}")

        original_end = None  # Set original_end to None
        print(f"{formatted_end}      {formatted_colon}  {formatted_plain_none if original_end is None else DateTimeIntoNotionFormat(original_end, date_only=True)} {formatted_right_arrow} {DateTimeIntoNotionFormat(end_alt, date_only=True)}")
        print(f"{formatted_startend} {formatted_colon}  {formatted_plain_none} {formatted_right_arrow} {DateTimeIntoNotionFormat(start_alt, date_only=True)}\n")
    if total_count_alternate_alldayevent_start > 0 and not no_pages_operated_B:
        print(f"\n{formatted_condition_met} {formatted_colon} '{formatted_italic.format('End')}' and '{formatted_italic.format('StartEnd')}' are {formatted_all_none} {formatted_semicolon}\n                '{formatted_italic.format('Start')}' is {formatted_explicitly_set_0000}")
        print(f"\nTotal Pages set {formatted_alternate_alldayevent} {formatted_colon} {formatted_count.format(total_count_alternate_alldayevent_start)}\n\n\n")
        page_printed = True


    for details in alldayevent_details:
        formatted_task, formatted_start, formatted_end, formatted_startend, page_title, start_alt, end_alt, prev_start, prev_end = details
        print(f"{formatted_task}     {formatted_colon}  {formatted_BOLD_italic.format(page_title)}")        
        if prev_start.date() != start_alt.date():
            # Print prev_start, formatted_right_arrow, and start_alt when dates are different
            print(f"{formatted_start}    {formatted_colon}  {DateTimeIntoNotionFormat(prev_start, date_only=True, time_format='24')} {formatted_right_arrow} {DateTimeIntoNotionFormat(start_alt, date_only=True, time_format='24')}")
        elif prev_start.time() == start_alt.time():
            # Strip off 00:00 from prev_start and remove formatted_right_arrow and start_alt
            print(f"{formatted_start}    {formatted_colon}  {DateTimeIntoNotionFormat(prev_start, date_only=True, time_format='24')}")
        if prev_end.date() != end_alt.date():
            # Print prev_end, formatted_right_arrow, and end_alt when dates are different
            print(f"{formatted_end}      {formatted_colon}  {DateTimeIntoNotionFormat(prev_end, date_only=True, time_format='24')} {formatted_right_arrow} {DateTimeIntoNotionFormat(end_alt, date_only=True, time_format='24')}")
        elif prev_end.time() == end_alt.time():
            # Strip off 00:00 from prev_end and remove formatted_right_arrow and end_alt
            print(f"{formatted_end}      {formatted_colon}  {DateTimeIntoNotionFormat(prev_end, date_only=True, time_format='24')}")
        end_date_formatted = DateTimeIntoNotionFormat(end_alt, date_only=True)
        start_date_formatted = str(DateTimeIntoNotionFormat(start_alt, date_only=True)).strip()
        if start_date_formatted == end_date_formatted:
            print(f"{formatted_startend} {formatted_colon}  {formatted_plain_previous} {formatted_right_arrow} {start_date_formatted}\n")
        else:
            print(f"{formatted_startend} {formatted_colon}  {formatted_plain_previous} {formatted_right_arrow} {start_date_formatted} — {end_date_formatted}\n")

    single_field = ""
    diff_field = ""            

    if total_count_alldayevent > 0 and not no_pages_operated_B:
        event_label = formatted_alldayevent if start_date_formatted == end_date_formatted else formatted_alldaysevent
        # Check conditions to set field_name
        if prev_start != start_alt:
            single_field = "'Start'"
            diff_field = "'End' + 'StartEnd'"
        elif prev_end != end_alt:
            single_field = "'End'"
            diff_field = "'Start' + 'StartEnd'"
        print(f"\n{formatted_condition_met} {formatted_colon} {formatted_italic.format(single_field)} {formatted_changed} {formatted_as} {formatted_single_date} {formatted_semicolon}\n                {formatted_italic.format(diff_field)} are Same")
        print(f"\nTotal Pages {formatted_overwritten} {formatted_as} {event_label} {formatted_colon} {formatted_count.format(total_count_alldayevent)}\n\n\n")
        page_printed = True

    def process_pages_filled_details(pages_filled_details):
        page_printed = False
        for updated_details in pages_filled_details:
            task, start_new, end_new, original_start, original_end, extra, updated_start_end, start, end = updated_details
            print(f"{formatted_task}     {formatted_colon}  {formatted_BOLD_italic.format(task)}")
            print(f"{formatted_start}    {formatted_colon}  {formatted_plain_none + '  ' if original_start is None and original_end is not None or original_start is None and original_end is None and extra is not None else DateTimeIntoNotionFormat(start_new, date_only=False, time_format='24') if original_start is not None else ''}{' ' if original_start is None and start_new is None else ''}{formatted_right_arrow + '  ' if original_start is None and original_end is not None or original_start is None and original_end is None and extra is not None else ''}{' ' if start_new is None else ''}{formatted_plain_none if start_new is None else DateTimeIntoNotionFormat(start_new, date_only=False, time_format='24') if start_new != original_start else ''} ")
            print(f"{formatted_end}      {formatted_colon}  {formatted_plain_none + '  ' if original_end is None and original_start is not None or original_end is None and original_start is None and extra is not None else DateTimeIntoNotionFormat(end_new, date_only=False, time_format='24') if original_end is not None else ''}{' ' if original_end is None and end_new is None else ''}{formatted_right_arrow + '  ' if original_end is None and original_start is not None or original_end is None and original_start is None and extra is not None else ''}{' ' if end_new is None else ''}{formatted_plain_none if end_new is None else DateTimeIntoNotionFormat(end_new, date_only=False, time_format='24') if end_new != original_end and start_new != end_new or original_end == original_start or original_end is None else ''}")
            if isinstance(start_new, datetime) and isinstance(end_new, datetime):
                if start_new.date() == end_new.date():
                    # If they are, format the end date to only show the time
                    end_date_formatted = end_new.strftime('%-H:%M')
                    if end_date_formatted.startswith('00:'):
                        end_date_formatted = end_date_formatted.lstrip('0')
                else:
                    end_date_formatted = DateTimeIntoNotionFormat(end_new, date_only=False, time_format='24')
            else:
                end_date_formatted = None

            start_date_formatted = DateTimeIntoNotionFormat(start_new, date_only=False, time_format='24')
            
            if extra is not None:
                original_start_str = extra['start']
                original_end_str = extra['end']
            else:
                original_start_str = original_end_str = None
            # Parse the original_start_str into a datetime object
            if original_start_str is not None:
                original_start = parse(original_start_str)
                if original_start.time() == dt_time(0, 0) and original_start.tzinfo is not None and original_end_str is None:
                    start_str = original_start.strftime('%b %-d, %Y') + '  00:00'
                else:
                    start_str = DateTimeIntoNotionFormat(original_start_str, time_format='24')
            else:
                start_str = start_date_formatted

            if original_end_str is not None:
                end_str = DateTimeIntoNotionFormat(original_end_str, time_format='24')
            else:
                end_str = start_date_formatted
            print(f"{formatted_startend} {formatted_colon}  {formatted_plain_none + '  ' if extra is None else ''}{start_str + ' ' if original_start_str is not None and original_start_str == extra else ''}{'— ' + DateTimeIntoNotionFormat(original_end_str, time_format='24') if original_end_str is not None and original_end_str == original_start_str else ''}{formatted_right_arrow + '  ' if extra is None else ''}{start_str}  {'—  ' + (end_str) if end_str != start_str else ''}\n")
        none_field = ""
        present_field = ""
        if total_count_pages_filled > 0 and not no_pages_operated_B:
            # Check conditions to set field_name to 'Start' or 'End'
            if extra is None:
                none_field = "'StartEnd'"
                present_field = "'Start' + 'End'"
            elif original_start is None and original_end is not None:
                none_field = "'Start'"
                present_field = "'End' + 'StartEnd'"
            elif original_end is None and original_start is not None:
                none_field = "'End'"
                present_field = "'Start' + 'StartEnd'"
            elif original_start is None and original_end is None and extra is not None:
                none_field = "'Start' + 'End'"
                present_field = "'StartEnd'"
            # Use field_name in the format function
            print(f"\n{formatted_condition_met} {formatted_colon} {formatted_italic.format(none_field)} {formatted_BOLD_italic.format('being')} {formatted_none} {formatted_semicolon}")
            print(f"                {formatted_italic.format(present_field)} {formatted_have_time}")
            print(f"\nTotal Pages where '{formatted_italic.format('None')}' {formatted_is_filled_accordingly} : {formatted_count.format(total_count_pages_filled)}\n\n\n")
            page_printed = True
        return page_printed
    
    page_printed = process_pages_filled_details(pages_filled_details)

    for details in pages_single_dates_details:
        formatted_task, formatted_prev_start, formatted_prev_end, formatted_original_start, formatted_original_end, start_end_formatted, page_title, new_start_value, new_end_value, prev_start, prev_end = details
        print(f"{formatted_task}     {formatted_colon}  {formatted_BOLD_italic.format(page_title)}")
        if prev_start == None:
            print(f"{formatted_start}    {formatted_colon}  {DateTimeIntoNotionFormat(new_start_value, date_only=True, time_format='24')}")
        else:
            print(f"{formatted_start}    {formatted_colon}  {formatted_prev_start}  {formatted_right_arrow}  {DateTimeIntoNotionFormat(new_start_value, date_only=True, time_format='24')}")
        if prev_end == None:
            print(f"{formatted_end}      {formatted_colon}  {DateTimeIntoNotionFormat(new_end_value, date_only=True, time_format='24')}")
        else:
            print(f"{formatted_end}      {formatted_colon}  {formatted_prev_end}  {formatted_right_arrow}  {DateTimeIntoNotionFormat(new_end_value, date_only=True, time_format='24')}")
        print(f"{formatted_startend} {formatted_colon}  {start_end_formatted}\n")
    if total_count_pages_single_dates > 0 and not no_pages_operated_B:
        # Print the count of pages where 'StartEnd' is filled accordingly 'Start' and 'End' Single-Dates
        
        if new_end_value.date() != new_start_value.date():
            plural_dates = formatted_s
        else:
            plural_dates = ''
        print(f"\n{formatted_condition_met} {formatted_colon}  Only '{formatted_italic.format('StartEnd')}' is {formatted_none} {formatted_semicolon}")
        print(f"                '{formatted_italic.format('Start')}' and '{formatted_italic.format('End')}' {formatted_have_single_date} {formatted_semicolon} but {formatted_no_time}")
        print(f"\nTotal Pages where '{formatted_italic.format('StartEnd')}' {formatted_is_filled_single_date}{plural_dates} accordingly '{formatted_italic.format('Start')}' and '{formatted_italic.format('End')}' Default Time {formatted_colon} {formatted_count.format(total_count_pages_single_dates)}\n\n\n")
        page_printed = True

    def process_pages_overwritten_details(pages_overwritten_details):
        page_printed = False
        for details in pages_overwritten_details:
            formatted_task, formatted_start, formatted_end, formatted_startend, page_title,original_start, original_end, start_value, end_value, prev_start_value, prev_end_value = details
            start_end = (start_value, end_value)
            print(f"{formatted_task}     {formatted_colon}  {formatted_BOLD_italic.format(page_title)}")                   
            print(f"{formatted_start}    {formatted_colon}  {formatted_plain_none if start_value is None else DateTimeIntoNotionFormat(prev_start_value, date_only=prev_start_value.time() == dt.time(0, 0), time_format='24')} {formatted_right_arrow if start_value is not None and prev_start_value is not None and start_value != prev_start_value else ''} {start_value.strftime('%H:%M') if start_value is not None and prev_start_value is not None and start_value.date() == prev_start_value.date() else DateTimeIntoNotionFormat(start_value, date_only=False, time_format='24') if start_value is not None and prev_start_value is not None and start_value != prev_start_value else '' if start_value is not None else ''}")
            print(f"{formatted_end}      {formatted_colon}  {formatted_plain_none if end_value is None else DateTimeIntoNotionFormat(prev_end_value, date_only=prev_end_value.time() == dt.time(0, 0), time_format='24')} {formatted_right_arrow if end_value is not None and prev_end_value is not None and end_value != prev_end_value else ''} {'' if end_value is not None and prev_end_value is not None and end_value == prev_end_value else end_value.strftime('%H:%M') if end_value is not None and prev_end_value is not None and end_value.date() == prev_end_value.date() else DateTimeIntoNotionFormat(end_value, date_only=False, time_format='24') if end_value is not None and prev_end_value is not None and end_value != prev_end_value else ''}")
            # Ensure 'start_end' is a tuple of datetime objects
            if start_end is not None and isinstance(start_end[0], str):
                start_end = (start_value, end_value)
            
            if start_end[0].date() == start_end[1].date():
                if start_end[1].hour > 9:
                    end_date_formatted = start_end[1].strftime('%H:%M')
                else:
                    end_date_formatted = start_end[1].strftime('%H:%M')
            else:
                end_date_formatted = DateTimeIntoNotionFormat(start_end[1], date_only=False, plus_time=True, time_format='24')
            startend_changed = start_end[0] != prev_start_value or start_end[1] != prev_end_value

            startend_string = f"{formatted_startend} {formatted_colon}"
            if startend_changed:
                startend_string += f"  {formatted_plain_previous} {formatted_right_arrow}"
            startend_string += f"  {DateTimeIntoNotionFormat(start_end[0], date_only=False, plus_time=True, show_midnight=True, time_format='24')}  —  {end_date_formatted}\n"
            print(startend_string)
                    
            # Initialize initially_modified as None
            initially_modified = None

            # Store the original values of 'Start' and 'StartEnd'
            original_start_value = original_start
            original_start_end_value = start_end[0]

            # Check if 'Start' is modified
            start_modified = start_value != original_start_value

            # Check if 'End' is modified
            end_modified = end_value != original_end

            # Check if 'StartEnd' is modified
            start_end_modified = prev_end_value == original_end and prev_start == original_start and start_end[0] != original_start_end_value or start_end[1] != original_end

            # Determine which value was initially modified
            if start_modified:
                initially_modified = "'Start' and 'StartEnd'" + ' ' + formatted_are
                if start_end_modified:
                    initially_modified = "'StartEnd'" + ' ' + formatted_is
            elif end_modified:
                initially_modified = "'End' and 'StartEnd'" + ' ' + formatted_are
            elif start_end_modified:
                initially_modified = "'StartEnd'" + ' ' + formatted_is

        if total_count_pages_overwritten > 0 and not no_pages_operated_B:
            print(f"{formatted_condition_met} {formatted_colon}  'All' {formatted_has_time} {formatted_semicolon}")
            print(f"                 {formatted_italic.format(initially_modified)} {formatted_initially_modified}")
            print(f"\nTotal Pages {formatted_overwritten} : {formatted_count.format(total_count_pages_overwritten)}\n\n\n")
            page_printed = True
        return page_printed
    
    page_printed = process_pages_overwritten_details(pages_overwritten_details)

    page_printed = True
    if page_printed:            
        no_pages_operated_B = True

    # After the loop, you can get the total number of modified pages like this:
    result['total_pages_modified'] = len(modified_pages)

    # This is the end of the loop #

if page['id'] not in processed_pages:
    executor = ThreadPoolExecutor(max_workers=1)
    future = executor.submit(process_pages_condition_A, page, result['counts'], result['details'].get('set_Default_details', []), result['details'].get('auto_default_setting_details', []), result['details'].get('set_Alternate_alldayevent_start_details', []), result['details'].get('pages_filled_details', []), lock, processed_pages)
    try:
        result = future.result(timeout=10.0)  # Wait at most 5 seconds
        if 'details' not in result:
            result['details'] = {'set_Default_details': [], 'auto_default_setting_details': [], 'set_Alternate_alldayevent_start_details': [], 'pages_filled_details': [], 'pages_single_dates_details': [], 'pages_overwritten_details': []}
    except TimeoutError:
        print("The function is taking longer than expected.")
        future.cancel()  # Cancel the future if it's taking too long
    except Exception as e:
        print(f"An error occurred: {type(e).__name__}, {e}")
        traceback.print_exc()  # Print the traceback
    finally:
        executor.shutdown()  # Always shutdown the executor when you're done

# After the threads have finished, you can get the results like this:
counts = {}  # Define the "counts" variable

while not return_values.empty():
    result = return_values.get()

# After the loop, you can get the total number of modified pages like this:
result['total_pages_modified'] = len(modified_pages)

if not no_pages_operated_B:
    print(f"{formatted_no} Condition is Met.\n{formatted_no} Operation is Performed.\n{formatted_no} Page is Modified\n")
else:
    print(f"Total Pages {formatted_modified} : {formatted_count.format(result['total_pages_modified'])}")

# Signal the dynamic_counter_indicator function to stop
stop_event.set()

# Wait for the separate thread to finish
thread.join()

# Erase the "Printing" message and the dots
print("\r" + " " * (len(f"{formatted_Printing} ") + total_dots + 10) + "\r", end="", flush=True)  # Clear the line and print spaces

print(f"{formatted_done} Processing.")

print('\n' + '-' * 70 + "\n" + ' ' * 29 + "End of Script\n" + '-' * 70)
        