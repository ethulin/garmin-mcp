#!/usr/bin/env bash
set -euo pipefail

REPO="git+https://github.com/ethulin/garmin-mcp"
CFG="$HOME/Library/Application Support/Claude/claude_desktop_config.json"

if ! command -v uvx >/dev/null 2>&1; then
    echo ">>> Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.local/bin:$PATH"
fi

echo ">>> Authenticating with Garmin (email, password, MFA)..."
uvx --from "$REPO" garmin-mcp-auth

echo ">>> Registering garmin MCP server in Claude Desktop config..."
UVX="$(command -v uvx)" CFG="$CFG" REPO="$REPO" python3 - <<'PY'
import json, os
from pathlib import Path
cfg = Path(os.environ["CFG"])
cfg.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(cfg.read_text()) if cfg.exists() else {}
data.setdefault("mcpServers", {})["garmin"] = {
    "command": os.environ["UVX"],
    "args": ["--from", os.environ["REPO"], "garmin-mcp"],
}
cfg.write_text(json.dumps(data, indent=2))
print(f"    wrote {cfg}")
PY

echo
echo ">>> Done. Quit Claude Desktop (Cmd+Q) and reopen it."
