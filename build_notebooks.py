# -*- coding: utf-8 -*-
"""Regenerate the two Colab notebooks from the source files."""

import json
from pathlib import Path

ROOT = Path(__file__).parent
UI = (ROOT / "ui.py").read_text(encoding="utf-8")
APP = (ROOT / "app.py").read_text(encoding="utf-8")
LOCAL_APP = (ROOT / "local_app.py").read_text(encoding="utf-8")

for src in (UI, APP, LOCAL_APP):
    assert src.endswith("\n")

# --------------------------------------------------------------------------- #
# Shared pieces
# --------------------------------------------------------------------------- #
CLOUDFLARED = """!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
!chmod +x /usr/local/bin/cloudflared"""

RUN_TAIL = """proc = subprocess.Popen(
    ["cloudflared", "tunnel", "--url", f"http://127.0.0.1:{PORT}", "--no-autoupdate"],
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
    bufsize=1,
)

found = False
for line in proc.stdout:
    if not found:
        m = re.search(r"https://[a-z0-9-]+\\.trycloudflare\\.com", line)
        if m:
            found = True
            print("=" * 68)
            print("🎉 នេះជា link សម្រាប់ជជែក (បើកបានគ្រប់ឧបករណ៍):\\n")
            print("   " + m.group(0))
            print("\\n" + "=" * 68)
            print("⚠️ កុំបិទ cell នេះ — កម្មវិធីដំណើរការពេល cell នេះនៅរត់។")
            print("   ចុច ⏹ ដើម្បីបញ្ឈប់។")

print("\\n🔌 Tunnel បានបិទ។ ប្រសិនបើអ្នកចង់បាន link ថ្មី សូមរត់ cell នេះម្តងទៀត។")"""

WAIT_SERVER = '''ready = False
for _ in range(80):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/health", timeout=2) as r:
            print("✅ Server ដំណើរការ:", r.read().decode()[:160])
            ready = True
            break
    except Exception:
        time.sleep(0.5)
if not ready:
    raise RuntimeError("Server មិនអាចចាប់ផ្តើមបានទេ — សូមមើល log ខាងលើ")'''


def code(src):
    return {
        "cell_type": "code",
        "execution_count": None,
        "metadata": {"id": None},
        "outputs": [],
        "source": src.splitlines(keepends=True),
    }


def md(src):
    return {
        "cell_type": "markdown",
        "metadata": {"id": None},
        "source": src.splitlines(keepends=True),
    }


def notebook(cells, name):
    for i, c in enumerate(cells):
        c["metadata"]["id"] = f"cell{i}"
    nb = {
        "nbformat": 4,
        "nbformat_minor": 0,
        "metadata": {
            "colab": {"provenance": [], "toc_visible": True},
            "kernelspec": {"display_name": "Python 3", "name": "python3"},
            "language_info": {"name": "python"},
        },
        "cells": cells,
    }
    out = ROOT / name
    out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
    print("wrote", name, len(cells), "cells,", out.stat().st_size, "bytes")


# --------------------------------------------------------------------------- #
# Notebook 1 — Gemini (cloud API)
# --------------------------------------------------------------------------- #
GEMINI_INTRO = """# ✦ Buffy AI — Chatbot ស្ទីល GPT នៅលើ Google Colab

កម្មវិធីជជែក AI ដែល៖
- 💬 ឆ្លើយសំណួរបានគ្រប់យ៉ាង ជាភាសាខ្មែរ ឬភាសាណាមួយ
- 🌐 ស្វែងរកអ៊ីនធឺណិត (Google Search) ដូច ChatGPT ព្រមទាំងបង្ហាញប្រភព
- 🖼️ ផ្ញើរូបភាពឱ្យ AI មើល និងវិភាគ
- 🎨 បង្កើត / កែរូបភាពដោយ AI (Nano Banana)
- 🔗 បង្កើត **link សាធារណៈ** សម្រាប់ជជែកពីទូរស័ព្ទ ឬកុំព្យូទ័រណាមួយ

---

## ជំហានទី 1 — យក API key ឥតគិតថ្លៃ
1. បើក 👉 https://aistudio.google.com/apikey
2. ចូលដោយគណនី Google រួចចុច **Create API key**
3. ចម្លង key (វាមានទម្រង់បែប `AIza...`)

## ជំហានទី 2 — រត់ cell ទី 1 និងទី 2
- Cell **1️⃣ ដំឡើង** — ដំឡើងបណ្ណាល័យ (រត់ម្តងប៉ុណ្ណោះ)
- Cell **2️⃣ ដាក់ API key** — paste key របស់អ្នក (លាក់មិនបង្ហាញ)

> គន្លឹះ៖ បើអ្នកមិនចង់ paste រាល់ដងទេ សូមដាក់ key ក្នុង 🔑 (Secrets) ខាងឆ្វេងដៃ ជាឈ្មោះ `GEMINI_API_KEY` ហើយបើក “Notebook access”។

## ជំហានទី 3 — រត់ cell ចុងក្រោយ
វានឹងបង្ហាញ **link** បែប `https://xxxx.trycloudflare.com` — ចម្លងទៅបើកក្នុង browser ហើយចាប់ផ្តើមជជែកបាន។

⏳ Link នេះដំណើរការដរាបណា cell ចុងក្រោយនៅរត់ (Colab បិទពេលអ្នកបិទ tab យូរ ឬអស់ម៉ោង)។
🔒 កុំចែករំលែក link ជាសាធារណៈ — អ្នកណាមាន link អាចប្រើ quota API key របស់អ្នកបាន។"""

