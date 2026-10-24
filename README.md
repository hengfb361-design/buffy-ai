# ✦ Buffy AI — Chatbot ស្ទីល GPT ដែលរត់ local ក្នុង Google Colab

កម្មវិធីជជែក AI ដែលរត់ **ម៉ូដែល open-source (Qwen GGUF)** នៅលើ GPU របស់ Google Colab
ហើយបង្កើត **link សាធារណៈ** សម្រាប់ជជែកពីទូរស័ព្ទ ឬកុំព្យូទ័រណាមួយ។

- ❌ គ្មាន Gemini, គ្មាន API key, គ្មានការចំណាយ
- ✅ ម៉ូដែលរត់ក្នុង Colab ផ្ទាល់ (ទិន្នន័យមិនចេញទៅខាងក្រៅ)
- ✅ UI ស្ទីល GPT៖ dark theme, streaming, Markdown + code block មាន copy, ភ្ជាប់ប្រវត្តិ, ទាញយក, ប្រើបានលើទូរស័ព្ទ

> ⚠️ ដែនកំណត់៖ ម៉ូដែល local ជា **text-only** — មិនអានរូបភាព, គ្មាន web search, គ្មានបង្កើតរូបភាព។

## ឯកសារ

| ឯកសារ | តួនាទី |
|---|---|
| `Qwen_Code_Colab.ipynb` | Notebook សម្រាប់ Colab៖ ដំឡើង engine, ទាញយក GGUF, បើក UI + link |
| `local_app.py` | Server៖ បម្រើ UI និង proxy streaming ទៅ engine OpenAI-compatible (Ollama / llama.cpp) |
| `ui.py` | UI HTML/CSS/JS តែមួយ (គ្មាន build step) |
| `build_notebooks.py` | បង្កើត notebook ឡើងវិញពីកូដ (`python build_notebooks.py`) |
| `push_to_github.sh` | រុញ project ទៅ GitHub ដោយពាក្យបញ្ជាតែមួយ |

Repo៖ https://github.com/hengfb361-design/buffy-ai

## របៀបប្រើ

1. បើក https://colab.research.google.com → **Upload** `Qwen_Code_Colab.ipynb`
2. `Runtime → Change runtime type → T4 GPU`
3. រត់ cell **1️⃣ ដំឡើង** → **2️⃣ ទាញយកម៉ូដែល** → **3️⃣ បើក UI**
4. ចម្លង link `https://xxxx.trycloudflare.com` ហើយចាប់ផ្តើមជជែក

### ម៉ូដែលដែលអាចជ្រើស (ទំហំពិតពី Hugging Face)

| ជម្រើស | ទំហំ | កំណត់សម្គាល់ |
|---|---|---|
| `coder30b` (default) — Qwen3-Coder-30B-A3B `Q3_K_S` | 13.3 GB | ល្អបំផុតសម្រាប់ code; MoE 3B active → លឿន; ត្រូវការ T4 16GB |
| `qwen38_27b` — Qwen3.8-27B `UD-IQ3_S` | 12.0 GB | ជំនាន់ថ្មី; dense → យឺតជាង |
| `coder7b` — Qwen2.5-Coder-7B `Q4_K_M` | 4.7 GB | ស្រាល/លឿន; រត់បានលើ CPU (យឺត) |

> **Qwen3.8-2.4T-A95B មិនអាចរត់ក្នុង Colab បានទេ**៖ weights ដើម ~4.9 TB,
> GGUF តូចបំផុត ~397 GB, ត្រូវការ RAM/VRAM ~410 GB+. Colab មាន RAM 12–50 GB
> និង disk ~100 GB។ នេះជាដែនកំណត់ hardware មិនមែនបញ្ហា link ទេ។

## រត់ក្នុងម៉ាស៊ីនផ្ទាល់ខ្លួន (ស្រេចចិត្ត)

```bash
pip install fastapi uvicorn requests
# engine ណាមួយដែលជា OpenAI-compatible ក៏បាន (Ollama ងាយបំផុត)
ollama serve
ollama create buffy-coder -f Modelfile
LLAMA_URL=http://127.0.0.1:11434 LOCAL_MODEL=buffy-coder \
  uvicorn local_app:app --host 127.0.0.1 --port 8000
```

## ការតភ្ជាប់ API key (server-side)

Website/`local_app.py` អាចប្រើ backend ពីរ — **key អានតែនៅ server, មិនដែលឆ្លងកាត់ browser**៖

