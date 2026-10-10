"""
AI adapter — routes inference through the local Ollama server running gemma4:e4b.
The adapter returns a structured unavailable response when Ollama is unreachable
or times out, so the frontend always gets a consistent JSON shape.
"""
import json
import urllib.error
import urllib.request
from typing import Any, Optional

from config import AI_TIMEOUT_SECONDS, GEMMA_MODEL_NAME, OLLAMA_BASE_URL


def _post_ollama(payload: dict, timeout: float) -> dict[str, Any]:
    data = json.dumps(payload).encode()
    req = urllib.request.Request(
        f"{OLLAMA_BASE_URL}/api/generate",
        data=data,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode())


def check_model_available(model: Optional[str] = None) -> bool:
    """Return True if Ollama is reachable and the model is listed."""
    target = model or GEMMA_MODEL_NAME
    try:
        with urllib.request.urlopen(
            f"{OLLAMA_BASE_URL}/api/tags", timeout=3
        ) as resp:
            data = json.loads(resp.read().decode())
            names = [m.get("name", "") for m in data.get("models", [])]
            return any(n.startswith(target.split(":")[0]) for n in names)
    except Exception:
        return False


def summarize_notes(notes_text: str, timeout: float = AI_TIMEOUT_SECONDS) -> dict[str, Any]:
    """
    Call Gemma to produce a structured study-notes summary.
    Returns a dict with keys:
      - success (bool)
      - summary (str | None)
      - key_terms (list[str])
      - practice_questions (list[dict[str, str]])
      - flashcards (list[dict[str, str]])
      - model (str)
      - error (str | None) — present only on failure
    """
    prompt = (
        "You are a helpful study assistant for an engineering student. "
        "Given the following study notes, produce:\n"
        "1. A brief summary (3-5 sentences).\n"
        "2. A JSON array of up to 8 flashcards, each with term and definition strings.\n"
        "3. A JSON array of up to 6 practice questions, each with question and answer strings.\n"
        "4. A JSON array of up to 6 key terms as strings.\n\n"
        "Respond ONLY in the following JSON format, with no extra text:\n"
        '{"summary":"...","key_terms":["..."],"flashcards":[{"term":"...","definition":"..."}],"practice_questions":[{"question":"...","answer":"..."}]}\n\n'
        f"NOTES:\n{notes_text[:3000]}"
    )

    if not check_model_available():
        return {
            "success": False,
            "summary": None,
            "key_terms": [],
            "practice_questions": [],
            "flashcards": [],
            "model": GEMMA_MODEL_NAME,
            "error": "AI model unavailable. Ollama is not running or gemma4:e4b is not loaded. "
                     "Start Ollama with: ollama serve",
        }

    try:
        raw = _post_ollama(
            {"model": GEMMA_MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        response_text = raw.get("response", "").strip()
        # Try to extract JSON from the response
        start = response_text.find("{")
        end = response_text.rfind("}") + 1
        if start >= 0 and end > start:
            parsed = json.loads(response_text[start:end])
            return {
                "success": True,
                "summary": parsed.get("summary", ""),
                "key_terms": parsed.get("key_terms", []),
                "practice_questions": parsed.get("practice_questions", []),
                "flashcards": parsed.get("flashcards", []),
                "model": GEMMA_MODEL_NAME,
                "error": None,
            }
        # If JSON parse fails, return raw text as summary
        return {
            "success": True,
            "summary": response_text,
            "key_terms": [],
            "practice_questions": [],
            "flashcards": [],
            "model": GEMMA_MODEL_NAME,
            "error": None,
        }
    except TimeoutError:
        return {
            "success": False,
            "summary": None,
            "key_terms": [],
            "practice_questions": [],
            "flashcards": [],
            "model": GEMMA_MODEL_NAME,
            "error": "AI inference timed out. The model may be loading or the system is under heavy load. Try again in a moment.",
        }
    except Exception as exc:
        return {
            "success": False,
            "summary": None,
            "key_terms": [],
            "practice_questions": [],
            "flashcards": [],
            "model": GEMMA_MODEL_NAME,
            "error": f"AI inference error: {exc}",
        }


def answer_question(question: str, context: str, timeout: float = AI_TIMEOUT_SECONDS) -> dict[str, Any]:
    """Answer a study question given note context."""
    prompt = (
        "You are a helpful study assistant. Answer the following question "
        "using ONLY the provided context. If the context doesn't contain enough "
        "information, say so clearly.\n\n"
        f"CONTEXT:\n{context[:2000]}\n\n"
        f"QUESTION: {question}\n\n"
        "Respond in plain text with a concise, helpful answer (2-4 sentences)."
    )

    if not check_model_available():
        return {
            "success": False,
            "answer": None,
            "model": GEMMA_MODEL_NAME,
            "error": "AI model unavailable. Start Ollama with: ollama serve",
        }

    try:
        raw = _post_ollama(
            {"model": GEMMA_MODEL_NAME, "prompt": prompt, "stream": False},
            timeout=timeout,
        )
        return {
            "success": True,
            "answer": raw.get("response", "").strip(),
            "model": GEMMA_MODEL_NAME,
            "error": None,
        }
    except TimeoutError:
        return {
            "success": False,
            "answer": None,
            "model": GEMMA_MODEL_NAME,
            "error": "AI inference timed out. Try again in a moment.",
        }
    except Exception as exc:
        return {
            "success": False,
            "answer": None,
            "model": GEMMA_MODEL_NAME,
            "error": f"AI inference error: {exc}",
        }
