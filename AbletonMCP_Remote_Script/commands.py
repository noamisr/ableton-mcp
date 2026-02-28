"""
commands.py — AbletonMCP command handlers

This module is HOT-RELOADED on every incoming command, so you can add or edit
commands here and they take effect immediately without restarting Ableton or
toggling the control surface.

Workflow:
  1. Edit this file (add a new function, update an existing one)
  2. Copy it to the installed path:
       cp AbletonMCP_Remote_Script/commands.py \
          ~/Music/Ableton/User\ Library/Remote\ Scripts/AbletonMCP_Remote_Script/commands.py
  3. Send your next MCP command — the new code loads automatically.

Functions receive (song, app_fn, log_fn, params) where:
  song   — Live.Application.get_application().get_document() (the current Live set)
  app_fn — callable that returns the Live Application object (for browser access)
  log_fn — callable(str) for writing to Ableton's log
  params — dict of parameters from the MCP request
"""
from __future__ import absolute_import, print_function, unicode_literals
import traceback

# ---------------------------------------------------------------------------
# Command routing table
# ---------------------------------------------------------------------------

# Commands in this set are scheduled on Ableton's main thread.
# All commands that modify Live state (create tracks, change playback, etc.)
# must be listed here.
MAIN_THREAD_COMMANDS = {
    "create_midi_track",
    "set_track_name",
    "create_clip",
    "add_notes_to_clip",
    "set_clip_name",
    "set_tempo",
    "fire_clip",
    "stop_clip",
    "start_playback",
    "stop_playback",
    "load_browser_item",
    "set_song_time",
}


def dispatch(command_type, params, song, app_fn, log_fn):
    """
    Route a command to its handler.

    Returns a result dict on success, raises an exception on failure.
    Unknown commands raise ValueError.
    """
    # ---- read-only commands ------------------------------------------------
    if command_type == "get_session_info":
        return get_session_info(song, log_fn)

    elif command_type == "get_track_info":
        return get_track_info(song, log_fn, params.get("track_index", 0))

    elif command_type == "get_browser_item":
        return get_browser_item(song, app_fn, log_fn,
                                params.get("uri", None),
                                params.get("path", None))

    elif command_type == "get_browser_categories":
        return get_browser_categories(song, app_fn, log_fn,
                                      params.get("category_type", "all"))

    elif command_type == "get_browser_items":
        return get_browser_items(song, app_fn, log_fn,
                                 params.get("path", ""),
                                 params.get("item_type", "all"))

    elif command_type == "get_browser_tree":
        return get_browser_tree(song, app_fn, log_fn,
                                params.get("category_type", "all"))

    elif command_type == "get_browser_items_at_path":
        return get_browser_items_at_path(song, app_fn, log_fn,
                                         params.get("path", ""))

    elif command_type == "search_track_notes":
        return search_track_notes(song, log_fn,
                                  params.get("track_index", 0))

    elif command_type == "get_track_notes":
        return get_track_notes(song, log_fn,
                               params.get("track_index", 0),
                               params.get("max_notes", 50))

    # ---- main-thread commands (state-modifying) ----------------------------
    elif command_type == "create_midi_track":
        return create_midi_track(song, log_fn, params.get("index", -1))

    elif command_type == "set_track_name":
        return set_track_name(song, log_fn,
                              params.get("track_index", 0),
                              params.get("name", ""))

    elif command_type == "create_clip":
        return create_clip(song, log_fn,
                           params.get("track_index", 0),
                           params.get("clip_index", 0),
                           params.get("length", 4.0))

    elif command_type == "add_notes_to_clip":
        return add_notes_to_clip(song, log_fn,
                                  params.get("track_index", 0),
                                  params.get("clip_index", 0),
                                  params.get("notes", []))

    elif command_type == "set_clip_name":
        return set_clip_name(song, log_fn,
                             params.get("track_index", 0),
                             params.get("clip_index", 0),
                             params.get("name", ""))

    elif command_type == "set_tempo":
        return set_tempo(song, log_fn, params.get("tempo", 120.0))

    elif command_type == "fire_clip":
        return fire_clip(song, log_fn,
                         params.get("track_index", 0),
                         params.get("clip_index", 0))

    elif command_type == "stop_clip":
        return stop_clip(song, log_fn,
                         params.get("track_index", 0),
                         params.get("clip_index", 0))

    elif command_type == "start_playback":
        return start_playback(song, log_fn)

    elif command_type == "stop_playback":
        return stop_playback(song, log_fn)

    elif command_type == "load_browser_item":
        return load_browser_item(song, app_fn, log_fn,
                                  params.get("track_index", 0),
                                  params.get("item_uri", ""))

    elif command_type == "set_song_time":
        return set_song_time(song, log_fn, params.get("time", 0.0))

    elif command_type == "hot_reload_test":
        return hot_reload_test(song, log_fn)

    else:
        raise ValueError("Unknown command: " + command_type)


