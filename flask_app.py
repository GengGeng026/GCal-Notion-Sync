import os
from pathlib import Path
from dotenv import load_dotenv
import requests
import slack
from flask import Flask, request, Response
from slackeventsapi import SlackEventAdapter
import re
import logging
import ssl
import certifi
import urllib.request

# Create a HTTPS handler with certifi's bundle of certificate authorities
https_handler = urllib.request.HTTPSHandler(context=ssl.create_default_context(cafile=certifi.where()))

# Create an opener that will use this handler
opener = urllib.request.build_opener(https_handler)

# Install the opener
urllib.request.install_opener(opener)

# Now, when you use urllib.request.urlopen, it will use the opener with certifi's bundle of certificate authorities
response = urllib.request.urlopen('https://example.com')

load_dotenv()

# 設置日誌的等級和格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 創建一個日誌處理器，將日誌寫入到文件中
handler = logging.FileHandler('/Users/mac/Desktop/GCal-Notion-Sync/log/app.log')
handler.setLevel(logging.INFO)

# 創建一個日誌格式器
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)

# 獲取 root logger，並添加我們剛剛創建的處理器
logger = logging.getLogger()
logger.addHandler(handler)

# 現在，你可以使用 logger.info() 和 logger.error() 來寫入日誌
logger.info('This is an info message.')
logger.error('This is an error message.')

# 獲取當前工作目錄
current_path = os.getcwd()

# .env 文件的絕對路徑
env_path = '/Users/mac/Documents/pythonProjects/Notion-and-Google-Calendar-2-Way-Sync-main/.env'

# 加載 .env 文件
load_dotenv(env_path)

app = Flask(__name__)
slack_event_adapter = SlackEventAdapter(
    os.environ['SIGNING_SECRET'], '/slack/events', app)

client = slack.WebClient(token=os.environ['SLACK_TOKEN'])
BOT_ID = client.api_call("auth.test")['user_id']

@slack_event_adapter.on('message')
def message(payload):
    event = payload.get('event', {})
    channel_id = event.get('channel')
    user_id = event.get('user')
    text = event.get('text')
    
    if BOT_ID != user_id:
        if any(keyword in text for keyword in ["Previous Start", "Previous End", "StarEnd"]):
            client.chat_postMessage(channel=channel_id, text="已更新 ✅ ")
        elif "edited in Tutorial Database" in text:  # 检查消息文本是否包含 "edited in Tutorial Database"
            trigger_status(user_id, channel_id, text)  # 调用触发Job的函数
        else:
            if text:  # 检查 text 变量是否不是空的
                client.chat_postMessage(channel=channel_id, text=text)


@app.route('/triggerjob', methods=['GET', 'POST'])
def triggerjob():
    if request.method == 'POST':
        data = request.form
    else:
        data = request.args

    user_id = data.get('user_id')
    channel_id = data.get('channel_id')
    client.chat_postMessage(channel=channel_id, text="I got the command")
    text = data.get('text')
    
    # Trigger the Jenkins job
    trigger_status(user_id, channel_id, text) 
    return Response(), 200

def trigger_status(user_id, channel_id, text):

    # 构建Jenkins Job的触发URL
    jenkins_job_url = "https://balanced-poorly-shiner.ngrok-free.app/generic-webhook-trigger/invoke?token=generic-webhook-trigger"

    # 发送请求触发Jenkins Job
    try:
        response = requests.get(jenkins_job_url)
    except requests.exceptions.RequestException as e:
        print(f"\n\nError: Failed to trigger Jenkins job: {e}")
        return

    # 检查响应状态码z
    if response.status_code == 200:
        
        # 解析 JSON 响应
        response_data = response.json()

        # 构建易读的消息
        jobs = response_data.get('jobs', {})
        job_names = ', '.join(jobs.keys())
        triggered_jobs = f"✦ {job_names}"
        
        # 使用正则表达式匹配用户名和对象名
        match_user = re.search(os.environ['USER_NAME'], text)
        match_script = re.search(os.environ['SCRIPT_NAME'], text)
        n = re.search(" and ", text)
        match_multiple = match_user and n and match_script or match_script and n and match_user
        action = re.search(" edited in", text)
        start = re.search("Start", text, re.DOTALL)
        end = re.search("End", text, re.DOTALL)
        previous_start = re.search("Previous Start", text, re.DOTALL)  # 使用 re.DOTALL 选项来匹配多行文本
        previous_end = re.search("Previous End", text, re.DOTALL)
        start_end = re.search("StarEnd", text, re.DOTALL)

        if (match_user and action and not start_end) or (match_user and not match_multiple and action):
            client.chat_postMessage(channel=channel_id, text=triggered_jobs + "\n我在替你更新時間。請稍等 · · ·")
        elif ((match_script or match_multiple) and action and not (start or end)):
            client.chat_postMessage(channel=channel_id, text="N. Database 已更新 ✅ ")

@app.route('/')
def home():
    return "Hi，歡迎來到 Flask"


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=8080)