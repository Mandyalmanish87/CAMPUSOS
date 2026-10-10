"""
CampusOS — FastAPI backend.
Serves the existing frontend and all API routes.
"""
import json
import logging
import sqlite3
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import ai_adapter
from config import CAMPUS_DATA_PATH, DB_PATH, STATIC_DIR
from database import connect_db, init_db

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger("campusos")


# ── Lifespan ──────────────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(_: FastAPI):
    log.info("CampusOS starting — initialising database at %s", DB_PATH)
    init_db()
    log.info("Database ready")
    yield
    log.info("CampusOS shutting down")


# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="CampusOS API",
    version="2.0.0",
    description="Backend for CampusOS — NIT Hamirpur student companion",
    lifespan=lifespan,
)


# ── Pydantic schemas (pydantic v1 compatible) ─────────────────────────────────

def _str(min_l=0, max_l=None):
    """Return pydantic-v1-compatible type annotation for constrained str."""
    try:
        from pydantic import constr
        return constr(min_length=min_l, max_length=max_l, strip_whitespace=True)
    except Exception:
        return str


class MemoryCreate(BaseModel):
    title: str = Field(default=..., max_length=120)
    description: str = Field(default="", max_length=4000)
    category: str = Field(default="Spots", max_length=60)
    location_id: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    x: Optional[float] = None
    y: Optional[float] = None
    z: Optional[float] = None
    by_author: str = Field(default="Demo student", max_length=120)
    image_url: str = Field(default="", max_length=2000)


class PostCreate(BaseModel):
    author: str = Field(default="CampusOS Student", max_length=80)
    tag: str = Field(default="Academics", max_length=60)
    title: str = Field(default=..., max_length=160)
    body: str = Field(default=..., max_length=8000)


class ReplyCreate(BaseModel):
    author: str = Field(default="CampusOS Student", max_length=80)
    text: str = Field(default=..., max_length=2000)


class TaskCreate(BaseModel):
    title: str = Field(default=..., max_length=200)
    course: str = Field(default="General", max_length=100)
    due_date: str = Field(default="", max_length=40)
    priority: str = Field(default="Normal", max_length=20)


class TaskUpdate(BaseModel):
    title: Optional[str] = Field(default=None, max_length=200)
    course: Optional[str] = Field(default=None, max_length=100)
    due_date: Optional[str] = Field(default=None, max_length=40)
    priority: Optional[str] = Field(default=None, max_length=20)


class EventCreate(BaseModel):
    title: str = Field(default=..., max_length=200)
    place: str = Field(default="", max_length=120)
    when_date: str = Field(default="", max_length=40)
    time_str: str = Field(default="", max_length=20)
    count: int = Field(default=0)


class SummarizeRequest(BaseModel):
    notes: str = Field(default=..., max_length=8000)



class QuestionRequest(BaseModel):
    question: str = Field(min_length=3, max_length=500)
    context: str = Field(min_length=10, max_length=8000)


# ── Helpers ───────────────────────────────────────────────────────────────────

def row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return dict(row)


def not_found(entity: str, id_: int) -> HTTPException:
    return HTTPException(status_code=404, detail=f"{entity} with id={id_} not found")


# ── Health ────────────────────────────────────────────────────────────────────

@app.get("/api/health", tags=["system"])
def health() -> dict[str, Any]:
    """Verifies server and actual database connectivity."""
    try:
        with connect_db() as conn:
            conn.execute("SELECT 1").fetchone()
        db_status = "ok"
    except Exception as exc:
        log.error("DB health check failed: %s", exc)
        return JSONResponse(
            status_code=503,
            content={"status": "error", "service": "CampusOS API", "database": "error", "detail": str(exc)},
        )
    ai_ok = ai_adapter.check_model_available()
    return {
        "status": "ok",
        "service": "CampusOS API",
        "database": db_status,
        "ai_model": "gemma4:e4b" if ai_ok else "unavailable",
        "version": "2.0.0",
    }


# ── Campus data (static JSON, no DB write needed) ──────────────────────────────

