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

def dynamic_counter_indicator(stop_event, message, start_percent=30, updates=[]):
    global total_dots
    current_percent = start_percent
    update_index = 0
    print(f"{BOLD}{COLORS['C2']}{message} {current_percent}%{RESET}", end="", flush=True)
    total_dots = len(message) + len(str(current_percent)) + 1  # 初始消息长度
    while not stop_event.is_set() and current_percent <= 100:
        tm.sleep(0.10)  # 模拟加载时间
        current_percent += 1
        if update_index < len(updates) and current_percent == updates[update_index][0]:
            message = updates[update_index][1]
            update_index += 1
        print("\r" + " " * total_dots + "\r", end="", flush=True)  # 清除之前的输出
        print(f"{BOLD}{COLORS['C2']}{current_percent}% {message}{RESET}", end="", flush=True)
        total_dots = len(str(current_percent)) + len(message) + 2  # 更新总点数
        sys.stdout.flush()
    print()  # 打印换行，以便在循环结束后输出不会混乱

stop_event = threading.Event()
updates = [
    (31, "updating"),
    (33, "updating"),
    (56, "modifying"),
    (100, "finishing")
]
thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event, "Loading", 30, updates))
thread.start()

# 为了演示，这里等待一段时间后停止线程
tm.sleep(10)
stop_event.set()
thread.join()



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