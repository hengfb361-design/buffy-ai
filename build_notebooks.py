# -*- coding: utf-8 -*-
"""Regenerate the Qwen Colab notebook from the source files.

Usage: python build_notebooks.py
"""

import json
from pathlib import Path

ROOT = Path(__file__).parent
UI = (ROOT / "ui.py").read_text(encoding="utf-8")
LOCAL_APP = (ROOT / "local_app.py").read_text(encoding="utf-8")

for src in (UI, LOCAL_APP):
    assert src.endswith("\n")

CLOUDFLARED = """!wget -q https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -O /usr/local/bin/cloudflared
!chmod +x /usr/local/bin/cloudflared"""

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
            print("   URL     : " + m.group(0))
            print("   API key : " + os.environ.get("ACCESS_KEY", ""))
            print("\\n" + "=" * 68)
            print("🔑 paste ទាំង URL និង API key ក្នុង website → sidebar → Colab។")
            print("⚠️ កុំបិទ cell នេះ — កម្មវិធីដំណើរការពេល cell នេះនៅរត់។")
            print("   ចុច ⏹ ដើម្បីបញ្ឈប់។")

print("\\n🔌 Tunnel បានបិទ។ ប្រសិនបើអ្នកចង់បាន link ថ្មី សូមរត់ cell នេះម្តងទៀត។")"""


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


INTRO = """# 🤖 Qwen Code — ម៉ូដែល AI ដំណើរការក្នុង Google Colab (ឥតគិតថ្លៃ)

Notebook នេះទាញយក **GGUF** ពី Hugging Face រួចរត់វាក្នុង Colab តាម **Ollama**
(OpenAI-compatible API) ហើយបើក **UI ស្ទីល GPT** ជាមួយ link សាធារណៈ។
**គ្មាន API key, គ្មាន Gemini, គ្មានការចំណាយ** — ម៉ូដែលរត់លើ GPU របស់ Colab ផ្ទាល់។

---

## ⚡ ផ្លូវលឿន — បន្ទាត់តែមួយ (គ្មាន notebook)

មិនចង់រត់ cell ទាំងនេះ? ក្នុង Colab cell ថ្មី សរសេរបន្ទាត់នេះ (មាន `!` នៅដើម)៖

```bash
!curl -fsSL -o /content/buffy-start.sh https://raw.githubusercontent.com/hengfb361-design/buffy-ai/main/colab-start.sh && bash /content/buffy-start.sh
```

វាដំឡើង Ollama, ទាញ Qwen2.5-Coder-7B abliterated, បើក API + tunnel,
រួចបង្ហាញ **URL** និង **API key** សម្រាប់ paste ចូល website។

## ⚠️ អានមុនគេ
1. **ត្រូវការ GPU**៖ `Runtime → Change runtime type → T4 GPU` (Qwen3-8B ដែលជា default សមល្មមសម្រាប់ T4 16GB)
2. **ទំហំ**៖ ម៉ូដែល 13GB ត្រូវការ disk ~30GB (ទាញយក + import) — Colab មាន ~100GB គ្រប់គ្រាន់
3. **ពេលវេលា**៖ ទាញយក ~3–10 នាទី; ចម្លើយដំបូងយឺត (~1 នាទី) ព្រោះត្រូវ load ចូល GPU

## ជម្រើសម៉ូដែល (ទំហំពិតពី Hugging Face)

| ជម្រើស | ទំហំ | លក្ខណៈ |
|---|---|---|
| `qwen38b` (default) | 5.0 GB | Qwen3-8B Q4_K_M — ល្អណាស់សម្រាប់ T4, ឆាប់រៀន, សន្សំសំចៃ VRAM |
| `coder30b` | 13.3 GB | Qwen3-Coder-30B-A3B — ល្អបំផុតសម្រាប់ code, MoE 3B active → លឿន |
| `qwen38_27b` | 12.0 GB | Qwen3.8-27B — ជំនាន់ថ្មី, យឺតជាង (dense 27B) |
| `coder7b` | 4.7 GB | Qwen2.5-Coder-7B — ស្រាល, លឿន, ប្រើបានលើ CPU |

