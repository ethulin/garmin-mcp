# garmin-mcp

MCP server that exposes the full `python-garminconnect` API (~130 methods) as
tools for Claude Desktop on macOS. Read-only by default; writes opt in via env.

## Why this exists

Garmin broke their auth in March 2026; `garth` is deprecated. This server uses
`python-garminconnect >= 0.3.2`, which uses `curl_cffi` TLS fingerprint
impersonation plus the Android mobile SSO flow with DI OAuth Bearer tokens that
auto-refresh indefinitely. No manual re-login needed after the first run.

## Setup (macOS)

Clone or copy this directory anywhere, then:

```sh
cd /path/to/garmin-mcp
python3 -m venv venv
venv/bin/pip install -r requirements.txt
```

Python 3.11 or newer is required (`curl_cffi` needs 3.10+).

## One-time authentication

Run this once from the terminal. It will prompt for email, password, and MFA
code, then persist tokens to `~/.garminconnect/`:

```sh
venv/bin/python auth.py
```

You can pre-populate creds via `GARMIN_EMAIL` and `GARMIN_PASSWORD` env vars;
MFA is always interactive.

Tokens live at `~/.garminconnect/garmin_tokens.json` by default (override with
the `GARMINTOKENS` env var). Refresh tokens rotate automatically on each API
call, so in practice you only need to re-auth if you go ~1 year without using
the server or if Garmin invalidates the token on their side.

## Claude Desktop config

Edit `~/Library/Application Support/Claude/claude_desktop_config.json` and add
this under `mcpServers` (preserve any existing entries):

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/absolute/path/to/garmin-mcp/venv/bin/python",
      "args": ["/absolute/path/to/garmin-mcp/server.py"]
    }
  }
}
```

Restart Claude Desktop. In a new chat, try: *"what was my last activity?"* —
Claude should call `get_last_activity` and return real data.

## Enabling write operations

By default the server only registers read-prefixed methods (`get_`, `list_`,
`count_`, `search_`, `find_`, `fetch_`). To also expose writes (`upload_`,
`create_`, `delete_`, `update_`, `set_`, `schedule_`, `unschedule_`, `add_`,
`remove_`, `import_`, `track_`), add an `env` block to the server entry:

```json
{
  "mcpServers": {
    "garmin": {
      "command": "/absolute/path/to/garmin-mcp/venv/bin/python",
      "args": ["/absolute/path/to/garmin-mcp/server.py"],
      "env": { "GARMIN_ALLOW_WRITES": "true" }
    }
  }
}
```

Be deliberate about this — Claude can delete a workout just as easily as fetch
one.

## Troubleshooting

- **Server fails to start with an auth error:** re-run `venv/bin/python auth.py`.
- **"Rate limit" errors mid-session:** back off for a few minutes. The server
  does not retry automatically.
- **Custom token location:** set `GARMINTOKENS=/path/to/dir` in both the
  terminal where you run `auth.py` and in the Claude Desktop `env` block.
