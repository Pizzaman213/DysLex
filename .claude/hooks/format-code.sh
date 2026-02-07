#!/bin/bash
# Format code after edits

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Format TypeScript/JavaScript/React files
if [[ "$FILE_PATH" == *.ts || "$FILE_PATH" == *.tsx || "$FILE_PATH" == *.js ]]; then
  cd "$(dirname "$FILE_PATH")"
  npx prettier --write "$(basename "$FILE_PATH")" 2>/dev/null
fi

# Format Python files
if [[ "$FILE_PATH" == *.py ]]; then
  python -m ruff format "$FILE_PATH" 2>/dev/null
fi

exit 0
