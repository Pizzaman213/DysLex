#!/bin/bash
# Lint check on file save

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Lint TypeScript/JavaScript files
if [[ "$FILE_PATH" == *.ts* || "$FILE_PATH" == *.js ]]; then
  cd "$CLAUDE_PROJECT_DIR/frontend"
  npx eslint "$FILE_PATH" --max-warnings 0 2>&1
fi

# Lint Python files
if [[ "$FILE_PATH" == *.py ]]; then
  cd "$CLAUDE_PROJECT_DIR/backend"
  python -m ruff check "$FILE_PATH" 2>&1
fi

exit 0
