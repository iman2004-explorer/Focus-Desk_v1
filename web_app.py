import json
import mimetypes
import os
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlparse

from focus_backend import FocusBackend
from productivity_model import rate_productivity


WEB_DIR = Path(__file__).parent / "web"
MAX_REQUEST_BYTES = 16_384


def _today_range():
    now = datetime.now().astimezone()
    start = now.replace(hour=0, minute=0, second=0, microsecond=0).timestamp()
    end = (now + timedelta(days=1)).replace(
        hour=0, minute=0, second=0, microsecond=0
    ).timestamp()
    return start, end


def _app_state(backend):
    remaining = backend.remaining_seconds()
    due_alarms = backend.take_due_alarms()
    start, end = _today_range()
    completed_sessions = [
        session for session in backend.completed_sessions
        if start <= session["completed_at"] < end
    ]
    focus_minutes = backend.completed_focus_minutes(start, end)
    tasks = backend.tasks
    return {
        "profile": backend.profile,
        "tasks": tasks,
        "alarms": backend.alarms,
        "distractions": backend.items,
        "due_alarms": due_alarms,
        "focus": {
            "running": backend.is_running(),
            "remaining_seconds": remaining,
        },
        "goal_minutes": backend.daily_goal_minutes,
        "focus_minutes": focus_minutes,
        "rating": rate_productivity(focus_minutes, backend.daily_goal_minutes),
        "completed_sessions": completed_sessions,
    }


def create_server(host="127.0.0.1", port=8765, backend=None):
    data = backend or FocusBackend()

    class RequestHandler(BaseHTTPRequestHandler):
        server_version = "FocusDesk/1.0"

        def log_message(self, _format, *_args):
            return

        def _send_json(self, payload, status=200):
            content = json.dumps(payload).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def _send_file(self, filename):
            path = WEB_DIR / filename
            if not path.is_file():
                self._send_json({"error": "Web app assets are missing."}, 500)
                return
            content = path.read_bytes()
            content_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            if content_type.startswith("text/") or content_type in (
                "application/javascript", "application/json"
            ):
                content_type += "; charset=utf-8"
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Cache-Control", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(content)

        def _read_json(self):
            if self.headers.get_content_type() != "application/json":
                raise ValueError("Send request data as JSON.")
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as error:
                raise ValueError("Invalid request length.") from error
            if length < 1 or length > MAX_REQUEST_BYTES:
                raise ValueError("Request body must be between 1 and 16384 bytes.")
            try:
                return json.loads(self.rfile.read(length))
            except (json.JSONDecodeError, UnicodeDecodeError) as error:
                raise ValueError("Request body is not valid JSON.") from error

        def _handle_error(self, error):
            if isinstance(error, (ValueError, KeyError)):
                self._send_json({"error": str(error)}, 400)
            else:
                self._send_json({"error": "The request could not be completed."}, 500)

        def do_GET(self):
            path = urlparse(self.path).path
            if path == "/":
                self._send_file("index.html")
            elif path == "/styles.css":
                self._send_file("styles.css")
            elif path == "/app.js":
                self._send_file("app.js")
            elif path == "/api/state":
                try:
                    self._send_json(_app_state(data))
                except (ValueError, KeyError) as error:
                    self._handle_error(error)
            else:
                self._send_json({"error": "Not found."}, 404)

        def do_POST(self):
            path = urlparse(self.path).path
            try:
                payload = self._read_json()
                if not isinstance(payload, dict):
                    raise ValueError("Request body must be a JSON object.")

                if path == "/api/tasks":
                    task = data.add_task(payload.get("title", ""))
                    self._send_json({"task": task}, 201)
                elif path == "/api/profile":
                    data.set_profile(
                        payload.get("name", ""),
                        payload.get("bio", ""),
                    )
                    self._send_json({"profile": data.profile})
                elif path == "/api/goal":
                    minutes = payload.get("minutes")
                    if type(minutes) is not int:
                        raise ValueError("Daily goal must be a whole number.")
                    data.set_daily_goal(minutes)
                    self._send_json({"goal_minutes": data.daily_goal_minutes})
                elif path == "/api/focus/start":
                    minutes = payload.get("minutes")
                    if type(minutes) is not int:
                        raise ValueError("Session length must be a whole number.")
                    data.start_or_resume(minutes)
                    self._send_json({"focus": {
                        "running": True,
                        "remaining_seconds": data.remaining_seconds(),
                    }})
                elif path == "/api/focus/pause":
                    data.pause()
                    self._send_json({"focus": {
                        "running": False,
                        "remaining_seconds": data.remaining_seconds(),
                    }})
                elif path == "/api/alarms":
                    timestamp = payload.get("timestamp")
                    if isinstance(timestamp, bool) or not isinstance(timestamp, (int, float)):
                        raise ValueError("Alarm time must be a timestamp.")
                    alarm = data.add_alarm(timestamp, payload.get("label", "Alarm"))
                    self._send_json({"alarm": alarm}, 201)
                elif path == "/api/distractions":
                    value = payload.get("value")
                    if not isinstance(value, str):
                        raise ValueError("Distraction must be text.")
                    added = data.add_item(value)
                    self._send_json({"added": added, "distractions": data.items}, 201)
                else:
                    self._send_json({"error": "Not found."}, 404)
            except (ValueError, KeyError) as error:
                self._handle_error(error)

        def do_PATCH(self):
            path = urlparse(self.path).path
            task_id = path.removeprefix("/api/tasks/")
            if not task_id or "/" in task_id:
                self._send_json({"error": "Not found."}, 404)
                return
            try:
                payload = self._read_json()
                if not isinstance(payload, dict) or type(payload.get("completed")) is not bool:
                    raise ValueError("Task completion state must be true or false.")
                data.set_task_completed(task_id, payload["completed"])
                self._send_json({"ok": True})
            except (ValueError, KeyError) as error:
                self._handle_error(error)

        def do_DELETE(self):
            path = urlparse(self.path).path
            if path == "/api/distractions":
                try:
                    payload = self._read_json()
                    if not isinstance(payload, dict) or type(payload.get("index")) is not int:
                        raise ValueError("Distraction index must be a whole number.")
                    data.remove_items([payload["index"]])
                    self._send_json({"distractions": data.items})
                except (ValueError, KeyError) as error:
                    self._handle_error(error)
                return
            if path.startswith("/api/tasks/"):
                item_id = path.removeprefix("/api/tasks/")
                delete = data.delete_task
            elif path.startswith("/api/alarms/"):
                item_id = path.removeprefix("/api/alarms/")
                delete = lambda value: data.delete_alarms([value])
            else:
                self._send_json({"error": "Not found."}, 404)
                return
            if not item_id or "/" in item_id:
                self._send_json({"error": "Not found."}, 404)
                return
            try:
                delete(item_id)
                self._send_json({"ok": True})
            except (ValueError, KeyError) as error:
                self._handle_error(error)

    server = HTTPServer((host, port), RequestHandler)
    return server


def main():
    backend = FocusBackend(os.environ.get("FOCUS_DATA_PATH"))
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", "8765"))
    server = create_server(host, port, backend)
    address, port = server.server_address
    print("Focus Desk web app: http://{}:{}/".format(address, port))
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Focus Desk web app.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