> **ហេតុអ្វីមិនប្រើ Qwen3.8-2.4T-A95B?** វាជា MoE ២.៤ ទ្រីលាន parameter៖ weights ដើម 4.9TB,
> GGUF តូចបំផុត ~397GB, ត្រូវការ RAM/VRAM 410GB+។ Colab មាន RAM 12–50GB និង disk ~100GB
> ដូច្នេះវាមិនអាចទាញយក ឬរត់ក្នុង Colab បានទេ — មិនមែនជាបញ្ហា link ទេ តែជាបញ្ហា hardware។

## អ្វីដែលបាន / មិនបាន
✅ ជជែក + សរសេរកូដ, គ្មាន API key, ទិន្នន័យមិនចេញក្រៅ, UI ស្អាត, link សាធារណៈ
❌ មិនអានរូបភាព, គ្មាន web search, គ្មានបង្កើតរូបភាព (ម៉ូដែល local ជា text-only)

> 🔐 ម៉ូដែល open-source មានគោលការណ៍សុវត្ថិភាពរបស់វាដោយខ្លួនឯង។ Notebook នេះ **មិន**កំណត់
> ឬ jailbreak ដើម្បីបំបែកគោលការណ៍ទាំងនោះទេ — សម្រាប់ការរៀនសុវត្ថិភាពសូមប្រើ lab
> ស្របច្បាប់ (TryHackMe, HackTheBox, DVWA) និងប្រព័ន្ធដែលអ្នកមានសិទ្ធិសាកល្បង។"""

INSTALL = """#@title 1️⃣ ដំឡើង Ollama + cloudflared
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

MODEL_CELL = '''#@title 2️⃣ ទាញយកម៉ូដែល + import ចូល Ollama
#@markdown ជ្រើសម៉ូដែល (សូមមើលតារាងខាងលើ):
MODEL_CHOICE = "coder7b_ablit"  #@param ["coder7b_ablit", "qwen38b", "coder30b", "qwen38_27b", "coder7b"]

import os, subprocess, time, urllib.request

MODELS = {
    "coder7b_ablit": dict(
        repo="bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF",
        file="Qwen2.5-Coder-7B-Instruct-abliterated-Q4_K_M.gguf",
        size_gb=4.7, num_ctx=8192,
        label="Qwen2.5-Coder-7B abliterated (Q4_K_M)",
        tag="qwen2.5-coder-7b-abliterated",
    ),
    "qwen38b": dict(
        repo="unsloth/Qwen3-8B-GGUF",
        file="Qwen3-8B-Q4_K_M.gguf",
        size_gb=5.0, num_ctx=8192,
        label="Qwen3-8B (Q4_K_M)",
        tag="qwen3-8b",
    ),
    "coder30b": dict(
        repo="unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF",
        file="Qwen3-Coder-30B-A3B-Instruct-Q3_K_S.gguf",
        size_gb=13.3, num_ctx=4096,
        label="Qwen3-Coder-30B-A3B (Q3_K_S)",
        tag="qwen3-coder-30b",
    ),
    "qwen38_27b": dict(
        repo="unsloth/Qwen3.8-27B-GGUF",
        file="Qwen3.8-27B-UD-IQ3_S.gguf",
        size_gb=12.0, num_ctx=4096,
        label="Qwen3.8-27B (UD-IQ3_S)",
        tag="qwen3.8-27b",
    ),
    "coder7b": dict(
        repo="unsloth/Qwen2.5-Coder-7B-Instruct-GGUF",
        file="Qwen2.5-Coder-7B-Instruct-Q4_K_M.gguf",
        size_gb=4.7, num_ctx=8192,
        label="Qwen2.5-Coder-7B (Q4_K_M)",
        tag="qwen2.5-coder-7b",
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

if gpu_gb < 15 and MODEL_CHOICE not in ("qwen38b", "coder7b", "coder7b_ablit"):
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

MODEL_TAG = cfg.get("tag") or "buffy-coder"
print("🧠 កំពុង import ចូល Ollama (អាចយូរ 1-3 នាទី) …")
r = subprocess.run(["ollama", "create", MODEL_TAG, "-f", "/content/Modelfile"],
                   capture_output=True, text=True)
print(r.stdout[-2000:] or r.stderr[-2000:])
print("✅ ម៉ូដែលរួចរាល់" if r.returncode == 0 else "❌ import មិនបាន — សូមមើលសារខាងលើ")'''

