#!/usr/bin/env bash
# Buffy AI — បើក API សម្រាប់ Qwen2.5-Coder-7B abliterated ក្នុង Google Colab
# ដោយបន្ទាត់តែមួយ។
#
# ក្នុង Colab (cell ថ្មី) សរសេរបន្ទាត់នេះ — មាន «!» នៅដើម បើអត់ វានឹងចេញ SyntaxError៖
#
#   !curl -fsSL -o /content/buffy-start.sh https://raw.githubusercontent.com/hengfb361-design/buffy-ai/main/colab-start.sh && bash /content/buffy-start.sh
#
# script នេះនឹង៖
#   ១. ដំឡើង Ollama (បើគ្មាន) និងបើក engine
#   ២. ទាញយក Qwen2.5-Coder-7B-Instruct-abliterated GGUF (~4.7 GB)
#   ៣. import ចូល Ollama ជា tag qwen2.5-coder-7b-abliterated
#   ៤. បើក API (local_app.py) + tunnel សាធារណៈ
#   ៥. បង្ហាញ URL និង API key → paste ក្នុង website → sidebar → Colab
#
# អាចប្តូរតាម env មុនពេលរត់ ឧ. BUFFY_MODEL_TAG=my-model bash colab-start.sh
# ចំណាំ៖ បើ cell នេះដាច់ (Runtime disconnected) ត្រូវរត់ម្តងទៀត — key ថ្មីនឹងបង្កើត។

set -euo pipefail

RAW_BASE="${BUFFY_RAW_BASE:-https://raw.githubusercontent.com/hengfb361-design/buffy-ai/main}"
HF_REPO="${BUFFY_HF_REPO:-bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF}"
HF_FILE="${BUFFY_HF_FILE:-Qwen2.5-Coder-7B-Instruct-abliterated-Q4_K_M.gguf}"
MODEL_TAG="${BUFFY_MODEL_TAG:-qwen2.5-coder-7b-abliterated}"
PORT="${PORT:-8000}"
WORK="${BUFFY_HOME:-/content/buffy-api}"
OLLAMA_URL_LOCAL="http://127.0.0.1:11434"

say()  { printf '\n\033[1;36m%s\033[0m\n' "$*"; }
ok()   { printf '\033[1;32m✅ %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m⚠️  %s\033[0m\n' "$*"; }
die()  { printf '\033[1;31m❌ %s\033[0m\n' "$*" >&2; exit 1; }

command -v curl >/dev/null 2>&1 || die "រកមិនឃើញ curl — សូមប្រើ Colab runtime ធម្មតា"
command -v python3 >/dev/null 2>&1 || die "រកមិនឃើញ python3"
mkdir -p "$WORK"

# បិទអ្វីៗទាំងអស់ពេលចុច ⏹
cleanup() {
  trap - INT TERM EXIT
  pkill -f "cloudflared tunnel" 2>/dev/null || true
  pkill -f "uvicorn local_app:app" 2>/dev/null || true
  pkill -f "ollama serve" 2>/dev/null || true
  printf '\n\033[1;33m🔌 បានបិទ API និង tunnel។\033[0m\n'
}
trap cleanup INT TERM EXIT

# ─── ១/៥ Ollama ────────────────────────────────────────────────────────────
say "១/៥  ពិនិត្យ Ollama"
if ! command -v ollama >/dev/null 2>&1; then
  echo "   កំពុងដំឡើង Ollama (១–២ នាទី) …"
  curl -fsSL https://ollama.com/install.sh | sh >"$WORK/ollama-install.log" 2>&1 \
    || die "ដំឡើង Ollama មិនបាន — សូមមើល $WORK/ollama-install.log"
fi
if ! curl -sf "$OLLAMA_URL_LOCAL/api/tags" >/dev/null 2>&1; then
  echo "   កំពុងបើក ollama serve …"
  nohup ollama serve >"$WORK/ollama.log" 2>&1 </dev/null &
  for _ in $(seq 1 60); do
    curl -sf "$OLLAMA_URL_LOCAL/api/tags" >/dev/null 2>&1 && break
    sleep 1
  done
fi
curl -sf "$OLLAMA_URL_LOCAL/api/tags" >/dev/null 2>&1 \
  || die "Ollama មិនឡើង — សូមមើល $WORK/ollama.log"
ok "Ollama ដំណើរការ"

# ─── ២/៥ ទាញយកម៉ូដែល ──────────────────────────────────────────────────────
GGUF="$WORK/$HF_FILE"
say "២/៥  ទាញយក $HF_FILE (~4.7 GB)"
if [ -s "$GGUF" ]; then
  ok "មានឯកសាររួចហើយ ($(du -h "$GGUF" | cut -f1)) — រំលងការទាញយក"
else
  curl -fL --retry 3 -C - --progress-bar -o "$GGUF" \
    "https://huggingface.co/$HF_REPO/resolve/main/$HF_FILE" \
    || die "ទាញយកមិនបាន — ពិនិត្យ internet រួចរត់ cell នេះម្តងទៀត (វាទាញបន្ត)"
  ok "បានទាញយក ($(du -h "$GGUF" | cut -f1))"
fi

