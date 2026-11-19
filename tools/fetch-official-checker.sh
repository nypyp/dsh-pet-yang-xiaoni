#!/usr/bin/env bash
# Fetch the official dsh-go pet pack checker (shipped with the app's `pet-theme`
# skill) into .cache/. It is not vendored in this repo: dsh-go is AGPL-3.0 and
# we only use it as a validation tool.
#
#   bash tools/fetch-official-checker.sh [ref]
#   python3 .cache/pet_pack_check.py pack --compat-reactions
set -euo pipefail

REF="${1:-c76c0db2d83573895f240307179e19802f674b1d}"
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUT="$ROOT/.cache/pet_pack_check.py"
REPO="ccch1mneyyy/dsh-go"

# The skill's files may live at the skill root or under scripts/ depending on
# the commit; try pinned commit first, then main, and verify the download.
paths=(
  "app/assets/skills/pet-theme/pet_pack_check.py"
  "app/assets/skills/pet-theme/scripts/pet_pack_check.py"
  "app/tool/pet_pack_check.py"
)
refs=("$REF" "main")

mkdir -p "$(dirname "$OUT")"
for ref in "${refs[@]}"; do
  for path in "${paths[@]}"; do
    for url in "https://raw.githubusercontent.com/$REPO/$ref/$path" \
               "https://cdn.jsdelivr.net/gh/$REPO@$ref/$path"; do
    tmp="$(mktemp)"
    if curl -fsSL --retry 2 --max-time 45 "$url" -o "$tmp" 2>/dev/null &&
       python3 - "$tmp" <<'PY' 2>/dev/null
import sys
data = open(sys.argv[1], 'rb').read()
ok = len(data) > 2000 and (b'pet_pack_check' in data or b'pet pack' in data.lower())
sys.exit(0 if ok else 1)
PY
    then
      mv "$tmp" "$OUT"
      [[ "$ref" != "$REF" ]] && echo "warning: pinned commit has no checker at these paths; used '$ref'" >&2
      echo "saved $OUT ($(wc -c < "$OUT") bytes from $ref:$path)"
      exit 0
    fi
    rm -f "$tmp"
    done
  done
done
echo "could not download the official checker (offline, or the repo layout changed)" >&2
echo "you can also import the zip in DSH Go once to confirm it locally" >&2
exit 1
