from contextlib import asynccontextmanager
from pathlib import Path
import json
import sqlite3
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "campusos.db"
INDEX_PATH = BASE_DIR / "static" / "index.html"


def connect_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with connect_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'General',
                latitude REAL,
                longitude REAL,
                image_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL DEFAULT 'CampusOS Student',
                category TEXT NOT NULL DEFAULT 'General',
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                due_date TEXT NOT NULL DEFAULT '',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)


@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="CampusOS API", version="0.1.0", lifespan=lifespan)


class MemoryCreate(BaseModel):
    title: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=4000)
    category: str = Field(default="General", max_length=60)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    image_url: str = Field(default="", max_length=2000)


class PostCreate(BaseModel):
    author: str = Field(default="CampusOS Student", min_length=1, max_length=80)
    category: str = Field(default="General", max_length=60)
    title: str = Field(min_length=1, max_length=160)
    body: str = Field(min_length=1, max_length=8000)


class TaskCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    due_date: str = Field(default="", max_length=40)


@app.get("/", include_in_schema=False)
def home():
    return FileResponse(INDEX_PATH)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "CampusOS API", "database": "SQLite"}


@app.get("/api/memories")
def list_memories() -> list[dict[str, Any]]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM memories ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/memories", status_code=201)
def create_memory(memory: MemoryCreate) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute(
            """INSERT INTO memories (title, description, category, latitude, longitude, image_url)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (memory.title.strip(), memory.description, memory.category,
             memory.latitude, memory.longitude, memory.image_url),
        )
        row = conn.execute("SELECT * FROM memories WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.delete("/api/memories/{memory_id}")
def delete_memory(memory_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        if cur.rowcount == 0:
            raise HTTPException(status_code=404, detail="Memory not found")
    return {"deleted": True, "id": memory_id}


@app.get("/api/posts")
def list_posts() -> list[dict[str, Any]]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM posts ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/posts", status_code=201)
def create_post(post: PostCreate) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute(
            "INSERT INTO posts (author, category, title, body) VALUES (?, ?, ?, ?)",
            (post.author.strip(), post.category, post.title.strip(), post.body.strip()),
        )
        row = conn.execute("SELECT * FROM posts WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.get("/api/tasks")
def list_tasks() -> list[dict[str, Any]]:
    with connect_db() as conn:
        rows = conn.execute("SELECT * FROM tasks ORDER BY id DESC").fetchall()
    return [dict(row) for row in rows]


@app.post("/api/tasks", status_code=201)
def create_task(task: TaskCreate) -> dict[str, Any]:
    with connect_db() as conn:
        cur = conn.execute(
            "INSERT INTO tasks (title, due_date) VALUES (?, ?)",
            (task.title.strip(), task.due_date),
        )
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (cur.lastrowid,)).fetchone()
    return dict(row)


@app.patch("/api/tasks/{task_id}/toggle")
def toggle_task(task_id: int) -> dict[str, Any]:
    with connect_db() as conn:
        row = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is None:
            raise HTTPException(status_code=404, detail="Task not found")
        new_value = 0 if row["completed"] else 1
        conn.execute("UPDATE tasks SET completed = ? WHERE id = ?", (new_value, task_id))
        updated = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    return dict(updated)
