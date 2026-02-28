# AbletonMCP/__init__.py
#
# This file handles socket communication and command routing.
# It NEVER needs to change when adding new commands.
#
# To add a new command:
#   1. Edit commands.py (add function + route in dispatch())
#   2. Copy commands.py to the installed path
#   3. Done — the next MCP call auto-reloads commands.py

from __future__ import absolute_import, print_function, unicode_literals

from _Framework.ControlSurface import ControlSurface
import socket
import json
import threading
import time
import traceback
import os
import sys

# Change queue import for Python 2
try:
    import Queue as queue  # Python 2
except ImportError:
    import queue  # Python 3

# Hot-reload support: importlib.reload() in Python 3, reload() builtin in Python 2
try:
    from importlib import reload as _reload_module
except ImportError:
    _reload_module = reload  # Python 2 builtin  # noqa: F821

# ---------------------------------------------------------------------------
# Load commands module from the same directory as this file
# ---------------------------------------------------------------------------
_SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if _SCRIPT_DIR not in sys.path:
    sys.path.insert(0, _SCRIPT_DIR)

import commands as _commands  # noqa: E402

_commands_path = os.path.join(_SCRIPT_DIR, "commands.py")
_commands_mtime = 0.0  # tracks last-seen modification time


def _hot_reload_commands(log_fn):
    """Reload commands.py if it has changed on disk since last call."""
    global _commands_mtime
    try:
        mtime = os.path.getmtime(_commands_path)
        if mtime != _commands_mtime:
            _reload_module(_commands)
            _commands_mtime = mtime
            log_fn("AbletonMCP: commands.py reloaded (mtime changed)")
    except Exception as e:
        log_fn("AbletonMCP: hot-reload failed: {0}".format(str(e)))


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
DEFAULT_PORT = 9877
HOST = "localhost"


def create_instance(c_instance):
    """Create and return the AbletonMCP script instance"""
    return AbletonMCP(c_instance)


class AbletonMCP(ControlSurface):
    """AbletonMCP Remote Script for Ableton Live"""

    def __init__(self, c_instance):
        ControlSurface.__init__(self, c_instance)
        self.log_message("AbletonMCP Remote Script initializing...")

        self.server = None
        self.client_threads = []
        self.server_thread = None
        self.running = False

        self._song = self.song()
        self.start_server()

        self.log_message("AbletonMCP initialized")
        self.show_message("AbletonMCP: Listening for commands on port " + str(DEFAULT_PORT))

    def disconnect(self):
        self.log_message("AbletonMCP disconnecting...")
        self.running = False

        if self.server:
            try:
                self.server.close()
            except Exception:
                pass

        if self.server_thread and self.server_thread.is_alive():
            self.server_thread.join(1.0)

        for client_thread in self.client_threads[:]:
            if client_thread.is_alive():
                self.log_message("Client thread still alive during disconnect")

        ControlSurface.disconnect(self)
        self.log_message("AbletonMCP disconnected")

    # -----------------------------------------------------------------------
    # Socket server
    # -----------------------------------------------------------------------

    def start_server(self):
        try:
            self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server.bind((HOST, DEFAULT_PORT))
            self.server.listen(5)

            self.running = True
            self.server_thread = threading.Thread(target=self._server_thread)
            self.server_thread.daemon = True
            self.server_thread.start()

            self.log_message("Server started on port " + str(DEFAULT_PORT))
        except Exception as e:
            self.log_message("Error starting server: " + str(e))
            self.show_message("AbletonMCP: Error starting server - " + str(e))

    def _server_thread(self):
        try:
            self.log_message("Server thread started")
            self.server.settimeout(1.0)

            while self.running:
                try:
                    client, address = self.server.accept()
                    self.log_message("Connection accepted from " + str(address))
                    self.show_message("AbletonMCP: Client connected")

                    client_thread = threading.Thread(
                        target=self._handle_client,
                        args=(client,)
                    )
                    client_thread.daemon = True
                    client_thread.start()

                    self.client_threads.append(client_thread)
                    self.client_threads = [t for t in self.client_threads if t.is_alive()]

                except socket.timeout:
                    continue
                except Exception as e:
                    if self.running:
                        self.log_message("Server accept error: " + str(e))
                    time.sleep(0.5)

            self.log_message("Server thread stopped")
        except Exception as e:
            self.log_message("Server thread error: " + str(e))

    def _handle_client(self, client):
        self.log_message("Client handler started")
        client.settimeout(None)
        buffer = ''

        try:
            while self.running:
                try:
                    data = client.recv(8192)
                    if not data:
                        self.log_message("Client disconnected")
                        break

                    try:
                        buffer += data.decode('utf-8')
                    except AttributeError:
                        buffer += data

                    try:
                        command = json.loads(buffer)
                        buffer = ''

                        self.log_message("Received command: " + str(command.get("type", "unknown")))

                        response = self._process_command(command)

                        try:
                            client.sendall(json.dumps(response).encode('utf-8'))
                        except AttributeError:
                            client.sendall(json.dumps(response))

                    except ValueError:
                        continue

                except Exception as e:
                    self.log_message("Error handling client data: " + str(e))
                    self.log_message(traceback.format_exc())

                    error_response = {"status": "error", "message": str(e)}
                    try:
                        client.sendall(json.dumps(error_response).encode('utf-8'))
                    except AttributeError:
                        client.sendall(json.dumps(error_response))
                    except Exception:
                        break

                    if not isinstance(e, ValueError):
                        break

        except Exception as e:
            self.log_message("Error in client handler: " + str(e))
        finally:
            try:
                client.close()
            except Exception:
                pass
            self.log_message("Client handler stopped")

    # -----------------------------------------------------------------------
    # Command dispatch (hot-reload aware)
    # -----------------------------------------------------------------------

    def _process_command(self, command):
        """
        Route an incoming command to commands.py.

        commands.py is reloaded automatically whenever its file changes on
        disk, so new commands take effect without restarting Ableton.
        """
        # Hot-reload commands.py if modified
        _hot_reload_commands(self.log_message)

        command_type = command.get("type", "")
        params = command.get("params", {})

        response = {"status": "success", "result": {}}

        try:
            if command_type in _commands.MAIN_THREAD_COMMANDS:
                # State-modifying commands must run on Ableton's main thread
                response_queue = queue.Queue()

                def main_thread_task():
                    try:
                        result = _commands.dispatch(
                            command_type, params,
                            self._song, self.application, self.log_message
                        )
                        response_queue.put({"status": "success", "result": result})
                    except Exception as e:
                        self.log_message("Error in main thread task: " + str(e))
                        self.log_message(traceback.format_exc())
                        response_queue.put({"status": "error", "message": str(e)})

                try:
                    self.schedule_message(0, main_thread_task)
                except AssertionError:
                    main_thread_task()

                try:
                    task_response = response_queue.get(timeout=10.0)
                    if task_response.get("status") == "error":
                        response["status"] = "error"
                        response["message"] = task_response.get("message", "Unknown error")
                    else:
                        response["result"] = task_response.get("result", {})
                except queue.Empty:
                    response["status"] = "error"
                    response["message"] = "Timeout waiting for operation to complete"

            else:
                # Read-only commands run directly in the socket thread
                response["result"] = _commands.dispatch(
                    command_type, params,
                    self._song, self.application, self.log_message
                )

        except ValueError as e:
            # Unknown command
            response["status"] = "error"
            response["message"] = str(e)
        except Exception as e:
            self.log_message("Error processing command: " + str(e))
            self.log_message(traceback.format_exc())
            response["status"] = "error"
            response["message"] = str(e)

        return response
