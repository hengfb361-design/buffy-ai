# -*- coding: utf-8 -*-
"""Buffy AI — a GPT-style chat app powered by the Gemini API.

Features
- Streaming chat replies (server-sent events)
- Google Search grounding with clickable sources (like ChatGPT web search)
- Image upload / understanding, and image generation & editing (Nano Banana)
- Beautiful dark UI, Markdown + code blocks, chat export, local history

Run locally:  GEMINI_API_KEY=... uvicorn app:app --host 127.0.0.1 --port 8000
In Colab:     the notebook writes this file and opens a public cloudflared link.
"""

import base64
import json
import os
import traceback

from fastapi import FastAPI
from fastapi.responses import HTMLResponse, StreamingResponse
from pydantic import BaseModel
from typing import List, Optional

from google import genai

from ui import PAGE

APP_NAME = "Buffy AI"

# Chat models offered in the UI. The allow-list also protects the public link
# from being used with arbitrary (expensive) model names.
CHAT_MODELS = {
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemini-3.6-flash": "Gemini 3.6 Flash",
    "gemini-3.5-flash-lite": "Gemini 3.5 Flash-Lite",
}
DEFAULT_MODEL = "gemini-3.8-flash"
IMAGE_MODEL = "gemini-nano-banana-2.1"

SYSTEM_INSTRUCTION = (
    "You are a helpful, highly knowledgeable AI assistant. "
    "Always answer in the same language the user writes in (Khmer, English, or any other). "
    "Answer every question completely and accurately, with structure: use Markdown headings, "
    "lists, tables and fenced code blocks with language tags where useful. "
    "When web search results are provided, base current facts on them and cite naturally. "
    "If you are not sure about something, say so briefly and give the best available answer. "
    "Be warm and clear, never rude, and never refuse a reasonable question."
)

app = FastAPI(title=APP_NAME)
_client = None


def get_client() -> "genai.Client":
    global _client
    if _client is None:
        key = os.environ.get("GEMINI_API_KEY", "").strip()
        if not key:
            raise RuntimeError(
                "GEMINI_API_KEY is not set. Add it in the Colab cell / environment first."
            )
        _client = genai.Client(api_key=key)
    return _client


# --------------------------------------------------------------------------- #
# Request models
# --------------------------------------------------------------------------- #
class ImageIn(BaseModel):
    data: str = ""
    mime_type: str = "image/png"


class Turn(BaseModel):
    role: str = "user"
    text: str = ""


class ChatRequest(BaseModel):
    message: str = ""
    model: str = DEFAULT_MODEL
    web_search: bool = True
    image_mode: bool = False
    images: List[ImageIn] = []
    history: List[Turn] = []


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def sse(obj: dict) -> str:
    return "data: " + json.dumps(obj, ensure_ascii=False) + "\n\n"


def clean_b64(data: str) -> str:
    if not data:
        return ""
    if "," in data and data.strip().startswith("data:"):
        return data.split(",", 1)[1]
    return data.strip()


def build_turn(message: str, images: List[ImageIn]) -> dict:
    parts = []
    if message.strip():
        parts.append({"type": "text", "text": message.strip()})
    for img in images[:4]:
        raw = clean_b64(img.data)
        if not raw:
            continue
        parts.append(
            {
                "type": "image",
                "data": raw,
                "mime_type": img.mime_type or "image/png",
            }
        )
    if not parts:
        parts.append({"type": "text", "text": "(empty message)"})
    return {"type": "user_input", "content": parts}


def build_history_steps(history: List[Turn]) -> List[dict]:
    steps = []
    for turn in history[-30:]:
        text = (turn.text or "").strip()
        if not text:
            continue
        if turn.role == "user":
            steps.append({"type": "user_input", "content": [{"type": "text", "text": text}]})
        else:
            steps.append({"type": "model_output", "content": [{"type": "text", "text": text}]})
    return steps


def collect_sources(interaction) -> List[dict]:
    sources, seen = [], set()
    for step in getattr(interaction, "steps", None) or []:
        if getattr(step, "type", None) != "model_output":
            continue
        for block in getattr(step, "content", None) or []:
            for ann in getattr(block, "annotations", None) or []:
                if getattr(ann, "type", None) != "url_citation":
                    continue
                url = getattr(ann, "url", None)
                if not url or url in seen:
                    continue
                seen.add(url)
                sources.append({"title": getattr(ann, "title", None) or url, "url": url})
    return sources[:8]


