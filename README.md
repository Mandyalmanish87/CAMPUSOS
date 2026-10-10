# CampusOS starter — existing UI + Python API

This starter keeps the reviewed CampusOS HTML and the map tile fallback patch. It adds a small FastAPI backend and SQLite database. The current frontend is **not yet wired to the API**: its existing interactions and localStorage behavior remain in place while you verify the backend first.

## Requirements
- Windows 10/11
- Python 3.11 or newer (Python 3.12 is a safe choice)
- Internet access for the HTML's existing CDN libraries and map tiles

## 1. Run it on Windows
Open this folder in VS Code, then open **Terminal → New Terminal**. Run each command separately:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m uvicorn app:app --reload
```

If PowerShell blocks activation, use Command Prompt terminal and run:

```bat
.venv\Scripts\activate.bat
```

Leave the terminal running. Open these URLs in Chrome:
- CampusOS UI: http://127.0.0.1:8000/
- Health check: http://127.0.0.1:8000/api/health
- Interactive API docs: http://127.0.0.1:8000/docs

Use `Ctrl+C` in the terminal to stop the server.

## 2. Test database-backed endpoints
In Chrome, open http://127.0.0.1:8000/docs. Try `POST /api/memories` with:

```json
{
  "title": "Test campus memory",
  "description": "Checking that SQLite saves data",
  "category": "Campus",
  "latitude": 31.7083,
  "longitude": 76.5273,
  "image_url": ""
}
```

Then use `GET /api/memories`. Stop and restart the server and check again: the record should remain because it is stored in `campusos.db`.

Also test `POST /api/posts`, `GET /api/posts`, `POST /api/tasks`, and `GET /api/tasks` from `/docs`.

## What is and isn't implemented
- Implemented: local FastAPI server, SQLite tables for memories/posts/tasks, basic CRUD/create/list routes, validation, API docs.
- Not yet implemented: frontend-to-API wiring, login, real user profiles, permissions, image upload/storage, Gemma integration, production hosting.
- Do not put real private student information into this prototype. It has no authentication or per-user access control yet.

## Next integration milestone
Once `/api/health` works, connect one UI feature at a time using `fetch('/api/memories')`, then wire memory creation to `POST /api/memories`. Keep the existing `localStorage` behavior as a fallback until the API path is tested. Do not rewrite the whole HTML or remove the map fallback.
