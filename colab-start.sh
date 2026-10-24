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
PORT="${PORT:-8000}"
WORK="${BUFFY_HOME:-/content/buffy-api}"
OLLAMA_URL_LOCAL="http://127.0.0.1:11434"

# ជម្រើសម៉ូដែល — script រើសតាម VRAM ដែល Colab មាន (បញ្ជាបានដោយ BUFFY_MODEL=coder32b|coder30b|coder7b|coder3b)
#   coder32b = Qwen2.5-Coder-32B Q4_K_M (19.85GB — "model 20g") ត្រូវការ A100/L4 24GB+
#   coder30b = Qwen3-Coder-30B-A3B Q3_K_S (13.3GB, MoE 3B active → លឿន) សម្រាប់ T4 16GB
#   coder7b  = Qwen2.5-Coder-7B abliterated Q4_K_M (4.7GB) ស្រាល/លឿន
#   coder3b  = Qwen2.5-Coder-3B abliterated Q4_K_M (1.9GB) លឿនបំផុត / គ្មាន GPU
HF_REPO=""; HF_FILE=""; MODEL_TAG=""; MODEL_SIZE_GB=""; CTX=4096; VRAM_GIB=0

choose_model() {
  local mib
  mib=$(nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits 2>/dev/null | head -1 | tr -dc '0-9' || true)
  [ -n "$mib" ] || mib=0
  VRAM_GIB=$(( mib / 1024 ))
  case "${BUFFY_MODEL:-}" in
    coder32b|coder30b|coder7b|coder3b) VRAM_GIB=99 ;;  # force: រំលងការពិនិត្យ GPU
  esac
  if [ "${BUFFY_MODEL:-}" = "coder32b" ] || [ -z "${BUFFY_MODEL:-}" ] && [ "$VRAM_GIB" -ge 23 ]; then
    HF_REPO="bartowski/Qwen2.5-Coder-32B-Instruct-GGUF"
    HF_FILE="Qwen2.5-Coder-32B-Instruct-Q4_K_M.gguf"
    MODEL_TAG="qwen2.5-coder-32b"; MODEL_SIZE_GB="19.9"
  elif [ "${BUFFY_MODEL:-}" = "coder30b" ] || [ -z "${BUFFY_MODEL:-}" ] && [ "$VRAM_GIB" -ge 13 ]; then
    HF_REPO="unsloth/Qwen3-Coder-30B-A3B-Instruct-GGUF"
    HF_FILE="Qwen3-Coder-30B-A3B-Instruct-Q3_K_S.gguf"
    MODEL_TAG="qwen3-coder-30b"; MODEL_SIZE_GB="13.3"
  elif [ "${BUFFY_MODEL:-}" = "coder7b" ] || [ -z "${BUFFY_MODEL:-}" ] && [ "$VRAM_GIB" -ge 8 ]; then
    HF_REPO="bartowski/Qwen2.5-Coder-7B-Instruct-abliterated-GGUF"
    HF_FILE="Qwen2.5-Coder-7B-Instruct-abliterated-Q4_K_M.gguf"
    MODEL_TAG="qwen2.5-coder-7b-abliterated"; MODEL_SIZE_GB="4.7"
  else
    HF_REPO="bartowski/Qwen2.5-Coder-3B-Instruct-abliterated-GGUF"
    HF_FILE="Qwen2.5-Coder-3B-Instruct-abliterated-Q4_K_M.gguf"
    MODEL_TAG="qwen2.5-coder-3b-abliterated"; MODEL_SIZE_GB="1.9"
  fi
  HF_REPO="${BUFFY_HF_REPO:-$HF_REPO}"
  HF_FILE="${BUFFY_HF_FILE:-$HF_FILE}"
  MODEL_TAG="${BUFFY_MODEL_TAG:-$MODEL_TAG}"
  CTX="${BUFFY_NUM_CTX:-4096}"
}
choose_model

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

