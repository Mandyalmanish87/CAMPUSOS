# CampusOS — NIT Hamirpur Student Companion

A locally-runnable student companion for NIT Hamirpur, built with:
- **Frontend**: HTML + React (Babel in-browser) + Tailwind CSS — all vendor files bundled locally, no CDN required at runtime
- **Backend**: Python · FastAPI · Uvicorn · SQLite
- **AI**: Gemma 4 E4B via Ollama (optional, local)
- **Campus map**: Native 3D map built with Three.js and OrbitControls — no external tile service, no API key

---

## Quick start (Windows)

### Option A — One-click launch (recommended)
```
Double-click:  run_campusos.bat
```
This creates a Python virtual environment, installs dependencies, starts the server, and opens Chrome.

### Option B — Manual

```powershell
# 1. Create and activate virtual environment
python -m venv venv
.\venv\Scripts\Activate.ps1

# 2. Install dependencies
pip install fastapi "uvicorn[standard]" pydantic httpx

# 3. Start server
python -m uvicorn app:app --host 127.0.0.1 --port 8000 --reload

# 4. Open in Chrome
start chrome http://127.0.0.1:8000
```

### Enable Gemma AI (optional)

If you have Ollama installed with `gemma4:e4b` already downloaded:

```powershell
# In a separate terminal
ollama serve
```

The "Summarize with Gemma AI" button in Study Studio will become active automatically.

---

## Project structure

```
CampusOS/
├── app.py                   ← FastAPI application (all API routes)
├── database.py              ← SQLite schema, init, seed data
├── config.py                ← Configuration constants
├── ai_adapter.py            ← Ollama / Gemma inference wrapper
├── requirements.txt         ← Python dependencies
├── run_campusos.bat         ← One-click Windows startup script
├── .env.example             ← Configuration reference
│
├── static/
│   ├── index.html           ← Main frontend (React + Tailwind, single file)
│   ├── campus_map_3d.html   ← Native 3D campus map (Three.js, no CDN)
│   ├── data/
│   │   └── campus_data.json ← Verified NIT Hamirpur campus locations
│   └── vendor/              ← Locally bundled JS (React, Babel, Tailwind, Three.js)
│
└── tests/
    └── test_api.py          ← Automated API tests (pytest)
```

---

## API endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | Server and database health check |
| GET | `/api/campus/data` | Campus locations and road data |
| GET/POST | `/api/memories` | Campus memories (CRUD) |
| PATCH | `/api/memories/{id}/like` | Like a memory |
| DELETE | `/api/memories/{id}` | Delete a memory |
| GET/POST | `/api/posts` | Community posts |
| POST | `/api/posts/{id}/reply` | Add a reply |
| PATCH | `/api/posts/{id}/vote` | Upvote a post |
| GET/POST | `/api/tasks` | Tasks |
| PATCH | `/api/tasks/{id}/toggle` | Toggle task completion |
| GET/POST | `/api/events` | Campus events |
| PATCH | `/api/events/{id}/rsvp` | RSVP to an event |
| GET | `/api/ai/status` | Check Gemma/Ollama availability |
| POST | `/api/ai/summarize` | AI note summarization via Gemma |
| POST | `/api/ai/question` | AI question answering |

Interactive API docs: `http://127.0.0.1:8000/docs`

---

## Running tests

```powershell
.\venv\Scripts\python -m pytest tests/ -v
```

---

## Campus map

The 3D campus map (`static/campus_map_3d.html`) uses:
- **Three.js r128** — bundled locally at `static/vendor/three.min.js`
- **OrbitControls** — bundled locally at `static/vendor/OrbitControls.js`
- **Campus data** — `static/data/campus_data.json` (15 verified NIT Hamirpur locations)

No internet connection is required to render the map. Building positions are based on verified campus landmarks and are clearly marked as approximate layout references, not survey-accurate coordinates.

To add or correct a campus location, edit `static/data/campus_data.json`.

---

## AI integration

| Component | Status |
|-----------|--------|
| Ollama | Installed at `C:\Users\mandy\AppData\Local\Programs\Ollama\ollama.exe` |
| Model | `gemma4:e4b` (6.6 GB) — already downloaded |
| Inference | Routes through `/api/ai/summarize` (120s timeout) |
| Fallback | If Ollama is offline, local word-frequency summary is used |

---

## Notes and limitations

- **Sign-in / accounts**: Not connected. This is a local guest mode application.
- **Building coordinates**: Approximate, based on verified campus landmarks. Not survey-accurate.
- **Community, market, lost & found**: Currently store in SQLite via the backend.
- **Profile**: Stored in browser localStorage (client-side preferences only).