| Env var | តួនាទី | ដាក់នៅឯណា |
|---|---|---|
| `API_BASE_URL` | base URL របស់ API ពិត (OpenAI-compatible) ឧ. `https://api.example.com/v1` | Sites → Secrets ឬ env |
| `API_KEY` | bearer key សម្រាប់ API នោះ | **Sites → Secrets** (ឬ Colab 🔑 Secrets) |
| `API_MODEL` | model id សម្រាប់ API នោះ | Sites → Secrets ឬ env |
| `LLAMA_URL` | engine local (Ollama / llama.cpp) — ប្រើពេល `API_BASE_URL` ទទេ | env |
| `LOCAL_MODEL` | model id នៅក្នុង engine local | env |
| `EXA_API_KEY` | **web search** សម្រាប់បង្ហាញប្រភព (Exa) — គ្មាន key = search បិទ | Sites → Secrets / Colab 🔑 Secrets |

- **មិនកំណត់** `API_BASE_URL` → ប្រើ engine local (`LLAMA_URL`) ដូចមុន
- **កំណត់** `API_BASE_URL` → ប្រើ API ពិត, `API_KEY` បញ្ជូនជា `Authorization: Bearer …` (តែនៅ server)
- `/api/health` រាយ `key_set: true/false` និង `web_search: "exa"|"off"` តែ **មិនបញ្ចេញតម្លៃ key** ទេ

### Web search (បង្ហាញប្រភព)

បើក toggle **🌐 ស្វែងរកអ៊ីនធឺណិត** ក្នុង sidebar → server ស្វែងរក ហើយ៖
- បង្ហាញ **chips ប្រភព** ចុចបានក្រោមចម្លើយ
- បញ្ចូលលទ្ធផល ៥ ដំបូង (title + URL + snippet) ក្នុង context ដើម្បីឲ្យម៉ូដែលដកស្រង់
- គ្មាន `EXA_API_KEY` → ប្រាប់ជាសារ រួចឆ្លើយធម្មតាបន្ត (មិន crash)
- គ្មាន `"type": "auto"`, គ្មានការបរាជ័យ → បញ្ជូន HTTP status ជាសារ

> Search API ឥតគិតថ្លៃ៖ Exa (≈2,800 searches ដំបូង + $10/ខែ គ្មានកាត)។ ទោះជាយ៉ាងណា កូដនេះក៏ទទួល
> endpoint ណាមួយដែលគាំទ្រ `POST …/search` + `Authorization: Bearer` បានដែរ។

> ⛔ កុំដាក់ key ក្នុងកូដ, `.env` ដែល commit, URL ឬ input box ក្នុង browser។
> បើ key ធ្លាយ (ឧ. paste ក្នុង chat) → revoke/regenerate ភ្លាម។

## Deploy ទៅ Render (website អចិន្ត្រៃយ៍)

Repo នេះ deploy ទៅ [Render](https://dashboard.render.com) បានដោយគ្មាន Docker — ត្រូវការតែ ៣ ក្រណាត់នៅ **New → Web Service** (ជ្រើស repo នេះ)៖

| Field | តម្លៃ |
|---|---|
| Runtime | `Python 3` |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn local_app:app --host 0.0.0.0 --port $PORT` |

> `requirements.txt` ត្រូវបាន commit ក្នុង repo (fastapi, uvicorn, requests) — ដោយសារតែ repo អត់មានវា
> Render error `Module "local_app" not found` / `No module named …`

Env vars នៅ **Environment** tab របស់ service (មិនចាំបាច់សម្រាប់ local Colab mode ទេ)៖

- `API_BASE_URL` + `API_KEY` + `API_MODEL` → ឆ្លើយពី API ពិត (គ្មាន GPU លើ Render ទេ)
- `EXA_API_KEY` → web search បង្ហាញប្រភព

> Render ឥតគិតថ្លៃ **sleep បន្ទាប់ពី ១៥ នាទី idle** — ការសួរដំបូងប្រហែល ៥០វិនាទី យឺត រួចប្រក្នុងល្បឿនធម្មតា។

## Push ទៅ GitHub

```bash
./push_to_github.sh https://github.com/<username>/<repo>.git
```

## សុវត្ថិភាព

- Repo នេះគ្មាន key ឬ token ណាមួយទេ — ហើយមិនត្រូវបន្ថែមវាឡើយ
- link `trycloudflare.com` ជាសាធារណៈ៖ អ្នកណាមាន link អាចប្រើ GPU/ម៉ូដែលរបស់អ្នក — កុំបង្ហោះជាសាធារណៈ
- បើ token/key ធ្លាយចេញ (ឧ. paste ក្នុង chat) សូម revoke/regenerate ភ្លាម

## ការប្រើប្រាស់ប្រកបដោយក្រមសីលធម៌

Project នេះមិនកំណត់បំពាន (jailbreak) ដើម្បីបំបែកគោលការណ៍សុវត្ថិភាពរបស់ម៉ូដែលឡើយ។
សម្រាប់ការរៀនសុវត្ថិភាព សូមប្រើ lab ស្របច្បាប់ (TryHackMe, HackTheBox, DVWA)
និងប្រព័ន្ធដែលអ្នកមានសិទ្ធិសាកល្បងជាលាយលក្ខណ៍អក្សរ។

## License

MIT
