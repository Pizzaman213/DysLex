#!/bin/bash
# Type checking

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

if [[ "$FILE_PATH" == *.ts* ]]; then
  cd "$CLAUDE_PROJECT_DIR/frontend"
  npx tsc --noEmit 2>&1
elif [[ "$FILE_PATH" == *.py ]]; then
  cd "$CLAUDE_PROJECT_DIR/backend"
  python -m mypy app/ --ignore-missing-imports 2>&1
fi

exit 0
