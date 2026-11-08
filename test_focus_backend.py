import tempfile
import unittest
from pathlib import Path
import json
from unittest.mock import patch

from focus_backend import FocusBackend


class FocusBackendTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.storage_path = Path(self.directory.name) / "focus.json"
        self.backend = FocusBackend(self.storage_path)

    def tearDown(self):
        self.directory.cleanup()

    def test_items_are_saved_and_duplicates_are_ignored(self):
        self.assertTrue(self.backend.add_item("  Browser  "))
        self.assertFalse(self.backend.add_item("browser"))

        reopened = FocusBackend(self.storage_path)
        self.assertEqual(reopened.items, ["Browser"])
        reopened.remove_items([0])
        self.assertEqual(FocusBackend(self.storage_path).items, [])

    def test_timer_can_pause_resume_and_expire(self):
        with patch("focus_backend.time.time", return_value=1000):
            self.backend.start_or_resume(1)
            self.assertTrue(self.backend.is_running())

        with patch("focus_backend.time.time", return_value=1012):
            self.backend.pause()
            self.assertEqual(self.backend.remaining_seconds(), 48)

        reopened = FocusBackend(self.storage_path)
        with patch("focus_backend.time.time", return_value=2000):
            reopened.start_or_resume(25)
            self.assertEqual(reopened.remaining_seconds(), 48)

        with patch("focus_backend.time.time", return_value=2048):
            self.assertFalse(reopened.is_running())
            self.assertEqual(reopened.remaining_seconds(), 0)

    def test_timer_rejects_out_of_range_durations(self):
        with self.assertRaises(ValueError):
            self.backend.start_or_resume(181)

    def test_completed_focus_sessions_are_recorded_and_persisted(self):
        with patch("focus_backend.time.time", return_value=1000):
            self.backend.start_or_resume(1)

        with patch("focus_backend.time.time", return_value=1060):
            self.assertEqual(self.backend.remaining_seconds(), 0)

        reopened = FocusBackend(self.storage_path)
        self.assertEqual(
            reopened.completed_focus_minutes(1000, 1100),
            1,
        )
        self.assertEqual(len(reopened.completed_sessions), 1)

    def test_daily_goal_is_validated_and_persisted(self):
        self.backend.set_daily_goal(180)
        self.assertEqual(FocusBackend(self.storage_path).daily_goal_minutes, 180)
        with self.assertRaises(ValueError):
            self.backend.set_daily_goal(0)

    def test_existing_focus_data_gets_productivity_defaults(self):
        self.storage_path.write_text(
            json.dumps({
                "items": ["Browser"],
                "remaining_seconds": 0,
                "end_time": None,
            }),
            encoding="utf-8",
        )
        migrated = FocusBackend(self.storage_path)
        self.assertEqual(migrated.items, ["Browser"])
        self.assertEqual(migrated.daily_goal_minutes, 120)
        self.assertEqual(migrated.completed_sessions, [])

    def test_profile_is_trimmed_normalized_and_persisted(self):
        self.backend.set_profile("  Maya Chen  ", " Learn Python\n every day ")
        reopened = FocusBackend(self.storage_path)
        self.assertEqual(
            reopened.profile,
            {"name": "Maya Chen", "bio": "Learn Python every day"},
        )

    def test_profile_rejects_fields_that_are_too_long(self):
        with self.assertRaises(ValueError):
            self.backend.set_profile("N" * 81, "")
        with self.assertRaises(ValueError):
            self.backend.set_profile("Name", "B" * 161)

    def test_tasks_can_be_added_completed_deleted_and_reopened(self):
        task = self.backend.add_task("  Study biology  ")
        self.backend.set_task_completed(task["id"], True)
        reopened = FocusBackend(self.storage_path)
        self.assertEqual(reopened.tasks[0]["title"], "Study biology")
        self.assertTrue(reopened.tasks[0]["completed"])
        reopened.delete_task(task["id"])
        self.assertEqual(FocusBackend(self.storage_path).tasks, [])

    def test_task_validation_and_missing_ids_are_reported(self):
        with self.assertRaises(ValueError):
            self.backend.add_task("  ")
        with self.assertRaises(KeyError):
            self.backend.delete_task("missing")

    def test_alarms_persist_and_due_alarms_are_consumed_once(self):
        alarm = self.backend.add_alarm(2000, "Study break")
        reopened = FocusBackend(self.storage_path)
        self.assertEqual(reopened.alarms[0]["label"], "Study break")
        self.assertEqual(reopened.take_due_alarms(1999), [])
        self.assertEqual(reopened.take_due_alarms(2000)[0]["id"], alarm["id"])
        self.assertEqual(reopened.take_due_alarms(2001), [])


if __name__ == "__main__":
    unittest.main()
