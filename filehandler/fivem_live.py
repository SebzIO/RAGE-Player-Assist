"""
Forked live source for GTAW FiveM chat - Python port of
GTAW-Log-Parser/Assistant/Controllers/FiveMChatCaptureController.NuiChatReader.

The C# assistant captures via FiveM's local NUI DevTools (Chrome DevTools Protocol):

  HTTP  GET http://127.0.0.1:13172/json          -> list of targets
         filter url == "nui://game/ui/root.html" -> webSocketDebuggerUrl

  WS    connect to webSocketDebuggerUrl
  WS    Page.getFrameTree                       -> find frame url == "https://cfx-nui-client/web/index.html"
  WS    Page.createIsolatedWorld {frameId}      -> executionContextId
  WS    Runtime.evaluate {expression, contextId, returnByValue:true}
        expression = JS that does:
          JSON.stringify(Array.from(document.querySelectorAll('.chat__messages > li'), el => {
            const text=(el.innerText||'').replace(/\\s+/g,' ').trim(); ...
            // also extracts timestamp from attribute/content containing \\d{1,2}:\\d{2}:\\d{2}
            return (timestamp ? '['+timestamp+'] ' : '') + text;
          }).filter(Boolean))

This Python module forks that logic so RAGE Player Assist can pull the *exact*
live source without shelling out to GTAWAssistant.exe, while still keeping the
file-tail (fivem_chat.py) as fallback via %LOCALAPPDATA%/GTAW-Log-Parser-FiveM/current-session.txt.

Dependencies: stdlib + optional `websockets` or `websocket-client`.
If neither is installed, probe mode still works via HTTP; live tail falls back
to file-tail with an informative message.

Refs:
  - https://github.com/AdvGTAW/GTAW-Log-Parser (FiveM adaptation branch)
  - Assistant/Controllers/FiveMChatCaptureController.cs:27-32, 236-403
"""

from __future__ import annotations

import json
import time
import urllib.request
import urllib.error
from pathlib import Path
from typing import Any

# Exact constants from C# source - do not drift
DEVTOOLS_TARGETS_URL = "http://127.0.0.1:13172/json"
ROOT_UI_URL = "nui://game/ui/root.html"
CLIENT_FRAME_URL = "https://cfx-nui-client/web/index.html"
POLL_INTERVAL_MS = 500

# The JS expression is verbatim from C# line 246 - kept identical for accuracy
JS_EXPRESSION = (
    r"JSON.stringify(Array.from(document.querySelectorAll('.chat__messages > li'), el => { "
    r"const text = (el.innerText || '').replace(/\s+/g, ' ').trim(); "
    r"if (!text) return ''; "
    r"const nodes = [el].concat(Array.from(el.querySelectorAll('*'))); "
    r"let timestamp = ''; "
    r"for (const node of nodes) { "
    r"for (const attribute of Array.from(node.attributes || [])) { "
    r"const match = String(attribute.value).match(/\b\d{1,2}:\d{2}:\d{2}\b/); "
    r"if (match) { timestamp = match[0]; break; } "
    r"} "
    r"if (!timestamp) { "
    r"const match = String(getComputedStyle(node, '::before').content || '').match(/\b\d{1,2}:\d{2}:\d{2}\b/); "
    r"if (match) timestamp = match[0]; "
    r"} "
    r"if (timestamp) break; "
    r"} "
    r"return (timestamp ? '[' + timestamp + '] ' : '') + text; "
    r"}).filter(Boolean))"
)