# ---------------------------------------------------------------------------
# Command implementations
# ---------------------------------------------------------------------------

def get_session_info(song, log_fn):
    """Get top-level information about the current Live set."""
    try:
        return {
            "tempo": song.tempo,
            "signature_numerator": song.signature_numerator,
            "signature_denominator": song.signature_denominator,
            "track_count": len(song.tracks),
            "return_track_count": len(song.return_tracks),
            "master_track": {
                "name": "Master",
                "volume": song.master_track.mixer_device.volume.value,
                "panning": song.master_track.mixer_device.panning.value,
            },
        }
    except Exception as e:
        log_fn("Error in get_session_info: {0}".format(str(e)))
        raise


def get_track_info(song, log_fn, track_index):
    """Get detailed information about a single track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")

        track = song.tracks[track_index]

        clip_slots = []
        for slot_index, slot in enumerate(track.clip_slots):
            clip_info = None
            if slot.has_clip:
                clip = slot.clip
                clip_info = {
                    "name": clip.name,
                    "length": clip.length,
                    "is_playing": clip.is_playing,
                    "is_recording": clip.is_recording,
                }
            clip_slots.append({
                "index": slot_index,
                "has_clip": slot.has_clip,
                "clip": clip_info,
            })

        devices = []
        for device_index, device in enumerate(track.devices):
            devices.append({
                "index": device_index,
                "name": device.name,
                "class_name": device.class_name,
                "type": _get_device_type(device),
            })

        return {
            "index": track_index,
            "name": track.name,
            "is_audio_track": track.has_audio_input,
            "is_midi_track": track.has_midi_input,
            "mute": track.mute,
            "solo": track.solo,
            "arm": track.arm,
            "volume": track.mixer_device.volume.value,
            "panning": track.mixer_device.panning.value,
            "clip_slots": clip_slots,
            "devices": devices,
        }
    except Exception as e:
        log_fn("Error in get_track_info: {0}".format(str(e)))
        raise


def create_midi_track(song, log_fn, index):
    """Create a new MIDI track at the given position."""
    try:
        song.create_midi_track(index)
        new_index = len(song.tracks) - 1 if index == -1 else index
        new_track = song.tracks[new_index]
        return {"index": new_index, "name": new_track.name}
    except Exception as e:
        log_fn("Error in create_midi_track: {0}".format(str(e)))
        raise


def set_track_name(song, log_fn, track_index, name):
    """Rename a track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].name = name
        return {"name": song.tracks[track_index].name}
    except Exception as e:
        log_fn("Error in set_track_name: {0}".format(str(e)))
        raise


