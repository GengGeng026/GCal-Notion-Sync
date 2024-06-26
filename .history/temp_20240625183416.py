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
from multiprocessing import Process, Event, Value
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
from tqdm import tqdm

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


def format_gradient(text, filled_length, gradient_state, bold_indices=None, less_visible_indices=None):
    # Assume BRIGHT, DIM, and RESET are defined constants for styling
    BRIGHT = "\033[1m"
    DIM = "\033[2m"
    RESET = "\033[0m"
    formatted_bar = ""
    for i, char in enumerate(text):
        if bold_indices and bold_indices[0] <= i < bold_indices[1]:
            formatted_bar += f"{BRIGHT}{char}{RESET}"
        elif less_visible_indices and less_visible_indices[0] <= i < less_visible_indices[1]:
            formatted_bar += f"{DIM}{char}{RESET}"
        else:
            formatted_bar += char
    return formatted_bar

# 保留您原有的函数定义不变
def animate_text_wave(text, repeat=1, sleep_time=0.01, continue_animation=lambda: False):
    length = len(text)
    animation_chars = ['/', '-', '\\', '|']
    while True:  # 添加一个外层循环，用于在需要时重复动画
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

                filled_length = 10  # Example value, adjust based on actual logic
                gradient_state = "some_state"

                # Apply gradient formatting to the wave text
                bold_start = max(0, int(i) - 1)
                bold_end = min(length, int(i) + 2)
                less_visible_start = max(0, int(i) - 3)
                less_visible_end = max(0, int(i) - 1)
                animated_text = format_gradient(wave_text, filled_length, gradient_state, bold_indices=(bold_start, bold_end), less_visible_indices=(less_visible_start, less_visible_end))
                
                sys.stdout.write(f"\r{animated_text}")
                sys.stdout.flush()
                time.sleep(sleep_time)
                i += 0.5  # 细腻控制迭代步进
                animation_index += 1  # 更新动画字符索引

            sys.stdout.write(f"\r{text}  ")  # 清除动画
            sys.stdout.flush()
            time.sleep(sleep_time)

        if not continue_animation():  # 检查是否继续动画
            break


class ProgressThread(threading.Thread):
    def __init__(self, total_size, phase_text=""):  # Add phase_text parameter with default value
        super().__init__()
        self.total_size = total_size
        self.downloaded_size = 0.0
        self.stop_event = threading.Event()
        self.gradient_state = 0
        self.phase_text = phase_text  # Set phase_text as an instance variable

    def run(self):
        while not self.stop_event.is_set():
            animate_text_wave(self.phase_text, repeat=1) 
            percent_complete = (self.downloaded_size / self.total_size) * 100
            bar_length = 50
            filled_length = int(bar_length * self.downloaded_size // self.total_size)
            
            bar = "━" * filled_length + " " * (bar_length - filled_length)  # Fixed missing symbol for unfilled part
            formatted_bar = format_gradient(bar, filled_length, self.gradient_state)
            
            sys.stdout.write(f'\r   {formatted_bar} {percent_complete:.1f}%')
            sys.stdout.flush()

            if self.downloaded_size >= self.total_size:
                self.stop()
                break

            time.sleep(0.01)  # Decrease sleep time for smoother updates
            self.gradient_state += 1

    def update_progress(self, size):
        self.downloaded_size += size
        if self.downloaded_size >= self.total_size:
            self.stop()

    def stop(self):
        self.stop_event.set()

def update_progress(size, progress_thread, updates, sleep_time=0.02, phase_text=""):
    for _ in range(updates):
        animate_text_wave(phase_text, repeat=1)  # 在更新进度条前显示动画文本
        progress_thread.update_progress(size)
        time.sleep(sleep_time)
        if progress_thread.stop_event.is_set():
            break

# Example usage
total_size = 5.0  # Use float for total size
progress_thread = ProgressThread(total_size)
progress_thread.start()

phases = [("initializing", 10), ("checking", 20), ("modifying", 30), ("updating", 40), ("finishing", 50)]
for phase, updates in phases:
    animate_text_wave(phase, repeat=5)
    size = 0.1  # Placeholder value for the size to add per update
    update_progress(size, progress_thread, updates)  # Corrected call

progress_thread.stop()