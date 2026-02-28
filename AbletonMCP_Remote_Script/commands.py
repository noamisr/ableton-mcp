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
    # Core
    "create_midi_track", "create_audio_track", "delete_track",
    "set_track_name",
    "create_clip", "add_notes_to_clip", "set_clip_name",
    "duplicate_clip", "delete_clip", "set_clip_loop",
    "set_tempo",
    "fire_clip", "stop_clip",
    "start_playback", "stop_playback",
    "load_browser_item",
    "set_song_time", "set_playback_position",
    # Mixing
    "set_track_volume", "set_track_panning", "set_track_mute",
    "set_track_solo", "set_track_arm", "set_track_send", "set_master_volume",
    # Scenes
    "create_scene", "fire_scene", "delete_scene",
    # Device control
    "set_device_parameter", "set_device_enabled", "delete_device",
    # Transport & Recording
    "set_record_mode", "set_overdub", "set_metronome",
    "capture_midi", "undo", "redo",
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

    # ---- playback position ------------------------------------------------
    elif command_type == "get_playback_position":
        return get_playback_position(song, log_fn)

    elif command_type == "set_playback_position":
        return set_playback_position(song, log_fn, params.get("position", 0.0))

    # ---- mixing ------------------------------------------------------------
    elif command_type == "set_track_volume":
        return set_track_volume(song, log_fn,
                                params.get("track_index", 0),
                                params.get("volume", 0.85))

    elif command_type == "set_track_panning":
        return set_track_panning(song, log_fn,
                                 params.get("track_index", 0),
                                 params.get("panning", 0.0))

    elif command_type == "set_track_mute":
        return set_track_mute(song, log_fn,
                              params.get("track_index", 0),
                              params.get("mute", False))

    elif command_type == "set_track_solo":
        return set_track_solo(song, log_fn,
                              params.get("track_index", 0),
                              params.get("solo", False))

    elif command_type == "set_track_arm":
        return set_track_arm(song, log_fn,
                             params.get("track_index", 0),
                             params.get("arm", False))

    elif command_type == "set_track_send":
        return set_track_send(song, log_fn,
                              params.get("track_index", 0),
                              params.get("send_index", 0),
                              params.get("value", 0.0))

    elif command_type == "get_return_track_info":
        return get_return_track_info(song, log_fn,
                                     params.get("track_index", 0))

    elif command_type == "set_master_volume":
        return set_master_volume(song, log_fn, params.get("volume", 0.85))

    # ---- tracks / scenes ---------------------------------------------------
    elif command_type == "create_audio_track":
        return create_audio_track(song, log_fn, params.get("index", -1))

    elif command_type == "delete_track":
        return delete_track(song, log_fn, params.get("track_index", 0))

    elif command_type == "get_scene_info":
        return get_scene_info(song, log_fn, params.get("scene_index", 0))

    elif command_type == "create_scene":
        return create_scene(song, log_fn, params.get("index", -1))

    elif command_type == "fire_scene":
        return fire_scene(song, log_fn, params.get("scene_index", 0))

    elif command_type == "delete_scene":
        return delete_scene(song, log_fn, params.get("scene_index", 0))

    elif command_type == "duplicate_clip":
        return duplicate_clip(song, log_fn,
                              params.get("track_index", 0),
                              params.get("clip_index", 0))

    elif command_type == "delete_clip":
        return delete_clip(song, log_fn,
                           params.get("track_index", 0),
                           params.get("clip_index", 0))

    elif command_type == "get_clip_notes":
        return get_clip_notes(song, log_fn,
                              params.get("track_index", 0),
                              params.get("clip_index", 0))

    elif command_type == "set_clip_loop":
        return set_clip_loop(song, log_fn,
                             params.get("track_index", 0),
                             params.get("clip_index", 0),
                             params.get("loop_start", 0.0),
                             params.get("loop_end", 4.0))

    # ---- device control ----------------------------------------------------
    elif command_type == "get_device_info":
        return get_device_info(song, log_fn,
                               params.get("track_index", 0),
                               params.get("device_index", 0))

    elif command_type == "get_device_parameters":
        return get_device_parameters(song, log_fn,
                                     params.get("track_index", 0),
                                     params.get("device_index", 0))

    elif command_type == "set_device_parameter":
        return set_device_parameter(song, log_fn,
                                    params.get("track_index", 0),
                                    params.get("device_index", 0),
                                    params.get("param_index", 0),
                                    params.get("value", 0.0))

    elif command_type == "set_device_enabled":
        return set_device_enabled(song, log_fn,
                                  params.get("track_index", 0),
                                  params.get("device_index", 0),
                                  params.get("enabled", True))

    elif command_type == "delete_device":
        return delete_device(song, log_fn,
                             params.get("track_index", 0),
                             params.get("device_index", 0))

    # ---- transport & recording ---------------------------------------------
    elif command_type == "set_record_mode":
        return set_record_mode(song, log_fn, params.get("enabled", False))

    elif command_type == "set_overdub":
        return set_overdub(song, log_fn, params.get("enabled", False))

    elif command_type == "set_metronome":
        return set_metronome(song, log_fn, params.get("enabled", False))

    elif command_type == "capture_midi":
        return capture_midi(song, log_fn)

    elif command_type == "undo":
        return undo(song, log_fn)

    elif command_type == "redo":
        return redo(song, log_fn)

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
# Playback position
# ---------------------------------------------------------------------------

