# ✦ Buffy AI — Chatbot ស្ទីល GPT សម្រាប់ Google Colab

កម្មវិធីជជែក AI ដែលដំណើរការក្នុង Google Colab ហើយបង្កើត **link សាធារណៈ** សម្រាប់ជជែក
ពីទូរស័ព្ទ ឬកុំព្យូទ័រណាមួយ។ មានពីរកំណែ៖

| Notebook | Engine | ត្រូវការ API key? | មុខងារ |
|---|---|---|---|
| `Buffy_AI_Colab.ipynb` | Gemini API (ពពក) | ✅ បាទ (ឥតគិតថ្លៃ) | ជជែក, **web search**, **អានរូបភាព**, **បង្កើតរូបភាព** |
| `Qwen_Code_Colab.ipynb` | Qwen GGUF (local, Ollama) | ❌ ទេ | ជជែក + សរសេរកូដ លើ GPU របស់ Colab |

UI ដូចគ្នាទាំងពីរ៖ dark theme ស្ទីល GPT, Markdown + code block មាន copy, streaming,
ភ្ជាប់រូបភាព, ប្រភព, ទាញយកប្រវត្តិ (`⬇️`), ប្រវត្តិរក្សាក្នុង browser, ប្រើបានលើទូរស័ព្ទ។

## ឯកសារ

| ឯកសារ | តួនាទី |
|---|---|
| `Buffy_AI_Colab.ipynb` | Notebook សម្រាប់ Gemini (upload ចូល Colab ហើយរត់) |
| `Qwen_Code_Colab.ipynb` | Notebook សម្រាប់ម៉ូដែល Qwen GGUF local |
| `app.py` | Server Gemini៖ streaming, Google Search grounding, រូបភាព, បង្កើតរូបភាព |
| `local_app.py` | Server local៖ proxy ទៅ engine OpenAI-compatible (Ollama / llama.cpp) |
| `ui.py` | UI HTML/CSS/JS តែមួយ (ប្រើដោយ app ទាំងពីរ) |
| `build_notebooks.py` | បង្កើត notebook ឡើងវិញពីកូដ (`python build_notebooks.py`) |
| `push_to_github.sh` | រុញ project ទៅ GitHub ដោយពាក្យបញ្ជាតែមួយ |

## របៀបប្រើ (Gemini)

1. យក API key ឥតគិតថ្លៃ៖ https://aistudio.google.com/apikey
2. Upload `Buffy_AI_Colab.ipynb` ចូល https://colab.research.google.com
3. រត់ cell **1️⃣ ដំឡើង** → **2️⃣ ដាក់ API key** → **3️⃣ បើក server**
4. ចម្លង link `https://xxxx.trycloudflare.com` ហើយបើកជជែក

## របៀបប្រើ (Qwen local)

1. `Runtime → Change runtime type → T4 GPU`
2. Upload `Qwen_Code_Colab.ipynb` ហើយរត់ cell **1️⃣ → 2️⃣ → 3️⃣**
3. Cell 2 ជ្រើសម៉ូដែលបាន (ទំហំពិតពី Hugging Face)៖

| ជម្រើស | ទំហំ | កំណត់សម្គាល់ |
|---|---|---|
| `coder30b` — Qwen3-Coder-30B-A3B `Q3_K_S` | 13.3 GB | ល្អបំផុតសម្រាប់ code; MoE 3B active → លឿន; ត្រូវការ T4 16GB |
| `qwen38_27b` — Qwen3.8-27B `UD-IQ3_S` | 12.0 GB | ជំនាន់ថ្មី; dense → យឺតជាង |
| `coder7b` — Qwen2.5-Coder-7B `Q4_K_M` | 4.7 GB | ស្រាល/លឿន; រត់បានលើ CPU (យឺត) |

> **Qwen3.8-2.4T-A95B មិនអាចរត់ក្នុង Colab បានទេ**៖ weights ដើម ~4.9 TB,
> GGUF តូចបំផុត ~397 GB, ត្រូវការ RAM/VRAM ~410 GB+. Colab មាន RAM 12–50 GB
> និង disk ~100 GB។ នេះជាដែនកំណត់ hardware មិនមែនបញ្ហា link ទេ។

## Push ទៅ GitHub

```bash
# 1) បង្កើត repo ទទេលើ https://github.com/new (កុំធីក "Add a README")
# 2) រត់៖
./push_to_github.sh https://github.com/<username>/<repo>.git
```

បើ git សួរ password សូមប្រើ **Personal Access Token ថ្មី** (scope `repo`) — មិនត្រូវប្រើ token ចាស់
ដែលបាន paste ក្នុង chat ឡើយ (សូម revoke វាមុន)។

## សុវត្ថិភាព

- **កុំ commit API key ឬ token** ចូល repo — ដាក់ក្នុង Colab Secrets (🔑) ឬ `.env` (មានក្នុង `.gitignore`)
- link `trycloudflare.com` ជាសាធារណៈ៖ អ្នកណាមាន link អាចប្រើ key/quota របស់អ្នក — កុំបង្ហោះជាសាធារណៈ
- បើ token/key ធ្លាយចេញ (ឧ. paste ក្នុង chat) សូម revoke/regenerate ភ្លាម

## ការប្រើប្រាស់ប្រកបដោយក្រមសីលធម៌

Project នេះមិនមាន និងមិនកំណត់បំពាន (jailbreak) ដើម្បីបំបែកគោលការណ៍សុវត្ថិភាពរបស់ម៉ូដែល
ដើម្បីឆ្លើយសំណួរវាយប្រហារ/ hacking ឡើយ។ សម្រាប់ការរៀនសុវត្ថិភាព សូមប្រើ lab ស្របច្បាប់
(TryHackMe, HackTheBox, DVWA) និងប្រព័ន្ធដែលអ្នកមានសិទ្ធិសាកល្បងជាលាយលក្ខណ៍អក្សរ។

## License

MIT
