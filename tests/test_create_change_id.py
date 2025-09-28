import re
import pytest

from git_publish.main import create_change_id


def test_create_change_id_uses_username_when_env_missing(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv("GITPUBLISH_BRANCH_PREFIX", raising=False)
    # We cannot rely on specific username, but we can assert format `name/xxxx`
    change_id = create_change_id()
    assert "/" in change_id
    name, suffix = change_id.split("/", 1)
    assert len(name) > 0
    assert re.fullmatch(r"[0-9a-f]{4}", suffix)


def test_create_change_id_uses_env_prefix(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("GITPUBLISH_BRANCH_PREFIX", "prefix")
    change_id = create_change_id()
    assert change_id.startswith("prefix/")
