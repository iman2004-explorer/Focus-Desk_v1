import json
import tempfile
import threading
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from focus_backend import FocusBackend
from web_app import create_server


class WebAppTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        backend = FocusBackend(Path(self.directory.name) / "focus.json")
        self.server = create_server("127.0.0.1", 0, backend)
        self.thread = threading.Thread(target=self.server.serve_forever)
        self.thread.start()
        host, port = self.server.server_address
        self.base_url = "http://{}:{}".format(host, port)

    def tearDown(self):
        self.server.shutdown()
        self.thread.join()
        self.server.server_close()
        self.directory.cleanup()

    def request_json(self, path, method="GET", payload=None):
        data = None if payload is None else json.dumps(payload).encode("utf-8")
        request = Request(
            self.base_url + path,
            data=data,
            method=method,
            headers={"Content-Type": "application/json"} if data is not None else {},
        )
        with urlopen(request) as response:
            return response.status, json.loads(response.read())

    def test_static_dashboard_is_served(self):
        with urlopen(self.base_url + "/") as response:
            self.assertEqual(response.status, 200)
            self.assertIn(b"Focus Desk", response.read())

    def test_logo_image_is_served(self):
        with urlopen(self.base_url + "/logo.png") as response:
            self.assertEqual(response.status, 200)
            self.assertEqual(response.headers.get_content_type(), "image/png")
            self.assertTrue(response.read().startswith(b"\x89PNG\r\n\x1a\n"))

    def test_tasks_profile_and_distractions_use_saved_backend(self):
        _, created = self.request_json(
            "/api/tasks", "POST", {"title": "Read notes"}
        )
        task = created["task"]
        self.request_json(
            "/api/tasks/{}".format(task["id"]),
            "PATCH",
            {"completed": True},
        )
        self.request_json("/api/profile", "POST", {
            "name": "Maya",
            "bio": "Learning Python",
        })
        self.request_json(
            "/api/distractions", "POST", {"value": "Social media"}
        )

        _, state = self.request_json("/api/state")
        self.assertEqual(state["tasks"][0]["title"], "Read notes")
        self.assertTrue(state["tasks"][0]["completed"])
        self.assertEqual(state["profile"]["name"], "Maya")
        self.assertEqual(state["distractions"], ["Social media"])

        self.request_json(
            "/api/distractions", "DELETE", {"index": 0}
        )
        self.request_json(
            "/api/tasks/{}".format(task["id"]), "DELETE"
        )
        _, state = self.request_json("/api/state")
        self.assertEqual(state["tasks"], [])
        self.assertEqual(state["distractions"], [])

    def test_alarm_and_goal_api_validation(self):
        self.request_json(
            "/api/alarms", "POST", {"timestamp": 1, "label": "Past alarm"}
        )
        _, state = self.request_json("/api/state")
        self.assertEqual(state["due_alarms"][0]["label"], "Past alarm")
        self.assertEqual(state["alarms"], [])
        self.request_json("/api/goal", "POST", {"minutes": 180})
        _, state = self.request_json("/api/state")
        self.assertEqual(state["goal_minutes"], 180)

        with self.assertRaises(HTTPError) as error:
            self.request_json("/api/goal", "POST", {"minutes": 0})
        self.assertEqual(error.exception.code, 400)
        error.exception.close()

    def test_focus_timer_can_be_started_and_paused_over_api(self):
        _, result = self.request_json(
            "/api/focus/start", "POST", {"minutes": 1}
        )
        self.assertTrue(result["focus"]["running"])
        _, result = self.request_json("/api/focus/pause", "POST", {})
        self.assertFalse(result["focus"]["running"])
        self.assertGreater(result["focus"]["remaining_seconds"], 0)


if __name__ == "__main__":
    unittest.main()
