import json

import pytest

from sonic.cli import cli
from sonic.lib.settings import import_legacy, state_root


def test_paths_are_read_only(tmp_path, monkeypatch, runner):
    monkeypatch.setenv("UDOS_HOME", str(tmp_path / "state"))
    result = runner.invoke(cli, ["config", "paths"])
    assert result.exit_code == 0
    assert json.loads(result.output)["state"] == str(tmp_path / "state" / "sonic")
    assert not (tmp_path / "state").exists()


@pytest.mark.parametrize("value", ["", "relative/path"])
def test_invalid_state_root(value, monkeypatch):
    monkeypatch.setenv("UDOS_HOME", value)
    with pytest.raises(ValueError):
        state_root()


def test_preview_apply_preserve_and_refuse_overwrite(tmp_path, monkeypatch):
    monkeypatch.setenv("UDOS_HOME", str(tmp_path / "state"))
    source = tmp_path / "old"
    source.mkdir()
    (source / "events.jsonl").write_bytes(b'{"event":1}\n')
    preview = import_legacy(source)
    assert not (tmp_path / "state").exists()
    assert preview["copied"] == []
    result = import_legacy(source, True)
    assert result["copied"] == ["events.jsonl"]
    assert "receipt" in result
    assert result["receipt"]["schema"] == "sonic.intake-receipt/1"
    assert result["receipt"]["file_count"] == 1
    dest = state_root() / "imports/legacy/events.jsonl"
    assert dest.read_bytes() == (source / "events.jsonl").read_bytes()
    receipt_file = state_root() / "imports/legacy/receipt.json"
    assert receipt_file.exists()
    receipt_content = json.loads(receipt_file.read_text(encoding="utf-8"))
    assert receipt_content["files"][0]["path"] == "events.jsonl"
    with pytest.raises(ValueError, match="already exists"):
        import_legacy(source, True)


def test_reject_symlink_and_overlap(tmp_path, monkeypatch):
    monkeypatch.setenv("UDOS_HOME", str(tmp_path / "state"))
    source = tmp_path / "old"
    source.mkdir()
    (source / "link").symlink_to(tmp_path / "outside")
    with pytest.raises(ValueError, match="Unsupported"):
        import_legacy(source, True)
    assert not (tmp_path / "state").exists()
    with pytest.raises(ValueError, match="overlap"):
        import_legacy(tmp_path)
