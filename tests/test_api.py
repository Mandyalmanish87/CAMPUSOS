"""
CampusOS API automated tests.
Run from project root: python -m pytest tests/ -v
Requires: the FastAPI app importable (pip dependencies installed).
Uses TestClient (no live server needed for most tests).
"""
import json
import os
import sys
import tempfile
import pathlib

import pytest

# Patch config to use a temp DB for tests so we don't corrupt the live database
_tmp_dir = pathlib.Path(tempfile.mkdtemp())
os.environ["CAMPUSOS_DB_PATH"] = str(_tmp_dir / "test_campusos.db")

# Make sure project root is in path
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent))

from fastapi.testclient import TestClient

import config  # noqa: F401 — imported after env var set
config.DB_PATH = _tmp_dir / "test_campusos.db"

from app import app  # noqa: E402 — must come after config patch
from database import init_db  # noqa: E402

# Re-init DB with patched path for each test session
init_db()

client = TestClient(app)


# ── Health ──────────────────────────────────────────────────────────────────

class TestHealth:
    def test_health_ok(self):
        r = client.get("/api/health")
        assert r.status_code == 200
        data = r.json()
        assert data["status"] == "ok"
        assert data["database"] == "ok"
        assert "version" in data


# ── Campus data ──────────────────────────────────────────────────────────────

class TestCampusData:
    def test_returns_locations(self):
        r = client.get("/api/campus/data")
        assert r.status_code == 200
        data = r.json()
        assert "locations" in data
        assert len(data["locations"]) > 0

    def test_locations_have_required_fields(self):
        r = client.get("/api/campus/data")
        for loc in r.json()["locations"]:
            assert "id" in loc
            assert "name" in loc
            assert "category" in loc


# ── Memories ──────────────────────────────────────────────────────────────────