# ─── ៣/៥ import ចូល Ollama ─────────────────────────────────────────────────
say "៣/៥  import ចូល Ollama ជា «$MODEL_TAG»"
if ollama show "$MODEL_TAG" >/dev/null 2>&1; then
  ok "ម៉ូដែលមានរួចហើយ — រំលង"
else
  cat >"$WORK/Modelfile" <<EOF
FROM $GGUF
PARAMETER num_ctx 8192
PARAMETER temperature 0.3
EOF
  ollama create "$MODEL_TAG" -f "$WORK/Modelfile" >"$WORK/ollama-create.log" 2>&1 \
    || die "import មិនបាន — សូមមើល $WORK/ollama-create.log"
  ok "import រួចរាល់"
fi

# ─── ៤/៥ API ───────────────────────────────────────────────────────────────
say "៤/៥  បើក API (uvicorn) នៅ port $PORT"
python3 -m pip install -q fastapi uvicorn requests >"$WORK/pip.log" 2>&1 \
  || die "pip install មិនបាន — សូមមើល $WORK/pip.log"

for f in local_app.py ui.py; do
  curl -fsSL -o "$WORK/$f" "$RAW_BASE/$f" || die "ទាញយក $f មិនបាន"
done

ACCESS_KEY="${BUFFY_ACCESS_KEY:-}"
if [ -z "$ACCESS_KEY" ]; then
  ACCESS_KEY="$(python3 - <<'PY' 2>/dev/null || true
try:
    from google.colab import userdata
    print((userdata.get("BUFFY_ACCESS_KEY") or "").strip())
except Exception:
    print("")
PY
)"
fi
if [ -z "$ACCESS_KEY" ]; then
  ACCESS_KEY="$(python3 -c 'import secrets; print(secrets.token_urlsafe(12))')"
fi

EXA_KEY="${EXA_API_KEY:-}"
if [ -z "$EXA_KEY" ]; then
  EXA_KEY="$(python3 - <<'PY' 2>/dev/null || true
try:
    from google.colab import userdata
    print((userdata.get("EXA_API_KEY") or "").strip())
except Exception:
    print("")
PY
)"
fi

cd "$WORK"
LLAMA_URL="$OLLAMA_URL_LOCAL" LOCAL_MODEL="$MODEL_TAG" \
  ACCESS_KEY="$ACCESS_KEY" EXA_API_KEY="$EXA_KEY" \
  nohup python3 -m uvicorn local_app:app --host 127.0.0.1 --port "$PORT" \
  --log-level warning >"$WORK/ui.log" 2>&1 </dev/null &

ready=""
for _ in $(seq 1 80); do
  if curl -sf "http://127.0.0.1:$PORT/api/health" >/dev/null 2>&1; then ready=1; break; fi
  sleep 1
done
[ -n "$ready" ] || die "API មិនឡើង — សូមមើល $WORK/ui.log"
ok "API ដំណើរការ"

# ─── ៥/៥ tunnel ────────────────────────────────────────────────────────────
say "៥/៥  បើក tunnel សាធារណៈ"
if ! command -v cloudflared >/dev/null 2>&1; then
  curl -fsSL -o /usr/local/bin/cloudflared \
    https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 \
    || die "ទាញយក cloudflared មិនបាន"
  chmod +x /usr/local/bin/cloudflared
fi
nohup cloudflared tunnel --url "http://127.0.0.1:$PORT" --no-autoupdate \
  >"$WORK/tunnel.log" 2>&1 </dev/null &

PUBLIC_URL=""
for _ in $(seq 1 60); do
  PUBLIC_URL="$(grep -Eo 'https://[a-z0-9-]+\.trycloudflare\.com' "$WORK/tunnel.log" | head -1 || true)"
  [ -n "$PUBLIC_URL" ] && break
  sleep 1
done
[ -n "$PUBLIC_URL" ] || die "tunnel មិនចេញ URL — សូមមើល $WORK/tunnel.log"

printf '\n\033[1;32m%s\033[0m\n' "════════════════════════════════════════════════════════════════"
printf '\033[1;32m🎉 API រួចរាល់ — paste ចូល website → sidebar → Colab\033[0m\n\n'
printf '   Model   : \033[1m%s\033[0m\n' "$MODEL_TAG"
printf '   URL     : \033[1m%s\033[0m\n' "$PUBLIC_URL"
printf '   API key : \033[1m%s\033[0m\n' "$ACCESS_KEY"
printf '\033[1;32m%s\033[0m\n' "════════════════════════════════════════════════════════════════"
printf '   (paste បន្ទាត់ណាមួយក្នុងប្រអប់ Colab របស់ website — វាស្រង់យកទាំងពីរ)\n'
printf '   បើក %s ក៏ជជែកបានផ្ទាល់ដែរ\n\n' "$PUBLIC_URL"
printf '\033[1;33m⚠️  កុំបិទ cell នេះ — កម្មវិធីរត់ពេល cell នៅរត់។ ចុច ⏹ ដើម្បីបញ្ឈប់។\033[0m\n'

# រក្សា cell ឲ្យរស់ ដើម្បីកុំឲ្យ Colab បិទ process
while :; do sleep 30; done
