#!/usr/bin/env bash
# Download SymSpell frequency dictionary for the spell-correction service.
# Source: https://github.com/wolfgarbe/SymSpell (MIT License)
set -euo pipefail

DEST="$(dirname "$0")/../ml/models/quick_correction_base_v1/frequency_dictionary_en_82_765.txt"

if [ -f "$DEST" ]; then
  echo "Frequency dictionary already exists at $DEST"
  exit 0
fi

echo "Downloading frequency_dictionary_en_82_765.txt ..."
curl -fSL -o "$DEST" \
  "https://raw.githubusercontent.com/wolfgarbe/SymSpell/master/SymSpell/frequency_dictionary_en_82_765.txt"

echo "Downloaded to $DEST ($(wc -l < "$DEST") entries)"
