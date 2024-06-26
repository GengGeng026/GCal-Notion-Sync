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



###########################################################################
##### Print Tool Section. Will be used throughoout entire script. 
###########################################################################
print('\n' + '-' * 70 + '\n')

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

# 保留您原有的函数定义不变
def animate_text_wave(text, repeat=1, sleep_time=0.02):  # 调整睡眠时间以减慢动画速度
    length = len(text)
    animation_chars = ['/', '-', '\\', '|']  # 定义动画字符
    for _ in range(repeat):
        i = 0
        animation_index = 0  # 初始化动画字符索引
        while i < (length + 2):  # 使用浮点数进行迭代控制
            wave_text = ""
            for j in range(length):
                # 根据浮点数索引计算当前应该大写的字母
                if j >= i - 1 and j < i + 2:
                    wave_text += text[j].upper()
                else:
                    wave_text += text[j].lower()

            # 在 wave_text 的末尾添加动画字符
            current_animation_char = animation_chars[animation_index % len(animation_chars)]
            wave_text += " " + current_animation_char

            # Apply gradient formatting to the wave text
            bold_start = max(0, int(i) - 1)
            bold_end = min(length, int(i) + 2)
            less_visible_start = max(0, int(i) - 3)
            less_visible_end = max(0, int(i) - 1)
            animated_text = format_gradient(wave_text, bold_indices=(bold_start, bold_end), less_visible_indices=(less_visible_start, less_visible_end))
            
            sys.stdout.write(f"\r{animated_text}")
            sys.stdout.flush()
            time.sleep(sleep_time)
            i += 0.5  # 细腻控制迭代步进
            animation_index += 1  # 更新动画字符索引

        sys.stdout.write(f"\r{text}  ")  # 清除动画
        sys.stdout.flush()
        time.sleep(sleep_time)

# 添加的全局变量和新函数定义
global_progress = 0

def animate_text_wave_with_progress(*, text, new_text, target_percentage, current_progress=0, sleep_time=0.01, percentage_first=True):
    global global_progress
    length = len(text)
    animation_chars = ['/', '-', '\\', '|']
    total_iterations = 50
    iteration_step = (target_percentage - current_progress) / total_iterations
    animation_index = 0

    start_time = time.time()
    while current_progress < target_percentage:
        elapsed_time = time.time() - start_time
        if elapsed_time > 5:
            break

        wave_text = ""
        for i in range(length):
            wave_text += text[i].upper() if i % 2 == animation_index % 2 else text[i].lower()

        current_animation_char = animation_chars[animation_index % len(animation_chars)]
        progress_percentage = int(current_progress)
        if percentage_first:
            display_text = f"{progress_percentage}%  {new_text}  {current_animation_char}"
        else:
            display_text = f"{new_text}  {current_animation_char}  {progress_percentage}%"

        sys.stdout.write(f"\r{display_text}")
        sys.stdout.flush()

        current_progress += iteration_step
        animation_index += 1
        time.sleep(sleep_time)

    global_progress = target_percentage
    if percentage_first:
        final_text = f"{target_percentage}%  {new_text}"
    else:
        final_text = f"{new_text}  {target_percentage}%"
    sys.stdout.write(f"\r{final_text}")
    sys.stdout.flush()

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
    "C4": BLUE_BG,
    # Add more colors as needed
}

def format_string(text, color=None, bold=False, italic=False, less_visible=False):
    return f"{BOLD if bold else ''}{ITALIC if italic else ''}{LESS_VISIBLE if less_visible else ''}{COLORS[color] if color else ''}{text}{RESET}"

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


# 假设 BOLD, COLORS, RESET, formatted_dot 已经在其他地方定义
BOLD = '\033[1m'
COLORS = {'C2': '\033[92m'}
RESET = '\033[0m'
formatted_dot = '.'

total_dots = 0

def dynamic_counter_indicator(stop_event, message):
    dot_counter = 0
    total_dots = 0
    print(f"{BOLD}{COLORS['C2']}{message}{RESET}", end="", flush=True)
    while not stop_event.is_set():
        if dot_counter == 4:
            print("\r" + " " * (len(message) + total_dots + 5) + "\r", end="", flush=True)
            dot_counter = 0
            total_dots = 0  # 重置total_dots以避免溢出到下一行
        else:
            tm.sleep(0.10)
            print(formatted_dot, end="", flush=True)
            dot_counter += 1
            total_dots += 1
        sys.stdout.flush()  # 确保立即打印

stop_event = threading.Event()
thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event, ""))
thread.start()

def dynamic_counter_indicator(start_percent, end_percent, status):
    dot_count = 0  # 初始化点的计数器
    for percent in range(start_percent, end_percent + 1):
        dots = '.' * (dot_count % 4)  # 根据计数器的值决定点的数量
        print(f"{percent}% {status}", end='\r', flush=True)
        time.sleep(0.1)  # 模拟耗时操作
        dot_count += 1  # 更新点的计数器
    print("\r\033[K", end="")  # 清除当前行，为下一个 Part 做准备

# Part 1: 0 - 10% Checking
dynamic_counter_indicator(0, 10, "Checking")
print("\r\033[K", end="")

# Part 2: 10% - 30% Inspecting
dynamic_counter_indicator(10, 30, "Inspecting")
print("\r\033[K", end="")

# Part 3: 30% - 45% Modifying
dynamic_counter_indicator(30, 45, "Modifying")

# Part 4: 45% - 75% Updating
dynamic_counter_indicator(45, 75, "Updating")

# Part 5: 75% - 100% Finishing
dynamic_counter_indicator(75, 100, "Finishing")

# Stop the dynamic counter indicator after the time-consuming operation
stop_event.set()
thread.join()