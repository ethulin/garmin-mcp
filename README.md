# garmin-mcp

MCP server that exposes the full `python-garminconnect` API (~95 read-only
tools, or 122 with writes enabled) as tools for Claude Code and Claude Desktop.

## Why this exists

Garmin broke their auth in March 2026; `garth` is deprecated. This server uses
`python-garminconnect >= 0.3.2`, which uses `curl_cffi` TLS fingerprint
impersonation plus the Android mobile SSO flow with DI OAuth Bearer tokens
that auto-refresh indefinitely. No manual re-login needed after the first run.

## Quick install (Claude Code, two commands)

Prerequisites: [`uv`](https://docs.astral.sh/uv/getting-started/installation/)
and the `claude` CLI. On macOS:

```sh
# 1. One-time: authenticate with Garmin (prompts for email, password, MFA)
uvx --from git+https://github.com/ethulin/garmin-mcp garmin-mcp-auth

# 2. Register the MCP server with Claude Code
claude mcp add garmin -- uvx --from git+https://github.com/ethulin/garmin-mcp garmin-mcp
```

That's it. Start a new Claude Code session and ask *"what was my last
activity?"* — Claude will call `get_last_activity` and return real data.

To enable write operations (upload/delete/create workouts, etc.), pass the
env var at register time:

```sh
claude mcp add garmin \
  --env GARMIN_ALLOW_WRITES=true \
  -- uvx --from git+https://github.com/ethulin/garmin-mcp garmin-mcp
```

## Claude Desktop (macOS) install

Edit `~/Library/Application Support/Claude/claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "uvx",
      "args": [
        "--from",
        "git+https://github.com/ethulin/garmin-mcp",
        "garmin-mcp"
      ]
    }
  }
}
```

Run `uvx --from git+https://github.com/ethulin/garmin-mcp garmin-mcp-auth`
once first to seed tokens, then restart Claude Desktop.

## Tokens

Tokens live at `~/.garminconnect/garmin_tokens.json` by default (override with
the `GARMINTOKENS` env var). Refresh tokens rotate automatically on each API
call, so in practice you only need to re-auth once a year, if that.

If the server ever starts reporting auth errors, re-run `garmin-mcp-auth`.

## Write operations

Read-only by default. Writes cover `upload_`, `create_`, `delete_`, `update_`,
`set_`, `schedule_`, `unschedule_`, `add_`, `remove_`, `import_`, `track_`
prefixes and are gated behind `GARMIN_ALLOW_WRITES=true`. Enable them only if
you want Claude to be able to modify your Garmin data — it can delete a
workout just as easily as fetch one.

## Development (local venv)

If you prefer a checkout instead of `uvx`:

```sh
git clone https://github.com/ethulin/garmin-mcp
cd garmin-mcp
python3 -m venv venv
venv/bin/pip install -r requirements.txt
venv/bin/python auth.py
venv/bin/python server.py   # blocks on stdio; Ctrl-C to quit
```

## Troubleshooting

- **"Rate limit" errors mid-session:** back off a few minutes. The server
  does not retry automatically.
- **Custom token location:** set `GARMINTOKENS=/path/to/dir` in the env of
  both the auth command and the MCP server registration.
- **`uvx` not found:** install with
  `curl -LsSf https://astral.sh/uv/install.sh | sh`.
