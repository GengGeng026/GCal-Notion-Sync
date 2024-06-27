import os
from dotenv import load_dotenv
from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
import anthropic

# 加载 .env 文件
load_dotenv()

# 设置环境变量
SLACK_BOT_TOKEN = os.getenv("SLACK_CLAUDE_BOT_TOKEN")  # 注意这里使用了您的自定义名称
SLACK_APP_TOKEN = os.getenv("SLACK_APP_TOKEN")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")

# 检查必要的环境变量是否存在
if not all([SLACK_BOT_TOKEN, SLACK_APP_TOKEN, ANTHROPIC_API_KEY]):
    raise ValueError("缺少必要的环境变量。请检查您的 .env 文件。")

# 初始化 Slack app，明确指定 token
app = App(token=SLACK_BOT_TOKEN)

# 初始化 Anthropic 客户端
client = anthropic.Client(api_key=ANTHROPIC_API_KEY)

@app.event("app_mention")
def handle_mention(event, say):
    # 获取用户的消息
    user_message = event["text"]
    
    # 调用 Claude API
    response = client.messages.create(
        model="claude-3-opus-20240229",
        max_tokens=1000,
        messages=[
            {"role": "user", "content": user_message}
        ]
    )
    
    # 发送 Claude 的回复到 Slack
    say(response.content[0].text)

if __name__ == "__main__":
    handler = SocketModeHandler(app, SLACK_APP_TOKEN)
    handler.start()