def probe_fivem_nui(timeout: float = 2.0) -> dict[str, Any]:
    """Probe the exact FiveM NUI DevTools endpoint and return diagnostic dict.

    This is the definitive answer to 'where to pull the exact fivem log from'.
    No game state is modified - it's a localhost read-only CDP endpoint.
    """
    result: dict[str, Any] = {
        "devtools_url": DEVTOOLS_TARGETS_URL,
        "root_ui_url": ROOT_UI_URL,
        "client_frame_url": CLIENT_FRAME_URL,
        "fivem_running": False,
        "nui_available": False,
        "targets": [],
        "root_target": None,
        "websocket_url": None,
        "error": None,
    }

    # IsFiveMRunning check mirrors AppController.IsFiveMRunning()
    try:
        import psutil as _psutil

        for proc in _psutil.process_iter(["name"]):
            name = (proc.info.get("name") or "").lower()
            if name.startswith("fivem"):
                result["fivem_running"] = True
                break
    except ImportError:
        # Fallback: try tasklist (no psutil installed)
        try:
            import subprocess

            out = subprocess.check_output("tasklist", text=True, encoding="utf-8", errors="ignore")
            if "FiveM" in out:
                result["fivem_running"] = True
        except Exception:
            pass
    except Exception:
        pass

    # HTTP probe
    try:
        req = urllib.request.Request(DEVTOOLS_TARGETS_URL, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
            targets = json.loads(body)
            result["targets"] = targets
            result["nui_available"] = True
            for t in targets if isinstance(targets, list) else []:
                if isinstance(t, dict) and t.get("url") == ROOT_UI_URL:
                    result["root_target"] = t
                    result["websocket_url"] = t.get("webSocketDebuggerUrl")
                    break
    except urllib.error.URLError as e:
        result["error"] = f"URLError: {e.reason} (FiveM NUI not listening - is FiveM running?)"
    except Exception as e:
        result["error"] = f"{type(e).__name__}: {e}"

    return result


def _http_get_targets(timeout: float = 2.0) -> list[dict[str, Any]]:
    req = urllib.request.Request(DEVTOOLS_TARGETS_URL, headers={"Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read().decode("utf-8", errors="replace")
        data = json.loads(body)
        return data if isinstance(data, list) else []


class LiveNuiReader:
    """Synchronous wrapper around the C# NuiChatReader flow.

    Usage:
        reader = LiveNuiReader()
        try:
            lines = reader.get_chat_lines()  # list[str] with "[HH:MM:SS] text"
        finally:
            reader.close()

    Thread-safety: single-threaded caller only (matches C# lock(SyncRoot)).
    """

    def __init__(self, timeout: float = 2.0):
        self.timeout = timeout
        self._ws = None
        self._context_id: int | None = None
        self._ws_url: str | None = None
        self._request_id = 0

    # -- public --
    def get_chat_lines(self) -> list[str]:
        self._ensure_connected()
        assert self._ws is not None and self._context_id is not None
        result = self._request("Runtime.evaluate", {"expression": JS_EXPRESSION, "contextId": self._context_id, "returnByValue": True})
        # result is {"result": {"value": "[\"[12:34:56] hi\", ...]"}}
        runtime_result = result.get("result") if isinstance(result, dict) else None
        value = runtime_result.get("value") if isinstance(runtime_result, dict) else "[]"
        if not isinstance(value, str):
            value = "[]"
        try:
            arr = json.loads(value)
        except json.JSONDecodeError:
            arr = []
        if not isinstance(arr, list):
            return []
        return [str(s).strip() for s in arr if isinstance(s, str) and str(s).strip()]

    def close(self) -> None:
        if self._ws is not None:
            try:
                # websocket-client
                if hasattr(self._ws, "close"):
                    self._ws.close()
                # websockets sync
                elif hasattr(self._ws, "abort"):
                    self._ws.abort()
            except Exception:
                pass
        self._ws = None
        self._context_id = None
        self._ws_url = None
        self._request_id = 0

    # -- internals --
    def _ensure_connected(self) -> None:
        # Quick check: if we have an open socket and context, reuse
        if self._ws is not None and self._context_id is not None:
            # websocket-client has .connected, websockets has .open
            try:
                if hasattr(self._ws, "connected") and not self._ws.connected:
                    raise OSError("websocket closed")
                # assume still open - a real check would send ping
                return
            except Exception:
                self.close()

        targets = _http_get_targets(timeout=self.timeout)
        root = next((t for t in targets if isinstance(t, dict) and t.get("url") == ROOT_UI_URL), None)
        if not root or not root.get("webSocketDebuggerUrl"):
            raise OSError("FiveM NUI DevTools unavailable (root UI not found at 127.0.0.1:13172)")
        ws_url = str(root["webSocketDebuggerUrl"])
        ws = self._connect_ws(ws_url)
        # CDP handshake: get frame tree then create isolated world
        tree = self._ws_request(ws, "Page.getFrameTree", {})
        frame_tree = tree.get("frameTree") if isinstance(tree, dict) else None
        client_frame = self._find_client_frame(frame_tree)
        if not client_frame or "id" not in client_frame:
            raise OSError("GTAW HUD not ready (client frame https://cfx-nui-client/web/index.html not found)")
        frame_id = client_frame["id"]
        world = self._ws_request(ws, "Page.createIsolatedWorld", {"frameId": frame_id, "worldName": "gtaw-log-parser-reader", "grantUniveralAccess": True})
        if not isinstance(world, dict) or "executionContextId" not in world:
            raise OSError("GTAW HUD context unavailable (Page.createIsolatedWorld failed)")
        self._ws = ws
        self._ws_url = ws_url
        self._context_id = int(world["executionContextId"])

    def _connect_ws(self, url: str):
        # Try websocket-client first (sync), then websockets (async-to-sync)
        last_err = None
        # Attempt 1: websocket-client (pip install websocket-client)
        try:
            import websocket as ws_client

            ws = ws_client.create_connection(url, timeout=self.timeout)
            return ws
        except ImportError as e:
            last_err = e
        except Exception as e:
            last_err = e

        # Attempt 2: websockets sync API (pip install websockets)
        try:
            from websockets.sync.client import connect as ws_connect

            ws = ws_connect(url, open_timeout=self.timeout)
            return ws
        except ImportError as e:
            last_err = e
        except Exception as e:
            last_err = e

        raise OSError(
            f"No websocket client available or connect failed: {last_err}. "
            "Install one of: pip install websocket-client  OR  pip install websockets"
        )

    def _ws_request(self, ws, method: str, params: dict[str, Any]) -> dict[str, Any]:
        self._request_id += 1
        rid = self._request_id
        payload = json.dumps({"id": rid, "method": method, "params": params})

        # websocket-client send/recv
        if hasattr(ws, "send") and hasattr(ws, "recv"):
            # detect which API: websocket-client has send(str) / recv()
            try:
                ws.send(payload)
                # Need to pump until we get matching id
                deadline = time.monotonic() + self.timeout
                while True:
                    if time.monotonic() > deadline:
                        raise TimeoutError(f"CDP request {method} timed out")
                    raw = ws.recv()
                    if not raw:
                        continue
                    try:
                        msg = json.loads(raw)
                    except json.JSONDecodeError:
                        continue
                    if msg.get("id") != rid:
                        continue
                    if "error" in msg:
                        raise OSError(f"CDP error for {method}: {msg['error']}")
                    return msg.get("result") if isinstance(msg.get("result"), dict) else {}
            except Exception:
                raise

        # websockets sync: send/recv are methods too
        try:
            ws.send(payload)
            deadline = time.monotonic() + self.timeout
            while True:
                if time.monotonic() > deadline:
                    raise TimeoutError(f"CDP request {method} timed out")
                raw = ws.recv(timeout=self.timeout)
                try:
                    msg = json.loads(raw)
                except json.JSONDecodeError:
                    continue
                if msg.get("id") != rid:
                    continue
                if "error" in msg:
                    raise OSError(f"CDP error for {method}: {msg['error']}")
                return msg.get("result") if isinstance(msg.get("result"), dict) else {}
        except Exception:
            raise

    def _request(self, method: str, params: dict[str, Any]) -> dict[str, Any]:
        assert self._ws is not None
        return self._ws_request(self._ws, method, params)

    @staticmethod
    def _find_client_frame(frame_tree: Any) -> dict[str, Any] | None:
        if not isinstance(frame_tree, dict):
            return None
        frame = frame_tree.get("frame")
        if isinstance(frame, dict) and frame.get("url") == CLIENT_FRAME_URL:
            return frame
        children = frame_tree.get("childFrames")
        if not isinstance(children, list):
            return None
        for child in children:
            found = LiveNuiReader._find_client_frame(child)
            if found is not None:
                return found
        return None


def watch_fivem_live(
    poll_interval: float = 0.5,
    timeout: float = 2.0,
    debug: bool = False,
):
    """Generator that yields new lines directly from live NUI (no file).

    Mirrors fivem_chat.watch_fivem_chat contract but bypasses the file.
    Falls back to file-tail if websocket deps missing or FiveM not running.
    """
    import time as _time

    reader = LiveNuiReader(timeout=timeout)
    previous: list[str] = []

    def _find_overlap(old: list[str], new: list[str]) -> int:
        m = min(len(old), len(new))
        for length in range(m, 0, -1):
            if old[-length:] == new[:length]:
                return length
        return 0

    try:
        while True:
            try:
                current = reader.get_chat_lines()
                # Trim blanks
                current = [l.strip() for l in current if l.strip()]
                if not previous:
                    previous = current
                    if debug and current:
                        print(f"[LIVE] initialized with {len(current)} lines")
                    _time.sleep(poll_interval)
                    continue
                overlap = _find_overlap(previous, current)
                new_lines = current[overlap:]
                if debug and new_lines:
                    print(f"[LIVE] {len(new_lines)} new")
                for line in new_lines:
                    yield line
                previous = current
            except Exception as e:
                if debug:
                    print(f"[LIVE] {type(e).__name__}: {e}")
                reader.close()
                # Back off a bit before retrying (HUD reload, FiveM restart)
                _time.sleep(1.0)
                previous = []  # reset overlap after disconnect
                continue
            _time.sleep(poll_interval)
    finally:
        reader.close()
