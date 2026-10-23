#!/usr/bin/env bash
# រុញ project នេះទៅ GitHub repository ដែលអ្នកបានបង្កើត (ទទេ)។
#
# របៀបប្រើ:
#   ./push_to_github.sh https://github.com/<username>/<repo>.git
set -euo pipefail

cd "$(dirname "$0")"

if [ $# -lt 1 ] || [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
  cat <<'USAGE'
Usage: ./push_to_github.sh <repo-url>

  1) បើក https://github.com/new  → ដាក់ឈ្មោះ (ឧ. buffy-ai)
     ⚠️ កុំធីក "Add a README file" (ត្រូវការ repo ទទេ)
  2) ចម្លង URL ឧ. https://github.com/username/buffy-ai.git
  3) រត់៖
       ./push_to_github.sh https://github.com/username/buffy-ai.git

  បើ git សួរ password សូមប្រើ Personal Access Token ថ្មី
  (GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)
   → Generate new token → ធីក scope "repo")។
USAGE
  exit 1
fi

URL="$1"
case "$URL" in
  https://github.com/*/*|git@github.com:*/*) ;;
  *)
    echo "❌ URL មិនត្រឹមត្រូវ: $URL"
    echo "   ត្រូវជាទម្រង់ https://github.com/<user>/<repo>.git"
    exit 1
    ;;
esac

git rev-parse --verify HEAD >/dev/null 2>&1 || {
  echo "❌ គ្មាន commit ក្នុង repo នេះទេ"
  exit 1
}

# ធានាថាមាន branch ឈ្មោះ main ចង្អុលទៅ commit ចុងក្រោយ
git branch -f main HEAD

if git remote get-url origin >/dev/null 2>&1; then
  git remote set-url origin "$URL"
else
  git remote add origin "$URL"
fi

echo "→ កំពុង push ទៅ $URL (branch: main) …"
git push origin main
git branch --set-upstream-to=origin/main main >/dev/null 2>&1 || true

echo
echo "✅ រួចរាល់! បើក ${URL%.git} ដើម្បីឃើញកូដ"