def create_clip(song, log_fn, track_index, clip_index, length):
    """Create a new empty MIDI clip in a session-view slot."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if slot.has_clip:
            raise Exception("Clip slot already has a clip")
        slot.create_clip(length)
        return {"name": slot.clip.name, "length": slot.clip.length}
    except Exception as e:
        log_fn("Error in create_clip: {0}".format(str(e)))
        raise


def add_notes_to_clip(song, log_fn, track_index, clip_index, notes):
    """Add MIDI notes to a session-view clip."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        live_notes = tuple(
            (n.get("pitch", 60),
             n.get("start_time", 0.0),
             n.get("duration", 0.25),
             n.get("velocity", 100),
             n.get("mute", False))
            for n in notes
        )
        slot.clip.set_notes(live_notes)
        return {"note_count": len(notes)}
    except Exception as e:
        log_fn("Error in add_notes_to_clip: {0}".format(str(e)))
        raise


def set_clip_name(song, log_fn, track_index, clip_index, name):
    """Rename a session-view clip."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        slot.clip.name = name
        return {"name": slot.clip.name}
    except Exception as e:
        log_fn("Error in set_clip_name: {0}".format(str(e)))
        raise


def set_tempo(song, log_fn, tempo):
    """Set the session tempo in BPM."""
    try:
        song.tempo = tempo
        return {"tempo": song.tempo}
    except Exception as e:
        log_fn("Error in set_tempo: {0}".format(str(e)))
        raise


def fire_clip(song, log_fn, track_index, clip_index):
    """Fire a session-view clip."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        slot.fire()
        return {"fired": True}
    except Exception as e:
        log_fn("Error in fire_clip: {0}".format(str(e)))
        raise