def get_playback_position(song, log_fn):
    """Get the current arrangement playhead position in beats."""
    try:
        return {"position": song.current_song_time, "playing": song.is_playing}
    except Exception as e:
        log_fn("Error in get_playback_position: {0}".format(str(e)))
        raise


def set_playback_position(song, log_fn, position):
    """Set the arrangement playhead to a beat position (does not stop/resume playback)."""
    try:
        song.current_song_time = float(position)
        return {"position": song.current_song_time, "playing": song.is_playing}
    except Exception as e:
        log_fn("Error in set_playback_position: {0}".format(str(e)))
        raise


# ---------------------------------------------------------------------------
# Mixing
# ---------------------------------------------------------------------------

def set_track_volume(song, log_fn, track_index, volume):
    """Set a track's volume (0.0–1.0)."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        vol = max(0.0, min(1.0, float(volume)))
        song.tracks[track_index].mixer_device.volume.value = vol
        return {"volume": song.tracks[track_index].mixer_device.volume.value}
    except Exception as e:
        log_fn("Error in set_track_volume: {0}".format(str(e)))
        raise


def set_track_panning(song, log_fn, track_index, panning):
    """Set a track's panning (-1.0 left … 1.0 right)."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        pan = max(-1.0, min(1.0, float(panning)))
        song.tracks[track_index].mixer_device.panning.value = pan
        return {"panning": song.tracks[track_index].mixer_device.panning.value}
    except Exception as e:
        log_fn("Error in set_track_panning: {0}".format(str(e)))
        raise


def set_track_mute(song, log_fn, track_index, mute):
    """Mute or unmute a track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].mute = bool(mute)
        return {"mute": song.tracks[track_index].mute}
    except Exception as e:
        log_fn("Error in set_track_mute: {0}".format(str(e)))
        raise


def set_track_solo(song, log_fn, track_index, solo):
    """Solo or unsolo a track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].solo = bool(solo)
        return {"solo": song.tracks[track_index].solo}
    except Exception as e:
        log_fn("Error in set_track_solo: {0}".format(str(e)))
        raise


def set_track_arm(song, log_fn, track_index, arm):
    """Arm or disarm a track for recording."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.tracks[track_index].arm = bool(arm)
        return {"arm": song.tracks[track_index].arm}
    except Exception as e:
        log_fn("Error in set_track_arm: {0}".format(str(e)))
        raise


def set_track_send(song, log_fn, track_index, send_index, value):
    """Set a track's send level (0.0–1.0)."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        sends = song.tracks[track_index].mixer_device.sends
        if send_index < 0 or send_index >= len(sends):
            raise IndexError("Send index out of range")
        v = max(0.0, min(1.0, float(value)))
        sends[send_index].value = v
        return {"send_index": send_index, "value": sends[send_index].value}
    except Exception as e:
        log_fn("Error in set_track_send: {0}".format(str(e)))
        raise


def get_return_track_info(song, log_fn, track_index):
    """Get info about a return (aux) track."""
    try:
        if track_index < 0 or track_index >= len(song.return_tracks):
            raise IndexError("Return track index out of range")
        track = song.return_tracks[track_index]
        devices = [{"index": i, "name": d.name, "class_name": d.class_name,
                    "type": _get_device_type(d)}
                   for i, d in enumerate(track.devices)]
        return {
            "index": track_index,
            "name": track.name,
            "volume": track.mixer_device.volume.value,
            "panning": track.mixer_device.panning.value,
            "mute": track.mute,
            "solo": track.solo,
            "devices": devices,
        }
    except Exception as e:
        log_fn("Error in get_return_track_info: {0}".format(str(e)))
        raise


def set_master_volume(song, log_fn, volume):
    """Set the master track volume (0.0–1.0)."""
    try:
        v = max(0.0, min(1.0, float(volume)))
        song.master_track.mixer_device.volume.value = v
        return {"volume": song.master_track.mixer_device.volume.value}
    except Exception as e:
        log_fn("Error in set_master_volume: {0}".format(str(e)))
        raise


