# garmin-mcp

MCP server that exposes the full `python-garminconnect` API (~95 read-only
tools, or 122 with writes enabled) as tools for Claude Desktop and Claude Code.

## Why this exists

Garmin broke their auth in March 2026; `garth` is deprecated. This server uses
`python-garminconnect >= 0.3.2`, which uses `curl_cffi` TLS fingerprint
impersonation plus the Android mobile SSO flow with DI OAuth Bearer tokens
that auto-refresh indefinitely. No manual re-login needed after the first run.

## Install for Claude Desktop (macOS)

One command. It installs `uv` if missing, prompts for Garmin email/password/
MFA, and registers the server in Claude Desktop's config:

```sh
bash <(curl -fsSL https://raw.githubusercontent.com/ethulin/garmin-mcp/master/install.sh)
```

Then quit Claude Desktop (⌘Q) and reopen it. Ask *"what was my last
activity?"* in a new chat.

### Enabling writes

Writes (`upload_`, `delete_`, `create_`, `set_`, etc. — 122 tools total
instead of 95) are off by default. To enable, edit the `garmin` entry in
`~/Library/Application Support/Claude/claude_desktop_config.json` and add:

```json
"env": { "GARMIN_ALLOW_WRITES": "true" }
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
