import os
from dotenv import load_dotenv
import httpx
from notion_client import Client
from notion_client.errors import RequestTimeoutError
import pickle
import requests
import pytz
from pytz import timezone as pytz_timezone
from dateutil.parser import parse
from urllib.parse import urlparse
from datetime import datetime, timedelta, timezone, time
import time as tm
import time
import sys
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
from googleapiclient.errors import HttpError
import googleapiclient.errors
from wcwidth import wcswidth
import traceback
import pprint


# 假设 BOLD, COLORS, RESET, formatted_dot 已经在其他地方定义
BOLD = '\033[1m'
COLORS = {'C2': '\033[92m'}
RESET = '\033[0m'
formatted_dot = '.'

total_dots = 0
def print_dots(stop_event, prefix_length):
    dot_counter = 0
    while not stop_event.is_set():
        if dot_counter == 4:
            print("\r" + " " * (prefix_length + dot_counter) + "\r" + " " * prefix_length, end="", flush=True)
            dot_counter = 0
        else:
            print(".", end="", flush=True)
            dot_counter += 1
        time.sleep(0.5)  # 控制点的打印速度
        sys.stdout.flush()

def dynamic_counter_indicator(start_percent, end_percent, status):
    stop_event = threading.Event()
    prefix = f"{end_percent}% {status}"
    prefix_length = len(prefix)
    print(prefix, end="", flush=True)
    threading.Thread(target=print_dots, args=(stop_event, prefix_length)).start()
    
    for percent in range(start_percent, end_percent + 1):
        time.sleep(0.1)  # 模拟耗时操作
    stop_event.set()
    print("\r\033[K", end="")  # 清除当前行，为下一个 Part 做准备

# Part 1: 0 - 10% Checking
dynamic_counter_indicator(0, 10, "Checking")

# Part 2: 10% - 30% Inspecting
dynamic_counter_indicator(10, 30, "Inspecting")

# Part 3: 30% - 45% Modifying
dynamic_counter_indicator(30, 45, "Modifying")

# Part 4: 45% - 75% Updating
dynamic_counter_indicator(45, 75, "Updating")

# Part 5: 75% - 100% Finishing
dynamic_counter_indicator(75, 100, "Finishing")