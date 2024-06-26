import os
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
from multiprocessing import Process, Event
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
from googleapiclient.errors import HttpError
import googleapiclient.errors
from wcwidth import wcswidth
import traceback
import pprint
import shutil

###########################################################################
##### Print Tool Section. Will be used throughoout entire script. 
###########################################################################
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

def format_string(text, color=None, bold=False, italic=False, less_visible=False, underline=False, light_color=False):
    return f"{BOLD if bold else ''}{ITALIC if italic else ''}{LESS_VISIBLE if less_visible else ''}{UNDERLINE if underline else ''}{LIGHT_GRAY if light_color else ''}{COLORS[color] if color else ''}{text}{RESET}"

# Use the function to format text
formatted_dot = format_string('.', 'C2', bold=True)
formatted_BOLD_italic = format_string('{}', bold=True, italic=True)
formatted_right_arrow = format_string(' ▸ ', 'C2', bold=True)
formatted_indicator = format_string('{}', 'C2', bold=True)
formatted_successful = format_string('Successful', 'C2', bold=True)
formatted_added = format_string('Added', 'C2', bold=True)
formatted_updated = format_string('Updated', 'C2', bold=True, italic=True)
formatted_failed = format_string('Failed', 'C3', bold=True)
formatted_deleted = format_string('Deleted', 'C3', bold=True, italic=True)
formatted_title = format_string('Title', bold=True)
formatted_start = format_string('Start', bold=True)
formatted_end = format_string('End', bold=True)
formatted_startend = format_string('StartEnd', bold=True)
formatted_condition_met = format_string('Condition Met', bold=True)
formatted_no = format_string('No', bold=True, italic=True)
formatted_has_time = format_string('has time', bold=True, italic=True)
formatted_is_changed = format_string('have been Changed', bold=True, italic=True)
formatted_count = format_string('{}', 'C2', bold=True)
formatted_plus = format_string('+', 'C2', bold=True)
formatted_slash = format_string('/', 'C2', bold=True)
formatted_colon = format_string(':', 'C2', bold=True)
formatted_semicolon = format_string(';', 'C1', bold=True)
formatted_reset_default_setting = format_string('RESET accordingly Default Setting', 'C2', bold=True)
formatted_default_time = format_string('Default Time Range', 'C2', bold=True)
formatted_time_range = format_string('Time Range', 'C2', bold=True)
formatted_explicitly_set = format_string('Explicitly Set', bold=True)
formatted_explicitly_set_0000 = format_string('Explicitly set to 00:00', bold=True)
formatted_alldayevent = format_string('All-Day-Event', 'C2', bold=True)
formatted_alternate_alldayevent = format_string('Alternate All-Day-Event', 'C2', bold=True)
formatted_have_time = format_string('have Time', bold=True, italic=True)
formatted_have_single_date = format_string('have Single-Date', bold=True, italic=True)
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
formatted_nothing = format_string('Nothing', bold=True)
formatted_all_none = format_string('All None', 'C1', bold=True, italic=True)
formatted_modified = format_string('Modified', 'C2', bold=True)


def dynamic_counter_indicator(stop_event):
    while not stop_event.is_set():
        print(".", end="", flush=True)
        time.sleep(1)  # 模擬工作

if __name__ == "__main__":
    stop_event = Event()
    p = Process(target=dynamic_counter_indicator, args=(stop_event,))
    p.start()

    try:
        # 模擬腳本運行時間
        time.sleep(5)
    finally:
        stop_event.set()
        p.join()
        print("\n腳本結束")