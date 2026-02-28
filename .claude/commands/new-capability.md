# Add New Ableton MCP Capability

Use this skill to add a new command/tool to the Ableton MCP system.

You will be asked to describe the new capability. Then follow these steps:

---

## How hot-reload works

`__init__.py` handles the socket server and routes commands. It **never needs to change**.

`commands.py` contains all command handler logic. It is **automatically reloaded** whenever its
file modification time changes on disk — meaning the next MCP command picks up your edits without
any Ableton restart or control-surface toggle.

---

## Step 1 — Add the handler function to `commands.py`

At the bottom of `AbletonMCP_Remote_Script/commands.py`, add your implementation:

```python
def your_new_command(song, log_fn, track_index):
    """
    Description of what this does.
    """
    try:
        track = song.tracks[track_index]
        # ... your logic using the Live Object Model ...
        return {"key": "value"}
    except Exception as e:
        log_fn("Error in your_new_command: {0}".format(str(e)))
        raise
```

Useful Live Object Model references:
- `song` — the current Live set (`self._song` in the old style)
- `song.tracks[i]` — a track
- `song.tracks[i].clip_slots[j].clip` — a clip in Session view
- `song.tracks[i].arrangement_clips` — clips in Arrangement view
- `song.tempo`, `song.signature_numerator` — session properties
- `app_fn()` — call this to get the Live Application object (needed for browser access)

## Step 2 — Add a route in `dispatch()` in `commands.py`

Inside the `dispatch()` function, add a new `elif` before the final `else`:

```python
elif command_type == "your_new_command":
    return your_new_command(song, log_fn, params.get("track_index", 0))
```

If the command **modifies Live state** (creates/changes tracks, clips, playback, etc.),
also add it to `MAIN_THREAD_COMMANDS` at the top of `commands.py`:

```python
MAIN_THREAD_COMMANDS = {
    ...,
    "your_new_command",   # ← add here
}
```

## Step 3 — Add the MCP tool to `MCP_Server/server.py`

In `MCP_Server/server.py`, add a new `@mcp.tool()` function:

```python
@mcp.tool()
def your_new_command(ctx: Context, track_index: int) -> str:
    """
    One-line description shown to Claude.

    Parameters:
    - track_index: The index of the track to operate on
    """
    try:
        ableton = get_ableton_connection()
        result = ableton.send_command("your_new_command", {"track_index": track_index})
        return f"Result: {result}"
    except Exception as e:
        logger.error(f"Error in your_new_command: {str(e)}")
        return f"Error: {str(e)}"
```

Also add `"your_new_command"` to the `is_modifying_command` list in `send_command()` if it
modifies state.

## Step 4 — Copy `commands.py` to Ableton (no restart needed!)

```bash
cp AbletonMCP_Remote_Script/commands.py \
   "/Users/noamisraeli/Music/Ableton/User Library/Remote Scripts/AbletonMCP_Remote_Script/commands.py"
```

That's it. The **next command you send will auto-reload** `commands.py` from disk.
No Ableton restart, no control-surface toggle required.

> **Note:** `__init__.py` only needs to be redeployed if you change the socket server itself
> (extremely rare). When you do, you still need a full Ableton restart.

## Step 5 — Test the new command

```python
import socket, json
sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
sock.connect(("localhost", 9877))
sock.sendall(json.dumps({"type": "your_new_command", "params": {"track_index": 0}}).encode())
print(json.loads(sock.recv(8192)))
sock.close()
```

## Notes

- The Remote Script runs inside Ableton's Python environment — use `.format()` for string
  formatting, not f-strings
- Read-only commands run directly in the socket thread; state-modifying commands are scheduled
  on Ableton's main thread via `self.schedule_message(0, fn)` — this is handled automatically
  by `__init__.py` based on `MAIN_THREAD_COMMANDS`
- Remote Script install path on this machine:
  `~/Music/Ableton/User Library/Remote Scripts/AbletonMCP_Remote_Script/`
