"""Manifest-scoped, loopback-first depot serving.

Only files registered in the depot manifest are reachable. There is no
directory listing, no implicit root discovery, and no path outside the artifact
root can be requested. Serving is a retention-safe read: nothing is written.
"""

from __future__ import annotations

import http.server
import mimetypes
import urllib.parse
from pathlib import Path
from typing import Callable, Dict, Optional, Tuple

from sonic.lib.depot import compute_sha256, load_depot_manifest

ArtifactIndex = Dict[str, Tuple[Path, str]]
CHUNK = 65536


class ServeError(Exception):
    """Raised when a depot cannot be served safely."""


def build_artifact_index(depot_dir: Path) -> ArtifactIndex:
    """Map URL paths to the exact registered file and its recorded digest.

    Records whose file is missing, or which resolve outside the artifact root
    (for example through a symlink), are dropped rather than served.
    """
    root = Path(depot_dir).expanduser().resolve()
    if not root.is_dir():
        raise ServeError(f"Artifact root does not exist: {root}")

    index: ArtifactIndex = {}
    for record in load_depot_manifest(root).values():
        if not record.relative_path:
            continue
        candidate = root / record.relative_path
        try:
            resolved = candidate.resolve(strict=True)
        except OSError:
            continue
        if not resolved.is_relative_to(root) or not resolved.is_file():
            continue
        index[f"/{record.relative_path}"] = (resolved, record.sha256)
    return index


def create_handler(
    index: ArtifactIndex,
    verify: bool = True,
    on_mismatch: Optional[Callable[[str], None]] = None,
) -> type[http.server.BaseHTTPRequestHandler]:
    """Build a handler that answers only for indexed paths."""

    checked: Dict[str, bool] = {}

    def checksum_ok(key: str, target: Path, expected: str) -> bool:
        if key not in checked:
            checked[key] = compute_sha256(target) == expected
            if not checked[key] and on_mismatch is not None:
                on_mismatch(key)
        return checked[key]

    class DepotHandler(http.server.BaseHTTPRequestHandler):
        server_version = "SonicDepot/1"

        def do_GET(self) -> None:  # noqa: N802
            self._respond(head_only=False)

        def do_HEAD(self) -> None:  # noqa: N802
            self._respond(head_only=True)

        def _reject(self, status: int, reason: str) -> None:
            body = f"{reason}\n".encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)

        def _respond(self, head_only: bool) -> None:
            raw_path = urllib.parse.urlsplit(self.path).path
            path = urllib.parse.unquote(raw_path)

            if "\x00" in path or ".." in path or path.endswith("/"):
                self._reject(404, "Not found")
                return

            entry = index.get(path)
            if entry is None:
                self._reject(404, "Not found")
                return

            target, expected = entry
            if verify and not checksum_ok(path, target, expected):
                self._reject(500, "Registered artifact failed verification")
                return

            try:
                size = target.stat().st_size
                stream = target.open("rb")
            except OSError:
                self._reject(404, "Not found")
                return

            with stream:
                self.send_response(200)
                content_type = mimetypes.guess_type(target.name)[0] or "application/octet-stream"
                self.send_header("Content-Type", content_type)
                self.send_header("Content-Length", str(size))
                self.send_header("X-Sonic-SHA256", expected)
                self.end_headers()
                if head_only:
                    return
                while chunk := stream.read(CHUNK):
                    self.wfile.write(chunk)

        def list_directory(self, path):  # noqa: ARG002
            return None  # never generate a listing

        def log_message(self, fmt: str, *args) -> None:
            print(f"depot: {self.address_string()} {fmt % args}", flush=True)

    return DepotHandler


def serve_depot(
    depot_dir: Path,
    host: str = "127.0.0.1",
    port: int = 8088,
    verify: bool = True,
    on_mismatch: Optional[Callable[[str], None]] = None,
    ready: Optional[Callable[[int], None]] = None,
) -> None:
    """Serve the registered artifacts until interrupted."""
    index = build_artifact_index(depot_dir)
    if not index:
        raise ServeError("No registered artifacts to serve in this depot")

    handler = create_handler(index, verify=verify, on_mismatch=on_mismatch)

    class Server(http.server.ThreadingHTTPServer):
        daemon_threads = True
        allow_reuse_address = True

    with Server((host, port), handler) as httpd:
        if ready is not None:
            ready(httpd.server_address[1])
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