GEMINI_INSTALL = """#@title 1️⃣ ដំឡើងបណ្ណាល័យ (រត់ម្តងប៉ុណ្ណោះ)
%pip install -q --upgrade fastapi uvicorn google-genai

""" + CLOUDFLARED + """
!cloudflared --version"""

GEMINI_KEY = """#@title 2️⃣ ដាក់ API key របស់អ្នក
import os

key = ""
try:  # ព្យាយាមអានពី Colab Secrets (🔑) មុន
    from google.colab import userdata
    key = userdata.get("GEMINI_API_KEY") or ""
except Exception:
    key = ""

if not key:
    from getpass import getpass
    key = getpass("Paste your Gemini API key (https://aistudio.google.com/apikey): ").strip()

os.environ["GEMINI_API_KEY"] = key
print("✅ ដាក់ API key រួចរាល់" if key else "❌ មិនមាន key — សូមរត់ cell នេះម្តងទៀត")"""

GEMINI_RUN = """#@title 3️⃣ បើក server + យក link សាធារណៈ
import re, subprocess, threading, time, urllib.request

import uvicorn

PORT = 8000

threading.Thread(
    target=uvicorn.run,
    args=("app:app",),
    kwargs=dict(host="127.0.0.1", port=PORT, log_level="warning"),
    daemon=True,
).start()

""" + WAIT_SERVER + """

print("🌐 កំពុងបើក tunnel… (រង់ចាំ 5-15 វិនាទី)\\n")

""" + RUN_TAIL

notebook(
    [
        md(GEMINI_INTRO),
        code(GEMINI_INSTALL),
        code("%%writefile ui.py\n" + UI),
        code("%%writefile app.py\n" + APP),
        code(GEMINI_KEY),
        code(GEMINI_RUN),
    ],
    "Buffy_AI_Colab.ipynb",
)