@app.get("/api/campus/data", tags=["campus"])
def campus_data() -> dict[str, Any]:
    """Return the verified NIT Hamirpur campus reference dataset."""
    if not CAMPUS_DATA_PATH.exists():
        raise HTTPException(status_code=404, detail="Campus data file not found")
    with open(CAMPUS_DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


# ── Memories ──────────────────────────────────────────────────────────────────

@app.get("/api/memories", tags=["memories"])
def list_memories(category: Optional[str] = None) -> list[dict[str, Any]]:
    with connect_db() as conn:
        if category and category != "All":
            rows = conn.execute(
                "SELECT * FROM memories WHERE category = ? ORDER BY id DESC", (category,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM memories ORDER BY id DESC").fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/api/memories/{memory_id}", tags=["memories"])
def get_memory(memory_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    if not row:
        raise not_found("Memory", memory_id)
    return row_to_dict(row)


@app.post("/api/memories", status_code=201, tags=["memories"])
def create_memory(body: MemoryCreate) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute(
            """INSERT INTO memories
               (title, description, category, location_id, latitude, longitude, x, y, z, by_author, image_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (body.title.strip(), body.description, body.category,
             body.location_id, body.latitude, body.longitude,
             body.x, body.y, body.z, body.by_author.strip(), body.image_url),
        )
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (cur.lastrowid,)).fetchone()
    log.info("Created memory id=%s title=%r", cur.lastrowid, body.title)
    return row_to_dict(row)


@app.patch("/api/memories/{memory_id}/like", tags=["memories"])
def like_memory(memory_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
        if not row:
            raise not_found("Memory", memory_id)
        conn.execute(
            "UPDATE memories SET likes = likes + 1, updated_at = datetime('now') WHERE id = ?",
            (memory_id,),
        )
        updated = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
    return row_to_dict(updated)


@app.delete("/api/memories/{memory_id}", tags=["memories"])
def delete_memory(memory_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if cur.rowcount == 0:
            raise not_found("Memory", memory_id)
    log.info("Deleted memory id=%s", memory_id)
    return {"deleted": True, "id": memory_id}


# ── Community posts ───────────────────────────────────────────────────────────

@app.get("/api/posts", tags=["community"])
def list_posts(tag: Optional[str] = None) -> list[dict[str, Any]]:
    with connect_db() as conn:
        if tag:
            rows = conn.execute(
                "SELECT * FROM posts WHERE tag = ? ORDER BY id DESC", (tag,)
            ).fetchall()
        else:
            rows = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    result = []
    for r in rows:
        d = row_to_dict(r)
        try:
            d["replies"] = json.loads(d.get("replies_json") or "[]")
        except Exception:
            d["replies"] = []
        result.append(d)
    return result


@app.get("/api/posts/{post_id}", tags=["community"])
def get_post(post_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    if not row:
        raise not_found("Post", post_id)
    d = row_to_dict(row)
    try:
        d["replies"] = json.loads(d.get("replies_json") or "[]")
    except Exception:
        d["replies"] = []
    return d


@app.post("/api/posts", status_code=201, tags=["community"])
def create_post(body: PostCreate) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute(
            "INSERT INTO posts (author, tag, title, body) VALUES (?, ?, ?, ?)",
            (body.author.strip(), body.tag, body.title.strip(), body.body.strip()),
        )
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (cur.lastrowid,)).fetchone()
    log.info("Created post id=%s", cur.lastrowid)
    d = row_to_dict(row)
    d["replies"] = []
    return d


@app.post("/api/posts/{post_id}/reply", status_code=201, tags=["community"])
def add_reply(post_id: int, body: ReplyCreate) -> dict[str, Any]:
    import uuid
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise not_found("Post", post_id)
        replies = json.loads(row["replies_json"] or "[]")
        new_reply = {"id": str(uuid.uuid4())[:8], "author": body.author.strip(), "text": body.text.strip()}
        replies.append(new_reply)
        conn.execute(
            "UPDATE posts SET replies_json = ?, updated_at = datetime('now') WHERE id = ?",
            (json.dumps(replies), post_id),
        )
        updated = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    d = row_to_dict(updated)
    d["replies"] = replies
    return d


@app.patch("/api/posts/{post_id}/vote", tags=["community"])
def vote_post(post_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
        if not row:
            raise not_found("Post", post_id)
        conn.execute(
            "UPDATE posts SET votes = votes + 1, updated_at = datetime('now') WHERE id = ?",
            (post_id,),
        )
        updated = conn.execute("SELECT * FROM posts WHERE id = ?", (post_id,)).fetchone()
    d = row_to_dict(updated)
    try:
        d["replies"] = json.loads(d.get("replies_json") or "[]")
    except Exception:
        d["replies"] = []
    return d


@app.delete("/api/posts/{post_id}", tags=["community"])
def delete_post(post_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute("DELETE FROM posts WHERE id = ?", (post_id,))
        if cur.rowcount == 0:
            raise not_found("Post", post_id)
    return {"deleted": True, "id": post_id}


# ── Tasks ─────────────────────────────────────────────────────────────────────

@app.get("/api/tasks", tags=["tasks"])
def list_tasks() -> list[dict[str, Any]]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY completed ASC, due_date ASC").fetchall()
    return [row_to_dict(r) for r in rows]


@app.get("/api/tasks/{task_id}", tags=["tasks"])
def get_task(task_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if not row:
        raise not_found("Task", task_id)
    return row_to_dict(row)


@app.post("/api/tasks", status_code=201, tags=["tasks"])
def create_task(body: TaskCreate) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, course, due_date, priority) VALUES (?, ?, ?, ?)",
            (body.title.strip(), body.course.strip(), body.due_date, body.priority),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@app.patch("/api/tasks/{task_id}", tags=["tasks"])
def update_task(task_id: int, body: TaskUpdate) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise not_found("Task", task_id)
        fields, vals = [], []
        if body.title is not None:
            fields.append("title = ?"); vals.append(body.title.strip())
        if body.course is not None:
            fields.append("course = ?"); vals.append(body.course.strip())
        if body.due_date is not None:
            fields.append("due_date = ?"); vals.append(body.due_date)
        if body.priority is not None:
            fields.append("priority = ?"); vals.append(body.priority)
        if fields:
            fields.append("updated_at = datetime('now')")
            vals.append(task_id)
            conn.execute(f"UPDATE tasks SET {', '.join(fields)} WHERE id = ?", vals)
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_dict(updated)


@app.patch("/api/tasks/{task_id}/toggle", tags=["tasks"])
def toggle_task(task_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not row:
            raise not_found("Task", task_id)
        new_val = 0 if row["completed"] else 1
        conn.execute(
            "UPDATE tasks SET completed = ?, updated_at = datetime('now') WHERE id = ?",
            (new_val, task_id),
        )
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return row_to_dict(updated)


@app.delete("/api/tasks/{task_id}", tags=["tasks"])
def delete_task(task_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
        if cur.rowcount == 0:
            raise not_found("Task", task_id)
    return {"deleted": True, "id": task_id}


# ── Events ────────────────────────────────────────────────────────────────────

@app.get("/api/events", tags=["events"])
def list_events() -> list[dict[str, Any]]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM events ORDER BY when_date ASC").fetchall()
    return [row_to_dict(r) for r in rows]


@app.post("/api/events", status_code=201, tags=["events"])
def create_event(body: EventCreate) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute(
            "INSERT INTO events (title, place, when_date, time_str, count) VALUES (?, ?, ?, ?, ?)",
            (body.title.strip(), body.place.strip(), body.when_date, body.time_str, body.count),
        )
        row = conn.execute("SELECT * FROM events WHERE id = ?", (cur.lastrowid,)).fetchone()
    return row_to_dict(row)


@app.patch("/api/events/{event_id}/rsvp", tags=["events"])
def toggle_rsvp(event_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
        if not row:
            raise not_found("Event", event_id)
        new_going = 0 if row["going"] else 1
        conn.execute(
            "UPDATE events SET going = ?, updated_at = datetime('now') WHERE id = ?",
            (new_going, event_id),
        )
        updated = conn.execute("SELECT * FROM events WHERE id = ?", (event_id,)).fetchone()
    return row_to_dict(updated)


@app.delete("/api/events/{event_id}", tags=["events"])
def delete_event(event_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute("DELETE FROM events WHERE id = ?", (event_id,))
        if cur.rowcount == 0:
            raise not_found("Event", event_id)
    return {"deleted": True, "id": event_id}


# ── AI endpoints ──────────────────────────────────────────────────────────────

@app.get("/api/ai/status", tags=["ai"])
def ai_status() -> dict[str, Any]:
    available = ai_adapter.check_model_available()
    return {
        "available": available,
        "model": "gemma4:e4b",
        "runtime": "Ollama",
        "message": "AI ready" if available else (
            "Ollama is running but model not loaded. Run: ollama pull gemma4:e4b"
            if _ollama_reachable() else
            "Ollama is not running. Start with: ollama serve"
        ),
    }


def _ollama_reachable() -> bool:
    try:
        urllib_req = __import__("urllib.request", fromlist=["urlopen"])
        urllib_req.urlopen("http://127.0.0.1:11434/", timeout=2)
        return True
    except Exception:
        return False


@app.post("/api/ai/summarize", tags=["ai"])
def ai_summarize(body: SummarizeRequest) -> dict[str, Any]:
    result = ai_adapter.summarize_notes(body.notes)
    if not result["success"]:
        # Return 200 with success=false so the frontend can display a friendly error
        return result
    return result


@app.post("/api/ai/question", tags=["ai"])
def ai_question(body: QuestionRequest) -> dict[str, Any]:
    result = ai_adapter.answer_question(body.question, body.context)
    return result


# ── Frontend static files ─────────────────────────────────────────────────────

app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/{full_path:path}", include_in_schema=False)
async def catch_all(full_path: str):
    """Serve index.html for any non-API route."""
    index = STATIC_DIR / "index.html"
    if not index.exists():
        raise HTTPException(status_code=404, detail="Frontend not found")
    return FileResponse(str(index))


@app.get("/", include_in_schema=False)
async def root():
    return FileResponse(str(STATIC_DIR / "index.html"))
