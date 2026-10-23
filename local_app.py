# -*- coding: utf-8 -*-
"""Local-model version of Buffy AI.

Serves the same ChatGPT-style UI (ui.py) but answers with a GGUF model that runs
locally through an OpenAI-compatible server (Ollama by default, llama.cpp also
works) — no cloud API key needed.

The Colab notebook starts the engine, imports the GGUF, then runs this app:

    ollama serve                                    # http://127.0.0.1:11434
    LLAMA_URL=http://127.0.0.1:11434 LOCAL_MODEL=buffy-coder \
        uvicorn local_app:app --host 127.0.0.1 --port 8000

Environment:
    LLAMA_URL    OpenAI-compatible base URL (default http://127.0.0.1:11434)
    LOCAL_MODEL  model name inside that engine (default "buffy-coder")

    API_BASE_URL OpenAI-compatible *hosted* API, e.g. https://api.example.com/v1
    API_KEY      bearer key for that API — set it in Sites → Secrets / env,
                 never in the browser or the source code
    API_MODEL    model id for that API (falls back to LOCAL_MODEL)

When API_BASE_URL is set the app calls that hosted API; otherwise it uses the
local engine at LLAMA_URL. The key is only ever read from the environment on
the server, so the public page never receives it.
"""

import json
import os
import traceback

import requests
from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List

from ui import PAGE

LLAMA_URL = os.environ.get("LLAMA_URL", "http://127.0.0.1:11434").rstrip("/")
LOCAL_MODEL = os.environ.get("LOCAL_MODEL", "buffy-coder")

# Optional hosted OpenAI-compatible API. The key lives only in the server
# environment (Sites → Secrets / process env) and is never sent to the browser.
API_BASE_URL = os.environ.get("API_BASE_URL", "").rstrip("/")
API_KEY = os.environ.get("API_KEY", "").strip()
API_MODEL = os.environ.get("API_MODEL", "").strip()


def backend():
    """(base_url, model, headers) for the engine that is currently configured."""
    if API_BASE_URL:
        headers = {"Content-Type": "application/json"}
        if API_KEY:
            headers["Authorization"] = "Bearer " + API_KEY
        return API_BASE_URL, API_MODEL or LOCAL_MODEL, headers
    return LLAMA_URL, LOCAL_MODEL, {}


def mode() -> str:
    return "hosted API" if API_BASE_URL else "local"

SYSTEM_INSTRUCTION = (
    "You are a helpful AI assistant running locally on the user's machine. "
    "Always answer in the same language the user writes in (Khmer, English, or any other). "
    "Be accurate and clear; use Markdown lists, tables and fenced code blocks with language "
    "tags when they help. Never invent facts — if you are unsure, say so."
)

app = FastAPI(title="Buffy AI (local)")


class ImageIn(BaseModel):
    data: str = ""
    mime_type: str = "image/png"


class Turn(BaseModel):
    role: str = "user"
    text: str = ""


class ChatRequest(BaseModel):
    message: str = ""
    model: str = "local"
    web_search: bool = False
    image_mode: bool = False
    images: List[ImageIn] = []
    history: List[Turn] = []


def sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def build_messages(req: ChatRequest) -> List[dict]:
    messages = [{"role": "system", "content": SYSTEM_INSTRUCTION}]
    for turn in req.history[-16:]:
        text = (turn.text or "").strip()
        if not text:
            continue
        role = "user" if turn.role == "user" else "assistant"
        messages.append({"role": role, "content": text[:6000]})
    messages.append({"role": "user", "content": req.message.strip() or "(empty message)"})
    return messages


def chat_stream(req: ChatRequest):
    try:
        if req.images:
            yield sse(
                {
                    "type": "error",
                    "text": "ម៉ូដែល local នេះជា text-only — មិនអាចអានរូបភាពបានទេ។",
                }
            )
        if req.image_mode:
            yield sse(
                {
                    "type": "error",
                    "text": "ម៉ូដែល local នេះមិនអាចបង្កើតរូបភាពបានទេ។",
                }
            )

        base_url, model_name, headers = backend()
        yield sse({"type": "status", "text": "កំពុងគិត (%s)…" % mode()})
        payload = {
            "model": model_name,
            "messages": build_messages(req),
            "stream": True,
            "max_tokens": 2048,
        }
        resp = requests.post(
            base_url + "/v1/chat/completions",
            json=payload,
            headers=headers,
            stream=True,
            timeout=(10, 600),
        )
        if resp.status_code != 200:
            text = resp.text[:300]
            yield sse(
                {
                    "type": "error",
                    "text": "%s មិនឆ្លើយតបត្រឹមត្រូវ (HTTP %s)៖ %s"
                    % (mode(), resp.status_code, text),
                }
            )
            yield sse({"type": "done"})
            return

        started = False
        for line in resp.iter_lines(decode_unicode=True):
            if not line:
                continue
            if line.startswith("data: "):
                line = line[6:].strip()
            if line == "[DONE]":
                break
            try:
                chunk = json.loads(line)
            except Exception:
                continue
            choices = chunk.get("choices") or []
            if not choices:
                continue
            delta = choices[0].get("delta") or {}
            piece = delta.get("content")
            if piece:
                if not started:
                    started = True
                    yield sse({"type": "status", "text": ""})
                yield sse({"type": "text", "text": piece})

        if not started:
            yield sse({"type": "error", "text": "ម៉ូដែលមិនបានផ្តល់ចម្លើយ។ សូមព្យាយាមម្ដងទៀត។"})
        yield sse({"type": "done"})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        yield sse(
            {
                "type": "error",
                "text": "មិនអាចភ្ជាប់ទៅ %s បានទេ — តើ %s ត្រូវបានកំណត់ឬដំណើរការ? (%s)"
                % (mode(), backend()[0], str(exc)[:200]),
            }
        )
        yield sse({"type": "done"})


@app.post("/api/chat")
def chat(req: ChatRequest):
    return StreamingResponse(
        chat_stream(req),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/health")
def health():
    """Reports the active engine. Deliberately never exposes the key value."""
    base_url, model_name, _headers = backend()
    if not API_BASE_URL:
        try:
            r = requests.get(base_url + "/v1/models", timeout=3)
            data = r.json().get("data") or []
            if data:
                model_name = data[0].get("id", "")
        except Exception:
            pass
    return {
        "ok": True,
        "app": "Buffy AI",
        "mode": mode(),
        "engine": base_url,
        "model": model_name,
        "key_set": bool(API_KEY),
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(PAGE)