def stop_clip(song, log_fn, track_index, clip_index):
    """Stop a session-view clip."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        track.clip_slots[clip_index].stop()
        return {"stopped": True}
    except Exception as e:
        log_fn("Error in stop_clip: {0}".format(str(e)))
        raise


def start_playback(song, log_fn):
    """Start Arrangement playback."""
    try:
        song.start_playing()
        return {"playing": song.is_playing}
    except Exception as e:
        log_fn("Error in start_playback: {0}".format(str(e)))
        raise


def stop_playback(song, log_fn):
    """Stop Arrangement playback."""
    try:
        song.stop_playing()
        return {"playing": song.is_playing}
    except Exception as e:
        log_fn("Error in stop_playback: {0}".format(str(e)))
        raise


def set_song_time(song, log_fn, time):
    """
    Move the arrangement playhead to a specific beat position.

    Stops playback if playing, seeks, then resumes if it was playing.
    """
    try:
        was_playing = song.is_playing
        if was_playing:
            song.stop_playing()
        song.current_song_time = float(time)
        if was_playing:
            song.start_playing()
        return {"song_time_set": float(time), "was_playing": was_playing}
    except Exception as e:
        log_fn("Error in set_song_time: {0}".format(str(e)))
        log_fn(traceback.format_exc())
        raise


def search_track_notes(song, log_fn, track_index):
    """
    Find the very first note in a track's arrangement clips.
    Returns bar number and beat position of the earliest note.
    """
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            return {"found": False,
                    "error": "Invalid track index: {0}".format(track_index),
                    "track_index": track_index}

        track = song.tracks[track_index]
        track_name = track.name if hasattr(track, 'name') else "Unknown"
        beats_per_bar = song.signature_numerator

        earliest_time = None
        earliest_details = None

        # Search arrangement clips first
        if hasattr(track, 'arrangement_clips'):
            for clip in track.arrangement_clips:
                if not clip.is_midi_clip:
                    continue
                clip_start = clip.start_time
                try:
                    notes = clip.get_notes(0, 0, clip.length, 128)
                except Exception:
                    continue
                for note in notes:
                    t = clip_start + note[1]
                    if earliest_time is None or t < earliest_time:
                        earliest_time = t
                        earliest_details = {
                            "clip_name": clip.name if hasattr(clip, 'name') else "Unnamed",
                            "note_pitch": note[0],
                            "note_velocity": note[3],
                            "start_time": t,
                        }

        # Fall back to session-view clips
        if earliest_time is None:
            for slot in track.clip_slots:
                if not slot.has_clip:
                    continue
                clip = slot.clip
                if not clip.is_midi_clip:
                    continue
                try:
                    notes = clip.get_notes(0, 0, clip.length, 128)
                except Exception:
                    continue
                for note in notes:
                    t = note[1]
                    if earliest_time is None or t < earliest_time:
                        earliest_time = t
                        earliest_details = {
                            "clip_name": clip.name if hasattr(clip, 'name') else "Unnamed",
                            "note_pitch": note[0],
                            "note_velocity": note[3],
                            "start_time": t,
                        }

        if earliest_time is None:
            return {"found": False, "track_index": track_index,
                    "track_name": track_name, "message": "No notes found in track"}

        bar = int(earliest_time / beats_per_bar) + 1
        beat = (earliest_time % beats_per_bar) + 1

        log_fn("Found first note in track {0} at bar {1}".format(track_index, bar))
        return {
            "found": True,
            "track_index": track_index,
            "track_name": track_name,
            "bar_number": bar,
            "beat_in_bar": beat,
            "note_time": earliest_time,
            "note_details": earliest_details,
        }
    except Exception as e:
        log_fn("Error in search_track_notes: {0}".format(str(e)))
        log_fn(traceback.format_exc())
        return {"found": False, "error": str(e), "track_index": track_index}


def get_track_notes(song, log_fn, track_index, max_notes=50):
    """
    Return up to max_notes notes from a track's arrangement clips,
    sorted by time with bar/beat annotations.
    """
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            return {"error": "Invalid track index: {0}".format(track_index)}

        track = song.tracks[track_index]
        track_name = track.name if hasattr(track, 'name') else "Unknown"
        beats_per_bar = song.signature_numerator
        notes = []

        if hasattr(track, 'arrangement_clips'):
            for clip in track.arrangement_clips:
                if not clip.is_midi_clip:
                    continue
                clip_start = clip.start_time
                try:
                    clip_notes = clip.get_notes(0, 0, clip.length, 128)
                except Exception:
                    continue
                clip_name = clip.name if hasattr(clip, 'name') else "?"
                for note in clip_notes:
                    abs_time = clip_start + note[1]
                    bar = int(abs_time / beats_per_bar) + 1
                    beat = (abs_time % beats_per_bar) + 1
                    notes.append({
                        "bar": bar,
                        "beat": round(beat, 3),
                        "time": abs_time,
                        "pitch": note[0],
                        "duration": note[2],
                        "velocity": note[3],
                        "clip": clip_name,
                    })

        notes.sort(key=lambda n: n["time"])
        return {
            "track_index": track_index,
            "track_name": track_name,
            "beats_per_bar": beats_per_bar,
            "notes": notes[:max_notes],
        }
    except Exception as e:
        log_fn("Error in get_track_notes: {0}".format(str(e)))
        log_fn(traceback.format_exc())
        return {"error": str(e), "track_index": track_index}


# ---------------------------------------------------------------------------
# Browser commands
# ---------------------------------------------------------------------------

def get_browser_item(song, app_fn, log_fn, uri, path):
    """Get a browser item by URI or path."""
    try:
        app = app_fn()
        if not app:
            raise RuntimeError("Could not access Live application")
        result = {"uri": uri, "path": path, "found": False}

        if uri:
            item = _find_browser_item_by_uri(app.browser, uri, log_fn)
            if item:
                result["found"] = True
                result["item"] = _browser_item_dict(item)
                return result

        if path:
            path_parts = path.split("/")
            current_item = _browser_root(app.browser, path_parts[0])
            if current_item is None:
                result["error"] = "Unknown browser category: {0}".format(path_parts[0])
                return result
            for part in path_parts[1:]:
                if not part:
                    continue
                found = False
                for child in current_item.children:
                    if child.name.lower() == part.lower():
                        current_item = child
                        found = True
                        break
                if not found:
                    result["error"] = "Path part not found: {0}".format(part)
                    return result
            result["found"] = True
            result["item"] = _browser_item_dict(current_item)

        return result
    except Exception as e:
        log_fn("Error in get_browser_item: {0}".format(str(e)))
        log_fn(traceback.format_exc())
        raise


def get_browser_categories(song, app_fn, log_fn, category_type="all"):
    """List top-level browser categories."""
    try:
        app = app_fn()
        if not app:
            raise RuntimeError("Could not access Live application")
        browser = app.browser
        categories = []
        for name in ["instruments", "sounds", "drums", "audio_effects", "midi_effects"]:
            if (category_type == "all" or category_type == name) and hasattr(browser, name):
                item = getattr(browser, name)
                categories.append({"name": name, "uri": item.uri if hasattr(item, 'uri') else None})
        return {"categories": categories}
    except Exception as e:
        log_fn("Error in get_browser_categories: {0}".format(str(e)))
        raise


def get_browser_items(song, app_fn, log_fn, path="", item_type="all"):
    """Get items inside a browser path."""
    return get_browser_items_at_path(song, app_fn, log_fn, path)


def get_browser_tree(song, app_fn, log_fn, category_type="all"):
    """Get a simplified browser category tree (top-level only)."""
    try:
        app = app_fn()
        if not app:
            raise RuntimeError("Could not access Live application")
        browser = app.browser
        browser_attrs = [a for a in dir(browser) if not a.startswith('_')]
        log_fn("Browser attrs: {0}".format(browser_attrs))

        categories = []

        def process_item(item):
            if not item:
                return None
            return {
                "name": item.name if hasattr(item, 'name') else "Unknown",
                "is_folder": hasattr(item, 'children') and bool(item.children),
                "is_device": hasattr(item, 'is_device') and item.is_device,
                "is_loadable": hasattr(item, 'is_loadable') and item.is_loadable,
                "uri": item.uri if hasattr(item, 'uri') else None,
                "children": [],
            }

        for name, display in [("instruments", "Instruments"), ("sounds", "Sounds"),
                               ("drums", "Drums"), ("audio_effects", "Audio Effects"),
                               ("midi_effects", "MIDI Effects")]:
            if (category_type == "all" or category_type == name) and hasattr(browser, name):
                try:
                    entry = process_item(getattr(browser, name))
                    if entry:
                        entry["name"] = display
                        categories.append(entry)
                except Exception as e:
                    log_fn("Error processing {0}: {1}".format(name, str(e)))

        return {"type": category_type, "categories": categories,
                "available_categories": browser_attrs}
    except Exception as e:
        log_fn("Error in get_browser_tree: {0}".format(str(e)))
        log_fn(traceback.format_exc())
        raise


def get_browser_items_at_path(song, app_fn, log_fn, path):
    """Get browser items at a slash-separated path."""
    try:
        app = app_fn()
        if not app:
            raise RuntimeError("Could not access Live application")
        browser = app.browser

        path_parts = path.split("/")
        current_item = _browser_root(browser, path_parts[0])
        if current_item is None:
            available = [a for a in dir(browser) if not a.startswith('_')]
            return {"path": path, "error": "Unknown category: {0}".format(path_parts[0]),
                    "available_categories": available, "items": []}

        for i, part in enumerate(path_parts[1:], 1):
            if not part:
                continue
            if not hasattr(current_item, 'children'):
                return {"path": path,
                        "error": "Item has no children at depth {0}".format(i),
                        "items": []}
            found = False
            for child in current_item.children:
                if hasattr(child, 'name') and child.name.lower() == part.lower():
                    current_item = child
                    found = True
                    break
            if not found:
                return {"path": path, "error": "Path part not found: {0}".format(part),
                        "items": []}

        items = []
        if hasattr(current_item, 'children'):
            for child in current_item.children:
                items.append(_browser_item_dict(child))

        log_fn("Retrieved {0} items at path: {1}".format(len(items), path))
        return {
            "path": path,
            "name": current_item.name if hasattr(current_item, 'name') else "Unknown",
            "uri": current_item.uri if hasattr(current_item, 'uri') else None,
            "items": items,
        }
    except Exception as e:
        log_fn("Error in get_browser_items_at_path: {0}".format(str(e)))
        log_fn(traceback.format_exc())
        raise


def load_browser_item(song, app_fn, log_fn, track_index, item_uri):
    """Load a browser item (by URI) onto a track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        app = app_fn()
        item = _find_browser_item_by_uri(app.browser, item_uri, log_fn)
        if not item:
            raise ValueError("Browser item with URI '{0}' not found".format(item_uri))
        song.view.selected_track = track
        app.browser.load_item(item)
        return {"loaded": True, "item_name": item.name,
                "track_name": track.name, "uri": item_uri}
    except Exception as e:
        log_fn("Error in load_browser_item: {0}".format(str(e)))
        log_fn(traceback.format_exc())
        raise


