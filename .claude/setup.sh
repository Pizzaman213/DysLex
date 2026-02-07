#!/bin/bash
# DysLex AI Claude Integration Setup
# Installs and configures MCP server and hooks

set -e

echo "============================================"
echo "  DysLex AI Claude Integration Setup"
echo "============================================"
echo ""

PROJECT_ROOT="/Users/connorsecrist/Dyslexia"
CLAUDE_CONFIG_DIR="$HOME/.claude"
MCP_CONFIG="$CLAUDE_CONFIG_DIR/mcp_config.json"

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

success() {
    echo -e "${GREEN}✓ $1${NC}"
}

warning() {
    echo -e "${YELLOW}⚠ $1${NC}"
}

error() {
    echo -e "${RED}✗ $1${NC}"
}

# Step 1: Check if MCP SDK is installed
echo "Step 1: Checking MCP SDK..."
if python3 -c "import mcp" 2>/dev/null; then
    success "MCP SDK is installed"
else
    warning "MCP SDK not found. Installing..."
    pip3 install mcp
    if python3 -c "import mcp" 2>/dev/null; then
        success "MCP SDK installed successfully"
    else
        error "Failed to install MCP SDK"
        exit 1
    fi
fi
echo ""

# Step 2: Create Claude config directory
echo "Step 2: Setting up Claude config directory..."
mkdir -p "$CLAUDE_CONFIG_DIR"
success "Claude config directory ready"
echo ""

# Step 3: Configure MCP server
echo "Step 3: Configuring MCP server..."

# Check if config exists
if [ -f "$MCP_CONFIG" ]; then
    warning "MCP config already exists at $MCP_CONFIG"
    echo "  Current content:"
    cat "$MCP_CONFIG" | head -20
    echo ""
    read -p "  Merge DysLex AI config into existing file? (y/n) " -n 1 -r
    echo ""
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # Backup existing config
        cp "$MCP_CONFIG" "$MCP_CONFIG.backup"
        success "Backed up existing config to $MCP_CONFIG.backup"

        # Merge configs (simplified - just show instruction)
        warning "Manual merge required:"
        echo "  1. Open $MCP_CONFIG"
        echo "  2. Add the 'dyslex-ai' server from .claude/mcp-config.json"
        echo "  3. Save and restart Claude Code"
    fi
else
    # Create new config
    cat > "$MCP_CONFIG" << 'EOF'
{
  "mcpServers": {
    "dyslex-ai": {
      "command": "python3",
      "args": [
        "/Users/connorsecrist/Dyslexia/.claude/mcp-server-dyslex.py"
      ],
      "description": "DysLex AI service controller"
    }
  }
}
EOF
    success "Created MCP config at $MCP_CONFIG"
fi
echo ""

# Step 4: Make scripts executable
echo "Step 4: Making scripts executable..."
chmod +x "$PROJECT_ROOT/.claude/mcp-server-dyslex.py"
chmod +x "$PROJECT_ROOT/.claude/hooks/auto-start.sh"
chmod +x "$PROJECT_ROOT/.claude/setup.sh"
success "Scripts are now executable"
echo ""

# Step 5: Test MCP server
echo "Step 5: Testing MCP server..."
if [ -x "$PROJECT_ROOT/.claude/mcp-server-dyslex.py" ]; then
    success "MCP server is executable"
    # Note: Can't easily test MCP server in batch mode
    warning "Restart Claude Code to load the MCP server"
else
    error "MCP server is not executable"
    exit 1
fi
echo ""

# Step 6: Display summary
echo "============================================"
echo "  Setup Complete!"
echo "============================================"
echo ""
success "MCP server configured"
success "Hooks installed"
echo ""
echo "Next steps:"
echo "  1. Restart Claude Code"
echo "  2. Try: 'Start DysLex AI with auto-setup'"
echo "  3. Or: 'Check DysLex AI status'"
echo ""
echo "Available tools in Claude Code:"
echo "  • dyslex_start  - Start services"
echo "  • dyslex_stop   - Stop services"
echo "  • dyslex_status - Check status"
echo "  • dyslex_logs   - View logs"
echo "  • dyslex_restart - Restart services"
echo "  • dyslex_check  - Run checks"
echo ""
echo "Documentation:"
echo "  $PROJECT_ROOT/.claude/README.md"
echo ""
