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

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(os.environ['SIGNING_SECRET'], '/slack/events', app)

jenkins_job_url = "https://balanced-poorly-shiner.ngrok-free.app/generic-webhook-trigger/invoke?token=generic-webhook-trigger"

def trigger_jenkins_job():
    try:
        response = requests.get(jenkins_job_url)
        if response.status_code == 200:
            logging.info("Jenkins job triggered successfully")
            response_data = response.json()
            jobs = response_data.get('jobs', {})
            job_names = ', '.join(jobs.keys())
            return f"✦ {job_names}"
        else:
            logging.error(f"Failed to trigger Jenkins job. Status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        logging.error(f"Error triggering Jenkins job: {e}")
    return None

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
    
    trigger_jenkins_job()

    time.sleep(1)  # 等待确保Flask启动信息已经打印
    print("\r\033[K", end="")
    print("\n")  # 打印新行作为分隔

    start_dynamic_counter_indicator()

    try:
        flask_thread.join()
    except KeyboardInterrupt:
        stop_clear_and_print()