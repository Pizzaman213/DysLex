#!/bin/bash
# Run tests after changes

INPUT=$(cat)
FILE_PATH=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')

if [ -z "$FILE_PATH" ]; then
  exit 0
fi

# Run frontend tests for React/TS changes
if [[ "$FILE_PATH" == frontend/*.ts* ]]; then
  cd "$CLAUDE_PROJECT_DIR/frontend"
  npm test -- --testPathPattern="$(basename "${FILE_PATH%.*}")" --passWithNoTests 2>&1
fi

# Run backend tests for Python changes
if [[ "$FILE_PATH" == backend/*.py ]]; then
  cd "$CLAUDE_PROJECT_DIR/backend"
  pytest tests/ -v --tb=short 2>&1
fi

exit 0
