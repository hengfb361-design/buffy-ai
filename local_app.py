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
                    "text": "ម៉ូដែល local នេះជា text-only — មិនអាចអានរូបភាពបានទេ។ "
                    "សូមប្រើកំណែ Gemini សម្រាប់រូបភាព។",
                }
            )
        if req.image_mode:
            yield sse(
                {
                    "type": "error",
                    "text": "ការបង្កើតរូបភាពត្រូវការ Gemini (Nano Banana) មិនមែនម៉ូដែល local ទេ។",
                }
            )

        yield sse({"type": "status", "text": "កំពុងគិត (local)…"})
        payload = {
            "model": LOCAL_MODEL,
            "messages": build_messages(req),
            "stream": True,
            "max_tokens": 2048,
        }
        resp = requests.post(
            LLAMA_URL + "/v1/chat/completions",
            json=payload,
            stream=True,
            timeout=(10, 600),
        )
        if resp.status_code != 200:
            text = resp.text[:300]
            yield sse(
                {
                    "type": "error",
                    "text": "Local engine មិនឆ្លើយតបត្រឹមត្រូវ (HTTP %s)៖ %s"
                    % (resp.status_code, text),
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
                "text": "មិនអាចភ្ជាប់ទៅ local engine បានទេ — តើវាដំណើរការនៅ %s ទេ? (%s)"
                % (LLAMA_URL, str(exc)[:200]),
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
    model_name = ""
    try:
        r = requests.get(LLAMA_URL + "/v1/models", timeout=3)
        data = r.json().get("data") or []
        if data:
            model_name = data[0].get("id", "")
    except Exception:
        model_name = ""
    return {
        "ok": True,
        "app": "Buffy AI (local)",
        "engine": LLAMA_URL,
        "model": model_name or LOCAL_MODEL,
    }


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(PAGE)