# ---------------------------------------------------------------------------
# Tracks & Scenes
# ---------------------------------------------------------------------------

def create_audio_track(song, log_fn, index):
    """Create a new audio track at the given position."""
    try:
        song.create_audio_track(index)
        new_index = len(song.tracks) - 1 if index == -1 else index
        return {"index": new_index, "name": song.tracks[new_index].name}
    except Exception as e:
        log_fn("Error in create_audio_track: {0}".format(str(e)))
        raise


def delete_track(song, log_fn, track_index):
    """Delete a track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        song.delete_track(track_index)
        return {"deleted": True, "track_count": len(song.tracks)}
    except Exception as e:
        log_fn("Error in delete_track: {0}".format(str(e)))
        raise


def get_scene_info(song, log_fn, scene_index):
    """Get info about a scene including its clips across all tracks."""
    try:
        if scene_index < 0 or scene_index >= len(song.scenes):
            raise IndexError("Scene index out of range")
        scene = song.scenes[scene_index]
        clip_slots = []
        for ti, track in enumerate(song.tracks):
            if scene_index < len(track.clip_slots):
                slot = track.clip_slots[scene_index]
                clip_info = None
                if slot.has_clip:
                    c = slot.clip
                    clip_info = {"name": c.name, "length": c.length,
                                 "is_playing": c.is_playing, "is_recording": c.is_recording}
                clip_slots.append({"track_index": ti, "track_name": track.name,
                                   "has_clip": slot.has_clip, "clip": clip_info})
        return {
            "index": scene_index,
            "name": scene.name,
            "tempo": scene.tempo if hasattr(scene, 'tempo') else None,
            "clip_slots": clip_slots,
        }
    except Exception as e:
        log_fn("Error in get_scene_info: {0}".format(str(e)))
        raise


def create_scene(song, log_fn, index):
    """Create a new scene."""
    try:
        song.create_scene(index)
        return {"index": index, "scene_count": len(song.scenes)}
    except Exception as e:
        log_fn("Error in create_scene: {0}".format(str(e)))
        raise


def fire_scene(song, log_fn, scene_index):
    """Launch all clips in a scene."""
    try:
        if scene_index < 0 or scene_index >= len(song.scenes):
            raise IndexError("Scene index out of range")
        song.scenes[scene_index].fire()
        return {"fired": True}
    except Exception as e:
        log_fn("Error in fire_scene: {0}".format(str(e)))
        raise


def delete_scene(song, log_fn, scene_index):
    """Delete a scene."""
    try:
        if scene_index < 0 or scene_index >= len(song.scenes):
            raise IndexError("Scene index out of range")
        song.delete_scene(scene_index)
        return {"deleted": True, "scene_count": len(song.scenes)}
    except Exception as e:
        log_fn("Error in delete_scene: {0}".format(str(e)))
        raise


def duplicate_clip(song, log_fn, track_index, clip_index):
    """Duplicate a clip to the next empty slot in the same track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        target_index = None
        for i in range(clip_index + 1, len(track.clip_slots)):
            if not track.clip_slots[i].has_clip:
                target_index = i
                break
        if target_index is None:
            raise Exception("No empty clip slot available after index {0}".format(clip_index))
        slot.duplicate_clip_to(track.clip_slots[target_index])
        return {"duplicated": True, "source_index": clip_index, "target_index": target_index}
    except Exception as e:
        log_fn("Error in duplicate_clip: {0}".format(str(e)))
        raise


def delete_clip(song, log_fn, track_index, clip_index):
    """Delete a clip from a slot."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        slot.delete_clip()
        return {"deleted": True}
    except Exception as e:
        log_fn("Error in delete_clip: {0}".format(str(e)))
        raise


def get_clip_notes(song, log_fn, track_index, clip_index):
    """Get MIDI notes from a session-view clip."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        clip = slot.clip
        raw = clip.get_notes(0.0, 0, clip.length, 128)
        notes = [{"pitch": n[0], "start_time": n[1], "duration": n[2],
                  "velocity": n[3], "mute": n[4]} for n in raw]
        return {"notes": notes, "count": len(notes), "clip_length": clip.length}
    except Exception as e:
        log_fn("Error in get_clip_notes: {0}".format(str(e)))
        raise


