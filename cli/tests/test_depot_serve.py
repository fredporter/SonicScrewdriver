"""Depot serving must expose only registered files, and only from the root."""

from __future__ import annotations

import hashlib
import http.client
import inspect
import http.server
import os
import threading
from pathlib import Path

import pytest
from click.testing import CliRunner

import sonic.lib.serve as serve_module
from sonic.cli import cli
from sonic.lib.depot import DepotRecord, save_depot_manifest
from sonic.lib.serve import build_artifact_index, create_handler, serve_depot

ALPHA = b"ALPHA-PAYLOAD"


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


@pytest.fixture
def served_depot(tmp_path: Path) -> Path:
    depot = tmp_path / "depot"
    depot.mkdir()
    (depot / "alpha.bin").write_bytes(ALPHA)
    (depot / "secret.txt").write_bytes(b"UNREGISTERED")
    (depot / "private").mkdir()
    (depot / "private" / "hidden.txt").write_bytes(b"HIDDEN")

    outside = tmp_path / "outside.txt"
    outside.write_bytes(b"OUTSIDE")
    (depot / "link.txt").symlink_to(outside)

    save_depot_manifest(
        depot,
        {
            "alpha": DepotRecord(
                id="alpha",
                kind="installer",
                version="1",
                file_name="alpha.bin",
                relative_path="alpha.bin",
                size_bytes=len(ALPHA),
                sha256=digest(ALPHA),
            ),
            "link": DepotRecord(
                id="link",
                kind="installer",
                version="1",
                file_name="link.txt",
                relative_path="link.txt",
                size_bytes=len(b"OUTSIDE"),
                sha256=digest(b"OUTSIDE"),
            ),
        },
    )
    return depot


@pytest.fixture
def depot_server(served_depot: Path):
    handler = create_handler(build_artifact_index(served_depot))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server.server_address[1]
    finally:
        server.shutdown()
        server.server_close()


def request(port: int, path: str, method: str = "GET"):
    connection = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    connection.request(method, path)
    response = connection.getresponse()
    body = response.read()
    connection.close()
    return response, body


def test_index_drops_unregistered_and_escaping_entries(served_depot: Path):
    index = build_artifact_index(served_depot)
    assert set(index) == {"/alpha.bin"}


def test_serves_a_registered_artifact(depot_server: int):
    response, body = request(depot_server, "/alpha.bin")
    assert response.status == 200
    assert body == ALPHA
    assert response.getheader("X-Sonic-SHA256") == digest(ALPHA)


def test_unregistered_file_is_not_served(depot_server: int):
    response, body = request(depot_server, "/secret.txt")
    assert response.status == 404
    assert b"UNREGISTERED" not in body


def test_unregistered_directory_is_not_listed(depot_server: int):
    for path in ("/private/hidden.txt", "/private/", "/"):
        response, _ = request(depot_server, path)
        assert response.status == 404


def test_traversal_and_encoded_traversal_are_refused(depot_server: int):
    for path in ("/../outside.txt", "/%2e%2e/outside.txt", "/..%2foutside.txt"):
        response, body = request(depot_server, path)
        assert response.status == 404
        assert b"OUTSIDE" not in body


def test_symlink_escape_is_not_served(depot_server: int):
    response, body = request(depot_server, "/link.txt")
    assert response.status == 404
    assert b"OUTSIDE" not in body


def test_head_has_no_body(depot_server: int):
    response, body = request(depot_server, "/alpha.bin", method="HEAD")
    assert response.status == 200
    assert body == b""
    assert response.getheader("Content-Length") == str(len(ALPHA))


def test_change_after_first_response_is_detected(served_depot: Path, depot_server: int):
    first, body = request(depot_server, "/alpha.bin")
    assert first.status == 200
    assert body == ALPHA

    # Rewrite through a hardlink: same inode, so a path-only check cannot help.
    alias = served_depot / "alpha-alias.bin"
    os.link(served_depot / "alpha.bin", alias)
    alias.write_bytes(b"BRAVO-PAYLOAD")  # deliberately the same length

    second, tampered = request(depot_server, "/alpha.bin")
    assert second.status == 500
    assert b"BRAVO" not in tampered


def test_verification_is_per_request_and_tied_to_the_served_descriptor():
    source = inspect.getsource(serve_module)

    assert "checked" not in source, "verification must not be cached across requests"
    assert "os.fstat(stream.fileno())" in source, "size must come from the opened descriptor"
    assert "stream.seek(0)" in source, "the hashed bytes must be the served bytes"
    assert "compute_sha256" not in source, "hashing must use the open stream, not a second open"


def test_tampered_artifact_is_refused(served_depot: Path):
    (served_depot / "alpha.bin").write_bytes(b"TAMPERED")
    handler = create_handler(build_artifact_index(served_depot))
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    server.daemon_threads = True
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        response, body = request(server.server_address[1], "/alpha.bin")
        assert response.status == 500
        assert b"TAMPERED" not in body
    finally:
        server.shutdown()
        server.server_close()


def test_serve_defaults_to_loopback():
    assert inspect.signature(serve_depot).parameters["host"].default == "127.0.0.1"


def test_cli_requires_an_explicit_root(monkeypatch):
    monkeypatch.delenv("SONIC_DEPOT_ROOT", raising=False)
    runner = CliRunner()
    result = runner.invoke(cli, ["depot", "serve"], env={"SONIC_DEPOT_ROOT": ""})
    assert result.exit_code != 0
    assert "explicit artifact root is required" in result.output
