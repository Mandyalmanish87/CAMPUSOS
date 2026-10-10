"""
CampusOS — Robust Backend Server (Pure Python Standard Library).
Completely avoids native DLL / pydantic Application Control blocking issues.
Provides all API endpoints (health, campus data, memories, posts, tasks, events, AI)
and serves static frontend files and 3D map.
"""
import cgi
import http.server
import json
import logging
import mimetypes
import os
import re
import socketserver
import sqlite3
import sys
import urllib.parse
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import ai_adapter
from config import CAMPUS_DATA_PATH, DB_PATH, STATIC_DIR
from database import connect_db, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("campusos")


def row_to_dict(row: sqlite3.Row) -> dict:
    return dict(row)


class CampusOSHandler(http.server.BaseHTTPRequestHandler):
    server_version = "CampusOS/2.0"

    def log_message(self, format, *args):
        log.info("%s - - [%s] %s", self.client_address[0], self.log_date_time_string(), format % args)

    def send_json(self, data: Any, status: int = 200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)

    def send_error_json(self, status: int, message: str):
        self.send_json({"detail": message, "error": True}, status=status)

    def read_json_body(self) -> Optional[dict]:
        content_length = int(self.headers.get("Content-Length", 0))
        if content_length == 0:
            return {}
        raw = self.rfile.read(content_length).decode("utf-8")
        try:
            return json.loads(raw)
        except Exception as e:
            log.warning("JSON parse error: %s", e)
            return None

    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, PATCH, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # Health
        if path == "/api/health":
            try:
                with connect_db() as conn:
                    conn.execute("SELECT 1").fetchone()
                db_status = "ok"
            except Exception as exc:
                self.send_json({"status": "error", "service": "CampusOS API", "database": "error", "detail": str(exc)}, status=503)
                return
            ai_ok = ai_adapter.check_model_available()
            self.send_json({
                "status": "ok",
                "service": "CampusOS API",
                "database": db_status,
                "ai_model": "gemma4:e4b" if ai_ok else "unavailable",
                "version": "2.0.0",
            })
            return

        # Campus data
        if path == "/api/campus/data":
            if not CAMPUS_DATA_PATH.exists():
                self.send_error_json(404, "Campus data file not found")
                return
            with open(CAMPUS_DATA_PATH, encoding="utf-8") as f:
                self.send_json(json.load(f))
            return

        # Memories list
        if path == "/api/memories":
            category = query.get("category", [None])[0]
            with connect_db() as conn:
                if category and category != "All":
                    rows = conn.execute("SELECT * FROM memories WHERE category = ? ORDER BY id DESC", (category,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM memories ORDER BY id DESC").fetchall()
            self.send_json([row_to_dict(r) for r in rows])
            return

        # Single memory: /api/memories/{id}
        m_mem = re.match(r"^/api/memories/(\d+)$", path)
        if m_mem:
            mid = int(m_mem.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM memories WHERE id = ?", (mid,)).fetchone()
            if not row:
                self.send_error_json(404, f"Memory with id={mid} not found")
                return
            self.send_json(row_to_dict(row))
            return

        # Posts list
        if path == "/api/posts":
            tag = query.get("tag", [None])[0]
            with connect_db() as conn:
                if tag and tag != "All":
                    rows = conn.execute("SELECT * FROM posts WHERE tag = ? ORDER BY id DESC", (tag,)).fetchall()
                else:
                    rows = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
            res = []
            for r in rows:
                d = row_to_dict(r)
                try:
                    d["replies"] = json.loads(d.get("replies_json") or "[]")
                except Exception:
                    d["replies"] = []
                res.append(d)
            self.send_json(res)
            return

        # Single post: /api/posts/{id}
        m_post = re.match(r"^/api/posts/(\d+)$", path)
        if m_post:
            pid = int(m_post.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
            if not row:
                self.send_error_json(404, f"Post with id={pid} not found")
                return
            d = row_to_dict(row)
            try:
                d["replies"] = json.loads(d.get("replies_json") or "[]")
            except Exception:
                d["replies"] = []
            self.send_json(d)
            return

        # Tasks list
        if path == "/api/tasks":
            with connect_db() as conn:
                rows = conn.execute("SELECT * FROM tasks ORDER BY completed ASC, due_date ASC").fetchall()
            self.send_json([row_to_dict(r) for r in rows])
            return

        # Single task: /api/tasks/{id}
        m_task = re.match(r"^/api/tasks/(\d+)$", path)
        if m_task:
            tid = int(m_task.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
            if not row:
                self.send_error_json(404, f"Task with id={tid} not found")
                return
            self.send_json(row_to_dict(row))
            return

        # Events list
        if path == "/api/events":
            with connect_db() as conn:
                rows = conn.execute("SELECT * FROM events ORDER BY when_date ASC").fetchall()
            self.send_json([row_to_dict(r) for r in rows])
            return

        # AI Status
        if path == "/api/ai/status":
            available = ai_adapter.check_model_available()
            self.send_json({
                "available": available,
                "model": "gemma4:e4b",
                "runtime": "Ollama",
                "message": "AI ready" if available else "Ollama is not running or model not loaded",
            })
            return

        # Static file serving & SPA fallback
        self.serve_static_file(path)

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.read_json_body()
        if body is None:
            self.send_error_json(400, "Invalid JSON body")
            return

        # Create memory
        if path == "/api/memories":
            title = str(body.get("title", "")).strip()
            if not title:
                self.send_error_json(422, "Title is required")
                return
            with connect_db() as conn:
                cur = conn.execute(
                    """INSERT INTO memories
                       (title, description, category, location_id, latitude, longitude, x, y, z, by_author, image_url)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (title, str(body.get("description", "")), str(body.get("category", "Spots")),
                     body.get("location_id"), body.get("latitude"), body.get("longitude"),
                     body.get("x"), body.get("y"), body.get("z"),
                     str(body.get("by_author", "Demo student")).strip(), str(body.get("image_url", ""))),
                )
                row = conn.execute("SELECT * FROM memories WHERE id = ?", (cur.lastrowid,)).fetchone()
            self.send_json(row_to_dict(row), status=201)
            return

        # Create post
        if path == "/api/posts":
            title = str(body.get("title", "")).strip()
            body_text = str(body.get("body", "")).strip()
            if not title or not body_text:
                self.send_error_json(422, "Title and body are required")
                return
            with connect_db() as conn:
                cur = conn.execute(
                    "INSERT INTO posts (author, tag, title, body) VALUES (?, ?, ?, ?)",
                    (str(body.get("author", "CampusOS Student")).strip(), str(body.get("tag", "Academics")), title, body_text),
                )
                row = conn.execute("SELECT * FROM posts WHERE id = ?", (cur.lastrowid,)).fetchone()
            d = row_to_dict(row)
            d["replies"] = []
            self.send_json(d, status=201)
            return

        # Reply to post
        m_reply = re.match(r"^/api/posts/(\d+)/reply$", path)
        if m_reply:
            import uuid
            pid = int(m_reply.group(1))
            text = str(body.get("text", "")).strip()
            if not text:
                self.send_error_json(422, "Reply text is required")
                return
            author = str(body.get("author", "CampusOS Student")).strip()
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
                if not row:
                    self.send_error_json(404, f"Post with id={pid} not found")
                    return
                replies = json.loads(row["replies_json"] or "[]")
                new_reply = {"id": str(uuid.uuid4())[:8], "author": author, "text": text}
                replies.append(new_reply)
                conn.execute(
                    "UPDATE posts SET replies_json = ?, updated_at = datetime('now') WHERE id = ?",
                    (json.dumps(replies), pid),
                )
                updated = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
            d = row_to_dict(updated)
            d["replies"] = replies
            self.send_json(d, status=201)
            return

        # Create task
        if path == "/api/tasks":
            title = str(body.get("title", "")).strip()
            if not title:
                self.send_error_json(422, "Task title is required")
                return
            with connect_db() as conn:
                cur = conn.execute(
                    "INSERT INTO tasks (title, course, due_date, priority) VALUES (?, ?, ?, ?)",
                    (title, str(body.get("course", "General")).strip(), str(body.get("due_date", "")), str(body.get("priority", "Normal"))),
                )
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
            self.send_json(row_to_dict(row), status=201)
            return

        # Create event
        if path == "/api/events":
            title = str(body.get("title", "")).strip()
            if not title:
                self.send_error_json(422, "Event title is required")
                return
            with connect_db() as conn:
                cur = conn.execute(
                    "INSERT INTO events (title, place, when_date, time_str, count) VALUES (?, ?, ?, ?, ?)",
                    (title, str(body.get("place", "")).strip(), str(body.get("when_date", "")), str(body.get("time_str", "")), int(body.get("count", 0))),
                )
                row = conn.execute("SELECT * FROM events WHERE id = ?", (cur.lastrowid,)).fetchone()
            self.send_json(row_to_dict(row), status=201)
            return

        # AI Summarize
        if path == "/api/ai/summarize":
            notes = str(body.get("notes", "")).strip()
            if len(notes) < 10:
                self.send_error_json(422, "Notes must be at least 10 characters")
                return
            result = ai_adapter.summarize_notes(notes)
            self.send_json(result)
            return

        # AI Question
        if path == "/api/ai/question":
            q = str(body.get("question", "")).strip()
            c = str(body.get("context", "")).strip()
            if not q or not c:
                self.send_error_json(422, "Question and context required")
                return
            result = ai_adapter.answer_question(q, c)
            self.send_json(result)
            return

        self.send_error_json(404, "Endpoint not found")

    def do_PATCH(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        body = self.read_json_body() or {}

        # Like memory
        m_like = re.match(r"^/api/memories/(\d+)/like$", path)
        if m_like:
            mid = int(m_like.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM memories WHERE id = ?", (mid,)).fetchone()
                if not row:
                    self.send_error_json(404, f"Memory with id={mid} not found")
                    return
                conn.execute("UPDATE memories SET likes = likes + 1, updated_at = datetime('now') WHERE id = ?", (mid,))
                updated = conn.execute("SELECT * FROM memories WHERE id = ?", (mid,)).fetchone()
            self.send_json(row_to_dict(updated))
            return

        # Vote post
        m_vote = re.match(r"^/api/posts/(\d+)/vote$", path)
        if m_vote:
            pid = int(m_vote.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
                if not row:
                    self.send_error_json(404, f"Post with id={pid} not found")
                    return
                conn.execute("UPDATE posts SET votes = votes + 1, updated_at = datetime('now') WHERE id = ?", (pid,))
                updated = conn.execute("SELECT * FROM posts WHERE id = ?", (pid,)).fetchone()
            d = row_to_dict(updated)
            try:
                d["replies"] = json.loads(d.get("replies_json") or "[]")
            except Exception:
                d["replies"] = []
            self.send_json(d)
            return

        # Toggle task
        m_ttog = re.match(r"^/api/tasks/(\d+)/toggle$", path)
        if m_ttog:
            tid = int(m_ttog.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
                if not row:
                    self.send_error_json(404, f"Task with id={tid} not found")
                    return
                new_val = 0 if row["completed"] else 1
                conn.execute("UPDATE tasks SET completed = ?, updated_at = datetime('now') WHERE id = ?", (new_val, tid))
                updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
            self.send_json(row_to_dict(updated))
            return

        # Update task
        m_tup = re.match(r"^/api/tasks/(\d+)$", path)
        if m_tup:
            tid = int(m_tup.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
                if not row:
                    self.send_error_json(404, f"Task with id={tid} not found")
                    return
                fields, vals = [], []
                if "title" in body:
                    fields.append("title = ?"); vals.append(str(body["title"]).strip())
                if "course" in body:
                    fields.append("course = ?"); vals.append(str(body["course"]).strip())
                if "due_date" in body:
                    fields.append("due_date = ?"); vals.append(str(body["due_date"]))
                if "priority" in body:
                    fields.append("priority = ?"); vals.append(str(body["priority"]))
                if fields:
                    fields.append("updated_at = datetime('now')")
                    vals.append(tid)
                    conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", vals)
                updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (tid,)).fetchone()
            self.send_json(row_to_dict(updated))
            return

        # RSVP event
        m_rsvp = re.match(r"^/api/events/(\d+)/rsvp$", path)
        if m_rsvp:
            eid = int(m_rsvp.group(1))
            with connect_db() as conn:
                row = conn.execute("SELECT * FROM events WHERE id = ?", (eid,)).fetchone()
                if not row:
                    self.send_error_json(404, f"Event with id={eid} not found")
                    return
                new_going = 0 if row["going"] else 1
                conn.execute("UPDATE events SET going = ?, updated_at = datetime('now') WHERE id = ?", (new_going, eid))
                updated = conn.execute("SELECT * FROM events WHERE id = ?", (eid,)).fetchone()
            self.send_json(row_to_dict(updated))
            return

        self.send_error_json(404, "Endpoint not found")

    def do_DELETE(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        m_mem = re.match(r"^/api/memories/(\d+)$", path)
        if m_mem:
            mid = int(m_mem.group(1))
            with connect_db() as conn:
                cur = conn.execute("DELETE FROM memories WHERE id = ?", (mid,))
                if cur.rowcount == 0:
                    self.send_error_json(404, f"Memory with id={mid} not found")
                    return
            self.send_json({"deleted": True, "id": mid})
            return

        m_post = re.match(r"^/api/posts/(\d+)$", path)
        if m_post:
            pid = int(m_post.group(1))
            with connect_db() as conn:
                cur = conn.execute("DELETE FROM posts WHERE id = ?", (pid,))
                if cur.rowcount == 0:
                    self.send_error_json(404, f"Post with id={pid} not found")
                    return
            self.send_json({"deleted": True, "id": pid})
            return

        m_task = re.match(r"^/api/tasks/(\d+)$", path)
        if m_task:
            tid = int(m_task.group(1))
            with connect_db() as conn:
                cur = conn.execute("DELETE FROM tasks WHERE id = ?", (tid,))
                if cur.rowcount == 0:
                    self.send_error_json(404, f"Task with id={tid} not found")
                    return
            self.send_json({"deleted": True, "id": tid})
            return

        m_event = re.match(r"^/api/events/(\d+)$", path)
        if m_event:
            eid = int(m_event.group(1))
            with connect_db() as conn:
                cur = conn.execute("DELETE FROM events WHERE id = ?", (eid,))
                if cur.rowcount == 0:
                    self.send_error_json(404, f"Event with id={eid} not found")
                    return
            self.send_json({"deleted": True, "id": eid})
            return

        self.send_error_json(404, "Endpoint not found")

    def serve_static_file(self, req_path: str):
        clean_path = req_path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"

        # Check in STATIC_DIR or current directory
        target = STATIC_DIR / clean_path
        if not target.exists() and clean_path.startswith("static/"):
            target = STATIC_DIR / clean_path[len("static/"):]

        if not target.exists() or target.is_dir():
            # SPA fallback: serve index.html
            target = STATIC_DIR / "index.html"

        if not target.exists():
            self.send_error_json(404, "File not found")
            return

        mime_type, _ = mimetypes.guess_type(str(target))
        if not mime_type:
            mime_type = "application/octet-stream"

        try:
            with open(target, "rb") as f:
                content = f.read()
            self.send_response(200)
            self.send_header("Content-Type", f"{mime_type}; charset=utf-8" if "text" in mime_type or "javascript" in mime_type else mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error_json(500, f"Error reading file: {e}")


class ThreadedTCPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    allow_reuse_address = True
    daemon_threads = True


def run_server(port: int = 8000, host: str = "127.0.0.1"):
    init_db()
    log.info("Starting CampusOS server on http://%s:%d", host, port)
    with ThreadedTCPServer((host, port), CampusOSHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            log.info("Shutting down server...")
            httpd.shutdown()


if __name__ == "__main__":
    port = 8000
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    run_server(port=port)