# --------------------------------------------------------------------------- #
# Notebook 2 — local Qwen via Ollama
# --------------------------------------------------------------------------- #
QWEN_INTRO = """# 🤖 Qwen Code — ម៉ូដែល open-source ដំណើរការក្នុង Colab (ឥតគិតថ្លៃ)

Notebook នេះទាញយក **GGUF** ពី Hugging Face រួចរត់វាក្នុង Colab តាម **Ollama**
(OpenAI-compatible API) ហើយបើក **UI ស្ទីល GPT** ដូច notebook មុន ជាមួយ link សាធារណៈ។
**មិនត្រូវការ API key** — ម៉ូដែលរត់លើ GPU របស់ Colab ផ្ទាល់។

---

## ⚠️ អានមុនគេ
1. **ត្រូវការ GPU**៖ `Runtime → Change runtime type → T4 GPU` (បើគ្មាន GPU វានឹងប្តូរទៅម៉ូដែល 7B លើ CPU ដែលយឺតខ្លាំង)
2. **ទំហំ**៖ ម៉ូដែល 13GB ត្រូវការ disk ~30GB (ទាញយក + import) — Colab មាន ~100GB គ្រប់គ្រាន់
3. **ពេលវេលា**៖ ទាញយក ~3–10 នាទី; ចម្លើយដំបូងយឺត (~1 នាទី) ព្រោះត្រូវ load ចូល GPU

## ជម្រើសម៉ូដែល (ទំហំពិតពី Hugging Face)

| ជម្រើស | ទំហំ | លក្ខណៈ |
|---|---|---|
| `coder30b` (default) | 13.3 GB | Qwen3-Coder-30B-A3B — ល្អបំផុតសម្រាប់ code, MoE 3B active → លឿន |
| `qwen38_27b` | 12.0 GB | Qwen3.8-27B — ជំនាន់ថ្មី, យឺតជាង (dense 27B) |
| `coder7b` | 4.7 GB | Qwen2.5-Coder-7B — ស្រាល, លឿន, ប្រើបានលើ CPU |

> **ហេតុអ្វីមិនប្រើ Qwen3.8-2.4T-A95B?** វាជា MoE ២.៤ ទ្រីលាន parameter៖ weights ដើម 4.9TB,
> GGUF តូចបំផុត ~397GB, ត្រូវការ RAM/VRAM 410GB+។ Colab មាន RAM 12–50GB និង disk ~100GB
> ដូច្នេះវាមិនអាចទាញយក ឬរត់ក្នុង Colab បានទេ — មិនមែនជាបញ្ហា link ទេ តែជាបញ្ហា hardware។

## អ្វីដែលបាន / មិនបាន
✅ ជជែក + សរសេរកូដ, គ្មាន API key, ទិន្នន័យមិនចេញក្រៅ, UI ស្អាត, link សាធារណៈ
❌ មិនអានរូបភាព, គ្មាន web search, គ្មានបង្កើតរូបភាព (សម្រាប់របស់ទាំងនោះ សូមប្រើ notebook Gemini)

> 🔐 ម៉ូដែល open-source មានគោលការណ៍សុវត្ថិភាពរបស់វាដោយខ្លួនឯង។ Notebook នេះ **មិន**កំណត់
> ឬ jailbreak ដើម្បីបំបែកគោលការណ៍ទាំងនោះទេ — សម្រាប់ការរៀនសុវត្ថិភាពសូមប្រើ lab
> ស្របច្បាប់ (TryHackMe, HackTheBox, DVWA) និងប្រព័ន្ធដែលអ្នកមានសិទ្ធិសាកល្បង។"""

QWEN_INSTALL = """#@title 1️⃣ ដំឡើង Ollama + cloudflared
# Ollama = engine សម្រាប់រត់ GGUF ក្នុងម៉ាស៊ីន ជាមួយ OpenAI-compatible API
!curl -fsSL https://ollama.com/install.sh | sh
!ollama --version

""" + CLOUDFLARED + """

import subprocess, time, urllib.request

# បើក ollama server ក្នុង background (Colab គ្មាន systemd)
subprocess.Popen(
    ["ollama", "serve"],
    stdout=open("/tmp/ollama.log", "w"),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)

for _ in range(60):
    try:
        urllib.request.urlopen("http://127.0.0.1:11434/api/tags", timeout=2)
        print("✅ Ollama server ដំណើរការ")
        break
    except Exception:
        time.sleep(1)
else:
    print("⚠️ Ollama មិនទាន់ឡើង — សូមមើល /tmp/ollama.log")

print()
print("=== GPU ===")
gpu = subprocess.run(
    ["nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
    capture_output=True, text=True,
).stdout.strip()
print(gpu or "⚠️ គ្មាន GPU — សូមបើក Runtime → Change runtime type → T4 GPU")"""

