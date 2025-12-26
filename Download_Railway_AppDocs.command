#!/bin/bash
set -euo pipefail

TS="$(date +%Y%m%d_%H%M%S)"
OUT_TGZ="$HOME/Downloads/appdocs_${TS}.tgz"
OUT_DIR="$HOME/Downloads/appdocs_${TS}"
B64_TMP="$HOME/Downloads/appdocs_${TS}.b64"
REMOTE_TGZ="/tmp/appdocs_snapshot.tgz"

echo "Creating archive on Railway..."
railway ssh -- sh -lc "
  set -e
  cd /app/development/src/static
  rm -f '$REMOTE_TGZ'
  tar czf '$REMOTE_TGZ' appdocs
  ls -lh '$REMOTE_TGZ'
" >/dev/null

echo "Downloading (base64) to:"
echo "  $OUT_TGZ"
echo

# Download as base64 text (robust against mixed stdout noise)
railway ssh -- sh -lc "base64 '$REMOTE_TGZ'" > "$B64_TMP"

# Decode locally to a real .tgz
base64 --decode "$B64_TMP" > "$OUT_TGZ"
rm -f "$B64_TMP"

# Sanity check: must be non-trivial size
SIZE=$(wc -c < "$OUT_TGZ" | tr -d ' ')
if [ "$SIZE" -lt 4096 ]; then
  echo "ERROR: Downloaded archive is too small ($SIZE bytes). Something went wrong."
  echo "Deleting: $OUT_TGZ"
  rm -f "$OUT_TGZ"
  read -p "Press Enter to close..."
  exit 1
fi

echo "✅ Download complete ($SIZE bytes)."
echo

# Auto-extract to a timestamped folder
mkdir -p "$OUT_DIR"
tar xzf "$OUT_TGZ" -C "$OUT_DIR"

echo "✅ Extracted to:"
echo "  $OUT_DIR"
echo

# Optional: open the extracted folder in Finder
open "$OUT_DIR"

read -p "Press Enter to close..."