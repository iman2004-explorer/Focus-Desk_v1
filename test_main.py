import unittest
from unittest.mock import Mock

from main import Dashboard


class FocusCompletionMonitorTests(unittest.TestCase):
    def test_alarm_poll_completes_focus_session_after_focus_window_closes(self):
        class Backend:
            def __init__(self):
                self.completed_sessions = []

            def remaining_seconds(self):
                self.completed_sessions.append({
                    "completed_at": 1,
                    "duration_seconds": 60,
                })
                return 0

            def take_due_alarms(self):
                return []

        dashboard = Mock()
        dashboard.focus_backend = Backend()

        Dashboard._check_alarms(dashboard)

        self.assertEqual(len(dashboard.focus_backend.completed_sessions), 1)
        dashboard._refresh_productivity.assert_called_once_with()
        dashboard.after.assert_called_once_with(500, dashboard._check_alarms)

    def test_alarm_poll_does_not_refresh_when_focus_session_is_incomplete(self):
        class Backend:
            completed_sessions = []

            def remaining_seconds(self):
                return 30

            def take_due_alarms(self):
                return []

        dashboard = Mock()
        dashboard.focus_backend = Backend()

        Dashboard._check_alarms(dashboard)

        dashboard._refresh_productivity.assert_not_called()


if __name__ == "__main__":
    unittest.main()
