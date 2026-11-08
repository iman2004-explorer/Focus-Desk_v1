import json
import math
import os
import tempfile
import time
import uuid
from pathlib import Path


class FocusBackend:
    def __init__(self, storage_path=None):
        self.storage_path = Path(storage_path) if storage_path else (
            Path.home() / ".focus_desk" / "focus.json"
        )
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        self._data = {
            "items": [],
            "remaining_seconds": 0,
            "end_time": None,
            "active_session_seconds": 0,
            "completed_sessions": [],
            "daily_goal_minutes": 120,
            "profile_name": "",
            "profile_bio": "",
            "tasks": [],
            "alarms": [],
        }
        if self.storage_path.exists():
            stored_data = json.loads(self.storage_path.read_text(encoding="utf-8"))
            self._data.update(stored_data)
            self._validate_data()

    @property
    def items(self):
        return list(self._data["items"])

    @property
    def completed_sessions(self):
        return [dict(session) for session in self._data["completed_sessions"]]

    @property
    def daily_goal_minutes(self):
        return self._data["daily_goal_minutes"]

    @property
    def profile(self):
        return {
            "name": self._data["profile_name"],
            "bio": self._data["profile_bio"],
        }

    @property
    def tasks(self):
        return [dict(task) for task in self._data["tasks"]]

    @property
    def alarms(self):
        return [dict(alarm) for alarm in self._data["alarms"]]

    def add_task(self, title):
        if not isinstance(title, str):
            raise ValueError("Task title must be text")
        title = title.strip()
        if not title:
            raise ValueError("Task title cannot be empty")
        if len(title) > 200:
            raise ValueError("Task title must be 200 characters or fewer")
        task = {"id": uuid.uuid4().hex, "title": title, "completed": False}
        self._data["tasks"].append(task)
        self._save()
        return dict(task)

    def set_task_completed(self, task_id, completed):
        if not isinstance(completed, bool):
            raise ValueError("Task completion state must be a boolean")
        for task in self._data["tasks"]:
            if task["id"] == task_id:
                task["completed"] = completed
                self._save()
                return
        raise KeyError("Task not found")

    def delete_task(self, task_id):
        original_count = len(self._data["tasks"])
        self._data["tasks"] = [
            task for task in self._data["tasks"] if task["id"] != task_id
        ]
        if len(self._data["tasks"]) == original_count:
            raise KeyError("Task not found")
        self._save()

    def add_alarm(self, timestamp, label):
        if not isinstance(timestamp, (int, float)):
            raise ValueError("Alarm time must be a timestamp")
        if not isinstance(label, str):
            raise ValueError("Alarm label must be text")
        label = label.strip() or "Alarm"
        if len(label) > 100:
            raise ValueError("Alarm label must be 100 characters or fewer")
        alarm = {"id": uuid.uuid4().hex, "timestamp": float(timestamp), "label": label}
        self._data["alarms"].append(alarm)
        self._data["alarms"].sort(key=lambda item: item["timestamp"])
        self._save()
        return dict(alarm)

    def delete_alarms(self, alarm_ids):
        alarm_ids = set(alarm_ids)
        self._data["alarms"] = [
            alarm for alarm in self._data["alarms"] if alarm["id"] not in alarm_ids
        ]
        self._save()

    def take_due_alarms(self, now=None):
        now = time.time() if now is None else now
        due = [alarm for alarm in self._data["alarms"] if alarm["timestamp"] <= now]
        if due:
            due_ids = {alarm["id"] for alarm in due}
            self._data["alarms"] = [
                alarm for alarm in self._data["alarms"] if alarm["id"] not in due_ids
            ]
            self._save()
        return [dict(alarm) for alarm in due]

    def set_profile(self, name, bio):
        if not isinstance(name, str) or not isinstance(bio, str):
            raise ValueError("Profile name and bio must be text")
        name = name.strip()
        bio = " ".join(bio.split())
        if len(name) > 80:
            raise ValueError("Name must be 80 characters or fewer")
        if len(bio) > 160:
            raise ValueError("Bio must be 160 characters or fewer")
        self._data["profile_name"] = name
        self._data["profile_bio"] = bio
        self._save()

    def set_daily_goal(self, minutes):
        if not isinstance(minutes, int) or not 1 <= minutes <= 600:
            raise ValueError("Daily goal must be between 1 and 600 minutes")
        self._data["daily_goal_minutes"] = minutes
        self._save()

    def completed_focus_minutes(self, start_time, end_time):
        return sum(
            session["duration_seconds"] // 60
            for session in self._data["completed_sessions"]
            if start_time <= session["completed_at"] < end_time
        )

    def add_item(self, value):
        item = value.strip()
        if not item or any(existing.lower() == item.lower() for existing in self.items):
            return False
        self._data["items"].append(item)
        self._save()
        return True

    def remove_items(self, indexes):
        items = self._data["items"]
        for index in sorted(set(indexes), reverse=True):
            if 0 <= index < len(items):
                del items[index]
        self._save()

    def is_running(self):
        return self._data["end_time"] is not None and self.remaining_seconds() > 0

    def remaining_seconds(self):
        end_time = self._data["end_time"]
        if end_time is None:
            return self._data["remaining_seconds"]
        remaining = max(0, math.ceil(end_time - time.time()))
        if remaining == 0:
            session_seconds = self._data["active_session_seconds"]
            if session_seconds > 0:
                self._data["completed_sessions"].append(
                    {
                        "completed_at": end_time,
                        "duration_seconds": session_seconds,
                    }
                )
            self._data["active_session_seconds"] = 0
            self._data["end_time"] = None
            self._data["remaining_seconds"] = 0
            self._save()
        return remaining

    def pause(self):
        self._data["remaining_seconds"] = self.remaining_seconds()
        self._data["end_time"] = None
        self._save()

    def start_or_resume(self, minutes):
        if not 1 <= minutes <= 180:
            raise ValueError("Session length must be between 1 and 180 minutes")
        remaining = self.remaining_seconds()
        if remaining <= 0:
            remaining = minutes * 60
            self._data["active_session_seconds"] = remaining
        self._data["remaining_seconds"] = 0
        self._data["end_time"] = time.time() + remaining
        self._save()

    def _validate_data(self):
        if (
            not isinstance(self._data, dict)
            or not isinstance(self._data.get("items"), list)
            or not all(isinstance(item, str) for item in self._data["items"])
            or not isinstance(self._data.get("remaining_seconds"), int)
            or self._data["remaining_seconds"] < 0
            or not isinstance(self._data.get("active_session_seconds"), int)
            or self._data["active_session_seconds"] < 0
            or not isinstance(self._data.get("completed_sessions"), list)
            or any(
                not isinstance(session, dict)
                or not isinstance(session.get("completed_at"), (int, float))
                or not isinstance(session.get("duration_seconds"), int)
                or session["duration_seconds"] <= 0
                for session in self._data["completed_sessions"]
            )
            or not isinstance(self._data.get("daily_goal_minutes"), int)
            or not 1 <= self._data["daily_goal_minutes"] <= 600
            or not isinstance(self._data.get("profile_name"), str)
            or len(self._data["profile_name"]) > 80
            or not isinstance(self._data.get("profile_bio"), str)
            or len(self._data["profile_bio"]) > 160
            or not isinstance(self._data.get("tasks"), list)
            or any(
                not isinstance(task, dict)
                or not isinstance(task.get("id"), str)
                or not task["id"]
                or not isinstance(task.get("title"), str)
                or not task["title"].strip()
                or len(task["title"]) > 200
                or not isinstance(task.get("completed"), bool)
                for task in self._data["tasks"]
            )
            or not isinstance(self._data.get("alarms"), list)
            or any(
                not isinstance(alarm, dict)
                or not isinstance(alarm.get("id"), str)
                or not alarm["id"]
                or not isinstance(alarm.get("timestamp"), (int, float))
                or not isinstance(alarm.get("label"), str)
                or not alarm["label"].strip()
                for alarm in self._data["alarms"]
            )
            or (
                self._data.get("end_time") is not None
                and not isinstance(self._data["end_time"], (int, float))
            )
        ):
            raise ValueError("Focus data file has an invalid format")

    def _save(self):
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=self.storage_path.parent,
            delete=False,
        ) as temporary:
            json.dump(self._data, temporary, indent=2)
            temporary_path = Path(temporary.name)
        os.replace(temporary_path, self.storage_path)