# Ollama ចេញជា .tar.zst — Colab ត្រូវការ zstd សិន (តូច ~1MB)
ensure_zstd() {
  command -v zstd >/dev/null 2>&1 && return 0
  echo "   ដំឡើង zstd (ត្រូវការសម្រាប់ Ollama) …"
  (apt-get update -qq && apt-get install -y -qq zstd) >>"$WORK/ollama-install.log" 2>&1 || true
  command -v zstd >/dev/null 2>&1
}

# ដំឡើងតាម script ផ្លូវការ; បើបរាជ័យ (ឧ. ollama.com ត្រូវបានបិទ/យឺត) → ទាញ binary ពី GitHub ផ្ទាល់
install_ollama() {
  local log="$WORK/ollama-install.log"
  local arch zst
  ensure_zstd || echo "   ⚠️  zstd មិនអាចដំឡើងបាន — សាកបន្តទៅមុខទៀត"
  echo "   កំពុងដំឡើងតាម ollama.com …"
  if curl -fsSL https://ollama.com/install.sh -o "$WORK/install.sh" 2>"$log" && sh "$WORK/install.sh" >>"$log" 2>&1; then
    return 0
  fi
  echo "   ⚠️  ollama.com មិនជោគជ័យ — សាកទាញ binary ពី GitHub release …"
  case "$(uname -m)" in
    x86_64|amd64) arch="amd64" ;;
    aarch64|arm64) arch="arm64" ;;
    *) arch="" ;;
  esac
  [ -n "$arch" ] || return 1
  zst="$WORK/ollama-linux-$arch.tar.zst"
  if curl -fL --retry 3 --progress-bar -o "$zst" \
      "https://github.com/ollama/ollama/releases/latest/download/ollama-linux-$arch.tar.zst" >>"$log" 2>&1; then
    if tar --zstd -C /usr/local -xf "$zst" >>"$log" 2>&1 \
       || tar -C /usr/local --use-compress-program=unzstd -xf "$zst" >>"$log" 2>&1; then
      [ -x /usr/local/bin/ollama ] && \
        ln -sf /usr/local/bin/ollama /usr/bin/ollama 2>/dev/null || true
      rm -f "$zst"
      return 0
    fi
  fi
  return 1
}

if ! command -v ollama >/dev/null 2>&1; then
  if ! install_ollama || ! command -v ollama >/dev/null 2>&1; then
    echo "   ── សារកំហុសចុងក្រោយ ──"
    tail -n 15 "$WORK/ollama-install.log" 2>/dev/null || true
    echo "   ─────────────────────────"
    die "ដំឡើង Ollama មិនបាន — សូមផ្ញើបន្ទាត់ខាងលើមកខ្ញុំ ឬសាករត់ cell ម្តងទៀត"
  fi
fi
# ករណី binary មានតែ /usr/local/bin ហើយ PATH មិនរួមបញ្ចូល
command -v ollama >/dev/null 2>&1 || export PATH="/usr/local/bin:$PATH"
if ! curl -sf "$OLLAMA_URL_LOCAL/api/tags" >/dev/null 2>&1; then
  echo "   កំពុងបើក ollama serve …"
  nohup ollama serve >"$WORK/ollama.log" 2>&1 </dev/null &
  for _ in $(seq 1 60); do
    curl -sf "$OLLAMA_URL_LOCAL/api/tags" >/dev/null 2>&1 && break
    sleep 1
  done
fi
if ! curl -sf "$OLLAMA_URL_LOCAL/api/tags" >/dev/null 2>&1; then
  echo "   ── សារកំហុសពី ollama.log ──"
  tail -n 10 "$WORK/ollama.log" 2>/dev/null || true
  echo "   ─────────────────────────"
  die "Ollama មិនឡើង — សូមផ្ញើបន្ទាត់ខាងលើមកខ្ញុំ"
fi
ok "Ollama ដំណើរការ"

# ─── ២/៥ ទាញយកម៉ូដែល ──────────────────────────────────────────────────────
GGUF="$WORK/$HF_FILE"
say "២/៥  ទាញយក $HF_FILE (~$MODEL_SIZE_GB GB) — GPU ${VRAM_GIB}GB, model «$MODEL_TAG»"
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
PARAMETER num_ctx $CTX
PARAMETER temperature 0.4
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