class TestMemories:
    def test_list_empty_initially(self):
        """Seed data may exist; just verify we get a list."""
        r = client.get("/api/memories")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_memory(self):
        r = client.post("/api/memories", json={
            "title": "Test memory",
            "description": "Under the library steps",
            "category": "Spots",
            "by_author": "Test student",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Test memory"
        assert data["category"] == "Spots"
        assert "id" in data
        return data["id"]

    def test_get_memory(self):
        # Create one first
        create_r = client.post("/api/memories", json={"title": "Fetch test", "description": "desc", "by_author": "A"})
        mid = create_r.json()["id"]
        r = client.get(f"/api/memories/{mid}")
        assert r.status_code == 200
        assert r.json()["title"] == "Fetch test"

    def test_get_nonexistent_memory(self):
        r = client.get("/api/memories/99999")
        assert r.status_code == 404

    def test_like_memory(self):
        create_r = client.post("/api/memories", json={"title": "Like test", "description": "d"})
        mid = create_r.json()["id"]
        r = client.patch(f"/api/memories/{mid}/like")
        assert r.status_code == 200
        assert r.json()["likes"] == 1

    def test_delete_memory(self):
        create_r = client.post("/api/memories", json={"title": "Delete test", "description": "d"})
        mid = create_r.json()["id"]
        r = client.delete(f"/api/memories/{mid}")
        assert r.status_code == 200
        assert r.json()["deleted"] is True
        # Verify gone
        r2 = client.get(f"/api/memories/{mid}")
        assert r2.status_code == 404

    def test_category_filter(self):
        client.post("/api/memories", json={"title": "Academic mem", "description": "d", "category": "Academic"})
        r = client.get("/api/memories?category=Academic")
        assert r.status_code == 200
        for m in r.json():
            assert m["category"] == "Academic"

    def test_title_required(self):
        r = client.post("/api/memories", json={"title": "", "description": "d"})
        assert r.status_code == 422


# ── Posts ─────────────────────────────────────────────────────────────────────

class TestPosts:
    def test_list_posts(self):
        r = client.get("/api/posts")
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    def test_create_post(self):
        r = client.post("/api/posts", json={
            "author": "Test User",
            "tag": "Academics",
            "title": "Test thread",
            "body": "This is a test thread body",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Test thread"
        assert data["replies"] == []

    def test_add_reply(self):
        create_r = client.post("/api/posts", json={"title": "Replyable", "body": "body"})
        pid = create_r.json()["id"]
        r = client.post(f"/api/posts/{pid}/reply", json={"author": "Replier", "text": "Hello"})
        assert r.status_code == 201
        assert len(r.json()["replies"]) == 1

    def test_vote_post(self):
        create_r = client.post("/api/posts", json={"title": "Votable", "body": "body"})
        pid = create_r.json()["id"]
        r = client.patch(f"/api/posts/{pid}/vote")
        assert r.status_code == 200
        assert r.json()["votes"] == 1

    def test_delete_post(self):
        create_r = client.post("/api/posts", json={"title": "Deletable post", "body": "b"})
        pid = create_r.json()["id"]
        r = client.delete(f"/api/posts/{pid}")
        assert r.status_code == 200


# ── Tasks ─────────────────────────────────────────────────────────────────────

class TestTasks:
    def test_list_tasks(self):
        r = client.get("/api/tasks")
        assert r.status_code == 200

    def test_create_task(self):
        r = client.post("/api/tasks", json={
            "title": "Submit assignment",
            "course": "CS101",
            "due_date": "2026-10-20",
            "priority": "High",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["title"] == "Submit assignment"
        assert data["completed"] == 0

    def test_toggle_task(self):
        create_r = client.post("/api/tasks", json={"title": "Toggle me"})
        tid = create_r.json()["id"]
        r = client.patch(f"/api/tasks/{tid}/toggle")
        assert r.status_code == 200
        assert r.json()["completed"] == 1
        # Toggle back
        r2 = client.patch(f"/api/tasks/{tid}/toggle")
        assert r2.json()["completed"] == 0

    def test_delete_task(self):
        create_r = client.post("/api/tasks", json={"title": "Temp task"})
        tid = create_r.json()["id"]
        r = client.delete(f"/api/tasks/{tid}")
        assert r.status_code == 200

    def test_nonexistent_task(self):
        r = client.get("/api/tasks/99999")
        assert r.status_code == 404


# ── Events ────────────────────────────────────────────────────────────────────

class TestEvents:
    def test_list_events(self):
        r = client.get("/api/events")
        assert r.status_code == 200

    def test_create_event(self):
        r = client.post("/api/events", json={
            "title": "Hackathon 2026",
            "place": "Main auditorium",
            "when_date": "2026-11-01",
            "time_str": "10:00 AM",
        })
        assert r.status_code == 201
        assert r.json()["title"] == "Hackathon 2026"

    def test_rsvp_toggle(self):
        create_r = client.post("/api/events", json={"title": "RSVP test event"})
        eid = create_r.json()["id"]
        r = client.patch(f"/api/events/{eid}/rsvp")
        assert r.status_code == 200
        assert r.json()["going"] == 1


# ── AI status endpoint ────────────────────────────────────────────────────────

class TestAI:
    def test_ai_status_returns_json(self):
        """AI status should always return 200 with 'available' key."""
        r = client.get("/api/ai/status")
        assert r.status_code == 200
        data = r.json()
        assert "available" in data
        assert "model" in data

    def test_summarize_short_notes_rejected(self):
        """Notes under 10 characters should fail Pydantic validation."""
        r = client.post("/api/ai/summarize", json={"notes": "short"})
        assert r.status_code == 422

    def test_summarize_returns_structure(self):
        """Summarize should always return success/error key, even if AI is offline."""
        r = client.post("/api/ai/summarize", json={"notes": "This is a long enough note body for the API to accept." * 3})
        assert r.status_code == 200
        data = r.json()
        assert "success" in data
        assert "model" in data


# ── Frontend served ───────────────────────────────────────────────────────────

class TestFrontend:
    def test_root_serves_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers.get("content-type", "")

    def test_campus_data_json_served(self):
        r = client.get("/static/data/campus_data.json")
        assert r.status_code == 200
