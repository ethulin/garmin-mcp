# garmin-mcp

MCP server that exposes the full `python-garminconnect` API (~95 read-only
tools, or 122 with writes enabled) as tools for Claude Desktop and Claude Code.

## Why this exists

Garmin broke their auth in March 2026; `garth` is deprecated. This server uses
`python-garminconnect >= 0.3.2`, which uses `curl_cffi` TLS fingerprint
impersonation plus the Android mobile SSO flow with DI OAuth Bearer tokens
that auto-refresh indefinitely. No manual re-login needed after the first run.

## Install for Claude Desktop (macOS)

Prerequisite: install [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
if you don't have it:

```sh
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Step 1 — authenticate with Garmin (one time):**

```sh
uvx --from git+https://github.com/ethulin/garmin-mcp garmin-mcp-auth
```

This prompts for your Garmin email, password, and MFA code, then writes tokens
to `~/.garminconnect/garmin_tokens.json`. The refresh token rotates on every
API call — in practice you only need to repeat this ~once a year.

**Step 2 — register the server with Claude Desktop.** Run this one-liner; it
merges the server into `~/Library/Application Support/Claude/claude_desktop_config.json`,
creating the file if needed:

```sh
UVX="$(command -v uvx)" python3 - <<'PY'
import json, os, pathlib
cfg = pathlib.Path("~/Library/Application Support/Claude/claude_desktop_config.json").expanduser()
cfg.parent.mkdir(parents=True, exist_ok=True)
data = json.loads(cfg.read_text()) if cfg.exists() else {}
data.setdefault("mcpServers", {})["garmin"] = {
    "command": os.environ["UVX"],
    "args": ["--from", "git+https://github.com/ethulin/garmin-mcp", "garmin-mcp"],
}
cfg.write_text(json.dumps(data, indent=2))
print("Updated", cfg)
PY
```

**Step 3 — quit Claude Desktop (⌘Q) and reopen it.** Claude Desktop only
reloads MCP config at launch. Then in a new chat, ask *"what was my last
activity?"* — Claude should call `get_last_activity` and return real data.

### Why the absolute `uvx` path

Claude Desktop launches MCP servers as GUI subprocesses, which don't inherit
your shell `PATH`. Embedding the absolute path (`$(command -v uvx)`) in the
config sidesteps the classic "works in Terminal, not in Claude Desktop" trap.

### Enabling writes

To expose `upload_`, `delete_`, `create_`, `set_`, etc. (122 tools total
instead of 95), re-run Step 2 with the env:

```sh
UVX="$(command -v uvx)" python3 - <<'PY'
import json, os, pathlib
cfg = pathlib.Path("~/Library/Application Support/Claude/claude_desktop_config.json").expanduser()
data = json.loads(cfg.read_text())
data["mcpServers"]["garmin"] = {
    "command": os.environ["UVX"],
    "args": ["--from", "git+https://github.com/ethulin/garmin-mcp", "garmin-mcp"],
    "env": {"GARMIN_ALLOW_WRITES": "true"},
}
cfg.write_text(json.dumps(data, indent=2))
PY
```

Be deliberate — Claude can delete a workout just as easily as fetch one.

## Install for Claude Code

If you also want this inside the Claude Code CLI (in addition to or instead of
Claude Desktop), after running Step 1 above:

```sh
claude mcp add garmin -- uvx --from git+https://github.com/ethulin/garmin-mcp garmin-mcp
```

With writes enabled:

```sh
claude mcp add garmin \
  --env GARMIN_ALLOW_WRITES=true \
  -- uvx --from git+https://github.com/ethulin/garmin-mcp garmin-mcp
```

## Tokens

- Path: `~/.garminconnect/garmin_tokens.json` (override with `GARMINTOKENS`).
- Refresh tokens rotate automatically; re-run `garmin-mcp-auth` only if you
  see auth errors or you've gone ~a year without using the server.

## Development (local checkout)

```sh
git clone https://github.com/ethulin/garmin-mcp
cd garmin-mcp
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python auth.py
venv/bin/python server.py   # blocks on stdio; Ctrl-C to quit
```

## Troubleshooting

- **"Rate limit" errors:** back off a few minutes; no automatic retry.
- **Custom token location:** set `GARMINTOKENS=/path/to/dir` in both the
  `garmin-mcp-auth` environment and the MCP server config `env` block.
- **Claude Desktop doesn't see the server:** fully quit with ⌘Q (not just
  close the window) and reopen. MCP config only reloads at launch.
