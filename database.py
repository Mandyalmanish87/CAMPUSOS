import sqlite3
from pathlib import Path
from typing import Optional
from config import DB_PATH

def connect_db(custom_path: Optional[Path] = None) -> sqlite3.Connection:
    target = custom_path or DB_PATH
    conn = sqlite3.connect(target)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db(custom_path: Optional[Path] = None) -> None:
    with connect_db(custom_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                description TEXT NOT NULL DEFAULT '',
                category TEXT NOT NULL DEFAULT 'Spots',
                location_id TEXT,
                latitude REAL,
                longitude REAL,
                x REAL,
                y REAL,
                z REAL,
                by_author TEXT NOT NULL DEFAULT 'Demo student',
                likes INTEGER NOT NULL DEFAULT 0,
                image_url TEXT NOT NULL DEFAULT '',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_cat ON memories(category)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL DEFAULT 'CampusOS Student',
                tag TEXT NOT NULL DEFAULT 'Academics',
                title TEXT NOT NULL,
                body TEXT NOT NULL,
                votes INTEGER NOT NULL DEFAULT 0,
                replies_json TEXT NOT NULL DEFAULT '[]',
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_posts_tag ON posts(tag)")

        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                course TEXT NOT NULL DEFAULT 'General',
                due_date TEXT NOT NULL DEFAULT '',
                priority TEXT NOT NULL DEFAULT 'Normal',
                completed INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                place TEXT NOT NULL DEFAULT '',
                when_date TEXT NOT NULL DEFAULT '',
                time_str TEXT NOT NULL DEFAULT '',
                going INTEGER NOT NULL DEFAULT 0,
                count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT (datetime('now')),
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
        """)

        # Seed initial data if empty
        row = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()
        if row and row["c"] == 0:
            seed_memories = [
                ("Food court steps", "Where every group project got planned over chai that was always slightly too sweet. The top step catches the evening sun.", "Dining", "loc-foodcourt", 31.7081, 76.5270, 205, 225, 4, "Riya, 3rd year", 24),
                ("Library, third-floor corner", "The window desk with the best view of the hills. A whole semester of notes got finished here during exam week.", "Academic", "loc-library", 31.7088, 76.5277, 370, 270, 8, "Karan, 4th year", 31),
                ("Sunset point", "A short climb from the sports ground. Go just before dusk: the valley turns orange and everyone goes quiet.", "Spots", "loc-sunset", 31.7095, 76.5302, 725, 440, 28, "Demo student", 58),
                ("Ground, late-night football", "Hostel versus hostel on the first Friday of the semester. Nobody remembers the score, everyone remembers the rain.", "Sports", "loc-ground", 31.7072, 76.5290, 650, 120, -4, "Imran, 2nd year", 40),
                ("LHC corridor", "Where results get shared before the portal even loads. Always crowded, always loud.", "Academic", "loc-lhc", 31.7091, 76.5282, 480, 205, 14, "Meera, 3rd year", 17),
                ("Hostel terrace", "Rooftop cricket with a tennis ball and a rule list nobody ever wrote down.", "Hostels", "loc-hostels-boys", 31.7065, 76.5262, 95, 115, 10, "Aman, 2nd year", 22),
                ("Main gate", "First day: parents, luggage and nervous smiles. The last day looks surprisingly similar.", "Spots", "loc-maingate", 31.7061, 76.5250, 110, 455, -2, "Demo student", 35),
                ("Auditorium backstage", "Rehearsals ran past midnight before cultural night, powered entirely by biscuits.", "Spots", "loc-auditorium", 31.7084, 76.5285, 420, 385, 2, "Sana, 3rd year", 19)
            ]
            conn.executemany("""
                INSERT INTO memories (title, description, category, location_id, latitude, longitude, x, y, z, by_author, likes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, seed_memories)

        row = conn.execute("SELECT COUNT(*) AS c FROM posts").fetchone()
        if row and row["c"] == 0:
            seed_posts = [
                ("Kavya (demo)", "Academics", "What do examiners ask in the analog electronics viva?",
                 "Our lab viva is next week. Seniors, what do examiners usually ask beyond the circuit diagram?", 14,
                 '[{"id":"r1","author":"Rohan (demo)","text":"Be ready to explain why each component value was chosen, not just what it is."},{"id":"r2","author":"Meera (demo)","text":"Know your observation table cold. They love asking what changes if one reading is off."}]'),
                ("Imran (demo)", "Campus life", "Quiet corners for exam week?",
                 "The library fills up by 9 am. Any other places where I can actually focus for a few hours?", 9,
                 '[{"id":"r3","author":"Sana (demo)","text":"Empty classrooms in the evening are underrated. Carry a charger."}]'),
                ("Aman (demo)", "Events", "Five-a-side before the semester gets heavy?",
                 "Looking for eight more people for a Sunday evening game at the ground. All skill levels welcome.", 6, '[]'),
                ("Riya (demo)", "Placements", "What should the resume clinic cover?",
                 "Projects versus coursework, one page versus two, how to write internships. What would you want reviewed?", 11, '[]')
            ]
            conn.executemany("""
                INSERT INTO posts (author, tag, title, body, votes, replies_json)
                VALUES (?, ?, ?, ?, ?, ?)
            """, seed_posts)

        row = conn.execute("SELECT COUNT(*) AS c FROM tasks").fetchone()
        if row and row["c"] == 0:
            seed_tasks = [
                ("Zener regulator lab report", "Electronics Lab", "2026-10-12", "High", 0),
                ("DSP problem set 4", "Digital Signal Processing", "2026-10-14", "Normal", 0),
                ("Revise Maxwell's equations for the quiz", "Electromagnetic Theory", "2026-10-11", "High", 0),
                ("Mini-project proposal", "Microprocessors", "2026-10-18", "Normal", 0),
                ("Assignment 2", "Communication Systems", "2026-10-09", "Normal", 1)
            ]
            conn.executemany("""
                INSERT INTO tasks (title, course, due_date, priority, completed)
                VALUES (?, ?, ?, ?, ?)
            """, seed_tasks)

        row = conn.execute("SELECT COUNT(*) AS c FROM events").fetchone()
        if row and row["c"] == 0:
            seed_events = [
                ("Open mic night", "Auditorium", "2026-10-11", "18:30", 0, 46),
                ("Resume clinic with alumni", "Seminar room", "2026-10-13", "15:00", 0, 28),
                ("Inter-branch football semifinal", "Sports ground", "2026-10-14", "16:30", 0, 112),
                ("Robotics club induction", "LHC 101", "2026-10-16", "17:00", 0, 63),
                ("Sunrise photo walk", "Main gate", "2026-10-19", "06:00", 0, 19)
            ]
            conn.executemany("""
                INSERT INTO events (title, place, when_date, time_str, going, count)
                VALUES (?, ?, ?, ?, ?, ?)
            """, seed_events)
