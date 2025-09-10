# app.py
import eventlet
eventlet.monkey_patch()

import config        # must set up basic logging & attach SocketLogger here
from flask import Flask, render_template, request
from flask_socketio import SocketIO
import asyncio
from core.curriculum import generate_curriculum
import logging

app = Flask(__name__, template_folder="templates", static_folder="static")

# Force eventlet mode
socketio = SocketIO(app, cors_allowed_origins="*", async_mode="eventlet")

# ─── SocketLogger handler ───
class SocketLogger(logging.Handler):
    def emit(self, record):
        msg = self.format(record)
        try:
            socketio.emit("log", msg)
        except Exception:
            self.handleError(record)

# attach before any other logging happens
socket_logger = SocketLogger()
socket_logger.setLevel(logging.INFO)
socket_logger.setFormatter(logging.Formatter("%(message)s"))
root = logging.getLogger()
root.addHandler(socket_logger)
root.setLevel(logging.INFO)

# Silence noisy loggers
logging.getLogger("werkzeug").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("openai").setLevel(logging.WARNING)

# Keep track of the greenlet
current_task = None


@app.route('/')
def index():
    return render_template("index.html")


@app.route("/generate", methods=["POST"])
def generate():
    global current_task
    topic = request.json.get("topic", "").strip()
    if not topic:
        return ("", 204)

    socketio.emit("log", f"▶️ Topic received: {topic}")

    # kill any previous run
    if current_task:
        current_task.kill()
        socketio.emit("log", "❌ Previous generation stopped")
        current_task = None

    # spawn a new greenlet
    current_task = eventlet.spawn(_do_generate, topic)
    return ("", 204)


def _do_generate(topic: str):
    socketio.emit("log", f"🛠 Starting to generate for {topic}…")

    # set up a fresh asyncio loop inside this greenlet
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(generate_curriculum(topic))
    except Exception as e:
        socketio.emit("log", f"❌ Generation error: {e}")
    finally:
        loop.close()

    socketio.emit("log", "✅ Finished generation!")


@socketio.on("stop_generation")
def stop_generation():
    global current_task
    if current_task:
        current_task.kill()
        socketio.emit("log", "❌ Generation stopped by user")
        current_task = None
    else:
        socketio.emit("log", "⚠️ No generation in progress")


if __name__ == "__main__":
    socketio.run(app, host="0.0.0.0", port=3531, debug=True)
