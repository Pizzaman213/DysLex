#!/bin/bash
# DysLex AI Auto-Start Hook
#
# This hook can automatically start DysLex AI services.
# Enable by uncommenting the trigger below.
#
# Trigger options:
# - on-enter: Start services when entering the project directory
# - on-command: Start services when a specific command is run
# - manual: Never auto-start (default)

TRIGGER="manual"  # Change to "on-enter" to enable auto-start

PROJECT_ROOT="/Users/connorsecrist/Dyslexia"
RUN_SCRIPT="$PROJECT_ROOT/run.py"

# Function to check if services are running
is_running() {
    # Check if backend is responding
    curl -s http://localhost:8000/health > /dev/null 2>&1
    return $?
}

# Function to start services
start_services() {
    echo "🚀 Starting DysLex AI services..."

    # Start in background
    cd "$PROJECT_ROOT"
    python3 "$RUN_SCRIPT" > /tmp/dyslex-ai.log 2>&1 &

    echo "✅ Services starting... Check status with: dyslex_status"
    echo "📝 Logs: tail -f /tmp/dyslex-ai.log"
}

# Main logic
case "$TRIGGER" in
    on-enter)
        if ! is_running; then
            start_services
        else
            echo "ℹ️  DysLex AI is already running"
        fi
        ;;
    manual)
        # Do nothing - manual start only
        ;;
    *)
        echo "⚠️  Unknown trigger: $TRIGGER"
        ;;
esac