def set_clip_loop(song, log_fn, track_index, clip_index, loop_start, loop_end):
    """Set loop start/end on a session-view clip."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if clip_index < 0 or clip_index >= len(track.clip_slots):
            raise IndexError("Clip index out of range")
        slot = track.clip_slots[clip_index]
        if not slot.has_clip:
            raise Exception("No clip in slot")
        clip = slot.clip
        clip.looping = True
        clip.loop_start = float(loop_start)
        clip.loop_end = float(loop_end)
        return {"looping": clip.looping, "loop_start": clip.loop_start, "loop_end": clip.loop_end}
    except Exception as e:
        log_fn("Error in set_clip_loop: {0}".format(str(e)))
        raise


# ---------------------------------------------------------------------------
# Device control
# ---------------------------------------------------------------------------

def get_device_info(song, log_fn, track_index, device_index):
    """Get device info including all parameters."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        params = [{"index": i, "name": p.name, "value": p.value,
                   "min": p.min, "max": p.max, "is_quantized": p.is_quantized}
                  for i, p in enumerate(device.parameters)]
        return {
            "index": device_index,
            "name": device.name,
            "class_name": device.class_name,
            "type": _get_device_type(device),
            "is_active": device.is_active if hasattr(device, 'is_active') else None,
            "parameters": params,
        }
    except Exception as e:
        log_fn("Error in get_device_info: {0}".format(str(e)))
        raise


def get_device_parameters(song, log_fn, track_index, device_index):
    """Get all parameters for a device."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        params = [{"index": i, "name": p.name, "value": p.value,
                   "min": p.min, "max": p.max, "is_quantized": p.is_quantized}
                  for i, p in enumerate(device.parameters)]
        return {"device_name": device.name, "parameters": params}
    except Exception as e:
        log_fn("Error in get_device_parameters: {0}".format(str(e)))
        raise


def set_device_parameter(song, log_fn, track_index, device_index, param_index, value):
    """Set a device parameter by index."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        if param_index < 0 or param_index >= len(device.parameters):
            raise IndexError("Parameter index out of range")
        param = device.parameters[param_index]
        param.value = max(param.min, min(param.max, float(value)))
        return {"name": param.name, "value": param.value}
    except Exception as e:
        log_fn("Error in set_device_parameter: {0}".format(str(e)))
        raise


def set_device_enabled(song, log_fn, track_index, device_index, enabled):
    """Enable or disable a device (via its Device On parameter)."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        device = track.devices[device_index]
        device.parameters[0].value = 1.0 if enabled else 0.0
        return {"enabled": bool(device.parameters[0].value)}
    except Exception as e:
        log_fn("Error in set_device_enabled: {0}".format(str(e)))
        raise


def delete_device(song, log_fn, track_index, device_index):
    """Remove a device from a track."""
    try:
        if track_index < 0 or track_index >= len(song.tracks):
            raise IndexError("Track index out of range")
        track = song.tracks[track_index]
        if device_index < 0 or device_index >= len(track.devices):
            raise IndexError("Device index out of range")
        track.delete_device(device_index)
        return {"deleted": True, "device_count": len(track.devices)}
    except Exception as e:
        log_fn("Error in delete_device: {0}".format(str(e)))
        raise


# ---------------------------------------------------------------------------
# Transport & Recording
# ---------------------------------------------------------------------------

def set_record_mode(song, log_fn, enabled):
    """Enable or disable Arrangement recording mode."""
    try:
        song.record_mode = bool(enabled)
        return {"record_mode": song.record_mode}
    except Exception as e:
        log_fn("Error in set_record_mode: {0}".format(str(e)))
        raise


def set_overdub(song, log_fn, enabled):
    """Enable or disable MIDI overdub."""
    try:
        song.overdub = bool(enabled)
        return {"overdub": song.overdub}
    except Exception as e:
        log_fn("Error in set_overdub: {0}".format(str(e)))
        raise


def set_metronome(song, log_fn, enabled):
    """Enable or disable the metronome."""
    try:
        song.metronome = bool(enabled)
        return {"metronome": song.metronome}
    except Exception as e:
        log_fn("Error in set_metronome: {0}".format(str(e)))
        raise


def capture_midi(song, log_fn):
    """Capture recently played MIDI into a clip."""
    try:
        song.capture_midi()
        return {"captured": True}
    except Exception as e:
        log_fn("Error in capture_midi: {0}".format(str(e)))
        raise


def undo(song, log_fn):
    """Undo the last action."""
    try:
        song.undo()
        return {"undone": True}
    except Exception as e:
        log_fn("Error in undo: {0}".format(str(e)))
        raise


def redo(song, log_fn):
    """Redo the last undone action."""
    try:
        song.redo()
        return {"redone": True}
    except Exception as e:
        log_fn("Error in redo: {0}".format(str(e)))
        raise


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