def friendly_error(exc: Exception) -> str:
    msg = str(exc) or exc.__class__.__name__
    low = msg.lower()
    if "api key" in low or "api_key" in low or "permission" in low or "401" in low or "403" in low:
        return "API key មិនត្រឹមត្រូវ ឬគ្មានសិទ្ធិ។ សូមពិនិត្យ GEMINI_API_KEY ឡើងវិញ។"
    if "quota" in low or "429" in low or "rate" in low:
        return "ប្រើប្រាស់លើសកំណត់ (rate limit) — សូមរង់ចាំមួយសន្ទុះ ហើយព្យាយាមម្ដងទៀត។"
    return "មានបញ្ហាបច្ចេកទេស៖ " + msg[:300]


# --------------------------------------------------------------------------- #
# Streaming chat
# --------------------------------------------------------------------------- #
def image_stream(req: ChatRequest):
    """Non-streaming image generation / editing (Nano Banana)."""
    try:
        yield sse({"type": "status", "text": "កំពុងបង្កើតរូបភាព…"})
        steps = build_history_steps(req.history) + [build_turn(req.message, req.images)]
        interaction = get_client().interactions.create(
            model=IMAGE_MODEL,
            input=steps,
        )
        img = getattr(interaction, "output_image", None)
        data = getattr(img, "data", None) if img is not None else None
        mime = getattr(img, "mime_type", None) if img is not None else None
        if data:
            yield sse({"type": "image", "data": data, "mime": mime or "image/png"})
        text = getattr(interaction, "output_text", None)
        if text:
            yield sse({"type": "text", "text": text})
        if not data and not text:
            yield sse({"type": "error", "text": "មិនអាចបង្កើតរូបភាពបានទេ។ សូមសាកល្បងបញ្ជាផ្សេង។"})
        yield sse({"type": "done"})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        yield sse({"type": "error", "text": friendly_error(exc)})


def chat_stream(req: ChatRequest):
    streamed = False
    try:
        model = req.model if req.model in CHAT_MODELS else DEFAULT_MODEL
        steps = build_history_steps(req.history) + [build_turn(req.message, req.images)]
        kwargs = {
            "model": model,
            "input": steps,
            "system_instruction": SYSTEM_INSTRUCTION,
            "stream": True,
        }
        if req.web_search:
            kwargs["tools"] = [{"type": "google_search"}]

        stream = get_client().interactions.create(**kwargs)
        for event in stream:
            etype = getattr(event, "event_type", None)

            if etype == "step.delta":
                delta = getattr(event, "delta", None)
                dtype = getattr(delta, "type", None)
                if dtype == "text":
                    chunk = getattr(delta, "text", "") or ""
                    if chunk:
                        streamed = True
                        yield sse({"type": "text", "text": chunk})
                elif dtype == "thought_summary":
                    yield sse({"type": "status", "text": "កំពុងគិត…"})
                elif dtype == "google_search_call":
                    queries = ""
                    args = getattr(delta, "arguments", None)
                    if isinstance(args, dict):
                        queries = ", ".join(args.get("queries") or [])
                    yield sse(
                        {
                            "type": "status",
                            "text": "កំពុងស្វែងរកអ៊ីនធឺណិត…" + (" " + queries if queries else ""),
                        }
                    )

            elif etype == "interaction.completed":
                interaction = getattr(event, "interaction", None)
                if interaction is not None:
                    sources = collect_sources(interaction)
                    if sources:
                        yield sse({"type": "sources", "sources": sources})
                    if not streamed:
                        text = getattr(interaction, "output_text", None)
                        if text:
                            streamed = True
                            yield sse({"type": "text", "text": text})

        if not streamed:
            yield sse({"type": "error", "text": "មិនមានចម្លើយត្រឡប់មកវិញទេ។ សូមព្យាយាមម្ដងទៀត។"})
        yield sse({"type": "done"})
    except Exception as exc:  # noqa: BLE001
        traceback.print_exc()
        yield sse({"type": "error", "text": friendly_error(exc)})


@app.post("/api/chat")
def chat(req: ChatRequest):
    generator = image_stream(req) if req.image_mode else chat_stream(req)
    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-transform",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "app": APP_NAME,
        "key_set": bool(os.environ.get("GEMINI_API_KEY", "").strip()),
        "models": list(CHAT_MODELS.keys()),
        "image_model": IMAGE_MODEL,
    }


# --------------------------------------------------------------------------- #
# Front-end (single page, no build step)
# --------------------------------------------------------------------------- #


@app.get("/", response_class=HTMLResponse)
def index():
    return HTMLResponse(PAGE)
