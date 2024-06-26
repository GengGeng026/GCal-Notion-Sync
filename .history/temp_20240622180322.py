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

def dynamic_counter_indicator(start_percent, end_percent, status):
    for percent in range(start_percent, end_percent + 1):
        print(f"{percent}% {status}", end='\r', flush=True)
        time.sleep(0.1)  # 模拟耗时操作
    print()  # 打印换行，为下一个 Part 做准备


# Part 1: 0 - 10% Checking
dynamic_counter_indicator(0, 10, "Checking")
print("\r\033[K", end="")
# Part 2: 10% - 30% Inspecting
dynamic_counter_indicator(10, 30, "Inspecting")
print("\r\033[K", end="")
# Part 3: 30% - 45% Modifying
dynamic_counter_indicator(30, 45, "Modifying")
print("\r\033[K", end="")
# Part 4: 45% - 75% Updating
dynamic_counter_indicator(45, 75, "Updating")
print("\r\033[K", end="")
# Part 5: 75% - 100% Finishing
dynamic_counter_indicator(75, 100, "Finishing")