# AbletonMCP

Ableton Live integration through the Model Context Protocol (MCP).

## Architecture

Two-part system communicating over TCP socket (localhost:9877):

- **`AbletonMCP_Remote_Script/__init__.py`** — Python Remote Script running inside Ableton Live. Creates a TCP socket server, receives JSON commands, executes them via the Ableton Live API (`_Framework.ControlSurface`). Must be **Python 2 compatible** — use `.format()` for strings, `Queue` module, no f-strings.

- **`MCP_Server/server.py`** — FastMCP server (Python 3.10+) that connects to the Remote Script, wraps commands as MCP tools for Claude.

## Communication Protocol

```
Command:  {"type": "command_name", "params": {...}}
Response: {"status": "success|error", "result": {...}, "message": "..."}
```

## Key Patterns

- **Read-only commands** (get_session_info, get_track_info, etc.): Execute directly on the client handler thread in `_process_command()`
- **State-modifying commands** (create_track, set_volume, etc.): Must be scheduled on Ableton's main thread via `schedule_message(0, func)` with a `response_queue` for thread-safe responses
- Every handler validates indices and raises `IndexError` with descriptive messages
- MCP tools return formatted strings (not raw dicts)

## Development

- Run MCP server: `uvx ableton-mcp` or `python -m MCP_Server.server`
- Remote Script must be installed in Ableton's MIDI Remote Scripts directory
- Testing requires a running Ableton Live instance with the Remote Script loaded
- Use `/ableton` slash command in Claude Code for music production workflows