QWEN_MODEL = '''#@title 2️⃣ ទាញយកម៉ូដែល + import ចូល Ollama
#@markdown ជ្រើសម៉ូដែល (សូមមើលតារាងខាងលើ):
MODEL_CHOICE = "coder30b"  #@param ["coder30b", "qwen38_27b", "coder7b"]

import os, subprocess, time, urllib.request

MODELS = {
    "coder30b": dict(
        repo="unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF",
        file="Qwen3-Coder-30B-A3B-Instruct-Q3_K_S.gguf",
        size_gb=13.3, num_ctx=4096,
        label="Qwen3-Coder-30B-A3B (Q3_K_S)",
    ),
    "qwen38_27b": dict(
        repo="unsloth/Qwen3.8-27B-GGUF",
        file="Qwen3.8-27B-UD-IQ3_S.gguf",
        size_gb=12.0, num_ctx=4096,
        label="Qwen3.8-27B (UD-IQ3_S)",
    ),
    "coder7b": dict(
        repo="unsloth/Qwen2.5-Coder-7B-Instruct-GGUF",
        file="Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
        size_gb=4.7, num_ctx=8192,
        label="Qwen2.5-Coder-7B (Q4_K_M)",
    ),
}

gpu = subprocess.run(
    ["nvidia-smi", "--query-gpu=memory.total", "--format=csv,noheader,nounits"],
    capture_output=True, text=True,
).stdout.strip()
gpu_gb = 0.0
if gpu:
    try:
        gpu_gb = max(float(x) for x in gpu.splitlines()) / 1024
    except Exception:
        gpu_gb = 0.0

if gpu_gb < 15 and MODEL_CHOICE != "coder7b":
    print(f"⚠️ GPU មានតែ {gpu_gb:.0f}GB (ឬគ្មាន) — ម៉ូដែល {MODELS[MODEL_CHOICE]['label']} "
          "អាចលើស memory។ ប្តូរទៅ 'coder7b' បើចង់ឲ្យរត់រលូន (ស្រាល លឿន)។")

cfg = MODELS[MODEL_CHOICE]
print(f"📦 កំពុងទាញយក {cfg['label']} (~{cfg['size_gb']}GB) … សូមរង់ចាំ")

from huggingface_hub import hf_hub_download

gguf_path = hf_hub_download(
    repo_id=cfg["repo"],
    filename=cfg["file"],
    local_dir="/content/models",
)
print("✅ បានទាញយក:", gguf_path, f"({os.path.getsize(gguf_path)/1e9:.1f} GB)")

modelfile = f"""FROM {gguf_path}
PARAMETER num_ctx {cfg['num_ctx']}
PARAMETER temperature 0.3
"""
with open("/content/Modelfile", "w") as f:
    f.write(modelfile)

print("🧠 កំពុង import ចូល Ollama (អាចយូរ 1-3 នាទី) …")
r = subprocess.run(["ollama", "create", "buffy-coder", "-f", "/content/Modelfile"],
                   capture_output=True, text=True)
print(r.stdout[-2000:] or r.stderr[-2000:])
print("✅ ម៉ូដែលរួចរាល់" if r.returncode == 0 else "❌ import មិនបាន — សូមមើលសារខាងលើ")'''

QWEN_RUN = '''#@title 3️⃣ បើក UI + link សាធារណៈ
import os, re, subprocess, sys, time, urllib.request

PORT = 8000
os.environ["LLAMA_URL"] = "http://127.0.0.1:11434"
os.environ["LOCAL_MODEL"] = "buffy-coder"

# កំដៅម៉ូដែល (load ចូល GPU មុន) ដើម្បីឲ្យសារដំបូងក្នុង UI លឿន
print("🔥 កំពុង load ម៉ូដែលចូល GPU … (អាចយូរ ~1 នាទី)")
try:
    import requests
    requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": "buffy-coder", "prompt": "hi", "stream": False,
              "options": {"num_predict": 1}},
        timeout=900,
    )
    print("✅ ម៉ូដែលរួចរាល់")
except Exception as exc:
    print("⚠️ warm-up មិនបាន:", exc)

subprocess.Popen(
    [sys.executable, "-m", "uvicorn", "local_app:app", "--host", "127.0.0.1",
     "--port", str(PORT), "--log-level", "warning"],
    stdout=open("/tmp/ui.log", "w"),
    stderr=subprocess.STDOUT,
    start_new_session=True,
)

''' + WAIT_SERVER + '''

print("🌐 កំពុងបើក tunnel… (រង់ចាំ 5-15 វិនាទី)\\n")

''' + RUN_TAIL

notebook(
    [
        md(QWEN_INTRO),
        code(QWEN_INSTALL),
        code(QWEN_MODEL),
        code("%%writefile ui.py\n" + UI),
        code("%%writefile local_app.py\n" + LOCAL_APP),
        code(QWEN_RUN),
    ],
    "Qwen_Code_Colab.ipynb",
)
