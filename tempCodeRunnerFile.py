
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

# Define a function to print the "Printing" message and dots
def dynamic_counter_indicator(stop_event):
    dot_counter = 0
    total_dots = 0  # New variable to keep track of the total number of dots
    
    while not stop_event.is_set():
        tm.sleep(0.45)  # Wait for 0.3 second
        print(f"{formatted_dot}", end="", flush=True)  # Print the colored dot
        dot_counter += 1
        total_dots += 1  # Increment the total number of dots

        # If the counter reaches 4, reset it and erase the dots
        if dot_counter == 4:
            terminal_width = os.get_terminal_size().columns  # Get the width of the terminal
            print("\r" + " " * min(len(f"") + total_dots + 10, terminal_width) + "\r", end="", flush=True)  # Clear the line and print spaces
            dot_counter = 0
            if stop_event.is_set():  # Check if stop_event is set immediately after resetting the dot_counter
                break
    print("\n", end="")  # Print a newline character at the end of the loop
    tm.sleep(0.10)  # Add a small delay
    
# Create a stop event
stop_event = threading.Event()

# Start the separate thread
thread = threading.Thread(target=dynamic_counter_indicator, args=(stop_event,))
thread.start()


def send_message(channel_id):
    global message_sent, timer, message_queue

    # 如果消息尚未发送，并且队列中有消息，则发送消息
    if not message_sent and not message_queue.empty():
        message = message_queue.get()
        client.chat_postMessage(channel=channel_id, text=message)  # 使用 Slack 客户端发送消息
        message_sent = True

    # 重置定时器和 message_sent 标志
    timer = None
    message_sent = False

@app.route('/')
def home():
    return "Flask server is running"


if __name__ == '__main__':
    app.run(debug=True, use_reloader=False, port=8080)
    
# Signal the dynamic_counter_indicator function to stop
stop_event.set()

# Wait for the separate thread to finish
thread.join()