def hot_reload_test(song, log_fn):
    """Confirms hot-reload is working — returns session info without a restart."""
    return {
        "hot_reload": "working",
        "tempo": song.tempo,
        "track_count": len(song.tracks),
        "message": "commands.py was reloaded automatically — no Ableton restart needed!",
    }


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _get_device_type(device):
    """Classify a device as instrument, rack, drum machine, or effect."""
    try:
        if device.can_have_drum_pads:
            return "drum_machine"
        elif device.can_have_chains:
            return "rack"
        elif "instrument" in device.class_display_name.lower():
            return "instrument"
        elif "audio_effect" in device.class_name.lower():
            return "audio_effect"
        elif "midi_effect" in device.class_name.lower():
            return "midi_effect"
        else:
            return "unknown"
    except Exception:
        return "unknown"


def _browser_item_dict(item):
    """Convert a browser item to a plain dict."""
    return {
        "name": item.name if hasattr(item, 'name') else "Unknown",
        "is_folder": hasattr(item, 'children') and bool(item.children),
        "is_device": hasattr(item, 'is_device') and item.is_device,
        "is_loadable": hasattr(item, 'is_loadable') and item.is_loadable,
        "uri": item.uri if hasattr(item, 'uri') else None,
    }


def _browser_root(browser, category_name):
    """Return the root BrowserItem for a category name, or None."""
    name = category_name.lower()
    for attr in ["instruments", "sounds", "drums", "audio_effects", "midi_effects"]:
        if name == attr and hasattr(browser, attr):
            return getattr(browser, attr)
    # Try any other attribute
    for attr in dir(browser):
        if not attr.startswith('_') and attr.lower() == name:
            try:
                return getattr(browser, attr)
            except Exception:
                pass
    return None


def _find_browser_item_by_uri(browser_or_item, uri, log_fn, max_depth=10, depth=0):
    """Recursively search for a browser item by URI."""
    try:
        if hasattr(browser_or_item, 'uri') and browser_or_item.uri == uri:
            return browser_or_item
        if depth >= max_depth:
            return None
        if hasattr(browser_or_item, 'instruments'):
            for cat in [browser_or_item.instruments, browser_or_item.sounds,
                        browser_or_item.drums, browser_or_item.audio_effects,
                        browser_or_item.midi_effects]:
                result = _find_browser_item_by_uri(cat, uri, log_fn, max_depth, depth + 1)
                if result:
                    return result
            return None
        if hasattr(browser_or_item, 'children') and browser_or_item.children:
            for child in browser_or_item.children:
                result = _find_browser_item_by_uri(child, uri, log_fn, max_depth, depth + 1)
                if result:
                    return result
        return None
    except Exception as e:
        log_fn("Error in _find_browser_item_by_uri: {0}".format(str(e)))
        return None
