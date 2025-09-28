import pytest

from git_publish.main import (
    append_change_id_in_commit_message,
    get_change_id,
    strip_change_id,
)


def test_append_change_id_in_commit_message_uses_prefix_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITPUBLISH_CHANGE_ID_PREFIX", "Change:")
    message = "feat: do thing\n\nBody here.\n"
    result = append_change_id_in_commit_message("user/1a2b", message)
    assert result.endswith("\n\nChange: user/1a2b\n")


def test_get_change_id_parses_prefix_default(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITPUBLISH_CHANGE_ID_PREFIX", raising=False)
    message = "subject\n\nChange-Id: alice/abcd\n"
    assert get_change_id(message) == "alice/abcd"


def test_get_change_id_parses_custom_prefix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITPUBLISH_CHANGE_ID_PREFIX", "X-Change:")
    message = "subject\n\nX-Change: bob/1234\n"
    assert get_change_id(message) == "bob/1234"


def test_get_change_id_returns_none_when_absent(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITPUBLISH_CHANGE_ID_PREFIX", raising=False)
    message = "subject only\n"
    assert get_change_id(message) is None


def test_strip_change_id_removes_line_with_default_prefix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITPUBLISH_CHANGE_ID_PREFIX", raising=False)
    message = "s\n\nbody\nChange-Id: cathy/c0de\ntrailing\n"
    assert strip_change_id(message) == "s\n\nbody\ntrailing"


def test_strip_change_id_removes_line_with_custom_prefix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITPUBLISH_CHANGE_ID_PREFIX", "Change:")
    message = "s\n\nbody\nChange: dave/beef\n"
    assert strip_change_id(message) == "s\n\nbody"
