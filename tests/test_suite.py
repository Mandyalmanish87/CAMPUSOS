"""
CampusOS Automated Test Suite (Pure Python Standard Library).
Executes against the running server or directly via standard urllib.
Covers: Health, Campus Data, Memories CRUD, Posts, Tasks, Events, Static Files.
"""
import json
import unittest
import urllib.error
import urllib.parse
import urllib.request

BASE_URL = "http://127.0.0.1:8000"


def http_request(path: str, method: str = "GET", data: dict = None):
    url = f"{BASE_URL}{path}"
    headers = {"Content-Type": "application/json"}
    body = json.dumps(data).encode("utf-8") if data is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            content = resp.read().decode("utf-8")
            content_type = resp.headers.get("Content-Type", "")
            if "application/json" in content_type:
                return resp.status, json.loads(content)
            return resp.status, content
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8")
        try:
            return e.code, json.loads(err_body)
        except Exception:
            return e.code, err_body


class TestCampusOS(unittest.TestCase):

    def test_01_health_check(self):
        status, body = http_request("/api/health")
        self.assertEqual(status, 200)
        self.assertEqual(body.get("status"), "ok")
        self.assertEqual(body.get("database"), "ok")
        self.assertIn("ai_model", body)

    def test_02_campus_data(self):
        status, body = http_request("/api/campus/data")
        self.assertEqual(status, 200)
        self.assertIn("locations", body)
        self.assertGreater(len(body["locations"]), 5)
        # Check first landmark structure
        loc = body["locations"][0]
        self.assertIn("id", loc)
        self.assertIn("name", loc)
        self.assertIn("coords3d", loc)

    def test_03_memories_crud(self):
        # 1. Create memory
        new_mem = {
            "title": "Automated Test Pine Point",
            "description": "Sitting under pine trees during lunch break.",
            "category": "Spots",
            "by_author": "PyTest Runner",
        }
        status, created = http_request("/api/memories", method="POST", data=new_mem)
        self.assertEqual(status, 201)
        mem_id = created.get("id")
        self.assertIsNotNone(mem_id)
        self.assertEqual(created["title"], new_mem["title"])

        # 2. Get single memory
        status, fetched = http_request(f"/api/memories/{mem_id}")
        self.assertEqual(status, 200)
        self.assertEqual(fetched["id"], mem_id)

        # 3. Like memory
        status, liked = http_request(f"/api/memories/{mem_id}/like", method="PATCH")
        self.assertEqual(status, 200)
        self.assertEqual(liked["likes"], 1)

        # 4. Delete memory
        status, deleted = http_request(f"/api/memories/{mem_id}", method="DELETE")
        self.assertEqual(status, 200)
        self.assertTrue(deleted.get("deleted"))

        # 5. Verify deleted
        status, _ = http_request(f"/api/memories/{mem_id}")
        self.assertEqual(status, 404)

    def test_04_posts_crud_and_replies(self):
        # Create post
        new_post = {
            "title": "Study Group for Endsem",
            "body": "Anyone wants to prepare for Digital Electronics together at Library?",
            "tag": "Academics",
            "author": "NIT Student",
        }
        status, created = http_request("/api/posts", method="POST", data=new_post)
        self.assertEqual(status, 201)
        post_id = created["id"]

        # Reply to post
        reply_data = {"author": "Batchmate", "text": "Count me in! Meet at 5 PM."}
        status, updated = http_request(f"/api/posts/{post_id}/reply", method="POST", data=reply_data)
        self.assertEqual(status, 201)
        self.assertEqual(len(updated["replies"]), 1)
        self.assertEqual(updated["replies"][0]["text"], reply_data["text"])

        # Vote on post
        status, voted = http_request(f"/api/posts/{post_id}/vote", method="PATCH")
        self.assertEqual(status, 200)
        self.assertEqual(voted["votes"], 1)

        # Cleanup
        status, _ = http_request(f"/api/posts/{post_id}", method="DELETE")
        self.assertEqual(status, 200)

    def test_05_tasks_lifecycle(self):
        new_task = {
            "title": "Submit Assignment 2",
            "course": "Operating Systems",
            "due_date": "2026-10-18",
            "priority": "High",
        }
        status, created = http_request("/api/tasks", method="POST", data=new_task)
        self.assertEqual(status, 201)
        task_id = created["id"]
        self.assertEqual(created["completed"], 0)

        # Toggle task completion
        status, toggled = http_request(f"/api/tasks/{task_id}/toggle", method="PATCH")
        self.assertEqual(status, 200)
        self.assertEqual(toggled["completed"], 1)

        # Cleanup
        status, _ = http_request(f"/api/tasks/{task_id}", method="DELETE")
        self.assertEqual(status, 200)

    def test_06_events_rsvp(self):
        status, events = http_request("/api/events")
        self.assertEqual(status, 200)
        self.assertGreater(len(events), 0)
        first_event = events[0]
        event_id = first_event["id"]

        # Toggle RSVP
        status, rsvpd = http_request(f"/api/events/{event_id}/rsvp", method="PATCH")
        self.assertEqual(status, 200)
        self.assertNotEqual(first_event["going"], rsvpd["going"])

    def test_07_static_and_3d_map(self):
        # Verify index.html loads
        status, html = http_request("/")
        self.assertEqual(status, 200)
        self.assertIn("CampusOS", html)

        # Verify 3D map loads
        status, map_html = http_request("/static/campus_map_3d.html")
        self.assertEqual(status, 200)
        self.assertIn("three-canvas", map_html)

        # Verify local vendor assets load
        status, _ = http_request("/static/vendor/three.min.js")
        self.assertEqual(status, 200)
        status, _ = http_request("/static/vendor/react.production.min.js")
        self.assertEqual(status, 200)


if __name__ == "__main__":
    unittest.main()