RUN = '''#@title 3️⃣ បើក UI + link សាធារណៈ
import os, re, subprocess, sys, time, urllib.request

PORT = 8000
# MODEL_TAG មកពី cell ២ (ឈ្មោះម៉ូដែលដែលបាន import) — បើរត់ cell នេះតែឯង ប្រើ "buffy-coder"
MODEL_TAG = globals().get("MODEL_TAG", "buffy-coder")
os.environ["LLAMA_URL"] = "http://127.0.0.1:11434"
os.environ["LOCAL_MODEL"] = MODEL_TAG
print("🧩 ម៉ូដែល:", MODEL_TAG)

# Access key សម្រាប់ website ខាងក្រៅ (ឧ. ai.onrender.com) ហៅមក server នេះ។
# បើអ្នកកំណត់ BUFFY_ACCESS_KEY ក្នុង Colab 🔑 Secrets វាប្រើតម្លៃនោះ បើអត់ វាបង្កើតថ្មី
# មួយដោយស្វ័យប្រវត្តិ ហើយបង្ហាញនៅ cell ៣ (ព្រមជាមួយ URL)។
import secrets

ACCESS_KEY = os.environ.get("BUFFY_ACCESS_KEY", "").strip()
if not ACCESS_KEY:
    try:
        from google.colab import userdata
        ACCESS_KEY = (userdata.get("BUFFY_ACCESS_KEY") or "").strip()
    except Exception:
        ACCESS_KEY = ""
if not ACCESS_KEY:
    ACCESS_KEY = secrets.token_urlsafe(12)
os.environ["ACCESS_KEY"] = ACCESS_KEY

# Web search (Exa) — key ត្រូវដាក់ក្នុង Colab 🔑 Secrets (ឈ្មោះ EXA_API_KEY)
# របៀប៖ sidebar ខាងឆ្វេង → 🔑 Secrets → Add New Secret
#   Name = EXA_API_KEY   Value = key របស់អ្នក   → បើក toggle "Notebook access"
try:
    from google.colab import userdata
    _k = userdata.get("EXA_API_KEY")
    if _k:
        os.environ["EXA_API_KEY"] = _k
        print("✅ EXA_API_KEY បានផ្ទុកពី Colab Secrets — web search បើក")
    else:
        print("ℹ️ EXA_API_KEY ទទេ — web search បិទ (app នៅតែរត់)។ ដាក់បាន: 🔑 Secrets")
except Exception:
    print("ℹ️ រកមិនឃើញ EXA_API_KEY ក្នុង Colab Secrets — web search បិទ (app នៅតែរត់)។")
    print("   ដាក់បានឥឡូវ៖ sidebar ខាងឆ្វេង → 🔑 Secrets → Add New Secret")
    print("   Name = EXA_API_KEY , Value = key , រួចបើក toggle 'Notebook access' → run cell នេះម្តងទៀត")

# កំដៅម៉ូដែល (load ចូល GPU មុន) ដើម្បីឲ្យសារដំបូងក្នុង UI លឿន
print("🔥 កំពុង load ម៉ូដែលចូល GPU … (អាចយូរ ~1 នាទី)")
try:
    import requests
    requests.post(
        "http://127.0.0.1:11434/api/generate",
        json={"model": MODEL_TAG, "prompt": "hi", "stream": False,
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

cells = [
    md(INTRO),
    code(INSTALL),
    code(MODEL_CELL),
    code("%%writefile ui.py\n" + UI),
    code("%%writefile local_app.py\n" + LOCAL_APP),
    code(RUN),
]
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

out = ROOT / "Qwen_Code_Colab.ipynb"
out.write_text(json.dumps(nb, ensure_ascii=False, indent=1), encoding="utf-8")
print("wrote", out.name, len(cells), "cells,", out.stat().st_size, "bytes")
