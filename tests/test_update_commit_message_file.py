from pathlib import Path

import pytest

from git_publish.main import update_commit_message_file


def write(path: Path, content: str) -> None:
    path.write_text(content)


def read(path: Path) -> str:
    return path.read_text()


def test_update_commit_message_file_appends_when_missing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITPUBLISH_CHANGE_ID_PREFIX", "Change:")
    message_path = tmp_path / "COMMIT_EDITMSG"
    write(message_path, "feat: hello\n\nBody\n")

    update_commit_message_file(str(message_path))

    content = read(message_path)
    assert content.startswith("feat: hello\n\nBody\n")
    last_line = content.rstrip().splitlines()[-1]
    assert last_line.startswith("Change: ")
    # Should contain a user/hash after the prefix
    assert len(last_line.split("Change: ", 1)[1]) > 0


def test_update_commit_message_file_keeps_existing_change_id(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITPUBLISH_CHANGE_ID_PREFIX", "Change-Id:")
    message_path = tmp_path / "COMMIT_EDITMSG"
    write(message_path, "fix: again\n\nBody\n\nChange-Id: user/1234\n")

    update_commit_message_file(str(message_path))

    content = read(message_path)
    assert content.endswith("\nChange-Id: user/1234\n")
